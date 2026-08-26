"""共享模型下载流程。"""

from pathlib import Path

from sd_webui_all_in_one.downloader import DownloadToolType
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.model_downloader import (
    download_model,
    export_model_list,
    display_model_table,
    search_models_from_library,
    SupportedWebUiType,
    ModelDownloadUrlType,
)
from sd_webui_all_in_one.utils import (
    print_divider,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def pre_download_model_for_webui(
    dtype: SupportedWebUiType,
    model_path: Path,
    webui_base_path: Path,
    model_name: str | list[str],
    download_resource_type: ModelDownloadUrlType | None,
    check_exists: bool = True,
) -> Path | None:
    """为 WebUI 预下载模型

    Args:
        dtype (SupportedWebUiType):
            WebUI 的类型
        model_path (Path):
            预下载模型的路径
        webui_base_path (Path):
            WebUI 的根路径
        model_name (str | list[str]):
            预下载的模型名称
        download_resource_type (ModelDownloadUrlType | None):
            模型下载源类型
        check_exists (bool):
            检查模型目录中是否已经存在模型而跳过预下载模型

    Returns:
        (Path | None):
            模型的保存路径
    """
    if check_exists:
        if not model_path.is_dir() or any(model_path.rglob("*.safetensors")):
            return None

    path = download_model(
        dtype=dtype,
        base_path=webui_base_path,
        download_resource_type=download_resource_type,
        model_name=model_name,
    )
    if len(path) > 0:
        return path[0]

    return None


def install_webui_model_from_library(
    webui_path: Path,
    dtype: SupportedWebUiType,
    download_resource_type: ModelDownloadUrlType | None = "modelscope",
    model_name: str | None = None,
    model_index: int | None = None,
    downloader: DownloadToolType | None = None,
    interactive_mode: bool = False,
    list_only: bool = False,
) -> list[Path] | None:
    """为 WebUI 下载模型, 使用模型库进行下载

    Args:
        webui_path (Path):
            WebUI 根目录
        dtype (SupportedWebUiType):
            WebUI 的类型
        download_resource_type (ModelDownloadUrlType | None):
            模型下载源类型
        model_name (str | None):
            下载的模型名称
        model_index (int | None):
            下载的模型在列表中的索引值, 索引值从 1 开始. 当同时提供 `model_name` 和 `model_index` 时, 优先使用 `model_index` 查找模型
        downloader (DownloadToolType | None):
            下载模型使用的工具
        interactive_mode (bool):
            是否启用交互模式
        list_only (bool):
            是否仅列出模型列表并退出

    Returns:
        list[Path] | None:
            模型的保存地址, 仅列出或退出时返回 None
    """

    def _input_to_int_list(_input: str) -> list[int] | None:
        try:
            return list({int(_i) for _i in _input.split()})
        except Exception:
            return None

    model_list = export_model_list(dtype)

    if list_only:
        print_divider("=")
        display_model_table(model_list)
        print_divider("=")
        return None

    display_model = True
    input_err = (0, None)

    if interactive_mode:
        while True:
            if display_model:
                print_divider("=")
                display_model_table(model_list)
                print_divider("=")

            display_model = True
            i, m = input_err
            if i == 1:
                logger.warning("输入有误, 请重试")
            elif i == 2:
                logger.warning("输入的数字有误, %s, 请重新输入", m)
            input_err = (0, None)
            print(
                "请选择要下载的模型\n"
                "提示:\n"
                "1. 输入数字后回车\n"
                "2. 如果需要下载多个模型, 可以输入多个数字并使用空格隔开\n"
                "3. 输入 search 可以进入列表搜索模式, 输入 search <模型名称> 可以直接搜索\n"
                "4. 输入 exit 退出模型下载"
            )
            user_input = input("==> ").strip()

            if user_input.lower() == "exit":
                return None

            command, _, command_arg = user_input.partition(" ")
            if command.lower() == "search":
                display_model = False
                print_divider("=")
                search_query = command_arg.strip()
                if not search_query:
                    search_query = input("请输入要从模型列表搜索的模型名称: ").strip()
                search_models_from_library(
                    query=search_query,
                    models=model_list,
                )
                print_divider("=")
                continue

            result = _input_to_int_list(user_input)

            if result is None or len(result) == 0:
                input_err = (1, None)
                continue

            try:
                return download_model(
                    dtype=dtype,
                    base_path=webui_path,
                    download_resource_type=download_resource_type,
                    model_index=result,
                    downloader=downloader,
                )
            except ValueError as e:
                input_err = (2, str(e))
                continue
    else:
        return download_model(
            dtype=dtype,
            base_path=webui_path,
            download_resource_type=download_resource_type,
            model_name=model_name,
            model_index=model_index,
            downloader=downloader,
        )
