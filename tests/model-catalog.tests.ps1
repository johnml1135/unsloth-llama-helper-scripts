<#
.SYNOPSIS
    Smoke tests for curated model catalog entries.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $repoRoot 'scripts\models.ps1')

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Name
    )

    if (-not $Condition) { throw $Name }
}

function Assert-Equal {
    param(
        [object]$Actual,
        [object]$Expected,
        [string]$Name
    )

    if ($Actual -ne $Expected) {
        throw "${Name}: expected '$Expected', got '$Actual'"
    }
}

function Assert-ContainsValue {
    param(
        [object[]]$Values,
        [object]$Expected,
        [string]$Name
    )

    if ($Expected -notin @($Values)) {
        throw "${Name}: expected list to contain '$Expected'"
    }
}

foreach ($key in @('qwen36-27b', 'qwen36-27b-quality-max', 'qwen36-27b-q5', 'qwen36-27b-max', 'qwen36-27b-mtp', 'qwen36-27b-mtp-quality', 'qwen36-27b-mtp-max')) {
    Assert-True $global:LlamaModelCatalog.Contains($key) "catalog contains $key"
}

$standard = $global:LlamaModelCatalog['qwen36-27b']
Assert-Equal $standard.Context 200000 'standard Qwen context'
Assert-Equal $standard.CacheTypeK 'q8_0' 'standard Qwen K cache type'
Assert-Equal $standard.CacheTypeV 'q8_0' 'standard Qwen V cache type'
Assert-Equal $standard.NoMmproj $true 'standard Qwen disables mmproj'

$qualityMax = $global:LlamaModelCatalog['qwen36-27b-quality-max']
Assert-Equal $qualityMax.HFRepo 'unsloth/Qwen3.6-27B-GGUF' 'quality max Qwen repo'
Assert-Equal $qualityMax.HFFile 'Qwen3.6-27B-UD-Q4_K_XL.gguf' 'quality max Qwen file'
Assert-Equal $qualityMax.Quant 'UD-Q4_K_XL' 'quality max Qwen quant'
Assert-Equal $qualityMax.Context 262144 'quality max Qwen context'
Assert-Equal $qualityMax.CacheTypeK 'q4_1' 'quality max Qwen K cache type'
Assert-Equal $qualityMax.CacheTypeV 'q4_1' 'quality max Qwen V cache type'
Assert-Equal $qualityMax.NoMmproj $true 'quality max Qwen disables mmproj'

$q5 = $global:LlamaModelCatalog['qwen36-27b-q5']
Assert-Equal $q5.HFRepo 'unsloth/Qwen3.6-27B-GGUF' 'Q5 Qwen repo'
Assert-Equal $q5.HFFile 'Qwen3.6-27B-Q5_K_S.gguf' 'Q5 Qwen file'
Assert-Equal $q5.Quant 'Q5_K_S' 'Q5 Qwen quant'
Assert-Equal $q5.Context 200000 'Q5 Qwen context'
Assert-Equal $q5.CacheTypeK 'q4_1' 'Q5 Qwen K cache type'
Assert-Equal $q5.CacheTypeV 'q4_1' 'Q5 Qwen V cache type'
Assert-Equal $q5.NoMmproj $true 'Q5 Qwen disables mmproj'

$standardMax = $global:LlamaModelCatalog['qwen36-27b-max']
Assert-Equal $standardMax.Context 262144 'max Qwen context'
Assert-Equal $standardMax.CacheTypeK 'q4_1' 'max Qwen K cache type'
Assert-Equal $standardMax.CacheTypeV 'q4_1' 'max Qwen V cache type'
Assert-Equal $standardMax.NoMmproj $true 'max Qwen disables mmproj'

$mtp = $global:LlamaModelCatalog['qwen36-27b-mtp']
Assert-Equal $mtp.HFRepo 'unsloth/Qwen3.6-27B-MTP-GGUF' 'MTP repo'
Assert-Equal $mtp.HFFile 'Qwen3.6-27B-IQ4_XS.gguf' 'MTP file'
Assert-Equal $mtp.Context 200000 'MTP standard context'
Assert-Equal $mtp.CacheTypeK 'q8_0' 'MTP standard K cache type'
Assert-Equal $mtp.CacheTypeV 'q8_0' 'MTP standard V cache type'
Assert-Equal $mtp.NoMmproj $true 'MTP standard disables mmproj'
Assert-ContainsValue $mtp.ExtraArgs '--spec-type' 'MTP has spec-type arg'
Assert-ContainsValue $mtp.ExtraArgs 'draft-mtp' 'MTP uses draft-mtp'
Assert-ContainsValue $mtp.ExtraArgs '--spec-draft-n-max' 'MTP has draft limit arg'
Assert-ContainsValue $mtp.ExtraArgs '2' 'MTP uses conservative draft limit'

$mtpQuality = $global:LlamaModelCatalog['qwen36-27b-mtp-quality']
Assert-Equal $mtpQuality.HFRepo 'unsloth/Qwen3.6-27B-MTP-GGUF' 'MTP quality repo'
Assert-Equal $mtpQuality.HFFile 'Qwen3.6-27B-UD-Q4_K_XL.gguf' 'MTP quality file'
Assert-Equal $mtpQuality.Quant 'UD-Q4_K_XL + MTP' 'MTP quality quant'
Assert-Equal $mtpQuality.Context 200000 'MTP quality context'
Assert-Equal $mtpQuality.CacheTypeK 'q4_1' 'MTP quality K cache type'
Assert-Equal $mtpQuality.CacheTypeV 'q4_1' 'MTP quality V cache type'
Assert-Equal $mtpQuality.NoMmproj $true 'MTP quality disables mmproj'
Assert-ContainsValue $mtpQuality.ExtraArgs 'draft-mtp' 'MTP quality uses draft-mtp'
Assert-ContainsValue $mtpQuality.ExtraArgs '2' 'MTP quality uses conservative draft limit'

$mtpMax = $global:LlamaModelCatalog['qwen36-27b-mtp-max']
Assert-Equal $mtpMax.Context 262144 'MTP max context'
Assert-Equal $mtpMax.CacheTypeK 'q4_1' 'MTP max K cache type'
Assert-Equal $mtpMax.CacheTypeV 'q4_1' 'MTP max V cache type'
Assert-Equal $mtpMax.NoMmproj $true 'MTP max disables mmproj'
Assert-ContainsValue $mtpMax.ExtraArgs 'draft-mtp' 'MTP max uses draft-mtp'

Write-Host 'model-catalog tests passed' -ForegroundColor Green