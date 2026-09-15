# 统一多租户运行时

## 迁移开关

服务端设置 `METALIO_DEVICE_SESSION_SECRET`（至少 32 个字符）后，OTA 会为设备返回 15 分钟设备会话令牌，WebSocket 会校验令牌中的租户、用户、设备、Client-Id 和作用域。令牌撤销由 `DeviceSessionAuthenticator.revoke()` 执行；多进程部署应把 token id 同步到共享撤销存储。

设置 `METALIO_UNIFIED_CHECKLIST_ENABLED=1` 并提供 `METALIO_CHECKLIST_BINDINGS_JSON` 可启用迁移期待办入口。JSON 的键是用户 ID，值包含 `app_id`、`app_secret`、`tasklist_guid` 和 `assignee_id`。生产部署应由 manager-api/密钥服务生成该映射，不要把密钥提交到仓库或固件。

统一入口为 `GET /v1/checklist/items`、`POST /v1/checklist/items` 和 `POST /v1/checklist/items/{id}/complete`，要求 `Authorization: Bearer <device-session>` 与匹配的 `Device-Id`。旧 `/b/<token>` 路由保持迁移兼容，可由租户策略关闭。

Provider/Hermes 地址默认必须为 HTTPS，并拒绝回环、内网、链路本地和云元数据地址；管理员允许的受控地址应通过 resolver 的 allowlist 配置。第三方密钥只写入 manager-api 的 `ai_provider_secret` 密文列，接口只返回 `secretRef` 和掩码。
