from __future__ import annotations

import json
import subprocess
import urllib.request
from typing import Any


def _run(args: list[str]) -> str:
    proc = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed (exit {proc.returncode}): {' '.join(args)}\n{proc.stdout}")
    return proc.stdout


def create_model(model_name: str, modelfile_path: str) -> str:
    return _run(["ollama", "create", model_name, "-f", modelfile_path])


def delete_model(model_name: str) -> str:
    return _run(["ollama", "rm", model_name])


def list_models() -> str:
    return _run(["ollama", "list"])


def run_model(model_name: str, prompt: str) -> str:
    return _run(["ollama", "run", model_name, prompt])


def chat_model(
    model_name: str,
    message: str,
    *,
    host: str = "http://127.0.0.1:11434",
    think: bool | None = None,
    num_predict: int = 64,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model_name,
        "messages": [{"role": "user", "content": message}],
        "stream": False,
        "options": {"num_predict": num_predict},
    }
    if think is not None:
        payload["think"] = think

    request = urllib.request.Request(
        f"{host.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.loads(response.read().decode("utf-8"))
