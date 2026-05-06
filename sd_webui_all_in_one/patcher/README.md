# sd_webui_all_in_one_hotpatcher 使用文档

`sd_webui_all_in_one_hotpatcher` 是一个通用的 Python import-time 热补丁框架。它从当前项目的补丁系统中抽出核心能力，并额外提供可选的栈隐藏、宿主通信和运行时控制能力。它不绑定 Automatic1111、ComfyUI 或旧 Windows named pipe 协议，可以复制到其他项目里使用。

## 开发文档导航

README 面向快速理解和接入；更细的架构、实现原理、扩展开发和测试维护说明放在 `src/docs/`：

- [架构总览](docs/architecture.md)：模块边界、启动路径、核心数据流。
- [Import Hook 原理](docs/import-hook.md)：`sys.meta_path`、finder/loader、补丁执行顺序和边界。
- [栈隐藏机制](docs/stack-shadow.md)：traceback filename 伪装、source/zip loader 支持和环境变量。
- [Runtime 通信协议](docs/runtime-protocol.md)：TCP JSONL、请求/响应、事件、fault raw channel 和日志采集。
- [Services 控制层](docs/services.md)：业务系统查询补丁能力、读取字段元数据、补齐配置、应用配置和 runtime 控制通道。
- [扩展模块开发](docs/extensions.md)：如何编写 `sd_webui_all_in_one_hotpatcher_ext` 扩展，含 ZLUDA 示例。
- [测试指南](docs/testing.md)：现有测试覆盖、fixture 约定、常见测试模式。

## 快速开始

把 `src` 加入 `PYTHONPATH`，或者把 `src/sd_webui_all_in_one_hotpatcher` 复制到你的项目中：

```bash
PYTHONPATH=src python your_app.py
```

最小示例：

```python
from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo

install_import_hook()

with monkey_zoo("some_package.some_module") as monkey:
    def patch_func(func, module):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            return f"patched: {result}"

        return wrapper

    monkey.patch_function("target_function", patch_func)

import some_package.some_module
```

补丁必须在目标模块第一次 import 之前注册。目标模块已经在 `sys.modules` 里时，普通 import hook 不会重新执行模块代码。

## 工作原理

Python 的 `import` 流程会查询 `sys.meta_path` 中的 finder。`sd_webui_all_in_one_hotpatcher.install_import_hook()` 会把一个自定义 finder 插到 `sys.meta_path` 前面。

当某个模块被 import 时：

1. finder 检查该模块名是否在 `monkey_zoo` 中注册过补丁。
2. 如果命中，finder 找到原始 module spec，并把原始 loader 换成 `MonkeySourceFileLoader`。
3. loader 在执行模块代码前后应用补丁。
4. 模块执行完成后，Python 正常把模块放入 `sys.modules`。

补丁执行顺序：

1. `patch_sources()`：读取 `.py` 文件源码后，编译前替换源码字符串。
2. `patch_ast()`：源码 parse 成 AST 后，编译前修改 AST。
3. `patch_bytecode()`：编译或读取 code object 后，修改字节码常量等结构。
4. `patch_premodule()`：模块代码执行前修改 module 对象。
5. `inject_import()`：模块代码执行前注入外部模块、函数或对象。
6. 执行原模块代码。
7. `patch_function()`：模块执行后替换模块顶层函数。
8. `patch_module()`：模块执行后对 module 对象做任意修改。
9. `prohibit_output()`：屏蔽整个模块或指定函数的标准输出。

框架还会包装 `importlib.util.spec_from_file_location()`，因此通过文件路径动态加载的模块也可以应用已注册补丁。

## API

### 安装和卸载

```python
from sd_webui_all_in_one_hotpatcher import install_import_hook, uninstall_import_hook

install_import_hook()
uninstall_import_hook()
```

`install_import_hook()` 是幂等的，多次调用不会重复插入 finder。

