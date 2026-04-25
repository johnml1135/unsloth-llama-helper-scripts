# Unsloth Llama Helper Scripts

PowerShell helpers for running [Unsloth](https://unsloth.ai/) GGUF models on a
single 24 GB NVIDIA GPU via [llama.cpp](https://github.com/ggml-org/llama.cpp)'s
`llama-server`, exposed as an OpenAI-compatible endpoint for **VS Code GitHub
Copilot Chat (BYOK)**, Cline, OpenCode, Claude Code Router, etc.

No GGUF rebuilding. No Modelfiles. No Ollama. We just call llama-server with the
parameters Unsloth itself recommends.

## Why not Ollama?

Ollama's bundled runner does not register the `qwen35moe` architecture used by
Qwen3.6-35B-A3B
([ollama/ollama#15747](https://github.com/ollama/ollama/issues/15747)) and
Unsloth's own docs state
[*"Currently no Qwen3.6 GGUF works in Ollama due to separate mmproj vision
files. Use llama.cpp compatible backends."*](https://unsloth.ai/docs/models/qwen3.6)

Use the **[GitHub Copilot LLM Gateway](https://marketplace.visualstudio.com/items?itemName=AndrewButson.github-copilot-llm-gateway)**
extension by Andrew Butson to connect Copilot Chat to your local llama-server.
The extension registers your server's models as a first-class provider inside
Copilot Chat, with full agent mode and tool calling support.

> Caveat: This powers **chat + agent** only. Inline ghost-text completions stay
> on GitHub-hosted models regardless of which inference backend you pick.

## Quick start

```powershell
# 1. (first run only) download a prebuilt llama.cpp into tools\llama.cpp\
.\scripts\install-llama.ps1            # CUDA build by default

# 2. pick a model from the menu and start the server in the background
.\scripts\start-server.ps1             # auto-installs llama.cpp if missing

# 3. check it
.\scripts\status-server.ps1

# 4. stop it
.\scripts\stop-server.ps1
```

The server listens on `http://127.0.0.1:8080/v1` (OpenAI-compatible).
First launch downloads the GGUF weights to `models\` (controlled via
`$env:LLAMA_CACHE`).

## Wire VS Code Copilot Chat to it

### 1. Install the GitHub Copilot LLM Gateway extension

Install **[GitHub Copilot LLM Gateway](https://marketplace.visualstudio.com/items?itemName=AndrewButson.github-copilot-llm-gateway)**
(`AndrewButson.github-copilot-llm-gateway`) from the VS Code Marketplace. This
workspace also lists it as a recommended extension — accept the prompt when you
open the folder, or install it from the Extensions view.

### 2. Configure the extension

The extension settings are under `github.copilot.llm-gateway.*`. The workspace
`.vscode/settings.json` already includes the defaults below, but you can
override them in your user settings if needed:

```jsonc
// .vscode/settings.json (already included in this repo)
"github.copilot.llm-gateway.serverUrl": "http://127.0.0.1:8080",
"github.copilot.llm-gateway.apiKey": "",
"github.copilot.llm-gateway.requestTimeout": 60000,
"github.copilot.llm-gateway.defaultMaxTokens": 262144,
"github.copilot.llm-gateway.defaultMaxOutputTokens": 4096,
"github.copilot.llm-gateway.enableToolCalling": true,
"github.copilot.llm-gateway.parallelToolCalling": true,
"github.copilot.llm-gateway.agentTemperature": 0.0
```

> **Important:** Set the `serverUrl` to the **base URL only** — do NOT include
> `/v1` or a trailing slash. The extension appends `/v1/models` itself.

### 3. Start the llama-server

```powershell
./scripts/start-server.ps1
```

Pick a model from the menu. The server listens on `http://127.0.0.1:8080/v1`.

### 4. Verify the connection

Open the Command Palette (`Ctrl+Shift+P`) and run:

- **GitHub Copilot LLM Gateway: Test Server Connection** — confirms connectivity
  and lists discovered models

### 5. Select a model in Copilot Chat

1. Open Copilot Chat (`Ctrl+Alt+I`)
2. Click the **model selector** dropdown at the bottom
3. Click **"Manage Models..."**
4. Select **"LLM Gateway"** as the provider
5. Enable the model(s) you want to use

The extension auto-discovers whatever model is currently loaded on llama-server.
See [the extension docs](https://github.com/arbs-io/github-copilot-llm-gateway)
for more details on tool calling, agent mode, and troubleshooting.

## Curated model catalog (24 GB profiles)

Defined in [scripts/models.ps1](scripts/models.ps1). Quants and contexts are
picked per model so that each fits a single 24 GB GPU with `q8_0` KV. Three of
the four profiles run at 200K context; see **Measured GPU RAM** below for
actual card usage.

| Key               | Model                       | Quant         | Size     | Context (24 GB) | Native max | Notes                                                                                              |
| ----------------- | --------------------------- | ------------- | -------- | --------------- | ---------- | -------------------------------------------------------------------------------------------------- |
| `qwen36-35b-a3b`  | Qwen3.6 35B-A3B (MoE)       | `UD-Q4_K_S`   | ~19.5 GB | **200 000**     | 262 144    | Recommended. MoE → tiny KV. Tight fit — drop to `UD-IQ4_XS` (16.5 GB) for ~3 GiB headroom.        |
| `qwen36-27b`      | Qwen3.6 27B (hybrid)        | `IQ4_XS`      | ~14.4 GB | **200 000**     | 262 144    | 16 of 64 layers full-attn (GQA 24:4), 48 Gated DeltaNet — KV barely grows with ctx.                |
| `gemma4-26b-a4b`  | Gemma 4 26B-A4B (MoE)       | `UD-Q5_K_S`   | ~17.5 GB | **200 000**     | 262 144    | Comfortable fit; multimodal weights downloaded but unused.                                         |
| `gemma4-31b`      | Gemma 4 31B (dense)         | `IQ4_XS`      | ~15.3 GB | **131 072**     | 262 144    | 60 layers, 10 full-attn + 50 sliding-window-1024. No headroom to push past 128K.                   |

### Why these contexts?

KV-cache memory ≈ `full_attn_layers × kv_heads × head_dim × 2 (k+v) ×
bytes_per_elem × ctx_tokens`.

- **Qwen3.6 MoE 35B-A3B** has `kv_heads=2`, so 200K @ q8_0 KV is ~8 GB —
  tight but feasible alongside ~19 GB of weights with `-fa on`.
- **Qwen3.6-27B** is *not* a classic dense model. Only **16 of its 64
  layers** use full attention (GQA 24:4, head_dim 256); the other 48 are
  Gated DeltaNet linear-attention with constant-size state. KV at 200K is
  ~7 GB, leaving room for `IQ4_XS` weights (14.4 GB) on 24 GB.
- **Gemma 4 31B** is dense but uses a 1-in-6 full-attention pattern (10
  global + 50 sliding-window-1024, GQA 32:4 on global layers, head_dim
  512). KV at 128K is ~6 GB. With `IQ4_XS` (15.3 GB) it fits, but there
  is no headroom to push past 128K.
- Per Unsloth, `q4_0` KV breaks Qwen3.x tool calls, so we keep KV at
  `q8_0` and shrink the quant or context as needed.

If you want a different ctx, pass `-ContextOverride 65536` to `start-server.ps1`
or edit [scripts/models.ps1](scripts/models.ps1).

## Sampler defaults

From [Unsloth's Qwen3.6 docs](https://unsloth.ai/docs/models/qwen3.6) and
[Gemma 4 docs](https://unsloth.ai/docs/models/gemma-4):

| Family | temp | top_p | top_k | min_p | presence_penalty | repeat_penalty |
| ------ | ---- | ----- | ----- | ----- | ---------------- | -------------- |
| Qwen3.6 (precise coding, thinking) | 0.6 | 0.95 | 20 | 0.0 | 0.0 | 1.0 |
| Gemma 4 (Google defaults)          | 1.0 | 0.95 | 64 | 0.0 | 0.0 | 1.0 |

Disable thinking with `-NoThink` (passes
`--chat-template-kwargs "{\"enable_thinking\":false}"`).

## Scripts

| Script                          | Purpose                                                              |
| ------------------------------- | -------------------------------------------------------------------- |
| `scripts\install-llama.ps1`     | Download official llama.cpp Windows release (CUDA/Vulkan/CPU).       |
| `scripts\start-server.ps1`      | Interactive menu, auto-installs llama.cpp, launches `llama-server`.  |
| `scripts\status-server.ps1`     | PID, model, /health probe, `nvidia-smi` snapshot.                    |
| `scripts\stop-server.ps1`       | Stop the background server.                                          |
| `scripts\models.ps1`            | Model catalog & sampler defaults (edit to add or tune profiles).     |
| `scripts\benchmark-models.ps1`  | Loads each catalog model, measures VRAM, runs a one-shot inference.  |

## Measured GPU RAM

Measured on **NVIDIA RTX 3090 (24 GiB)** running Windows, with
`--flash-attn on --cache-type-k q8_0 --cache-type-v q8_0 --n-gpu-layers 99`.
Numbers are total card usage from `nvidia-smi --query-gpu=memory.used` after
the model is loaded **and** a one-shot chat-completion has been served.
Baseline (no llama-server) is ~0.5 GiB.

| Key               | Quant        | Context     | GPU RAM        | Free     |
| ----------------- | ------------ | ----------- | -------------- | -------- |
| `qwen36-35b-a3b`  | `UD-Q4_K_S`  | 200 000     | GPU RAM = 23.6 GB | 0.5 GiB |
| `qwen36-27b`      | `IQ4_XS`     | 200 000     | GPU RAM = 23.0 GB | 1.0 GiB |
| `gemma4-26b-a4b`  | `UD-Q5_K_S`  | 200 000     | GPU RAM = 22.4 GB | 1.6 GiB |
| `gemma4-31b`      | `IQ4_XS`     | 131 072     | GPU RAM = 23.0 GB | 1.5 GiB |

Reproduce with:

```powershell
.\scripts\benchmark-models.ps1            # all four
.\scripts\benchmark-models.ps1 -Models qwen36-27b
```

Results are appended to `logs\benchmark-results.json`.

> **Headroom:** `qwen36-35b-a3b` at `UD-Q4_K_S` / 200K leaves only ~0.5 GiB.
> If you also have a desktop compositor or browser using the GPU, drop the
> profile's `HFFile` to `Qwen3.6-35B-A3B-UD-IQ4_XS.gguf` (16.5 GB → ~20.6 GiB
> total VRAM at 200K) for a safe ~3 GiB headroom.

## VS Code tasks
