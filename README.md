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
"github.copilot.llm-gateway.defaultMaxTokens": 64000,
"github.copilot.llm-gateway.defaultMaxOutputTokens": 4096,
"github.copilot.llm-gateway.enableToolCalling": true,
"github.copilot.llm-gateway.parallelToolCalling": false,
"github.copilot.llm-gateway.agentTemperature": 0.0
```

> **Important:** Set the `serverUrl` to the **base URL only** — do NOT include
> `/v1` or a trailing slash. The extension appends `/v1/models` itself.

On this 24 GB Qwen setup, keep the advertised Copilot context inside the
effective local budget rather than the model's theoretical max. The repo now
defaults Copilot to **64K** tokens, which matches the soft ceiling used by the
local context-budget skill and leaves reserve for generation and follow-up tool
turns. Parallel tool calling is disabled by default because serial calls are
slower but more reliable on local Qwen; turn it back on after your tool calls
are stable.

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
  therefore defaults `defaultMaxTokens` to **64000**, while the skills treat
  **32K as the high-quality zone** and **64K as a soft ceiling**.
- Anthropic's multi-agent post shows token usage alone explains ~80% of agent
  performance variance, and that multi-agent systems use ~15× more tokens than
  chat — so on a single GPU with no parallelism, subagents are for *context
  isolation*, not speed.
- The Berkeley Function-Calling Leaderboard shows every model degrades with
  more tools (a quantized Llama-3.1-8B failed with 46 tools, succeeded with
  19), which is why `parallelToolCalling` defaults to `false` and the tool
  reliability skill recommends trimming the tool surface before debugging the
  parser.

## Curated Qwen3.6 27B profiles (24 GB)

Defined in [scripts/models.ps1](scripts/models.ps1). The actively tuned Qwen
profiles now target **Qwen3.6 27B only**. The safe 200K profiles keep `q8_0` KV
for the most conservative tool-call reliability; the max-context and
higher-weight profiles use `q4_1` KV because `q8_0` failed above the 200K range
on this RTX 3090, while `q4_1` held the native 262,144-token window with all
layers on GPU.

For better weights, the catalog prefers Unsloth's Dynamic `UD-Q4_K_XL` over
plain `Q4_K_M`: Qwen3.6's own Unsloth examples use `UD-Q4_K_XL`, and the
Dynamic 2.0 docs position those builds as layer-aware quants designed to stay
closer to full precision. A non-MTP `Q5_K_S` profile is also included for runs
where quality matters more than native-max context.

All Qwen 27B profiles pass `--no-mmproj`. The Unsloth GGUF repos include a
vision projector, but Copilot/Cline/OpenCode coding chat does not need it and it
costs VRAM during load.

| Key | Model | Quant | KV | Context (24 GB) | Speculative | Notes |
| --- | ----- | ----- | -- | --------------- | ----------- | ----- |
| `qwen36-27b` | Qwen3.6 27B | `IQ4_XS` | `q8_0` | **200 000** | none | Safest non-MTP agent profile. |
| `qwen36-27b-quality-max` | Qwen3.6 27B | `UD-Q4_K_XL` | `q4_1` | **262 144** | none | Higher-quality Dynamic Q4 weights at native max context. |
| `qwen36-27b-q5` | Qwen3.6 27B | `Q5_K_S` | `q4_1` | **200 000** | none | Highest-weight curated non-MTP profile; less context headroom. |
| `qwen36-27b-max` | Qwen3.6 27B | `IQ4_XS` | `q4_1` | **262 144** | none | Native max context; use when context matters more than conservative KV. |
| `qwen36-27b-mtp` | Qwen3.6 27B MTP | `IQ4_XS + MTP` | `q8_0` | **200 000** | `draft-mtp`, draft max 2 | Fast MTP profile with q8 KV; tight but verified. |
| `qwen36-27b-mtp-quality` | Qwen3.6 27B MTP | `UD-Q4_K_XL + MTP` | `q4_1` | **200 000** | `draft-mtp`, draft max 2 | Better MTP weights; native-max context stays on the lighter MTP profile. |
| `qwen36-27b-mtp-max` | Qwen3.6 27B MTP | `IQ4_XS + MTP` | `q4_1` | **262 144** | `draft-mtp`, draft max 2 | Fast native-max profile; currently the best fit for long local agent sessions. |

The older 35B/Gemma catalog entries remain available in `scripts/models.ps1`,
but they are not the tuning target for this setup.

Exact Hugging Face file sizes checked for the 27B candidates:

| Quant | Non-MTP GGUF | MTP GGUF | Delta vs `IQ4_XS` | Catalog decision |
| ----- | ------------ | -------- | ----------------- | ---------------- |
| `IQ4_XS` | 14.38 GiB | 14.63 GiB | baseline | Safe/default and native-max long-context profiles. |
| `Q4_K_M` | 15.66 GiB | 15.93 GiB | +1.28 GiB / +1.30 GiB | Likely fits, but skipped because `UD-Q4_K_XL` is the better Q4-quality target. |
| `UD-Q4_K_XL` | 16.40 GiB | 16.68 GiB | +2.02 GiB / +2.05 GiB | Curated Dynamic Q4 quality profile for both non-MTP and MTP. |
| `Q5_K_S` | 17.66 GiB | 17.95 GiB | +3.28 GiB / +3.32 GiB | Curated only for non-MTP 200K; MTP would be too tight for comfort. |
| `Q5_K_M` | 18.17 GiB | 18.47 GiB | +3.79 GiB / +3.84 GiB | Too tight for the curated 24 GB set once KV/cache reserve is included. |
| `UD-Q5_K_XL` | 18.66 GiB | 18.95 GiB | +4.28 GiB / +4.32 GiB | Not selected for 24 GB; expected to leave little or no reliable headroom. |

The experimental `qwen36-27b-ngram-*` profiles are still isolated speed
experiments, not recommended defaults for agent sessions. On current llama.cpp
builds they use:

```text
--spec-type ngram-mod --spec-ngram-mod-n-match 24 --spec-ngram-mod-n-min 12 --spec-ngram-mod-n-max 48
```

### Why these contexts?

KV-cache memory ≈ `full_attn_layers × kv_heads × head_dim × 2 (k+v) ×
bytes_per_elem × ctx_tokens`.

- **Qwen3.6-27B** is *not* a classic dense model. Only **16 of its 64
  layers** use full attention (GQA 24:4, head_dim 256); the other 48 are
  Gated DeltaNet linear-attention with constant-size state. KV at 200K is
  ~7 GB, leaving room for `IQ4_XS` weights (14.4 GB) on 24 GB.
- **Qwen3.6-27B MTP** adds a small draft context. At native max context the
  verified load has 5.00 GiB primary KV plus 320 MiB draft KV with `q4_1`.
- Avoid `q4_0` KV for Qwen. For max context, `q4_1` is the compromise used
  here; for conservative reliability, use the 200K `q8_0` profiles.

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
"Request failed" errors. VS Code Copilot Chat also does not reliably resend
Qwen `reasoning_content` across tool turns, which makes long-horizon tool use
degrade even after the template fix. That issue is especially noticeable on
older builds and in the 35B-A3B profile; the 27B profile is the safer default
for Copilot agent sessions. For Qwen3.6 profiles, `start-server.ps1` now uses
the local fixed template at [scripts/templates/qwen36-tool-fix.jinja](scripts/templates/qwen36-tool-fix.jinja) and defaults to:

```powershell
LLAMA_CHAT_TEMPLATE_KWARGS={"tool_parser":"qwen3_coder","enable_thinking":false}
--reasoning off
```

That uses the patched multi-turn Qwen template, selects the more forgiving Qwen
coder tool parser, and avoids the Copilot reasoning-trace gap by keeping Qwen
reasoning off by default. If your client does preserve reasoning traces, use
`-EnableReasoning`; that switches Qwen back to:

```powershell
LLAMA_CHAT_TEMPLATE_KWARGS={"tool_parser":"qwen3_coder"}
--reasoning on
--reasoning-format deepseek
```

`-NoThink` still disables reasoning for non-Qwen families too.

When Qwen still fails after a follow-up tool call, capture the boundary between
Copilot and `llama-server` instead of guessing which side dropped the tool call:

```powershell
# Terminal 1: keep llama-server on 8080
.\scripts\start-server.ps1 -Model qwen36-27b

