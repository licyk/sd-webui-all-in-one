"""补丁系统业务控制服务"""

from __future__ import annotations

import copy
import json
import socket
import threading
from pathlib import Path
from typing import Any

from .hook import install_import_hook, is_import_hook_installed, monkey_zoo
from .runtime.client import RuntimeClient
from .runtime.errors import (
    DEFAULT_CAUGHT_EXCLUDE_MODULE_PREFIXES,
    install_error_capture,
    is_error_capture_installed,
    uninstall_error_capture,
)
from .runtime.logs import (
    DEFAULT_FD_CAPTURE,
    DEFAULT_HOOK_CHECK_INTERVAL,
    DEFAULT_HOOK_POLICY,
    DEFAULT_LOGGER_EXCLUDE,
    DEFAULT_MAX_CHARS,
    DEFAULT_QUEUE_SIZE,
    DEFAULT_STREAMS,
    install_log_capture,
)
from .runtime.protocol import RuntimeProtocolError, decode_message, encode_message
from .state import HotpatcherState, get_default_state
from .stack_shadow import (
    DEFAULT_FILENAME_TEMPLATE,
    install_stack_shadower,
    is_stack_shadower_installed,
)

_MISSING = object()

DEFAULT_CONFIG: dict[str, Any] = {
    "services": {
        "apply_on_bootstrap": True,
    },
    "core": {
        "import_hook": {
            "enabled": True,
        },
        "stack_shadow": {
            "enabled": True,
            "prefixes": [
                "sd_webui_all_in_one_hotpatcher",
                "sd_webui_all_in_one_hotpatcher_ext",
            ],
            "filename_template": DEFAULT_FILENAME_TEMPLATE,
            "include_source_loaders": True,
        },
    },
    "runtime": {
        "errors": {
            "enabled": False,
            "sys_excepthook": True,
            "threading_excepthook": True,
            "unraisablehook": True,
            "asyncio": True,
            "include_locals": False,
            "caught_exceptions": {
                "enabled": False,
                "threading": True,
                "module_prefixes": [],
                "exclude_module_prefixes": list(DEFAULT_CAUGHT_EXCLUDE_MODULE_PREFIXES),
                "max_events_per_second": 20,
            },
        },
        "logs": {
            "enabled": False,
            "logging": True,
            "streams": list(DEFAULT_STREAMS),
            "subprocess": "safe",
            "policy": "bounded",
            "max_chars": DEFAULT_MAX_CHARS,
            "queue_size": DEFAULT_QUEUE_SIZE,
            "logger_include": [],
            "logger_exclude": list(DEFAULT_LOGGER_EXCLUDE),
            "hook_policy": DEFAULT_HOOK_POLICY,
            "hook_check_interval": DEFAULT_HOOK_CHECK_INTERVAL,
            "fd_capture": DEFAULT_FD_CAPTURE,
        },
    },
    "extensions": {
        "zluda": {
            "enabled": False,
            "compat": False,
            "path": "",
            "torch_zluda_timer": False,
        },
        "extension_index": {
            "webui": {
                "enabled": False,
                "url": "auto",
            },
            "comfyui_manager": {
                "enabled": False,
                "url": "auto",
            },
        },
        "hf_endpoint_mirror": {
            "enabled": False,
        },
        "uv_pip": {
            "enabled": False,
            "symlink": False,
        },
    },
}

