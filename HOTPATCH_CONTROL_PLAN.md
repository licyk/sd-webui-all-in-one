# Hotpatcher Control Plane: Analysis and Implementation Plan

> Status: **approved, implementation in progress**. On 2026-11-11 the user accepted every recommended default for D1–D7 (§10).
> Created: 2026-11-11 on branch `dev`, at commit `8e0aa484`.
> Progress is tracked in [`todo.md`](todo.md).
> When implementation is done, this file is rewritten to describe the shipped design and moved into the documentation tree (see §10, decision D1). `todo.md` is then deleted.

## 0. Goal and scope

The task asks for four things:

1. Extend the hot-patching system (`sd_webui_all_in_one/patcher/`) with a **wider range of patch operations**.
2. Add **debugging** capabilities.
3. Support **runtime loading and unloading of patches**.
4. Make the **runtime-server connection parameters** updatable. The plan reads "updating the connection parameters of the hot-patching server" as covering both ends of the link:
   - the patched child's target: host, port, token, timeouts and reconnect;
   - the host-side `HotpatcherRuntimeHost` listener: its listen address, port and token, which can change while a child is attached.

   See §4.6 and decision D7.

All four are exposed through **one unified, extensible API**.

Hard constraints:

- **No new dependencies.** Only the stdlib and the existing infrastructure.
- **The patcher core stays standalone.** `sd_webui_all_in_one_hotpatcher` must not import `sd_webui_all_in_one`. It is injected into product venvs through `PYTHONPATH`.
- **Python ≥ 3.10 syntax.** CI runs 3.10–3.15.
- **No `global` statements** anywhere in the core. This is enforced by `patcher/tests/core/test_hotpatcher_state.py`, and all process state lives on `HotpatcherState`.
- **Behaviour is backward compatible** for:
  - every existing public API;
  - every environment variable;
  - every wire message (`services.*`, desktop `config.apply`, legacy JSONL);
  - the output of `get_default_config()` and `get_catalog()`, which the GUI and the host consume.

The reference projects are used narrowly. §3 lists exactly what is borrowed and what is a non-goal.

---

## 1. Current implementation: architecture and mechanisms

### 1.1 Layers

| Layer | Location | What it does today |
|---|---|---|
| Import hook | `patcher/sd_webui_all_in_one_hotpatcher/hook.py` | `Monkey` holds the patch plan for one module, as 8 lists of tuples. `MonkeyZoo` maps casefolded names to a `Monkey`. `HookedMetaPathFinder` sits at `sys.meta_path[0]`, and `MonkeySourceFileLoader` applies the plan. It also wraps `importlib.util.spec_from_file_location`. |
| Code mutation | `mutable.py` | `CodeWrapper` and `TupleWrapper` make code objects editable for bytecode patches. |
| Stack shadow | `stack_shadow.py` | A second finder that rewrites `co_filename` for prefixed modules. |
| State | `state.py` | The `HotpatcherState` dataclass, which holds every piece of process-global state. |
| Bootstrap | `bootstrap.py`, `patcher/sitecustomize.py` | Environment-driven start-up. The order is: shadow, import hook, transport, config, `apply_config`, error/log capture, services channel. |
| Services | `services.py` (1506 lines) | `DEFAULT_CONFIG`, `SETTING_SCHEMA`, catalog, normalize/load/save, `apply_config`, and the JSON request handler. It also contains `ServiceControlChannel`, a second TCP connection that serves `services.*` requests coming from the host. |
| Runtime, legacy | `runtime/{protocol,transport,client,config}.py` | TCP JSONL. **The child is the client**: it connects once to the host's server. |
| Runtime, desktop | `runtime/desktop_broker.py` | HTTP broker client owned by Rust/Hanafubuki, protocol v2. It has bounded queues, replay, and commands. |
| Runtime features | `runtime/{browser,errors,logs,faults,audit,progress,fileops}.py` | Event producers. They talk to the transport through the `RuntimeEventSink` duck type in `runtime/interfaces.py`. |
| Extensions | `patcher/sd_webui_all_in_one_hotpatcher_ext/*` | Six recipes: zluda, extension_index, hf_endpoint_mirror, uv_pip, comfyui_auto_port, xformers_cutlass. Each exposes `apply_from_config(cfg)`. |
| Host side | `base_manager/hotpatcher_manager/{config,host,protocol}.py`, `base_manager/gui/hotpatcher_manager_gui/` | Builds the launch environment. `HotpatcherRuntimeHost` is a `ThreadingTCPServer` and is **only started by the Tk GUI**. |
| Surfaces | `cli_manager/utils.py` (`self-manager patcher …`), `api_server/registry.py` (`hotpatcher.*`) | Config-only operations. The API server deliberately has **no** runtime control, and `tests/api_server/test_registry.py:43-45` asserts that. |

### 1.2 Key mechanisms (verified in source)

- **Patch application order** (`hook.py:659-715`):
  1. `get_code`: source → AST → compile → bytecode.
  2. `exec_module`: premodule → import injection (with stdout redirected if prohibited) → `exec` → function patches → module patches → per-function output prohibition.
  3. Within each stage, entries run in ascending integer `priority` order.
- **Finder cache** (`hook.py:563-567`). `find_spec` returns `self.cache[fullname]` *before* it consults the zoo. The cached spec's loader holds a reference to the `Monkey`.
- **Loader eligibility** (`hook.py:608-626`, `860-861`). Only `SourceFileLoader` specs are wrapped. Modules loaded from extensions, sourceless `.pyc` files or zips get **no patches at all**, not even post-exec function or module patches.
- **The `spec_from_file_location` wrapper** (`hook.py:841-857`) always uses `get_default_state()`, never an explicit state.
- **Error policy.** Every `eval_*` wraps each hooker in `try/except Exception: capture_exception()`. A failing patch is logged and the import continues. A source patch that matches nothing is completely silent.
- **Services dispatch** (`services.py:997-1054`) is an `if` chain over 7 `services.*` types. Desktop dispatch is a separate function (`bootstrap.py:257-286`) that accepts only `config.apply`. A third dispatcher lives on the host side, as wrappers in `host.py:175-240`.
- **The feature catalog is hardcoded in five places in `services.py`**:
  1. `DEFAULT_CONFIG` (54-140);
  2. `SETTING_SCHEMA` (142-440);
  3. `_apply_extension_config` (1194-1260);
  4. `_warn_disabled_but_active` (1295-1336);
  5. `_attach_feature_state` (1339-1367).

  Adding an extension means editing all five, plus `test_extension_package_layout.py`.
- **Legacy connection** (`runtime/client.py:123-170`). `RuntimeClient.connect_from_env` reads `…_HOST/_PORT/_TOKEN/_TIMEOUT/_CONNECT_TIMEOUT/_REQUEST_TIMEOUT/_EVENT_WRITE_TIMEOUT` exactly once. There is **no reconnect** anywhere in the legacy client or transport. Once the connection is missed, it is permanent for the life of the process.
- **Desktop broker** (`runtime/desktop_broker.py`):
  - `DesktopBrokerSettings` is a frozen dataclass built from Rust-owned environment variables.
  - Commands run **synchronously on the single broker worker thread** (`_accept_command`, around line 810).
  - Bounds: each result is ≤ 64 KiB, command types are ≤ 128 bytes, and there is a heartbeat every 5 s.
  - The Rust side (`Hanafubuki-dev/src-tauri/crates/hanafubuki-runtime-broker/src/session/commands.rs:4-29`) accepts **any** `commandType` of 1–128 bytes. Today it only sends `config.apply`, from `hanafubuki-management/src/service/hotpatch/apply.rs:134-139`, with a 30 s deadline.
