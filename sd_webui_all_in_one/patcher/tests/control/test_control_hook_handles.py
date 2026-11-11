import ast
import importlib
import importlib.machinery
import importlib.util
import sys
import threading
from typing import Any

import pytest
from control_hook_test_helpers import clean_hook_state, forget_module, write_module

from sd_webui_all_in_one_hotpatcher import (
    HotpatcherState,
    MonkeyZoo,
    get_default_state,
    install_import_hook,
    is_strict_mode,
    monkey_zoo,
    register_customize_hook,
    register_hook,
    set_strict_mode,
    uninstall_import_hook,
)
from sd_webui_all_in_one_hotpatcher.control import PatchHandle, PatchOutcomeKind, PatchSet, PatchStatus, current_patch_context
from sd_webui_all_in_one_hotpatcher.hook import MonkeySourceFileLoader


@pytest.fixture(autouse=True)
def clean_state():
    with clean_hook_state():
        yield


@pytest.fixture
def module_dir(tmp_path):
    sys.path.insert(0, str(tmp_path))
    return tmp_path


def greet_module(module_dir, name):
    return write_module(
        module_dir,
        name,
        """
        def greet(name):
            return f"hello {name}"

        def noisy():
            print("noise")
            return "done"
        """,
    )


def upper_wrapper(func, module):
    def wrapper(name):
        return func(name).upper()

    return wrapper


def outcome_of(handle):
    outcome = handle.last_outcome
    assert outcome is not None
    return outcome


def loader_of(module):
    spec = module.__spec__
    assert spec is not None
    return spec.loader


def last_kind(handle):
    return outcome_of(handle).kind if handle.last_outcome is not None else None


# ---------------------------------------------------------------- handles and listing


def test_every_registration_returns_a_listed_handle():
    with monkey_zoo("hpc_listing") as monkey:
        handles = [
            monkey.patch_premodule(lambda module: None),
            monkey.patch_module(lambda module: None),
            monkey.patch_function("f", lambda func, module: None),
            monkey.patch_sources(lambda source, filename: source),
            monkey.patch_ast(lambda tree: tree),
            monkey.patch_bytecode(lambda code: None),
            monkey.prohibit_output("f"),
            monkey.inject_import("math", "sqrt"),
        ]

    assert all(isinstance(handle, PatchHandle) for handle in handles)
    assert [handle.stage for handle in handles] == ["premodule", "module", "function", "source", "ast", "bytecode", "output_prohibition", "import_injection"]
    assert {handle.kind for handle in handles} == {"import"}
    assert all(handle.status is PatchStatus.REGISTERED and handle.owner is None for handle in handles)
    assert monkey.handles() == handles
    assert monkey_zoo.handles() == handles
    assert [handle.id for handle in handles] == [handle_id for handle_id in get_default_state().patch_handles if handle_id in {h.id for h in handles}]
    assert handles[2].target == "hpc_listing:f"
    assert handles[7].target == "hpc_listing:sqrt"


def test_register_helpers_return_handles():
    function_handle = register_hook("hpc_helpers", "f", lambda func, module: None)
    module_handle = register_customize_hook("hpc_helpers", lambda module: None)

    monkey = monkey_zoo["hpc_helpers"]
    assert monkey is not None
    assert monkey.handles() == [module_handle, function_handle]


def test_extension_style_tuple_unpacking_still_works():
    def hooker(module):
        return None

    with monkey_zoo("hpc_tuples") as monkey:
        monkey.patch_module(hooker, priority=5)
        monkey.patch_function("f", upper_wrapper, 7, True)
        monkey.inject_import("math", "sqrt", "root", 3)
        monkey.prohibit_output(None)

    assert [(found, priority) for found, priority in monkey.module_patches] == [(hooker, 5)]
    assert [(name, found, priority, force) for name, found, priority, force in monkey.function_patches] == [("f", upper_wrapper, 7, True)]
    assert monkey.import_injections == [("math", "sqrt", "root", 3)]
    assert monkey.output_prohibition == [None]


