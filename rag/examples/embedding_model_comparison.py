"""Compare embedding models on fixed SciFact development passages."""
import gc
import json
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
import numpy as np
from huggingface_hub import model_info
from sentence_transformers import SentenceTransformer
from rag.cache import file_hash, load_embedding_cache
from rag.examples.retrieval_baseline import DATA_DIR, load_training_queries
from rag.examples.retrieval_experiments import KS, evaluate_rankings, RESULT_DIR as BASELINE_DIR
from rag.examples.export_retrieval_results import export_results

RESULT_DIR = DATA_DIR.parents[1] / 'results/scifact_models'
MODELS = [
    {'name': 'bge_small_en_v1_5', 'model': 'BAAI/bge-small-en-v1.5', 'dimensions': 384,
     'query_prefix': 'Represent this sentence for searching relevant passages: ', 'passage_prefix': ''},
    {'name': 'e5_base_v2', 'model': 'intfloat/e5-base-v2', 'dimensions': 768,
     'query_prefix': 'query: ', 'passage_prefix': 'passage: '},
]


def validate_inputs(model, texts):
    """Refuse silent truncation so every model receives complete fixed inputs."""
    maximum = 0
    for text in texts:
        size = len(model.tokenizer(text, truncation=False, add_special_tokens=True, verbose=False)['input_ids'])
        maximum = max(maximum, size)
        if size > model.max_seq_length:
            raise ValueError(f'Input has {size} tokens but model accepts {model.max_seq_length}; comparison stopped')
    return maximum


def validate_arrays(passages, queries, chunk_count, query_count, dimensions):
    for vectors, count in [(passages, chunk_count), (queries, query_count)]:
        if vectors.shape != (count, dimensions): raise ValueError('Embedding shape mismatch')
        if not np.isfinite(vectors).all(): raise ValueError('Non-finite embeddings')
        if not np.allclose(np.linalg.norm(vectors, axis=1), 1., atol=1e-5):
            raise ValueError('Embeddings must be normalized')


def write_result(result):
    (RESULT_DIR / (result['variant'] + '.json')).write_text(json.dumps(result, indent=2))
    export_results(RESULT_DIR)


