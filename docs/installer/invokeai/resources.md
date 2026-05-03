# InvokeAI Installer 模型与资源

## 资源管理

### 添加模型
如果没有下载模型，可以使用 `download_models.ps1` 脚本下载模型。这里也推荐使用 [HuggingFace](https://huggingface.co) 或者 [Civitai](https://civitai.com) 下载模型。在 InvokeAI 左侧栏选择模型管理器，在模型管理器中可以添加本地的模型或者下载模型，可以和 SD WebUI / InvokeAI 共享模型。具体可以查看 [Installing Models - InvokeAI Documentation](https://invoke-ai.github.io/InvokeAI/installation/050_INSTALLING_MODELS/)。

### 设置模型下载源
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](config.md#管理-invokeai-installer-设置) 中提到的的 `settings.ps1` 进行修改。

使用 `download_models.ps1` 脚本下载模型时，默认使用的下载源为 [ModelScope](https://modelscope.cn)，如果需要切换到 [HuggingFace](https://huggingface.co) 下载源，可以在和脚本同级的路径中创建一个 `disable_model_mirror.txt` 文件，再次启动 `download_models.ps1` 脚本时下载模型将使用 [HuggingFace](https://huggingface.co) 下载源。

### InvokeAI 的使用方法
推荐下面的教程：  
- [InvokeAI - SD Note](https://sdnote.netlify.app/guide/invokeai)
- [给所有想学习AI辅助绘画的人的入门课（基于 InvokeAI 3.7.0）](https://docs.qq.com/doc/p/9a03673f4a0493b4cd76babc901a49f0e6d52140)
- [InvokeAI 官方入门教程（基于 InvokeAI 5.x）](https://www.youtube.com/playlist?list=PLvWK1Kc8iXGrQy8r9TYg6QdUuJ5MMx-ZO)
- [一个使用 InvokeAI 5.0 的新统一画布完成常见任务的简述（升级到 InvokeAI 5.0 后必看）](https://www.youtube.com/watch?v=Tl-69JvwJ2s)
- [如何使用 InvokeAI 5.0 的新统一画布和工作流系统](https://www.youtube.com/watch?v=y80W3PjR0Gc)
- [InvokeAI 官方视频教程](https://www.youtube.com/@invokeai)
- [InvokeAI Documentation](https://invoke-ai.github.io/InvokeAI)
- [Solutions : Invoke Support Portal](https://support.invoke.ai/support/solutions)
- [Reddit 社区](https://www.reddit.com/r/invokeai)

除了上面的教程，也可以通过 Google 等平台搜索教程。

### 启用 InvokeAI 低显存模式
当显存较小，并且经常出现显存不足的问题，可尝试启用 InvokeAI 的低显存模式。

!!! info
    InvokeAI 低显存模式在 InvokeAI 5.6.0 的版本中被加入，如果当前 InvokeAI 的版本低于 5.6.0，需要运行 `update.ps1` 对 InvokeAI 进行更新。

在运行 `launch.ps1` 启动一次 InvokeAI 后，在`InvokeAI/invokeai` 路径将产生一个`invokeai.yaml` 文件，这就是 InvokeAI 的配置文件。

打开 `invokeai.yaml` 文件后，在该文件添加以下内容启用 InvokeAI 的低显存模式。

```yaml
enable_partial_loading: true
```

保存该文件并重新启动 InvokeAI 即可应用该设置。

如果在 VAE 解码阶段出现爆显存，还可以启用 Tiled VAE，在配置文件中添加一下参数进行启用。

```yaml
force_tiled_decode: true
```

!!! note
    关于 InvokeAI 低显存模式详细说明可阅读：[Low-VRAM mode - Invoke](https://invoke-ai.github.io/InvokeAI/features/low-vram)。