def test_direct_appends_get_lazy_handles(module_dir):
    write_module(module_dir, "hpc_direct", "VALUE = 1\n")
    calls = []

    install_import_hook()
    with monkey_zoo("hpc_direct") as monkey:
        handle = monkey.patch_module(lambda module: calls.append("registered"))
    monkey.module_patches.append((lambda module: calls.append("direct"), 200))
    monkey.output_prohibition.append(None)

    listed = monkey.handles()
    assert len(listed) == 3
    assert listed[0] is handle
    lazy = [item for item in listed if item is not handle]
    assert {item.stage for item in lazy} == {"module", "output_prohibition"}
    assert all(item.id in get_default_state().patch_handles for item in lazy)
    assert monkey.handles() == listed

    importlib.import_module("hpc_direct")

    assert calls == ["registered", "direct"]
    assert all(last_kind(item) is PatchOutcomeKind.APPLIED for item in listed)


def test_direct_removal_from_public_list_forgets_handle():
    with monkey_zoo("hpc_direct_remove") as monkey:
        handle = monkey.patch_module(lambda module: None)
    monkey.module_patches.clear()

    assert monkey.handles() == []
    assert handle.status is PatchStatus.DEREGISTERED
    assert handle.id not in get_default_state().patch_handles


def test_identity_search_distinguishes_equal_entries():
    with monkey_zoo("hpc_identity") as monkey:
        first = monkey.prohibit_output(None)
        second = monkey.prohibit_output(None)
        third = monkey.prohibit_output("f")

    assert monkey.remove(second) is PatchStatus.DEREGISTERED
    assert monkey.output_prohibition == [None, "f"]
    assert monkey.handles() == [first, third]


def test_casefold_lookup_is_kept():
    with monkey_zoo("HPC_Case") as monkey:
        monkey.patch_module(lambda module: None)

    assert "hpc_case" in monkey_zoo
    assert monkey_zoo["Hpc_CASE"] is monkey
    assert monkey.name == "HPC_Case"


# ---------------------------------------------------------------- removal before import


def test_remove_before_import_deregisters_and_drops_empty_plan():
    with monkey_zoo("hpc_before") as monkey:
        handle = monkey.patch_function("greet", upper_wrapper)

    assert monkey.remove(handle) is PatchStatus.DEREGISTERED
    assert handle.status is PatchStatus.DEREGISTERED
    assert monkey.function_patches == []
    assert "hpc_before" not in monkey_zoo
    assert handle.id not in get_default_state().patch_handles
    assert monkey.remove(handle) is None


def test_owned_registration_before_import_deregisters_on_unload():
    patch_set = PatchSet("before-import")
    with patch_set.context.module("hpc_owned_before") as monkey:
        handles = [monkey.patch_function("greet", upper_wrapper), monkey.patch_sources(lambda source, filename: source)]

    assert all(handle.owner == patch_set.id for handle in handles)
    assert patch_set.handles == handles

    report = patch_set.close()

    assert [item["status"] for item in report.handles] == ["deregistered", "deregistered"]
    assert "hpc_owned_before" not in monkey_zoo
    assert monkey.function_patches == [] and monkey.source_patches == []


def test_plain_zoo_registration_inside_active_set_is_owned():
    patch_set = PatchSet("plain-zoo")
    with patch_set:
        handle = register_hook("hpc_plain_owned", "greet", upper_wrapper)

    assert handle.owner == patch_set.id
    patch_set.close()
    assert handle.status is PatchStatus.DEREGISTERED
    assert "hpc_plain_owned" not in monkey_zoo


def test_registration_on_closed_set_leaves_no_entry():
    from sd_webui_all_in_one_hotpatcher.control import PatchSetClosedError

    patch_set = PatchSet("closed")
    patch_set.close()
    with pytest.raises(PatchSetClosedError):
        with patch_set.context.activate(), monkey_zoo("hpc_closed") as monkey:
            monkey.patch_module(lambda module: None)

    assert "hpc_closed" not in monkey_zoo


# ---------------------------------------------------------------- removal after import


