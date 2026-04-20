from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelTemplate:
    template: str
    stop: list[str]
    renderer: str | None = None
    parser: str | None = None
    # Default sampler temperature when the caller doesn't supply one. This lets
    # each architecture follow its upstream "best for coding" recommendation
    # (e.g. Unsloth recommends temperature=0.6 for Qwen3.6 thinking-mode coding).
    default_temperature: float = 0.7
    # Extra Ollama PARAMETER lines emitted in the generated Modelfile. Keys are
    # raw Ollama parameter names (top_p, top_k, min_p, repeat_penalty, ...).
    # Values are emitted verbatim. These are the upstream-recommended sampler
    # defaults for the architecture and can be overridden via Ollama's
    # /set parameter API at runtime.
    recommended_params: dict[str, float | int | str] = field(default_factory=dict)


_SYSTEM_MESSAGE = (
    "You are a helpful AI assistant with tool calling capabilities. "
    "You can help with code, answer questions, and use tools when needed."
)


_TOOLS_PREAMBLE = (
    "You have access to the following tools. Use them when helpful. "
    "When you call a tool, call it using the tool calling mechanism (not as plain text in the chat content).\n"
)


_TEMPLATES: dict[str, ModelTemplate] = {
    # Nemotron models in Ollama use a dedicated parser/renderer.
    # Applying Llama/Mistral-style chat templates to these models can result in empty outputs.
    "nemotron": ModelTemplate(
        template="{{ .Prompt }}",
        stop=[],
        renderer="nemotron-3-nano",
        parser="nemotron-3-nano",
    ),
    "llama3": ModelTemplate(
        template=(
            "{{ if .Messages }}\n"
            "{{- if or .System .Tools }}<|start_header_id|>system<|end_header_id|>\n"
            "{{- if .System }}\n\n"
            "{{ .System }}\n"
            "{{- end }}\n"
            "{{- if .Tools }}\n\n"
            f"{_TOOLS_PREAMBLE}"
            "{{ .Tools }}\n"
            "{{- end }}<|eot_id|>\n"
            "{{- end }}\n"
            "{{- range .Messages }}\n"
            "<|start_header_id|>{{ .Role }}<|end_header_id|>\n\n"
            "{{ .Content }}<|eot_id|>\n"
            "{{- end }}\n"
            "<|start_header_id|>assistant<|end_header_id|>\n\n"
            "{{ .Response }}<|eot_id|>\n"
            "{{- else }}\n"
            "<|start_header_id|>system<|end_header_id|>\n\n"
            "{{ .System }}<|eot_id|>\n"
            "<|start_header_id|>user<|end_header_id|>\n\n"
            "{{ .Prompt }}<|eot_id|>\n"
            "<|start_header_id|>assistant<|end_header_id|>\n\n"
            "{{ .Response }}<|eot_id|>"
            "{{- end }}"
        ),
        stop=["<|start_header_id|>", "<|end_header_id|>", "<|eot_id|>"],
    ),
    "mistral": ModelTemplate(
        template=(
            "{{ if .Messages }}\n"
            "{{- if or .System .Tools }}[INST]\n"
            "{{- if .System }}{{ .System }}\n"
            "{{- end }}\n"
            "{{- if .Tools }}\n\n"
            f"{_TOOLS_PREAMBLE}"
            "{{ .Tools }}\n"
            "{{- end }}[/INST]\n"
            "{{- end }}\n"
            "{{- range .Messages }}\n"
            "{{- if eq .Role \"user\" }}[INST] {{ .Content }} [/INST]\n"
            "{{- else if eq .Role \"assistant\" }}{{ .Content }}</s>\n"
            "{{- end }}\n"
            "{{- end }}\n"
            "{{ .Response }}</s>\n"
            "{{- else }}[INST] {{ if .System }}{{ .System }}\n\n"
            "{{ end }}{{ .Prompt }} [/INST]\n"
            "{{ .Response }}</s>\n"
            "{{- end }}"
        ),
        stop=["</s>", "[INST]", "[/INST]"],
    ),
    "phi3": ModelTemplate(
        template=(
            "{{ if .Messages }}\n"
            "{{- if or .System .Tools }}<|system|>\n"
            "{{- if .System }}{{ .System }}\n"
            "{{- end }}\n"
            "{{- if .Tools }}\n\n"
            f"{_TOOLS_PREAMBLE}"
            "{{ .Tools }}\n"
            "{{- end }}<|end|>\n"
            "{{- end }}\n"
            "{{- range .Messages }}\n"
            "<|{{ .Role }}|>\n"
            "{{ .Content }}<|end|>\n"
            "{{- end }}\n"
            "<|assistant|>\n"
            "{{ .Response }}<|end|>\n"
            "{{- else }}<|system|>\n"
            "{{ .System }}<|end|>\n"
            "<|user|>\n"
            "{{ .Prompt }}<|end|>\n"
            "<|assistant|>\n"
            "{{ .Response }}<|end|>\n"
            "{{- end }}"
        ),
        stop=["<|end|>", "<|system|>", "<|user|>", "<|assistant|>"],
    ),
    "gemma2": ModelTemplate(
        template=(
            "{{ if .Messages }}\n"
            "{{- if or .System .Tools }}<start_of_turn>model\n"
            "{{- if .System }}{{ .System }}\n"
            "{{- end }}\n"
            "{{- if .Tools }}\n\n"
            f"{_TOOLS_PREAMBLE}"
            "{{ .Tools }}\n"
            "{{- end }}<end_of_turn>\n"
            "{{- end }}\n"
            "{{- range .Messages }}\n"
            "<start_of_turn>{{ .Role }}\n"
            "{{ .Content }}<end_of_turn>\n"
            "{{- end }}\n"
            "<start_of_turn>model\n"
            "{{ .Response }}<end_of_turn>\n"
            "{{- else }}<start_of_turn>system\n"
            "{{ .System }}<end_of_turn>\n"
            "<start_of_turn>user\n"
            "{{ .Prompt }}<end_of_turn>\n"
            "<start_of_turn>model\n"
            "{{ .Response }}<end_of_turn>\n"
            "{{- end }}"
        ),
        stop=["<end_of_turn>", "<start_of_turn>"],
    ),
    "qwen": ModelTemplate(
        template=(
            "{{ if .Messages }}\n"
            "{{- if or .System .Tools }}<|im_start|>system\n"
            "{{- if .System }}\n"
            "{{ .System }}\n"
            "{{- end }}\n"
            "{{- if .Tools }}\n\n"
            f"{_TOOLS_PREAMBLE}"
            "{{ .Tools }}\n"
            "{{- end }}<|im_end|>\n"
            "{{- end }}\n"
            "{{- range .Messages }}\n"
            "<|im_start|>{{ .Role }}\n"
            "{{ .Content }}<|im_end|>\n"
            "{{- end }}\n"
            "<|im_start|>assistant\n"
            "{{ .Response }}<|im_end|>\n"
            "{{- else }}<|im_start|>system\n"
            "{{ .System }}<|im_end|>\n"
            "<|im_start|>user\n"
            "{{ .Prompt }}<|im_end|>\n"
            "<|im_start|>assistant\n"
            "{{ .Response }}<|im_end|>\n"
            "{{- end }}"
        ),
        stop=["<|im_start|>", "<|im_end|>"],
    ),
    "qwen35": ModelTemplate(
        template=(
            "{{- $lastUserIdx := -1 -}}\n"
            "{{- range $idx, $msg := .Messages -}}\n"
            "{{- if eq $msg.Role \"user\" }}{{ $lastUserIdx = $idx }}{{ end -}}\n"
            "{{- end }}\n"
            "{{- if or .System .Tools }}<|im_start|>system\n"
            "{{ if .System }}\n"
            "{{ .System }}\n"
            "{{- end }}\n"
            "{{- if .Tools }}# Tools\n"
            "You may call one or more functions to assist with the user query.\n"
            "You are provided with function signatures within <tools></tools> XML tags:\n"
            "<tools>\n"
            "{{- range .Tools }}\n"
            "{\"type\": \"function\", \"function\": {{ .Function }}}\n"
            "{{- end }}\n"
            "</tools>\n"
            "For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\n"
            "<tool_call>\n"
            "{\"name\": <function-name>, \"arguments\": <args-json-object>}\n"
            "</tool_call>\n"
            "{{- end -}}\n"
            "<|im_end|>\n"
            "{{ end }}\n"
            "{{- range $i, $_ := .Messages }}\n"
            "{{- $last := eq (len (slice $.Messages $i)) 1 -}}\n"
            "{{- if eq .Role \"user\" }}<|im_start|>user\n"
            "{{ .Content }}{{ if eq $i $lastUserIdx }} /no_think{{ end }}<|im_end|>\n"
            "{{ else if eq .Role \"assistant\" }}<|im_start|>assistant\n"
            "{{ if .Content }}{{ .Content }}\n"
            "{{- else if .ToolCalls }}<tool_call>\n"
            "{{ range .ToolCalls }}{\"name\": \"{{ .Function.Name }}\", \"arguments\": {{ .Function.Arguments }}}\n"
            "{{ end }}</tool_call>\n"
            "{{- end }}{{ if not $last }}<|im_end|>\n"
            "{{ end }}\n"
            "{{- else if eq .Role \"tool\" }}<|im_start|>user\n"
            "<tool_response>\n"
            "{{ .Content }}\n"
            "</tool_response><|im_end|>\n"
            "{{ end }}\n"
            "{{- if and (ne .Role \"assistant\") $last }}<|im_start|>assistant\n"
            "<think>\n\n</think>\n\n"
            "{{ end }}\n"
            "{{- end }}"
        ),
        stop=["<|im_start|>", "<|im_end|>"],
        # Unsloth-recommended Qwen3 thinking-mode "precise coding" sampler:
        # https://unsloth.ai/docs/models/qwen3.6 (same family guidance applies
        # to Qwen3.5 thinking-mode coding workloads such as GitHub Copilot).
        default_temperature=0.6,
        recommended_params={
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0.0,
            "repeat_penalty": 1.0,
        },
    ),
    # Qwen3.6 template.
    #
    # Behaviour matrix for the final assistant head and user-message suffix:
    #
    #   Tools present | IsThinkSet | Think | user suffix | assistant head seed
    #   ------------- | ---------- | ----- | ----------- | -------------------
    #   no            | no         | -     | /no_think   | <think>\n\n</think>\n\n
    #   no            | yes        | true  | /think      | <think>\n
    #   no            | yes        | false | /no_think   | <think>\n\n</think>\n\n
    #   yes           | no         | -     | (none)      | (none) -- let model emit <tool_call>
    #   yes           | yes        | true  | /think      | <think>\n
    #   yes           | yes        | false | /no_think   | <think>\n\n</think>\n\n
    #
    # The "tools present, no explicit think" path is critical for GitHub Copilot:
    # seeding </think> there makes the model treat the turn as "final answer"
    # and emit plain narration instead of <tool_call> blocks.
    "qwen36": ModelTemplate(
        template=(
            "{{- $lastUserIdx := -1 -}}\n"
            "{{- range $idx, $msg := .Messages -}}\n"
            "{{- if eq $msg.Role \"user\" }}{{ $lastUserIdx = $idx }}{{ end -}}\n"
            "{{- end }}\n"
            "{{- if or .System .Tools }}<|im_start|>system\n"
            "{{ if .System }}\n"
            "{{ .System }}\n"
            "{{- end }}\n"
            "{{- if .Tools }}# Tools\n"
            "You may call one or more functions to assist with the user query.\n"
            "You are provided with function signatures within <tools></tools> XML tags:\n"
            "<tools>\n"
            "{{- range .Tools }}\n"
            "{\"type\": \"function\", \"function\": {{ .Function }}}\n"
            "{{- end }}\n"
            "</tools>\n"
            "For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\n"
            "<tool_call>\n"
            "{\"name\": <function-name>, \"arguments\": <args-json-object>}\n"
            "</tool_call>\n"
            "{{- end -}}\n"
            "<|im_end|>\n"
            "{{ end }}\n"
            "{{- range $i, $_ := .Messages }}\n"
            "{{- $last := eq (len (slice $.Messages $i)) 1 -}}\n"
            "{{- if or (eq .Role \"system\") (eq .Role \"developer\") }}<|im_start|>{{ .Role }}\n"
            "{{ .Content }}<|im_end|>\n"
            "{{ else if eq .Role \"user\" }}<|im_start|>user\n"
            "{{ .Content }}"
            "{{- if eq $i $lastUserIdx }}"
            "{{- if $.IsThinkSet -}}"
            "{{- if $.Think -}} /think{{- else -}} /no_think{{- end -}}"
            "{{- else if not $.Tools -}} /no_think{{- end -}}"
            "{{- end }}<|im_end|>\n"
            "{{ else if eq .Role \"assistant\" }}<|im_start|>assistant\n"
            "{{- if and .Thinking (or $last (gt $i $lastUserIdx)) -}}"
            "<think>{{ .Thinking }}</think>\n"
            "{{- end }}"
            "{{ if .Content }}{{ .Content }}\n"
            "{{- else if .ToolCalls }}<tool_call>\n"
            "{{ range .ToolCalls }}{\"name\": \"{{ .Function.Name }}\", \"arguments\": {{ .Function.Arguments }}}\n"
            "{{ end }}</tool_call>\n"
            "{{- end }}{{ if not $last }}<|im_end|>\n"
            "{{ end }}\n"
            "{{- else if eq .Role \"tool\" }}<|im_start|>user\n"
            "<tool_response>\n"
            "{{ .Content }}\n"
            "</tool_response><|im_end|>\n"
            "{{ end }}\n"
            "{{- if and (ne .Role \"assistant\") $last }}<|im_start|>assistant\n"
            "{{- if $.IsThinkSet -}}"
            "{{- if $.Think -}}<think>\n{{- else -}}<think>\n\n</think>\n\n{{- end -}}"
            "{{- else if not $.Tools -}}<think>\n\n</think>\n\n{{- end }}\n"
            "{{ end }}\n"
            "{{- end }}"
        ),
        stop=["<|im_start|>", "<|im_end|>"],
        # Unsloth-recommended Qwen3.6 thinking-mode "precise coding" sampler.
        # Source: https://unsloth.ai/docs/models/qwen3.6 (Recommended Settings
        # -> Thinking mode -> Precise coding tasks). Copilot's agentic coding
        # workflow with tool calling matches this profile most closely; the
        # qwen36 template lets the model think when tools are present so this
        # sampler is the safest default.
        default_temperature=0.6,
        recommended_params={
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0.0,
            "repeat_penalty": 1.0,
        },
    ),
    "qwen35_legacy": ModelTemplate(
        template=(
            "{{ if .Messages }}\n"
            "{{- if or .System .Tools }}<|im_start|>system\n"
            "{{- if .Tools }}\n"
            "# Tools\n\n"
            "You have access to the following functions:\n\n<tools>\n"
            "{{ .Tools }}\n"
            "</tools>\n\n"
            "If you choose to call a function, respond with a tool call using the model's native tool-call format."
            "{{- if .System }}\n\n{{ .System }}{{- end }}"
            "{{- else if .System }}{{ .System }}"
            "{{- end }}<|im_end|>\n"
            "{{- end }}\n"
            "{{- range .Messages }}\n"
            "<|im_start|>{{ .Role }}\n"
            "{{ .Content }}<|im_end|>\n"
            "{{- end }}\n"
            "<|im_start|>assistant\n"
            "<think>\n"
            "{{ .Response }}"
            "{{- else }}\n"
            "<|im_start|>system\n"
            "{{ .System }}<|im_end|>\n"
            "<|im_start|>user\n"
            "{{ .Prompt }}<|im_end|>\n"
            "<|im_start|>assistant\n"
            "<think>\n"
            "{{ .Response }}"
            "{{- end }}"
        ),
        stop=["<|im_start|>", "<|im_end|>"],
    ),
}


