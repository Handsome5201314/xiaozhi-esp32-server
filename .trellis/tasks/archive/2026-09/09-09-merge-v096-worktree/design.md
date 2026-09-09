# 整合边界与数据流

- 代码权威：主目录 main；源目录 server-v0.9.6 仅提供尚未移植的工作树补丁。医疗模块与其测试的已提交版本在两边完全一致。
- 模块：MedicalHandler 负责认证、设备归属和请求错误 envelope；SessionStore 负责真实文件、帧序号及 Ogg 输出；ConnectionHandler 以 bind_completed_event 和 need_bind 决定路由。
- 数据流：HTTP finish 请求 → 认证/设备归属 → 整数序号校验 → SessionStore.finish → finish.json 与 recording.ogg。接口保留现有 status/missing 及 error/code/message/request_id。
- 绑定状态权威：Manager API 查询完成设置事件，消息路由最多等候 10 秒；超时不能推断未绑定。真实 need_bind 状态仍触发原绑定流程。
- 包和依赖：沿用 main/xiaozhi-server Python 包及 requirements.txt；不新增依赖，不改数据库及迁移。
- 配置和运行数据：生产容器 xiaozhi-esp32-server-v096-medical 的 data 挂载来自旧目录；模型挂载来自主目录。保密配置不输出，不纳入 Git。
- 回滚：变更前保存目标文件副本与已有脏文件哈希；逐文件补丁整合，不整条 merge，不删除旧目录，不改其他未提交内容。
- 风险：主目录仍为较早上游基线，不能覆盖整个 connection.py；验证须使用主目录代码。使用已有镜像启动隔离测试容器，禁网、无生产数据挂载。
