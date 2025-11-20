"""ComfyUI 环境检查工具"""

import sys
from pathlib import Path
from typing import TypedDict

from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.env_manager import install_requirements
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR
from sd_webui_all_in_one.utils import remove_duplicate_object_from_list
from sd_webui_all_in_one.package_analyzer.py_ver_cmp import PyWhlVersionComparison
from sd_webui_all_in_one.package_analyzer.pkg_check import (
    get_package_name,
    get_package_version,
    is_package_has_version,
    is_package_installed,
    parse_requirement_list,
    read_packages_from_requirements_file,
)


logger = get_logger(
    name="ComfyUI Env Check",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class ComponentEnvironmentDetails(TypedDict):
    """ComfyUI 组件的环境信息结构

    Attributes:
        requirement_path (str): 依赖文件路径
        is_disabled (bool): 组件是否禁用
        requires (list[str]): 需要的依赖列表
        has_missing_requires (bool): 是否存在缺失依赖
        missing_requires (list[str]): 具体缺失的依赖项
        has_conflict_requires (bool): 是否存在冲突依赖
        conflict_requires (list[str]): 具体冲突的依赖项
    """

    requirement_path: str
    """依赖文件路径"""

    is_disabled: bool
    """组件是否禁用"""

    requires: list[str]
    """需要的依赖列表"""

    has_missing_requires: bool
    """是否存在缺失依赖"""

    missing_requires: list[str]
    """具体缺失的依赖项"""

    has_conflict_requires: bool
    """是否存在冲突依赖"""

    conflict_requires: list[str]
    """具体冲突的依赖项"""


ComfyUIEnvironmentComponent = dict[str, ComponentEnvironmentDetails]
"""ComfyUI 环境组件表字典"""


def create_comfyui_environment_dict(
    comfyui_path: str | Path,
) -> ComfyUIEnvironmentComponent:
    """创建 ComfyUI 环境组件表字典

    Args:
        comfyui_path (str | Path): ComfyUI 根路径

    Returns:
        ComfyUIEnvironmentComponent: ComfyUI 环境组件表字典
    """
    comfyui_path = Path(comfyui_path) if not isinstance(comfyui_path, Path) and comfyui_path is not None else comfyui_path
    comfyui_env_data: ComfyUIEnvironmentComponent = {
        "ComfyUI": {
            "requirement_path": (comfyui_path / "requirements.txt").as_posix(),
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
        custom_node_is_disabled = True if custom_node.parent.as_posix().endswith(".disabled") else False

        comfyui_env_data[custom_node.name] = {
            "requirement_path": (custom_node_requirement_path.as_posix() if custom_node_requirement_path.exists() else None),
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
    requirement_path: str | None = None,
    is_disabled: bool | None = None,
    requires: list[str] | None = None,
    has_missing_requires: bool | None = None,
    missing_requires: list[str] | None = None,
    has_conflict_requires: bool | None = None,
    conflict_requires: list[str] | None = None,
) -> None:
    """更新 ComfyUI 环境组件表字典

    Args:
        env_data (ComfyUIEnvironmentComponent): ComfyUI 环境组件表字典
        component_name (str): ComfyUI 组件名称
        requirement_path (str | None): ComfyUI 组件依赖文件路径
        is_disabled (bool | None): ComfyUI 组件是否被禁用
        requires (list[str] | None): ComfyUI 组件需要的依赖列表
        has_missing_requires (bool | None): ComfyUI 组件是否存在缺失依赖
        missing_requires (list[str] | None): ComfyUI 组件缺失依赖列表
        has_conflict_requires (bool | None): ComfyUI 组件是否存在冲突依赖
        conflict_requires (list[str] | None): ComfyUI 组件冲突依赖列表
    """
    env_data[component_name] = {
        "requirement_path": (requirement_path if requirement_path else env_data.get(component_name).get("requirement_path")),
        "is_disabled": (is_disabled if is_disabled else env_data.get(component_name).get("is_disabled")),
        "requires": (requires if requires else env_data.get(component_name).get("requires")),
        "has_missing_requires": (has_missing_requires if has_missing_requires else env_data.get(component_name).get("has_missing_requires")),
        "missing_requires": (missing_requires if missing_requires else env_data.get(component_name).get("missing_requires")),
        "has_conflict_requires": (has_conflict_requires if has_conflict_requires else env_data.get(component_name).get("has_conflict_requires")),
        "conflict_requires": (conflict_requires if conflict_requires else env_data.get(component_name).get("conflict_requires")),
    }


def update_comfyui_component_requires_list(
    env_data: ComfyUIEnvironmentComponent,
) -> None:
    """更新 ComfyUI 环境组件表字典, 根据字典中的 requirement_path 确定 Python 软件包版本声明文件, 并解析后写入 requires 字段

    Args:
        env_data (ComfyUIEnvironmentComponent): ComfyUI 环境组件表字典
    """
    for component_name, details in env_data.items():
        if details.get("is_disabled"):
            continue

        requirement_path = details.get("requirement_path")
        if requirement_path is None:
            continue

        origin_requires = read_packages_from_requirements_file(requirement_path)
        requires = parse_requirement_list(origin_requires)
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
        env_data (ComfyUIEnvironmentComponent): ComfyUI 环境组件表字典
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


def update_comfyui_component_conflict_requires_list(env_data: ComfyUIEnvironmentComponent, conflict_package_list: list[str]) -> None:
    """更新 ComfyUI 环境组件表字典, 根据 conflicconflict_package_listt_package 检查 ComfyUI 组件冲突的 Python 软件包, 并保存到 conflict_requires 字段和设置 has_conflict_requires 状态

    Args:
        env_data (ComfyUIEnvironmentComponent): ComfyUI 环境组件表字典
        conflict_package_list (list[str]): 冲突的 Python 软件包列表
    """
    for component_name, details in env_data.items():
        if details.get("is_disabled"):
            continue

        requires = details.get("requires")
        has_conflict_requires = False
        conflict_requires: list[str] = []

        for conflict_package in conflict_package_list:
            for package in requires:
                if is_package_has_version(package) and get_package_name(conflict_package) == get_package_name(package):
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
        env_data (ComfyUIEnvironmentComponent): ComfyUI 环境组件表字典

    Returns:
        list[str]: ComfyUI 环境组件的 Python 软件包列表
    """
    package_list = []
    for _, details in env_data.items():
        if details.get("is_disabled"):
            continue

        package_list += details.get("requires")

    return remove_duplicate_object_from_list(package_list)


def statistical_need_install_require_component(
    env_data: ComfyUIEnvironmentComponent,
) -> list[str]:
    """根据 ComfyUI 环境组件表字典中的 has_missing_requires 和 has_conflict_requires 字段确认需要安装依赖的列表

    Args:
        env_data (ComfyUIEnvironmentComponent): ComfyUI 环境组件表字典

    Returns:
        list[str]: ComfyUI 环境组件的依赖文件路径列表
    """
    requirement_list = []
    for _, details in env_data.items():
        if details.get("has_missing_requires") or details.get("has_conflict_requires"):
            requirement_list.append(Path(details.get("requirement_path")).as_posix())

    return requirement_list


def statistical_has_conflict_component(env_data: ComfyUIEnvironmentComponent, conflict_package_list: list[str]) -> str:
    """根据 ComfyUI 环境组件表字典中的 conflict_requires 字段统计冲突的组件信息

    Args:
        env_data (ComfyUIEnvironmentComponent): ComfyUI 环境组件表字典

    Returns:
        str: ComfyUI 环境冲突的组件信息列表
    """
    content = []
    # 统一成下划线
    conflict_package_list = remove_duplicate_object_from_list([x.replace("-", "_") for x in conflict_package_list])
    for conflict_package in conflict_package_list:
        content.append(get_package_name(f"{conflict_package}:"))
        for component_name, details in env_data.items():
            for conflict_component_package in details.get("conflict_requires"):
                # 将中划线统一成下划线再对比
                conflict_component_package_format = get_package_name(conflict_component_package).replace("-", "_")
                conflict_package_format = conflict_package.replace("-", "_")
                if conflict_component_package_format == conflict_package_format:
                    content.append(f" - {component_name}: {conflict_component_package}")
        content.append("")
    return "\n".join([str(x) for x in (content[:-1] if len(content) > 0 and content[-1] == "" else content)])


def fitter_has_version_package(package_list: list[str]) -> list[str]:
    """过滤不包含版本的 Python 软件包, 仅保留包含版本号声明的 Python 软件包

    Args:
        package_list (list[str]): Python 软件包列表

    Returns:
        list[str]: 仅包含版本号的 Python 软件包列表
    """
    return [p for p in package_list if is_package_has_version(p)]


def detect_conflict_package(pkg1: str, pkg2: str) -> bool:
    """检测 Python 软件包版本号声明是否存在冲突

    Args:
        pkg1 (str): 第 1 个 Python 软件包名称
        pkg2 (str): 第 2 个 Python 软件包名称

    Returns:
        bool: 如果 Python 软件包版本声明出现冲突则返回`True`
    """
    # 进行 2 次循环, 第 2 次循环时交换版本后再进行判断
    for i in range(2):
        if i == 1:
            if pkg1 == pkg2:
                break
            else:
                pkg1, pkg2 = pkg2, pkg1

        ver1 = get_package_version(pkg1)
        ver2 = get_package_version(pkg2)
        logger.debug(
            "冲突依赖检测: pkg1: %s, pkg2: %s, ver1: %s, ver2: %s",
            pkg1,
            pkg2,
            ver1,
            ver2,
        )

        # >=, <=
        if ">=" in pkg1 and "<=" in pkg2:
            if PyWhlVersionComparison(ver1) > PyWhlVersionComparison(ver2):
                logger.debug("冲突依赖: %s, %s, 版本冲突: %s > %s", pkg1, pkg2, ver1, ver2)
                return True

        # >=, <
        if ">=" in pkg1 and "<" in pkg2 and "=" not in pkg2:
            if PyWhlVersionComparison(ver1) >= PyWhlVersionComparison(ver2):
                logger.debug("冲突依赖: %s, %s, 版本冲突: %s >= %s", pkg1, pkg2, ver1, ver2)
                return True

        # >, <=
        if ">" in pkg1 and "=" not in pkg1 and "<=" in pkg2:
            if PyWhlVersionComparison(ver1) >= PyWhlVersionComparison(ver2):
                logger.debug("冲突依赖: %s, %s, 版本冲突: %s >= %s", pkg1, pkg2, ver1, ver2)
                return True

        # >, <
        if ">" in pkg1 and "=" not in pkg1 and "<" in pkg2 and "=" not in pkg2:
            if PyWhlVersionComparison(ver1) >= PyWhlVersionComparison(ver2):
                logger.debug("冲突依赖: %s, %s, 版本冲突: %s >= %s", pkg1, pkg2, ver1, ver2)
                return True

        # >, ==
        if ">" in pkg1 and "=" not in pkg1 and "==" in pkg2:
            if PyWhlVersionComparison(ver1) >= PyWhlVersionComparison(ver2):
                logger.debug("冲突依赖: %s, %s, 版本冲突: %s >= %s", pkg1, pkg2, ver1, ver2)
                return True

        # >=, ==
        if ">=" in pkg1 and "==" in pkg2:
            if PyWhlVersionComparison(ver1) > PyWhlVersionComparison(ver2):
                logger.debug("冲突依赖: %s, %s, 版本冲突: %s > %s", pkg1, pkg2, ver1, ver2)
                return True

        # <, ==
        if "<" in pkg1 and "=" not in pkg1 and "==" in pkg2:
            if PyWhlVersionComparison(ver1) <= PyWhlVersionComparison(ver2):
                logger.debug("冲突依赖: %s, %s, 版本冲突: %s <= %s", pkg1, pkg2, ver1, ver2)
                return True

        # <=, ==
        if "<=" in pkg1 and "==" in pkg2:
            if PyWhlVersionComparison(ver1) < PyWhlVersionComparison(ver2):
                logger.debug("冲突依赖: %s, %s, 版本冲突: %s < %s", pkg1, pkg2, ver1, ver2)
                return True

        # !=, ==
        if "!=" in pkg1 and "==" in pkg2:
            if PyWhlVersionComparison(ver1) == PyWhlVersionComparison(ver2):
                logger.debug("冲突依赖: %s, %s, 版本冲突: %s == %s", pkg1, pkg2, ver1, ver2)
                return True

        # >, ~=
        if ">" in pkg1 and "=" not in pkg1 and "~=" in pkg2:
            if PyWhlVersionComparison(ver1) >= PyWhlVersionComparison(ver2):
                logger.debug("冲突依赖: %s, %s, 版本冲突: %s >= %s", pkg1, pkg2, ver1, ver2)
                return True

        # >=, ~=
        if ">=" in pkg1 and "~=" in pkg2:
            if PyWhlVersionComparison(ver1) > PyWhlVersionComparison(ver2):
                logger.debug("冲突依赖: %s, %s, 版本冲突: %s > %s", pkg1, pkg2, ver1, ver2)
                return True

        # <, ~=
        if "<" in pkg1 and "=" not in pkg1 and "~=" in pkg2:
            if PyWhlVersionComparison(ver1) <= PyWhlVersionComparison(ver2):
                logger.debug("冲突依赖: %s, %s, 版本冲突: %s <= %s", pkg1, pkg2, ver1, ver2)
                return True

        # <=, ~=
        if "<=" in pkg1 and "~=" in pkg2:
            if PyWhlVersionComparison(ver1) < PyWhlVersionComparison(ver2):
                logger.debug("冲突依赖: %s, %s, 版本冲突: %s < %s", pkg1, pkg2, ver1, ver2)
                return True

        # !=, ~=
        # 这个也没什么必要
        # if '!=' in pkg1 and '~=' in pkg2:
        #     if is_v1_c_eq_v2(ver1, ver2):
        #         logger.debug(
        #             '冲突依赖: %s, %s, 版本冲突: %s ~= %s',
        #             pkg1, pkg2, ver1, ver2)
        #         return True

        # ~=, == / ~=, ===
        if ("~=" in pkg1 and "==" in pkg2) or ("~=" in pkg1 and "===" in pkg2):
            if PyWhlVersionComparison(ver1) > PyWhlVersionComparison(ver2):
                logger.debug("冲突依赖: %s, %s, 版本冲突: %s > %s", pkg1, pkg2, ver1, ver2)
                return True

        # ~=, ~=
        # ~= 类似 >= V.N, == V.*, 所以该部分的比较没必要使用
        # if '~=' in pkg1 and '~=' in pkg2:
        #     if not is_v1_c_eq_v2(ver1, ver2):
        #         logger.debug(
        #             '冲突依赖: %s, %s, 版本冲突: %s !~= %s',
        #             pkg1, pkg2, ver1, ver2)
        #         return True

        # ==, == / ===, ===
        if ("==" in pkg1 and "==" in pkg2) or ("===" in pkg1 and "===" in pkg2):
            if PyWhlVersionComparison(ver1) != PyWhlVersionComparison(ver2):
                logger.debug("冲突依赖: %s, %s, 版本冲突: %s != %s", pkg1, pkg2, ver1, ver2)
                return True

    return False


def detect_conflict_package_from_list(package_list: list[str]) -> list[str]:
    """检测 Python 软件包版本声明列表中存在冲突的软件包

    Args:
        package_list (list[str]): Python 软件包版本声明列表

    Returns:
        list[str]: 冲突的 Python 软件包列表
    """
    conflict_package = []
    for i in package_list:
        for j in package_list:
            # 截取包名并将包名中的中划线统一成下划线
            pkg1 = get_package_name(i).replace("-", "_")
            pkg2 = get_package_name(j).replace("-", "_")
            if pkg1 == pkg2 and detect_conflict_package(i, j):
                conflict_package.append(get_package_name(i))

    return remove_duplicate_object_from_list(conflict_package)


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


def display_check_result(requirement_list: list[str], conflict_result: str) -> None:
    """显示 ComfyUI 运行环境检查结果

    Args:
        requirement_list (list[str]): ComfyUI 组件依赖文件路径列表
        conflict_result (str): 冲突组件统计信息
    """
    if len(requirement_list) > 0:
        logger.debug("需要安装 ComfyUI 组件列表")
        for requirement in requirement_list:
            component_name = requirement.split("/")[-2]
            logger.debug("%s:", component_name)
            logger.debug(" - %s", requirement)
        print()

    if len(conflict_result) > 0:
        logger.debug("ComfyUI 冲突组件: \n%s", conflict_result)


def process_comfyui_env_analysis(comfyui_root_path: Path | str) -> tuple[dict[str, ComponentEnvironmentDetails], list[str], str] | tuple[None, None, None]:
    """分析 ComfyUI 环境

    Args:
        comfyui_root_path (Path | str): ComfyUI 根目录
    Returns:
        (tuple[dict[str, ComponentEnvironmentDetails], list[str], str] | tuple[None, None, None]):
            ComfyUI 环境组件信息, 缺失依赖的依赖表, 冲突组件信息
    """
    comfyui_root_path = Path(comfyui_root_path) if not isinstance(comfyui_root_path, Path) and comfyui_root_path is not None else comfyui_root_path
    if not (comfyui_root_path / "requirements.txt").exists():
        logger.error("ComfyUI 依赖文件缺失, 请检查 ComfyUI 是否安装完整")
        return None, None, None

    if not (comfyui_root_path / "custom_nodes").exists():
        logger.error("ComfyUI 自定义节点文件夹未找到, 请检查 ComfyUI 是否安装完整")
        return None, None, None

    env_data = create_comfyui_environment_dict(comfyui_root_path)
    update_comfyui_component_requires_list(env_data)
    update_comfyui_component_missing_requires_list(env_data)
    pkg_list = get_comfyui_component_requires_list(env_data)
    has_version_pkg = fitter_has_version_package(pkg_list)
    conflict_pkg = detect_conflict_package_from_list(has_version_pkg)
    update_comfyui_component_conflict_requires_list(env_data, conflict_pkg)
    req_list = statistical_need_install_require_component(env_data)
    conflict_info = statistical_has_conflict_component(env_data, conflict_pkg)
    return env_data, req_list, conflict_info


def comfyui_conflict_analyzer(
    comfyui_root_path: Path | str,
    install_conflict_component_requirement: bool | None = False,
    use_uv: bool | None = True,
    debug_mode: bool | None = False,
) -> None:
    """检查并安装 ComfyUI 的依赖环境

    Args:
        comfyui_root_path (Path | str): ComfyUI 根目录
        install_conflict_component_requirement (bool | None): 检测到冲突依赖时是否按顺序安装组件依赖
        use_uv (bool | None): 是否使用 uv 安装依赖
        debug_mode (bool | None): 显示调试信息
    """
    logger.info("检测 ComfyUI 环境中")
    env_data, req_list, conflict_info = process_comfyui_env_analysis(comfyui_root_path)

    if debug_mode:
        display_comfyui_environment_dict(env_data)
        display_check_result(req_list, conflict_info)

    if len(conflict_info) > 0:
        logger.warning("检测到当前 ComfyUI 环境中安装的插件之间存在依赖冲突情况, 该问题并非致命, 但建议只保留一个插件, 否则部分功能可能无法正常使用")
        logger.warning("您可以选择按顺序安装依赖, 由于这将向环境中安装不符合版本要求的组件, 您将无法完全解决此问题, 但可避免组件由于依赖缺失而无法启动的情况")
        logger.warning("检测到冲突的依赖:")
        print(conflict_info)
        if not install_conflict_component_requirement:
            logger.info("忽略警告并继续启动 ComfyUI")
            return

    task_sum = len(req_list)
    count = 0
    for req in req_list:
        count += 1
        req_path = Path(req)
        name = req_path.parent.name
        installer_script = req_path / "install.py"
        logger.info("[%s/%s] 安装 %s 的依赖中", count, task_sum, name)
        try:
            install_requirements(
                path=req,
                use_uv=use_uv,
                cwd=req_path.parent,
            )
        except Exception as e:
            logger.error("[%s/%s] 安装 %s 的依赖失败: %s", count, task_sum, name, e)

        if installer_script.is_file():
            logger.info("[%s/%s] 执行 %s 的安装脚本中", count, task_sum, name)
            try:
                run_cmd(
                    [Path(sys.executable).as_posix(), installer_script.as_posix()],
                    cwd=req_path.parent,
                )
            except Exception as e:
                logger.info("[%s/%s] 执行 %s 的安装脚本时发生错误: %s", count, task_sum, name, e)

    logger.info("ComfyUI 环境检查完成")
