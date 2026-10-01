"""ComfyUI 环境组件信息收集"""

import posixpath
from pathlib import Path
from urllib.parse import (
    unquote,
    urlsplit,
)

from sd_webui_all_in_one.utils import (
    remove_duplicate_object_from_list,
)
from sd_webui_all_in_one.package_analyzer import (
    EntryKind,
    Requirement,
    RequirementEntry,
    UndefinedEnvironmentName,
    is_package_installed,
    normalize_name,
    parse_requirements_file,
)
from sd_webui_all_in_one.env_check.shared import logger
from sd_webui_all_in_one.env_check.comfyui_env_analyze.models import (
    ComponentType,
    ComfyUIEnvironmentComponent,
    ComfyUIConflictItem,
    ComfyUIConflictGroup,
)


def _guess_name_from_vcs_url(
    url: str,
) -> str | None:
    """从 VCS URL 的仓库名猜测软件包名

    仓库名与软件包名并不一定一致, 仅在 URL 未通过 ``#egg=`` 声明软件包名时作为兜底.

    Args:
        url (str):
            VCS URL, 如 ``git+https://github.com/user/repo.git@main``

    Returns:
        (str | None):
            猜测的软件包名, 无法提取时为 ``None``
    """
    path = urlsplit(url).path
    if "@" in path:
        path = path.rsplit("@", 1)[0]
    name = posixpath.basename(unquote(path).rstrip("/"))
    if name.endswith(".git"):
        name = name[:-4]
    return name or None


def _requirement_entry_to_declaration(
    entry: RequirementEntry,
) -> str | None:
    """将依赖文件条目转换为不含 extras 与环境标记的软件包声明

    Args:
        entry (RequirementEntry):
            依赖文件条目

    Returns:
        (str | None):
            软件包声明, 如 ``numpy<2``; 无法确定软件包名时为 ``None``
    """
    if entry.kind == EntryKind.NAMED and entry.requirement is not None:
        requirement = entry.requirement
        name = requirement.name.lower()
        return name if requirement.url is not None else f"{name}{requirement.specifier}"

    name = entry.name
    if name is None and entry.vcs is not None and entry.url is not None:
        name = _guess_name_from_vcs_url(entry.url)
    if name is None:
        return None

    name = name.lower()
    if entry.version is not None and not entry.editable:
        return f"{name}=={entry.version}"
    return name


def read_requirement_declarations(
    requirement_path: Path,
) -> list[str]:
    """读取依赖文件, 返回适用于当前环境的软件包声明列表

    按 requirements 文件格式解析 (含 ``-r`` 引用的嵌套文件, ``-e`` 可编辑条目, URL 与本地路径条目).
    声明了 ``# skip_verify`` 或环境标记不适用于当前环境的条目会被排除;
    无法解析的行与无法确定软件包名的条目只产生警告.

    Args:
        requirement_path (Path):
            依赖文件路径

    Returns:
        list[str]:
            软件包声明列表, 每个条目对应一项, 如 ``["torch==2.3.0", "protobuf>=4.25.3,<5"]``

    Raises:
        OSError:
            依赖文件不存在或无法读取时
        UnicodeDecodeError:
            依赖文件无法解码时
    """
    parsed = parse_requirements_file(requirement_path)
    for diagnostic in parsed.diagnostics:
        if diagnostic.severity == "error":
            logger.warning("%s, 已跳过", diagnostic)
        else:
            logger.debug("%s", diagnostic)

    declarations: list[str] = []
    for entry in parsed.entries:
        if entry.skip_verify:
            continue
        try:
            if not entry.applies_to():
                continue
        except UndefinedEnvironmentName as e:
            logger.warning("%s: 无法对 '%s' 的环境标记求值, 已跳过: %s", entry.source, entry, e)
            continue
        declaration = _requirement_entry_to_declaration(entry)
        if declaration is None:
            logger.warning("%s: 无法确定 '%s' 的软件包名, 已跳过该条目的检查", entry.source, entry)
            continue
        declarations.append(declaration)

    return declarations


def _has_version_constraint(
    package: str,
) -> bool:
    """判断软件包声明是否带有版本约束 (URL 依赖视为带有版本约束)"""
    requirement = Requirement.try_parse(package)
    return requirement is not None and (requirement.url is not None or bool(requirement.specifier))


def _package_name(
    package: str,
) -> str:
    """获取软件包声明中规范化后的软件包名, 声明无法解析时按整个字符串规范化"""
    requirement = Requirement.try_parse(package)
    return requirement.normalized_name if requirement is not None else normalize_name(package.strip())