- **Host connection handling** (`host.py:257-353`):
  - The token is checked on the first line only, and an empty token accepts anyone.
  - `hello.version` and `hello.features` are recorded but never inspected.
  - There is one `_service_channel` slot. It is replaced by the newest channel, and removal checks identity (`host.py:476-479`).
- **Launch path** (`hotpatcher_manager/config.py:199-275`):
  - It strips every `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_*` variable except `DEBUG`, plus `TOKEN` and `TIMEOUT` when runtime is on.
  - It hardcodes `HOST=127.0.0.1` and has no token flag.
  - It drops the user's `CONNECT_TIMEOUT`, `REQUEST_TIMEOUT`, `EVENT_WRITE_TIMEOUT`, `TRANSPORT_MODE`, `LOG_*` and `ERROR_*` settings.
  - A second builder, `build_hotpatcher_runtime_env` (`config.py:345-381`), disagrees with the first. It replaces `PYTHONPATH` instead of prepending, uses the `remote` config source, and sets `IMPORT_HOOK=1`.
- **Existing un-patch precedents**:
  - `uv_pip` keeps the original `subprocess.run` and restores it only if its own wrapper is still installed (`uv_pip/patches.py:56-121`).
  - `browser.py` installs a wrapper once and switches behaviour through a mode stored on state, so the wrapper is effectively a trampoline. Its "unload" is a switch to `passthrough`.
  - `comfyui_auto_port` registers an import-time patch **and** applies it directly when the module is already imported. It tags its hooker with a marker attribute for idempotency.

### 1.3 Limitations this plan addresses

| # | Limitation | Evidence |
|---|---|---|
| L1 | Patches are anonymous tuples with no id, so nothing can be listed per patch, unloaded, or replaced. | `Monkey.*_patches` lists |
| L2 | There is no undo for anything. Services v1 explicitly "does not uninstall". | `services.py:1295-1336` warnings |
| L3 | Patches only work if they are registered *before* the first import. Already-imported modules need hand-written code in each extension. | `comfyui_auto_port`, `browser` |
| L4 | Non-`SourceFileLoader` modules silently get no patches. | `hook.py:614` |
| L5 | Patch failures and source patches that match nothing are silent, and there is no strict mode, tracing, or introspection. | every `eval_*` |
| L6 | There is no way to load a patch at runtime from a file or module, or to reload or unload it. | — |
| L7 | The feature catalog is hardcoded in five places, so extensions are not pluggable. | `services.py` |
| L8 | There are three ad-hoc dispatchers and no shared command model, capability discovery, or versioning for control. | `services.py:997`, `bootstrap.py:257`, `host.py:175` |
| L9 | Legacy connection parameters are frozen at bootstrap. There is no reconnect and no live update, and the launch path cannot set host or token and drops timeouts. | `client.py:123`, `config.py:199` |
| L10 | The finder cache can serve a stale wrapped spec after the plan changes. | `hook.py:566` |
| L11 | The `spec_from_file_location` wrapper ignores a non-default state. | `hook.py:842` |

---

## 2. Reference projects: what to borrow

### 2.1 pytest and pluggy (pytest repo, plus pluggy 1.6.0 from the py311 env)

| Idea | Source | Use here |
|---|---|---|
| **Undo journal** of `(target, name, old_or_NOTSET)` entries. `NOTSET` means "absent", so undo becomes a delete. For classes the old value is read from the raw `__dict__`, which preserves `staticmethod` and `classmethod` objects. | `_pytest/monkeypatch.py:141-145, 254-272, 415-456` | `control/journal.py`. Improvement over pytest: **one** LIFO list with per-entry error isolation and an idempotent `undo()`. |
| Resolve dotted targets with `getattr` first, then import. `rsplit` splits module from attribute. | `monkeypatch.py:65-110` | `resolve_target("pkg.mod:Cls.attr")`. |
| Atomic writes: write to a temp file, then `os.replace`. | `assertion/rewrite.py:312-331` | Writing config back during live updates. |
| `mark_rewrite` warns when a module is **already imported**. | `rewrite.py:260-286` | The `already_imported` outcome and diagnostic in `explain()`. |
| Stable trampolines whose target is swapped at runtime, so code is never recompiled. | `rewrite.py:502-524` | `wrap_callable(..., trampoline=True)`. References copied elsewhere keep working after unload. |
| **TagTracer**: hierarchical tags, near-zero cost when off, enabled through an env var. | `pluggy/_tracing.py:16-72`, `config/__init__.py:534-547` | `control/trace.py`, `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TRACE`. |
| One dispatch choke point with monitors that return an undo closure. | `pluggy/_manager.py:109-120, 447-482` | `CommandRegistry.dispatch` is the single entry point for tracing, auth and timing. |
| A save stack for global replacements, restored through cleanup. | `_pytest/debugging.py:65-89` | Journal entries for `sys.excepthook`-style globals. |
| `ExitStack`-based `add_cleanup` (LIFO). | `config/__init__.py:1266, 1309-1313` | `PatchSet` disposers. |

### 2.2 pykardia

| Idea | Source | Use here |
|---|---|---|
| **Every acquisition is paired with its inverse** ("effect"). Disposers run LIFO and continue past failures, re-raising the first error. A disposer added after close runs immediately. | `core/effect.py`, `core/cleanup.py:50-128` | `PatchSet` owns its journal and disposers. Closing it reverts everything newest-first. |
| **A failed mid-load reverts that episode's resources**, and the unit ends in a sticky `failed` state. | `core/state.py:514-529` | `PatchSet` loading is transactional: if `setup` raises, everything it registered is reverted. |
| `on_update` hooks change parameters **in place**; a restart is only the fallback. | `core/context.py:456-497`, `core/fiber.py:100-141` | `FeatureSpec.update` and `connection.update`. Validate first, keep the old state if validation fails. |
| Side effects run **after the lock is released**, never while holding it. | `core/root.py:40-49`, `runtime.py:80-92` | The registry lock never covers imports or user callbacks; this avoids deadlock with the import lock. |
| Status is derived from target and episode, with explicit states. | `core/status.py`, `state.py:87-93` | `PatchHandle.status`: `registered/applied/reverted/failed/requires_restart`. |
| An event ring buffer read with cursors, plus lifecycle events. | `core/logger.py:147-167`, `core/events.py:34-81` | `control/events.py` ring buffer. Its cursor API is shaped like host `read_logs`. |
| Hot-reload pitfall: break-before-make with no fallback to the old version. | `docs/hot-reload.md:87-89` | `PatchSet.reload` keeps the previous module and **re-applies it** if the new one fails. |
| A versioned handshake that degrades gracefully for old peers. | `hmr/process.py:255-276` | `hotpatch.capabilities`. Old peers answer `unknown_request` or `unknown_command`, and the caller falls back. |

### 2.3 Explicit non-goals

- pykardia's fiber, asyncio and service-DI runtime.
- pluggy's banded `tryfirst`/`trylast`/wrapper ordering. The existing integer `priority` is kept.
- pytest's pyc rewrite cache.
- File-watch dependencies. Optional watching uses stdlib polling only.
- Changing desktop-broker connection parameters from Python. They are owned by Rust.

---

## 3. Target architecture

### 3.1 Overview

