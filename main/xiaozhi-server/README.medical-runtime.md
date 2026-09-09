# 本机医疗录音服务

当前运行配置为 `compose.medical-runtime.yaml`，数据目录为同目录 `data/`。服务沿用本机已有镜像 `xiaozhi-esp32-server:v0.9.6-medical-gpu-bindwait-20260823`，不从远端拉取，不自动构建 main 分支。

## 启动与检查

在仓库根目录执行：

```powershell
docker compose -f main/xiaozhi-server/compose.medical-runtime.yaml config --quiet
docker compose -f main/xiaozhi-server/compose.medical-runtime.yaml up -d --pull never
docker compose -f main/xiaozhi-server/compose.medical-runtime.yaml ps
```

使用外部 Docker 网络 `xiaozhi-server_default`、现有模型 `models/SenseVoiceSmall/model.pt` 和全部可用 GPU。端口为 8000（WebSocket）及 8003（HTTP/医疗接口）。健康检查同时读取两个服务端口；不等同于设备录音到 ASR 的端到端验证。

本地配置、密钥、床位和录音保存在 `data/`，禁止提交。运行配置以此目录为准，不再使用相邻 v0.9.6 工作目录。部署镜像升级是单独任务，不能直接把主目录旧上游基线覆盖到当前容器。

## 2026-09-09 迁移与回退

用户随后要求清理旧目录。已完整归档并校验旧工作目录的 8,261 个文件，删除 `xiaozhi-esp32-server-v0.9.6` worktree 和已停用的旧容器；`server-v0.9.6` 分支仍保留。

私有备份位于仓库 `.git/runtime-backups/20260909-v096-data/`：

- `live-data-before.tar`：停止原容器后备份的完整运行数据。
- `main-data-before/`：主目录迁移前的三个数据文件。
- `container-inspect.json`：原容器完整运行参数，可能包含敏感信息。
- `live-data-hashes.json`、`main-data-hashes.json`：SHA-256 校验清单。
- `old-worktree-before-removal.tar`、`old-worktree-hashes.json`：删除前完整旧目录及校验清单。
- `old-container-final.log`：删除前保存的旧容器日志。

需要恢复旧内容时，从备份解压到独立目录，勿把归档内的 `.git` 工作树指针覆盖进当前仓库。需要回退运行数据时，先停止服务并备份当前 data，确认迁移后产生的录音及元数据已保全、同步，再按归档数据及原容器参数制定恢复操作。归档没有迁移后产生的新数据，不能直接覆盖当前 data。