SETTING_SCHEMA: dict[str, Any] = {
    "services": {
        "title": "服务控制",
        "description": "控制 hotpatcher services 在 bootstrap 和运行时控制通道中的行为。",
        "settings": {
            "apply_on_bootstrap": {
                "type": "bool",
                "title": "启动时应用配置",
                "description": "bootstrap 读取配置后立即调用 services.apply_config()。",
            },
        },
    },
    "core.import_hook": {
        "title": "Import Hook",
        "description": "安装 import hook，让已注册的模块补丁在目标模块首次导入时生效。",
        "settings": {
            "enabled": {
                "type": "bool",
                "title": "启用",
                "description": "启用 import hook。补丁必须在目标模块首次导入前注册。",
            },
        },
    },
    "core.stack_shadow": {
        "title": "栈隐藏",
        "description": "把补丁系统相关 traceback 文件名伪装成更友好的路径，降低用户日志噪音。",
        "settings": {
            "enabled": {
                "type": "bool",
                "title": "启用",
                "description": "安装 traceback 栈隐藏器。",
            },
            "prefixes": {
                "type": "list[str]",
                "title": "隐藏模块前缀",
                "description": "需要隐藏的模块名前缀。GUI 中可用逗号分隔多个值。",
            },
            "filename_template": {
                "type": "str",
                "title": "文件名模板",
                "description": "伪装 traceback 文件名时使用的模板。",
            },
            "include_source_loaders": {
                "type": "bool",
                "title": "处理源码 loader",
                "description": "同时处理从源码 loader 获取的文件名。",
            },
        },
    },
    "runtime.logs": {
        "title": "运行时日志",
        "description": "把 logging、标准输出和子进程输出采集到 runtime host。",
        "settings": {
            "enabled": {
                "type": "bool",
                "title": "启用日志采集",
                "description": "启用 runtime 日志采集。需要 runtime client 可用。",
            },
            "logging": {
                "type": "bool",
                "title": "采集 logging",
                "description": "采集 Python logging 记录并发送 log.record。",
            },
            "streams": {
                "type": "list[str]",
                "title": "标准流",
                "description": "采集的标准流名称。GUI 中可用逗号分隔多个值。",
            },
            "subprocess": {
                "type": "choice",
                "title": "子进程采集",
                "description": "控制是否包装子进程输出。safe 仅在安全场景启用，force 强制启用。",
                "choices": ["0", "safe", "force"],
            },
            "policy": {
                "type": "choice",
                "title": "输出策略",
                "description": "bounded 会限制单条消息长度，raw 保留原始输出。",
                "choices": ["bounded", "raw"],
            },
            "max_chars": {
                "type": "int",
                "title": "最大字符数",
                "description": "bounded 策略下单条日志最多保留的字符数。",
            },
            "queue_size": {
                "type": "int",
                "title": "队列大小",
                "description": "日志发送队列的最大长度。",
            },
            "logger_include": {
                "type": "list[str]",
                "title": "包含 logger",
                "description": "只采集这些 logger 前缀。为空表示不限制。",
            },
            "logger_exclude": {
                "type": "list[str]",
                "title": "排除 logger",
                "description": "不采集这些 logger 前缀。GUI 中可用逗号分隔多个值。",
            },
            "hook_policy": {
                "type": "choice",
                "title": "Hook 冲突策略",
                "description": "控制日志 hook 被其它软件替换后的处理方式。cooperative 只协作包装，warn 仅告警，reapply 自动重新接管。",
                "choices": ["cooperative", "warn", "reapply"],
            },
            "hook_check_interval": {
                "type": "int",
                "title": "Hook 检查间隔",
                "description": "warn/reapply 策略下检查日志 hook 状态的间隔秒数。",
            },
            "fd_capture": {
                "type": "choice",
                "title": "FD 级捕获",
                "description": "实验性标准流捕获。0 关闭，fallback 在普通 stream hook 丢失时尝试启用，force 启动时直接启用。",
                "choices": ["0", "fallback", "force"],
            },
        },
    },
    "runtime.errors": {
        "title": "运行时错误",
        "description": "捕获未处理 Python 异常并发送结构化 error.exception 事件到 runtime host。",
        "settings": {
            "enabled": {
                "type": "bool",
                "title": "启用错误捕获",
                "description": "启用未处理 Python 异常捕获。需要 runtime client 可用。",
            },
            "sys_excepthook": {
                "type": "bool",
                "title": "主线程异常",
                "description": "捕获 sys.excepthook 处理的主线程未处理异常。",
            },
            "threading_excepthook": {
                "type": "bool",
                "title": "线程异常",
                "description": "捕获 threading.excepthook 处理的线程未处理异常。",
            },
            "unraisablehook": {
                "type": "bool",
                "title": "Unraisable 异常",
                "description": "捕获 sys.unraisablehook 处理的析构、回调等不可抛出异常。",
            },
            "asyncio": {
                "type": "bool",
                "title": "Asyncio 异常",
                "description": "捕获 asyncio event loop exception handler 中的异常上下文。",
            },
            "include_locals": {
                "type": "bool",
                "title": "包含局部变量",
                "description": "在 error.exception 的 traceback frame 中附带脱敏后的局部变量 repr 摘要。",
            },
            "caught_exceptions.enabled": {
                "type": "bool",
                "title": "捕获已处理异常",
                "description": "实验性功能。使用 sys.settrace 捕获被业务代码 except 处理过的异常, 可能影响性能。",
            },
            "caught_exceptions.threading": {
                "type": "bool",
                "title": "跟踪新线程",
                "description": "为后续新建线程安装 caught exception trace 捕获。",
            },
            "caught_exceptions.module_prefixes": {
                "type": "list[str]",
                "title": "包含模块前缀",
                "description": "只捕获这些模块名前缀中的异常。为空表示不限制。",
            },
            "caught_exceptions.exclude_module_prefixes": {
                "type": "list[str]",
                "title": "排除模块前缀",
                "description": "不捕获这些模块名前缀中的异常。GUI 中可用逗号分隔多个值。",
            },
            "caught_exceptions.max_events_per_second": {
                "type": "int",
                "title": "每秒事件上限",
                "description": "caught exception 事件限流值。用于降低 sys.settrace 带来的事件噪音。",
            },
        },
    },
    "extensions.zluda": {
        "title": "ZLUDA",
        "description": "注册 ZLUDA 兼容性补丁和可选路径注入。",
        "settings": {
            "enabled": {
                "type": "bool",
                "title": "启用",
                "description": "启用 ZLUDA 扩展补丁。",
            },
            "compat": {
                "type": "bool",
                "title": "兼容模式",
                "description": "注册 torch / torch.backends.cuda 的 ZLUDA 兼容性补丁。",
            },
            "path": {
                "type": "str",
                "title": "ZLUDA 路径",
                "description": "添加到动态库搜索路径的 ZLUDA 目录。为空则不注入路径。",
            },
            "torch_zluda_timer": {
                "type": "bool",
                "title": "Torch 编译热修复",
                "description": "修复 torch.utils.cpp_extension 中不兼容 ZLUDA 的 HIP_HOME 判断。",
            },
        },
    },
    "extensions.extension_index": {
        "title": "扩展索引镜像",
        "description": "替换 WebUI / ComfyUI 扩展索引和 ComfyUI-Manager 相关 URL。",
        "settings": {
            "webui.enabled": {
                "type": "bool",
                "title": "启用 SD WebUI 镜像",
                "description": "启用 A1111 / Forge / Vladmandic 扩展索引镜像补丁。",
            },
            "webui.url": {
                "type": "str",
                "title": "SD WebUI 镜像 URL",
                "description": "用于替换 A1111 / Forge / Vladmandic 扩展索引的镜像 JSON URL；填 auto 时自动检测网络并按需使用 GitHub raw 镜像。",
            },
            "comfyui_manager.enabled": {
                "type": "bool",
                "title": "启用 ComfyUI-Manager 镜像",
                "description": "启用 ComfyUI-Manager channel 镜像补丁。",
            },
            "comfyui_manager.url": {
                "type": "str",
                "title": "ComfyUI-Manager 镜像 URL",
                "description": "用于替换 ComfyUI-Manager channel 前缀的镜像 URL；填 auto 时自动检测网络并按需使用 GitHub raw 镜像。",
            },
        },
    },
    "extensions.hf_endpoint_mirror": {
        "title": "Hugging Face 镜像",
        "description": "注册 Hugging Face endpoint 镜像相关补丁。",
        "settings": {
            "enabled": {
                "type": "bool",
                "title": "启用",
                "description": "启用 Hugging Face endpoint 镜像补丁。",
            },
        },
    },
    "extensions.uv_pip": {
        "title": "uv Pip 替换",
        "description": "把 subprocess.run() 调用中的 pip 命令改写为 uv pip，用于加速运行期依赖安装。",
        "settings": {
            "enabled": {
                "type": "bool",
                "title": "启用",
                "description": "启用 uv pip 命令替换补丁。",
            },
            "symlink": {
                "type": "bool",
                "title": "符号链接模式",
                "description": "为 uv pip 命令添加 --link-mode symlink。通常只在明确需要共享文件链接时启用。",
            },
        },
    },
}


