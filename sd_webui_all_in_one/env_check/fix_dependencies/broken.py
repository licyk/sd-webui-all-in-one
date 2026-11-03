"""元数据已损坏的软件包检查与修复"""

import shutil

from sd_webui_all_in_one.pkg_manager import pip_install
from sd_webui_all_in_one.package_analyzer import (
    find_broken_distributions,
    get_package_version_from_library,
)
from sd_webui_all_in_one.env_check.shared import logger


def repair_broken_distributions(
    use_uv: bool = True,
    custom_env: dict[str, str] | None = None,
) -> None:
    """检测并修复元数据已损坏的软件包

    ``.dist-info`` 目录缺少 ``METADATA`` 或其中没有 ``Version`` 时, ``importlib.metadata`` 读到的版本号为 ``None``,
    而 uv 根据目录名仍认为软件包已安装, 缺少 ``RECORD`` 时 Pip 也无法卸载, 普通的安装命令无法修复.

    修复方式为删除损坏的 ``.dist-info`` 目录 (只包含元数据, 不影响软件包文件), 再按目录名记录的版本重新安装该软件包.
    同名软件包仍有正常的分发时 (例如残留的旧版元数据目录) 只删除损坏的目录, 不重新安装.

    Args:
        use_uv (bool):
            是否使用 uv 安装依赖
        custom_env (dict[str, str] | None):
            环境变量字典

    Raises:
        RuntimeError:
            删除损坏的元数据或重新安装软件包发生错误时
    """
    broken = find_broken_distributions()
    if not broken:
        return

    for item in broken:
        logger.warning("检测到元数据已损坏的软件包 '%s' (%s): %s", item.name or item.path.name, item.reason, item.path)

    for item in broken:
        try:
            shutil.rmtree(item.path)
        except OSError as e:
            logger.error("移除损坏的软件包元数据 '%s' 时出现错误: %s", item.path, e)
            raise RuntimeError(f"移除损坏的软件包元数据 '{item.path}' 时出现错误: {e}") from e

    packages: list[str] = []
    for item in broken:
        requirement = item.requirement
        if item.name is None or requirement is None:
            logger.warning("无法从 '%s' 确定软件包名, 已移除损坏的元数据但不会重新安装", item.path.name)
            continue
        if get_package_version_from_library(item.name) is not None:
            logger.info("软件包 '%s' 仍有正常的分发, 已移除残留的损坏元数据", item.name)
            continue
        if requirement not in packages:
            packages.append(requirement)

    if not packages:
        return

    logger.info("重新安装元数据已损坏的软件包中: %s", ", ".join(packages))
    try:
        pip_install(*packages, "--no-deps", use_uv=use_uv, custom_env=custom_env)
    except RuntimeError as e:
        logger.error("重新安装元数据已损坏的软件包出现错误: %s", e)
        raise RuntimeError(f"重新安装元数据已损坏的软件包 ({', '.join(packages)}) 时出现错误: {e}") from e
    logger.info("元数据已损坏的软件包修复完成")
