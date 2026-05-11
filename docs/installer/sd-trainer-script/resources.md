# SD Trainer Script Installer 模型与资源

## 资源管理

### 添加模型
在 SD-Trainer-Script 中可以选择本地已下载的模型，如果没有下载某些用于训练的模型（非融合模型），可以使用 `download_models.ps1` 脚本下载模型。这里也推荐使用 [HuggingFace](https://huggingface.co) 或者 [Civitai](https://civitai.com) 下载模型。

### 设置模型下载源
!!! info
    该设置可通过 [管理 SD Trainer Script Installer 设置](config.md#sd-trainer-script-installer_1) 中提到的 `settings.ps1` 进行修改。

使用 `download_models.ps1` 脚本下载模型时，默认使用的下载源为 [ModelScope](https://modelscope.cn)，如果需要切换到 [HuggingFace](https://huggingface.co) 下载源，可以在和脚本同级的路径中创建一个 `disable_model_mirror.txt` 文件，再次启动 `download_models.ps1` 脚本时下载模型将使用 [HuggingFace](https://huggingface.co) 下载源。

### 模型训练的方法
推荐的哔哩哔哩 UP 主：

- 青龙圣者：https://space.bilibili.com/219296
- 秋葉aaaki：https://space.bilibili.com/12566101
- 琥珀青葉：https://space.bilibili.com/507303431

观看这些 UP 主的视频可获得一些训练模型的教程。

其他的一些训练模型的教程：

- https://sd-moadel-doc.maozi.io
- https://rentry.org/59xed3
- https://civitai.com/articles/2056
- https://civitai.com/articles/124/lora-analogy-about-lora-trainning-and-using
- https://civitai.com/articles/143/some-shallow-understanding-of-lora-training-lora
- https://civitai.com/articles/632/why-this-lora-can-not-bring-good-result-lora
- https://civitai.com/articles/726/an-easy-way-to-make-a-cosplay-lora-cosplay-lora
- https://civitai.com/articles/2135/lora-quality-improvement-some-experiences-about-datasets-and-captions-lora
- https://civitai.com/articles/2297/ways-to-make-a-character-lora-that-is-easier-to-change-clothes-lora

除了上面的教程，也可以通过哔哩哔哩、Google 等平台搜索教程。
