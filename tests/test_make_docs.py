import os
import subprocess
import sys
from pathlib import Path

import pytest


MAKE_DOCS = Path(__file__).parents[1] / ".github" / "make_docs.py"


def run_make_docs(docs_path: Path, platform: str | None = None) -> None:
    command = [sys.executable, str(MAKE_DOCS), str(docs_path)]
    if platform is not None:
        command.extend(["--platform", platform])
    subprocess.run(command, check=True)


def test_make_docs_defaults_to_windows(tmp_path: Path):
    (tmp_path / "launch.ps1").touch()

    run_make_docs(tmp_path)

    assert (tmp_path / "启动.bat").is_file()
    assert not (tmp_path / "launch.sh").exists()
    assert not (tmp_path / "解除 macOS 隔离属性.command").exists()
    assert "configure_env.bat" in (tmp_path / "必读使用说明.txt").read_text(encoding="utf-8")


def test_make_docs_handles_non_utf8_console_output(tmp_path: Path):
    (tmp_path / "launch.ps1").touch()
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "ascii"

    command = [sys.executable, str(MAKE_DOCS), str(tmp_path)]
    subprocess.run(command, check=True, env=env)

    assert (tmp_path / "必读使用说明.txt").is_file()
    assert (tmp_path / "启动.bat").is_file()


@pytest.mark.parametrize("platform", ["linux", "macos"])
def test_make_docs_generates_unix_launchers(tmp_path: Path, platform: str):
    (tmp_path / "launch.ps1").touch()

    run_make_docs(tmp_path, platform)

    launch_sh = tmp_path / "launch.sh"
    assert launch_sh.is_file()
    assert "command -v pwsh" in launch_sh.read_text(encoding="utf-8")
    assert not list(tmp_path.glob("*.bat"))
    if os.name != "nt":
        assert os.access(launch_sh, os.X_OK)

    launch_command = tmp_path / "launch.command"
    assert launch_command.exists() is (platform == "macos")
    if launch_command.exists() and os.name != "nt":
        assert os.access(launch_command, os.X_OK)

    quarantine_command = tmp_path / "解除 macOS 隔离属性.command"
    assert quarantine_command.exists() is (platform == "macos")
    if quarantine_command.exists():
        quarantine_content = quarantine_command.read_text(encoding="utf-8")
        assert 'xattr -dr com.apple.quarantine "$SCRIPT_DIR"' in quarantine_content
        assert "|| true" not in quarantine_content
        if os.name != "nt":
            assert os.access(quarantine_command, os.X_OK)

    help_content = (tmp_path / "必读使用说明.txt").read_text(encoding="utf-8")
    assert "PowerShell 7" in help_content
    assert "系统 Git" in help_content
    assert "Hanafubuki" in help_content
    assert "启动整合包：" in help_content
    assert "启动 ComfyUI" not in help_content
    if platform == "macos":
        assert "解除 macOS 隔离属性.command" in help_content
        assert "xattr -dr com.apple.quarantine" in help_content
        assert "完整的整合包解压目录" in help_content
    else:
        assert "com.apple.quarantine" not in help_content
