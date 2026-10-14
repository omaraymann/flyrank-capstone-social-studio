"""BGE-specific chunking experiments using its actual token budget."""
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
import numpy as np
from sentence_transformers import SentenceTransformer
from rag.cache import file_hash, serialize_chunks
from rag.chunking import prepare_passage, split_into_sentences
from rag.examples.retrieval_baseline import DATA_DIR, load_documents, load_training_queries
from rag.examples.retrieval_experiments import KS, evaluate_rankings
from rag.examples.embedding_model_comparison import validate_arrays, validate_inputs
from rag.examples.export_retrieval_results import export_results

RESULT_DIR = DATA_DIR.parents[1] / 'results/scifact_bge_chunking'
REFERENCE_DIR = DATA_DIR.parents[1] / 'results/scifact_models'


def prepare_bge_chunks(documents, tokenizer, budget, overlap, titles):
    """Pack complete sentences with optional overlap; BGE has no passage prefix."""
    def count(text):
        return len(tokenizer(text, truncation=False, add_special_tokens=True, verbose=False)['input_ids'])
    chunks = []
    for doc in documents:
        title = doc.get('title') if titles else None
        full = prepare_passage(doc['text'], title)
        if count(full) <= budget:
            passages = [full]
        else:
            pieces = []
            for sentence in split_into_sentences(doc['text']):
                if count(prepare_passage(sentence, title)) <= budget:
                    pieces.append(sentence)
                else:
                    words = []
                    for word in sentence.split():
                        if count(prepare_passage(' '.join(words + [word]), title)) <= budget:
                            words.append(word)
                        else:
                            if words: pieces.append(' '.join(words))
                            if count(prepare_passage(word, title)) > budget:
                                raise ValueError('Single word/title exceeds BGE chunk budget')
                            words = [word]
                    if words: pieces.append(' '.join(words))
            passages, current = [], []
            for piece in pieces:
                if count(prepare_passage(' '.join(current + [piece]), title)) <= budget:
                    current.append(piece)
                    continue
                passages.append(prepare_passage(' '.join(current), title))
                candidate = [current[-1], piece] if overlap else [piece]
                current = candidate if count(prepare_passage(' '.join(candidate), title)) <= budget else [piece]
            if current: passages.append(prepare_passage(' '.join(current), title))
        for index, passage in enumerate(passages):
            token_count = count(passage)
            if token_count > budget: raise ValueError('Chunk exceeds BGE token budget')
            chunks.append({'document_id': doc['_id'], 'chunk_index': index,
                           'text': passage, 'token_count': token_count})
    return chunks


