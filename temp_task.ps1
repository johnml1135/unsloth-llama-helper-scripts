.\scripts\stop-server.ps1
$startParam = "-Model qwen36-27b-mtp-max"
Write-Host "Starting server with $startParam..."
.\scripts\start-server.ps1 -Model qwen36-27b-mtp-max

$timeout = New-TimeSpan -Minutes 45
$sw = [diagnostics.stopwatch]::StartNew()
$lastDownloadReport = [diagnostics.stopwatch]::StartNew()
$ready = $false
$failed = $false

while ($sw.Elapsed -lt $timeout) {
    try {
        $statusStr = (.\scripts\status-server.ps1 | Out-String).Trim()
        # Look for the JSON block starting with {
        if ($statusStr -match '\{.*\}') {
            $jsonMatch = [regex]::Match($statusStr, '\{.*\}').Value
            $status = $jsonMatch | ConvertFrom-Json
            if ($status.status -eq "ok") {
                $ready = $true
                break
            }
        }
    } catch { }
    
    if (Test-Path "logs\llama-server.log.err") {
        $tail = Get-Content -Path "logs\llama-server.log.err" -Tail 200
        # Check for specific fatal errors, avoiding the "HEAD 404" or non-fatal ones
        if ($tail -match "error loading model|failed to load model|out of memory|CUDA error") {
            $failed = $true
            break
        }
    }

    if ($lastDownloadReport.Elapsed.TotalMinutes -ge 2) {
        $blobs = Get-ChildItem "models\models--unsloth--Qwen3.6-27B-MTP-GGUF\blobs\*.downloadInProgress" -ErrorAction SilentlyContinue
        if ($blobs) {
            foreach ($b in $blobs) {
                Write-Host "Download in progress: $($b.Name) - $([math]::round($b.Length / 1MB, 2)) MB"
            }
        } else {
            Write-Host "Polling: no active downloads found at $(Get-Date)"
        }
        $lastDownloadReport.Restart()
    }
    Start-Sleep -Seconds 20
}

if ($ready) { Write-Host "Server is ready." }
elseif ($failed) { Write-Host "Server failed to start." }
else { Write-Host "Timed out waiting for server." }

.\scripts\status-server.ps1
if (Test-Path "logs\llama-server.log.err") {
    $pattern = "speculative|draft|download|memory breakdown|projected to use|will leave|offloaded|CPU_Mapped model buffer|CUDA0 model buffer|llama_context: n_ctx\s*=|llama_kv_cache: size|KV buffer size|server is listening|error loading model|failed|out of memory"
    Select-String -Path "logs\llama-server.log.err" -Pattern $pattern | Select-Object -Last 160
}
.\scripts\stop-server.ps1