`uninstall_import_hook()` 会移除 finder，并恢复 `importlib.util.spec_from_file_location()`。

### 注册模块补丁

```python
from sd_webui_all_in_one_hotpatcher import monkey_zoo

with monkey_zoo("package.module") as monkey:
    ...
```

模块名大小写会用 `casefold()` 归一化。只有 `Monkey` 中至少注册了一个补丁动作时，它才会被保存。

### 替换函数

```python
with monkey_zoo("target") as monkey:
    def patch_run(func, module):
        def wrapper(*args, **kwargs):
            print("before")
            return func(*args, **kwargs)

        return wrapper

    monkey.patch_function("run", patch_run)
```

`patch_function(name, hooker, priority=100, add_if_not_exists=False)` 的 `hooker` 接收原函数和 module 对象。返回 `None` 表示不替换。

如果 `add_if_not_exists=True`，即使模块里不存在该名字，也会调用 hooker；这可以用于给模块新增函数。

### 修改模块对象

```python
with monkey_zoo("target") as monkey:
    def patch_module(module):
        module.ENABLED = True

    monkey.patch_module(patch_module)
```

`patch_module()` 在原模块代码执行完成之后运行，适合改常量、类属性、字典映射等。

### 修改源码

```python
with monkey_zoo("target") as monkey:
    def patch_source(source, filename):
        return source.replace("OLD_VALUE", "NEW_VALUE")

    monkey.patch_sources(patch_source)
```

源码补丁发生在编译前。它适合小范围兼容修复，但字符串替换比较脆弱，建议只替换非常明确的片段。

### 修改 AST

```python
import ast

class Transformer(ast.NodeTransformer):
    def visit_Constant(self, node):
        if node.value == "old":
            return ast.copy_location(ast.Constant("new"), node)
        return node

with monkey_zoo("target") as monkey:
    monkey.patch_ast(Transformer())
```

AST 补丁比源码字符串替换更结构化，但实现成本更高。

### 修改字节码常量

```python
with monkey_zoo("target") as monkey:
    def patch_code(code):
        code.co_consts.replace_primitive("old", "new")

    monkey.patch_bytecode(patch_code)
```

`patch_bytecode()` 接收 `CodeWrapper`。它可以替换 `co_consts` 等 code object 字段，最后通过 `code.replace()` 生成新的 code object。

### 注入 import

```python
with monkey_zoo("target") as monkey:
    monkey.inject_import("math", "sqrt")
```

这会在目标模块执行前把 `sqrt` 注入目标模块的全局命名空间。

### 模块别名 fallback

```python
monkey_zoo.alias_if_not_exists("old_name", "new_name")
```

当 `old_name` 无法正常 import 时，框架会 fallback 到 `new_name`。这适合处理包名迁移或 vendor 包 fallback。

## 示例

示例位于 `src/examples`。

函数包装：

```bash
PYTHONPATH=src python -m examples.function_patch
```

源码替换：

```bash
PYTHONPATH=src python -m examples.source_patch
```

字节码常量替换：

```bash
PYTHONPATH=src python -m examples.bytecode_patch
```

栈隐藏演示：

```bash
PYTHONPATH=src python -m examples.stack_shadow_demo
```

宿主通信演示需要两个终端：

```bash
PYTHONPATH=src python -m examples.runtime_host
```

```bash
PYTHONPATH=src python -m examples.runtime_client
```

## 扩展模块

可选扩展放在 `src/sd_webui_all_in_one_hotpatcher_ext`，用于承载从原项目抽出的具体补丁配方。核心 `sd_webui_all_in_one_hotpatcher` 只负责补丁机制，扩展模块负责“补谁、怎么补”。

### ZLUDA 扩展

ZLUDA 扩展位于 `sd_webui_all_in_one_hotpatcher_ext.zluda`，抽自原来的 `swlpatches/zluda_companion.py`，并额外包含原 `torch_zluda_timer` hotfix。

