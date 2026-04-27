# Evidence

- Berkeley function-calling results summarized by Drew Breunig: more tools usually means worse tool use, especially on smaller models.
- Anthropic, "Building effective agents": tool definitions are part of the prompt; clear names and absolute paths reduce failure modes.
- Aider benchmark, "LLMs are bad at returning code in JSON": large JSON payloads harm code-edit quality; plain-text or search-replace formats are safer.
- Qwen3-Coder guidance plus repo testing: Qwen is more reliable with sequential tool calls, Jinja chat templates, and the Qwen coder parser.

Full source list: [shared references](../../REFERENCES.md)