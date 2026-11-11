"""PatchSet / PatchContext / 句柄注册表测试。"""

import contextvars
import os
import sys
import threading
import types

import pytest

from sd_webui_all_in_one_hotpatcher.control.handles import (
    PatchOutcome,
    PatchOutcomeKind,
    PatchStatus,
    allocate_patch_id,
    create_patch_handle,
    get_patch_handle,
    list_patch_handles,
)
from sd_webui_all_in_one_hotpatcher.control.patchset import (
    PatchSet,
    PatchSetClosedError,
    PatchSetStatus,
    current_patch_context,
    get_patch_set,
    list_patch_sets,
    register_patch_set,
    remove_patch_set,
)
from sd_webui_all_in_one_hotpatcher.state import HotpatcherState

ENV_NAME = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TEST_CONTROL_PATCHSET"
MODULE_NAME = "hp_control_patchset_target"


@pytest.fixture
def state():
    return HotpatcherState()


@pytest.fixture
def target_module():
    module = types.ModuleType(MODULE_NAME)
    module.__dict__.update(FLAG=False, REGISTRY={"existing": 1})
    sys.modules[MODULE_NAME] = module
    yield module
    sys.modules.pop(MODULE_NAME, None)


def last_outcome(handle):
    outcome = handle.last_outcome
    assert outcome is not None
    return outcome


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(ENV_NAME, raising=False)
    yield
    os.environ.pop(ENV_NAME, None)


@pytest.fixture(autouse=True)
def restore_sys_path():
    before_path = list(sys.path)
    yield
    sys.path[:] = before_path


def test_operations_apply_and_unload_reports_per_handle(state, target_module):
    path_list_before = list(sys.path)
    patch_set = PatchSet("fix-target", state=state)

    with patch_set as ctx:
        attr = ctx.set_attr(f"{MODULE_NAME}:FLAG", True)
        new_attr = ctx.set_attr(target_module, "ADDED", 1, raising=False)
        item = ctx.set_item(target_module.REGISTRY, "new", 2)
        env = ctx.set_env(ENV_NAME, "on")
        path = ctx.syspath_prepend("/hp-control-patchset-path")
        noop = ctx.del_attr(target_module, "NOT_THERE", raising=False)

    assert target_module.FLAG is True
    assert target_module.ADDED == 1
    assert target_module.REGISTRY == {"existing": 1, "new": 2}
    assert os.environ[ENV_NAME] == "on"
    assert sys.path[0] == "/hp-control-patchset-path"
    assert [handle.status for handle in (attr, new_attr, item, env, path, noop)] == [PatchStatus.APPLIED] * 6
    assert last_outcome(attr).kind is PatchOutcomeKind.APPLIED
    assert last_outcome(noop).kind is PatchOutcomeKind.NOOP
    assert attr.owner == patch_set.id
    assert attr.target == f"{MODULE_NAME}:FLAG"
    assert get_patch_handle(attr.id, state=state) is attr
    assert patch_set.status is PatchSetStatus.OPEN

    report = patch_set.unload()

    assert report.ok
    assert report.status is PatchSetStatus.CLOSED
    assert [item["status"] for item in report.handles] == ["reverted"] * 6
    assert [item["id"] for item in report.handles] == [handle.id for handle in (attr, new_attr, item, env, path, noop)]
    assert target_module.FLAG is False
    assert not hasattr(target_module, "ADDED")
    assert target_module.REGISTRY == {"existing": 1}
    assert ENV_NAME not in os.environ
    assert sys.path == path_list_before
    assert list_patch_handles(state=state) == []
    assert patch_set.close() is report


def test_transactional_failure_reverts_partial_work(state, target_module):
    patch_set = PatchSet("tx", state=state)

    with pytest.raises(RuntimeError, match="setup exploded"):
        with patch_set as ctx:
            ctx.set_attr(target_module, "FLAG", True)
            ctx.set_item(target_module.REGISTRY, "partial", 1)
            raise RuntimeError("setup exploded")

    assert target_module.FLAG is False
    assert target_module.REGISTRY == {"existing": 1}
    assert patch_set.status is PatchSetStatus.FAILED
    assert patch_set.error is not None
    assert patch_set.error.error_type == "RuntimeError"
    assert patch_set.error.error_message == "setup exploded"
    assert all(handle.status is PatchStatus.REVERTED for handle in patch_set.handles)
    assert patch_set.close().status is PatchSetStatus.FAILED
    with pytest.raises(PatchSetClosedError):
        patch_set.context.set_attr(target_module, "FLAG", True)


