"""ComfyUI 组件冲突处理操作"""

import os
import sys
from pathlib import Path
from collections.abc import Callable

from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.pkg_manager import install_requirements
from sd_webui_all_in_one.utils import (
    append_python_path,
)
from sd_webui_all_in_one.env_check.shared import logger
from sd_webui_all_in_one.env_check.comfyui_env_analyze.models import (
    ComfyUIConflictResolution,
    ComfyUIConflictAction,
)


def _prompt_conflict_action(
    resolution: ComfyUIConflictResolution,
) -> ComfyUIConflictAction:
    """在交互模式下询问检测到冲突依赖时的处理方式

    Args:
        resolution (ComfyUIConflictResolution):
            冲突组件禁用方案

    Returns:
        ComfyUIConflictAction: 用户选择的处理方式
    """
    can_disable = len(resolution["disable_components"]) > 0
    print("请选择冲突依赖的处理方式:")
    print("1. 按顺序安装冲突组件依赖")
    if can_disable:
        print(f"2. 禁用冲突组件并继续安装依赖 (将禁用: {', '.join(resolution['disable_components'])})")
    print("N. 忽略冲突并继续")
    answer = input("请输入选项 (1/2/N): " if can_disable else "请输入选项 (1/N): ").strip().lower()
    if answer in ["1", "yes", "y"]:
        return "install"
    if can_disable and answer in ["2", "d", "disable"]:
        return "disable"
    return "skip"


def _select_conflict_action(
    resolution: ComfyUIConflictResolution,
    install_conflict_component_requirement: bool,
    disable_conflict_component: bool,
    interactive_mode: bool,
) -> ComfyUIConflictAction:
    """确定检测到冲突依赖时的处理方式

    交互模式下由用户选择; 非交互模式下优先禁用冲突组件, 其次按顺序安装冲突组件依赖.

    Args:
        resolution (ComfyUIConflictResolution):
            冲突组件禁用方案
        install_conflict_component_requirement (bool):
            是否按顺序安装冲突组件依赖
        disable_conflict_component (bool):
            是否禁用冲突组件并继续安装依赖
        interactive_mode (bool):
            是否启用交互模式

    Returns:
        ComfyUIConflictAction: 处理方式
    """
    if interactive_mode:
        return _prompt_conflict_action(resolution)
    if disable_conflict_component and resolution["disable_components"]:
        return "disable"
    if install_conflict_component_requirement:
        return "install"
    return "skip"


def _create_disable_component_callback(
    comfyui_root_path: Path,
) -> Callable[[str], None]:
    """创建默认的 ComfyUI 组件禁用函数

    Args:
        comfyui_root_path (Path):
            ComfyUI 根目录

    Returns:
        Callable[[str], None]: 接收组件名称并禁用该组件的函数
    """
    # 延迟导入, 避免 env_check 与 base_manager 之间的循环导入
    from sd_webui_all_in_one.base_manager.comfyui_base.extensions.local import set_comfyui_custom_node_status  # pylint: disable=import-outside-toplevel

    def disable_component(component_name: str) -> None:
        set_comfyui_custom_node_status(comfyui_root_path, component_name, False)

    return disable_component


def _disable_conflict_components(
    components: list[str],
    disable_component_callback: Callable[[str], None],
) -> list[Exception]:
    """禁用冲突组件

    Args:
        components (list[str]):
            需要禁用的组件列表
        disable_component_callback (Callable[[str], None]):
            禁用单个组件的函数

    Returns:
        list[Exception]: 禁用组件时出现的错误
    """
    err: list[Exception] = []
    disabled: list[str] = []
    task_sum = len(components)
    for count, component_name in enumerate(components, start=1):
        logger.info("[%s/%s] 禁用 %s 中", count, task_sum, component_name)
        try:
            disable_component_callback(component_name)
            disabled.append(component_name)
        except (OSError, ValueError, RuntimeError) as e:
            err.append(e)
            logger.error("[%s/%s] 禁用 %s 失败: %s", count, task_sum, component_name, e)

    if disabled:
        logger.info("已禁用以下冲突组件: %s", ", ".join(disabled))
        logger.info("如需重新启用, 可在 ComfyUI 扩展管理中重新启用这些组件")
    return err


