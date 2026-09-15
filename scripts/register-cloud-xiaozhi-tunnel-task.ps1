param(
    [string]$TaskName = "xiaozhi-cloud-tunnel",
    [string]$ScriptPath = (Join-Path $PSScriptRoot "watch-cloud-xiaozhi-tunnel.ps1"),
    [string]$PowerShellPath = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ScriptPath)) {
    throw "Tunnel script not found: $ScriptPath"
}

$action = New-ScheduledTaskAction `
    -Execute $PowerShellPath `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""

$startupTrigger = New-ScheduledTaskTrigger -AtStartup
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger @($startupTrigger, $logonTrigger) `
    -Settings $settings `
    -Description "Keeps the xiaozhi reverse SSH tunnel online for 39.106.188.229." `
    -RunLevel Highest `
    -Force | Out-Null

Get-ScheduledTask -TaskName $TaskName |
    Select-Object TaskName, State, Author
