# Import Hook 实现原理

`sd_webui_all_in_one_hotpatcher.hook` 是系统的核心。它利用 Python import machinery 的标准扩展点，在目标模块第一次 import 时替换 loader，从而在模块代码执行前后修改源码、AST、字节码或模块对象。

## Python import 流程中的切入点

Python 执行：

```python
import target
```

大致会经历：

1. 检查 `sys.modules`，如果已经有 `target`，直接返回。
2. 遍历 `sys.meta_path` 中的 finder，询问谁能返回 module spec。
3. spec 中的 loader 创建/执行 module。
4. 执行成功后 module 放入 `sys.modules`。

`sd_webui_all_in_one_hotpatcher` 的切入点是第 2 和第 3 步：

- `install_import_hook()` 把 `HookedMetaPathFinder` 插入 `sys.meta_path`。
- finder 命中目标模块后，把原始 `SourceFileLoader` 换成 `MonkeySourceFileLoader`。

## 安装与卸载

```python
from sd_webui_all_in_one_hotpatcher import install_import_hook, uninstall_import_hook

finder = install_import_hook()
uninstall_import_hook()
```

安装做两件事：

1. 把 finder 插到 `sys.meta_path` 头部。
2. 包装 `importlib.util.spec_from_file_location`。

第二点是为了支持动态文件加载。很多插件系统不会走普通 `import target`，而是：

```python
spec = importlib.util.spec_from_file_location("plugin", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
```

如果只插 `sys.meta_path`，这种路径会绕过普通 finder。包装 `spec_from_file_location` 可以让这类动态加载也套上 `MonkeySourceFileLoader`。

卸载会：

- 从 `sys.meta_path` 移除当前 finder。
- 清空 finder cache。
- 恢复原始 `spec_from_file_location`。

## `Monkey`

`Monkey` 是单个目标模块的补丁计划。它不直接执行补丁，只记录“目标模块加载时要做什么”。

它维护这些列表：

- `premodule_patches`
- `module_patches`
- `function_patches`
- `source_patches`
- `ast_patches`
- `bytecode_patches`
- `output_prohibition`
- `import_injections`

### source patch

```python
with monkey_zoo("target") as monkey:
    def patch_source(source, filename):
        return source.replace("old", "new")

    monkey.patch_sources(patch_source)
```

执行时机：读取源码之后、`ast.parse` 之前。

适用场景：

- 目标代码里有明确字符串片段要替换。
- 需要修正 import-time 常量、条件分支、硬编码路径。

风险：

- 对目标源码版本敏感。
- 替换片段过宽会误伤。
- 如果目标模块不是源码 loader，可能无法应用。

### AST patch

```python
import ast

class Transformer(ast.NodeTransformer):
    ...

with monkey_zoo("target") as monkey:
    monkey.patch_ast(Transformer())
```

执行时机：source patch 后、compile 前。

适用场景：

- 需要结构化修改语法树。
- 想避免脆弱的字符串替换。

风险：

- 实现成本高。
- 需要维护 AST location，否则 traceback 或调试体验可能变差。

### bytecode patch

```python
with monkey_zoo("target") as monkey:
    def patch_code(code):
        code.co_consts.replace_primitive("old", "new")

    monkey.patch_bytecode(patch_code)
```

执行时机：code object 生成后、模块执行前。

适用场景：

- 替换常量字符串。
- 替换嵌套 code object。
- 不想重新 parse 源码。

支撑模块是 `sd_webui_all_in_one_hotpatcher.mutable`：

- `CodeWrapper` 包装 `types.CodeType`。
- `TupleWrapper` 包装 `co_consts` 等 tuple 字段。
- 最后通过 `code.replace(**overrides)` 生成新 code object。

风险：

- 对 Python 字节码/code object 结构敏感。
- 可读性比 source/AST patch 差。

### premodule patch

```python
with monkey_zoo("target") as monkey:
    def before_exec(module):
        module.SOMETHING = 1

    monkey.patch_premodule(before_exec)
```

执行时机：module 对象创建后、模块代码执行前。

适用场景：

- 提前注入对象。
- 准备环境。
- 像 ZLUDA 那样在 `torch` 执行前加载 DLL。

### import injection

```python
with monkey_zoo("target") as monkey:
    monkey.inject_import("math", "sqrt")
```

执行时机：模块代码执行前。

效果是：

```python
target.__dict__["sqrt"] = math.sqrt
```

适用场景：

- 给被 patch 后的源码提供额外名字。
- 配合 source/AST patch 使用。

### function patch

