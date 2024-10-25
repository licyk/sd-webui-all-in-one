# 有关 PowerShell 脚本保存编码的问题: https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_character_encoding?view=powershell-7.4#the-byte-order-mark
# InvokeAI Installer 版本和检查更新间隔
$INVOKEAI_INSTALLER_VERSION = 138
$UPDATE_TIME_SPAN = 3600
# Pip 镜像源
$PIP_INDEX_MIRROR = "https://mirrors.cloud.tencent.com/pypi/simple"
# $PIP_EXTRA_INDEX_MIRROR = "https://mirror.baidu.com/pypi/simple"
$PIP_EXTRA_INDEX_MIRROR = "https://mirrors.cernet.edu.cn/pypi/web/simple"
$PIP_FIND_MIRROR = "https://mirror.sjtu.edu.cn/pytorch-wheels/torch_stable.html"
$PIP_EXTRA_INDEX_MIRROR_PYTORCH = "https://download.pytorch.org/whl"
$PIP_EXTRA_INDEX_MIRROR_CU121 = "https://download.pytorch.org/whl/cu121"
$PIP_EXTRA_INDEX_MIRROR_CU124 = "https://download.pytorch.org/whl/cu124"
# uv 最低版本
$UV_MINIMUM_VER = "0.4.24"
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
$Env:UV_FIND_LINKS = $PIP_FIND_MIRROR
$Env:UV_LINK_MODE = "copy"
$Env:UV_HTTP_TIMEOUT = 30
$Env:UV_CONCURRENT_DOWNLOADS = 50
$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
$Env:PIP_NO_WARN_SCRIPT_LOCATION = 0
$Env:PIP_TIMEOUT = 30
$Env:PIP_RETRIES = 5
$Env:PYTHONUTF8 = 1
$Env:PYTHONIOENCODING = "utf8"
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


# 代理配置
function Set-Proxy {
    $Env:NO_PROXY = "localhost,127.0.0.1,::1"
    if (!(Test-Path "$PSScriptRoot/disable_proxy.txt")) { # 检测是否禁用自动设置镜像源
        $INTERNET_SETTING = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        if (Test-Path "$PSScriptRoot/proxy.txt") { # 本地存在代理配置
            $proxy_value = Get-Content "$PSScriptRoot/proxy.txt"
            $Env:HTTP_PROXY = $proxy_value
            $Env:HTTPS_PROXY = $proxy_value
            Print-Msg "检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理"
        } elseif ($INTERNET_SETTING.ProxyEnable -eq 1) { # 系统已设置代理
            $Env:HTTP_PROXY = "http://$($INTERNET_SETTING.ProxyServer)"
            $Env:HTTPS_PROXY = "http://$($INTERNET_SETTING.ProxyServer)"
            Print-Msg "检测到系统设置了代理, 已读取系统中的代理配置并设置代理"
        }
    } else {
        Print-Msg "检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理"
    }
}


# 设置 uv 的使用状态
function Set-uv {
    if (Test-Path "$PSScriptRoot/disable_uv.txt") {
        Print-Msg "检测到 disable_uv.txt 配置文件, 已禁用 uv, 使用 Pip 作为 Python 包管理器"
        $Global:USE_UV = $false
    } else {
        Print-Msg "默认启用 uv 作为 Python 包管理器, 加快 Python 软件包的安装速度"
        Print-Msg "当 uv 安装 Python 软件包失败时, 将自动切换成 Pip 重试 Python 软件包的安装"
        $Global:USE_UV = $true
    }
}


# 检查 uv 是否需要更新
function Check-uv-Version {
    $content = "
import re
from importlib.metadata import version



def compare_versions(version1, version2) -> int:
    nums1 = re.sub(r'[a-zA-Z]+', '', version1).split('.')
    nums2 = re.sub(r'[a-zA-Z]+', '', version2).split('.')

    for i in range(max(len(nums1), len(nums2))):
        num1 = int(nums1[i]) if i < len(nums1) else 0
        num2 = int(nums2[i]) if i < len(nums2) else 0

        if num1 == num2:
            continue
        elif num1 > num2:
            return 1
        else:
            return -1

    return 0



def is_uv_need_update() -> bool:
    try:
        uv_ver = version('uv')
    except:
        return True
    
    if compare_versions(uv_ver, uv_minimum_ver) == -1:
        return True
    else:
        return False



uv_minimum_ver = '$UV_MINIMUM_VER'
print(is_uv_need_update())
"
    Print-Msg "检测 uv 是否需要更新"
    $status = $(python -c "$content")
    if ($status -eq "True") {
        Print-Msg "更新 uv 中"
        python -m pip install -U "uv>=$UV_MINIMUM_VER"
        if ($?) {
            Print-Msg "uv 更新成功"
        } else {
            Print-Msg "uv 更新失败, 可能会造成 uv 部分功能异常"
        }
    } else {
        Print-Msg "uv 无需更新"
    }
}


