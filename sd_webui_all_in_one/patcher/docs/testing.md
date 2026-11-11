# 测试指南

这份文档说明如何测试 `sd_webui_all_in_one_hotpatcher` 的 import hook、stack shadow、runtime 和扩展模块。重点不是 pytest 语法，而是这些全局 hook 系统如何避免测试污染。

## 推荐命令

```bash
env PYTHONDONTWRITEBYTECODE=1 /root/micromamba/envs/py311/bin/python -m pytest sd_webui_all_in_one/patcher/tests
```

`PYTHONDONTWRITEBYTECODE=1` 可以避免生成 `__pycache__`，保持工作区清爽。

## 测试文件职责

测试按被测模块分目录存放。`tests/` 及其子目录都不是 Python 包（没有 `__init__.py`），pytest 以文件名导入测试模块，所以**所有测试文件和辅助模块的文件名必须全局唯一**，辅助模块使用 `<主题>_test_helpers.py` 命名。

```text
tests/conftest.py
  把 patcher 根目录加入 sys.path。

tests/core/
  test_hotpatcher_hook.py          import hook 核心能力
  test_hotpatcher_state.py         核心模块不使用 global 语句
  test_stack_shadow.py             traceback filename 隐藏，source/zip loader，env bootstrap

tests/services/
  test_services_config.py          默认配置、配置合并、配置文件、catalog、请求处理
  test_services_apply.py           apply_config 启用核心补丁与扩展补丁
  test_services_bootstrap.py       服务控制通道与 bootstrap
  test_services_golden_snapshot.py get_default_config() / 静态 get_catalog() 的 golden 快照 (golden/*.json)
  test_services_golden_v1_subset.py 当前输出必须是 P0 快照 golden/*_v1.json 的深度超集 (只允许新增)
  test_services_wire_compat.py     services.* 响应结构与错误码的线上兼容
  test_services_import_invariant.py 导入 services 不加载任何扩展模块

tests/control/
  control_hook_test_helpers.py     import hook 句柄测试的临时模块与清理工具
  test_control_journal.py          PatchJournal: NOTSET、描述符、LIFO、失败隔离、幂等撤销
  test_control_targets.py          目标路径解析
  test_control_patchset.py         PatchSet 事务、disposer、嵌套与报告
  test_control_hook_handles.py     import 阶段句柄、归属、撤销状态、finder 缓存失效、严格模式、outcome
  test_control_hook_loaders.py     PostExecLoader、条件补丁、apply_if_loaded、spec_from_file_location 状态
  test_control_operations.py       实时操作、蹦床、rebind_references、reload_module
  test_control_features.py         功能注册表、扩展归属与撤销、reconcile、第三方功能
  test_control_loader.py           运行时加载/卸载/重新加载/更新、control 配置区段、文件监视、远程加载门禁
  test_control_debug.py            跟踪、事件日志与转发、explain/source/verify/status
  test_control_commands.py         命令注册表、传输策略、envelope、capabilities、门面、D6 配置门禁
  test_control_concurrency.py      控制线程与导入线程并发、线程本地 LoadingSkipper、桌面阻塞命令
  test_control_connection.py       连接切换、回滚、重连、非回环限制、脱敏

tests/runtime/
  runtime_test_helpers.py          JsonlHost 等 runtime 测试宿主
  test_runtime_client.py           TCP JSONL、config、progress、browser、fileops、faults、audit
  test_runtime_errors.py           异常上报与 error capture
  test_runtime_caught_exceptions.py  已捕获异常追踪
  test_runtime_logs.py             日志采集
  test_runtime_bootstrap.py        runtime bootstrap
  test_transport_mode.py           传输模式选择
  legacy_transport_test_helpers.py / test_legacy_*.py
                                   旧版 JSONL 传输超时与服务通道
  desktop_broker_test_helpers.py / test_desktop_broker_*.py
                                   桌面端代理 HTTP、事件队列、诊断、命令与 bootstrap
  test_desktop_command_compat.py   桌面 config.apply 的 applyResult 映射与错误码兼容

tests/extensions/
  test_extension_package_layout.py 扩展包结构与公开 API
  test_<扩展名>_extension.py       各扩展测试，例如 ZLUDA、Extension Index、HF Endpoint Mirror、uv Pip
```

宿主侧的控制测试在仓库根目录的 `tests/` 中：`tests/base_manager/hotpatcher_manager/`（`test_host_control.py`、`test_host_control_hello.py`、`test_launch_env_overrides.py` 等）和 `tests/base_manager/gui/`（`test_hotpatcher_gui_runtime_control.py`、`test_hotpatcher_gui_json_field.py`）。

