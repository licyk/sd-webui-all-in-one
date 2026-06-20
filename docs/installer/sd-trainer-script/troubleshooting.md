# SD Trainer Script Installer 故障排查

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
.\sd_trainer_script_installer.ps1 : 无法加载文件 D:\SD-Trainer-Script\sd_trainer_script_installer.ps1。
未对文件 D:\SD-Trainer-Script\sd_trainer_script_installer.ps1 进行数字签名。无法在当前系统上运行该脚本。
有关运行脚本和设置执行策略的详细信息，请参阅 https:/go.microsoft.com/fwlink/?LinkID=135170 中的 about_Execution_Policies。
所在位置 行:1 字符：1
+ .\sd_trainer_script_installer.ps1
+ ~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : SecurityError: (:) []，PSSecurityException
    + FullyQualifiedErrorId : UnauthorizedAccess
```

或者右键运行 PowerShell 脚本时窗口闪一下就消失了。遇到这种情况，优先运行安装文档“环境配置”中的 `configure_env.bat`，完成环境配置后再右键 `.ps1` 脚本选择 `使用 PowerShell 运行`。不要左键双击 `.ps1` 脚本，左键双击通常会用记事本或默认编辑器打开脚本，而不是执行脚本。

如果仍然无法运行，可以使用管理员权限打开 PowerShell，运行下面的命令。

```powershell
Set-ExecutionPolicy Unrestricted -Scope CurrentUser
```

也可以重新使用 [环境配置](install.md#_1) 中的脚本解除 Windows 系统对运行 PowerShell 脚本的限制。

!!! note
    关于 PowerShell 执行策略的说明：[关于执行策略 ### PowerShell | Microsoft Learn](https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_execution_policies)

### 启用 Windows 长路径支持
使用管理员权限打开 PowerShell，运行以下命令：

```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

!!! note
    关于 Windows 长路径支持的说明：[最大路径长度限制 ### Win32 apps | Microsoft Learn](https://learn.microsoft.com/zh-cn/windows/win32/fileio/maximum-file-path-limitation)

### SD-Trainer-Script 提示'Torch is not able to use GPU'
尝试将显卡驱动更至最新，确保显卡驱动支持的 CUDA 版本大于或等于 PyTorch 中所带的 CUDA 版本，或者使用 `reinstall_pytorch.ps1` 重装 PyTorch。

!!! note
    Nvidia 显卡驱动下载：https://www.nvidia.cn/geforce/drivers

如果要查询驱动最高支持的 CUDA 版本，可以打开 PowerShell，运行下方的命令。

```powershell
nvidia-smi
```

可以看到 PowerShell 中显示的以下信息。

```
Fri Jun  7 19:07:00 2024
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 552.44                 Driver Version: 552.44         CUDA Version: 12.4     |
|-----------------------------------------+------------------------+----------------------+
| GPU  Name                     TCC/WDDM  | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce RTX 4060 ...  WDDM  |   00000000:01:00.0 Off |                  N/A |
| N/A   51C    P0             16W /   95W |       0MiB /   8188MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI        PID   Type   Process name                              GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|  No running processes found                                                             |
+-----------------------------------------------------------------------------------------+
```

`CUDA Version` 后面显示的数字即为显卡驱动支持最高的 CUDA 版本。

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
运行 SD Trainer Script Installer 时出现以下类似的错误。

```
ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE. If you have updated the package versions, please update the hashes. Otherwise, examine the package contents carefully; someone may have tampered with them.
    rsa<5,>=3.1.4 from https://mirrors.cloud.tencent.com/pypi/packages/49/97/fa78e3d2f65c02c8e1268b9aba606569fe97f6c8f7c2d74394553347c145/rsa-4.9-py3-none-any.whl#sha256=90260d9058e514786967344d0ef75fa8727eed8a7d2e43ce9f4bcf1b536174f7 (from google-auth<3,>=1.6.3->tensorboard==2.10.1->-r requirements.txt (line 12)):
        Expected sha256 90260d9058e514786967344d0ef75fa8727eed8a7d2e43ce9f4bcf1b536174f7
             Got        b7593b59699588c6ce7347aecf17263295c079efb3677553c2a81b08e857f838
```

这是因为下载下来的 Python 软件包出现了损坏，Pip 无法进行安装，需要将 `SD-Trainer-Script/cache/pip` 文件夹删除，再重新运行 SD Trainer Script Installer。

### RuntimeError: Error(s) in loading state_dict for UNet2DConditionModel
检查训练参数是否正确，确认是否选择对应大模型版本的训练参数。

### UnicodeDecodeError: 'utf-8' codec can't decode byte xxxx in position xxx: invalid continuation byte
检查训练参数中是否存在中文，如模型文件名是否包含中文等。

### RuntimeError: NaN detected in latents: X:\xxx\xxx\xx.png
检查图片是否有问题，如果是训练 SDXL 的 LoRA，请外挂一个 [sdxl_fp16_fix](https://modelscope.cn/models/licyks/sd-vae/resolve/master/sdxl_1.0/sdxl_fp16_fix_vae.safetensors) 的 VAE 或者使用 BF16 精度进行训练。

### CUDA out of memory
确认显卡的显存大小是否满足训练要求（显存最低要求 > 6G），如果满足，重新调整训练参数。

### DefaultCPUAllocator: not enough memory
尝试增加系统的虚拟内存，或者增加内存条。

### Loss?
当 Loss 不为 nan 或者大于 1 时没必要看。想要看练出来的模型效果如何，直接用模型进行跑图测试，Loss 并不能准确的代表训练出来的模型的好坏。

### 训练素材中图片的分辨率不一致，而且有些图片的分辨率很大，需要裁剪？
请使用 SD-Trainer-Script 的 arb 桶，这将自动处理不同分辨率的图片，无需手动进行图片裁剪。

### AssertError: caption file is empty: xxx\xxxxxx\xx\2_xxx\xxxxxxx.txt
这是因为图片的打标文件的内容为空，请检查报错指出的文件里的内容是否为空，如果为空，需要重新打标。

### NotImplemenredError: Cannot cppy out of meta tensor; no data! Please use torch.nn.Module.to_empty() instead of torch.nn.Module.to() when moving module from mera to a different device.
训练使用的模型可能有问题，尝试更换模型。

### Microsoft Visual C++ Redistributable is not installed, this may lead to the DLL load failure.
下载 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) 并安装。