# 下载并解压 Python
function Install-Python {
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/python-3.10.11-amd64.zip"

    # 下载 Python
    Print-Msg "正在下载 Python"
    Invoke-WebRequest -Uri $url -OutFile "$PSScriptRoot/InvokeAI/cache/python-3.10.11-amd64.zip"
    if ($?) { # 检测是否下载成功并解压
        # 创建 Python 文件夹
        if (!(Test-Path "$PSScriptRoot/InvokeAI/python")) {
            New-Item -ItemType Directory -Force -Path "$PSScriptRoot/InvokeAI/python" > $null
        }
        # 解压 Python
        Print-Msg "正在解压 Python"
        Expand-Archive -Path "$PSScriptRoot/InvokeAI/cache/python-3.10.11-amd64.zip" -DestinationPath "$PSScriptRoot/InvokeAI/python" -Force
        Remove-Item -Path "$PSScriptRoot/InvokeAI/cache/python-3.10.11-amd64.zip"
        Print-Msg "Python 安装成功"
    } else {
        Print-Msg "Python 安装失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 下载 uv
function Install-uv {
    Print-Msg "正在下载 uv"
    python -m pip install uv
    if ($?) {
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
    $invokeai_ver = "InvokeAI==5.0.2"
    Print-Msg "正在下载 InvokeAI"
    if ($USE_UV) {
        uv pip install $invokeai_ver --no-deps
        if (!($?)) {
            Print-Msg "检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装"
            python -m pip install $invokeai_ver --no-deps --use-pep517
        }
    } else {
        python -m pip install $invokeai_ver --no-deps --use-pep517
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
import re
from importlib.metadata import version


def compare_versions(version1, version2):
    nums1 = re.sub(r'[a-zA-Z]+', '', version1).split('.')
    nums2 = re.sub(r'[a-zA-Z]+', '', version2).split('.')

    for i in range(max(len(nums1), len(nums2))):
        num1 = int(nums1[i]) if i < len(nums1) else 0
        num2 = int(nums2[i]) if i < len(nums2) else 0

        if num1 == num2:
            continue
        elif num1 > num2:
            return 1
        else:
            return -1

    return 0


if compare_versions(version('invokeai'), '5.0.2') == 1:
    print(True)
else:
    print(False)
"

    $status = $(python -c "$content") # 检查 InvokeAI 是否大于 5.0.2
    if ($status -eq "True") {
        $cuda_ver = "+cu124"
        $Env:PIP_FIND_LINKS = " "
        $Env:UV_FIND_LINKS = ""
        $Env:PIP_EXTRA_INDEX_URL = "$Env:PIP_EXTRA_INDEX_URL $PIP_EXTRA_INDEX_MIRROR_CU124"
        $Env:UV_EXTRA_INDEX_URL = $PIP_EXTRA_INDEX_MIRROR_CU124
    } else {
        $cuda_ver = "+cu118"
    }

    $content = "
from importlib.metadata import requires


pytorch_ver = []
cuda_ver = '$cuda_ver'
xf_cuda_ver = ''
ver_list = ''

invokeai_requires = requires('invokeai')

if cuda_ver == '+cu118':
    xf_cuda_ver = cuda_ver


for i in invokeai_requires:
    if i.startswith('torch=='):
        pytorch_ver.append(i.split(';')[0].strip() + cuda_ver)

    if i.startswith('torchvision=='):
        pytorch_ver.append(i.split(';')[0].strip() + cuda_ver)

    if i.startswith('torchaudio=='):
        pytorch_ver.append(i.split(';')[0].strip() + cuda_ver)

    if i.startswith('xformers=='):
        pytorch_ver.append(i.split(';')[0].strip() + xf_cuda_ver)


for i in pytorch_ver:
    ver_list = f'{ver_list} {i}'


print(ver_list)
"

    $pytorch_ver = $(python -c "$content") # 获取 PyTorch 版本
    Print-Msg "安装 InvokeAI 依赖中"
    if ($USE_UV) {
        uv pip install "InvokeAI[xformers]" $pytorch_ver.ToString().Split()
        if (!($?)) {
            Print-Msg "检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装"
            python -m pip install "InvokeAI[xformers]" $pytorch_ver.ToString().Split() --use-pep517
        }
    } else {
        python -m pip install "InvokeAI[xformers]" $pytorch_ver.ToString().Split() --use-pep517
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

    if (!(Test-Path "$PSScriptRoot/InvokeAI/python/Lib/site-packages/patchmatch/libpatchmatch_windows_amd64.dll")) {
        Print-Msg "下载 libpatchmatch_windows_amd64.dll 中"
        Invoke-WebRequest -Uri $url_1 -OutFile "$PSScriptRoot/InvokeAI/cache/libpatchmatch_windows_amd64.dll"
        if ($?) {
            Move-Item -Path "$PSScriptRoot/InvokeAI/cache/libpatchmatch_windows_amd64.dll" -Destination "$PSScriptRoot/InvokeAI/python/Lib/site-packages/patchmatch/libpatchmatch_windows_amd64.dll" -Force
            Print-Msg "下载 libpatchmatch_windows_amd64.dll 成功"
        } else {
            Print-Msg "下载 libpatchmatch_windows_amd64.dll 失败"
        }
    } else {
        Print-Msg "无需下载 libpatchmatch_windows_amd64.dll"
    }

    if (!(Test-Path "$PSScriptRoot/InvokeAI/python/Lib/site-packages/patchmatch/opencv_world460.dll")) {
        Print-Msg "下载 opencv_world460.dll 中"
        Invoke-WebRequest -Uri $url_2 -OutFile "$PSScriptRoot/InvokeAI/cache/opencv_world460.dll"
        if ($?) {
            Move-Item -Path "$PSScriptRoot/InvokeAI/cache/opencv_world460.dll" -Destination "$PSScriptRoot/InvokeAI/python/Lib/site-packages/patchmatch/opencv_world460.dll" -Force
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
        Invoke-WebRequest -Uri $url.ToString() -OutFile "$PSScriptRoot/InvokeAI/cache/$name"
        if ($?) {
            Move-Item -Path "$PSScriptRoot/InvokeAI/cache/$name" -Destination "$path" -Force
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
    New-Item -ItemType Directory -Path "$PSScriptRoot/InvokeAI/invokeai/configs/stable-diffusion" -Force > $null
    New-Item -ItemType Directory -Path "$PSScriptRoot/InvokeAI/invokeai/configs/controlnet" -Force > $null
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_base.yaml" "$PSScriptRoot/InvokeAI/invokeai/configs/stable-diffusion/sd_xl_base.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_inpaint.yaml" "$PSScriptRoot/InvokeAI/invokeai/configs/stable-diffusion/sd_xl_inpaint.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_refiner.yaml" "$PSScriptRoot/InvokeAI/invokeai/configs/stable-diffusion/sd_xl_refiner.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-finetune.yaml" "$PSScriptRoot/InvokeAI/invokeai/configs/stable-diffusion/v1-finetune.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-finetune_style.yaml" "$PSScriptRoot/InvokeAI/invokeai/configs/stable-diffusion/v1-finetune_style.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inference-v.yaml" "$PSScriptRoot/InvokeAI/invokeai/configs/stable-diffusion/v1-inference-v.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inference.yaml" "$PSScriptRoot/InvokeAI/invokeai/configs/stable-diffusion/v1-inference.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inpainting-inference.yaml" "$PSScriptRoot/InvokeAI/invokeai/configs/stable-diffusion/v1-inpainting-inference.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-m1-finetune.yaml" "$PSScriptRoot/InvokeAI/invokeai/configs/stable-diffusion/v1-m1-finetune.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inference-v.yaml" "$PSScriptRoot/InvokeAI/invokeai/configs/stable-diffusion/v2-inference-v.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inference.yaml" "$PSScriptRoot/InvokeAI/invokeai/configs/stable-diffusion/v2-inference.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inpainting-inference-v.yaml" "$PSScriptRoot/InvokeAI/invokeai/configs/stable-diffusion/v2-inpainting-inference-v.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inpainting-inference.yaml" "$PSScriptRoot/InvokeAI/invokeai/configs/stable-diffusion/v2-inpainting-inference.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-midas-inference.yaml" "$PSScriptRoot/InvokeAI/invokeai/configs/stable-diffusion/v2-midas-inference.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/controlnet/cldm_v15.yaml" "$PSScriptRoot/InvokeAI/invokeai/configs/controlnet/cldm_v15.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/controlnet/cldm_v21.yaml" "$PSScriptRoot/InvokeAI/invokeai/configs/controlnet/cldm_v21.yaml"
    Print-Msg "模型配置文件下载完成"
}


# 安装
function Check-Install {
    if (!(Test-Path "$PSScriptRoot/InvokeAI")) {
        New-Item -ItemType Directory -Path "$PSScriptRoot/InvokeAI" > $null
    }

    if (!(Test-Path "$PSScriptRoot/InvokeAI/cache")) {
        New-Item -ItemType Directory -Path "$PSScriptRoot/InvokeAI/cache" > $null
    }

    Print-Msg "检测是否安装 Python"
    if (Test-Path "$PSScriptRoot/InvokeAI/python/python.exe") {
        Print-Msg "Python 已安装"
    } else {
        Print-Msg "Python 未安装"
        Install-Python
    }


    Print-Msg "检测是否安装 uv"
    python -m pip show uv --quiet 2> $null
    if ($?) {
        Print-Msg "uv 已安装"
    } else {
        Print-Msg "uv 未安装"
        Install-uv
    }
    Check-uv-Version

    Print-Msg "检查是否安装 InvokeAI"
    python -m pip show invokeai --quiet 2> $null
    if ($?) {
        Print-Msg "InvokeAI 已安装"
    } else {
        Print-Msg "InvokeAI 未安装"
        Install-InvokeAI
    }

    Install-InvokeAI-Requirements

    Print-Msg "检测是否需要安装 PyPatchMatch"
    Install-PyPatchMatch

    Print-Msg "检测是否需要下载模型配置文件"
    Get-Model-Config-File

    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/InvokeAI/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
}


# 启动脚本
function Write-Launch-Script {
    $content = "
# InvokeAI Installer 版本和检查更新间隔
`$INVOKEAI_INSTALLER_VERSION = $INVOKEAI_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# Pip 镜像源
`$PIP_INDEX_MIRROR = `"$PIP_INDEX_MIRROR`"
`$PIP_EXTRA_INDEX_MIRROR = `"$PIP_EXTRA_INDEX_MIRROR`"
`$PIP_FIND_MIRROR = `"$PIP_FIND_MIRROR`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
# 环境变量
`$Env:PIP_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
`$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR`"
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
# `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR`"
`$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:UV_CONCURRENT_DOWNLOADS = 50
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$Env:PIP_NO_WARN_SCRIPT_LOCATION = 0
`$Env:PIP_TIMEOUT = 30
`$Env:PIP_RETRIES = 5
`$Env:PYTHONUTF8 = 1
`$Env:PYTHONIOENCODING = `"utf8`"
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



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
}


# InvokeAI Installer 更新检测
function Check-InvokeAI-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 InvokeAI Installer 的自动检查更新功能`"
        return
    }

    # 获取更新时间间隔
    try {
        `$last_update_time = Get-Content `"`$PSScriptRoot/update_time.txt`" 2> `$null
        `$last_update_time = Get-Date `$last_update_time -Format `"yyyy-MM-dd HH:mm:ss`"
    }
    catch {
        `$last_update_time = Get-Date 0 -Format `"yyyy-MM-dd HH:mm:ss`"
    }
    finally {
        `$update_time = Get-Date -Format `"yyyy-MM-dd HH:mm:ss`"
        `$time_span = New-TimeSpan -Start `$last_update_time -End `$update_time
    }

    if (`$time_span.TotalSeconds -gt `$UPDATE_TIME_SPAN) {
        Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间
        ForEach (`$url in `$urls) {
            Print-Msg `"检查 InvokeAI Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/invokeai_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$PSScriptRoot/cache/invokeai_installer.ps1`" | Select-String -Pattern `"INVOKEAI_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$INVOKEAI_INSTALLER_VERSION) {
                    New-Item -ItemType File -Path `"`$PSScriptRoot/use_update_mode.txt`" -Force > `$null
                    Print-Msg `"检测到 InvokeAI Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"=========================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 InvokeAI Installer 进行更新中`"
                        `$folder_name = Split-Path `$PSScriptRoot -Leaf
                        if (!(`$folder_name -eq `"InvokeAI`")) { # 检测脚本所在文件夹是否符合要求
                            Remove-Item -Path `"`$PSScriptRoot/cache/invokeai_installer.ps1`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/update_time.txt`" 2> `$null
                            Print-Msg `"检测到 InvokeAI Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                            Print-Msg `"当前 InvokeAI Installer 管理脚本所在文件夹名称: `$folder_name`"
                            Print-Msg `"请前往 `$(Split-Path `"`$PSScriptRoot`") 路径, 将名称为 `$folder_name 的文件夹改名为 InvokeAI, 再重新更新 InvokeAI Installer 管理脚本`"
                            Print-Msg `"终止 InvokeAI Installer 的更新`"
                            Read-Host | Out-Null
                            exit 1
                        }
                        Set-Location `"`$PSScriptRoot/..`"
                        Move-Item -Path `"`$PSScriptRoot/cache/invokeai_installer.ps1`" `"`$PSScriptRoot/../invokeai_installer.ps1`" -Force
                        ./invokeai_installer.ps1
                        Set-Location `"`$PSScriptRoot`"
                        Print-Msg `"更新结束, 需重新启动 InvokeAI Installer 管理脚本以应用更新, 回车退出 InvokeAI Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Remove-Item -Path `"`$PSScriptRoot/cache/invokeai_installer.ps1`" 2> `$null
                        Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                        Print-Msg `"跳过 InvokeAI Installer 更新`"
                    }
                } else {
                    Remove-Item -Path `"`$PSScriptRoot/cache/invokeai_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                    Print-Msg `"InvokeAI Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 InvokeAI Installer 更新中`"
                } else {
                    Print-Msg `"检查 InvokeAI Installer 更新失败`"
                }
            }
        }
    }
}


# 代理配置
function Set-Proxy {
    `$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    if (!(Test-Path `"`$PSScriptRoot/disable_proxy.txt`")) { # 检测是否禁用自动设置镜像源
        `$INTERNET_SETTING = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
        if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
            `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
            `$Env:HTTP_PROXY = `$proxy_value
            `$Env:HTTPS_PROXY = `$proxy_value
            Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
        } elseif (`$INTERNET_SETTING.ProxyEnable -eq 1) { # 系统已设置代理
            `$Env:HTTP_PROXY = `"http://`$(`$INTERNET_SETTING.ProxyServer)`"
            `$Env:HTTPS_PROXY = `"http://`$(`$INTERNET_SETTING.ProxyServer)`"
            Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
        }
    } else {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
    }
}


# Huggingface 镜像源
function Set-HuggingFace-Mirror {
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
}


# 获取 InvokeAI 的网页端口
function Get-InvokeAI-Launch-Port {
    `$port = `"9090`"
    if (!(Test-Path `"`$PSScriptRoot/invokeai/invokeai.yaml`")) {
        return `$port
    }

    Get-Content -Path `"`$PSScriptRoot/invokeai/invokeai.yaml`" | ForEach-Object {
        `$matches = [regex]::Matches(`$_, '^(\w+): (.+)')
        foreach (`$match in `$matches) {
            `$key = `$match.Groups[1].Value
            `$value = `$match.Groups[2].Value
            if ((`$key -eq `"port`") -and (!(`$match.Groups[0].Value -eq `"`"))) {
                `$port = `$value
                break
            }
        }
    }
    return `$port
}


# 写入 InvokeAI 启动脚本
function Write-Launch-InvokeAI-Script {
    `$content = `"
import re
import sys
from invokeai.app.run_app import run_app
if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
    sys.exit(run_app())
`"

    if (!(Test-Path `"`$PSScriptRoot/cache`")) {
        New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" > `$null
    }
    Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/cache/launch_invokeai.py`" -Value `$content
}


