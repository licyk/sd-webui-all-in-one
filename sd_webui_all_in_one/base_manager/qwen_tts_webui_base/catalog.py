"""Implementation grouped from the former ``qwen_tts_webui_base.py`` module."""

from __future__ import annotations

import importlib
from pathlib import Path
from sd_webui_all_in_one.launch_arguments import (
    DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    LaunchArgumentCatalog,
    build_script_help_command,
    discover_launch_argument_catalog,
)
from sd_webui_all_in_one.config import (
    ROOT_PATH,
)
from sd_webui_all_in_one.utils import TemporaryModulePath

QWEN_TTS_WEBUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY = "qwen_tts_webui.cmd_args:get_args_parser"


def get_qwen_tts_webui_launch_argument_catalog(
    qwen_tts_webui_path: str | Path,
    use_parser_object: bool = True,
    *,
    python_executable: str | Path | None = None,
    timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
) -> LaunchArgumentCatalog:
    """发现 Qwen TTS 启动参数，对象解析失败时回退到 ``--help``。

    Args:
        qwen_tts_webui_path (str | Path): Qwen TTS WebUI 根目录。
        use_parser_object (bool): 是否优先解析实际参数对象。
        python_executable (str | Path | None): 执行 ``--help`` 的 Python。
        timeout_seconds (float): ``--help`` 命令超时秒数。

    Returns:
        LaunchArgumentCatalog: 规范化的启动参数目录。
    """
    path = Path(qwen_tts_webui_path)

    def load_parser():
        with TemporaryModulePath(path):
            return importlib.import_module("qwen_tts_webui.cmd_args").get_args_parser()

    return discover_launch_argument_catalog(
        "qwen_tts_webui",
        path,
        provider_identity=QWEN_TTS_WEBUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
        help_command_factory=lambda context: build_script_help_command(context, ("launch.py",)),
        parser_loader=load_parser,
        parser_source_identity="qwen_tts_webui.cmd_args:get_args_parser",
        use_parser_object=use_parser_object,
        python_executable=python_executable,
        timeout_seconds=timeout_seconds,
    )


QWEN_TTS_WEBUI_PRESET_HF_PATH = ROOT_PATH / "base_manager" / "config" / "qwen_tts_webui_config_huggingface.json"

QWEN_TTS_WEBUI_PRESET_MS_PATH = ROOT_PATH / "base_manager" / "config" / "qwen_tts_webui_config_modelscope.json"

QWEN_TTS_WEBUI_REPO = "https://github.com/licyk/qwen-tts-webui"