```text
                 ┌──────────────────────────────────────────────────────────┐
 Python API ───▶ │ HotpatchController (control/controller.py)               │
 services.* ───▶ │   └─ CommandRegistry (control/commands.py)               │◀─ desktop commandType
 legacy channel▶ │        dispatch(type, payload, ctx) → envelope           │◀─ host request_control()
                 │   ┌───────────────┬──────────────┬──────────────┬───────┤
                 │   │ PatchManager  │ FeatureReg.  │ Debug        │ Conn. │
                 │   │ (sets/handles │ (FeatureSpec │ (trace,      │ Mgr   │
                 │   │  journal,     │  replaces 5  │  events,     │       │
                 │   │  loader)      │  hardcodes)  │  inspect)    │       │
                 │   └──────┬────────┴──────┬───────┴──────┬───────┴───┬───┘
                 └──────────┼───────────────┼──────────────┼───────────┼────┘
                            ▼               ▼              ▼           ▼
                  hook.py (Monkey/Zoo/  ext/* FEATURE   all layers   runtime/client.py
                  Finder/Loader +       declarations    emit trace   (RuntimeClient.rebind,
                  handles, generic                       + events      services/fault reopen)
                  post-exec loader)
```

New subpackage: `sd_webui_all_in_one_hotpatcher/control/`. It is lazily imported, which keeps bootstrap cheap and keeps it compatible with stack shadowing. Existing modules get additive changes only.

| New module | Responsibility |
|---|---|
| `control/journal.py` | `NOTSET`, `JournalEntry`, `PatchJournal` (LIFO, isolated undo, idempotent). |
| `control/targets.py` | `resolve_target("pkg.mod:Obj.attr")`, `split_target`. Accepts both `:` and dotted forms. |
| `control/handles.py` | `PatchHandle`, `PatchStatus`, `PatchOutcome`, and the id allocator, which uses a counter on state. |
| `control/patchset.py` | `PatchSet`, the unit of load/unload/reload; `PatchContext`, the API a patch author sees; and the `current_patch_context()` contextvar. |
| `control/operations.py` | Live operations (§4.1). |
| `control/loader.py` | Runtime loading of patch modules from a dotted name or file path, reload with rollback, and an optional polling watcher. |
| `control/features.py` | `FeatureSpec`, `FeatureRegistry`, and the list of built-in features. |
| `control/trace.py` | `HotpatchTracer`, a TagTracer-style tracer. |
| `control/events.py` | `PatchEventLog`, a bounded ring buffer with cursors. |
| `control/inspect.py` | `explain`, `render_patched_source`, `verify_source_patches`, `snapshot`. |
| `control/commands.py` | `CommandSpec`, `CommandRegistry`, payload validation, error codes, envelopes. |
| `control/controller.py` | The `HotpatchController` facade and `get_controller(state=None)`. |
| `runtime/connection.py` | `RuntimeConnectionSettings` and `ConnectionManager` (legacy live update and reconnect). |

### 3.2 State additions (`state.py`)

These are added as fields on `HotpatcherState`, so the code needs no `global` statement:

- `control_lock`: an `RLock`.
- `patch_id_counter`.
- `patch_sets`: `dict[str, PatchSet]`.
- `patch_handles`: `dict[str, PatchHandle]`.
- `feature_registry`.
- `tracer`.
- `event_log`.
- `strict_mode`.
- `connection_manager`.
- `controller`.

**Lock discipline.** `control_lock` guards only in-memory registry mutation. It is **never** held while any of the following runs:

- `importlib` calls;
- user hookers or patch `setup` functions;
- socket or HTTP I/O.

The pattern is "compute under the lock, then act outside it" (from pykardia). This prevents deadlock with the per-module import lock: the main thread can hold the import lock while it reads the zoo, while a control thread holding `control_lock` tries to import.

**The finder's re-entrancy guard becomes thread-local.**

- `LoadingSkipper` (`hook.py:480-497`, and a copy in `stack_shadow.py:22-40`) is today a shared list with `append`/`pop`. `find_spec` returns `None` for any name currently in that list.
- That is safe while only one thread imports through the hook. Once control threads import or call `find_spec` (load, explain, verify, `apply_if_loaded`), a concurrent import of the same name on the main thread could receive an **unpatched** spec.
- Both guards move to `threading.local()` storage on the finder instance. The concurrency test (§7) covers this case.

### 3.3 Handles on import-time patches (fixes L1 and L10)

- The `Monkey` list entries **keep their exact tuple shapes**, because extensions unpack them: `for hooker, _priority in monkey.module_patches`.
- Handles are kept as **one parallel list of handle ids per stage**, for example `_premodule_handle_ids: list[str]`, aligned index-for-index with the public list.
  - An `id(entry)` key cannot work. `output_prohibition` entries are `str | None` (`hook.py:59`), so every `None` and every interned name would share one id.
  - `list.remove` also matches by equality, not identity.
  - Removal therefore finds the index by **identity search** (`is`) over the stage list and deletes the same index from both lists.
  - Entries appended to a public list directly, bypassing `patch_*`, get a handle lazily the first time the plan is listed.
- Every `patch_*` method returns its `PatchHandle`. The current return value is `None`, so this is an additive change.
- `Monkey.remove(handle)` removes the entry as described above.
- **Ownership through a context variable.** While a `PatchSet` is active, every `patch_*` call attaches its handle to that set. A set is active during its `setup`, during feature `apply`, or inside `with ps:`, and is exposed through the `current_patch_context()` contextvar. This applies even when the call goes through the plain `monkey_zoo(...)` / `register_hook(...)` APIs. As a result, unmodified extension `apply_from_config` code is attributed to its feature's set, and `features.disable` can revert it.
- `MonkeyZoo.discard(name)` drops a `Monkey` that has become inactive.
- **Every plan mutation invalidates the finder cache for that module name**, via a new `HookedMetaPathFinder.invalidate(fullname)`. This fixes L10.
- `_spec_from_file_location_wrapper` resolves the state that owns the active finder, instead of always using the default. This fixes L11. The single-state behaviour stays identical.

### 3.4 Outcome recording (fixes L5, baseline debugging)

Each `eval_*` records one `PatchOutcome` per hooker invocation into the handle and the event log:

- **`applied`**
- **`noop`**:
  - a source hooker that returned identical text;
  - a function hooker that returned `None`;
  - an AST transformer that returned the same tree object with no change. This is detected by comparing `ast.dump` before and after, and only in debug mode, because the dump is expensive.
- **`failed`**, with the exception type, message and bounded traceback.
- **`skipped`**, with a reason such as `function_missing`, `unsupported_loader` or `condition_false`.

**Strict mode** is enabled by `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_STRICT=1`, by `core.debug.strict`, or at runtime through `hotpatch.debug.strict.set`. In strict mode a hooker exception propagates out of the import instead of being swallowed. The default is off, which keeps today's tolerance.

---

## 4. Feature design

### 4.1 Wider range of patch operations

Every operation is available as a `PatchSet` / `PatchContext` method. Each one returns a `PatchHandle` and journals its inverse.