def test_owned_post_exec_writes_are_reverted_on_unload(module_dir, capsys):
    greet_module(module_dir, "hpc_owned_after")
    install_import_hook()
    patch_set = PatchSet("after-import")
    with patch_set.context.module("hpc_owned_after") as monkey:
        function_handle = monkey.patch_function("greet", upper_wrapper)
        injection_handle = monkey.inject_import("math", "sqrt")
        prohibition_handle = monkey.prohibit_output("noisy")

    module = importlib.import_module("hpc_owned_after")
    capsys.readouterr()
    assert module.greet("ada") == "HELLO ADA"
    assert module.sqrt(9) == 3
    assert module.noisy() == "done"
    assert capsys.readouterr().out == ""
    assert {function_handle.status, injection_handle.status, prohibition_handle.status} == {PatchStatus.APPLIED}

    report = patch_set.close()

    assert {item["id"]: item["status"] for item in report.handles} == {
        function_handle.id: "reverted",
        injection_handle.id: "reverted",
        prohibition_handle.id: "reverted",
    }
    assert report.ok
    assert module.greet("ada") == "hello ada"
    assert "sqrt" not in module.__dict__
    assert module.noisy() == "done"
    assert capsys.readouterr().out == "noise\n"
    assert "hpc_owned_after" not in monkey_zoo


def test_code_stages_after_import_require_restart(module_dir):
    write_module(module_dir, "hpc_code_after", 'VALUE = "old"\n')
    install_import_hook()

    class Rename(ast.NodeTransformer):
        def visit_Constant(self, node):
            if node.value == "source":
                return ast.copy_location(ast.Constant("ast"), node)
            return node

    patch_set = PatchSet("code-stages")
    with patch_set.context.module("hpc_code_after") as monkey:
        handles = [
            monkey.patch_sources(lambda source, filename: source.replace('"old"', '"source"'), priority=1),
            monkey.patch_ast(Rename()),
            monkey.patch_bytecode(lambda code: code.co_consts.replace_primitive("ast", "bytecode")),
            monkey.patch_premodule(lambda module: setattr(module, "PRE", True)),
            monkey.patch_module(lambda module: setattr(module, "POST", True)),
        ]

    module = importlib.import_module("hpc_code_after")
    assert (module.VALUE, module.PRE, module.POST) == ("bytecode", True, True)

    report = patch_set.close()

    assert [item["status"] for item in report.handles] == ["requires_restart"] * 5
    assert all(handle.status is PatchStatus.REQUIRES_RESTART for handle in handles)
    assert module.VALUE == "bytecode"


def test_revert_hook_reverts_module_and_premodule_patches(module_dir):
    write_module(module_dir, "hpc_revert", "VALUE = 1\n")
    install_import_hook()
    reverted = []

    patch_set = PatchSet("revert")
    with patch_set.context.module("hpc_revert") as monkey:
        module_handle = monkey.patch_module(lambda module: setattr(module, "EXTRA", 2), revert=lambda module: (reverted.append("module"), delattr(module, "EXTRA")))
        pre_handle = monkey.patch_premodule(lambda module: setattr(module, "PRE", 1), revert=lambda module: reverted.append("premodule"))

    module = importlib.import_module("hpc_revert")
    assert module.EXTRA == 2

    patch_set.close()

    assert module_handle.status is PatchStatus.REVERTED
    assert pre_handle.status is PatchStatus.REVERTED
    assert sorted(reverted) == ["module", "premodule"]
    assert not hasattr(module, "EXTRA")


def test_revert_hook_not_called_when_never_executed():
    reverted = []
    with monkey_zoo("hpc_revert_unused") as monkey:
        handle = monkey.patch_module(lambda module: None, revert=lambda module: reverted.append(module))

    assert monkey.remove(handle) is PatchStatus.DEREGISTERED
    assert reverted == []


def test_monkey_remove_reverts_single_owned_entry(module_dir):
    greet_module(module_dir, "hpc_single")
    install_import_hook()
    patch_set = PatchSet("single")
    with patch_set.context.module("hpc_single") as monkey:
        greet_handle = monkey.patch_function("greet", upper_wrapper)
        injection_handle = monkey.inject_import("math", "sqrt")

    module = importlib.import_module("hpc_single")

    assert monkey.remove(greet_handle) is PatchStatus.REVERTED
    assert greet_handle.status is PatchStatus.REVERTED
    assert module.greet("ada") == "hello ada"
    assert module.sqrt(4) == 2
    assert monkey.handles() == [injection_handle]

    report = patch_set.close()

    assert {item["id"]: item["status"] for item in report.handles} == {greet_handle.id: "reverted", injection_handle.id: "reverted"}
    assert "sqrt" not in module.__dict__


