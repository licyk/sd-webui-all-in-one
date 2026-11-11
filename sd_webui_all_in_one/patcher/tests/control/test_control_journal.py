"""PatchJournal 可撤销日志测试。"""

import os
import types
from typing import Any

import pytest

from sd_webui_all_in_one_hotpatcher.control.journal import NOTSET, PatchJournal

ENV_NAME = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TEST_CONTROL_JOURNAL"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(ENV_NAME, raising=False)
    yield
    os.environ.pop(ENV_NAME, None)


def test_notset_round_trip_deletes_new_attribute():
    module = types.ModuleType("hp_control_journal_module")
    journal = PatchJournal()

    entry = journal.set_attr(module, "added", 1, raising=False)

    assert entry.old_value is NOTSET
    assert module.added == 1
    journal.undo()
    assert not hasattr(module, "added")


def test_set_attr_raising_on_missing_attribute_records_nothing():
    module = types.ModuleType("hp_control_journal_module")
    journal = PatchJournal()

    with pytest.raises(AttributeError, match="missing"):
        journal.set_attr(module, "missing", 1)

    assert len(journal) == 0


def test_class_descriptors_survive_set_and_undo_by_identity():
    class Target:
        @staticmethod
        def static():
            return "static"

        @classmethod
        def klass(cls):
            return "class"

        @property
        def prop(self):
            return "prop"

    originals = {name: Target.__dict__[name] for name in ("static", "klass", "prop")}
    journal = PatchJournal()

    for name in originals:
        journal.set_attr(Target, name, lambda *args: "patched")
    journal.del_attr(Target, "static")
    assert "static" not in Target.__dict__

    journal.undo()

    for name, original in originals.items():
        assert Target.__dict__[name] is original
    assert Target.static() == "static"
    assert Target.klass() == "class"
    assert Target().prop == "prop"


def test_inherited_class_attribute_is_deleted_from_subclass_on_undo():
    class Base:
        value = "base"

    class Child(Base):
        pass

    journal = PatchJournal()
    journal.set_attr(Child, "value", "child")
    assert Child.value == "child"

    journal.undo()

    assert "value" not in Child.__dict__
    assert Child.value == "base"


def test_instance_attribute_shadowing_class_attribute_is_removed_on_undo():
    class Target:
        value = "class"

    instance = Target()
    journal = PatchJournal()

    journal.set_attr(instance, "value", "instance")
    assert vars(instance) == {"value": "instance"}

    journal.undo()

    assert "value" not in vars(instance)
    assert instance.value == "class"
    Target.value = "changed"
    assert instance.value == "changed"


def test_instance_existing_attribute_is_restored():
    class Target:
        value: str

    instance = Target()
    instance.value = "old"
    journal = PatchJournal()

    journal.set_attr(instance, "value", "new")
    journal.del_attr(instance, "value")
    assert not hasattr(instance, "value")

    journal.undo()

    assert vars(instance) == {"value": "old"}


def test_dict_items_set_and_delete_are_restored():
    mapping = {"keep": 1, "drop": 2}
    journal = PatchJournal()

    journal.set_item(mapping, "keep", 10)
    journal.set_item(mapping, "new", 3)
    journal.del_item(mapping, "drop")
    assert journal.del_item(mapping, "absent", raising=False) is None
    with pytest.raises(KeyError):
        journal.del_item(mapping, "absent")
    assert mapping == {"keep": 10, "new": 3}

    journal.undo()

    assert mapping == {"keep": 1, "drop": 2}


def test_item_already_removed_counts_as_reverted():
    mapping = {}
    journal = PatchJournal()
    journal.set_item(mapping, "new", 1)
    del mapping["new"]

    report = journal.undo()

    assert report.ok
    assert mapping == {}


def test_env_set_prepend_and_delete_are_restored():
    journal = PatchJournal()

    journal.set_env(ENV_NAME, "first")
    assert os.environ[ENV_NAME] == "first"
    journal.set_env(ENV_NAME, "second", prepend=os.pathsep)
    assert os.environ[ENV_NAME] == f"second{os.pathsep}first"
    journal.del_env(ENV_NAME)
    assert ENV_NAME not in os.environ
    assert journal.del_env(ENV_NAME, raising=False) is None

    journal.undo()

    assert ENV_NAME not in os.environ


def test_env_existing_value_is_restored(monkeypatch):
    monkeypatch.setenv(ENV_NAME, "original")
    journal = PatchJournal()

    non_string: Any = 5
    with pytest.warns(RuntimeWarning):
        journal.set_env(ENV_NAME, non_string)
    assert os.environ[ENV_NAME] == "5"

    journal.undo()

    assert os.environ[ENV_NAME] == "original"


