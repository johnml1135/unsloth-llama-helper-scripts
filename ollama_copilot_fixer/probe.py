from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import console
from .modelfile import generate_modelfile
from .ollama import chat_model, create_model, delete_model

_PROBE_PROMPT = "Reply with exactly: Hello!"
_META_REASONING_PATTERNS = [
    re.compile(r"\bthinking process\b", re.IGNORECASE),
    re.compile(r"\bi need to think\b", re.IGNORECASE),
    re.compile(r"\blet me think\b", re.IGNORECASE),
    re.compile(r"\bthe user wants\b", re.IGNORECASE),
]


@dataclass(frozen=True)
class ProbeCandidate:
    architecture: str
    label: str


@dataclass(frozen=True)
class ProbeOutcome:
    candidate: ProbeCandidate
    accepted: bool
    reason: str
    content_preview: str


def candidates_for_architecture(architecture: str) -> list[ProbeCandidate]:
    if architecture == "qwen35":
        return [
            ProbeCandidate("qwen35", "ollama-qwen-no-think"),
            ProbeCandidate("qwen35_legacy", "legacy-qwen35"),
            ProbeCandidate("qwen", "generic-qwen"),
        ]
    return [ProbeCandidate(architecture, architecture)]


def evaluate_probe_payload(payload: dict[str, Any]) -> tuple[bool, str, str]:
    message = payload.get("message")
    if not isinstance(message, dict):
        return False, "missing message object", ""

    content = message.get("content")
    thinking = message.get("thinking")
    text = content if isinstance(content, str) else ""
    preview = text.strip()

    if preview and "<think>" not in preview.lower() and "</think>" not in preview.lower():
        for pattern in _META_REASONING_PATTERNS:
            if pattern.search(preview):
                return False, "response leaked meta reasoning text", preview[:120]
        return True, "clean final content", preview[:120]
    if isinstance(thinking, str) and thinking.strip():
        return False, "response exposed separate thinking field", preview[:120]
    if "<think>" in text.lower() or "</think>" in text.lower():
        return False, "response leaked visible think tags", preview[:120]
    if not preview:
        return False, "response content was empty", ""
    if re.search(r"/no_think|/think", text, re.IGNORECASE):
        return False, "response echoed think control token", preview[:120]
    return False, "response did not meet clean output requirements", preview[:120]


def probe_template_candidates(
    *,
    model_name: str,
    absolute_model_path: str,
    architecture: str,
    context_length: int | None,
    temperature: float,
    system_message: str | None,
    temp_dir: Path,
) -> tuple[str, list[ProbeOutcome]]:
    outcomes: list[ProbeOutcome] = []

    for index, candidate in enumerate(candidates_for_architecture(architecture), start=1):
        probe_model_name = f"{model_name}-probe-{index}"
        probe_modelfile = temp_dir / f"Modelfile.probe.{index}"
        probe_text = generate_modelfile(
            absolute_model_path=absolute_model_path,
            architecture=candidate.architecture,
            context_length=context_length,
            temperature=temperature,
            system_message=system_message,
        )
        probe_modelfile.write_text(probe_text, encoding="utf-8")

        try:
            create_model(probe_model_name, str(probe_modelfile))
            payload = chat_model(probe_model_name, _PROBE_PROMPT)
            accepted, reason, preview = evaluate_probe_payload(payload)
            outcomes.append(
                ProbeOutcome(
                    candidate=candidate,
                    accepted=accepted,
                    reason=reason,
                    content_preview=preview,
                )
            )
            if accepted:
                console.info(f"Template probe selected: {candidate.label}")
                return candidate.architecture, outcomes
        finally:
            try:
                delete_model(probe_model_name)
            except Exception:
                pass

    return architecture, outcomes
