from __future__ import annotations

from ollama_copilot_fixer.modelfile import generate_modelfile


def test_qwen35_modelfile_uses_default_no_think_path() -> None:
    modelfile = generate_modelfile(
        absolute_model_path=r"C:\models\qwen35.gguf",
        architecture="qwen35",
        context_length=131072,
        temperature=0.6,
    )

    assert "/no_think" in modelfile
    assert "<think>\n\n</think>\n\n" in modelfile
    assert '"name": <function-name>, "arguments": <args-json-object>' in modelfile


def test_qwen35_legacy_modelfile_keeps_think_prefix() -> None:
    modelfile = generate_modelfile(
        absolute_model_path=r"C:\models\qwen35.gguf",
        architecture="qwen35_legacy",
        context_length=131072,
        temperature=0.6,
    )

    assert "<|im_start|>assistant\n<think>\n" in modelfile
    assert "/no_think" not in modelfile


def test_qwen36_modelfile_defaults_to_no_think_but_supports_think_toggle_and_developer_role() -> None:
    modelfile = generate_modelfile(
        absolute_model_path=r"C:\models\qwen36.gguf",
        architecture="qwen36",
        context_length=131072,
        temperature=0.6,
    )

    assert "/no_think" in modelfile
    assert "/think" in modelfile
    assert "$.IsThinkSet" in modelfile
    assert "$.Think" in modelfile
    assert '.Role "developer"' in modelfile
    assert "<think>\n\n</think>\n\n" in modelfile
    assert "<think>\n" in modelfile
    # When tools are present and no explicit think toggle is set, the template
    # must NOT inject the no-think seed or /no_think suffix; otherwise the model
    # emits narration instead of <tool_call> blocks and the Copilot agent stalls.
    assert "else if not $.Tools" in modelfile


def test_qwen36_modelfile_emits_unsloth_recommended_sampler_params() -> None:
    # Defaults from https://unsloth.ai/docs/models/qwen3.6 (thinking-mode
    # precise coding profile) — see ModelTemplate.recommended_params.
    modelfile = generate_modelfile(
        absolute_model_path=r"C:\models\qwen36.gguf",
        architecture="qwen36",
        context_length=131072,
        temperature=None,
    )

    assert "PARAMETER temperature 0.6" in modelfile
    assert "PARAMETER top_p 0.95" in modelfile
    assert "PARAMETER top_k 20" in modelfile
    assert "PARAMETER min_p 0.0" in modelfile
    assert "PARAMETER repeat_penalty 1.0" in modelfile


def test_qwen35_modelfile_emits_unsloth_recommended_sampler_params() -> None:
    modelfile = generate_modelfile(
        absolute_model_path=r"C:\models\qwen35.gguf",
        architecture="qwen35",
        context_length=131072,
        temperature=None,
    )

    assert "PARAMETER temperature 0.6" in modelfile
    assert "PARAMETER top_p 0.95" in modelfile
    assert "PARAMETER top_k 20" in modelfile
    assert "PARAMETER min_p 0.0" in modelfile
    assert "PARAMETER repeat_penalty 1.0" in modelfile


def test_explicit_temperature_overrides_architecture_default() -> None:
    modelfile = generate_modelfile(
        absolute_model_path=r"C:\models\qwen36.gguf",
        architecture="qwen36",
        context_length=131072,
        temperature=0.9,
    )

    assert "PARAMETER temperature 0.9" in modelfile
    # Other recommended params still come along.
    assert "PARAMETER top_p 0.95" in modelfile