def test_unowned_remove_after_import_restores_module_dict(module_dir):
    greet_module(module_dir, "hpc_unowned_after")
    install_import_hook()
    with monkey_zoo("hpc_unowned_after") as monkey:
        handle = monkey.patch_function("greet", upper_wrapper)
        source_handle = monkey.patch_sources(lambda source, filename: source + "\nEXTRA = 1\n")

    module = importlib.import_module("hpc_unowned_after")
    assert module.greet("ada") == "HELLO ADA"

    assert monkey.remove(handle) is PatchStatus.REVERTED
    assert module.greet("ada") == "hello ada"
    assert monkey_zoo.remove(source_handle) is PatchStatus.REQUIRES_RESTART
    assert get_default_state().patch_handles.get(handle.id) is None


def test_restore_does_not_clobber_a_later_write(module_dir):
    greet_module(module_dir, "hpc_stacked")
    install_import_hook()
    with monkey_zoo("hpc_stacked") as monkey:
        handle = monkey.patch_function("greet", upper_wrapper)

    module = importlib.import_module("hpc_stacked")

    def replaced(name):
        return "replaced"

    setattr(module, "greet", replaced)

    assert monkey.remove(handle) is PatchStatus.REQUIRES_RESTART
    assert module.greet is replaced


def test_hooker_runs_with_owning_set_active(module_dir):
    write_module(module_dir, "hpc_activation", "VALUE = 1\n")
    install_import_hook()
    seen = []
    patch_set = PatchSet("activation")
    with patch_set.context.module("hpc_activation") as monkey:
        monkey.patch_module(lambda module: seen.append(current_patch_context()))

    assert current_patch_context() is None
    importlib.import_module("hpc_activation")

    assert seen == [patch_set.context]
    assert current_patch_context() is None


# ---------------------------------------------------------------- finder cache invalidation


def test_discard_invalidates_finder_cache(module_dir):
    greet_module(module_dir, "hpc_cache")
    finder = install_import_hook()
    with monkey_zoo("hpc_cache") as monkey:
        handle = monkey.patch_function("greet", upper_wrapper)

    assert importlib.import_module("hpc_cache").greet("ada") == "HELLO ADA"
    assert "hpc_cache" in finder.cache

    assert monkey_zoo.discard("HPC_CACHE") is monkey
    assert "hpc_cache" not in finder.cache
    assert handle.status is PatchStatus.REQUIRES_RESTART
    assert handle.id not in get_default_state().patch_handles

    forget_module("hpc_cache")
    assert importlib.import_module("hpc_cache").greet("ada") == "hello ada"
    assert monkey_zoo.discard("hpc_cache") is None


def test_plan_changes_invalidate_cached_spec(module_dir):
    greet_module(module_dir, "hpc_cache_add")
    finder = install_import_hook()
    with monkey_zoo("hpc_cache_add") as monkey:
        handle = monkey.patch_function("greet", upper_wrapper)
    importlib.import_module("hpc_cache_add")
    assert "hpc_cache_add" in finder.cache

    with monkey_zoo("hpc_cache_add") as monkey:
        monkey.inject_import("math", "sqrt")
    assert "hpc_cache_add" not in finder.cache

    forget_module("hpc_cache_add")
    module = importlib.import_module("hpc_cache_add")
    assert module.sqrt(9) == 3
    assert "hpc_cache_add" in finder.cache

    monkey.remove(handle)
    assert "hpc_cache_add" not in finder.cache

    importlib.import_module("hpc_cache_add")
    monkey_zoo.clear()
    assert finder.cache == {}
    forget_module("hpc_cache_add")
    module = importlib.import_module("hpc_cache_add")
    assert module.greet("ada") == "hello ada"
    assert "sqrt" not in module.__dict__


def test_alias_registration_returns_handle_and_invalidates(module_dir):
    write_module(module_dir, "hpc_alias_real", "VALUE = 42\n")
    finder = install_import_hook()
    finder.cache["hpc_alias_missing"] = importlib.machinery.ModuleSpec("hpc_alias_missing", None)

    patch_set = PatchSet("alias")
    with patch_set:
        handle = monkey_zoo.alias_if_not_exists("hpc_alias_missing", "hpc_alias_real")

    assert "hpc_alias_missing" not in finder.cache
    assert handle.kind == "alias" and handle.owner == patch_set.id
    assert handle in monkey_zoo.handles()
    assert importlib.import_module("hpc_alias_missing").VALUE == 42

    patch_set.close()

    assert handle.status is PatchStatus.REQUIRES_RESTART
    assert "hpc_alias_missing" not in monkey_zoo.aliases_fallback


