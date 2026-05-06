# sd_webui_all_in_one_hotpatcher 架构总览

这份文档面向后续开发者，说明 `src/` 下抽取系统的模块职责、启动路径、数据流和扩展边界。README 讲“怎么用”，这里讲“系统为什么长这样”。

## 顶层目标

`sd_webui_all_in_one_hotpatcher` 要解决三类问题：

1. 在 Python import 阶段给目标模块打补丁。
2. 在需要时隐藏补丁系统或补丁模块的真实加载路径。
3. 通过通用宿主通信协议，把运行时控制和事件交给外部进程。

它刻意不包含具体业务补丁。业务补丁放在 `sd_webui_all_in_one_hotpatcher_ext`，例如当前的 ZLUDA、Extension Index、HF Endpoint Mirror 和 uv Pip 扩展。这个边界很重要：核心框架负责“补丁能力”，扩展负责“补谁、怎么补”。

## 目录结构

```text
src/
  README.md
  sitecustomize.py
  sd_webui_all_in_one_hotpatcher/
    __init__.py
    hook.py
    mutable.py
    stack_shadow.py
    bootstrap.py
    services.py
    exceptions.py
    runtime/
      protocol.py
      transport.py
      client.py
      config.py
      progress.py
      browser.py
      fileops.py
      faults.py
      audit.py
      errors.py
      logs.py
  sd_webui_all_in_one_hotpatcher_ext/
    zluda/
      __init__.py
    extension_index/
      __init__.py
    hf_endpoint_mirror/
      __init__.py
    uv_pip/
      __init__.py
  examples/
  tests/
  docs/
```

## 模块分层

```text
应用 / 扩展
  |
  | 调用 monkey_zoo / runtime client / extension API
  v
sd_webui_all_in_one_hotpatcher_ext/*
  |
  | 注册具体补丁
  v
sd_webui_all_in_one_hotpatcher.hook        sd_webui_all_in_one_hotpatcher.stack_shadow       sd_webui_all_in_one_hotpatcher.runtime
  |                    |                             |
  | import-time patch  | traceback filename hiding   | host control plane
  v                    v                             v
Python import system   Python loader/compile          TCP JSONL host
```

### `sd_webui_all_in_one_hotpatcher.hook`

核心 import hook。它维护全局 `monkey_zoo`，在 `sys.meta_path` 里插入 finder，命中目标模块时替换 loader，并在模块执行前后应用补丁。

关键对象：

- `Monkey`：一个目标模块的补丁计划。
- `MonkeyZoo`：模块名到 `Monkey` 的注册表。
- `HookedMetaPathFinder`：拦截 import 查询。
- `MonkeySourceFileLoader`：真正执行源码/AST/字节码/模块对象补丁。

### `sd_webui_all_in_one_hotpatcher.mutable`

提供 `CodeWrapper` 和 `TupleWrapper`，用于修改不可变的 code object。典型用途是替换 `co_consts` 中的字符串常量或嵌套 code object。

### `sd_webui_all_in_one_hotpatcher.stack_shadow`

可选的栈隐藏层。它不是业务补丁，也不是 runtime 通信。它只改变被选中模块编译时的 `co_filename`，让 traceback 不暴露真实文件路径或 zip 路径。

### `sd_webui_all_in_one_hotpatcher.runtime`

通用宿主通信层。当前协议是 TCP + JSON Lines。它包含：

- 传输层：`JsonlTcpTransport`
- 高层 client：`RuntimeClient`
- 配置：`load_config`
- 控制能力：progress、browser、fileops、faults、audit、errors、logs

### `sd_webui_all_in_one_hotpatcher.bootstrap`

环境变量驱动启动器。它把“是否启用 stack shadow / import hook / runtime client / config”集中到一个入口：

```python
from sd_webui_all_in_one_hotpatcher.bootstrap import configure_from_env

state = configure_from_env()
```

这个模块使用懒导入。原因是：如果用户想隐藏 `sd_webui_all_in_one_hotpatcher.*`，就必须先安装 stack shadower，再导入 hook/runtime 等更重的模块。

