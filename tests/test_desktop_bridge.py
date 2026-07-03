import json
import shutil
import subprocess
from io import StringIO

import pytest

from sd_webui_all_in_one.base_manager.repository_inspector import RepositoryState
from sd_webui_all_in_one.desktop_bridge import operations
from sd_webui_all_in_one.base_manager.version_manager import BranchInfo
from sd_webui_all_in_one.desktop_bridge.protocol import handle_request, main


def test_bridge_info_advertises_supported_capabilities():
    response = handle_request(
        {
            "requestId": "info-1",
            "operation": "bridge.info",
            "payload": {},
        }
    )

    assert response["requestId"] == "info-1"
    assert response["ok"] is True
    assert response["data"]["bridgeProtocol"] == 1
    assert response["data"]["capabilities"] == [
        "bridge.info",
        "version.get_state",
        "version.list_branches",
        "instance.prepare_launch",
    ]
    assert "get_install_catalog" not in response["data"]["capabilities"]


def test_version_get_state_returns_git_state(monkeypatch, tmp_path):
    core_path = tmp_path / "core"
    core_path.mkdir()
    repository = RepositoryState(
        path=core_path,
        is_git_repo=True,
        name="core",
        url="https://example.test/repo.git",
        branch="main",
        commit="abcdef1234567890abcdef1234567890abcdef12",
        commit_date="2026-07-03 12:00:00 +0000",
        message="test commit",
    )

    monkeypatch.setattr(operations, "inspect_repository", lambda path: repository)
    monkeypatch.setattr(operations, "_git_dirty", lambda path: False)
    monkeypatch.setattr(operations, "_git_upstream_branch", lambda path: "origin/main")
    monkeypatch.setattr(operations, "_git_ahead_behind", lambda path: (1, 2))

    response = handle_request(
        {
            "requestId": "version-1",
            "operation": "version.get_state",
            "payload": {
                "instance": {
                    "kind": "sd_webui",
                    "corePath": str(core_path),
                }
            },
        }
    )

    assert response["ok"] is True
    state = response["data"]["state"]
    assert state == {
        "mode": "git",
        "branch": "main",
        "commit": "abcdef1234567890abcdef1234567890abcdef12",
        "commitShort": "abcdef1",
        "commitDate": "2026-07-03 12:00:00 +0000",
        "dirty": False,
        "remote": "https://example.test/repo.git",
        "upstreamBranch": "origin/main",
        "ahead": 1,
        "behind": 2,
        "updateAvailable": True,
    }


def test_git_dirty_uses_no_optional_locks(monkeypatch, tmp_path):
    calls = []

    def fake_run_git_output(path, *args):
        calls.append((path, args))
        return ""

    monkeypatch.setattr(operations, "run_git_output", fake_run_git_output)

    assert operations._git_dirty(tmp_path) is False
    assert calls == [(tmp_path, ("--no-optional-locks", "status", "--porcelain"))]


