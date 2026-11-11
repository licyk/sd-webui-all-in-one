import asyncio
import functools
import importlib
import inspect
import sys
import types

import pytest
from control_hook_test_helpers import clean_hook_state, write_module

from sd_webui_all_in_one_hotpatcher import install_import_hook, set_strict_mode
from sd_webui_all_in_one_hotpatcher.control import (
    TRAMPOLINE_ATTRIBUTE,
    PatchOutcomeKind,
    PatchSet,
    PatchStatus,
    TargetAttributeError,
    TargetImportError,
    Trampoline,
    current_patch_context,
    get_trampoline,
)

MODULE = "hpc_ops_target"
COPY_MODULES = ("hpc_ops_copy_a", "hpc_ops_copy_b", "hpc_ops_copy_c")
HOTPATCHER_LOOKALIKE = "sd_webui_all_in_one_hotpatcher_ext_hpc_ops_lookalike"


@pytest.fixture(autouse=True)
def clean_state():
    with clean_hook_state():
        yield
    sys.modules.pop(HOTPATCHER_LOOKALIKE, None)


def make_module(name, **attrs):
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    sys.modules[name] = module
    return module


def build_target_functions():
    # 在函数内创建目标函数: rebind_references 会扫描所有模块命名空间, 测试模块全局变量不能持有它们。
    def greet(name):
        return f"hello {name}"

    async def fetch(value):
        await asyncio.sleep(0)
        return value * 2

    def numbers(limit):
        yield from range(limit)

    return {"greet": greet, "fetch": fetch, "numbers": numbers}


@pytest.fixture
def target():
    return make_module(MODULE, VALUE=1, **build_target_functions())


def upper(func):
    @functools.wraps(func)
    def wrapper(name):
        return func(name).upper()

    return wrapper


def exclaim(func):
    def wrapper(name):
        return func(name) + "!"

    return wrapper


def require_context():
    ctx = current_patch_context()
    assert ctx is not None
    return ctx


def last_outcome(handle):
    outcome = handle.last_outcome
    assert outcome is not None
    return outcome


class Widget:
    label = "plain"

    def method(self, value):
        return f"method {value}"

    @staticmethod
    def static(value):
        return f"static {value}"

    @classmethod
    def build(cls, value):
        return f"{cls.__name__} {value}"

    @property
    def size(self):
        return 3

    @size.setter
    def size(self, value):
        self._size = value


class SubWidget(Widget):
    pass


# ---------------------------------------------------------------- wrap


def test_wrap_applies_and_reverts(target):
    greet = target.greet
    patch_set = PatchSet("wrap")

    handle = patch_set.context.wrap(f"{MODULE}:greet", upper)

    assert target.greet("ada") == "HELLO ADA"
    assert target.greet.__wrapped__ is greet
    assert handle.kind == "wrap"
    assert handle.target == f"{MODULE}:greet"
    assert handle.status is PatchStatus.APPLIED
    assert last_outcome(handle).kind is PatchOutcomeKind.APPLIED

    report = patch_set.close()

    assert report.handles[0]["status"] == "reverted"
    assert target.greet is greet


def test_wrap_accepts_owner_pair_and_noop_factory(target):
    greet = target.greet
    patch_set = PatchSet("pair")

    handle = patch_set.context.wrap((target, "greet"), exclaim)
    noop = patch_set.context.wrap((target, "VALUE"), lambda original: None)

    assert target.greet("ada") == "hello ada!"
    assert handle.target == f"{MODULE}.greet"
    assert last_outcome(noop).kind is PatchOutcomeKind.NOOP
    patch_set.close()
    assert target.greet is greet
    assert target.VALUE == 1


def test_wrap_factory_error_propagates_and_leaves_no_partial_state(target):
    greet = target.greet
    patch_set = PatchSet("factory-error", transactional=False)

    def broken(original):
        raise RuntimeError("factory exploded")

    with pytest.raises(RuntimeError, match="factory exploded"):
        patch_set.context.wrap(f"{MODULE}:greet", broken, trampoline=True)

    failed = patch_set.handles[-1]
    assert failed.status is PatchStatus.FAILED
    assert last_outcome(failed).reason is None
    assert patch_set.journal.entries(handle_id=failed.id) == []
    assert target.greet is greet


