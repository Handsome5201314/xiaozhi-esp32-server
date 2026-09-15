param(
    [string]$DbContainer = "xiaozhi-esp32-server-db",
    [string]$RedisContainer = "xiaozhi-esp32-server-redis",
    [string]$ServerContainer = "xiaozhi-esp32-server",
    [string]$WebContainer = "xiaozhi-esp32-server-web",
    [string]$MysqlPassword = "123456"
)

$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)

    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

function Invoke-Db {
    param([string]$Sql)

    docker exec $DbContainer mysql -uroot "-p$MysqlPassword" -D xiaozhi_esp32_server -N -B -e $Sql 2>$null
}

function Get-ParamValue {
    param([string]$Code)

    $result = Invoke-Db "select param_value from sys_params where param_code = '$Code' limit 1;"
    if ($null -eq $result) {
        return $null
    }

    if ($result -is [System.Array]) {
        return ($result | Select-Object -First 1).Trim()
    }

    return $result.Trim()
}

function Test-OtaUrl {
    param(
        [string]$Label,
        [string]$Url
    )

    if ([string]::IsNullOrWhiteSpace($Url) -or $Url -eq "null") {
        Write-Host "$Label`t<empty>"
        return
    }

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
        Write-Host "$Label`t$($response.StatusCode)`t$($response.Content)"
    }
    catch {
        Write-Host "$Label`tFAIL`t$($_.Exception.Message)"
    }
}

Write-Section "Docker"
docker ps --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}" |
    Select-String "NAMES|xiaozhi-esp32-server|docker-nginx-1"

$serverOta = Get-ParamValue "server.ota"
$serverWebsocket = Get-ParamValue "server.websocket"
$serverFrontedUrl = Get-ParamValue "server.fronted_url"

Write-Section "Sys Params"
Write-Host "server.fronted_url`t$serverFrontedUrl"
Write-Host "server.websocket`t$serverWebsocket"
Write-Host "server.ota`t$serverOta"

Write-Section "OTA Health"
Test-OtaUrl -Label "loopback" -Url "http://127.0.0.1:8002/xiaozhi/ota/"
Test-OtaUrl -Label "lan" -Url $serverOta

Write-Section "ai_device"
$deviceCount = Invoke-Db "select count(*) from ai_device;"
Write-Host "device_count`t$deviceCount"
$deviceRows = Invoke-Db "select mac_address,auto_update,board,app_version,update_date from ai_device order by update_date desc limit 10;"
if ($deviceRows) {
    $deviceRows | ForEach-Object { Write-Host $_ }
}
else {
    Write-Host "<no bound devices>"
}

Write-Section "ai_ota"
$otaRows = Invoke-Db "select firmware_name,type,version,size,firmware_path,create_date from ai_ota order by create_date desc limit 10;"
if ($otaRows) {
    $otaRows | ForEach-Object { Write-Host $_ }
}
else {
    Write-Host "<no ota records>"
}

Write-Section "Redis Activation Cache"
$activationKeys = docker exec $RedisContainer redis-cli --scan --pattern "ota:activation:*"
if ($activationKeys) {
    foreach ($key in $activationKeys) {
        $value = docker exec $RedisContainer redis-cli GET $key
        Write-Host "$key`t$value"
    }
}
else {
    Write-Host "<no activation cache>"
}

Write-Section "Recent Logs"
Write-Host "[manager-api]"
docker logs --tail 30 $WebContainer 2>&1 | Select-String "server\\.mqtt_gateway|DeviceDao\\.selectList|activation|ota"
Write-Host ""
Write-Host "[xiaozhi-server]"
docker logs --tail 30 $ServerContainer 2>&1 | Select-String "Websocket|OTA|从API读取配置|POST /config/server-base"
