# 运行数据迁移

用户已明确确认短暂停机与主目录数据备份。数据 Source of Truth 为运行中旧容器挂载的 v0.9.6/data；主目录 data 的三个文件保留在本地私有备份中，不与运行配置混合。

容器没有额外修改的 .py/.yaml 业务文件，沿用现有镜像及其业务行为；不在本次部署较旧 main 基线。保留名称、8000/8003 端口、GPU、模型挂载、xiaozhi-server_default 网络和 always 重启策略；新增 HTTP/WS 服务健康检查。

配置由 main/xiaozhi-server/compose.medical-runtime.yaml 管理；运行密钥仍只在 data/.config.yaml，Docker inspect 和数据备份放入 .git/runtime-backups，禁止纳入提交或输出内容。

流程：停止旧容器确保帧文件及 SQLite 不再写入 → tar 备份与复制到临时 data 目录 → SHA-256 全量比对 → 主目录 data 移到备份 → 临时目录改为 data → 旧容器改名并禁用自动启动 → Compose 创建同名容器 → 健康/认证/文件/GPU检查。

回滚：停止失败的新容器，保留新数据目录并核对是否已产生新录音；旧容器恢复原名/重启策略后从旧数据目录启动。原目录不删除，旧容器保留且禁用自动重启。迁移开始前不存在新业务写入时可直接恢复；产生新数据后必须先保全并回传新录音，不能无检查回切。