# ---------------------------------------------------------------- trampoline


def test_trampoline_is_stable_and_swaps_back_on_unload(target):
    greet = target.greet
    patch_set = PatchSet("trampoline")

    handle = patch_set.context.wrap(f"{MODULE}:greet", upper, trampoline=True)
    installed = target.greet
    copied = installed  # 等价于此时执行 from hpc_ops_target import greet

    state = get_trampoline(installed)
    assert isinstance(state, Trampoline)
    assert getattr(installed, TRAMPOLINE_ATTRIBUTE) is state
    assert installed.__wrapped__ is greet
    assert installed.__name__ == "greet"
    assert state.original is greet
    assert state.layer_ids == [handle.id]
    assert state.describe()["layers"] == [handle.id]
    assert copied("ada") == "HELLO ADA"
    assert last_outcome(handle).detail == {"trampoline": True, "layers": [handle.id]}

    report = patch_set.close()

    assert report.handles[0]["status"] == "reverted"
    assert target.greet is installed
    assert copied("ada") == "hello ada"
    assert state.layer_ids == []
    assert not state.active


def test_trampoline_copy_taken_between_wraps_follows_later_wraps(target):
    first = PatchSet("first")
    first.context.wrap(f"{MODULE}:greet", upper, trampoline=True)
    first.close()
    copied = target.greet  # 蹦床已安装, 没有包装层

    second = PatchSet("second")
    second.context.wrap(f"{MODULE}:greet", exclaim, trampoline=True)

    assert target.greet is copied
    assert copied("ada") == "hello ada!"
    second.close()
    assert copied("ada") == "hello ada"


def test_pre_wrap_copies_follow_trampoline_with_rebind_references(target):
    greet = target.greet
    copy_module = make_module(COPY_MODULES[0], greet=greet, alias=greet)
    patch_set = PatchSet("rebind-trampoline")

    handle = patch_set.context.wrap(f"{MODULE}:greet", upper, trampoline=True, rebind_references=True)

    installed = target.greet
    assert copy_module.greet is installed
    assert copy_module.alias is installed
    assert copy_module.greet("ada") == "HELLO ADA"
    detail = last_outcome(handle).detail
    assert detail is not None
    assert sorted(detail["rebound"]) == [f"{COPY_MODULES[0]}.alias", f"{COPY_MODULES[0]}.greet"]
    assert detail["truncated"] is False

    patch_set.close()

    assert copy_module.greet("ada") == "hello ada"
    assert copy_module.greet is greet
    assert copy_module.alias is greet
    assert target.greet is installed


@pytest.mark.parametrize("unload_order", ["first-then-second", "second-then-first"])
def test_trampoline_composition_unloads_in_either_order(target, unload_order):
    greet = target.greet
    received = []

    def recording(factory):
        def build(original):
            received.append(original)
            return factory(original)

        return build

    first = PatchSet("first")
    second = PatchSet("second")
    first_handle = first.context.wrap(f"{MODULE}:greet", recording(upper), trampoline=True)
    second_handle = second.context.wrap(f"{MODULE}:greet", recording(exclaim), trampoline=True)
    copied = target.greet
    state = get_trampoline(copied)
    assert state is not None

    assert received[0] is greet
    assert received[1]("ada") == "HELLO ADA"
    assert received[1] is not state.target
    assert received[1].__name__ == "greet"
    assert copied("ada") == "HELLO ADA!"
    assert state.layer_ids == [first_handle.id, second_handle.id]

    if unload_order == "first-then-second":
        first.close()
        assert copied("ada") == "hello ada!"
        assert state.layer_ids == [second_handle.id]
        second.close()
    else:
        second.close()
        assert copied("ada") == "HELLO ADA"
        assert state.layer_ids == [first_handle.id]
        first.close()

    assert copied("ada") == "hello ada"
    assert target.greet is copied
    assert not state.active


