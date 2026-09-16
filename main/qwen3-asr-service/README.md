# Qwen3-ASR 本地服务

该服务使用 vLLM 原生 OpenAI 音频转写接口，在独立 GPU 容器中运行
`Qwen/Qwen3-ASR-1.7B`。小智复用现有 `openai` ASR Provider，不需要改管理端前端。

模型权重通过 ModelScope 预下载到命名卷 `xiaozhi-qwen3-asr-cache` 的
`/models/Qwen3-ASR-1.7B`。智控台仍使用标准模型 ID
`Qwen/Qwen3-ASR-1.7B`，本地存储路径不会进入业务配置。

## 启动

```powershell
& main/qwen3-asr-service/Download-Model.ps1
docker compose -p xiaozhi-server -f main/qwen3-asr-service/compose.yaml up -d --build
```

Compose 项目名固定为 `xiaozhi-server`，因此该可选服务会和小智核心服务显示在同一个
Docker Desktop Containers / Apps 项目下；旧版 Compose 也可以继续使用命令中的 `-p` 参数。

运行镜像以本机已有的 vLLM nightly 固定摘要为基础，只补充官方 `audio` extra
所需的 PyAV、SciPy、SoundFile 与 SoXR。首次部署前需要把模型权重放入命名卷；
当前机器已完成该步骤。

`Download-Model.ps1` 是幂等的；已有完整权重时 ModelScope 会复用文件。模型卷被
Compose 声明为外部卷，因此停止或重建服务不会删除模型。

服务健康后，把模型注册到智控台：

```powershell
& main/qwen3-asr-service/Register-Model.ps1
```

该操作是幂等的，只把模型设为“已启用”，不会自动覆盖当前默认 ASR。

## 接口

- 健康检查：`GET http://127.0.0.1:10097/health`
- 转写：`POST http://127.0.0.1:10097/v1/audio/transcriptions`
- 小智容器内部地址：`http://qwen3-asr:8000/v1/audio/transcriptions`

## 回滚

先在智控台把智能体 ASR 切回 `ASR_FunASR`，再停止服务：

```powershell
docker compose -p xiaozhi-server -f main/qwen3-asr-service/compose.yaml stop qwen3-asr
```

停止容器不会删除模型缓存。
