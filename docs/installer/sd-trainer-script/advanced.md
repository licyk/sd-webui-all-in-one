# SD Trainer Script Installer 高级功能

## 高级功能

### 使用命令运行 SD Trainer Script Installer
SD Trainer Script Installer 支持使用命令参数设置安装 SD-Trainer-Script 的参数，支持的参数如下。

**参数清单**

- `-Help`：获取 SD Trainer Script Installer 的帮助信息。
- `-CorePrefix` `<内核路径前缀>`：设置内核路径前缀。可填写内核目录名、相对路径或绝对路径；绝对路径会在运行时转换为相对于安装器脚本目录的内核路径前缀。未指定时会按预设目录自动识别，未找到时使用 `core`。
- `-InstallPath` `<安装 SD Trainer Script 的绝对路径>`：指定 SD Trainer Script Installer 安装 SD Trainer Script 的路径，使用绝对路径表示。
    例如：`./sd_trainer_script_installer.ps1 -InstallPath "D:\Download"`，这将指定安装到 D:\Download 路径。
- `-PyTorchMirrorType` `<PyTorch 镜像源类型>`：指定安装 PyTorch 时使用的镜像源类型。可指定的类型包括：`cu113`, `cu117`, `cu118`, `cu121`, `cu124`, `cu126`, `cu128`, `cu129`, `cu130`, `rocm5.4.2`, `rocm5.6`, `rocm5.7`, `rocm6.0`, `rocm6.1`, `rocm6.2`, `rocm6.2.4`, `rocm6.3`, `rocm6.4`, `rocm7.1`, `rocm_rdna3`, `rocm_rdna3.5`, `rocm_rdna4`, `rocm_win`, `xpu`, `ipex_legacy_arc`, `cpu`, `directml`, `all`
- `-InstallPythonVersion` `<Python 版本>`：指定要安装的 Python 版本。可选值：`3.10`, `3.11`, `3.12`, `3.13`, `3.14`
- `-InstallBranch` `<安装的 SD Trainer Script 分支>`：指定安装的分支。未指定时默认安装 `kohya-ss/sd-scripts`。
    支持的分支如下：
    - `sd_scripts_main`: kohya-ss - sd-scripts 主分支
    - `sd_scripts_dev`: kohya-ss - sd-scripts 测试分支
    - `sd_scripts_sd3`: kohya-ss - sd-scripts SD3 分支
    - `ai_toolkit_main`: ostris - ai-toolkit 分支
    - `finetrainers_main`: a-r-r-o-w - finetrainers 分支
    - `diffusion_pipe_main`: tdrussell - diffusion-pipe 分支
    - `musubi_tuner_main`: kohya-ss - musubi-tuner 分支
- `-UseUpdateMode`：指定 SD Trainer Script Installer 使用更新模式，只对管理脚本进行更新。
- `-DisablePyPIMirror`：禁用 SD Trainer Script Installer 使用 PyPI镜像源，改用 PyPI 官方源。
- `-DisableAutoMirror`：禁用 CLI 自动镜像源选择。默认自动镜像启用时，Python CLI 会强制覆盖 PyPI / Github / HuggingFace / 模型下载源等手动镜像设置；需要手动控制这些镜像参数时，请添加该参数。
- `-DisableProxy`：禁用 SD Trainer Script Installer 自动设置代理服务器。
- `-UseCustomProxy` `<代理服务器地址>`：使用自定义的代理服务器地址。例如：`-UseCustomProxy "http://127.0.0.1:10809"`
- `-DisableUV`：禁用 SD Trainer Script Installer 使用 uv 安装 Python 软件包，改用 Pip 安装。
- `-DisableGithubMirror`：禁用 SD Trainer Script Installer 自动设置 Github 镜像源。
- `-UseCustomGithubMirror` `<Github 镜像站地址>`：使用自定义的 Github 镜像站地址。例如：`https://ghfast.top/https://github.com` 等。
- `-BuildMode`：启用构建模式，在基础安装结束后将调用管理脚本执行剩余任务。出现错误时不再暂停而是直接退出。
    多个脚本将按以下优先级执行：
    - `reinstall_pytorch.ps1`：对应`-BuildWithTorch`/`-BuildWithTorchReinstall`
    - `download_models.ps1`：对应`-BuildWithModel`
    - `switch_branch.ps1`：对应`-BuildWithBranch`
    - `update.ps1`：对应`-BuildWithUpdate`
    - `init.ps1`：对应`-BuildWithLaunch`
