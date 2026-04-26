"""Ngrok 内网穿透实现"""

from pathlib import Path

from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.pkg_manager import pip_install
from sd_webui_all_in_one.tunnel.base import BaseTunnel
from sd_webui_all_in_one.mirror_manager import get_auto_pypi_mirror_config


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class NgrokTunnel(BaseTunnel):
    """Ngrok 内网穿透

    使用 pyngrok 库实现 Ngrok 内网穿透.

    Attributes:
        ngrok_token (str):
            Ngrok 账号 Token, 可从 https://dashboard.ngrok.com/get-started/your-authtoken 获取
    """

    def __init__(
        self,
        port: int,
        workspace: Path,
        ngrok_token: str,
    ) -> None:
        """初始化 Ngrok 内网穿透

        Args:
            port (int):
                要进行端口映射的端口
            workspace (Path):
                工作区路径
            ngrok_token (str):
                Ngrok 账号 Token
        """
        super().__init__(port, workspace)
        self.ngrok_token = ngrok_token
        self._ngrok_module = None

    def start(
        self,
    ) -> str:
        """启动 Ngrok 内网穿透

        Returns:
            str: Ngrok 内网穿透生成的访问地址

        Raises:
            RuntimeError: 启动 Ngrok 内网穿透失败时
        """
        logger.info("启动 Ngrok 内网穿透")

        # 导入或安装 pyngrok
        try:
            from pyngrok import conf, ngrok
            from pyngrok.exception import PyngrokError
        except ImportError:
            try:
                custom_env = get_auto_pypi_mirror_config()
                pip_install(
                    "pyngrok",
                    custom_env=custom_env,
                )
                from pyngrok import conf, ngrok
                from pyngrok.exception import PyngrokError
            except (RuntimeError, ImportError) as e:
                logger.error("安装 Ngrok 内网穿透模块失败: %s", e)
                raise RuntimeError(f"安装 Ngrok 内网穿透模块失败: {e}") from e

        # 保存 ngrok 模块引用, 用于后续清理
        self._ngrok_module = ngrok

        try:
            conf.get_default().auth_token = self.ngrok_token
            conf.get_default().monitor_thread = False
            ssh_tunnels = ngrok.get_tunnels(conf.get_default())

            if len(ssh_tunnels) == 0:
                ssh_tunnel = ngrok.connect(self.port, bind_tls=True)
                self._url = ssh_tunnel.public_url
            else:
                self._url = ssh_tunnels[0].public_url

            logger.info("Ngrok 内网穿透启动完成")
            return self._url
        except PyngrokError as e:
            logger.error("启动 Ngrok 内网穿透时出现了错误: %s", e)
            raise RuntimeError(f"启动 Ngrok 内网穿透时出现了错误: {e}") from e

    def stop(
        self,
    ) -> None:
        """停止 Ngrok 内网穿透

        断开所有 Ngrok 隧道连接.
        """
        if self._ngrok_module:
            try:
                logger.info("正在停止 Ngrok 内网穿透")
                self._ngrok_module.disconnect(self._url)
                logger.info("Ngrok 内网穿透已停止")
            except Exception as e:
                logger.error("停止 Ngrok 内网穿透时发生错误: %s", e)

        # 调用父类的 stop 方法（虽然 Ngrok 不使用 subprocess）
        super().stop()
