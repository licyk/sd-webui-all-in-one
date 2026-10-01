"""ComfyUI 环境检查入口"""

from pathlib import Path
from collections.abc import Callable

from sd_webui_all_in_one.pkg_manager import install_requirements
from sd_webui_all_in_one.utils import (
    print_divider,
)
from sd_webui_all_in_one.package_analyzer import (
    is_package_installed,
    validate_requirements,
)
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.env_check.shared import logger
from sd_webui_all_in_one.env_check.comfyui_env_analyze.models import (
    ComponentEnvironmentDetails,
    ComfyUIConflictGroup,
    ComfyUIConflictAnalysisResult,
)
from sd_webui_all_in_one.env_check.comfyui_env_analyze.environment import (
    create_comfyui_environment_dict,
    update_comfyui_component_requires_list,
    update_comfyui_component_missing_requires_list,
    update_comfyui_component_conflict_requires_list,
    get_comfyui_component_requires_list,
    statistical_need_install_require_component,
    collect_conflict_components,
    fitter_has_version_package,
)
from sd_webui_all_in_one.env_check.comfyui_env_analyze.conflict_detection import (
    detect_conflict_package_from_list,
)
from sd_webui_all_in_one.env_check.comfyui_env_analyze.resolution import (
    resolve_conflict_components,
)
from sd_webui_all_in_one.env_check.comfyui_env_analyze.reporting import (
    format_conflict_info,
    format_conflict_resolution_info,
    display_comfyui_environment_dict,
    display_check_result,
)
from sd_webui_all_in_one.env_check.comfyui_env_analyze.actions import (
    _select_conflict_action,
    _create_disable_component_callback,
    _disable_conflict_components,
    _install_component_requirements,
)


def process_comfyui_env_analysis(
    comfyui_root_path: Path,
) -> tuple[dict[str, ComponentEnvironmentDetails], list[Path], list[ComfyUIConflictGroup]]:
    """分析 ComfyUI 环境

    Args:
        comfyui_root_path (Path):
            ComfyUI 根目录
    Returns:
        (tuple[dict[str, ComponentEnvironmentDetails], list[Path], list[ComfyUIConflictGroup]]):
            ComfyUI 环境组件信息, 缺失依赖的依赖表, 结构化冲突信息

    Raises:
        FileNotFoundError:
            ComfyUI 依赖文件缺失 / 自定义节点文件夹未找到时
    """
    if not (comfyui_root_path / "requirements.txt").exists():
        logger.error("ComfyUI 依赖文件缺失, 请检查 ComfyUI 是否安装完整")
        raise FileNotFoundError("ComfyUI 依赖文件缺失, 请检查 ComfyUI 是否安装完整")

    if not (comfyui_root_path / "custom_nodes").exists():
        logger.error("ComfyUI 自定义节点文件夹未找到, 请检查 ComfyUI 是否安装完整")
        raise FileNotFoundError("ComfyUI 自定义节点文件夹未找到, 请检查 ComfyUI 是否安装完整")

    env_data = create_comfyui_environment_dict(comfyui_root_path)
    update_comfyui_component_requires_list(env_data)
    update_comfyui_component_missing_requires_list(env_data)
    pkg_list = get_comfyui_component_requires_list(env_data)
    has_version_pkg = fitter_has_version_package(pkg_list)
    conflict_pkg = detect_conflict_package_from_list(has_version_pkg)
    update_comfyui_component_conflict_requires_list(env_data, conflict_pkg)
    req_list = statistical_need_install_require_component(env_data)
    conflicts = collect_conflict_components(env_data, conflict_pkg)
    return env_data, req_list, conflicts


def check_comfyui_component_dependencies(
    comfyui_root_path: Path,
) -> ComfyUIConflictAnalysisResult:
    """检查 ComfyUI 组件依赖状态，不执行依赖修复。

    Args:
        comfyui_root_path (Path):
            ComfyUI 根目录。

    Returns:
        ComfyUIConflictAnalysisResult: ComfyUI 组件依赖检查结果。

    Raises:
        FileNotFoundError: ComfyUI 依赖文件缺失 / 自定义节点文件夹未找到时抛出。
    """
    env_data, req_list, conflicts = process_comfyui_env_analysis(comfyui_root_path)
    conflict_info = format_conflict_info(conflicts)
    has_missing_requires = any(details.get("has_missing_requires", False) for details in env_data.values())
    has_conflict_requires = any(details.get("has_conflict_requires", False) for details in env_data.values())
    # 保留数量相同时, 优先保留冲突依赖已被当前环境满足的组件, 以减少对现有环境的改动
    preferred_components = [
        component_name for component_name, details in env_data.items() if details.get("conflict_requires") and all(is_package_installed(package) for package in details["conflict_requires"])
    ]
    conflict_resolution = resolve_conflict_components(conflicts, preferred_components=preferred_components)
    return {
        "components": env_data,
        "requirement_paths": req_list,
        "conflicts": conflicts,
        "conflict_info": conflict_info,
        "has_missing_requires": has_missing_requires,
        "has_conflict_requires": has_conflict_requires,
        "conflict_resolution": conflict_resolution,
    }


