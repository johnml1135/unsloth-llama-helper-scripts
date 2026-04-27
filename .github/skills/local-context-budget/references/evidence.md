# Evidence

- Anthropic, "Effective context engineering for AI agents": use the smallest high-signal token set, compact long histories, clear stale tool results, and load context just in time.
- NVIDIA RULER: public Qwen3 models degrade well before their claimed maximum context; Qwen3-30B-A3B is a close public proxy for the local Qwen3.6 A3B profile and is effectively a 64K model, not a 128K-quality model.
- "Lost in the Middle": high-value facts are recalled best at the start and end of the prompt.
- Drew Breunig, "How Long Contexts Fail": large contexts start distracting models well before the window is full; smaller models degrade earlier.

Full source list: [shared references](../../REFERENCES.md)