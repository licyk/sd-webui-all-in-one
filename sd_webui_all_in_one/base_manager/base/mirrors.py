"""自动镜像设置解析。"""

from typing import Any

from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.model_downloader import (
    ModelDownloadUrlType,
)
from sd_webui_all_in_one.utils import (
    network_gfw_test,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def resolve_auto_mirror_settings(
    auto_mirror: bool,
    use_pypi_mirror: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    use_hf_mirror: bool = False,
    custom_hf_mirror: str | list[str] | None = None,
    model_download_resource_type: ModelDownloadUrlType | None = None,
) -> dict[str, Any]:
    """根据网络环境解析并覆盖镜像源相关设置

    该函数为自动镜像源选择的核心逻辑, 供 CLI 和 API Server 共同使用。

    Args:
        auto_mirror (bool):
            是否启用自动镜像源选择
        use_pypi_mirror (bool):
            是否使用 PyPI 镜像源
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        use_hf_mirror (bool):
            是否使用 HuggingFace 镜像源
        custom_hf_mirror (str | list[str] | None):
            自定义 HuggingFace 镜像源
        model_download_resource_type (ModelDownloadUrlType | None):
            模型下载源类型

    Returns:
        dict[str, Any]:
            应用自动镜像源选择后的镜像源设置字典, 包含以下字段:
            - use_pypi_mirror: 是否使用 PyPI 镜像源
            - use_github_mirror: 是否使用 Github 镜像源
            - custom_github_mirror: 自定义 Github 镜像源
            - use_hf_mirror: 是否使用 HuggingFace 镜像源
            - custom_hf_mirror: 自定义 HuggingFace 镜像源
            - model_download_resource_type: 模型下载源类型
    """
    if not auto_mirror:
        logger.info("已禁用自动镜像源选择, 将遵守手动镜像源参数设置")
        return {
            "use_pypi_mirror": use_pypi_mirror,
            "use_github_mirror": use_github_mirror,
            "custom_github_mirror": custom_github_mirror,
            "use_hf_mirror": use_hf_mirror,
            "custom_hf_mirror": custom_hf_mirror,
            "model_download_resource_type": model_download_resource_type,
        }

    logger.info("启用自动镜像源选择, 将根据网络检测结果强制覆盖镜像源相关参数")
    use_mirror = not network_gfw_test()
    model_resource: ModelDownloadUrlType = "modelscope" if use_mirror else "huggingface"
    if use_mirror:
        logger.info("网络检测结果: 将强制使用镜像源, 模型下载源设置为 ModelScope")
    else:
        logger.info("网络检测结果: 将强制使用官方源, 模型下载源设置为 HuggingFace")

    return {
        "use_pypi_mirror": use_mirror,
        "use_github_mirror": use_mirror,
        "custom_github_mirror": None,
        "use_hf_mirror": use_mirror,
        "custom_hf_mirror": None,
        "model_download_resource_type": model_resource,
    }
