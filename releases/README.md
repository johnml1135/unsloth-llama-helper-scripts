# Release cards

Each published Hugging Face model repo should start from a markdown card in this folder.

- Create one file per publish job.
- Keep the filename stable; the local `publish` command uploads that same file into the Hugging Face repo under `releases/`.
- Use `_template.md` as the starting point.

The local publish flow reads the card frontmatter, generates the Hugging Face `README.md`, uploads the GGUF, and uploads a Copilot-compatible `Modelfile`.
