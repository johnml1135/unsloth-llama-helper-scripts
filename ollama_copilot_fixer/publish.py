from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .huggingface import _enable_fast_hf_transfers


_DEFAULT_TAGS = ("gguf", "ollama", "github-copilot", "tool-calling")


@dataclass(frozen=True)
class ReleaseCard:
    title: str
    original_model: str
    body: str
    license_name: str | None
    tags: tuple[str, ...]
    metadata: dict[str, str]


def sanitize_repo_name(name: str) -> str:
    value = name.strip().lower()
    value = re.sub(r"[^a-z0-9._-]", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "copilot-fixed-model"


def git_remote_origin_url(cwd: Path | None = None) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=str(cwd) if cwd else None,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return None

    remote = (proc.stdout or "").strip()
    return remote or None


def parse_github_remote(url: str | None) -> tuple[str, str, str] | None:
    if not url:
        return None

    cleaned = url.strip()
    cleaned = re.sub(r"\.git$", "", cleaned)

    https_match = re.match(r"^https://github\.com/([^/]+)/([^/]+)$", cleaned)
    if https_match:
        owner, repo = https_match.groups()
        return owner, repo, f"https://github.com/{owner}/{repo}"

    ssh_match = re.match(r"^git@github\.com:([^/]+)/([^/]+)$", cleaned)
    if ssh_match:
        owner, repo = ssh_match.groups()
        return owner, repo, f"https://github.com/{owner}/{repo}"

    return None


def split_frontmatter(markdown: str) -> tuple[str, str]:
    normalized = markdown.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return "", normalized.strip()

    end = normalized.find("\n---\n", 4)
    if end == -1:
        raise ValueError("Release card frontmatter is missing the closing --- line.")

    frontmatter = normalized[4:end]
    body = normalized[end + 5 :].lstrip("\n")
    return frontmatter, body.strip()


def parse_simple_frontmatter(frontmatter: str) -> dict[str, str | list[str]]:
    metadata: dict[str, str | list[str]] = {}
    lines = frontmatter.splitlines()
    idx = 0

    while idx < len(lines):
        line = lines[idx].rstrip()
        if not line.strip():
            idx += 1
            continue

        if ":" not in line:
            raise ValueError(f"Invalid frontmatter line: {line!r}")

        raw_key, raw_value = line.split(":", 1)
        key = raw_key.strip().lower().replace("-", "_")
        value = raw_value.strip()

        if value:
            metadata[key] = value.strip().strip("\"'")
            idx += 1
            continue

        idx += 1
        items: list[str] = []
        while idx < len(lines):
            candidate = lines[idx]
            stripped = candidate.strip()
            if not stripped:
                idx += 1
                continue
            if stripped.startswith("- "):
                items.append(stripped[2:].strip().strip("\"'"))
                idx += 1
                continue
            break
        metadata[key] = items

    return metadata


def parse_release_card(path: Path) -> ReleaseCard:
    markdown = path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(markdown)
    data = parse_simple_frontmatter(frontmatter)

    title = str(data.pop("title", "")).strip()
    original_model = str(data.pop("original_model", "")).strip()
    license_name = str(data.pop("license", "")).strip() or None
    tags_value = data.pop("tags", [])
    tags = tuple(str(item).strip() for item in tags_value if str(item).strip()) if isinstance(tags_value, list) else ()

    if not title:
        raise ValueError(f"Release card {path} is missing required field: title")
    if not original_model:
        raise ValueError(f"Release card {path} is missing required field: original_model")

    metadata = {
        key: str(value).strip()
        for key, value in data.items()
        if not isinstance(value, list) and str(value).strip()
    }

    return ReleaseCard(
        title=title,
        original_model=original_model,
        body=body,
        license_name=license_name,
        tags=tags,
        metadata=metadata,
    )


def extract_hf_repo_id(reference: str) -> str | None:
    cleaned = reference.strip().removesuffix("/")
    for prefix in ("https://huggingface.co/", "http://huggingface.co/", "hf.co/"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
            break

    parts = [part for part in cleaned.split("/") if part]
    if len(parts) >= 2 and ":" not in parts[0]:
        return f"{parts[0]}/{parts[1]}"
    return None


def build_hf_repo_id(*, namespace: str, repo_name: str) -> str:
    cleaned_namespace = namespace.strip().strip("/")
    if not cleaned_namespace:
        raise ValueError("A Hugging Face namespace is required. Pass --namespace or set OLLAMA_COPILOT_FIXER_HF_NAMESPACE.")
    return f"{cleaned_namespace}/{sanitize_repo_name(repo_name)}"


def build_model_readme(
    *,
    card: ReleaseCard,
    repo_id: str,
    gguf_filename: str,
    modelfile_filename: str,
    source_repo_url: str | None,
) -> str:
    base_model = card.metadata.get("base_model") or extract_hf_repo_id(card.original_model) or card.original_model
    tags: list[str] = []
    for tag in (*_DEFAULT_TAGS, *card.tags):
        if tag not in tags:
            tags.append(tag)

    frontmatter = ["---"]
    if card.license_name:
        frontmatter.append(f"license: {card.license_name}")
    if base_model:
        frontmatter.append(f"base_model: {base_model}")
    if tags:
        frontmatter.append("tags:")
        frontmatter.extend(f"- {tag}" for tag in tags)
    frontmatter.append("---")

    details: list[tuple[str, str]] = [
        ("Published repo", f"`{repo_id}`"),
        ("Original model", f"[{card.original_model}]({card.original_model})"),
        ("GitHub Copilot fix", f"Included `{modelfile_filename}` with Copilot-safe Ollama tool calling"),
        ("Weights", "Unchanged GGUF weights from the original upstream release"),
        ("GGUF file", f"`{gguf_filename}`"),
    ]

    for key in ("model_name", "architecture", "quantization", "context_length"):
        value = card.metadata.get(key)
        if value:
            label = key.replace("_", " ").title()
            details.append((label, value))

    lines = [
        *frontmatter,
        "",
        f"# {card.title}",
        "",
        "This model package is **fixed to work with GitHub Copilot**.",
        "",
        "It republishes the original GGUF together with the Copilot-compatible Ollama configuration from this repository.",
        "",
        "| Field | Value |",
        "| --- | --- |",
    ]
    lines.extend(f"| {label} | {value} |" for label, value in details)

    lines.extend(
        [
            "",
            "## What is included",
            "",
            f"- `{gguf_filename}`",
            f"- `{modelfile_filename}`",
            "- `README.md` with release notes and provenance",
            "",
            "## Use with Ollama",
            "",
            "Download the repository contents locally and run:",
            "",
            "```bash",
            "ollama create my-copilot-model -f Modelfile",
            "```",
            "",
            f"The included `Modelfile` expects `./{gguf_filename}` in the same directory.",
        ]
    )

    if source_repo_url:
        lines.extend(
            [
                "",
                "## Provenance",
                "",
                f"- Generated with [`ollama-copilot-fixer`]({source_repo_url}).",
            ]
        )

    if card.body:
        lines.extend(
            [
                "",
                "## Release Notes",
                "",
                card.body,
            ]
        )

    return "\n".join(lines).strip() + "\n"


def publish_release(
    *,
    repo_id: str,
    gguf_path: Path,
    release_card_path: Path,
    modelfile_path: Path,
    readme_text: str,
    token: str | None = None,
    private: bool = False,
) -> str:
    _enable_fast_hf_transfers()

    try:
        from huggingface_hub import CommitOperationAdd, HfApi  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "huggingface_hub is required for publishing. Install dependencies with: python -m pip install -r requirements.txt"
        ) from exc

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="model", private=private, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ollama-copilot-publish-") as temp_dir:
        readme_path = Path(temp_dir) / "README.md"
        readme_path.write_text(readme_text, encoding="utf-8")

        operations = [
            CommitOperationAdd(path_in_repo=gguf_path.name, path_or_fileobj=str(gguf_path)),
            CommitOperationAdd(path_in_repo="Modelfile", path_or_fileobj=str(modelfile_path)),
            CommitOperationAdd(path_in_repo="README.md", path_or_fileobj=str(readme_path)),
            CommitOperationAdd(
                path_in_repo=f"releases/{release_card_path.name}",
                path_or_fileobj=str(release_card_path),
            ),
        ]

        api.create_commit(
            repo_id=repo_id,
            repo_type="model",
            operations=operations,
            commit_message=f"Publish {gguf_path.name} fixed for GitHub Copilot",
        )

    return f"https://huggingface.co/{repo_id}"