def comfyui_conflict_analyzer(
    comfyui_root_path: Path,
    install_conflict_component_requirement: bool = False,
    disable_conflict_component: bool = False,
    interactive_mode: bool = False,
    use_uv: bool = True,
    custom_env: dict[str, str] | None = None,
    disable_component_callback: Callable[[str], None] | None = None,
) -> None:
    """检查并安装 ComfyUI 的依赖环境

    Args:
        comfyui_root_path (Path):
            ComfyUI 根目录
        install_conflict_component_requirement (bool):
            检测到冲突依赖时是否按顺序安装组件依赖
        disable_conflict_component (bool):
            检测到冲突依赖时是否禁用冲突组件 (保留尽可能多的组件) 并继续安装依赖, 优先于 ``install_conflict_component_requirement``
        interactive_mode (bool):
            是否启用交互模式, 当检测到冲突依赖时将询问处理方式
        use_uv (bool):
            是否使用 uv 安装依赖
        custom_env (dict[str, str] | None):
            环境变量字典
        disable_component_callback (Callable[[str], None] | None):
            禁用单个组件的函数, 未指定时使用 ComfyUI 扩展管理的禁用方式

    Raises:
        AggregateError:
            禁用冲突组件或安装依赖出现错误时
    """
    logger.info("检测 ComfyUI 环境中")
    analysis = check_comfyui_component_dependencies(comfyui_root_path)
    env_data = analysis["components"]
    req_list = analysis["requirement_paths"]
    conflict_info = analysis["conflict_info"]

    if logger.level <= 10:
        display_comfyui_environment_dict(env_data)
        display_check_result(req_list, conflict_info)

    err: list[Exception] = []
    has_conflict = len(conflict_info) > 0
    if has_conflict:
        resolution = analysis["conflict_resolution"]
        resolution_info = format_conflict_resolution_info(resolution)
        logger.warning("检测到当前 ComfyUI 环境中安装的插件之间存在依赖冲突情况, 该问题并非致命, 但建议只保留一个插件, 否则部分功能可能无法正常使用")
        logger.warning("您可以选择按顺序安装依赖, 由于这将向环境中安装不符合版本要求的组件, 您将无法完全解决此问题, 但可避免组件由于依赖缺失而无法启动的情况")
        if resolution["disable_components"]:
            logger.warning("您也可以选择禁用部分冲突组件, 在保留尽可能多组件的前提下消除冲突, 再继续安装依赖")
        logger.warning("检测到冲突的依赖:")
        print_divider("=")
        print(conflict_info)
        if resolution_info:
            print_divider("-")
            print(resolution_info)
        print_divider("=")

        action = _select_conflict_action(
            resolution=resolution,
            install_conflict_component_requirement=install_conflict_component_requirement,
            disable_conflict_component=disable_conflict_component,
            interactive_mode=interactive_mode,
        )
        if action == "disable":
            if disable_component_callback is None:
                disable_component_callback = _create_disable_component_callback(comfyui_root_path)
            err.extend(_disable_conflict_components(resolution["disable_components"], disable_component_callback))

            logger.info("重新检测 ComfyUI 环境中")
            analysis = check_comfyui_component_dependencies(comfyui_root_path)
            req_list = analysis["requirement_paths"]
            conflict_info = analysis["conflict_info"]
            has_conflict = len(conflict_info) > 0
            if has_conflict:
                logger.warning("禁用冲突组件后仍存在依赖冲突:")
                print_divider("=")
                print(conflict_info)
                print_divider("=")
                if interactive_mode:
                    install_conflict = input("是否按顺序安装冲突组件依赖 (y/N): ").strip().lower() in ["yes", "y"]
                else:
                    install_conflict = install_conflict_component_requirement
                action = "install" if install_conflict else "skip"
            else:
                logger.info("禁用冲突组件后已不存在依赖冲突, 继续安装依赖")

        if action == "skip":
            logger.info("忽略警告并继续启动 ComfyUI")
            if err:
                raise AggregateError("禁用 ComfyUI 冲突组件时出现错误", err)
            return

    err.extend(
        _install_component_requirements(
            comfyui_root_path=comfyui_root_path,
            req_list=req_list,
            install_sequentially=has_conflict,
            use_uv=use_uv,
            custom_env=custom_env,
        )
    )

    if err:
        raise AggregateError("安装 ComfyUI 依赖时出现错误", err)

    logger.info("ComfyUI 环境检查完成")


def check_comfyui_manager_dependence(
    comfyui_root_path: Path,
    use_uv: bool = True,
    custom_env: dict[str, str] | None = None,
) -> None:
    """检查 ComfyUI Manager 依赖

    Args:
        comfyui_root_path (Path):
            ComfyUI 根目录
        use_uv (bool):
            是否使用 uv 安装依赖
        custom_env (dict[str, str] | None):
            环境变量字典

    Raises:
        RuntimeError:
            安装 ComfyUI Manager 依赖发生错误时
    """
    comfyui_manager_requirement = comfyui_root_path / "manager_requirements.txt"
    if not comfyui_manager_requirement.is_file():
        logger.debug("ComfyUI Manager 依赖表不存在, 跳过 ComfyUI Manager 依赖检查")
        return

    logger.info("检查 ComfyUI Manager 依赖中")
    if not validate_requirements(comfyui_manager_requirement):
        logger.info("安装 ComfyUI Manager 依赖中")
        try:
            install_requirements(
                path=comfyui_manager_requirement,
                use_uv=use_uv,
                custom_env=custom_env,
                cwd=comfyui_root_path,
            )
            logger.info("安装 ComfyUI Manager 依赖完成")
        except RuntimeError as e:
            logger.error("安装 ComfyUI Manager 依赖出现错误: %s", e)
            raise RuntimeError(f"安装 ComfyUI Manager 依赖出现错误: {e}") from e
    else:
        logger.info("ComfyUI Manager 依赖检查完成")
