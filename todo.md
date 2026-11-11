# todo: Hotpatcher control plane (temporary)

> Temporary tracking file for the hotpatcher control plane. The as-built design is [`docs/development/hotpatcher-control.md`](docs/development/hotpatcher-control.md); the original plan (`HOTPATCH_CONTROL_PLAN.md`) is in git history at commit `bbaab617`. Delete this file in the final step of P11.
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
- [x] D4 Hanafubuki integration → revised 2026-11-11: in scope as P11 (after P10)
- [x] D5 apply_config reconcile (recommended: opt-in)
- [x] D6 remote patch load gate (recommended: off + token)
- [x] D7 scope of "server connection params" (recommended: child target + host listener rebind)

## P0 Baseline
- [x] Golden snapshot test: `get_default_config()` and static `get_catalog()`
- [x] Snapshot tests: `services.*` response shapes and desktop `config.apply` result
- [x] Invariant test: importing `services` loads no `sd_webui_all_in_one_hotpatcher_ext` modules
- [x] Verify: regression green

## P1 Journal and PatchSet
- [x] `control/journal.py` (NOTSET, LIFO, isolated, idempotent undo, raw `__dict__` for classes)
- [x] `control/targets.py` (resolve `pkg.mod:Obj.attr`)
- [x] `control/handles.py` (PatchHandle, PatchStatus, PatchOutcome, id counter on state)
- [x] `control/patchset.py` (PatchSet, PatchContext, contextvar, transactional setup)
- [x] `state.py` fields + lock discipline doc comment
- [x] Tests: `test_control_journal.py`, `test_control_targets.py`, `test_control_patchset.py`
- [x] Verify: regression + static green (343 passed)

## P2 Hook upgrades
- [x] grep: no caller relies on `patch_*` returning None
- [x] Thread-local `LoadingSkipper` in hook.py and stack_shadow.py
- [x] Handles: per-stage parallel id lists + identity search; `remove`, `MonkeyZoo.discard`
- [x] Ownership: `patch_*` attach handles to the active PatchSet via `current_patch_context()`
- [x] Finder `invalidate(fullname)` on every plan mutation (L10)
- [x] State-aware `_spec_from_file_location_wrapper` (L11)
- [x] Outcome recording in every `eval_*`; strict mode
- [x] Framework-journaled function/injection/prohibition writes; `revert=` on module/premodule
- [x] `PostExecLoader` for non-SourceFileLoader specs (L4); `condition=`; `apply_if_loaded`
- [x] Tests: `test_control_hook_handles.py`, `test_control_hook_loaders.py` (+ `control_hook_test_helpers.py`)
- [x] Verify: regression + static green (389 passed on 3.11; patcher suite 333 passed on 3.10)

## P3 Live operations
- [x] attr/item/env/sys.path ops, `wrap` (+trampoline), class members, `rebind_references`, `reload_module`
- [x] `_undo_entry` heuristic: module/premodule hookers whose every invocation registered owned `ctx.*` ops (and did not raise) report `reverted`; explicit `revert=` wins
- [x] Tests: `test_control_operations.py`
- [x] Verify: regression + static green (419 passed on 3.11; patcher suite 363 passed on 3.10)

## P4 Feature registry
- [x] `control/features.py` (FeatureSpec, FeatureRegistry); built-in specs as core data with lazy `"module:callable"` refs (no eager ext imports)
- [x] Derive DEFAULT_CONFIG / SETTING_SCHEMA / apply / warnings / feature state from registry
- [x] Per-feature PatchSet; enable/disable/update; opt-in reconcile (D5)
- [x] Tests: `test_control_features.py` (golden equality, ownership of unmodified extensions, import invariant); v1 golden subset guard (`golden/*_v1.json`)
- [x] Verify: regression + static green (447 passed on 3.11; patcher suite 391 passed on 3.10)

## P5 Runtime loading
- [x] `control/loader.py`: load (module/file, private name), unload report, reload w/ rollback, update
- [x] `control.patch_sets` config section + catalog schema (one `control` FeatureSpec; GUI gains `json`/`float` kinds)
- [x] `PatchFileWatcher` (stdlib polling, off by default)
- [x] Remote-load gate (D6): `check_remote_load_allowed` defined and tested; P7 wires it into commands
- [x] Tests: `test_control_loader.py` (+ `tests/base_manager/gui/test_hotpatcher_gui_json_field.py`)
- [x] Verify: regression + static green (485 passed on 3.11; patcher suite 429 passed on 3.10; full suite 2058 passed / 13 skipped)

## P6 Debugging
- [x] `control/trace.py` + `…_TRACE` / `…_TRACE_FILE` env
- [x] `control/events.py` ring buffer + optional forwarding (`control.forward_events`, default off, rate-capped)
- [x] `control/inspect.py`: explain, source (≤48 KiB), verify, status snapshot
- [x] Tests: `test_control_debug.py`
- [x] Verify: regression + static green (526 passed on 3.11; patcher suite 459 passed on 3.10; full suite 2088 passed / 13 skipped)

