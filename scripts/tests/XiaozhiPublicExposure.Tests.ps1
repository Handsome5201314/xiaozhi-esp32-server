$modulePath = Join-Path $PSScriptRoot "..\lib\XiaozhiPublicExposure.psm1"
Import-Module $modulePath -Force

Describe "Xiaozhi public exposure helpers" {
    It "builds ssh tunnel arguments with the expected loopback-only reverse forwards" {
        $args = Get-XiaozhiTunnelSshArguments `
            -ServerHost "39.106.188.229" `
            -User "admin" `
            -KeyPath "C:\keys\xiaozhi_cloud_tunnel_ed25519" `
            -KnownHostsPath "C:\keys\known_hosts" `
            -SshLogPath "C:\logs\xiaozhi-cloud-tunnel.log"

        ($args -contains "-NT") | Should Be $true
        ($args -contains "admin@39.106.188.229") | Should Be $true
        ($args -contains "127.0.0.1:18000:127.0.0.1:8000") | Should Be $true
        ($args -contains "127.0.0.1:18002:127.0.0.1:8002") | Should Be $true
        ($args -contains "127.0.0.1:18003:127.0.0.1:8003") | Should Be $true
        ($args -contains "C:\keys\xiaozhi_cloud_tunnel_ed25519") | Should Be $true
        ($args -contains "UserKnownHostsFile=C:\keys\known_hosts") | Should Be $true
        ($args -contains "C:\logs\xiaozhi-cloud-tunnel.log") | Should Be $true
    }

    It "returns public IP endpoint values by default" {
        $values = Get-XiaozhiPublicEndpointValues

        $values["server.fronted_url"] | Should Be "http://39.106.188.229"
        $values["server.websocket"] | Should Be "ws://39.106.188.229/xiaozhi/v1/"
        $values["server.ota"] | Should Be "http://39.106.188.229/xiaozhi/ota/"
        $values["server.vision_explain"] | Should Be "http://39.106.188.229/mcp/vision/explain"
        $values["server.http_port"] | Should Be "8003"
    }

    It "renders a caddyfile for the HTTP public IP ingress" {
        $content = Get-XiaozhiCaddyfileContent

        ($content -match "http://39\.106\.188\.229 \{") | Should Be $true
        ($content -match "@websocket") | Should Be $true
        ($content -match "reverse_proxy @websocket 127\.0\.0\.1:18000") | Should Be $true
        ($content -match "@vision") | Should Be $true
        ($content -match "reverse_proxy @vision 127\.0\.0\.1:18003") | Should Be $true
        ($content -match "@xiaozhi") | Should Be $true
        ($content -match "reverse_proxy @xiaozhi 127\.0\.0\.1:18002") | Should Be $true
        ($content -match "reverse_proxy 127\.0\.0\.1:18002") | Should Be $true
    }

    It "renders a subdomain ingress site block for future services" {
        $content = Get-SubdomainIngressCaddySiteBlock -HostName "api.tongyimoheai.top" -Upstream "127.0.0.1:18100"

        ($content -match "api\.tongyimoheai\.top") | Should Be $true
        ($content -match "reverse_proxy 127\.0\.0\.1:18100") | Should Be $true
    }

    It "renders a ragflow subdomain ingress block on the unified root domain" {
        $content = Get-RagflowIngressCaddySiteBlock -RootDomain "tongyimoheai.top"

        ($content -match "ragflow\.tongyimoheai\.top") | Should Be $true
        ($content -match "reverse_proxy 127\.0\.0\.1:18008") | Should Be $true
    }

    It "renders a unified ingress caddyfile that combines xiaozhi path routing and ragflow subdomain routing" {
        $content = Get-TongyimoheUnifiedIngressCaddyfileContent -RootDomain "tongyimoheai.top"

        ($content -match "http://39\.106\.188\.229 \{") | Should Be $true
        ($content -match "ragflow\.tongyimoheai\.top \{") | Should Be $true
        ($content -match "/xiaozhi/v1/\*") | Should Be $true
        ($content -match "reverse_proxy 127\.0\.0\.1:18008") | Should Be $true
    }

    It "returns the expected tunnel health probe configuration" {
        $probe = Get-XiaozhiTunnelHealthProbeConfig

        $probe.ProcessNeedle | Should Be "127.0.0.1:18000:127.0.0.1:8000"
        $probe.PublicOtaUrl | Should Be "http://39.106.188.229/xiaozhi/ota/"
        $probe.PublicOtaHealthySubstring | Should Be "OTA接口运行正常"
        $probe.LocalOtaUrl | Should Be "http://127.0.0.1:8002/xiaozhi/ota/"
        $probe.LocalVisionUrl | Should Be "http://127.0.0.1:8003/mcp/vision/explain"
        $probe.LocalWebsocketUrl | Should Be "http://127.0.0.1:8000/xiaozhi/v1/"
    }

    It "returns the expected remote loopback probe configuration" {
        $probe = Get-XiaozhiTunnelRemoteProbeConfig

        $probe.ServerHost | Should Be "39.106.188.229"
        $probe.User | Should Be "admin"
        $probe.KeyPath | Should Be "C:\Users\lishuaishuai\.ssh\xiaozhi_cloud_tunnel_ed25519"
        $probe.KnownHostsPath | Should Be "C:\Users\lishuaishuai\.ssh\known_hosts_xiaozhi_cloud"
        $probe.RemoteOtaUrl | Should Be "http://127.0.0.1:18002/xiaozhi/ota/"
        $probe.RemoteVisionUrl | Should Be "http://127.0.0.1:18003/mcp/vision/explain"
        $probe.RemoteOtaHealthySubstring | Should Be "OTA接口运行正常"
        $probe.RemoteVisionHealthySubstring | Should Be "MCP Vision 接口运行正常"
    }
}