| Operation | API | Undo | Notes |
|---|---|---|---|
| Set or delete an attribute | `ctx.set_attr(target, value, *, raising=True)`, `ctx.del_attr(target)` | journal (raw `__dict__` for classes) | The target can be a module, class or instance, given as an object or a string. |
| Set or delete an item | `ctx.set_item(mapping, key, value)`, `ctx.del_item(mapping, key)` | journal | Covers registries, dict constants and `sys.modules` aliasing. |
| Environment variable | `ctx.set_env(name, value, *, prepend=None)`, `ctx.del_env(name)` | journal | Same semantics as pytest `setenv`, with prepend. |
| `sys.path` | `ctx.syspath_prepend(path)` | journal (remove the inserted entry by value) | Calls `importlib.invalidate_caches()`. |
| Wrap a callable | `ctx.wrap(target, factory, *, trampoline=False)` | journal; with `trampoline=True` the target is swapped back to the original | `factory(original) -> replacement`. A trampoline keeps the installed object stable, so `from x import f` copies follow the swap and the unload. |
| Class member patch | `ctx.patch_method(target, factory)`, `ctx.set_class_attr(...)` | journal (keeps `staticmethod`/`classmethod`/`property` descriptors) | Applies the pytest descriptor rules. |
| Rebind copied references | `ctx.wrap(..., rebind_references=True)` | journal per rebind | Optional. Scans `sys.modules[*].__dict__` for identity matches with the original, for code that already ran `from mod import f`. The scan is bounded and listed in the outcome. |
| Import-time plan (existing stages) | `with ctx.module("pkg.mod") as monkey: …` | deregister, plus the live-revert rules in §4.3 | This is the existing `Monkey` API, now owned by the set. |
| Retroactive apply | `ctx.module("pkg.mod", apply_if_loaded=True)` | journal for the function and injection writes | Runs function patches, module patches, injections and output prohibition against `sys.modules[name]` if it is already loaded. This generalises what `comfyui_auto_port` and `browser` hand-roll today. |
| Post-exec patches for any loader | automatic | as above | A new `PostExecLoader` delegates `create_module` and `exec_module` to the original loader, then runs the post-exec stages. Source, AST and bytecode stages are reported as `skipped:unsupported_loader`. Fixes L4. |
| Conditional patch | `condition=callable` on any registration | — | Evaluated when the patch is applied. A false result gives `skipped:condition_false` (for example, version guards in the style of `xformers_cutlass`). |
| Explicit module reload | `ctx.reload_module(name)`; command `hotpatch.modules.reload` | not undoable; marks `requires_restart` | **Opt-in only.** It re-executes the module under the current plan through `importlib.reload`, logs a warning, and lists the caveats about stale references in other modules. |

### 4.2 Runtime patch loading and unloading

A **patch module** is a Python module or file that defines:

```python
def setup(ctx: PatchContext) -> None: ...                      # required
def teardown(ctx: PatchContext) -> None: ...                   # optional, runs before the journal undo
def update(ctx: PatchContext, config: dict) -> bool: ...       # optional, in-place reconfiguration
```

- **Load.** `controller.load_patch(source, *, name=None, config=None)` loads the module.
  - A dotted name is imported normally.
  - A file path is loaded with `spec_from_file_location` under the private name `sd_webui_all_in_one_hotpatcher_dynamic.<set_id>`. It is **not** inserted into user-visible names.
  - The module's `setup` then runs inside a new `PatchSet`.
- **Transactional.** If `setup` raises, the set is closed (LIFO revert), its status becomes `failed`, and the error is returned.
- **Unload.** `controller.unload_patch(set_id)`:
  1. calls `teardown`;
  2. undoes the journal (LIFO, with isolated failures);
  3. deregisters the import-time entries the set owns;
  4. invalidates the finder cache.

  It returns a per-handle report: `reverted`, `deregistered`, or `requires_restart`.
- **Reload.** `controller.reload_patch(set_id)` works as follows:
  1. The old module is kept.
  2. The old set is unloaded.
  3. The new code is loaded.
  4. **If the new code fails, the old module's `setup` runs again.** The result is `rolled_back`, and the error is attached.
- **Update.** `controller.update_patch(set_id, config)` calls `update()` when it is defined and returns true. Otherwise it falls back to a reload.
- **Watching** (`control/loader.py: PatchFileWatcher`) is optional and off by default.
  - It is enabled with `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_WATCH=1` or `control.watch.enabled`.
  - A daemon thread polls the file's mtime, size and sha256 every `interval` seconds (default 1.0).
  - A change triggers a debounced `reload_patch`, and failed paths are retried on the next change.
- **Config-declared sets.** A new config section `control.patch_sets: [{"source": ..., "config": {...}, "enabled": true}]` is applied by `apply_config` after the extensions, so patch sets can be shipped in `patcher_config.json`.
- **Trust boundary.** Loading code is code execution.
  - Over a channel, `hotpatch.patches.load` with a `source` is **disabled unless** `control.allow_remote_load=true` (default `false`).
  - On legacy transports it also requires a **non-empty token**.
  - In-process Python API calls are always allowed.

### 4.3 Unload semantics by stage

This is the contract that `unload` reports for each handle:

| Stage | Target not yet imported | Target already imported |
|---|---|---|
| `patch_sources` / `patch_ast` / `patch_bytecode` | `deregistered` (fully reverted) | `requires_restart`. The live code cannot be un-compiled. Only future imports and reloads are affected. |
| `patch_premodule` | `deregistered` | `requires_restart`, unless the hooker registered an inverse through `current_patch_context()` |
| `inject_import` | `deregistered` | `reverted` (the framework journals the write into `module.__dict__`) |
| `patch_function` | `deregistered` | `reverted` (framework-journaled write). Copies outside the module are reverted only with `rebind_references` or `trampoline` |
| `patch_module` | `deregistered` | `requires_restart`, unless the hooker used `ctx.*` operations, which are journaled, or passed `revert=` |
| `prohibit_output` | `deregistered` | `reverted` (wrapper journaled) |
| `alias_if_not_exists` | `deregistered` | `requires_restart` if the alias module is already in `sys.modules` |
| live operations (§4.1) | — | `reverted` |
| runtime features (browser, errors, logs) | — | use the existing uninstall paths: `uninstall_error_capture`, `uninstall_log_capture`, browser `passthrough`. Audit hooks cannot be removed (`sys.addaudithook`), so they report `requires_restart`. |

`Monkey.patch_module(hooker, priority=100, *, revert=None)` and `patch_premodule(..., revert=None)` gain an optional inverse. This is additive.

### 4.4 Extensible feature registry (fixes L7)

```python
@dataclass(frozen=True)
class FeatureSpec:
    key: str                         # "extensions.uv_pip"  (catalog key; config path derived by split(".") )
    title: str
    description: str
    defaults: Mapping[str, Any]      # merged into DEFAULT_CONFIG at key path
    settings: Mapping[str, Any]      # SETTING_SCHEMA["..."]["settings"]
    apply: str | Callable[[FeatureContext, dict], bool | None]  # "module:callable" resolved lazily; None/True → applied; False → optional-skip
    is_active: Callable[[], bool] | None = None
    revert: Callable[[FeatureContext], None] | None = None # else: PatchSet journal revert if possible
    update: Callable[[FeatureContext, dict, dict], bool] | None = None  # in-place param change
    enabled: Callable[[dict], bool] = _enabled_flag        # extension_index uses any(sub.enabled)
    requires_runtime_client: bool = False
    optional: bool = False           # current _apply_optional_step semantics
    disabled_warning: str | None = None  # preserves the exact current warning texts
    order: int = 100                 # preserves current apply order
```

- The built-in core, runtime and extension features are declared as `FeatureSpec`s, **as data inside the core** in `control/features.py`.
  - Defaults, schema, titles and warnings are plain literals.
  - `apply`, `is_active`, `revert` and `update` refer to extension code by lazy `"sd_webui_all_in_one_hotpatcher_ext.uv_pip:apply_from_config"` strings, resolved only when they are called.
  - **Why:** today `import sd_webui_all_in_one_hotpatcher.services` loads **no** `sd_webui_all_in_one_hotpatcher_ext` modules (verified 2026-11-11). Extensions are first imported inside `_apply_extension_config`, i.e. *after* `_apply_core_config` has installed the stack shadower, so they get shadowed tracebacks.
  - Eager `ext/*/feature.py` imports would break that ordering, and would break a core-only copy of the package. A P0 invariant test locks the current behaviour.
  - Third-party or out-of-tree features can still pass a callable directly.
- `FeatureRegistry` has `register(spec)`, `unregister(key)`, `get(key)` and `iter()`.
- Third-party features can register at runtime, and they appear in the catalog immediately.
- `DEFAULT_CONFIG`, `SETTING_SCHEMA`, `_apply_extension_config`, `_warn_disabled_but_active` and `_attach_feature_state` are **derived from the registry**.
  - The module constants `DEFAULT_CONFIG` and `SETTING_SCHEMA` remain as computed module-level dicts for compatibility.
  - A **golden snapshot test** freezes the current output of `get_default_config()` and `get_catalog()`, minus volatile `active` fields, before the refactor, and must still pass after it.
