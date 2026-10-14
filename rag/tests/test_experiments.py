import numpy as np
import pytest
from rag.examples.retrieval_experiments import prepare_variant, evaluate_rankings
from rag.retrieval import retrieve_top_documents

class Tokenizer:
    def __call__(self, text, **kwargs): return {'input_ids': list(range(len(text.split()) + 2))}
class Model:
    tokenizer = Tokenizer()

def test_overlap_toggle_and_token_budget():
    docs = [{'_id':'d', 'title':'Title', 'text':'One two. Three four. Five six.'}]
    overlapping = prepare_variant(docs, Model(), 8, True, True)
    separate = prepare_variant(docs, Model(), 8, False, True)
    assert [c['text'] for c in overlapping] == ['Title\nOne two. Three four.', 'Title\nThree four. Five six.']
    assert [c['text'] for c in separate] == ['Title\nOne two. Three four.', 'Title\nFive six.']
    assert all(c['token_count'] <= 8 for c in overlapping + separate)
    assert all(c['document_id'] == 'd' for c in overlapping)

def test_title_toggle_and_long_sentence_fallback():
    docs = [{'_id':'d', 'title':'Title', 'text':'One two three four five six seven eight.'}]
    chunks = prepare_variant(docs, Model(), 7, False, False)
    assert ' '.join(c['text'] for c in chunks) == docs[0]['text']
    assert all(c['token_count'] <= 7 for c in chunks)

def test_document_ranking_deduplicates_chunks():
    vectors = np.array([[1.,0.], [.8,.6], [0.,1.]])
    chunks = [{'document_id':'a'}, {'document_id':'a'}, {'document_id':'b'}]
    assert retrieve_top_documents(np.array([1.,0.]), vectors, chunks, 2) == ['a','b']
    with pytest.raises(ValueError): retrieve_top_documents(np.array([1.,0.]), vectors, chunks, 0)

def test_averages_metrics_over_queries():
    chunks = [{'document_id':'a'}, {'document_id':'b'}]
    vectors = np.eye(2)
    queries = [{'_id':'q1','text':'first'}, {'_id':'q2','text':'second'}]
    metrics, details, _ = evaluate_rankings(queries, {'q1':{'a'},'q2':{'a'}}, chunks, vectors, vectors)
    assert metrics['1']['recall'] == .5
    assert metrics['5']['recall'] == 1.
    assert metrics['5']['mrr'] == .75
    assert metrics['5']['precision'] == .2
    assert len(details) == 2