class ServiceControlChannel:
    """
    services 运行时控制通道

    独立连接宿主 TCP JSONL 端口, 打开 ``channel.open: services`` 后在后台线程中
    接收 ``services.*`` 请求并写回响应。

    Attributes:
        client (RuntimeClient):
            提供 host、port、token 信息的运行时客户端
        service (PatchService):
            处理 services 请求的服务对象
        sock (socket.socket):
            独立控制通道 socket
        closed (bool):
            控制通道是否已关闭
    """

    def __init__(
        self,
        client: RuntimeClient,
        service: "PatchService | None" = None,
        *,
        timeout: float = 5.0,
    ) -> None:
        """
        初始化 services 控制通道

        Args:
            client (RuntimeClient):
                已连接的运行时客户端
            service (PatchService | None):
                请求处理服务。为 None 时使用默认服务。
            timeout (float):
                TCP 连接超时时间
        """

        self.client = client
        self.service = service or PatchService()
        self.sock = socket.create_connection((client.host, client.port), timeout=timeout)
        self.reader = self.sock.makefile("rb")
        self.write_lock = threading.Lock()
        self.closed = False
        self.thread = threading.Thread(
            target=self._run,
            name="sd_webui_all_in_one_hotpatcher-services",
            daemon=True,
        )

    def start(self) -> "ServiceControlChannel":
        """
        发送通道握手并启动后台线程

        Returns:
            ServiceControlChannel:
                当前控制通道对象
        """

        self._send(
            {
                "type": "channel.open",
                "channel": "services",
                "token": self.client.token,
            }
        )
        self.thread.start()
        return self

    def close(self) -> None:
        """关闭控制通道"""

        if self.closed:
            return
        self.closed = True
        try:
            self.reader.close()
        finally:
            self.sock.close()

    def _run(self) -> None:
        while not self.closed:
            try:
                line = self.reader.readline()
                if not line:
                    return
                request = decode_message(line)
                response = self.service.handle_request_json(request, runtime_client=self.client)
                if "id" in request:
                    response["id"] = request["id"]
                self._send(response)
            except Exception as exc:
                if self.closed:
                    return
                self._send(_error_response("request_failed", str(exc)))

    def _send(self, message: dict[str, Any]) -> None:
        with self.write_lock:
            self.sock.sendall(encode_message(message))


