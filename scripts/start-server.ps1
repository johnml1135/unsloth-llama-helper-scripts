<#
.SYNOPSIS
    Interactive launcher for llama-server with curated Unsloth GGUF profiles
    sized for a 24 GB NVIDIA GPU. Auto-installs llama.cpp on first run.

.DESCRIPTION
    Workflow:
      1. If llama-server.exe is not on PATH and not in tools\llama.cpp\,
         scripts\install-llama.ps1 is invoked first.
      2. Shows a menu of curated models (see scripts\models.ps1).
      3. Launches llama-server in the background, exposing an OpenAI-compatible
         endpoint at http://127.0.0.1:<Port>/v1 for VS Code Copilot Chat
         (BYOK via "github.copilot.chat.customOAIModels") or any other
         OpenAI-compatible client.

    Models are downloaded on demand by llama.cpp via -hf and cached under
    $env:LLAMA_CACHE (defaults to <repo>\models).

.PARAMETER Model
    Model key from scripts\models.ps1 (e.g. 'qwen36-35b-a3b'). If omitted
    or invalid, an interactive menu is shown.

.PARAMETER Port
    TCP port to bind. Default 8080.

.PARAMETER NoThink
    Disable reasoning/thinking output. For Qwen3.6, this forces
    `--reasoning off` and passes `enable_thinking:false` into the chat
    template.

.PARAMETER EnableReasoning
    Re-enable Qwen3.6 reasoning traces. This is disabled by default for
    Copilot-style clients because they do not reliably round-trip
    `reasoning_content` across tool calls.

.PARAMETER ContextOverride
    Override the catalog's --ctx-size for this launch.

.EXAMPLE
    .\scripts\start-server.ps1
    # interactive menu

.EXAMPLE
    .\scripts\start-server.ps1 -Model qwen36-27b
    # Copilot-safe default: reasoning off

.EXAMPLE
    .\scripts\start-server.ps1 -Model qwen36-27b -EnableReasoning
    # opt back into Qwen reasoning if your client preserves reasoning traces
#>