```python
from sd_webui_all_in_one_hotpatcher_ext.zluda import apply_zluda_compat, apply_zluda_library

apply_zluda_compat()
apply_zluda_library("C:/path/to/zluda")

import torch
```

也可以通过配置对象启用：

```python
from sd_webui_all_in_one_hotpatcher_ext.zluda import apply_from_config

apply_from_config({
    "compat": True,
    "path": "C:/path/to/zluda",
    "torch_zluda_timer": True,
})
```

能力：

- `apply_zluda_library(path)`：在 `torch` 执行模块代码前加载指定目录下的 ZLUDA DLL。
- `apply_zluda_compat()`：禁用 `torch.backends.cudnn.enabled`、flash SDP 和 memory efficient SDP，强制相关开关保持 `False`。
- `apply_torch_zluda_timer_hotfix()`：源码 patch `torch.utils.cpp_extension`，修复 ZLUDA/Windows timer build 相关逻辑。

`apply_zluda_library()` 是 Windows/ZLUDA 场景专用；在非 Windows 上启用并导入 `torch` 会抛出明确错误。

### 扩展索引镜像扩展

扩展索引镜像扩展位于 `sd_webui_all_in_one_hotpatcher_ext.extension_index`，抽自原来的 `swlpatches/extension_index.py`。

```python
from sd_webui_all_in_one_hotpatcher_ext.extension_index import (
    patch_extension_index_a1111,
    patch_extension_index_comfyui_manager,
)

patch_extension_index_a1111("https://mirror.example/extensions.json")
patch_extension_index_comfyui_manager()
```

也可以通过配置对象启用：

```python
from sd_webui_all_in_one_hotpatcher_ext.extension_index import apply_from_config

apply_from_config({
    "extension_index_url": "https://mirror.example/extensions.json",
    "comfyui_manager": True,
})
```

能力：

- `patch_extension_index_a1111(url)`：把 A1111/Forge/Vladmandic 扩展索引常量替换为指定 URL。
- `patch_extension_index_comfyui_manager()`：把 ComfyUI-Manager 默认 GitHub raw 地址改到镜像地址，并 patch `get_data()` 运行时入参。
- `apply_from_config(config)`：按配置启用上述补丁。

这些补丁仍然是 import-time patch，必须在 `modules.ui_extensions` 或 `ComfyUI-Manager` 目标模块加载前调用。

### HF Endpoint 镜像扩展

HF Endpoint 镜像扩展位于 `sd_webui_all_in_one_hotpatcher_ext.hf_endpoint_mirror`，抽自原来的：

- `swlpatches/hfmirror/comfyui_wd14_tagger.py`
- `swlpatches/hfmirror/torchhub.py`
- `swlpatches/hfmirror/torchvision.py`
- 自定义的 SD WebUI `modules.util.load_file_from_url` 补丁

抽取版不再使用原项目的 spec/cache/link-or-copy 机制，而是在下载函数入口做 URL 重写。镜像源只从 `HF_ENDPOINT` 环境变量读取：

```bash
HF_ENDPOINT=https://hf-mirror.example
```

使用方式：

```python
from sd_webui_all_in_one_hotpatcher_ext.hf_endpoint_mirror import apply_mirror

apply_mirror()
```

能力：

- patch `torch.hub.download_url_to_file(url, dst, ...)`
- patch `torchvision.datasets.utils._urlretrieve(url, fpath, ...)`
- patch `ComfyUI-WD14-Tagger.pysssss.download_to_file(url, dst, ...)`
- replace `modules.util.load_file_from_url(url, *, model_dir, ...)`

规则：

- `https://huggingface.co/user/repo/resolve/main/file.bin` 会替换为 `{HF_ENDPOINT}/user/repo/resolve/main/file.bin`。
- 未设置 `HF_ENDPOINT`、`HF_ENDPOINT` 为空、`HF_ENDPOINT` 不是完整 URL、或下载 URL 的真实 host 不是 `huggingface.co` 时不做替换。
- wrapper 在函数调用时读取 `HF_ENDPOINT`，所以运行期间修改环境变量会影响之后的下载调用。
- `modules.util.load_file_from_url` 的替换实现会保留缓存命中、临时文件下载、`hash_prefix` 校验和失败清理逻辑，但不再依赖 `shared.hf_endpoint`。