def create_comfyui_environment_dict(
    comfyui_path: Path,
) -> ComfyUIEnvironmentComponent:
    """创建 ComfyUI 环境组件表字典

    Args:
        comfyui_path (Path):
            ComfyUI 根路径

    Returns:
        ComfyUIEnvironmentComponent:
            ComfyUI 环境组件表字典
    """
    comfyui_env_data: ComfyUIEnvironmentComponent = {
        "ComfyUI": {
            "requirement_path": comfyui_path / "requirements.txt",
            "component_type": "core",
            "is_disabled": False,
            "requires": [],
            "has_missing_requires": False,
            "missing_requires": [],
            "has_conflict_requires": False,
            "conflict_requires": [],
        },
    }

    custom_nodes_path = comfyui_path / "custom_nodes"
    for custom_node in custom_nodes_path.iterdir():
        if custom_node.is_file():
            continue

        custom_node_requirement_path = custom_node / "requirements.txt"
        custom_node_is_disabled = custom_node.name.endswith(".disabled")

        comfyui_env_data[custom_node.name] = {
            "requirement_path": custom_node_requirement_path if custom_node_requirement_path.is_file() else None,
            "component_type": "extension",
            "is_disabled": custom_node_is_disabled,
            "requires": [],
            "has_missing_requires": False,
            "missing_requires": [],
            "has_conflict_requires": False,
            "conflict_requires": [],
        }

    return comfyui_env_data


def update_comfyui_environment_dict(
    env_data: ComfyUIEnvironmentComponent,
    component_name: str,
    requirement_path: Path | None = None,
    component_type: ComponentType | None = None,
    is_disabled: bool | None = None,
    requires: list[str] | None = None,
    has_missing_requires: bool | None = None,
    missing_requires: list[str] | None = None,
    has_conflict_requires: bool | None = None,
    conflict_requires: list[str] | None = None,
) -> None:
    """更新 ComfyUI 环境组件表字典

    Args:
        env_data (ComfyUIEnvironmentComponent):
            ComfyUI 环境组件表字典
        component_name (str):
            ComfyUI 组件名称
        requirement_path (Path | None):
            ComfyUI 组件依赖文件路径
        component_type (ComponentType | None):
            组件类型
        is_disabled (bool | None):
            ComfyUI 组件是否被禁用
        requires (list[str] | None):
            ComfyUI 组件需要的依赖列表
        has_missing_requires (bool | None):
            ComfyUI 组件是否存在缺失依赖
        missing_requires (list[str] | None):
            ComfyUI 组件缺失依赖列表
        has_conflict_requires (bool | None):
            ComfyUI 组件是否存在冲突依赖
        conflict_requires (list[str] | None):
            ComfyUI 组件冲突依赖列表
    """
    current = env_data.get(
        component_name,
        {
            "requirement_path": None,
            "is_disabled": False,
            "component_type": None,
            "requires": [],
            "has_missing_requires": False,
            "missing_requires": [],
            "has_conflict_requires": False,
            "conflict_requires": [],
        },
    )
    env_data[component_name] = {
        "requirement_path": requirement_path if requirement_path is not None else current.get("requirement_path"),
        "component_type": component_type if component_type is not None else current.get("component_type", "core"),
        "is_disabled": is_disabled if is_disabled is not None else current.get("is_disabled", False),
        "requires": requires if requires is not None else current.get("requires", []),
        "has_missing_requires": has_missing_requires if has_missing_requires is not None else current.get("has_missing_requires", False),
        "missing_requires": missing_requires if missing_requires is not None else current.get("missing_requires", []),
        "has_conflict_requires": has_conflict_requires if has_conflict_requires is not None else current.get("has_conflict_requires", False),
        "conflict_requires": conflict_requires if conflict_requires is not None else current.get("conflict_requires", []),
    }


def update_comfyui_component_requires_list(
    env_data: ComfyUIEnvironmentComponent,
) -> None:
    """更新 ComfyUI 环境组件表字典, 根据字典中的 requirement_path 确定 Python 软件包版本声明文件, 并解析后写入 requires 字段

    Args:
        env_data (ComfyUIEnvironmentComponent):
            ComfyUI 环境组件表字典
    """
    for component_name, details in env_data.items():
        if details.get("is_disabled"):
            continue

        requirement_path = details.get("requirement_path")
        if requirement_path is None:
            continue

        try:
            requires = read_requirement_declarations(requirement_path)
        except (OSError, UnicodeDecodeError) as e:
            # 单个组件的依赖表损坏不应中断整个环境分析, 但需要让用户知道该组件未被检查
            logger.error("读取 '%s' 的依赖表 '%s' 失败, 跳过该组件的依赖检查: %s", component_name, requirement_path, e)
            continue

        update_comfyui_environment_dict(
            env_data=env_data,
            component_name=component_name,
            requires=requires,
        )


