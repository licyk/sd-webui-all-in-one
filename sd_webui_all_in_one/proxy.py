import os
import sys
import re
import configparser
from pathlib import Path

from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.cmd import run_cmd

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def get_windows_proxy_address() -> str | None:
    """获取 Windows 系统上的代理配置

    Returns:
        (str | None):
            代理地址
    """
    import winreg

    proxy_config_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, proxy_config_path, 0, winreg.KEY_READ) as reg:
            proxy_enable: int = winreg.QueryValueEx(reg, "ProxyEnable")[0]
            proxy_server: str = winreg.QueryValueEx(reg, "ProxyServer")[0]
    except Exception as e:
        logger.debug("获取 Windows 上的代理地址出现错误: %s", e)
        return None

    if proxy_enable != 1:
        return None

    # 匹配 http 或 https 的情况
    http_match = re.search(r"(?:http|https)=([^;]+)", proxy_server)
    if http_match:
        proxy_value = http_match.group(1)
        # 去除可能存在的协议前缀并统一加 http://
        proxy_value = proxy_value.replace("http://", "").replace("https://", "")
        return f"http://{proxy_value}"

    #  匹配 socks 的情况
    socks_match = re.search(r"socks=([^;]+)", proxy_server)
    if socks_match:
        proxy_value = socks_match.group(1)
        # 去除前缀并加 socks://
        proxy_value = proxy_value.replace("http://", "").replace("https://", "").replace("socks://", "")
        return f"socks://{proxy_value}"

    # 直接是 IP:PORT 形式
    # 先清理掉可能存在的简单协议头
    clean_value = proxy_server.replace("http://", "").replace("https://", "").replace("socks://", "")
    return f"http://{clean_value}"


def get_linux_proxy_address() -> str | None:
    """获取 Linux 系统上的代理配置

    Returns:
        (str | None):
            代理地址
    """
    try:
        mode = run_cmd(["gsettings", "get", "org.gnome.system.proxy", "mode"], live=False).strip().replace("'", "").replace('"', "")
        if mode == "manual":
            http_host = run_cmd(["gsettings", "get", "org.gnome.system.proxy.http", "host"], live=False).strip().replace("'", "").replace('"', "")
            http_port = run_cmd(["gsettings", "get", "org.gnome.system.proxy.http", "port"], live=False).strip()
            if http_host and http_port and http_port != "0":
                return f"http://{http_host}:{http_port}"

            socks_host = run_cmd(["gsettings", "get", "org.gnome.system.proxy.socks", "host"], live=False).strip().replace("'", "").replace('"', "")
            socks_port = run_cmd(["gsettings", "get", "org.gnome.system.proxy.socks", "port"], live=False).strip()
            if socks_host and socks_port and socks_port != "0":
                return f"socks://{socks_host}:{socks_port}"
    except RuntimeError as e:
        logger.debug("获取 Linux (Gnome) 上的代理地址出现错误: %s", e)

    kde_config_path = Path("~/.config/kioslaverc").expanduser()
    config = configparser.ConfigParser(interpolation=None)
    if not kde_config_path.is_file():
        return None

    try:
        with open(kde_config_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 构造一个虚拟的头部来包裹那些不在 section 里的配置项项
        fake_content = "[GLOBAL]\n" + content
        config.read_string(fake_content)

        # 检查目标节 [Proxy Settings]
        section_name = "Proxy Settings"
        if not config.has_section(section_name):
            return None

        section = config[section_name]

        # ProxyType=1 代表手动代理
        if section.get("ProxyType") != "1":
            return None

        # 获取代理配置
        # 依次尝试 httpProxy, httpsProxy, socksProxy
        raw_proxy = section.get("httpProxy") or section.get("httpsProxy") or section.get("socksProxy")
        if not raw_proxy:
            return None

        # 判断最终应该返回的协议头
        if section.get("httpProxy") or section.get("httpsProxy"):
            target_proto = "http"
        else:
            target_proto = "socks"

        # 格式化地址 (处理 "http://127.0.0.1 10808" 这种带空格的情况)
        # 先去掉协议头
        clean_value = re.sub(r"^(https?|socks)://", "", raw_proxy).strip()
        # 将空格替换为冒号 (127.0.0.1 10808 -> 127.0.0.1:10808)
        clean_value = clean_value.replace(" ", ":")

        if clean_value:
            return f"{target_proto}://{clean_value}"

    except Exception as e:
        logger.error("获取 Linux (KDE) 上的代理地址出现错误: %s", e)


def get_macos_proxy_address() -> str | None:
    """获取 MacOS 系统上的代理配置

    Returns:
        (str | None):
            代理地址
    """
    try:
        output = run_cmd(["scutil", "--proxy"], live=False)
        # HTTP 代理
        http_enabled = re.search(r"HTTPEnable\s+:\s+1", output)
        if http_enabled:
            host = re.search(r"HTTPProxy\s+:\s+(\S+)", output)
            port = re.search(r"HTTPPort\s+:\s+(\d+)", output)
            if host and port:
                return f"http://{host.group(1)}:{port.group(1)}"

        # HTTPS 代理
        http_enabled = re.search(r"HTTPSEnable\s+:\s+1", output)
        if http_enabled:
            host = re.search(r"HTTPSProxy\s+:\s+(\S+)", output)
            port = re.search(r"HTTPSPort\s+:\s+(\d+)", output)
            if host and port:
                return f"http://{host.group(1)}:{port.group(1)}"

        # SOCKS 代理
        socks_enabled = re.search(r"SOCKSEnable\s+:\s+1", output)
        if socks_enabled:
            host = re.search(r"SOCKSProxy\s+:\s+(\S+)", output)
            port = re.search(r"SOCKSPort\s+:\s+(\d+)", output)
            if host and port:
                return f"socks://{host.group(1)}:{port.group(1)}"
    except RuntimeError as e:
        logger.debug("获取 MacOS 上的代理地址出现错误: %s", e)
        return None


def get_system_proxy_address() -> str | None:
    """获取系统上的代理地址

    Returns:
        (str | None):
            代理地址
    """
    if sys.platform == "win32":
        return get_windows_proxy_address()
    if sys.platform == "linux":
        return get_linux_proxy_address()
    if sys.platform == "darwin":
        return get_macos_proxy_address()

    return None


def set_proxy(addr: str) -> None:
    """通过环境变量配置代理

    Args:
        addr (str):
            代理地址
    """
    os.environ["HTTP_PROXY"] = addr
    os.environ["HTTPS_PROXY"] = addr


def clean_proxy() -> None:
    """将环境变量中的代理清除"""
    if "HTTP_PROXY" in os.environ:
        del os.environ["HTTP_PROXY"]

    if "HTTPS_PROXY" in os.environ:
        del os.environ["HTTPS_PROXY"]
