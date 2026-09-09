# v0.9.6 医疗录音接口整合实施计划

> **Goal:** 将 ESP32 医疗录音 Gateway 接入 v0.9.6 Docker Server，同时保持原有实时对话协议不变。

**Architecture:** `SimpleHttpServer` 继续承载 HTTP/OTA/视觉接口，并新增医疗会话路由。医疗录音使用独立的 `data/medical` 存储和会话协议；WebSocket 实时对话仍只走 `WebSocketServer` 的 `/xiaozhi/v1/`。

**Tech Stack:** Python 3.10、aiohttp、websockets、pytest、Docker。

---

### Task 1: 引入医疗领域模块

**Files:**
- Create: `main/xiaozhi-server/core/medical/{config.py,frame.py,ogg.py,session_store.py}`
- Create: `main/xiaozhi-server/data/medical/beds.json`

- [ ] 复制现有 Gateway 的床位校验、帧编解码、Ogg Opus 落盘和幂等会话存储逻辑，去除 FastAPI 依赖。
- [ ] 保证会话目录只能位于 `data/medical/sessions`，禁止路径逃逸。

### Task 2: 先写医疗 HTTP/WebSocket 契约测试

**Files:**
- Create: `main/xiaozhi-server/tests/test_medical_gateway.py`

- [ ] 测试床位列表、禁用床位拒绝、会话创建幂等、音频帧 ACK、结束后生成 Ogg。
- [ ] 测试路径同时支持 `/v1/...` 和 `/medical/v1/...`，以兼容已刷入固件和未来新客户端。

### Task 3: 接入 SimpleHttpServer

**Files:**
- Create: `main/xiaozhi-server/core/api/medical_handler.py`
- Modify: `main/xiaozhi-server/core/http_server.py`

- [ ] 使用 aiohttp 实现 JSON 错误 envelope、HTTP 创建/结束会话、WebSocket 二进制帧 ACK。
- [ ] 从配置读取 `medical.beds_file` 和 `medical.data_dir`，默认值分别为 `data/medical/beds.json`、`data/medical/sessions`。
- [ ] 只在 HTTP 服务中新增路由，不修改实时 WebSocket Server。

### Task 4: Docker 验证

**Files:**
- Modify: `main/xiaozhi-server/data/.config.yaml`

- [ ] 构建 `xiaozhi-esp32-server:v0.9.6-medical-test`。
- [ ] 用 `8100/8103` 运行独立测试容器，验证原 HTTP 健康响应和医疗接口。
- [ ] 运行单元测试、`git diff --check`、Docker 日志检查后再报告结果。