### uv Pip 替换扩展

uv Pip 替换扩展位于 `sd_webui_all_in_one_hotpatcher_ext.uv_pip`，由原来的 `sdaio_patcher/sdaio_patches/uv_patch.py` 迁移而来。

```python
from sd_webui_all_in_one_hotpatcher_ext.uv_pip import patch_uv_to_subprocess

patch_uv_to_subprocess()
```

也可以通过配置对象启用：

```python
from sd_webui_all_in_one_hotpatcher_ext.uv_pip import apply_from_config

apply_from_config({
    "enabled": True,
    "symlink": False,
})
```

能力：

- 包装当前进程的 `subprocess.run()`。
- 当命令中包含 `pip` / `pip.exe` / `pip3` / `pip3.exe` 时，改写为 `uv pip ...`。
- 自动移除 `--prefer-binary`、`--ignore-installed`、`-I` 这类不适合直接传给 `uv pip` 的参数。
- `symlink=true` 时添加 `--link-mode symlink`。

这个补丁是运行时 wrapper，不依赖 import hook。它会包住已经存在的 `subprocess.run` wrapper；卸载时只恢复自己仍持有的 wrapper，避免覆盖后来安装的第三方 hook。

## 栈隐藏

`sd_webui_all_in_one_hotpatcher.stack_shadow` 可以在目标模块 import 时重新编译源码，并把 code object 的 `co_filename` 替换成伪装后的名字。这样异常 traceback 不再暴露真实文件路径或 zip 包路径。

显式启用：

```python
from sd_webui_all_in_one_hotpatcher import install_stack_shadower

install_stack_shadower(
    prefixes=["sd_webui_all_in_one_hotpatcher", "my_patches"],
    filename_template="<hidden {name}>",
)
```

环境变量启用：

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW=1 \
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW_PREFIXES=sd_webui_all_in_one_hotpatcher,my_patches \
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW_TEMPLATE='<hidden {name}>' \
PYTHONPATH=src python your_app.py
```

如果 `src/sitecustomize.py` 在启动路径中，且存在任意 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_*` 环境变量，它会调用 `sd_webui_all_in_one_hotpatcher.bootstrap.configure_from_env()`。没有相关环境变量时，它不会安装任何 hook。

注意事项：

- 栈隐藏只影响安装后才 import 的模块；已经加载的模块不会被重写。
- 默认同时支持普通源码 loader 和 `zipimporter`。设置 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW_SOURCE_LOADERS=0` 后只处理 zip 模块。
- 模板支持 `{name}`、`{fullname}`、`{module}`。例如 `<frozen importlib._bootstrap>` 会产生更强的隐藏效果，但调试也更难。
- 它不修改业务逻辑，只改变 traceback 和 code object 里的 filename。

## 宿主通信协议

`sd_webui_all_in_one_hotpatcher.runtime` 使用 TCP + JSON Lines。每条消息是一行 UTF-8 JSON。宿主只需要开 TCP server，读写 JSONL 即可接入。

连接环境变量：

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST=127.0.0.1
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT=8765
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN=optional-secret
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TIMEOUT=5
```

首包握手：

```json
{"type":"hello","version":1,"token":"optional-secret","features":["config","progress","browser","fileops","faults","audit","logs","services"]}
```

请求消息：

```json
{"id":"...","type":"file.delete","payload":{"path":"/tmp/example"}}
```

成功响应：

```json
{"id":"...","ok":true,"payload":{}}
```

失败响应：

```json
{"id":"...","ok":false,"error":{"code":"cancelled","message":"user cancelled"}}
```

事件消息：