- Each feature applies inside its own `PatchSet` (`feature:<key>`). That makes `hotpatch.features.disable` able to really revert whenever every handle is revertible. Otherwise it reports `requires_restart`.
- **`apply_config` semantics are unchanged by default.** `enabled=false` still means "do not register", and the existing warnings stay. Reverting disabled features is opt-in, through `apply_config(..., reconcile=True)` or the config field `services.reconcile_disabled: false`. See decision D5.

### 4.5 Debugging capabilities

| Capability | API / command | Details |
|---|---|---|
| Per-patch outcomes | `hotpatch.patches.list` / `get` | Status, last outcome, counts, owner set, target and stage. See §3.4. |
| Strict mode | `hotpatch.debug.strict.set` | Patch errors propagate. Applies to new imports only. |
| Tracing | `hotpatch.debug.trace.get/set`; env `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TRACE=import,patch,control,conn` and `…_TRACE_FILE` | Tags: `import` (finder hits and skips with a reason), `patch` (each hooker invocation and outcome), `control` (each dispatch with timing), `conn` (connection changes). The writer goes to stderr or a file. When disabled it costs one attribute check. |
| Event log | `hotpatch.debug.events.read {since_cursor, limit}` | A ring buffer of 1000 entries with cursor and `truncated` semantics, matching host `read_logs`. Event types: `patch.registered`, `patch.applied`, `patch.noop`, `patch.failed`, `patch.reverted`, `set.loaded`, `set.unloaded`, `set.failed`, `set.rolled_back`, `import.intercepted`, `import.skipped`, `connection.changed`. |
| Event forwarding | config `control.forward_events: false` | When enabled, `patch.failed`, `set.*` and `connection.changed` are sent through the runtime sink as `hotpatch.event` events. This is **opt-in**, to protect the desktop queue's 240-slot admission. |
| Explain | `hotpatch.inspect.explain {module}` | Answers "why is or isn't this patched?" It reports whether a plan exists, whether the module is already in `sys.modules`, its loader type and eligibility, whether the finder is installed, whether the finder is first on `meta_path` relative to the stack shadower, the cache state, and the handles and outcomes. |
| Patched source | `hotpatch.inspect.source {module, max_bytes}` | Runs the source patches, AST patches and `ast.unparse` **without executing**. The output is bounded to 48 KiB by default to stay under the desktop 64 KiB result cap, and has a `truncated` flag. |
| Verify | `hotpatch.inspect.verify {module?}` | A dry run of the source and AST patches. It reports which hookers were no-ops, so a target library upgrade that broke a `str.replace` patch is caught. |
| Snapshot | `hotpatch.status` | Versions, transport status, installed hooks, sets, features, strict/trace state, and connection settings with the token redacted. |

### 4.6 Connection parameters (fixes L9)

**Layer 1: settings model** (`runtime/connection.py`):

```python
@dataclass(frozen=True)
class RuntimeConnectionSettings:
    host: str; port: int; token: str = ""
    connect_timeout: float; request_timeout: float; event_write_timeout: float
    reconnect: bool = False; reconnect_initial: float = 0.1; reconnect_max: float = 5.0
    allow_non_loopback: bool = False
    @classmethod
    def from_env(cls, environ=None) -> "RuntimeConnectionSettings | None": ...
    def merged(self, changes: Mapping[str, Any]) -> "RuntimeConnectionSettings": ...  # validated
    def redacted(self) -> dict[str, Any]: ...
```

- `RuntimeClient.connect_from_env` is reimplemented on top of `from_env`, with identical behaviour.
- New environment variables are additive:
  - `…_RECONNECT=1`, which turns reconnect on;
  - `…_ALLOW_NON_LOOPBACK=1`, which allows a non-loopback host.

**Layer 2: live update and reconnect for the legacy transport.**

- `RuntimeClient` gains `rebind(transport)`. It atomically swaps `self.transport` under a new lock.
- Every holder references the `RuntimeClient` object, never the transport: error capture, log capture, browser state, `Progress.manager`, `ServiceControlChannel.client`, and fault. Swapping the inner transport therefore keeps every holder valid without touching them. The repository has no `isinstance(..., RuntimeClient)` checks, verified by grep.
- `ConnectionManager.update(changes)` uses **make-before-break with rollback**:
  1. Validate with `settings.merged()`. A non-loopback host is rejected unless allowed.
  2. Connect a new transport and send `hello`. On failure return `connection_failed`, with nothing changed.
  3. Respond OK on the channel that carried the command. The switch runs as a **post-response action**: the command envelope carries `after_send` callbacks, which the services channel runs after `_send`.
  4. Open the new services channel, then re-enable faulthandler on a new fault channel, then `client.rebind(new_transport)`.
  5. If step 4 fails, rebind back to the old transport, close the new sockets, record a diagnostic, and emit `connection.changed {status: "rolled_back"}`.
  6. On success, close the old services channel and old transport. Host-side identity-checked removal (`host.py:476-479`) makes this ordering safe.
- **Reconnect** is opt-in. When the transport dies, a daemon thread retries with exponential backoff from 0.1 s to 5 s. While disconnected, events are dropped as best-effort, with a counter reported as `log.dropped`-style diagnostics. After reconnecting, the services and fault channels reopen.
- **Desktop broker.** `hotpatch.connection.get` returns `DesktopBrokerClient.status()` with credentials redacted. `update` returns `unsupported_transport`, because the settings are owned by Rust and frozen.

**Layer 2b: server-side parameter change** (`HotpatcherRuntimeHost.rebind(host=None, port=None, token=None)`, decision D7). The host changes its own listen address, port or token while a child is attached:

1. Start a second listener on the new address. Accept both the old and the new token during a bounded transition window, 30 s by default.
2. Send `hotpatch.connection.update {host, port, token}` to the child over the current services channel. Do this only if the child advertised `control` through the capability probe.
3. Wait, bounded, for the child's new services channel to arrive on the new listener.
4. Stop the old listener and drop the old token.

On timeout or failure, the new listener is shut down and the old one keeps serving. The method reports `{status: "switched" | "rolled_back" | "unsupported", ...}`. A child without `control` gets `unsupported`. The GUI's connection panel (D3) calls this method.

**Layer 3: host and launch path** (`base_manager/hotpatcher_manager`):

- `apply_hotpatcher_launch_env` gains `host` (default `DEFAULT_RUNTIME_HOST`) and `token` (default `None`, which inherits).
  - It **also preserves** the user's `CONNECT_TIMEOUT`, `REQUEST_TIMEOUT`, `EVENT_WRITE_TIMEOUT`, `TRACE`, `STRICT` and `RECONNECT` settings.
  - The default output is unchanged, which existing tests verify.
- `build_hotpatcher_runtime_env` and `apply_hotpatcher_launch_env` share one connection-variable builder. `PYTHONPATH` handling is unified on the prepend behaviour, with a test.
- `HotpatcherRuntimeHost`:
  - records `hello.version` and `hello.features` per main connection, for diagnostics only;
  - probes `hotpatch.capabilities` on each new services channel and caches the result as `client_capabilities`. A reply of `unknown_request` means a legacy peer;
  - gains `request_control(type, payload, timeout)` and convenience wrappers (`list_patches`, `load_patch`, `unload_patch`, `update_connection`, `read_patch_events`), plus `rebind()` (Layer 2b);
  - falls back to `services.*` when the peer is legacy;
  - logs a warning when bound to non-loopback with an empty token.
