"""ComfyUI 环境检查结果展示"""

from pathlib import Path

from sd_webui_all_in_one.env_check.shared import logger
from sd_webui_all_in_one.env_check.comfyui_env_analyze.models import (
    ComfyUIEnvironmentComponent,
    ComfyUIConflictGroup,
    ComfyUIConflictResolution,
)


def format_conflict_info(
    conflicts: list[ComfyUIConflictGroup],
) -> str:
    """将结构化冲突组渲染为文本说明。

    Args:
        conflicts (list[ComfyUIConflictGroup]):
            冲突组信息列表

    Returns:
        冲突信息文本
    """
    content: list[str] = []
    for conflict in conflicts:
        content.append(f"{conflict['package']}:")
        for item in conflict["components"]:
            component_type = item.get("component_type")
            type_suffix = f" ({component_type})" if component_type else ""
            content.append(f" - {item['component']}{type_suffix}: {item['requirement']}")
        content.append("")

    if len(content) > 0 and content[-1] == "":
        content.pop()

    return "\n".join(content)


def format_conflict_resolution_info(
    resolution: ComfyUIConflictResolution,
) -> str:
    """将冲突组件禁用方案渲染为文本说明。

    Args:
        resolution (ComfyUIConflictResolution):
            冲突组件禁用方案

    Returns:
        str: 禁用方案文本
    """
    content: list[str] = []
    if resolution["disable_details"]:
        content.append(f"可禁用以下 {len(resolution['disable_components'])} 个组件以解决冲突 (保留 {len(resolution['keep_components'])} 个冲突相关组件):")
        for detail in resolution["disable_details"]:
            packages = ", ".join(detail["packages"])
            conflicts_with = ", ".join(detail["conflicts_with"])
            if detail["reason"] == "self_conflict":
                content.append(f" - {detail['component']}: 组件自身的依赖声明存在冲突 ({packages})")
            elif detail["reason"] == "conflicts_with_protected":
                content.append(f" - {detail['component']}: 与必须保留的组件 {conflicts_with} 存在冲突 ({packages})")
            else:
                content.append(f" - {detail['component']}: 与 {conflicts_with} 存在冲突 ({packages})")
        if not resolution["is_optimal"]:
            content.append("冲突关系较复杂, 以上为近似方案, 可能不是保留组件最多的方案")

    if resolution["unresolvable_conflicts"]:
        content.append("以下冲突无法通过禁用扩展解决:")
        for edge in resolution["unresolvable_conflicts"]:
            content.append(f" - {edge['package']}: {edge['component']} ({edge['requirement']}) <-> {edge['other_component']} ({edge['other_requirement']})")

    return "\n".join(content)


def display_comfyui_environment_dict(
    env_data: ComfyUIEnvironmentComponent,
) -> None:
    """列出 ComfyUI 环境组件字典内容

    Args:
        env_data (ComfyUIEnvironmentComponent): ComfyUI 环境组件表字典
    """
    logger.debug("ComfyUI 环境组件表")
    for component_name, details in env_data.items():
        logger.debug("Component: %s", component_name)
        logger.debug(" - requirement_path: %s", details["requirement_path"])
        logger.debug(" - is_disabled: %s", details["is_disabled"])
        logger.debug(" - requires: %s", details["requires"])
        logger.debug(" - has_missing_requires: %s", details["has_missing_requires"])
        logger.debug(" - missing_requires: %s", details["missing_requires"])
        logger.debug(" - has_conflict_requires: %s", details["has_conflict_requires"])
        logger.debug(" - conflict_requires: %s", details["conflict_requires"])
        print()


def display_check_result(
    requirement_list: list[Path],
    conflict_result: str,
) -> None:
    """显示 ComfyUI 运行环境检查结果

    Args:
        requirement_list (list[Path]):
            ComfyUI 组件依赖文件路径列表
        conflict_result (str):
            冲突组件统计信息
    """
    if len(requirement_list) > 0:
        logger.debug("需要安装 ComfyUI 组件列表")
        for requirement in requirement_list:
            component_name = requirement.parent.name
            logger.debug("%s:", component_name)
            logger.debug(" - %s", requirement)
        print()

    if len(conflict_result) > 0:
        logger.debug("ComfyUI 冲突组件: \n%s", conflict_result)
