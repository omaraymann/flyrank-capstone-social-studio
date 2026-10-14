"""Export saved retrieval experiments as flat CSV files for plotting."""
import csv
import json
from pathlib import Path
from rag.evaluation import precision_at_k, recall_at_k, reciprocal_rank_at_k
from rag.examples.retrieval_experiments import RESULT_DIR


def write_csv(path, rows):
    if not rows: return
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def export_results(result_dir: Path):
    summaries, query_rows, ranking_rows = [], [], []
    for path in sorted(result_dir.glob('*.json')):
        result = json.loads(path.read_text())
        if not isinstance(result, dict) or 'per_query' not in result: continue
        shared = {key: result[key] for key in ('variant', 'split', 'query_count', 'document_count',
                  'chunk_count', 'max_tokens', 'sentence_overlap', 'include_title', 'created_at')}
        shared.update(model=result['settings']['model'], model_revision=result['settings']['model_revision'])
        timings = result.get('timings', {})
        shared.update(
            embedding_dimensions=result['settings']['dimensions'],
            vector_array_bytes=result.get('vector_array_bytes', ''),
            passage_embedding_seconds=timings.get('passage_embedding_seconds', ''),
            query_embedding_seconds=timings.get('query_embedding_seconds', ''),
            model_load_seconds=timings.get('load_seconds', ''),
            parameter_count=timings.get('parameter_count', ''),
        )
        for k, metrics in result['metrics'].items():
            summaries.append({**shared, 'k': int(k), **metrics,
                              'search_seconds': result['search_seconds'],
                              'preparation_or_cache_seconds': result['preparation_or_cache_seconds']})
        for query in result['per_query']:
            relevant = set(query['relevant_ids'])
            for k in result['metrics']:
                k = int(k)
                query_rows.append({'variant': result['variant'], 'split': result['split'],
                    'query_id': query['query_id'], 'query': query['query'], 'k': k,
                    'relevant_document_count': len(relevant),
                    'precision': precision_at_k(query['retrieved_ids'], relevant, k),
                    'recall': recall_at_k(query['retrieved_ids'], relevant, k),
                    'reciprocal_rank': reciprocal_rank_at_k(query['retrieved_ids'], relevant, k)})
            for rank, document_id in enumerate(query['retrieved_ids'], 1):
                ranking_rows.append({'variant': result['variant'], 'split': result['split'],
                    'query_id': query['query_id'], 'rank': rank, 'document_id': document_id,
                    'labelled_relevant': document_id in relevant})
    write_csv(result_dir / 'summary.csv', summaries)
    write_csv(result_dir / 'per_query_metrics.csv', query_rows)
    write_csv(result_dir / 'rankings.csv', ranking_rows)
    print(f'Exported {len(summaries)} summary rows, {len(query_rows)} query-metric rows, '
          f'{len(ranking_rows)} ranking rows.', flush=True)
    return summaries, query_rows, ranking_rows

if __name__ == '__main__': export_results(RESULT_DIR)