- CLI and GUI exposure is listed in §10 (decisions D2 and D3).
- The **API server stays free of runtime control**. The test assertion is kept.

### 4.7 Unified API

**One command registry, three transports, one Python facade.**

```python
# control/commands.py
@dataclass(frozen=True)
class CommandSpec:
    name: str                        # "hotpatch.patches.list"
    handler: Callable[[CommandContext, dict], dict]
    payload: Mapping[str, PayloadField]   # lightweight typed validation (type, required, choices, max_len)
    mutating: bool = False
    requires_token: bool = False     # enforced for legacy channel when token is empty
    remote: bool = True              # False → in-process only
    since: int = 1                   # control_version introduced
    aliases: tuple[str, ...] = ()    # e.g. "services.config.apply"

class CommandRegistry:
    def register(self, spec) -> None; def unregister(self, name) -> None
    def names(self) -> list[str]
    def dispatch(self, name, payload, ctx) -> dict   # single choke point: validate → trace → call → envelope
```

- **Envelopes are unchanged.** The success form is `{"ok": true, "payload": {...}}` and the error form is `{"ok": false, "error": {"code", "message"}}`. Existing error codes are kept: `invalid_request`, `invalid_json`, `unknown_request`, `request_failed`. New codes:
  - `invalid_payload`
  - `forbidden`
  - `not_found`
  - `unsupported_transport`
  - `connection_failed`
  - `remote_load_disabled`
- **`services.*` compatibility.** The 7 existing types are registered as commands, so `handle_request_json` becomes a thin shim over `dispatch`. Their payload shapes and result keys (`catalog`, `config`, `result`) are byte-compatible.
- **Desktop.** `_handle_desktop_command` becomes `dispatch` plus a mapping of `config.apply` → `{"applyResult": ...}`. Any other registered remote command is accepted. Unknown types still raise `DesktopBrokerCommandError("unknown_command")`.
  - Handlers run on the **single broker worker thread**, which also drives the 5 s heartbeat and event upload. So every command reachable from desktop must be **non-blocking and bounded**, with each result capped below 64 KiB and truncation flags.
  - A soft time budget does not bound anything, so it is not the mechanism. Instead, `CommandSpec.blocking=True` marks commands that import modules or run user code: `sets.load`, `sets.reload`, `sets.update`, `modules.reload`, and `features.enable` / `features.update` when they resolve a lazy `apply` for the first time.
  - On desktop, blocking commands return `unsupported_transport` in control_version 1. `config.apply` keeps its current synchronous behaviour, so its semantics are unchanged.
  - Off-thread execution for desktop, with an accepted result and a later completion event, is a follow-up together with D4.
  - On legacy, commands run on the services-channel thread, which blocks only that channel.
- **Capability negotiation.**
  - The legacy main connection's `hello` carries `features=[]` today, because `connect_from_env` passes none. The services channel is also a separate connection opened with `channel.open`, so `hello` features cannot describe it.
  - The mechanism is therefore an explicit **`hotpatch.capabilities` probe** on the channel the caller will use. A reply of `unknown_request` (legacy) or `unknown_command` (desktop) means an old peer.
  - `hello.features` additionally gains `"control"` as a hint for logs only. The host never inspects features (`host.py:274-280`), so this is safe.
  - `PROTOCOL_VERSION` stays 1. Control has its own `CONTROL_VERSION = 1`, reported by the probe.
- **Python facade** (`from sd_webui_all_in_one_hotpatcher import hotpatch`, which returns the controller for the default state):

```python
hotpatch.call("hotpatch.patches.list")            # generic, identical to remote dispatch
with hotpatch.patch_set("fix-foo") as ps:         # in-process authoring
    ps.set_attr("pkg.mod:FLAG", True)
    ps.wrap("pkg.mod:run", lambda f: wrapped(f), trampoline=True)
    with ps.module("pkg.other", apply_if_loaded=True) as monkey:
        monkey.patch_function("go", hooker)
hotpatch.unload_patch("fix-foo")
hotpatch.load_patch("my_patches.fix_bar", config={...})
hotpatch.connection.update(port=9000)
hotpatch.debug.trace(["patch", "import"]); hotpatch.inspect.explain("pkg.mod")
```

**Initial command set** (control_version 1):

| Group | Commands |
|---|---|
| Meta | `hotpatch.capabilities`, `hotpatch.status` |
| Patches | `hotpatch.patches.list`, `.get`, `.unload` (by handle id) |
| Sets | `hotpatch.sets.list`, `.load`, `.unload`, `.reload`, `.update` |
| Features | `hotpatch.features.list`, `.enable`, `.disable`, `.update` |
| Modules | `hotpatch.modules.reload` (opt-in, mutating, requires token) |
| Inspect | `hotpatch.inspect.explain`, `.source`, `.verify` |
| Debug | `hotpatch.debug.trace.get/set`, `hotpatch.debug.strict.set`, `hotpatch.debug.events.read` |
| Connection | `hotpatch.connection.get`, `.update`, `.test` (try to connect without swapping) |
| Legacy aliases | `services.catalog.get`, `services.defaults.get`, `services.config.current/normalize/load/save/apply`, desktop `config.apply` |


### 4.8 Hanafubuki integration (P11)

This is the desktop host side, in `/root/code_workspace/Hanafubuki-dev` (Tauri 2: Rust backend plus Vue). Work happens on a feature branch `hotpatch-control`, which is pushed to `origin`. The user merges it. Follow that repo's `AGENTS.md`. Findings from a survey on 2026-11-11:

- **Broker** (`crates/hanafubuki-runtime-broker`):
  - `queue_command` already accepts any 1–128 byte command type.
  - Results are stored in a 64-entry FIFO and can only be read by cloning the full session snapshot. `completedAt` is required.
  - Unknown **event** types are rejected (`session/events.rs:71-85`).
  - Changes:
    - accept `hotpatch.event` (bounded, retained like the runtime log events) for the opt-in forwarded events;
    - add a cheap `command_result(session, command_id)` lookup, so management does not clone snapshots for every query.
- **Management** (`crates/hanafubuki-management`):
  - Today `config.apply` is the only broker operation. It is task-shaped, using `BrokerOperationHandle` and the reconciler.
  - Add a typed **runtime control** service:
    - **Queries** (`hotpatch.capabilities`, `status`, `patches.list/get`, `sets.list`, `features.list`, `inspect.*`, `debug.events.read`, `debug.trace.get`, `connection.get`) are bounded request/response calls with a short deadline. They wait on the broker's result lookup and do not create a management task.
    - **Mutations** (`patches.unload`, `sets.unload`, `features.enable/disable/update`, `debug.trace.set`, `debug.strict.set`) are management tasks, like `config.apply`, using the existing claim and maintenance gates.
  - Python marks some commands `blocking` (`sets.load/reload/update`, `modules.reload`, first-time feature resolution) and rejects them on desktop with `unsupported_transport`. Hanafubuki does not offer them.
  - Capability gating: probe `hotpatch.capabilities` once per active session and cache the result. An `unknown_command` reply means a legacy peer, and the runtime control capability is reported as unsupported.
- **IPC.** Thin async Tauri commands through the module guard, with typed requests using `deny_unknown_fields` plus `strict-decoding-policy.toml` entries, registered in `lib.rs`.
- **Frontend:**
  - A "Runtime control" area in `HotpatchPanel` covering:
    - status and capabilities;
    - patches and patch sets, with unload;
    - features, with enable, disable and update;
    - inspect: explain, verify and source;
    - debug: trace, strict mode, and the event log with cursor paging;
    - connection status, read-only (desktop settings are owned by Rust).
  - `HotpatchField` support for the new catalog setting types `json` (a JSON text editor) and `float`, introduced in P5.
  - Every string in both `en` and `zh`.
