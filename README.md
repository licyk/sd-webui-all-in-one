# sd-webui-all-in-one
这是一个支持部署多种 WebUI 的 Jupyter Notebook，支持部署以下 WebUI：
- 1、[Stable-Diffusion-WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
- 2、[ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- 3、[InvokeAI](https://github.com/invoke-ai/InvokeAI)
- 4、[Fooocus](https://github.com/lllyasviel/Fooocus)
- 5、[lora-scripts](https://github.com/Akegarasu/lora-scripts)
- 6、[kohya_ss](https://github.com/bmaltais/kohya_ss)

使用时请按顺序执行 Jupyter Notebook 单元。

## 主要功能
1. 功能初始化：导入 SD WebUI All In One 所使用的功能
2. 参数配置：配置安装参数和远程访问方式
3. 应用参数配置：应用已设置的参数
4. 安装：根据配置安装对应的 WebUI
5. 启动：根据配置启动对应的 WebUI

## 其他功能
1. 自定义模型 / 扩展下载配置：设置要下载的模型 / 扩展参数
2. 自定义模型 / 扩展下载：根据配置进行下载模型 / 扩展
3. 更新：将已安装的 WebUI 进行更新

## 提示
1. 在参数配置界面，请填写工作区路径，选择要使用的 WebUI，根据自己的需求选择内网穿透方式（用于访问 WebUI 界面），再根据自己的需求选择模型和扩展。
2. 已知 CloudFlare、Gradio 内网穿透会导致 [Kaggle](https://www.kaggle.com) 平台强制关机，在使用 [Kaggle](https://www.kaggle.com) 平台时请勿勾选这两个选项。
3. 若使用 [Colab](https://colab.research.google.com) 平台，请注意该 Jupyter Notebook 无法在免费版的 Colab 账号中使用，运行前将会收到 Colab 的警告提示，强行运行将会导致 Colab 强制关机（如果 Colab 账号已付费订阅可直接使用该 Jupyter Notebook），可选择仓库中其他的  Jupyter Notebook（将 Colab 中禁止的 WebUI 移除了）。
4. [Ngrok](https://ngrok.com) 内网穿透的稳定性高，使用前需要填写 Ngrok Token，可在 [Ngrok](https://ngrok.com) 官网获取。
5. 在启动时将启动内网穿透，可在控制台输出中看到内网穿透地址，用于访问 WebUI 界面。