# 设置 InvokeAI 的快捷启动方式
function Create-InvokeAI-Shortcut {
    `$filename = `"InvokeAI`"
    `$url = `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/invokeai_icon.ico`"
    `$shortcut_icon = `"`$PSScriptRoot/invokeai_icon.ico`"

    if (!(Test-Path `"`$PSScriptRoot/enable_shortcut.txt`")) {
        return
    }

    Print-Msg `"检查 InvokeAI 快捷启动方式中`"
    if (!(Test-Path `"`$shortcut_icon`")) {
        Print-Msg `"获取 InvokeAI 图标中`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/invokeai_icon.ico`"
        if (!(`$?)) {
            Print-Msg `"获取 InvokeAI 图标失败, 无法创建 InvokeAI 快捷启动方式`"
            return
        }
    }

    Print-Msg `"保存 InvokeAI 快捷启动方式`"
    `$shell = New-Object -ComObject WScript.Shell
    `$desktop = [System.Environment]::GetFolderPath(`"Desktop`")
    `$shortcut_path = `"`$desktop\`$filename.lnk`"
    `$shortcut = `$shell.CreateShortcut(`$shortcut_path)
    `$shortcut.TargetPath = `"`$PSHome\powershell.exe`"
    `$launch_script_path = `$(Get-Item `"`$PSScriptRoot/launch.ps1`").FullName
    `$shortcut.Arguments = `"-File ```"`$launch_script_path```"`"
    `$shortcut.IconLocation = `$shortcut_icon

    # 保存到桌面
    `$shortcut.Save()
    `$start_menu_path = `"`$Env:APPDATA/Microsoft/Windows/Start Menu/Programs`"
    `$taskbar_path = `"`$Env:APPDATA\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar`"
    # 保存到开始菜单
    Copy-Item -Path `"`$shortcut_path`" -Destination `"`$start_menu_path`" -Force
    # 固定到任务栏
    # Copy-Item -Path `"`$shortcut_path`" -Destination `"`$taskbar_path`" -Force
    # `$shell = New-Object -ComObject Shell.Application
    # `$shell.Namespace([System.IO.Path]::GetFullPath(`$taskbar_path)).ParseName((Get-Item `$shortcut_path).Name).InvokeVerb('taskbarpin')
}


function Main {
    Print-Msg `"初始化中`"
    Print-Msg `"InvokeAI Installer 版本: v`$INVOKEAI_INSTALLER_VERSION`"
    Set-Proxy
    Set-HuggingFace-Mirror
    Check-InvokeAI-Installer-Update
    Create-InvokeAI-Shortcut
    `$port = Get-InvokeAI-Launch-Port
    Print-Msg `"将使用浏览器打开 http://127.0.0.1:`$port 地址, 进入 InvokeAI 的界面`"
    Print-Msg `"提示: 打开浏览器后, 浏览器可能会显示连接失败, 这是因为 InvokeAI 未完成启动, 可以在弹出的 PowerShell 中查看 InvokeAI 的启动过程, 等待 InvokeAI 启动完成后刷新浏览器网页即可`"
    Print-Msg `"提示：如果 PowerShell 界面长时间不动, 并且 InvokeAI 未启动, 可以尝试按下几次回车键`"
    Start-Sleep -Seconds 2
    Print-Msg `"调用浏览器打开地址中`"
    Start-Process `"http://127.0.0.1:`$port`"
    Print-Msg `"启动 InvokeAI 中`"
    Write-Launch-InvokeAI-Script
    python `"`$PSScriptRoot/cache/launch_invokeai.py`" --root `"`$PSScriptRoot/invokeai`"
    if (`$?) {
        Print-Msg `"InvokeAI 正常退出`"
    } else {
        Print-Msg `"InvokeAI 出现异常, 已退出`"
    }
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/InvokeAI/launch.ps1") {
        Print-Msg "更新 launch.ps1 中"
    } else {
        Print-Msg "生成 launch.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/InvokeAI/launch.ps1" -Value $content
}


# 更新脚本
function Write-Update-Script {
    $content = "
# InvokeAI Installer 版本和检查更新间隔
`$INVOKEAI_INSTALLER_VERSION = $INVOKEAI_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# Pip 镜像源
`$PIP_INDEX_MIRROR = `"$PIP_INDEX_MIRROR`"
`$PIP_EXTRA_INDEX_MIRROR = `"$PIP_EXTRA_INDEX_MIRROR`"
`$PIP_FIND_MIRROR = `"$PIP_FIND_MIRROR`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
# 环境变量
`$Env:PIP_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
`$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR`"
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
# `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR`"
`$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:UV_CONCURRENT_DOWNLOADS = 50
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$Env:PIP_NO_WARN_SCRIPT_LOCATION = 0
`$Env:PIP_TIMEOUT = 30
`$Env:PIP_RETRIES = 5
`$Env:PYTHONUTF8 = 1
`$Env:PYTHONIOENCODING = `"utf8`"
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



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
}


# InvokeAI Installer 更新检测
function Check-InvokeAI-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 InvokeAI Installer 的自动检查更新功能`"
        return
    }

    # 获取更新时间间隔
    try {
        `$last_update_time = Get-Content `"`$PSScriptRoot/update_time.txt`" 2> `$null
        `$last_update_time = Get-Date `$last_update_time -Format `"yyyy-MM-dd HH:mm:ss`"
    }
    catch {
        `$last_update_time = Get-Date 0 -Format `"yyyy-MM-dd HH:mm:ss`"
    }
    finally {
        `$update_time = Get-Date -Format `"yyyy-MM-dd HH:mm:ss`"
        `$time_span = New-TimeSpan -Start `$last_update_time -End `$update_time
    }

    if (`$time_span.TotalSeconds -gt `$UPDATE_TIME_SPAN) {
        Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间
        ForEach (`$url in `$urls) {
            Print-Msg `"检查 InvokeAI Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/invokeai_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$PSScriptRoot/cache/invokeai_installer.ps1`" | Select-String -Pattern `"INVOKEAI_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$INVOKEAI_INSTALLER_VERSION) {
                    New-Item -ItemType File -Path `"`$PSScriptRoot/use_update_mode.txt`" -Force > `$null
                    Print-Msg `"检测到 InvokeAI Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"=========================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 InvokeAI Installer 进行更新中`"
                        `$folder_name = Split-Path `$PSScriptRoot -Leaf
                        if (!(`$folder_name -eq `"InvokeAI`")) { # 检测脚本所在文件夹是否符合要求
                            Remove-Item -Path `"`$PSScriptRoot/cache/invokeai_installer.ps1`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/update_time.txt`" 2> `$null
                            Print-Msg `"检测到 InvokeAI Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                            Print-Msg `"当前 InvokeAI Installer 管理脚本所在文件夹名称: `$folder_name`"
                            Print-Msg `"请前往 `$(Split-Path `"`$PSScriptRoot`") 路径, 将名称为 `$folder_name 的文件夹改名为 InvokeAI, 再重新更新 InvokeAI Installer 管理脚本`"
                            Print-Msg `"终止 InvokeAI Installer 的更新`"
                            Read-Host | Out-Null
                            exit 1
                        }
                        Set-Location `"`$PSScriptRoot/..`"
                        Move-Item -Path `"`$PSScriptRoot/cache/invokeai_installer.ps1`" `"`$PSScriptRoot/../invokeai_installer.ps1`" -Force
                        ./invokeai_installer.ps1
                        Set-Location `"`$PSScriptRoot`"
                        Print-Msg `"更新结束, 需重新启动 InvokeAI Installer 管理脚本以应用更新, 回车退出 InvokeAI Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Remove-Item -Path `"`$PSScriptRoot/cache/invokeai_installer.ps1`" 2> `$null
                        Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                        Print-Msg `"跳过 InvokeAI Installer 更新`"
                    }
                } else {
                    Remove-Item -Path `"`$PSScriptRoot/cache/invokeai_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                    Print-Msg `"InvokeAI Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 InvokeAI Installer 更新中`"
                } else {
                    Print-Msg `"检查 InvokeAI Installer 更新失败`"
                }
            }
        }
    }
}


# 代理配置
function Set-Proxy {
    `$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    if (!(Test-Path `"`$PSScriptRoot/disable_proxy.txt`")) { # 检测是否禁用自动设置镜像源
        `$INTERNET_SETTING = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
        if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
            `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
            `$Env:HTTP_PROXY = `$proxy_value
            `$Env:HTTPS_PROXY = `$proxy_value
            Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
        } elseif (`$INTERNET_SETTING.ProxyEnable -eq 1) { # 系统已设置代理
            `$Env:HTTP_PROXY = `"http://`$(`$INTERNET_SETTING.ProxyServer)`"
            `$Env:HTTPS_PROXY = `"http://`$(`$INTERNET_SETTING.ProxyServer)`"
            Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
        }
    } else {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
    }
}


# 检查 uv 是否需要更新
function Check-uv-Version {
    `$content = `"
import re
from importlib.metadata import version



def compare_versions(version1, version2) -> int:
    nums1 = re.sub(r'[a-zA-Z]+', '', version1).split('.')
    nums2 = re.sub(r'[a-zA-Z]+', '', version2).split('.')

    for i in range(max(len(nums1), len(nums2))):
        num1 = int(nums1[i]) if i < len(nums1) else 0
        num2 = int(nums2[i]) if i < len(nums2) else 0

        if num1 == num2:
            continue
        elif num1 > num2:
            return 1
        else:
            return -1

    return 0



def is_uv_need_update() -> bool:
    try:
        uv_ver = version('uv')
    except:
        return True
    
    if compare_versions(uv_ver, uv_minimum_ver) == -1:
        return True
    else:
        return False



uv_minimum_ver = '`$UV_MINIMUM_VER'
print(is_uv_need_update())
`"
    Print-Msg `"检测 uv 是否需要更新`"
    `$status = `$(python -c `"`$content`")
    if (`$status -eq `"True`") {
        Print-Msg `"更新 uv 中`"
        python -m pip install -U `"uv>=`$UV_MINIMUM_VER`"
        if (`$?) {
            Print-Msg `"uv 更新成功`"
        } else {
            Print-Msg `"uv 更新失败, 可能会造成 uv 部分功能异常`"
        }
    } else {
        Print-Msg `"uv 无需更新`"
    }
}


# 设置 uv 的使用状态
function Set-uv {
    if (Test-Path `"`$PSScriptRoot/disable_uv.txt`") {
        Print-Msg `"检测到 disable_uv.txt 配置文件, 已禁用 uv, 使用 Pip 作为 Python 包管理器`"
        `$Global:USE_UV = `$false
    } else {
        Print-Msg `"默认启用 uv 作为 Python 包管理器, 加快 Python 软件包的安装速度`"
        Print-Msg `"当 uv 安装 Python 软件包失败时, 将自动切换成 Pip 重试 Python 软件包的安装`"
        `$Global:USE_UV = `$true
        Check-uv-Version
    }
}