class PatchService:
    """补丁系统业务控制服务对象"""

    def __init__(self, *, state: HotpatcherState | None = None) -> None:
        """初始化补丁服务对象

        Args:
            state (HotpatcherState | None):
                可选状态对象。为 None 时使用默认状态。
        """

        self.state = state or get_default_state()

    def get_catalog(self) -> dict[str, Any]:
        """
        查询补丁系统能力目录

        Returns:
            dict[str, Any]:
                当前功能目录、可调设置和已注册补丁状态
        """

        return get_catalog(state=self.state)

    def get_default_config(self) -> dict[str, Any]:
        """
        查询默认配置

        Returns:
            dict[str, Any]:
                完整默认配置副本
        """

        return get_default_config()

    def get_current_config(self) -> dict[str, Any]:
        """
        查询当前进程配置

        Returns:
            dict[str, Any]:
                当前进程最后加载或应用的完整配置副本
        """

        return get_current_config(state=self.state)

    def normalize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        补齐配置默认值

        Args:
            config (dict[str, Any]):
                用户配置

        Returns:
            dict[str, Any]:
                补齐默认值后的配置
        """

        return normalize_config(config)

    def handle_request_json(
        self,
        raw: str | dict[str, Any],
        *,
        runtime_client: RuntimeClient | None = None,
    ) -> dict[str, Any]:
        """
        处理 services JSON 请求

        Args:
            raw (str | dict[str, Any]):
                JSON 字符串或请求对象
            runtime_client (RuntimeClient | None):
                可选运行时客户端

        Returns:
            dict[str, Any]:
                固定 ok/error 格式响应
        """

        return handle_request_json(raw, runtime_client=runtime_client, state=self.state)


def get_catalog(*, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    查询当前可用功能和已注册补丁

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            JSON-serializable 能力目录
    """

    active_state = state or get_default_state()
    defaults = get_default_config()
    features = copy.deepcopy(SETTING_SCHEMA)
    _attach_feature_state(features, defaults, active_state)
    return {
        "features": features,
        "registered_patches": _registered_patches(active_state),
    }


def get_default_config() -> dict[str, Any]:
    """
    获取完整默认配置

    Returns:
        dict[str, Any]:
            默认配置深拷贝
    """

    return copy.deepcopy(DEFAULT_CONFIG)


