<#
.SYNOPSIS
    Catalog of Unsloth GGUF models tuned for a single 24 GB NVIDIA GPU.

.DESCRIPTION
    Each entry is a profile of well-known-good llama-server arguments derived
    from Unsloth's official "How to Run Locally" pages:
      https://unsloth.ai/docs/models/qwen3.6
      https://unsloth.ai/docs/models/gemma-4

    Files are pulled via llama.cpp's `-hf user/repo --hf-file <name>.gguf`
    form, cached under $env:LLAMA_CACHE.

    Context-window choices are SIZED FOR 24 GB VRAM:
      - Qwen3.6 MoE 35B-A3B: kv_heads=2, KV scales modestly with ctx.
      - Qwen3.6-27B: HYBRID -- 16 of 64 layers full-attention (GQA 24:4,
        head_dim 256), other 48 are Gated DeltaNet linear-attention with
        constant-size state. KV at 128K @ q8_0 ~= 4.5 GB.
      - Gemma 4 26B-A4B (MoE): kv_heads=4 with sliding-window pattern;
        very modest KV.
      - Gemma 4 31B (dense): 60 layers w/ 1-in-6 full-attention pattern
        (10 full + 50 sliding-window-1024). KV at 128K @ q8_0 ~= 6 GB.

    Sizes/contexts here have been verified by scripts\benchmark-models.ps1.
    See README.md "Measured GPU RAM" section for actual numbers.
#>

# Profile schema:
#   Key        : menu key (short id)
#   Name       : human label
#   HFRepo     : huggingface repo for `-hf` shortcut
#   HFFile     : explicit GGUF filename in that repo (avoids HF preset 404s)
#   Quant      : human-readable quant tag (display only)
#   Alias      : value advertised to OpenAI clients (the "model" field)
#   Context    : --ctx-size (sized for 24 GB GPU, NOT the model max)
#   MaxContext : the model's native max (for documentation only)
#   Size       : on-disk weight size at the chosen quant (verified vs HF)
#   Family     : 'qwen36' | 'gemma4' (controls samplers)
#   Temp/TopP/TopK/MinP/PresencePenalty/RepeatPenalty
#              : optional per-profile sampler overrides
#   CacheTypeK/CacheTypeV
#              : KV cache quantization for this profile; default q8_0
#   NoMmproj   : pass --no-mmproj to avoid auto-loading unused vision projector
#   Batch/UBatch
#              : optional logical/physical batch sizes to reduce compute buffer
#   ExtraArgs  : array of llama-server args appended verbatim
#   Notes      : free-form caveats shown in the menu

