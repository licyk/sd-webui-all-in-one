# 扩展模块开发指南

`sd_webui_all_in_one_hotpatcher_ext` 用来放具体补丁配方。核心框架 `sd_webui_all_in_one_hotpatcher` 不应该知道某个业务库、硬件兼容层或 WebUI 的细节。

## 为什么需要扩展目录

核心框架和业务补丁混在一起会有两个坏处：

1. 核心变得难稳定，任何业务补丁都可能影响基础能力。
2. 使用者无法只拿走通用框架，必须背上一堆无关依赖。

所以约定：

```text
sd_webui_all_in_one_hotpatcher/
  通用机制

sd_webui_all_in_one_hotpatcher_ext/
  具体补丁配方
```

当前已有：

```text
src/sd_webui_all_in_one_hotpatcher_ext/zluda/__init__.py
src/sd_webui_all_in_one_hotpatcher_ext/extension_index/__init__.py
src/sd_webui_all_in_one_hotpatcher_ext/hf_endpoint_mirror/__init__.py
src/sd_webui_all_in_one_hotpatcher_ext/uv_pip/__init__.py
```

## 扩展模块推荐结构

简单扩展：

```text
sd_webui_all_in_one_hotpatcher_ext/foo/__init__.py
```

复杂扩展：

```text
sd_webui_all_in_one_hotpatcher_ext/foo/
  __init__.py
  config.py
  patches.py
  docs.md
```

不要求每个扩展都有独立文档，但复杂扩展应至少在 README 或 `src/docs/extensions.md` 中留下使用说明。

## 扩展 API 设计原则

推荐提供三类入口：

1. 明确能力入口：

```python
apply_foo_compat()
apply_foo_runtime_patch()
```

2. 配置入口：

```python
apply_from_config(config)
```

3. 可选的低层 patch 函数，供测试或高级用户直接调用。

如果扩展使用 import-time patch，入口内部应该调用 `install_import_hook()`，不要要求使用者额外记住。纯运行时 wrapper 可以直接安装自己的 wrapper。

如果扩展提供配置项，还应在 `sd_webui_all_in_one_hotpatcher.services.SETTING_SCHEMA` 中声明 catalog 元数据。管理器 GUI 会读取 `get_catalog()` 自动生成设置界面，所以新增字段需要包含：

- feature 的 `title` 和 `description`。
- 每个 setting 的 `type`、`title`、`description`。
- 枚举字段的 `choices`。

示例：

```python
"extensions.foo": {
    "title": "Foo 镜像",
    "description": "替换 Foo 服务的默认下载地址。",
    "settings": {
        "enabled": {
            "type": "bool",
            "title": "启用",
            "description": "启用 Foo 镜像补丁。",
        },
        "endpoint": {
            "type": "str",
            "title": "Endpoint",
            "description": "Foo 服务镜像地址。",
        },
    },
}
```

## 注册补丁的基本模式

```python
from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo

def apply_feature_patch():
    install_import_hook()

    with monkey_zoo("target.module") as monkey:
        def patch_func(func, module):
            ...

        monkey.patch_function("run", patch_func)
```

如果补丁必须在目标模块执行前做准备，用 `patch_premodule()`：

```python
with monkey_zoo("target") as monkey:
    def before_exec(module):
        ...

    monkey.patch_premodule(before_exec)
```

如果目标模块已经 import，普通 import hook 不会生效。扩展文档必须写清楚“调用入口要在 import 目标库之前”。

## ZLUDA 扩展示例

ZLUDA 扩展抽自原系统的：

- `swlpatches/zluda_companion.py`
- `swlpatches/hotfix/torch_zluda_timer.py`

当前 API：

```python
from sd_webui_all_in_one_hotpatcher_ext.zluda import (
    apply_zluda_library,
    apply_zluda_compat,
    apply_torch_zluda_timer_hotfix,
    apply_from_config,
)
```

### `apply_zluda_library(path)`

注册 `torch` 的 `premodule` patch。在 `torch` 模块代码执行前加载指定目录下的 ZLUDA DLL。

为什么用 `premodule`：

- DLL 必须在 torch 初始化 CUDA 相关逻辑前加载。
- 模块执行后再加载就太晚了。

这个函数是 Windows 专用。当前实现非 Windows 下导入 `torch` 时会抛明确错误。

### `apply_zluda_compat()`

注册两个补丁：

- `torch` 的 `module` patch：禁用 cudnn、flash SDP、mem efficient SDP，启用 math SDP。
- `torch.backends.cuda` 的 `function` patch：把 `enable_flash_sdp(True)` 和 `enable_mem_efficient_sdp(True)` 强制转成 `False`。

为什么既 patch `torch` 又 patch `torch.backends.cuda`：

- `torch` patch 负责初始化后设置一次状态。
- `torch.backends.cuda` patch 防止后续代码重新打开不兼容开关。