## P7 Unified commands
- [x] `control/commands.py` (CommandSpec, registry, validation, envelopes, error codes)
- [x] `control/controller.py` + `hotpatch` facade export in `__init__.py` (lazy module `__getattr__`; handlers in `control/builtin_commands.py`)
- [x] `services.handle_request_json` → shim over dispatch (aliases)
- [x] `_handle_desktop_command` → dispatch (keep `applyResult`, `unknown_command`)
- [x] `hotpatch.capabilities` probe + `CONTROL_VERSION`; `hello.features += "control"` (hint only; `connect()` already sent `DEFAULT_FEATURES`, not `[]`)
- [x] `CommandSpec.blocking`; blocking commands → `unsupported_transport` on desktop
- [x] Post-response actions in `ServiceControlChannel`
- [x] Gate config-borne `control.patch_sets` / `allow_remote_load` on remote `services.config.apply` and desktop `config.apply` against the pre-request config (D6 bypass found in P5); also remote `services.config.save` and `features.enable/update` for `control`
- [x] Tests: `test_control_commands.py`, `test_control_concurrency.py` (+ `tests/base_manager/hotpatcher_manager/test_host_control_hello.py`)
- [x] Verify: regression + static green (572 passed on 3.11; patcher suite 504 passed on 3.10; full suite 2134 passed / 13 skipped)

## P8 Connection
- [x] P7 review fix: `CommandSpec.transports` allowlist; `services.config.load/save` → `forbidden` on desktop (dispatch + capabilities)
- [x] `runtime/connection.py` (RuntimeConnectionSettings, ConnectionManager, `get_connection_manager`)
- [x] `RuntimeClient.rebind`; `connect_from_env` on settings (parity table test)
- [x] Make-before-break update with rollback; services + fault reopen (`state.fault_channel`, `ServiceControlChannel(endpoint=...)`)
- [x] Opt-in reconnect with backoff (`…_RECONNECT=1`; write failure or services-channel EOF); desktop read-only
- [x] `hotpatch.connection.test/update` commands + facade; `connection.get`/status fed by the manager
- [x] Tests: `test_control_connection.py`
- [x] Verify: regression + static green (667 passed on 3.11; patcher suite 599 passed on 3.10; full suite 2229 passed / 13 skipped)

## P9 Host side
- [x] Flaky fix: `test_legacy_services_channel_end_to_end` asserts `hello` order-independently (300/300 runs)
- [x] Launch env `host`/`token` params; preserve timeout/trace/strict/reconnect overrides (debug vars also without runtime); unify builders (partial env kept, documented merge)
- [x] Host: capability probe per services channel (lazy by default, `auto_probe=True` in the GUI; cached on the channel); `request_control` + wrappers (`host_control.py` mixin); empty-token non-loopback warning
- [x] `HotpatcherRuntimeHost.rebind()` (new listener or token-only on the same listener, dual-token window, child update, commit = old services channel closes, rollback closes the new listener and its connections; no-child move) (D7)
- [x] CLI/GUI per D2/D3: no CLI change; GUI "运行时控制" tab (`hotpatcher_manager_gui/runtime_control.py`); API server stays without runtime control
- [x] Tests: `test_host_control.py` (20/20 runs), `test_launch_env_overrides.py`, `tests/base_manager/gui/test_hotpatcher_gui_runtime_control.py`
- [x] Verify: regression + static green (702 passed on 3.11; patcher suite 599 passed on 3.10; full suite 2264 passed / 13 skipped; ty 13)

## P10 Docs and cleanup
- [x] Rewrite `HOTPATCH_CONTROL_PLAN.md` as the as-built doc (Chinese) and move it to the D1 location (+ zensical nav, `docs/development/index.md` link)
- [x] Update patcher `README.md` and `docs/{architecture,services,runtime-protocol,environment-variables,extensions,testing,import-hook,desktop-broker-protocol}.md`
- [x] Add `examples/runtime_patch_load.py` (+ `examples/greeting_patch.py`)
- [x] Remove `HOTPATCH_CONTROL_PLAN.md` from the root
- [x] Final full regression + static checks
- [x] Verify: regression + static green (702 passed / 13 skipped on 3.11; patcher suite 599 passed on 3.10; full suite 2264 passed / 13 skipped; ruff check + format clean; `zensical build --clean` no issues; ty not run, docs/examples only)
- [ ] (`todo.md` deletion moves to the end of P11)

## P11 Hanafubuki integration (repo: /root/code_workspace/Hanafubuki-dev, branch `hotpatch-control`)
- [ ] Broker: accept `hotpatch.event`; `command_result(session, command_id)` lookup
- [ ] Management: runtime control service (bounded queries, task-shaped mutations), capabilities probe + cache, gating
- [ ] IPC: typed Tauri commands + strict-decoding policy entries + registration
- [ ] Frontend: Runtime control area, `json`/`float` field kinds, en+zh strings
- [ ] Tests: broker, management (real broker + scripted runtime), vitest
- [ ] Docs: backend-spec §8.6, rules docs
- [ ] Verify: `bun run format:check && bun run check && bun run test`
- [ ] Push branch; update the sd-webui-all-in-one as-built doc for the Hanafubuki side
- [ ] Delete `todo.md`
