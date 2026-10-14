import json
import numpy as np
import pytest
from rag import config
from rag.cache import load_embedding_cache, save_embedding_cache

@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'EMBEDDING_DIMENSIONS', 2)
    chunks = [{'document_id': '1', 'chunk_index': 0, 'text': 'Example.', 'token_count': 4}]
    vectors = np.array([[1., 0.]], dtype=np.float32)
    save_embedding_cache(tmp_path, chunks, vectors)
    return tmp_path, chunks, vectors

def test_round_trip_and_order(cache):
    folder, chunks, vectors = cache
    loaded_chunks, loaded_vectors = load_embedding_cache(folder, chunks)
    assert loaded_chunks == chunks
    np.testing.assert_array_equal(loaded_vectors, vectors)

@pytest.mark.parametrize('setting,value', [('EMBEDDING_MODEL', 'other'), ('EMBEDDING_REVISION', 'other'), ('PASSAGE_PREFIX', 'other'), ('CHUNKING_VERSION', 'other')])
def test_rejects_changed_settings(cache, monkeypatch, setting, value):
    folder, _, _ = cache
    monkeypatch.setattr(config, setting, value)
    with pytest.raises(ValueError, match='settings changed'):
        load_embedding_cache(folder)

def test_rejects_changed_chunks(cache):
    folder, chunks, _ = cache
    changed = [{**chunks[0], 'text': 'Changed.'}]
    with pytest.raises(ValueError, match='Prepared chunks changed'):
        load_embedding_cache(folder, changed)

@pytest.mark.parametrize('name', ['chunks.jsonl', 'chunk_embeddings.npy'])
def test_rejects_corruption(cache, name):
    folder, _, _ = cache
    with (folder / name).open('ab') as stream: stream.write(b'corruption')
    with pytest.raises(ValueError, match='checksum mismatch'):
        load_embedding_cache(folder)

def test_rejects_legacy_cache(cache):
    folder, _, _ = cache
    (folder / 'manifest.json').unlink()
    with pytest.raises(FileNotFoundError): load_embedding_cache(folder)

def test_rejects_invalid_vectors(cache):
    folder, chunks, _ = cache
    with pytest.raises(ValueError, match='not normalized'):
        save_embedding_cache(folder, chunks, np.array([[2., 0.]]))
    with pytest.raises(ValueError, match='finite'):
        save_embedding_cache(folder, chunks, np.array([[np.nan, 0.]]))

def test_baseline_reuses_cache_without_embedding(cache, monkeypatch):
    from rag.examples import retrieval_baseline
    folder, chunks, vectors = cache
    def unexpected(_): raise AssertionError('Must not recompute a valid cache')
    monkeypatch.setattr(retrieval_baseline, 'embed_documents', unexpected)
    result = retrieval_baseline.create_and_save_chunk_embeddings(chunks, folder)
    np.testing.assert_array_equal(result, vectors)

def test_baseline_rebuilds_after_chunk_changes(cache, monkeypatch):
    from rag.examples import retrieval_baseline
    folder, chunks, vectors = cache
    changed = [{**chunks[0], 'text': 'New text.'}]
    calls = []
    def embed(texts):
        calls.append(texts)
        return vectors
    monkeypatch.setattr(retrieval_baseline, 'embed_documents', embed)
    retrieval_baseline.create_and_save_chunk_embeddings(changed, folder)
    assert calls == [['New text.']]
    assert load_embedding_cache(folder, changed)[0] == changed
