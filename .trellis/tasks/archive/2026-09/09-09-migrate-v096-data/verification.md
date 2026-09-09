# 迁移结果

- 用户明确确认短暂停机后执行。源目录 6,593 个文件先停止写入，再 tar 备份、复制、SHA-256 全量比对，完全一致。
- 主目录原三个数据文件移动至 `.git/runtime-backups/20260909-v096-data/main-data-before`，哈希全部一致。
- 新容器挂载 `xiaozhi-esp32-server/main/xiaozhi-server/data` 和该主目录下的原模型。当前无运行中容器挂载旧 worktree。
- 所用镜像 ID、环境、启动命令、端口、重启策略、GPU 预留和网络与原容器一致。Docker Compose 将 GPU Options 从空对象序列化为 null，两者均表示没有额外选项；其余 GPU 字段一致，实际 CUDA 可用且设备数为 1。
- 新容器状态 running / healthy，未发生自动重启；原容器 stopped / restart=no，名称为 xiaozhi-v096-before-data-move-20260909。
- HTTP OTA 与 WebSocket 服务 HTTP 检查均 200；医疗接口携带现有认证返回 200，床位响应 SHA-256 与迁移前一致；未认证请求仍为 401。
- 迁移后再次核验 6,593 个原运行数据文件全部一致；主目录原三个文件、278 个既有工作文件全部保全。
- 从停机后开始快照到完成恢复验证约 57 秒（观测上限，不代表精确不可用时长）。
- 启动日志未发现 ERROR 或 Python traceback。未发起真实患者录音、未验证完整设备至 ASR 推理链路。
- 持久部署入口为 `main/xiaozhi-server/compose.medical-runtime.yaml`，说明为同目录 `README.medical-runtime.md`。运行密钥和私有备份均被 Git 忽略。
- 本次未升级 main 或生产镜像，未删除旧 worktree 和回退容器。
