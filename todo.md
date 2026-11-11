# todo: Hotpatcher control plane (temporary)

> Temporary tracking file for [`HOTPATCH_CONTROL_PLAN.md`](HOTPATCH_CONTROL_PLAN.md). Delete it in the final step.
>
> Baseline (2026-11-11, `8e0aa484`): 256 passed with the regression command below.

## Verification commands

```bash
PY=/root/micromamba/envs/py311/bin/python
# Regression (must stay green after every phase)
env PYTHONDONTWRITEBYTECODE=1 $PY -m pytest -q -p no:cacheprovider \
  sd_webui_all_in_one/patcher/tests tests/base_manager/hotpatcher_manager \
  tests/base_manager/gui/test_hotpatcher_manager_gui.py tests/api_server/test_registry.py \
  tests/cli_manager/test_self_manager_patcher.py
# Static checks (on touched paths)
$PY -m ruff check sd_webui_all_in_one && $PY -m ruff format --check sd_webui_all_in_one
$PY -m ty check --python $PY --output-format concise sd_webui_all_in_one
$PY -m python_docstring_checker .
```

## Decisions (resolved 2026-11-11: every recommended default accepted)

- [x] D1 final doc location (recommended: `docs/development/hotpatcher-control.md` + nav, plus patcher docs)
- [x] D2 launch flags for host/token (recommended: env/API only)
- [x] D3 GUI scope (recommended: minimal Runtime control tab)
- [x] D4 Hanafubuki follow-up (recommended: out of scope)
- [x] D5 apply_config reconcile (recommended: opt-in)
- [x] D6 remote patch load gate (recommended: off + token)
- [x] D7 scope of "server connection params" (recommended: child target + host listener rebind)

## P0 Baseline
- [x] Golden snapshot test: `get_default_config()` and static `get_catalog()`
- [x] Snapshot tests: `services.*` response shapes and desktop `config.apply` result
- [x] Invariant test: importing `services` loads no `sd_webui_all_in_one_hotpatcher_ext` modules
- [x] Verify: regression green

## P1 Journal and PatchSet
- [ ] `control/journal.py` (NOTSET, LIFO, isolated, idempotent undo, raw `__dict__` for classes)
- [ ] `control/targets.py` (resolve `pkg.mod:Obj.attr`)
- [ ] `control/handles.py` (PatchHandle, PatchStatus, PatchOutcome, id counter on state)
- [ ] `control/patchset.py` (PatchSet, PatchContext, contextvar, transactional setup)
- [ ] `state.py` fields + lock discipline doc comment
- [ ] Tests: `test_control_journal.py`, `test_control_patchset.py`
- [ ] Verify: regression + static green

## P2 Hook upgrades
- [ ] grep: no caller relies on `patch_*` returning None
- [ ] Thread-local `LoadingSkipper` in hook.py and stack_shadow.py
- [ ] Handles: per-stage parallel id lists + identity search; `remove`, `MonkeyZoo.discard`
- [ ] Ownership: `patch_*` attach handles to the active PatchSet via `current_patch_context()`
- [ ] Finder `invalidate(fullname)` on every plan mutation (L10)
- [ ] State-aware `_spec_from_file_location_wrapper` (L11)
- [ ] Outcome recording in every `eval_*`; strict mode
- [ ] Framework-journaled function/injection/prohibition writes; `revert=` on module/premodule
- [ ] `PostExecLoader` for non-SourceFileLoader specs (L4); `condition=`; `apply_if_loaded`
- [ ] Tests: `test_control_hook_handles.py`
- [ ] Verify: regression + static green

## P3 Live operations
- [ ] attr/item/env/sys.path ops, `wrap` (+trampoline), class members, `rebind_references`, `reload_module`
- [ ] Tests: `test_control_operations.py`
- [ ] Verify

## P4 Feature registry
- [ ] `control/features.py` (FeatureSpec, FeatureRegistry); built-in specs as core data with lazy `"module:callable"` refs (no eager ext imports)
- [ ] Derive DEFAULT_CONFIG / SETTING_SCHEMA / apply / warnings / feature state from registry
- [ ] Per-feature PatchSet; enable/disable/update; opt-in reconcile (D5)
- [ ] Tests: `test_control_features.py` (golden equality, ownership of unmodified extensions, import invariant)
- [ ] Verify

## P5 Runtime loading
- [ ] `control/loader.py`: load (module/file, private name), unload report, reload w/ rollback, update
- [ ] `control.patch_sets` config section + catalog schema
- [ ] `PatchFileWatcher` (stdlib polling, off by default)
- [ ] Remote-load gate (D6)
- [ ] Tests: `test_control_loader.py`
- [ ] Verify

## P6 Debugging
- [ ] `control/trace.py` + `…_TRACE` / `…_TRACE_FILE` env
- [ ] `control/events.py` ring buffer + optional forwarding
- [ ] `control/inspect.py`: explain, source (≤48 KiB), verify, status snapshot
- [ ] Tests: `test_control_debug.py`
- [ ] Verify

## P7 Unified commands
- [ ] `control/commands.py` (CommandSpec, registry, validation, envelopes, error codes)
- [ ] `control/controller.py` + `hotpatch` facade export in `__init__.py`
- [ ] `services.handle_request_json` → shim over dispatch (aliases)
- [ ] `_handle_desktop_command` → dispatch (keep `applyResult`, `unknown_command`)
- [ ] `hotpatch.capabilities` probe + `CONTROL_VERSION`; `hello.features += "control"` (hint only)
- [ ] `CommandSpec.blocking`; blocking commands → `unsupported_transport` on desktop
- [ ] Post-response actions in `ServiceControlChannel`
- [ ] Tests: `test_control_commands.py`, `test_control_concurrency.py`
- [ ] Verify

## P8 Connection
- [ ] `runtime/connection.py` (RuntimeConnectionSettings, ConnectionManager)
- [ ] `RuntimeClient.rebind`; `connect_from_env` on settings
- [ ] Make-before-break update with rollback; services + fault reopen
- [ ] Opt-in reconnect with backoff; desktop read-only
- [ ] Tests: `test_control_connection.py`
- [ ] Verify

## P9 Host side
- [ ] Launch env `host`/`token` params; preserve timeout/trace/strict/reconnect overrides; unify builders
- [ ] Host: capability probe per services channel; `request_control` + wrappers; empty-token non-loopback warning
- [ ] `HotpatcherRuntimeHost.rebind()` (new listener, dual-token window, child update, rollback) (D7)
- [ ] CLI/GUI per D2/D3; API server stays without runtime control
- [ ] Tests: `test_host_control.py`, `test_launch_env.py` additions
- [ ] Verify

## P10 Docs and cleanup
- [ ] Rewrite `HOTPATCH_CONTROL_PLAN.md` as the as-built doc (Chinese) and move it to the D1 location (+ zensical nav)
- [ ] Update patcher `README.md` and `docs/{architecture,services,runtime-protocol,environment-variables,extensions,testing}.md`
- [ ] Add `examples/runtime_patch_load.py`
- [ ] Remove `HOTPATCH_CONTROL_PLAN.md` from the root
- [ ] Final full regression + static checks
- [ ] Delete `todo.md`
