# SD WebUI Installer 安装

## 安装
SD WebUI Installer 默认情况下安装的是 [AUTOMATIC1111/Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) 分支，如果需要指定安装的分支，需要在 SD WebUI Installer 所在路径创建配置文件，以下为不同配置文件对应的 Stable Diffusion WebUI 分支。

|配置文件名 | 对应安装的分支|
|---|---|
|`install_sd_webui.txt`|[AUTOMATIC1111/Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)|
|`install_sd_webui_forge.txt`|[lllyasviel/Stable-Diffusion-WebUI-Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)|
|`install_sd_webui_reforge.txt`|[Panchovix/Stable-Diffusion-WebUI-reForge](https://github.com/Panchovix/stable-diffusion-webui-reForge)|
|`install_sd_webui_forge_classic.txt`|[Haoming02/Stable-Diffusion-WebUI-Forge-Classic](https://github.com/Haoming02/sd-webui-forge-classic)|
|`install_sd_webui_amdgpu.txt`|[lshqqytiger/Stable-Diffusion-WebUI-AMDGPU](https://github.com/lshqqytiger/stable-diffusion-webui-amdgpu)|
|`install_sd_next.txt`|[vladmandic/SD.Next](https://github.com/vladmandic/sdnext)|

创建配置文件后，将 SD WebUI Installer 下载至本地，和配置文件放在一起，如下所示。

```
.
├── 119966207_p0_master1200.jpg
├── 437A9AE81C043B83110F55316EC7789E.png
├── BaiduNetdiskDownload
├── BaiduNetdiskWorkspace
├── install_sd_webui.txt                  # 这是配置文件
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
    - [设置 Github 镜像源](config.md#设置-github-镜像源)
    - [设置 PyPI 镜像源](config.md#设置-pypi-镜像源)
    - [设置 uv 包管理器](config.md#设置-uv-包管理器)
    - [配置代理](config.md#配置代理)
    - [设置内核路径前缀](config.md#设置内核路径前缀)
    - [设置模型下载源](resources.md#设置模型下载源)
    
    通常这些参数不需要配置，保持默认即可，如有需要再根据说明进行配置。

|SD WebUI Installer 下载地址|
|---|
|[下载地址 1](https://github.com/licyk/sd-webui-all-in-one/releases/download/stable_diffusion_webui_installer/stable_diffusion_webui_installer.ps1)|
|[下载地址 2](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/stable_diffusion_webui_installer/stable_diffusion_webui_installer.ps1)|
|[下载地址 3](https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/stable_diffusion_webui_installer.ps1)|
|[下载地址 4](https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/stable_diffusion_webui_installer.ps1)|
|[下载地址 5](https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/stable_diffusion_webui_installer.ps1)|

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
    1. 如果运行 PowerShell 脚本出现闪退，说明 Windows 对 PowerShell 脚本的运行限制未解除，需要按照 [环境配置](environment.md#环境配置) 中的方法进行解除。
    2. SD WebUI Installer 支持使用在命令行中通过参数配置 Stable Diffusion WebUI 的安装参数，具体说明可阅读 [使用命令运行 SD WebUI Installer](advanced.md#使用命令运行-sd-webui-installer)。
