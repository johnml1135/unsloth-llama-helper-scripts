<#
.SYNOPSIS
Downloads the latest llama.cpp binaries, bypassing outdated WinGet installs.
#>
[CmdletBinding()]
param(
    [ValidateSet('cuda', 'vulkan', 'cpu')]
    [string]$Backend = 'cuda',
    [string]$Tag = 'latest',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$toolsDir = Join-Path $repoRoot 'tools\llama.cpp'
$binProbe = Join-Path $toolsDir 'llama-server.exe'

# 1. Scour PATH for the problematic WinGet version and remove it from current session
$env:PATH = ($env:PATH -split ';' | Where-Object { $_ -notmatch 'WinGet\\Packages\\ggml\.llamacpp' }) -join ';'

if ((Test-Path $binProbe) -and (-not $Force)) {
    Write-Host "Local llama.cpp already exists at $toolsDir" -ForegroundColor Green
    $env:PATH = "$toolsDir;$env:PATH"
    return $toolsDir
}

# -- Resolve release ----------------------------------------------------------
Write-Host "Querying GitHub for llama.cpp release ($Tag)..." -ForegroundColor Cyan
$apiUrl = if ($Tag -eq 'latest') { 'https://api.github.com/repos/ggml-org/llama.cpp/releases/latest' } else { "https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/$Tag" }
$headers = @{ 'User-Agent' = 'unsloth-llama-helper-scripts' }
$release = Invoke-RestMethod -Uri $apiUrl -Headers $headers

# -- Pick the right asset -----------------------------------------------------
# Pattern updated to handle both "cu12" and "cuda-12.x" naming variants
$pattern = switch ($Backend) {
    'cuda'   { '^llama-.*-bin-win-cuda-.*-x64\.zip$|^llama-.*-bin-win-cu.*-x64\.zip$' }
    'vulkan' { '^llama-.*-bin-win-vulkan-x64\.zip$' }
    'cpu'    { '^llama-.*-bin-win-cpu-x64\.zip$' }
}

$asset = $release.assets | Where-Object { $_.name -match $pattern } | Select-Object -First 1
if (-not $asset) {
    throw "No Windows $Backend asset found in release $($release.tag_name)."
}

Write-Host "Downloading $($asset.name)..." -ForegroundColor Cyan
$zip = Join-Path $env:TEMP "$($asset.name)"
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -UseBasicParsing

# -- Extract ------------------------------------------------------------------
if (Test-Path $toolsDir) { Remove-Item $toolsDir -Recurse -Force }
New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null

Write-Host "Extracting to $toolsDir..." -ForegroundColor Cyan
Expand-Archive -Path $zip -DestinationPath $toolsDir -Force
Remove-Item $zip -Force

# Flatten nested folders if present
if (-not (Test-Path (Join-Path $toolsDir 'llama-server.exe'))) {
    $inner = Get-ChildItem $toolsDir -Directory | Select-Object -First 1
    if ($inner) {
        Get-ChildItem $inner.FullName | Move-Item -Destination $toolsDir
        Remove-Item $inner.FullName -Recurse -Force
    }
}

# -- CUDA runtime DLLs (The 'cudart' fix) -------------------------------------
if ($Backend -eq 'cuda') {
    $cudartPattern = '^cudart-llama-bin-win-cu.*-x64\.zip$'
    $cudartAsset = $release.assets | Where-Object { $_.name -match $cudartPattern } | Select-Object -First 1
    
    if ($cudartAsset) {
        Write-Host "Downloading matching CUDA runtimes: $($cudartAsset.name)..." -ForegroundColor Cyan
        $cuZip = Join-Path $env:TEMP $cudartAsset.name
        Invoke-WebRequest -Uri $cudartAsset.browser_download_url -OutFile $cuZip -UseBasicParsing
        Expand-Archive -Path $cuZip -DestinationPath $toolsDir -Force
        Remove-Item $cuZip -Force
    }
}

$env:PATH = "$toolsDir;$env:PATH"
Write-Host "Successfully installed llama.cpp $($release.tag_name) to $toolsDir" -ForegroundColor Green
return $toolsDir