def test_version_get_state_reads_real_git_repository_without_upstream(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git executable is not available")

    core_path = tmp_path / "core"
    core_path.mkdir()
    _run_git(core_path, "init")
    _run_git(core_path, "config", "user.email", "desktop-bridge@example.test")
    _run_git(core_path, "config", "user.name", "Desktop Bridge")
    tracked_file = core_path / "README.md"
    tracked_file.write_text("initial\n", encoding="utf-8")
    _run_git(core_path, "add", "README.md")
    _run_git(core_path, "commit", "-m", "initial")
    tracked_file.write_text("changed\n", encoding="utf-8")

    response = handle_request(
        {
            "requestId": "version-real-git",
            "operation": "version.get_state",
            "payload": {
                "instance": {
                    "kind": "sd_webui",
                    "corePath": str(core_path),
                }
            },
        }
    )

    assert response["ok"] is True
    state = response["data"]["state"]
    assert state["mode"] == "git"
    assert state["commit"]
    assert state["commitShort"] == state["commit"][:7]
    assert state["dirty"] is True
    assert "upstreamBranch" not in state
    assert "ahead" not in state
    assert "behind" not in state
    assert "updateAvailable" not in state


def test_version_list_branches_returns_git_branches_without_fetch(monkeypatch, tmp_path):
    core_path = tmp_path / "core"
    core_path.mkdir()
    repository = RepositoryState(
        path=core_path,
        is_git_repo=True,
        name="core",
        branch="main",
        commit="abcdef1234567890abcdef1234567890abcdef12",
    )
    calls = []

    def fake_list_branches(path, fetch=True):
        calls.append((path, fetch))
        return [
            BranchInfo(name="main", is_current=True, is_remote=False),
            BranchInfo(name="feature", is_current=False, is_remote=False),
            BranchInfo(name="release", is_current=False, is_remote=True),
        ]

    monkeypatch.setattr(operations, "inspect_repository", lambda path: repository)
    monkeypatch.setattr(operations, "list_branches", fake_list_branches)

    response = handle_request(
        {
            "requestId": "branches-1",
            "operation": "version.list_branches",
            "payload": {
                "instance": {
                    "kind": "comfyui",
                    "corePath": str(core_path),
                }
            },
        }
    )

    assert response["ok"] is True
    assert response["data"] == {
        "mode": "git",
        "fetched": False,
        "branches": [
            {"name": "main", "isCurrent": True, "isRemote": False},
            {"name": "feature", "isCurrent": False, "isRemote": False},
            {"name": "release", "isCurrent": False, "isRemote": True},
        ],
    }
    assert calls == [(core_path, False)]


def test_version_list_branches_rejects_invokeai_package_mode():
    response = handle_request(
        {
            "requestId": "branches-2",
            "operation": "version.list_branches",
            "payload": {
                "instance": {
                    "kind": "invokeai",
                    "corePath": "/tmp/not-used",
                }
            },
        }
    )

    assert response["requestId"] == "branches-2"
    assert response["ok"] is False
    assert response["error"]["code"] == "VERSION_BRANCHES_KIND_UNSUPPORTED"
    assert response["error"]["details"]["kind"] == "invokeai"


def test_version_list_branches_reads_real_git_repository_without_fetch(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git executable is not available")

    core_path = tmp_path / "core"
    core_path.mkdir()
    _run_git(core_path, "init")
    _run_git(core_path, "config", "user.email", "desktop-bridge@example.test")
    _run_git(core_path, "config", "user.name", "Desktop Bridge")
    tracked_file = core_path / "README.md"
    tracked_file.write_text("initial\n", encoding="utf-8")
    _run_git(core_path, "add", "README.md")
    _run_git(core_path, "commit", "-m", "initial")
    _run_git(core_path, "checkout", "-b", "feature/local")

    response = handle_request(
        {
            "requestId": "branches-real-git",
            "operation": "version.list_branches",
            "payload": {
                "instance": {
                    "kind": "sd_webui",
                    "corePath": str(core_path),
                }
            },
        }
    )

    assert response["ok"] is True
    assert response["data"]["mode"] == "git"
    assert response["data"]["fetched"] is False
    branches = {branch["name"]: branch for branch in response["data"]["branches"]}
    assert branches["feature/local"]["isCurrent"] is True
    assert branches["feature/local"]["isRemote"] is False
    assert any(name in branches for name in ("master", "main"))


def test_version_get_state_returns_invokeai_package_state(monkeypatch):
    monkeypatch.setattr(operations, "package_version", lambda package: "4.2.0")

    response = handle_request(
        {
            "requestId": "version-2",
            "operation": "version.get_state",
            "payload": {
                "instance": {
                    "kind": "invokeai",
                    "corePath": "/tmp/not-used",
                }
            },
        }
    )

    assert response["ok"] is True
    assert response["data"]["state"] == {
        "mode": "pypi_package",
        "packageName": "invokeai",
        "installedVersion": "4.2.0",
        "latestVersion": None,
        "updateAvailable": None,
    }


def test_version_get_state_reports_non_git_repository(monkeypatch, tmp_path):
    core_path = tmp_path / "core"
    repository = RepositoryState(
        path=core_path,
        is_git_repo=False,
        name="core",
        error="非 Git 仓库",
    )
    monkeypatch.setattr(operations, "inspect_repository", lambda path: repository)

    response = handle_request(
        {
            "requestId": "version-3",
            "operation": "version.get_state",
            "payload": {
                "instance": {
                    "kind": "comfyui",
                    "corePath": str(core_path),
                }
            },
        }
    )

    assert response["requestId"] == "version-3"
    assert response["ok"] is False
    assert response["error"]["code"] == "VERSION_STATE_NOT_GIT_REPOSITORY"
    assert response["error"]["details"]["repository"]["path"] == str(core_path)


def test_prepare_launch_returns_comfyui_launch_spec(tmp_path):
    core_path = tmp_path / "core"
    core_path.mkdir()
    entrypoint = core_path / "main.py"
    entrypoint.write_text("# comfyui\n", encoding="utf-8")
    python_path = tmp_path / "python" / "bin" / "python"

    response = handle_request(
        {
            "requestId": "launch-1",
            "operation": "instance.prepare_launch",
            "payload": {
                "instance": {
                    "kind": "comfyui",
                    "corePath": str(core_path),
                    "pythonPath": str(python_path),
                    "host": "127.0.0.1",
                    "port": 8188,
                    "launchArgs": ["--disable-auto-launch"],
                    "envVars": {"CUSTOM_ENV": "1"},
                }
            },
        }
    )

    assert response["ok"] is True
    launch = response["data"]["launch"]
    assert launch["cmd"] == str(python_path)
    assert launch["args"] == [
        str(entrypoint),
        "--disable-auto-launch",
        "--listen",
        "127.0.0.1",
        "--port",
        "8188",
    ]
    assert launch["cwd"] == str(core_path)
    assert launch["env"] == {
        "PYTHONNOUSERSITE": "1",
        "PYTHONUNBUFFERED": "1",
        "CUSTOM_ENV": "1",
    }
    assert launch["host"] == "127.0.0.1"
    assert launch["port"] == 8188
    assert launch["url"] == "http://127.0.0.1:8188"
    assert launch["readyCheck"] == {
        "type": "port",
        "host": "127.0.0.1",
        "port": 8188,
        "timeoutMs": 300000,
    }
    assert launch["healthCheck"] == {"kind": "http", "url": "http://127.0.0.1:8188"}


def test_prepare_launch_selects_sd_trainer_existing_entrypoint(tmp_path):
    core_path = tmp_path / "core"
    core_path.mkdir()
    entrypoint = core_path / "kohya_gui.py"
    entrypoint.write_text("# kohya\n", encoding="utf-8")

    response = handle_request(
        {
            "requestId": "launch-sd-trainer",
            "operation": "instance.prepare_launch",
            "payload": {
                "instance": {
                    "kind": "sd_trainer",
                    "corePath": str(core_path),
                    "pythonPath": "/tmp/python/bin/python",
                    "host": "0.0.0.0",
                    "port": 7860,
                    "launchArgs": [],
                    "envVars": {},
                }
            },
        }
    )

    assert response["ok"] is True
    launch = response["data"]["launch"]
    assert launch["args"] == [str(entrypoint), "--listen", "--server_port", "7860"]
    assert launch["url"] == "http://127.0.0.1:7860"


@pytest.mark.parametrize(
    ("kind", "entrypoint_name", "port"),
    [
        ("sd_webui", "launch.py", 7860),
        ("fooocus", "launch.py", 7865),
    ],
)
def test_prepare_launch_uses_git_core_entrypoint(kind, entrypoint_name, port, tmp_path):
    core_path = tmp_path / "core"
    core_path.mkdir()
    entrypoint = core_path / entrypoint_name
    entrypoint.write_text("# launch\n", encoding="utf-8")

    response = handle_request(
        {
            "requestId": f"launch-{kind}",
            "operation": "instance.prepare_launch",
            "payload": {
                "instance": {
                    "kind": kind,
                    "corePath": str(core_path),
                    "pythonPath": "/tmp/python/bin/python",
                    "host": "127.0.0.1",
                    "port": port,
                    "launchArgs": ["--theme", "dark"],
                    "envVars": {},
                }
            },
        }
    )

    assert response["ok"] is True
    launch = response["data"]["launch"]
    assert launch["args"] == [
        str(entrypoint),
        "--theme",
        "dark",
        "--port",
        str(port),
    ]
    assert launch["port"] == port


def test_prepare_launch_uses_qwen_tts_server_args(tmp_path):
    core_path = tmp_path / "core"
    core_path.mkdir()
    entrypoint = core_path / "launch.py"
    entrypoint.write_text("# qwen\n", encoding="utf-8")

    response = handle_request(
        {
            "requestId": "launch-qwen",
            "operation": "instance.prepare_launch",
            "payload": {
                "instance": {
                    "kind": "qwen_tts_webui",
                    "corePath": str(core_path),
                    "pythonPath": "/tmp/python/bin/python",
                    "host": "0.0.0.0",
                    "port": 7860,
                    "launchArgs": ["--api"],
                    "envVars": {},
                }
            },
        }
    )

    assert response["ok"] is True
    launch = response["data"]["launch"]
    assert launch["args"] == [
        str(entrypoint),
        "--api",
        "--server-name",
        "0.0.0.0",
        "--server-port",
        "7860",
    ]
    assert launch["url"] == "http://127.0.0.1:7860"


def test_prepare_launch_rejects_unsupported_invokeai(tmp_path):
    core_path = tmp_path / "core"
    core_path.mkdir()

    response = handle_request(
        {
            "requestId": "launch-invokeai",
            "operation": "instance.prepare_launch",
            "payload": {
                "instance": {
                    "kind": "invokeai",
                    "corePath": str(core_path),
                    "pythonPath": "/tmp/python/bin/python",
                    "host": "127.0.0.1",
                    "port": 9090,
                }
            },
        }
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "PREPARE_LAUNCH_KIND_UNSUPPORTED"
    assert response["error"]["details"]["kind"] == "invokeai"


def test_prepare_launch_rejects_missing_port(tmp_path):
    core_path = tmp_path / "core"
    core_path.mkdir()
    (core_path / "launch.py").write_text("# launch\n", encoding="utf-8")

    response = handle_request(
        {
            "requestId": "launch-no-port",
            "operation": "instance.prepare_launch",
            "payload": {
                "instance": {
                    "kind": "sd_webui",
                    "corePath": str(core_path),
                    "pythonPath": "/tmp/python/bin/python",
                    "host": "127.0.0.1",
                }
            },
        }
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "PREPARE_LAUNCH_PORT_MISSING"


def test_prepare_launch_rejects_missing_entrypoint(tmp_path):
    core_path = tmp_path / "core"
    core_path.mkdir()

    response = handle_request(
        {
            "requestId": "launch-missing-entrypoint",
            "operation": "instance.prepare_launch",
            "payload": {
                "instance": {
                    "kind": "fooocus",
                    "corePath": str(core_path),
                    "pythonPath": "/tmp/python/bin/python",
                    "host": "127.0.0.1",
                    "port": 7865,
                }
            },
        }
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "PREPARE_LAUNCH_ENTRYPOINT_MISSING"
    assert response["error"]["details"]["entrypoint"] == str(core_path / "launch.py")


def test_unsupported_operation_returns_structured_error():
    response = handle_request(
        {
            "requestId": "bad-1",
            "operation": "models.list_local",
            "payload": {},
        }
    )

    assert response["requestId"] == "bad-1"
    assert response["ok"] is False
    assert response["error"]["code"] == "BRIDGE_OPERATION_UNSUPPORTED"
    assert response["error"]["details"]["capabilities"] == [
        "bridge.info",
        "version.get_state",
        "version.list_branches",
        "instance.prepare_launch",
    ]


def test_main_reads_stdin_and_writes_one_response_line():
    stdout = StringIO()
    exit_code = main(
        stdin=StringIO('{"requestId":"info-2","operation":"bridge.info","payload":{}}\n'),
        stdout=stdout,
    )

    assert exit_code == 0
    lines = stdout.getvalue().splitlines()
    assert len(lines) == 1
    response = json.loads(lines[0])
    assert response["requestId"] == "info-2"
    assert response["ok"] is True


def test_invalid_payload_returns_structured_error():
    response = handle_request(
        {
            "requestId": "bad-2",
            "operation": "version.get_state",
            "payload": [],
        }
    )

    assert response["requestId"] == "bad-2"
    assert response["ok"] is False
    assert response["error"]["code"] == "BRIDGE_REQUEST_INVALID"


def _run_git(repo_path, *args):
    subprocess.run(
        ["git", *args],
        cwd=repo_path,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
