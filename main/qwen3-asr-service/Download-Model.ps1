param(
    [string]$ModelId = "Qwen/Qwen3-ASR-1.7B",
    [string]$ModelDirectory = "Qwen3-ASR-1.7B",
    [string]$CacheVolume = "xiaozhi-qwen3-asr-cache",
    [string]$HelperImage = "xiaozhi-esp32-server:v0.9.6-medical-gpu-20260822"
)

$ErrorActionPreference = "Stop"

if ($ModelId -notmatch '^[A-Za-z0-9._/-]+$' -or
    $ModelDirectory -notmatch '^[A-Za-z0-9._-]+$' -or
    $CacheVolume -notmatch '^[A-Za-z0-9._-]+$') {
    throw "Model and volume parameters contain unsupported characters"
}

docker image inspect $HelperImage *> $null
if ($LASTEXITCODE -ne 0) {
    throw "ModelScope helper image is not available: $HelperImage"
}

docker volume inspect $CacheVolume *> $null
if ($LASTEXITCODE -ne 0) {
    docker volume create $CacheVolume | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create model cache volume: $CacheVolume"
    }
}

$downloadCommand = "pip install --no-cache-dir setuptools==80.9.0 && " +
    "modelscope download --model $ModelId --local_dir /models/$ModelDirectory"

docker run --rm `
    --volume "${CacheVolume}:/models" `
    $HelperImage `
    sh -lc $downloadCommand

if ($LASTEXITCODE -ne 0) {
    throw "ModelScope download failed: $ModelId"
}

docker run --rm `
    --volume "${CacheVolume}:/models" `
    $HelperImage `
    sh -lc "test -s /models/$ModelDirectory/model.safetensors.index.json"

if ($LASTEXITCODE -ne 0) {
    throw "Downloaded model files could not be verified"
}

Write-Output "Model ready in volume ${CacheVolume}:/models/$ModelDirectory"
