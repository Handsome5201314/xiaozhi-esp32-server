param(
    [Alias("Domain")]
    [string]$PublicHost = "39.106.188.229",
    [ValidateSet("http", "https")]
    [string]$HttpScheme = "http",
    [string]$StartScriptPath = (Join-Path $PSScriptRoot "start-cloud-xiaozhi-tunnel.ps1"),
    [string]$WatchLogPath = "C:\tmp\xiaozhi-cloud-tunnel-watch.log",
    [int]$IntervalSeconds = 30,
    [int]$RestartCooldownSeconds = 90
)

$ErrorActionPreference = "Stop"

Import-Module (Join-Path $PSScriptRoot "lib\XiaozhiPublicExposure.psm1") -Force

function Write-WatchLog {
    param([string]$Message)

    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $WatchLogPath -Value $line
}

function Test-RemoteHttpContains {
    param(
        [hashtable]$RemoteProbe,
        [string]$Url,
        [string]$ContainsText
    )

    $sshArgs = @(
        "-i", $RemoteProbe.KeyPath,
        "-o", "StrictHostKeyChecking=yes",
        "-o", "UserKnownHostsFile=$($RemoteProbe.KnownHostsPath)",
        "$($RemoteProbe.User)@$($RemoteProbe.ServerHost)",
        "curl -sS --max-time 5 $Url"
    )

    try {
        $output = & ssh @sshArgs 2>$null
        if ($LASTEXITCODE -ne 0) {
            return $false
        }
        if ([string]::IsNullOrEmpty($ContainsText)) {
            return $true
        }
        return ($output -join [Environment]::NewLine) -like "*$ContainsText*"
    }
    catch {
        return $false
    }
}

function Test-HttpContains {
    param(
        [string]$Url,
        [string]$ContainsText
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
        if ([string]::IsNullOrEmpty($ContainsText)) {
            return $true
        }
        return $response.Content -like "*$ContainsText*"
    }
    catch {
        return $false
    }
}

function Test-HttpOk {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
    }
    catch {
        return $false
    }
}

if (-not (Test-Path -LiteralPath $StartScriptPath)) {
    throw "Start script not found: $StartScriptPath"
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $WatchLogPath) | Out-Null
$probe = Get-XiaozhiTunnelHealthProbeConfig -PublicHost $PublicHost -HttpScheme $HttpScheme
$remoteProbe = Get-XiaozhiTunnelRemoteProbeConfig
$lastRestartAt = [datetime]::MinValue
Write-WatchLog "watcher_started"

while ($true) {
    $tunnelProcess = Get-CimInstance Win32_Process -Filter "Name = 'ssh.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*$($probe.ProcessNeedle)*" } |
        Select-Object -First 1

    $localOtaOk = Test-HttpOk -Url $probe.LocalOtaUrl
    $localVisionOk = Test-HttpOk -Url $probe.LocalVisionUrl
    $localWebsocketOk = Test-HttpOk -Url $probe.LocalWebsocketUrl
    $localServicesHealthy = $localOtaOk -and $localVisionOk -and $localWebsocketOk

    if (-not $localServicesHealthy) {
        Write-WatchLog "local_services_unhealthy"
        Start-Sleep -Seconds $IntervalSeconds
        continue
    }

    $restartReason = $null
    if (-not $tunnelProcess) {
        $restartReason = "tunnel_process_missing"
    }
    else {
        $remoteOtaOk = Test-RemoteHttpContains -RemoteProbe $remoteProbe -Url $remoteProbe.RemoteOtaUrl -ContainsText $remoteProbe.RemoteOtaHealthySubstring
        $remoteVisionOk = Test-RemoteHttpContains -RemoteProbe $remoteProbe -Url $remoteProbe.RemoteVisionUrl -ContainsText $remoteProbe.RemoteVisionHealthySubstring
        $remoteLoopbackHealthy = $remoteOtaOk -and $remoteVisionOk

        if (-not $remoteLoopbackHealthy) {
            $restartReason = "remote_loopback_unhealthy"
        }
        else {
            $publicOtaOk = Test-HttpContains -Url $probe.PublicOtaUrl -ContainsText $probe.PublicOtaHealthySubstring
            if (-not $publicOtaOk) {
                Write-WatchLog "public_ingress_unhealthy_but_tunnel_ok"
            }
        }
    }

    if ($restartReason) {
        $secondsSinceRestart = ((Get-Date) - $lastRestartAt).TotalSeconds
        if ($secondsSinceRestart -lt $RestartCooldownSeconds) {
            Start-Sleep -Seconds $IntervalSeconds
            continue
        }

        Write-WatchLog $restartReason
        Write-WatchLog "tunnel_restart_attempted"
        try {
            & $StartScriptPath | Out-Null
            $lastRestartAt = Get-Date
            Start-Sleep -Seconds 5

            $remoteOtaRecovered = Test-RemoteHttpContains -RemoteProbe $remoteProbe -Url $remoteProbe.RemoteOtaUrl -ContainsText $remoteProbe.RemoteOtaHealthySubstring
            $remoteVisionRecovered = Test-RemoteHttpContains -RemoteProbe $remoteProbe -Url $remoteProbe.RemoteVisionUrl -ContainsText $remoteProbe.RemoteVisionHealthySubstring
            if ($remoteOtaRecovered -and $remoteVisionRecovered) {
                Write-WatchLog "tunnel_recovered"
            }
            else {
                Write-WatchLog "tunnel_restart_failed"
            }
        }
        catch {
            $lastRestartAt = Get-Date
            Write-WatchLog ("tunnel_restart_failed: {0}" -f $_.Exception.Message)
        }
    }

    Start-Sleep -Seconds $IntervalSeconds
}