def update_comfyui_component_missing_requires_list(
    env_data: ComfyUIEnvironmentComponent,
) -> None:
    """更新 ComfyUI 环境组件表字典, 根据字典中的 requires 检查缺失的 Python 软件包, 并保存到 missing_requires 字段和设置 has_missing_requires 状态

    Args:
        env_data (ComfyUIEnvironmentComponent):
            ComfyUI 环境组件表字典
    """
    for component_name, details in env_data.items():
        if details.get("is_disabled"):
            continue

        requires = details.get("requires")
        has_missing_requires = False
        missing_requires = []

        for package in requires:
            if not is_package_installed(package):
                has_missing_requires = True
                missing_requires.append(package)

        update_comfyui_environment_dict(
            env_data=env_data,
            component_name=component_name,
            has_missing_requires=has_missing_requires,
            missing_requires=missing_requires,
        )


def update_comfyui_component_conflict_requires_list(
    env_data: ComfyUIEnvironmentComponent,
    conflict_package_list: list[str],
) -> None:
    """更新 ComfyUI 环境组件表字典, 根据 conflicconflict_package_listt_package 检查 ComfyUI 组件冲突的 Python 软件包, 并保存到 conflict_requires 字段和设置 has_conflict_requires 状态

    Args:
        env_data (ComfyUIEnvironmentComponent):
            ComfyUI 环境组件表字典
        conflict_package_list (list[str]):
            冲突的 Python 软件包列表
    """
    for component_name, details in env_data.items():
        if details.get("is_disabled"):
            continue

        requires = details.get("requires")
        has_conflict_requires = False
        conflict_requires: list[str] = []

        for conflict_package in conflict_package_list:
            for package in requires:
                if _has_version_constraint(package) and _package_name(conflict_package) == _package_name(package):
                    has_conflict_requires = True
                    conflict_requires.append(package)

        update_comfyui_environment_dict(
            env_data=env_data,
            component_name=component_name,
            has_conflict_requires=has_conflict_requires,
            conflict_requires=conflict_requires,
        )


def get_comfyui_component_requires_list(
    env_data: ComfyUIEnvironmentComponent,
) -> list[str]:
    """从 ComfyUI 环境组件表字典读取所有组件的 requires

    Args:
        env_data (ComfyUIEnvironmentComponent):
            ComfyUI 环境组件表字典

    Returns:
        list[str]:
            ComfyUI 环境组件的 Python 软件包列表
    """
    package_list = []
    for _, details in env_data.items():
        if details.get("is_disabled"):
            continue

        package_list += details.get("requires")

    return remove_duplicate_object_from_list(package_list)


def statistical_need_install_require_component(
    env_data: ComfyUIEnvironmentComponent,
) -> list[Path]:
    """根据 ComfyUI 环境组件表字典中的 has_missing_requires 和 has_conflict_requires 字段确认需要安装依赖的列表

    Args:
        env_data (ComfyUIEnvironmentComponent):
            ComfyUI 环境组件表字典

    Returns:
        list[Path]:
            ComfyUI 环境组件的依赖文件路径列表
    """
    requirement_list = []
    for _, details in env_data.items():
        requirement_path = details.get("requirement_path")
        if requirement_path is not None and (details.get("has_missing_requires") or details.get("has_conflict_requires")):
            requirement_list.append(requirement_path)

    return requirement_list


def collect_conflict_components(
    env_data: ComfyUIEnvironmentComponent,
    conflict_package_list: list[str],
) -> list[ComfyUIConflictGroup]:
    """收集 ComfyUI 组件冲突信息并返回结构化数据。

    Args:
        env_data (ComfyUIEnvironmentComponent):
            ComfyUI 环境组件表字典
        conflict_package_list (list[str]):
            冲突的软件包名称列表

    Returns:
        list[ComfyUIConflictGroup]:
            结构化的冲突组列表
    """
    conflict_package_list = remove_duplicate_object_from_list([_package_name(x) for x in conflict_package_list])
    conflicts: list[ComfyUIConflictGroup] = []

    for conflict_package in conflict_package_list:
        group_components: list[ComfyUIConflictItem] = []
        for component_name, details in env_data.items():
            for conflict_component_package in details.get("conflict_requires"):
                if _package_name(conflict_component_package) == conflict_package:
                    group_components.append(
                        {
                            "component": component_name,
                            "component_type": details.get("component_type"),
                            "requirement": conflict_component_package,
                        }
                    )

        if group_components:
            conflicts.append(
                {
                    "package": conflict_package,
                    "components": group_components,
                }
            )

    return conflicts


def fitter_has_version_package(
    package_list: list[str],
) -> list[str]:
    """过滤不包含版本的 Python 软件包, 仅保留包含版本号声明的 Python 软件包

    Args:
        package_list (list[str]): Python 软件包列表

    Returns:
        list[str]: 仅包含版本号的 Python 软件包列表
    """
    return [p for p in package_list if _has_version_constraint(p)]
