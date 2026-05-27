"""模型库管理工具"""

import re
from pathlib import Path

from sd_webui_all_in_one.downloader import (
    download_file,
    DownloadToolType,
)
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.ansi_color import ANSIColor
from sd_webui_all_in_one.model_downloader.model_data import MODEL_DOWNLOAD_DICT
from sd_webui_all_in_one.model_downloader.types import (
    SUPPORTED_WEBUI_LIST,
    ModelCard,
    ModelCardList,
    ModelDownloadUrlType,
    SupportedWebUiType,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def export_model_list(
    dtype: SupportedWebUiType,
) -> ModelCardList:
    """导出模型列表

    Args:
        dtype (SupportedWebUiType): 要导出的模型类型

    Returns:
        ModelCardList:
            模型下载信息列表

    Raises:
        ValueError:
            WebUI 类型不受支持时抛出。
    """
    if dtype not in SUPPORTED_WEBUI_LIST:
        raise ValueError(f"不支持的 WebUI 类型: '{dtype}'")

    new_model_list = [m for m in MODEL_DOWNLOAD_DICT if dtype in m["supported_webui"]]

    return new_model_list


def download_model(
    dtype: SupportedWebUiType,
    base_path: Path,
    download_resource_type: ModelDownloadUrlType | None = "modelscope",
    model_name: str | list[str] | None = None,
    model_index: int | list[int] | None = None,
    downloader: DownloadToolType | None = None,
) -> list[Path]:
    """下载模型到 WebUI 目录中

    Args:
        dtype (SupportedWebUiType):
            WebUI 的类型
        base_path (Path):
            WebUI 的根目录
        download_resource_type (ModelDownloadUrlType | None):
            模型下载源类型
        model_name (str | list[str] | None):
            下载的模型名称
        model_index (int | list[int] | None):
            下载的模型在列表中的索引值, 索引值从 1 开始. 当同时提供 `model_name` 和 `model_index` 时, 优先使用 `model_index` 查找模型
        downloader (DownloadToolType | None):
            下载模型使用的工具

    Returns:
        list[Path]:
            模型的保存路径列表

    Raises:
        RuntimeError:
            下载模型时发生错误时
    """
    if download_resource_type is None:
        download_resource_type = "modelscope"

    queue_model = query_model_info(
        dtype=dtype,
        model_name=model_name,
        model_index=model_index,
    )
    logger.debug("查询到的模型下载列表: %s", queue_model)
    count = 0
    sums = len(queue_model)
    save_paths: list[Path] = []
    for model in queue_model:
        count += 1
        name = model["name"]
        filename = model["filename"]
        save_dir_name = model["save_dir"].get(dtype)
        url = model["url"].get(download_resource_type)
        if save_dir_name is None or url is None:
            raise RuntimeError(f"模型 {name} 缺少 {dtype} 的保存路径或 {download_resource_type} 下载地址")
        save_dir = base_path / save_dir_name
        logger.info("[%s/%s] 下载 %s 到 %s 中", count, sums, name, save_dir)
        try:
            p = download_file(
                url=url,
                path=save_dir,
                save_name=filename,
                tool=downloader,
            )
            logger.info("[%s/%s] 下载 %s 完成", count, sums, name)
            save_paths.append(p)
        except RuntimeError as e:
            logger.info("[%s/%s] 下载 %s 时发生错误: %s", count, sums, name, e)
            raise RuntimeError(f"下载 {name} 时发生错误: {e}") from e

    return save_paths


def query_model_info(
    dtype: SupportedWebUiType,
    model_name: str | list[str] | None = None,
    model_index: int | list[int] | None = None,
) -> ModelCardList:
    """从模型列表中查询指定的模型信息

    Args:
        dtype (SupportedWebUiType):
            WebUI 的类型
        model_name (str | list[str] | None):
            下载的模型名称
        model_index (int | list[int] | None):
            下载的模型在列表中的索引值, 索引值从 1 开始. 当同时提供 `model_name` 和 `model_index` 时, 优先使用 `model_index` 查找模型

    Returns:
        ModelCardList:
            模型信息列表

    Raises:
        ValueError:
            提供的 `model_index` 超出有效范围时 / `model_name` 和 `model_index` 时
        FileNotFoundError:
            根据 `model_name` 却无法找到对应的模型时
    """

    def _validate_index(
        index: int,
    ) -> None:
        if not 0 < index <= len(model_list):
            raise ValueError(f"索引值 {index} 超出范围, 模型有效的范围为: 1 ~ {len(model_list)}")

    def _get_model_with_name(name: str) -> ModelCardList:
        _queue_model: ModelCardList = []
        has_found = False
        for model in model_list:
            if model["name"] == name:
                _queue_model.append(model)
                has_found = True
        if not has_found:
            raise FileNotFoundError(f"未找到指定的模型名称: {name}")
        return _queue_model

    model_list = export_model_list(dtype)
    if model_name is None and model_index is None:
        raise ValueError("`model_name` 和 `model_index` 缺失, 需要提供其中一项才能进行模型信息查找")

    query_model: ModelCardList = []

    if model_index is not None:
        if isinstance(model_index, list):
            for i in model_index:
                _validate_index(i)
                query_model.append(model_list[i - 1])
        else:
            _validate_index(model_index)
            query_model.append(model_list[model_index - 1])
    elif model_name is not None:
        if isinstance(model_name, list):
            for n in model_name:
                query_model += _get_model_with_name(n)
        else:
            query_model += _get_model_with_name(model_name)

    return query_model


def display_model_table(
    models: ModelCardList,
) -> None:
    """显示模型库中的模型

    Args:
        models (ModelCardList):
            模型列表
    """

    grouped_models: dict[str, list[tuple[int, ModelCard]]] = {}
    for index, model in enumerate(models, start=1):
        dtype = model["dtype"]
        if dtype not in grouped_models:
            grouped_models[dtype] = []
        grouped_models[dtype].append((index, model))

    for dtype, items in grouped_models.items():
        print(f"{ANSIColor.BLUE}- {dtype}{ANSIColor.RESET}")
        for idx, model in items:
            filename = model["filename"]
            print(f"  - {ANSIColor.GOLD}{idx}{ANSIColor.RESET}、{ANSIColor.WHITE}{filename}{ANSIColor.RESET} ({ANSIColor.BLUE}{dtype}{ANSIColor.RESET})")

        print()


def normalize_model_search_text(
    value: str,
) -> str:
    """归一化模型搜索文本

    Args:
        value (str):
            要归一化的文本

    Returns:
        str: 去除分隔符并转换为小写后的文本
    """
    return "".join(char.lower() for char in value if char.isalnum())


def get_model_search_text(
    model: ModelCard,
) -> tuple[str, str]:
    """获取模型搜索文本

    Args:
        model (ModelCard):
            模型信息

    Returns:
        tuple[str, str]: 原始搜索文本和归一化搜索文本
    """
    fields: list[str] = [
        model["name"],
        model["filename"],
        model["dtype"],
        Path(model["filename"]).stem,
    ]
    fields.extend(model["supported_webui"])
    for webui in SUPPORTED_WEBUI_LIST:
        save_dir = model["save_dir"].get(webui)
        if save_dir is not None:
            fields.append(save_dir)
    raw_text = " ".join(fields).lower()
    normalized_text = normalize_model_search_text(raw_text)
    return raw_text, normalized_text


def model_matches_search_query(
    model: ModelCard,
    query: str,
) -> bool:
    """判断模型是否匹配搜索关键词

    Args:
        model (ModelCard):
            模型信息
        query (str):
            搜索关键词

    Returns:
        bool: 匹配时返回 True
    """
    query = query.strip()
    if not query:
        return False

    query_lower = query.lower()
    normalized_query = normalize_model_search_text(query)
    query_terms = [normalize_model_search_text(term) for term in re.split(r"[\s,，;；/\\._-]+", query) if normalize_model_search_text(term)]
    raw_text, normalized_text = get_model_search_text(model)

    if query_lower in raw_text:
        return True

    if normalized_query and normalized_query in normalized_text:
        return True

    return bool(query_terms) and all(term in normalized_text for term in query_terms)


def search_models_from_library(
    query: str,
    models: ModelCardList,
) -> list[int]:
    """从模型库搜索模型并显示结果

    Args:
        query (str):
            搜索关键词
        models (ModelCardList):
            模型列表

    Returns:
        list[int]: 匹配到的模型序号列表
    """

    results_indices = []
    matched_items = []

    for index, model in enumerate(models, start=1):
        if model_matches_search_query(model, query):
            results_indices.append(index)
            matched_items.append((index, model))

    for idx, model in matched_items:
        filename = model["filename"]
        dtype = model["dtype"]
        print(f" - {ANSIColor.GOLD}{idx}{ANSIColor.RESET}、{ANSIColor.WHITE}{filename}{ANSIColor.RESET} ({ANSIColor.BLUE}{dtype}{ANSIColor.RESET})")

    print(f"\n搜索 {query} 得到的结果数量: {len(results_indices)}")

    return results_indices
