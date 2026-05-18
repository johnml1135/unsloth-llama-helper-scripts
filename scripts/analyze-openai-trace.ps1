<#
.SYNOPSIS
    Summarizes OpenAI-compatible request/response traces captured by trace-openai-proxy.js.
#>

[CmdletBinding()]
param(
    [string]$LogPath = (Join-Path (Split-Path -Parent $PSScriptRoot) 'logs\openai-proxy-trace.jsonl'),
    [int]$Last = 20
)

$ErrorActionPreference = 'Stop'

function ConvertFrom-JsonOrNull {
    param([string]$Text)
    try {
        return $Text | ConvertFrom-Json -ErrorAction Stop
    } catch {
        return $null
    }
}

function Get-ResponseSummary {
    param([string]$Body)

    $json = ConvertFrom-JsonOrNull $Body
    if ($json) {
        $toolNames = @()
        $finishReasons = @()
        $hasReasoning = $false
        $hasToolXml = $false

        foreach ($choice in @($json.choices)) {
            $finishReasons += $choice.finish_reason
            $message = $choice.message
            if ($message.reasoning_content) {
                $hasReasoning = $true
                if ([string]$message.reasoning_content -like '*<tool_call>*') { $hasToolXml = $true }
            }
            if ($message.content -and [string]$message.content -like '*<tool_call>*') { $hasToolXml = $true }
            foreach ($toolCall in @($message.tool_calls)) {
                if ($toolCall.function.name) {
                    $toolNames += $toolCall.function.name
                } else {
                    $toolNames += 'tool_call'
                }
            }
        }

        return [pscustomobject]@{
            Mode = 'json'
            FinishReasons = ($finishReasons | Where-Object { $_ }) -join ', '
            ToolCallCount = $toolNames.Count
            ToolCallNames = $toolNames -join ', '
            HasReasoningContent = $hasReasoning
            HasToolXmlInText = $hasToolXml
        }
    }

    $toolCallsByIndex = @{}
    $finishReasons = @()
    $hasReasoning = $false
    $hasToolXml = $false

    foreach ($line in ($Body -split "`r?`n")) {
        if (-not $line.StartsWith('data:')) { continue }
        $payload = $line.Substring(5).Trim()
        if (-not $payload -or $payload -eq '[DONE]') { continue }
        $chunk = ConvertFrom-JsonOrNull $payload
        if (-not $chunk) { continue }
        foreach ($choice in @($chunk.choices)) {
            if ($choice.finish_reason) { $finishReasons += $choice.finish_reason }
            $delta = $choice.delta
            if ($delta.reasoning_content) {
                $hasReasoning = $true
                if ([string]$delta.reasoning_content -like '*<tool_call>*') { $hasToolXml = $true }
            }
            if ($delta.content -and [string]$delta.content -like '*<tool_call>*') { $hasToolXml = $true }
            foreach ($toolCall in @($delta.tool_calls)) {
                $key = if ($null -ne $toolCall.index) { [string]$toolCall.index } elseif ($toolCall.id) { [string]$toolCall.id } else { [string]$toolCallsByIndex.Count }
                if ($toolCall.function.name) {
                    $toolCallsByIndex[$key] = $toolCall.function.name
                } elseif (-not $toolCallsByIndex.ContainsKey($key)) {
                    $toolCallsByIndex[$key] = 'tool_call'
                }
            }
        }
    }

    $toolNames = @($toolCallsByIndex.Values)

    return [pscustomobject]@{
        Mode = 'sse-or-text'
        FinishReasons = ($finishReasons | Where-Object { $_ }) -join ', '
        ToolCallCount = $toolNames.Count
        ToolCallNames = $toolNames -join ', '
        HasReasoningContent = $hasReasoning
        HasToolXmlInText = $hasToolXml
    }
}

if (-not (Test-Path $LogPath)) {
    throw "Trace log not found: $LogPath"
}

$entries = Get-Content $LogPath | Where-Object { $_ } | Select-Object -Last $Last | ForEach-Object { $_ | ConvertFrom-Json }

foreach ($entry in $entries) {
    $request = $entry.requestSummary
    $response = if ($entry.responseSummary) { $entry.responseSummary } else { Get-ResponseSummary $entry.responseBody }
    $roles = if ($request.messages) { ($request.messages | ForEach-Object { $_.role }) -join ' -> ' } else { '' }
    $tools = if ($request.tools) { $request.tools -join ', ' } else { '' }
    $finishReasons = @($response.finishReasons) -join ', '
    $toolCallCount = [int]$response.toolCallCount
    $toolCallNames = @($response.toolCallNames) -join ', '
    $hasReasoningContent = [bool]$response.hasReasoningContent
    $hasToolXml = [bool]$response.hasToolXmlInContentOrReasoning
    if ($response.PSObject.Properties.Name -contains 'HasToolXmlInText') {
        $hasToolXml = [bool]$response.HasToolXmlInText
    }

    $verdict = 'server-no-structured-tool-call'
    if ($toolCallCount -gt 0) {
        $verdict = 'server-returned-structured-tool-calls'
    } elseif ($hasToolXml) {
        $verdict = 'server-returned-tool-xml-outside-tool_calls'
    } elseif ($hasReasoningContent) {
        $verdict = 'server-returned-reasoning-without-tool_calls'
    }

    Write-Host "[$($entry.id)] $($entry.startedAt) $($entry.method) $($entry.path) -> $($entry.responseStatus) $($entry.durationMs)ms" -ForegroundColor Cyan
    Write-Host "  request : model=$($request.model) stream=$($request.stream) tool_choice=$($request.tool_choice) roles=$roles tools=$tools"
    Write-Host "  response: finish=$finishReasons toolCalls=$toolCallCount names=$toolCallNames reasoning=$hasReasoningContent toolXml=$hasToolXml"
    Write-Host "  verdict : $verdict"
    Write-Host ""
}