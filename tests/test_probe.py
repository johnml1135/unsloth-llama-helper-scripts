from __future__ import annotations

from ollama_copilot_fixer.probe import candidates_for_architecture, evaluate_probe_payload


def test_candidates_for_qwen35_prefers_official_profile_first() -> None:
    candidates = candidates_for_architecture("qwen35")

    assert [c.architecture for c in candidates] == ["qwen35", "qwen35_legacy", "qwen"]


def test_evaluate_probe_payload_accepts_clean_content() -> None:
    accepted, reason, preview = evaluate_probe_payload(
        {"message": {"role": "assistant", "content": "Hello!"}}
    )

    assert accepted is True
    assert reason == "clean final content"
    assert preview == "Hello!"


def test_evaluate_probe_payload_rejects_visible_think_tags() -> None:
    accepted, reason, _ = evaluate_probe_payload(
        {"message": {"role": "assistant", "content": "<think>secret</think>\nHello!"}}
    )

    assert accepted is False
    assert reason == "response leaked visible think tags"


def test_evaluate_probe_payload_rejects_separate_thinking_field() -> None:
    accepted, reason, _ = evaluate_probe_payload(
        {"message": {"role": "assistant", "content": "", "thinking": "secret"}}
    )

    assert accepted is False
    assert reason == "response exposed separate thinking field"


def test_evaluate_probe_payload_rejects_meta_reasoning_text() -> None:
    accepted, reason, _ = evaluate_probe_payload(
        {"message": {"role": "assistant", "content": "The user wants me to think before I answer. Hello!"}}
    )

    assert accepted is False
    assert reason == "response leaked meta reasoning text"
