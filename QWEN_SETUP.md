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
