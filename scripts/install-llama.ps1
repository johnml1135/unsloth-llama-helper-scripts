<#
.SYNOPSIS
    Downloads a prebuilt llama.cpp Windows binary release into tools\llama.cpp\
    and adds it to the current PowerShell session's PATH.

.DESCRIPTION
    Idempotent. If a working llama-server.exe already exists in tools\llama.cpp\
    it does nothing unless -Force is passed.

    Default backend is CUDA 12 (works on every modern NVIDIA driver).
    Pass -Backend vulkan for AMD/Intel/cross-vendor or -Backend cpu for CPU-only.

    Source: https://github.com/ggml-org/llama.cpp/releases (official builds).
#>

[CmdletBinding()]
param(
    [ValidateSet('cuda', 'vulkan', 'cpu')]
    [string]$Backend = 'cuda',

    # Specific release tag like 'b6700'. Default = latest.
    [string]$Tag = 'latest',

    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$toolsDir = Join-Path $repoRoot 'tools\llama.cpp'
$binProbe = Join-Path $toolsDir 'llama-server.exe'

if ((Test-Path $binProbe) -and (-not $Force)) {
    Write-Host "llama.cpp already installed at $toolsDir" -ForegroundColor Green
    $env:PATH = "$toolsDir;$env:PATH"
    return $toolsDir
}

# -- Resolve release ----------------------------------------------------------
Write-Host "Querying GitHub for llama.cpp release ($Tag)..." -ForegroundColor Cyan
$apiUrl = if ($Tag -eq 'latest') {
    'https://api.github.com/repos/ggml-org/llama.cpp/releases/latest'
} else {
    "https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/$Tag"
}

$headers = @{ 'User-Agent' = 'unsloth-llama-helper-scripts' }
$release = Invoke-RestMethod -Uri $apiUrl -Headers $headers

# -- Pick the right asset -----------------------------------------------------
# Asset names look like:
#   llama-b6700-bin-win-cuda-12.4-x64.zip
#   llama-b6700-bin-win-vulkan-x64.zip
#   llama-b6700-bin-win-cpu-x64.zip
$pattern = switch ($Backend) {
    'cuda'   { '^llama-.*-bin-win-cuda-.*-x64\.zip$' }
    'vulkan' { '^llama-.*-bin-win-vulkan-x64\.zip$' }
    'cpu'    { '^llama-.*-bin-win-cpu-x64\.zip$' }
}

$asset = $release.assets | Where-Object { $_.name -match $pattern } | Select-Object -First 1
if (-not $asset) {
    $names = ($release.assets.name -join "`n  ")
    throw "No Windows $Backend asset found in release $($release.tag_name).`nAvailable assets:`n  $names"
}

Write-Host "Downloading $($asset.name) ($([math]::Round($asset.size / 1MB, 1)) MB)..." -ForegroundColor Cyan

$tmp = New-TemporaryFile
$zip = "$($tmp.FullName).zip"
Remove-Item $tmp -Force
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -UseBasicParsing

# -- Extract ------------------------------------------------------------------
if (Test-Path $toolsDir) { Remove-Item $toolsDir -Recurse -Force }
New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null

Write-Host "Extracting to $toolsDir..." -ForegroundColor Cyan
Expand-Archive -Path $zip -DestinationPath $toolsDir -Force
Remove-Item $zip -Force

# Some release zips nest binaries one level deep; flatten if so.
if (-not (Test-Path (Join-Path $toolsDir 'llama-server.exe'))) {
    $inner = Get-ChildItem $toolsDir -Directory | Select-Object -First 1
    if ($inner) {
        Get-ChildItem $inner.FullName | Move-Item -Destination $toolsDir
        Remove-Item $inner.FullName -Recurse -Force
    }
}

if (-not (Test-Path (Join-Path $toolsDir 'llama-server.exe'))) {
    throw "Extraction succeeded but llama-server.exe not found under $toolsDir."
}

# -- CUDA runtime DLLs --------------------------------------------------------
# CUDA builds REQUIRE the matching cudart DLLs to load the CUDA backend; the
# release zip ships them in a separate cudart-llama-bin-win-*.zip. Auto-fetch
# the one matching the chosen CUDA version of the main asset.
if ($Backend -eq 'cuda') {
    $cudartProbe = Get-ChildItem $toolsDir -Filter 'cudart*.dll' -ErrorAction SilentlyContinue
    if (-not $cudartProbe) {
        # Match the CUDA version embedded in the main asset name, e.g. "cuda-12.4".
        $cudaVer = $null
        if ($asset.name -match 'cuda-([\d\.]+)') { $cudaVer = $Matches[1] }
        $cudartPattern = if ($cudaVer) {
            "^cudart-llama-bin-win-cuda-$([regex]::Escape($cudaVer))-x64\.zip$"
        } else {
            '^cudart-llama-bin-win-cuda-.*-x64\.zip$'
        }
        $cudartAsset = $release.assets | Where-Object { $_.name -match $cudartPattern } | Select-Object -First 1
        if ($cudartAsset) {
            Write-Host "Downloading $($cudartAsset.name) ($([math]::Round($cudartAsset.size / 1MB, 1)) MB)..." -ForegroundColor Cyan
            $cudartZip = "$($zip).cudart.zip"
            Invoke-WebRequest -Uri $cudartAsset.browser_download_url -OutFile $cudartZip -UseBasicParsing
            Expand-Archive -Path $cudartZip -DestinationPath $toolsDir -Force
            Remove-Item $cudartZip -Force
            Write-Host "CUDA runtime DLLs extracted to $toolsDir" -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "NOTE: CUDA build extracted, but no cudart*.dll detected and no cudart" -ForegroundColor Yellow
            Write-Host "asset matched. If llama-server fails to start, manually download a" -ForegroundColor Yellow
            Write-Host "cudart-llama-bin-win-*.zip from the release page into $toolsDir." -ForegroundColor Yellow
        }
    }
}

$env:PATH = "$toolsDir;$env:PATH"

Write-Host ""
Write-Host "Installed llama.cpp $($release.tag_name) ($Backend) -> $toolsDir" -ForegroundColor Green
Write-Host "llama-server.exe is on PATH for this session." -ForegroundColor Green
return $toolsDir
