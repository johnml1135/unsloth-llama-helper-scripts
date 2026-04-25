<#
.SYNOPSIS
    Reports whether llama-server (started via start-server.ps1) is running,
    which model it is serving, and whether its HTTP endpoint responds.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$logDir   = Join-Path $repoRoot 'logs'
$pidFile  = Join-Path $logDir   'llama-server.pid'
$infoFile = Join-Path $logDir   'llama-server.info.json'

if (-not (Test-Path $pidFile)) {
    Write-Host "llama-server: NOT RUNNING (no PID file)." -ForegroundColor Yellow
    return
}

$serverPid = (Get-Content $pidFile | Select-Object -First 1).Trim()
$proc = Get-Process -Id $serverPid -ErrorAction SilentlyContinue

if (-not $proc) {
    Write-Host "llama-server: NOT RUNNING (stale PID $serverPid)." -ForegroundColor Yellow
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    return
}

$info = $null
if (Test-Path $infoFile) {
    $info = Get-Content $infoFile -Raw | ConvertFrom-Json
}

Write-Host "llama-server: RUNNING" -ForegroundColor Green
Write-Host ("  PID         : {0}" -f $proc.Id)
Write-Host ("  Started     : {0:yyyy-MM-dd HH:mm:ss}" -f $proc.StartTime)
$mem = [math]::Round($proc.WorkingSet64 / 1GB, 2)
Write-Host ("  RAM (RSS)   : {0} GB" -f $mem)

if ($info) {
    Write-Host ("  Model key   : {0}" -f $info.Model)
    Write-Host ("  Alias       : {0}" -f $info.Alias)
    Write-Host ("  HF repo     : {0}" -f $info.HFRepo)
    if ($info.HFFile) {
        Write-Host ("  HF file     : {0}  ({1})" -f $info.HFFile, $info.Quant)
    } else {
        Write-Host ("  Quant       : {0}" -f $info.Quant)
    }
    Write-Host ("  Context     : {0}" -f $info.Context)
    Write-Host ("  Endpoint    : {0}" -f $info.BaseUrl)
    Write-Host ("  NoThink     : {0}" -f $info.NoThink)
}

# -- Probe HTTP endpoint ------------------------------------------------------
if ($info) {
    $health = "http://$($info.Host):$($info.Port)/health"
    $models = "http://$($info.Host):$($info.Port)/v1/models"
    try {
        $h = Invoke-RestMethod -Uri $health -TimeoutSec 3
        $status = if ($h.status) { $h.status } else { 'ok' }
        Write-Host ("  HTTP /health: {0}" -f $status) -ForegroundColor Green
    } catch {
        Write-Host ("  HTTP /health: UNREACHABLE ({0})" -f $_.Exception.Message) -ForegroundColor Yellow
        Write-Host "                (server may still be loading the model — check the log)" -ForegroundColor DarkGray
        return
    }
    try {
        $m = Invoke-RestMethod -Uri $models -TimeoutSec 3
        $names = ($m.data | ForEach-Object { $_.id }) -join ', '
        Write-Host ("  /v1/models  : {0}" -f $names)
    } catch {
        # not fatal
    }
}

# -- nvidia-smi snapshot if available ----------------------------------------
$smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($smi) {
    Write-Host ""
    Write-Host "GPU memory:" -ForegroundColor Cyan
    & nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader
}
