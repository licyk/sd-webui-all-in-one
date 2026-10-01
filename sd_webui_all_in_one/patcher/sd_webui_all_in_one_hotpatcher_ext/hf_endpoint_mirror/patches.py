"""Hugging Face 镜像补丁注册"""

from __future__ import annotations

import asyncio
from functools import wraps
from typing import Any

from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo

from .download import load_file_from_url
from .urls import _hf_endpoint, rewrite_huggingface_url

_HF_URL_WRAPPER_ATTR = "__sd_webui_all_in_one_hf_endpoint_mirror__"


def apply_mirror() -> None:
    """
    注册全部 Hugging Face 镜像补丁

    包装函数会在调用时读取 ``HF_ENDPOINT``。环境变量为空或 URL 不是
    Hugging Face 链接时, 保持原始 URL 不变。
    """

    patch_torchhub()
    patch_torchvision()
    patch_comfyui_wd14_tagger()
    patch_comfyui_manager_model_downloads()
    patch_sd_webui_load_file_from_url()


def patch_torchhub() -> None:
    """补丁 ``torch.hub.download_url_to_file`` 的 URL 参数"""

    install_import_hook()

    with monkey_zoo("torch.hub") as monkey:

        def download_url_to_file_wrapper(func: Any, module: Any):
            @wraps(func)
            def wrapper(url, dst, *args, **kwargs):
                return func(rewrite_huggingface_url(url), dst, *args, **kwargs)

            return wrapper

        monkey.patch_function("download_url_to_file", download_url_to_file_wrapper)


def patch_torchvision() -> None:
    """补丁 ``torchvision.datasets.utils._urlretrieve`` 的 URL 参数"""

    install_import_hook()

    with monkey_zoo("torchvision.datasets.utils") as monkey:

        def urlretrieve_wrapper(func: Any, module: Any):
            @wraps(func)
            def wrapper(url, fpath, *args, **kwargs):
                return func(rewrite_huggingface_url(url), fpath, *args, **kwargs)

            return wrapper

        monkey.patch_function("_urlretrieve", urlretrieve_wrapper)


def patch_comfyui_wd14_tagger() -> None:
    """补丁 ComfyUI WD14 tagger ``download_to_file`` 的 URL 参数"""

    install_import_hook()

    with monkey_zoo("ComfyUI-WD14-Tagger.pysssss") as monkey:

        def download_to_file_wrapper(func: Any, module: Any):
            @wraps(func)
            async def wrapper(url, dst, *args, **kwargs):
                rewritten = rewrite_huggingface_url(url)
                task = asyncio.create_task(asyncio.to_thread(func, rewritten, dst, *args, **kwargs))
                await asyncio.sleep(0)
                await task
                return task.result()

            return wrapper

        monkey.patch_function("download_to_file", download_to_file_wrapper)


def patch_comfyui_manager_model_downloads() -> None:
    """补丁 ComfyUI-Manager 模型下载入口的 Hugging Face URL 参数"""

    install_import_hook()

    with monkey_zoo("manager_downloader") as monkey:
        monkey.patch_function("download_url", _rewrite_first_url_arg_wrapper)
        monkey.patch_function("download_url_with_agent", _rewrite_first_url_arg_wrapper)
        monkey.patch_function("download_repo_in_bytes", _download_repo_in_bytes_wrapper)

    with monkey_zoo("manager_server") as monkey:
        monkey.patch_function("download_url", _rewrite_first_url_arg_wrapper)
        monkey.patch_function("download_url_with_agent", _rewrite_first_url_arg_wrapper)


def patch_sd_webui_load_file_from_url() -> None:
    """替换 ``modules.util.load_file_from_url`` 为支持 HF_ENDPOINT 的实现"""

    install_import_hook()

    with monkey_zoo("modules.util") as monkey:

        def load_file_from_url_wrapper(func: Any, module: Any):
            return load_file_from_url

        monkey.patch_function(
            "load_file_from_url",
            load_file_from_url_wrapper,
            add_if_not_exists=True,
        )


def _rewrite_first_url_arg_wrapper(func: Any, module: Any) -> Any:
    if getattr(func, _HF_URL_WRAPPER_ATTR, False):
        return func

    @wraps(func)
    def wrapper(url, *args, **kwargs):
        return func(rewrite_huggingface_url(url), *args, **kwargs)

    setattr(wrapper, _HF_URL_WRAPPER_ATTR, True)
    return wrapper


def _download_repo_in_bytes_wrapper(func: Any, module: Any) -> Any:
    if getattr(func, _HF_URL_WRAPPER_ATTR, False):
        return func

    @wraps(func)
    def wrapper(repo_id, local_dir, *args, **kwargs):
        if args or kwargs:
            return func(repo_id, local_dir, *args, **kwargs)
        return _download_comfyui_manager_repo_in_bytes(module, repo_id, local_dir)

    setattr(wrapper, _HF_URL_WRAPPER_ATTR, True)
    return wrapper


def _download_comfyui_manager_repo_in_bytes(module: Any, repo_id: str, local_dir: str) -> None:
    endpoint = _hf_endpoint()
    try:
        api = module.HfApi(endpoint=endpoint) if endpoint is not None else module.HfApi()
    except TypeError:
        api = module.HfApi()
    repo_info = api.repo_info(repo_id=repo_id, files_metadata=True)

    module.os.makedirs(local_dir, exist_ok=True)

    total_size = 0
    for file_info in repo_info.siblings:
        if file_info.size is not None:
            total_size += file_info.size

    pbar = module.tqdm(total=total_size, unit="B", unit_scale=True, desc="Downloading")
    try:
        for file_info in repo_info.siblings:
            if file_info.size is None:
                continue

            out_path = module.os.path.join(local_dir, file_info.rfilename)
            module.os.makedirs(module.os.path.dirname(out_path), exist_ok=True)
            download_url = rewrite_huggingface_url(f"https://huggingface.co/{repo_id}/resolve/main/{file_info.rfilename}")

            with module.requests.get(download_url, stream=True) as response, open(out_path, "wb") as file:
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        file.write(chunk)
                        pbar.update(len(chunk))
    finally:
        pbar.close()
