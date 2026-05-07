# ComfyUI Installer 模型与资源

## 资源管理

### 共享 Stable Diffusion WebUI 的模型
在 ComfyUI 启动一次后，在 ComfyUI 的根目录会生成一个 extra_model_paths.yaml.example 共享目录示例文件，通过修改这个文件可以使 ComfyUI 共享 Stable Diffusion WebUI 的模型文件。

这是一个例子，我的 Stable Diffusion WebUI 路径在`E:/Softwares/stable-diffusion-webui`，则将这个示例文件的 `base_path:` 后面的路径改成 Stable Diffusion WebUI 的路径。

```yaml
#Rename this to extra_model_paths.yaml and ComfyUI will load it

#config for a1111 ui
#all you have to do is change the base_path to where yours is installed
a111:
    base_path: E:/Softwares/stable-diffusion-webui # 填写 Stable Diffusion WebUI 的路径，注意冒号后面必须有空格

    checkpoints: models/Stable-diffusion # 大模型
    configs: models/Stable-diffusion # 大模型配置文件
    vae: models/VAE # VAE 模型
    loras: | # LoRA 模型
         models/Lora
         models/LyCORIS
    upscale_models: | # 放大模型
                  models/ESRGAN
                  models/RealESRGAN
                  models/SwinIR
    embeddings: embeddings # Embedding 模型
    hypernetworks: models/hypernetworks # Hypernetwork 模型
    controlnet: models/Controlnet # ControlNet 模型
    ipadapter: models/Controlnet # IP Adapter 模型
    clip_vision: extensions/sd-webui-controlnet/annotator/downloads/clip_vision # clip_vision 模型
    # AnimateDiff 模型共享的说明：https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved?tab=readme-ov-file#model-setup
    animatediff_models: extensions/sd-webui-animatediff/model # AnimateDiff 模型
    animatediff_motion_lora: extensions/sd-webui-animatediff/model # AnimateDiff LoRA 模型

#config for comfyui
#your base path should be either an existing comfy install or a central folder where you store all of your models, loras, etc.

comfyui:
#     base_path: path/to/comfyui/
#     checkpoints: models/checkpoints/
#     clip: models/clip/
#     configs: models/configs/
#     controlnet: models/controlnet/
#     embeddings: models/embeddings/
#     loras: models/loras/
#     upscale_models: models/upscale_models/
#     vae: models/vae/
#     classifiers: models/classifiers/
#     clip_vision: models/clip_vision/
#     diffusers: models/diffusers/
#     diffusion_models: models/diffusion_models/
#     gligen: models/gligen/
#     hypernetworks: models/hypernetworks/
#     photomaker: models/photomaker/
#     style_models: models/style_models/
#     unet: models/unet/
#     vae_approx: models/vae_approx/
#     animatediff_models: models/animatediff_models/
#     animatediff_motion_lora: models/animatediff_motion_lora/
#     animatediff_video_formats: models/animatediff_video_formats/
#     ipadapter: models/ipadapter/
#     liveportrait: models/liveportrait/
#     insightface: models/insightface/
#     layerstyle: models/layerstyle/
#     LLM: models/LLM/
#     Joy_caption: models/Joy_caption/
#     sams: models/sams/
#     blip: models/blip/
#     CogVideo: models/CogVideo/
#     xlabs: models/xlabs/
#     instantid: models/instantid/
#     custom_nodes: custom_nodes/

#other_ui:
#    base_path: path/to/ui
#    checkpoints: models/checkpoints
#    gligen: models/gligen
#    custom_nodes: path/custom_nodes
```

### 下载模型
可以使用 `download_models.ps1` 脚本下载模型。这里也推荐使用 [HuggingFace](https://huggingface.co) 或者 [Civitai](https://civitai.com) 下载模型。

### 设置模型下载源
!!! info
    该设置可通过 [管理 ComfyUI Installer 设置](config.md#comfyui-installer_1) 中提到的 `settings.ps1` 进行修改。

使用 `download_models.ps1` 脚本下载模型时，默认使用的下载源为 [ModelScope](https://modelscope.cn)，如果需要切换到 [HuggingFace](https://huggingface.co) 下载源，可以在和脚本同级的路径中创建一个 `disable_model_mirror.txt` 文件，再次启动 `download_models.ps1` 脚本时下载模型将使用 [HuggingFace](https://huggingface.co) 下载源。

### ComfyUI 使用方法
推荐的哔哩哔哩 UP 主：
- 只剩一瓶辣椒酱：https://space.bilibili.com/35723238
- 秋葉aaaki：https://space.bilibili.com/12566101

ComfyUI 的使用教程：
- [ComfyUI 使用教程 - SD Note](https://sdnote.netlify.app/guide/comfyui)
- [ComfyUI 常见问题 - SD Note](https://sdnote.netlify.app/help/comfyui)
- https://docs.comfy.org/zh-CN/get_started/first_generation
- https://www.aigodlike.com
- https://space.bilibili.com/35723238/channel/collectiondetail?sid=1320931
- https://comfyanonymous.github.io/ComfyUI_examples
- https://blenderneko.github.io/ComfyUI-docs
- https://comfyui-wiki.com/zh
