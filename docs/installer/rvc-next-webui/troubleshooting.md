# RVC Next WebUI Installer 故障排查

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
.\rvc_next_webui_installer.ps1 : 无法加载文件 D:\rvc-next-webui\rvc_next_webui_installer.ps1。
未对文件 D:\rvc-next-webui\rvc_next_webui_installer.ps1 进行数字签名。无法在当前系统上运行该脚本。
有关运行脚本和设置执行策略的详细信息，请参阅 https:/go.microsoft.com/fwlink/?LinkID=135170 中的 about_Execution_Policies。
所在位置 行:1 字符：1
+ .\rvc_next_webui_installer.ps1
+ ~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : SecurityError: (:) []，PSSecurityException
    + FullyQualifiedErrorId : UnauthorizedAccess
```

或者右键运行 PowerShell 脚本时窗口闪一下就消失了。遇到这种情况，优先运行安装文档“环境配置”中的 `configure_env.bat`，完成环境配置后再右键 `.ps1` 脚本选择 `使用 PowerShell 运行`。不要左键双击 `.ps1` 脚本，左键双击通常会用记事本或默认编辑器打开脚本，而不是执行脚本。

如果仍然无法运行，可以使用管理员权限打开 PowerShell，运行下面的命令。

```powershell
Set-ExecutionPolicy Unrestricted -Scope CurrentUser
```

也可以重新使用 [环境配置](install.md#_2) 中的脚本解除 Windows 系统对运行 PowerShell 脚本的限制。

!!! note
    关于 PowerShell 执行策略的说明：[关于执行策略 ### PowerShell | Microsoft Learn](https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_execution_policies)

### 启用 Windows 长路径支持
使用管理员权限打开 PowerShell，运行以下命令：

```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

!!! note
    关于 Windows 长路径支持的说明：[最大路径长度限制 ### Win32 apps | Microsoft Learn](https://learn.microsoft.com/zh-cn/windows/win32/fileio/maximum-file-path-limitation)

### ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE
运行 RVC Next WebUI Installer 时出现以下类似的错误。

```
ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE. If you have updated the package versions, please update the hashes. Otherwise, examine the package contents carefully; someone may have tampered with them.
    rsa<5,>=3.1.4 from https://mirrors.cloud.tencent.com/pypi/packages/49/97/fa78e3d2f65c02c8e1268b9aba606569fe97f6c8f7c2d74394553347c145/rsa-4.9-py3-none-any.whl#sha256=90260d9058e514786967344d0ef75fa8727eed8a7d2e43ce9f4bcf1b536174f7 (from google-auth<3,>=1.6.3->tensorboard==2.10.1->-r requirements.txt (line 12)):
        Expected sha256 90260d9058e514786967344d0ef75fa8727eed8a7d2e43ce9f4bcf1b536174f7
             Got        b7593b59699588c6ce7347aecf17263295c079efb3677553c2a81b08e857f838
```

这是因为下载下来的 Python 软件包出现了损坏，Pip 无法进行安装，需要将 `rvc-next-webui/cache/pip` 文件夹删除，再重新运行 RVC Next WebUI Installer。

### CUDA out of memory
关闭其他占用显存的程序后重试；训练模型时可尝试在 RVC Next WebUI 中降低批大小（batch size）。

### DefaultCPUAllocator: not enough memory
尝试增加系统的虚拟内存，或者增加内存条。

### 端口被占用或无法绑定端口
RVC Next WebUI 默认使用 `7868` 端口，端口被占用时会自动尝试下一个端口，实际的访问地址以控制台中显示的地址为准。如果在启动参数中添加了 `--strict-port`，端口被占用时 RVC Next WebUI 会直接退出。

如果需要固定使用其他端口，可在`launch.ps1` 所在目录创建`launch_args.txt` 文件，在该文件中写上启动参数把 RVC Next WebUI 端口修改，如`--port 8888`，保存 `launch_args.txt` 文件后使用 `launch.ps1` 重新启动 RVC Next WebUI。

!!! note
    设置 RVC Next WebUI 启动参数的方法可参考 [设置 RVC Next WebUI 启动参数](usage.md#rvc-next-webui_2)。

### Linux 上无法使用实时变声
RVC Next 的实时变声功能需要系统的 PortAudio 库，Debian / Ubuntu 上可使用以下命令安装：

```bash
sudo apt install libportaudio2
```

安装完成后重新运行 `launch.ps1` 启动 RVC Next WebUI。

### RVC Next WebUI 设置界面中的下载源无法修改
这是因为 RVC Next WebUI Installer 启用了 HuggingFace 镜像源，启动时通过 `RVC_NEXT_DOWNLOADS__SOURCE` / `RVC_NEXT_DOWNLOADS__ENDPOINT` 环境变量固定了 RVC Next 的下载源。如果需要在 RVC Next WebUI 设置界面中选择下载源，请禁用 RVC Next WebUI Installer 的 HuggingFace 镜像源，具体方法可阅读 [设置 HuggingFace 镜像](config.md#huggingface)。

### Microsoft Visual C++ Redistributable is not installed, this may lead to the DLL load failure.
下载 [Microsoft Visual C++ Redistributable](https://aka.ms/vc14/vc_redist.x64.exe) 并安装。
