"""内网穿透工具"""

import re
import sys
import uuid
import time
import shlex
import queue
import shutil
import tarfile
import secrets
import platform
import threading
import traceback
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.env_manager import pip_install
from sd_webui_all_in_one.downloader import download_file
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR


logger = get_logger(
    name="Tunnel",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class TunnelManager:
    """内网穿透工具

    Attributes:
        workspace (Path | str): 工作区路径
        port (int): 要进行端口映射的端口
    """

    def __init__(self, workspace: Path | str, port: int) -> None:
        """内网穿透工具初始化

        Args:
            workspace (Path | str): 工作区路径
            port (int): 要进行端口映射的端口
        """
        self.workspace = Path(workspace)
        self.port = port

    def ngrok(self, ngrok_token: str | None = None) -> str | None:
        """使用 Ngrok 内网穿透

        Args:
            ngrok_token (str | None): Ngrok 账号 Token
        Returns:
            (str | None): Ngrok 内网穿透生成的访问地址
        """
        if ngrok_token is None:
            logger.warning("缺少 Ngrok Token, 取消启动 Ngrok 内网穿透")
            return None
        logger.info("启动 Ngrok 内网穿透")
        try:
            from pyngrok import conf, ngrok
        except Exception as _:
            try:
                pip_install("pyngrok")
                from pyngrok import conf, ngrok
            except Exception as e:
                logger.error("安装 Ngrok 内网穿透模块失败: %s", e)
                return None

        try:
            conf.get_default().auth_token = ngrok_token
            conf.get_default().monitor_thread = False
            ssh_tunnels = ngrok.get_tunnels(conf.get_default())
            if len(ssh_tunnels) == 0:
                ssh_tunnel = ngrok.connect(self.port, bind_tls=True)
                logger.info("Ngrok 内网穿透启动完成")
                return ssh_tunnel.public_url
            else:
                logger.info("Ngrok 内网穿透启动完成")
                return ssh_tunnels[0].public_url
        except Exception as e:
            logger.error("启动 Ngrok 内网穿透时出现了错误: %s", e)
            return None

    def cloudflare(self) -> str | None:
        """使用 CloudFlare 内网穿透

        Returns:
            (str | None): CloudFlare 内网穿透生成的访问地址
        """
        logger.info("启动 CloudFlare 内网穿透")
        try:
            from pycloudflared import try_cloudflare
        except Exception as _:
            try:
                pip_install("pycloudflared")
                from pycloudflared import try_cloudflare
            except Exception as e:
                logger.error("安装 CloudFlare 内网穿透失败: %s", e)
                return None

        try:
            tunnel_url = try_cloudflare(self.port).tunnel
            logger.info("CloudFlare 内网穿透启动完成")
            return tunnel_url
        except Exception as e:
            logger.error("启动 CloudFlare 内网穿透时出现了错误: %s", e)
            return None

    def gradio(self) -> str | None:
        """使用 Gradio 进行内网穿透

        Returns:
            (str | None): 使用内网穿透得到的访问地址, 如果启动内网穿透失败则不返回地址
        """
        logger.info("启动 Gradio 内网穿透")
        try:
            from gradio_tunneling.main import setup_tunnel
        except Exception as _:
            try:
                pip_install("gradio-tunneling")
                from gradio_tunneling.main import setup_tunnel
            except Exception as e:
                logger.error("安装 Gradio Tunneling 内网穿透时出现了错误: %s", e)
                return None

        try:
            tunnel_url = setup_tunnel(
                local_host="127.0.0.1",
                local_port=self.port,
                share_token=secrets.token_urlsafe(32),
                share_server_address=None,
            )
            logger.info("Gradio 内网穿透启动完成")
            return tunnel_url
        except Exception as e:
            logger.error("启动 Gradio 内网穿透时出现错误: %s", e)
            return None

    def gen_key(self, path: Path | str) -> bool:
        """生成 SSH 密钥

        Args:
            path (str | Path): 生成 SSH 密钥的路径
        Returns:
            bool: 生成成功时返回`True`
        """
        path = Path(path) if not isinstance(path, Path) and path is not None else path
        try:
            arg_string = f'ssh-keygen -t rsa -b 4096 -N "" -q -f {path.as_posix()}'
            args = shlex.split(arg_string)
            subprocess.run(args, check=True)
            path.chmod(0o600)
            return True
        except Exception as e:
            logger.error("生成 SSH 密钥失败: %s", e)
            return False

    def ssh_tunnel(
        self,
        launch_args: list,
        host_pattern: re.Pattern[str],
        line_limit: int,
    ) -> str | None:
        """使用 SSH 进行内网穿透

        基础 SSH 命令为: `ssh -o StrictHostKeyChecking=no -i <ssh_path>`

        Args:
            launch_args (list): 启动 SSH 内网穿透的参数
            host_pattern (re.Pattern[str]): 用于匹配内网穿透地址的正则表达式
            line_limit (int): 内网穿透地址所在的输出行数
        Returns:
            (str | None): 内网穿透地址
        """
        ssh_name = "id_rsa"
        ssh_path = self.workspace / ssh_name

        if not ssh_path.exists():
            if not self.gen_key(ssh_path):
                tmp = TemporaryDirectory()
                ssh_path = Path(tmp.name) / ssh_name
                self.gen_key(ssh_path)

        command = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-i",
            ssh_path.as_posix(),
        ] + launch_args
        if sys.platform == "win32":
            # 在 Windows 平台上不使用 shlex 处理成字符串
            command_to_exec = command
        else:
            # 把列表转换为字符串, 避免 subprocss 只把使用列表第一个元素作为命令
            command_to_exec = shlex.join(command) if isinstance(command, list) else command

        tunnel = subprocess.Popen(
            command_to_exec,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )

        output_queue = queue.Queue()
        lines = []

        def _read_output():
            for line in iter(tunnel.stdout.readline, ""):
                output_queue.put(line)
            tunnel.stdout.close()

        thread = threading.Thread(target=_read_output)
        thread.daemon = True
        thread.start()

        for _ in range(line_limit):
            try:
                line = output_queue.get(timeout=10)
                lines.append(line)
                if line.startswith("Warning"):
                    print(line, end="")

                url_match = host_pattern.search(line)
                if url_match:
                    return url_match.group("url")
            except queue.Empty:
                logger.error("未捕获到指定输出, 输出内容列表: %s", lines)
                break
            except Exception as e:
                logger.error("运行 SSH 进程时发生错误: %s", e)
                break

        return None

    def localhost_run(self) -> str | None:
        """使用 localhost.run 进行内网穿透

        Returns:
            return (str|None): 使用内网穿透得到的访问地址, 如果启动内网穿透失败则不返回地址
        """
        logger.info("启动 localhost.run 内网穿透")
        urls = self.ssh_tunnel(
            launch_args=["-R", f"80:127.0.0.1:{self.port}", "localhost.run"],
            host_pattern=re.compile(r"(?P<url>https?://\S+\.lhr\.life)"),
            line_limit=27,
        )
        if urls is not None:
            logger.info("localhost.run 内网穿透启动完成")
            return urls
        logger.error("启动 localhost.run 内网穿透失败")
        return None

    def remote_moe(self) -> str | None:
        """使用 remote.moe 进行内网穿透

        Returns:
            return (str|None): 使用内网穿透得到的访问地址, 如果启动内网穿透失败则不返回地址
        """
        logger.info("启动 remote.moe 内网穿透")
        urls = self.ssh_tunnel(
            launch_args=["-R", f"80:127.0.0.1:{self.port}", "remote.moe"],
            host_pattern=re.compile(r"(?P<url>https?://\S+\.remote\.moe)"),
            line_limit=10,
        )
        if urls is not None:
            logger.info("remote.moe 内网穿透启动完成")
            return urls
        logger.error("启动 remote.moe 内网穿透失败")
        return None

    def pinggy_io(self) -> str | None:
        """使用 pinggy.io 进行内网穿透

        Returns:
            return (str|None): 使用内网穿透得到的访问地址, 如果启动内网穿透失败则不返回地址
        """
        logger.info("启动 pinggy.io 内网穿透")
        urls = self.ssh_tunnel(
            launch_args=["-p", "443", f"-R0:127.0.0.1:{self.port}", "free.pinggy.io"],
            host_pattern=re.compile(r"(?P<url>https?://\S+\.pinggy\.link)"),
            line_limit=10,
        )
        if urls is not None:
            logger.info("pinggy.io 内网穿透启动完成")
            return urls
        logger.error("启动 pinggy.io 内网穿透失败")
        return None

    def get_latest_zrok_release(self) -> list[str] | None:
        """获取最新的 Zrok 发行内容下载列表

        Returns:
            (list[str] | None): 获取到的发行版下载列表 (`[<文件名>, <下载链接>]`)
        """
        import requests

        url = "https://api.github.com/repos/openziti/zrok/releases/latest"
        data = {
            "Accept": "application/vnd.github+json",
        }
        logger.info("获取 Zrok 发行版本列表")
        response = requests.get(url=url, data=data)
        res = response.json()
        if response.status_code < 200 or response.status_code > 300:
            logger.info("获取 Zrok 发行版本列表失败")
            return None

        file_list = []
        for i in res.get("assets"):
            file_list.append([i.get("name"), i.get("browser_download_url")])
        return file_list

    def get_appropriate_zrok_package(self, packages: list[str]) -> tuple[str, str] | None:
        """获取适合当前平台的 Zrok 版本

        Args:
            packages (list[str]): 发行版下载列表
        Returns:
            (tuple[str, str] | None): 文件名和下载链接
        """

        def _get_current_platform_and_arch() -> tuple[str, str]:
            _arch = platform.machine()
            _platform = sys.platform
            _platform = _platform.replace("win32", "windows").replace("cygwin", "windows").replace("linux2", "linux")
            _arch = _arch.replace("x86_64", "amd64").replace("AMD64", "amd64").replace("aarch64", "arm64").replace("armv7l", "armv7")
            return _platform, _arch

        zrok_package_name_pattern = r"""
            ^
            (?P<software>[\w]+?)                        # 软件名
            _
            (?P<version>[\d.]+)                         # 版本号 (数字和点)
            _
            (?P<platform>[\w]+?)                        # 系统类型
            _
            (?P<arch>[\w]+?)                            # 架构
            \.
            (?P<extension>[a-z0-9]+(?:\.[a-z0-9]+)?)    # 扩展名 (支持多级扩展)
            $
        """

        # 编译正则表达式 (忽略大小写, 详细模式)
        zrok_name_parse_regex = re.compile(zrok_package_name_pattern, re.VERBOSE | re.IGNORECASE)

        current_platform, current_arch = _get_current_platform_and_arch()

        for p, url in packages:
            match = zrok_name_parse_regex.match(p)
            if match:
                groups = match.groupdict()
                support_arch = groups.get("arch")
                support_platform = groups.get("platform")
                if current_platform == support_platform and support_arch == current_arch:
                    logger.info("找到合适 Zrok 版本: %s", p)
                    return p, url

        logger.error("未找到适合当前平台的 Zrok")
        return None, None

    def install_zrok(self) -> Path | None:
        """安装 Zrok

        Returns:
            (Path | None): Zrok 可执行文件路径, 安装失败时则返回`None`
        """
        if sys.platform == "win32":
            bin_extension_name = ".exe"
        else:
            bin_extension_name = ""

        zrok_bin = self.workspace / f"zrok{bin_extension_name}"
        if zrok_bin.is_file():
            try:
                run_cmd([zrok_bin.as_posix(), "version"], live=False)
                logger.info("Zrok 已安装")
                return zrok_bin
            except Exception as _:
                pass

        logger.info("安装 Zrok 中")
        if zrok_bin.exists():
            shutil.move(zrok_bin, zrok_bin.parent / f"zrok_{uuid.uuid4()}")

        release = self.get_latest_zrok_release()
        if release is None:
            logger.error("获取 Zrok 发行版信息失败, 无法安装 Zrok")
            return None

        package_name, download_url = self.get_appropriate_zrok_package(release)
        if package_name is None:
            return None

        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            zrok_archive_file = download_file(
                url=download_url,
                path=tmp_dir,
                save_name=package_name,
            )
            if zrok_archive_file is None:
                logger.error("Zrok 安装包下载失败")
                return None
            try:
                with tarfile.open(zrok_archive_file, "r:gz") as tar:
                    tar.extractall(path=tmp_dir)
                zrok_bin_in_tmp_dir = tmp_dir / f"zrok{bin_extension_name}"
                shutil.move(zrok_bin_in_tmp_dir, zrok_bin)
                logger.info("Zrok 安装成功")
                return zrok_bin
            except Exception as e:
                traceback.print_exc()
                logger.error("Zrok 安装失败: %s", e)
                return None

    def zrok(self, zrok_token: str | None = None) -> str | None:
        """启动 Zrok 内网穿透

        Args:
            zrok_token (str | None): Zrok Token
        Returns:
            (str | None): Zrok 内网穿透地址
        """
        if zrok_token is None:
            logger.warning("缺少 Zrok Token, 取消启动 Zrok 内网穿透")
            return None

        logger.info("启动 Zrok 内网穿透中")
        zrok_bin = self.install_zrok()
        if zrok_bin is None:
            logger.error("启动 Zrok 内网穿透失败")
            return None

        logger.info("初始化 Zrok 配置")
        try:
            run_cmd([zrok_bin.as_posix(), "disable"], live=False)
        except Exception as _:
            pass

        try:
            run_cmd([zrok_bin.as_posix(), "enable", zrok_token])
            logger.info("Zrok 配置初始化完成")
        except Exception as e:
            logger.error("初始化 Zrok 配置失败, 无法使用 Zrok 内网穿透: %s", e)
            return None

        host_pattern = re.compile(r"(?P<url>https?://\S+\.share\.zrok\.io)")

        command = [zrok_bin.as_posix(), "share", "public", str(self.port), "--headless"]
        if sys.platform == "win32":
            # 在 Windows 平台上不使用 shlex 处理成字符串
            command_to_exec = command
        else:
            # 把列表转换为字符串, 避免 subprocss 只把使用列表第一个元素作为命令
            command_to_exec = shlex.join(command) if isinstance(command, list) else command

        tunnel = subprocess.Popen(
            command_to_exec,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )

        output_queue = queue.Queue()
        buffer = ""  # 缓冲不完整的行

        def _read_output():
            nonlocal buffer
            for char in iter(lambda: tunnel.stdout.read(1), ""):
                buffer += char
                # 遇到换行符时处理一行
                if char in ("\n", "\r"):
                    output_queue.put(buffer)
                    url_match = host_pattern.search(buffer)
                    if url_match:
                        output_queue.put(("URL", url_match.group("url")))
                    buffer = ""
            tunnel.stdout.close()

        thread = threading.Thread(target=_read_output)
        thread.daemon = True
        thread.start()

        start_ts = time.time()
        while time.time() - start_ts < 60:
            try:
                item = output_queue.get(timeout=1)
                if isinstance(item, tuple) and item[0] == "URL":
                    logger.info("Zrok 内网穿透启动完成")
                    return item[1]
            except queue.Empty:
                if tunnel.poll() is not None:
                    break

        logger.error("启动 Zrok 内网穿透失败")
        return None

    def start_tunnel(
        self,
        use_ngrok: bool | None = False,
        ngrok_token: str | None = None,
        use_cloudflare: bool | None = False,
        use_remote_moe: bool | None = False,
        use_localhost_run: bool | None = False,
        use_gradio: bool | None = False,
        use_pinggy_io: bool | None = False,
        use_zrok: bool | None = False,
        zrok_token: str | None = None,
        message: str | None = None,
    ) -> dict[str, str]:
        """启动内网穿透

        Args:
            use_ngrok (bool | None): 启用 Ngrok 内网穿透
            ngrok_token (str | None): Ngrok 账号 Token
            use_cloudflare (bool | None): 启用 CloudFlare 内网穿透
            use_remote_moe (bool | None): 启用 remote.moe 内网穿透
            use_localhost_run (bool | None): 使用 localhost.run 内网穿透
            use_gradio (bool | None): 使用 Gradio 内网穿透
            use_pinggy_io (bool | None): 使用 pinggy.io 内网穿透
            use_zrok (bool | None): 使用 Zrok 内网穿透
            zrok_token (str | None): Zrok 账号 Token
            message (str | None): 描述信息
        Returns:
            (dict[str, str]): 内网穿透地址
        """

        if any(
            [
                use_cloudflare,
                use_ngrok and ngrok_token,
                use_remote_moe,
                use_localhost_run,
                use_gradio,
                use_pinggy_io,
                use_zrok,
            ]
        ):
            logger.info("启动内网穿透")
        else:
            return

        cloudflare_url = self.cloudflare() if use_cloudflare else None
        ngrok_url = self.ngrok(ngrok_token) if use_ngrok and ngrok_token else None
        remote_moe_url = self.remote_moe() if use_remote_moe else None
        localhost_run_url = self.localhost_run() if use_localhost_run else None
        gradio_url = self.gradio() if use_gradio else None
        pinggy_io_url = self.pinggy_io() if use_pinggy_io else None
        zrok_url = self.zrok(zrok_token) if use_zrok and zrok_token else None

        logger.info("http://127.0.0.1:%s 的内网穿透地址", self.port)
        print("==================================================================================")
        if message is not None:
            print(f"{message}")
        print(f":: CloudFlare: {cloudflare_url}")
        print(f":: Ngrok: {ngrok_url}")
        print(f":: remote.moe: {remote_moe_url}")
        print(f":: localhost_run: {localhost_run_url}")
        print(f":: Gradio: {gradio_url}")
        print(f":: pinggy.io: {pinggy_io_url}")
        print(f":: Zrok: {zrok_url}")
        print("==================================================================================")
        return {
            "cloudflare": cloudflare_url,
            "ngrok": ngrok_url,
            "remote_moe": remote_moe_url,
            "localhost_run": localhost_run_url,
            "gradio": gradio_url,
            "pinggy_io": pinggy_io_url,
            "zrok": zrok_url,
        }
