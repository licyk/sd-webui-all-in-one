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
from .runtime.logs import (
    DEFAULT_LOGGER_EXCLUDE,
    DEFAULT_MAX_CHARS,
    DEFAULT_QUEUE_SIZE,
    DEFAULT_STREAMS,
    install_log_capture,
)
from .runtime.protocol import RuntimeProtocolError, decode_message, encode_message
from .stack_shadow import (
    DEFAULT_FILENAME_TEMPLATE,
    install_stack_shadower,
    is_stack_shadower_installed,
)

DEFAULT_CONFIG: dict[str, Any] = {
    "services": {
        "apply_on_bootstrap": False,
    },
    "core": {
        "import_hook": {
            "enabled": False,
        },
        "stack_shadow": {
            "enabled": False,
            "prefixes": [
                "sd_webui_all_in_one_hotpatcher",
                "sd_webui_all_in_one_hotpatcher_ext",
            ],
            "filename_template": DEFAULT_FILENAME_TEMPLATE,
            "include_source_loaders": True,
        },
    },
    "runtime": {
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
            "enabled": False,
            "extension_index_url": "",
            "a1111_url": "",
            "comfyui_manager": False,
        },
        "hf_endpoint_mirror": {
            "enabled": False,
        },
    },
}

SETTING_SCHEMA: dict[str, Any] = {
    "services": {
        "settings": {
            "apply_on_bootstrap": "bool",
        },
    },
    "core.import_hook": {
        "settings": {
            "enabled": "bool",
        },
    },
    "core.stack_shadow": {
        "settings": {
            "enabled": "bool",
            "prefixes": "list[str] | comma-separated str",
            "filename_template": "str",
            "include_source_loaders": "bool",
        },
    },
    "runtime.logs": {
        "settings": {
            "enabled": "bool",
            "logging": "bool",
            "streams": "list[str] | comma-separated str",
            "subprocess": "0 | safe | force",
            "policy": "bounded | raw",
            "max_chars": "int",
            "queue_size": "int",
            "logger_include": "list[str]",
            "logger_exclude": "list[str]",
        },
    },
    "extensions.zluda": {
        "settings": {
            "enabled": "bool",
            "compat": "bool",
            "path": "str",
            "torch_zluda_timer": "bool",
        },
    },
    "extensions.extension_index": {
        "settings": {
            "enabled": "bool",
            "extension_index_url": "str",
            "a1111_url": "str",
            "comfyui_manager": "bool | object",
        },
    },
    "extensions.hf_endpoint_mirror": {
        "settings": {
            "enabled": "bool",
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

    def get_catalog(self) -> dict[str, Any]:
        """
        查询补丁系统能力目录

        Returns:
            dict[str, Any]:
                当前功能目录、可调设置和已注册补丁状态
        """

        return get_catalog()

    def get_default_config(self) -> dict[str, Any]:
        """
        查询默认配置

        Returns:
            dict[str, Any]:
                完整默认配置副本
        """

        return get_default_config()

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

        return handle_request_json(raw, runtime_client=runtime_client)


def get_catalog() -> dict[str, Any]:
    """
    查询当前可用功能和已注册补丁

    Returns:
        dict[str, Any]:
            JSON-serializable 能力目录
    """

    defaults = get_default_config()
    features = copy.deepcopy(SETTING_SCHEMA)
    _attach_feature_state(features, defaults)
    return {
        "features": features,
        "registered_patches": _registered_patches(),
    }


def get_default_config() -> dict[str, Any]:
    """
    获取完整默认配置

    Returns:
        dict[str, Any]:
            默认配置深拷贝
    """

    return copy.deepcopy(DEFAULT_CONFIG)


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
) -> dict[str, Any]:
    """
    按配置启用补丁系统功能

    Args:
        config (dict[str, Any]):
            用户配置或完整配置
        runtime_client (RuntimeClient | None):
            可选运行时客户端, 用于启用日志采集

    Returns:
        dict[str, Any]:
            ``applied``、``warnings``、``errors`` 结果对象
    """

    normalized = normalize_config(config)
    result: dict[str, Any] = {"applied": [], "warnings": [], "errors": []}

    _apply_core_config(normalized, result)
    _apply_runtime_config(normalized, result, runtime_client)
    _apply_extension_config(normalized, result)
    _warn_disabled_but_active(normalized, result)
    return result


def handle_request_json(
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

    try:
        request = _decode_request(raw)
        message_type = request["type"]
        payload = request.get("payload", {})
        if not isinstance(payload, dict):
            return _error_response("invalid_request", "payload must be an object")

        if message_type == "services.catalog.get":
            return _success_response({"catalog": get_catalog()})
        if message_type == "services.defaults.get":
            return _success_response({"config": get_default_config()})
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
            result = apply_config(_payload_config(payload), runtime_client=runtime_client)
            return _success_response({"result": result})

        return _error_response("unknown_request", f"unknown services request: {message_type}")
    except json.JSONDecodeError as exc:
        return _error_response("invalid_json", str(exc))
    except (OSError, RuntimeProtocolError, ValueError, TypeError) as exc:
        return _error_response("request_failed", str(exc))


def install_service_control_channel(
    client: RuntimeClient,
    service: PatchService | None = None,
) -> ServiceControlChannel:
    """
    安装 services runtime 控制通道

    Args:
        client (RuntimeClient):
            已连接的运行时客户端
        service (PatchService | None):
            可选服务对象

    Returns:
        ServiceControlChannel:
            已启动的控制通道
    """

    return ServiceControlChannel(client, service).start()


def _apply_core_config(config: dict[str, Any], result: dict[str, Any]) -> None:
    core = _section(config, "core")
    import_hook = _section(core, "import_hook")
    if import_hook.get("enabled"):
        _apply_step("core.import_hook", install_import_hook, result)

    stack_shadow = _section(core, "stack_shadow")
    if stack_shadow.get("enabled"):
        _apply_step(
            "core.stack_shadow",
            lambda: install_stack_shadower(
                _normalize_string_list(stack_shadow.get("prefixes", [])),
                filename_template=str(stack_shadow.get("filename_template", DEFAULT_FILENAME_TEMPLATE)),
                include_source_loaders=bool(stack_shadow.get("include_source_loaders", True)),
            ),
            result,
        )


def _apply_runtime_config(
    config: dict[str, Any],
    result: dict[str, Any],
    runtime_client: RuntimeClient | None,
) -> None:
    logs = _section(_section(config, "runtime"), "logs")
    if not logs.get("enabled"):
        return
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
    if extension_index.get("enabled"):
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


def _warn_disabled_but_active(config: dict[str, Any], result: dict[str, Any]) -> None:
    core = _section(config, "core")
    if not _section(core, "import_hook").get("enabled") and is_import_hook_installed():
        result["warnings"].append(
            {
                "feature": "core.import_hook",
                "message": "import hook is already installed and v1 services does not uninstall it",
            }
        )
    if not _section(core, "stack_shadow").get("enabled") and is_stack_shadower_installed():
        result["warnings"].append(
            {
                "feature": "core.stack_shadow",
                "message": "stack shadower is already installed and v1 services does not uninstall it",
            }
        )


def _attach_feature_state(features: dict[str, Any], defaults: dict[str, Any]) -> None:
    features["services"]["default"] = defaults["services"]
    features["services"]["active"] = False
    features["core.import_hook"]["default"] = defaults["core"]["import_hook"]
    features["core.import_hook"]["active"] = is_import_hook_installed()
    features["core.stack_shadow"]["default"] = defaults["core"]["stack_shadow"]
    features["core.stack_shadow"]["active"] = is_stack_shadower_installed()
    features["runtime.logs"]["default"] = defaults["runtime"]["logs"]
    features["runtime.logs"]["active"] = False
    features["extensions.zluda"]["default"] = defaults["extensions"]["zluda"]
    features["extensions.extension_index"]["default"] = defaults["extensions"]["extension_index"]
    features["extensions.hf_endpoint_mirror"]["default"] = defaults["extensions"]["hf_endpoint_mirror"]


def _registered_patches() -> dict[str, Any]:
    modules: dict[str, Any] = {}
    for name, monkey in sorted(monkey_zoo.monkeys.items()):
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
        "aliases": dict(sorted(monkey_zoo.aliases_fallback.items())),
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
