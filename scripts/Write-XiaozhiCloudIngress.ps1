param(
    [Alias("Domain")]
    [string]$SiteAddress = "http://39.106.188.229",
    [string]$OutputPath = (Join-Path $PSScriptRoot "Caddyfile")
)

$ErrorActionPreference = "Stop"

Import-Module (Join-Path $PSScriptRoot "lib\XiaozhiPublicExposure.psm1") -Force

$content = Get-XiaozhiCaddyfileContent -SiteAddress $SiteAddress
$resolvedOutputPath = if ([System.IO.Path]::IsPathRooted($OutputPath)) {
    $OutputPath
}
else {
    Join-Path (Get-Location) $OutputPath
}

Set-Content -Path $resolvedOutputPath -Value $content -Encoding UTF8
Get-Item $resolvedOutputPath | Select-Object FullName, Length, LastWriteTime
