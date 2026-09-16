# 统一多租户运行时

## 迁移开关

服务端设置 `METALIO_DEVICE_SESSION_SECRET`（至少 32 个字符）后，OTA 会为设备返回 15 分钟设备会话令牌，WebSocket 会校验令牌中的租户、用户、设备、Client-Id 和作用域。令牌撤销由 `DeviceSessionAuthenticator.revoke()` 执行；多进程部署应把 token id 同步到共享撤销存储。

设置 `METALIO_UNIFIED_CHECKLIST_ENABLED=1` 并提供 `METALIO_CHECKLIST_BINDINGS_JSON` 可启用迁移期待办入口。JSON 的键是用户 ID，值包含 `app_id`、`app_secret`、`tasklist_guid` 和 `assignee_id`。生产部署应由 manager-api/密钥服务生成该映射，不要把密钥提交到仓库或固件。

统一入口为 `GET /v1/checklist/items`、`POST /v1/checklist/items` 和 `POST /v1/checklist/items/{id}/complete`，要求 `Authorization: Bearer <device-session>` 与匹配的 `Device-Id`。旧 `/b/<token>` 路由保持迁移兼容，可由租户策略关闭。

## 每日总结设备接口

设置 `METALIO_DAILY_SUMMARY_ENABLED=1` 后，设备会话可访问 `GET /v1/daily-summary/today`、
`POST /v1/daily-summary/generate` 和 `POST /v1/daily-summary/ack`。接口要求匹配的
`Device-Id` 与设备会话，并分别使用 `summary:read` / `summary:write` scope。
`METALIO_DAILY_SUMMARY_STORE` 指向服务端持久化文件（默认 `/data/daily-summary.json`）。
17:00 定时任务和总结内容由 Hermes 负责；小智 Server 不自行调度。未注入 Hermes 生成器时，
生成接口返回 503，不会伪造空总结；生产部署应替换为数据库存储
并接入用户绑定的 Hermes 实例。

设备使用带 `summary:read` scope 的短期会话重新完成 WebSocket hello 后，服务会按租户、用户、
设备和日期读取已保存总结并补发 `daily_summary` 消息。旧固定 token/白名单连接没有租户上下文，
不会触发补发。当前 JSON 存储仅适用于单进程迁移验证；多进程生产环境必须接入共享数据库/锁。

## Hermes 工具网关契约

Hermes 通过小智 Server 的 `GET /v1/hermes/tools` 获取当前设备可用工具，使用
`POST /v1/hermes/tools/call` 调用工具。两者都要求设备短期会话和 `tools:call` scope，且
`Device-Id` 必须与会话一致。工具管理器由 Server 侧按会话上下文创建，因此胸卡工具、待办
和医疗数据仍由 Server 做租户隔离；Hermes 不直接连接设备，也不会获得第三方密钥。

Provider/Hermes 地址默认必须为 HTTPS，并拒绝回环、内网、链路本地和云元数据地址；管理员允许的受控地址应通过 resolver 的 allowlist 配置。第三方密钥只写入 manager-api 的 `ai_provider_secret` 密文列，接口只返回 `secretRef` 和掩码。
