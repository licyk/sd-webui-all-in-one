"""Qwen TTS WebUI 管理器测试"""

import os

from sd_webui_all_in_one.base_manager import (
    qwen_tts_webui_base,
)
from tests.base_manager.products.helpers import implementation_module, use_temp_git_config


def test_install_qwen_tts_webui_orchestrates_without_external_side_effects(monkeypatch, tmp_path):
    calls = []
    git_config_path = use_temp_git_config(monkeypatch, tmp_path)
    implementation = implementation_module(qwen_tts_webui_base, "install_qwen_tts_webui")
    (tmp_path / "requirements.txt").write_text("demo\n", encoding="utf-8")

    monkeypatch.setattr(implementation, "prepare_pytorch_install_info", lambda **kwargs: ("torch", "xformers", {"TORCH": "env"}))
    monkeypatch.setattr(implementation, "get_pypi_mirror_config", lambda use_cn_mirror=True: {"PIP": str(use_cn_mirror)})
    monkeypatch.setattr(
        implementation,
        "apply_git_base_config_and_github_mirror",
        lambda **kwargs: {**kwargs["origin_env"], "GIT_CONFIG_GLOBAL": git_config_path},
    )
    monkeypatch.setattr(implementation, "clone_repo", lambda **kwargs: calls.append(("clone", kwargs)))
    monkeypatch.setattr(implementation, "install_pytorch_for_webui", lambda **kwargs: calls.append(("pytorch", kwargs)))
    monkeypatch.setattr(implementation, "install_requirements", lambda **kwargs: calls.append(("requirements", kwargs)))
    monkeypatch.setattr(implementation, "install_qwen_tts_webui_config", lambda **kwargs: calls.append(("config", kwargs)))

    qwen_tts_webui_base.install_qwen_tts_webui(
        tmp_path,
        use_pypi_mirror=False,
        use_uv=False,
        use_github_mirror=True,
        custom_github_mirror="https://mirror.example",
        model_download_resource_type="huggingface",
    )

    assert os.environ["GIT_CONFIG_GLOBAL"] == git_config_path
    assert calls[0] == ("clone", {"repo": qwen_tts_webui_base.QWEN_TTS_WEBUI_REPO, "path": tmp_path})
    assert calls[1] == (
        "pytorch",
        {"pytorch_package": "torch", "xformers_package": "xformers", "custom_env": {"TORCH": "env"}, "use_uv": False},
    )
    assert calls[2][0] == "requirements"
    assert calls[2][1]["path"] == tmp_path / "requirements.txt"
    assert calls[2][1]["cwd"] == tmp_path
    assert calls[3] == ("config", {"qwen_tts_webui_path": tmp_path, "download_resource_type": "huggingface"})

    calls.clear()
    qwen_tts_webui_base.install_qwen_tts_webui(
        tmp_path,
        no_pre_download_model=True,
        model_download_resource_type="huggingface",
    )
    assert calls[-1] == ("config", {"qwen_tts_webui_path": tmp_path, "download_resource_type": False})