# 检查 InvokeAI 版本是否大于 5.0.2
function Check-InvokeAI-Version {
    `$content = `"
import re
from importlib.metadata import version


def compare_versions(version1, version2):
    nums1 = re.sub(r'[a-zA-Z]+', '', version1).split('.')
    nums2 = re.sub(r'[a-zA-Z]+', '', version2).split('.')

    for i in range(max(len(nums1), len(nums2))):
        num1 = int(nums1[i]) if i < len(nums1) else 0
        num2 = int(nums2[i]) if i < len(nums2) else 0

        if num1 == num2:
            continue
        elif num1 > num2:
            return 1
        else:
            return -1

    return 0


if compare_versions(version('invokeai'), '5.0.2') == 1:
    print(True)
else:
    print(False)
`"

    return `$(python -c `"`$content`")
}


# 获取 PyTorch 版本
function Get-PyTorch-Version (`$cuda_ver) {
    `$content = `"
from importlib.metadata import requires


pytorch_ver = []
cuda_ver = '`$cuda_ver'
xf_cuda_ver = ''
ver_list = ''

invokeai_requires = requires('invokeai')

if cuda_ver == '+cu118':
    xf_cuda_ver = cuda_ver


for i in invokeai_requires:
    if i.startswith('torch=='):
        pytorch_ver.append(i.split(';')[0].strip() + cuda_ver)

    if i.startswith('torchvision=='):
        pytorch_ver.append(i.split(';')[0].strip() + cuda_ver)

    if i.startswith('torchaudio=='):
        pytorch_ver.append(i.split(';')[0].strip() + cuda_ver)

    if i.startswith('xformers=='):
        pytorch_ver.append(i.split(';')[0].strip() + xf_cuda_ver)


for i in pytorch_ver:
    ver_list = f'{ver_list} {i}'


print(ver_list)
`"

    return `$(python -c `"`$content`")
}


function Main {
    Print-Msg `"初始化中`"
    Print-Msg `"InvokeAI Installer 版本: v`$INVOKEAI_INSTALLER_VERSION`"
    Set-Proxy
    Set-uv
    Check-InvokeAI-Installer-Update
    `$update_fail = 0

    Print-Msg `"更新 InvokeAI 内核中`"
    `$ver = `$(python -m pip freeze | Select-String -Pattern `"invokeai`" | Out-String).trim().split(`"==`")[2]
    if (`$USE_UV) {
        uv pip install InvokeAI --upgrade --no-deps
        if (!(`$?)) {
            Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
            python -m pip install InvokeAI --upgrade --no-deps --use-pep517
        }
    } else {
        python -m pip install InvokeAI --upgrade --no-deps --use-pep517
    }

    if (`$?) {
        Print-Msg `"InvokeAI 内核更新成功, 开始更新 InvokeAI 依赖`"
        `$core_update_msg = `"更新成功`"

        # 检查 InvokeAI 版本是否大于 5.0.2
        `$status = Check-InvokeAI-Version

        if (`$status -eq `"True`") {
            `$cuda_ver = `"+cu124`"
            `$Env:PIP_FIND_LINKS = `" `"
            `$Env:UV_FIND_LINKS = `"`"
            `$Env:PIP_EXTRA_INDEX_URL = `"`$Env:PIP_EXTRA_INDEX_URL `$PIP_EXTRA_INDEX_MIRROR_CU124`"
            `$Env:UV_EXTRA_INDEX_URL = `$PIP_EXTRA_INDEX_MIRROR_CU124
        } else {
            `$cuda_ver = `"+cu118`"
        }

        # 获取 PyTorch 版本
        `$pytorch_ver = Get-PyTorch-Version `$cuda_ver

        `$ver_ = `$(python -m pip freeze | Select-String -Pattern `"invokeai`" | Out-String).Trim().Split(`"==`")[2]
        if (`$USE_UV) {
            uv pip install `"InvokeAI[xformers]`" `$pytorch_ver.ToString().Split() --upgrade
            if (!(`$?)) {
                Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
                python -m pip install `"InvokeAI[xformers]`" `$pytorch_ver.ToString().Split() --upgrade --use-pep517
            }
        } else {
            python -m pip install `"InvokeAI[xformers]`" `$pytorch_ver.ToString().Split() --upgrade --use-pep517
        }
        if (`$?) {
            Print-Msg `"InvokeAI 依赖更新成功`"
            `$req_update_msg = `"更新成功`"
        } else {
            Print-Msg `"InvokeAI 依赖更新失败`"
            `$req_update_msg = `"更新失败`"
            `$update_fail = 1
        }
    } else {
        Print-Msg `"InvokeAI 内核更新失败`"
        `$core_update_msg = `"更新失败`"
        `$req_update_msg = `"由于内核更新失败, 不进行依赖更新`"
        `$update_fail = 1
    }
    Print-Msg `"==================================================================`"
    Print-Msg `"InvokeAI 更新结果：`"
    Print-Msg `"InvokeAI 核心: `$core_update_msg`"
    Print-Msg `"InvokeAI 依赖: `$req_update_msg`"
    Print-Msg `"==================================================================`"
    if (`$update_fail -eq 0) {
        if (`$ver -eq `$ver_) {
            Print-Msg `"InvokeAI 更新成功, 当前版本：`$ver_`"
        } else {
            Print-Msg `"InvokeAI 更新成功, 版本：`$ver -> `$ver_`"
        }
        Print-Msg `"该版本更新日志：https://github.com/invoke-ai/InvokeAI/releases/latest`"
    } else {
        Print-Msg `"InvokeAI 更新失败, 请检查控制台日志。可尝试重新运行 InvokeAI 更新脚本进行重试`"
    }

    Print-Msg `"退出 InvokeAI 更新脚本`"
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/InvokeAI/update.ps1") {
        Print-Msg "更新 update.ps1 中"
    } else {
        Print-Msg "生成 update.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/InvokeAI/update.ps1" -Value $content
}


# 获取安装脚本
function Write-InvokeAI-Install-Script {
    $content = "
`$INVOKEAI_INSTALLER_VERSION = $INVOKEAI_INSTALLER_VERSION
# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
}


# 代理配置
function Set-Proxy {
    `$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    if (!(Test-Path `"`$PSScriptRoot/disable_proxy.txt`")) { # 检测是否禁用自动设置镜像源
        `$INTERNET_SETTING = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
        if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
            `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
            `$Env:HTTP_PROXY = `$proxy_value
            `$Env:HTTPS_PROXY = `$proxy_value
            Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
        } elseif (`$INTERNET_SETTING.ProxyEnable -eq 1) { # 系统已设置代理
            `$Env:HTTP_PROXY = `"http://`$(`$INTERNET_SETTING.ProxyServer)`"
            `$Env:HTTPS_PROXY = `"http://`$(`$INTERNET_SETTING.ProxyServer)`"
            Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
        }
    } else {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
    }
}


function Main {
    Print-Msg `"初始化中`"
    Print-Msg `"InvokeAI Installer 版本: v`$INVOKEAI_INSTALLER_VERSION`"
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`")
    `$count = `$urls.Length
    `$i = 0

    ForEach (`$url in `$urls) {
        Print-Msg `"正在下载最新的 InvokeAI Installer 脚本`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/invokeai_installer.ps1`"
        if (`$?) {
            Move-Item -Path `"`$PSScriptRoot/cache/invokeai_installer.ps1`" -Destination `"`$PSScriptRoot/../invokeai_installer.ps1`" -Force
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
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/InvokeAI/get_invokeai_installer.ps1") {
        Print-Msg "更新 get_invokeai_installer.ps1 中"
    } else {
        Print-Msg "生成 get_invokeai_installer.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/InvokeAI/get_invokeai_installer.ps1" -Value $content
}


# PyTorch 重装脚本
function Write-PyTorch-ReInstall-Script {
    $content = "
# InvokeAI Installer 版本和检查更新间隔
`$INVOKEAI_INSTALLER_VERSION = $INVOKEAI_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# Pip 镜像源
`$PIP_INDEX_MIRROR = `"$PIP_INDEX_MIRROR`"
`$PIP_EXTRA_INDEX_MIRROR = `"$PIP_EXTRA_INDEX_MIRROR`"
`$PIP_FIND_MIRROR = `"$PIP_FIND_MIRROR`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
# 环境变量
`$Env:PIP_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
`$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR`"
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
# `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR`"
`$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:UV_CONCURRENT_DOWNLOADS = 50
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$Env:PIP_NO_WARN_SCRIPT_LOCATION = 0
`$Env:PIP_TIMEOUT = 30
`$Env:PIP_RETRIES = 5
`$Env:PYTHONUTF8 = 1
`$Env:PYTHONIOENCODING = `"utf8`"
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



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
}


# 检查 InvokeAI 版本是否大于 5.0.2
function Check-InvokeAI-Version {
    `$content = `"
import re
from importlib.metadata import version


def compare_versions(version1, version2):
    nums1 = re.sub(r'[a-zA-Z]+', '', version1).split('.')
    nums2 = re.sub(r'[a-zA-Z]+', '', version2).split('.')

    for i in range(max(len(nums1), len(nums2))):
        num1 = int(nums1[i]) if i < len(nums1) else 0
        num2 = int(nums2[i]) if i < len(nums2) else 0

        if num1 == num2:
            continue
        elif num1 > num2:
            return 1
        else:
            return -1

    return 0


if compare_versions(version('invokeai'), '5.0.2') == 1:
    print(True)
else:
    print(False)
`"

    return `$(python -c `"`$content`")
}


# 获取 PyTorch 版本
function Get-PyTorch-Version (`$cuda_ver) {
    `$content = `"
from importlib.metadata import requires


pytorch_ver = []
cuda_ver = '`$cuda_ver'
xf_cuda_ver = ''
ver_list = ''

invokeai_requires = requires('invokeai')

if cuda_ver == '+cu118':
    xf_cuda_ver = cuda_ver


for i in invokeai_requires:
    if i.startswith('torch=='):
        pytorch_ver.append(i.split(';')[0].strip() + cuda_ver)

    if i.startswith('torchvision=='):
        pytorch_ver.append(i.split(';')[0].strip() + cuda_ver)

    if i.startswith('torchaudio=='):
        pytorch_ver.append(i.split(';')[0].strip() + cuda_ver)

    if i.startswith('xformers=='):
        pytorch_ver.append(i.split(';')[0].strip() + xf_cuda_ver)


for i in pytorch_ver:
    ver_list = f'{ver_list} {i}'


print(ver_list)
`"

    return `$(python -c `"`$content`")
}


# InvokeAI Installer 更新检测
function Check-InvokeAI-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 InvokeAI Installer 的自动检查更新功能`"
        return
    }

    # 获取更新时间间隔
    try {
        `$last_update_time = Get-Content `"`$PSScriptRoot/update_time.txt`" 2> `$null
        `$last_update_time = Get-Date `$last_update_time -Format `"yyyy-MM-dd HH:mm:ss`"
    }
    catch {
        `$last_update_time = Get-Date 0 -Format `"yyyy-MM-dd HH:mm:ss`"
    }
    finally {
        `$update_time = Get-Date -Format `"yyyy-MM-dd HH:mm:ss`"
        `$time_span = New-TimeSpan -Start `$last_update_time -End `$update_time
    }

    if (`$time_span.TotalSeconds -gt `$UPDATE_TIME_SPAN) {
        Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间
        ForEach (`$url in `$urls) {
            Print-Msg `"检查 InvokeAI Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/invokeai_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$PSScriptRoot/cache/invokeai_installer.ps1`" | Select-String -Pattern `"INVOKEAI_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$INVOKEAI_INSTALLER_VERSION) {
                    New-Item -ItemType File -Path `"`$PSScriptRoot/use_update_mode.txt`" -Force > `$null
                    Print-Msg `"检测到 InvokeAI Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"=========================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 InvokeAI Installer 进行更新中`"
                        `$folder_name = Split-Path `$PSScriptRoot -Leaf
                        if (!(`$folder_name -eq `"InvokeAI`")) { # 检测脚本所在文件夹是否符合要求
                            Remove-Item -Path `"`$PSScriptRoot/cache/invokeai_installer.ps1`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/update_time.txt`" 2> `$null
                            Print-Msg `"检测到 InvokeAI Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                            Print-Msg `"当前 InvokeAI Installer 管理脚本所在文件夹名称: `$folder_name`"
                            Print-Msg `"请前往 `$(Split-Path `"`$PSScriptRoot`") 路径, 将名称为 `$folder_name 的文件夹改名为 InvokeAI, 再重新更新 InvokeAI Installer 管理脚本`"
                            Print-Msg `"终止 InvokeAI Installer 的更新`"
                            Read-Host | Out-Null
                            exit 1
                        }
                        Set-Location `"`$PSScriptRoot/..`"
                        Move-Item -Path `"`$PSScriptRoot/cache/invokeai_installer.ps1`" `"`$PSScriptRoot/../invokeai_installer.ps1`" -Force
                        ./invokeai_installer.ps1
                        Set-Location `"`$PSScriptRoot`"
                        Print-Msg `"更新结束, 需重新启动 InvokeAI Installer 管理脚本以应用更新, 回车退出 InvokeAI Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Remove-Item -Path `"`$PSScriptRoot/cache/invokeai_installer.ps1`" 2> `$null
                        Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                        Print-Msg `"跳过 InvokeAI Installer 更新`"
                    }
                } else {
                    Remove-Item -Path `"`$PSScriptRoot/cache/invokeai_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                    Print-Msg `"InvokeAI Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 InvokeAI Installer 更新中`"
                } else {
                    Print-Msg `"检查 InvokeAI Installer 更新失败`"
                }
            }
        }
    }
}


# 检查 uv 是否需要更新
function Check-uv-Version {
    `$content = `"
import re
from importlib.metadata import version



def compare_versions(version1, version2) -> int:
    nums1 = re.sub(r'[a-zA-Z]+', '', version1).split('.')
    nums2 = re.sub(r'[a-zA-Z]+', '', version2).split('.')

    for i in range(max(len(nums1), len(nums2))):
        num1 = int(nums1[i]) if i < len(nums1) else 0
        num2 = int(nums2[i]) if i < len(nums2) else 0

        if num1 == num2:
            continue
        elif num1 > num2:
            return 1
        else:
            return -1

    return 0



def is_uv_need_update() -> bool:
    try:
        uv_ver = version('uv')
    except:
        return True
    
    if compare_versions(uv_ver, uv_minimum_ver) == -1:
        return True
    else:
        return False



uv_minimum_ver = '`$UV_MINIMUM_VER'
print(is_uv_need_update())
`"
    Print-Msg `"检测 uv 是否需要更新`"
    `$status = `$(python -c `"`$content`")
    if (`$status -eq `"True`") {
        Print-Msg `"更新 uv 中`"
        python -m pip install -U `"uv>=`$UV_MINIMUM_VER`"
        if (`$?) {
            Print-Msg `"uv 更新成功`"
        } else {
            Print-Msg `"uv 更新失败, 可能会造成 uv 部分功能异常`"
        }
    } else {
        Print-Msg `"uv 无需更新`"
    }
}


# 设置 uv 的使用状态
function Set-uv {
    if (Test-Path `"`$PSScriptRoot/disable_uv.txt`") {
        Print-Msg `"检测到 disable_uv.txt 配置文件, 已禁用 uv, 使用 Pip 作为 Python 包管理器`"
        `$Global:USE_UV = `$false
    } else {
        Print-Msg `"默认启用 uv 作为 Python 包管理器, 加快 Python 软件包的安装速度`"
        Print-Msg `"当 uv 安装 Python 软件包失败时, 将自动切换成 Pip 重试 Python 软件包的安装`"
        `$Global:USE_UV = `$true
        Check-uv-Version
    }
}


function Main {
    Print-Msg `"初始化中`"
    Print-Msg `"InvokeAI Installer 版本: v`$INVOKEAI_INSTALLER_VERSION`"
    Set-uv
    Check-InvokeAI-Installer-Update

    Print-Msg `"是否重新安装 PyTorch (yes/no)?`"
    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
    `$arg = Read-Host `"=========================================>`"
    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
        Print-Msg `"卸载原有的 PyTorch`"
        python -m pip uninstall torch torchvision xformers -y
        Print-Msg `"重新安装 PyTorch`"
        # 检查 InvokeAI 版本是否大于 5.0.2
        `$status = Check-InvokeAI-Version

        if (`$status -eq `"True`") {
            `$cuda_ver = `"+cu124`"
            `$Env:PIP_FIND_LINKS = `" `"
            `$Env:UV_FIND_LINKS = `"`"
            `$Env:PIP_EXTRA_INDEX_URL = `"`$Env:PIP_EXTRA_INDEX_URL `$PIP_EXTRA_INDEX_MIRROR_CU124`"
            `$Env:UV_EXTRA_INDEX_URL = `$PIP_EXTRA_INDEX_MIRROR_CU124
        } else {
            `$cuda_ver = `"+cu118`"
        }

        # 获取 PyTorch 版本
        `$pytorch_ver = Get-PyTorch-Version `$cuda_ver
        if (`$USE_UV) {
            uv pip install `$pytorch_ver.ToString().Split()
            if (!(`$?)) {
                Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
                python -m pip install `$pytorch_ver.ToString().Split() --use-pep517
            }
        } else {
            python -m pip install `$pytorch_ver.ToString().Split() --use-pep517
        }
        if (`$?) {
            Print-Msg `"重新安装 PyTorch 成功`"
        } else {
            Print-Msg `"重新安装 PyTorch 失败, 请重新运行 PyTorch 重装脚本`"
        }
    } else {
        Print-Msg `"取消重装 PyTorch`"
    }
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/InvokeAI/reinstall_pytorch.ps1") {
        Print-Msg "更新 reinstall_pytorch.ps1 中"
    } else {
        Print-Msg "生成 reinstall_pytorch.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/InvokeAI/reinstall_pytorch.ps1" -Value $content
}


# 下载模型配置文件脚本
function Write-Download-Config-Script {
    $content = "
`$INVOKEAI_INSTALLER_VERSION = $INVOKEAI_INSTALLER_VERSION
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
        Invoke-WebRequest -Uri `$url.ToString() -OutFile `"`$PSScriptRoot/cache/`$name`"
        if (`$?) {
            Move-Item -Path `"`$PSScriptRoot/cache/`$name`" -Destination `"`$path`" -Force
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
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_base.yaml`" `"`$PSScriptRoot/invokeai/configs/stable-diffusion/sd_xl_base.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_inpaint.yaml`" `"`$PSScriptRoot/invokeai/configs/stable-diffusion/sd_xl_inpaint.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_refiner.yaml`" `"`$PSScriptRoot/invokeai/configs/stable-diffusion/sd_xl_refiner.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-finetune.yaml`" `"`$PSScriptRoot/invokeai/configs/stable-diffusion/v1-finetune.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-finetune_style.yaml`" `"`$PSScriptRoot/invokeai/configs/stable-diffusion/v1-finetune_style.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inference-v.yaml`" `"`$PSScriptRoot/invokeai/configs/stable-diffusion/v1-inference-v.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inference.yaml`" `"`$PSScriptRoot/invokeai/configs/stable-diffusion/v1-inference.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inpainting-inference.yaml`" `"`$PSScriptRoot/invokeai/configs/stable-diffusion/v1-inpainting-inference.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-m1-finetune.yaml`" `"`$PSScriptRoot/invokeai/configs/stable-diffusion/v1-m1-finetune.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inference-v.yaml`" `"`$PSScriptRoot/invokeai/configs/stable-diffusion/v2-inference-v.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inference.yaml`" `"`$PSScriptRoot/invokeai/configs/stable-diffusion/v2-inference.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inpainting-inference-v.yaml`" `"`$PSScriptRoot/invokeai/configs/stable-diffusion/v2-inpainting-inference-v.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inpainting-inference.yaml`" `"`$PSScriptRoot/invokeai/configs/stable-diffusion/v2-inpainting-inference.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-midas-inference.yaml`" `"`$PSScriptRoot/invokeai/configs/stable-diffusion/v2-midas-inference.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/controlnet/cldm_v15.yaml`" `"`$PSScriptRoot/invokeai/configs/controlnet/cldm_v15.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/controlnet/cldm_v21.yaml`" `"`$PSScriptRoot/invokeai/configs/controlnet/cldm_v21.yaml`"
}


function Main {
    Print-Msg `"初始化中`"
    Print-Msg `"InvokeAI Installer 版本: v`$INVOKEAI_INSTALLER_VERSION`"
    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null
    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null
    New-Item -ItemType Directory -Path `"`$PSScriptRoot/invokeai/configs/stable-diffusion`" -Force > `$null
    New-Item -ItemType Directory -Path `"`$PSScriptRoot/invokeai/configs/controlnet`" -Force > `$null
    Print-Msg `"预下载模型配置文件中`"
    Get-Model-Config-File
    Print-Msg `"模型配置文件下载完成`"
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/InvokeAI/download_config.ps1") {
        Print-Msg "更新 download_config.ps1 中"
    } else {
        Print-Msg "生成 download_config.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/InvokeAI/download_config.ps1" -Value $content
}


# InvokeAI Installer 设置脚本
function Write-InvokeAI-Installer-Settings-Script {
    $content = "
# InvokeAI Installer 版本和检查更新间隔
`$INVOKEAI_INSTALLER_VERSION = $INVOKEAI_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# Pip 镜像源
`$PIP_INDEX_MIRROR = `"$PIP_INDEX_MIRROR`"
`$PIP_EXTRA_INDEX_MIRROR = `"$PIP_EXTRA_INDEX_MIRROR`"
`$PIP_FIND_MIRROR = `"$PIP_FIND_MIRROR`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
# 环境变量
`$Env:PIP_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
`$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR`"
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
# `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR`"
`$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:UV_CONCURRENT_DOWNLOADS = 50
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$Env:PIP_NO_WARN_SCRIPT_LOCATION = 0
`$Env:PIP_TIMEOUT = 30
`$Env:PIP_RETRIES = 5
`$Env:PYTHONUTF8 = 1
`$Env:PYTHONIOENCODING = `"utf8`"
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



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
}


# 代理配置
function Set-Proxy {
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
}


# 获取代理设置
function Get-Proxy-Setting {
    if (Test-Path `"`$PSScriptRoot/disable_proxy.txt`") {
        return `"禁用`"
    } elseif (Test-Path `"`$PSScriptRoot/proxy.txt`") {
        return `"启用 (使用自定义代理服务器: `$(Get-Content `"`$PSScriptRoot/proxy.txt`"))`"
    } else {
        return `"启用 (使用系统代理)`"
    }
}


# 获取 Python 包管理器设置
function Get-Python-Package-Manager-Setting {
    if (Test-Path `"`$PSScriptRoot/disable_uv.txt`") {
        return `"Pip`"
    } else {
        return `"uv`"
    }
}


# 获取 HuggingFace 镜像源设置
function Get-HuggingFace-Mirror-Setting {
    if (Test-Path `"`$PSScriptRoot/disable_hf_mirror.txt`") {
        return `"禁用`"
    } elseif (Test-Path `"`$PSScriptRoot/hf_mirror.txt`") {
        return `"启用 (自定义镜像源: `$(Get-Content `"`$PSScriptRoot/hf_mirror.txt`"))`"
    } else {
        return `"启用 (默认镜像源)`"
    }
}


# 获取 InvokeAI Installer 自动检测更新设置
function Get-InvokeAI-Installer-Auto-Check-Update-Setting {
    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        return `"禁用`"
    } else {
        return `"启用`"
    }
}


# 获取自动创建快捷启动方式
function Get-Auto-Set-Launch-Shortcut-Setting {
    if (Test-Path `"`$PSScriptRoot/enable_shortcut.txt`") {
        return `"启用`"
    } else {
        return `"禁用`"
    }
}


# 获取 Github 镜像源设置
function Get-Github-Mirror-Setting {
    if (Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") {
        return `"禁用`"
    } elseif (Test-Path `"`$PSScriptRoot/gh_mirror.txt`") {
        return `"启用 (使用自定义镜像源: `$(Get-Content `"`$PSScriptRoot/gh_mirror.txt`"))`"
    } else {
        return `"启用 (自动选择镜像源)`"
    }
}


# 获取用户输入
function Get-User-Input {
    return Read-Host `"=========================================>`"
}


# 代理设置
function Update-Proxy-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前代理设置: `$(Get-Proxy-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用代理 (使用系统代理)`"
        Print-Msg `"2. 启用代理 (手动设置代理服务器)`"
        Print-Msg `"3. 禁用代理`"
        Print-Msg `"4. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_proxy.txt`" 2> `$null
                Remove-Item -Path `"`$PSScriptRoot/proxy.txt`" 2> `$null
                Print-Msg `"启用代理成功, 当设置了系统代理后将自动读取并使用`"
                break
            }
            2 {
                Print-Msg `"请输入代理服务器地址`"
                Print-Msg `"提示: 代理地址可查看代理软件获取, 代理地址的格式如 http://127.0.0.1:10809、socks://127.0.0.1:7890 等, 输入后回车保存`"
                `$proxy_address = Get-User-Input
                Remove-Item -Path `"`$PSScriptRoot/disable_proxy.txt`" 2> `$null
                Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/proxy.txt`" -Value `$proxy_address
                Print-Msg `"启用代理成功, 使用的代理服务器为: `$proxy_address`"
                break
            }
            3 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_proxy.txt`" -Force > `$null
                Remove-Item -Path `"`$PSScriptRoot/proxy.txt`" 2> `$null
                Print-Msg `"禁用代理成功`"
                break
            }
            4 {
                `$go_to = 1
                break
            }
            Default {
                Print-Msg `"输入有误, 请重试`"
            }
        }

        if (`$go_to -eq 1) {
            break
        }
    }
}


# Python 包管理器设置
function Update-Python-Package-Manager-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前使用的 Python 包管理器: `$(Get-Python-Package-Manager-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 使用 uv 作为 Python 包管理器`"
        Print-Msg `"2. 使用 Pip 作为 Python 包管理器`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_uv.txt`" 2> `$null
                Print-Msg `"设置 uv 作为 Python 包管理器成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_uv.txt`" -Force > `$null
                Print-Msg `"设置 Pip 作为 Python 包管理器成功`"
                break
            }
            3 {
                `$go_to = 1
                break
            }
            Default {
                Print-Msg `"输入有误, 请重试`"
            }
        }

        if (`$go_to -eq 1) {
            break
        }
    }
}


# 设置 HuggingFace 镜像源
function Update-HuggingFace-Mirror-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 HuggingFace 镜像源设置: `$(Get-HuggingFace-Mirror-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 HuggingFace 镜像源 (使用默认镜像源)`"
        Print-Msg `"2. 启用 HuggingFace 镜像源 (使用自定义 HuggingFace 镜像源)`"
        Print-Msg `"3. 禁用 HuggingFace 镜像源`"
        Print-Msg `"4. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_hf_mirror.txt`" 2> `$null
                Remove-Item -Path `"`$PSScriptRoot/hf_mirror.txt`" 2> `$null
                Print-Msg `"启用 HuggingFace 镜像成功, 使用默认的 HuggingFace 镜像源 (https://hf-mirror.com)`"
                break
            }
            2 {
                Print-Msg `"请输入 HuggingFace 镜像源地址`"
                Print-Msg `"提示: 可用的 HuggingFace 镜像源有:`"
                Print-Msg `"1. https://hf-mirror.com`"
                Print-Msg `"2. https://huggingface.sukaka.top`"
                Print-Msg `"输入 HuggingFace 镜像源地址后回车保存`"
                `$huggingface_mirror_address = Get-User-Input
                Remove-Item -Path `"`$PSScriptRoot/disable_hf_mirror.txt`" 2> `$null
                Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/hf_mirror.txt`" -Value `$huggingface_mirror_address
                Print-Msg `"启用 HuggingFace 镜像成功, 使用的 HuggingFace 镜像源为: `$huggingface_mirror_address`"
                break
            }
            3 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_hf_mirror.txt`" -Force > `$null
                Remove-Item -Path `"`$PSScriptRoot/hf_mirror.txt`" 2> `$null
                Print-Msg `"禁用 HuggingFace 镜像成功`"
                break
            }
            4 {
                `$go_to = 1
                break
            }
            Default {
                Print-Msg `"输入有误, 请重试`"
            }
        }

        if (`$go_to -eq 1) {
            break
        }
    }
}


# InvokeAI Installer 自动检查更新设置
function Update-InvokeAI-Installer-Auto-Check-Update-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 InvokeAI Installer 自动检测更新设置: `$(Get-InvokeAI-Installer-Auto-Check-Update-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 InvokeAI Installer 自动更新检查`"
        Print-Msg `"2. 禁用 InvokeAI Installer 自动更新检查`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_update.txt`" 2> `$null
                Print-Msg `"启用 InvokeAI Installer 自动更新检查成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_update.txt`" -Force > `$null
                Print-Msg `"禁用 InvokeAI Installer 自动更新检查成功`"
                break
            }
            3 {
                `$go_to = 1
                break
            }
            Default {
                Print-Msg `"输入有误, 请重试`"
            }
        }

        if (`$go_to -eq 1) {
            break
        }
    }
}


# 自动创建 InvokeAI 快捷启动方式设置
function Auto-Set-Launch-Shortcut-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前自动创建 InvokeAI 快捷启动方式设置: `$(Get-Auto-Set-Launch-Shortcut-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用自动创建 InvokeAI 快捷启动方式`"
        Print-Msg `"2. 禁用自动创建 InvokeAI 快捷启动方式`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/enable_shortcut.txt`" -Force > `$null
                Print-Msg `"启用自动创建 InvokeAI 快捷启动方式成功`"
                break
            }
            2 {
                Remove-Item -Path `"`$PSScriptRoot/enable_shortcut.txt`" 2> `$null
                Print-Msg `"禁用自动创建 InvokeAI 快捷启动方式成功`"
                break
            }
            3 {
                `$go_to = 1
                break
            }
            Default {
                Print-Msg `"输入有误, 请重试`"
            }
        }

        if (`$go_to -eq 1) {
            break
        }
    }
}


# 设置 Github 镜像源
function Update-Github-Mirror-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 Github 镜像源设置: `$(Get-Github-Mirror-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 Github 镜像源 (自动检测可用的 Github 镜像源并使用)`"
        Print-Msg `"2. 启用 Github 镜像源 (使用自定义 Github 镜像源)`"
        Print-Msg `"3. 禁用 Github 镜像源`"
        Print-Msg `"4. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_gh_mirror.txt`" 2> `$null
                Remove-Item -Path `"`$PSScriptRoot/gh_mirror.txt`" 2> `$null
                Print-Msg `"启用 Github 镜像成功, 在更新 SD-Trainer 时将自动检测可用的 Github 镜像源并使用`"
                break
            }
            2 {
                Print-Msg `"请输入 Github 镜像源地址`"
                Print-Msg `"提示: 可用的 Github 镜像源有: `"
                Print-Msg `"1. https://ghp.ci/https://github.com`"
                Print-Msg `"2. https://mirror.ghproxy.com/https://github.com`"
                Print-Msg `"3. https://ghproxy.net/https://github.com`"
                Print-Msg `"4. https://gitclone.com/github.com`"
                Print-Msg `"5. https://gh-proxy.com/https://github.com`"
                Print-Msg `"6. https://ghps.cc/https://github.com`"
                Print-Msg `"7. https://gh.idayer.com/https://github.com`"
                Print-Msg `"输入 Github 镜像源地址后回车保存`"
                `$github_mirror_address = Get-User-Input
                Remove-Item -Path `"`$PSScriptRoot/disable_gh_mirror.txt`" 2> `$null
                Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/gh_mirror.txt`" -Value `$github_mirror_address
                Print-Msg `"启用 Github 镜像成功, 使用的 Github 镜像源为: `$github_mirror_address`"
                break
            }
            3 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_gh_mirror.txt`" -Force > `$null
                Remove-Item -Path `"`$PSScriptRoot/gh_mirror.txt`" 2> `$null
                Print-Msg `"禁用 Github 镜像成功`"
                break
            }
            4 {
                `$go_to = 1
                break
            }
            Default {
                Print-Msg `"输入有误, 请重试`"
            }
        }

        if (`$go_to -eq 1) {
            break
        }
    }
}


# 检查 InvokeAI Installer 更新
function Check-InvokeAI-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间
    ForEach (`$url in `$urls) {
        Print-Msg `"检查 InvokeAI Installer 更新中`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/invokeai_installer.ps1`"
        if (`$?) {
            `$latest_version = [int]`$(Get-Content `"`$PSScriptRoot/cache/invokeai_installer.ps1`" | Select-String -Pattern `"INVOKEAI_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
            if (`$latest_version -gt `$INVOKEAI_INSTALLER_VERSION) {
                New-Item -ItemType File -Path `"`$PSScriptRoot/use_update_mode.txt`" -Force > `$null
                Print-Msg `"InvokeAI Installer 有新版本可用`"
                Print-Msg `"调用 InvokeAI Installer 进行更新中`"
                `$folder_name = Split-Path `$PSScriptRoot -Leaf
                if (!(`$folder_name -eq `"InvokeAI`")) { # 检测脚本所在文件夹是否符合要求
                    Remove-Item -Path `"`$PSScriptRoot/cache/invokeai_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/update_time.txt`" 2> `$null
                    Print-Msg `"检测到 InvokeAI Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                    Print-Msg `"当前 InvokeAI Installer 管理脚本所在文件夹名称: `$folder_name`"
                    Print-Msg `"请前往 `$(Split-Path `"`$PSScriptRoot`") 路径, 将名称为 `$folder_name 的文件夹改名为 InvokeAI, 再重新更新 InvokeAI Installer 管理脚本`"
                    Print-Msg `"终止 InvokeAI Installer 的更新`"
                    return
                }
                Set-Location `"`$PSScriptRoot/..`"
                Move-Item -Path `"`$PSScriptRoot/cache/invokeai_installer.ps1`" `"`$PSScriptRoot/../invokeai_installer.ps1`" -Force
                ./invokeai_installer.ps1
                Set-Location `"`$PSScriptRoot`"
                Print-Msg `"更新结束, 需重新启动 InvokeAI Installer 管理脚本以应用更新, 回车退出 InvokeAI Installer 管理脚本`"
                Read-Host | Out-Null
                exit 0
            } else {
                Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                Remove-Item -Path `"`$PSScriptRoot/cache/invokeai_installer.ps1`" 2> `$null
                Print-Msg `"InvokeAI Installer 已是最新版本`"
            }
            break
        } else {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 InvokeAI Installer 更新中`"
            } else {
                Print-Msg `"检查 InvokeAI Installer 更新失败`"
            }
        }
    }
}


