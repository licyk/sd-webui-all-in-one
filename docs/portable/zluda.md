# AMD ZLUDA 使用

本文适用于 Windows 平台的 AMD RX 系列显卡和 AMD 780M / 680M 核显用户，通过绘世启动器启用 ZLUDA 引擎运行 SD WebUI、SD WebUI Forge、ComfyUI 或 Fooocus。

目前在 ROCm 未在 Windows 上正式发布，则 AMD 显卡想要在 Windows 平台上跑图，需要借助 ZLUDA 进行转译。Installer 暂未提供 ZLUDA 功能支持（因技术原因），所以需使用绘世启动器提供 ZLUDA 功能支持，下面介绍了在 SD WebUI 上的操作方法，同时该方法也适用于 SD WebUI Forge、ComfyUI 和 Fooocus。

!!! info
    方法适用于 AMD RX 系列显卡和 AMD 780M 显卡，除了 SD WebUI 可以用这个方式，SD WebUI Forge、ComfyUI 和 Fooocus 都可以用，可自行测试。

## 1. 安装 SD WebUI
在 [整合包下载](./portable.md) 里找到 Stable Diffusion WebUI 整合包，下 Stable 版或者 Nightly 版都可以，然后解压。不用整合包安装的方式也可以用 Installer 从头一键安装，去  [SD WebUI Installer](../installer/sd-webui/index.md) 文档里按照说明操作就行。

!!! note
    **如果用的是整合包就直接跳过这蓝色部分的说明**，整合包用的是 Installer 的构建模式制作出来的，把绘世启动器什么的都配置好了。而自己使用 Installer 安装环境的话，如果只是使用默认参数直接右键启动安装脚本，是不会做额外的环境配置（除非根据 Installer 文档使用构建模式去启动安装脚本）。
    
    要做的额外步骤如下：
    
    ### 切换 SD WebUI 分支到测试分支
    在安装目录中找到 switch_branch.ps1，右键运行，然后选择`AUTOMATIC1111 - Stable-Diffusion-WebUI 测试分支`并切换。
    
    <img width="1716" height="1027" alt="Image" src="https://github.com/user-attachments/assets/c5b5a756-cd4e-430e-b871-e725b37f14f1" />
    
    ### 安装绘世启动器
    在安装目录中找到 terminal.ps1，右键运行，运行后会打开终端，输入下面的命令后回车运行。
    
    ```powershell
    Install-Hanamizuki
    ```
    
    <img width="1699" height="1007" alt="Image" src="https://github.com/user-attachments/assets/0d56c7b2-7935-481b-92d8-ae6a6a29de5d" />
    
    这样额外步骤就做完了。

## 2. 安装 HIP SDK
打开 [AMD HIP SDK for Windows](https://www.amd.com/en/developer/resources/rocm-hub/hip-sdk.html) 这个下载页面，找到 OS 是 Windows 10 & 11 和 ROCm Version 是 5.7.1 的那行，点右边的下载。

<img width="1484" height="993" alt="Image" src="https://github.com/user-attachments/assets/9e82ec1c-d065-4d8c-bf50-923d3aa4ae46" />

在下载页面翻到最底下有个 Accept 按钮，点击就可以下载 HIP SDK。

下载完成后就可以安装，一直点下一步就行，如果系统里安装了其他版本的 HIP SDK 就先卸载掉，再安装。**安装完成后必须重启电脑！**

## 3. 重装 PyTorch
默认带的 PyTorch 是没法正常跑 ZLUDA 的，要重新安装，在安装目录中找到 reinstall_pytorch.ps1，右键运行，选择`Torch 2.3.0 (CUDA 11.8) + xFormers 0.0.26.post1`这个 PyTorch 组合后重新安装。

<img width="1722" height="1036" alt="Image" src="https://github.com/user-attachments/assets/6b0b0217-38e6-4bee-8240-8473103a827d" />

## 4. 额外配置 ZLUDA
!!! info
    如果 AMD 显卡的型号是 AMD 780M / 680M，就需要额外的配置 ZLUDA，其他 AMD 显卡可以跳过这个步骤。

下载 [780m_20240321_163205.7z](https://modelscope.cn/models/licyks/sdnote/resolve/master/other/780m_20240321_163205.7z) 这个压缩包，然后把压缩包里的 2 个文件解压到 SD WebUI 内核目录。

<img width="1200" height="333" alt="Image" src="https://github.com/user-attachments/assets/7f9d3a00-b48b-4072-b7c1-0a989b776916" />

<img width="1186" height="886" alt="Image" src="https://github.com/user-attachments/assets/152a8d13-e2df-41dc-994d-f19a3ea19d1c" />

<img width="1227" height="877" alt="Image" src="https://github.com/user-attachments/assets/995b4b95-23fe-4e9a-a9ab-7c5ca53429bf" />

## 5. 安装模型
在安装目录中找到 download_models.ps1，右键运行，找个合适的模型下载就行。

如果是 AMD 780M 显卡，那点显存只能跑 SD1.5 的模型，推荐 nai1-artist_all_in_one_merge.safetensors。

<img width="1698" height="1015" alt="Image" src="https://github.com/user-attachments/assets/22821c48-9c32-446d-b137-cf69dc8d5661" />

如果是 AMD RX 系列的显卡，可以下 SDXL 的模型，推荐这几个。

<img width="1709" height="1024" alt="Image" src="https://github.com/user-attachments/assets/a87bdbc3-20f4-44ea-891f-e1f4e7aa75e9" />

## 6. 使用绘世启动器启动
在安装目录中找到 hanamizuki.bat，双击打开后就会启动绘世启动器，在绘世启动器的高级选项中，可以选择 ZLUDA 引擎去启动。

<img width="1898" height="1175" alt="Image" src="https://github.com/user-attachments/assets/18e7df0e-2c66-49de-8832-5d0d0a078b77" />

选择 ZLUDA 引擎后就可以点一键启动去启动 SD WebUI。

<img width="1910" height="1187" alt="Image" src="https://github.com/user-attachments/assets/747b48a6-89fc-4553-8e1a-07cc9ec038c7" />

第一次启动会经历非常长时间的 ZLUDA 转译，快的话 20 分钟左右，慢的话可能一两个小时，这个只能等。

## 7. 跑图测试
提示词放这了。

- 正面提示词
```
tyomimas,
1girl,solo,cat ears,animal ear fluff,hair ornament,hair bow,long hair,blonde hair,low ponytail,twintails,blue eyes,open mouth,blue bow,dress,blue dress,braid,short sleeves,white frills,
holding pillow,pillow hug,sitting,on couch,looking at viewer,light smile,open mouth,
couch,indoors,room,desk,vase,flower,
front view,
masterpiece,best quality,newest,
```

- 负面提示词
```
low quality,worst quality,normal quality,text,signature,jpeg artifacts,bad anatomy,old,early,copyright name,watermark,artist name,signature,
```

跑图时也会有 ZLUDA 转译，只能等，完整跑完一次图后一般就不会有 ZLUDA 转译的过程了。

<img width="1238" height="1281" alt="Image" src="https://github.com/user-attachments/assets/820449e4-6ec8-43c2-b855-90f2cf475979" />

<img width="863" height="998" alt="Image" src="https://github.com/user-attachments/assets/d32290a1-638c-47fb-b750-9d0923a80c94" />

出现`OutOfMemoryError: CUDA out of memory`就把分辨率调小点，再启用 Tiled VAE。

出现`NansException: A tensor with NaNs was produced in Unet.`就在绘世启动器的**性能设置 -> 计算精度设置**里把**开启 UNet 模型半精度优化关了**，不过爆显存概率会增大很多。