$global:LlamaModelCatalog = [ordered]@{

    'qwen36-27b' = @{
        Name       = 'Qwen3.6 27B (dense/hybrid, recommended for tools)'
        HFRepo     = 'unsloth/Qwen3.6-27B-GGUF'
        HFFile     = 'Qwen3.6-27B-IQ4_XS.gguf'
        Quant      = 'IQ4_XS'
        Alias      = 'qwen3.6-27b'
        Context    = 200000
        MaxContext = 262144
        Size       = '14.4 GB'
        Family     = 'qwen36'
        CacheTypeK = 'q8_0'
        CacheTypeV = 'q8_0'
        NoMmproj   = $true
        Notes      = 'Dense coding profile with stronger structured outputs. This is the safest Qwen3.6 choice for agentic tool use after the llama.cpp reasoning/tool-call fixes; uses q8_0 KV for tool-call reliability and measures ~23.0 GiB @ 200K (~1 GiB free).'
    }

    'qwen36-27b-quality-max' = @{
        Name       = 'Qwen3.6 27B (Dynamic Q4 quality, max native context)'
        HFRepo     = 'unsloth/Qwen3.6-27B-GGUF'
        HFFile     = 'Qwen3.6-27B-UD-Q4_K_XL.gguf'
        Quant      = 'UD-Q4_K_XL'
        Alias      = 'qwen3.6-27b-quality-max'
        Context    = 262144
        MaxContext = 262144
        Size       = '16.4 GB'
        Family     = 'qwen36'
        CacheTypeK = 'q4_1'
        CacheTypeV = 'q4_1'
        NoMmproj   = $true
        Notes      = 'Higher-quality Unsloth Dynamic 4-bit build for non-MTP sessions. Verified 65/65 GPU layers at 262K with q4_1 KV, using 22,210 MiB of 23,154 MiB initially free; prefer qwen36-27b when q8_0 KV reliability matters more than quant quality.'
    }

    'qwen36-27b-q5' = @{
        Name       = 'Qwen3.6 27B (Q5 quality, 200K context)'
        HFRepo     = 'unsloth/Qwen3.6-27B-GGUF'
        HFFile     = 'Qwen3.6-27B-Q5_K_S.gguf'
        Quant      = 'Q5_K_S'
        Alias      = 'qwen3.6-27b-q5'
        Context    = 200000
        MaxContext = 262144
        Size       = '17.7 GB'
        Family     = 'qwen36'
        CacheTypeK = 'q4_1'
        CacheTypeV = 'q4_1'
        NoMmproj   = $true
        Notes      = 'Highest-weight non-MTP 27B profile kept in the curated 24 GB set. Verified 65/65 GPU layers at 200K with q4_1 KV, using 21,950 MiB and leaving 1,203 MiB; use this for quality-sensitive runs when less context is acceptable.'
    }

    'qwen36-27b-max' = @{
        Name       = 'Qwen3.6 27B (max native context, KV q4_1)'
        HFRepo     = 'unsloth/Qwen3.6-27B-GGUF'
        HFFile     = 'Qwen3.6-27B-IQ4_XS.gguf'
        Quant      = 'IQ4_XS'
        Alias      = 'qwen3.6-27b-max'
        Context    = 262144
        MaxContext = 262144
        Size       = '14.4 GB'
        Family     = 'qwen36'
        CacheTypeK = 'q4_1'
        CacheTypeV = 'q4_1'
        NoMmproj   = $true
        Notes      = 'Native 256K context profile for the 24 GB card. Uses q4_1 KV because q8_0 KV spills/fails above ~200K on this RTX 3090; prefer qwen36-27b for strict tool-call reliability.'
    }

    'qwen36-27b-mtp' = @{
        Name        = 'Qwen3.6 27B MTP (fast, q8_0 KV)'
        HFRepo      = 'unsloth/Qwen3.6-27B-MTP-GGUF'
        HFFile      = 'Qwen3.6-27B-IQ4_XS.gguf'
        Quant       = 'IQ4_XS + MTP'
        Alias       = 'qwen3.6-27b-mtp'
        Context     = 200000
        MaxContext  = 262144
        Size        = '14.6 GB'
        Family      = 'qwen36'
        CacheTypeK  = 'q8_0'
        CacheTypeV  = 'q8_0'
        NoMmproj    = $true
        Speculative = 'draft-mtp, draft_n_max=2'
        ExtraArgs   = @(
            '--spec-type', 'draft-mtp',
            '--spec-draft-n-max', '2'
        )
        Notes       = 'MTP speculative decoding profile from Unsloth. Keeps q8_0 KV and a conservative draft limit for agent sessions; increase draft_n_max only after local throughput testing.'
    }

    'qwen36-27b-mtp-quality' = @{
        Name        = 'Qwen3.6 27B MTP (Dynamic Q4 quality, 200K context)'
        HFRepo      = 'unsloth/Qwen3.6-27B-MTP-GGUF'
        HFFile      = 'Qwen3.6-27B-UD-Q4_K_XL.gguf'
        Quant       = 'UD-Q4_K_XL + MTP'
        Alias       = 'qwen3.6-27b-mtp-quality'
        Context     = 200000
        MaxContext  = 262144
        Size        = '16.7 GB'
        Family      = 'qwen36'
        CacheTypeK  = 'q4_1'
        CacheTypeV  = 'q4_1'
        NoMmproj    = $true
        Speculative = 'draft-mtp, draft_n_max=2'
        ExtraArgs   = @(
            '--spec-type', 'draft-mtp',
            '--spec-draft-n-max', '2'
        )
        Notes       = 'Higher-quality MTP profile using Unsloth Dynamic 4-bit weights. Verified 66/66 GPU layers at 200K with q4_1 KV, using 21,400 MiB and leaving 1,453 MiB; native-max context is intentionally left to the lighter IQ4_XS MTP profile.'
    }

    'qwen36-27b-mtp-max' = @{
        Name        = 'Qwen3.6 27B MTP (max native context, KV q4_1)'
        HFRepo      = 'unsloth/Qwen3.6-27B-MTP-GGUF'
        HFFile      = 'Qwen3.6-27B-IQ4_XS.gguf'
        Quant       = 'IQ4_XS + MTP'
        Alias       = 'qwen3.6-27b-mtp-max'
        Context     = 262144
        MaxContext  = 262144
        Size        = '14.6 GB'
        Family      = 'qwen36'
        CacheTypeK  = 'q4_1'
        CacheTypeV  = 'q4_1'
        NoMmproj    = $true
        Speculative = 'draft-mtp, draft_n_max=2'
        ExtraArgs   = @(
            '--spec-type', 'draft-mtp',
            '--spec-draft-n-max', '2'
        )
        Notes       = 'Fast native-256K profile. Uses q4_1 KV to avoid spilling model layers/state off the GPU on a 24 GB card; quality/reliability may be below the q8_0 200K profiles.'
    }

    'qwen36-35b-a3b' = @{ 
        Name       = 'Qwen3.6 35B-A3B (MoE, fast local coding)'
        HFRepo     = 'unsloth/Qwen3.6-35B-A3B-GGUF'
        HFFile     = 'Qwen3.6-35B-A3B-UD-Q4_K_S.gguf'
        Quant      = 'UD-Q4_K_S'
        Alias      = 'qwen3.6-35b-a3b'
        Context    = 200000
        MaxContext = 262144
        Size       = '19.5 GB'
        Family     = 'qwen36'
        CacheTypeK = 'q8_0'
        CacheTypeV = 'q8_0'
        Notes      = 'Fast MoE profile. Measured 23.6 GiB @ 200K -- TIGHT (~0.5 GiB free). Better for general coding than hard tool reliability; use qwen36-27b first for Copilot agent sessions.'
    }

    'gemma4-26b-a4b' = @{
        Name       = 'Gemma 4 26B-A4B (MoE)'
        HFRepo     = 'unsloth/gemma-4-26B-A4B-it-GGUF'
        HFFile     = 'gemma-4-26B-A4B-it-UD-Q5_K_S.gguf'
        Quant      = 'UD-Q5_K_S'
        Alias      = 'gemma-4-26b-a4b'
        Context    = 200000
        MaxContext = 262144
        Size       = '17.5 GB'
        Family     = 'gemma4'
        CacheTypeK = 'q8_0'
        CacheTypeV = 'q8_0'
        ExtraArgs  = @()
        Notes      = 'MoE w/ sliding-window. Measured 22.4 GiB @ 200K (~1.6 GiB free). mmproj vision sidecar not loaded.'
    }

    'gemma4-31b' = @{
        Name       = 'Gemma 4 31B (dense, sliding-window)'
        HFRepo     = 'unsloth/gemma-4-31B-it-GGUF'
        HFFile     = 'gemma-4-31B-it-IQ4_XS.gguf'
        Quant      = 'IQ4_XS'
        Alias      = 'gemma-4-31b'
        Context    = 131072
        MaxContext = 262144
        Size       = '15.3 GB'
        Family     = 'gemma4'
        CacheTypeK = 'q8_0'
        CacheTypeV = 'q8_0'
        ExtraArgs  = @()
        Notes      = 'Dense 60-layer with 1-in-6 full-attn (10 full + 50 sliding-1024). Measured 23.0 GiB @ 128K (no headroom for 200K).'
    }

    'qwen36-27b-ngram-general' = @{
        Name            = 'Qwen3.6 27B (experimental ngram speed, general)'
        HFRepo          = 'unsloth/Qwen3.6-27B-GGUF'
        HFFile          = 'Qwen3.6-27B-IQ4_XS.gguf'
        Quant           = 'IQ4_XS'
        Alias           = 'qwen3.6-27b-ngram-general'
        Context         = 128000
        MaxContext      = 262144
        Size            = '14.4 GB'
        Family          = 'qwen36'
        CacheTypeK      = 'q8_0'
        CacheTypeV      = 'q8_0'
        Temp            = '1.0'
        PresencePenalty = '1.5'
        ExtraArgs       = @(
            '--spec-type', 'ngram-mod',
            '--spec-ngram-mod-n-match', '24',
            '--spec-ngram-mod-n-min', '12',
            '--spec-ngram-mod-n-max', '48'
        )
        Notes           = 'Experimental speed preset adapted from the Reddit ngram-mod setup. Uses 128K ctx on the 24 GB IQ4_XS build. Best for repetitive rewrite/summarize loops; can regress or destabilize tool use.'
    }

    'qwen36-27b-ngram-coding' = @{
        Name       = 'Qwen3.6 27B (experimental ngram speed, coding)'
        HFRepo     = 'unsloth/Qwen3.6-27B-GGUF'
        HFFile     = 'Qwen3.6-27B-IQ4_XS.gguf'
        Quant      = 'IQ4_XS'
        Alias      = 'qwen3.6-27b-ngram-coding'
        Context    = 128000
        MaxContext = 262144
        Size       = '14.4 GB'
        Family     = 'qwen36'
        CacheTypeK = 'q8_0'
        CacheTypeV = 'q8_0'
        ExtraArgs  = @(
            '--spec-type', 'ngram-mod',
            '--spec-ngram-mod-n-match', '24',
            '--spec-ngram-mod-n-min', '12',
            '--spec-ngram-mod-n-max', '48'
        )
        Notes      = 'Experimental coding-speed preset using the corrected Reddit flags at 128K ctx. Keeps the standard Qwen coding sampler, but ngram-mod can still leak prior phrasing or break tool-heavy sessions.'
    }
}

# Family-level sampler defaults from Unsloth docs (precise-coding profile for
# Qwen3.6 thinking; Google defaults for Gemma 4).
$global:LlamaFamilyDefaults = @{
    'qwen36' = @{
        Temp            = '0.6'
        TopP            = '0.95'
        TopK            = '20'
        MinP            = '0.0'
        PresencePenalty = '0.0'
        RepeatPenalty   = '1.0'
    }
    'gemma4' = @{
        Temp            = '1.0'
        TopP            = '0.95'
        TopK            = '64'
        MinP            = '0.0'
        PresencePenalty = '0.0'
        RepeatPenalty   = '1.0'
    }
}