- `-BuildWithTorch` `<PyTorch 版本编号>`：(需添加 `-BuildMode`) 调用 `reinstall_pytorch.ps1` 脚本，根据版本编号安装指定的 PyTorch 版本。编号可运行该脚本查看。
- `-BuildWithTorchReinstall`：(需添加 `-BuildMode`及`-BuildWithTorch`) 执行 PyTorch 指定版本安装时使用强制重新安装模式。
- `-BuildWithModel` `<模型编号列表>`：(需添加 `-BuildMode`) 调用 `download_models.ps1` 脚本，根据编号列表下载模型。编号可运行该脚本查看。
- `-BuildWithBranch` `<SD Trainer Script 分支编号>`：(需添加 `-BuildMode`) 调用 `switch_branch.ps1` 脚本，根据分支编号切换分支。编号可运行该脚本查看。
- `-BuildWithUpdate`：(需添加 `-BuildMode`) 安装流程结束后调用 `update.ps1` 脚本，更新 SD Trainer Script 内核。
- `-BuildWithLaunch`：(需添加 `-BuildMode`) 安装流程结束后调用 `launch.ps1` (对应构建列表中的 `init.ps1`) 脚本，执行启动前的环境检查，但跳过启动程序。
- `-NoPreDownloadModel`：安装 SD Trainer Script 时跳过预下载模型。
- `-PyTorchPackage` `<PyTorch 软件包>`：(需搭配 `-xFormersPackage`) 指定安装的 PyTorch 版本。如：`-PyTorchPackage "torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118"`
- `-xFormersPackage` `<xFormers 软件包>`：(需搭配 `-PyTorchPackage`) 指定安装的 xFormers 版本。如：`-xFormersPackage "xformers===0.0.26.post1+cu118"`
- `-NoCleanCache`：安装结束后保留下载的 Python 软件包缓存。
- `-DisableModelMirror`：不使用 ModelScope 下载模型, 使用 HuggingFace 下载模型。
- `-NoPause`：脚本执行完成后不暂停, 直接退出。
- `-DisableUpdate`：(仅在构建模式生效且只作用于管理脚本) 禁用 SD Trainer Script Installer 更新检查。
- `-DisableHuggingFaceMirror`：(仅在构建模式生效且只作用于管理脚本) 禁用 HuggingFace 镜像源。
- `-UseCustomHuggingFaceMirror` `<HuggingFace 镜像源地址>`：(仅在构建模式生效且只作用于管理脚本) 使用自定义 HuggingFace 镜像源。例如：`-UseCustomHuggingFaceMirror "https://hf-mirror.com"`
- `-LaunchArg` `<SD Trainer Script 启动参数>`：(仅在构建模式生效且只作用于管理脚本) 设置自定义启动参数。如：`-LaunchArg "--fast --auto-launch"`
- `-DisableCUDAMalloc`：(仅在构建模式生效且只作用于管理脚本) 禁用通过 `PYTORCH_CUDA_ALLOC_CONF` / `PYTORCH_ALLOC_CONF` 环境变量设置 CUDA 内存分配器。
- `-DisableEnvCheck`：(仅在构建模式生效且只作用于管理脚本) 禁用检查 SD Trainer Script 运行环境问题。
- `-DisableHotpatcher`：(仅在构建模式生效且只作用于管理脚本) 禁用 Hotpatcher 补丁系统。
- `-HotpatcherConfig` `<配置文件路径>`：(仅在构建模式生效且只作用于管理脚本) 指定 Hotpatcher 配置文件路径。指定后不会自动创建默认配置。
- `-EnableHotpatcherRuntime`：启用 Hotpatcher runtime host 连接。
- `-HotpatcherPort` `<端口>`：(仅在构建模式生效且只作用于管理脚本) 指定 Hotpatcher runtime 模式通信端口，端口范围为 `1..65535`。

!!! note
    SD Trainer Script 不通过 Python `launch` 子命令启动训练器。`-BuildWithLaunch` 会把 Hotpatcher 参数转发给 `init.ps1`，由 `init.ps1` 在环境检查结束后设置 `PYTHONPATH` 和 `SD_WEBUI_ALL_IN_ONE_HOTPATCHER_*` 环境变量，后续训练命令会继承这些环境变量。