```python
with monkey_zoo("target") as monkey:
    def patch_run(func, module):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    monkey.patch_function("run", patch_run)
```

执行时机：模块代码执行完成后。

适用场景：

- 包装模块顶层函数。
- 新增函数，使用 `add_if_not_exists=True`。

注意：它只处理模块字典里的名字，不会自动递归 patch 类方法。类方法需要在 `patch_module()` 里修改类对象。

### module patch

```python
with monkey_zoo("target") as monkey:
    def patch_module(module):
        module.FLAG = True

    monkey.patch_module(patch_module)
```

执行时机：模块代码执行完成后、function patch 之后。

适用场景：

- 改常量。
- 改类属性。
- 修改注册表、映射表。
- 对已定义对象做复杂改造。

### output prohibition

```python
with monkey_zoo("target") as monkey:
    monkey.prohibit_output()
```

传 `None` 时，会在模块执行期间 redirect stdout。传函数名时，会把该函数包装成静默 stdout 版本。

## `MonkeyZoo`

`monkey_zoo` 是全局注册表。

```python
with monkey_zoo("target") as monkey:
    monkey.patch_module(...)
```

上下文退出时：

- 如果 `monkey.active` 为真，保存到注册表。
- 如果没有任何补丁动作，移除对应项。

模块名会用 `casefold()` 归一化。这样做是从原系统继承来的，对 Windows/部分路径大小写环境更宽容。

### alias fallback

```python
monkey_zoo.alias_if_not_exists("old_name", "new_name")
```

当 `old_name` 找不到时，finder 会尝试导入 `new_name` 并把它作为 `old_name` 返回。

测试中用它覆盖包名迁移场景。

## `HookedMetaPathFinder`

finder 的核心逻辑：

1. 如果模块正在加载，跳过，避免递归。
2. 如果模块属于 `sd_webui_all_in_one_hotpatcher` 自己，跳过，避免自己 patch 自己。
3. 如果模块在 `monkey_zoo`，用标准 `importlib.util.find_spec` 找原 spec。
4. 如果原 loader 是 `SourceFileLoader`，换成 `MonkeySourceFileLoader`。
5. 如果模块有 alias fallback，处理缺失模块 fallback。

它有一个 `cache`，缓存已经包装过的 spec。`uninstall_import_hook()` 会清空 cache。

## `MonkeySourceFileLoader`

loader 做两件事：生成 code object、执行 module。

### `get_code()`

如果没有 source/AST patch：

```text
原 loader.get_code()
  -> bytecode patch
  -> return code object
```

如果有 source/AST patch：

```text
读取源码
  -> eval_source
  -> ast.parse
  -> eval_ast
  -> compile
  -> eval_bytecode
  -> return code object
```

### `exec_module()`

执行顺序固定：

```text
eval_premodule(module)
eval_import_injection(module)
exec(code_object, module.__dict__)
eval_function(module)
eval_module(module)
eval_prohibit_output(module)
```

这个顺序很关键。比如：

- source/AST/bytecode 必须在 exec 前。
- function/module patch 必须在 exec 后，因为函数和类此时才存在。
- import injection 要在 exec 前，否则目标代码看不到注入名。

## 已导入模块限制

普通 import hook 对已经在 `sys.modules` 里的模块无效。

```python
import target

with monkey_zoo("target") as monkey:
    ...

import target  # 不会重新执行 loader
```

处理方式：

- 尽量在目标模块首次 import 前注册补丁。
- 对已加载模块，手动调用修改逻辑。
- 必要时测试环境可以清理 `sys.modules` 后重新 import，但生产环境要谨慎。

## 与 stack shadow 的关系

`hook.py` 和 `stack_shadow.py` 都会插 finder 到 `sys.meta_path`，但职责不同：

- `hook.py` 修改模块行为。
- `stack_shadow.py` 修改 traceback filename。

如果二者都启用，安装顺序会影响谁先看到目标模块。bootstrap 里刻意先安装 stack shadower，再按需安装 import hook，是为了尽早隐藏 `sd_webui_all_in_one_hotpatcher` 相关模块。一般业务目标模块不要同时给两个 finder 处理，除非你明确知道顺序效果。

## 调试建议

- 用 `PYTHONDONTWRITEBYTECODE=1` 跑测试，减少 pyc 噪音。
- 在测试里总是清理 `sys.modules`、`monkey_zoo` 和 import hook。
- source patch 失败时先打印最终 source 或缩小替换片段。
- bytecode patch 先用简单常量替换测试，再做嵌套 code object 操作。
