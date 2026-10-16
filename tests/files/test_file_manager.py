"""文件管理测试"""

import os

import pytest

from sd_webui_all_in_one import file_manager


def test_file_manager_copy_move_remove_scan_and_sync(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("a", encoding="utf-8")
    nested = src / "nested"
    nested.mkdir()
    (nested / "b.txt").write_text("b", encoding="utf-8")

    copied = tmp_path / "copied"
    file_manager.copy_files(src, copied)
    assert (copied / "a.txt").read_text(encoding="utf-8") == "a"
    assert (copied / "nested" / "b.txt").read_text(encoding="utf-8") == "b"

    moved = tmp_path / "moved.txt"
    file_manager.move_files(copied / "a.txt", moved)
    assert moved.read_text(encoding="utf-8") == "a"
    assert not (copied / "a.txt").exists()

    files = {p.name for p in file_manager.get_file_list(src, show_progress=False)}
    assert files == {"a.txt", "b.txt"}

    dst = tmp_path / "dst"
    (dst / "nested").mkdir(parents=True)
    (dst / "a.txt").write_text("a", encoding="utf-8")
    missing = file_manager.get_sync_files(src, dst)
    assert [p.relative_to(src).as_posix() for p in missing] == ["nested/b.txt"]

    file_manager.sync_files(src, dst)
    assert (dst / "nested" / "b.txt").read_text(encoding="utf-8") == "b"

    file_manager.remove_files(moved)
    assert not moved.exists()


def test_file_manager_copy_merge_directly_merges_directory(tmp_path):
    src = tmp_path / "t"
    src.mkdir()
    (src / "a.txt").write_text("new", encoding="utf-8")
    (src / "nested").mkdir()
    (src / "nested" / "b.txt").write_text("b", encoding="utf-8")

    dst = tmp_path / "test"
    dst.mkdir()
    (dst / "a.txt").write_text("old", encoding="utf-8")
    (dst / "keep.txt").write_text("keep", encoding="utf-8")
    (dst / "nested").mkdir()
    (dst / "nested" / "old.txt").write_text("old", encoding="utf-8")

    file_manager.copy_files_merge(src, dst)

    assert not (dst / "t").exists()
    assert (dst / "a.txt").read_text(encoding="utf-8") == "new"
    assert (dst / "keep.txt").read_text(encoding="utf-8") == "keep"
    assert (dst / "nested" / "b.txt").read_text(encoding="utf-8") == "b"
    assert (dst / "nested" / "old.txt").read_text(encoding="utf-8") == "old"
    assert (src / "a.txt").exists()


def test_file_manager_move_merge_directly_merges_directory(tmp_path):
    src = tmp_path / "t"
    src.mkdir()
    (src / "a.txt").write_text("new", encoding="utf-8")
    (src / "nested").mkdir()
    (src / "nested" / "b.txt").write_text("b", encoding="utf-8")

    dst = tmp_path / "test"
    dst.mkdir()
    (dst / "a.txt").write_text("old", encoding="utf-8")
    (dst / "keep.txt").write_text("keep", encoding="utf-8")
    (dst / "nested").mkdir()
    (dst / "nested" / "old.txt").write_text("old", encoding="utf-8")

    file_manager.move_files_merge(src, dst)

    assert not src.exists()
    assert not (dst / "t").exists()
    assert not (dst / "nested" / "nested").exists()
    assert (dst / "a.txt").read_text(encoding="utf-8") == "new"
    assert (dst / "keep.txt").read_text(encoding="utf-8") == "keep"
    assert (dst / "nested" / "b.txt").read_text(encoding="utf-8") == "b"
    assert (dst / "nested" / "old.txt").read_text(encoding="utf-8") == "old"


def test_file_manager_copy_preserves_top_level_symlink(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("target", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to("target.txt")
    dst = tmp_path / "dst"
    dst.mkdir()

    file_manager.copy_files(link, dst)

    copied_link = dst / "link.txt"
    assert copied_link.is_symlink()
    assert os.readlink(copied_link) == "target.txt"
    assert not (dst / "target.txt").exists()
    assert target.read_text(encoding="utf-8") == "target"


def test_file_manager_move_preserves_top_level_symlink(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("target", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to("target.txt")
    moved_link = tmp_path / "moved-link.txt"

    file_manager.move_files(link, moved_link)

    assert not link.is_symlink()
    assert moved_link.is_symlink()
    assert os.readlink(moved_link) == "target.txt"
    assert target.read_text(encoding="utf-8") == "target"


def test_file_manager_merge_variants_preserve_directory_symlink(tmp_path):
    target_dir = tmp_path / "target-dir"
    target_dir.mkdir()
    (target_dir / "a.txt").write_text("a", encoding="utf-8")
    copy_link = tmp_path / "copy-link"
    copy_link.symlink_to("target-dir")
    copy_dst = tmp_path / "copy-dst"
    copy_dst.mkdir()

    file_manager.copy_files_merge(copy_link, copy_dst)

    copied_link = copy_dst / "copy-link"
    assert copied_link.is_symlink()
    assert os.readlink(copied_link) == "target-dir"
    assert not (copy_dst / "a.txt").exists()

    move_link = tmp_path / "move-link"
    move_link.symlink_to("target-dir")
    move_dst = tmp_path / "move-dst"
    move_dst.mkdir()

    file_manager.move_files_merge(move_link, move_dst)

    moved_link = move_dst / "move-link"
    assert not move_link.is_symlink()
    assert moved_link.is_symlink()
    assert os.readlink(moved_link) == "target-dir"
    assert not (move_dst / "a.txt").exists()
    assert (target_dir / "a.txt").read_text(encoding="utf-8") == "a"


def test_sync_files_and_create_symlink_preserves_existing_link_contents(tmp_path):
    src = tmp_path / "drive" / "models"
    link = tmp_path / "workspace" / "models"
    link.mkdir(parents=True)
    (link / "old.txt").write_text("old", encoding="utf-8")

    file_manager.sync_files_and_create_symlink(src, link)

    assert link.is_symlink()
    assert link.resolve() == src.resolve()
    assert (src / "old.txt").read_text(encoding="utf-8") == "old"


def test_file_manager_error_paths_tree_and_empty_status(tmp_path, capsys):
    with pytest.raises(FileNotFoundError):
        file_manager.copy_files(tmp_path / "missing", tmp_path / "out")

    src = tmp_path / "src"
    src.mkdir()
    (src / "visible.txt").write_text("visible", encoding="utf-8")
    (src / ".hidden").write_text("hidden", encoding="utf-8")

    with pytest.raises(ValueError):
        file_manager.copy_files(src, src / "child")

    empty = tmp_path / "empty"
    empty.mkdir()
    assert file_manager.is_folder_empty(empty) is True
    assert file_manager.is_folder_empty(src) is False
    with pytest.raises(ValueError):
        file_manager.is_folder_empty(src / "visible.txt")

    file_manager.generate_dir_tree(src, max_depth=1, show_hidden=False)
    output = capsys.readouterr().out
    assert "visible.txt" in output
    assert ".hidden" not in output

    file_manager.display_directories(src, tmp_path / "missing", recursive=False, show_hidden=False)
    assert "visible.txt" in capsys.readouterr().out
