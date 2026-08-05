"""Tests for clarifying answer storage and prompt formatting."""

from app.repositories.feature_repository import (
    decode_clarifying_answers,
    encode_clarifying_answers,
    format_clarifying_qa_for_prompt,
)


def test_encode_decode_clarifying_answers_roundtrip():
    raw = encode_clarifying_answers(
        [
            {"question": "Should versioning be manual?", "answer": "Auto from revisions."},
        ]
    )
    assert decode_clarifying_answers(raw) == [
        {"question": "Should versioning be manual?", "answer": "Auto from revisions."},
    ]


def test_format_clarifying_qa_for_prompt_includes_answered_and_unanswered():
    text = format_clarifying_qa_for_prompt(
        ["Q1?", "Q2?"],
        [{"question": "Q1?", "answer": "Yes."}],
    )
    assert "Q: Q1?" in text
    assert "A: Yes." in text
    assert "Q: Q2?" in text
    assert "A: (not answered)" in text


def test_format_clarifying_qa_for_prompt_none_when_no_questions():
    assert format_clarifying_qa_for_prompt([], []) == "(none)"
