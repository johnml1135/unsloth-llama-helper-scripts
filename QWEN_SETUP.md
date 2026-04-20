# Qwen Setup Notes

## Recommended path for Unsloth Qwen3.6

Use the CLI in this repo instead of the hand-written Modelfiles.

```bash
python -m ollama_copilot_fixer \
  --model-source "hf.co/unsloth/Qwen3.6-35B-A3B-GGUF:UD-IQ4_XS" \
  --model-name "qwen36-35b-a3b-ud-iq4xs-128k" \
  --context-length 131072
```

For extra safety on unknown variants:

```bash
python -m ollama_copilot_fixer \
  --model-source "hf.co/unsloth/Qwen3.6-35B-A3B-GGUF:UD-IQ4_XS" \
  --model-name "qwen36-35b-a3b-ud-iq4xs-128k" \
  --context-length 131072 \
  --probe-template
```

## What this repo does for Qwen3.6

1. Detects Qwen3.6 explicitly even though the GGUF architecture still reports `qwen35moe`
2. Applies an Ollama-style Qwen template
3. Uses the default no-think path (`/no_think` + empty `<think></think>` block) for Copilot-safe output
4. **Automatically disables the no-think seed when Copilot sends `tools`** — otherwise the
   pre-closed `</think>` head caused Qwen3.6 to emit a one-line narration and skip the
   `<tool_call>` block, which made the Copilot agent loop stall after a single turn.
5. Preserves tool-capable prompting and `developer` messages for Ollama/Copilot use
6. Allows `think=true` callers to request a separate `thinking` stream on harder prompts
7. **Bakes Unsloth's recommended sampler defaults into the generated Modelfile** (see below)

## Unsloth-recommended sampler defaults (baked in)

For Qwen3.6 (and Qwen3.5) the generated Modelfile now emits Unsloth's
"thinking-mode, precise coding" profile, which is the closest match to GitHub
Copilot's agentic coding workflow:

| Parameter        | Value | Notes                                                |
| ---------------- | ----- | ---------------------------------------------------- |
| `temperature`    | 0.6   | Lowered from previous default (0.7) for coding tasks |
| `top_p`          | 0.95  |                                                      |
| `top_k`          | 20    |                                                      |
| `min_p`          | 0.0   |                                                      |
| `repeat_penalty` | 1.0   | Off (Unsloth recommends 0.0–2.0 only if needed)      |

Source: <https://unsloth.ai/docs/models/qwen3.6> → *Recommended Settings →
Thinking mode → Precise coding tasks*.

`--temperature` on the CLI still overrides the architecture default if you want
to experiment. The other parameters can be tuned at runtime via Ollama's
`/set parameter ...` command without rebuilding the model.

## Context length guidance

- Maximum native context for Qwen3.6-35B-A3B: **262,144** tokens
  (extendable to 1M via YaRN, not enabled here by default)
- Adequate output length per Unsloth: ~32,768 tokens
- The example commands above use 131,072 (128K) which is a good balance for
  Copilot workloads on consumer GPUs

If you see gibberish, raise the context length first or pin the KV cache to
`bf16` at the llama.cpp / Ollama runtime layer.

## Caveats

- Unsloth notes that some Qwen3.6 GGUF builds ship a separate `mmproj` vision
  file that stock Ollama does not load. This repo targets the **text-only**
  agentic coding path; vision input is not configured.
- Do **not** run on CUDA 13.2 — Unsloth reports gibberish outputs there.

## Tested Qwen3.6 result

- Source: `unsloth/Qwen3.6-35B-A3B-GGUF:UD-IQ4_XS`
- Created model: `qwen36-35b-a3b-ud-iq4xs-128k`
- Default path: clean no-think output
- Think-enabled path: separate `message.thinking` is available for harder
  prompts through Ollama's API

## Legacy manual Modelfile examples

`Modelfile.qwen35` and `Modelfile.qwen-256k` are older manual examples for the
official Ollama `qwen2.5:32b` model. They are **not** used by
`ollama_copilot_fixer` and should be treated as standalone reference files only.
# Qwen Setup Notes

## Recommended path for Unsloth Qwen3.6

Use the CLI in this repo instead of the hand-written Modelfiles.

```bash
python -m ollama_copilot_fixer \
  --model-source "hf.co/unsloth/Qwen3.6-35B-A3B-GGUF:UD-IQ4_XS" \
  --model-name "qwen36-35b-a3b-ud-iq4xs-128k" \
  --context-length 131072
```

For extra safety on unknown variants:

```bash
python -m ollama_copilot_fixer \
  --model-source "hf.co/unsloth/Qwen3.6-35B-A3B-GGUF:UD-IQ4_XS" \
  --model-name "qwen36-35b-a3b-ud-iq4xs-128k" \
  --context-length 131072 \
  --probe-template
```

This repo now handles Qwen3.6 by:

1. Detecting Qwen3.6 explicitly even though the GGUF architecture still reports `qwen35moe`
2. Applying an Ollama-style Qwen template
3. Using the default no-think path (`/no_think` + empty `<think></think>` block) for Copilot-safe output
4. **Automatically disabling the no-think seed when Copilot sends `tools`** — otherwise the
   pre-closed `</think>` head caused Qwen3.6 to emit a one-line narration and skip the
   `<tool_call>` block, which made the Copilot agent loop stall after a single turn.
4. Preserving tool-capable prompting and `developer` messages for Ollama/Copilot use
5. Allowing `think=true` callers to request a separate `thinking` stream on harder prompts

## Tested Qwen3.6 result

- Source: `unsloth/Qwen3.6-35B-A3B-GGUF:UD-IQ4_XS`
- Created model: `qwen36-35b-a3b-ud-iq4xs-128k`
- Default path: clean no-think output
- Think-enabled path: separate `message.thinking` is available for harder prompts through Ollama's API

## Legacy manual Modelfile examples

`Modelfile.qwen35` and `Modelfile.qwen-256k` are older manual examples for the official Ollama `qwen2.5:32b` model.

They are **not** used by `ollama_copilot_fixer` and should be treated as standalone reference files only.
