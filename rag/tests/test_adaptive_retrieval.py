import numpy as np
import pytest
from rag.adaptive_retrieval import largest_gap_count, adaptive_count, apply_token_budget

def test_largest_gap_uses_count_not_zero_based_index():
    assert largest_gap_count(np.array([.89,.87,.85,.65,.64]))==3
    assert adaptive_count(np.array([.89,.87,.85,.65,.64]),buffer=1)==4

def test_paper_buffer_and_tail_exclusion():
    assert adaptive_count(np.array([.9,.6,.59,.58,.57,.56,.55,.54,.53,.1]),buffer=5)==6

def test_bounded_rule_never_exceeds_cap():
    scores=np.r_[np.linspace(.9,.85,10),np.linspace(.5,.4,20)]
    assert adaptive_count(scores,buffer=1,candidate_limit=30,max_selected=5)==5

def test_small_pools_and_invalid_inputs():
    assert adaptive_count(np.array([]))==0
    assert adaptive_count(np.array([.8]))==1
    with pytest.raises(ValueError): largest_gap_count(np.array([.5,.8]))
    with pytest.raises(ValueError): largest_gap_count(np.array([np.nan]))
    with pytest.raises(ValueError): adaptive_count(np.array([.9,.8]),max_selected=0)

def test_token_budget_keeps_ranked_prefix():
    assert apply_token_budget([512,512,512,100],4,1500)==(2,1024)
    assert apply_token_budget([512],1,100)==(0,0)

def test_small_gaps_are_not_a_relevance_gate():
    assert largest_gap_count(np.array([.5,.49,.48,.46]),search_fraction=1)==3
