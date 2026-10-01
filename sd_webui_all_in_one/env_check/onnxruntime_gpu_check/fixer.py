"""ONNXRuntime GPU 检查与修复"""

import os
import sys
from pathlib import Path

from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.pkg_manager import pip_install
from sd_webui_all_in_one.env_check.shared import logger
from sd_webui_all_in_one.env_check.onnxruntime_gpu_check.resolver import (
    need_install_ort_ver,
)
from sd_webui_all_in_one.env_check.onnxruntime_gpu_check.models import (
    OrtType,
)


def check_onnxruntime_gpu(
    use_uv: bool = True,
    skip_if_missing: bool = False,
    custom_env: dict[str, str] | None = None,
) -> None:
    """检查并修复 ONNXRuntime GPU 版本问题

    Args:
        use_uv (bool):
            是否使用 uv 安装依赖
        skip_if_missing (bool):
            当 onnxruntime 未安装时是否跳过检查
            - `True`: 未安装时则不给出需要安装的 ONNXRuntime GPU 版本
            - `False`: 即使 ONNXRuntime GPU 未安装也给出推荐安装的 ONNXRuntime GPU 版本
        custom_env (dict[str, str] | None):
            环境变量字典

    Raises:
        RuntimeError:
            当修复 ONNXRuntime GPU 版本问题发生错误时
    """

    def _clean_env() -> None:
        if custom_env is None:
            return
        custom_env.pop("PIP_EXTRA_INDEX_URL", None)
        custom_env.pop("UV_INDEX", None)
        custom_env.pop("PIP_FIND_LINKS", None)
        custom_env.pop("UV_FIND_LINKS", None)

    def _uninstall_onnxruntime_gpu() -> None:
        run_cmd([Path(sys.executable).as_posix(), "-m", "pip", "uninstall", "onnxruntime-gpu", "-y"])

    def _install_onnxruntime_gpu(
        ver: str,
    ) -> None:
        # 先安装 ONNXRuntime GPU 本体
        pip_install(ver, "--no-cache-dir", "--no-deps", use_uv=use_uv, custom_env=custom_env)
        # 补全剩余的依赖
        pip_install(ver, use_uv=use_uv, custom_env=origin_env)

    logger.info("检查 ONNXRuntime GPU 版本问题中")
    ver = need_install_ort_ver(skip_if_missing)
    logger.debug("需要安装的 ONNXRuntime GPU 版本类型: %s", ver)
    if ver is None:
        logger.info("ONNXRuntime GPU 无版本问题")
        return

    if custom_env is None:
        custom_env = os.environ.copy()
    else:
        custom_env = custom_env.copy()

    origin_env = custom_env.copy()

    try:
        logger.info("修复 ONNXRuntime GPU 版本问题中")
        if ver == OrtType.CU118:
            _clean_env()
            custom_env["PIP_INDEX_URL"] = "https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-11/pypi/simple/"
            custom_env["UV_DEFAULT_INDEX"] = "https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-11/pypi/simple/"
            _uninstall_onnxruntime_gpu()
            _install_onnxruntime_gpu("onnxruntime-gpu>=1.18.1")
        elif ver == OrtType.CU121CUDNN9:
            _uninstall_onnxruntime_gpu()
            _install_onnxruntime_gpu("onnxruntime-gpu>=1.19.0,<=1.26.0")
        elif ver == OrtType.CU121CUDNN8:
            _clean_env()
            custom_env["PIP_INDEX_URL"] = "https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/"
            custom_env["UV_DEFAULT_INDEX"] = "https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/"
            _uninstall_onnxruntime_gpu()
            _install_onnxruntime_gpu("onnxruntime-gpu==1.17.1")
        elif ver == OrtType.CU130:
            # _clean_env()
            # custom_env["PIP_INDEX_URL"] = "https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-13/pypi/simple/"
            # custom_env["UV_DEFAULT_INDEX"] = "https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-13/pypi/simple/"
            _uninstall_onnxruntime_gpu()
            _install_onnxruntime_gpu("onnxruntime-gpu>=1.27.0")
    except RuntimeError as e:
        logger.error("修复 ONNXRuntime GPU 版本问题时出现错误: %s", e)
        raise RuntimeError(f"修复 Onnxrunime GPU 版本问题时发生错误: {e}") from e

    logger.info("ONNXRuntime GPU 版本问题修复完成")