# Terminal 2: proxy Copilot traffic through 8090 and log raw request/response JSON
node .\scripts\trace-openai-proxy.js --listen 8090 --target http://127.0.0.1:8080

# Point Copilot's custom model URL at http://127.0.0.1:8090/v1, reproduce once,
# then summarize what the server actually returned.
.\scripts\analyze-openai-trace.ps1
```

If the analyzer reports `server-returned-structured-tool-calls` for the failing
second turn, `llama-server` did its job and the remaining bug is in the Copilot
or gateway agent loop. If it reports `server-returned-tool-xml-outside-tool_calls`
or `server-returned-reasoning-without-tool_calls`, the failure is still on the
model/template/parser side. The trace log contains full prompts and tool
results, so treat `logs\openai-proxy-trace.jsonl` as sensitive.

The standard 200K Qwen profiles deliberately keep KV cache at `q8_0`. The
native-max profiles switch to `q4_1` KV because that is what lets the 262,144
window fit on a 24 GB card without CPU layer spill. MTP uses llama.cpp's current
`--spec-type draft-mtp --spec-draft-n-max 2` flags; Unsloth notes that more
draft tokens can be faster on some hardware, but acceptance drops sharply above
2 in their MTP benchmark, so the catalog keeps the conservative value.

The `qwen36-27b-ngram-*` profiles remain isolated experiments, not recommended
defaults for Copilot agent sessions.

## Scripts

| Script                          | Purpose                                                              |
| ------------------------------- | -------------------------------------------------------------------- |
| `scripts\install-llama.ps1`     | Download official llama.cpp Windows release (CUDA/Vulkan/CPU).       |
| `scripts\start-server.ps1`      | Interactive menu, auto-installs llama.cpp, launches `llama-server`.  |
| `scripts\status-server.ps1`     | PID, model, /health probe, `nvidia-smi` snapshot.                    |
| `scripts\stop-server.ps1`       | Stop the background server.                                          |
| `scripts\trace-openai-proxy.js` | Logs raw OpenAI-compatible traffic between Copilot and `llama-server`. |
| `scripts\analyze-openai-trace.ps1` | Summarizes whether traced responses contained structured tool calls. |
| `scripts\models.ps1`            | Model catalog & sampler defaults (edit to add or tune profiles).     |
| `scripts\benchmark-models.ps1`  | Loads each catalog model, measures VRAM, runs a one-shot inference.  |
| `scripts\inspect-copilot-context.ps1` | Summarize Copilot prompt sizes and llama-server prompt tokens. |
| `scripts\initialize-copilot-local-agent.ps1` | Install minimal-context skills and LLM Gateway settings into a repo or user profile. |

## Measured GPU RAM

Verified on **NVIDIA RTX 3090 (24 GiB)** running Windows with llama.cpp
`b9219`, `--flash-attn on`, `--n-gpu-layers 99`, and `--no-mmproj` for the 27B
profiles. The numbers below are llama.cpp load-time fit estimates and parsed KV
details from `scripts\status-server.ps1`; they are the best signal for whether
the model stays on GPU without CPU layer spill.

| Key | KV | Context allocated | Layers on GPU | Fit estimate | KV details |
| --- | -- | ----------------- | ------------- | ------------ | ---------- |
| `qwen36-27b` | `q8_0` | 200,192 | 65/65 | 21,483 MiB used of 23,154 MiB free | 6.49 GiB primary KV |
| `qwen36-27b-quality-max` | `q4_1` | 262,144 | 65/65 | 22,210 MiB used of 23,154 MiB free | 5.00 GiB primary KV |
| `qwen36-27b-q5` | `q4_1` | 200,192 | 65/65 | 21,950 MiB used of 23,154 MiB free; leaves 1,203 MiB | 3.82 GiB primary KV |
| `qwen36-27b-max` | `q4_1` | 262,144 | 65/65 | 20,138 MiB used of 23,154 MiB free | 5.00 GiB primary KV |
| `qwen36-27b-mtp` | `q8_0` | 200,192 | 66/66 | 22,036 MiB used of 22,854 MiB free | 6.49 GiB primary KV plus draft KV |
| `qwen36-27b-mtp-quality` | `q4_1` | 200,192 | 66/66 | 21,400 MiB used of 22,854 MiB free; leaves 1,453 MiB | 3.82 GiB primary KV + 244 MiB draft KV |
| `qwen36-27b-mtp-max` | `q4_1` | 262,144 | 66/66 | 20,690 MiB used of 22,854 MiB free | 5.00 GiB primary KV + 320 MiB draft KV |

Reproduce with:

```powershell
.\scripts\start-server.ps1 -Model qwen36-27b
.\scripts\status-server.ps1
.\scripts\start-server.ps1 -Model qwen36-27b-quality-max
.\scripts\status-server.ps1
.\scripts\start-server.ps1 -Model qwen36-27b-q5
.\scripts\status-server.ps1
.\scripts\start-server.ps1 -Model qwen36-27b-mtp-quality
.\scripts\status-server.ps1
.\scripts\start-server.ps1 -Model qwen36-27b-mtp-max
.\scripts\status-server.ps1
```

For automated sweeps, `scripts\benchmark-models.ps1` still records results to
`logs\benchmark-results.json`, but the status parser is now the richer source
for context, KV, GPU/CPU split, speculative decoding, and load state.

## VS Code tasks
