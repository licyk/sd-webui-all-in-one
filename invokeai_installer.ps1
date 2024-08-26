# 有关 PowerShell 脚本保存编码的问题: https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_character_encoding?view=powershell-7.4#the-byte-order-mark
Set-Location "$PSScriptRoot"
# Pip 镜像源
$PIP_INDEX_MIRROR = "https://mirrors.cloud.tencent.com/pypi/simple"
$PIP_EXTRA_INDEX_MIRROR = "https://mirror.baidu.com/pypi/simple"
$PIP_FIND_MIRROR = "https://mirror.sjtu.edu.cn/pytorch-wheels/cu118/torch_stable.html"
$PIP_EXTRA_INDEX_MIRROR_CU121 = "https://mirror.sjtu.edu.cn/pytorch-wheels/cu121"
$PIP_FIND_MIRROR_CU121 = "https://mirror.sjtu.edu.cn/pytorch-wheels/cu121/torch_stable.html"
# PATH
$PYTHON_PATH = "$PSScriptRoot/InvokeAI/python"
$PYTHON_SCRIPTS_PATH = "$PSScriptRoot/InvokeAI/python/Scripts"
$Env:PATH = "$PYTHON_PATH$([System.IO.Path]::PathSeparator)$PYTHON_SCRIPTS_PATH$([System.IO.Path]::PathSeparator)$Env:PATH"
# 环境变量
$Env:PIP_INDEX_URL = $PIP_INDEX_MIRROR
$Env:PIP_EXTRA_INDEX_URL = $PIP_EXTRA_INDEX_MIRROR
$Env:PIP_FIND_LINKS = $PIP_FIND_MIRROR
$Env:UV_INDEX_URL = $PIP_INDEX_MIRROR
# $Env:UV_EXTRA_INDEX_URL = $PIP_EXTRA_INDEX_MIRROR
# $Env:UV_FIND_LINKS = $PIP_FIND_MIRROR
$Env:UV_LINK_MODE = "copy"
$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
$Env:PIP_TIMEOUT = 30
$Env:PIP_RETRIES = 5
$Env:CACHE_HOME = "$PSScriptRoot/InvokeAI/cache"
$Env:HF_HOME = "$PSScriptRoot/InvokeAI/cache/huggingface"
$Env:MATPLOTLIBRC = "$PSScriptRoot/InvokeAI/cache"
$Env:MODELSCOPE_CACHE = "$PSScriptRoot/InvokeAI/cache/modelscope/hub"
$Env:MS_CACHE_HOME = "$PSScriptRoot/InvokeAI/cache/modelscope/hub"
$Env:SYCL_CACHE_DIR = "$PSScriptRoot/InvokeAI/cache/libsycl_cache"
$Env:TORCH_HOME = "$PSScriptRoot/InvokeAI/cache/torch"
$Env:U2NET_HOME = "$PSScriptRoot/InvokeAI/cache/u2net"
$Env:XDG_CACHE_HOME = "$PSScriptRoot/InvokeAI/cache"
$Env:PIP_CACHE_DIR = "$PSScriptRoot/InvokeAI/cache/pip"
$Env:PYTHONPYCACHEPREFIX = "$PSScriptRoot/InvokeAI/cache/pycache"
$Env:INVOKEAI_ROOT = "$PSScriptRoot/InvokeAI/invokeai"
$Env:UV_CACHE_DIR = "$PSScriptRoot/InvokeAI/cache/uv"
$Env:UV_PYTHON = "$PSScriptRoot/InvokeAI/python/python.exe"


# 消息输出
function Print-Msg ($msg) {
    Write-Host "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")][InvokeAI Installer]:: $msg"
}

Print-Msg "初始化中"

# 代理配置
$Env:NO_PROXY = "localhost,127.0.0.1,::1"
if (!(Test-Path "$PSScriptRoot/disable_proxy.txt")) { # 检测是否禁用自动设置镜像源
    $internet_setting = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    if (Test-Path "$PSScriptRoot/proxy.txt") { # 本地存在代理配置
        $proxy_value = Get-Content "$PSScriptRoot/proxy.txt"
        $Env:HTTP_PROXY = $proxy_value
        $Env:HTTPS_PROXY = $proxy_value
        Print-Msg "检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理"
    } elseif ($internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        $Env:HTTP_PROXY = "http://$($internet_setting.ProxyServer)"
        $Env:HTTPS_PROXY = "http://$($internet_setting.ProxyServer)"
        Print-Msg "检测到系统设置了代理, 已读取系统中的代理配置并设置代理"
    }
} else {
    Print-Msg "检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理"
}

# 设置 uv 的使用状态
if (Test-Path "./disable_uv.txt") {
    Print-Msg "检测到 disable_uv.txt 配置文件, 已禁用 uv, 使用 Pip 作为 Python 包管理器"
    $USE_UV = $false
} else {
    Print-Msg "默认启用 uv 作为 Python 包管理器, 加快 Python 软件包的安装速度"
    $USE_UV = $true
}