def test_failed_operation_marks_handle_failed_and_run_reverts(state, target_module):
    patch_set = PatchSet("run", state=state)

    def setup(ctx, value):
        ctx.set_attr(target_module, "FLAG", value)
        ctx.set_attr(target_module, "MISSING", 1)

    with pytest.raises(AttributeError, match="MISSING"):
        patch_set.run(setup, True)

    applied, failed = patch_set.handles
    assert target_module.FLAG is False
    assert applied.status is PatchStatus.REVERTED
    assert failed.status is PatchStatus.FAILED
    failure = last_outcome(failed)
    assert failure.kind is PatchOutcomeKind.FAILED
    assert failure.error_type == "AttributeError"
    assert failure.traceback is not None
    assert "MISSING" in failure.traceback
    assert patch_set.status is PatchSetStatus.FAILED


def test_non_transactional_exit_with_exception_keeps_patches(state, target_module):
    patch_set = PatchSet("loose", transactional=False, state=state)

    with pytest.raises(ValueError):
        with patch_set as ctx:
            ctx.set_attr(target_module, "FLAG", True)
            raise ValueError("keep going")

    assert target_module.FLAG is True
    assert patch_set.status is PatchSetStatus.OPEN
    patch_set.close()
    assert target_module.FLAG is False


def test_disposers_run_lifo_with_journal_and_continue_past_failures(state, target_module):
    calls = []
    patch_set = PatchSet(state=state)
    ctx = patch_set.context

    ctx.add_disposer(lambda: calls.append("first"), "first")
    ctx.set_attr(target_module, "FLAG", True)
    failing = ctx.add_disposer(lambda: (_ for _ in ()).throw(RuntimeError("dispose failed")), "failing")
    ctx.add_disposer(lambda: calls.append(("last", target_module.FLAG)), "last")

    report = patch_set.close()

    assert calls == [("last", True), "first"]
    assert target_module.FLAG is False
    assert not report.ok
    assert report.errors == [{"handle_id": failing.id, "label": "failing", "error_type": "RuntimeError", "error_message": "dispose failed"}]
    assert failing.status is PatchStatus.FAILED
    with pytest.raises(RuntimeError, match="dispose failed"):
        report.raise_first_error()


def test_interrupted_close_can_be_resumed(state, target_module):
    calls = []
    patch_set = PatchSet(state=state)
    ctx = patch_set.context
    ctx.set_attr(target_module, "FLAG", True)

    def interrupt():
        calls.append("interrupt")
        raise KeyboardInterrupt

    ctx.add_disposer(interrupt, "interrupt")
    ctx.add_disposer(lambda: calls.append("newest"), "newest")

    with pytest.raises(KeyboardInterrupt):
        patch_set.close()

    assert calls == ["newest", "interrupt"]
    assert target_module.FLAG is True
    assert not patch_set.closed

    report = patch_set.close()

    assert target_module.FLAG is False
    assert calls == ["newest", "interrupt"]
    assert report.status is PatchSetStatus.CLOSED
    assert patch_set.close() is report


def test_disposer_added_after_close_runs_immediately(state):
    calls = []
    patch_set = PatchSet(state=state)
    patch_set.close()

    handle = patch_set.add_disposer(lambda: calls.append("late"), "late")

    assert calls == ["late"]
    assert handle.status is PatchStatus.REVERTED
    assert handle in patch_set.handles
    assert get_patch_handle(handle.id, state=state) is None


def test_disposer_added_after_close_propagates_failure(state):
    patch_set = PatchSet(state=state)
    patch_set.close()

    def boom():
        raise OSError("late failure")

    with pytest.raises(OSError, match="late failure"):
        patch_set.add_disposer(boom)

    assert patch_set.handles[-1].status is PatchStatus.FAILED


def test_disposer_added_during_close_runs_immediately(state):
    calls = []
    patch_set = PatchSet(state=state)
    patch_set.add_disposer(lambda: patch_set.add_disposer(lambda: calls.append("nested")), "outer")

    patch_set.close()

    assert calls == ["nested"]


def test_adopted_handle_reports_status_returned_by_undo(state):
    patch_set = PatchSet(state=state)
    deregistered = create_patch_handle("function", "pkg.mod.func", stage="function", state=state)
    restart = create_patch_handle("source", "pkg.mod", stage="source", state=state)
    restart.status = PatchStatus.APPLIED

    patch_set.adopt_handle(deregistered, undo=lambda: PatchStatus.DEREGISTERED)
    patch_set.adopt_handle(restart, undo=lambda: "requires_restart")

    assert deregistered.owner == patch_set.id
    report = patch_set.close()

    assert [item["status"] for item in report.handles] == ["deregistered", "requires_restart"]
    assert list_patch_handles(state=state) == []


