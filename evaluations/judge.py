"""Compatibility imports for evaluation scripts; shared judge lives in the app."""
from app.services.factuality import (
    JUDGE_PROMPT_VERSION, JUDGE_PROMPT_V1, JUDGE_PROMPT_V2, JUDGE_PROMPT_V3,
    JUDGE_PROMPT_V4, JUDGE_PROMPT, ClaimVerdict, JudgeResult, SpanAssessment,
    SpanResult, PassageClaim, PassageResult, validate_result, evaluate_draft,
)
