# Ollama Copilot Fixer

A small Python CLI for one narrow job: make a short list of strong local coding models work cleanly with GitHub Copilot on 24 GB-class consumer hardware.

The main focus is Unsloth GGUF releases that already run in Ollama but still need the right template, Modelfile, and runtime defaults to behave correctly in Copilot, especially for tool calling.

## Current Focus

- Qwen3.5 and Qwen3.6 Unsloth GGUFs in Ollama
- Nemotron 3 Nano 30B A3B class local setups
- clean Copilot tool calling
- practical local runs on 24 GB-class machines

This repo is not trying to support every GGUF on Hugging Face. It is intentionally focused on a few local coding models that are worth getting right.

## What The CLI Does

- download a GGUF from Hugging Face or use a local GGUF
- merge sharded GGUFs when needed
- generate a Copilot-safe Ollama Modelfile
- create the model in Ollama
- publish the fixed package back to Hugging Face

## Most Tested Path

The most validated setup in this repo is:

- `unsloth/Qwen3.6-35B-A3B-GGUF:UD-IQ4_XS`
- context length `131072`
- published example: `johnml1135/qwen36-35b-a3b-ud-iq4xs-128k-github-copilot`

For Qwen3.5 and Qwen3.6, the key fix is using an Ollama-style Qwen template and safe no-think defaults so Copilot sees clean responses and structured tool calls instead of raw `<think>` output.

## Requirements

- Python 3.10+
- [Ollama](https://ollama.ai/download) installed and running
- `python -m pip install -r requirements.txt`
- `hf auth login` if you need Hugging Face downloads or publishing
- `llama.cpp` only if you need to merge sharded GGUFs

## Quick Start

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

If you need Hugging Face access:

```bash
hf auth login
```

Create the validated Qwen3.6 model locally:

```bash
python -m ollama_copilot_fixer \
	--model-source "hf.co/unsloth/Qwen3.6-35B-A3B-GGUF:UD-IQ4_XS" \
	--model-name "qwen36-35b-a3b-ud-iq4xs-128k" \
	--context-length 131072 \
	--probe-template
```

Create a Nemotron local model:

```bash
python -m ollama_copilot_fixer \
	--model-source "hf.co/unsloth/Nemotron-3-Nano-30B-A3B-GGUF:Q4_0" \
	--model-name "nemotron-copilot"
```

Use a GGUF that is already on disk:

```bash
python -m ollama_copilot_fixer --model-source "C:\\Models\\model.gguf"
```

## Publish A Fixed Model

The repo also includes a local publish flow that uploads:

- the GGUF
- a Copilot-compatible `Modelfile`
- a generated `README.md`
- the release card from `releases/`

Example:

```bash
python -m ollama_copilot_fixer publish \
	--gguf-path "C:\\path\\to\\Qwen3.6-35B-A3B-UD-IQ4_XS.gguf" \
	--release-card "releases\\qwen36-35b-a3b-ud-iq4xs-128k.md" \
	--context-length 131072
```

Use `releases/_template.md` as the starting point for new release cards.

If a publish is interrupted, rerun the same command. The uploader now stages files in the local cache and resumes chunk uploads automatically.

## Useful Commands

```bash
python -m ollama_copilot_fixer --help
python -m ollama_copilot_fixer cache info
python -m ollama_copilot_fixer cache clear
```

## Notes

- If a model comes as split GGUF shards, install `llama.cpp` and point `--llama-cpp-path` at `llama-gguf-split`.
- For Qwen3.5 and Qwen3.6, `--probe-template` is the safest path when trying a new quant or variant.
- Some Nemotron GGUFs still emit plain-text tool markup through Ollama. When that happens, NVIDIA NIM is often the better runtime.

## Non-Goals

This repo does not retune weights, fix broken GGUF exports, or guarantee every upstream model will become Copilot-safe. It focuses on a small set of practical local coding models and making the Unsloth plus Ollama path work reliably with GitHub Copilot.