def test_trampoline_rewrap_after_out_of_order_unload_composes_on_remaining_layer(target):
    first = PatchSet("first")
    second = PatchSet("second")
    first.context.wrap(f"{MODULE}:greet", upper, trampoline=True)
    second.context.wrap(f"{MODULE}:greet", exclaim, trampoline=True)
    first.close()

    third = PatchSet("third")
    third.context.wrap(f"{MODULE}:greet", lambda original: lambda name: f"<{original(name)}>", trampoline=True)

    assert target.greet("ada") == "<hello ada!>"
    second.close()
    assert target.greet("ada") == "<hello ada>"
    third.close()
    assert target.greet("ada") == "hello ada"


def test_async_trampoline_stays_a_coroutine_function(target):
    def doubled(original):
        async def wrapper(value):
            return await original(value) + 1

        return wrapper

    patch_set = PatchSet("async")
    patch_set.context.wrap(f"{MODULE}:fetch", doubled, trampoline=True)
    installed = target.fetch

    assert inspect.iscoroutinefunction(installed)
    assert asyncio.run(installed(2)) == 5
    patch_set.close()
    assert inspect.iscoroutinefunction(installed)
    assert asyncio.run(installed(2)) == 4


def test_generator_function_passes_through_trampoline(target):
    patch_set = PatchSet("generator")
    patch_set.context.wrap(f"{MODULE}:numbers", lambda original: lambda limit: (value * 10 for value in original(limit)), trampoline=True)

    assert list(target.numbers(3)) == [0, 10, 20]
    patch_set.close()
    assert list(target.numbers(3)) == [0, 1, 2]


def test_trampoline_from_other_module_is_not_reused(target):
    first = PatchSet("source-module")
    first.context.wrap(f"{MODULE}:greet", upper, trampoline=True)
    copy_module = make_module(COPY_MODULES[0], greet=target.greet)

    second = PatchSet("copy-module")
    second.context.wrap((copy_module, "greet"), exclaim, trampoline=True)

    assert copy_module.greet("ada") == "HELLO ADA!"
    assert target.greet("ada") == "HELLO ADA"
    assert get_trampoline(copy_module.greet) is not get_trampoline(target.greet)
    second.close()
    first.close()
    assert copy_module.greet("ada") == "hello ada"


# ---------------------------------------------------------------- class members


@pytest.fixture
def widget_module():
    module = make_module(MODULE, Widget=Widget, SubWidget=SubWidget)
    originals = dict(Widget.__dict__)
    yield module
    for name in ("method", "static", "build", "size", "label"):
        if Widget.__dict__.get(name) is not originals[name]:
            setattr(Widget, name, originals[name])
    for name in ("method", "label"):
        if name in SubWidget.__dict__:
            delattr(SubWidget, name)


def test_patch_method_preserves_descriptor_kinds_and_restores_identity(widget_module):
    originals = {name: Widget.__dict__[name] for name in ("method", "static", "build", "size")}
    patch_set = PatchSet("methods")

    def suffix(original):
        def wrapper(*args):
            return f"{original(*args)} patched"

        return wrapper

    handles = [
        patch_set.context.patch_method(f"{MODULE}:Widget.method", suffix),
        patch_set.context.patch_method(f"{MODULE}:Widget.static", suffix),
        patch_set.context.patch_method((Widget, "build"), suffix),
        patch_set.context.patch_method(f"{MODULE}:Widget.size", lambda fget: lambda self: fget(self) * 10),
    ]

    assert isinstance(Widget.__dict__["static"], staticmethod)
    assert isinstance(Widget.__dict__["build"], classmethod)
    assert isinstance(Widget.__dict__["size"], property)
    assert Widget.__dict__["size"].fset is originals["size"].fset
    widget = Widget()
    assert widget.method(1) == "method 1 patched"
    assert Widget.static(2) == "static 2 patched"
    assert widget.static(2) == "static 2 patched"
    assert SubWidget.build(3) == "SubWidget 3 patched"
    assert widget.size == 30
    assert [handle.kind for handle in handles] == ["method"] * 4

    patch_set.close()

    for name, original in originals.items():
        assert Widget.__dict__[name] is original
    assert widget.size == 3


