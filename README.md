# Ollama Copilot Fixer 🔧🤖

**Fix and enable custom GGUF models (including sharded files) from HuggingFace/Unsloth for GitHub Copilot with full Tool support**

GitHub Copilot's local model integration requires the **"Tool"** capability to function properly. This repo provides a **Python CLI** that:

1. ✅ **Downloads GGUFs from Hugging Face**
2. ✅ **Detects + merges sharded GGUFs** (via `llama-gguf-split`)
3. ✅ **Generates an Ollama Modelfile** with tool-capable chat templates
4. ✅ **Runs `ollama create`** so the model is usable by Copilot

---

## 🎯 Problems This Solves

### Problem 1: Sharded GGUF Files
Large models on HuggingFace are often split into multiple files (`model-00001-of-00005.gguf`, etc.). Ollama cannot load these directly—they must be merged first.

### Problem 2: Missing Tool Capability
Custom GGUF imports to Ollama only show "Inference" capability by default. GitHub Copilot requires "Tool" capability to function. 

### Problem 3: Manual Downloads
Downloading models from HuggingFace and configuring them manually is tedious and error-prone.

**This script fixes all three issues automatically.** 🚀

---

## ✨ Features

- 🔗 **Download from HuggingFace** - Provide a repo URL or ID
- 📁 **Local file support** - Use GGUF files already on disk
- 🧩 **Auto-merge sharded files** - Detects and combines split models
- 🔍 **Auto-detect architecture** (Llama 3, Mistral, Phi-3, Gemma 2, Nemotron)
- 🛠️ **Apply tool templates** automatically
- ✅ **Validate and test** models after setup
- 🎨 **Color-coded output** for easy troubleshooting
- 🧹 **Automatic cleanup** of temporary files

---

## 📋 Prerequisites

