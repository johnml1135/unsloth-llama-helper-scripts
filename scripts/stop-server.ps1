<#
.SYNOPSIS
    Stops the background llama-server started by start-server.ps1.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$logDir   = Join-Path $repoRoot 'logs'
$pidFile  = Join-Path $logDir   'llama-server.pid'
$infoFile = Join-Path $logDir   'llama-server.info.json'

function Remove-StateFiles {
    foreach ($f in @($pidFile, $infoFile)) {
        if (Test-Path $f) { Remove-Item $f -Force -ErrorAction SilentlyContinue }
    }
}

if (-not (Test-Path $pidFile)) {
    Write-Host "No PID file at $pidFile - falling back to process-name match." -ForegroundColor Yellow
    $procs = Get-Process -Name 'llama-server' -ErrorAction SilentlyContinue
    if (-not $procs) {
        Write-Host "No llama-server process found." -ForegroundColor Yellow
        Remove-StateFiles
        return
    }
    foreach ($p in $procs) {
        Write-Host "Stopping llama-server PID $($p.Id)..." -ForegroundColor Cyan
        Stop-Process -Id $p.Id -Force
    }
    Remove-StateFiles
    return
}

$serverPid = (Get-Content $pidFile | Select-Object -First 1).Trim()
$proc = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
if (-not $proc) {
    Write-Host "PID $serverPid not running; cleaning up state files." -ForegroundColor Yellow
    Remove-StateFiles
    return
}

if ($proc.ProcessName -ne 'llama-server') {
    Write-Host "PID $serverPid is not llama-server (it's $($proc.ProcessName)); PID file is stale." -ForegroundColor Yellow
    Remove-StateFiles
    # Fall back to process-name match
    $procs = Get-Process -Name 'llama-server' -ErrorAction SilentlyContinue
    if ($procs) {
        foreach ($p in $procs) {
            Write-Host "Stopping llama-server PID $($p.Id)..." -ForegroundColor Cyan
            Stop-Process -Id $p.Id -Force
        }
        Write-Host "Stopped." -ForegroundColor Green
    }
    else {
        Write-Host "No llama-server process found." -ForegroundColor Yellow
    }
    return
}

Write-Host "Stopping llama-server PID $serverPid..." -ForegroundColor Cyan
Stop-Process -Id $serverPid -Force
Remove-StateFiles
Write-Host "Stopped." -ForegroundColor Green
