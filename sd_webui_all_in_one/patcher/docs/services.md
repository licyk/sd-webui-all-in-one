# Services 控制层

`sd_webui_all_in_one_hotpatcher.services` 是业务系统接入补丁框架的统一入口。它面向“外部系统需要知道有什么能力、默认配置是什么、如何保存和补齐配置、如何按 JSON 启用功能”的场景。

## 能力边界

services 管理两类能力：

- 核心框架能力：`core.import_hook`、`core.stack_shadow`、`runtime.logs`
- 现有扩展补丁：`extensions.zluda`、`extensions.extension_index`、`extensions.hf_endpoint_mirror`、`extensions.uv_pip`

v1 只负责启用和注册补丁，不负责撤销已经注册或已经生效的 import-time 补丁。`enabled=false` 的含义是“不主动注册这个功能”。

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
- `apply_config(config, runtime_client=None)`：按配置启用功能, 返回 `applied/warnings/errors`。
- `handle_request_json(raw, runtime_client=None)`：处理 JSON 请求并返回固定响应对象。

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

## JSON 请求

请求对象固定使用 `type` 和 `payload`：

```json
{"type":"services.defaults.get","payload":{}}
```

支持的请求类型：

- `services.catalog.get`
- `services.defaults.get`
- `services.config.normalize`
- `services.config.load`
- `services.config.save`
- `services.config.apply`

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

```python
from sd_webui_all_in_one_hotpatcher.services import install_service_control_channel

channel = install_service_control_channel(client)
```

连接后客户端先发送：

```json
{"type":"channel.open","channel":"services","token":"..."}
```

随后宿主可以向该通道发送 `services.*` 请求；客户端会返回同样包含 `id` 的响应，便于宿主关联请求。

bootstrap 自动启用：

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES=1
```

如果配置中包含：

```json
{"services":{"apply_on_bootstrap":true}}
```

`bootstrap.configure_from_env()` 会在加载配置后调用 `apply_config()`。