# 检查环境完整性
function Check-Env {
    Print-Msg `"检查环境完整性中`"
    `$broken = 0
    if (Test-Path `"`$PSScriptRoot/python/python.exe`") {
        `$python_status = `"已安装`"
    } else {
        `$python_status = `"未安装`"
        `$broken = 1
    }

    python -m pip show uv --quiet 2> `$null
    if (`$?) {
        `$uv_status = `"已安装`"
    } else {
        `$uv_status = `"未安装`"
        `$broken = 1
    }

    python -m pip show invokeai --quiet 2> `$null
    if (`$?) {
        `$invokeai_status = `"已安装`"
    } else {
        `$invokeai_status = `"未安装`"
        `$broken = 1
    }

    python -m pip show torch --quiet 2> `$null
    if (`$?) {
        `$torch_status = `"已安装`"
    } else {
        `$torch_status = `"未安装`"
        `$broken = 1
    }

    python -m pip show xformers --quiet 2> `$null
    if (`$?) {
        `$xformers_status = `"已安装`"
    } else {
        `$xformers_status = `"未安装`"
        `$broken = 1
    }

    Print-Msg `"-----------------------------------------------------`"
    Print-Msg `"当前环境:`"
    Print-Msg `"Python: `$python_status`"
    Print-Msg `"uv: `$uv_status`"
    Print-Msg `"PyTorch: `$torch_status`"
    Print-Msg `"xFormers: `$xformers_status`"
    Print-Msg `"InvokeAI: `$invokeai_status`"
    Print-Msg `"-----------------------------------------------------`"
    if (`$broken -eq 1) {
        Print-Msg `"检测到环境出现组件缺失, 可尝试运行 InvokeAI Installer 进行安装`"
    } else {
        Print-Msg `"当前环境无缺失组件`"
    }
}


# 查看 InvokeAI Installer 文档
function Get-InvokeAI-Installer-Help-Docs {
    Print-Msg `"调用浏览器打开 InvokeAI Installer 文档中`"
    Start-Process `"https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md`"
}


function Main {
    Print-Msg `"初始化中`"
    Print-Msg `"InvokeAI Installer 版本: v`$INVOKEAI_INSTALLER_VERSION`"
    Set-Proxy
    while (`$true) {
        `$go_to = 0
        Print-Msg `"-----------------------------------------------------`"
        Print-Msg `"当前环境配置:`"
        Print-Msg `"代理设置: `$(Get-Proxy-Setting)`"
        Print-Msg `"Python 包管理器: `$(Get-Python-Package-Manager-Setting)`"
        Print-Msg `"HuggingFace 镜像源设置: `$(Get-HuggingFace-Mirror-Setting)`"
        Print-Msg `"InvokeAI Installer 自动检查更新: `$(Get-InvokeAI-Installer-Auto-Check-Update-Setting)`"
        Print-Msg `"自动创建 InvokeAI 快捷启动方式: `$(Get-Auto-Set-Launch-Shortcut-Setting)`"
        Print-Msg `"Github 镜像源设置: `$(Get-Github-Mirror-Setting)`"
        Print-Msg `"-----------------------------------------------------`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 进入代理设置`"
        Print-Msg `"2. 进入 Python 包管理器设置`"
        Print-Msg `"3. 进入 HuggingFace 镜像源设置`"
        Print-Msg `"4. 进入 InvokeAI Installer 自动检查更新设置`"
        Print-Msg `"5. 进入自动创建 InvokeAI 快捷启动方式设置`"
        Print-Msg `"6. 进入 Github 镜像源设置`"
        Print-Msg `"7. 更新 InvokeAI Installer 管理脚本`"
        Print-Msg `"8. 检查环境完整性`"
        Print-Msg `"9. 查看 InvokeAI Installer 文档`"
        Print-Msg `"10. 退出 InvokeAI Installer 设置`"
        Print-Msg `"提示: 输入数字后回车`"
        `$arg = Get-User-Input
        switch (`$arg) {
            1 {
                Update-Proxy-Setting
                break
            }
            2 {
                Update-Python-Package-Manager-Setting
                break
            }
            3 {
                Update-HuggingFace-Mirror-Setting
                break
            }
            4 {
                Update-InvokeAI-Installer-Auto-Check-Update-Setting
                break
            }
            5 {
                Auto-Set-Launch-Shortcut-Setting
                break
            }
            6 {
                Update-Github-Mirror-Setting
                break
            }
            7 {
                Check-InvokeAI-Installer-Update
                break
            }
            8 {
                Check-Env
                break
            }
            9 {
                Get-InvokeAI-Installer-Help-Docs
                break
            }
            10 {
                `$go_to = 1
                break
            }
            Default {
                Print-Msg `"输入有误, 请重试`"
                break
            }
        }

        if (`$go_to -eq 1) {
            Print-Msg `"退出 InvokeAI Installer 设置`"
            break
        }
    }
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/InvokeAI/settings.ps1") {
        Print-Msg "更新 settings.ps1 中"
    } else {
        Print-Msg "生成 settings.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/InvokeAI/settings.ps1" -Value $content
}


# 虚拟环境激活脚本
function Write-Env-Activate-Script {
    $content = "
# InvokeAI Installer 版本和检查更新间隔
`$Env:INVOKEAI_INSTALLER_VERSION = $INVOKEAI_INSTALLER_VERSION
`$Env:UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# Pip 镜像源
`$PIP_INDEX_MIRROR = `"$PIP_INDEX_MIRROR`"
`$PIP_EXTRA_INDEX_MIRROR = `"$PIP_EXTRA_INDEX_MIRROR`"
`$PIP_FIND_MIRROR = `"$PIP_FIND_MIRROR`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
# Github 镜像源
`$GITHUB_MIRROR_LIST = @(
    `"https://ghp.ci/https://github.com`",
    `"https://mirror.ghproxy.com/https://github.com`",
    `"https://ghproxy.net/https://github.com`",
    `"https://gitclone.com/github.com`",
    `"https://gh-proxy.com/https://github.com`",
    `"https://ghps.cc/https://github.com`",
    `"https://gh.idayer.com/https://github.com`"
)
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
# 环境变量
`$Env:PIP_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
`$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR`"
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
# `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR`"
`$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:UV_CONCURRENT_DOWNLOADS = 50
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$Env:PIP_NO_WARN_SCRIPT_LOCATION = 0
`$Env:PIP_TIMEOUT = 30
`$Env:PIP_RETRIES = 5
`$Env:PYTHONUTF8 = 1
`$Env:PYTHONIOENCODING = `"utf8`"
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



# 提示信息
function global:prompt {
    `"`$(Write-Host `"[InvokeAI Env]`" -ForegroundColor Green -NoNewLine) `$(Get-Location)> `"
}


# 消息输出
function global:Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
}


# 更新 uv
function global:Update-uv {
    Print-Msg `"更新 uv 中`"
    python -m pip install uv --upgrade
    if (`$?) {
        Print-Msg `"更新 uv 成功`"
    } else {
        Print-Msg `"更新 uv 失败, 可尝试重新运行更新命令`"
    }
}


# InvokeAI Installer 更新检测
function global:Check-InvokeAI-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    Set-Content -Encoding UTF8 -Path `"`$Env:CACHE_HOME/../update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间
    ForEach (`$url in `$urls) {
        Print-Msg `"检查 InvokeAI Installer 更新中`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/invokeai_installer.ps1`"
        if (`$?) {
            `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/invokeai_installer.ps1`" | Select-String -Pattern `"INVOKEAI_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
            if (`$latest_version -gt `$Env:INVOKEAI_INSTALLER_VERSION) {
                New-Item -ItemType File -Path `"`$Env:CACHE_HOME/../use_update_mode.txt`" -Force > `$null
                Print-Msg `"InvokeAI Installer 有新版本可用`"
                Print-Msg `"调用 InvokeAI Installer 进行更新中`"
                `$folder_name = Split-Path `$Env:CACHE_HOME/.. -Leaf
                if (!(`$folder_name -eq `"InvokeAI`")) { # 检测脚本所在文件夹是否符合要求
                    Remove-Item -Path `"`$Env:CACHE_HOME/../cache/invokeai_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$Env:CACHE_HOME/../use_update_mode.txt`" 2> `$null
                    Remove-Item -Path `"`$Env:CACHE_HOME/../update_time.txt`" 2> `$null
                    Print-Msg `"检测到 InvokeAI Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                    Print-Msg `"当前 InvokeAI Installer 管理脚本所在文件夹名称: `$folder_name`"
                    Print-Msg `"请前往 `$(Split-Path `"`$(Split-Path `"`$Env:CACHE_HOME`")`") 路径, 将名称为 `$folder_name 的文件夹改名为 InvokeAI, 再重新更新 InvokeAI Installer 管理脚本`"
                    Print-Msg `"终止 InvokeAI Installer 的更新`"
                    return
                }
                Set-Location `"`$Env:CACHE_HOME/../..`"
                Move-Item -Path `"`$Env:CACHE_HOME/invokeai_installer.ps1`" `"`$Env:CACHE_HOME/../../invokeai_installer.ps1`" -Force
                ./invokeai_installer.ps1
                Set-Location `"`$Env:CACHE_HOME/..`"
                Print-Msg `"更新结束, 需重新启动 InvokeAI Installer 管理脚本以应用更新, 回车退出 InvokeAI Installer 管理脚本`"
                Read-Host | Out-Null
                exit 0
            } else {
                Remove-Item -Path `"`$Env:CACHE_HOME/../use_update_mode.txt`" 2> `$null
                Remove-Item -Path `"`$Env:CACHE_HOME/invokeai_installer.ps1`" 2> `$null
                Print-Msg `"InvokeAI Installer 已是最新版本`"
            }
            break
        } else {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 InvokeAI Installer 更新中`"
            } else {
                Print-Msg `"检查 InvokeAI Installer 更新失败`"
            }
        }
    }
}


# 安装 Git
function global:Install-Git {
    `$url = `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/PortableGit.zip`"
    if ((Get-Command git -ErrorAction SilentlyContinue) -or(Test-Path `"`$Env:CACHE_HOME/../git/bin/git.exe`")) {
        Print-Msg `"Git 已安装`"
        return
    }
    Print-Msg `"正在下载 Git`"
    Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/PortableGit.zip`"
    if (`$?) { # 检测是否下载成功并解压
        # 创建 Git 文件夹
        if (!(Test-Path `"`$Env:CACHE_HOME/../git`")) {
            New-Item -ItemType Directory -Force -Path `$Env:CACHE_HOME/../git > `$null
        }
        # 解压 Git
        Print-Msg `"正在解压 Git`"
        Expand-Archive -Path `"`$Env:CACHE_HOME/PortableGit.zip`" -DestinationPath `"`$Env:CACHE_HOME/../git`" -Force
        Remove-Item -Path `"`$Env:CACHE_HOME/PortableGit.zip`"
        Print-Msg `"Git 安装成功`"
        return `$true
    } else {
        Print-Msg `"Git 安装失败, 可重新运行命令重试安装`"
        return `$false
    }
}


# 启用 Github 镜像源
function global:Test-Github-Mirror {
    if (Test-Path `"`$Env:CACHE_HOME/../disable_gh_mirror.txt`") { # 禁用 Github 镜像源
        Print-Msg `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件, 禁用 Github 镜像源`"
    } else {
        `$Env:GIT_CONFIG_GLOBAL = `"`$Env:CACHE_HOME/../.gitconfig`" # 设置 Git 配置文件路径
        if (Test-Path `"`$Env:CACHE_HOME/../.gitconfig`") {
            Remove-Item -Path `"`$Env:CACHE_HOME/../.gitconfig`" -Force
        }

        if (Test-Path `"`$PSScriptRoot/gh_mirror.txt`") { # 使用自定义 Github 镜像源
            `$github_mirror = Get-Content `"`$PSScriptRoot/gh_mirror.txt`"
            git config --global --add safe.directory `"*`"
            git config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
            Print-Msg `"检测到本地存在 gh_mirror.txt Github 镜像源配置文件, 已读取 Github 镜像源配置文件并设置 Github 镜像源`"
        } else { # 自动检测可用镜像源并使用
            `$status = 0
            ForEach(`$i in `$GITHUB_MIRROR_LIST) {
                Print-Msg `"测试 Github 镜像源: `$i`"
                if (Test-Path `"`$Env:CACHE_HOME/github-mirror-test`") {
                    Remove-Item -Path `"`$Env:CACHE_HOME/github-mirror-test`" -Force -Recurse
                }
                git clone `$i/licyk/empty `$Env:CACHE_HOME/github-mirror-test --quiet
                if (`$?) {
                    Print-Msg `"该 Github 镜像源可用`"
                    `$github_mirror = `$i
                    `$status = 1
                    break
                } else {
                    Print-Msg `"镜像源不可用, 更换镜像源进行测试`"
                }
            }
            if (Test-Path `"`$Env:CACHE_HOME/github-mirror-test`") {
                Remove-Item -Path `"`$Env:CACHE_HOME/github-mirror-test`" -Force -Recurse
            }
            if (`$status -eq 0) {
                Print-Msg `"无可用 Github 镜像源, 取消使用 Github 镜像源`"
                Remove-Item -Path env:GIT_CONFIG_GLOBAL -Force
            } else {
                Print-Msg `"设置 Github 镜像源`"
                git config --global --add safe.directory `"*`"
                git config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
            }
        }
    }
}


