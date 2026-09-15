param(
    [string]$ServerHost = "39.106.188.229",
    [string]$KnownHostsPath = "$HOME\.ssh\known_hosts_xiaozhi_cloud",
    [string]$SourceKnownHostsPath = "$HOME\.ssh\known_hosts"
)

$ErrorActionPreference = "Stop"

$targetDir = Split-Path -Parent $KnownHostsPath
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

if (Test-Path -LiteralPath $SourceKnownHostsPath) {
    $scanOutput = & ssh-keygen -F $ServerHost -f $SourceKnownHostsPath 2>$null |
        Where-Object {
            $_ -is [string] -and
            $_ -and
            -not $_.StartsWith("#") -and
            $_ -like "$ServerHost *"
        }
}

if (-not $scanOutput) {
    throw "No existing host key for $ServerHost was found in $SourceKnownHostsPath. Please add the host key once with ssh or ssh-keyscan, then rerun this script."
}

Set-Content -Path $KnownHostsPath -Value $scanOutput -Encoding ascii
Get-Item $KnownHostsPath | Select-Object FullName, Length, LastWriteTime
