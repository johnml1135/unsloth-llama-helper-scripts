---
title: Qwen3.6-35B-A3B-UD-IQ4_XS fixed for GitHub Copilot
original_model: https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF
license: apache-2.0
tags:
  - qwen
  - qwen3.6
  - reasoning
  - local-models
model_name: qwen36-35b-a3b-ud-iq4xs-128k
architecture: qwen36
context_length: 131072
quantization: UD-IQ4_XS
---
This package keeps the original Unsloth GGUF weights and adds the Ollama `Modelfile`
needed to make the model work cleanly with GitHub Copilot local model agent flows.

Validated in this repo against:

- clean no-think chat output by default
- structured tool calls for Copilot agent turns
- optional `think=true` reasoning streams on harder prompts

The Copilot-specific fix is in the included `Modelfile` and runtime settings, not in altered model weights.