## Golden 快照

`tests/services/golden/default_config.json` 和 `catalog_static.json` 冻结默认配置与目录静态部分（含键顺序，去掉 `active` / `registered` 这类依赖进程状态的字段）。有意修改默认配置或 schema（例如新增 `FeatureSpec` 或设置字段）时重新生成并检查差异：

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_REGEN_GOLDEN=1 python -m pytest sd_webui_all_in_one/patcher/tests/services/test_services_golden_snapshot.py
```

`*_v1.json` 是控制平面改造前的快照，不要重新生成；`test_services_golden_v1_subset.py` 用它保证改动只新增内容。

## Python 3.10

patcher 核心需要兼容 Python 3.10（CI 覆盖 3.10 到 3.15），修改 `control/`、`runtime/` 或 `hook.py` 后再用 3.10 跑一次 patcher 测试，例如：

```bash
uv run --no-project --python 3.10 --with pytest python -m pytest -q -p no:cacheprovider sd_webui_all_in_one/patcher/tests
```

## 测试 import hook 的固定套路

Import hook 测试通常这样写：

```python
@pytest.fixture(autouse=True)
def clean_import_state():
    uninstall_import_hook()
    monkey_zoo.clear()
    before_path = list(sys.path)
    yield
    uninstall_import_hook()
    monkey_zoo.clear()
    sys.path[:] = before_path
    for name in list(sys.modules):
        if name.startswith("hp_target_"):
            sys.modules.pop(name, None)
```

关键点：

- 测试前卸载 hook，避免上个测试留下 finder。
- 清理 `monkey_zoo`。
- 保存并恢复 `sys.path`。
- 清理临时目标模块的 `sys.modules`。

否则 import 系统会非常“记仇”：目标模块一旦进入 `sys.modules`，后续 import 不会重新触发 loader。

## 临时模块测试

用 `tmp_path` 写出临时 `.py` 文件：

```python
def write_module(module_dir, name, source):
    path = module_dir / f"{name}.py"
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    importlib.invalidate_caches()
    return path
```

然后：

```python
sys.path.insert(0, str(tmp_path))
install_import_hook()
with monkey_zoo("hp_target") as monkey:
    ...
module = importlib.import_module("hp_target")
```

这种方式比 monkeypatch 内存对象更接近真实 import 流程。

## source patch 测试

断言最终执行结果，不要只断言 patch 函数被调用：

```python
def patch_source(source, filename):
    return source.replace('"before"', '"after"')


monkey.patch_sources(patch_source)
module = importlib.import_module("hp_target_source")
assert module.VALUE == "after"
```

这样可以覆盖读取源码、替换源码、parse、compile、exec 的完整链路。

## bytecode patch 测试

使用简单常量：

```python
def patch_bytecode(code):
    code.co_consts.replace_primitive("old", "new")