### `sd_webui_all_in_one_hotpatcher.services`

业务系统接入层。它提供补丁能力目录、默认配置、配置文件补齐、JSON 请求处理和可选 runtime services 控制通道。services 会调用 core 和扩展入口启用功能，但 v1 不负责撤销已经注册的 import-time 补丁。

### `src/sitecustomize.py`

可选自动启动入口。Python 启动时会自动导入路径上的 `sitecustomize`。当前实现只有在存在 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_*` 环境变量时才调用 bootstrap，避免无配置时产生副作用。

## 启动路径

### 显式调用

最推荐的开发方式：

```python
from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo

install_import_hook()
with monkey_zoo("target") as monkey:
    ...

import target
```

优点是可见、可测试、可控。

### 环境变量 + bootstrap

适合注入式启动：

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_IMPORT_HOOK=1 \
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW=1 \
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW_PREFIXES=sd_webui_all_in_one_hotpatcher,my_patches \
PYTHONPATH=src python app.py
```

如果 `src/sitecustomize.py` 在 `PYTHONPATH` 中，它会调用 `configure_from_env()`。

### 扩展模块入口

扩展模块应自己安装 import hook。例如 ZLUDA 扩展：

```python
from sd_webui_all_in_one_hotpatcher_ext.zluda import apply_zluda_compat

apply_zluda_compat()
import torch
```

扩展入口内部调用 `install_import_hook()`，使用者不需要记住额外步骤。

## 关键数据流

### Import-time patch 数据流

```text
用户注册 monkey_zoo("target")
  -> install_import_hook()
  -> import target
  -> HookedMetaPathFinder.find_spec("target")
  -> 原始 importlib 找到 target spec
  -> loader 替换为 MonkeySourceFileLoader
  -> get_code(): source/AST/bytecode patch
  -> exec_module(): premodule/import injection/exec/function/module patch
  -> target 进入 sys.modules
```

### Runtime 数据流

```text
RuntimeClient.connect(host, port)
  -> TCP connect
  -> 发送 hello JSONL
  -> event(): 只发不等
  -> request(): 发送带 id 的请求并等待同 id 响应
```

### Fault channel 数据流

```text
install_faulthandler(client)
  -> 新建第二条 TCP 连接
  -> 发送 {"type":"channel.open","channel":"fault"}
  -> socket file 交给 faulthandler.enable()
  -> fatal crash 时 Python faulthandler 写入该 raw channel
```

## 状态管理

`sd_webui_all_in_one_hotpatcher` 有几处进程级全局状态：

- `sys.meta_path`：import hook finder 和 stack shadow finder 都会插入这里。
- `importlib.util.spec_from_file_location`：import hook 会包装这个函数。
- `monkey_zoo`：保存目标模块补丁计划。
- runtime exception reporter：`exceptions.set_exception_reporter()` 设置全局 reporter。
- `Progress.manager`：进度上报的全局 manager。

测试和嵌入式环境中必须清理这些状态，否则用例之间会串味。

## 与原系统的差异

原系统是面向 Stable Diffusion/WebUI 的一整套增强运行时，包含具体业务补丁、旧 Windows named pipe 协议、Sentry、A1111/ComfyUI 适配等。

抽取后的系统只保留通用机制：

- import-time patch
- stack shadow
- runtime host protocol
- extension API

具体业务补丁移到 `sd_webui_all_in_one_hotpatcher_ext`。当前已有 ZLUDA、Extension Index、HF Endpoint Mirror 和 uv Pip 作为样例。

## 后续扩展建议

新增能力时优先按这个顺序判断放置位置：

1. 纯补丁机制：放 `sd_webui_all_in_one_hotpatcher` core。
2. 宿主通信能力：放 `sd_webui_all_in_one_hotpatcher.runtime`。
3. 某个库/项目的具体补丁：放 `sd_webui_all_in_one_hotpatcher_ext/<name>`。
4. 测试工具或示例：放 `tests` / `examples`，不要塞进 core。

这个边界能让核心保持小而稳，让具体补丁像插件一样增长。挺朴素，但很抗乱。