# 安装 InvokeAI 自定义节点
function global:Install-InvokeAI-Node (`$url) {
    Print-Msg `"检测 Git 是否安装`"
    if ((!(Get-Command git -ErrorAction SilentlyContinue)) -and (!(Test-Path `"`$Env:CACHE_HOME/../git/bin/git.exe`"))) {
        Print-Msg `"检测到 Git 未安装`"
        `$status = Install-Git
        if (`$status) {
            Print-Msg `"Git 安装成功`"
        } else {
            Print-Msg `"Git 安装失败, 无法调用 Git 安装 InvokeAI 自定义节点`"
            return
        }
    } else {
        Print-Msg `"Git 已安装`"
    }

    # 应用 Github 镜像源
    if (`$global:is_test_gh_mirror -ne 1) {
        Test-Github-Mirror
        `$global:is_test_gh_mirror = 1
    }

    `$node_name = `$(Split-Path `$url -Leaf) -replace `".git`", `"`"
    if (!(Test-Path `"`$Env:INVOKEAI_ROOT/nodes/`$node_name`")) {
        `$status = 1
    } else {
        `$items = Get-ChildItem `"`$Env:INVOKEAI_ROOT/nodes/`$node_name`" -Recurse
        if (`$items.Count -eq 0) {
            `$status = 1
        }
    }

    if (`$status -eq 1) {
        Print-Msg `"安装 `$node_name 自定义节点中`"
        git clone --recurse-submodules `$url `"`$Env:INVOKEAI_ROOT/nodes/`$node_name`"
        if (`$?) {
            Print-Msg `"`$node_name 自定义节点安装成功`"
        } else {
            Print-Msg `"`$node_name 自定义节点安装失败`"
        }
    } else {
        Print-Msg `"`$node_name 自定义节点已安装`"
    }
}


# 安装 InvokeAI 自定义节点
function global:Git-Clone (`$url, `$path) {
    Print-Msg `"检测 Git 是否安装`"
    if ((!(Get-Command git -ErrorAction SilentlyContinue)) -and (!(Test-Path `"`$Env:CACHE_HOME/../git/bin/git.exe`"))) {
        Print-Msg `"检测到 Git 未安装`"
        `$status = Install-Git
        if (`$status) {
            Print-Msg `"Git 安装成功`"
        } else {
            Print-Msg `"Git 安装失败, 无法调用 Git 安装 InvokeAI 自定义节点`"
            return
        }
    } else {
        Print-Msg `"Git 已安装`"
    }

    # 应用 Github 镜像源
    if (`$global:is_test_gh_mirror -ne 1) {
        Test-Github-Mirror
        `$global:is_test_gh_mirror = 1
    }

    `$repo_name = `$(Split-Path `$url -Leaf) -replace `".git`", `"`"
    if (`$path.Length -ne 0) {
        `$repo_path = `$path
    } else {
        `$repo_path = `"`$(`$(Get-Location).ToString())/`$repo_name`"
    }
    if (!(Test-Path `"`$repo_path`")) {
        `$status = 1
    } else {
        `$items = Get-ChildItem `"`$repo_path`" -Recurse
        if (`$items.Count -eq 0) {
            `$status = 1
        }
    }

    if (`$status -eq 1) {
        Print-Msg `"下载 `$repo_name 中`"
        git clone --recurse-submodules `$url `"`$path`"
        if (`$?) {
            Print-Msg `"`$repo_name 下载成功`"
        } else {
            Print-Msg `"`$repo_name 下载失败`"
        }
    } else {
        Print-Msg `"`$repo_name 已存在`"
    }
}


# 修复 Git 分支游离
function global:Fix-Git-Point-Off-Set {
    param(
        `$path
    )
    if (Test-Path `"`$path/.git`") {
        git -C `"`$path`" symbolic-ref HEAD > `$null 2> `$null
        if (!(`$?)) {
            Print-Msg `"检测到出现分支游离, 进行修复中`"
            git -C `"`$path`" remote prune origin # 删除无用分支
            git -C `"`$path`" submodule init # 初始化git子模块
            `$branch = `$(git -C `"`$path`" branch -a | Select-String -Pattern `"/HEAD`").ToString().Split(`"/`")[3] # 查询远程HEAD所指分支
            git -C `"`$path`" checkout `$branch # 切换到主分支
            git -C `"`$path`" reset --recurse-submodules --hard origin/`$branch # 回退到远程分支的版本
        }
    }
}


# 更新所有 InvokeAI 自定义节点
function global:Update-InvokeAI-Node {
    Print-Msg `"检测 Git 是否安装`"
    if ((!(Get-Command git -ErrorAction SilentlyContinue)) -and (!(Test-Path `"`$Env:CACHE_HOME/../git/bin/git.exe`"))) {
        Print-Msg `"检测到 Git 未安装`"
        `$status = Install-Git
        if (`$status) {
            Print-Msg `"Git 安装成功`"
        } else {
            Print-Msg `"Git 安装失败, 无法调用 Git 安装 InvokeAI 自定义节点`"
            return
        }
    } else {
        Print-Msg `"Git 已安装`"
    }

    # 应用 Github 镜像源
    if (`$global:is_test_gh_mirror -ne 1) {
        Test-Github-Mirror
        `$global:is_test_gh_mirror = 1
    }

    `$node_list = Get-ChildItem -Path `"`$Env:CACHE_HOME/../invokeai/nodes`" | Select-Object -ExpandProperty FullName
    `$sum = 0
    `$count = 0
    ForEach (`$node in `$node_list) {
        if (Test-Path `"`$node/.git`") {
            `$sum += 1
        }
    }
    Print-Msg `"更新 InvokeAI 自定义节点中`"
    ForEach (`$node in `$node_list) {
        if (!(Test-Path `"`$node/.git`")) {
            continue
        }

        `$count += 1
        Print-Msg `"[`$count/`$sum]:: 更新 `$(`$(Get-Item `$node).Name) 自定义节点中`"
        Fix-Git-Point-Off-Set `"`$node`"
        `$origin_ver = `$(git -C `"`$node`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")
        `$branch = `$(git -C `"`$node`" symbolic-ref --quiet HEAD 2> `$null).split(`"/`")[2]
        git -C `"`$node`" fetch --recurse-submodules
        if (`$?) {
            `$commit_hash = `$(git -C `"`$node`" log origin/`$branch --max-count 1 --format=`"%h`")
            git -C `"`$node`" reset --hard `$commit_hash --recurse-submodules
            `$latest_ver = `$(git -C `"`$node`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")
            if (`$origin_ver -eq `$latest_ver) {
                Print-Msg `"[`$count/`$sum]:: `$(`$(Get-Item `$node).Name) 自定义节点已为最新版`"
            } else {
                Print-Msg `"[`$count/`$sum]:: `$(`$(Get-Item `$node).Name) 自定义节点更新成功, 版本：`$origin_ver -> `$latest_ver`"
            }
        } else {
            Print-Msg `"[`$count/`$sum]:: `$(`$(Get-Item `$node).Name) 自定义节点更新失败`"
        }
    }
    Print-Msg `"更新 InvokeAI 自定义节点完成`"
}


# 列出 InvokeAI Installer 内置命令
function global:List-CMD {
    Write-Host `"
==================================
InvokeAI Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
==================================

当前可用的 InvokeAI Installer 内置命令：

    Update-uv
    Check-InvokeAI-Installer-Update
    Install-Git
    Install-InvokeAI-Node
    Git-Clone
    Test-Github-Mirror
    Update-InvokeAI-Node
    List-CMD

更多帮助信息可在 InvokeAI Installer 文档中查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md
`"
}


# 代理配置
function Set-Proxy {
    `$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    if (!(Test-Path `"`$PSScriptRoot/disable_proxy.txt`")) { # 检测是否禁用自动设置镜像源
        `$INTERNET_SETTING = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
        if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
            `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
            `$Env:HTTP_PROXY = `$proxy_value
            `$Env:HTTPS_PROXY = `$proxy_value
            Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
        } elseif (`$INTERNET_SETTING.ProxyEnable -eq 1) { # 系统已设置代理
            `$Env:HTTP_PROXY = `"http://`$(`$INTERNET_SETTING.ProxyServer)`"
            `$Env:HTTPS_PROXY = `"http://`$(`$INTERNET_SETTING.ProxyServer)`"
            Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
        }
    } else {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
    }
}


# HuggingFace 镜像源
function Set-HuggingFace-Mirror {
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
}


function Main {
    Print-Msg `"初始化中`"
    Print-Msg `"InvokeAI Installer 版本: v`$Env:INVOKEAI_INSTALLER_VERSION`"
    Set-Proxy
    Set-HuggingFace-Mirror
    Print-Msg `"激活 InvokeAI Env`"
    Print-Msg `"更多帮助信息可在 InvokeAI Installer 项目地址查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md`"
}

###################

Main
"

    if (Test-Path "$PSScriptRoot/InvokeAI/activate.ps1") {
        Print-Msg "更新 activate.ps1 中"
    } else {
        Print-Msg "生成 activates.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/InvokeAI/activate.ps1" -Value $content
}


# 快捷启动终端脚本, 启动后将自动运行环境激活脚本
function Write-Launch-Terminal-Script {
    $content = "
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
}

Print-Msg `"执行 InvokeAI Installer 激活环境脚本`"
powershell -NoExit -File `"`$PSScriptRoot/activate.ps1`"
"

    if (Test-Path "$PSScriptRoot/InvokeAI/terminal.ps1") {
        Print-Msg "更新 terminal.ps1 中"
    } else {
        Print-Msg "生成 terminal.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/InvokeAI/terminal.ps1" -Value $content
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
reinstall_pytorch.ps1：重装 PyTorch 脚本，解决 PyTorch 无法正常使用或者 xFormers 版本不匹配导致无法调用的问题。
download_config.ps1：下载模型配置文件，当删除 invokeai 文件夹后，InvokeAI 将重新下载模型配置文件，但在无代理的情况下可能下载失败，所以可以通过该脚本进行下载。
settings.ps1：管理 InvokeAI Installer 的设置。
terminal.ps1：启动 PowerShell 终端并自动激活虚拟环境，激活虚拟环境后即可使用 Python、Pip、InvokeAI 的命令。
help.txt：帮助文档。


要启动 InvokeAI，在 InvokeAI 文件夹中找到 launch.ps1 脚本，右键这个脚本，选择使用 PowerShell 运行，等待 InvokeAI 启动完成，启动完成后将在控制台显示访问地址，地址为 http://127.0.0.1:9090，将该地址输入浏览器地址栏并回车后进入 InvokeAI 界面。

InvokeAI 默认的界面语言为英文，在 InvokeAI 左下角的齿轮图标，点进 Settings，在 Language 选项选择简体中文即可将界面语言设置为中文。

使用 InvokeAI 时，建议阅读下列教程，以更快的了解并掌握使用 InvokeAI 的方法。
给所有想学习AI辅助绘画的人的入门课 By Yuno779（基于 InvokeAI 3.7.0）：https://docs.qq.com/doc/p/9a03673f4a0493b4cd76babc901a49f0e6d52140
InvokeAI 官方入门教程（基于 InvokeAI 5.x）：https://www.youtube.com/playlist?list=PLvWK1Kc8iXGrQy8r9TYg6QdUuJ5MMx-ZO
一个使用 InvokeAI 5.0 的新统一画布完成常见任务的简述（升级到 InvokeAI 5.0 后必看）：https://www.youtube.com/watch?v=Tl-69JvwJ2s
如何使用 InvokeAI 5.0 的新统一画布和工作流系统：https://www.youtube.com/watch?v=y80W3PjR0Gc

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

InvokeAI Installer 提供了配置管理器, 运行 settings.ps1 即可管理各个配置。

InvokeAI Installer 的管理脚本在启动时会检查管理脚本的更新，如果有更新将会提示并显示具体的更新方法，如果要禁用更新，可以在脚本同级的目录创建 disable_update.txt 文件，这将禁用 InvokeAI Installer 更新检查。

更多详细的帮助可在下面的链接查看。
InvokeAI Installer 使用帮助：https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md
InvokeAI 官方文档：https://invoke-ai.github.io/InvokeAI
InvokeAI 官方视频教程：https://www.youtube.com/@invokeai
Reddit 社区：https://www.reddit.com/r/invokeai
"

    if (Test-Path "$PSScriptRoot/InvokeAI/help.txt") {
        Print-Msg "更新 help.txt 中"
    } else {
        Print-Msg "生成 help.txt 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/InvokeAI/help.txt" -Value $content
}


# 写入管理脚本和文档
function Write-Manager-Scripts {
    Write-Launch-Script
    Write-Update-Script
    Write-InvokeAI-Install-Script
    Write-Env-Activate-Script
    Write-PyTorch-ReInstall-Script
    Write-Download-Config-Script
    Write-InvokeAI-Installer-Settings-Script
    Write-Launch-Terminal-Script
    Write-ReadMe
}


# 执行安装
function Use-Install-Mode {
    Set-Proxy
    Set-uv
    Print-Msg "启动 InvokeAI 安装程序"
    Print-Msg "提示: 若出现某个步骤执行失败, 可尝试再次运行 InvokeAI Installer, 更多的说明请阅读 InvokeAI Installer 使用文档"
    Print-Msg "InvokeAI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md"
    Print-Msg "即将进行安装的路径: $PSScriptRoot\InvokeAI"
    Check-Install
    Print-Msg "添加管理脚本和文档中"
    Write-Manager-Scripts
    Print-Msg "InvokeAI 安装结束, 安装路径为: $PSScriptRoot\InvokeAI"
    Print-Msg "帮助文档可在 InvokeAI 文件夹中查看, 双击 help.txt 文件即可查看, 更多的说明请阅读 InvokeAI Installer 使用文档"
    Print-Msg "InvokeAI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md"
    Print-Msg "退出 InvokeAI Installer"
    Read-Host | Out-Null
}


# 执行管理脚本更新
function Use-Update-Mode {
    Print-Msg "更新管理脚本和文档中"
    Write-Manager-Scripts
    Print-Msg "更新管理脚本和文档完成"
}


# 主程序
function Main {
    Print-Msg "初始化中"
    Print-Msg "InvokeAI Installer 版本: v$INVOKEAI_INSTALLER_VERSION"
    if (Test-Path "$PSScriptRoot/InvokeAI/use_update_mode.txt") {
        Print-Msg "使用更新模式"
        Remove-Item -Path "$PSScriptRoot/InvokeAI/use_update_mode.txt" 2> $null
        Set-Content -Encoding UTF8 -Path "$PSScriptRoot/InvokeAI/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
        Use-Update-Mode
    } else {
        Print-Msg "使用安装模式"
        Use-Install-Mode
    }
}


###################


Main