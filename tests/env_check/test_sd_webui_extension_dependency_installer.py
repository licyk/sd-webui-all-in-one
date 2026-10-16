"""SD WebUI 扩展依赖安装测试"""

import importlib
import json
import sys
from pathlib import Path

ext_installer = importlib.import_module("sd_webui_all_in_one.env_check.sd_webui_extension_dependency_installer")


ext_installer_runner = importlib.import_module("sd_webui_all_in_one.env_check.sd_webui_extension_dependency_installer.runner")


ext_installer_installer = importlib.import_module("sd_webui_all_in_one.env_check.sd_webui_extension_dependency_installer.installer")


def test_run_extension_installer_sets_pythonpath_and_live_output(monkeypatch, tmp_path):
    webui = tmp_path / "webui"
    extension = webui / "extensions" / "demo"
    extension.mkdir(parents=True)
    (extension / "install.py").write_text("print('install')\n", encoding="utf-8")
    origin_env = {"PYTHONPATH": "old", "KEEP": "1"}
    calls = []

    def fake_run_cmd(command, custom_env, cwd):
        calls.append((command, custom_env, cwd))

    monkeypatch.setattr(ext_installer_runner, "run_cmd", fake_run_cmd)

    assert ext_installer.run_extension_installer(webui, extension, custom_env=origin_env) is True
    assert origin_env == {"PYTHONPATH": "old", "KEEP": "1"}
    assert calls[0][0] == [Path(sys.executable).as_posix(), (extension / "install.py").as_posix()]
    assert calls[0][1]["WEBUI_LAUNCH_LIVE_OUTPUT"] == "1"
    assert calls[0][1]["PYTHONPATH"].startswith(webui.as_posix())
    assert calls[0][2] == webui

    monkeypatch.setattr(ext_installer_runner, "run_cmd", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bad install")))
    assert ext_installer.run_extension_installer(webui, extension) is False
    assert ext_installer.run_extension_installer(webui, webui / "missing") is False


def test_install_extension_requirements_filters_disabled_and_builtin(monkeypatch, tmp_path):
    webui = tmp_path / "webui"
    extra = webui / "extensions"
    builtin = webui / "extensions-builtin"
    for folder in [
        extra / "enabled",
        extra / "disabled",
        builtin / "builtin-enabled",
        builtin / "builtin-disabled",
    ]:
        folder.mkdir(parents=True)
        (folder / "install.py").write_text("", encoding="utf-8")
    (webui / "config.json").write_text(json.dumps({"disabled_extensions": ["disabled", "builtin-disabled"]}), encoding="utf-8")
    calls = []
    monkeypatch.setattr(ext_installer_installer, "run_extension_installer", lambda sd_webui_base_path, extension_dir, custom_env=None: calls.append(extension_dir.name) or True)

    ext_installer.install_extension_requirements(webui, custom_env={"A": "B"})
    assert calls == ["enabled", "builtin-enabled"]

    calls.clear()
    (webui / "config.json").write_text(json.dumps({"disable_all_extensions": "extra"}), encoding="utf-8")
    ext_installer.install_extension_requirements(webui)
    assert sorted(calls) == ["builtin-disabled", "builtin-enabled"]

    calls.clear()
    (webui / "config.json").write_text(json.dumps({"disable_all_extensions": "all"}), encoding="utf-8")
    ext_installer.install_extension_requirements(webui)
    assert calls == []