- **Tests:**
  - broker unit tests (event type, result lookup);
  - management tests against a real `RuntimeBroker` with a scripted fake runtime, following `hotpatch_and_sessions.rs`;
  - vitest for the API wrappers, composables and panel.
- **Docs:** update `docs/backend-spec.md` §8.6 and the relevant `docs/rules/*`.
- **Validation:** `bun run format:check`, `bun run check` (includes `xtask` architecture policies) and `bun run test`; run `bun run prepare:assets` once before cargo.

---

## 5. Compatibility analysis

| Area | Risk | Mitigation |
|---|---|---|
| `Monkey` tuple shapes | Extensions and services unpack the tuples. | Shapes are unchanged; handles live in a side table. |
| `patch_*` return value | Currently `None`. | Returning a handle is additive. No caller uses the return value (to be grepped in phase 1). |
| `DEFAULT_CONFIG` / `SETTING_SCHEMA` / catalog | The GUI form and host defaults depend on them. | Golden snapshot test before refactoring; module constants are kept. |
| `services.*` wire | The host and GUI depend on it. | Registered as aliases with identical payloads and error codes; existing tests unchanged. |
| Desktop `config.apply` → `applyResult` | Rust depends on it. | A dedicated result mapping, covered by the existing broker command tests. |
| `apply_config` disable semantics | The GUI's remote apply expects "no uninstall". | Reconcile is opt-in (D5). |
| `hello.features` change | An old host could reject it. | The host never inspects features (verified, `host.py:274-280`). Capabilities come from the explicit probe instead. |
| New patcher plus old host | The host does not know control. | An old host never sends `hotpatch.*`, so the patcher's existing `services.*` handling is unchanged. |
| New host plus old patcher | Commands are unknown. | The `hotpatch.capabilities` probe returns `unknown_request`; the host marks the peer legacy and reports `unsupported` to the GUI. |
| Extension import order | Eagerly importing extensions would bypass the stack shadower and break a core-only copy. | Feature specs are data in core with lazy `"module:callable"` references; P0 invariant test. |
| Shared `LoadingSkipper` | A concurrent import could receive an unpatched spec. | Thread-local guard (§3.2), covered by the concurrency test. |
| Desktop worker stall | Blocking commands would stall heartbeats. | `blocking` commands are rejected on desktop in v1 (§4.7). |
| Lock and import-lock deadlock | Control commands arrive on channel or broker threads. | The lock discipline in §3.2, plus a dedicated concurrency test. |
| Stack shadow | New `control.*` modules get shadowed tracebacks. | Expected. Note that the `prefixes` setting can exclude them when debugging. |
| Bootstrap cost | Importing `control` at start-up. | Lazy: imported only when a command, feature registry access or patch set is needed. `services` derives its constants through a small eager `features` import, which has no heavy dependencies. |
| `global` ban, Python 3.10 | Language-level constraints. | All state on `HotpatcherState`; no `match` beyond 3.10, no `typing.Self` (3.11). |
| Patcher standalone | `comfyui_auto_port` already imports `sd_webui_all_in_one.utils` lazily (existing coupling, out of scope). | The new core modules import nothing from `sd_webui_all_in_one`. |
| Test filename uniqueness | `tests/` has no `__init__.py`. | New files are prefixed `test_control_*` / `control_test_helpers.py`. |
| Security | Remote load means remote code execution, and connection update redirects logs. | Remote load is off by default and needs a token; loopback is enforced by default; tokens are redacted in status and trace; the host warns about an empty token on a non-loopback bind. |
| Rust/Hanafubuki | It may want the new commands. | No Rust change is required for compatibility: Python accepts the new types when Rust starts sending them. P11 adds the Hanafubuki side (D4, revised 2026-11-11). |
| Remote load through config | `services.config.apply` and desktop `config.apply` can carry `control.patch_sets` or set `control.allow_remote_load` themselves, bypassing D6 (found in P5). | P7 gates config-borne patch sets on the configuration in effect **before** the request. A remote apply cannot enable `allow_remote_load` and use it in the same request, and remote patch-set entries are refused while the gate is closed. |

---

## 6. Implementation phases

Each phase ends **green** on the existing suites before moving on. That covers the 256 tests in the hotpatcher-related suites (baseline 2026-11-11), plus ruff, ty and docstring checks on touched files. The exact commands are in `todo.md`.

| Phase | Deliverable | Touches |
|---|---|---|
| **P0 Baseline** | Golden snapshots of `get_default_config()` / `get_catalog()` (static parts), the `services.*` response shapes, and the desktop `config.apply` result. Invariant test: importing `services` loads no `sd_webui_all_in_one_hotpatcher_ext` modules. | new tests only |
| **P1 Journal and PatchSet** | `control/{journal,targets,handles,patchset}.py`; state fields; LIFO isolated undo; transactional set. | `state.py`, new modules |
| **P2 Hook upgrades** | Thread-local `LoadingSkipper` (hook and stack shadow); handles on `Monkey` (parallel id lists, ownership through the contextvar); `remove` and `discard`; finder cache invalidation (L10); state-aware file-location wrapper (L11); outcome recording; strict mode; `revert=`; framework-journaled function, injection and prohibition writes; `PostExecLoader` (L4); `condition=`; retroactive `apply_if_loaded`. | `hook.py`, `exceptions.py` |
| **P3 Live operations** | `control/operations.py`: attr, item, env, sys.path, wrap/trampoline, class members, `rebind_references`, `reload_module`. | new module |
| **P4 Feature registry** | `control/features.py`; `FEATURE` declarations in each extension (`feature.py`); `services.py` derives its five hardcoded places from the registry; per-feature `PatchSet`; `features.enable/disable/update`; opt-in reconcile. | `services.py`, `ext/*/feature.py`, `test_extension_package_layout.py` |
| **P5 Runtime loading** | `control/loader.py`: load, unload, reload with rollback, update; config-declared `control.patch_sets`; `PatchFileWatcher`; trust gates. | new module, `services.py` (config section and catalog) |
| **P6 Debugging** | `control/{trace,events,inspect}.py`; env variables; optional event forwarding. | new modules, `bootstrap.py` (trace from env) |
| **P7 Unified commands** | `control/{commands,controller}.py`; `services.handle_request_json` becomes a shim; desktop handler goes through the registry; `hello` gains `"control"`; post-response actions in `ServiceControlChannel`; `hotpatch` facade export. | `services.py`, `bootstrap.py`, `runtime/protocol.py`, `__init__.py` |
| **P8 Connection** | `runtime/connection.py`; `RuntimeClient.rebind`; `ConnectionManager` update, test and reconnect; the services and fault channels reopen; desktop is read-only. | `runtime/client.py`, `transport.py`, `services.py`, `faults.py`, `bootstrap.py` |
| **P9 Host side** | Launch env `host` and `token`, preserved overrides, unified builders; host capability probe and `request_control` wrappers; `HotpatcherRuntimeHost.rebind()` server-side parameter change (D7); empty-token warning; CLI and GUI per D2/D3. | `base_manager/hotpatcher_manager/*`, GUI, `cli_manager/*` |
| **P11 Hanafubuki integration** | In `Hanafubuki-dev` on a feature branch (§4.8): broker, management, IPC, frontend, tests and docs for the `hotpatch.*` commands, plus the `json`/`float` catalog setting types. | `/root/code_workspace/Hanafubuki-dev` |
| **P10 Docs and cleanup** | Rewrite this plan as the as-built document at the D1 location; update patcher `README.md`, `docs/{architecture,services,runtime-protocol,environment-variables,extensions,testing}.md`; add `examples/runtime_patch_load.py`; delete `todo.md`. | docs |

