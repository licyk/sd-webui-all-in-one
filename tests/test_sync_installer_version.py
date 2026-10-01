import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).parents[1] / ".github" / "sync_installer_version.py"
SPEC = importlib.util.spec_from_file_location("sync_installer_version", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
sync_installer_version = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sync_installer_version
SPEC.loader.exec_module(sync_installer_version)

BOM = b"\xef\xbb\xbf"


def _installer_content(flag, version, core_version):
    return (
        "param ()\n"
        "# Installer 版本和检查更新间隔\n"
        f"$script:{flag} = {version}\n"
        "$script:UPDATE_TIME_SPAN = 3600\n"
        "# SD WebUI All In One 内核最低版本\n"
        f'$script:CORE_MINIMUM_VER = "{core_version}"\n'
        '$content = "\n'
        f"`$script:{flag} = $script:{flag}\n"
        '`$script:CORE_MINIMUM_VER = `"$script:CORE_MINIMUM_VER`"\n'
        '"\n'
    )


def _make_workspace(tmp_path, core_version="2.5.18", installers=None):
    installers = installers or {"comfyui": ("COMFYUI_INSTALLER_VERSION", 532, "2.5.17"), "fooocus": ("FOOOCUS_INSTALLER_VERSION", 449, "2.5.18")}
    package_dir = tmp_path / "sd_webui_all_in_one"
    package_dir.mkdir()
    (package_dir / "version.py").write_bytes(f'"""SD WebUI All In One 版本"""\n\nVERSION = "{core_version}"\n'.encode())
    installer_dir = tmp_path / "installer"
    installer_dir.mkdir()
    for name, (flag, version, core) in installers.items():
        (installer_dir / f"{name}_installer.ps1").write_bytes(BOM + _installer_content(flag, version, core).encode())
    (installer_dir / "install_embed_python.ps1").write_bytes(b"# not an installer\n")
    return tmp_path


def _read(workspace, name):
    return (workspace / "installer" / f"{name}_installer.ps1").read_bytes()


def test_sync_only_updates_core_minimum_version(tmp_path, capsys):
    workspace = _make_workspace(tmp_path)
    fooocus_before = _read(workspace, "fooocus")

    assert sync_installer_version.main(["--workspace", str(workspace)]) == 0

    assert _read(workspace, "comfyui") == BOM + _installer_content("COMFYUI_INSTALLER_VERSION", 532, "2.5.18").encode()
    assert _read(workspace, "fooocus") == fooocus_before
    assert "Updated 1 file(s)." in capsys.readouterr().out

    assert sync_installer_version.main(["--workspace", str(workspace)]) == 0
    assert "already in sync" in capsys.readouterr().out


def test_bump_installer_and_core_versions(tmp_path, capsys):
    workspace = _make_workspace(tmp_path)

    assert sync_installer_version.main(["--workspace", str(workspace), "--bump-core", "--bump-installer"]) == 0

    assert 'VERSION = "2.5.19"' in (workspace / "sd_webui_all_in_one" / "version.py").read_text(encoding="utf-8")
    assert _read(workspace, "comfyui") == BOM + _installer_content("COMFYUI_INSTALLER_VERSION", 533, "2.5.19").encode()
    assert _read(workspace, "fooocus") == BOM + _installer_content("FOOOCUS_INSTALLER_VERSION", 450, "2.5.19").encode()
    output = capsys.readouterr().out
    assert "Core version: 2.5.18 -> 2.5.19" in output
    assert "v5.3.2 -> v5.3.3" in output
    assert "Updated 3 file(s)." in output


@pytest.mark.parametrize(
    ("part", "expected"),
    [("patch", "2.5.19"), ("minor", "2.6.0"), ("major", "3.0.0")],
)
def test_bump_core_version_parts(part, expected):
    assert sync_installer_version.bump_core_version("2.5.18", part) == expected


def test_explicit_core_version_and_installer_filter(tmp_path):
    workspace = _make_workspace(tmp_path)
    fooocus_before = _read(workspace, "fooocus")

    assert sync_installer_version.main(["--workspace", str(workspace), "--core-version", "3.0.0", "--bump-installer", "--installer", "comfyui"]) == 0

    assert _read(workspace, "comfyui") == BOM + _installer_content("COMFYUI_INSTALLER_VERSION", 533, "3.0.0").encode()
    assert _read(workspace, "fooocus") == fooocus_before


def test_dry_run_writes_nothing(tmp_path, capsys):
    workspace = _make_workspace(tmp_path)
    before = {path: path.read_bytes() for path in workspace.rglob("*") if path.is_file()}

    assert sync_installer_version.main(["--workspace", str(workspace), "--bump-core", "minor", "--bump-installer", "--dry-run"]) == 0

    assert {path: path.read_bytes() for path in workspace.rglob("*") if path.is_file()} == before
    assert "Dry run: 3 file(s) would be updated." in capsys.readouterr().out


def test_crlf_line_endings_are_preserved(tmp_path):
    workspace = _make_workspace(tmp_path)
    path = workspace / "installer" / "comfyui_installer.ps1"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))

    assert sync_installer_version.main(["--workspace", str(workspace), "--bump-installer"]) == 0

    assert path.read_bytes() == BOM + _installer_content("COMFYUI_INSTALLER_VERSION", 533, "2.5.18").replace("\n", "\r\n").encode()


@pytest.mark.parametrize(
    ("replace_from", "replace_to", "message"),
    [
        ("$script:COMFYUI_INSTALLER_VERSION = 532\n", "", "installer version assignment, found 0"),
        ('$script:CORE_MINIMUM_VER = "2.5.17"\n', '$script:CORE_MINIMUM_VER = "2.5.17"\n$script:CORE_MINIMUM_VER = "2.5.17"\n', "CORE_MINIMUM_VER assignment, found 2"),
    ],
)
def test_invalid_installer_fails_without_writing(tmp_path, capsys, replace_from, replace_to, message):
    workspace = _make_workspace(tmp_path, installers={"comfyui": ("COMFYUI_INSTALLER_VERSION", 532, "2.5.17"), "afirst": ("AFIRST_INSTALLER_VERSION", 100, "2.5.17")})
    path = workspace / "installer" / "comfyui_installer.ps1"
    path.write_bytes(path.read_bytes().replace(replace_from.encode(), replace_to.encode()))
    before = {item: item.read_bytes() for item in workspace.rglob("*") if item.is_file()}

    assert sync_installer_version.main(["--workspace", str(workspace), "--bump-core", "--bump-installer"]) == 1

    assert {item: item.read_bytes() for item in workspace.rglob("*") if item.is_file()} == before
    assert message in capsys.readouterr().err


def test_invalid_arguments_are_rejected(tmp_path, capsys):
    workspace = _make_workspace(tmp_path)

    assert sync_installer_version.main(["--workspace", str(workspace), "--core-version", "3.0"]) == 1
    assert "X.Y.Z" in capsys.readouterr().err

    assert sync_installer_version.main(["--workspace", str(workspace), "--installer", "missing"]) == 1
    assert "unknown installer: missing" in capsys.readouterr().err

    with pytest.raises(SystemExit):
        sync_installer_version.main(["--workspace", str(workspace), "--bump-core", "--core-version", "3.0.0"])
