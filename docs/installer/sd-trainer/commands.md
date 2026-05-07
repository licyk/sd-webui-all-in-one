# SD Trainer Installer 常用命令

## 命令的使用
使用命令前需要激活环境，有以下 2 种方式激活。

### 1. 使用自动环境激活脚本
运行 `terminal.ps1` 后将自动打开 PowerShell 并激活 SD-Trainer Env。

### 2. 手动输入命令激活
在 `SD-Trainer` 文件夹打开 PowerShell，输入下面的命令激活 SD-Trainer Env：

```powershell
./activate.ps1
```

!!! info
    在 PowerShell 中一定要显示 `[SD-Trainer Env]` 才算进入了环境，这样才能使用下面的命令。

## 常用命令

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

!!! note
    推荐使用 `python -m pip` 的写法，`pip` 的写法也可用。SD Trainer Installer 默认将 `pip` 命令链接到 `python -m pip` 避免直接调用 `pip`。  
    参考：[Deprecate pip, pipX, and pipX.Y · Issue #3164 · pypa/pip](https://github.com/pypa/pip/issues/3164)

### 使用 uv 安装软件包
```powershell
# 命令中的 <package_name> 替换成具体的 Python 软件包名
uv pip install <package_name>
```

!!! note
    uv 命令的用法可参考：[uv docs](https://docs.astral.sh/uv)

### 更新仓库
```powershell
git pull --recurse-submodules
```

### 运行某个 Python 脚本
```powershell
# 命令中的 <python_script.py> 替换成要执行的 Python 脚本路径
python <python_script.py>
```

### 下载文件
```powershell
# 命令中的 <url> 替换成下载链接，<dir> 替换成下载到的路径，<output_file_name> 替换成保存的文件名
aria2c <url> -c -s 16 -x 16 -k 1M -d <dir> -o <output_file_name>
```

### 安装绘世启动器并自动配置绘世启动器所需的环境
```powershell
Install-Hanamizuki
```

!!! info
    运行该命令前请确保 SD-Trainer 已经关闭，如果运行该命令出现报错，可根据报错提示内容进行其他操作，再重新运行该命令。

### 列出 SD Trainer Installer 内置命令
```powershell
List-CMD
```

### 查看并切换 SD-Trainer 的版本
（已在 [环境管理](usage.md#_2) 章节中说明）

### 将 LoRA 模型融进 Stable Diffusion 模型中
```powershell
# 先下载融合 LoRA 的工具
git clone https://github.com/KohakuBlueleaf/LyCORIS

# 安装 kohya scripts 的 library 库
python -m pip install -e lora-scripts/scripts/dev

# 接下来就能进行模型融合了，比如我要融合的 LoRA 模型为 artist_all_in_one_2-000036.safetensors，Stable Diffusion 模型为 animagine-xl-3.1.safetensors，先把这 2 个模型放到当前的文件夹，接下来就可以进行模型融合
python LyCORIS/tools/merge.py animagine-xl-3.1.safetensors artist_all_in_one_2-000036.safetensors licyk_style_v0.1.safetensors --is_sdxl --dtype fp16

# 解释上面命令的意思：
# animagine-xl-3.1.safetensors 为 Stable Diffusion 模型
# artist_all_in_one_2-000036.safetensors 为 LoRA 模型
# licyk_style_v0.1.safetensors 为融合后要保存的模型名称
# --is_sdxl 参数指定了模型类型为 SDXL，如果模型类型为 SD 2.x 则改为 --is_v2，如果模型类型为 SD 1.x 则不需要加参数
# --dtype fp16 指定保存的模型精度为 fp16，常用的模型精度为 fp16、bf16
# 融合完成后在当前文件夹中就可以看到融合好的 Stable Diffusion 模型
# 注意，融合模型需要大于或等于 64G 的内存，如果内存低于这个大小可能会大量使用虚拟内存进行补足，增大硬盘的读写消耗
```

### 查看 Git / Python 命令实际调用的路径
（已在 [环境管理](usage.md#_2) 章节中说明）
