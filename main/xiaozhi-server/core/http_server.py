import asyncio
import os
from aiohttp import web
from config.logger import setup_logging
from core.api.ota_handler import OTAHandler
from core.api.vision_handler import VisionHandler
from core.api.medical_handler import MedicalHandler, medical_error_middleware
from core.api.checklist_handler import ChecklistHandler, ChecklistAccessLogger, UnifiedChecklistHandler
from core.api.daily_summary_handler import from_environment as daily_summary_from_environment
from core.api.hermes_tools_handler import HermesToolsHandler
from core.api.quiz_handler import QuizHandler
from core.api.knowledge_sync import from_environment as knowledge_from_environment
from core.security.session import DeviceSessionAuthenticator

TAG = __name__


class SimpleHttpServer:
    def __init__(self, config: dict, websocket_server=None):
        self.config = config
        self.websocket_server = websocket_server
        self.logger = setup_logging()
        self.ota_handler = OTAHandler(config)
        self.vision_handler = VisionHandler(config)
        self.medical_handler = MedicalHandler(config)

    def _get_websocket_url(self, local_ip: str, port: int) -> str:
        """获取websocket地址

        Args:
            local_ip: 本地IP地址
            port: 端口号

        Returns:
            str: websocket地址
        """
        server_config = self.config["server"]
        websocket_config = server_config.get("websocket")

        if websocket_config and "你" not in websocket_config:
            return websocket_config
        else:
            return f"ws://{local_ip}:{port}/xiaozhi/v1/"

    def create_application(self) -> web.Application:
        app = web.Application(middlewares=[medical_error_middleware])
        app.add_routes(
            [
                web.get("/xiaozhi/ota/", self.ota_handler.handle_get),
                web.post("/xiaozhi/ota/", self.ota_handler.handle_post),
                web.options("/xiaozhi/ota/", self.ota_handler.handle_options),
                web.get(
                    "/xiaozhi/ota/download/{filename}",
                    self.ota_handler.handle_download,
                ),
                web.options(
                    "/xiaozhi/ota/download/{filename}",
                    self.ota_handler.handle_options,
                ),
                web.get("/mcp/vision/explain", self.vision_handler.handle_get),
                web.post("/mcp/vision/explain", self.vision_handler.handle_post),
                web.options(
                    "/mcp/vision/explain", self.vision_handler.handle_options
                ),
            ]
        )
        app.add_routes(self.medical_handler.routes())
        checklist = ChecklistHandler.from_environment()
        if checklist is not None:
            app.add_routes(checklist.routes())
        unified_checklist = UnifiedChecklistHandler.from_environment()
        if unified_checklist is not None:
            app.add_routes(unified_checklist.routes())
        daily_summary = daily_summary_from_environment()
        if daily_summary is not None:
            app.add_routes(daily_summary.routes())
        knowledge = knowledge_from_environment(
            self.config["server"].get("auth", {}).get("device_session_secret")
        )
        if knowledge is not None:
            app.add_routes(knowledge.routes())
        if self.websocket_server is not None and os.environ.get("METALIO_QUIZ_ENABLED") == "1":
            secret = self.config["server"].get("auth", {}).get("device_session_secret") or os.environ.get("METALIO_DEVICE_SESSION_SECRET", "")
            if len(secret) < 32:
                raise ValueError("METALIO_DEVICE_SESSION_SECRET is required")
            app.add_routes(QuizHandler(DeviceSessionAuthenticator(secret), self.websocket_server.online_devices.get).routes())
        if self.websocket_server is not None and os.environ.get("METALIO_HERMES_TOOLS_ENABLED") == "1":
            secret = self.config["server"].get("auth", {}).get("device_session_secret") or os.environ.get("METALIO_DEVICE_SESSION_SECRET", "")
            if len(secret) < 32:
                raise ValueError("METALIO_DEVICE_SESSION_SECRET is required")
            app.add_routes(HermesToolsHandler(
                DeviceSessionAuthenticator(secret), self.websocket_server.online_devices.get
            ).routes())
        return app

    async def start(self):
        try:
            server_config = self.config["server"]
            host = server_config.get("ip", "0.0.0.0")
            port = int(server_config.get("http_port", 8003))

            if port:
                app = self.create_application()

                # 运行服务
                runner = web.AppRunner(app)
                await runner.setup()
                site = web.TCPSite(runner, host, port)
                await site.start()

                # 保持服务运行
                while True:
                    await asyncio.sleep(3600)  # 每隔 1 小时检查一次
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"HTTP服务器启动失败: {e}")
            import traceback

            self.logger.bind(tag=TAG).error(f"错误堆栈: {traceback.format_exc()}")
            raise
