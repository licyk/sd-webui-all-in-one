import json
import shutil
import subprocess
from io import StringIO

import pytest

from sd_webui_all_in_one.base_manager.repository_inspector import RepositoryState
from sd_webui_all_in_one.desktop_bridge import operations
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
    assert response["data"]["capabilities"] == ["bridge.info", "version.get_state"]
    assert "get_install_catalog" not in response["data"]["capabilities"]
    assert "instance.prepare_launch" not in response["data"]["capabilities"]


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
    assert response["error"]["details"]["capabilities"] == ["bridge.info", "version.get_state"]


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
