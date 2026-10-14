"""Compare fixed and adaptive selection on development document rankings."""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
import numpy as np
from rag.cache import file_hash
from rag.adaptive_retrieval import adaptive_count, apply_token_budget
from rag.evaluation import recall_at_k, reciprocal_rank_at_k
from rag.examples.retrieval_baseline import DATA_DIR, load_training_queries
from rag.examples.embedding_model_comparison import validate_arrays

RESULT_DIR = DATA_DIR.parents[1] / 'results/scifact_adaptive'
CHUNK_DIR = DATA_DIR.parents[1] / 'results/scifact_bge_chunking/bge_512_no_overlap_title'
QUERY_DIR = DATA_DIR.parents[1] / 'results/scifact_models/bge_small_en_v1_5'
METHODS = {
    'fixed_k10': {'k': 10},
    'paper_style_document_adaptive': {'buffer': 5, 'search_fraction': .9},
    'bounded_adaptive_cap5': {'candidate_limit': 30, 'buffer': 1, 'max_selected': 5,
                            'estimated_token_budget': 1500, 'search_fraction': .9},
    # A small fixed comparator helps separate adaptation from returning fewer results.
    'fixed_k5_control': {'k': 5},
    'bounded_cap5_buffer2': {'candidate_limit': 30, 'buffer': 2, 'max_selected': 5,
                           'estimated_token_budget': 1500, 'search_fraction': .9},
    'bounded_cap5_buffer3': {'candidate_limit': 30, 'buffer': 3, 'max_selected': 5,
                           'estimated_token_budget': 1500, 'search_fraction': .9},
}


