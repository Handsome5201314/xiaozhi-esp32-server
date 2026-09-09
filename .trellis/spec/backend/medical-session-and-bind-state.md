# 医疗会话结束与绑定等待契约

## 适用范围

医疗录音 finish 路由和设备首次消息等待 Manager API 的流程。来源：09-09-merge-v096-worktree 整合验证。

## Interface

- `POST /v1/sessions/{session_id}/finish`，以及已有 `/medical/v1/` 路由。
- `SessionStore.finish(session_id: str, last_sequence: int) -> FinishResult`。
- `ConnectionHandler._route_message(message)` 等待 `bind_completed_event`，之后读取 `need_bind`。

## 请求与响应

finish 保留 Bearer key、Device-Id 与会话归属校验。`last_sequence` 为整数，`-1` 表示无帧录音；0 及以上为最后帧序号。成功为 `{"status":"completed","missing":[]}`，缺帧为 incomplete 与范围列表；真实文件输出仍归 SessionStore 管理。

## 校验与错误

HTTP 边界拒绝布尔、非整数、小于 -1 的序号，返回 422 / INVALID_REQUEST，错误 envelope 沿用 error/code/message/request_id。无认证为 401，设备不匹配为 403。

绑定查询最多等候 10 秒。超时仅记录 warning 并丢弃当前消息，不设置已完成事件，不推断设备未绑定。事件完成后仍依据真实 need_bind 决定是否播放绑定提示。

## 正常与错误案例

- 空录音 + -1：生成结束记录及 Ogg 文件，返回 completed。
- 有帧 + 最后帧序号：延续原完整性检查。
- -2、true、1.5、"0"、null：422，不生成 finish.json。
- 查询耗时 1.1 秒后完成：首条消息继续正常路由。
- 10 秒仍未完成：丢弃当前消息；之后查询完成，新音频可正常进入队列。

## 测试入口

`tests/test_medical_gateway.py`、`tests/test_medical_session_store.py`、`tests/test_connection_bind_wait.py`。HTTP/WebSocket 使用 aiohttp 测试服务，文件使用真实临时目录。超时恢复测试使用真实 asyncio.Event 和音频队列。

## 易错点

错误：把 API 查询超时当作设备未注册；正确：绑定状态必须来自查询结果。

错误：把旧 worktree 直接当副本删除；正确：先比对本地提交是否已移植、未提交/忽略文件以及运行容器挂载。代码整合时旧目录仍提供运行数据；2026-09-09 获用户停机授权后，数据和挂载已迁至主目录。

## 运行数据与部署权威

当前 data 权威为 `main/xiaozhi-server/data`，运行参数由 `main/xiaozhi-server/compose.medical-runtime.yaml` 管理；操作与回退见同目录 `README.medical-runtime.md`。运行镜像沿用已验证的 v0.9.6 医疗镜像，不代表 main 已合入 v0.9.6 全部上游变化。

源 worktree 与停用的旧容器已按用户后续要求清理；删除前完整归档至 `.git/runtime-backups/20260909-v096-data/old-worktree-before-removal.tar`，并校验全部 8,261 个文件。迁移后产生的数据只在主目录，恢复历史归档前必须保全新数据。任何后续目录清理都要重新核对运行容器挂载与备份，而不能依赖历史目录名称。
