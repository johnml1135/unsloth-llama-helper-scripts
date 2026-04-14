from __future__ import annotations

import sys


def _print(prefix: str, message: str, stream) -> None:
    line = f"{prefix} {message}\n"
    try:
        stream.write(line)
    except UnicodeEncodeError:
        fallback_prefix = {
            "ℹ": "[INFO]",
            "✓": "[OK]",
            "⚠": "[WARN]",
            "✗": "[ERROR]",
        }.get(prefix, "[LOG]")
        stream.write(f"{fallback_prefix} {message}\n")


def info(message: str) -> None:
    _print("ℹ", message, sys.stdout)


def success(message: str) -> None:
    _print("✓", message, sys.stdout)


def warn(message: str) -> None:
    _print("⚠", message, sys.stdout)


def error(message: str) -> None:
    _print("✗", message, sys.stderr)