def test_patch_method_on_inherited_member_shadows_and_unshadows(widget_module):
    patch_set = PatchSet("inherited")

    patch_set.context.patch_method(f"{MODULE}:SubWidget.method", lambda original: lambda self, value: "sub " + original(self, value))

    assert SubWidget().method(1) == "sub method 1"
    assert Widget().method(1) == "method 1"
    patch_set.close()
    assert "method" not in SubWidget.__dict__


def test_patch_method_trampoline_keeps_classmethod_binding(widget_module):
    original = Widget.__dict__["build"]
    patch_set = PatchSet("class-trampoline")

    patch_set.context.patch_method(f"{MODULE}:Widget.build", lambda func: lambda cls, value: func(cls, value).upper(), trampoline=True)

    installed = Widget.__dict__["build"]
    assert isinstance(installed, classmethod)
    assert get_trampoline(installed) is not None
    assert SubWidget.build(1) == "SUBWIDGET 1"
    patch_set.close()
    assert Widget.__dict__["build"] is installed
    assert SubWidget.build(1) == "SubWidget 1"
    state = get_trampoline(installed)
    assert state is not None
    assert state.original is original.__func__


def test_patch_method_requires_a_class(target):
    greet = target.greet
    patch_set = PatchSet("not-class")

    with pytest.raises(TypeError, match="not a class member"):
        patch_set.context.patch_method(f"{MODULE}:greet", upper)

    assert patch_set.handles[-1].status is PatchStatus.FAILED
    assert target.greet is greet


def test_set_class_attr_uses_raw_dict(widget_module):
    original_static = Widget.__dict__["static"]
    patch_set = PatchSet("class-attr")

    replaced = patch_set.context.set_class_attr(f"{MODULE}:Widget.static", staticmethod(lambda value: "replaced"))
    shadow = patch_set.context.set_class_attr(SubWidget, "label", "sub")

    assert Widget.static(1) == "replaced"
    assert SubWidget.label == "sub"
    assert Widget.label == "plain"
    assert (replaced.kind, shadow.kind) == ("class_attr", "class_attr")

    patch_set.close()

    assert Widget.__dict__["static"] is original_static
    assert "label" not in SubWidget.__dict__

    with pytest.raises(TypeError, match="must be a class"):
        PatchSet("instance").context.set_class_attr(Widget(), "label", "x")


# ---------------------------------------------------------------- rebind_references


def test_set_attr_rebind_references_is_journaled(target):
    greet = target.greet
    copy_module = make_module(COPY_MODULES[0], greet=greet)
    lookalike = make_module(HOTPATCHER_LOOKALIKE, greet=greet)
    patch_set = PatchSet("rebind-set")

    def replacement(name):
        return f"hi {name}"

    handle = patch_set.context.set_attr(f"{MODULE}:greet", replacement, rebind_references=True)

    assert target.greet is replacement
    assert copy_module.greet is replacement
    assert lookalike.greet is greet
    outcome = last_outcome(handle)
    assert outcome.reason == "rebound 1 reference(s)"
    assert outcome.detail == {"rebound": [f"{COPY_MODULES[0]}.greet"], "truncated": False, "limit": 1000}
    assert [entry["kind"] for entry in patch_set.journal.entries(handle_id=handle.id)] == ["attr", "rebind"]

    patch_set.close()

    assert target.greet is greet
    assert copy_module.greet is greet


def test_set_attr_without_rebind_does_not_read_through_module_getattr():
    def exploding_getattr(name):
        raise RuntimeError(f"lazy attribute {name} exploded")

    module = make_module("hpc_ops_lazy", __getattr__=exploding_getattr)
    patch_set = PatchSet("lazy")

    handle = patch_set.context.set_attr(module, "NEW", 1, raising=False)

    assert handle.status is PatchStatus.APPLIED
    assert module.NEW == 1
    patch_set.close()
    assert "NEW" not in module.__dict__