def main():
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    documents = load_documents(DATA_DIR)
    queries, labels = load_training_queries(DATA_DIR)
    sources = {name: file_hash(DATA_DIR / name) for name in ['corpus.jsonl','queries.jsonl','qrels/train.tsv']}
    manifest = json.loads((REFERENCE_DIR / 'bge_small_en_v1_5/manifest.json').read_text())
    identity = manifest['identity']
    if identity['source_hashes'] != sources: raise ValueError('Reference dataset changed')
    if identity['query_ids'] != [q['_id'] for q in queries]: raise ValueError('Reference query order changed')
    folder = REFERENCE_DIR / 'bge_small_en_v1_5'
    for filename, digest in manifest['files'].items():
        if file_hash(folder / filename) != digest: raise ValueError('Reference checksum mismatch')
    query_vectors = np.load(folder / 'query_vectors.npy', allow_pickle=False)
    original_vectors = np.load(folder / 'passage_vectors.npy', allow_pickle=False)
    original_chunk_file = DATA_DIR.parents[1] / 'processed/scifact/chunks.jsonl'
    if file_hash(original_chunk_file) != identity['chunk_sha256']: raise ValueError('Reference passages changed')
    original_chunks = [json.loads(line) for line in original_chunk_file.open() if line.strip()]
    validate_arrays(original_vectors, query_vectors, len(original_chunks), len(queries), 384)
    known = {c['text']: v for c,v in zip(original_chunks, original_vectors)}
    model = SentenceTransformer(identity['model'], revision=identity['model_revision'], device='cpu', local_files_only=True)
    model.default_prompt_name = None
    model.prompts = {}
    reference = json.loads((REFERENCE_DIR / 'bge_small_en_v1_5.json').read_text())
    reference['variant'] = 'original_fixed_chunks_reference'
    reference['note'] = 'Reference uses original E5-generated chunks (5680), not native BGE 512-token chunking.'
    (RESULT_DIR / 'original_fixed_chunks_reference.json').write_text(json.dumps(reference, indent=2))
    summary = [reference]
    for name, budget, overlap, titles in [
        ('bge_512_overlap_title',512,True,True), ('bge_256_overlap_title',256,True,True),
        ('bge_512_no_overlap_title',512,False,True), ('bge_512_overlap_no_title',512,True,False)]:
        chunks = prepare_bge_chunks(documents, model.tokenizer, budget, overlap, titles)
        validate_inputs(model, [c['text'] for c in chunks])
        output = RESULT_DIR / name
        output.mkdir(exist_ok=True)
        (output / 'chunks.jsonl').write_bytes(serialize_chunks(chunks))
        settings = {**identity, 'chunk_sha256': file_hash(output / 'chunks.jsonl'),
                    'chunking_version':name, 'max_tokens':budget, 'sentence_overlap':overlap,
                    'include_title':titles, 'runner_sha256':file_hash(Path(__file__))}
        vector_file = output / 'vectors.npy'
        cache_file = output / 'manifest.json'
        cached = json.loads(cache_file.read_text()) if cache_file.exists() else None
        started = perf_counter()
        missing = list(dict.fromkeys(c['text'] for c in chunks if c['text'] not in known))
        if cached and cached['settings']==settings and vector_file.exists() and file_hash(vector_file)==cached['sha256']:
            vectors = np.load(vector_file,allow_pickle=False)
            print(name, 'reusing verified cache',flush=True)
        else:
            print(f'{name}: {len(chunks)} chunks; {len(missing)} new passage embeddings',flush=True)
            if missing:
                encoded = model.encode(missing,batch_size=16,normalize_embeddings=True,
                                       convert_to_numpy=True,show_progress_bar=True)
                known.update(zip(missing,encoded))
            vectors = np.stack([known[c['text']] for c in chunks])
            np.save(vector_file,vectors)
            cache_file.write_text(json.dumps({'settings':settings,'sha256':file_hash(vector_file)},indent=2))
        known.update(zip((c['text'] for c in chunks),vectors))
        preparation_seconds = perf_counter()-started
        validate_arrays(vectors,query_vectors,len(chunks),len(queries),384)
        metrics,details,search_seconds = evaluate_rankings(queries,labels,chunks,vectors,query_vectors)
        result={'variant':name,'split':'train','query_count':len(queries),'document_count':len(documents),
                'chunk_count':len(chunks),'max_tokens':budget,'sentence_overlap':overlap,'include_title':titles,
                'settings':settings,'source_hashes':sources,'created_at':datetime.now(timezone.utc).isoformat(),
                'preparation_or_cache_seconds':preparation_seconds,'search_seconds':search_seconds,
                'vector_array_bytes':vectors.nbytes,'metrics':metrics,'per_query':details}
        (RESULT_DIR / f'{name}.json').write_text(json.dumps(result,indent=2))
        summary.append(result)
        (RESULT_DIR / 'comparison.json').write_text(json.dumps([{k:v for k,v in r.items() if k!='per_query'} for r in summary],indent=2))
        export_results(RESULT_DIR)
        print(name,json.dumps(metrics),flush=True)
    lines=['# BGE-small chunking development comparison','','All 809 training-labelled queries, all 5183 documents, same pinned model and cached query vectors. Native BGE token counting includes special tokens and no passage prefix. The original fixed-chunk model-comparison result is retained separately as a reference. Test labels were not read.','',
           '| Configuration | Chunks | k | Precision | Recall | MRR |','|---|---:|---:|---:|---:|---:|']
    for r in summary:
        for k in KS:
            m=r['metrics'][str(k)]
            lines.append(f"| {r['variant']} | {r['chunk_count']} | {k} | {m['precision']:.4f} | {m['recall']:.4f} | {m['mrr']:.4f} |")
    lines+=['','Native 512-token overlap/title is the controlled baseline for the three new variants. Original E5 chunks reserve prefix tokens, so their partition differs slightly from native BGE chunks; compare controlled variants against the native BGE baseline. Identical texts reuse vectors, therefore preparation timing is not a pure inference benchmark. All scores are development-set measurements. Application settings and PostgreSQL data were not changed.']
    (RESULT_DIR / 'REPORT.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__': main()
