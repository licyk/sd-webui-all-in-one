"""环境快照保存, 列出与读取测试"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from sd_webui_all_in_one.base_manager import snapshot as snapshot_utils
from sd_webui_all_in_one.base_manager.gui.snapshot_gui import (
    format_snapshot_timestamp,
    list_snapshot_files,
)
from sd_webui_all_in_one.base_manager.snapshot import collection as snapshot_collection
from sd_webui_all_in_one.base_manager.snapshot import storage as snapshot_storage
from sd_webui_all_in_one.cli_manager.snapshot import create_pre_operation_snapshot, output_snapshot
from tests.base_manager.snapshot.helpers import make_extension_snapshot, make_package_snapshot, make_webui_snapshot


def test_output_snapshot_writes_default_or_explicit_directory(monkeypatch, tmp_path):
    snapshot = make_webui_snapshot(tmp_path / "demo")
    snapshot_json = snapshot_utils.snapshot_to_dict(snapshot)
    default_dir = tmp_path / "snapshots"
    default_file = default_dir / "demo-2026-06-18T000000Z.json"

    monkeypatch.setattr(snapshot_storage, "SD_WEBUI_ALL_IN_ONE_SNAPSHOT_DIR", default_dir)

    assert output_snapshot(lambda: snapshot) == default_file
    assert json.loads(default_file.read_text(encoding="utf-8")) == snapshot_json

    output_dir = tmp_path / "custom-snapshots"
    output_file = output_dir / "demo-2026-06-18T000000Z.json"
    assert output_snapshot(lambda: snapshot, output=output_dir) == output_file
    assert json.loads(output_file.read_text(encoding="utf-8")) == snapshot_json


def test_create_pre_operation_snapshot_writes_to_directory(tmp_path):
    snapshot = make_webui_snapshot(tmp_path / "demo")
    output_dir = tmp_path / "pre-operation-snapshots"
    output_file = output_dir / "demo-2026-06-18T000000Z.json"

    assert create_pre_operation_snapshot(lambda: snapshot, "update demo", snapshot_dir=output_dir) == output_file
    assert json.loads(output_file.read_text(encoding="utf-8")) == snapshot_utils.snapshot_to_dict(snapshot)


def test_create_pre_operation_snapshot_failure_or_disabled_does_not_raise(tmp_path):
    called = False

    def disabled_factory():
        nonlocal called
        called = True
        raise AssertionError("disabled snapshot should not call factory")

    def failing_factory():
        raise RuntimeError("boom")

    assert create_pre_operation_snapshot(disabled_factory, "disabled demo", snapshot_enabled=False, snapshot_dir=tmp_path) is None
    assert called is False
    assert create_pre_operation_snapshot(failing_factory, "failing demo", snapshot_dir=tmp_path) is None


def test_webui_snapshot_operations_share_the_same_default_directory(tmp_path):
    webui_path = tmp_path / "demo"
    webui_path.mkdir()

    def factory(path: Path, include_packages: bool):
        assert path == webui_path
        assert include_packages is False
        return make_webui_snapshot(path)

    saved = snapshot_utils.create_webui_snapshot(webui_path, factory, include_packages=False)

    assert saved.path.parent == webui_path / "snapshots"
    assert saved.snapshot.webui.path == webui_path
    summaries = snapshot_utils.list_webui_snapshots(webui_path)
    assert len(summaries) == 1
    assert summaries[0].path == saved.path
    assert summaries[0].webui_type == "demo"
    assert snapshot_utils.delete_snapshot(saved.path) == saved.path
    assert snapshot_utils.list_webui_snapshots(webui_path) == []


def test_list_webui_snapshots_reports_invalid_files(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    invalid_path = snapshot_dir / "broken.json"
    invalid_path.write_text("{", encoding="utf-8")

    summaries = snapshot_utils.list_webui_snapshots(tmp_path)

    assert len(summaries) == 1
    assert summaries[0].path == invalid_path
    assert summaries[0].error


def test_format_snapshot_timestamp_uses_local_time_and_keeps_invalid_values():
    local_timestamp = datetime.fromisoformat("2026-06-18T00:00:00+00:00").astimezone()
    suffix = local_timestamp.strftime("%Z") or local_timestamp.strftime("%z")
    expected = f"{local_timestamp:%Y-%m-%d %H:%M:%S}{f' {suffix}' if suffix else ''}"

    assert format_snapshot_timestamp("2026-06-18T00:00:00Z") == expected
    assert format_snapshot_timestamp("not-a-timestamp") == "not-a-timestamp"


def test_list_snapshot_files_reads_valid_snapshots_sorted_by_created_at(tmp_path):
    old_snapshot = make_webui_snapshot(tmp_path / "old")
    old_snapshot.created_at = "2026-06-17T00:00:00Z"
    old_snapshot.packages = [make_package_snapshot("old", "1.0.0")]
    old_path = snapshot_utils.save_snapshot(old_snapshot, tmp_path / "old.json")

    new_snapshot = make_webui_snapshot(tmp_path / "new")
    new_snapshot.created_at = "2026-06-18T00:00:00Z"
    new_snapshot.extensions = [make_extension_snapshot("ext", tmp_path / "new" / "extensions" / "ext", True)]
    new_path = snapshot_utils.save_snapshot(new_snapshot, tmp_path / "new.json")
    (tmp_path / "invalid.json").write_text("{", encoding="utf-8")
    (tmp_path / "note.txt").write_text("not a snapshot", encoding="utf-8")

    items = list_snapshot_files(tmp_path)

    assert [item.path for item in items] == [new_path, old_path]
    assert items[0].filename == "new.json"
    assert items[0].created_at == "2026-06-18T00:00:00Z"
    assert items[0].created_at_display == format_snapshot_timestamp("2026-06-18T00:00:00Z")
    assert items[0].webui_name == "Demo"
    assert items[0].webui_type == "demo"
    assert items[0].package_count == 0
    assert items[0].extension_count == 1
    assert items[1].package_count == 1


def test_list_snapshot_files_keeps_invalid_timestamp_display(tmp_path):
    snapshot = make_webui_snapshot(tmp_path / "invalid-time")
    snapshot.created_at = "invalid-time"
    path = snapshot_utils.save_snapshot(snapshot, tmp_path / "invalid-time.json")

    items = list_snapshot_files(tmp_path)

    assert len(items) == 1
    assert items[0].path == path
    assert items[0].created_at == "invalid-time"
    assert items[0].created_at_display == "invalid-time"


def test_list_snapshot_files_returns_empty_for_missing_directory(tmp_path):
    assert list_snapshot_files(tmp_path / "missing") == []


def test_load_snapshot_roundtrip_and_rejects_unsupported_schema(tmp_path):
    local_source = tmp_path / "local-package"
    local_source.mkdir()
    snapshot = make_webui_snapshot(tmp_path / "demo")
    snapshot.packages = [
        snapshot_utils.PackageSnapshot(
            name="demo-editable",
            version="1.2.3",
            installer="pip",
            requested=True,
            editable=True,
            direct_url=snapshot_utils.DirectUrlSnapshot(
                url=local_source.as_uri(),
                dir_info=snapshot_utils.DirectUrlDirInfo(editable=True),
            ),
            source_type="local-directory",
            wheel=snapshot_utils.WheelSnapshot(generator="bdist_wheel", root_is_purelib=True, tags=["py3-none-any"]),
        )
    ]
    snapshot.extensions = [make_extension_snapshot("ext", tmp_path / "demo" / "extensions" / "ext", True)]

    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    loaded = snapshot_utils.load_snapshot(output)

    assert snapshot_utils.snapshot_to_dict(loaded) == snapshot_utils.snapshot_to_dict(snapshot)

    unsupported = tmp_path / "unsupported.json"
    unsupported.write_text(json.dumps({"schema_version": 999}), encoding="utf-8")
    with pytest.raises(ValueError, match="不支持的快照结构版本"):
        snapshot_utils.load_snapshot(unsupported)


def test_load_legacy_snapshot_without_system_field_uses_current_system(monkeypatch, tmp_path):
    snapshot = make_webui_snapshot(tmp_path / "demo")
    snapshot_data = snapshot_utils.snapshot_to_dict(snapshot)
    assert isinstance(snapshot_data, dict)
    snapshot_data.pop("system")
    output = tmp_path / "legacy.json"
    output.write_text(json.dumps(snapshot_data), encoding="utf-8")
    monkeypatch.setattr(snapshot_collection, "collect_system_info", lambda: snapshot_utils.SystemSnapshot(system="CurrentOS", architecture="riscv64"))

    loaded = snapshot_utils.load_snapshot(output)

    assert loaded.system == snapshot_utils.SystemSnapshot(system="CurrentOS", architecture="riscv64")
