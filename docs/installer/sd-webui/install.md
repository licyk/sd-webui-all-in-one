# SD WebUI Installer 环境准备与安装

## 快速流程

1. Windows 用户先在“环境配置脚本下载”中下载环境配置脚本 `configure_env.bat` 并运行；Linux / macOS 用户先安装 PowerShell，macOS 还需要安装 Homebrew。
2. 在“SD WebUI Installer 下载地址”中下载 SD WebUI Installer 安装脚本 `stable_diffusion_webui_installer.ps1`。
3. 将 SD WebUI Installer 安装脚本 `stable_diffusion_webui_installer.ps1` 放到希望安装 Stable Diffusion WebUI 的位置；需要指定 WebUI 分支时，再在同一目录创建对应配置文件。
4. 右键 SD WebUI Installer 安装脚本 `stable_diffusion_webui_installer.ps1` 选择`使用 PowerShell 运行`，或在终端中使用 `pwsh stable_diffusion_webui_installer.ps1`。

## 环境配置
该脚本在 Windows / Linux / MacOS 系统上需要进行不同的环境配置，以下为不同平台配置环境的方法。

### Windows
下载环境自动配置脚本，双击运行`configure_env.bat`后将会弹出管理员权限申请提示，选择`是`授权管理员权限给环境配置脚本，这时将自动配置运行环境。

**环境配置脚本下载**

