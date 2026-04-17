from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from . import console
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


def _format_bytes(n: int) -> str:
    size = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{n} B"


def _link_or_copy(src: Path, dst: Path) -> None:
    """Link src to dst (hardlink where possible) to avoid duplicating large files.

    Falls back to a chunked copy if hardlinks are unsupported (cross-volume,
    ReFS/NTFS oddities, etc.). If dst already exists with the same size as src,
    we leave it alone so that resumed runs don't re-copy multi-GB files.
    """
    if dst.exists():
        try:
            if dst.stat().st_size == src.stat().st_size:
                return
        except OSError:
            pass
        try:
            dst.unlink()
        except OSError:
            pass

    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        os.link(src, dst)
        return
    except (OSError, NotImplementedError, AttributeError):
        pass

    console.info(f"Copying {src.name} into staging directory (hardlink unavailable)...")
    total = src.stat().st_size
    copied = 0
    last_report = time.monotonic()
    with src.open("rb") as fin, dst.open("wb") as fout:
        while True:
            chunk = fin.read(16 * 1024 * 1024)
            if not chunk:
                break
            fout.write(chunk)
            copied += len(chunk)
            now = time.monotonic()
            if now - last_report >= 5.0:
                pct = (copied / total * 100.0) if total else 0.0
                console.info(f"  copy: {_format_bytes(copied)} / {_format_bytes(total)} ({pct:.1f}%)")
                last_report = now


def _staging_dir_for(cache_root: Path, repo_id: str) -> Path:
    safe = repo_id.replace("/", "__")
    return cache_root / "publish" / safe


def _snapshot_state(staging: Path) -> tuple[int, float]:
    """Return (total_bytes_in_hub_cache, newest_mtime) for resumable upload state.

    `upload_large_folder` writes per-chunk progress under <folder>/.cache/huggingface/.
    Tracking byte-count + newest mtime across that tree is a reliable
    "something is still happening" signal for the heartbeat watchdog.
    """
    root = staging / ".cache" / "huggingface"
    if not root.exists():
        return 0, 0.0
    total = 0
    newest = 0.0
    try:
        for p in root.rglob("*"):
            try:
                st = p.stat()
            except OSError:
                continue
            if not p.is_file():
                continue
            total += st.st_size
            if st.st_mtime > newest:
                newest = st.st_mtime
    except OSError:
        pass
    return total, newest


def _heartbeat_loop(
    staging: Path,
    total_upload_bytes: int,
    stop_event: threading.Event,
    *,
    interval_seconds: float = 30.0,
    stuck_warn_seconds: float = 300.0,
) -> None:
    start = time.monotonic()
    last_bytes, last_mtime = _snapshot_state(staging)
    last_change = time.monotonic()

    while not stop_event.wait(interval_seconds):
        cur_bytes, cur_mtime = _snapshot_state(staging)
        now = time.monotonic()
        elapsed = now - start

        changed = cur_bytes != last_bytes or cur_mtime != last_mtime
        if changed:
            last_bytes, last_mtime = cur_bytes, cur_mtime
            last_change = now

        idle = now - last_change
        pct = (cur_bytes / total_upload_bytes * 100.0) if total_upload_bytes else 0.0
        msg = (
            f"[heartbeat] elapsed={int(elapsed)}s  "
            f"state_cache={_format_bytes(cur_bytes)} (~{pct:.1f}% of payload)  "
            f"idle={int(idle)}s"
        )
        if idle >= stuck_warn_seconds:
            console.warn(
                msg
                + f"  - no state change for over {int(stuck_warn_seconds)}s. Upload may be stuck; "
                "huggingface_hub will retry automatically. Press Ctrl-C and re-run to resume."
            )
        else:
            console.info(msg)


def publish_release(
    *,
    repo_id: str,
    gguf_path: Path,
    release_card_path: Path,
    modelfile_path: Path,
    readme_text: str,
    staging_root: Path,
    token: str | None = None,
    private: bool = False,
) -> str:
    """Publish a model repo to Hugging Face using a resumable, chunked upload.

    The staging directory under `staging_root` is persistent so that interrupted
    uploads resume where they left off on the next run.
    """
    _enable_fast_hf_transfers()

    try:
        from huggingface_hub import HfApi  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "huggingface_hub is required for publishing. Install dependencies with: "
            "python -m pip install -r requirements.txt"
        ) from exc

    staging = _staging_dir_for(staging_root, repo_id)
    staging.mkdir(parents=True, exist_ok=True)
    console.info(f"Staging directory: {staging}")

    gguf_staged = staging / gguf_path.name
    _link_or_copy(gguf_path, gguf_staged)

    (staging / "Modelfile").write_text(modelfile_path.read_text(encoding="utf-8"), encoding="utf-8")
    (staging / "README.md").write_text(readme_text, encoding="utf-8")

    releases_dir = staging / "releases"
    releases_dir.mkdir(exist_ok=True)
    staged_card = releases_dir / release_card_path.name
    staged_card.write_text(release_card_path.read_text(encoding="utf-8"), encoding="utf-8")

    total_bytes = 0
    for p in staging.rglob("*"):
        if p.is_file() and ".cache" not in p.parts:
            try:
                total_bytes += p.stat().st_size
            except OSError:
                pass
    console.info(f"Payload size: {_format_bytes(total_bytes)}")

    api = HfApi(token=token)
    console.info(f"Ensuring repo exists: {repo_id}")
    api.create_repo(repo_id=repo_id, repo_type="model", private=private, exist_ok=True)

    console.info(
        "Starting resumable upload via huggingface_hub.upload_large_folder. "
        "For multi-GB GGUFs this typically takes 10-30+ minutes on a home connection."
    )
    console.info(
        "Phase 1 is SHA-256 hashing (CPU-bound, no network traffic yet). "
        "Phase 2 is chunked HTTPS upload in parallel workers."
    )
    console.info(
        "If interrupted (Ctrl-C, network drop, crash), re-run the same command - "
        "already-uploaded chunks are skipped automatically via the .cache/huggingface state."
    )

    stop_event = threading.Event()
    heartbeat = threading.Thread(
        target=_heartbeat_loop,
        args=(staging, total_bytes, stop_event),
        kwargs={"interval_seconds": 30.0, "stuck_warn_seconds": 300.0},
        daemon=True,
        name="publish-heartbeat",
    )
    heartbeat.start()

    try:
        api.upload_large_folder(
            repo_id=repo_id,
            repo_type="model",
            folder_path=str(staging),
            ignore_patterns=[".cache/**", ".cache/*"],
            print_report=True,
            print_report_every=60,
        )
    finally:
        stop_event.set()
        heartbeat.join(timeout=3)

    console.success("Upload complete.")
    return f"https://huggingface.co/{repo_id}"
