# ComfyUI Installer 故障排查

## 故障排查

### 运行脚本时出现中文乱码
这可能是 Windows 系统中启用了 UTF 8 编码，可以按照下列方法解决。

1. 按下 `Win + R` 键，输入 `control` 后回车启动控制面板。
2. 点击 `时钟和区域`->`区域`
3. 在弹出的区域设置窗口中点击顶部的 `管理`，再点击 `更改系统区域设置`.
4. 在弹出的窗口中将 `使用 Unicode UTF-8 提供全球语言支持` 取消勾选，然后一直点击确定保存设置，并重启电脑。

### 无法使用 PowerShell 运行
运行 PowerShell 脚本时出现以下错误。

```
.\comfyui_installer.ps1 : 无法加载文件 D:\ComfyUI\comfyui_installer.ps1。
未对文件 D:\ComfyUI\comfyui_installer.ps1 进行数字签名。无法在当前系统上运行该脚本。
有关运行脚本和设置执行策略的详细信息，请参阅 https:/go.microsoft.com/fwlink/?LinkID=135170 中的 about_Execution_Policies。
所在位置 行:1 字符：1
+ .\comfyui_installer.ps1
+ ~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : SecurityError: (:) []，PSSecurityException
    + FullyQualifiedErrorId : UnauthorizedAccess
```

或者右键运行 PowerShell 脚本时闪一下 PowerShell 的界面后就消失了。

这是因为未解除 Windows 系统对运行 PowerShell 脚本的限制，请使用管理员权限打开 PowerShell，运行下面的命令。

```powershell
Set-ExecutionPolicy Unrestricted -Scope CurrentUser
```

或者使用 [环境配置](environment.md#环境配置) 中的脚本解除 Windows 系统对运行 PowerShell 脚本的限制。

!!! note
    关于 PowerShell 执行策略的说明：[关于执行策略 ### PowerShell | Microsoft Learn](https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_execution_policies)

### 启用 Windows 长路径支持
使用管理员权限打开 PowerShell，运行以下命令：

```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

!!! note
    关于 Windows 长路径支持的说明：[最大路径长度限制 ### Win32 apps | Microsoft Learn](https://learn.microsoft.com/zh-cn/windows/win32/fileio/maximum-file-path-limitation)

### PowerShell 中出现 xFormers 报错
在控制台中出现有关 xFormers 的警告信息，类似下面的内容。

```
WARNING[XFORMERS]: xFormers can't load C++/CUDA extensions. xFormers was built for:
    PyTorch 2.2.1+cu118 with CUDA 1108 (you have 2.2.2+cu121)
    Python  3.10.11 (you have 3.10.11)
  Please reinstall xformers (see https://github.com/facebookresearch/xformers#installing-xformers)
  Memory-efficient attention, SwiGLU, sparse and more won't be available.
```

这是因为 xFormers 所适配的 CUDA 版本和 PyTorch 所带的 CUDA 版本不一致，请运行 `reinstall_pytorch.ps1` 重装 PyTorch。

### ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE
运行 ComfyUI Installer 时出现以下类似的错误。

```
ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE. If you have updated the package versions, please update the hashes. Otherwise, examine the package contents carefully; someone may have tampered with them.
    rsa<5,>=3.1.4 from https://mirrors.cloud.tencent.com/pypi/packages/49/97/fa78e3d2f65c02c8e1268b9aba606569fe97f6c8f7c2d74394553347c145/rsa-4.9-py3-none-any.whl#sha256=90260d9058e514786967344d0ef75fa8727eed8a7d2e43ce9f4bcf1b536174f7 (from google-auth<3,>=1.6.3->tensorboard==2.10.1->-r requirements.txt (line 12)):
        Expected sha256 90260d9058e514786967344d0ef75fa8727eed8a7d2e43ce9f4bcf1b536174f7
             Got        b7593b59699588c6ce7347aecf17263295c079efb3677553c2a81b08e857f838
```

这是因为下载下来的 Python 软件包出现了损坏，Pip 无法进行安装，需要将 `ComfyUI/cache/pip` 文件夹删除，再重新运行 ComfyUI Installer。

### CUDA out of memory
尝试使用分块编 / 解码 VAE 节点，降低出图分辨率。

### DefaultCPUAllocator: not enough memory
尝试增加系统的虚拟内存，或者增加内存条。

### 以一种访问权限不允许的方式做了一个访问套接字的尝试
启动 ComfyUI 时出现以下的错误。
```
ERROR: [Error 13] error while attempting to bind on address ('127.0.0.1', 28000): 以一种访问权限不允许的方式做了一个访问套接字的尝试。
```

这是因为该端口被其他软件占用，ComfyUI 无法使用。可尝试将占用该端口的软件关闭，或者在`launch.ps1` 所在目录创建`launch_args.txt` 文件，在该文件中写上启动参数把 ComfyUI 端口修改，如`--port 8888`，保存 `launch_args.txt` 文件后使用 `launch.ps1` 重新启动 ComfyUI。

!!! note
    设置 ComfyUI 启动参数的方法可参考 [设置 ComfyUI 启动参数](usage.md#设置-comfyui-启动参数)。

### Microsoft Visual C++ Redistributable is not installed, this may lead to the DLL load failure.
下载 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) 并安装。
