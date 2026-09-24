# Hermes 多实例接入

Hermes 由用户独立部署，Server 只通过用户登记的 HTTPS 地址调用 OpenAI 兼容接口。Server 不部署 Hermes，也不向设备下发 Hermes API Key。

## 启用

1. 在 Hermes 自己的 Caddy/Nginx 反代上提供 HTTPS，并准备 API Key。
2. 在智控台的“Provider / Hermes”中登记名称、HTTPS 地址、模型、能力 JSON、可选设备 ID、优先级和启用状态。
3. 使用“更新密钥”写入 API Key。列表只显示 `secretRef` 和掩码。
4. 确认 Server 与 manager-api 使用同一 `XIAOZHI_SECRET_MASTER_KEY`。
5. 默认不开启 Metalio 路由；验证前设置 `METALIO_HERMES_ROUTING_ENABLED=1`。需要内网主机时，在 manager-api 和 Server 同时设置 `XIAOZHI_HERMES_ALLOWED_HOSTS=hermes-medical.internal`。

内网地址只能在 Server 和 manager-api 所在的运行环境可达时使用。`192.168.x.x` 等地址不会因为浏览器能访问而自动对公网部署可达；公网智控台仍需要可从 Server 容器访问的 HTTPS 域名、VPN 地址或受控隧道。`http://127.0.0.1:8643` 也不能直接登记，必须先由 Hermes 自己的 HTTPS 反代提供地址，并让 Server 容器信任该反代证书。

设备 hello 声明 `model=metalio-e-ink-4` 后，Server 按设备精确绑定、用户绑定、租户可用实例和优先级选择 Hermes。没有可用实例或 Hermes 返回错误时，当前会话返回服务错误，不切换到普通 Provider。其他设备继续使用原 Provider、知识库和工具链路。

## 回滚

在智控台将 Hermes 实例设为禁用，或移除 `METALIO_HERMES_ROUTING_ENABLED`/设为 `0`，即可停止 Metalio Hermes 路由；旧 Provider、RAGFlow 和知识库无需回滚。数据库迁移 `202609201000` 只新增 `model` 列，回滚代码前保留该列即可。

## 安全边界

- URL 只接受 HTTPS；本机和内网地址必须命中显式 hostname 白名单。
- API Key 仅保存在 `ai_provider_secret` 的密文中，不能出现在设备响应、日志或知识库。
- Hermes 路由请求必须同时匹配当前租户、用户和设备；设备短期会话不会转发给 Hermes。
