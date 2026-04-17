from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from . import console
from .cache import clear_cache, ensure_cache_dirs, format_bytes, get_cache_info
from .config import load_config
from .gguf import detect_architecture, is_sharded_model, merge_sharded_model, shard_files, shards_fingerprint
from .huggingface import hf_download_cached
from .modelfile import generate_modelfile, supported_architectures
from .ollama import create_model, list_models, run_model
from .paths import find_llama_gguf_split
from .probe import probe_template_candidates
from .publish import (
    build_hf_repo_id,
    build_model_readme,
    git_remote_origin_url,
    parse_github_remote,
    parse_release_card,
    publish_release,
)
from .source import parse_model_source


def _sanitize_model_name(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9-_]", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _auto_model_name_from_path(p: Path) -> str:
    base = p.stem.lower()
    base = re.sub(r"[^a-z0-9-_]", "-", base)
    base = re.sub(r"-+", "-", base)
    base = re.sub(r"-\d{5}-of-\d{5}$", "", base)
    base = re.sub(r"-\d{4}-of-\d{4}$", "", base)
    return base.strip("-") or "ollama-model"


def build_setup_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ollama-copilot-fixer",
        description="Download/merge GGUF and create an Ollama model with Tool-capable template for GitHub Copilot.",
    )

    p.add_argument("--config", help="Path to config.json (default: OS config dir or $OLLAMA_COPILOT_FIXER_CONFIG)")
    p.add_argument("--cache-root", help="Override cache root directory (downloads/merged/work live here)")

    p.add_argument(
        "--model-source",
        required=True,
        help=(
            "Local GGUF path OR Hugging Face repo id/URL. Examples: "
            "unsloth/Llama-3.2-3B-Instruct-GGUF, hf.co/unsloth/Nemotron-3-Nano-30B-A3B-GGUF:Q4_0, "
            "or 'ollama run hf.co/owner/repo:Q4_0'"
        ),
    )
    p.add_argument("--model-name", help="Name to register in Ollama (default: derived from GGUF filename).")
    p.add_argument(
        "--architecture",
        default="auto",
        choices=["auto", *supported_architectures()],
        help="Force architecture, or auto-detect.",
    )
    p.add_argument(
        "--context-length",
        type=int,
        default=None,
        help=(
            "Context window (num_ctx). If omitted, do not set num_ctx in the Modelfile "
            "and let Ollama/model defaults apply (Ollama may cap this, e.g. to 256k)."
        ),
    )
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--quantization-type", help="Quant filter for Hugging Face downloads, e.g. Q4_0, Q4_K_M, IQ2_XXS")
    p.add_argument(
        "--llama-cpp-path",
        help="Path to llama.cpp folder or llama-gguf-split.exe (required to merge sharded GGUFs).",
    )
    p.add_argument("--keep-downloads", action="store_true", help="Keep temporary download/merge directory.")
    p.add_argument(
        "--probe-template",
        action="store_true",
        help="Probe candidate templates and select the first one that produces a clean response.",
    )
    p.add_argument(
        "--skip-test",
        action="store_true",
        help="Skip running a quick 'ollama run' smoke test.",
    )

    return p


def build_cache_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ollama-copilot-fixer cache",
        description="Inspect and clear the ollama-copilot-fixer cache.",
    )
    p.add_argument("--config", help="Path to config.json (default: OS config dir or $OLLAMA_COPILOT_FIXER_CONFIG)")
    p.add_argument("--cache-root", help="Override cache root directory")

    sub = p.add_subparsers(dest="cache_cmd", required=True)
    sub.add_parser("info", help="Show cache locations and sizes")
    clear = sub.add_parser("clear", help="Clear cache directories")
    clear.add_argument("--all", action="store_true", help="Clear everything (default)")
    clear.add_argument("--hf", action="store_true", help="Clear Hugging Face cache (managed by this tool)")
    clear.add_argument("--downloads", action="store_true", help="Clear CLI download copies")
    clear.add_argument("--merged", action="store_true", help="Clear merged GGUF outputs")
    clear.add_argument("--work", action="store_true", help="Clear work directories")
    return p


