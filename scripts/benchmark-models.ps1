<#
.SYNOPSIS
    Benchmark each model in scripts/models.ps1: start it, wait for /health,
    measure VRAM after load and after a small inference, stop it, record
    results to logs/benchmark-results.json.

.DESCRIPTION
    Used to verify catalog Context/Quant choices fit a 24 GB GPU. Run with
    no other GPU consumers active. First runs will download weights.

.PARAMETER Models
    Optional subset of model keys. Default: all in the catalog.

.PARAMETER Port
    TCP port to test on. Default 8080.
#>
[CmdletBinding()]
param(
    [string[]]$Models,
    [int]$Port = 8080
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$logDir   = Join-Path $repoRoot 'logs'
$resultsFile = Join-Path $logDir 'benchmark-results.json'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

. (Join-Path $PSScriptRoot 'models.ps1')

if (-not $Models) { $Models = @($global:LlamaModelCatalog.Keys) }

function Get-GpuMb {
    $line = & nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | Select-Object -First 1
    return [int]$line.Trim()
}

function Wait-ForHealth {
    param([string]$Url, [int]$TimeoutSec = 600)
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSec) {
        try {
            $r = Invoke-RestMethod -Uri $Url -TimeoutSec 2 -ErrorAction Stop
            if ($r.status -eq 'ok' -or $r.status -eq $null) { return $true }
        } catch { }
        Start-Sleep -Milliseconds 1500
    }
    return $false
}

$results = @()
foreach ($key in $Models) {
    if (-not $global:LlamaModelCatalog.Contains($key)) {
        Write-Warning "Unknown model key: $key (skipping)"
        continue
    }

    Write-Host ""
    Write-Host "===== Benchmarking $key =====" -ForegroundColor Cyan

    # Make sure nothing is running.
    & (Join-Path $PSScriptRoot 'stop-server.ps1') | Out-Null
    Start-Sleep -Seconds 2

    $baseMb = Get-GpuMb
    Write-Host ("  Baseline VRAM used: {0} MiB" -f $baseMb) -ForegroundColor DarkGray

    # Launch via the real start-server.ps1 so we test the same args users get.
    & (Join-Path $PSScriptRoot 'start-server.ps1') -Model $key -Port $Port | Out-Null

    $base = "http://127.0.0.1:$Port"
    $ready = Wait-ForHealth -Url "$base/health" -TimeoutSec 1800
    if (-not $ready) {
        Write-Warning "  $key never became healthy; skipping"
        & (Join-Path $PSScriptRoot 'stop-server.ps1') | Out-Null
        $results += [ordered]@{
            Model     = $key
            Status    = 'failed-to-load'
        }
        continue
    }

    Start-Sleep -Seconds 3
    $loadedMb = Get-GpuMb
    Write-Host ("  After load        : {0} MiB ({1} MiB delta)" -f $loadedMb, ($loadedMb - $baseMb)) -ForegroundColor Green

    # Small inference to populate KV cache and exercise compute paths.
    $info = Get-Content (Join-Path $logDir 'llama-server.info.json') -Raw | ConvertFrom-Json
    $body = @{
        model       = $info.Alias
        messages    = @(@{ role = 'user'; content = 'Reply with exactly: OK' })
        max_tokens  = 8
        temperature = 0
    } | ConvertTo-Json -Depth 5
    $reply = $null
    try {
        $resp = Invoke-RestMethod -Uri "$base/v1/chat/completions" -Method Post `
            -ContentType 'application/json' -Body $body -TimeoutSec 120
        $reply = $resp.choices[0].message.content
    } catch {
        Write-Warning "  inference failed: $($_.Exception.Message)"
    }

    Start-Sleep -Seconds 2
    $afterMb = Get-GpuMb
    Write-Host ("  After inference   : {0} MiB ({1} MiB delta from baseline)" -f $afterMb, ($afterMb - $baseMb)) -ForegroundColor Green

    $profile = $global:LlamaModelCatalog[$key]
    $results += [ordered]@{
        Model            = $key
        HFRepo           = $profile.HFRepo
        Quant            = $profile.Quant
        Context          = $profile.Context
        BaselineMiB      = $baseMb
        LoadedMiB        = $loadedMb
        AfterInferMiB    = $afterMb
        DeltaLoadMiB     = $loadedMb - $baseMb
        DeltaInferMiB    = $afterMb - $baseMb
        DeltaInferGiB    = [math]::Round(($afterMb - $baseMb) / 1024.0, 2)
        Reply            = $reply
        Status           = 'ok'
    }

    & (Join-Path $PSScriptRoot 'stop-server.ps1') | Out-Null
    Start-Sleep -Seconds 3
}

$results | ConvertTo-Json -Depth 5 | Set-Content -Path $resultsFile -Encoding utf8
Write-Host ""
Write-Host "===== SUMMARY =====" -ForegroundColor Cyan
$results | ForEach-Object {
    if ($_.Status -eq 'ok') {
        Write-Host ("  {0,-18} {1,-14} ctx {2,-7} -> {3,5} GiB used (delta from baseline)" -f `
            $_.Model, $_.Quant, $_.Context, $_.DeltaInferGiB) -ForegroundColor Green
    } else {
        Write-Host ("  {0,-18} FAILED ({1})" -f $_.Model, $_.Status) -ForegroundColor Red
    }
}
Write-Host ""
Write-Host "Results written to $resultsFile" -ForegroundColor DarkGray
