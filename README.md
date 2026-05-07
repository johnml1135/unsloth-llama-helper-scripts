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
"github.copilot.llm-gateway.requestTimeout": 600000,
"github.copilot.llm-gateway.defaultMaxTokens": 150000,
"github.copilot.llm-gateway.defaultMaxOutputTokens": 4096,
"github.copilot.llm-gateway.enableToolCalling": true,
"github.copilot.llm-gateway.parallelToolCalling": false,
"github.copilot.llm-gateway.agentTemperature": 0.0
```

> **Important:** Set the `serverUrl` to the **base URL only** — do NOT include
> `/v1` or a trailing slash. The extension appends `/v1/models` itself.

The 150K advertised context leaves roughly 50K tokens of headroom when the
server is running a 200K profile. That reserve matters for Qwen thinking,
generation, and tool-call continuation. Parallel tool calling is disabled by
default because serial calls are slower but more reliable on local Qwen; turn it
back on after your tool calls are stable.

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

## Initialize Copilot for local agents

This repo includes a small Copilot customization bundle for people using a
single 24 GB GPU with a local LLM Gateway model. It installs five skills that
teach Copilot to keep context small, delegate focused research to subagents, and
debug local tool-call failures without stuffing the whole session into Qwen.

Run the initializer and choose whether to install into your **user profile** or
into a **repository**:

```powershell
.\scripts\initialize-copilot-local-agent.ps1
```

Non-interactive examples:

```powershell
# Install skills to ~\.copilot\skills and settings to VS Code User settings
.\scripts\initialize-copilot-local-agent.ps1 -Scope User