- **Python 3.10+**
- **[Ollama](https://ollama.ai/download)** installed and running (`ollama serve`)
- **[llama.cpp](https://github.com/ggml-org/llama.cpp/releases)** (only needed for merging sharded GGUFs)
- **Python deps**: `python -m pip install -r requirements.txt`
- **Hugging Face CLI** (optional fallback for HF downloads): `python -m pip install -U huggingface_hub`
- **VS Code** with GitHub Copilot extension

---

## 🚀 Quick Start

### 1) (Optional) Install Hugging Face CLI

```bash
python -m pip install -r requirements.txt
```

If the repo is gated/private, authenticate first:

```bash
hf auth login
```

### 2) Run the tool

The CLI is runnable directly from the repo:

```bash
python -m ollama_copilot_fixer --help
```

### Usage Examples

#### 1. Download from Hugging Face

```bash
python -m ollama_copilot_fixer \
	--model-source "unsloth/Llama-3.2-3B-Instruct-GGUF" \
	--model-name "llama3-copilot"
```

#### 1b. Download using Ollama-style HF syntax (recommended)

```bash
python -m ollama_copilot_fixer \
	--model-source "hf.co/unsloth/Nemotron-3-Nano-30B-A3B-GGUF:Q4_0" \
	--model-name "nemotron-copilot"
```

Notes:
- `hf.co/<owner>/<repo>` is treated as the Hugging Face repo id.
- The `:<QUANT>` suffix is treated like `--quantization-type` (e.g. `Q4_0`, `Q4_K_M`, `IQ2_XXS`).

#### 2. Use a local GGUF file

```bash
python -m ollama_copilot_fixer --model-source "C:\\Models\\nemotron-nano-Q4_K_M.gguf"
```

#### 3. Merge sharded files and configure

Provide the **first shard** and a path to `llama-gguf-split`:

```bash
python -m ollama_copilot_fixer \
	--model-source "C:\\Models\\llama-405b-00001-of-00008.gguf" \
	--llama-cpp-path "C:\\llama.cpp\\bin" \
	--model-name "llama-405b"
```

#### 4. Download a specific quant

```bash
python -m ollama_copilot_fixer \
	--model-source "bartowski/Llama-3.3-70B-Instruct-GGUF" \
	--quantization-type "Q4_K_M"
```

#### 5. Works with Unsloth Dynamic 2.0 quants

```bash
python -m ollama_copilot_fixer --model-source "hf.co/unsloth/<MODEL-REPO>:IQ2_XXS"
```

#### 6. Probe candidate templates before creating the final model

```bash
python -m ollama_copilot_fixer \
  --model-source "hf.co/unsloth/Qwen3.6-35B-A3B-GGUF:UD-IQ4_XS" \
  --model-name "qwen36-35b-a3b-ud-iq4xs-128k" \
  --context-length 131072 \
  --probe-template
```

This creates temporary probe models, tests candidate templates, and picks the first one that returns a clean response.

---

## 📖 CLI Options

Run `python -m ollama_copilot_fixer --help` for the full list.

Common options:

| Option | Required | Default | Description |
|---|---:|---:|---|
| `--model-source` | ✅ Yes | - | Local path, HF repo id/URL, or `hf.co/<owner>/<repo>:<QUANT>` |
| `--model-name` | ❌ No | Derived | Name to register in Ollama |
| `--architecture` | ❌ No | `auto` | `nemotron`, `llama3`, `mistral`, `phi3`, `gemma2`, `qwen`, `qwen35`, `qwen36`, or `auto` |
| `--context-length` | ❌ No | (auto) | Context window (`num_ctx`). If omitted, this tool will not set `num_ctx` in the Modelfile and Ollama/model defaults apply (Ollama may cap the maximum, e.g. 256k). |
| `--temperature` | ❌ No | `0.7` | Default sampling temperature |
| `--quantization-type` | ❌ No | - | Quant filter for HF downloads |
| `--llama-cpp-path` | ❌ No | - | Path to llama.cpp folder or `llama-gguf-split.exe` |
| `--keep-downloads` | ❌ No | off | Keep temp working directory |
| `--probe-template` | ❌ No | off | Probe candidate templates and select the first clean one |
| `--skip-test` | ❌ No | off | Skip `ollama run` smoke test |

Tip: if you want to explicitly request a large context window (subject to Ollama limits), pass it directly:

```bash
python -m ollama_copilot_fixer \
	--model-source "hf.co/unsloth/Nemotron-3-Nano-30B-A3B-GGUF:Q4_0" \
	--model-name "nemotron-copilot" \
	--context-length 262144
```

### Caching + config

This tool now uses an app-managed cache directory (downloads, HF cache, merged GGUFs) to reduce repeated downloads and merges.

- Default config path:
	- Windows: `%APPDATA%\ollama-copilot-fixer\config.json`
	- Linux: `$XDG_CONFIG_HOME/ollama-copilot-fixer/config.json` (or `~/.config/...`)
- Default cache root:
	- Windows: `%LOCALAPPDATA%\ollama-copilot-fixer\cache`
	- Linux: `$XDG_CACHE_HOME/ollama-copilot-fixer` (or `~/.cache/...`)

Override config and cache locations:

```bash
python -m ollama_copilot_fixer --config "C:\path\to\config.json" --cache-root "D:\LLMCache"
```

An example config is provided in [config.example.json](config.example.json).

Cache commands:

```bash
python -m ollama_copilot_fixer cache info
python -m ollama_copilot_fixer cache clear
```

---

## 🏗️ Supported Architectures

- ✅ **Llama 3 / 3.1 / 3.2 / 3.3** (including Nemotron variants)
- ✅ **Mistral / Mixtral**
- ✅ **Phi-3 / Phi-4**
- ✅ **Gemma 2**
- ✅ **Qwen 2 / 2.5**
- ✅ **Qwen 3.5** (including Unsloth GGUFs)
- ✅ **Qwen 3.6** (including Unsloth GGUFs)

---

## 🔧 How It Works

### For Local Files
1. Detects if file is part of a sharded set
2. Merges shards using llama.cpp's `llama-gguf-split` tool
3. Applies architecture-specific tool template
4. Creates model in Ollama with Tool capability

### For HuggingFace URLs:
1. Downloads model using HuggingFace CLI
2. Auto-selects specified quantization or first GGUF found
3. Handles sharded downloads automatically
4. Proceeds with merge and configuration

## ✅ Qwen3.5 / Qwen3.6 on Ollama: What Actually Works

For Unsloth Qwen3.5 and Qwen3.6 GGUFs, the reliable path is to use an **Ollama-style Qwen thinking template** rather than a plain ChatML/Qwen2 template.

This repo now applies that behavior automatically for `qwen35` and `qwen36` models by:

1. Detecting Qwen3.5 / Qwen3.6 GGUFs explicitly, even when the GGUF architecture still reports `qwen35moe`
2. Using an Ollama-style Qwen template for tool calling
3. Defaulting the last user turn to `/no_think`
4. Seeding an empty `<think></think>` block before the assistant response
5. Preserving `developer` messages for OpenAI-compatible clients such as Copilot
6. Allowing `think=true` callers to switch back to `/think` and receive a separate `thinking` channel when the model decides to reason

That combination matches the behavior Ollama's official `qwen3` models use when reasoning is disabled, and it prevents raw `<think>` output for tested Unsloth Qwen3.5 and Qwen3.6 models.

Validated in this repo:

- `unsloth/Qwen3.6-35B-A3B-GGUF:UD-IQ4_XS`
- model name: `qwen36-35b-a3b-ud-iq4xs-128k`
- context length: `131072`
- direct Ollama chat output is clean by default
- `think=true` can produce a separate `message.thinking` stream on harder prompts

If you want extra safety for unknown variants, enable `--probe-template` to test multiple candidate templates before the final model is created.

---

## ✅ Recommended Fix for Nemotron Tool Calling: NVIDIA NIM

Some Nemotron GGUF builds (notably `Nemotron-3-Nano`) can emit tool calls as **plain text** (for example, XML-ish blocks like `<function=read_file>...`) when run via Ollama. GitHub Copilot expects **OpenAI-style structured tool calls** (`tool_calls`), so it may render that markup verbatim instead of executing tools.

NVIDIA NIM provides an OpenAI-compatible `/v1` API and supports tool calling for **Nemotron 3 Nano**.

### If you are using an LLM-specific NIM container (recommended)

Tool calling is enabled automatically for supported models (Nemotron 3 Nano is listed as supported), and NVIDIA’s docs explicitly recommend **not** setting tool-calling environment variables externally for LLM-specific NIM containers.

Configure Copilot to point at the NIM endpoint:
- Base URL: `http://localhost:8000/v1`

### If you are using a generic LLM NIM deployment

Enable tool calling and select a post-processor:

```bash
NIM_ENABLE_AUTO_TOOL_CHOICE=1
NIM_TOOL_CALL_PARSER=pythonic
```

If the chat response contains an empty `tool_calls` field but the function call appears in `content`, the parser/template combination is mismatched. Per NVIDIA’s guidance, fix this by switching parsers (options include `mistral`, `llama3_json`, `granite`, `hermes`, `jamba`) and/or overriding the chat template via `NIM_CHAT_TEMPLATE`.

---

---

## 📊 Example Output

```
╔════════════════════════════════════════════════════════════╗
║          Ollama Copilot Fixer - Model Setup Tool           ║
╚════════════════════════════════════════════════════════════╝

ℹ Step 1: Checking dependencies... 
✓ Ollama is installed
✓ llama.cpp found at C:\llama.cpp\bin
✓ HuggingFace CLI is installed

ℹ Step 2: Processing model source... 
ℹ Detected HuggingFace repository:  unsloth/Llama-3.2-3B-Instruct-GGUF
ℹ Downloading model files... 
✓ Downloaded:  Llama-3.2-3B-Instruct-Q4_K_M.gguf (2.1 GB)

ℹ Step 3: Checking for sharded files... 
✓ Model is a single file (no merging needed)

ℹ Step 4: Determining model architecture...
✓ Using architecture: llama3

ℹ Step 5: Generating Modelfile with Tool capability...
✓ Modelfile generated with tool support

ℹ Step 6: Creating model in Ollama...
✓ Model created successfully:  llama3-copilot

ℹ Step 7: Testing model...
✓ Model responded successfully

╔════════════════════════════════════════════════════════════╗
║                    SETUP COMPLETE!                          ║
╚════════════════════════════════════════════════════════════╝

Your model is ready for use with GitHub Copilot!  🎉
```

---

## 🤔 Troubleshooting

### Sharded file merging fails

**Error:** "gguf-split not found" or merge errors

**Solutions:**
1. Install llama.cpp from [releases](https://github.com/ggml-org/llama.cpp/releases)
2. Specify the path to `llama-gguf-split` manually: `--llama-cpp-path "C:\\path\\to\\llama.cpp\\bin"`
3. Ensure all shard files are in the same directory
4. Verify files downloaded completely (check file sizes)

### Hugging Face download issues

**Error:** `hf` not found

```bash
python -m pip install -U huggingface_hub
```

**Error:** no GGUFs found after download

- The repo may be gated: run `hf auth login`.
- Your quant filter may be too strict: omit `--quantization-type` and try again.

### Model not appearing in Copilot

1. Restart VS Code completely
2. Verify `ollama list` shows the model
3. Check `ollama show MODEL_NAME --modelfile`
4. Ensure Ollama is running: `ollama serve`

### Copilot shows `<function=...>` or other tool markup

This usually means the model is outputting tool calls as plain text, not as structured `tool_calls`.

- For Nemotron models, prefer running them via NVIDIA NIM (see the section above).
- For Qwen3.5 / Qwen3.6 GGUF imports, use the built-in Ollama-style Qwen template path in this repo and optionally `--probe-template`.

### Visible `<think>` blocks or reasoning text in API output

For Unsloth Qwen3.5 / Qwen3.6 GGUFs, this repo now uses the Ollama-style no-think path by default. If a specific variant still leaks visible reasoning, rerun setup with `--probe-template` so the repo can test candidate templates before creating the final model.

If you want a visible reasoning stream instead, call Ollama with `think=true`. For the tested Qwen3.6 model, harder prompts can return reasoning in `message.thinking` / streaming `thinking` chunks while keeping the final answer in `message.content`.

### Out of Disk Space

For large models (70B+), ensure you have:
- 2x model size for sharded files during merge
- Use the default cleanup behavior (omit `--keep-downloads`) to remove temporary downloads/merges

---

## 🎓 Technical Background

### Why Sharded Files Exist
Models over ~50GB are often split by HuggingFace due to:
- Git LFS file size limits
- Easier parallel downloads
- Repository storage constraints

### Why Tool Capability Matters
GitHub Copilot uses "tool calling" (function calling) to:
- Execute code completions
- Access context from your workspace
- Invoke language model APIs properly

The tool template tells Ollama how to format these special requests.

### Merging Process
The `gguf-split` utility from llama.cpp:
1. Reads shard metadata from first file
2. Concatenates tensor data in correct order
3. Rebuilds GGUF header with full model info
4. Outputs single monolithic file

---

## 📚 Resources

- [Ollama Documentation](https://github.com/ollama/ollama/blob/main/docs/README.md)
- [llama.cpp GGUF Split Guide](https://github.com/ggml-org/llama.cpp/discussions/6404)
- [HuggingFace CLI Documentation](https://huggingface.co/docs/huggingface_hub/main/en/guides/cli)
- [GitHub Copilot Local Models](https://code.visualstudio.com/docs/copilot/copilot-customization)
- [Ollama Multi-file GGUF Issue](https://github.com/ollama/ollama/issues/5245)
- [NVIDIA NIM Function (Tool) Calling](https://docs.nvidia.com/nim/large-language-models/1.15.0/function-calling.html)

---

## 🧩 What This Repo Can Fix vs. What It Cannot

### The scripts can fix

- Downloading the right GGUF from Hugging Face
- Ignoring helper GGUFs like `mmproj`, `imatrix`, `clip`, or other non-weight artifacts
- Merging sharded GGUFs into a single file
- Detecting architecture and generating an architecture-appropriate Modelfile
- Setting context length and runtime defaults in Ollama
- Selecting the correct Ollama-style Qwen no-think template for Qwen3.5 models
- Probing multiple candidate templates before final model creation

### The scripts cannot fully fix on their own

- Broken or incompatible GGUF tensor data
- Missing projector/vision components that the runtime truly requires
- Upstream Ollama bugs in JSON formatting, token accounting, or model-specific runtime behavior
- Model behaviors that require actual GGUF reconstruction, requantization, or upstream template fixes

In short: this repo can solve many integration/runtime issues with scripts and Modelfiles. It cannot rewrite model weights or guarantee that a fundamentally broken GGUF becomes correct without upstream conversion or re-export.

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional architecture support
- Better error recovery
- Cross-platform support (Linux/macOS)
- GUI wrapper

Please open an issue or pull request! 

---

## 📝 License

MIT License - free to use, modify, and distribute. 

---

## 🙏 Acknowledgments

- **Ollama team** - Excellent local LLM runtime
- **llama.cpp** - GGUF tools and quantization
- **Unsloth** - Optimized model quantizations
- **HuggingFace** - Model hosting and distribution
- **GitHub** - Copilot's local model support

---

**Made with ❤️ for the local AI community**

**Problems fixed:  3 | Stars deserved:  ⭐⭐⭐**