def supported_architectures(*, include_internal: bool = False) -> list[str]:
    names = sorted(_TEMPLATES.keys())
    if include_internal:
        return names
    return [name for name in names if not name.endswith("_legacy")]


def generate_modelfile(
    *,
    absolute_model_path: str,
    architecture: str,
    context_length: int | None,
    temperature: float | None,
    extra_stop: list[str] | None = None,
    system_message: str | None = None,
) -> str:
    if architecture not in _TEMPLATES:
            raise ValueError(
            f"Unsupported architecture: {architecture}. Supported: {', '.join(supported_architectures(include_internal=True))}"
        )

    mt = _TEMPLATES[architecture]
    stop = list(mt.stop)
    if extra_stop:
        for s in extra_stop:
            if s not in stop:
                stop.append(s)

    effective_temperature = mt.default_temperature if temperature is None else temperature

    # Ollama Modelfile syntax
    out = [
        "# Auto-generated Modelfile with Tool capability for GitHub Copilot",
        f"# Architecture: {architecture}",
        "",
        f"FROM {absolute_model_path}",
        *(
            [f"RENDERER {mt.renderer}"]
            if mt.renderer
            else []
        ),
        *(
            [f"PARSER {mt.parser}"]
            if mt.parser
            else []
        ),
        "",
        "# Template",
        f'TEMPLATE """{mt.template}"""',
        "",
        "# Stop sequences",
    ]

    for seq in stop:
        out.append(f'PARAMETER stop "{seq}"')

    out += [
        "",
        "# Model parameters",
        f"PARAMETER temperature {effective_temperature}",
    ]
    for key, value in mt.recommended_params.items():
        out.append(f"PARAMETER {key} {value}")
    out += [
        "PARAMETER num_predict -1",
        "",
    ]

    # Nemotron parser/renderer handles chat/tool formatting; avoid forcing a system message
    # that isn't referenced in the template.
    if architecture != "nemotron":
        out += [
            "# System message",
            f'SYSTEM """{system_message or _SYSTEM_MESSAGE}"""',
            "",
        ]

    if context_length is not None:
        if context_length <= 0:
            raise ValueError("context_length must be a positive integer")
        out.insert(out.index("PARAMETER num_predict -1"), f"PARAMETER num_ctx {context_length}")

    return "\n".join(out)