def get_current_config(*, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    获取当前进程最后加载或应用的完整配置

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            当前进程配置副本。尚未记录时返回默认配置。
    """

    active_state = state or get_default_state()
    with active_state.current_config_lock:
        if active_state.current_config is None:
            return get_default_config()
        return copy.deepcopy(active_state.current_config)


def set_current_config(config: dict[str, Any], *, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    更新当前进程配置快照

    Args:
        config (dict[str, Any]):
            用户配置或完整配置
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            规范化后的当前配置副本
    """

    active_state = state or get_default_state()
    normalized = normalize_config(config)
    with active_state.current_config_lock:
        active_state.current_config = copy.deepcopy(normalized)
    return copy.deepcopy(normalized)


def clear_current_config(*, state: HotpatcherState | None = None) -> None:
    """清除当前进程配置快照, 下一次查询将返回默认配置

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。
    """

    active_state = state or get_default_state()
    with active_state.current_config_lock:
        active_state.current_config = None


def normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    """
    深度补齐默认配置

    用户配置中已有值保持不变。只有当用户值和默认值都是 dict 时才递归合并。

    Args:
        config (dict[str, Any]):
            用户配置

    Returns:
        dict[str, Any]:
            补齐默认值后的配置

    Raises:
        ValueError:
            配置顶层不是 object
    """

    if not isinstance(config, dict):
        raise ValueError("config must be an object")
    return _merge_defaults(copy.deepcopy(config), get_default_config())


def load_config_file(path: str | Path, write_back: bool = True) -> dict[str, Any]:
    """
    读取并规范化 JSON 配置文件

    Args:
        path (str | Path):
            JSON 配置文件路径
        write_back (bool):
            是否把补齐后的配置写回文件

    Returns:
        dict[str, Any]:
            规范化后的配置

    Raises:
        ValueError:
            JSON 顶层不是 object
    """

    config_path = Path(path).expanduser()
    with config_path.open("r", encoding="utf-8") as file:
        loaded = json.load(file)
    if not isinstance(loaded, dict):
        raise ValueError("config file must decode to an object")

    normalized = normalize_config(loaded)
    if write_back:
        save_config_file(config_path, normalized)
    return normalized


def save_config_file(path: str | Path, config: dict[str, Any]) -> None:
    """
    保存规范化后的 JSON 配置文件

    Args:
        path (str | Path):
            JSON 配置文件路径
        config (dict[str, Any]):
            待保存配置
    """

    config_path = Path(path).expanduser()
    normalized = normalize_config(config)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as file:
        json.dump(normalized, file, ensure_ascii=False, indent=2)
        file.write("\n")


def apply_config(
    config: dict[str, Any],
    *,
    runtime_client: RuntimeClient | None = None,
    state: HotpatcherState | None = None,
) -> dict[str, Any]:
    """
    按配置启用补丁系统功能

    Args:
        config (dict[str, Any]):
            用户配置或完整配置
        runtime_client (RuntimeClient | None):
            可选运行时客户端, 用于启用日志采集
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            ``applied``、``warnings``、``errors`` 结果对象
    """

    active_state = state or get_default_state()
    normalized = normalize_config(config)
    result: dict[str, Any] = {"applied": [], "warnings": [], "errors": []}
    set_current_config(normalized, state=active_state)

    _apply_core_config(normalized, result, active_state)
    _apply_runtime_config(normalized, result, runtime_client, active_state)
    _apply_extension_config(normalized, result)
    _warn_disabled_but_active(normalized, result, active_state)
    return result


def handle_request_json(
    raw: str | dict[str, Any],
    *,
    runtime_client: RuntimeClient | None = None,
    state: HotpatcherState | None = None,
) -> dict[str, Any]:
    """
    处理 services JSON 请求

    Args:
        raw (str | dict[str, Any]):
            JSON 字符串或请求对象
        runtime_client (RuntimeClient | None):
            可选运行时客户端
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            固定 ok/error 格式响应
    """

    active_state = state or get_default_state()
    try:
        request = _decode_request(raw)
        message_type = request["type"]
        payload = request.get("payload", {})
        if not isinstance(payload, dict):
            return _error_response("invalid_request", "payload must be an object")

        if message_type == "services.catalog.get":
            return _success_response({"catalog": get_catalog(state=active_state)})
        if message_type == "services.defaults.get":
            return _success_response({"config": get_default_config()})
        if message_type == "services.config.current":
            return _success_response({"config": get_current_config(state=active_state)})
        if message_type == "services.config.normalize":
            return _success_response({"config": normalize_config(_payload_config(payload))})
        if message_type == "services.config.load":
            config = load_config_file(
                _payload_path(payload),
                write_back=bool(payload.get("write_back", True)),
            )
            return _success_response({"config": config})
        if message_type == "services.config.save":
            path = _payload_path(payload)
            config = normalize_config(_payload_config(payload))
            save_config_file(path, config)
            return _success_response({"config": config})
        if message_type == "services.config.apply":
            result = apply_config(_payload_config(payload), runtime_client=runtime_client, state=active_state)
            return _success_response({"result": result})

        return _error_response("unknown_request", f"unknown services request: {message_type}")
    except json.JSONDecodeError as exc:
        return _error_response("invalid_json", str(exc))
    except (OSError, RuntimeProtocolError, ValueError, TypeError) as exc:
        return _error_response("request_failed", str(exc))


def install_service_control_channel(
    client: RuntimeClient,
    service: PatchService | None = None,
    *,
    state: HotpatcherState | None = None,
) -> ServiceControlChannel:
    """
    安装 services runtime 控制通道

    Args:
        client (RuntimeClient):
            已连接的运行时客户端
        service (PatchService | None):
            可选服务对象
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        ServiceControlChannel:
            已启动的控制通道
    """

    return ServiceControlChannel(client, service or PatchService(state=state)).start()


def _apply_core_config(config: dict[str, Any], result: dict[str, Any], state: HotpatcherState) -> None:
    core = _section(config, "core")
    import_hook = _section(core, "import_hook")
    if import_hook.get("enabled"):
        _apply_step("core.import_hook", lambda: install_import_hook(state=state), result)

    stack_shadow = _section(core, "stack_shadow")
    if stack_shadow.get("enabled"):
        _apply_step(
            "core.stack_shadow",
            lambda: install_stack_shadower(
                _normalize_string_list(stack_shadow.get("prefixes", [])),
                filename_template=str(stack_shadow.get("filename_template", DEFAULT_FILENAME_TEMPLATE)),
                include_source_loaders=bool(stack_shadow.get("include_source_loaders", True)),
                state=state,
            ),
            result,
        )


def _apply_runtime_config(
    config: dict[str, Any],
    result: dict[str, Any],
    runtime_client: RuntimeClient | None,
    state: HotpatcherState,
) -> None:
    runtime = _section(config, "runtime")
    errors = _section(runtime, "errors")
    if errors.get("enabled"):
        if runtime_client is None:
            uninstall_error_capture(state=state)
            result["warnings"].append(
                {
                    "feature": "runtime.errors",
                    "message": "runtime_client is required to enable errors",
                }
            )
        else:
            caught_exceptions = _section(errors, "caught_exceptions")
            _apply_step(
                "runtime.errors",
                lambda: install_error_capture(
                    runtime_client,
                    sys_excepthook=bool(errors.get("sys_excepthook", True)),
                    threading_excepthook=bool(errors.get("threading_excepthook", True)),
                    unraisablehook=bool(errors.get("unraisablehook", True)),
                    asyncio=bool(errors.get("asyncio", True)),
                    include_locals=bool(errors.get("include_locals", False)),
                    caught_exceptions_enabled=bool(caught_exceptions.get("enabled", False)),
                    caught_exceptions_threading=bool(caught_exceptions.get("threading", True)),
                    caught_exception_module_prefixes=_normalize_string_list(caught_exceptions.get("module_prefixes", [])),
                    caught_exception_exclude_module_prefixes=_normalize_string_list(caught_exceptions.get("exclude_module_prefixes", DEFAULT_CAUGHT_EXCLUDE_MODULE_PREFIXES)),
                    caught_exception_max_events_per_second=int(caught_exceptions.get("max_events_per_second", 20)),
                    state=state,
                ),
                result,
            )
    else:
        uninstall_error_capture(state=state)

    logs = _section(runtime, "logs")
    if logs.get("enabled"):
        if runtime_client is None:
            result["warnings"].append(
                {
                    "feature": "runtime.logs",
                    "message": "runtime_client is required to enable logs",
                }
            )
            return

        _apply_step(
            "runtime.logs",
            lambda: install_log_capture(
                runtime_client,
                capture_logging=bool(logs.get("logging", True)),
                streams=_normalize_string_list(logs.get("streams", DEFAULT_STREAMS)),
                subprocess_mode=str(logs.get("subprocess", "safe")),
                policy=str(logs.get("policy", "bounded")),
                max_chars=int(logs.get("max_chars", DEFAULT_MAX_CHARS)),
                queue_size=int(logs.get("queue_size", DEFAULT_QUEUE_SIZE)),
                logger_include=_normalize_string_list(logs.get("logger_include", [])),
                logger_exclude=_normalize_string_list(logs.get("logger_exclude", DEFAULT_LOGGER_EXCLUDE)),
                hook_policy=str(logs.get("hook_policy", DEFAULT_HOOK_POLICY)),
                hook_check_interval=int(logs.get("hook_check_interval", DEFAULT_HOOK_CHECK_INTERVAL)),
                fd_capture=str(logs.get("fd_capture", DEFAULT_FD_CAPTURE)),
                state=state,
            ),
            result,
        )


def _apply_extension_config(config: dict[str, Any], result: dict[str, Any]) -> None:
    extensions = _section(config, "extensions")
    zluda = _section(extensions, "zluda")
    if zluda.get("enabled"):
        from sd_webui_all_in_one_hotpatcher_ext.zluda import apply_from_config as apply_zluda

        _apply_step("extensions.zluda", lambda: apply_zluda(zluda), result)

    extension_index = _section(extensions, "extension_index")
    if _is_extension_index_enabled(extension_index):
        from sd_webui_all_in_one_hotpatcher_ext.extension_index import (
            apply_from_config as apply_extension_index,
        )

        _apply_step(
            "extensions.extension_index",
            lambda: apply_extension_index(extension_index),
            result,
        )

    hf_endpoint_mirror = _section(extensions, "hf_endpoint_mirror")
    if hf_endpoint_mirror.get("enabled"):
        from sd_webui_all_in_one_hotpatcher_ext.hf_endpoint_mirror import (
            apply_from_config as apply_hf_endpoint_mirror,
        )

        _apply_step(
            "extensions.hf_endpoint_mirror",
            lambda: apply_hf_endpoint_mirror(hf_endpoint_mirror),
            result,
        )

    uv_pip = _section(extensions, "uv_pip")
    if uv_pip.get("enabled"):
        from sd_webui_all_in_one_hotpatcher_ext.uv_pip import (
            apply_from_config as apply_uv_pip,
        )

        _apply_step(
            "extensions.uv_pip",
            lambda: apply_uv_pip(uv_pip),
            result,
        )


def _is_extension_index_enabled(config: dict[str, Any]) -> bool:
    return any(isinstance(section, dict) and bool(section.get("enabled")) for section in (config.get("webui"), config.get("comfyui_manager")))


def _apply_step(feature: str, callback: Any, result: dict[str, Any]) -> None:
    try:
        callback()
        result["applied"].append(feature)
    except Exception as exc:  # pragma: no cover - exercised through service-level tests
        result["errors"].append(
            {
                "feature": feature,
                "code": type(exc).__name__,
                "message": str(exc),
            }
        )


def _warn_disabled_but_active(config: dict[str, Any], result: dict[str, Any], state: HotpatcherState) -> None:
    core = _section(config, "core")
    if not _section(core, "import_hook").get("enabled") and is_import_hook_installed(state=state):
        result["warnings"].append(
            {
                "feature": "core.import_hook",
                "message": "import hook is already installed and v1 services does not uninstall it",
            }
        )
    if not _section(core, "stack_shadow").get("enabled") and is_stack_shadower_installed(state=state):
        result["warnings"].append(
            {
                "feature": "core.stack_shadow",
                "message": "stack shadower is already installed and v1 services does not uninstall it",
            }
        )

    extensions = _section(config, "extensions")
    if not _section(extensions, "uv_pip").get("enabled") and _is_uv_pip_patch_installed():
        result["warnings"].append(
            {
                "feature": "extensions.uv_pip",
                "message": "uv pip patch is already installed and v1 services does not uninstall it",
            }
        )


def _attach_feature_state(features: dict[str, Any], defaults: dict[str, Any], state: HotpatcherState) -> None:
    features["services"]["default"] = defaults["services"]
    features["services"]["active"] = False
    features["core.import_hook"]["default"] = defaults["core"]["import_hook"]
    features["core.import_hook"]["active"] = is_import_hook_installed(state=state)
    features["core.stack_shadow"]["default"] = defaults["core"]["stack_shadow"]
    features["core.stack_shadow"]["active"] = is_stack_shadower_installed(state=state)
    features["runtime.errors"]["default"] = defaults["runtime"]["errors"]
    features["runtime.errors"]["active"] = is_error_capture_installed(state=state)
    features["runtime.logs"]["default"] = defaults["runtime"]["logs"]
    features["runtime.logs"]["active"] = False
    features["extensions.zluda"]["default"] = defaults["extensions"]["zluda"]
    features["extensions.zluda"]["active"] = False
    features["extensions.extension_index"]["default"] = defaults["extensions"]["extension_index"]
    features["extensions.extension_index"]["active"] = False
    features["extensions.hf_endpoint_mirror"]["default"] = defaults["extensions"]["hf_endpoint_mirror"]
    features["extensions.hf_endpoint_mirror"]["active"] = False
    features["extensions.uv_pip"]["default"] = defaults["extensions"]["uv_pip"]
    features["extensions.uv_pip"]["active"] = _is_uv_pip_patch_installed()
    _attach_setting_defaults(features)


def _is_uv_pip_patch_installed() -> bool:
    try:
        from sd_webui_all_in_one_hotpatcher_ext.uv_pip import is_uv_patch_installed

        return is_uv_patch_installed()
    except Exception:
        return False


def _attach_setting_defaults(features: dict[str, Any]) -> None:
    for feature in features.values():
        if not isinstance(feature, dict):
            continue
        feature_default = feature.get("default", {})
        if not isinstance(feature_default, dict):
            continue
        settings = feature.get("settings", {})
        if not isinstance(settings, dict):
            continue
        for setting_name, metadata in settings.items():
            if not isinstance(metadata, dict):
                continue
            setting_default = _get_value_by_path(feature_default, setting_name, _MISSING)
            if setting_default is _MISSING:
                continue
            metadata["default"] = copy.deepcopy(setting_default)


def _registered_patches(state: HotpatcherState) -> dict[str, Any]:
    modules: dict[str, Any] = {}
    zoo = state.monkey_zoo or monkey_zoo
    for name, monkey in sorted(zoo.monkeys.items()):
        modules[name] = {
            "premodule": len(monkey.premodule_patches),
            "module": len(monkey.module_patches),
            "function": len(monkey.function_patches),
            "source": len(monkey.source_patches),
            "ast": len(monkey.ast_patches),
            "bytecode": len(monkey.bytecode_patches),
            "output_prohibition": len(monkey.output_prohibition),
            "import_injection": len(monkey.import_injections),
        }
    return {
        "modules": modules,
        "aliases": dict(sorted(zoo.aliases_fallback.items())),
    }


def _merge_defaults(config: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    for key, default_value in defaults.items():
        if key not in config:
            config[key] = copy.deepcopy(default_value)
            continue
        current_value = config[key]
        if isinstance(current_value, dict) and isinstance(default_value, dict):
            _merge_defaults(current_value, default_value)
    return config


def _decode_request(raw: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, str):
        raw = json.loads(raw)
    if not isinstance(raw, dict):
        raise ValueError("request must be an object")
    if not isinstance(raw.get("type"), str):
        raise ValueError("request type is required")
    return raw


def _payload_config(payload: dict[str, Any]) -> dict[str, Any]:
    config = payload.get("config", {})
    if not isinstance(config, dict):
        raise ValueError("payload.config must be an object")
    return config


def _payload_path(payload: dict[str, Any]) -> str:
    path = payload.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError("payload.path must be a non-empty string")
    return path


def _get_value_by_path(config: dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = config
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _section(config: dict[str, Any], key: str) -> dict[str, Any]:
    value = config.get(key, {})
    return value if isinstance(value, dict) else {}


def _normalize_string_list(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(",") if item.strip())
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def _success_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "payload": payload}


def _error_response(code: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
