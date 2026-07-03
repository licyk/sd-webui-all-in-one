"""Desktop bridge operations.

This module is intentionally small and read-only. It adapts existing library
helpers to the JSON payloads expected by the Tauri desktop shell without
touching launcher configuration files or invoking GUI code.
"""

from __future__ import annotations

from dataclasses import asdict
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any

from sd_webui_all_in_one.base_manager.repository_inspector import inspect_repository, run_git_output
from sd_webui_all_in_one.desktop_bridge import BRIDGE_PROTOCOL, CAPABILITIES
from sd_webui_all_in_one.base_manager.version_manager import list_branches
from sd_webui_all_in_one.version import VERSION


GIT_CORE_KINDS = {
    "sd_webui",
    "comfyui",
    "fooocus",
    "sd_trainer",
    "qwen_tts_webui",
}
PACKAGE_VERSION_KINDS = {
    "invokeai": "invokeai",
}


class BridgeOperationError(Exception):
    """Structured bridge operation failure."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def dispatch_operation(operation: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    """
    Dispatch a desktop bridge operation.

    Args:
        operation (str):
            Operation name from the bridge request.
        payload (dict[str, Any] | None):
            Request payload.

    Returns:
        dict[str, Any]: JSON-serializable operation data.
    """
    payload = payload or {}
    if operation == "bridge.info":
        return bridge_info()
    if operation == "version.get_state":
        return get_version_state(payload)
    if operation == "version.list_branches":
        return list_version_branches(payload)
    raise BridgeOperationError(
        "BRIDGE_OPERATION_UNSUPPORTED",
        f"Unsupported desktop bridge operation: {operation}",
        {"operation": operation, "capabilities": list(CAPABILITIES)},
    )


def bridge_info() -> dict[str, Any]:
    """
    Return desktop bridge metadata.

    Returns:
        dict[str, Any]: Bridge protocol metadata.
    """
    return {
        "libraryVersion": VERSION,
        "libraryCommit": None,
        "bridgeProtocol": BRIDGE_PROTOCOL,
        "capabilities": list(CAPABILITIES),
    }


def get_version_state(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Return read-only version state for a desktop instance.

    Args:
        payload (dict[str, Any]):
            Desktop bridge payload containing an instance object.

    Returns:
        dict[str, Any]: Version state wrapped in ``state``.
    """
    instance = _require_mapping(payload, "instance")
    kind = _require_string(instance, "kind")
    if kind in GIT_CORE_KINDS:
        core_path = Path(_require_string(instance, "corePath"))
        return {"state": _git_version_state(kind, core_path)}
    if kind in PACKAGE_VERSION_KINDS:
        return {"state": _package_version_state(PACKAGE_VERSION_KINDS[kind])}
    raise BridgeOperationError(
        "VERSION_STATE_KIND_UNSUPPORTED",
        f"Unsupported instance kind for version state: {kind}",
        {"kind": kind},
    )


def list_version_branches(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Return local Git branches for a desktop instance without fetching.

    Args:
        payload (dict[str, Any]):
            Desktop bridge payload containing an instance object.

    Returns:
        dict[str, Any]: Branch list wrapped in ``branches``.
    """
    instance = _require_mapping(payload, "instance")
    kind = _require_string(instance, "kind")
    if kind in GIT_CORE_KINDS:
        core_path = Path(_require_string(instance, "corePath"))
        return {"mode": "git", "fetched": False, "branches": _git_version_branches(kind, core_path)}
    raise BridgeOperationError(
        "VERSION_BRANCHES_KIND_UNSUPPORTED",
        f"Unsupported instance kind for branch listing: {kind}",
        {"kind": kind},
    )


def _git_version_state(kind: str, core_path: Path) -> dict[str, Any]:
    repository = inspect_repository(core_path)
    if not repository.is_git_repo:
        raise BridgeOperationError(
            "VERSION_STATE_NOT_GIT_REPOSITORY",
            "Instance corePath is not a Git repository",
            {
                "kind": kind,
                "corePath": str(core_path),
                "repository": _jsonable_repository_state(repository),
            },
        )
    if not repository.commit:
        raise BridgeOperationError(
            "VERSION_STATE_COMMIT_MISSING",
            "Git repository state does not contain a current commit",
            {
                "kind": kind,
                "corePath": str(core_path),
                "repository": _jsonable_repository_state(repository),
            },
        )

    ahead, behind = _git_ahead_behind(core_path)
    state = {
        "mode": "git",
        "branch": repository.branch,
        "commit": repository.commit,
        "commitShort": repository.commit[:7],
        "commitDate": repository.commit_date,
        "dirty": _git_dirty(core_path),
        "remote": repository.url,
        "upstreamBranch": _git_upstream_branch(core_path),
        "ahead": ahead,
        "behind": behind,
        "updateAvailable": behind > 0 if behind is not None else None,
    }
    return _strip_none_values(state)


def _package_version_state(package_name: str) -> dict[str, Any]:
    try:
        installed_version = package_version(package_name)
    except PackageNotFoundError as error:
        raise BridgeOperationError(
            "VERSION_STATE_PACKAGE_NOT_FOUND",
            f"Python package is not installed: {package_name}",
            {"packageName": package_name},
        ) from error

    return {
        "mode": "pypi_package",
        "packageName": package_name,
        "installedVersion": installed_version,
        "latestVersion": None,
        "updateAvailable": None,
    }


def _git_version_branches(kind: str, core_path: Path) -> list[dict[str, Any]]:
    repository = inspect_repository(core_path)
    if not repository.is_git_repo:
        raise BridgeOperationError(
            "VERSION_BRANCHES_NOT_GIT_REPOSITORY",
            "Instance corePath is not a Git repository",
            {
                "kind": kind,
                "corePath": str(core_path),
                "repository": _jsonable_repository_state(repository),
            },
        )

    try:
        branches = list_branches(core_path, fetch=False)
    except Exception as error:
        raise BridgeOperationError(
            "VERSION_BRANCHES_LIST_FAILED",
            f"Failed to list Git branches: {error}",
            {
                "kind": kind,
                "corePath": str(core_path),
            },
        ) from error

    return [
        {
            "name": branch.name,
            "isCurrent": branch.is_current,
            "isRemote": branch.is_remote,
        }
        for branch in branches
        if branch.name
    ]


def _git_dirty(path: Path) -> bool | None:
    try:
        return run_git_output(path, "--no-optional-locks", "status", "--porcelain") != ""
    except Exception:
        return None


def _git_upstream_branch(path: Path) -> str | None:
    try:
        upstream = run_git_output(path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    except Exception:
        return None
    return upstream or None


def _git_ahead_behind(path: Path) -> tuple[int | None, int | None]:
    try:
        output = run_git_output(path, "rev-list", "--left-right", "--count", "HEAD...@{u}")
    except Exception:
        return None, None
    parts = output.split()
    if len(parts) != 2:
        return None, None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None, None


def _jsonable_repository_state(repository: Any) -> dict[str, Any]:
    value = asdict(repository)
    if isinstance(value.get("path"), Path):
        value["path"] = str(value["path"])
    return value


def _require_mapping(payload: dict[str, Any], field: str) -> dict[str, Any]:
    value = payload.get(field)
    if isinstance(value, dict):
        return value
    raise BridgeOperationError(
        "BRIDGE_REQUEST_INVALID",
        f"Bridge request field {field} must be an object",
        {"field": field},
    )


def _require_string(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise BridgeOperationError(
        "BRIDGE_REQUEST_INVALID",
        f"Bridge request field {field} must be a non-empty string",
        {"field": field},
    )


def _strip_none_values(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}