```

先验证常量替换，再考虑嵌套 code object。字节码测试最好保持小，太复杂会让失败原因很难读。

## `spec_from_file_location` 测试

动态文件加载路径要单独测：

```python
spec = importlib.util.spec_from_file_location("hp_target_dynamic", module_path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
```

这是为了确认 `install_import_hook()` 包装的 `spec_from_file_location` 生效。

## Stack shadow 测试

source loader 测试：

1. 写一个会抛异常的临时模块。
2. 安装 `install_stack_shadower("shadow_source_target", "<hidden {name}>")`。
3. import 模块并调用抛错函数。
4. 用 `traceback.format_exception()` 检查 traceback。

断言：

- 包含 `<hidden shadow_source_target>`。
- 不包含真实临时文件路径。

zip loader 测试类似，只是把模块写进 zip，然后把 zip 路径插入 `sys.path`。

## Runtime 测试

`runtime/runtime_test_helpers.py` 里的 `JsonlHost` 是一个最小测试宿主：

- 后台线程开 TCP server。
- 每个连接一个 handler 线程。
- 收到每条 JSONL 放进 `messages`。
- 如果消息带 `id`，按 `responses` 返回响应。

它能覆盖：

- hello 握手
- request/response
- event
- raw fault channel 第一行握手

测试 event 时用：

```python
assert host.wait_for(lambda message: message.get("type") == "progress.update")
```

因为 event 是 best-effort 发送，线程处理有一点异步性。

## File operation 测试

文件操作要覆盖成功和取消。

取消响应：

```python
{"file.delete": {"ok": False, "error": {"code": "cancelled", "message": "user cancelled"}}}
```

客户端应抛 `UserCanceledException`。

这个映射是文件操作 API 的关键语义，不要只测成功路径。

## Fault channel 测试

不要在测试里制造真实崩溃。当前只验证：

- `install_faulthandler(client, enable=False)` 会打开第二条 TCP 连接。
- 第一行 JSON 是 `channel.open`。
- `channel` 为 `fault`。
- token 正确。

这足够验证协议，不会让测试环境变成现场事故模拟器。

## Audit 测试

Python audit hook 不能卸载，所以测试必须使用专用事件名：

```python
install_audit_hook(client, ["sd_webui_all_in_one_hotpatcher.test_event"])
sys.audit("sd_webui_all_in_one_hotpatcher.test_event", "payload")
```

不要用常见事件名做全局测试，否则后续测试中的 import/compile 都可能触发事件，日志会像开了小喇叭。

## Error reporter 测试

异常上报有两条路径：

1. 显式传异常对象：

```python
capture_exception(ValueError("bad value"))
```

2. 在 except 块中不传参数：

```python
try:
    raise RuntimeError("from except")
except RuntimeError:
    capture_exception()
```

测试要断言：

- 宿主收到 `error.exception`。
- payload 包含 type/name/message/traceback/process。
- `capture_exception()` 仍然会打印 stderr。

## Log capture 测试

日志采集会 patch 多个进程级对象，测试必须在前后调用 `uninstall_log_capture()`：

```python
@pytest.fixture(autouse=True)
def clean_runtime_state():
    uninstall_log_capture()
    yield
    uninstall_log_capture()
```

需要覆盖四类行为：

- `logging`：安装后 root handler 能发送 `log.record`，默认排除 `sd_webui_all_in_one_hotpatcher.*`。
- `stdout/stderr`：`StreamTee` 发送 `log.stream`，同时原 stream 仍能被 `capsys` 捕获。
- `subprocess=safe`：只捕获 `capture_output=True` 或显式 `PIPE` 的输出，不强制接管继承输出。
- `subprocess=force`：未指定 stdout/stderr 的子进程输出会被捕获、写回父进程原 stream，并发送 `log.stream`。
- `hook_policy`：预先存在的第三方 hook 应被协作式包装；安装后被替换时，`warn` 发送 `log.hook_status(status="lost")`，`reapply` 重新包装并发送 `status="reapplied"`。
- `fd_capture`：只测试显式 `force` 或可控 fallback 场景；不支持 fd 的环境应断言安全跳过或收到 `unsupported/error` 状态。

策略测试：

- `bounded` 下超长文本会截断并设置 `truncated=true`。
- `raw` 下文本不截断。
- 队列满时发送 `log.dropped`。这个测试最好用 fake transport 阻塞第一条发送，让队列稳定达到满载状态。

注意：同时开启 logging handler 和 stderr tee 时，一条 logging 可能既有 `log.record` 也有 `log.stream`。测试应分别断言目标事件，不要假设全局只有一条日志。

## 扩展模块测试

扩展不要依赖真实大库。以 ZLUDA 为例，测试创建 fake torch：

```text
tmp/
  torch/
    __init__.py
    backends/
      cuda.py
      cudnn.py
    utils/
      cpp_extension.py
```

然后调用扩展入口，import fake torch，断言补丁效果。

这样测试不依赖 GPU、不依赖 Windows、不依赖真实 torch，速度也很体面。

uv Pip 这种运行时 wrapper 不需要 fake import 目标。测试直接替换 `subprocess.run` 为 fake 函数，断言 Pip 命令被改写为 `uv pip`，非 Pip 命令保持原样，并验证第三方后续替换 `subprocess.run` 时卸载逻辑不会覆盖它。

## 新增测试 checklist

新增测试时确认：

- 是否清理 `sys.modules`。
- 是否清理 `monkey_zoo`。
- 是否卸载 import hook / stack shadower。
- 是否恢复 `sys.path`。
- 是否避免真实网络端口冲突，使用系统分配端口。
- 是否避免不可卸载的全局 hook 污染后续测试。
- 是否用 `PYTHONDONTWRITEBYTECODE=1` 避免 pyc。
- 是否使用隔离的 `HotpatcherState()`，或在结束时卸载测试创建的补丁集、关闭补丁文件监视器、停止跟踪。
- 控制平面测试文件是否使用 `test_control_*` 前缀，保持文件名全局唯一。