[CmdletBinding()]
param(
    [string]$Model,
    [int]$Port = 8080,
    [string]$ListenHost = '127.0.0.1',
    [switch]$NoThink,
    [switch]$EnableReasoning,
    [int]$ContextOverride
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$logDir   = Join-Path $repoRoot 'logs'
$logFile  = Join-Path $logDir   'llama-server.log'
$pidFile  = Join-Path $logDir   'llama-server.pid'
$infoFile = Join-Path $logDir   'llama-server.info.json'
$modelsDir = Join-Path $repoRoot 'models'
$qwenTemplateFile = Join-Path $PSScriptRoot 'templates\qwen36-tool-fix.jinja'
$statusScript = Join-Path $PSScriptRoot 'status-server.ps1'

. (Join-Path $PSScriptRoot 'server-status.ps1')

function Wait-LlamaServerStartupStatus {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$LogFile,
        [string]$ErrorLogFile,
        [int]$TimeoutSec = 60,
        [int]$PollSec = 3
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $lastBrief = $null

    Write-Host ""
    Write-Host ("Waiting for llama-server to load (up to {0} seconds)..." -f $TimeoutSec) -ForegroundColor Cyan

    while ($true) {
        $snapshot = Get-LlamaServerLogSnapshot -LogFile $LogFile -ErrorLogFile $ErrorLogFile
        $brief = Format-LlamaServerBriefStatus -Snapshot $snapshot

        if ($brief -and $brief -ne $lastBrief) {
            Write-Host ("  [{0:HH:mm:ss}] {1}" -f (Get-Date), $brief)
            $lastBrief = $brief
        }

        if ($snapshot.LoadState -eq 'ready') { return 'ready' }
        if ($snapshot.LoadState -eq 'failed') { return 'failed' }

        $Process.Refresh()
        if ($Process.HasExited) { return 'exited' }

        $remaining = ($deadline - (Get-Date)).TotalSeconds
        if ($remaining -le 0) { return 'timeout' }

        $sleepSeconds = [math]::Min($PollSec, [math]::Max(1, [int][math]::Ceiling($remaining)))
        Start-Sleep -Seconds $sleepSeconds
    }
}

if ($NoThink -and $EnableReasoning) {
    throw 'Choose either -NoThink or -EnableReasoning, not both.'
}

New-Item -ItemType Directory -Force -Path $logDir, $modelsDir | Out-Null

# -- Already running? ---------------------------------------------------------
if (Test-Path $pidFile) {
    $existingPid = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if ($existingPid -and (Get-Process -Id $existingPid -ErrorAction SilentlyContinue)) {
        Write-Host "llama-server is already running (PID $existingPid)." -ForegroundColor Yellow
        Write-Host "  scripts\status-server.ps1   # check status" -ForegroundColor Yellow
        Write-Host "  scripts\stop-server.ps1     # stop it" -ForegroundColor Yellow
        Write-Host ""
        & $statusScript
        return
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

# -- Ensure llama.cpp is installed --------------------------------------------
$toolsDir = Join-Path $repoRoot 'tools\llama.cpp'
$bundled  = Join-Path $toolsDir 'llama-server.exe'
$onPath   = Get-Command llama-server -ErrorAction SilentlyContinue

if (Test-Path $bundled) {
    $env:PATH = "$toolsDir;$env:PATH"
} elseif (-not $onPath) {
    Write-Host "llama-server not found. Installing llama.cpp..." -ForegroundColor Cyan
    & (Join-Path $PSScriptRoot 'install-llama.ps1') | Out-Null
    if (-not (Test-Path $bundled)) {
        throw "Install failed: $bundled missing."
    }
    $env:PATH = "$toolsDir;$env:PATH"
}

# -- Load catalog -------------------------------------------------------------
. (Join-Path $PSScriptRoot 'models.ps1')

# -- Select model -------------------------------------------------------------
$keys = @($global:LlamaModelCatalog.Keys)

if (-not $Model -or -not $global:LlamaModelCatalog.Contains($Model)) {
    Write-Host ""
    Write-Host "Select a model (24 GB VRAM profiles):" -ForegroundColor Cyan
    Write-Host ""
    for ($i = 0; $i -lt $keys.Count; $i++) {
        $k = $keys[$i]
        $m = $global:LlamaModelCatalog[$k]
        $idx = "[{0}]" -f ($i + 1)
        Write-Host ("  {0,-4} {1}" -f $idx, $m.Name) -ForegroundColor White
        Write-Host ("       size {0}, ctx {1} (native max {2})" -f $m.Size, $m.Context, $m.MaxContext) -ForegroundColor DarkGray
        Write-Host ("       {0}" -f $m.Notes) -ForegroundColor DarkGray
        Write-Host ""
    }

    $choice = Read-Host "Choice [1-$($keys.Count)]"
    $idxNum = 0
    if (-not [int]::TryParse($choice, [ref]$idxNum) -or $idxNum -lt 1 -or $idxNum -gt $keys.Count) {
        throw "Invalid selection: $choice"
    }
    $Model = $keys[$idxNum - 1]
}

$profile = $global:LlamaModelCatalog[$Model]
$family  = $global:LlamaFamilyDefaults[$profile.Family]

$ctx = if ($ContextOverride) { $ContextOverride } else { $profile.Context }
$temp = if ($profile.ContainsKey('Temp')) { $profile.Temp } else { $family.Temp }
$topP = if ($profile.ContainsKey('TopP')) { $profile.TopP } else { $family.TopP }
$topK = if ($profile.ContainsKey('TopK')) { $profile.TopK } else { $family.TopK }
$minP = if ($profile.ContainsKey('MinP')) { $profile.MinP } else { $family.MinP }
$presencePenalty = if ($profile.ContainsKey('PresencePenalty')) { $profile.PresencePenalty } else { $family.PresencePenalty }
$repeatPenalty = if ($profile.ContainsKey('RepeatPenalty')) { $profile.RepeatPenalty } else { $family.RepeatPenalty }
$cacheTypeK = if ($profile.ContainsKey('CacheTypeK')) { $profile.CacheTypeK } else { 'q8_0' }
$cacheTypeV = if ($profile.ContainsKey('CacheTypeV')) { $profile.CacheTypeV } else { 'q8_0' }
$speculative = if ($profile.ContainsKey('Speculative')) { $profile.Speculative } else { $null }
$noMmproj = $profile.ContainsKey('NoMmproj') -and [bool]$profile.NoMmproj
$batch = if ($profile.ContainsKey('Batch')) { $profile.Batch } else { $null }
$ubatch = if ($profile.ContainsKey('UBatch')) { $profile.UBatch } else { $null }

$reasoningMode = 'auto'
if ($profile.Family -eq 'qwen36') {
    if ($EnableReasoning) {
        $reasoningMode = 'on'
    } else {
        $reasoningMode = 'off'
    }
} elseif ($NoThink) {
    $reasoningMode = 'off'
}

# -- Build llama-server arg vector --------------------------------------------
$env:LLAMA_CACHE = $modelsDir

$llamaArgs = @(
    '-hf',               $profile.HFRepo
    '--hf-file',         $profile.HFFile
    '--alias',           $profile.Alias
    '--host',            $ListenHost
    '--port',            $Port
    '--ctx-size',        $ctx
    '--n-gpu-layers',    '99'
    '--flash-attn',      'on'
    '--cache-type-k',    $cacheTypeK
    '--cache-type-v',    $cacheTypeV
    '--jinja'
    '--temp',            $temp
    '--top-p',           $topP
    '--top-k',           $topK
    '--min-p',           $minP
    '--presence-penalty',$presencePenalty
    '--repeat-penalty',  $repeatPenalty
    '--parallel',        '1'
    '--metrics'
    '--verbose'
)

if ($batch) {
    $llamaArgs += @('--batch-size', $batch)
}

if ($ubatch) {
    $llamaArgs += @('--ubatch-size', $ubatch)
}

if ($noMmproj) {
    $llamaArgs += @('--no-mmproj')
}

if ($profile.ExtraArgs) {
    $llamaArgs += $profile.ExtraArgs
}

if ($profile.Family -eq 'qwen36') {
    if (-not (Test-Path $qwenTemplateFile)) {
        throw "Missing Qwen chat template file: $qwenTemplateFile"
    }
    $llamaArgs += @('--chat-template-file', $qwenTemplateFile)
}

# Qwen3.6 works best with the patched template. Keep reasoning off by default
# for Copilot-style clients, which do not resend reasoning_content across tool turns.
$templateKwargs = [ordered]@{}
if ($profile.Family -eq 'qwen36') {
    $templateKwargs['tool_parser'] = 'qwen3_coder'
    if ($reasoningMode -eq 'on') {
        $llamaArgs += @('--reasoning', 'on', '--reasoning-format', 'deepseek')
    } else {
        $llamaArgs += @('--reasoning', 'off')
        $templateKwargs['enable_thinking'] = $false
    }
}

if ($NoThink -and $profile.Family -ne 'qwen36') {
    $llamaArgs += @('--reasoning', 'off')
    $templateKwargs['enable_thinking'] = $false
}

if ($templateKwargs.Count -gt 0) {
    $kwargsJson = $templateKwargs | ConvertTo-Json -Compress
    $env:LLAMA_CHAT_TEMPLATE_KWARGS = $kwargsJson
} else {
    $kwargsJson = $null
    Remove-Item Env:\LLAMA_CHAT_TEMPLATE_KWARGS -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Starting llama-server..." -ForegroundColor Cyan
Write-Host "  Model       : $($profile.Name)"
Write-Host "  HF repo     : $($profile.HFRepo)"
Write-Host "  HF file     : $($profile.HFFile)  ($($profile.Quant), $($profile.Size))"
Write-Host "  Alias       : $($profile.Alias)"
Write-Host "  Context     : $ctx (native max $($profile.MaxContext))"
Write-Host "  KV cache    : K $cacheTypeK, V $cacheTypeV"
if ($batch -or $ubatch) {
    Write-Host "  Batch       : n_batch $batch, n_ubatch $ubatch"
}
if ($noMmproj) {
    Write-Host "  Vision      : mmproj disabled"
}
if ($speculative) {
    Write-Host "  Speculative : $speculative"
}
Write-Host "  Reasoning   : $reasoningMode"
if ($kwargsJson) {
    Write-Host "  Template    : $kwargsJson"
}
Write-Host "  Cache (HF)  : $modelsDir"
Write-Host "  Listen      : http://$ListenHost`:$Port  (OpenAI-compatible /v1)"
Write-Host "  Log         : $logFile"
Write-Host ""
Write-Host "First run will download $($profile.Size) of weights — be patient." -ForegroundColor Yellow

# Truncate previous log
Set-Content -Path $logFile -Value '' -Encoding ascii
Set-Content -Path "$logFile.err" -Value '' -Encoding ascii

$proc = Start-Process -FilePath 'llama-server' `
    -ArgumentList $llamaArgs `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError  "$logFile.err" `
    -WindowStyle Hidden `
    -PassThru

$proc.Id | Out-File -FilePath $pidFile -Encoding ascii -NoNewline

# Persist info for status-server.ps1
$info = [ordered]@{
    Pid       = $proc.Id
    Model     = $Model
    ModelName = $profile.Name
    Alias     = $profile.Alias
    Family    = $profile.Family
    HFRepo    = $profile.HFRepo
    HFFile    = $profile.HFFile
    Quant     = $profile.Quant
    Size      = $profile.Size
    Context   = $ctx
    MaxContext = $profile.MaxContext
    Host      = $ListenHost
    Port      = $Port
    BaseUrl   = "http://$ListenHost`:$Port/v1"
    StartedAt = (Get-Date).ToString('o')
    NoThink   = [bool]$NoThink
    Reasoning = $reasoningMode
    TemplateKwargs = $kwargsJson
    GpuLayers = 99
    FlashAttention = 'on'
    CacheTypeK = $cacheTypeK
    CacheTypeV = $cacheTypeV
    Speculative = $speculative
    VerboseLogging = $true
    NoMmproj = $noMmproj
    Batch = $batch
    UBatch = $ubatch
    Parallel = 1
    Temp = $temp
    TopP = $topP
    TopK = $topK
    MinP = $minP
    PresencePenalty = $presencePenalty
    RepeatPenalty = $repeatPenalty
}
$info | ConvertTo-Json | Set-Content -Path $infoFile -Encoding ascii

Write-Host ""
Write-Host "Started (PID $($proc.Id))." -ForegroundColor Green
Write-Host ""
Write-Host "VS Code Copilot Chat (BYOK):" -ForegroundColor Green
Write-Host "  Open settings.json and add to github.copilot.chat.customOAIModels:"
Write-Host @"
    {
      "name": "$($profile.Alias) (local)",
      "url":  "http://$ListenHost`:$Port/v1",
      "apiKey": "sk-no-key-required",
      "modelId": "$($profile.Alias)"
    }
"@ -ForegroundColor DarkGray
Write-Host ""
Write-Host "Tail log : Get-Content -Wait '$logFile'"
Write-Host "Status   : scripts\status-server.ps1"
Write-Host "Stop     : scripts\stop-server.ps1"

$startupResult = Wait-LlamaServerStartupStatus -Process $proc -LogFile $logFile -ErrorLogFile "$logFile.err" -TimeoutSec 60

Write-Host ""
if ($startupResult -eq 'ready') {
    Write-Host "Startup wait finished: server is ready." -ForegroundColor Green
} elseif ($startupResult -eq 'failed') {
    Write-Host "Startup wait finished: llama-server reported a load failure." -ForegroundColor Red
} elseif ($startupResult -eq 'exited') {
    Write-Host "Startup wait finished: llama-server exited before it became ready." -ForegroundColor Red
} else {
    Write-Host "Startup wait finished: 60 seconds elapsed; server may still be loading." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Full status:" -ForegroundColor Cyan
& $statusScript