def _install_component_requirements(
    comfyui_root_path: Path,
    req_list: list[Path],
    install_sequentially: bool,
    use_uv: bool,
    custom_env: dict[str, str] | None,
) -> list[Exception]:
    """安装 ComfyUI 组件依赖并执行组件的安装脚本

    Args:
        comfyui_root_path (Path):
            ComfyUI 根目录
        req_list (list[Path]):
            需要安装的依赖文件路径列表
        install_sequentially (bool):
            是否按顺序逐个安装依赖, 为 ``False`` 时先尝试批量安装, 失败后回退到按顺序安装
        use_uv (bool):
            是否使用 uv 安装依赖
        custom_env (dict[str, str] | None):
            环境变量字典

    Returns:
        list[Exception]: 安装依赖时出现的错误
    """
    comfyui_root_path = comfyui_root_path.resolve()
    req_paths = [req.resolve() for req in req_list]
    task_sum = len(req_paths)
    install_script_paths = [req_path for req_path in req_paths if (req_path.parent / "install.py").is_file()]
    install_script_sum = len(install_script_paths)
    install_script_index = {req_path: count for count, req_path in enumerate(install_script_paths, start=1)}
    if custom_env is None:
        custom_env = os.environ.copy()

    custom_env = append_python_path(
        new_path=comfyui_root_path,
        origin_env=custom_env,
    )

    err: list[Exception] = []

    def install_one_requirement(
        req_path: Path,
        count: int,
    ) -> None:
        name = req_path.parent.name
        logger.info("[%s/%s] 安装 %s 的依赖中", count, task_sum, name)
        try:
            install_requirements(
                path=req_path,
                use_uv=use_uv,
                cwd=req_path.parent,
                custom_env=custom_env,
            )
        except RuntimeError as e:
            err.append(e)
            logger.error("[%s/%s] 安装 %s 的依赖失败: %s", count, task_sum, name, e)

    def run_one_install_script(
        req_path: Path,
        count: int,
    ) -> None:
        name = req_path.parent.name
        installer_script = req_path.parent / "install.py"
        logger.info("[%s/%s] 执行 %s 的安装脚本中", count, install_script_sum, name)
        try:
            run_cmd(
                [Path(sys.executable).as_posix(), installer_script.as_posix()],
                cwd=req_path.parent,
                custom_env=custom_env,
            )
        except RuntimeError as e:
            err.append(e)
            logger.info("[%s/%s] 执行 %s 的安装脚本时发生错误: %s", count, install_script_sum, name, e)

    def run_install_script_for_requirement(req_path: Path) -> None:
        install_script_count = install_script_index.get(req_path)
        if install_script_count is not None:
            run_one_install_script(req_path, install_script_count)

    def install_requirements_sequentially() -> None:
        for count, req_path in enumerate(req_paths, start=1):
            install_one_requirement(req_path, count)
            run_install_script_for_requirement(req_path)

    def run_install_scripts_sequentially() -> None:
        install_script_names = ", ".join(req_path.parent.name for req_path in install_script_paths)
        if len(install_script_paths) > 0:
            logger.info("执行以下 ComfyUI 组件的安装脚本中: %s", install_script_names)
        for count, req_path in enumerate(install_script_paths, start=1):
            run_one_install_script(req_path, count)

    batch_requirement_names = ", ".join(req_path.parent.name for req_path in req_paths)
    if install_sequentially:
        install_requirements_sequentially()
    elif req_paths:
        try:
            logger.info("批量安装以下 ComfyUI 组件的依赖中: %s", batch_requirement_names)
            install_requirements(
                path=req_paths,
                use_uv=use_uv,
                cwd=comfyui_root_path,
                custom_env=custom_env,
            )
            logger.info("批量安装以下 ComfyUI 组件的依赖完成: %s", batch_requirement_names)
            run_install_scripts_sequentially()
        except RuntimeError as e:
            logger.warning("批量安装以下 ComfyUI 组件的依赖失败, 回退到按顺序安装: %s, 错误: %s", batch_requirement_names, e)
            install_requirements_sequentially()

    return err
