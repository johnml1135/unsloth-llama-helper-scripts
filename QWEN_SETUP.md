# Qwen Setup Notes

## Recommended path for Unsloth Qwen3.5

Use the CLI in this repo instead of the hand-written Modelfiles.

```bash
python -m ollama_copilot_fixer \
  --model-source "hf.co/unsloth/Qwen3.5-35B-A3B-GGUF:UD-IQ3_S" \
  --model-name "qwen35-35b-a3b-128k" \
  --context-length 131072
```

For extra safety on unknown variants:

```bash
python -m ollama_copilot_fixer \
  --model-source "hf.co/unsloth/Qwen3.5-35B-A3B-GGUF:UD-IQ3_S" \
  --model-name "qwen35-35b-a3b-128k" \
  --context-length 131072 \
  --probe-template
```

This repo now handles Qwen3.5 by:

1. Detecting Qwen3.5 / Qwen3.5-MoE GGUFs
2. Applying an Ollama-style Qwen template
3. Using the default no-think path (`/no_think` + empty `<think></think>` block)
4. Preserving tool-capable prompting for Ollama/Copilot use

## Legacy manual Modelfile examples

`Modelfile.qwen35` and `Modelfile.qwen-256k` are older manual examples for the official Ollama `qwen2.5:32b` model.

They are **not** used by `ollama_copilot_fixer` and should be treated as standalone reference files only.
