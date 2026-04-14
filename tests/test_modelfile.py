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
