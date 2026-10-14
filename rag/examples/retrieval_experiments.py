"""Controlled development-split experiments; never reads test labels."""
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
import numpy as np
from rag import config
from rag.cache import cache_settings, file_hash, load_embedding_cache
from rag.chunking import prepare_passage, count_passage_tokens, split_into_sentences, split_oversized_sentence
from rag.embeddings import load_model, embed_documents, embed_queries
from rag.evaluation import precision_at_k, recall_at_k, reciprocal_rank_at_k
from rag.examples.retrieval_baseline import DATA_DIR, load_documents, load_training_queries
from rag.retrieval import retrieve_top_documents

RESULT_DIR = DATA_DIR.parents[1] / 'results/scifact_development'
KS = [1, 3, 5, 10, 20]


def prepare_variant(documents, model, max_tokens, overlap, include_title):
    """Sentence packing with optional one-sentence overlap and optional titles."""
    chunks = []
    for document in documents:
        title = document.get('title') if include_title else None
        full = prepare_passage(document['text'], title)
        if count_passage_tokens(full, model.tokenizer) <= max_tokens:
            passages = [full]
        else:
            pieces = []
            for sentence in split_into_sentences(document['text']):
                if count_passage_tokens(prepare_passage(sentence, title), model.tokenizer) <= max_tokens:
                    pieces.append(sentence)
                else:
                    pieces.extend(split_oversized_sentence(sentence, model.tokenizer, max_tokens, title))
            passages, current = [], []
            for piece in pieces:
                candidate = prepare_passage(' '.join(current + [piece]), title)
                if count_passage_tokens(candidate, model.tokenizer) <= max_tokens:
                    current.append(piece)
                    continue
                passages.append(prepare_passage(' '.join(current), title))
                shared = [current[-1], piece] if overlap else [piece]
                if count_passage_tokens(prepare_passage(' '.join(shared), title), model.tokenizer) > max_tokens:
                    shared = [piece]
                current = shared
            if current:
                passages.append(prepare_passage(' '.join(current), title))
        for index, passage in enumerate(passages):
            count = count_passage_tokens(passage, model.tokenizer)
            if count > max_tokens: raise ValueError('Oversized experimental passage')
            chunks.append({'document_id': document['_id'], 'chunk_index': index,
                           'text': passage, 'token_count': count})
    return chunks


def evaluate_rankings(queries, labels, chunks, vectors, query_vectors):
    totals = {str(k): {'precision': 0., 'recall': 0., 'mrr': 0.} for k in KS}
    details = []
    started = perf_counter()
    for query, vector in zip(queries, query_vectors):
        ids = retrieve_top_documents(vector, vectors, chunks, top_k=max(KS))
        relevant = labels[query['_id']]
        for k in KS:
            totals[str(k)]['precision'] += precision_at_k(ids, relevant, k)
            totals[str(k)]['recall'] += recall_at_k(ids, relevant, k)
            totals[str(k)]['mrr'] += reciprocal_rank_at_k(ids, relevant, k)
        details.append({'query_id': query['_id'], 'query': query['text'],
                        'relevant_ids': sorted(relevant), 'retrieved_ids': ids})
    for row in totals.values():
        for metric in row: row[metric] /= len(queries)
    return totals, details, perf_counter() - started