```json
{"type":"progress.update","payload":{"id":123,"value":50}}
```

需要响应的操作包括配置拉取和文件操作。进度、浏览器和 audit 默认是 best-effort 事件；发送失败会捕获异常并继续运行。

## 配置来源

配置支持环境变量内嵌 JSON、JSON 配置文件和远程拉取：

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE=env
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON='{"enabled":true}'
```

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE=file
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE=/path/to/hotpatcher-config.json
```

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE=remote
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST=127.0.0.1
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT=8765
```

配置文件必须是 UTF-8 JSON 对象。

`SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE=auto` 是默认值：优先读取 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON`，没有 env JSON 时读取 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE`，再没有时尝试远程配置。如果没有宿主连接参数，则返回空配置。

代码中读取：

```python
from sd_webui_all_in_one_hotpatcher.runtime.config import load_config

config = load_config()
```

## Services 控制层

`sd_webui_all_in_one_hotpatcher.services` 是给业务系统接入使用的统一控制层。它不会替代 import hook 或 runtime client，而是把“当前有什么补丁、默认配置是什么、如何补齐配置、如何按 JSON 启用功能”整理成稳定 API。

```python
from sd_webui_all_in_one_hotpatcher.services import (
    apply_config,
    get_catalog,
    get_default_config,
    load_config_file,
)

catalog = get_catalog()
defaults = get_default_config()
config = load_config_file("hotpatcher.json", write_back=True)
result = apply_config(config)
```

配置文件只需要保存用户改过的部分。加载时会深度补齐默认值, 已存在的用户值不覆盖：

```json
{
  "extensions": {
    "hf_endpoint_mirror": {
      "enabled": true
    }
  }
}
```

上面的配置读取后会自动补齐 `core`、`runtime.logs`、`extensions.zluda`、`extensions.extension_index`、`extensions.uv_pip` 等缺失设置。

services 也支持 JSON 请求：

```json
{"type":"services.defaults.get","payload":{}}
```

响应固定为：

```json
{"ok":true,"payload":{"config":{}}}
```

如果已经连接 runtime 宿主，可以打开独立 services 控制通道：

```python
from sd_webui_all_in_one_hotpatcher.services import install_service_control_channel

channel = install_service_control_channel(client)
```

环境变量启用：

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES=1
```

配置中设置 `"services": {"apply_on_bootstrap": true}` 后，`bootstrap.configure_from_env()` 会在加载配置后自动调用 `apply_config()`。v1 只负责启用补丁，不承诺撤销已经注册或已经生效的 import-time 补丁。

## 运行时控制能力

连接宿主：

```python
from sd_webui_all_in_one_hotpatcher.runtime import RuntimeClient

client = RuntimeClient.connect("127.0.0.1", 8765, token="optional-secret")
```

进度上报：

```python
from sd_webui_all_in_one_hotpatcher.runtime import Progress, ProgressManager

Progress.manager = ProgressManager(client)
with Progress("download", 100) as progress:
    progress.value = 50
    progress.right = "50%"
```

浏览器托管：

```python
from sd_webui_all_in_one_hotpatcher.runtime import ManagedBrowser

ManagedBrowser(client).open("https://example.com")
```

也可以 patch 标准库 `webbrowser.open`：

```python
from sd_webui_all_in_one_hotpatcher.runtime import patch_webbrowser

patch_webbrowser(client)
```

文件操作：

```python
from sd_webui_all_in_one_hotpatcher.runtime import FileOperation, UserCanceledException

try:
    with FileOperation(client) as fileop:
        fileop.delete("/tmp/example")
        fileop.perform()
except UserCanceledException:
    pass
```

`FileOperation` 会等待宿主响应。宿主返回 `{"code":"cancelled"}` 时会抛出 `UserCanceledException`。

faulthandler 转发：

```python
from sd_webui_all_in_one_hotpatcher.runtime.faults import install_faulthandler

fault_channel = install_faulthandler(client)
```

