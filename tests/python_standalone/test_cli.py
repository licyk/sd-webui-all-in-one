"""Python Standalone 命令行测试"""

import argparse
import json
from pathlib import Path

import pytest

from sd_webui_all_in_one.cli_manager import python_standalone_cli
from sd_webui_all_in_one.python_standalone import sync
from sd_webui_all_in_one.python_standalone.types import RepoTarget, SyncConfig, SyncPlan
from tests.python_standalone.helpers import LINUX_312, make_asset, make_resource


# -- 命令行 ------------------------------------------------------------------
def _parse(argv):
    parser = argparse.ArgumentParser()
    python_standalone_cli.register_python_standalone(parser.add_subparsers())
    return parser.parse_args(argv)


def test_parse_platform_map_and_select_platforms():
    mapping = python_standalone_cli.parse_platform_map(["linux/musl=x86_64-unknown-linux-musl"])
    assert mapping["linux/musl"] == "x86_64-unknown-linux-musl"
    assert python_standalone_cli.select_platforms(mapping, ["linux/musl"]) == {"linux/musl": "x86_64-unknown-linux-musl"}
    with pytest.raises(ValueError):
        python_standalone_cli.parse_platform_map(["linux/musl"])
    with pytest.raises(ValueError):
        python_standalone_cli.select_platforms(mapping, ["linux/riscv64"])


def test_sync_cli_builds_config_and_writes_reports(tmp_path, monkeypatch):
    captured = {}

    def fake_create_sync_plan(config, manager):
        captured["config"] = config
        return SyncPlan(release_tag="20260901", source_repo=config.source_repo, targets=config.targets, tasks=[])

    monkeypatch.setattr(python_standalone_cli, "create_repo_manager", lambda hf_token, ms_token: object())
    monkeypatch.setattr(python_standalone_cli, "create_sync_plan", fake_create_sync_plan)
    args = _parse(
        [
            "python-standalone",
            "sync",
            "--release-tag",
            "20260901",
            "--versions",
            "3.11, 3.12",
            "--platforms",
            "linux/amd64",
            "--archive-format",
            ".tar.gz",
            "--no-ms",
            "--hf-repo-id",
            "me/repo",
            "--hf-repo-type",
            "dataset",
            "--report-json",
            str(tmp_path / "r.json"),
            "--report-markdown",
            str(tmp_path / "r.md"),
        ]
    )

    args.func(args)

    config = captured["config"]
    assert config.release_tag == "20260901"
    assert config.versions == ["3.11", "3.12"]
    assert config.platforms == {"linux/amd64": "x86_64-unknown-linux-gnu"}
    assert config.archive_format == ".tar.gz"
    assert config.targets == [RepoTarget("huggingface", "me/repo", "dataset")]
    assert json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))["release_tag"] == "20260901"
    assert "同步报告 (20260901)" in (tmp_path / "r.md").read_text(encoding="utf-8")


def test_sync_cli_dry_run_and_failure_exit(tmp_path, monkeypatch):
    task = sync.plan_tasks([("linux/amd64", make_asset(LINUX_312))], {}, SyncConfig())[0]
    plan = SyncPlan(release_tag="t", source_repo="r", targets=[], tasks=[task])
    monkeypatch.setattr(python_standalone_cli, "create_sync_plan", lambda config, manager: plan)
    monkeypatch.setattr(python_standalone_cli, "run_sync", lambda *args, **kwargs: [sync.SyncTaskResult(task=task, status="failed", error="x")])

    args = _parse(["python-standalone", "sync", "--no-upload", "--dry-run"])
    args.func(args)

    args = _parse(["python-standalone", "sync", "--no-upload"])
    with pytest.raises(SystemExit) as exc:
        args.func(args)
    assert exc.value.code == 1


def test_list_cli_outputs_latest_json(tmp_path, monkeypatch):
    items = [make_resource("3.12.12", "20260203"), make_resource("3.12.14", "20260924")]
    captured = {}

    def fake_collect(manager, targets, path_in_repo, revision, platforms):
        captured["targets"] = targets
        return items

    monkeypatch.setattr(python_standalone_cli, "create_repo_manager", lambda hf_token, ms_token: object())
    monkeypatch.setattr(python_standalone_cli, "collect_resources", fake_collect)
    monkeypatch.setattr(python_standalone_cli, "silence_logger_output", lambda: None)
    output = tmp_path / "list.json"

    args = _parse(["python-standalone", "list", "--no-hf", "--format", "json", "--output", str(output)])
    args.func(args)

    data = json.loads(output.read_text(encoding="utf-8"))
    assert captured["targets"] == [RepoTarget("modelscope", "licyks/sd-webui-all-in-one")]
    assert data["latest_only"] is True
    assert [r["version"] for r in data["resources"]] == ["3.12.14"]

    args = _parse(["python-standalone", "list", "--all", "--format", "markdown", "--output", str(output)])
    args.func(args)
    assert "3.12.12" in output.read_text(encoding="utf-8")


def test_list_cli_requires_a_repo():
    args = _parse(["python-standalone", "list", "--no-hf", "--no-ms"])
    with pytest.raises(ValueError):
        args.func(args)


def test_sync_cli_output_options(tmp_path, monkeypatch):
    captured = {}

    def fake_create_sync_plan(config, manager):
        captured["config"] = config
        return SyncPlan(release_tag="t", source_repo="r", targets=config.targets, tasks=[])

    monkeypatch.setattr(python_standalone_cli, "create_repo_manager", lambda hf_token, ms_token: object())
    monkeypatch.setattr(python_standalone_cli, "create_sync_plan", fake_create_sync_plan)

    args = _parse(["python-standalone", "sync", "--temp-output"])
    args.func(args)
    assert captured["config"].temp_output is True

    args = _parse(["python-standalone", "sync", "--output-dir", str(tmp_path / "dist")])
    args.func(args)
    assert captured["config"].temp_output is False
    assert captured["config"].output_dir == tmp_path / "dist"

    args = _parse(["python-standalone", "sync"])
    args.func(args)
    assert captured["config"].output_dir == Path("python_dist")

    with pytest.raises(SystemExit):
        _parse(["python-standalone", "sync", "--temp-output", "--output-dir", str(tmp_path)])