[GitHub Release 下载 :material-download:](https://github.com/licyk/sd-webui-all-in-one/releases/download/archive/configure_env.bat){ .md-button .md-button--primary }
[Gitee Release 下载 :material-download:](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/archive/configure_env.bat){ .md-button }
[GitHub Raw 下载 :material-download:](https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/configure_env.bat){ .md-button }
[Gitee Raw 下载 :material-download:](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/configure_env.bat){ .md-button }
[GitLab Raw 下载 :material-download:](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/configure_env.bat){ .md-button }

### Linux
参考该文档安装 PowerShell：[在 Linux 上安装 PowerShell - PowerShell | Microsoft Learn](https://learn.microsoft.com/zh-cn/powershell/scripting/install/install-powershell-on-linux?view=powershell-7.5)

### MacOS
参考该文档安装 PowerShell：[在 macOS 上安装 PowerShell - PowerShell | Microsoft Learn](https://learn.microsoft.com/zh-cn/powershell/scripting/install/install-powershell-on-macos?view=powershell-7.5)

再参考该文档安装 HomeBrew：[macOS（或 Linux）缺失的软件包的管理器 — Homebrew](https://brew.sh/zh-cn)

## 安装

**SD WebUI Installer 下载地址**

[GitHub Release 下载 :material-download:](https://github.com/licyk/sd-webui-all-in-one/releases/download/stable_diffusion_webui_installer/stable_diffusion_webui_installer.ps1){ .md-button .md-button--primary }
[Gitee Release 下载 :material-download:](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/stable_diffusion_webui_installer/stable_diffusion_webui_installer.ps1){ .md-button }
[GitHub Raw 下载 :material-download:](https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/stable_diffusion_webui_installer.ps1){ .md-button }
[Gitee Raw 下载 :material-download:](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/stable_diffusion_webui_installer.ps1){ .md-button }
[GitLab Raw 下载 :material-download:](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/stable_diffusion_webui_installer.ps1){ .md-button }

SD WebUI Installer 默认情况下安装的是 [AUTOMATIC1111/Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) 分支，如果需要指定安装的分支，需要在 SD WebUI Installer 所在路径创建配置文件，以下为不同配置文件对应的 Stable Diffusion WebUI 分支。

|配置文件名 | 对应安装的分支|
|---|---|
|`install_sd_webui_main.txt`|[AUTOMATIC1111/Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) 主分支|
|`install_sd_webui_dev.txt`|[AUTOMATIC1111/Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) 测试分支|
|`install_sd_webui_forge.txt`|[lllyasviel/Stable-Diffusion-WebUI-Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)|
|`install_sd_webui_reforge_main.txt`|[Panchovix/Stable-Diffusion-WebUI-reForge](https://github.com/Panchovix/stable-diffusion-webui-reForge) 主分支|
|`install_sd_webui_reforge_dev.txt`|[Panchovix/Stable-Diffusion-WebUI-reForge](https://github.com/Panchovix/stable-diffusion-webui-reForge) 测试分支|
|`install_sd_webui_forge_classic.txt`|[Haoming02/Stable-Diffusion-WebUI-Forge-Classic](https://github.com/Haoming02/sd-webui-forge-classic)|
|`install_sd_webui_forge_neo.txt`|[Haoming02/Stable-Diffusion-WebUI-Forge-Neo](https://github.com/Haoming02/sd-webui-forge-classic)|
|`install_sd_webui_amdgpu.txt`|[lshqqytiger/Stable-Diffusion-WebUI-AMDGPU](https://github.com/lshqqytiger/stable-diffusion-webui-amdgpu)|
|`install_sd_next_main.txt`|[vladmandic/SD.Next](https://github.com/vladmandic/sdnext) 主分支|
|`install_sd_next_dev.txt`|[vladmandic/SD.Next](https://github.com/vladmandic/sdnext) 测试分支|

上表使用当前代码中的 `InstallBranch` 分支标识作为配置文件名。旧版短名称配置文件仍由安装器兼容识别，新建配置时建议使用上表文件名。

如果创建了配置文件，将 SD WebUI Installer 和配置文件放在一起，如下所示。

```
.
├── 119966207_p0_master1200.jpg
├── 437A9AE81C043B83110F55316EC7789E.png
├── BaiduNetdiskDownload
├── BaiduNetdiskWorkspace
├── install_sd_webui_main.txt             # 这是配置文件
├── QQDownloads
├── stable_diffusion_webui_installer.ps1  # 这是 SD WebUI Installer
├── z-noob_artist.csv
└── 得意黑_横屏.prtextstyle
```

右键 `stable_diffusion_webui_installer.ps1` 脚本，在弹出的右键菜单中点击`使用 PowerShell 运行`，此时 SD WebUI Installer 将安装 Stable Diffusion WebUI 至本地。

!!! info
    右键菜单中点击`使用 PowerShell 运行`为 Windows 平台上的使用方法，如果需要在 Linux / MacOS 平台中运行，请打开终端并使用`pwsh`命令去运行，例如：
    
    ```bash
    pwsh stable_diffusion_webui_installer.ps1
    ```
    对于其他 PowerShell 脚本也是类似的方法去运行。

!!! note
    SD WebUI Installer 在安装时还可以通过其他配置文件指定其他参数，可阅读以下的说明：
    - [设置 Github 镜像源](config.md#github)
    - [设置 PyPI 镜像源](config.md#pypi)
    - [设置 uv 包管理器](config.md#uv)
    - [配置代理](config.md#_2)
    - [设置内核路径前缀](config.md#_5)
    - [设置模型下载源](resources.md#_3)
    
    通常这些参数不需要配置，保持默认即可，如有需要再根据说明进行配置。

在 SD WebUI Installer 成功安装 Stable Diffusion WebUI 后，在`stable-diffusion-webui`文件夹中可以看到 Stable Diffusion WebUI 的文件和各种管理脚本。如果出现某个步骤运行失败，可尝试重新运行 SD WebUI Installer。

??? note "查看 SD WebUI Installer 为 Stable Diffusion WebUI 预装的扩展"
    
    |[AUTOMATIC1111/Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)|
    |---|
    |[Coyote-A/ultimate-upscale-for-automatic1111](https://github.com/Coyote-A/ultimate-upscale-for-automatic1111)|
    |[DominikDoom/a1111-sd-webui-tagcomplete](https://github.com/DominikDoom/a1111-sd-webui-tagcomplete)|
    |[Bing-su/adetailer](https://github.com/Bing-su/adetailer)|
    |[zanllp/sd-webui-infinite-image-browsing](https://github.com/zanllp/sd-webui-infinite-image-browsing)|
    |[huchenlei/sd-webui-openpose-editor](https://github.com/huchenlei/sd-webui-openpose-editor)|
    |[licyk/sd-webui-prompt-all-in-one](https://github.com/licyk/sd-webui-prompt-all-in-one)|
    |[licyk/sd-webui-wd14-tagger](https://github.com/licyk/sd-webui-wd14-tagger)|
    |[hanamizuki-ai/stable-diffusion-webui-localization-zh_Hans](https://github.com/hanamizuki-ai/stable-diffusion-webui-localization-zh_Hans)|
    |[Haoming02/sd-webui-mosaic-outpaint](https://github.com/Haoming02/sd-webui-mosaic-outpaint)|
    |[Haoming02/sd-webui-resource-monitor](https://github.com/Haoming02/sd-webui-resource-monitor)|
    |[licyk/sd-webui-tcd-sampler](https://github.com/licyk/sd-webui-tcd-sampler)|
    |[licyk/advanced_euler_sampler_extension](https://github.com/licyk/advanced_euler_sampler_extension)|
    |[hako-mikan/sd-webui-regional-prompter](https://github.com/hako-mikan/sd-webui-regional-prompter)|
    |[Akegarasu/sd-webui-model-converter](https://github.com/Akegarasu/sd-webui-model-converter)|
    |[Mikubill/sd-webui-controlnet](https://github.com/Mikubill/sd-webui-controlnet)|
    |[pkuliyi2015/multidiffusion-upscaler-for-automatic1111](https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111)|
    |[mcmonkeyprojects/sd-dynamic-thresholding](https://github.com/mcmonkeyprojects/sd-dynamic-thresholding)|
    |[hako-mikan/sd-webui-lora-block-weight](https://github.com/hako-mikan/sd-webui-lora-block-weight)|
    |[licyk/stable-diffusion-webui-model-toolkit](https://github.com/licyk/stable-diffusion-webui-model-toolkit)|
    |[licyk/a1111-sd-webui-haku-img](https://github.com/licyk/a1111-sd-webui-haku-img)|
    |[hako-mikan/sd-webui-supermerger](https://github.com/hako-mikan/sd-webui-supermerger)|
    |[continue-revolution/sd-webui-segment-anything](https://github.com/continue-revolution/sd-webui-segment-anything)|
    |[licyk/sd-webui-licyk-style-image](https://github.com/licyk/sd-webui-licyk-style-image)|
    |[w-e-w/sdwebui-close-confirmation-dialogue](https://github.com/w-e-w/sdwebui-close-confirmation-dialogue)|
    |[viyiviyi/stable-diffusion-webui-zoomimage](https://github.com/viyiviyi/stable-diffusion-webui-zoomimage)|
    
    |[lllyasviel/Stable-Diffusion-WebUI-Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)|
    |---|
    |[Coyote-A/ultimate-upscale-for-automatic1111](https://github.com/Coyote-A/ultimate-upscale-for-automatic1111)|
    |[DominikDoom/a1111-sd-webui-tagcomplete](https://github.com/DominikDoom/a1111-sd-webui-tagcomplete)|
    |[Bing-su/adetailer](https://github.com/Bing-su/adetailer)|
    |[zanllp/sd-webui-infinite-image-browsing](https://github.com/zanllp/sd-webui-infinite-image-browsing)|
    |[huchenlei/sd-webui-openpose-editor](https://github.com/huchenlei/sd-webui-openpose-editor)|
    |[licyk/sd-webui-prompt-all-in-one](https://github.com/licyk/sd-webui-prompt-all-in-one)|
    |[licyk/sd-webui-wd14-tagger](https://github.com/licyk/sd-webui-wd14-tagger)|
    |[hanamizuki-ai/stable-diffusion-webui-localization-zh_Hans](https://github.com/hanamizuki-ai/stable-diffusion-webui-localization-zh_Hans)|
    |[Haoming02/sd-webui-mosaic-outpaint](https://github.com/Haoming02/sd-webui-mosaic-outpaint)|
    |[Haoming02/sd-webui-resource-monitor](https://github.com/Haoming02/sd-webui-resource-monitor)|
    |[licyk/sd-webui-tcd-sampler](https://github.com/licyk/sd-webui-tcd-sampler)|
    |[licyk/advanced_euler_sampler_extension](https://github.com/licyk/advanced_euler_sampler_extension)|
    |[hako-mikan/sd-webui-regional-prompter](https://github.com/hako-mikan/sd-webui-regional-prompter)|
    |[Akegarasu/sd-webui-model-converter](https://github.com/Akegarasu/sd-webui-model-converter)|
    |[licyk/a1111-sd-webui-haku-img](https://github.com/licyk/a1111-sd-webui-haku-img)|
    |[licyk/sd_forge_hypertile_svd_z123](https://github.com/licyk/sd_forge_hypertile_svd_z123)|
    |[lllyasviel/sd-forge-layerdiffuse](https://github.com/lllyasviel/sd-forge-layerdiffuse)|
    |[licyk/sd-webui-licyk-style-image](https://github.com/licyk/sd-webui-licyk-style-image)|
    |[w-e-w/sdwebui-close-confirmation-dialogue](https://github.com/w-e-w/sdwebui-close-confirmation-dialogue)|
    |[viyiviyi/stable-diffusion-webui-zoomimage](https://github.com/viyiviyi/stable-diffusion-webui-zoomimage)|
    
    |[Panchovix/Stable-Diffusion-WebUI-reForge](https://github.com/Panchovix/stable-diffusion-webui-reForge)|
    |---|
    |[Coyote-A/ultimate-upscale-for-automatic1111](https://github.com/Coyote-A/ultimate-upscale-for-automatic1111)|
    |[DominikDoom/a1111-sd-webui-tagcomplete](https://github.com/DominikDoom/a1111-sd-webui-tagcomplete)|
    |[Bing-su/adetailer](https://github.com/Bing-su/adetailer)|
    |[zanllp/sd-webui-infinite-image-browsing](https://github.com/zanllp/sd-webui-infinite-image-browsing)|
    |[huchenlei/sd-webui-openpose-editor](https://github.com/huchenlei/sd-webui-openpose-editor)|
    |[licyk/sd-webui-prompt-all-in-one](https://github.com/licyk/sd-webui-prompt-all-in-one)|
    |[licyk/sd-webui-wd14-tagger](https://github.com/licyk/sd-webui-wd14-tagger)|
    |[hanamizuki-ai/stable-diffusion-webui-localization-zh_Hans](https://github.com/hanamizuki-ai/stable-diffusion-webui-localization-zh_Hans)|
    |[Haoming02/sd-webui-mosaic-outpaint](https://github.com/Haoming02/sd-webui-mosaic-outpaint)|
    |[Haoming02/sd-webui-resource-monitor](https://github.com/Haoming02/sd-webui-resource-monitor)|
    |[licyk/sd-webui-tcd-sampler](https://github.com/licyk/sd-webui-tcd-sampler)|
    |[licyk/advanced_euler_sampler_extension](https://github.com/licyk/advanced_euler_sampler_extension)|
    |[hako-mikan/sd-webui-regional-prompter](https://github.com/hako-mikan/sd-webui-regional-prompter)|
    |[Akegarasu/sd-webui-model-converter](https://github.com/Akegarasu/sd-webui-model-converter)|
    |[licyk/stable-diffusion-webui-model-toolkit](https://github.com/licyk/stable-diffusion-webui-model-toolkit)|
    |[licyk/a1111-sd-webui-haku-img](https://github.com/licyk/a1111-sd-webui-haku-img)|
    |[hako-mikan/sd-webui-supermerger](https://github.com/hako-mikan/sd-webui-supermerger)|
    |[continue-revolution/sd-webui-segment-anything](https://github.com/continue-revolution/sd-webui-segment-anything)|
    |[licyk/sd-webui-licyk-style-image](https://github.com/licyk/sd-webui-licyk-style-image)|
    |[w-e-w/sdwebui-close-confirmation-dialogue](https://github.com/w-e-w/sdwebui-close-confirmation-dialogue)|
    |[viyiviyi/stable-diffusion-webui-zoomimage](https://github.com/viyiviyi/stable-diffusion-webui-zoomimage)|
    
    |[Haoming02/Stable-Diffusion-WebUI-Forge-Classic](https://github.com/Haoming02/sd-webui-forge-classic)|
    |---|
    |[Coyote-A/ultimate-upscale-for-automatic1111](https://github.com/Coyote-A/ultimate-upscale-for-automatic1111)|
    |[DominikDoom/a1111-sd-webui-tagcomplete](https://github.com/DominikDoom/a1111-sd-webui-tagcomplete)|
    |[Bing-su/adetailer](https://github.com/Bing-su/adetailer)|
    |[zanllp/sd-webui-infinite-image-browsing](https://github.com/zanllp/sd-webui-infinite-image-browsing)|
    |[licyk/sd-webui-prompt-all-in-one](https://github.com/licyk/sd-webui-prompt-all-in-one)|
    |[hanamizuki-ai/stable-diffusion-webui-localization-zh_Hans](https://github.com/hanamizuki-ai/stable-diffusion-webui-localization-zh_Hans)|
    |[Haoming02/sd-webui-mosaic-outpaint](https://github.com/Haoming02/sd-webui-mosaic-outpaint)|
    |[Haoming02/sd-webui-resource-monitor](https://github.com/Haoming02/sd-webui-resource-monitor)|
    |[licyk/sd-webui-tcd-sampler](https://github.com/licyk/sd-webui-tcd-sampler)|
    |[licyk/advanced_euler_sampler_extension](https://github.com/licyk/advanced_euler_sampler_extension)|
    |[Akegarasu/sd-webui-model-converter](https://github.com/Akegarasu/sd-webui-model-converter)|
    |[licyk/stable-diffusion-webui-model-toolkit](https://github.com/licyk/stable-diffusion-webui-model-toolkit)|
    |[licyk/a1111-sd-webui-haku-img](https://github.com/licyk/a1111-sd-webui-haku-img)|
    |[licyk/sd-webui-licyk-style-image](https://github.com/licyk/sd-webui-licyk-style-image)|
    |[w-e-w/sdwebui-close-confirmation-dialogue](https://github.com/w-e-w/sdwebui-close-confirmation-dialogue)|
    |[viyiviyi/stable-diffusion-webui-zoomimage](https://github.com/viyiviyi/stable-diffusion-webui-zoomimage)|
    
    |[lshqqytiger/Stable-Diffusion-WebUI-AMDGPU](https://github.com/lshqqytiger/stable-diffusion-webui-amdgpu)|
    |---|
    |[Coyote-A/ultimate-upscale-for-automatic1111](https://github.com/Coyote-A/ultimate-upscale-for-automatic1111)|
    |[DominikDoom/a1111-sd-webui-tagcomplete](https://github.com/DominikDoom/a1111-sd-webui-tagcomplete)|
    |[Bing-su/adetailer](https://github.com/Bing-su/adetailer)|
    |[zanllp/sd-webui-infinite-image-browsing](https://github.com/zanllp/sd-webui-infinite-image-browsing)|
    |[huchenlei/sd-webui-openpose-editor](https://github.com/huchenlei/sd-webui-openpose-editor)|
    |[licyk/sd-webui-prompt-all-in-one](https://github.com/licyk/sd-webui-prompt-all-in-one)|
    |[licyk/sd-webui-wd14-tagger](https://github.com/licyk/sd-webui-wd14-tagger)|
    |[hanamizuki-ai/stable-diffusion-webui-localization-zh_Hans](https://github.com/hanamizuki-ai/stable-diffusion-webui-localization-zh_Hans)|
    |[Haoming02/sd-webui-mosaic-outpaint](https://github.com/Haoming02/sd-webui-mosaic-outpaint)|
    |[Haoming02/sd-webui-resource-monitor](https://github.com/Haoming02/sd-webui-resource-monitor)|
    |[licyk/sd-webui-tcd-sampler](https://github.com/licyk/sd-webui-tcd-sampler)|
    |[licyk/advanced_euler_sampler_extension](https://github.com/licyk/advanced_euler_sampler_extension)|
    |[hako-mikan/sd-webui-regional-prompter](https://github.com/hako-mikan/sd-webui-regional-prompter)|
    |[Akegarasu/sd-webui-model-converter](https://github.com/Akegarasu/sd-webui-model-converter)|
    |[Mikubill/sd-webui-controlnet](https://github.com/Mikubill/sd-webui-controlnet)|
    |[pkuliyi2015/multidiffusion-upscaler-for-automatic1111](https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111)|
    |[mcmonkeyprojects/sd-dynamic-thresholding](https://github.com/mcmonkeyprojects/sd-dynamic-thresholding)|
    |[hako-mikan/sd-webui-lora-block-weight](https://github.com/hako-mikan/sd-webui-lora-block-weight)|
    |[licyk/stable-diffusion-webui-model-toolkit](https://github.com/licyk/stable-diffusion-webui-model-toolkit)|
    |[licyk/a1111-sd-webui-haku-img](https://github.com/licyk/a1111-sd-webui-haku-img)|
    |[hako-mikan/sd-webui-supermerger](https://github.com/hako-mikan/sd-webui-supermerger)|
    |[continue-revolution/sd-webui-segment-anything](https://github.com/continue-revolution/sd-webui-segment-anything)|
    |[licyk/sd-webui-licyk-style-image](https://github.com/licyk/sd-webui-licyk-style-image)|
    |[w-e-w/sdwebui-close-confirmation-dialogue](https://github.com/w-e-w/sdwebui-close-confirmation-dialogue)|
    |[viyiviyi/stable-diffusion-webui-zoomimage](https://github.com/viyiviyi/stable-diffusion-webui-zoomimage)|
    
    |[vladmandic/SD.Next](https://github.com/vladmandic/sdnext)|
    |---|
    |[Coyote-A/ultimate-upscale-for-automatic1111](https://github.com/Coyote-A/ultimate-upscale-for-automatic1111)|
    |[DominikDoom/a1111-sd-webui-tagcomplete](https://github.com/DominikDoom/a1111-sd-webui-tagcomplete)|
    |[Bing-su/adetailer](https://github.com/Bing-su/adetailer)|
    |[zanllp/sd-webui-infinite-image-browsing](https://github.com/zanllp/sd-webui-infinite-image-browsing)|
    |[huchenlei/sd-webui-openpose-editor](https://github.com/huchenlei/sd-webui-openpose-editor)|
    |[licyk/sd-webui-prompt-all-in-one](https://github.com/licyk/sd-webui-prompt-all-in-one)|
    |[hanamizuki-ai/stable-diffusion-webui-localization-zh_Hans](https://github.com/hanamizuki-ai/stable-diffusion-webui-localization-zh_Hans)|
    |[Haoming02/sd-webui-mosaic-outpaint](https://github.com/Haoming02/sd-webui-mosaic-outpaint)|
    |[Haoming02/sd-webui-resource-monitor](https://github.com/Haoming02/sd-webui-resource-monitor)|
    |[licyk/sd-webui-tcd-sampler](https://github.com/licyk/sd-webui-tcd-sampler)|
    |[Akegarasu/sd-webui-model-converter](https://github.com/Akegarasu/sd-webui-model-converter)|
    |[mcmonkeyprojects/sd-dynamic-thresholding](https://github.com/mcmonkeyprojects/sd-dynamic-thresholding)|
    |[hako-mikan/sd-webui-lora-block-weight](https://github.com/hako-mikan/sd-webui-lora-block-weight)|
    |[licyk/a1111-sd-webui-haku-img](https://github.com/licyk/a1111-sd-webui-haku-img)|
    |[continue-revolution/sd-webui-segment-anything](https://github.com/continue-revolution/sd-webui-segment-anything)|
    |[licyk/sd-webui-licyk-style-image](https://github.com/licyk/sd-webui-licyk-style-image)|
    |[w-e-w/sdwebui-close-confirmation-dialogue](https://github.com/w-e-w/sdwebui-close-confirmation-dialogue)|
    |[viyiviyi/stable-diffusion-webui-zoomimage](https://github.com/viyiviyi/stable-diffusion-webui-zoomimage)|
    
    !!! note
        由于不同分支对扩展的兼容性不同，部分扩展在某些分支上不会被安装。
    

!!! note
    1. 如果运行 PowerShell 脚本出现闪退，说明 Windows 对 PowerShell 脚本的运行限制未解除，需要按照 [环境配置](install.md#_1) 中的方法进行解除。
    2. SD WebUI Installer 支持使用在命令行中通过参数配置 Stable Diffusion WebUI 的安装参数，具体说明可阅读 [使用命令运行 SD WebUI Installer](advanced.md#sd-webui-installer_1)。
