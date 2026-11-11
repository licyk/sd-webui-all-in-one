# Services 控制层

`sd_webui_all_in_one_hotpatcher.services` 是业务系统接入补丁框架的统一入口。它面向“外部系统需要知道有什么能力、默认配置是什么、如何保存和补齐配置、如何按 JSON 启用功能”的场景。

## 能力边界

services 管理两类能力：

- 核心框架能力：`core.import_hook`、`core.stack_shadow`、`runtime.browser`、`runtime.errors`、`runtime.logs`
- 现有扩展补丁：`extensions.comfyui_auto_port`、`extensions.zluda`、`extensions.extension_index`、`extensions.hf_endpoint_mirror`、`extensions.uv_pip`、`extensions.xformers_cutlass`
- 控制平面：`control`（配置声明的补丁集、补丁文件监视、事件转发）

这些功能不再硬编码在 `services.py` 中，而是由 `control/features.py` 的功能注册表（`FeatureSpec` / `FeatureRegistry`）描述。默认配置、`SETTING_SCHEMA`、目录、规范化、应用和禁用告警都从注册表派生；第三方功能注册后立即出现在这些接口中。内置功能的行为通过 `"module:callable"` 字符串惰性引用扩展代码，因此导入 `services` 不会加载任何 `sd_webui_all_in_one_hotpatcher_ext` 模块。

`apply_config` 默认保持 v1 语义：只负责启用和注册补丁，`enabled=false` 的含义是“不主动注册这个功能”，已经生效的补丁保留并产生告警。每个功能在自己的补丁集 `feature:<key>` 中应用，因此可以撤销：

- `apply_config(config, reconcile=True)` 或配置 `services.reconcile_disabled: true` 会撤销之前已应用、现在被禁用的功能，结果多出 `reconciled` 列表；显式传入的 `reconcile` 优先于配置。
- `control.features.disable_feature(key)` 单独撤销一个功能；仍然生效、无法在线撤销的部分报告 `requires_restart`。

`runtime.browser` 默认是 `{"enabled": false, "mode": "host"}`。`host`
抑制系统浏览器并发送 `browser.open`，`suppress` 只抑制，`passthrough`
保留标准库行为。未知 mode 会在规范化时明确失败。host 模式即使没有
runtime client 也会安全抑制并返回诊断，绝不会回退到系统浏览器。

## Python API

```python
from sd_webui_all_in_one_hotpatcher.services import (
    apply_config,
    get_catalog,
    get_default_config,
    load_config_file,
    normalize_config,
    save_config_file,
)

catalog = get_catalog()
defaults = get_default_config()
config = normalize_config({"extensions": {"hf_endpoint_mirror": {"enabled": True}}})
result = apply_config(config)
```

主要接口：

- `get_catalog()`：返回功能目录、字段元数据、默认值和当前 `monkey_zoo` 注册状态。
- `get_default_config()`：返回完整默认配置副本。
- `normalize_config(config)`：深度补齐默认配置, 已存在用户值不覆盖。
- `load_config_file(path, write_back=True)`：读取 JSON 文件, 补齐缺失默认值, 默认写回。
- `save_config_file(path, config)`：规范化后保存 JSON 文件。
- `apply_config(config, runtime_client=None, reconcile=None)`：按配置启用功能, 返回 `applied/warnings/errors`（开启 reconcile 时另有 `reconciled`）。扩展入口导入失败或抛出异常时记录到 `errors`，不会中断其他功能。
- `handle_request_json(raw, runtime_client=None)`：处理 JSON 请求并返回固定响应对象。它是统一命令注册表上的薄封装，也接受 `hotpatch.*` 控制命令。

## Catalog 字段元数据

`get_catalog()` 返回的 `features` 可直接用于 GUI 或外部管理器自动生成配置界面。每个 feature 以配置路径命名，例如 `core.stack_shadow`、`runtime.logs`、`extensions.zluda`：