def test_unowned_alias_removed_through_zoo():
    handle = monkey_zoo.alias_if_not_exists("hpc_alias_unused", "hpc_alias_target")

    assert monkey_zoo.remove(handle) is PatchStatus.DEREGISTERED
    assert monkey_zoo.aliases_fallback == {}
    assert handle.id not in get_default_state().patch_handles


# ---------------------------------------------------------------- outcomes, strict mode, conditions


def test_noop_source_patch_is_recorded(module_dir):
    write_module(module_dir, "hpc_noop", "VALUE = 1\n")
    install_import_hook()
    with monkey_zoo("hpc_noop") as monkey:
        noop = monkey.patch_sources(lambda source, filename: source.replace("MISSING", "OTHER"))
        applied = monkey.patch_sources(lambda source, filename: source + "EXTRA = 2\n")
        function_noop = monkey.patch_function("VALUE", lambda value, module: None)

    module = importlib.import_module("hpc_noop")

    assert module.EXTRA == 2
    assert last_kind(noop) is PatchOutcomeKind.NOOP
    assert last_kind(applied) is PatchOutcomeKind.APPLIED
    assert last_kind(function_noop) is PatchOutcomeKind.NOOP


def test_ast_noop_detected_only_in_strict_or_debug(module_dir, monkeypatch):
    write_module(module_dir, "hpc_ast_noop", "VALUE = 1\n")
    install_import_hook()
    with monkey_zoo("hpc_ast_noop") as monkey:
        handle = monkey.patch_ast(ast.NodeTransformer())

    importlib.import_module("hpc_ast_noop")
    assert last_kind(handle) is PatchOutcomeKind.APPLIED

    forget_module("hpc_ast_noop")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_DEBUG", "1")
    importlib.import_module("hpc_ast_noop")
    assert last_kind(handle) is PatchOutcomeKind.NOOP


def test_strict_mode_propagates_hooker_errors(module_dir):
    greet_module(module_dir, "hpc_strict")
    install_import_hook()

    def broken(func, module):
        raise RuntimeError("broken patch")

    with monkey_zoo("hpc_strict") as monkey:
        handle = monkey.patch_function("greet", broken)

    assert not is_strict_mode()
    set_strict_mode(True)
    assert is_strict_mode()

    with pytest.raises(RuntimeError, match="broken patch"):
        importlib.import_module("hpc_strict")

    assert last_kind(handle) is PatchOutcomeKind.FAILED
    assert outcome_of(handle).error_type == "RuntimeError"
    assert handle.status is PatchStatus.FAILED
    assert "hpc_strict" not in sys.modules


def bad_source(source: str, filename: str) -> Any:
    return 42


def test_non_strict_mode_records_failure_and_continues(module_dir, capsys):
    greet_module(module_dir, "hpc_tolerant")
    install_import_hook()
    reported = []
    state = get_default_state()
    previous_reporter = state.exception_reporter
    state.exception_reporter = lambda exc_type, exc, tb: reported.append(exc)

    def broken(func, module):
        raise RuntimeError("tolerated")

    try:
        with monkey_zoo("hpc_tolerant") as monkey:
            failed = monkey.patch_function("greet", broken, priority=1)
            applied = monkey.patch_function("greet", upper_wrapper, priority=2)
            source_failed = monkey.patch_sources(bad_source)

        module = importlib.import_module("hpc_tolerant")
    finally:
        state.exception_reporter = previous_reporter

    assert module.greet("ada") == "HELLO ADA"
    assert last_kind(failed) is PatchOutcomeKind.FAILED
    assert last_kind(applied) is PatchOutcomeKind.APPLIED
    assert last_kind(source_failed) is PatchOutcomeKind.FAILED
    assert outcome_of(source_failed).error_type == "TypeError"
    assert [type(exc) for exc in reported] == [TypeError, RuntimeError]
    assert "tolerated" in capsys.readouterr().err