它会打开第二条 TCP 连接，先发送：

```json
{"type":"channel.open","channel":"fault","token":"..."}
```

随后把 socket file 交给 `faulthandler.enable()`。

audit hook：

```python
from sd_webui_all_in_one_hotpatcher.runtime.audit import install_audit_hook

install_audit_hook(client, ["import", "compile"])
```

audit 事件会以 `audit.event` 发送给宿主。bytes 和 code object 会转换成 JSON 安全结构。

普通异常上报：

```python
from sd_webui_all_in_one_hotpatcher.exceptions import capture_exception
from sd_webui_all_in_one_hotpatcher.runtime.errors import install_exception_reporter

install_exception_reporter(client)

try:
    ...
except Exception:
    capture_exception()
```

`capture_exception()` 仍会把 traceback 打到 stderr，同时发送 `error.exception` 事件。事件 payload 包含异常类型、消息、完整 traceback 字符串、frame 列表和进程信息。它和 `faulthandler` 的定位不同：`error.exception` 处理普通 Python 异常，`faults.install_faulthandler()` 处理 fatal crash/native crash 栈。

日志采集：

```python
import logging
from sd_webui_all_in_one_hotpatcher.runtime import install_log_capture, uninstall_log_capture

capture = install_log_capture(client, subprocess_mode="safe")

logging.getLogger("app").warning("structured log")
print("stdout text")

uninstall_log_capture()
```

也可以通过环境变量在 bootstrap 阶段安装：

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGS=1
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGGING=1
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_STREAMS=stdout,stderr
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_SUBPROCESS=safe
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_POLICY=bounded
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_HOOK_POLICY=cooperative
```

事件类型：

- `log.record`：Python `logging` 结构化记录。
- `log.stream`：`stdout`、`stderr` 和子进程输出。
- `log.dropped`：日志队列满导致的丢弃计数。

默认策略是 `bounded`，会限制单条字符串长度和队列大小；`SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_POLICY=raw` 会原样发送。子进程默认 `safe`，只捕获显式 `PIPE` / `capture_output=True` 的输出；`force` 会接管未指定 stdout/stderr 的子进程并写回父进程原 stream。

hook 冲突策略默认是 `cooperative`，会包装当前已有的 stdout/stderr、logging 和 subprocess hook 并继续转发。可设为 `warn` 发送 `log.hook_status` 告警，或设为 `reapply` 在被覆盖后重新包装当前对象。实验性 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_FD_CAPTURE=fallback|force` 可用于标准流 wrapper 被覆盖时的 fd 级兜底。

## 测试

测试位于 `src/tests`：

```bash
python -m pytest src/tests
```

测试覆盖函数补丁、模块补丁、源码补丁、字节码补丁、import 注入、别名 fallback、动态文件加载、栈隐藏、TCP JSONL 协议、配置来源、运行时控制能力、日志采集和 services 控制层。

## 限制和注意事项

- 这个系统主要针对“尚未 import 的模块”。目标模块已经加载后，注册补丁不会自动重新应用。
- import hook 是进程级全局行为。测试中应在用例结束后调用 `uninstall_import_hook()` 并清理 `sys.modules`。
- 源码字符串替换容易受目标库版本变更影响。对长期维护的补丁，优先考虑函数包装或 AST 补丁。
- 补丁内部异常默认会打印 traceback，但不会中断目标模块 import。这能提升容错性，但也可能隐藏补丁失效，需要关注日志。
- 只支持普通源码模块。内建模块、扩展模块和没有 `SourceFileLoader` 的模块不会被这个 loader 改写。
- 栈隐藏会降低 traceback 可调试性。开发环境建议使用 `<hidden {name}>` 这类可读模板，发布环境再考虑更强隐藏模板。
- runtime 通信协议不兼容原项目的 Windows named pipe + GUID 二进制协议。宿主端需要实现新的 TCP JSONL 协议。