def test_rebind_references_is_bounded(target):
    greet = target.greet
    copies = [make_module(name, greet=greet) for name in COPY_MODULES]
    patch_set = PatchSet("rebind-cap")

    handle = patch_set.context.wrap(f"{MODULE}:greet", upper, rebind_references=True, rebind_limit=2)

    outcome = last_outcome(handle)
    assert outcome.detail is not None
    assert len(outcome.detail["rebound"]) == 2
    assert outcome.detail["truncated"] is True
    assert outcome.reason == "rebound 2 reference(s) (truncated at 2)"
    rebound = [module for module in copies if module.greet is not greet]
    assert len(rebound) == 2
    assert all(module.greet("ada") == "HELLO ADA" for module in rebound)

    patch_set.close()

    assert all(module.greet is greet for module in copies)
    with pytest.raises(ValueError, match="rebind_limit"):
        PatchSet("bad-limit").context.wrap(f"{MODULE}:greet", upper, rebind_limit=-1)


def test_rebind_restore_does_not_clobber_later_writes(target):
    greet = target.greet
    copy_module = make_module(COPY_MODULES[0], greet=greet)
    patch_set = PatchSet("rebind-overwritten")
    handle = patch_set.context.wrap(f"{MODULE}:greet", upper, rebind_references=True)

    def later(name):
        return name

    copy_module.greet = later
    report = patch_set.close()

    assert copy_module.greet is later
    assert target.greet is greet
    assert report.handles[0]["status"] == "requires_restart"
    assert handle.status is PatchStatus.REQUIRES_RESTART


# ---------------------------------------------------------------- reload_module


def test_reload_module_requires_restart(tmp_path):
    sys.path.insert(0, str(tmp_path))
    write_module(tmp_path, "hpc_ops_reload", "COUNTER = []\nCOUNTER.append(1)\n")
    module = importlib.import_module("hpc_ops_reload")
    old_counter = module.COUNTER
    patch_set = PatchSet("reload")

    handle = patch_set.context.reload_module("hpc_ops_reload")

    assert module.COUNTER is not old_counter
    assert handle.kind == "reload"
    assert handle.status is PatchStatus.REQUIRES_RESTART
    outcome = last_outcome(handle)
    assert outcome.kind is PatchOutcomeKind.APPLIED
    assert outcome.reason == "stale_references_may_remain"
    assert outcome.detail is not None
    assert outcome.detail["module"] == "hpc_ops_reload"

    report = patch_set.close()

    assert report.handles[0]["status"] == "requires_restart"
    assert handle.status is PatchStatus.REQUIRES_RESTART


def test_reload_module_runs_under_current_plan(tmp_path):
    sys.path.insert(0, str(tmp_path))
    write_module(tmp_path, "hpc_ops_reload_plan", 'VALUE = "old"\n')
    install_import_hook()
    module = importlib.import_module("hpc_ops_reload_plan")
    patch_set = PatchSet("reload-plan")
    with patch_set.context.module("hpc_ops_reload_plan") as monkey:
        monkey.patch_sources(lambda source, filename: source.replace('"old"', '"new"'))

    patch_set.context.reload_module(module)

    assert module.VALUE == "new"
    patch_set.close()


def test_reload_module_not_imported_fails_without_raising():
    patch_set = PatchSet("reload-missing")

    handle = patch_set.context.reload_module("hpc_ops_never_imported")

    assert handle.status is PatchStatus.FAILED
    assert last_outcome(handle).reason == "target_unresolved"
    assert last_outcome(handle).error_type == "TargetImportError"


# ---------------------------------------------------------------- failure semantics


def test_resolution_failure_marks_handle_failed_without_raising(target):
    patch_set = PatchSet("tolerant")

    missing_attr = patch_set.context.wrap(f"{MODULE}:missing", upper)
    missing_module = patch_set.context.patch_method("hpc_ops_no_such_module:Cls.meth", upper)
    missing_class_attr = patch_set.context.set_class_attr(Widget, "nope", 1)

    for handle in (missing_attr, missing_module, missing_class_attr):
        assert handle.status is PatchStatus.FAILED
        assert last_outcome(handle).reason == "target_unresolved"
    assert last_outcome(missing_module).error_type == "TargetImportError"
    assert patch_set.status.value == "open"
    report = patch_set.close()
    assert [item["status"] for item in report.handles] == ["failed"] * 3
    assert "nope" not in Widget.__dict__


