# Stack Shadow 栈隐藏机制

`sd_webui_all_in_one_hotpatcher.stack_shadow` 用来隐藏模块在 traceback 中显示的真实文件名。它来自原系统的 `swlutils/stack_shadower.py`，但抽取后做成了可配置、可卸载、环境变量驱动的通用能力。

## 它解决什么问题

当补丁系统以源码目录、zip 包或嵌入式资源形式分发时，异常 traceback 可能暴露真实路径：

```text
File "/real/path/src/sd_webui_all_in_one_hotpatcher_ext/foo/bar.py", line 10, in patch
```

栈隐藏后可以变成：

```text
File "<hidden sd_webui_all_in_one_hotpatcher_ext.foo.bar>", line 10, in patch
```

它只影响 code object 的 `co_filename`，不修改业务逻辑，也不负责发送 traceback。普通异常上报由 `runtime.errors` 处理，fatal crash 栈由 `runtime.faults` 处理。

## 核心原理

Python 编译源码时会把 filename 写进 code object：

```python
compile(source, filename, "exec")
```

traceback 展示的文件名来自 code object 的 `co_filename`。Stack shadower 通过自定义 loader 重新编译目标模块源码，并传入伪装后的 filename。

流程：

```text
import target
  -> StackShadowFinder.find_spec("target")
  -> 原始 importlib 找到 spec
  -> 判断 loader 是否可读源码
  -> loader.get_source("target")
  -> 替换 loader 为 StackShadowSourceLoader
  -> compile(source, "<hidden target>", "exec")
  -> exec(code, module.__dict__)
```

## 支持的 loader

当前支持：

- `zipimporter`
- `SourceFileLoader`

只要 loader 能提供 `get_source(fullname)`，就可以重新编译源码。

不支持或默认跳过：

- built-in module
- extension module
- namespace package
- 已经加载到 `sys.modules` 的模块
- 没有源码的模块

## API

```python
from sd_webui_all_in_one_hotpatcher import install_stack_shadower, uninstall_stack_shadower

install_stack_shadower(
    prefixes=["sd_webui_all_in_one_hotpatcher", "sd_webui_all_in_one_hotpatcher_ext"],
    filename_template="<hidden {name}>",
    include_source_loaders=True,
)

uninstall_stack_shadower()
```

参数：

- `prefixes`：模块名前缀，字符串或列表。`foo` 会匹配 `foo` 和 `foo.bar`。
- `filename_template`：伪装文件名模板。
- `include_source_loaders`：是否处理普通源码 loader。为 `False` 时只处理 zipimport。

模板变量：

- `{name}`
- `{fullname}`
- `{module}`

三者当前都等于完整模块名，保留多个名字是为了以后扩展。

## 环境变量

```bash
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW=1
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW_PREFIXES=sd_webui_all_in_one_hotpatcher,sd_webui_all_in_one_hotpatcher_ext
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW_TEMPLATE='<hidden {name}>'
SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW_SOURCE_LOADERS=1
```

`configure_stack_shadower_from_env()` 只在 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW=1` 时安装。

如果 `src/sitecustomize.py` 在 `PYTHONPATH` 中，且存在任意 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_*` 环境变量，会调用 `bootstrap.configure_from_env()`，再由 bootstrap 调用 `configure_stack_shadower_from_env()`。

## 启动时机

Stack shadower 必须尽早安装。

有效：

```python
install_stack_shadower("my_patches")
import my_patches.foo
```

无效：

```python
import my_patches.foo
install_stack_shadower("my_patches")
```

已经 import 的模块 code object 不会被重编译。

## 与 import hook 的顺序

`stack_shadow` 和 `hook` 都用 `sys.meta_path`。如果同一个模块同时被 stack shadower 和 import hook 匹配，先插入 `sys.meta_path` 的 finder 更早参与。

bootstrap 采用：

```text
configure_stack_shadower_from_env()
install_import_hook()
connect runtime
load config
```

原因是隐藏能力应该尽可能早启用，尤其是用户想隐藏 `sd_webui_all_in_one_hotpatcher.*` 自身时。

## 调试代价

隐藏 filename 后，traceback 不再直接显示真实文件路径。这对发布场景有用，但开发时会多一点麻烦。

开发建议：

- 使用 `<hidden {name}>`，保留模块名。
- 不要一上来用 `<frozen importlib._bootstrap>` 这种强隐藏模板。
- 如果需要定位真实路径，临时关闭 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW`。

## 安全边界

它不是安全沙箱，也不是反调试系统。

它能做到：

- 改 traceback 中的 filename。
- 隐藏 zip/source loader 原始路径。

它不能做到：

- 阻止用户从 `sys.modules` 查看模块对象。
- 阻止进程级调试器。
- 加密源码。
- 隐藏所有运行时痕迹。

把它看作“减少路径暴露和日志噪音”的工程工具，会比较稳。