# 下载并解压 Python
function Install-Python {
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/python-3.10.11-embed-amd64.zip"

    # 下载 Python
    Print-Msg "正在下载 Python"
    Invoke-WebRequest -Uri $url -OutFile "./InvokeAI/python-3.10.11-embed-amd64.zip"
    if ($?) { # 检测是否下载成功并解压
        # 创建 Python 文件夹
        if (!(Test-Path "./InvokeAI/python")) {
            New-Item -ItemType Directory -Force -Path ./InvokeAI/python > $null
        }
        # 解压 Python
        Print-Msg "正在解压 Python"
        Expand-Archive -Path "./InvokeAI/python-3.10.11-embed-amd64.zip" -DestinationPath "./InvokeAI/python" -Force
        Remove-Item -Path "./InvokeAI/python-3.10.11-embed-amd64.zip"
        Modify-PythonPath
        Print-Msg "Python 安装成功"
    } else {
        Print-Msg "Python 安装失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 修改 python310._pth 文件的内容
function Modify-PythonPath {
    Print-Msg "修改 python310._pth 文件内容"
    $content = @("python310.zip", ".", "", "# Uncomment to run site.main() automatically", "import site")
    Set-Content -Path "./InvokeAI/python/python310._pth" -Value $content
}


# 配置 Python 的 Pip 模块
function Install-Pip {
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/get-pip.py"

    # 下载 get-pip.py
    Print-Msg "正在下载 get-pip.py"
    Invoke-WebRequest -Uri $url -OutFile "./InvokeAI/cache/get-pip.py"
    if ($?) { # 检测是否下载成功
        # 执行 get-pip.py
        Print-Msg "通过 get-pip.py 安装 Pip 中"
        python ./InvokeAI/cache/get-pip.py --no-warn-script-location
        if ($?) { # 检测是否安装成功
            Remove-Item -Path "./InvokeAI/cache/get-pip.py"
            Print-Msg "Pip 安装成功"
        } else {
            Remove-Item -Path "./InvokeAI/cache/get-pip.py"
            Print-Msg "Pip 安装失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
            Read-Host | Out-Null
            exit 1
        }
    } else {
        Print-Msg "下载 get-pip.py 失败"
        Print-Msg "Pip 安装失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 下载 uv
function Install-uv {
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/uv.exe"
    Print-Msg "正在下载 uv"
    Invoke-WebRequest -Uri $url -OutFile "./InvokeAI/cache/uv.exe"
    if ($?) {
        Move-Item -Path "./InvokeAI/cache/uv.exe" -Destination "./InvokeAI/python/Scripts/uv.exe"
        Print-Msg "uv 下载成功"
    } else {
        Print-Msg "uv 下载失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 安装 InvokeAI
function Install-InvokeAI {
    # 下载 InvokeAI
    Print-Msg "正在下载 InvokeAI"
    if ($USE_UV) {
        uv pip install InvokeAI --no-deps --find-links $PIP_FIND_MIRROR
    } else {
        python -m pip install InvokeAI --no-deps --no-warn-script-location --use-pep517
    }
    if ($?) { # 检测是否下载成功
        Print-Msg "InvokeAI 安装成功"
    } else {
        Print-Msg "InvokeAI 安装失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 安装 InvokeAI 依赖
function Install-InvokeAI-Requirements {
    $content = "
from importlib.metadata import requires

requirements = requires('invokeai')

for i in requirements:
    if i.startswith('torch=='):
        torch_ver = i.split(';')[0]

    if i.startswith('torchvision=='):
        torchvision_ver = i.split(';')[0]

    if i.startswith('xformers=='):
        xformers_ver = i.split(';')[0]

print(f'{torch_ver}+cu118 {torchvision_ver}+cu118 {xformers_ver}+cu118')
"

    $requirements = $(python -c "$content")
    Print-Msg "安装 InvokeAI 依赖中"
    if ($USE_UV) {
        uv pip install "InvokeAI[xformers]" $requirements.ToString().Split() --find-links $PIP_FIND_MIRROR
    } else {
        python -m pip install "InvokeAI[xformers]" $requirements.ToString().Split() --no-warn-script-location --use-pep517
    }
    if ($?) {
        Print-Msg "InvokeAI 依赖安装成功"
    } else {
        Print-Msg "InvokeAI 依赖安装失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 下载 PyPatchMatch
function Install-PyPatchMatch {
    # PyPatchMatch
    $url_1 = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/libpatchmatch_windows_amd64.dll"
    $url_2 = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/opencv_world460.dll"

    if (!(Test-Path "./InvokeAI/python/Lib/site-packages/patchmatch/libpatchmatch_windows_amd64.dll")) {
        Print-Msg "下载 libpatchmatch_windows_amd64.dll 中"
        Invoke-WebRequest -Uri $url_1 -OutFile "./InvokeAI/cache/libpatchmatch_windows_amd64.dll"
        if ($?) {
            Move-Item -Path "./InvokeAI/cache/libpatchmatch_windows_amd64.dll" -Destination "./InvokeAI/python/Lib/site-packages/patchmatch/libpatchmatch_windows_amd64.dll"
            Print-Msg "下载 libpatchmatch_windows_amd64.dll 成功"
        } else {
            Print-Msg "下载 libpatchmatch_windows_amd64.dll 失败"
        }
    } else {
        Print-Msg "无需下载 libpatchmatch_windows_amd64.dll"
    }

    if (!(Test-Path "./InvokeAI/python/Lib/site-packages/patchmatch/opencv_world460.dll")) {
        Print-Msg "下载 opencv_world460.dll 中"
        Invoke-WebRequest -Uri $url_2 -OutFile "./InvokeAI/cache/opencv_world460.dll"
        if ($?) {
            Move-Item -Path "./InvokeAI/cache/opencv_world460.dll" -Destination "./InvokeAI/python/Lib/site-packages/patchmatch/opencv_world460.dll"
            Print-Msg "下载 opencv_world460.dll 成功"
        } else {
            Print-Msg "下载 opencv_world460.dll 失败"
        }
    } else {
        Print-Msg "无需下载 opencv_world460.dll"
    }
}


# 下载配置文件
function Download-Config-File($url, $path) {
    $length = $url.split("/").length
    $name = $url.split("/")[$length - 1]
    if (!(Test-Path $path)) {
        Print-Msg "下载 $name 中"
        Invoke-WebRequest -Uri $url.ToString() -OutFile "./InvokeAI/cache/$name"
        if ($?) {
            Move-Item -Path "./InvokeAI/cache/$name" -Destination "$path"
            Print-Msg "$name 下载成功"
        } else {
            Print-Msg "$name 下载失败"
        }
    } else {
        Print-Msg "$name 已存在"
    }
}


# 预下载模型配置文件
function Get-Model-Config-File {
    Print-Msg "预下载模型配置文件中"
    New-Item -ItemType Directory -Path "./InvokeAI/invokeai/configs/stable-diffusion" -Force > $null
    New-Item -ItemType Directory -Path "./InvokeAI/invokeai/configs/controlnet" -Force > $null
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_base.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/sd_xl_base.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_inpaint.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/sd_xl_inpaint.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_refiner.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/sd_xl_refiner.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-finetune.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v1-finetune.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-finetune_style.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v1-finetune_style.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inference-v.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v1-inference-v.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inference.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v1-inference.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inpainting-inference.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v1-inpainting-inference.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-m1-finetune.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v1-m1-finetune.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inference-v.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v2-inference-v.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inference.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v2-inference.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inpainting-inference-v.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v2-inpainting-inference-v.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inpainting-inference.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v2-inpainting-inference.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-midas-inference.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v2-midas-inference.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/controlnet/cldm_v15.yaml" "./InvokeAI/invokeai/configs/controlnet/cldm_v15.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/controlnet/cldm_v21.yaml" "./InvokeAI/invokeai/configs/controlnet/cldm_v21.yaml"
    Print-Msg "模型配置文件下载完成"
}


# 安装
function Check-Install {
    if (!(Test-Path "./InvokeAI")) {
        New-Item -ItemType Directory -Path "./InvokeAI" > $null
    }

    if (!(Test-Path "./InvokeAI/cache")) {
        New-Item -ItemType Directory -Path "./InvokeAI/cache" > $null
    }

    Print-Msg "检测是否安装 Python"
    if (Test-Path "./InvokeAI/python/python.exe") {
        Print-Msg "Python 已安装"
    } else {
        Print-Msg "Python 未安装"
        Install-Python
    }

    Print-Msg "检查是否安装 Pip"
    python -c "import pip" 2> $null
    if ($?) {
        Print-Msg "Pip 已安装"
    } else {
        Print-Msg "Pip 未安装"
        Install-Pip
    }

    Print-Msg "检测是否安装 uv"
    if (Test-Path "./InvokeAI/python/Scripts/uv.exe") {
        Print-Msg "uv 已安装"
    } else {
        Print-Msg "uv 未安装"
        Install-uv
    }

    Print-Msg "检查是否安装 InvokeAI"
    if (Test-Path "./InvokeAI/python/Scripts/invokeai-web.exe") {
        Print-Msg "InvokeAI 已安装"
    } else {
        Print-Msg "InvokeAI 未安装"
        Install-InvokeAI
    }

    Install-InvokeAI-Requirements

    # Print-Msg "检测是否需要重装 xFormers"
    # Reinstall-Xformers

    Print-Msg "检测是否需要安装 PyPatchMatch"
    Install-PyPatchMatch

    Print-Msg "检测是否需要下载模型配置文件"
    Get-Model-Config-File
}


# 启动脚本
function Write-Launch-Script {
    $content = "
Set-Location `"`$PSScriptRoot`"
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
}
Print-Msg `"初始化中`"

# 代理配置
`$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
if (!(Test-Path `"`$PSScriptRoot/disable_proxy.txt`")) { # 检测是否禁用自动设置镜像源
    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
        `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
    } elseif (`$internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        `$Env:HTTP_PROXY = `"http://`$(`$internet_setting.ProxyServer)`"
        `$Env:HTTPS_PROXY = `"http://`$(`$internet_setting.ProxyServer)`"
        Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
} else {
    Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
}

# Huggingface 镜像源
if (!(Test-Path `"`$PSScriptRoot/disable_mirror.txt`")) { # 检测是否禁用了自动设置huggingface镜像源
    if (Test-Path `"`$PSScriptRoot/mirror.txt`") { # 本地存在huggingface镜像源配置
        `$hf_mirror_value = Get-Content `"`$PSScriptRoot/mirror.txt`"
        `$Env:HF_ENDPOINT = `$hf_mirror_value
        Print-Msg `"检测到本地存在 mirror.txt 配置文件, 已读取该配置并设置 HuggingFace 镜像源`"
    } else { # 使用默认设置
        `$Env:HF_ENDPOINT = `"https://hf-mirror.com`"
        Print-Msg `"使用默认 HuggingFace 镜像源`"
    }
} else {
    Print-Msg `"检测到本地存在 disable_mirror.txt 镜像源配置文件, 禁用自动设置 HuggingFace 镜像源`"
}

# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
# 环境变量
`$Env:PIP_INDEX_URL = `"$PIP_INDEX_MIRROR`"
`$Env:PIP_EXTRA_INDEX_URL = `"$PIP_EXTRA_INDEX_MIRROR`"
`$Env:PIP_FIND_LINKS = `"$PIP_FIND_MIRROR`"
`$Env:UV_INDEX_URL = `"$PIP_INDEX_MIRROR`"
# `$Env:UV_EXTRA_INDEX_URL = `"$PIP_EXTRA_INDEX_MIRROR`"
# `$Env:UV_FIND_LINKS = `"$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$Env:PIP_TIMEOUT = 30
`$Env:PIP_RETRIES = 5
`$Env:CACHE_HOME = `"`$PSScriptRoot/cache`"
`$Env:HF_HOME = `"`$PSScriptRoot/cache/huggingface`"
`$Env:MATPLOTLIBRC = `"`$PSScriptRoot/cache`"
`$Env:MODELSCOPE_CACHE = `"`$PSScriptRoot/cache/modelscope/hub`"
`$Env:MS_CACHE_HOME = `"`$PSScriptRoot/cache/modelscope/hub`"
`$Env:SYCL_CACHE_DIR = `"`$PSScriptRoot/cache/libsycl_cache`"
`$Env:TORCH_HOME = `"`$PSScriptRoot/cache/torch`"
`$Env:U2NET_HOME = `"`$PSScriptRoot/cache/u2net`"
`$Env:XDG_CACHE_HOME = `"`$PSScriptRoot/cache`"
`$Env:PIP_CACHE_DIR = `"`$PSScriptRoot/cache/pip`"
`$Env:PYTHONPYCACHEPREFIX = `"`$PSScriptRoot/cache/pycache`"
`$Env:INVOKEAI_ROOT = `"`$PSScriptRoot/invokeai`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"

Print-Msg `"将使用浏览器打开 http://127.0.0.1:9090 地址, 进入 InvokeAI 的界面`"
Print-Msg `"提示: 打开浏览器后, 浏览器可能会显示连接失败, 这是因为 InvokeAI 未完成启动, 可以在弹出的 PowerShell 中查看 InvokeAI 的启动过程, 等待 InvokeAI 启动完成后刷新浏览器网页即可`"
Print-Msg `"提示：如果 PowerShell 界面长时间不动, 并且 InvokeAI 未启动, 可以尝试按下几次回车键`"
Start-Sleep -Seconds 2
Print-Msg `"调用浏览器打开地址中`"
Start-Process `"http://127.0.0.1:9090`"
Print-Msg `"启动 InvokeAI 中`"
invokeai-web --root `"`$PSScriptRoot/invokeai`"
`$req = `$?
if (`$req) {
    Print-Msg `"InvokeAI 正常退出`"
} else {
    Print-Msg `"InvokeAI 出现异常, 已退出`"
}
Read-Host | Out-Null
"

    Set-Content -Encoding UTF8 -Path "./InvokeAI/launch.ps1" -Value $content
}


# 更新脚本
function Write-Update-Script {
    $content = "
Set-Location `"`$PSScriptRoot`"
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
}

# 代理配置
`$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
if (!(Test-Path `"`$PSScriptRoot/disable_proxy.txt`")) { # 检测是否禁用自动设置镜像源
    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
        `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
    } elseif (`$internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        `$Env:HTTP_PROXY = `"http://`$(`$internet_setting.ProxyServer)`"
        `$Env:HTTPS_PROXY = `"http://`$(`$internet_setting.ProxyServer)`"
        Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
} else {
    Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
}

# 设置 uv 的使用状态
if (Test-Path `"./disable_uv.txt`") {
    Print-Msg `"检测到 disable_uv.txt 配置文件, 已禁用 uv, 使用 Pip 作为 Python 包管理器`"
    `$USE_UV = `$false
} else {
    Print-Msg `"默认启用 uv 作为 Python 包管理器, 加快 Python 软件包的安装速度`"
    `$USE_UV = `$true
}

# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
# 环境变量
`$Env:PIP_INDEX_URL = `"$PIP_INDEX_MIRROR`"
`$Env:PIP_EXTRA_INDEX_URL = `"$PIP_EXTRA_INDEX_MIRROR`"
`$Env:PIP_FIND_LINKS = `"$PIP_FIND_MIRROR`"
`$Env:UV_INDEX_URL = `"$PIP_INDEX_MIRROR`"
# `$Env:UV_EXTRA_INDEX_URL = `"$PIP_EXTRA_INDEX_MIRROR`"
# `$Env:UV_FIND_LINKS = `"$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$Env:PIP_TIMEOUT = 30
`$Env:PIP_RETRIES = 5
`$Env:CACHE_HOME = `"`$PSScriptRoot/cache`"
`$Env:HF_HOME = `"`$PSScriptRoot/cache/huggingface`"
`$Env:MATPLOTLIBRC = `"`$PSScriptRoot/cache`"
`$Env:MODELSCOPE_CACHE = `"`$PSScriptRoot/cache/modelscope/hub`"
`$Env:MS_CACHE_HOME = `"`$PSScriptRoot/cache/modelscope/hub`"
`$Env:SYCL_CACHE_DIR = `"`$PSScriptRoot/cache/libsycl_cache`"
`$Env:TORCH_HOME = `"`$PSScriptRoot/cache/torch`"
`$Env:U2NET_HOME = `"`$PSScriptRoot/cache/u2net`"
`$Env:XDG_CACHE_HOME = `"`$PSScriptRoot/cache`"
`$Env:PIP_CACHE_DIR = `"`$PSScriptRoot/cache/pip`"
`$Env:PYTHONPYCACHEPREFIX = `"`$PSScriptRoot/cache/pycache`"
`$Env:INVOKEAI_ROOT = `"`$PSScriptRoot/invokeai`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"

# 获取 PyTorch 版本
function Get-PyTorch-Version {
    `$content = `"
from importlib.metadata import requires

requirements = requires('invokeai')

for i in requirements:
    if i.startswith('torch=='):
        torch_ver = i.split(';')[0]

    if i.startswith('torchvision=='):
        torchvision_ver = i.split(';')[0]

    if i.startswith('xformers=='):
        xformers_ver = i.split(';')[0]

print(f'{torch_ver}+cu118 {torchvision_ver}+cu118 {xformers_ver}+cu118')
`"

    `$pytorch_ver = `$(python -c `"`$content`")
    return `$pytorch_ver
}

Print-Msg `"更新 InvokeAI 内核中`"
`$ver = `$(python -m pip freeze | Select-String -Pattern `"invokeai`" | Out-String).trim().split(`"==`")[2]
if (`$USE_UV) {
    uv pip install InvokeAI --upgrade --no-deps --find-links `"$PIP_FIND_MIRROR`"
} else {
    python -m pip install InvokeAI --upgrade --no-deps --no-warn-script-location --use-pep517
}

if (`$?) {
    Print-Msg `"InvokeAI 内核更新成功, 开始更新 InvokeAI 依赖`"
    `$pytorch_ver = Get-PyTorch-Version
    `$ver_ = `$(python -m pip freeze | Select-String -Pattern `"invokeai`" | Out-String).trim().split(`"==`")[2]
    if (`$USE_UV) {
        uv pip install `"InvokeAI[xformers]`" `$pytorch_ver.ToString().Split() --upgrade --find-links `"$PIP_FIND_MIRROR`"
    } else {
        python -m pip install `"InvokeAI[xformers]`" `$pytorch_ver.ToString().Split() --upgrade --no-warn-script-location --use-pep517
    }
    if (`$?) {
        if (`$ver -eq `$ver_) {
            Print-Msg `"InvokeAI 已为最新版, 当前版本：`$ver_`"
        } else {
            Print-Msg `"InvokeAI 更新成功, 版本：`$ver -> `$ver_`"
        }
        Print-Msg `"该版本更新日志：https://github.com/invoke-ai/InvokeAI/releases/latest`"
    }
} else {
    Print-Msg `"InvokeAI 内核更新失败`"
}
Read-Host | Out-Null
"

    Set-Content -Encoding UTF8 -Path "./InvokeAI/update.ps1" -Value $content
}


# 数据库修复
function Write-InvokeAI-DB-Fix-Script {
    $content = "
Set-Location `"`$PSScriptRoot`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
`$Env:INVOKEAI_ROOT = `"`$PSScriptRoot/invokeai`"
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
}

Print-Msg `"修复 InvokeAI 数据库中`"
invokeai-db-maintenance --operation all --root `"`$PSScriptRoot/invokeai`"
Print-Msg `"修复 InvokeAI 数据库完成`"
Read-Host | Out-Null
"

    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/InvokeAI/fix_db.ps1" -Value $content
}


# 获取安装脚本
function Write-InvokeAI-Install-Script {
    $content = "
Set-Location `"`$PSScriptRoot`"
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
}

# 代理配置
`$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
if (!(Test-Path `"`$PSScriptRoot/disable_proxy.txt`")) { # 检测是否禁用自动设置镜像源
    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
        `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
    } elseif (`$internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        `$Env:HTTP_PROXY = `"http://`$(`$internet_setting.ProxyServer)`"
        `$Env:HTTPS_PROXY = `"http://`$(`$internet_setting.ProxyServer)`"
        Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
} else {
    Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
}

# 可用的下载源
`$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`")
`$count = `$urls.Length
`$i = 0

ForEach (`$url in `$urls) {
    Print-Msg `"正在下载最新的 InvokeAI Installer 脚本`"
    Invoke-WebRequest -Uri `$url -OutFile `"./cache/invokeai_installer.ps1`"
    if (`$?) {
        if (Test-Path `"../invokeai_installer.ps1`") {
            Print-Msg `"删除原有的 InvokeAI Installer 脚本`"
            Remove-Item `"../invokeai_installer.ps1`" -Force
        }
        Move-Item -Path `"./cache/invokeai_installer.ps1`" -Destination `"../invokeai_installer.ps1`"
        `$parentDirectory = Split-Path `$PSScriptRoot -Parent
        Print-Msg `"下载 InvokeAI Installer 脚本成功, 脚本路径为 `$parentDirectory\invokeai_installer.ps1`"
        break
    } else {
        Print-Msg `"下载 InvokeAI Installer 脚本失败`"
        `$i += 1
        if (`$i -lt `$count) {
            Print-Msg `"重试下载 InvokeAI Installer 脚本`"
        }
    }
}
Read-Host | Out-Null
"

    Set-Content -Encoding UTF8 -Path "./InvokeAI/get_invokeai_installer.ps1" -Value $content
}


# 虚拟环境激活脚本
function Write-Env-Activate-Script {
    $content = "
function global:prompt {
    `"`$(Write-Host `"[InvokeAI Env]`" -ForegroundColor Green -NoNewLine) `$(Get-Location)> `"
}

function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
}

# 代理配置
`$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
if (!(Test-Path `"`$PSScriptRoot/disable_proxy.txt`")) { # 检测是否禁用自动设置镜像源
    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
        `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
    } elseif (`$internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        `$Env:HTTP_PROXY = `"http://`$(`$internet_setting.ProxyServer)`"
        `$Env:HTTPS_PROXY = `"http://`$(`$internet_setting.ProxyServer)`"
        Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
} else {
    Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
}

# HuggingFace 镜像源
if (!(Test-Path `"`$PSScriptRoot/disable_mirror.txt`")) { # 检测是否禁用了自动设置 HuggingFace 镜像源
    if (Test-Path `"`$PSScriptRoot/mirror.txt`") { # 本地存在 HuggingFace 镜像源配置
        `$hf_mirror_value = Get-Content `"`$PSScriptRoot/mirror.txt`"
        `$Env:HF_ENDPOINT = `$hf_mirror_value
        Print-Msg `"检测到本地存在 mirror.txt 配置文件, 已读取该配置并设置 HuggingFace 镜像源`"
    } else { # 使用默认设置
        `$Env:HF_ENDPOINT = `"https://hf-mirror.com`"
        Print-Msg `"使用默认 HuggingFace 镜像源`"
    }
} else {
    Print-Msg `"检测到本地存在 disable_mirror.txt 镜像源配置文件, 禁用自动设置 HuggingFace 镜像源`"
}

# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
# 环境变量
`$py_path = `"`$PSScriptRoot/python`"
`$py_scripts_path = `"`$PSScriptRoot/python/Scripts`"
`$Env:PATH = `"`$py_path`$([System.IO.Path]::PathSeparator)`$py_scripts_path`$([System.IO.Path]::PathSeparator)`$Env:PATH`" # 将python添加到环境变量
`$Env:PIP_INDEX_URL = `"$PIP_INDEX_MIRROR`"
`$Env:PIP_EXTRA_INDEX_URL = `"$PIP_EXTRA_INDEX_MIRROR`"
`$Env:PIP_FIND_LINKS = `"$PIP_FIND_MIRROR`"
`$Env:UV_INDEX_URL = `"$PIP_INDEX_MIRROR`"
# `$Env:UV_EXTRA_INDEX_URL = `"$PIP_EXTRA_INDEX_MIRROR`"
# `$Env:UV_FIND_LINKS = `"$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$Env:PIP_TIMEOUT = 30
`$Env:PIP_RETRIES = 5
`$Env:CACHE_HOME = `"`$PSScriptRoot/cache`"
`$Env:HF_HOME = `"`$PSScriptRoot/cache/huggingface`"
`$Env:MATPLOTLIBRC = `"`$PSScriptRoot/cache`"
`$Env:MODELSCOPE_CACHE = `"`$PSScriptRoot/cache/modelscope/hub`"
`$Env:MS_CACHE_HOME = `"`$PSScriptRoot/cache/modelscope/hub`"
`$Env:SYCL_CACHE_DIR = `"`$PSScriptRoot/cache/libsycl_cache`"
`$Env:TORCH_HOME = `"`$PSScriptRoot/cache/torch`"
`$Env:U2NET_HOME = `"`$PSScriptRoot/cache/u2net`"
`$Env:XDG_CACHE_HOME = `"`$PSScriptRoot/cache`"
`$Env:PIP_CACHE_DIR = `"`$PSScriptRoot/cache/pip`"
`$Env:PYTHONPYCACHEPREFIX = `"`$PSScriptRoot/cache/pycache`"
`$Env:INVOKEAI_ROOT = `"`$PSScriptRoot/invokeai`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"

Print-Msg `"激活 InvokeAI Env`"
Print-Msg `"更多帮助信息可在 InvokeAI Installer 项目地址查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md`"
"

    Set-Content -Encoding UTF8 -Path "./InvokeAI/activate.ps1" -Value $content
}


# PyTorch 重装脚本
function Write-PyTorch-ReInstall-Script {
    $content = "
Set-Location `"`$PSScriptRoot`"
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
}

# 设置 uv 的使用状态
if (Test-Path `"./disable_uv.txt`") {
    Print-Msg `"检测到 disable_uv.txt 配置文件, 已禁用 uv, 使用 Pip 作为 Python 包管理器`"
    `$USE_UV = `$false
} else {
    Print-Msg `"默认启用 uv 作为 Python 包管理器, 加快 Python 软件包的安装速度`"
    `$USE_UV = `$true
}

# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
# 环境变量
`$Env:PIP_INDEX_URL = `"$PIP_INDEX_MIRROR`"
`$Env:PIP_EXTRA_INDEX_URL = `"$PIP_EXTRA_INDEX_MIRROR`"
`$Env:PIP_FIND_LINKS = `"$PIP_FIND_MIRROR`"
`$Env:UV_INDEX_URL = `"$PIP_INDEX_MIRROR`"
# `$Env:UV_EXTRA_INDEX_URL = `"$PIP_EXTRA_INDEX_MIRROR`"
# `$Env:UV_FIND_LINKS = `"$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$Env:PIP_TIMEOUT = 30
`$Env:PIP_RETRIES = 5
`$Env:CACHE_HOME = `"`$PSScriptRoot/cache`"
`$Env:HF_HOME = `"`$PSScriptRoot/cache/huggingface`"
`$Env:MATPLOTLIBRC = `"`$PSScriptRoot/cache`"
`$Env:MODELSCOPE_CACHE = `"`$PSScriptRoot/cache/modelscope/hub`"
`$Env:MS_CACHE_HOME = `"`$PSScriptRoot/cache/modelscope/hub`"
`$Env:SYCL_CACHE_DIR = `"`$PSScriptRoot/cache/libsycl_cache`"
`$Env:TORCH_HOME = `"`$PSScriptRoot/cache/torch`"
`$Env:U2NET_HOME = `"`$PSScriptRoot/cache/u2net`"
`$Env:XDG_CACHE_HOME = `"`$PSScriptRoot/cache`"
`$Env:PIP_CACHE_DIR = `"`$PSScriptRoot/cache/pip`"
`$Env:PYTHONPYCACHEPREFIX = `"`$PSScriptRoot/cache/pycache`"
`$Env:INVOKEAI_ROOT = `"`$PSScriptRoot/invokeai`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"

# 获取 PyTorch 版本
function Get-PyTorch-Version {
    `$content = `"
from importlib.metadata import requires

requirements = requires('invokeai')

for i in requirements:
    if i.startswith('torch=='):
        torch_ver = i.split(';')[0]

    if i.startswith('torchvision=='):
        torchvision_ver = i.split(';')[0]

    if i.startswith('xformers=='):
        xformers_ver = i.split(';')[0]

print(f'{torch_ver}+cu118 {torchvision_ver}+cu118 {xformers_ver}+cu118')
`"

    `$pytorch_ver = `$(python -c `"`$content`")
    return `$pytorch_ver
}

Print-Msg `"是否重新安装 PyTorch (yes/no)?`"
Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
`$arg = Read-Host `"=========================================>`"
if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
    Print-Msg `"卸载原有的 PyTorch`"
    python -m pip uninstall torch torchvision xformers -y
    Print-Msg `"重新安装 PyTorch`"
    `$pytorch_ver = Get-PyTorch-Version
    if (`$USE_UV) {
        uv pip install `$pytorch_ver.ToString().Split() --find-links `"$PIP_FIND_MIRROR`"
    } else {
        python -m pip install `$pytorch_ver.ToString().Split() --no-warn-script-location --use-pep517
    }
    if (`$?) {
        Print-Msg `"重新安装 PyTorch 成功`"
    } else {
        Print-Msg `"重新安装 PyTorch 失败, 请重新运行 PyTorch 重装脚本`"
    }
} else {
    Print-Msg `"取消重装 PyTorch`"
}

Read-Host | Out-Null
"

    Set-Content -Encoding UTF8 -Path "./InvokeAI/reinstall_pytorch.ps1" -Value $content
}


# 下载模型配置文件脚本
function Write-Download-Config-Script {
    $content = "
Set-Location `"`$PSScriptRoot`"

# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
}

# 下载配置文件
function Download-Config-File(`$url, `$path) {
    `$length = `$url.split(`"/`").length
    `$name = `$url.split(`"/`")[`$length - 1]
    if (!(Test-Path `$path)) {
        Print-Msg `"下载 `$name 中`"
        Invoke-WebRequest -Uri `$url.ToString() -OutFile `"./cache/`$name`"
        if (`$?) {
            Move-Item -Path `"./cache/`$name`" -Destination `"`$path`"
            Print-Msg `"`$name 下载成功`"
        } else {
            Print-Msg `"`$name 下载失败`"
        }
    } else {
        Print-Msg `"`$name 已存在`"
    }
}


# 预下载模型配置文件
function Get-Model-Config-File {
    Print-Msg `"预下载模型配置文件中`"
    New-Item -ItemType Directory -Path `"./cache`" -Force > `$null
    New-Item -ItemType Directory -Path `"./invokeai/configs/stable-diffusion`" -Force > `$null
    New-Item -ItemType Directory -Path `"./invokeai/configs/controlnet`" -Force > `$null
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_base.yaml`" `"./invokeai/configs/stable-diffusion/sd_xl_base.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_inpaint.yaml`" `"./invokeai/configs/stable-diffusion/sd_xl_inpaint.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_refiner.yaml`" `"./invokeai/configs/stable-diffusion/sd_xl_refiner.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-finetune.yaml`" `"./invokeai/configs/stable-diffusion/v1-finetune.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-finetune_style.yaml`" `"./invokeai/configs/stable-diffusion/v1-finetune_style.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inference-v.yaml`" `"./invokeai/configs/stable-diffusion/v1-inference-v.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inference.yaml`" `"./invokeai/configs/stable-diffusion/v1-inference.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inpainting-inference.yaml`" `"./invokeai/configs/stable-diffusion/v1-inpainting-inference.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-m1-finetune.yaml`" `"./invokeai/configs/stable-diffusion/v1-m1-finetune.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inference-v.yaml`" `"./invokeai/configs/stable-diffusion/v2-inference-v.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inference.yaml`" `"./invokeai/configs/stable-diffusion/v2-inference.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inpainting-inference-v.yaml`" `"./invokeai/configs/stable-diffusion/v2-inpainting-inference-v.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inpainting-inference.yaml`" `"./invokeai/configs/stable-diffusion/v2-inpainting-inference.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-midas-inference.yaml`" `"./invokeai/configs/stable-diffusion/v2-midas-inference.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/controlnet/cldm_v15.yaml`" `"./invokeai/configs/controlnet/cldm_v15.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/controlnet/cldm_v21.yaml`" `"./invokeai/configs/controlnet/cldm_v21.yaml`"
    Print-Msg `"模型配置文件下载完成`"
}

Get-Model-Config-File
Read-Host | Out-Null
"
    Set-Content -Encoding UTF8 -Path "./InvokeAI/download_config.ps1" -Value $content
}

# 帮助文档
function Write-ReadMe {
    $content = "==================================
InvokeAI Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
==================================

这是关于 InvokeAI 的简单使用文档。

使用 InvokeAI Installer 进行安装并安装成功后，将在当前目录生成 InvokeAI 文件夹，以下为文件夹中不同文件 / 文件夹的作用。

cache：缓存文件夹，保存着 Pip / HuggingFace 等缓存文件。
python：Python 的存放路径，InvokeAI 安装的位置在此处，如果需要重装 InvokeAI，可将该文件夹删除，并使用 InvokeAI Installer 重新部署 InvokeAI。请注意，请勿将该 Python 文件夹添加到环境变量，这可能导致不良后果。
invokeai：InvokeAI 存放模型、图片等的文件夹。
activate.ps1：虚拟环境激活脚本，使用该脚本激活虚拟环境后即可使用 Python、Pip、InvokeAI 的命令。
get_invokeai_installer.ps1：获取最新的 InvokeAI Installer 安装脚本，运行后将会在与 InvokeAI 文件夹同级的目录中生成 invokeai_installer.ps1 安装脚本。
update.ps1：更新 InvokeAI 的脚本，可使用该脚本更新 InvokeAI。
launch.ps1：启动 InvokeAI 的脚本。
fix_db.ps1：修复 InvokeAI 数据库脚本，解决删除 InvokeAI 的图片后在界面中出现无效图片的问题。
reinstall_pytorch.ps1：重装 PyTorch 脚本，解决 PyTorch 无法正常使用或者 xFormers 版本不匹配导致无法调用的问题。
download_config.ps1：下载模型配置文件，当删除 invokeai 文件夹后，InvokeAI 将重新下载模型配置文件，但在无代理的情况下可能下载失败，所以可以通过该脚本进行下载。
help.txt：帮助文档。


要启动 InvokeAI，在 InvokeAI 文件夹中找到 launch.ps1 脚本，右键这个脚本，选择使用 PowerShell 运行，等待 InvokeAI 启动完成，启动完成后将在控制台显示访问地址，地址为 http://127.0.0.1:9090，将该地址输入浏览器地址栏并回车后进入 InvokeAI 界面。

InvokeAI 默认的界面语言为英文，在 InvokeAI 左下角的齿轮图标，点进 Settings，在 Language 选项选择简体中文即可将界面语言设置为中文。

使用 InvokeAI 时，建议阅读下列教程，以更快的了解并掌握使用 InvokeAI 的方法。
给所有想学习AI辅助绘画的人的入门课 By Yuno779：https://docs.qq.com/doc/p/9a03673f4a0493b4cd76babc901a49f0e6d52140

脚本为 InvokeAI 设置了 HuggingFace 镜像源，解决国内无法直接访问 HuggingFace，导致 InvokeAI 的模型管理无法从 HuggingFace 下载模型的问题。
如果想自定义 HuggingFace 镜像源，可以在本地创建 mirror.txt 文件，在文件中填写 HuggingFace 镜像源的地址后保存，再次启动脚本时将自动读取配置。
如果需要禁用 HuggingFace 镜像源，则创建 disable_mirror.txt 文件，启动脚本时将不再设置 HuggingFace 镜像源。

以下为可用的 HuggingFace 镜像源地址：
https://hf-mirror.com
https://huggingface.sukaka.top

若要为脚本设置代理，则在代理软件中打开系统代理模式即可，或者在本地创建 proxy.txt 文件，在文件中填写代理地址后保存，再次启动脚本是将自动读取配置。
如果要禁用自动设置代理，可以在本地创建 disable_proxy.txt 文件，启动脚本时将不再自动设置代理。

脚本默认调用 uv 作为 Python 包管理器，相比于 Pip，安装 Python 软件包的速度更快。
如需禁用，可在脚本目录下创建 disable_uv.txt 文件，这将禁用 uv 并使用 Pip 作为 Python 包管理器。

更多详细的帮助可在下面的链接查看。
InvokeAI Installer 使用帮助：https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md
InvokeAI 官方文档：https://invoke-ai.github.io/InvokeAI
InvokeAI 官方视频教程：https://www.youtube.com/@invokeai
Reddit 社区：https://www.reddit.com/r/invokeai
"

    Set-Content -Encoding UTF8 -Path "./InvokeAI/help.txt" -Value $content
}


# 主程序
function Main {
    Print-Msg "启动 InvokeAI 安装程序"
    Print-Msg "提示: 若出现某个步骤执行失败, 可尝试再次运行 InvokeAI Installer"
    Print-Msg "InvokeAI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md"
    Check-Install
    Print-Msg "添加启动脚本和文档中"
    Write-Launch-Script
    Write-Update-Script
    Write-InvokeAI-DB-Fix-Script
    Write-InvokeAI-Install-Script
    Write-Env-Activate-Script
    Write-PyTorch-ReInstall-Script
    Write-Download-Config-Script
    Write-ReadMe
    Print-Msg "InvokeAI 安装结束, 安装路径为 $PSScriptRoot\InvokeAI"
    Print-Msg "关于该 InvokeAI 版本的更新日志：https://github.com/invoke-ai/InvokeAI/releases/latest"
    Print-Msg "帮助文档可在 InvokeAI 文件夹中查看, 双击 help.txt 文件即可查看"
    Print-Msg "退出 InvokeAI Installer"
}


###################


Main
Read-Host | Out-Null