def build_publish_parser() -> argparse.ArgumentParser:
    remote = parse_github_remote(git_remote_origin_url(Path(__file__).resolve().parents[1]))
    default_namespace = os.environ.get("OLLAMA_COPILOT_FIXER_HF_NAMESPACE") or (remote[0] if remote else "")
    default_source_repo_url = os.environ.get("OLLAMA_COPILOT_FIXER_SOURCE_REPO") or (remote[2] if remote else "")

    p = argparse.ArgumentParser(
        prog="ollama-copilot-fixer publish",
        description="Publish a public Hugging Face model repo containing a GGUF, a Copilot-compatible Modelfile, and a model card.",
    )
    p.add_argument("--gguf-path", required=True, help="Path to the local GGUF to publish.")
    p.add_argument(
        "--release-card",
        required=True,
        help="Markdown release card stored in the repo releases/ folder.",
    )
    p.add_argument("--repo-id", help="Full Hugging Face repo id, e.g. your-name/model-name.")
    p.add_argument(
        "--namespace",
        default=default_namespace,
        help="Hugging Face namespace/user. Defaults to OLLAMA_COPILOT_FIXER_HF_NAMESPACE or the current GitHub remote owner.",
    )
    p.add_argument(
        "--repo-name",
        help="Model repo name. Defaults to the release card filename with a -github-copilot suffix.",
    )
    p.add_argument(
        "--architecture",
        default="auto",
        choices=["auto", *supported_architectures()],
        help="Architecture used to generate the published Modelfile.",
    )
    p.add_argument(
        "--context-length",
        type=int,
        default=None,
        help="Context window to bake into the published Modelfile.",
    )
    p.add_argument("--temperature", type=float, default=0.7, help="Temperature written into the published Modelfile.")
    p.add_argument("--modelfile-path", help="Optional existing Modelfile to upload instead of generating one.")
    p.add_argument("--token", help="Optional Hugging Face token. If omitted, use your local hf auth login session.")
    p.add_argument(
        "--source-repo-url",
        default=default_source_repo_url,
        help="GitHub repository URL to reference in the generated README.",
    )
    p.add_argument("--private", action="store_true", help="Create the Hugging Face repo as private. Public is the default.")
    p.add_argument("--dry-run", action="store_true", help="Validate inputs and generate files without uploading anything.")
    return p


def _run_cache(argv: list[str]) -> int:
    args = build_cache_parser().parse_args(argv)
    config = load_config(config_path=args.config, cache_root_override=args.cache_root)
    ensure_cache_dirs(config)

    if args.cache_cmd == "info":
        info = get_cache_info(config)
        console.info(f"Config: {info.cache_root}")
        console.info(f"HF cache: {info.hf_cache_dir} ({format_bytes(info.hf_bytes)})")
        console.info(f"Downloads: {info.downloads_dir} ({format_bytes(info.downloads_bytes)})")
        console.info(f"Merged: {info.merged_dir} ({format_bytes(info.merged_bytes)})")
        console.info(f"Work: {info.work_dir} ({format_bytes(info.work_bytes)})")
        console.success(f"Total: {format_bytes(info.total_bytes)}")
        return 0

    if args.cache_cmd == "clear":
        # If no specific flags given, default to --all.
        any_specific = bool(args.hf or args.downloads or args.merged or args.work)
        clear_all = bool(args.all) or not any_specific
        clear_cache(
            config=config,
            clear_hf=clear_all or bool(args.hf),
            clear_downloads=clear_all or bool(args.downloads),
            clear_merged=clear_all or bool(args.merged),
            clear_work=clear_all or bool(args.work),
        )
        console.success("Cache cleared.")
        return 0

    console.error("Unknown cache command.")
    return 2