Dependencies: P1 → P2 → P3. P4 depends on P1 and P2. P5 depends on P1–P3. P6 can start after P2. P7 depends on P4–P6. P8 depends on P7 for the post-response actions. P9 depends on P7 and P8. P11 depends on P6–P8, the Python command surface. It runs after P10 because the as-built docs describe the wire contract P11 consumes, and P11 then updates the hotpatcher docs only where Hanafubuki behaviour is described.

---

## 7. Testing requirements

New test files live under `sd_webui_all_in_one/patcher/tests/control/` and `tests/base_manager/hotpatcher_manager/`. Every filename is globally unique.

- **Journal** (`test_control_journal.py`):
  - `NOTSET` round trips;
  - class `staticmethod`/`classmethod`/`property` preserved through undo;
  - instance attributes that shadow class attributes;
  - LIFO order;
  - one failing entry does not stop the others, and the first error is reported;
  - idempotent `undo()`.
- **PatchSet** (`test_control_patchset.py`):
  - transactional failure reverts partial work;
  - a disposer registered after close runs immediately;
  - nested sets.
- **Hook** (`test_control_hook_handles.py`):
  - handle removal before import gives `deregistered`;
  - after import, function patches give `reverted` and source patches give `requires_restart`;
  - finder cache invalidation (register, import, discard, reimport after `sys.modules` cleanup);
  - `PostExecLoader` on an extension-module stub or sourceless `.pyc`;
  - strict mode raises;
  - outcome `noop` for a source patch that matches nothing;
  - extension tuple-unpacking still works.
- **Operations** (`test_control_operations.py`):
  - each operation applied and reverted;
  - a trampoline survives `from x import f` and is swapped back on unload;
  - the `rebind_references` scan is bounded and journaled.
- **Features** (`test_control_features.py`):
  - **golden snapshot equality** of defaults and catalog;
  - registering a third-party feature shows up in the catalog and in `apply_config`;
  - disable reverts `uv_pip`;
  - the existing disabled warnings are textually identical.
- **Loader** (`test_control_loader.py`):
  - load from a dotted module and from a file path, under a private name;
  - unload report;
  - reload rollback when the new version raises;
  - `update()` in place;
  - the watcher (tmp file, short interval, monkeypatched clock) triggers a debounced reload;
  - the remote-load gate refuses unless enabled and a token is present.
- **Debug** (`test_control_debug.py`):
  - the tracer is off by default (no writer calls);
  - tag filtering;
  - the event log ring and cursors, including truncation;
  - `explain` reasons (not registered, already imported, unsupported loader, finder missing);
  - `inspect.source` bounded at 48 KiB with a truncated flag;
  - `verify` reports no-ops.
- **Commands** (`test_control_commands.py`):
  - payload validation errors;
  - the `forbidden` path;
  - `services.*` aliases produce byte-identical responses to the P0 snapshots;
  - desktop `config.apply` keeps the `applyResult` mapping;
  - unknown command codes on both transports;
  - capabilities list.
- **Connection** (`test_control_connection.py`, reusing `runtime_test_helpers.JsonlHost`):
  - update to a second host: the response arrives on the old channel, then all three connections move;
  - a failed connect leaves everything unchanged;
  - a failed services reopen rolls back;
  - non-loopback is rejected by default;
  - reconnect after the host restarts (bounded backoff with an injected clock);
  - desktop returns `unsupported_transport`;
  - the token is redacted in status and trace.
- **Concurrency** (`test_control_concurrency.py`):
  - a control thread unloads or loads sets while the main thread imports patched modules in a loop. No deadlock within a timeout, and a consistent final state;
  - two threads import the same patched module concurrently while a third calls `explain`. Every resulting spec is wrapped, which verifies the thread-local `LoadingSkipper`;
  - on a desktop dispatch, a `blocking` command returns `unsupported_transport` without invoking its handler.
- **Ownership** (in `test_control_features.py`): an unmodified extension's `apply_from_config` registrations are attributed to its feature set, and `features.disable` deregisters them.
- **Host rebind** (`test_host_control.py`):
  - `rebind(port=…)` with a control-capable child gives `switched`, and the old listener is closed;
  - with a legacy child it gives `unsupported`;
  - if the child never arrives, the result is `rolled_back` and the old listener still serves;
  - the dual-token window expires.
- **Host** (`tests/base_manager/hotpatcher_manager/test_host_control.py`, `test_launch_env.py` additions):
  - `request_control` round trip;
  - feature fallback against a peer without `"control"`;
  - launch env default output unchanged, the new `host`/`token` parameters, and preserved overrides;
  - the unified builders agree on `PYTHONPATH`.
- **Regression.** The full existing suites must pass unchanged. That covers `patcher/tests`, `tests/base_manager/hotpatcher_manager`, the GUI test, `tests/api_server/test_registry.py` (including the assertion that no runtime control exists) and `tests/cli_manager/test_self_manager_patcher.py`.
- **Static checks** on touched files:
  - `ruff check`, `ruff format --check`;
  - `ty check --python <py311>`;
  - `python -m python_docstring_checker .`;
  - the no-`global` test.

---

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Live revert leaves stale references, such as bound methods already captured or closures. | The per-handle report is honest (`requires_restart`); trampoline mode and `rebind_references` are offered and documented. |
| Deadlocks between the control thread and the import lock. | The lock discipline in §3.2 and a concurrency test. |
| Broker thread stall: a heavy command blocks heartbeats. | Bounded handlers, a soft time budget, and documented guidance that heavy imports go through in-process or legacy paths. |
| Scope creep in the GUI and CLI. | Gated by decisions D2 and D3; the Python and wire API is complete without them. |
| `services.py` refactor regressions. | P0 golden snapshots, plus refactoring in small commits. |
| Debug-mode overhead (`ast.dump`, outcome recording). | Outcome counters are always on and cheap; expensive comparisons only run under trace or strict mode. |

---

## 9. Out of scope

- Changing desktop-broker connection parameters from Python.
- A new transport, a TLS layer, or authenticating beyond the existing token and session model.
- Removing the existing `comfyui_auto_port` → `sd_webui_all_in_one.utils` coupling.

---

## 10. Decisions (resolved 2026-11-11: every **bold** default accepted)

| # | Question | Options | Recommended default |
|---|---|---|---|
| D1 | Where does the final as-built document go? | (a) `docs/development/hotpatcher-control.md` plus a nav entry in `zensical.toml` under 开发维护, with the patcher's own `patcher/docs/*` updated alongside; (b) only `sd_webui_all_in_one/patcher/docs/control.md`. | **(a)**, written in Chinese to match the project docs. |
| D2 | Should `--hotpatcher-host` / `--hotpatcher-token` launch flags be added to every product CLI? | Uniform across all products, or env and API only. | **Env and API only** in this change. Uniform CLI flags are a follow-up, because they touch every product CLI, the PS installers and the user docs. |
| D3 | GUI scope | None, minimal (patch list, load/unload, connection panel), or full. | **Minimal**: one "Runtime control" tab built on `request_control`. |
| D4 | Hanafubuki integration | In this change, or a follow-up. | ~~Follow-up~~ → **revised 2026-11-11: in this change, as P11, after P10** (the user finished Hanafubuki development and asked for the phase). |
| D5 | Should `apply_config` revert disabled features? | Opt-in reconcile, or default on. | **Opt-in** (`services.reconcile_disabled: false`). |
| D6 | Remote patch loading | Allowed by default, or gated. | **Gated** (`control.allow_remote_load: false`, non-empty token on legacy). |
| D7 | What "update the hot-patching server's connection parameters" covers | (a) the child's target only; (b) the child's target **and** a host listener rebind while attached. | **(b)**: both, as in §4.6 Layers 2 and 2b. |