def test_strict_mode_raises_on_resolution_failure(target):
    set_strict_mode(True)
    patch_set = PatchSet("strict", transactional=False)

    with pytest.raises(TargetAttributeError, match="missing"):
        patch_set.context.wrap(f"{MODULE}:missing", upper)
    with pytest.raises(TargetImportError):
        patch_set.context.reload_module("hpc_ops_never_imported")

    assert [handle.status for handle in patch_set.handles] == [PatchStatus.FAILED, PatchStatus.FAILED]


def test_p1_set_attr_still_raises_on_unresolved_path(target):
    patch_set = PatchSet("p1", transactional=False)

    with pytest.raises(TargetImportError):
        patch_set.context.set_attr("hpc_ops_no_such_module:VALUE", 2)

    assert patch_set.handles[-1].status is PatchStatus.FAILED
    assert last_outcome(patch_set.handles[-1]).reason is None


# ---------------------------------------------------------------- module hooker heuristic


def test_module_hooker_using_context_operations_reports_reverted(tmp_path):
    sys.path.insert(0, str(tmp_path))
    write_module(tmp_path, "hpc_ops_hooker", "def greet(name):\n    return f'hello {name}'\n")
    install_import_hook()

    def hooker(module):
        ctx = require_context()
        ctx.set_attr(module, "EXTRA", 1, raising=False)
        ctx.wrap((module, "greet"), upper)

    patch_set = PatchSet("hooker")
    with patch_set.context.module("hpc_ops_hooker") as monkey:
        handle = monkey.patch_module(hooker)

    module = importlib.import_module("hpc_ops_hooker")
    assert module.EXTRA == 1
    assert module.greet("ada") == "HELLO ADA"

    report = patch_set.close()

    statuses = {item["id"]: item["status"] for item in report.handles}
    assert statuses[handle.id] == "reverted"
    assert set(statuses.values()) == {"reverted"}
    assert not hasattr(module, "EXTRA")
    assert module.greet("ada") == "hello ada"


def test_monkey_remove_undoes_hooker_operations(tmp_path):
    sys.path.insert(0, str(tmp_path))
    write_module(tmp_path, "hpc_ops_hooker_remove", "VALUE = 1\n")
    install_import_hook()

    def hooker(module):
        require_context().set_attr(module, "VALUE", 2)

    patch_set = PatchSet("hooker-remove")
    with patch_set.context.module("hpc_ops_hooker_remove") as monkey:
        handle = monkey.patch_module(hooker)

    module = importlib.import_module("hpc_ops_hooker_remove")
    assert module.VALUE == 2
    live = [item for item in patch_set.handles if item.kind == "attr"]

    assert monkey.remove(handle) is PatchStatus.REVERTED

    assert module.VALUE == 1
    assert [item.status for item in live] == [PatchStatus.REVERTED]
    patch_set.close()
    assert module.VALUE == 1


def test_module_hooker_without_operations_or_with_failure_requires_restart(tmp_path):
    sys.path.insert(0, str(tmp_path))
    write_module(tmp_path, "hpc_ops_hooker_plain", "VALUE = 1\n")
    install_import_hook()

    def failing(module):
        require_context().set_attr(module, "VALUE", 3)
        raise RuntimeError("hooker failed")

    reverted = []
    patch_set = PatchSet("hooker-plain")
    with patch_set.context.module("hpc_ops_hooker_plain") as monkey:
        plain = monkey.patch_module(lambda module: setattr(module, "PLAIN", True))
        broken = monkey.patch_module(failing)
        explicit = monkey.patch_module(lambda module: require_context().set_attr(module, "OTHER", 1, raising=False), revert=lambda module: reverted.append(module))

    module = importlib.import_module("hpc_ops_hooker_plain")
    report = patch_set.close()

    statuses = {item["id"]: item["status"] for item in report.handles}
    assert statuses[plain.id] == "requires_restart"
    assert statuses[broken.id] == "requires_restart"
    assert statuses[explicit.id] == "reverted"
    assert reverted == [module]
    assert module.VALUE == 1
    assert not hasattr(module, "OTHER")
