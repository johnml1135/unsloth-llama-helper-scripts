from __future__ import annotations

from ollama_copilot_fixer import huggingface


def test_enable_fast_hf_transfers_prefers_xet_when_available(monkeypatch) -> None:
    env: dict[str, str] = {}

    monkeypatch.setattr(
        huggingface,
        "_module_available",
        lambda name: name == "hf_xet",
    )

    huggingface._enable_fast_hf_transfers(env)

    assert env["HF_XET_HIGH_PERFORMANCE"] == "1"
    assert "HF_HUB_ENABLE_HF_TRANSFER" not in env


def test_enable_fast_hf_transfers_respects_existing_values(monkeypatch) -> None:
    env = {
        "HF_XET_HIGH_PERFORMANCE": "0",
        "HF_HUB_ENABLE_HF_TRANSFER": "0",
    }

    monkeypatch.setattr(
        huggingface,
        "_module_available",
        lambda name: True,
    )

    huggingface._enable_fast_hf_transfers(env)

    assert env["HF_XET_HIGH_PERFORMANCE"] == "0"
    assert env["HF_HUB_ENABLE_HF_TRANSFER"] == "0"