```json
{
  "features": {
    "runtime.logs": {
      "title": "运行时日志",
      "description": "把 logging、标准输出和子进程输出采集到 runtime host。",
      "settings": {
        "subprocess": {
          "type": "choice",
          "title": "子进程采集",
          "description": "控制是否包装子进程输出。safe 仅在安全场景启用，force 强制启用。",
          "choices": ["0", "safe", "force"],
          "default": "safe"
        },
        "hook_policy": {
          "type": "choice",
          "title": "Hook 冲突策略",
          "description": "控制日志 hook 被其它软件替换后的处理方式。",
          "choices": ["cooperative", "warn", "reapply"],
          "default": "cooperative"
        },
        "fd_capture": {
          "type": "choice",
          "title": "FD 级捕获",
          "description": "实验性标准流捕获。",
          "choices": ["0", "fallback", "force"],
          "default": "0"
        }
      },
      "default": {},
      "active": false
    }
  },
  "registered_patches": {}
}
```

字段元数据约定：

- `title`：面向用户显示的字段名。
- `description`：字段说明，可作为 tooltip 或辅助说明文字。
- `type`：控件类型提示，当前使用 `bool`、`str`、`int`、`list[str]`、`choice`、`object`。
- `choices`：`type=choice` 时的可选值列表。
- `default`：当前字段的默认配置值，由 `get_catalog()` 从 `get_default_config()` 自动附加。

配置文件格式不受 catalog 元数据影响，仍然只保存真实配置值。未被 catalog 描述的未来字段应由管理器保留在原 JSON 中。

`runtime.errors.include_locals=true` 会在 `error.exception` 的 traceback frame 中附带脱敏后的局部变量 `repr()` 摘要。该项默认关闭, 并会自动脱敏敏感变量名和截断过大的值。

设置类型包括 `bool`、`int`、`float`、`str`、`choice`、`list[str]` 和 `json`（`float` 与 `json` 由 `control` 区段引入，Hotpatcher 管理器 GUI 已支持）。

`runtime.errors.caught_exceptions.enabled=true` 是实验性功能, 会通过 `sys.settrace` 发送
`error.caught_exception` 事件来观察被业务代码 `except` 捕获的异常。该功能默认关闭,
可能明显影响性能, 且不会与已有 debugger、coverage 或 profiler trace function 强行共存。

## 配置补齐

配置文件可以只保存用户改过的部分：

```json
{
  "extensions": {
    "hf_endpoint_mirror": {
      "enabled": true
    }
  }
}
```

`load_config_file(..., write_back=True)` 读取后会补齐 `core`、`runtime.logs`、`extensions.uv_pip` 和其他扩展默认值, 并把完整配置写回文件。补齐规则是深度合并：只有当用户值和默认值都是 object 时才递归合并；用户已有的非 object 值保持原样。

配置文件只支持 UTF-8 JSON object，不支持 YAML/TOML。

## `control` 配置区段

`control` 区段由内置功能 `control` 在全部扩展之后应用：

```json
{
  "services": {"apply_on_bootstrap": true, "reconcile_disabled": false},
  "control": {
    "allow_remote_load": false,
    "patch_sets": [{"source": "my_patches.fix_foo", "name": "fix-foo", "config": {}, "enabled": true}],
    "watch": {"enabled": false, "interval": 1.0},
    "forward_events": false
  }
}
```