### `apply_torch_zluda_timer_hotfix()`

注册 `torch.utils.cpp_extension` source patch：

- 把 `HIP_HOME = _join_rocm_home('hip') if ROCM_HOME else None` 改成 `HIP_HOME = ROCM_HOME`。
- 禁用 Windows 分支中的 raise。

这是典型的小范围源码替换，测试里用 fake `torch.utils.cpp_extension` 验证。

### `apply_from_config(config)`

支持配置：

```python
{
    "compat": True,
    "path": "C:/path/to/zluda",
    "torch_zluda_timer": True
}
```

扩展配置入口应保持简单，不要把 runtime config 读取逻辑塞进扩展本身。配置从哪里来由调用方决定。

## Extension Index 扩展示例

Extension Index 扩展抽自原系统的：

- `swlpatches/extension_index.py`

当前 API：

```python
from sd_webui_all_in_one_hotpatcher_ext.extension_index import (
    patch_extension_index_a1111,
    patch_extension_index_comfyui_manager,
    apply_from_config,
)
```

### `patch_extension_index_a1111(url)`

注册 `modules.ui_extensions` bytecode patch，把 A1111/Forge/Vladmandic 中几个已知扩展索引 URL 常量替换为传入的镜像 URL。

这个补丁使用 `CodeWrapper.co_consts` 做常量替换。抽取版会递归处理嵌套 tuple/code object，比原实现更能覆盖编译期折叠后的常量。

### `patch_extension_index_comfyui_manager()`

注册 `ComfyUI-Manager` 和 `ComfyUI-Manager-main` 的补丁：

- bytecode patch：替换 `default_cache_update()` / `get_cache()` 中的 GitHub raw 前缀。
- function patch：包装 `get_data(uri)`，运行时把入参中的 GitHub raw 前缀改成镜像前缀。

默认目标前缀是：

```text
https://gitcode.net/ranting8323/ComfyUI-Manager/-/raw/main/
```

也可以传自定义前缀：

```python
patch_extension_index_comfyui_manager(
    "https://mirror.example/ComfyUI-Manager/main/",
    source_prefix="https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/",
)
```

### `apply_from_config(config)`

支持配置：

```python
{
    "extension_index_url": "https://mirror.example/extensions.json",
    "comfyui_manager": True,
}
```

或自定义 ComfyUI-Manager 前缀：

```python
{
    "comfyui_manager": {
        "source_prefix": "https://source.example/main/",
        "destination_prefix": "https://mirror.example/main/",
    }
}
```

注意：这些补丁都必须在目标模块 import 前注册。如果目标 WebUI 已经加载了扩展管理模块，后注册不会自动改写已存在的函数或 code object。

## HF Endpoint Mirror 扩展示例

HF Endpoint Mirror 扩展抽自原系统的：

- `swlpatches/hfmirror/comfyui_wd14_tagger.py`
- `swlpatches/hfmirror/torchhub.py`
- `swlpatches/hfmirror/torchvision.py`
- 自定义的 SD WebUI `modules.util.load_file_from_url` 补丁

当前 API：

```python
from sd_webui_all_in_one_hotpatcher_ext.hf_endpoint_mirror import (
    apply_mirror,
    patch_torchhub,
    patch_torchvision,
    patch_comfyui_wd14_tagger,
    patch_sd_webui_load_file_from_url,
    load_file_from_url,
    compare_sha256,
    rewrite_huggingface_url,
)
```

抽取版不再查询原系统的 mirror spec，也不再把缓存文件 link/copy 到目标路径。它只做一件事：在目标下载函数被调用时，把 Hugging Face URL 的 host 替换为 `HF_ENDPOINT`。

示例：

```bash
HF_ENDPOINT=https://hf-mirror.example
```

```python
from sd_webui_all_in_one_hotpatcher_ext.hf_endpoint_mirror import apply_mirror

apply_mirror()
```

URL 规则：

```text
https://huggingface.co/user/repo/resolve/main/model.bin
  -> https://hf-mirror.example/user/repo/resolve/main/model.bin
```

如果 `HF_ENDPOINT` 没有设置、为空、不是完整 URL，或者下载 URL 的真实 host 不是 `huggingface.co`，wrapper 会把原 URL 原样传给目标函数。

### `patch_torchhub()`

注册 `torch.hub` 的 function patch，包装：

```python
download_url_to_file(url, dst, ...)
```

### `patch_torchvision()`

注册 `torchvision.datasets.utils` 的 function patch，包装：

```python
_urlretrieve(url, fpath, ...)
```

### `patch_comfyui_wd14_tagger()`

注册 `ComfyUI-WD14-Tagger.pysssss` 的 function patch，包装：

```python
download_to_file(url, dst, ...)
```

保持原补丁的 async wrapper 形态：包装后的函数是 async，并通过 `asyncio.to_thread()` 调用原始下载函数。

### `patch_sd_webui_load_file_from_url()`