# Install skills/settings into another repo
.\scripts\initialize-copilot-local-agent.ps1 -Scope Repo -RepoPath C:\src\my-repo
```

Repo installs write:

- `.github\skills\...`
- `.vscode\settings.json`

User installs write:

- `~\.copilot\skills\...`
- `%APPDATA%\Code\User\settings.json` on Windows

Existing settings files are backed up before being rewritten. Existing skill
folders are skipped unless you pass `-Force`.

Installed skills:

| Skill | Use it for |
| ----- | ---------- |
| `local-context-budget` | Inspecting prompt bloat, context reserve, and token-heavy Copilot sessions. |
| `local-repo-triage` | Finding only the files needed for a coding task before implementation. |
| `local-subagent-delegation` | Using same-model fresh-context subagents for focused research or review. |
| `local-tool-reliability` | Stabilizing Qwen/llama-server/LLM Gateway tool calls. |
| `local-session-handoff` | Compressing a long local-agent session into a fresh-chat checkpoint. |

After installing, restart or reload VS Code if the skills do not immediately
appear in the `/` menu. The skills are intentionally task-specific rather than
always-on instructions, so they do not burn context unless Copilot loads them for
a relevant request.

The skills are now structured for progressive loading instead of carrying their
rationale in the main instruction body. Discovery stays in the frontmatter
`description`, action steps stay in each `SKILL.md`, and the supporting research
lives in per-skill `references/evidence.md` files plus the shared
[.github/skills/REFERENCES.md](.github/skills/REFERENCES.md). This matches the
VS Code skill-loading model: concise procedural bodies, heavier references only
when needed.

Headline numbers that drive the defaults:

- RULER puts Qwen3-30B-A3B's *effective* context at **64K** despite a 128K
  claim — accuracy drops from 96.5 @ 4K to 79.2 @ 128K. The repo's installer
  therefore defaults `defaultMaxTokens` to 150K (well below server max) and the
  skills treat **32K as the high-quality zone** and **64K as a soft ceiling**.
- Anthropic's multi-agent post shows token usage alone explains ~80% of agent
  performance variance, and that multi-agent systems use ~15× more tokens than
  chat — so on a single GPU with no parallelism, subagents are for *context
  isolation*, not speed.
- The Berkeley Function-Calling Leaderboard shows every model degrades with
  more tools (a quantized Llama-3.1-8B failed with 46 tools, succeeded with
  19), which is why `parallelToolCalling` defaults to `false` and the tool
  reliability skill recommends trimming the tool surface before debugging the
  parser.

## Curated model catalog (24 GB profiles)

Defined in [scripts/models.ps1](scripts/models.ps1). Quants and contexts are
picked per model so that each fits a single 24 GB GPU with `q8_0` KV. The Qwen
3.6 27B profile is listed first because it is the safer agentic/tool-use choice;
the remaining profiles are conservative defaults, and profiles 3 and 4 are opt-
in `ngram-mod` speed experiments for repetitive Qwen 27B sessions. See
**Measured GPU RAM** below for actual card usage.

| Key               | Model                       | Quant         | Size     | Context (24 GB) | Native max | Notes                                                                                              |
| ----------------- | --------------------------- | ------------- | -------- | --------------- | ---------- | -------------------------------------------------------------------------------------------------- |
| `qwen36-27b`      | Qwen3.6 27B (dense/hybrid)  | `IQ4_XS`      | ~14.4 GB | **200 000**     | 262 144    | Recommended for agentic coding and tool calls. Uses `q8_0` KV because low-bit KV can break tools.  |
| `qwen36-35b-a3b`  | Qwen3.6 35B-A3B (MoE)       | `UD-Q4_K_S`   | ~19.5 GB | **200 000**     | 262 144    | Fast MoE profile. Tight fit — use `qwen36-27b` first for stricter structured/tool-heavy coding.    |
| `qwen36-27b-ngram-general` | Qwen3.6 27B (ngram speed, general) | `IQ4_XS` | ~14.4 GB | **128 000** | 262 144 | Experimental `ngram-mod` preset adapted from the Reddit speed thread. Higher variance; best for repetitive rewrite/summarize loops, not tool reliability. |
| `qwen36-27b-ngram-coding` | Qwen3.6 27B (ngram speed, coding) | `IQ4_XS` | ~14.4 GB | **128 000** | 262 144 | Experimental coding-speed preset using the corrected Reddit flags and standard Qwen coding sampler. Keeps the stable profile separate. |
| `gemma4-26b-a4b`  | Gemma 4 26B-A4B (MoE)       | `UD-Q5_K_S`   | ~17.5 GB | **200 000**     | 262 144    | Comfortable fit; multimodal weights downloaded but unused.                                         |
| `gemma4-31b`      | Gemma 4 31B (dense)         | `IQ4_XS`      | ~15.3 GB | **131 072**     | 262 144    | 60 layers, 10 full-attn + 50 sliding-window-1024. No headroom to push past 128K.                   |

Profiles `qwen36-27b-ngram-general` and `qwen36-27b-ngram-coding` map to menu
items 5 and 6 in `start-server.ps1`. They use:

```text
--spec-type ngram-mod --spec-ngram-size-n 24 --draft-min 12 --draft-max 48
```

Those settings came from the corrected Reddit follow-up config rather than the
original post text. They are intentionally capped at 128K context on this repo's
24 GB `IQ4_XS` setup, because the original report used a 40 GB machine and a
Q8_0 model.

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

Disable thinking with `-NoThink`. The script merges `enable_thinking: false`
into `LLAMA_CHAT_TEMPLATE_KWARGS` without dropping the Qwen tool-call fixes.

### Qwen3.6 tool calling fixes

Qwen3.6 models can leak reasoning content or fail to close `<thinking>` tags
before outputting tool calls, causing strict XML-style parsing to fail with
"Request failed" errors. That issue is especially noticeable on older builds
and in the 35B-A3B profile; the 27B profile is the safer default for Copilot
agent sessions. For Qwen3.6 profiles, `start-server.ps1` now uses the local
fixed template at [scripts/templates/qwen36-tool-fix.jinja](scripts/templates/qwen36-tool-fix.jinja) and sets:

```powershell
LLAMA_CHAT_TEMPLATE_KWARGS={"preserve_thinking":true,"tool_parser":"qwen3_coder"}
--reasoning-format deepseek
```

That keeps prior reasoning in context for multi-turn tool use, selects the more
forgiving Qwen coder tool parser, and extracts `<think>` content away from normal
assistant text where supported by the installed `llama-server` build. `-NoThink`
only adds `enable_thinking:false`; it keeps `preserve_thinking` and the parser
selection intact.

The scripts also deliberately keep Qwen KV cache at `q8_0` and do not enable
n-gram speculative decoding by default. Community reports show low-bit KV and
ngram speculative decoding can hurt coding/tool-call reliability even when they
improve speed. The new `qwen36-27b-ngram-*` profiles are isolated experiments,
not recommended defaults for Copilot agent sessions.

## Scripts

| Script                          | Purpose                                                              |
| ------------------------------- | -------------------------------------------------------------------- |
| `scripts\install-llama.ps1`     | Download official llama.cpp Windows release (CUDA/Vulkan/CPU).       |
| `scripts\start-server.ps1`      | Interactive menu, auto-installs llama.cpp, launches `llama-server`.  |
| `scripts\status-server.ps1`     | PID, model, /health probe, `nvidia-smi` snapshot.                    |
| `scripts\stop-server.ps1`       | Stop the background server.                                          |
| `scripts\models.ps1`            | Model catalog & sampler defaults (edit to add or tune profiles).     |
| `scripts\benchmark-models.ps1`  | Loads each catalog model, measures VRAM, runs a one-shot inference.  |
| `scripts\inspect-copilot-context.ps1` | Summarize Copilot prompt sizes and llama-server prompt tokens. |
| `scripts\initialize-copilot-local-agent.ps1` | Install minimal-context skills and LLM Gateway settings into a repo or user profile. |

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