def test_syspath_style_list_removes_only_inserted_entry():
    path_list = ["/a", "/b"]
    journal = PatchJournal()

    journal.syspath_prepend("/inserted", path_list=path_list)
    path_list.append("/later")
    path_list.insert(0, "/other")
    assert path_list == ["/other", "/inserted", "/a", "/b", "/later"]

    journal.undo()

    assert path_list == ["/other", "/a", "/b", "/later"]


def test_list_insert_removes_inserted_object_by_identity_first():
    first = ["dup"]
    second = ["dup"]
    sequence = [first]
    journal = PatchJournal()

    journal.insert(sequence, 1, second)
    journal.undo()

    assert len(sequence) == 1
    assert sequence[0] is first


def test_undo_runs_lifo_across_entry_kinds():
    calls = []
    module = types.ModuleType("hp_control_journal_module")
    journal = PatchJournal()

    journal.record_callback(lambda: calls.append("first"), "first")
    journal.set_attr(module, "value", 1, raising=False)
    journal.record_callback(lambda: calls.append(("second", hasattr(module, "value"))), "second")

    report = journal.undo()

    assert calls == [("second", True), "first"]
    assert [result.entry.label for result in report.results] == ["second", "hp_control_journal_module.value", "first"]


def test_failing_entry_does_not_stop_others_and_first_error_is_reported():
    calls = []
    journal = PatchJournal()

    def boom(message):
        def undo():
            raise RuntimeError(message)

        return undo

    journal.record_callback(lambda: calls.append("oldest"), "oldest")
    journal.record_callback(boom("older failure"), "older")
    journal.record_callback(lambda: calls.append("middle"), "middle")
    journal.record_callback(boom("newest failure"), "newest")

    report = journal.undo()

    assert calls == ["middle", "oldest"]
    assert not report.ok
    assert [str(error) for error in report.errors] == ["newest failure", "older failure"]
    assert str(report.first_error) == "newest failure"
    with pytest.raises(RuntimeError, match="newest failure"):
        report.raise_first_error()
    assert report.to_dict()["failed"][0]["label"] == "newest"


def test_undo_is_idempotent_and_does_not_retry_failures():
    calls = []
    journal = PatchJournal()

    def failing():
        calls.append("failing")
        raise ValueError("nope")

    journal.record_callback(failing, "failing")
    journal.record_callback(lambda: calls.append("ok"), "ok")

    first = journal.undo()
    second = journal.undo()

    assert calls == ["ok", "failing"]
    assert len(first.results) == 2
    assert second.results == []
    assert second.ok
    assert len(journal) == 0


def test_base_exception_restores_unrun_entries():
    calls = []
    journal = PatchJournal()

    def interrupt():
        raise KeyboardInterrupt

    journal.record_callback(lambda: calls.append("oldest"), "oldest")
    journal.record_callback(interrupt, "interrupt")
    journal.record_callback(lambda: calls.append("newest"), "newest")

    with pytest.raises(KeyboardInterrupt):
        journal.undo()

    assert calls == ["newest"]
    assert [entry["label"] for entry in journal.entries()] == ["oldest"]


def test_selective_undo_by_handle_id():
    mapping = {}
    journal = PatchJournal()
    journal.set_item(mapping, "a", 1, handle_id="patch_a")
    journal.set_item(mapping, "b", 2, handle_id="patch_b")
    journal.set_item(mapping, "a2", 3, handle_id="patch_a")

    report = journal.undo(handle_id="patch_a")

    assert [result.entry.key for result in report.results] == ["a2", "a"]
    assert mapping == {"b": 2}
    assert journal.handle_ids() == ["patch_b"]


def test_entries_introspection():
    module = types.ModuleType("hp_control_journal_module")
    journal = PatchJournal()
    journal.set_attr(module, "value", 1, raising=False, handle_id="patch_1")
    journal.set_item({"k": 0}, "k", 1)

    entries = journal.entries()

    assert len(journal) == 2
    assert entries[0] == {
        "kind": "attr",
        "label": "hp_control_journal_module.value",
        "handle_id": "patch_1",
        "key": "'value'",
        "had_previous_value": False,
    }
    assert entries[1]["kind"] == "item"
    assert entries[1]["had_previous_value"] is True
    assert journal.entries(handle_id="patch_1") == entries[:1]


def test_record_callback_requires_callable():
    with pytest.raises(TypeError):
        not_callable: Any = "not callable"
        PatchJournal().record_callback(not_callable, "label")