例如在 `D:/Download` 这个路径安装 [bmaltais/Kohya GUI](https://github.com/bmaltais/kohya_ss)，则在 SD Trainer Script Installer 所在路径打开 PowerShell，使用参数运行 SD Trainer Script Installer。

```powershell
./sd_trainer_script_installer.ps1 -InstallPath "D:/Download" -InstallBranch "kohya_gui"
```

### SD Trainer Script Installer 构建模式和普通安装模式
SD Trainer Script Installer 主要由两部分构成：安装脚本和环境管理脚本。

在 SD Trainer Script Installer 默认的普通安装模式下，只执行最基础的安装流程，而像其他的流程，如 PyTorch 版本更换，模型安装，运行环境检查和修复等并不会执行，这些步骤是在 SD Trainer Script Installer 管理脚本中进行，如执行 `init.ps1`，`reinstall_pytorch.ps1` 脚本等。

而 SD Trainer Script Installer 构建模式允许在执行基础安装流程后，调用 SD Trainer Script Installer 管理脚本完成这些步骤。基于这个特性，启用构建模式的 SD Trainer Script Installer 可用于整合包制作，搭配自动化平台可实现全自动制作整合包。

构建模式需要使用命令行参数进行启用，具体可阅读 [使用命令运行 SD Trainer Script Installer](advanced.md#sd-trainer-script-installer_1) 中的参数说明。

!!! info
    通常安装 SD-Trainer-Script 并不需要使用 SD Trainer Script Installer 构建模式进行安装，使用默认的普通安装模式即可。构建模式多用于自动化制作整合包。

使用 Github Action 提供的容器可用于运行 SD Trainer Script Installer 并启用构建模式，实现自动化制作整合包，Github Action 工作流代码可参考：[build_sd_scripts.yml · licyk/sd-webui-all-in-one](https://github.com/licyk/sd-webui-all-in-one/blob/main/.github/workflows/build_sd_scripts.yml)

### 编写训练脚本
进行模型训练需要编写代码来调用训练器进行训练，下面将介绍如何进行编写。

#### 如何编写
SD Trainer Script Installer 在安装时将会生成一个 `train.ps1` 脚本，可用于编写训练命令。该脚本的内容如下

```powershell
#################################################
# 初始化基础环境变量，以正确识别到运行环境
& "$PSScriptRoot/init.ps1"
Set-Location $PSScriptRoot
# 此处的代码不要修改或者删除，否则可能会出现意外情况
# 
# SD-Trainer-Script 环境初始化后提供以下变量便于使用
# 
# ${ROOT_PATH}               当前目录
# ${SD_SCRIPTS_PATH}         训练脚本所在目录
# ${DATASET_PATH}            数据集目录
# ${MODEL_PATH}              模型下载器下载的模型路径
# ${GIT_EXEC}                Git 路径
# ${PYTHON_EXEC}             Python 解释器路径
# 
# 下方可编写训练代码
# 编写训练命令可参考：https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md#%E7%BC%96%E5%86%99%E8%AE%AD%E7%BB%83%E8%84%9A%E6%9C%AC
# 编写结束后，该文件必须使用 UTF-8 with BOM 编码保存
#################################################

#################################################
Write-Host "训练结束，退出训练脚本"
Read-Host | Out-Null # 训练结束后保持控制台不被关闭
```

该脚本在执行时将会运行 `init.ps1` 用于初始化环境（在`& "$PSScriptRoot/init.ps1"`部分），使训练所需的环境能够被正确识别，这是必须的步骤。在执行完 `init.ps1` 后将设置一些路径变量可供使用，并且将会显示出来，可以在部分路径变量指出的路径放置训练所需的文件方便使用。

`Set-Location $PSScriptRoot` 将切换目录到 `train.ps1` 所在路径。

必要的步骤执行后，下方的训练命令就可以执行了，这里尝试编写一个训练模型命令。以下的训练命令基于 [kohya-ss/sd-scripts](https://github.com/kohya-ss/sd-scripts)，不同的训练器所使用的训练参数各不同，需阅读项目的文档进行了解。

```powershell
#################################################
# 初始化基础环境变量, 以正确识别到运行环境
& "$PSScriptRoot/init.ps1"
Set-Location $PSScriptRoot
# 此处的代码不要修改或者删除, 否则可能会出现意外情况
# 
# SD-Trainer-Script 环境初始化后提供以下变量便于使用
# 
# ${ROOT_PATH}               当前目录
# ${SD_SCRIPTS_PATH}         训练脚本所在目录
# ${DATASET_PATH}            数据集目录
# ${MODEL_PATH}              模型下载器下载的模型路径
# ${OUTPUT_PATH}             保存训练模型的路径
# ${GIT_EXEC}                Git 路径
# ${PYTHON_EXEC}             Python 解释器路径
# 
# 下方可编写训练代码
# 编写训练命令可参考: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md#%E7%BC%96%E5%86%99%E8%AE%AD%E7%BB%83%E8%84%9A%E6%9C%AC
# 编写结束后, 该文件必须使用 UTF-8 with BOM 编码保存
#################################################

python "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=12 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.0001 `
    --unet_lr=0.0001 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
        preset="full" `
    --optimizer_args `
        weight_decay=0.05 `
        betas="0.9,0.95" `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --debiased_estimation_loss `
    --vae_batch_size=4 `
    --full_fp16

#################################################
Write-Host "训练结束, 退出训练脚本"
Read-Host | Out-Null # 训练结束后保持控制台不被关闭
```

这是一段在 SDXL 模型上训练 LoRA 的训练命令，每一行参数使用 ` 符号进行换行，而最后一行参数则不需要该符号进行换行。

在最后一行 `Read-Host | Out-Null` 是为了在训练结束后保持控制台不被关闭。

训练命令编写完成后，将该文件保存下来，再运行 `train.ps1` 即可开始训练。

除了编辑 `train.ps1` 进行训练，也可以自行创建 PowerShell 脚本并按照要求进行编写。

!!! warning
    `train.ps1` 文件或者其他 PowerShell 脚本需要将保存编码设置为`UTF-8 BOM`，否则将出现乱码或者运行异常的问题。

#### kohya-ss/sd-scripts 训练命令参考
下面是 [kohya-ss/sd-scripts](https://github.com/kohya-ss/sd-scripts) 不同的训练参数例子，可用于参考。

```powershell
# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
#
# 这个参数在 animagine-xl-3.1.safetensors 测试, 大概在 30 ~ 40 Epoch 有比较好的效果 (在 36 Epoch 出好效果的概率比较高)
#
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/animagine-xl-3.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=50 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.0001 `
    --unet_lr=0.0001 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="cosine_with_restarts" `
    --lr_warmup_steps=0 `
    --lr_scheduler_num_cycles=1 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16

# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
#
# 这个参数是在 Illustrious-XL-v0.1.safetensors 模型上测出来的, 大概在 32 Epoch 左右有比较好的效果
# 用 animagine-xl-3.1.safetensors 那套参数也有不错的效果, 只是学习率比这套低了点, 学得慢一点
#
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.00012 `
    --unet_lr=0.00012 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="cosine_with_restarts" `
    --lr_warmup_steps=0 `
    --lr_scheduler_num_cycles=1 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16

# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
#
# 这个参数是在 Illustrious-XL-v0.1.safetensors 模型上测出来的, 大概在 32 Epoch 左右有比较好的效果
# 用 animagine-xl-3.1.safetensors 那套参数也有不错的效果, 只是学习率比这套低了点, 学得慢一点
# 学习率调度器从 cosine_with_restarts 换成 constant_with_warmup, 此时学习率靠优化器(Lion8bit)进行调度
# 拟合速度会更快
# constant_with_warmup 用在大规模的训练上比较好, 但用在小规模训练也有不错的效果
# 如果训练集的图比较少, 重复的图较多, 重复次数较高, 可能容易造成过拟合
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.00012 `
    --unet_lr=0.00012 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16

# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
#
# 这个参数是在 Illustrious-XL-v0.1.safetensors 模型上测出来的, 大概在 32 Epoch 左右有比较好的效果
# 用 animagine-xl-3.1.safetensors 那套参数也有不错的效果, 只是学习率比这套低了点, 学得慢一点
# 学习率调度器从 cosine_with_restarts 换成 constant_with_warmup, 此时学习率靠优化器(Lion8bit)进行调度
# 拟合速度会更快
# constant_with_warmup 用在大规模的训练上比较好, 但用在小规模训练也有不错的效果
# 如果训练集的图比较少, 重复的图较多, 重复次数较高, 可能容易造成过拟合
# 
# 在 --network_args 设置了 preset，可以调整训练网络的大小
# 该值默认为 full，而使用 attn-mlp 可以得到更小的 LoRA 但几乎不影响 LoRA 效果
# 可用的预设可阅读文档: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/docs/Preset.md
# 该预设也可以自行编写并指定, 编写例子可查看: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/example_configs/preset_configs/example.toml
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.00012 `
    --unet_lr=0.00012 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
        preset="attn-mlp" `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16

# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
#
# 这个参数是在 Illustrious-XL-v0.1.safetensors 模型上测出来的, 大概在 32 Epoch 左右有比较好的效果
# 用 animagine-xl-3.1.safetensors 那套参数也有不错的效果, 只是学习率比这套低了点, 学得慢一点
# 学习率调度器从 cosine_with_restarts 换成 constant_with_warmup, 此时学习率靠优化器(Lion8bit)进行调度
# 拟合速度会更快
# constant_with_warmup 用在大规模的训练上比较好, 但用在小规模训练也有不错的效果
# 如果训练集的图比较少, 重复的图较多, 重复次数较高, 可能容易造成过拟合
# 
# 在 --network_args 设置了 preset，可以调整训练网络的大小
# 该值默认为 full，而使用 attn-mlp 可以得到更小的 LoRA 但几乎不影响 LoRA 效果
# 可用的预设可阅读文档: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/docs/Preset.md
# 该预设也可以自行编写并指定, 编写例子可查看: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/example_configs/preset_configs/example.toml
# 
# 使用 --optimizer_args 设置 weight_decay 和 betas, 更高的 weight_decay 可以降低拟合程度, 减少过拟合
# 如果拟合程度不够高, 可以提高 --max_train_epochs 的值, 或者适当降低 weight_decay 的值, 可自行测试
# 较小的训练集适合使用较小的值, 如 0.05, 较大的训练集适合用 0.1
# 当 weight_decay 设置为 0.05 时, 大概在 38 Epoch 有比较好的效果
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.00012 `
    --unet_lr=0.00012 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
        preset="attn-mlp" `
    --optimizer_args `
        weight_decay=0.1 `
        betas="0.9,0.95" `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16

# (自己在用的)
# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
# 
# 学习率调度器从 cosine_with_restarts 换成 constant_with_warmup, 此时学习率靠优化器(Lion8bit)进行调度
# 拟合速度会更快
# constant_with_warmup 用在大规模的训练上比较好, 但用在小规模训练也有不错的效果
# 如果训练集的图比较少, 重复的图较多, 重复次数较高, 可能容易造成过拟合
# 
# 在 --network_args 设置了 preset, 可以调整训练网络的大小
# 该值默认为 full, 如果使用 attn-mlp 可以得到更小的 LoRA, 但对于难学的概念使用 full 效果会更好
# 
# 可用的预设可阅读文档: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/docs/Preset.md
# 该预设也可以自行编写并指定, 编写例子可查看: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/example_configs/preset_configs/example.toml
# 
# 使用 --optimizer_args 设置 weight_decay 和 betas, 更高的 weight_decay 可以降低拟合程度, 减少过拟合
# 如果拟合程度不够高, 可以提高 --max_train_epochs 的值, 或者适当降低 weight_decay 的值, 可自行测试
# 较小的训练集适合使用较小的值, 如 0.05, 较大的训练集适合用 0.1
# 大概 34 Epoch 会有比较好的效果吧, 不过不好说, 看训练集
# 自己测的时候大概在 26~40 Epoch 之间会出现好结果, 测试了很多炉基本都在这个区间里, 但也不排除意外情况 (训练参数这东西好麻烦啊, 苦い)
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.0001 `
    --unet_lr=0.0001 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
        preset="full" `
    --optimizer_args `
        weight_decay=0.05 `
        betas="0.9,0.95" `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16

# (自己在用的)
# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
# 
# 学习率调度器从 cosine_with_restarts 换成 constant_with_warmup, 此时学习率靠优化器(Lion8bit)进行调度
# 拟合速度会更快
# constant_with_warmup 用在大规模的训练上比较好, 但用在小规模训练也有不错的效果
# 如果训练集的图比较少, 重复的图较多, 重复次数较高, 可能容易造成过拟合
# 
# 在 --network_args 设置了 preset, 可以调整训练网络的大小
# 该值默认为 full, 如果使用 attn-mlp 可以得到更小的 LoRA, 但对于难学的概念使用 full 效果会更好 (最好还是 full 吧, 其他的预设效果不是很好)
# 
# 可用的预设可阅读文档: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/docs/Preset.md
# 该预设也可以自行编写并指定, 编写例子可查看: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/example_configs/preset_configs/example.toml
# 
# 使用 --optimizer_args 设置 weight_decay 和 betas, 更高的 weight_decay 可以降低拟合程度, 减少过拟合
# 如果拟合程度不够高, 可以提高 --max_train_epochs 的值, 或者适当降低 weight_decay 的值, 可自行测试
# 较小的训练集适合使用较小的值, 如 0.05, 较大的训练集适合用 0.1
# 大概 34 Epoch 会有比较好的效果吧, 不过不好说, 看训练集
# 自己测的时候大概在 26~40 Epoch 之间会出现好结果, 测试了很多炉基本都在这个区间里, 但也不排除意外情况 (训练参数这东西好麻烦啊, 苦い)
# 
# 测试的时候发现 --debiased_estimation_loss 对于训练效果的有些改善
# 这里有个对比: https://licyk.netlify.app/2025/02/10/debiased_estimation_loss_in_stable_diffusion_model_training
# 启用后能提高拟合速度和颜色表现吧, 画风的学习能学得更好
# 但, 肢体崩坏率可能会有点提高, 不过有另一套参数去优化了一下这个问题, 貌似会好一点
# debiased estimation loss 有个相关的论文可以看看: https://arxiv.org/abs/2310.08442
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.0001 `
    --unet_lr=0.0001 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
        preset="full" `
    --optimizer_args `
        weight_decay=0.05 `
        betas="0.9,0.95" `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --debiased_estimation_loss `
    --vae_batch_size=4 `
    --full_fp16

# (自己在用的)
# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
# 
# 学习率调度器从 cosine_with_restarts 换成 constant_with_warmup, 此时学习率靠优化器(Lion8bit)进行调度
# 拟合速度会更快
# constant_with_warmup 用在大规模的训练上比较好, 但用在小规模训练也有不错的效果
# 如果训练集的图比较少, 重复的图较多, 重复次数较高, 可能容易造成过拟合
# 
# 在 --network_args 设置了 preset, 可以调整训练网络的大小
# 该值默认为 full, 如果使用 attn-mlp 可以得到更小的 LoRA, 但对于难学的概念使用 full 效果会更好 (最好还是 full 吧, 其他的预设效果不是很好)
# 
# 可用的预设可阅读文档: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/docs/Preset.md
# 该预设也可以自行编写并指定, 编写例子可查看: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/example_configs/preset_configs/example.toml
# 
# 使用 --optimizer_args 设置 weight_decay 和 betas, 更高的 weight_decay 可以降低拟合程度, 减少过拟合
# 如果拟合程度不够高, 可以提高 --max_train_epochs 的值, 或者适当降低 weight_decay 的值, 可自行测试
# 较小的训练集适合使用较小的值, 如 0.05, 较大的训练集适合用 0.1
# 大概 34 Epoch 会有比较好的效果吧, 不过不好说, 看训练集
# 自己测的时候大概在 26~40 Epoch 之间会出现好结果, 测试了很多炉基本都在这个区间里, 但也不排除意外情况 (训练参数这东西好麻烦啊, 苦い)
# 
# 测试的时候发现 --debiased_estimation_loss 对于训练效果的有些改善
# 这里有个对比: https://licyk.netlify.app/2025/02/10/debiased_estimation_loss_in_stable_diffusion_model_training
# 启用后能提高拟合速度和颜色表现吧, 画风的学习能学得更好
# 但, 肢体崩坏率可能会有点提高, 不过有另一套参数去优化了一下这个问题, 貌似会好一点
# 可能画风会弱化, 所以不是很确定哪个比较好用, 只能自己试了
# debiased estimation loss 有个相关的论文可以看看: https://arxiv.org/abs/2310.08442
# 
# 加上 v 预测参数进行训练, 提高模型对暗处和亮处的表现效果, 并且能让模型能够直出纯黑色背景, 画面也更干净
# 相关的论文可以看看: https://arxiv.org/abs/2305.08891
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/noobaiXLNAIXL_vPred10Version.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.0001 `
    --unet_lr=0.0001 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
        preset="full" `
    --optimizer_args `
        weight_decay=0.05 `
        betas="0.9,0.95" `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --debiased_estimation_loss `
    --vae_batch_size=4 `
    --zero_terminal_snr `
    --v_parameterization `
    --scale_v_pred_loss_like_noise_pred `
    --full_fp16

# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
# 
# 在 --network_args 设置了 preset, 可以调整训练网络的大小
# 该值默认为 full, 如果使用 attn-mlp 可以得到更小的 LoRA, 但对于难学的概念使用 full 效果会更好 (最好还是 full 吧, 其他的预设效果不是很好)
# 
# 可用的预设可阅读文档: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/docs/Preset.md
# 该预设也可以自行编写并指定, 编写例子可查看: https://github.com/KohakuBlueleaf/LyCORIS/blob/main/example_configs/preset_configs/example.toml
# 
# 使用 --optimizer_args 设置 weight_decay 和 betas, 更高的 weight_decay 可以降低拟合程度, 减少过拟合
# 如果拟合程度不够高, 可以提高 --max_train_epochs 的值, 或者适当降低 weight_decay 的值, 可自行测试
# 较小的训练集适合使用较小的值, 如 0.05, 较大的训练集适合用 0.1
# 大概 34 Epoch 会有比较好的效果吧, 不过不好说, 看训练集
# 自己测的时候大概在 26~40 Epoch 之间会出现好结果, 测试了很多炉基本都在这个区间里, 但也不排除意外情况 (训练参数这东西好麻烦啊, 苦い)
# 
# 测试的时候发现 --debiased_estimation_loss 对于训练效果的有些改善
# 这里有个对比: https://licyk.netlify.app/2025/02/10/debiased_estimation_loss_in_stable_diffusion_model_training
# 启用后能提高拟合速度和颜色表现吧, 画风的学习能学得更好
# 把学习率调度器 constant_with_warmup 换成了cosine, 稍微缓解了一下拟合速度过快导致肢体崩坏率增大的问题
# 如果学的效果不够好, 拟合度不够高, 可以适当增加 --max_train_epochs 的值或者提高训练集的重复次数
# debiased estimation loss 有个相关的论文可以看看: https://arxiv.org/abs/2310.08442
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.0001 `
    --unet_lr=0.0001 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="cosine" `
    --lr_warmup_steps=0 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
        preset="full" `
    --optimizer_args `
        weight_decay=0.05 `
        betas="0.9,0.95" `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --debiased_estimation_loss `
    --vae_batch_size=4 `
    --full_fp16

# 使用 lokr 算法训练 XL 人物 LoRA, 使用多卡进行训练
# 适合极少图或者单图训练集进行人物 LoRA 训练
# 训练集使用打标器进行打标后, 要保留的人物的哪些特征, 就把对应的 Tag 删去, 触发词可加可不加
# 
# 该参数使用 scale_weight_norms 降低过拟合程度, 进行训练时, 可在控制台输出看到 Average key norm 这个值
# 通常测试 LoRA 时就测试 Average key norm 值在 0.5 ~ 0.9 之间的保存的 LoRA 模型
# max_train_epochs 设置为 200, save_every_n_epochs 设置为 1 以为了更好的挑选最好的结果
# 
# 可使用该方法训练一个人物 LoRA 模型用于生成人物的图片, 并将这些图片重新制作成训练集
# 再使用不带 scale_weight_norms 的训练参数进行训练, 通过这种方式, 可以在图片极少的情况下得到比较好的 LoRA 模型
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=200 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.00012 `
    --unet_lr=0.00012 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=1 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --scale_weight_norms=1 `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16

# 使用 lokr 算法训练 XL 画风 LoRA, 使用 rtx 4060 8g laptop 进行训练, 通过 fp8 降低显存占用
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
#
# 这个参数是在 Illustrious-XL-v0.1.safetensors 模型上测出来的, 大概在 32 Epoch 左右有比较好的效果
# 用 animagine-xl-3.1.safetensors 那套参数也有不错的效果, 只是学习率比这套低了点, 学得慢一点
# 学习率调度器从 cosine_with_restarts 换成 constant_with_warmup, 此时学习率靠优化器(Lion8bit)进行调度
# 拟合速度会更快
# constant_with_warmup 用在大规模的训练上比较好, 但用在小规模训练也有不错的效果
# 如果训练集的图比较少, 重复的图较多, 重复次数较高, 可能容易造成过拟合
# 
python "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=3 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.0002 `
    --unet_lr=0.0002 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="AdamW8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --fp8_base

# 使用 lokr 算法训练 XL 画风 LoRA, 使用多卡进行训练
# 该参数也可以用于人物 LoRA 训练
# 
# 在训练多画风 LoRA 或者人物 LoRA 时, 通常会打上触发词
# 当使用了 --network_train_unet_only 后, Text Encoder 虽然不会训练, 但并不影响将触发词训练进 LoRA 模型中
# 并且不训练 Text Encoder 避免 Text Encoder 被炼烂(Text Encoder 比较容易被炼烂)
#
# 这个参数是在 Illustrious-XL-v0.1.safetensors 模型上测出来的, 大概在 32 Epoch 左右有比较好的效果
# 用 animagine-xl-3.1.safetensors 那套参数也有不错的效果, 只是学习率比这套低了点, 学得慢一点
# 学习率调度器从 cosine_with_restarts 换成 constant_with_warmup, 此时学习率靠优化器(Lion8bit)进行调度
# 拟合速度会更快
# constant_with_warmup 用在大规模的训练上比较好, 但用在小规模训练也有不错的效果
# 如果训练集的图比较少, 重复的图较多, 重复次数较高, 可能容易造成过拟合
# 
# 参数加上了 noise_offset, 可以提高暗处和亮处的表现, 一般使用设置成 0.05 ~ 0.1
# 但 noise_offset 可能会导致画面泛白, 光影效果变差
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/Illustrious-XL-v0.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/Nachoneko" `
    --output_name="Nachoneko_2" `
    --output_dir="${OUTPUT_PATH}/Nachoneko" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.00012 `
    --unet_lr=0.00012 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --noise_offset=0.1 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16

# 使用 lokr 算法训练 XL 人物 LoRA, 使用多卡进行训练
# 参数中使用了 --scale_weight_norms, 用于提高泛化性, 但可能会造成拟合度降低
# 如果当训练人物 LoRA 的图片较多时, 可考虑删去该参数
# 当训练人物 LoRA 的图片较少, 为了避免过拟合, 就可以考虑使用 --scale_weight_norms 降低过拟合概率
#
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/animagine-xl-3.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/robin" `
    --output_name="robin_1" `
    --output_dir="${OUTPUT_PATH}/robin_1" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=50 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --learning_rate=0.0001 `
    --unet_lr=0.0001 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="cosine_with_restarts" `
    --lr_warmup_steps=0 `
    --lr_scheduler_num_cycles=1 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --scale_weight_norms=1 `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16

# 使用 lokr 算法训练 XL 人物 LoRA, 使用多卡进行训练
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/animagine-xl-3.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/murasame_(senren)_3" `
    --output_name="murasame_(senren)_10" `
    --output_dir="${OUTPUT_PATH}/murasame_(senren)_10" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=50 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --learning_rate=0.0001 `
    --unet_lr=0.0001 `
    --text_encoder_lr=0.00004 `
    --lr_scheduler="cosine_with_restarts" `
    --lr_warmup_steps=0 `
    --lr_scheduler_num_cycles=1 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --scale_weight_norms=1 `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16

# 使用 lokr 算法训练 XL 画风 LoRA, 使用单卡进行训练 (Kaggle 的单 Tesla P100 性能不如双 Tesla T4, 建议使用双卡训练)
python "${SD_SCRIPTS_PATH}/sdxl_train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/animagine-xl-3.1.safetensors" `
    --vae="${MODEL_PATH}/sdxl_fp16_fix_vae.safetensors" `
    --train_data_dir="${DATASET_PATH}/rafa" `
    --output_name="rafa_1" `
    --output_dir="${OUTPUT_PATH}/rafa" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="1024,1024" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=4096 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=50 `
    --train_batch_size=6 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.00007 `
    --unet_lr=0.00007 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="cosine_with_restarts" `
    --lr_warmup_steps=0 `
    --lr_scheduler_num_cycles=1 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16

# 使用 lokr 算法训练 SD1.5 画风 LoRA, 使用双卡进行训练
# 使用 NovelAI 1 模型进行训练
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/animefull-final-pruned.safetensors" `
    --vae="${MODEL_PATH}/vae-ft-mse-840000-ema-pruned.safetensors" `
    --train_data_dir="${DATASET_PATH}/sunfish" `
    --output_name="nai1-sunfish_5" `
    --output_dir="${OUTPUT_PATH}/nai1-sunfish_5" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="768,768" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=1024 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=12 `
    --gradient_checkpointing `
    --network_train_unet_only `
    --learning_rate=0.00024 `
    --unet_lr=0.00024 `
    --text_encoder_lr=0.00001 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16

# 使用 lokr 算法训练 SD1.5 多画风(多概念) LoRA, 使用双卡进行训练
# 使用 NovelAI 1 模型进行训练
# 
# 在 SD1.5 中训练 Text Encoder 可以帮助模型更好的区分不同的画风(概念)
# 
python -m accelerate.commands.launch `
    --num_cpu_threads_per_process=1 `
    --multi_gpu `
    --num_processes=2 `
    "${SD_SCRIPTS_PATH}/train_network.py" `
    --pretrained_model_name_or_path="${MODEL_PATH}/animefull-final-pruned.safetensors" `
    --vae="${MODEL_PATH}/vae-ft-mse-840000-ema-pruned.safetensors" `
    --train_data_dir="${DATASET_PATH}/sunfish" `
    --output_name="nai1-sunfish_5" `
    --output_dir="${OUTPUT_PATH}/nai1-sunfish_5" `
    --wandb_run_name="Nachoneko" `
    --log_tracker_name="lora-Nachoneko" `
    --prior_loss_weight=1 `
    --resolution="768,768" `
    --enable_bucket `
    --min_bucket_reso=256 `
    --max_bucket_reso=1024 `
    --bucket_reso_steps=64 `
    --save_model_as="safetensors" `
    --save_precision="fp16" `
    --save_every_n_epochs=1 `
    --max_train_epochs=40 `
    --train_batch_size=12 `
    --gradient_checkpointing `
    --learning_rate=0.00028 `
    --unet_lr=0.00028 `
    --text_encoder_lr=0.000015 `
    --lr_scheduler="constant_with_warmup" `
    --lr_warmup_steps=100 `
    --optimizer_type="Lion8bit" `
    --network_module="lycoris.kohya" `
    --network_dim=100000 `
    --network_alpha=100000 `
    --network_args `
        conv_dim=100000 `
        conv_alpha=100000 `
        algo=lokr `
        dropout=0 `
        factor=8 `
        train_norm=True `
    --log_with="tensorboard" `
    --logging_dir="${OUTPUT_PATH}/logs" `
    --caption_extension=".txt" `
    --shuffle_caption `
    --keep_tokens=0 `
    --max_token_length=225 `
    --seed=1337 `
    --mixed_precision="fp16" `
    --xformers `
    --cache_latents `
    --cache_latents_to_disk `
    --persistent_data_loader_workers `
    --vae_batch_size=4 `
    --full_fp16
```

#### 使用 TensorBoard 查看训练情况
这里可以编写一个 `tensorboard.ps1` 脚本用于运行 TensorBoard。

```powershell
# 初始化基础环境变量，以正确识别到运行环境
& "$PSScriptRoot/init.ps1"

# TensorBoard 日志路径
$LOG_DIR = "${OUTPUT_PATH}/logs"

python -m tensorboard.main `
    --host=127.0.0.1 `
    --port=8899 `
    --logdir="${LOG_DIR}"

# 运行这个脚本后将会在 http://127.0.0.1:8899 打开 TensorBoard 的网页界面
```

保存后右键运行即可启动。
