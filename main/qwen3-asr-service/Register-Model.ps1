param(
    [string]$DatabaseContainer = "xiaozhi-esp32-server-db"
)

$ErrorActionPreference = "Stop"

$serviceDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$sqlPath = Join-Path $serviceDirectory "register-model.sql"

docker inspect $DatabaseContainer *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Database container is not available: $DatabaseContainer"
}

Get-Content -Raw -LiteralPath $sqlPath |
    docker exec -i $DatabaseContainer sh -lc 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"'

if ($LASTEXITCODE -ne 0) {
    throw "Failed to register ASR_Qwen3ASRLocal"
}

$verificationSql = @"
SELECT id, model_name, is_enabled, is_default
FROM ai_model_config
WHERE id = 'ASR_Qwen3ASRLocal';
"@

$verification = $verificationSql |
    docker exec -i $DatabaseContainer sh -lc 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -N'

if ($LASTEXITCODE -ne 0) {
    throw "Model registration could not be verified"
}

if (-not ($verification -match '^ASR_Qwen3ASRLocal\s')) {
    throw "Registered model was not returned by the verification query"
}

$verification