- `patch_sets`：随配置加载的补丁模块（点分模块名或 `.py` 文件路径），逐条处理且相互隔离，重复应用幂等；不再列出的条目在开启 reconcile 时卸载，否则保留并告警。
- `allow_remote_load`：是否允许经运行时通道加载补丁代码，默认关闭。远程请求（services 通道、桌面 `config.apply`）不能在同一个请求中开启它并加载新的补丁集。
- `watch`：轮询补丁源文件并自动重新加载，也可用 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_WATCH=1` 开启。
- `forward_events`：把补丁失败、补丁集、功能和连接事件以 `hotpatch.event` 转发给宿主，每秒最多 10 条。

补丁模块的写法与加载语义见 [Hotpatcher 控制平面](https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/development/hotpatcher-control.md)。

## JSON 请求

请求对象固定使用 `type` 和 `payload`：

```json
{"type":"services.defaults.get","payload":{}}
```

v1 支持的请求类型：

- `services.catalog.get`
- `services.defaults.get`
- `services.config.current`
- `services.config.normalize`
- `services.config.load`
- `services.config.save`
- `services.config.apply`

`services.config.current` 返回当前进程最后加载或应用的完整配置。若当前进程尚未记录配置, 返回默认完整配置。

这些类型现在注册在统一命令注册表中（`config.apply` 是 `services.config.apply` 的别名），响应与 v1 字节级一致。同一入口还接受 `hotpatch.*` 控制命令，例如 `hotpatch.capabilities`、`hotpatch.patches.list`、`hotpatch.sets.load`；完整命令表、错误码和传输策略见 [Hotpatcher 控制平面](https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/development/hotpatcher-control.md)。`services.config.load` / `services.config.save` 读写任意文件路径，不对桌面传输开放。

响应格式：

```json
{"ok":true,"payload":{}}
```

失败响应：

```json
{"ok":false,"error":{"code":"unknown_request","message":"..."}}
```

## Runtime 控制通道

services runtime 控制通道使用独立 TCP JSONL 连接，不复用 `RuntimeClient.request()` 所在的同步连接。

`ServiceControlChannel(..., timeout=5)` 保留历史调用形式：`timeout` 是兼容
种子，未单独指定时同时作为 TCP 建连和单次 response write deadline。可以通过
`connect_timeout=` 和 `response_write_timeout=` 分别覆盖，配置值必须是大于零
的有限数字。`channel.open` 和每个 response 写入只在各自的有限 write scope 内
临时设置 socket timeout，成功后恢复之前的 mode。

建连后 socket 在创建 buffered reader 前立即恢复 blocking；后台 worker 的 idle
`readline()` 不使用建连或 response timeout，也没有五秒 idle policy。EOF、reset、不可
恢复 read failure 或 response send failure/timeout 都会 terminal close worker；失败阶段以
`connect/read/decode/handler/response/close` 分类保留在最多 100 条 diagnostics 中。
已断开的 services channel 不会停止完整 runtime host，也不会删除 host 已保留的
browser events。

```python
from sd_webui_all_in_one_hotpatcher.services import install_service_control_channel

channel = install_service_control_channel(client)
```

连接后客户端先发送：

```json
{"type":"channel.open","channel":"services","token":"..."}
```

随后宿主可以向该通道发送 `services.*` 请求和 `hotpatch.*` 控制命令；客户端会返回同样包含 `id` 的响应，便于宿主关联请求。命令以 `legacy` 传输分发，`requires_token` 命令使用该通道的 token 判断；`hotpatch.connection.update` 这类需要在响应之后执行的动作在响应写出后才运行。连接切换会重新打开这条通道（见 [Runtime 通信协议](runtime-protocol.md)）。

bootstrap 自动启用：

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES=1
```

如果配置中包含：

```json
{"services":{"apply_on_bootstrap":true}}
```

`bootstrap.configure_from_env()` 会在加载配置后调用 `apply_config()`。
因此启用的 `runtime.browser` 会在 WebUI 入口脚本执行前注册；初始拦截不依赖
services 远程控制通道。即使通用 `services.apply_on_bootstrap=false`，显式启用的
`runtime.browser` 仍会强制执行这次早期应用。运行时重应用可以改变 mode/client，但已经注册的 wrapper
需要进程重启才能彻底移除。

显式 `desktop_broker` 不创建这条 legacy TCP channel。Rust 通过 broker v2 commands
发送稳定 command ID；Python 端经同一个命令注册表以 `desktop` 传输分发：`config.apply`
保持 v1 契约（`payload.config` 交给同一个 `apply_config()`，结果映射为 `applyResult`），
其他已注册的非阻塞远程命令（例如 `hotpatch.status`、`hotpatch.patches.list`）也可用。
重复 command ID 只重发缓存结果，不重复执行 side effect；过期和未知 command 返回 typed error。详见
[Desktop Broker v2](desktop-broker-protocol.md)。
