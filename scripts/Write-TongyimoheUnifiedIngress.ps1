param(
    [string]$RootDomain = "tongyimoheai.top",
    [string]$XiaozhiSiteAddress = "http://39.106.188.229",
    [string]$OutputPath = (Join-Path $PSScriptRoot "Caddyfile"),
    [string]$RagflowUpstream = "127.0.0.1:18008"
)

$ErrorActionPreference = "Stop"

Import-Module (Join-Path $PSScriptRoot "lib\XiaozhiPublicExposure.psm1") -Force

$content = Get-TongyimoheUnifiedIngressCaddyfileContent `
    -RootDomain $RootDomain `
    -XiaozhiSiteAddress $XiaozhiSiteAddress `
    -RagflowUpstream $RagflowUpstream

$resolvedOutputPath = if ([System.IO.Path]::IsPathRooted($OutputPath)) {
    $OutputPath
}
else {
    Join-Path (Get-Location) $OutputPath
}

Set-Content -Path $resolvedOutputPath -Value $content -Encoding UTF8
Get-Item $resolvedOutputPath | Select-Object FullName, Length, LastWriteTime