def main():
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    documents = load_documents(DATA_DIR)
    queries, labels = load_training_queries(DATA_DIR)
    settings = cache_settings()
    sources = {name: file_hash(DATA_DIR / name) for name in
               ['corpus.jsonl', 'queries.jsonl', 'qrels/train.tsv']}
    model = load_model()
    query_path = RESULT_DIR / 'query_embeddings.npy'
    query_manifest = RESULT_DIR / 'query_manifest.json'
    query_identity = {'settings': settings, 'sources': sources, 'query_ids': [q['_id'] for q in queries],
                      'query_prefix': config.QUERY_PREFIX}
    if query_manifest.exists() and query_path.exists():
        saved = json.loads(query_manifest.read_text())
        if saved['identity'] == query_identity and saved['sha256'] == file_hash(query_path):
            query_vectors = np.load(query_path, allow_pickle=False)
        else: query_vectors = None
    else: query_vectors = None
    if query_vectors is None:
        print(f'Embedding {len(queries)} development queries once...', flush=True)
        query_vectors = embed_queries([q['text'] for q in queries])
        np.save(query_path, query_vectors)
        query_manifest.write_text(json.dumps({'identity': query_identity, 'sha256': file_hash(query_path)}, indent=2))
    if query_vectors.shape != (len(queries), config.EMBEDDING_DIMENSIONS): raise ValueError('Query shape mismatch')
    variants = [('baseline_512_overlap_title', 512, True, True),
                ('512_no_overlap_title', 512, False, True),
                ('256_overlap_title', 256, True, True),
                ('512_overlap_no_title', 512, True, False)]
    baseline_chunks, baseline_vectors = load_embedding_cache(DATA_DIR.parents[1] / 'processed/scifact')
    known_vectors = {chunk['text']: vector for chunk, vector in zip(baseline_chunks, baseline_vectors)}
    summary = []
    for name, budget, overlap, title in variants:
        started = perf_counter()
        if name.startswith('baseline'):
            chunks, vectors = load_embedding_cache(DATA_DIR.parents[1] / 'processed/scifact')
        else:
            chunks = prepare_variant(documents, model, budget, overlap, title)
            cache_dir = RESULT_DIR / name
            cache_dir.mkdir(exist_ok=True)
            identity = {'settings': settings, 'sources': sources, 'budget': budget,
                        'overlap': overlap, 'title': title, 'experiment_code_sha256': file_hash(Path(__file__))}
            manifest_path = cache_dir / 'manifest.json'
            vector_path = cache_dir / 'vectors.npy'
            saved = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
            if saved and saved['identity'] == identity and vector_path.exists() and saved['sha256'] == file_hash(vector_path):
                vectors = np.load(vector_path, allow_pickle=False)
                print(f'{name}: reusing vectors', flush=True)
            else:
                print(f'{name}: embedding {len(chunks)} passages', flush=True)
                missing_texts = list(dict.fromkeys(c['text'] for c in chunks if c['text'] not in known_vectors))
                print(f'{name}: {len(missing_texts)} new texts; reuse identical cached passages', flush=True)
                if missing_texts:
                    new_vectors = embed_documents(missing_texts)
                    known_vectors.update(zip(missing_texts, new_vectors))
                vectors = np.stack([known_vectors[c['text']] for c in chunks])
                np.save(vector_path, vectors)
                manifest_path.write_text(json.dumps({'identity': identity, 'sha256': file_hash(vector_path)}, indent=2))
        embedding_seconds = perf_counter() - started
        metrics, details, search_seconds = evaluate_rankings(queries, labels, chunks, vectors, query_vectors)
        result = {'variant': name, 'split': 'train', 'query_count': len(queries), 'document_count': len(documents),
                  'chunk_count': len(chunks), 'max_tokens': budget, 'sentence_overlap': overlap, 'include_title': title,
                  'settings': settings, 'source_hashes': sources, 'created_at': datetime.now(timezone.utc).isoformat(),
                  'metrics': metrics, 'preparation_or_cache_seconds': embedding_seconds,
                  'search_seconds': search_seconds, 'per_query': details}
        (RESULT_DIR / f'{name}.json').write_text(json.dumps(result, indent=2))
        summary.append({key: value for key, value in result.items() if key != 'per_query'})
        (RESULT_DIR / 'comparison.json').write_text(json.dumps(summary, indent=2))
        print(name, json.dumps(metrics), flush=True)
    lines = ['# SciFact development retrieval comparison', '',
             '809 training-labelled queries against all 5,183 documents. Exact cosine search; document score is maximum chunk score. Test labels were not read.', '',
             '| Configuration | Chunks | k | Precision | Recall | MRR |',
             '|---|---:|---:|---:|---:|---:|']
    for row in summary:
        for k in KS:
            m = row['metrics'][str(k)]
            lines.append(f"| {row['variant']} | {row['chunk_count']} | {k} | {m['precision']:.4f} | {m['recall']:.4f} | {m['mrr']:.4f} |")
    lines += ['', 'Higher k increases evidence volume as well as recall; these retrieval metrics do not establish generation quality. Precision uses a fixed denominator k and incomplete relevance judgments. Timing includes cache reads where reused, so it is not a controlled embedding-speed comparison. All experiments keep model revision, prefixes, and normalization fixed. Existing production cache and PostgreSQL data were not replaced.']
    (RESULT_DIR / 'REPORT.md').write_text('\n'.join(lines)+'\n')

if __name__ == '__main__': main()
