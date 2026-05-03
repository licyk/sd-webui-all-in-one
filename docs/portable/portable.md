# 整合包下载与使用

## 简介
基于 [sd-webui-all-in-one/Installer](../installer/index.md) 全自动构建的整合包。

整合包使用 7z 格式进行打包，若 Windows 系统不支持解压该格式，请使用 [7-Zip](https://7-zip.org/) / [Bandizip](https://www.bandisoft.com/bandizip/) 或者其他支持解压 7z 格式的工具进行解压，解压完成后，首次使用需要双击运行`configure_env.bat`进行环境配置，保证 PowerShell 脚本能够正常运行。

PowerShell 脚本需要右键该脚本，选择`使用 PowerShell 运行`才可以运行。目录中包含多个 PowerShell 脚本用于启动和管理文件，根据需求运行脚本。

部分 WebUI 支持使用绘世启动器进行启动和管理，运行`hanamizuki.bat`即可启动绘世启动器，如果没有这个文件说明绘世启动器不支持启动和管理该 WebUI。


## 下载
!!! note
    Windows 用户可以使用整合包下载器进行下载，下载速度更快，并且支持下载完自动解压整合包。
    
    
    <img width="1165" height="1042" alt="图片" src="https://github.com/user-attachments/assets/76dcfb6b-10a6-4a40-8efa-0b7d3f026e75" />
    
    [下载器地址 1 :material-download:](https://github.com/licyk/sd-webui-all-in-one/releases/download/portable/sd_portable_downloader.bat){ .md-button .md-button--primary }
    [下载器地址 2 :material-download:](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/portable/sd_portable_downloader.bat){ .md-button }

点击对应下载按钮即可下载整合包。推荐优先下载 Nightly 版整合包。Stable 版相对较旧，Nightly 版版本更新，但未经过完整测试，不过通常也是可以正常使用的。

## Stable Diffusion WebUI
![sd_webui](https://github.com/user-attachments/assets/02f40729-f816-49ea-b046-67c36501dcef)

**上手简单，操作方便，适合入门使用。**

支持 SD WebUI Installer / 绘世启动器进行管理。

[下载 Stable 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=stable&software=Stable+Diffusion+WebUI){ .md-button }
[下载 Nightly 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=nightly&software=Stable+Diffusion+WebUI){ .md-button .md-button--primary }

### SD WebUI Installer 管理方式
- configure_env.bat：首次使用 SD WebUI Installer 需要运行一次，保证能正常运行
- launch.ps1：启动 Stable Diffusion WebUI
- update.ps1：更新 Stable Diffusion WebUI
- update_extension.ps1：更新 Stable Diffusion WebUI 扩展
- download_models.ps1：下载模型
- switch_branch.ps1：切换 Stable Diffusion WebUI 分支
- reinstall_pytorch.ps1：切换 / 重装 PyTorch
- version_manager.ps1：管理对应 WebUI / 扩展的版本，安装、启用 / 禁用、卸载扩展
- settings.ps1：SD WebUI Installer 设置
- terminal.ps1：打开终端并进入 Stable Diffusion WebUI 环境
- activate.ps1：激活 Stable Diffusion WebUI 环境
- launch_stable_diffusion_webui_installer.ps1：运行 SD WebUI Installer 并执行安装任务

SD WebUI Installer 使用说明可阅读：[SD WebUI Installer](../installer/sd-webui/index.md)

### 绘世启动器管理方式
- hanamizuki.bat：启动绘世启动器

详细绘世启动器使用说明可阅读：https://sdnote.netlify.app/sd_launcher


## Stable Diffusion WebUI Forge
![sd_webui_forge](https://github.com/user-attachments/assets/a9b92d5d-320f-4724-9194-422120bc5712)

**基于 Stable Diffusion WebUI，有更强的显存优化，多了 FLUX 模型支持。**

支持 SD WebUI Installer / 绘世启动器进行管理。

[下载 Stable 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=stable&software=Stable+Diffusion+WebUI+Forge){ .md-button }
[下载 Nightly 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=nightly&software=Stable+Diffusion+WebUI+Forge){ .md-button .md-button--primary }

### SD WebUI Installer 管理方式
- configure_env.bat：首次使用 SD WebUI Installer 需要运行一次，保证能正常运行
- launch.ps1：启动 Stable Diffusion WebUI Forge
- update.ps1：更新 Stable Diffusion WebUI Forge
- update_extension.ps1：更新 Stable Diffusion WebUI Forge 扩展
- download_models.ps1：下载模型
- switch_branch.ps1：切换 Stable Diffusion WebUI Forge 分支
- reinstall_pytorch.ps1：切换 / 重装 PyTorch
- version_manager.ps1：管理对应 WebUI / 扩展的版本，安装、启用 / 禁用、卸载扩展
- settings.ps1：SD WebUI Installer 设置
- terminal.ps1：打开终端并进入 Stable Diffusion WebUI Forge 环境
- activate.ps1：激活 Stable Diffusion WebUI Forge 环境
- launch_stable_diffusion_webui_installer.ps1：运行 SD WebUI Installer 并执行安装任务

详细 SD WebUI Installer 使用说明可阅读：[SD WebUI Installer](../installer/sd-webui/index.md)

### 绘世启动器管理方式
- hanamizuki.bat：启动绘世启动器

详细绘世启动器使用说明可阅读：https://sdnote.netlify.app/sd_launcher


## Stable Diffusion WebUI reForge
![sd_webui_reforge](https://github.com/user-attachments/assets/c177586c-cedb-47b1-86d8-8ece231eedd0)

**基于旧版 Stable Diffusion WebUI Forge 开发，插件兼容性比 Stable Diffusion WebUI Forge 好一点。**

支持 SD WebUI Installer / 绘世启动器进行管理。

[下载 Stable 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=stable&software=Stable+Diffusion+WebUI+reForge){ .md-button }
[下载 Nightly 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=nightly&software=Stable+Diffusion+WebUI+reForge){ .md-button .md-button--primary }

### SD WebUI Installer 管理方式
- configure_env.bat：首次使用 SD WebUI Installer 需要运行一次，保证能正常运行
- launch.ps1：启动 Stable Diffusion WebUI reForge
- update.ps1：更新 Stable Diffusion WebUI reForge
- update_extension.ps1：更新 Stable Diffusion WebUI reForge 扩展
- download_models.ps1：下载模型
- switch_branch.ps1：切换 Stable Diffusion WebUI reForge 分支
- reinstall_pytorch.ps1：切换 / 重装 PyTorch
- version_manager.ps1：管理对应 WebUI / 扩展的版本，安装、启用 / 禁用、卸载扩展
- settings.ps1：SD WebUI Installer 设置
- terminal.ps1：打开终端并进入 Stable Diffusion WebUI reForge 环境
- activate.ps1：激活 Stable Diffusion WebUI reForge 环境
- launch_stable_diffusion_webui_installer.ps1：运行 SD WebUI Installer 并执行安装任务

详细 SD WebUI Installer 使用说明可阅读：[SD WebUI Installer](../installer/sd-webui/index.md)

### 绘世启动器管理方式
- hanamizuki.bat：启动绘世启动器

详细绘世启动器使用说明可阅读：https://sdnote.netlify.app/sd_launcher


## Stable Diffusion WebUI Forge Classic
![sd_webui_forge_classic](https://github.com/user-attachments/assets/1603e299-6589-4e19-87bd-436ac8b37ef7)

**基于旧版 Stable Diffusion WebUI Forge 开发，精简了无用组件，更轻量。**

支持 SD WebUI Installer / 绘世启动器进行管理。

[下载 Stable 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=stable&software=Stable+Diffusion+WebUI+Forge+Classic){ .md-button }
[下载 Nightly 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=nightly&software=Stable+Diffusion+WebUI+Forge+Classic){ .md-button .md-button--primary }

### SD WebUI Installer 管理方式
- configure_env.bat：首次使用 SD WebUI Installer 需要运行一次，保证能正常运行
- launch.ps1：启动 Stable Diffusion WebUI Forge Classic
- update.ps1：更新 Stable Diffusion WebUI Forge Classic
- update_extension.ps1：更新 Stable Diffusion WebUI Forge Classic 扩展
- download_models.ps1：下载模型
- switch_branch.ps1：切换 Stable Diffusion WebUI Forge Classic 分支
- reinstall_pytorch.ps1：切换 / 重装 PyTorch
- version_manager.ps1：管理对应 WebUI / 扩展的版本，安装、启用 / 禁用、卸载扩展
- settings.ps1：SD WebUI Installer 设置
- terminal.ps1：打开终端并进入 Stable Diffusion WebUI Forge Classic 环境
- activate.ps1：激活 Stable Diffusion WebUI Forge Classic 环境
- launch_stable_diffusion_webui_installer.ps1：运行 SD WebUI Installer 并执行安装任务

详细 SD WebUI Installer 使用说明可阅读：[SD WebUI Installer](../installer/sd-webui/index.md)

### 绘世启动器管理方式
- hanamizuki.bat：启动绘世启动器

详细绘世启动器使用说明可阅读：https://sdnote.netlify.app/sd_launcher


## SD Next
![sdnext](https://github.com/user-attachments/assets/3eb9e4b7-7ca9-4fce-b744-868db127f836)

**基于 Stable Diffusion WebUI 开发，支持的模型种类多，就是比较臃肿。**

支持 SD WebUI Installer / 绘世启动器进行管理。

[下载 Stable 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=stable&software=SD+Next){ .md-button }
[下载 Nightly 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=nightly&software=SD+Next){ .md-button .md-button--primary }

### SD WebUI Installer 管理方式
- configure_env.bat：首次使用 SD WebUI Installer 需要运行一次，保证能正常运行
- launch.ps1：启动 SD Next
- update.ps1：更新 SD Next
- update_extension.ps1：更新 SD Next 扩展
- download_models.ps1：下载模型
- switch_branch.ps1：切换 SD Next 分支
- reinstall_pytorch.ps1：切换 / 重装 PyTorch
- version_manager.ps1：管理对应 WebUI / 扩展的版本，安装、启用 / 禁用、卸载扩展
- settings.ps1：SD WebUI Installer 设置
- terminal.ps1：打开终端并进入 SD Next 环境
- activate.ps1：激活 SD Next 环境
- launch_stable_diffusion_webui_installer.ps1：运行 SD WebUI Installer 并执行安装任务

详细 SD WebUI Installer 使用说明可阅读：[SD WebUI Installer](../installer/sd-webui/index.md)

### 绘世启动器管理方式
- hanamizuki.bat：启动绘世启动器

详细绘世启动器使用说明可阅读：https://sdnote.netlify.app/sd_launcher


## ComfyUI
![comfyui](https://github.com/user-attachments/assets/6cd98e59-e39a-4e97-bdf8-17e79e758f0c)

**流程高度自定义，可玩性高，显存优化强，支持的模型丰富，~~除了某些插件喜欢冲突弄坏环境~~。**

支持 ComfyUI Installer / 绘世启动器进行管理。

**Nvidia 显卡版本：**

[下载 Stable 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=stable&software=ComfyUI){ .md-button }
[下载 Nightly 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=nightly&software=ComfyUI){ .md-button .md-button--primary }

**AMD 显卡版本：**

[下载 Nightly 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=nightly&software=ComfyUI+(ROCm)){ .md-button .md-button--primary }

**Intel 显卡版本：**

[下载 Nightly 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=nightly&software=ComfyUI+(XPU)){ .md-button .md-button--primary }

### ComfyUI Installer 管理方式
- configure_env.bat：首次使用 ComfyUI Installer 需要运行一次，保证能正常运行
- launch.ps1：启动 ComfyUI
- update.ps1：更新 ComfyUI
- update_node.ps1：更新 ComfyUI 扩展
- download_models.ps1：下载模型
- reinstall_pytorch.ps1：切换 / 重装 PyTorch
- version_manager.ps1：管理 ComfyUI / 自定义节点的版本，安装、启用 / 禁用、卸载自定义节点
- settings.ps1：ComfyUI Installer 设置
- terminal.ps1：打开终端并进入 ComfyUI 环境
- activate.ps1：激活 ComfyUI 环境
- launch_comfyui_installer.ps1：运行 ComfyUI Installer 并执行安装任务

详细 ComfyUI Installer 使用说明可阅读：[ComfyUI Installer](../installer/comfyui/index.md)

### 绘世启动器管理方式
- hanamizuki.bat：启动绘世启动器

详细绘世启动器使用说明可阅读：https://sdnote.netlify.app/sd_launcher


## Fooocus
![fooocus](https://github.com/user-attachments/assets/71c11744-45a3-4dca-a34a-c69e70e06729)

**化繁为简，更专注于提示词书写。**

支持 Fooocus Installer / 绘世启动器进行管理。

[下载 Stable 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=stable&software=Fooocus){ .md-button }
[下载 Nightly 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=nightly&software=Fooocus){ .md-button .md-button--primary }

### Fooocus Installer 管理方式
- configure_env.bat：首次使用 Fooocus Installer 需要运行一次，保证能正常运行
- launch.ps1：启动 Fooocus
- update.ps1：更新 Fooocus
- switch_branch.ps1：切换 Fooocus 分支
- download_models.ps1：下载模型
- reinstall_pytorch.ps1：切换 / 重装 PyTorch
- version_manager.ps1：管理 Fooocus 的版本
- settings.ps1：Fooocus Installer 设置
- terminal.ps1：打开终端并进入 Fooocus 环境
- activate.ps1：激活 Fooocus 环境
- launch_fooocus_installer.ps1：运行 Fooocus Installer 并执行安装任务

详细 Fooocus Installer 使用说明可阅读：[Fooocus Installer](../installer/fooocus/index.md)

### 绘世启动器管理方式
- hanamizuki.bat：启动绘世启动器

详细绘世启动器使用说明可阅读：https://sdnote.netlify.app/sd_launcher


## InvokeAI
![invokeai](https://github.com/user-attachments/assets/d2511de0-05c7-40c4-9c88-2d3a0417a6ec)

**拥有最强大的画布系统，更适合作为辅助绘画工具。**

仅支持 InvokeAI Installer 进行管理。

[下载 Stable 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=stable&software=InvokeAI){ .md-button }
[下载 Nightly 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=nightly&software=InvokeAI){ .md-button .md-button--primary }

### InvokeAI Installer 管理方式
- configure_env.bat：首次使用 InvokeAI Installer 需要运行一次，保证能正常运行
- launch.ps1：启动 InvokeAI
- update.ps1：更新 InvokeAI
- update_node.ps1：更新 InvokeAI 扩展
- download_models.ps1：下载模型
- reinstall_pytorch.ps1：切换 / 重装 PyTorch
- version_manager.ps1：管理 InvokeAI / 扩展的版本，安装、启用 / 禁用、卸载扩展
- settings.ps1：InvokeAI Installer 设置
- terminal.ps1：打开终端并进入 InvokeAI 环境
- activate.ps1：激活 InvokeAI 环境
- launch_invokeai_installer.ps1：运行 InvokeAI Installer 并执行安装任务

详细 InvokeAI Installer 使用说明可阅读：[InvokeAI Installer](../installer/invokeai/index.md)


## SD-Trainer
![sd_trainer](https://github.com/user-attachments/assets/0c0a7921-f1a0-4409-a518-ea1b0be5e385)

**训练模型如此简单。**

支持 SD-Trainer Installer / 绘世启动器进行管理。

[下载 Stable 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=stable&software=SD+Trainer){ .md-button }
[下载 Nightly 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=nightly&software=SD+Trainer){ .md-button .md-button--primary }

### SD-Trainer Installer 管理方式
- configure_env.bat：首次使用 SD-Trainer Installer 需要运行一次，保证能正常运行
- launch.ps1：启动 SD-Trainer
- update.ps1：更新 SD-Trainer
- switch_branch.ps1：切换 SD-Trainer 分支
- download_models.ps1：下载模型
- reinstall_pytorch.ps1：切换 / 重装 PyTorch
- version_manager.ps1：管理 SD-Trainer 的版本
- settings.ps1：SD-Trainer Installer 设置
- terminal.ps1：打开终端并进入 SD-Trainer 环境
- activate.ps1：激活 SD-Trainer 环境
- launch_sd_trainer_installer.ps1：运行 SD-Trainer Installer 并执行安装任务

详细 SD-Trainer Installer 使用说明可阅读：[SD Trainer Installer](../installer/sd-trainer/index.md)

### 绘世启动器管理方式
- hanamizuki.bat：启动绘世启动器

详细绘世启动器使用说明可阅读：https://sdnote.netlify.app/sd_launcher


## Kohya GUI
![kohya_gui](https://github.com/user-attachments/assets/06cd3001-5d15-4b3e-aeba-3579f3159a48)

**支持训练更多种类的模型，不过操作麻烦一点。**

仅支持 SD-Trainer Installer 进行管理。

[下载 Stable 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=stable&software=Kohya+GUI){ .md-button }
[下载 Nightly 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=nightly&software=Kohya+GUI){ .md-button .md-button--primary }

### SD-Trainer Installer 管理方式
- configure_env.bat：首次使用 SD-Trainer Installer 需要运行一次，保证能正常运行
- launch.ps1：启动 Kohya GUI
- update.ps1：更新 Kohya GUI
- switch_branch.ps1：切换 Kohya GUI 分支
- download_models.ps1：下载模型
- reinstall_pytorch.ps1：切换 / 重装 PyTorch
- version_manager.ps1：管理 Kohya GUI 的版本
- settings.ps1：SD-Trainer Installer 设置
- terminal.ps1：打开终端并进入 Kohya GUI 环境
- activate.ps1：激活 Kohya GUI 环境
- launch_sd_trainer_installer.ps1：运行 SD-Trainer Installer 并执行安装任务

详细 SD-Trainer Installer 使用说明可阅读：[SD Trainer Installer](../installer/sd-trainer/index.md)


## SD Scripts

**支持训练 SD1.5，SDXL，FLUX，ControlNet 等多种模型，并且是 SD-Trainer 和 Kohya GUI 的训练核心，不过操作比较麻烦。**

仅支持 SD-Trainer-Script Installer 进行管理。

[下载 Nightly 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=nightly&software=SD+Scripts){ .md-button .md-button--primary }

### SD-Trainer-Script Installer 管理方式
- configure_env.bat：首次使用 SD-Trainer-Script Installer 需要运行一次，保证能正常运行
- init.ps1：初始化 SD Scripts 基础环境
- train.ps1：用于编写训练命令并启动 SD Scripts
- update.ps1：更新 SD Scripts
- download_models.ps1：下载模型
- reinstall_pytorch.ps1：切换 / 重装 PyTorch
- version_manager.ps1：管理 SD-Trainer-Script 的版本
- settings.ps1：SD-Trainer-Script Installer 设置
- terminal.ps1：打开终端并进入 SD Scripts 环境
- activate.ps1：激活 SD Scripts 环境
- launch_sd_trainer_script_installer.ps1：运行 SD-Trainer-Script Installer 并执行安装任务

详细 SD-Trainer Installer 使用说明可阅读：[SD Trainer Script Installer](../installer/sd-trainer-script/index.md)


## Musubi Tuner

**支持训练 Hunyuan，Wan 等视频生成模型。**

仅支持 SD-Trainer-Script Installer 进行管理。

[下载 Nightly 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=nightly&software=Musubi+Tuner){ .md-button .md-button--primary }

### SD-Trainer-Script Installer 管理方式
- configure_env.bat：首次使用 SD-Trainer-Script Installer 需要运行一次，保证能正常运行
- init.ps1：初始化 Musubi Tuner 基础环境
- train.ps1：用于编写训练命令并启动 Musubi Tuner
- update.ps1：更新 Musubi Tuner
- download_models.ps1：下载模型
- reinstall_pytorch.ps1：切换 / 重装 PyTorch
- version_manager.ps1：管理 SD-Trainer-Script 的版本
- settings.ps1：SD-Trainer-Script Installer 设置
- terminal.ps1：打开终端并进入 Musubi Tuner 环境
- activate.ps1：激活 Musubi Tuner 环境
- launch_sd_trainer_script_installer.ps1：运行 SD-Trainer-Script Installer 并执行安装任务

详细 SD-Trainer-Script Installer 使用说明可阅读：[SD Trainer Script Installer](../installer/sd-trainer-script/index.md)


## Qwen TTS WebUI
![qwen_tts_webui](https://github.com/user-attachments/assets/c0af72b0-cd62-4f07-b5a8-e473b0a43a3a)

**支持使用 Qwen3 TTS 生成语音。**

仅支持 Qwen TTS WebUI Installer 进行管理。

[下载 Nightly 版 :material-download:](https://licyk-tools.netlify.app/#/sd_portable/download?source=modelscope&channel=nightly&software=Qwen+TTS+WebUI){ .md-button .md-button--primary }

### Qwen TTS WebUI Installer 管理方式
- configure_env.bat：首次使用 Qwen TTS WebUI Installer 需要运行一次，保证能正常运行
- launch.ps1：启动 Qwen TTS WebUI
- update.ps1：更新 Qwen TTS WebUI
- reinstall_pytorch.ps1：切换 / 重装 PyTorch
- version_manager.ps1：管理 Qwen TTS WebUI 的版本
- settings.ps1：Qwen TTS WebUI Installer 设置
- terminal.ps1：打开终端并进入 Qwen TTS WebUI 环境
- activate.ps1：激活 Qwen TTS WebUI 环境
- launch_qwen_tts_webui_installer.ps1：运行 Qwen TTS WebUI Installer 并执行安装任务

详细 Qwen TTS WebUI Installer 使用说明可阅读：[Qwen TTS WebUI Installer](../installer/qwen-tts-webui/index.md)


## 所有版本
整合包存储在 [HuggingFace](https://huggingface.co/licyk/sdnote/tree/main/portable) / [ModelScope](https://modelscope.cn/models/licyks/sdnote/files) 中。

**整合包合集链接：https://licyk.github.io/t/sd_portable**

!!! note
    1. 整合包分为 Stable 和 Nightly 版本，Nightly 版本是未经测试的版本，并且使用日期进行命名，如`comfyui_licyk_20250322_nightly`，`comfyui`代表该整合包为 ComfyUI 整合包，`20250322`代表整合包在 2025.3.22 时进行构建。虽然 Nightly 版本未经过测试，但通常是可以使用的。
    2. Stable 版本为 Nightly 版本中经过测试的版本，但因为作者时间问题，Stable 版本并不会经常更新。
    3. 使用 [sd-webui-all-in-one/Installer](../installer/index.md) 安装的 WebUI 和使用整合包没什么区别，因为这些整合包就是使用 [sd-webui-all-in-one/Installer](../installer/index.md) 进行构建的。
    4. 更新 WebUI / ComfyUI / ... 通常情况下不需要重新下载整合包，使用 [sd-webui-all-in-one/Installer](../installer/index.md) 或者绘世启动器即可对 WebUI / ComfyUI / ... 进行更新。