def save_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer=csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def main():
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    manifest=json.loads((CHUNK_DIR/'manifest.json').read_text())
    if file_hash(CHUNK_DIR/'vectors.npy') != manifest['sha256']: raise ValueError('Passage vectors changed')
    if file_hash(CHUNK_DIR/'chunks.jsonl') != manifest['settings']['chunk_sha256']: raise ValueError('Passages changed')
    query_manifest=json.loads((QUERY_DIR/'manifest.json').read_text())
    if file_hash(QUERY_DIR/'query_vectors.npy') != query_manifest['files']['query_vectors.npy']: raise ValueError('Query vectors changed')
    queries,labels=load_training_queries(DATA_DIR)
    sources={name:file_hash(DATA_DIR/name) for name in ['corpus.jsonl','queries.jsonl','qrels/train.tsv']}
    if sources!=manifest['settings']['source_hashes'] or sources!=query_manifest['identity']['source_hashes']:
        raise ValueError('Source dataset changed')
    if query_manifest['identity']['query_ids'] != [q['_id'] for q in queries]: raise ValueError('Query order changed')
    chunks=[json.loads(line) for line in (CHUNK_DIR/'chunks.jsonl').open() if line.strip()]
    vectors=np.load(CHUNK_DIR/'vectors.npy',allow_pickle=False)
    query_vectors=np.load(QUERY_DIR/'query_vectors.npy',allow_pickle=False)
    validate_arrays(vectors,query_vectors,len(chunks),len(queries),384)
    document_ids=list(dict.fromkeys(c['document_id'] for c in chunks))
    document_positions={document_id:index for index,document_id in enumerate(document_ids)}
    chunk_document_positions=np.array([document_positions[c['document_id']] for c in chunks])
    rows=[]; rankings=[]; started=perf_counter()
    for query,query_vector in zip(queries,query_vectors):
        chunk_scores=vectors @ query_vector
        document_scores=np.full(len(document_ids),-np.inf)
        np.maximum.at(document_scores,chunk_document_positions,chunk_scores)
        # Same tie ordering as the previous chunk-first document-ranking baseline.
        chunk_order=chunk_scores.argsort()[::-1]
        best_chunks={}
        for index in chunk_order:
            best_chunks.setdefault(chunks[index]['document_id'],int(index))
        ordered_ids=list(best_chunks)
        scores=np.array([document_scores[document_positions[i]] for i in ordered_ids])
        token_counts=[chunks[best_chunks[i]]['token_count'] for i in ordered_ids]
        gold=labels[query['_id']]
        for method,params in METHODS.items():
            if 'k' in params: count=min(params['k'],len(scores))
            else:
                count=adaptive_count(scores,buffer=params['buffer'],
                    candidate_limit=params.get('candidate_limit'),max_selected=params.get('max_selected'))
            tokens=sum(token_counts[:count])
            if 'estimated_token_budget' in params:
                count,tokens=apply_token_budget(token_counts,count,params['estimated_token_budget'])
            selected=ordered_ids[:count]; hits=len(set(selected)&gold)
            rows.append({'method':method,'query_id':query['_id'],'query':query['text'],
                'selected_count':count,'estimated_context_tokens':tokens,'relevant_count':len(gold),
                'labelled_hits':hits,'precision':hits/count if count else 0.,
                'recall':recall_at_k(selected,gold,count) if count else 0.,
                'reciprocal_rank':reciprocal_rank_at_k(selected,gold,count) if count else 0.})
            for rank,document_id in enumerate(selected,1):
                index=best_chunks[document_id]
                rankings.append({'method':method,'query_id':query['_id'],'rank':rank,
                    'document_id':document_id,'chunk_index':chunks[index]['chunk_index'],
                    'similarity':float(scores[rank-1]),'labelled_relevant':document_id in gold})
    summaries=[]
    for method in METHODS:
        group=[r for r in rows if r['method']==method]
        counts=np.array([r['selected_count'] for r in group])
        summaries.append({'method':method,'query_count':len(group),
            'precision':float(np.mean([r['precision'] for r in group])),
            'recall':float(np.mean([r['recall'] for r in group])),
            'mrr':float(np.mean([r['reciprocal_rank'] for r in group])),
            'mean_selected':float(counts.mean()),'median_selected':float(np.median(counts)),
            'p95_selected':float(np.percentile(counts,95)), 'max_selected':int(counts.max()),
            'mean_estimated_context_tokens':float(np.mean([r['estimated_context_tokens'] for r in group])),
            'zero_evidence_queries':int(np.sum(counts==0)),
            'no_labelled_hit_queries':sum(r['labelled_hits']==0 for r in group)})
    save_csv(RESULT_DIR/'summary.csv',summaries)
    save_csv(RESULT_DIR/'per_query_metrics.csv',rows)
    save_csv(RESULT_DIR/'rankings.csv',rankings)
    payload={'created_at':datetime.now(timezone.utc).isoformat(),'split':'train','settings':manifest['settings'],
        'source_hashes':sources,'runner_sha256':file_hash(Path(__file__)),'methods':METHODS,'summary':summaries,'per_query':rows,
        'search_seconds':perf_counter()-started,
        'note':'Document-level adaptation: one highest-scoring chunk per unique document. Token counts are BGE-tokenizer estimates including special tokens, not generation-model token counts. Paper-style uses the published gap rule on documents; this is not a reproduction of its passage-level benchmark.'}
    (RESULT_DIR/'results.json').write_text(json.dumps(payload,indent=2))
    lines=['# Adaptive selection development comparison','',payload['note'],'',
        '| Method | Precision | Recall | MRR | Mean documents | Mean estimated tokens | Maximum documents |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in summaries:
        lines.append(f"| {r['method']} | {r['precision']:.4f} | {r['recall']:.4f} | {r['mrr']:.4f} | {r['mean_selected']:.2f} | {r['mean_estimated_context_tokens']:.0f} | {r['max_selected']} |")
    lines+=['','Precision divides by actual selected count per query; empty selections score zero. Fixed k=5 is an additional control to distinguish adaptation from simply returning fewer documents. Scores use only positive qrels; unlabelled results are not confirmed irrelevant. All variants share the same model, query vectors and document rankings. No labels influence the selection rule. Test labels were not read. No generation or judge calls were made. Existing application defaults and PostgreSQL data were not changed.','',
        'Paper-style: largest gap among top 90% of documents, followed by a five-document buffer. Bounded: top-30 candidate documents, one-document buffer, cap of five and 1500 estimated BGE tokens. Buffers of two and three are additional development comparisons with the same cap and token estimate budget. These parameters are not proven optimal. The corpus-wide method can still select a large context; a relative score gap does not guarantee relevance or detect an unanswerable query.','',
        'Reference: https://aclanthology.org/2025.emnlp-main.1017.pdf']
    (RESULT_DIR/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summaries,indent=2),flush=True)

if __name__=='__main__': main()