def test_failed_hooker_unload_status_agrees_between_close_and_remove(module_dir):
    greet_module(module_dir, "hpc_failed_unload")
    install_import_hook()

    def broken(func, module):
        raise RuntimeError("broken")

    closing = PatchSet("failed-close")
    removing = PatchSet("failed-remove")
    with closing.context.module("hpc_failed_unload") as monkey:
        closed_handle = monkey.patch_function("greet", broken)
    with removing.context.module("hpc_failed_unload") as monkey:
        removed_handle = monkey.patch_function("noisy", broken)

    importlib.import_module("hpc_failed_unload")
    assert closed_handle.status is PatchStatus.FAILED
    assert removed_handle.status is PatchStatus.FAILED

    report = closing.close()
    removed_status = monkey.remove(removed_handle)

    assert report.handles[0]["status"] == "reverted"
    assert closed_handle.status is PatchStatus.REVERTED
    assert removed_status is PatchStatus.REVERTED
    assert removed_handle.status is PatchStatus.REVERTED


def test_strict_mode_is_per_state():
    other = HotpatcherState()
    set_strict_mode(True, state=other)

    assert is_strict_mode(state=other)
    assert not is_strict_mode()


def test_strict_mode_reads_environment(monkeypatch):
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_STRICT", "1")
    assert HotpatcherState().strict_mode is True
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_STRICT", "0")
    assert HotpatcherState().strict_mode is False


def test_condition_false_skips_patch(module_dir):
    greet_module(module_dir, "hpc_condition")
    install_import_hook()
    with monkey_zoo("hpc_condition") as monkey:
        skipped = monkey.patch_function("greet", upper_wrapper, condition=lambda: False)
        applied = monkey.inject_import("math", "sqrt", condition=lambda: True)
        source_skipped = monkey.patch_sources(lambda source, filename: "raise SystemExit\n", condition=lambda: 0)
        missing = monkey.patch_function("absent", upper_wrapper)

    module = importlib.import_module("hpc_condition")

    assert module.greet("ada") == "hello ada"
    assert module.sqrt(9) == 3
    assert outcome_of(skipped).kind is PatchOutcomeKind.SKIPPED and outcome_of(skipped).reason == "condition_false"
    assert outcome_of(source_skipped).reason == "condition_false"
    assert last_kind(applied) is PatchOutcomeKind.APPLIED
    assert outcome_of(missing).reason == "function_missing"
    assert skipped.status is PatchStatus.REGISTERED
    assert monkey.remove(skipped) is PatchStatus.DEREGISTERED


# ---------------------------------------------------------------- retroactive apply


def test_apply_if_loaded_patches_live_module_once(module_dir):
    greet_module(module_dir, "hpc_retro")
    module = importlib.import_module("hpc_retro")
    install_import_hook()
    calls = []

    def counting(func, module):
        calls.append(module)
        return upper_wrapper(func, module)

    with monkey_zoo("hpc_retro") as monkey:
        old_handle = monkey.patch_module(lambda module: calls.append("old"))

    with monkey_zoo("hpc_retro", apply_if_loaded=True) as monkey:
        function_handle = monkey.patch_function("greet", counting)
        injection_handle = monkey.inject_import("math", "sqrt")
        source_handle = monkey.patch_sources(lambda source, filename: source)
        premodule_handle = monkey.patch_premodule(lambda module: None)
        whole_module_handle = monkey.prohibit_output(None)

    assert module.greet("ada") == "HELLO ADA"
    assert module.sqrt(16) == 4
    assert calls == [module]
    assert old_handle.last_outcome is None
    for handle in (source_handle, premodule_handle, whole_module_handle):
        assert outcome_of(handle).kind is PatchOutcomeKind.SKIPPED
        assert outcome_of(handle).reason == "already_imported"
    assert injection_handle.status is PatchStatus.APPLIED

    monkey.apply_to_loaded(module, handle_ids={function_handle.id})
    with monkey_zoo("hpc_retro", apply_if_loaded=True):
        pass
    assert calls == [module]

    importlib.reload(module)
    assert calls == [module, module, "old"]
    assert module.greet("ada") == "HELLO ADA"
    assert isinstance(loader_of(module), MonkeySourceFileLoader)
    assert not isinstance(loader_of(module).loader, MonkeySourceFileLoader)


def test_apply_if_loaded_without_loaded_module_only_registers(module_dir):
    greet_module(module_dir, "hpc_retro_later")
    install_import_hook()

    with monkey_zoo("hpc_retro_later", apply_if_loaded=True) as monkey:
        handle = monkey.patch_function("greet", upper_wrapper)

    assert handle.last_outcome is None
    assert importlib.import_module("hpc_retro_later").greet("ada") == "HELLO ADA"


