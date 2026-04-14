from __future__ import annotations

from pathlib import Path

from ollama_copilot_fixer.gguf import detect_architecture


def test_detect_architecture_qwen35_from_content(tmp_path: Path) -> None:
    file_path = tmp_path / "model.gguf"
    file_path.write_bytes(b"GGUF\x00general.architectureqwen35moe")

    assert detect_architecture(str(file_path)) == "qwen35"


def test_detect_architecture_qwen35_from_filename(tmp_path: Path) -> None:
    file_path = tmp_path / "Qwen3.5-35B-A3B-UD-IQ3_S.gguf"
    file_path.write_bytes(b"GGUF")

    assert detect_architecture(str(file_path)) == "qwen35"
