import numpy as np
import pytest
from rag.examples.embedding_model_comparison import validate_arrays, validate_inputs

class Model:
    max_seq_length = 3
    def tokenizer(self, text, **kwargs): return {'input_ids': text.split()}

def test_input_check_prevents_truncation():
    assert validate_inputs(Model(), ['one two', 'three']) == 2
    with pytest.raises(ValueError, match='comparison stopped'):
        validate_inputs(Model(), ['one two three four'])

def test_array_validation_accepts_different_model_dimensions():
    validate_arrays(np.eye(2), np.array([[1., 0.]]), 2, 1, 2)
    validate_arrays(np.array([[1.,0.,0.]]), np.array([[0.,1.,0.]]), 1, 1, 3)

def test_array_validation_rejects_misaligned_or_invalid_vectors():
    with pytest.raises(ValueError, match='shape mismatch'):
        validate_arrays(np.eye(2), np.eye(2), 3, 2, 2)
    with pytest.raises(ValueError, match='Non-finite'):
        validate_arrays(np.array([[np.nan,0.]]), np.array([[1.,0.]]), 1, 1, 2)
    with pytest.raises(ValueError, match='normalized'):
        validate_arrays(np.array([[2.,0.]]), np.array([[1.,0.]]), 1, 1, 2)