def main():
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    chunks, baseline_vectors = load_embedding_cache(DATA_DIR.parents[1] / 'processed/scifact')
    queries, labels = load_training_queries(DATA_DIR)
    sources = {name: file_hash(DATA_DIR / name) for name in
               ['corpus.jsonl', 'queries.jsonl', 'qrels/train.tsv']}
    baseline = json.loads((BASELINE_DIR / 'baseline_512_overlap_title.json').read_text())
    if baseline['source_hashes'] != sources: raise ValueError('Baseline source files changed')
    if baseline['chunk_count'] != len(chunks): raise ValueError('Baseline chunk count changed')
    if baseline['query_count'] != len(queries): raise ValueError('Baseline queries changed')
    baseline['variant'] = 'e5_small_v2'
    baseline['benchmark_note'] = 'Previously verified baseline; its preparation timing includes cache reads.'
    write_result(baseline)
    summary = [baseline]
    chunk_hash = file_hash(DATA_DIR.parents[1] / 'processed/scifact/chunks.jsonl')
    for spec in MODELS:
        folder = RESULT_DIR / spec['name']
        folder.mkdir(exist_ok=True)
        revision_file = folder / 'revision.txt'
        if revision_file.exists(): revision = revision_file.read_text().strip()
        else:
            revision = model_info(spec['model']).sha
            revision_file.write_text(revision + '\n')
        identity = {**spec, 'model_revision': revision, 'normalized': True, 'device': 'cpu',
                    'batch_size': 16, 'source_hashes': sources, 'chunk_sha256': chunk_hash,
                    'query_ids': [q['_id'] for q in queries],
                    'libraries': {name: version(name) for name in ('sentence-transformers','transformers','torch')},
                    'runner_sha256': file_hash(Path(__file__))}
        manifest_path = folder / 'manifest.json'
        paths = [folder / 'passage_vectors.npy', folder / 'query_vectors.npy']
        saved = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
        if saved and saved['identity'] == identity and all(path.exists() and file_hash(path) == saved['files'][path.name] for path in paths):
            vectors, query_vectors = [np.load(path, allow_pickle=False) for path in paths]
            timings = saved['timings']
            print(f"{spec['name']}: reusing verified vectors", flush=True)
        else:
            print(f"{spec['name']}: loading pinned model {revision}", flush=True)
            start = perf_counter()
            model = SentenceTransformer(spec['model'], revision=revision, device='cpu')
            # Prefixes are supplied explicitly; disable any model-saved prompts.
            model.default_prompt_name = None
            model.prompts = {}
            load_seconds = perf_counter() - start
            passages = [spec['passage_prefix'] + chunk['text'] for chunk in chunks]
            inputs = [spec['query_prefix'] + query['text'] for query in queries]
            max_passage = validate_inputs(model, passages)
            max_query = validate_inputs(model, inputs)
            print(f"{spec['name']}: complete inputs fit; embedding {len(passages)} passages", flush=True)
            start = perf_counter()
            vectors = model.encode(passages, batch_size=16, normalize_embeddings=True,
                                   convert_to_numpy=True, show_progress_bar=True)
            passage_seconds = perf_counter() - start
            print(f"{spec['name']}: embedding {len(inputs)} development queries", flush=True)
            start = perf_counter()
            query_vectors = model.encode(inputs, batch_size=16, normalize_embeddings=True,
                                         convert_to_numpy=True, show_progress_bar=True)
            timings = {'load_seconds': load_seconds, 'passage_embedding_seconds': passage_seconds,
                       'query_embedding_seconds': perf_counter() - start,
                       'max_passage_tokens': max_passage, 'max_query_tokens': max_query,
                       'parameter_count': sum(p.numel() for p in model.parameters())}
            validate_arrays(vectors, query_vectors, len(chunks), len(queries), spec['dimensions'])
            for path, array in zip(paths, [vectors, query_vectors]): np.save(path, array)
            manifest_path.write_text(json.dumps({'identity': identity, 'timings': timings,
                                     'files': {path.name: file_hash(path) for path in paths}}, indent=2))
            del model
            gc.collect()
        validate_arrays(vectors, query_vectors, len(chunks), len(queries), spec['dimensions'])
        metrics, details, search_seconds = evaluate_rankings(queries, labels, chunks, vectors, query_vectors)
        result = {'variant': spec['name'], 'split': 'train', 'query_count': len(queries),
                  'document_count': baseline['document_count'], 'chunk_count': len(chunks),
                  'max_tokens': 512, 'sentence_overlap': True, 'include_title': True,
                  'settings': identity, 'source_hashes': sources, 'chunk_sha256': chunk_hash,
                  'created_at': datetime.now(timezone.utc).isoformat(), 'metrics': metrics,
                  'search_seconds': search_seconds, 'timings': timings,
                  'vector_array_bytes': vectors.nbytes,
                  'preparation_or_cache_seconds': timings['passage_embedding_seconds'] + timings['query_embedding_seconds'],
                  'per_query': details}
        write_result(result)
        summary.append(result)
        print(spec['name'], json.dumps(metrics), flush=True)
        del vectors, query_vectors
        gc.collect()
    (RESULT_DIR / 'comparison.json').write_text(json.dumps([{k:v for k,v in row.items() if k!='per_query'} for row in summary], indent=2))
    lines = ['# Embedding-model development comparison', '',
             'Same 5,680 passages, 809 development queries, maximum chunk-score document ranking, exact cosine search and normalized vectors. Test labels were not read.', '',
             '| Model | Dimensions | k | Precision | Recall | MRR |', '|---|---:|---:|---:|---:|---:|']
    for row in summary:
        for k in KS:
            metric = row['metrics'][str(k)]
            lines.append(f"| {row['settings']['model']} | {row['settings']['dimensions']} | {k} | {metric['precision']:.4f} | {metric['recall']:.4f} | {metric['mrr']:.4f} |")
    lines += ['', 'Each model uses its documented query/passage formatting. Input lengths were checked without truncation. Model revisions, source hashes, library versions, array checksums and per-query results are saved. New-model CPU timings include inference only; model-loading timings include downloads. Baseline preparation timing includes cache reads and is not comparable to new-model encoding time. Vector-array bytes are storage size, not peak runtime memory. These are development results, not held-out estimates. Existing embedding config, cache, and PostgreSQL data were not changed.', '',
              'Model cards: https://huggingface.co/intfloat/e5-base-v2 and https://huggingface.co/BAAI/bge-small-en-v1.5']
    (RESULT_DIR / 'REPORT.md').write_text('\n'.join(lines)+'\n')

if __name__ == '__main__': main()
