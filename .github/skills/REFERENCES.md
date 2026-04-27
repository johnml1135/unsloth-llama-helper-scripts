# Evidence base for the local-agent skills

Shared citation list for [.github/skills/](.github/skills/). Numbers used as `[E1]`-`[E9]` inside individual `SKILL.md` files.

## E1 — Anthropic, "Effective context engineering for AI agents" (Sep 29, 2025)
- URL: <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>
- Findings used:
  - "Context rot": as token count grows, recall degrades for **all** models; transformer attention is n² over context, so each new token depletes a finite "attention budget".
  - Goal is "the smallest possible set of high-signal tokens that maximize the likelihood of some desired outcome".
  - Long-horizon techniques: **compaction** (summarize then reinitiate), **structured note-taking** (NOTES.md / to-do file outside context), **sub-agent architectures** (each sub-agent burns 10K+ tokens, returns 1K-2K distilled).
  - Tool result clearing is a "lightest touch" form of compaction.
  - Just-in-time retrieval: keep lightweight identifiers (paths, queries) and load on demand via `glob`/`grep`/`head`/`tail` instead of pre-loading everything. Hybrid `CLAUDE.md` upfront + just-in-time exploration.
  - Bloated tool sets and overlapping tools are a top failure mode.

## E2 — Anthropic, "How we built our multi-agent research system" (Jun 13, 2025)
- URL: <https://www.anthropic.com/engineering/built-multi-agent-research-system>
- Findings used:
  - Token usage alone explains **80%** of performance variance on BrowseComp; tool-call count and model choice explain the remaining 15%.
  - Multi-agent (Opus lead + Sonnet sub-agents) beat single Opus by **90.2%** on internal research eval.
  - **Cost caveat**: agents use ~4× more tokens than chat; multi-agent uses ~**15×** more. Most coding tasks are not parallelizable enough to justify multi-agent.
  - Sub-agents must receive an explicit objective, output format, tool/source guidance, and clear task boundaries; vague delegations cause duplication.
  - Parallel tool calling (3-5 sub-agents in parallel, 3+ tools per sub-agent) cut research time by up to **90%** — but only when the model and parser support it cleanly.

## E3 — Anthropic, "Building effective agents" (Dec 19, 2024)
- URL: <https://www.anthropic.com/engineering/building-effective-agents>
- Findings used:
  - "Find the simplest solution possible, and only increase complexity when needed."
  - Agent-Computer Interface (ACI) deserves the same care as a UI: tool descriptions are part of the prompt budget.
  - Concrete fix: requiring **absolute file paths** removed a class of agent errors in their SWE-bench work.
  - Token-format rule: keep formats close to text the model has seen on the internet; avoid escape-heavy formats.

## E4 — Aider, "LLMs are bad at returning code in JSON" (Aug 14, 2024)
- URL: <https://aider.chat/2024/08/14/code-in-json.html>
- Findings used:
  - Across GPT-4o, Sonnet, DeepSeek-Coder: code wrapped in JSON tool calls scored measurably worse than markdown plain text on the Exercism benchmark, including more `SyntaxError`/`IndentationError` instances.
  - OpenAI strict-mode JSON did not recover the gap.
  - Implication: prefer search/replace blocks or markdown over JSON tool args for code edits, especially for smaller local models.

## E5 — Aider, Repository map (docs)
- URL: <https://aider.chat/docs/repomap.html>
- Findings used:
  - Aider sends a graph-ranked, token-budgeted **repo map** (default `--map-tokens 1024`) of class/method signatures only, instead of full files.
  - This is the canonical evidence-based pattern for "give the model enough context to navigate the repo without paying for the whole repo".

## E6 — Hsieh et al., "RULER: What's the Real Context Size of Your Long-Context LMs?" (arXiv 2404.06654, COLM 2024)
- URL: <https://arxiv.org/abs/2404.06654> · Leaderboard: <https://github.com/NVIDIA/RULER>
- Findings used:
  - Models advertise 128K-1M context but most degrade well below the claimed length on tasks beyond plain needle-in-haystack.
  - Concrete numbers relevant to this repo's models:
    - **Qwen3-30B-A3B (claim 128K, effective 64K)**: 96.5 @ 4K → 91.6 avg @ 32K → 79.2 @ 128K. This is the closest public proxy for the Qwen3.6-35B-A3B GGUF used here.
    - **Qwen3-32B (claim 128K, effective 128K)**: 98.4 @ 4K → 91.8 @ 32K → 85.6 @ 128K (still **~13 point** drop).
    - **Qwen3-14B**: 98.0 @ 4K → 94.0 @ 32K → 85.1 @ 128K.
  - Practical inference: on a single 24 GB GPU, treating the **first ~32K tokens** as the high-quality zone and **64K** as a soft ceiling gives a reproducible quality/throughput tradeoff.

## E7 — Liu et al., "Lost in the Middle: How Language Models Use Long Contexts" (arXiv 2307.03172, TACL 2023)
- URL: <https://arxiv.org/abs/2307.03172>
- Findings used:
  - Recall is U-shaped: information at the **start or end** of the prompt is recovered far better than information in the middle, even for explicit long-context models.
  - Implication: place the user's current task and the most-load-bearing facts at the **top of the system prompt** and again **immediately before the model's turn**; bury low-value context in the middle if it must be present.

## E8 — Drew Breunig, "How Long Contexts Fail" (Jun 22, 2025)
- URL: <https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html>
- Findings used (each is sourced to a primary paper or report in the article):
  - **Context Distraction**: Databricks long-context RAG study found Llama 3.1 405B accuracy starts to fall around **32K**; smaller models earlier. Gemini 2.5 Pro Pokémon agent began repeating actions past **~100K** tokens.
  - **Context Confusion**: Berkeley Function-Calling Leaderboard shows every model performs worse with more than one tool; quantized Llama-3.1-8B failed on GeoEngine with **46 tools** but succeeded with **19 tools**, even though the prompt fit in 16K.
  - **Context Clash**: Microsoft/Salesforce sharded-prompt study showed an average **39% drop** when information arrived in pieces vs. all at once; o3 dropped from **98.1 → 64.1**. "When LLMs take a wrong turn in a conversation, they get lost and do not recover" — strong argument for **fresh chats** and explicit handoffs over long incremental sessions.
  - **Context Poisoning**: Gemini 2.5 technical report — once a hallucinated "goal" enters context, the agent can pursue impossible goals for many turns.

## E9 — Qwen team, "Qwen3-Coder: Agentic Coding in the World" (Jul 22, 2025)
- URL: <https://qwenlm.github.io/blog/qwen3-coder/>
- Findings used:
  - Qwen3-Coder natively supports **256K** context, **1M with YaRN**.
  - It is RL-trained for multi-turn tool use (Agent RL), so it benefits from being driven as an agent — but RULER ([E6]) shows the *effective* context is still well under the advertised length.
