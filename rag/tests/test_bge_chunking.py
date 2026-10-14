from rag.examples.bge_chunking_experiments import prepare_bge_chunks

class Tokenizer:
    def __call__(self,text,**kwargs): return {'input_ids':list(range(len(text.split())+2))}

def test_bge_counts_without_e5_prefix_and_preserves_overlap():
    docs=[{'_id':'1','title':'Title','text':'One two. Three four. Five six.'}]
    chunks=prepare_bge_chunks(docs,Tokenizer(),8,True,True)
    assert [c['text'] for c in chunks]==['Title\nOne two. Three four.','Title\nThree four. Five six.']
    assert all(c['token_count']==7 for c in chunks)
    assert all(c['document_id']=='1' for c in chunks)

def test_no_overlap_and_no_titles():
    docs=[{'_id':'1','title':'Title','text':'One two. Three four. Five six.'}]
    chunks=prepare_bge_chunks(docs,Tokenizer(),6,False,False)
    assert [c['text'] for c in chunks]==['One two. Three four.','Five six.']
    assert ' '.join(c['text'] for c in chunks)==docs[0]['text']

def test_oversized_sentence_preserves_word_order():
    docs=[{'_id':'1','text':'One two three four five six.'}]
    chunks=prepare_bge_chunks(docs,Tokenizer(),5,False,False)
    assert ' '.join(c['text'] for c in chunks)==docs[0]['text']
    assert all(c['token_count']<=5 for c in chunks)