注册 `modules.util` 的 function patch，替换：

```python
load_file_from_url(url, *, model_dir, progress=True, file_name=None, hash_prefix=None, re_download=False)
```

替换实现来自自定义 SD WebUI 下载函数，但镜像逻辑改成调用 `rewrite_huggingface_url(url)`：

- 不读取 `shared.hf_endpoint`。
- 只从 `HF_ENDPOINT` 环境变量读取镜像源。
- 只在 URL 的真实 host 是 `huggingface.co` 时替换。
- 保留 query 和 fragment。
- 保留已有文件缓存命中、`.tmp` 临时下载、`hash_prefix` 校验。
- 下载失败或 hash mismatch 时会清理临时文件。

### `rewrite_huggingface_url(url)`

低层工具函数，方便测试和高级调用。它在调用时读取 `HF_ENDPOINT`，所以运行期间修改环境变量会影响后续下载调用。

## uv Pip 扩展示例

uv Pip 扩展由原 `sdaio_patcher/sdaio_patches/uv_patch.py` 迁移而来。它不是 import-time patch，而是在当前进程里包装 `subprocess.run()`，把运行期安装依赖时出现的 Pip 命令改写为 uv。

当前 API：

```python
from sd_webui_all_in_one_hotpatcher_ext.uv_pip import (
    apply_from_config,
    patch_uv_to_subprocess,
    unpatch_uv_to_subprocess,
)
```

### `patch_uv_to_subprocess(symlink=False)`

包装当前的 `subprocess.run()`。当命令中包含 `pip` / `pip.exe` / `pip3` / `pip3.exe` 时，转换为：

```text
uv pip ...
```

转换时会移除 `--prefer-binary`、`--ignore-installed`、`-I`。如果 `symlink=True`，会额外添加：

```text
--link-mode symlink
```

这个补丁会把当前的 `subprocess.run` 当作下游继续调用，所以可以包住已经存在的第三方 wrapper。卸载时只在当前 `subprocess.run` 仍是自己的 wrapper 时恢复原函数，避免覆盖后续安装的 wrapper。

### `apply_from_config(config)`

支持配置：

```python
{
    "enabled": True,
    "symlink": False
}
```

services catalog 中对应功能路径是 `extensions.uv_pip`。

## 扩展测试策略

不要依赖真实大型库。ZLUDA 测试没有导入真实 torch，而是在 `tmp_path` 创建 fake torch 包：

```text
tmp/
  torch/
    __init__.py
    backends/
      cuda.py
      cudnn.py
```

测试流程：

1. `sys.path.insert(0, tmp_path)`
2. 调用扩展入口注册补丁
3. import fake target
4. 断言模块状态或函数行为
5. 清理 `sys.modules`、`monkey_zoo`、import hook

好处：

- 测试快。
- 不依赖 GPU、torch、Windows。
- 能精确验证补丁机制。

Extension Index 测试同理：

- 创建 fake `modules.ui_extensions` 验证 A1111 URL 常量替换。
- 创建 fake `ComfyUI-Manager.py` / `ComfyUI-Manager-main.py` 验证 bytecode 和 `get_data()` patch。
- 对带连字符的模块名，测试使用 `importlib.util.spec_from_file_location()`，覆盖 sd_webui_all_in_one_hotpatcher 对动态文件加载的包装路径。

HF Endpoint Mirror 测试创建 fake `torch.hub`、fake `torchvision.datasets.utils`、fake `ComfyUI-WD14-Tagger.pysssss` 和 fake `modules.util`，断言：

- 设置 `HF_ENDPOINT` 时 Hugging Face URL 被替换。
- 不设置 `HF_ENDPOINT` 时 URL 原样保留。
- 非 Hugging Face URL 原样保留。
- ComfyUI WD14 的 async wrapper 可以正常返回原下载函数结果。
- SD WebUI `load_file_from_url` 替换函数会写入目标文件、复用缓存、校验 hash，并在 hash mismatch 时删除临时文件。

## 扩展开发 checklist

新增扩展时检查：

- API 名称是否表达具体能力。
- import-time patch 是否在入口内部调用 `install_import_hook()`。
- 是否说明必须在目标模块 import 前调用。
- 是否有 `apply_from_config()`。
- 是否在 services catalog schema 中声明字段名、说明、类型和必要的 choices。
- 是否能用 fake dependency 测试。
- 是否没有把业务补丁塞进 `sd_webui_all_in_one_hotpatcher` core。
- 是否更新 README 或 docs。

## 常见坑

- 目标模块已加载：补丁不会自动生效。
- source patch 片段太宽：容易误伤。
- 扩展里直接 import 目标库：会导致补丁注册前目标库已经加载。
- 扩展测试没有清理 `sys.modules`：下一个测试会拿到旧模块。
- 把环境读取写死在扩展里：后续宿主配置、文件配置、远程配置会不好接。
