"""accelerate 软件包检查测试"""

import importlib
import sys
from pathlib import Path


fix_accelerate_bin = importlib.import_module("sd_webui_all_in_one.env_check.fix_accelerate_bin.fixer")


def test_check_accelerate_bin_reinstalls_for_kohya_repo(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(fix_accelerate_bin.git_warpper, "get_current_branch_remote_url", lambda _path: "https://github.com/other/repo")
    fix_accelerate_bin.check_accelerate_bin(tmp_path)
    assert calls == []

    monkeypatch.setattr(fix_accelerate_bin.git_warpper, "get_current_branch_remote_url", lambda _path: "https://github.com/bmaltais/kohya_ss")

    def fake_run_cmd(command, **_kwargs):
        calls.append(("cmd", command))
        if command == ["accelerate", "--help"]:
            raise RuntimeError("missing")

    monkeypatch.setattr(fix_accelerate_bin, "run_cmd", fake_run_cmd)
    monkeypatch.setattr(fix_accelerate_bin, "get_package_version_from_library", lambda _name: "0.31.0")
    monkeypatch.setattr(fix_accelerate_bin, "pip_install", lambda *args, **kwargs: calls.append(("pip", args, kwargs)))

    fix_accelerate_bin.check_accelerate_bin(tmp_path, use_uv=False, custom_env={"M": "1"})

    assert calls[0] == ("cmd", ["accelerate", "--help"])
    assert calls[1][0] == "cmd"
    assert calls[1][1] == [Path(sys.executable).as_posix(), "-m", "pip", "uninstall", "accelerate", "-y"]
    assert calls[2] == ("pip", ("accelerate==0.31.0", "--no-deps"), {"use_uv": False, "custom_env": {"M": "1"}})