def _run_publish(argv: list[str]) -> int:
    args = build_publish_parser().parse_args(argv)

    try:
        gguf_path = Path(args.gguf_path).expanduser().resolve()
        if not gguf_path.exists():
            console.error(f"GGUF path not found: {gguf_path}")
            return 1
        if gguf_path.suffix.lower() != ".gguf":
            console.error(f"Expected a .gguf file: {gguf_path}")
            return 1

        release_card_path = Path(args.release_card).expanduser().resolve()
        if not release_card_path.exists():
            console.error(f"Release card not found: {release_card_path}")
            return 1

        card = parse_release_card(release_card_path)

        if args.repo_id:
            repo_id = args.repo_id.strip()
        else:
            repo_name = args.repo_name or f"{release_card_path.stem}-github-copilot"
            repo_id = build_hf_repo_id(namespace=args.namespace, repo_name=repo_name)

        architecture = args.architecture
        if architecture == "auto":
            console.info("Detecting architecture for published Modelfile...")
            architecture = detect_architecture(str(gguf_path))
        console.success(f"Architecture: {architecture}")

        with tempfile.TemporaryDirectory(prefix="ollama_copilot_publish_") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            if args.modelfile_path:
                modelfile_path = Path(args.modelfile_path).expanduser().resolve()
                if not modelfile_path.exists():
                    console.error(f"Modelfile path not found: {modelfile_path}")
                    return 1
            else:
                modelfile_path = temp_dir / "Modelfile"
                modelfile_text = generate_modelfile(
                    absolute_model_path=f"./{gguf_path.name}",
                    architecture=architecture,
                    context_length=args.context_length,
                    temperature=args.temperature,
                )
                modelfile_path.write_text(modelfile_text, encoding="utf-8")

            readme_text = build_model_readme(
                card=card,
                repo_id=repo_id,
                gguf_filename=gguf_path.name,
                modelfile_filename="Modelfile",
                source_repo_url=args.source_repo_url or None,
            )

            console.info(f"Target Hugging Face repo: {repo_id}")
            console.info("Publishing is public by default." if not args.private else "Publishing as a private repo.")

            if args.dry_run:
                console.success("Dry run complete. README and Modelfile generation succeeded.")
                console.info(f"Validated release card: {release_card_path.name}")
                return 0

            repo_url = publish_release(
                repo_id=repo_id,
                gguf_path=gguf_path,
                release_card_path=release_card_path,
                modelfile_path=modelfile_path,
                readme_text=readme_text,
                token=args.token,
                private=bool(args.private),
            )

        console.success(f"Published model repo: {repo_url}")
        console.success("The release README explicitly states that the package is fixed to work with GitHub Copilot.")
        return 0
    except KeyboardInterrupt:
        console.warn("Cancelled (Ctrl-C).")
        return 130
    except Exception as e:
        console.error(str(e))
        return 1


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0].lower() == "cache":
        return _run_cache(argv[1:])
    if argv and argv[0].lower() == "publish":
        return _run_publish(argv[1:])

    args = build_setup_parser().parse_args(argv)

    config = load_config(config_path=args.config, cache_root_override=args.cache_root)
    ensure_cache_dirs(config)

    if not shutil.which("ollama"):
        console.error("Ollama ('ollama') not found on PATH. Install from https://ollama.ai and ensure it's running.")
        return 1

    parsed = parse_model_source(args.model_source)

    temp_dir = Path(tempfile.mkdtemp(prefix="ollama_copilot_fixer_", dir=str(config.work_dir)))
    console.info(f"Working directory: {temp_dir}")

    try:
        quant = args.quantization_type
        if not quant and parsed.quant_suffix:
            quant = parsed.quant_suffix

        working_gguf: Path

        if parsed.is_hf and parsed.repo_id:
            console.info(f"Hugging Face repo detected: {parsed.repo_id}")
            if quant:
                console.info(f"Quantization filter: {quant}")
            console.info("Downloading GGUF(s) from Hugging Face...")
            gguf_path = hf_download_cached(parsed.repo_id, config, quant)
            working_gguf = Path(gguf_path)
            console.success(f"Downloaded/selected: {working_gguf.name}")
        else:
            if not parsed.local_path:
                console.error("Model source not recognized.")
                return 1
            candidate = Path(parsed.local_path)
            if not candidate.exists():
                console.error(f"Local path not found: {candidate}")
                return 1
            working_gguf = candidate.resolve()
            console.success(f"Using local file: {working_gguf}")

        final_gguf = working_gguf

        console.info("Checking for sharded GGUF...")
        if is_sharded_model(str(working_gguf)):
            console.warn("Sharded model detected; merge required.")
            llama_split = find_llama_gguf_split(args.llama_cpp_path)
            if not llama_split:
                console.error(
                    "llama-gguf-split not found. Install llama.cpp and/or add llama-gguf-split to PATH, "
                    "or pass --llama-cpp-path."
                )
                return 1
            console.info(f"Using llama-gguf-split: {llama_split}")

            shards = shard_files(str(working_gguf))
            fp = shards_fingerprint(shards)
            merged = config.merged_dir / f"merged_{fp}.gguf"
            merged_created = False
            if merged.exists() and merged.stat().st_size > 0:
                console.success(f"Reusing cached merge: {merged.name}")
                final_gguf = merged
            else:
                final_path = merge_sharded_model(str(working_gguf), str(merged), llama_split)
                final_gguf = Path(final_path)
                merged_created = True
            console.success(f"Merged into: {final_gguf.name}")
        else:
            console.success("Single-file model (no merge needed).")

        size_gb = final_gguf.stat().st_size / (1024**3)
        console.success(f"Working with: {final_gguf.name} ({size_gb:.2f} GB)")

        model_name = args.model_name
        if not model_name:
            model_name = _auto_model_name_from_path(final_gguf)
            console.info(f"Auto model name: {model_name}")
        model_name = _sanitize_model_name(model_name)

        arch = args.architecture
        if arch == "auto":
            console.info("Detecting architecture...")
            arch = detect_architecture(str(final_gguf))
        console.success(f"Architecture: {arch}")

        # Nemotron GGUFs frequently leak turn markers / non-standard tool markup.
        # We apply a small set of safe stop tokens and stronger system guidance.
        source_hint = (parsed.repo_id or "") + " " + final_gguf.name
        is_nemotron = "nemotron" in source_hint.lower()
        extra_stop: list[str] = []
        system_message = None

        if args.probe_template:
            console.info("Probing template candidates...")
            selected_arch, probe_outcomes = probe_template_candidates(
                model_name=model_name,
                absolute_model_path=str(final_gguf.resolve()),
                architecture=arch,
                context_length=args.context_length,
                temperature=args.temperature,
                system_message=system_message,
                temp_dir=temp_dir,
            )
            for outcome in probe_outcomes:
                status = "selected" if outcome.accepted else "rejected"
                preview = f" preview={outcome.content_preview!r}" if outcome.content_preview else ""
                console.info(f"Probe {outcome.candidate.label}: {status} ({outcome.reason}){preview}")
            if not any(outcome.accepted for outcome in probe_outcomes):
                console.warn(
                    "No probe candidate produced a clean response; falling back to the detected architecture profile."
                )
            arch = selected_arch
            console.success(f"Using probed architecture/template: {arch}")

        console.info("Generating Modelfile...")
        modelfile_path = temp_dir / "Modelfile"
        if is_nemotron:
            # Note: Nemotron models in Ollama use a dedicated parser/renderer. We avoid
            # applying Llama-style stop tokens here because they can cause empty outputs.
            console.info("Nemotron detected; using Nemotron-compatible Modelfile settings.")

        modelfile_text = generate_modelfile(
            absolute_model_path=str(final_gguf.resolve()),
            architecture=arch,
            context_length=args.context_length,
            temperature=args.temperature,
            extra_stop=extra_stop or None,
            system_message=system_message,
        )
        modelfile_path.write_text(modelfile_text, encoding="utf-8")
        console.success(f"Wrote Modelfile: {modelfile_path}")

        console.info("Creating model in Ollama...")
        create_out = create_model(model_name, str(modelfile_path))
        if create_out.strip():
            console.info(create_out.strip())
        console.success(f"Created model: {model_name}")

        console.info("Verifying with 'ollama list'...")
        lst = list_models()
        if model_name in lst:
            console.success("Model is registered in Ollama.")
        else:
            console.warn("Model name not found in 'ollama list' output (this can be transient).")

        if not args.skip_test:
            console.info("Running a quick smoke test (ollama run)...")
            try:
                out = run_model(model_name, "Hello, can you help me with code?")
                if out.strip():
                    console.success("Model responded successfully.")
            except Exception as e:
                console.warn(f"Smoke test failed: {e}")

        console.success("Setup complete. Your model should show Tool capability in VS Code Copilot.")
        if arch in {"qwen35", "qwen36"}:
            console.info(
                "Applied the Ollama-style Qwen thinking template with default no_think behavior."
            )

        # Cleanup cached merged artifacts if configured.
        try:
            if is_sharded_model(str(working_gguf)) and (not config.keep_merged):
                if 'merged' in locals() and isinstance(merged, Path) and merged.exists():
                    if 'merged_created' in locals() and merged_created:
                        merged.unlink(missing_ok=True)
        except Exception:
            pass

        if args.keep_downloads:
            console.info(f"Kept working directory: {temp_dir}")
        return 0

    except KeyboardInterrupt:
        console.warn("Cancelled (Ctrl-C).")
        return 130
    except Exception as e:
        console.error(str(e))
        return 1

    finally:
        if not args.keep_downloads:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
