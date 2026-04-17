from __future__ import annotations

from pathlib import Path

from ollama_copilot_fixer.publish import (
    build_hf_repo_id,
    build_model_readme,
    parse_github_remote,
    parse_release_card,
)


def test_parse_release_card_reads_frontmatter_and_body(tmp_path: Path) -> None:
    card_path = tmp_path / "qwen36.md"
    card_path.write_text(
        """---
title: Qwen3.6 UD-IQ4_XS fixed for GitHub Copilot
original_model: https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF
license: apache-2.0
tags:
  - qwen
  - reasoning
architecture: qwen36
context_length: 131072
---
This upload preserves the original GGUF weights and adds the Copilot-safe Modelfile.
""",
        encoding="utf-8",
    )

    card = parse_release_card(card_path)

    assert card.title == "Qwen3.6 UD-IQ4_XS fixed for GitHub Copilot"
    assert card.original_model == "https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF"
    assert card.license_name == "apache-2.0"
    assert card.tags == ("qwen", "reasoning")
    assert card.metadata["architecture"] == "qwen36"
    assert card.metadata["context_length"] == "131072"
    assert "Copilot-safe Modelfile" in card.body


def test_build_model_readme_mentions_copilot_fix(tmp_path: Path) -> None:
    card_path = tmp_path / "qwen36.md"
    card_path.write_text(
        """---
title: Qwen3.6 UD-IQ4_XS fixed for GitHub Copilot
original_model: https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF
license: apache-2.0
tags:
  - qwen
quantization: UD-IQ4_XS
---
Validated against GitHub Copilot local agent tool calling.
""",
        encoding="utf-8",
    )

    readme = build_model_readme(
        card=parse_release_card(card_path),
        repo_id="johnml1135/qwen36-github-copilot",
        gguf_filename="Qwen3.6-35B-A3B-UD-IQ4_XS.gguf",
        modelfile_filename="Modelfile",
        source_repo_url="https://github.com/johnml1135/ollama-copilot-fixer",
    )

    assert "fixed to work with GitHub Copilot" in readme
    assert "Unchanged GGUF weights from the original upstream release" in readme
    assert "ollama create my-copilot-model -f Modelfile" in readme
    assert "UD-IQ4_XS" in readme


def test_build_hf_repo_id_requires_namespace_and_sanitizes_name() -> None:
    assert (
        build_hf_repo_id(namespace="johnml1135", repo_name="Qwen 3.6 Fixed For Copilot")
        == "johnml1135/qwen-3.6-fixed-for-copilot"
    )


def test_parse_github_remote_supports_https_and_ssh() -> None:
    assert parse_github_remote("https://github.com/johnml1135/ollama-copilot-fixer.git") == (
        "johnml1135",
        "ollama-copilot-fixer",
        "https://github.com/johnml1135/ollama-copilot-fixer",
    )
    assert parse_github_remote("git@github.com:johnml1135/ollama-copilot-fixer.git") == (
        "johnml1135",
        "ollama-copilot-fixer",
        "https://github.com/johnml1135/ollama-copilot-fixer",
    )
