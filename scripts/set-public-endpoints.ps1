param(
    [Alias("Domain")]
    [string]$PublicHost = "39.106.188.229",
    [ValidateSet("http", "https")]
    [string]$HttpScheme = "http",
    [ValidateSet("ws", "wss")]
    [string]$WebSocketScheme = "ws",
    [string]$DbContainer = "xiaozhi-esp32-server-db",
    [string]$ServerContainer = "xiaozhi-esp32-server",
    [string]$MysqlPassword = "123456"
)

$ErrorActionPreference = "Stop"

Import-Module (Join-Path $PSScriptRoot "lib\XiaozhiPublicExposure.psm1") -Force

function Invoke-Db {
    param([string]$Sql)

    $output = docker exec -e "MYSQL_PWD=$MysqlPassword" $DbContainer mysql -uroot -D xiaozhi_esp32_server -N -B -e $Sql 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ($output -join [Environment]::NewLine)
    }

    $output
}

$values = Get-XiaozhiPublicEndpointValues -PublicHost $PublicHost -HttpScheme $HttpScheme -WebSocketScheme $WebSocketScheme
$existingCodes = @{}
$rows = Invoke-Db -Sql "select param_code from sys_params where param_code like 'server.%';"
foreach ($row in $rows) {
    if (-not [string]::IsNullOrWhiteSpace($row)) {
        $existingCodes[$row.Trim()] = $true
    }
}

$maxIdRaw = Invoke-Db -Sql "select ifnull(max(id), 0) from sys_params;"
$nextId = [int64]($maxIdRaw | Select-Object -First 1)

foreach ($item in $values.GetEnumerator()) {
    $escapedValue = $item.Value.Replace("'", "''")
    $escapedCode = $item.Key.Replace("'", "''")
    if ($existingCodes.ContainsKey($item.Key)) {
        $sql = "update sys_params set param_value = '$escapedValue' where param_code = '$escapedCode';"
    }
    else {
        $nextId++
        $valueType = if ($item.Key -eq "server.http_port") { "number" } else { "string" }
        $remark = switch ($item.Key) {
            "server.vision_explain" { "Public vision endpoint distributed to devices" }
            "server.http_port" { "HTTP service port for the vision endpoint" }
            default { "Public endpoint value written by Codex" }
        }
        $escapedRemark = $remark.Replace("'", "''")
        $sql = "insert into sys_params (id, param_code, param_value, value_type, param_type, remark) values ({0}, '{1}', '{2}', '{3}', 1, '{4}');" -f $nextId, $escapedCode, $escapedValue, $valueType, $escapedRemark
    }
    Invoke-Db -Sql $sql | Out-Null
}

docker restart $ServerContainer | Out-Null
Start-Sleep -Seconds 5

$codes = ($values.Keys | ForEach-Object { "'" + $_ + "'" }) -join ","
Invoke-Db -Sql "select param_code, param_value from sys_params where param_code in ($codes) order by param_code;"
