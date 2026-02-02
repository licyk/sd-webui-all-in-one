from pathlib import Path
from dataclasses import dataclass

from sd_webui_all_in_one.model_downloader.base import MODEL_DOWNLOAD_DICT, ModelCardList, SupportedWebUiType, SUPPORTED_WEBUI_LIST, ModelDownloadUrlType
from sd_webui_all_in_one.downloader import download_file, DownloadToolType
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR
from sd_webui_all_in_one.logger import get_logger

logger = get_logger(
    name="Model Utils",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def export_model_list(dtype: SupportedWebUiType) -> ModelCardList:
    """导出模型列表

    Args:
        dtype (SupportedWebUiType): 要导出的模型类型

    Returns:
        ModelCardList:
            模型下载信息列表
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
    downloader: DownloadToolType | None = "aria2",
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
        save_dir = base_path / model["save_dir"][dtype]
        url = model["url"][download_resource_type]
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

    def _validate_index(index: int) -> None:
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
        raise ValueError("`model_name` 和 `model_index` 缺失, 需要提供其中一项才能进行模型下载")

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


@dataclass
class ANSIColor:
    """ANSI 转义码, 用于在终端中显示彩色文本"""

    BLUE = "\033[94m"
    """蓝色"""

    GOLD = "\033[33m"
    """金色"""

    WHITE = "\033[97m"
    """白色"""

    RESET = "\033[0m"
    """重置颜色"""


def display_model_table(
    models: ModelCardList,
) -> None:
    """显示模型库中的模型

    Args:
        models (ModelCardList):
            模型列表
    """

    grouped_models: dict[str, list[tuple[int, str]]] = {}
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
    query_lower = query.lower()

    for index, model in enumerate(models, start=1):
        if query_lower in model["name"].lower() or query_lower in model["filename"].lower():
            results_indices.append(index)
            matched_items.append((index, model))

    for idx, model in matched_items:
        filename = model["filename"]
        dtype = model["dtype"]
        print(f" - {ANSIColor.GOLD}{idx}{ANSIColor.RESET}、{ANSIColor.WHITE}{filename}{ANSIColor.RESET} ({ANSIColor.BLUE}{dtype}{ANSIColor.RESET})")

    print(f"\n搜索 {query} 得到的结果数量: {len(results_indices)}")

    return results_indices
