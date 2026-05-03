# InvokeAI Installer 常用命令

## 命令的使用
使用命令前需要激活环境，有以下 2 种方式激活。

### 1. 使用自动环境激活脚本
运行 `terminal.ps1` 后将自动打开 PowerShell 并激活 InvokeAI Env。

### 2. 手动输入命令激活
在 `InvokeAI` 文件夹打开 PowerShell，输入下面的命令激活 InvokeAI Env：

```powershell
./activate.ps1
```

!!! info
    在 PowerShell 中一定要显示 `[InvokeAI-Env]` 才算进入了环境，这样才能使用下面的命令。

## 常用命令

### 启动 InvokeAI
```powershell
invokeai-web
```

### 查看 InvokeAI 的版本
```powershell
invokeai-web --version
```

### 修复 InvokeAI 数据库
```powershell
invokeai-db-maintenance --operation all
```

!!! warning
    该命令因为会造成数据丢失，已被 InvokeAI 官方移除，详情可阅读：[build: remove broken scripts · invoke-ai/InvokeAI@576f1cb](https://github.com/invoke-ai/InvokeAI/commit/576f1cbb757ac107c0532681cd643f98d6e0d2e8)

### 从旧版 InvokeAI 导入图片到新版的 InvokeAI
```powershell
invokeai-import-images
```

!!! warning
    该命令因为会造成数据丢失，已被 InvokeAI 官方移除，详情可阅读：[build: remove broken scripts · invoke-ai/InvokeAI@576f1cb](https://github.com/invoke-ai/InvokeAI/commit/576f1cbb757ac107c0532681cd643f98d6e0d2e8)

### 清理安装时产生的 Pip 缓存
```powershell
python -m pip cache purge
```

### 安装某个 Python 软件包
```powershell
# 命令中的 <package_name> 替换成具体的 Python 软件包名
python -m pip install <package_name>
```

### 更新某个软件包
```powershell
# 命令中的 <package_name> 替换成具体的 Python 软件包名
python -m pip install <package_name> -U
```

### 重装某个软件包
```powershell
# 命令中的 <package_name> 替换成具体的 Python 软件包名
python -m pip install <package_name> --force-reinstall
```

### 卸载某个软件包
```powershell
# 命令中的 <package_name> 替换成具体的 Python 软件包名
python -m pip uninstall <package_name>
```

### 解决 ModuleNotFoundError: No module named 'controlnet_aux'
```powershell
python -m pip cache remove controlnet_aux
python -m pip uninstall controlnet_aux -y
python -m pip install controlnet_aux
```

!!! note
    1. 推荐使用 `python -m pip` 的写法，`pip` 的写法也可用。InvokeAI Installer 默认将 `pip` 命令链接到 `python -m pip` 避免直接调用 `pip`。  
    参考：[Deprecate pip, pipX, and pipX.Y · Issue #3164 · pypa/pip](https://github.com/pypa/pip/issues/3164)
    2. 该问题的参考：[ModuleNotFoundError: No module named 'controlnet_aux' - FAQ - Invoke](https://invoke-ai.github.io/InvokeAI/faq/?h=controlnet_aux#modulenotfounderror-no-module-named-controlnet_aux)

### 使用 uv 安装软件包
```powershell
# 命令中的 <package_name> 替换成具体的 Python 软件包名
uv pip install <package_name>
```
!!! note
    uv 命令的用法可参考：[uv docs](https://docs.astral.sh/uv)

### 列出 InvokeAI Installer 内置命令
```powershell
List-CMD
```

### 查看可用的 InvokeAI 版本并切换
（已在 [环境管理](usage.md#环境管理) 章节中说明）

### 更新到 InvokeAI RC 版
（已在 [环境管理](usage.md#环境管理) 章节中说明）

### 查看 Git / Python 命令实际调用的路径
（已在 [环境管理](usage.md#环境管理) 章节中说明）

### 解决 AttributeError: module 'cv2.ximgproc' has no attribute 'thinning'
```powershell
python -m pip install opencv-contrib-python --force-reinstall --no-deps
```