def test_nested_sets_restore_current_patch_context(state):
    outer = PatchSet("outer", state=state)
    inner = PatchSet("inner", state=state)

    assert current_patch_context() is None
    with outer as outer_ctx:
        assert current_patch_context() is outer_ctx
        with inner as inner_ctx:
            assert current_patch_context() is inner_ctx
            with outer_ctx.activate():
                assert current_patch_context() is outer_ctx
            assert current_patch_context() is inner_ctx
        assert current_patch_context() is outer_ctx
        with pytest.raises(KeyError):
            with inner:
                raise KeyError("inner failure")
        assert current_patch_context() is outer_ctx
        assert inner.status is PatchSetStatus.FAILED
        assert outer.status is PatchSetStatus.OPEN
    assert current_patch_context() is None


def test_reentrant_activation_of_same_set(state):
    patch_set = PatchSet(state=state)

    with patch_set as first:
        with patch_set as second:
            assert first is second is current_patch_context()
        assert current_patch_context() is first
    assert current_patch_context() is None


def test_current_patch_context_is_isolated_per_thread(state):
    patch_set = PatchSet(state=state)
    seen = []

    with patch_set:
        thread = threading.Thread(target=lambda: seen.append(current_patch_context()))
        thread.start()
        thread.join()
        copied = contextvars.copy_context().run(current_patch_context)

    assert seen == [None]
    assert copied is patch_set.context


def test_state_registry_helpers(state):
    first = PatchSet("first", state=state)
    second = PatchSet(state=state)

    assert register_patch_set(first) is first
    assert register_patch_set(first) is first
    register_patch_set(second, state=state)

    assert list_patch_sets(state=state) == [first, second]
    assert get_patch_set(first.id, state=state) is first
    assert get_patch_set("first", state=state) is first
    assert get_patch_set(second.id, state=state) is second
    assert second.name == second.id
    assert get_patch_set("missing", state=state) is None

    with pytest.raises(ValueError, match="already registered"):
        register_patch_set(PatchSet("first", state=state))
    with pytest.raises(ValueError, match="different HotpatcherState"):
        register_patch_set(PatchSet("other", state=HotpatcherState()), state=state)

    assert remove_patch_set("first", state=state) is first
    assert remove_patch_set(second) is second
    assert remove_patch_set(second) is None
    assert remove_patch_set("missing", state=state) is None
    assert list_patch_sets(state=state) == []


def test_ids_are_identifiers_and_share_the_state_counter(state):
    patch_set = PatchSet(state=state)
    handle = create_patch_handle("attr", "x", state=state)

    assert patch_set.id == "set_1"
    assert handle.id == "patch_2"
    assert state.patch_id_counter == 2
    assert patch_set.id.isidentifier()
    with pytest.raises(ValueError):
        allocate_patch_id("bad-prefix", state=state)


def test_id_allocation_is_thread_safe(state):
    thread_count = 8
    per_thread = 200
    barrier = threading.Barrier(thread_count)
    results = [[] for _ in range(thread_count)]

    def worker(index):
        barrier.wait()
        for _ in range(per_thread):
            results[index].append(allocate_patch_id(state=state))

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(thread_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    ids = [patch_id for chunk in results for patch_id in chunk]
    assert len(ids) == len(set(ids)) == thread_count * per_thread
    assert state.patch_id_counter == thread_count * per_thread


def test_handle_outcomes_are_bounded_and_serializable(state):
    handle = create_patch_handle("attr", "target", state=state)
    for _ in range(50):
        handle.record_outcome(PatchOutcome.noop())
    try:
        raise ValueError("x" * 5000)
    except ValueError as exc:
        handle.record_outcome(PatchOutcome.failed(exc))

    data = handle.to_dict()

    assert len(handle.outcomes) == 20
    assert handle.outcome_counts == {"noop": 50, "failed": 1}
    assert data["status"] == "registered"
    assert data["outcomes"][-1]["kind"] == "failed"
    assert len(data["outcomes"][-1]["error_message"]) <= 1000
    assert PatchOutcome.skipped("condition_false").to_dict()["reason"] == "condition_false"


def test_patch_set_to_dict(state, target_module):
    patch_set = PatchSet("describe", state=state, config={"enabled": True})
    patch_set.context.set_attr(target_module, "FLAG", True)

    data = patch_set.to_dict()

    assert patch_set.context.config == {"enabled": True}
    assert data["name"] == "describe"
    assert data["status"] == "open"
    assert data["handles"][0]["kind"] == "attr"
    assert data["journal"][0]["label"] == f"{MODULE_NAME}.FLAG"
    patch_set.close()
    assert patch_set.to_dict()["journal"] == []
