# 知识库同步接口契约

## 目标与边界

Obsidian/Hermes 维护 Markdown 源文件；小智 Server 只读取已挂载的源目录，确定性转换为设备可读的 UTF-8 `.ebook`，并通过短期设备会话分发。胸卡只读同步，Server 不连接 Obsidian、Hermes、飞书或模型 API，也不会向设备返回第三方密钥。

本功能不修改固件或 Hermes 本地工作区。

## 源目录与权限

启用 `METALIO_KNOWLEDGE_ENABLED=1` 后，Server 使用以下目录：

```text
METALIO_KNOWLEDGE_SOURCE_ROOT/<tenant_id>/<user_id>/**/*.md
METALIO_KNOWLEDGE_PUBLISH_ROOT/<scope-hash>/
```

`tenant_id`、`user_id` 只能包含字母、数字、点、下划线和短横线，目录遍历、符号链接和越界路径会被拒绝或跳过。源文件必须是 UTF-8 Markdown。默认单文件上限为 2 MiB，单租户用户总量上限为 50 MiB，可分别通过 `METALIO_KNOWLEDGE_MAX_FILE_BYTES` 和 `METALIO_KNOWLEDGE_MAX_TOTAL_BYTES` 调整，但 Server 会拒绝超过安全上限的配置。

设备会话必须同时满足：

- `knowledge:read`：读取清单和文件；
- `knowledge:ack`：确认文件已接收；
- 会话内的 `tenant_id`、`user_id`、`device_id` 与请求头 `Device-Id` 匹配；
- 如果设置 `METALIO_KNOWLEDGE_PERMISSIONS_JSON`，还必须命中配置的租户、用户、设备绑定。

权限配置示例（不包含任何密钥）：

```json
[{"tenant_id":"tenant-a","user_id":"user-a","device_ids":["AA:BB:CC:DD:EE:01"],"enabled":true}]
```

## Manifest

```http
GET /v1/knowledge/manifest
Authorization: Bearer <short-lived-device-session>
Device-Id: AA:BB:CC:DD:EE:01
```

成功响应的 `data` 包含全局 `revision`、推荐 `chunk_size` 和 `files`。每个 `files[]` 项都包含：

```json
{
  "revision": 3,
  "file_id": "稳定的路径哈希",
  "path": "guides/rounding.md",
  "source_sha256": "原始 Markdown 的 SHA-256",
  "ebook_sha256": "设备文件的 SHA-256",
  "source_size": 1234,
  "ebook_size": 987,
  "updated_at": "2026-09-20T12:00:00+00:00",
  "deleted": false
}
```

删除源文件会发布 tombstone（`deleted: true`），不会立即复用旧 `file_id`。没有变化的文件保留原 revision 和时间戳。首次发布从 revision 1 开始，每个租户用户作用域独立递增。

## 文件读取与断点续传

```http
GET /v1/knowledge/files/{file_id}
Range: bytes=65536-131071
```

默认返回设备 `.ebook`，响应为 `text/plain; charset=utf-8`，支持单段 HTTP Range：

- 完整读取：`200`；
- 分片读取：`206`，返回 `Content-Range`、`Accept-Ranges: bytes` 和 `Content-Length`；
- `ETag` 与 `X-Knowledge-SHA256` 为对应 `.ebook` 的哈希；
- 原始 Markdown 只保存在 Server 的源目录和发布卷中，不通过设备接口返回。

文件只按 `file_id` 查找，不能把路径拼接进文件系统；跨租户、跨用户或跨设备访问不会命中当前作用域。

## Ack

```http
POST /v1/knowledge/ack
Content-Type: application/json

{"file_id":"...","revision":3,"ebook_sha256":"..."}
```

Server 校验当前作用域的版本和哈希后，按设备保存最后确认记录。重复 ack 幂等；版本或哈希不匹配返回 `409`，文件不存在返回 `404`。

## Markdown 转换规则

转换只产生纯文本，不产生 HTML、CSS、JavaScript 或可执行资源：

- 标题、段落保留为文本行；
- 列表统一为 `- `；引用统一为 `| `；
- 粗体、斜体标记去除但保留文字；
- 代码块以 `[代码块: 语言]` 标记，代码内容按普通文本保留；Mermaid、HTML、JavaScript 等不会执行；
- 简单表格转换为 `列1 | 列2` 文本行，分隔线丢弃；
- Obsidian Wiki 链接使用显示文本或目标笔记名；
- 图片、视频和所有 Markdown 链接只保留文本提示，不保留可点击 URL；
- 换行、UTF-8 解码和输出末尾换行固定，重复转换结果字节级一致。

转换、写入和状态更新采用临时文件加原子替换。任一文件解码或转换失败时，旧状态文件和旧 revision 不会被覆盖，本次请求返回错误，新版本不会进入 manifest。

## 状态码

| 状态 | 含义 |
| ---: | --- |
| 200 | 成功或完整文件读取 |
| 206 | Range 分片成功 |
| 400 | JSON、UTF-8、路径或 Range 参数无效 |
| 401 | 缺少、过期或签名无效的设备会话 |
| 403 | 租户、用户、设备或 scope 无权限 |
| 404 | 文件不存在或已删除 |
| 409 | ack 版本/哈希冲突 |
| 413 | 文件数、单文件或总大小超限 |
| 416 | Range 超出文件范围 |
| 503 | 状态或发布文件不可用 |

响应体不会包含堆栈、主机私有路径、Provider/Hermes/飞书/模型 API 密钥。

## 迁移、部署与回滚

1. 在 Server 持久卷创建 `source/<tenant_id>/<user_id>/`，从 Obsidian/Hermes 的导出或同步流程复制 Markdown；不要把 Hermes 凭据写入该目录。
2. 配置 `METALIO_KNOWLEDGE_SOURCE_ROOT`、`METALIO_KNOWLEDGE_PUBLISH_ROOT`、`METALIO_DEVICE_SESSION_SECRET`，并为会话签发 `knowledge:read`、`knowledge:ack` scope。
3. 多租户部署设置 `METALIO_KNOWLEDGE_PERMISSIONS_JSON`，逐项绑定租户、用户和设备；先用测试设备请求 manifest，再启用生产设备。
4. 本功能使用版本化文件状态，不新增 MySQL/Liquibase 表；持久卷中的 `state.json`、原始 `.md` 和 `.ebook` 是回滚所需的迁移资产。部署前备份这三个目录。
5. 回滚时停用 `METALIO_KNOWLEDGE_ENABLED` 或回退 Server 镜像，保留 source/publish 卷；旧版本会继续读取旧 `state.json`，不会把失败转换结果发布给设备。确认旧版本稳定后再清理未被 manifest 引用的临时文件。

## 测试

`main/xiaozhi-server/tests/test_knowledge_sync.py` 覆盖：

- 同一 Markdown 重复转换字节一致；
- manifest 的源文件和 ebook 哈希；
- Range 断点读取和响应哈希；
- ack 正确校验及错误哈希拒绝；
- 租户、用户、设备隔离；
- UTF-8/转换失败保留上一 revision；
- 超大文件拒绝。

运行：

```powershell
python -m pytest main/xiaozhi-server/tests/test_knowledge_sync.py -q
```
