param(
    [string]$ServerHost = "39.106.188.229",
    [string]$User = "root",
    [string]$KeyPath = "$HOME\.ssh\ai-scale-deploy",
    [string]$KnownHostsPath = "$HOME\AppData\Local\XiaozhiTunnel\known_hosts",
    [string]$SshPath = "C:\Windows\System32\OpenSSH\ssh.exe",
    [string]$SshLogPath = "C:\tmp\xiaozhi-cloud-tunnel-ssh.log",
    [string]$StdOutPath = "C:\tmp\xiaozhi-cloud-tunnel-out.log",
    [string]$StdErrPath = "C:\tmp\xiaozhi-cloud-tunnel-err.log"
)

$ErrorActionPreference = "Stop"

Import-Module (Join-Path $PSScriptRoot "lib\XiaozhiPublicExposure.psm1") -Force

function Assert-FileExists {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$Label
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label not found: $Path"
    }
}

Assert-FileExists -Path $SshPath -Label "ssh.exe"
Assert-FileExists -Path $KeyPath -Label "SSH private key"
Assert-FileExists -Path $KnownHostsPath -Label "Known hosts file"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $SshLogPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StdOutPath) | Out-Null

Get-CimInstance Win32_Process -Filter "Name = 'ssh.exe'" -ErrorAction SilentlyContinue |
    Where-Object {
        $_.ExecutablePath -eq $SshPath -and
        $_.CommandLine -like "*$ServerHost*" -and
        $_.CommandLine -like "*127.0.0.1:18000:127.0.0.1:8000*"
    } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

Remove-Item $StdOutPath, $StdErrPath, $SshLogPath -ErrorAction SilentlyContinue

$arguments = Get-XiaozhiTunnelSshArguments `
    -ServerHost $ServerHost `
    -User $User `
    -KeyPath $KeyPath `
    -KnownHostsPath $KnownHostsPath `
    -SshLogPath $SshLogPath

$process = Start-Process -FilePath $SshPath `
    -ArgumentList $arguments `
    -WindowStyle Hidden `
    -RedirectStandardOutput $StdOutPath `
    -RedirectStandardError $StdErrPath `
    -PassThru

Start-Sleep -Seconds 5

$running = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
if (-not $running) {
    $details = @()
    if (Test-Path $StdErrPath) {
        $details += Get-Content $StdErrPath -Tail 100
    }
    if (Test-Path $SshLogPath) {
        $details += Get-Content $SshLogPath -Tail 100
    }

    throw "SSH tunnel process exited before becoming healthy.`n$($details -join [Environment]::NewLine)"
}

$running | Select-Object Id, ProcessName, StartTime

if (Test-Path $StdErrPath) {
    Get-Content $StdErrPath -Tail 20
}
