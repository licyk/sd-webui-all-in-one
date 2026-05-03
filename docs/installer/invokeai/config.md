# InvokeAI Installer 配置与镜像

## 配置管理

### 设置 InvokeAI 中文
InvokeAI 默认的界面语言为英文，在 InvokeAI 左下角的齿轮图标，点进 Settings，在 Language 选项选择简体中文即可将界面语言设置为中文。

### 设置 HuggingFace 镜像
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置) 中提到的的 `settings.ps1` 进行修改。

InvokeAI Installer 生成的 PowerShell 脚本中已设置了 HuggingFace 镜像源，如果需要自定义 HuggingFace 镜像源，可以在和脚本同级的目录创建 `mirror.txt` 文件，在文件中填写 HuggingFace 镜像源的地址后保存，再次启动脚本时将读取该文件的配置并设置 HuggingFace 镜像源。

|可用的 HuggingFace 镜像源 |
|---|
|https://hf-mirror.com|
|https://huggingface.sukaka.top|

如果需要禁用设置 HuggingFace 镜像源，在和脚本同级的目录中创建 `disable_mirror.txt` 文件，再次启动脚本时将禁用 HuggingFace 镜像源。

### 设置 Github 镜像源
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置) 中提到的的 `settings.ps1` 进行修改。

InvokeAI Installer 为了加速访问 Github 的速度，如加快下载和更新 InvokeAI 自定义节点的速度，默认在启动脚本时自动检测可用的 Github 镜像源并设置。如果需要自定义 Github 镜像源，可以在和脚本同级的目录创建 `gh_mirror.txt` 文件，在文件中填写 Github 镜像源的地址后保存，再次启动脚本时将取消自动检测可用的 Github 镜像源，而是读取该文件的配置并设置 Github 镜像源。

|可用的 Github 镜像源 |
|---|
|https://ghfast.top/https://github.com|
|https://mirror.ghproxy.com/https://github.com|
|https://gh.api.99988866.xyz/https://github.com|
|https://gitclone.com/github.com|
|https://gh-proxy.com/https://github.com|
|https://ghps.cc/https://github.com|
|https://gh.idayer.com/https://github.com|
|https://ghproxy.1888866.xyz/github.com|
|https://slink.ltd/https://github.com|
|https://github.boki.moe/github.com|
|https://github.moeyy.xyz/https://github.com|
|https://gh-proxy.net/https://github.com|
|https://gh-proxy.ygxz.in/https://github.com|
|https://wget.la/https://github.com|
|https://kkgithub.com|
|https://ghproxy.net/https://github.com|

如果需要禁用设置 Github 镜像源，在和脚本同级的目录中创建 `disable_gh_mirror.txt` 文件，再次启动脚本时将禁用 Github 镜像源。

### 设置 PyPI 镜像源
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置) 中提到的的 `settings.ps1` 进行修改。

InvokeAI Installer 默认启用了 PyPI镜像源加速下载 Python 软件包，如果需要禁用 PyPI镜像源，可以在脚本同级目录创建 `disable_pypi_mirror.txt` 文件，再次运行脚本时将 PyPI 源切换至官方源。

### 配置代理
如果出现某些文件无法下载，比如在控制台出现 `由于连接芳在一段时间后没有正确答复或连接的主机没有反应，连接尝试失败` 之类的报错时，可以尝试配置代理，有以下两种方法。

#### 1. 使用系统代理
在代理软件中启用系统代理，再运行脚本，这时候脚本将自动读取系统中的代理配置并设置代理。

#### 2. 使用配置文件
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置) 中提到的的 `settings.ps1` 进行修改。

在和脚本同级的路径中创建一个 `proxy.txt` 文件，在文件中填写代理地址，如`http://127.0.0.1:10809`，保存后运行脚本，这时候脚本会自动读取这个配置文件中的代理配置并设置代理。

!!! note
    **配置文件**的优先级高于**系统代理**配置，所以当同时使用了两种方式配置代理，脚本将优先使用**配置文件**中的代理配置。

#### 禁用自动设置代理
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置) 中提到的的 `settings.ps1` 进行修改。

在和脚本同级的路径中创建一个 `disable_proxy.txt` 文件，再次启动脚本时将禁用设置代理。

## 其他配置
### 设置 uv 包管理器
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置) 中提到的的 `settings.ps1` 进行修改。

InvokeAI Installer 默认使用了 uv 作为 Python 包管理器，大大加快管理 Python 软件包的速度（如安装 Python 软件包）。
如需禁用 uv，可在脚本所在目录创建一个 `disable_uv.txt` 文件，这将禁用 uv，并使用 Pip 作为 Python 包管理器。

!!! note
    当 uv 安装 Python 软件包失败时，将切换至 Pip 重试 Python 软件包的安装。

### 设置内核路径前缀
!!! info
    该设置可通过 [管理 InvokeAI Installer 设置](#管理-invokeai-installer-设置) 中提到的的 `settings.ps1` 进行修改。

InvokeAI Installer 通过路径前缀在安装目录中寻找 InvokeAI 内核并使用。查找时通过遍历 InvokeAI Installer 内部预设的列表，若该预设名有对应的文件夹名，则将该预设名作为内核路径前缀，并对该文件夹中的内核进行启动和管理。当未找到任何内核文件夹时，使用默认的内核路径前缀`core`。

内核路径前缀可手动指定，若内核文件夹在脚本所在路径中的名称为 `InvokeAI-aki-v1`，此时可在当前路径创建 `core_prefix.txt` 文件，并在文件中将刚刚的名称写进该文件中，即 `InvokeAI-aki-v1`，再保存文件，此时 InvokeAI Installer 将对该内核文件夹进行启动和管理。

内核路径前缀除了可以使用名称，还可以使用绝对路径或者相对路径，即 InvokeAI Installer 可以启动和管理在当前脚本所在路径之外的 InvokeAI。比如 InvokeAI 所在路径为`D:/Tools/AI/InvokeAI-aki-v1.1`。如果使用绝对路径，则直接将这个路径作为内核路径前缀，推荐使用这个方式，比较简单。

如果使用相对路径，此时需要知道 InvokeAI Installer 所在路径，比如`D:/Downloads/InvokeAI`，则可以得出内核路径前缀为`../../Tools/AI/InvokeAI-aki-v1.1`。

### 管理 InvokeAI Installer 设置
运行 `settings.ps1`，根据提示进行设置管理和调整。