def test_context_module_apply_if_loaded_is_owned_and_revertible(module_dir):
    greet_module(module_dir, "hpc_retro_owned")
    module = importlib.import_module("hpc_retro_owned")
    patch_set = PatchSet("retro")

    with patch_set.context.module("hpc_retro_owned", apply_if_loaded=True) as monkey:
        handle = monkey.patch_function("greet", upper_wrapper)

    assert handle.owner == patch_set.id
    assert module.greet("ada") == "HELLO ADA"

    report = patch_set.close()

    assert report.handles[0]["status"] == "reverted"
    assert module.greet("ada") == "hello ada"


# ---------------------------------------------------------------- thread-local skipper


def test_loading_skipper_is_thread_local():
    finder = install_import_hook()
    inside = threading.Event()
    release = threading.Event()
    seen_from_other_thread = []

    def hold():
        with finder.currently_loading("hpc_thread_name"):
            inside.set()
            release.wait(5)

    holder = threading.Thread(target=hold)
    holder.start()
    assert inside.wait(5)
    try:
        checker = threading.Thread(target=lambda: seen_from_other_thread.append("hpc_thread_name" in finder.currently_loading))
        checker.start()
        checker.join(5)
    finally:
        release.set()
        holder.join(5)

    assert seen_from_other_thread == [False]
    assert "hpc_thread_name" not in finder.currently_loading


def test_find_spec_from_other_thread_during_import_returns_wrapped_spec(module_dir):
    write_module(module_dir, "hpc_parked", "VALUE = 1\n")
    finder = install_import_hook()
    parked = threading.Event()
    release = threading.Event()
    errors = []

    def park(module):
        parked.set()
        release.wait(5)

    with monkey_zoo("hpc_parked") as monkey:
        monkey.patch_premodule(park)

    def do_import():
        try:
            importlib.import_module("hpc_parked")
        except BaseException as exc:  # pragma: no cover - reported below
            errors.append(exc)

    importer = threading.Thread(target=do_import)
    importer.start()
    assert parked.wait(5)
    try:
        spec = finder.find_spec("hpc_parked", None)
    finally:
        release.set()
        importer.join(5)

    assert errors == []
    assert spec is not None
    assert isinstance(spec.loader, MonkeySourceFileLoader)


def test_concurrent_imports_of_patched_module_are_patched(module_dir):
    greet_module(module_dir, "hpc_concurrent")
    install_import_hook()
    with monkey_zoo("hpc_concurrent") as monkey:
        monkey.patch_function("greet", upper_wrapper)

    barrier = threading.Barrier(2)
    results = []

    def do_import():
        barrier.wait(5)
        module = importlib.import_module("hpc_concurrent")
        results.append((module.greet("ada"), type(loader_of(module))))

    threads = [threading.Thread(target=do_import) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)

    assert results == [("HELLO ADA", MonkeySourceFileLoader)] * 2


# ---------------------------------------------------------------- state-aware file location wrapper


def test_spec_from_file_location_uses_non_default_state(tmp_path):
    other = HotpatcherState()
    other_zoo = MonkeyZoo(state=other)
    other.monkey_zoo = other_zoo
    module_path = tmp_path / "dynamic_target.py"
    module_path.write_text('VALUE = "before"\n', encoding="utf-8")

    install_import_hook(state=other)
    try:
        assert get_default_state().import_hook_wrapped_spec_from_file_location is None
        with other_zoo("hpc_dynamic_other") as monkey:
            handle = monkey.patch_sources(lambda source, filename: source.replace('"before"', '"after"'))

        spec = importlib.util.spec_from_file_location("hpc_dynamic_other", module_path)
        assert spec is not None and isinstance(spec.loader, MonkeySourceFileLoader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert module.VALUE == "after"
        assert handle.id in other.patch_handles
        assert handle.id not in get_default_state().patch_handles
        unpatched = importlib.util.spec_from_file_location("hpc_dynamic_plain", module_path)
        assert unpatched is not None and not isinstance(unpatched.loader, MonkeySourceFileLoader)
    finally:
        uninstall_import_hook(state=other)
        other_zoo.clear()
