﻿# 有关 PowerShell 脚本保存编码的问题: https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_character_encoding?view=powershell-7.4#the-byte-order-mark
# ComfyUI Installer 版本和检查更新间隔
$COMFYUI_INSTALLER_VERSION = 108
$UPDATE_TIME_SPAN = 3600
# Pip 镜像源
$PIP_INDEX_ADDR = "https://mirrors.cloud.tencent.com/pypi/simple"
$PIP_INDEX_ADDR_ORI = "https://pypi.python.org/simple"
$PIP_EXTRA_INDEX_ADDR = "https://mirrors.cernet.edu.cn/pypi/web/simple"
$PIP_EXTRA_INDEX_ADDR_ORI = "https://download.pytorch.org/whl"
$PIP_FIND_ADDR = "https://mirror.sjtu.edu.cn/pytorch-wheels/torch_stable.html"
$PIP_FIND_ADDR_ORI = "https://download.pytorch.org/whl/torch_stable.html"
$USE_PIP_MIRROR = if (!(Test-Path "$PSScriptRoot/disable_pip_mirror.txt")) { $true } else { $false }
$PIP_INDEX_MIRROR = if ($USE_PIP_MIRROR) { $PIP_INDEX_ADDR } else { $PIP_INDEX_ADDR_ORI }
$PIP_EXTRA_INDEX_MIRROR = if ($USE_PIP_MIRROR) { $PIP_EXTRA_INDEX_ADDR } else { $PIP_EXTRA_INDEX_ADDR_ORI }
$PIP_FIND_MIRROR = if ($USE_PIP_MIRROR) { $PIP_FIND_ADDR } else { $PIP_FIND_ADDR_ORI }
# $PIP_FIND_MIRROR_CU121 = "https://download.pytorch.org/whl/cu121/torch_stable.html"
$PIP_EXTRA_INDEX_MIRROR_PYTORCH = "https://download.pytorch.org/whl"
$PIP_EXTRA_INDEX_MIRROR_CU121 = "https://download.pytorch.org/whl/cu121"
$PIP_EXTRA_INDEX_MIRROR_CU124 = "https://download.pytorch.org/whl/cu124"
# Github 镜像源列表
$GITHUB_MIRROR_LIST = @(
    "https://ghp.ci/https://github.com",
    "https://mirror.ghproxy.com/https://github.com",
    "https://ghproxy.net/https://github.com",
    "https://gitclone.com/github.com",
    "https://gh-proxy.com/https://github.com",
    "https://ghps.cc/https://github.com",
    "https://gh.idayer.com/https://github.com"
)
# PyTorch 版本
$PYTORCH_VER = "torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118"
$XFORMERS_VER = "xformers===0.0.26.post1+cu118"
# uv 最低版本
$UV_MINIMUM_VER = "0.4.30"
# ComfyUI 仓库地址
$COMFYUI_REPO = "https://github.com/comfyanonymous/ComfyUI"
# PATH
$PYTHON_PATH = "$PSScriptRoot/ComfyUI/python"
$PYTHON_EXTRA_PATH = "$PSScriptRoot/ComfyUI/ComfyUI/python"
$PYTHON_SCRIPTS_PATH = "$PSScriptRoot/ComfyUI/python/Scripts"
$PYTHON_SCRIPTS_EXTRA_PATH = "$PSScriptRoot/ComfyUI/ComfyUI/python/Scripts"
$GIT_PATH = "$PSScriptRoot/ComfyUI/git/bin"
$GIT_EXTRA_PATH = "$PSScriptRoot/ComfyUI/ComfyUI/git/bin"
$Env:PATH = "$PYTHON_EXTRA_PATH$([System.IO.Path]::PathSeparator)$PYTHON_SCRIPTS_EXTRA_PATH$([System.IO.Path]::PathSeparator)$GIT_EXTRA_PATH$([System.IO.Path]::PathSeparator)$PYTHON_PATH$([System.IO.Path]::PathSeparator)$PYTHON_SCRIPTS_PATH$([System.IO.Path]::PathSeparator)$GIT_PATH$([System.IO.Path]::PathSeparator)$Env:PATH"
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
$Env:CACHE_HOME = "$PSScriptRoot/ComfyUI/cache"
$Env:HF_HOME = "$PSScriptRoot/ComfyUI/cache/huggingface"
$Env:MATPLOTLIBRC = "$PSScriptRoot/ComfyUI/cache"
$Env:MODELSCOPE_CACHE = "$PSScriptRoot/ComfyUI/cache/modelscope/hub"
$Env:MS_CACHE_HOME = "$PSScriptRoot/ComfyUI/cache/modelscope/hub"
$Env:SYCL_CACHE_DIR = "$PSScriptRoot/ComfyUI/cache/libsycl_cache"
$Env:TORCH_HOME = "$PSScriptRoot/ComfyUI/cache/torch"
$Env:U2NET_HOME = "$PSScriptRoot/ComfyUI/cache/u2net"
$Env:XDG_CACHE_HOME = "$PSScriptRoot/ComfyUI/cache"
$Env:PIP_CACHE_DIR = "$PSScriptRoot/ComfyUI/cache/pip"
$Env:PYTHONPYCACHEPREFIX = "$PSScriptRoot/ComfyUI/cache/pycache"
$Env:UV_CACHE_DIR = "$PSScriptRoot/ComfyUI/cache/uv"
$Env:UV_PYTHON = "$PSScriptRoot/ComfyUI/python/python.exe"



# 消息输出
function Print-Msg ($msg) {
    Write-Host "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")]" -ForegroundColor Yellow -NoNewline
    Write-Host "[ComfyUI Installer]" -ForegroundColor Cyan -NoNewline
    Write-Host ":: " -ForegroundColor Blue -NoNewline
    Write-Host "$msg"
}


# Pip 镜像源状态
function Pip-Mirror-Status {
    if ($USE_PIP_MIRROR) {
        Print-Msg "使用 Pip 镜像源"
    } else {
        Print-Msg "检测到 disable_pip_mirror.txt 配置文件, 已将 Pip 源切换至官方源"
    }
}


# 代理配置
function Set-Proxy {
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
    try:
        nums1 = re.sub(r'[a-zA-Z]+', '', version1).replace('-', '.').replace('+', '.').split('.')
        nums2 = re.sub(r'[a-zA-Z]+', '', version2).replace('-', '.').replace('+', '.').split('.')
    except:
        return 0

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
    Invoke-WebRequest -Uri $url -OutFile "$PSScriptRoot/ComfyUI/cache/python-3.10.11-amd64.zip"
    if ($?) { # 检测是否下载成功并解压
        # 创建 Python 文件夹
        if (!(Test-Path "$PSScriptRoot/ComfyUI/python")) {
            New-Item -ItemType Directory -Force -Path "$PSScriptRoot/ComfyUI/python" > $null
        }
        # 解压 Python
        Print-Msg "正在解压 Python"
        Expand-Archive -Path "$PSScriptRoot/ComfyUI/cache/python-3.10.11-amd64.zip" -DestinationPath "$PSScriptRoot/ComfyUI/python" -Force
        Remove-Item -Path "$PSScriptRoot/ComfyUI/cache/python-3.10.11-amd64.zip"
        Print-Msg "Python 安装成功"
    } else {
        Print-Msg "Python 安装失败, 终止 ComfyUI 安装进程, 可尝试重新运行 ComfyUI Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 下载并解压 Git
function Install-Git {
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/PortableGit.zip"
    Print-Msg "正在下载 Git"
    Invoke-WebRequest -Uri $url -OutFile "$PSScriptRoot/ComfyUI/cache/PortableGit.zip"
    if ($?) { # 检测是否下载成功并解压
        # 创建 Git 文件夹
        if (!(Test-Path "$PSScriptRoot/ComfyUI/git")) {
            New-Item -ItemType Directory -Force -Path $PSScriptRoot/ComfyUI/git > $null
        }
        # 解压 Git
        Print-Msg "正在解压 Git"
        Expand-Archive -Path "$PSScriptRoot/ComfyUI/cache/PortableGit.zip" -DestinationPath "$PSScriptRoot/ComfyUI/git" -Force
        Remove-Item -Path "$PSScriptRoot/ComfyUI/cache/PortableGit.zip"
        Print-Msg "Git 安装成功"
    } else {
        Print-Msg "Git 安装失败, 终止 ComfyUI 安装进程, 可尝试重新运行 ComfyUI Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 下载 Aria2
function Install-Aria2 {
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/aria2c.exe"
    Print-Msg "正在下载 Aria2"
    Invoke-WebRequest -Uri $url -OutFile "$PSScriptRoot/ComfyUI/cache/aria2c.exe"
    if ($?) {
        Move-Item -Path "$PSScriptRoot/ComfyUI/cache/aria2c.exe" -Destination "$PSScriptRoot/ComfyUI/git/bin/aria2c.exe" -Force
        Print-Msg "Aria2 下载成功"
    } else {
        Print-Msg "Aria2 下载失败, 终止 ComfyUI 安装进程, 可尝试重新运行 ComfyUI Installer 重试失败的安装"
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
        Print-Msg "uv 下载失败, 终止 ComfyUI 安装进程, 可尝试重新运行 ComfyUI Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# Github 镜像测试
function Test-Github-Mirror {
    if (Test-Path "$PSScriptRoot/disable_gh_mirror.txt") { # 禁用 Github 镜像源
        Print-Msg "检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件, 禁用 Github 镜像源"
    } else {
        $Env:GIT_CONFIG_GLOBAL = "$PSScriptRoot/ComfyUI/.gitconfig" # 设置 Git 配置文件路径
        if (Test-Path "$PSScriptRoot/ComfyUI/.gitconfig") {
            Remove-Item -Path "$PSScriptRoot/ComfyUI/.gitconfig" -Force
        }

        if (Test-Path "$PSScriptRoot/gh_mirror.txt") { # 使用自定义 Github 镜像源
            $github_mirror = Get-Content "$PSScriptRoot/gh_mirror.txt"
            git config --global --add safe.directory "*"
            git config --global url."$github_mirror".insteadOf "https://github.com"
            Print-Msg "检测到本地存在 gh_mirror.txt Github 镜像源配置文件, 已读取 Github 镜像源配置文件并设置 Github 镜像源"
        } else { # 自动检测可用镜像源并使用
            $status = 0
            ForEach($i in $GITHUB_MIRROR_LIST) {
                Print-Msg "测试 Github 镜像源: $i"
                if (Test-Path "$PSScriptRoot/ComfyUI/cache/github-mirror-test") {
                    Remove-Item -Path "$PSScriptRoot/ComfyUI/cache/github-mirror-test" -Force -Recurse
                }
                git clone $i/licyk/empty $PSScriptRoot/ComfyUI/cache/github-mirror-test --quiet
                if ($?) {
                    Print-Msg "该 Github 镜像源可用"
                    $github_mirror = $i
                    $status = 1
                    break
                } else {
                    Print-Msg "镜像源不可用, 更换镜像源进行测试"
                }
            }
            if (Test-Path "$PSScriptRoot/ComfyUI/cache/github-mirror-test") {
                Remove-Item -Path "$PSScriptRoot/ComfyUI/cache/github-mirror-test" -Force -Recurse
            }
            if ($status -eq 0) {
                Print-Msg "无可用 Github 镜像源, 取消使用 Github 镜像源"
                Remove-Item -Path env:GIT_CONFIG_GLOBAL -Force
            } else {
                Print-Msg "设置 Github 镜像源"
                git config --global --add safe.directory "*"
                git config --global url."$github_mirror".insteadOf "https://github.com"
            }
        }
    }
}


# Git 仓库下载
function Git-CLone {
    param (
        [String]$url,
        [String]$path
    )

    $name = [System.IO.Path]::GetFileNameWithoutExtension("$url")
    Print-Msg "检测 $name 是否已安装"
    $status = 0
    if (!(Test-Path "$path")) {
        $status = 1
    } else {
        $items = Get-ChildItem "$path" -Recurse
        if ($items.Count -eq 0) {
            $status = 1
        }
    }

    if ($status -eq 1) {
        Print-Msg "正在下载 $name"
        git clone --recurse-submodules $url "$path"
        if ($?) { # 检测是否下载成功
            Print-Msg "$name 安装成功"
        } else {
            Print-Msg "$name 安装失败, 终止 ComfyUI 安装进程, 可尝试重新运行 ComfyUI Installer 重试失败的安装"
            Read-Host | Out-Null
            exit 1
        }
    } else {
        Print-Msg "$name 已安装"
    }
}


# 安装 PyTorch
function Install-PyTorch {
    Print-Msg "检测是否需要安装 PyTorch"
    python -m pip show torch --quiet 2> $null
    if (!($?)) {
        Print-Msg "安装 PyTorch 中"
        if ($USE_UV) {
            uv pip install $PYTORCH_VER.ToString().Split()
            if (!($?)) {
                Print-Msg "检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装"
                python -m pip install $PYTORCH_VER.ToString().Split()
            }
        } else {
            python -m pip install $PYTORCH_VER.ToString().Split()
        }
        if ($?) {
            Print-Msg "PyTorch 安装成功"
        } else {
            Print-Msg "PyTorch 安装失败, 终止 ComfyUI 安装进程, 可尝试重新运行 ComfyUI Installer 重试失败的安装"
            Read-Host | Out-Null
            exit 1
        }
    } else {
        Print-Msg "PyTorch 已安装, 无需再次安装"
    }

    Print-Msg "检测是否需要安装 xFormers"
    python -m pip show xformers --quiet 2> $null
    if (!($?)) {
        Print-Msg "安装 xFormers 中"
        if ($USE_UV) {
            uv pip install $XFORMERS_VER --no-deps
            if (!($?)) {
                Print-Msg "检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装"
                python -m pip install $XFORMERS_VER --no-deps
            }
        } else {
            python -m pip install $XFORMERS_VER --no-deps
        }
        if ($?) {
            Print-Msg "xFormers 安装成功"
        } else {
            Print-Msg "xFormers 安装失败, 终止 ComfyUI 安装进程, 可尝试重新运行 ComfyUI Installer 重试失败的安装"
            Read-Host | Out-Null
            exit 1
        }
    } else {
        Print-Msg "xFormers 已安装, 无需再次安装"
    }
}


# 安装 ComfyUI 依赖
function Install-ComfyUI-Dependence {
    # 记录脚本所在路径
    $current_path = $(Get-Location).ToString()
    Set-Location "$PSScriptRoot/ComfyUI/ComfyUI"
    Print-Msg "安装 ComfyUI 依赖中"
    if ($USE_UV) {
        uv pip install -r requirements.txt
        if (!($?)) {
            Print-Msg "检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装"
            python -m pip install -r requirements.txt
        }
    } else {
        python -m pip install -r requirements.txt
    }
    if ($?) {
        Print-Msg "ComfyUI 依赖安装成功"
    } else {
        Print-Msg "ComfyUI 依赖安装失败, 终止 ComfyUI 安装进程, 可尝试重新运行 ComfyUI Installer 重试失败的安装"
        Set-Location "$current_path"
        Read-Host | Out-Null
        exit 1
    }
    Set-Location "$current_path"
}


# 安装
function Check-Install {
    New-Item -ItemType Directory -Path "$PSScriptRoot/ComfyUI" -Force > $null
    New-Item -ItemType Directory -Path "$PSScriptRoot/ComfyUI/cache" -Force > $null

    Print-Msg "检测是否安装 Python"
    if ((Test-Path "$PSScriptRoot/ComfyUI/python/python.exe") -or (Test-Path "$PSScriptRoot/ComfyUI/ComfyUI/python/python.exe")) {
        Print-Msg "Python 已安装"
    } else {
        Print-Msg "Python 未安装"
        Install-Python
    }

    # 切换 uv 指定的 Python
    if (Test-Path "$PSScriptRoot/ComfyUI/ComfyUI/python/python.exe") {
        $Env:UV_PYTHON = "$PSScriptRoot/ComfyUI/ComfyUI/python/python.exe"
    }

    Print-Msg "检测是否安装 Git"
    if ((Test-Path "$PSScriptRoot/ComfyUI/git/bin/git.exe") -or (Test-Path "$PSScriptRoot/ComfyUI/ComfyUI/git/bin/git.exe")) {
        Print-Msg "Git 已安装"
    } else {
        Print-Msg "Git 未安装"
        Install-Git
    }

    Print-Msg "检测是否安装 Aria2"
    if ((Test-Path "$PSScriptRoot/ComfyUI/git/bin/aria2c.exe") -or (Test-Path "$PSScriptRoot/ComfyUI/ComfyUI/git/bin/aria2c.exe")) {
        Print-Msg "Aria2 已安装"
    } else {
        Print-Msg "Aria2 未安装"
        Install-Aria2
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

    Test-Github-Mirror
    Git-CLone "$COMFYUI_REPO" "$PSScriptRoot/ComfyUI/ComfyUI"
    Git-CLone "https://github.com/ltdrdata/ComfyUI-Manager" "$PSScriptRoot/ComfyUI/ComfyUI/custom_nodes/ComfyUI-Manager"
    Git-CLone "https://github.com/AIGODLIKE/AIGODLIKE-COMFYUI-TRANSLATION" "$PSScriptRoot/ComfyUI/ComfyUI/custom_nodes/AIGODLIKE-COMFYUI-TRANSLATION"
    Install-PyTorch
    Install-ComfyUI-Dependence

    if (!(Test-Path "$PSScriptRoot/ComfyUI/launch_args.txt")) {
        Print-Msg "设置默认 ComfyUI 启动参数"
        $content = "--auto-launch --preview-method auto --disable-cuda-malloc"
        Set-Content -Encoding UTF8 -Path "$PSScriptRoot/ComfyUI/launch_args.txt" -Value $content
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/ComfyUI/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
}


# 启动脚本
function Write-Launch-Script {
    $content = "
# ComfyUI Installer 版本和检查更新间隔
`$COMFYUI_INSTALLER_VERSION = $COMFYUI_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# Pip 镜像源
`$PIP_INDEX_ADDR = `"$PIP_INDEX_ADDR`"
`$PIP_INDEX_ADDR_ORI = `"$PIP_INDEX_ADDR_ORI`"
`$PIP_EXTRA_INDEX_ADDR = `"$PIP_EXTRA_INDEX_ADDR`"
`$PIP_EXTRA_INDEX_ADDR_ORI = `"$PIP_EXTRA_INDEX_ADDR_ORI`"
`$PIP_FIND_ADDR = `"$PIP_FIND_ADDR`"
`$PIP_FIND_ADDR_ORI = `"$PIP_FIND_ADDR_ORI`"
`$USE_PIP_MIRROR = if (!(Test-Path `"`$PSScriptRoot/disable_pip_mirror.txt`")) { `$true } else { `$false }
`$PIP_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_INDEX_ADDR } else { `$PIP_INDEX_ADDR_ORI }
`$PIP_EXTRA_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_EXTRA_INDEX_ADDR } else { `$PIP_EXTRA_INDEX_ADDR_ORI }
`$PIP_FIND_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_FIND_ADDR } else { `$PIP_FIND_ADDR_ORI }
# `$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
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
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/git/bin`"
`$Env:PATH = `"`$PYTHON_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$GIT_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
# 环境变量
`$Env:PIP_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
`$Env:PIP_EXTRA_INDEX_URL = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`" } else { `$PIP_EXTRA_INDEX_MIRROR }
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
`$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
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
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[ComfyUI Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# Pip 镜像源状态
function Pip-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 Pip 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pip_mirror.txt 配置文件, 已将 Pip 源切换至官方源`"
    }
}


# 修复 PyTorch 的 libomp 问题
function Fix-PyTorch {
    `$content = `"
import importlib.util
import shutil
import os
import ctypes
import logging


torch_spec = importlib.util.find_spec('torch')
for folder in torch_spec.submodule_search_locations:
    lib_folder = os.path.join(folder, 'lib')
    test_file = os.path.join(lib_folder, 'fbgemm.dll')
    dest = os.path.join(lib_folder, 'libomp140.x86_64.dll')
    if os.path.exists(dest):
        break

    with open(test_file, 'rb') as f:
        contents = f.read()
        if b'libomp140.x86_64.dll' not in contents:
            break
    try:
        mydll = ctypes.cdll.LoadLibrary(test_file)
    except FileNotFoundError as e:
        logging.warning('检测到 PyTorch 版本存在 libomp 问题, 进行修复')
        shutil.copyfile(os.path.join(lib_folder, 'libiomp5md.dll'), dest)
`"

    python -c `"`$content`"
}


# ComfyUI Installer 更新检测
function Check-ComfyUI-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/comfyui_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/comfyui_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/comfyui_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 ComfyUI Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 ComfyUI Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/comfyui_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$PSScriptRoot/cache/comfyui_installer.ps1`" | Select-String -Pattern `"COMFYUI_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$COMFYUI_INSTALLER_VERSION) {
                    New-Item -ItemType File -Path `"`$PSScriptRoot/use_update_mode.txt`" -Force > `$null
                    Print-Msg `"检测到 ComfyUI Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"========================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 ComfyUI Installer 进行更新中`"
                        `$folder_name = Split-Path `$PSScriptRoot -Leaf
                        if (!(`$folder_name -eq `"ComfyUI`")) { # 检测脚本所在文件夹是否符合要求
                            Remove-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/update_time.txt`" 2> `$null
                            Print-Msg `"检测到 ComfyUI Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                            Print-Msg `"当前 ComfyUI Installer 管理脚本所在文件夹名称: `$folder_name`"
                            Print-Msg `"请前往 `$(Split-Path `"`$PSScriptRoot`") 路径, 将名称为 `$folder_name 的文件夹改名为 ComfyUI, 再重新更新 ComfyUI Installer 管理脚本`"
                            Print-Msg `"终止 ComfyUI Installer 的更新`"
                            Read-Host | Out-Null
                            exit 1
                        }
                        Move-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" `"`$PSScriptRoot/../comfyui_installer.ps1`" -Force
                        . `"`$PSScriptRoot/../comfyui_installer.ps1`"
                        Print-Msg `"更新结束, 需重新启动 ComfyUI Installer 管理脚本以应用更新, 回车退出 ComfyUI Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Remove-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" 2> `$null
                        Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                        Print-Msg `"跳过 ComfyUI Installer 更新`"
                    }
                } else {
                    Remove-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                    Print-Msg `"ComfyUI Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 ComfyUI Installer 更新中`"
                } else {
                    Print-Msg `"检查 ComfyUI Installer 更新失败`"
                }
            }
        }
    }
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


# HuggingFace 镜像源
function Set-HuggingFace-Mirror {
    if (!(Test-Path `"`$PSScriptRoot/disable_hf_mirror.txt`")) { # 检测是否禁用了自动设置 HuggingFace 镜像源
        if (Test-Path `"`$PSScriptRoot/hf_mirror.txt`") { # 本地存在 HuggingFace 镜像源配置
            `$hf_mirror_value = Get-Content `"`$PSScriptRoot/hf_mirror.txt`"
            `$Env:HF_ENDPOINT = `$hf_mirror_value
            Print-Msg `"检测到本地存在 hf_mirror.txt 配置文件, 已读取该配置并设置 HuggingFace 镜像源`"
        } else { # 使用默认设置
            `$Env:HF_ENDPOINT = `"https://hf-mirror.com`"
            Print-Msg `"使用默认 HuggingFace 镜像源`"
        }
    } else {
        Print-Msg `"检测到本地存在 disable_hf_mirror.txt 镜像源配置文件, 禁用自动设置 HuggingFace 镜像源`"
    }
}


# Github 镜像源
function Set-Github-Mirror {
    if (Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") { # 禁用 Github 镜像源
        Print-Msg `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件, 禁用 Github 镜像源`"
    } else {
        `$Env:GIT_CONFIG_GLOBAL = `"`$PSScriptRoot/.gitconfig`" # 设置 Git 配置文件路径
        if (Test-Path `"`$PSScriptRoot/.gitconfig`") {
            Remove-Item -Path `"`$PSScriptRoot/.gitconfig`" -Force
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
                if (Test-Path `"`$PSScriptRoot/cache/github-mirror-test`") {
                    Remove-Item -Path `"`$PSScriptRoot/cache/github-mirror-test`" -Force -Recurse
                }
                git clone `$i/licyk/empty `"`$PSScriptRoot/cache/github-mirror-test`" --quiet
                if (`$?) {
                    Print-Msg `"该 Github 镜像源可用`"
                    `$github_mirror = `$i
                    `$status = 1
                    break
                } else {
                    Print-Msg `"镜像源不可用, 更换镜像源进行测试`"
                }
            }
            if (Test-Path `"`$PSScriptRoot/cache/github-mirror-test`") {
                Remove-Item -Path `"`$PSScriptRoot/cache/github-mirror-test`" -Force -Recurse
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


# 检查 uv 是否需要更新
function Check-uv-Version {
    `$content = `"
import re
from importlib.metadata import version



def compare_versions(version1, version2) -> int:
    try:
        nums1 = re.sub(r'[a-zA-Z]+', '', version1).replace('-', '.').replace('+', '.').split('.')
        nums2 = re.sub(r'[a-zA-Z]+', '', version2).replace('-', '.').replace('+', '.').split('.')
    except:
        return 0

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
        # 切换 uv 指定的 Python
        if (Test-Path `"`$PSScriptRoot/ComfyUI/python/python.exe`") {
            `$Env:UV_PYTHON = `"`$PSScriptRoot/ComfyUI/python/python.exe`"
        }
        Check-uv-Version
    }
}


# ComfyUI 启动参数
function Get-ComfyUI-Launch-Args {
    if (Test-Path `"`$PSScriptRoot/launch_args.txt`") {
        `$args = Get-Content `"`$PSScriptRoot/launch_args.txt`"
        Print-Msg `"检测到本地存在 launch_args.txt 启动参数配置文件, 已读取该启动参数配置文件并应用启动参数`"
        Print-Msg `"使用的启动参数: `$args`"
    } else {
        `$args = `"`"
    }
    return `$args
}


# 设置 ComfyUI 的快捷启动方式
function Create-ComfyUI-Shortcut {
    `$filename = `"ComfyUI`"
    `$url = `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/comfyui_icon.ico`"
    `$shortcut_icon = `"`$PSScriptRoot/comfyui_icon.ico`"

    if (!(Test-Path `"`$PSScriptRoot/enable_shortcut.txt`")) {
        return
    }

    Print-Msg `"检查 ComfyUI 快捷启动方式中`"
    if (!(Test-Path `"`$shortcut_icon`")) {
        Print-Msg `"获取 ComfyUI 图标中`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/comfyui_icon.ico`"
        if (!(`$?)) {
            Print-Msg `"获取 ComfyUI 图标失败, 无法创建 ComfyUI 快捷启动方式`"
            return
        }
    }

    Print-Msg `"更新 ComfyUI 快捷启动方式`"
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


# 设置 CUDA 内存分配器
function Set-PyTorch-CUDA-Memory-Alloc {
    if (!(Test-Path `"`$PSScriptRoot/disable_set_pytorch_cuda_memory_alloc.txt`")) {
        Print-Msg `"检测是否可设置 CUDA 内存分配器`"
    } else {
        Print-Msg `"检测到 disable_set_pytorch_cuda_memory_alloc.txt 配置文件, 已禁用自动设置 CUDA 内存分配器`"
        return
    }

    `$content = `"
import os
import importlib.util
import subprocess

#Can't use pytorch to get the GPU names because the cuda malloc has to be set before the first import.
def get_gpu_names():
    if os.name == 'nt':
        import ctypes

        # Define necessary C structures and types
        class DISPLAY_DEVICEA(ctypes.Structure):
            _fields_ = [
                ('cb', ctypes.c_ulong),
                ('DeviceName', ctypes.c_char * 32),
                ('DeviceString', ctypes.c_char * 128),
                ('StateFlags', ctypes.c_ulong),
                ('DeviceID', ctypes.c_char * 128),
                ('DeviceKey', ctypes.c_char * 128)
            ]

        # Load user32.dll
        user32 = ctypes.windll.user32

        # Call EnumDisplayDevicesA
        def enum_display_devices():
            device_info = DISPLAY_DEVICEA()
            device_info.cb = ctypes.sizeof(device_info)
            device_index = 0
            gpu_names = set()

            while user32.EnumDisplayDevicesA(None, device_index, ctypes.byref(device_info), 0):
                device_index += 1
                gpu_names.add(device_info.DeviceString.decode('utf-8'))
            return gpu_names
        return enum_display_devices()
    else:
        gpu_names = set()
        out = subprocess.check_output(['nvidia-smi', '-L'])
        for l in out.split(b'\n'):
            if len(l) > 0:
                gpu_names.add(l.decode('utf-8').split(' (UUID')[0])
        return gpu_names

blacklist = {'GeForce GTX TITAN X', 'GeForce GTX 980', 'GeForce GTX 970', 'GeForce GTX 960', 'GeForce GTX 950', 'GeForce 945M',
                'GeForce 940M', 'GeForce 930M', 'GeForce 920M', 'GeForce 910M', 'GeForce GTX 750', 'GeForce GTX 745', 'Quadro K620',
                'Quadro K1200', 'Quadro K2200', 'Quadro M500', 'Quadro M520', 'Quadro M600', 'Quadro M620', 'Quadro M1000',
                'Quadro M1200', 'Quadro M2000', 'Quadro M2200', 'Quadro M3000', 'Quadro M4000', 'Quadro M5000', 'Quadro M5500', 'Quadro M6000',
                'GeForce MX110', 'GeForce MX130', 'GeForce 830M', 'GeForce 840M', 'GeForce GTX 850M', 'GeForce GTX 860M',
                'GeForce GTX 1650', 'GeForce GTX 1630', 'Tesla M4', 'Tesla M6', 'Tesla M10', 'Tesla M40', 'Tesla M60'
                }


def cuda_malloc_supported():
    try:
        names = get_gpu_names()
    except:
        names = set()
    for x in names:
        if 'NVIDIA' in x:
            for b in blacklist:
                if b in x:
                    return False
    return True


def is_nvidia_device():
    try:
        names = get_gpu_names()
    except:
        names = set()
    for x in names:
        if 'NVIDIA' in x:
            return True
    return False


def get_pytorch_cuda_alloc_conf():
    if is_nvidia_device():
        if cuda_malloc_supported():
            return 'cuda_malloc'
        else:
            return 'pytorch_malloc'
    else:
        return None


if __name__ == '__main__':
    try:
        version = ''
        torch_spec = importlib.util.find_spec('torch')
        for folder in torch_spec.submodule_search_locations:
            ver_file = os.path.join(folder, 'version.py')
            if os.path.isfile(ver_file):
                spec = importlib.util.spec_from_file_location('torch_version_import', ver_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                version = module.__version__
        if int(version[0]) >= 2: #enable by default for torch version 2.0 and up
            print(get_pytorch_cuda_alloc_conf())
        else:
            print(None)
    except:
        print(None)
`"

    `$status = `$(python -c `"`$content`")
    switch (`$status) {
        cuda_malloc {
            Print-Msg `"设置 CUDA 内存分配器为 CUDA 内置异步分配器`"
            `$Env:PYTORCH_CUDA_ALLOC_CONF = `"backend:cudaMallocAsync`"
        }
        pytorch_malloc {
            Print-Msg `"设置 CUDA 内存分配器为 PyTorch 原生分配器`"
            `$Env:PYTORCH_CUDA_ALLOC_CONF = `"garbage_collection_threshold:0.9,max_split_size_mb:512`"
        }
        Default {
            Print-Msg `"显卡非 Nvidia 显卡, 无法设置 CUDA 内存分配器`"
        }
    }
}


# 检查 ComfyUI 依赖完整性
function Check-ComfyUI-Requirements {
    `$content = `"
import os
import re
import argparse
import importlib.metadata
from pathlib import Path


# 参数输入
def get_args():
    parser = argparse.ArgumentParser()
    normalized_filepath = lambda filepath: str(Path(filepath).absolute().as_posix())

    parser.add_argument('--requirement-path', type = normalized_filepath, default = None, help = '依赖文件路径')

    return parser.parse_args()


# 判断 2 个版本的大小, 前面大返回 1, 后面大返回 -1, 相同返回 0
def compare_versions(version1, version2):
    try:
        nums1 = re.sub(r'[a-zA-Z]+', '', version1).replace('-', '.').replace('+', '.').split('.')
        nums2 = re.sub(r'[a-zA-Z]+', '', version2).replace('-', '.').replace('+', '.').split('.')
    except:
        return 0

    for i in range(max(len(nums1), len(nums2))):
        num1 = int(nums1[i]) if i < len(nums1) else 0  # 如果版本号 1 的位数不够, 则补 0
        num2 = int(nums2[i]) if i < len(nums2) else 0  # 如果版本号 2 的位数不够, 则补 0

        if num1 == num2:
            continue
        elif num1 > num2:
            return 1  # 版本号 1 更大
        else:
            return -1  # 版本号 2 更大

    return 0  # 版本号相同


# 获取包版本号
def get_pkg_ver_from_lib(pkg_name: str) -> str:
    try:
        ver = importlib.metadata.version(pkg_name)
    except:
        ver = None

    if ver is None:
        try:
            ver = importlib.metadata.version(pkg_name.lower())
        except:
            ver = None

    if ver is None:
        try:
            ver = importlib.metadata.version(pkg_name.replace('_', '-'))
        except:
            ver = None

    return ver


# 确认是否安装某个软件包
def is_installed(package: str) -> bool:
    #
    # This function was adapted from code written by vladimandic: https://github.com/vladmandic/automatic/commits/master
    #

    # Remove brackets and their contents from the line using regular expressions
    # e.g., diffusers[torch]==0.10.2 becomes diffusers==0.10.2
    package = re.sub(r'\[.*?\]', '', package)

    try:
        pkgs = [
            p
            for p in package.split()
            if not p.startswith('-') and not p.startswith('=')
        ]
        pkgs = [
            p.split('/')[-1] for p in pkgs
        ]   # get only package name if installing from URL

        for pkg in pkgs:
            # 去除从 Git 链接安装的软件包后面的 .git
            pkg = pkg.split('.git')[0] if pkg.endswith('.git') else pkg
            if '>=' in pkg:
                pkg_name, pkg_version = [x.strip() for x in pkg.split('>=')]
            elif '==' in pkg:
                pkg_name, pkg_version = [x.strip() for x in pkg.split('==')]
            elif '<=' in pkg:
                pkg_name, pkg_version = [x.strip() for x in pkg.split('<=')]
            elif '<' in pkg:
                pkg_name, pkg_version = [x.strip() for x in pkg.split('<')]
            elif '>' in pkg:
                pkg_name, pkg_version = [x.strip() for x in pkg.split('>')]
            else:
                pkg_name, pkg_version = pkg.strip(), None

            # 获取本地 Python 软件包信息
            version = get_pkg_ver_from_lib(pkg_name)

            if version is not None:
                # 判断版本是否符合要求
                if pkg_version is not None:
                    if '>=' in pkg:
                        # ok = version >= pkg_version
                        if compare_versions(version, pkg_version) == 1 or compare_versions(version, pkg_version) == 0:
                            ok = True
                        else:
                            ok = False
                    elif '<=' in pkg:
                        # ok = version <= pkg_version
                        if compare_versions(version, pkg_version) == -1 or compare_versions(version, pkg_version) == 0:
                            ok = True
                        else:
                            ok = False
                    elif '>' in pkg:
                        # ok = version > pkg_version
                        if compare_versions(version, pkg_version) == 1:
                            ok = True
                        else:
                            ok = False
                    elif '<' in pkg:
                        # ok = version < pkg_version
                        if compare_versions(version, pkg_version) == -1:
                            ok = True
                        else:
                            ok = False
                    else:
                        # ok = version == pkg_version
                        if compare_versions(version, pkg_version) == 0:
                            ok = True
                        else:
                            ok = False

                    if not ok:
                        return False
            else:
                return False

        return True
    except ModuleNotFoundError:
        return False


# 验证是否存在未安装的依赖
def validate_requirements(requirements_file: str):
    with open(requirements_file, 'r', encoding = 'utf8') as f:
        lines = [
            line.strip()
            for line in f.readlines()
            if line.strip() != ''
            and not line.startswith('#')
            and not (line.startswith('-') and not line.startswith('--index-url '))
            and line is not None
            and '# skip_verify' not in line
        ]

        for line in lines:
            if line.startswith('--index-url '):
                continue

            if not is_installed(line.split()[0].strip()):
                return False

    return True



if __name__ == '__main__':
    args = get_args()
    path = args.requirement_path
    print(validate_requirements(path))
`"
    if (!(Test-Path `"`$PSScriptRoot/cache`")) {
        New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" > `$null
    }
    Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/cache/check_comfyui_requirement.py`" -Value `$content

    `$status = `$(python `"`$PSScriptRoot/cache/check_comfyui_requirement.py`" --requirement-path `"`$PSScriptRoot/ComfyUI/requirements.txt`")

    if (`$status -eq `"False`") {
        Print-Msg `"检测到 ComfyUI 内核有依赖缺失, 安装 ComfyUI 依赖中`"
        if (`$USE_UV) {
            uv pip install `"`$PSScriptRoot/ComfyUI/requirements.txt`"
            if (!(`$?)) {
                Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
                python -m pip install `"`$PSScriptRoot/ComfyUI/requirements.txt`"
            }
        } else {
            python -m pip install `"`$PSScriptRoot/ComfyUI/requirements.txt`"
        }
        if (`$?) {
            Print-Msg `"ComfyUI 依赖安装成功`"
        } else {
            Print-Msg `"ComfyUI 依赖安装失败, 这将会导致 ComfyUI 缺失依赖无法正常运行`"
        }
    } else {
        Print-Msg `"ComfyUI 无缺失依赖`"
    }
}


# 检查 ComfyUI 环境中组件依赖
function Check-ComfyUI-Env-Requirements {
    `$content = `"
import os
import re
import argparse
import importlib.metadata
from pathlib import Path



# 参数输入
def get_args():
    parser = argparse.ArgumentParser()
    normalized_filepath = lambda filepath: str(Path(filepath).absolute().as_posix())

    parser.add_argument('--comfyui-path', type = normalized_filepath, default = None, help = 'ComfyUI 路径')
    parser.add_argument('--conflict-depend-notice-path', type = normalized_filepath, default = None, help = '保存 ComfyUI 扩展依赖冲突信息的文件路径')
    parser.add_argument('--requirement-list-path', type = normalized_filepath, default = None, help = '保存 ComfyUI 需要安装扩展依赖的路径列表')

    return parser.parse_args()


# 获取 ComfyUI / ComfyUI 自定义节点的依赖记录文件
def get_requirement_file(path: str) -> dict:
    requirement_list = {}
    requirement_list['ComfyUI'] = {}
    requirement_list['ComfyUI'] = {'requirements_path': Path(os.path.join(path, 'requirements.txt')).as_posix()}
    for custom_node_name in os.listdir(os.path.join(path, 'custom_nodes')):
        if custom_node_name.endswith('.disabled'):
                continue
        custom_node_requirement = Path(os.path.join(path, 'custom_nodes', custom_node_name, 'requirements.txt')).as_posix()
        if os.path.exists(custom_node_requirement):
            requirement_list[custom_node_name] = {'requirements_path': custom_node_requirement}

    return requirement_list


# 读取依赖文件中的包名
def get_requirement_list(requirement_list: dict) -> dict:
    for requirement_name in requirement_list:
        requirements_path = requirement_list.get(requirement_name).get('requirements_path')
        requirements = [] # Python 包名列表
        try:
            with open(requirements_path, 'r', encoding = 'utf8') as f:
                # 处理文件内容
                lines = [
                    line.strip()
                    for line in f.readlines()
                    if line.strip() != ''
                    and not line.startswith('#')
                    and not (line.startswith('-')
                    and not line.startswith('--index-url '))
                    and line is not None
                    and '# skip_verify' not in line
                ]

                # 添加到 Python 包名列表
                for line in lines:
                    requirements.append(line)

                requirement_list[requirement_name] = {'requirements_path': requirements_path, 'requirements': requirements}
        except:
            pass

    return requirement_list


# 获取包版本号
def get_pkg_ver_from_lib(pkg_name: str) -> str:
    try:
        ver = importlib.metadata.version(pkg_name)
    except:
        ver = None

    if ver is None:
        try:
            ver = importlib.metadata.version(pkg_name.lower())
        except:
            ver = None

    if ver is None:
        try:
            ver = importlib.metadata.version(pkg_name.replace('_', '-'))
        except:
            ver = None

    return ver


# 判断是否有软件包未安装
def is_installed(package: str) -> bool:
    # 使用正则表达式删除括号和括号内的内容
    # 如: diffusers[torch]==0.10.2 -> diffusers==0.10.2
    package = re.sub(r'\[.*?\]', '', package)

    try:
        pkgs = [
            p
            for p in package.split()
            if not p.startswith('-') and not p.startswith('=')
        ]
        pkgs = [
            p.split('/')[-1] for p in pkgs
        ]   # 如果软件包从网址获取则只截取名字

        for pkg in pkgs:
            # 去除从 Git 链接安装的软件包后面的 .git
            pkg = pkg.split('.git')[0] if pkg.endswith('.git') else pkg
            if '>=' in pkg:
                pkg_name, pkg_version = [x.strip() for x in pkg.split('>=')]
            elif '==' in pkg:
                pkg_name, pkg_version = [x.strip() for x in pkg.split('==')]
            elif '<=' in pkg:
                pkg_name, pkg_version = [x.strip() for x in pkg.split('<=')]
            elif '<' in pkg:
                pkg_name, pkg_version = [x.strip() for x in pkg.split('<')]
            elif '>' in pkg:
                pkg_name, pkg_version = [x.strip() for x in pkg.split('>')]
            else:
                pkg_name, pkg_version = pkg.strip(), None

            # 获取本地 Python 软件包信息
            version = get_pkg_ver_from_lib(pkg_name)

            if version is not None:
                # 判断版本是否符合要求
                if pkg_version is not None:
                    if '>=' in pkg:
                        # ok = version >= pkg_version
                        if compare_versions(version, pkg_version) == 1 or compare_versions(version, pkg_version) == 0:
                            ok = True
                        else:
                            ok = False
                    elif '<=' in pkg:
                        # ok = version <= pkg_version
                        if compare_versions(version, pkg_version) == -1 or compare_versions(version, pkg_version) == 0:
                            ok = True
                        else:
                            ok = False
                    elif '>' in pkg:
                        # ok = version > pkg_version
                        if compare_versions(version, pkg_version) == 1:
                            ok = True
                        else:
                            ok = False
                    elif '<' in pkg:
                        # ok = version < pkg_version
                        if compare_versions(version, pkg_version) == -1:
                            ok = True
                        else:
                            ok = False
                    else:
                        # ok = version == pkg_version
                        if compare_versions(version, pkg_version) == 0:
                            ok = True
                        else:
                            ok = False

                    if not ok:
                        return False
            else:
                return False

        return True
    except ModuleNotFoundError:
        return False


def check_missing_requirement(requirement_list: dict) -> dict:
    for requirement_name in requirement_list:
        requirements_path = requirement_list.get(requirement_name).get('requirements_path')
        requirements = requirement_list.get(requirement_name).get('requirements')

        missing_requirement = []
        for pkg in requirements:
            if not is_installed(pkg.split()[0].strip()):
                missing_requirement.append(pkg)

        requirement_list[requirement_name] = {'requirements_path': requirements_path, 'requirements': requirements, 'missing_requirement': missing_requirement}

    return requirement_list


# 格式化包名
def format_package_name(package: str) -> str:
    package = re.sub(r'\[.*?\]', '', package)

    pkgs = [
        p
        for p in package.split()
        if not p.startswith('-') and not p.startswith('=')
    ]
    pkgs = [
        p.split('/')[-1] for p in pkgs
    ]   # 如果软件包从网址获取则只截取名字

    for pkg in pkgs:
        # 除去从 Git 链接中的 .git 后缀
        pkg.split('.git')[0] if pkg.endswith('.git') else pkg
        return pkg


# 去重
def remove_duplicate(lists: list) -> list:
    return list(set(lists))


# 获取包版本号
def get_version(ver: str) -> str:
    # return ''.join(re.findall(r'\d+', ver))
    return ver.split('>').pop().split('<').pop().split('=').pop()


# 判断是否有版本号
def has_version(ver: str) -> bool:
    if re.sub(r'\d+', '', ver) != ver:
        return True
    else:
        return False


# 获取包名(去除版本号)
def get_package_name(pkg: str) -> str:
    return pkg.split('>')[0].split('<')[0].split('==')[0]


# 判断 2 个版本的大小, 前面大返回 1, 后面大返回 -1, 相同返回 0
def compare_versions(version1, version2):
    try:
        nums1 = re.sub(r'[a-zA-Z]+', '', version1).replace('-', '.').replace('+', '.').split('.')
        nums2 = re.sub(r'[a-zA-Z]+', '', version2).replace('-', '.').replace('+', '.').split('.')
    except:
        return 0

    for i in range(max(len(nums1), len(nums2))):
        num1 = int(nums1[i]) if i < len(nums1) else 0  # 如果版本号 1 的位数不够, 则补 0
        num2 = int(nums2[i]) if i < len(nums2) else 0  # 如果版本号 2 的位数不够, 则补 0

        if num1 == num2:
            continue
        elif num1 > num2:
            return 1  # 版本号 1 更大
        else:
            return -1  # 版本号 2 更大

    return 0  # 版本号相同


# 检测是否为冲突依赖
def detect_conflict_package(pkg_1: str, pkg_2: str) -> bool:
    if not has_version(get_version(pkg_1)) or not has_version(get_version(pkg_2)):
        return False

    # 进行 2 次循环, 第 2 次循环时交换版本后再进行判断
    for i in range(2):
        if i == 1:
            tmp = pkg_1
            pkg_1 = pkg_2
            pkg_2 = tmp

        # >=, <=
        if '>=' in pkg_1 and '<=' in pkg_2:
            ver_1 = get_version(pkg_1.split('>=').pop())
            ver_2 = get_version(pkg_2.split('<=').pop())
            if compare_versions(ver_1, ver_2) == 1:
                return True

        # >=, <
        if '>=' in pkg_1 and '<' in pkg_2 and '=' not in pkg_2:
            ver_1 = get_version(pkg_1.split('>=').pop())
            ver_2 = get_version(pkg_2.split('<').pop())
            if compare_versions(ver_1, ver_2) == 0 or compare_versions(ver_1, ver_2) == 1:
                return True

        # >, <=
        if '>' in pkg_1 and '=' not in pkg_1 and '<=' in pkg_2:
            ver_1 = get_version(pkg_1.split('>').pop())
            ver_2 = get_version(pkg_2.split('<=').pop())
            if compare_versions(ver_1, ver_2) == 0 or compare_versions(ver_1, ver_2) == 1:
                return True

        # >, <
        if '>' in pkg_1 and '=' not in pkg_1 and '<' in pkg_2 and '=' not in pkg_2:
            ver_1 = get_version(pkg_1.split('>').pop())
            ver_2 = get_version(pkg_2.split('<').pop())
            if compare_versions(ver_1, ver_2) == 0 or compare_versions(ver_1, ver_2) == 1:
                return True

        # >, ==
        if '>' in pkg_1 and '=' not in pkg_1 and '==' in pkg_2:
            ver_1 = get_version(pkg_1.split('>').pop())
            ver_2 = get_version(pkg_2.split('==').pop())
            if compare_versions(ver_1, ver_2) == 1 or compare_versions(ver_1, ver_2) == 0:
                return True

        # >=, ==
        if '>=' in pkg_1 and '==' in pkg_2:
            ver_1 = get_version(pkg_1.split('>').pop())
            ver_2 = get_version(pkg_2.split('==').pop())
            if compare_versions(ver_1, ver_2) == 1:
                return True

        # <, ==
        if '<' in pkg_1 and '=' not in pkg_1 and '==' in pkg_2:
            ver_1 = get_version(pkg_1.split('<').pop())
            ver_2 = get_version(pkg_2.split('==').pop())
            if compare_versions(ver_1, ver_2) == -1 or compare_versions(ver_1, ver_2) == 0:
                return True

        # <=, ==
        if '<=' in pkg_1 and '==' in pkg_2:
            ver_1 = get_version(pkg_1.split('<=').pop())
            ver_2 = get_version(pkg_2.split('==').pop())
            if compare_versions(ver_1, ver_2) == -1:
                return True

        # ==, ==
        if '==' in pkg_1 and '==' in pkg_2:
            ver_1 = get_version(pkg_1.split('==').pop())
            ver_2 = get_version(pkg_2.split('==').pop())
            if compare_versions(ver_1, ver_2) != 0:
                return True

    return False


# 标记包含冲突依赖的自定义节点
def find_conflict(requirement_list: dict, conflict_package) -> dict:
    for requirement_name in requirement_list:
        requirements_path = requirement_list.get(requirement_name).get('requirements_path')
        requirements = requirement_list.get(requirement_name).get('requirements')
        missing_requirement = requirement_list.get(requirement_name).get('missing_requirement')
        has_conflict_package = False
        for pkg_1 in conflict_package:
            for pkg_2 in requirements:
                if pkg_1 == get_package_name(format_package_name(pkg_2)) and has_version(pkg_2):
                    has_conflict_package = True
                    break

        requirement_list[requirement_name] = {'requirements_path': requirements_path, 'requirements': requirements, 'missing_requirement': missing_requirement, 'has_conflict_package': has_conflict_package}

    return requirement_list


# 统计冲突依赖信息
def sum_conflict_notice(requirement_list: dict, conflict_package) -> list:
    content = []
    # 读取冲突的包名
    for conflict_pkg in conflict_package:
        content.append(f'{conflict_pkg}:')
        # 读取依赖记录表
        for requirement_name in requirement_list:

            # 查找自定义节点中的依赖是否包含冲突依赖
            for pkg in requirement_list.get(requirement_name).get('requirements'):
                if conflict_pkg.lower() == get_package_name(format_package_name(pkg)).lower() and has_version(pkg):
                    content.append(f' - {requirement_name}: {pkg}')

        content.append('')

    content = content[:-1] if len(content) > 0 and content[-1] == '' else content
    return content


# 将内容写入文件中
def write_content_to_file(content: list, path: str) -> None:
    if len(content) == 0:
        return

    with open(path, 'w', encoding = 'utf8') as f:
        for item in content:
            f.write(item + '\n')


# 找出需要安装依赖的自定义节点并将依赖表的路径进行记录
def sum_need_to_install(requirement_list: dict) -> list:
    path_list = []
    for i in requirement_list:
        if len(requirement_list.get(i).get('missing_requirement')) != 0:
            path_list.append(requirement_list.get(i).get('requirements_path'))

    for i in requirement_list:
        if requirement_list.get(i).get('has_conflict_package') is True:
            path_list.append(requirement_list.get(i).get('requirements_path'))

    return path_list



if __name__ == '__main__':
    args = get_args()
    comfyui_path = args.comfyui_path
    term_sd_notice_path = args.conflict_depend_notice_path
    term_sd_need_install_requirement_path = args.requirement_list_path

    lists = get_requirement_list(get_requirement_file(comfyui_path))
    lists = check_missing_requirement(lists)
    pkg_list = [] # 依赖列表
    conflict_package = [] # 冲突的依赖列表

    # 记录依赖
    for i in lists:
        for pkg_name in lists.get(i).get('requirements'):
            pkg_list.append(format_package_name(pkg_name))


    # 判断冲突依赖
    for i in pkg_list:
        for j in pkg_list:
            if get_package_name(i) == get_package_name(j) and detect_conflict_package(i.lower(), j.lower()):
                conflict_package.append(i)

    # conflict_package = remove_duplicate(conflict_package)
    conflict_package = remove_duplicate([get_package_name(x) for x in conflict_package]) # 去除版本号并去重
    lists = find_conflict(lists, conflict_package) # 将有冲突依赖的自定义节点进行标记
    notice = sum_conflict_notice(lists, conflict_package)
    path_list = remove_duplicate(sum_need_to_install(lists))
    write_content_to_file(notice, term_sd_notice_path)
    write_content_to_file(path_list, term_sd_need_install_requirement_path)
`"
    Print-Msg `"检测 ComfyUI 运行环境组件依赖中`"
    if (!(Test-Path `"`$PSScriptRoot/cache`")) {
        New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" > `$null
    }
    Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/cache/check_comfyui_env.py`" -Value `$content
    Remove-Item -Path `"`$PSScriptRoot/cache/comfyui_requirement_list.txt`" 2> `$null
    Remove-Item -Path `"`$PSScriptRoot/cache/comfyui_conflict_requirement_list.txt`" 2> `$null

    python `"`$PSScriptRoot/cache/check_comfyui_env.py`" --comfyui-path `"`$PSScriptRoot/ComfyUI`" --conflict-depend-notice-path `"`$PSScriptRoot/cache/comfyui_conflict_requirement_list.txt`" --requirement-list-path `"`$PSScriptRoot/cache/comfyui_requirement_list.txt`" `

    if (Test-Path `"`$PSScriptRoot/cache/comfyui_conflict_requirement_list.txt`") {
        Print-Msg `"检测到当前 ComfyUI 环境中安装的插件之间存在依赖冲突情况, 该问题并非致命, 但建议只保留一个插件, 否则部分功能可能无法正常使用`"
        Print-Msg `"您可以选择按顺序安装依赖, 由于这将向环境中安装不符合版本要求的组件, 您将无法完全解决此问题, 但可避免组件由于依赖缺失而无法启动的情况`"
        Print-Msg `"您通常情况下可以选择忽略该警告并继续运行`"
        Write-Host `"-------------------------------------------------------------------------------`"
        Write-Host `"发生冲突的组件:`"
        `$content = Get-Content `"`$PSScriptRoot/cache/comfyui_conflict_requirement_list.txt`"
        for (`$i = 0; `$i -lt `$content.Length; `$i++) {
            Write-Host `$content[`$i]
        }
        Write-Host `"-------------------------------------------------------------------------------`"
        Print-Msg `"是否按顺序安装冲突依赖 (yes/no) ?`"
        Print-Msg `"提示:`"
        Print-Msg `"如果不选择按顺序安装冲突依赖, 则跳过安装冲突依赖直接运行 ComfyUI`"
        Print-Msg `"输入 yes 或 no 后回车`"
        `$option = Read-Host `"========================================>`"
        if (`$option -eq `"yes`" -or `$option -eq `"y`" -or `$option -eq `"YES`" -or `$option -eq `"Y`") {
            Print-Msg `"按顺序安装冲突组件依赖中`"
        } else {
            Print-Msg `"跳过按顺序安装组件依赖`"
            return
        }
    }

    # 安装组件依赖
    if (!(Test-Path `"`$PSScriptRoot/cache/comfyui_requirement_list.txt`")) {
        Print-Msg `"ComfyUI 无组件依赖缺失`"
        return
    }
    `$requirement_list = Get-Content `"`$PSScriptRoot/cache/comfyui_requirement_list.txt`"
    `$sum = if (`$requirement_list.GetType().Name -eq `"String`") { 1 } else { `$requirement_list.Length }
    for (`$i = 0; `$i -lt `$sum; `$i++) {
        `$path = if (`$requirement_list.GetType().Name -eq `"String`") { `$requirement_list } else { `$requirement_list[`$i] }
        `$name = Split-Path `$(Split-Path `$path -Parent) -Leaf

        Print-Msg `"[`$(`$i + 1)/`$sum]:: 安装 `$name 组件依赖中`"
        if (`$USE_UV) {
            uv pip install -r `"`$path`"
            if (!(`$?)) {
                Print-Msg `"[`$(`$i + 1)/`$sum]:: 检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
                python -m pip install -r `"`$path`"
            }
        } else {
            python -m pip install -r `"`$path`"
        }
        if (`$?) {
            Print-Msg `"[`$(`$i + 1)/`$sum]:: `$name 组件依赖安装成功`"
        } else {
            Print-Msg `"[`$(`$i + 1)/`$sum]:: `$name 组件依赖安装失败, 可能会导致该组件缺失依赖出现运行异常`"
        }

        `$install_script = `"`$(Split-Path `$path -Parent)/install.py`"
        if (Test-Path `"`$install_script`") {
            Print-Msg `"[`$(`$i + 1)/`$sum]:: 执行 `$name 的依赖安装脚本中`"
            python `"`$install_script`"
            if (`$?) {
                Print-Msg `"[`$(`$i + 1)/`$sum]:: `$name 组件依赖安装脚本执行成功`"
            } else {
                Print-Msg `"[`$(`$i + 1)/`$sum]:: `$name 组件依赖安装脚本执行失败, 可能会导致该组件缺失依赖出现运行异常`"
            }
        }
    }
}


# 检查 onnxruntime-gpu 版本问题
function Check-Onnxruntime-GPU {
    `$content = `"
import re
import importlib.metadata
from pathlib import Path



# 获取记录 onnxruntime 版本的文件路径
def get_onnxruntime_version_file() -> str:
    package = 'onnxruntime-gpu'
    try:
        util = [p for p in importlib.metadata.files(package) if 'onnxruntime/capi/version_info.py' in str(p)][0]
        info_path = Path(util.locate()).as_posix()
    except importlib.metadata.PackageNotFoundError:
        info_path = None

    return info_path


# 获取 onnxruntime 支持的 CUDA 版本
def get_onnxruntime_support_cuda_version() -> tuple:
    ver_path = get_onnxruntime_version_file()
    cuda_ver = None
    cudnn_ver = None
    try:
        with open(ver_path, 'r', encoding = 'utf8') as f:
            for line in f:
                if 'cuda_version' in line:
                    cuda_ver = line.strip()
                if 'cudnn_version' in line:
                    cudnn_ver = line.strip()
    except:
        pass

    return cuda_ver, cudnn_ver


# 截取版本号
def get_version(ver: str) -> str:
    return ''.join(re.findall(r'\d+', ver.split('=').pop().strip()))


# 判断版本
def compare_versions(version1: str, version2: str) -> int:
    nums1 = re.sub(r'[a-zA-Z]+', '', version1).split('.')  # 将版本号 1 拆分成数字列表
    nums2 = re.sub(r'[a-zA-Z]+', '', version2).split('.')  # 将版本号 2 拆分成数字列表

    for i in range(max(len(nums1), len(nums2))):
        num1 = int(nums1[i]) if i < len(nums1) else 0  # 如果版本号 1 的位数不够, 则补 0
        num2 = int(nums2[i]) if i < len(nums2) else 0  # 如果版本号 2 的位数不够, 则补 0

        if num1 == num2:
            continue
        elif num1 > num2:
            return 1  # 版本号 1 更大
        else:
            return -1  # 版本号 2 更大

    return 0  # 版本号相同


# 获取 Torch 的 CUDA, CUDNN 版本
def get_torch_cuda_ver() -> tuple:
    try:
        import torch
        return torch.__version__, int(str(torch.backends.cudnn.version())[0]) if torch.backends.cudnn.version() is not None else None
    except:
        return None, None


# 判断需要安装的 onnxruntime 版本
def need_install_ort_ver():
    # 检测是否安装了 Torch
    torch_ver, cuddn_ver = get_torch_cuda_ver()
    # 缺少 Torch 版本或者 CUDNN 版本时取消判断
    if torch_ver is None or cuddn_ver is None:
        return None

    # 检测是否安装了 onnxruntime-gpu
    ort_support_cuda_ver, ort_support_cudnn_ver = get_onnxruntime_support_cuda_version()
    # 通常 onnxruntime 的 CUDA 版本和 CUDNN 版本会同时存在, 所以只需要判断 CUDA 版本是否存在即可
    if ort_support_cuda_ver is None:
        return None

    ort_support_cuda_ver = get_version(ort_support_cuda_ver)
    ort_support_cudnn_ver = int(get_version(ort_support_cudnn_ver))

    # 判断 Torch 中的 CUDA 版本是否为 CUDA 12.1
    if 'cu12' in torch_ver: # CUDA 12.1
        # 比较 onnxtuntime 支持的 CUDA 版本是否和 Torch 中所带的 CUDA 版本匹配
        if compare_versions(ort_support_cuda_ver, '12.0') == 1:
            # CUDA 版本为 12.x, torch 和 ort 的 CUDA 版本匹配

            # 判断 torch 和 ort 的 CUDNN 是否匹配
            if ort_support_cudnn_ver > cuddn_ver: # ort CUDNN 版本 > torch CUDNN 版本
                return 'cu121cudnn8'
            elif ort_support_cudnn_ver < cuddn_ver: # ort CUDNN 版本 < torch CUDNN 版本
                return 'cu121cudnn9'
            else:
                return None
        else:
            # CUDA 版本非 12.x
            if cuddn_ver > 8:
                return 'cu121cudnn9'
            else:
                return 'cu121cudnn8'
    else: # CUDA <= 11.8
        if compare_versions(ort_support_cuda_ver, '12.0') == -1:
            return None
        else:
            return 'cu118'



if __name__ == '__main__':
    print(need_install_ort_ver())
`"
    Print-Msg `"检查 onnxruntime-gpu 版本问题中`"
    `$status = `$(python -c `"`$content`")

    `$need_reinstall_ort = `$false
    `$need_switch_mirror = `$false
    switch (`$status) {
        cu118 {
            `$need_reinstall_ort = `$true
            `$ort_version = `"onnxruntime-gpu==1.18.1`"
        }
        cu121cudnn9 {
            `$need_reinstall_ort = `$true
            `$ort_version = `"onnxruntime-gpu>=1.19.0`"
        }
        cu121cudnn8 {
            `$need_reinstall_ort = `$true
            `$ort_version = `"onnxruntime-gpu==1.17.1`"
            `$need_switch_mirror = `$true
        }
        Default {
            `$need_reinstall_ort = `$false
        }
    }

    if (`$need_reinstall_ort) {
        Print-Msg `"检测到 onnxruntime-gpu 所支持的 CUDA 版本 和 PyTorch 所支持的 CUDA 版本不匹配, 将执行重装操作`"
        if (`$need_switch_mirror) {
            `$tmp_pip_index_url = `$Env:PIP_INDEX_URL
            `$tmp_pip_extra_index_url = `$Env:PIP_EXTRA_INDEX_URL
            `$tmp_uv_index_url = `$Env:UV_INDEX_URL
            `$tmp_UV_extra_index_url = `$Env:UV_EXTRA_INDEX_URL
            `$Env:PIP_INDEX_URL = `"https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/`"
            `$Env:PIP_EXTRA_INDEX_URL = `"https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple`"
            `$Env:UV_INDEX_URL = `"https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/`"
            `$Env:UV_EXTRA_INDEX_URL = `"https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple`"
        }

        Print-Msg `"卸载原有的 onnxruntime-gpu 中`"
        python -m pip uninstall onnxruntime-gpu -y

        Print-Msg `"重新安装 onnxruntime-gpu 中`"
        if (`$USE_UV) {
            uv pip install `$ort_version
            if (!(`$?)) {
                Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
                python -m pip install `$ort_version
            }
        } else {
            python -m pip install `$ort_version
        }
        if (`$?) {
            Print-Msg `"onnxruntime-gpu 重新安装成功`"
        } else {
            Print-Msg `"onnxruntime-gpu 重新安装失败, 这可能导致部分功能无法正常使用, 如使用反推模型无法正常调用 GPU 导致推理降速`"
        }

        if (`$need_switch_mirror) {
            `$Env:PIP_INDEX_URL = `$tmp_pip_index_url
            `$Env:PIP_EXTRA_INDEX_URL = `$tmp_pip_extra_index_url
            `$Env:UV_INDEX_URL = `$tmp_uv_index_url
            `$Env:UV_EXTRA_INDEX_URL = `$tmp_UV_extra_index_url
        }
    } else {
        Print-Msg `"onnxruntime-gpu 无版本问题`"
    }
}


# 检查 Numpy 版本
function Check-Numpy-Version {
    `$content = `"
import importlib.metadata
from importlib.metadata import version

try:
    ver = int(version('numpy').split('.')[0])
except importlib.metadata.PackageNotFoundError:
    ver = -1

if ver > 1:
    print(True)
else:
    print(False)
`"
    `$status = `$(python -c `"`$content`")

    if (`$status -eq `"True`") {
        Print-Msg `"检测到 Numpy 版本大于 1, 这可能导致部分组件出现异常, 尝试重装中`"
        if (`$USE_UV) {
            uv pip install `"numpy==1.26.4`"
            if (!(`$?)) {
                Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
                python -m pip install `"numpy==1.26.4`"
            }
        } else {
            python -m pip install `"numpy==1.26.4`"
        }
        if (`$?) {
            Print-Msg `"Numpy 重新安装成功`"
        } else {
            Print-Msg `"Numpy 重新安装失败, 这可能导致部分功能异常`"
        }
    } else {
        Print-Msg `"Numpy 无版本问题`"
    }
}


# 检查 ComfyUI 运行环境
function Check-ComfyUI-Env {
    if (Test-Path `"`$PSScriptRoot/disable_check_env.txt`") {
        Print-Msg `"检测到 disable_check_env.txt 配置文件, 已禁用 ComfyUI 运行环境检测, 这可能会导致 ComfyUI 运行环境中存在的问题无法被发现并解决`"
        return
    } else {
        Print-Msg `"检查 ComfyUI 运行环境中`"
    }

    Check-ComfyUI-Requirements
    Check-ComfyUI-Env-Requirements
    Fix-PyTorch
    Check-Onnxruntime-GPU
    Check-Numpy-Version
    Print-Msg `"ComfyUI 运行环境检查完成`"
}


function Main {
    Print-Msg `"初始化中`"
    Print-Msg `"ComfyUI Installer 版本: v`$COMFYUI_INSTALLER_VERSION`"
    Set-Proxy
    Set-Github-Mirror
    Set-HuggingFace-Mirror
    Set-uv
    Pip-Mirror-Status
    `$args = Get-ComfyUI-Launch-Args
    # 记录上次的路径
    `$current_path = `$(Get-Location).ToString()

    Check-ComfyUI-Installer-Update
    Create-ComfyUI-Shortcut
    Check-ComfyUI-Env
    Set-PyTorch-CUDA-Memory-Alloc
    Print-Msg `"启动 ComfyUI 中`"
    Set-Location `"`$PSScriptRoot/ComfyUI`"
    python main.py `$args.ToString().Split()
    `$req = `$?
    if (`$req) {
        Print-Msg `"ComfyUI 正常退出`"
    } else {
        Print-Msg `"ComfyUI 出现异常, 已退出`"
    }
    Set-Location `"`$current_path`"
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/ComfyUI/launch.ps1") {
        Print-Msg "更新 launch.ps1 中"
    } else {
        Print-Msg "生成 launch.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/ComfyUI/launch.ps1" -Value $content
}


# 更新脚本
function Write-Update-Script {
    $content = "
# ComfyUI Installer 版本和检查更新间隔
`$COMFYUI_INSTALLER_VERSION = $COMFYUI_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# Pip 镜像源
`$PIP_INDEX_ADDR = `"$PIP_INDEX_ADDR`"
`$PIP_INDEX_ADDR_ORI = `"$PIP_INDEX_ADDR_ORI`"
`$PIP_EXTRA_INDEX_ADDR = `"$PIP_EXTRA_INDEX_ADDR`"
`$PIP_EXTRA_INDEX_ADDR_ORI = `"$PIP_EXTRA_INDEX_ADDR_ORI`"
`$PIP_FIND_ADDR = `"$PIP_FIND_ADDR`"
`$PIP_FIND_ADDR_ORI = `"$PIP_FIND_ADDR_ORI`"
`$USE_PIP_MIRROR = if (!(Test-Path `"`$PSScriptRoot/disable_pip_mirror.txt`")) { `$true } else { `$false }
`$PIP_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_INDEX_ADDR } else { `$PIP_INDEX_ADDR_ORI }
`$PIP_EXTRA_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_EXTRA_INDEX_ADDR } else { `$PIP_EXTRA_INDEX_ADDR_ORI }
`$PIP_FIND_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_FIND_ADDR } else { `$PIP_FIND_ADDR_ORI }
# `$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
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
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/git/bin`"
`$Env:PATH = `"`$PYTHON_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$GIT_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
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
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[ComfyUI Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# Pip 镜像源状态
function Pip-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 Pip 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pip_mirror.txt 配置文件, 已将 Pip 源切换至官方源`"
    }
}


# 修复 Git 分支游离
function Fix-Git-Point-Off-Set {
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


# 获取 PyTorch 版本
function Get-PyTorch-Version {
    `$content = `"
from importlib.metadata import version

pytorch_version = []

try:
    pytorch_version.append('torch==' + version('torch'))
except:
    pass

try:
    pytorch_version.append('torchvision==' + version('torchvision'))
except:
    pass

try:
    pytorch_version.append('torchaudio==' + version('torchaudio'))
except:
    pass

try:
    pytorch_version.append('xformers==' + version('xformers'))
except:
    pass

version_list = ''

for i in pytorch_version:
    version_list = f'{version_list} {i}'

print(version_list)
`"

    `$pytorch_ver = `$(python -c `"`$content`")
    return `$pytorch_ver
}


# 为 CUDA 设置镜像源
function Set-Pip-Extra-Index-URL-For-CUDA {
    `$content = `"
from importlib.metadata import version

def get_cuda_ver(ver):
    if 'cu124' in ver:
        return 'cu124'
    
    if 'cu121' in ver:
        return 'cu121'
    
    return 'other'


try:
    torch_ver = version('torch')
except:
    torch_ver = ''

print(get_cuda_ver(torch_ver))
`"

    `$cuda_ver = `$(python -c `"`$content`")

    if (`$cuda_ver -eq `"cu124`") {
        `$Env:PIP_EXTRA_INDEX_URL = `"`$Env:PIP_EXTRA_INDEX_URL `$PIP_EXTRA_INDEX_MIRROR_CU124`"
        `$Env:UV_EXTRA_INDEX_URL = `$PIP_EXTRA_INDEX_MIRROR_CU124
    } elseif (`$cuda_ver -eq `"cu121`") {  
        `$Env:PIP_EXTRA_INDEX_URL = `"`$Env:PIP_EXTRA_INDEX_URL `$PIP_EXTRA_INDEX_MIRROR_CU121`"
        `$Env:UV_EXTRA_INDEX_URL = `$PIP_EXTRA_INDEX_MIRROR_CU121
    } else {
        `$Env:PIP_EXTRA_INDEX_URL = `"`$Env:PIP_EXTRA_INDEX_URL `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
        `$Env:UV_EXTRA_INDEX_URL = `$PIP_EXTRA_INDEX_MIRROR_PYTORCH
    }
}


# ComfyUI Installer 更新检测
function Check-ComfyUI-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/comfyui_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/comfyui_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/comfyui_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 ComfyUI Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 ComfyUI Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/comfyui_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$PSScriptRoot/cache/comfyui_installer.ps1`" | Select-String -Pattern `"COMFYUI_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$COMFYUI_INSTALLER_VERSION) {
                    New-Item -ItemType File -Path `"`$PSScriptRoot/use_update_mode.txt`" -Force > `$null
                    Print-Msg `"检测到 ComfyUI Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"========================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 ComfyUI Installer 进行更新中`"
                        `$folder_name = Split-Path `$PSScriptRoot -Leaf
                        if (!(`$folder_name -eq `"ComfyUI`")) { # 检测脚本所在文件夹是否符合要求
                            Remove-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/update_time.txt`" 2> `$null
                            Print-Msg `"检测到 ComfyUI Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                            Print-Msg `"当前 ComfyUI Installer 管理脚本所在文件夹名称: `$folder_name`"
                            Print-Msg `"请前往 `$(Split-Path `"`$PSScriptRoot`") 路径, 将名称为 `$folder_name 的文件夹改名为 ComfyUI, 再重新更新 ComfyUI Installer 管理脚本`"
                            Print-Msg `"终止 ComfyUI Installer 的更新`"
                            Read-Host | Out-Null
                            exit 1
                        }
                        Move-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" `"`$PSScriptRoot/../comfyui_installer.ps1`" -Force
                        . `"`$PSScriptRoot/../comfyui_installer.ps1`"
                        Print-Msg `"更新结束, 需重新启动 ComfyUI Installer 管理脚本以应用更新, 回车退出 ComfyUI Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Remove-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" 2> `$null
                        Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                        Print-Msg `"跳过 ComfyUI Installer 更新`"
                    }
                } else {
                    Remove-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                    Print-Msg `"ComfyUI Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 ComfyUI Installer 更新中`"
                } else {
                    Print-Msg `"检查 ComfyUI Installer 更新失败`"
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
    try:
        nums1 = re.sub(r'[a-zA-Z]+', '', version1).replace('-', '.').replace('+', '.').split('.')
        nums2 = re.sub(r'[a-zA-Z]+', '', version2).replace('-', '.').replace('+', '.').split('.')
    except:
        return 0

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
        # 切换 uv 指定的 Python
        if (Test-Path `"`$PSScriptRoot/ComfyUI/python/python.exe`") {
            `$Env:UV_PYTHON = `"`$PSScriptRoot/ComfyUI/python/python.exe`"
        }
        `$Global:USE_UV = `$true
        Check-uv-Version
    }
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


# Github 镜像源
function Set-Github-Mirror {
    if (Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") { # 禁用 Github 镜像源
        Print-Msg `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件, 禁用 Github 镜像源`"
    } else {
        `$Env:GIT_CONFIG_GLOBAL = `"`$PSScriptRoot/.gitconfig`" # 设置 Git 配置文件路径
        if (Test-Path `"`$PSScriptRoot/.gitconfig`") {
            Remove-Item -Path `"`$PSScriptRoot/.gitconfig`" -Force
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
                if (Test-Path `"`$PSScriptRoot/cache/github-mirror-test`") {
                    Remove-Item -Path `"`$PSScriptRoot/cache/github-mirror-test`" -Force -Recurse
                }
                git clone `$i/licyk/empty `"`$PSScriptRoot/cache/github-mirror-test`" --quiet
                if (`$?) {
                    Print-Msg `"该 Github 镜像源可用`"
                    `$github_mirror = `$i
                    `$status = 1
                    break
                } else {
                    Print-Msg `"镜像源不可用, 更换镜像源进行测试`"
                }
            }
            if (Test-Path `"`$PSScriptRoot/cache/github-mirror-test`") {
                Remove-Item -Path `"`$PSScriptRoot/cache/github-mirror-test`" -Force -Recurse
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


function Main {
    Print-Msg `"初始化中`"
    Print-Msg `"ComfyUI Installer 版本: v`$COMFYUI_INSTALLER_VERSION`"
    Set-uv
    Set-Proxy
    Set-Github-Mirror
    Pip-Mirror-Status
    Check-ComfyUI-Installer-Update

    Print-Msg `"拉取 ComfyUI 更新内容中`"
    Fix-Git-Point-Off-Set `"`$PSScriptRoot/ComfyUI`"
    `$core_origin_ver = `$(git -C `"`$PSScriptRoot/ComfyUI`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")
    `$branch = `$(git -C `"`$PSScriptRoot/ComfyUI`" symbolic-ref --quiet HEAD 2> `$null).split(`"/`")[2]
    git -C `"`$PSScriptRoot/ComfyUI`" fetch --recurse-submodules
    if (`$?) {
        Print-Msg `"应用 ComfyUI 更新中`"
        `$commit_hash = `$(git -C `"`$PSScriptRoot/ComfyUI`" log origin/`$branch --max-count 1 --format=`"%h`")
        git -C `"`$PSScriptRoot/ComfyUI`" reset --hard `$commit_hash --recurse-submodules
        `$core_latest_ver = `$(git -C `"`$PSScriptRoot/ComfyUI`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")

        if (`$core_origin_ver -eq `$core_latest_ver) {
            Print-Msg `"ComfyUI 已为最新版, 当前版本：`$core_origin_ver`"
        } else {
            Print-Msg `"ComfyUI 更新成功, 版本：`$core_origin_ver -> `$core_latest_ve`"
        }
    } else {
        Print-Msg `"拉取 ComfyUI 更新内容失败`"
    }

    Print-Msg `"退出 ComfyUI 更新脚本`"
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/ComfyUI/update.ps1") {
        Print-Msg "更新 update.ps1 中"
    } else {
        Print-Msg "生成 update.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/ComfyUI/update.ps1" -Value $content
}


# 获取安装脚本
function Write-ComfyUI-Install-Script {
    $content = "
`$COMFYUI_INSTALLER_VERSION = $COMFYUI_INSTALLER_VERSION
# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[ComfyUI Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
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


function Main {
    Print-Msg `"初始化中`"
    Print-Msg `"ComfyUI Installer 版本: v`$COMFYUI_INSTALLER_VERSION`"
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/comfyui_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/comfyui_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/comfyui_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    ForEach (`$url in `$urls) {
        Print-Msg `"正在下载最新的 ComfyUI Installer 脚本`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/comfyui_installer.ps1`"
        if (`$?) {
            Move-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" -Destination `"`$PSScriptRoot/../comfyui_installer.ps1`" -Force
            `$parentDirectory = Split-Path `$PSScriptRoot -Parent
            Print-Msg `"下载 ComfyUI Installer 脚本成功, 脚本路径为 `$parentDirectory\comfyui_installer.ps1`"
            break
        } else {
            Print-Msg `"下载 ComfyUI Installer 脚本失败`"
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试下载 ComfyUI Installer 脚本`"
            } else {
                Print-Msg `"更新 ComfyUI Installer 脚本失败, 可尝试重新运行 ComfyUI Installer 下载脚本`"
            }
        }
    }

    Print-Msg `"退出 ComfyUI Installer 下载脚本`"
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/ComfyUI/get_comfyui_installer.ps1") {
        Print-Msg "更新 get_comfyui_installer.ps1 中"
    } else {
        Print-Msg "生成 get_comfyui_installer.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/ComfyUI/get_comfyui_installer.ps1" -Value $content
}


# 重装 PyTorch 脚本
function Write-PyTorch-ReInstall-Script {
    $content = "
# ComfyUI Installer 版本和检查更新间隔
`$COMFYUI_INSTALLER_VERSION = $COMFYUI_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# Pip 镜像源
`$PIP_INDEX_ADDR = `"$PIP_INDEX_ADDR`"
`$PIP_INDEX_ADDR_ORI = `"$PIP_INDEX_ADDR_ORI`"
`$PIP_EXTRA_INDEX_ADDR = `"$PIP_EXTRA_INDEX_ADDR`"
`$PIP_EXTRA_INDEX_ADDR_ORI = `"$PIP_EXTRA_INDEX_ADDR_ORI`"
`$PIP_FIND_ADDR = `"$PIP_FIND_ADDR`"
`$PIP_FIND_ADDR_ORI = `"$PIP_FIND_ADDR_ORI`"
`$USE_PIP_MIRROR = if (!(Test-Path `"`$PSScriptRoot/disable_pip_mirror.txt`")) { `$true } else { `$false }
`$PIP_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_INDEX_ADDR } else { `$PIP_INDEX_ADDR_ORI }
`$PIP_EXTRA_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_EXTRA_INDEX_ADDR } else { `$PIP_EXTRA_INDEX_ADDR_ORI }
`$PIP_FIND_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_FIND_ADDR } else { `$PIP_FIND_ADDR_ORI }
# `$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/git/bin`"
`$Env:PATH = `"`$PYTHON_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$GIT_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
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
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[ComfyUI Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# Pip 镜像源状态
function Pip-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 Pip 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pip_mirror.txt 配置文件, 已将 Pip 源切换至官方源`"
    }
}


# ComfyUI Installer 更新检测
function Check-ComfyUI-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/comfyui_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/comfyui_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/comfyui_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 ComfyUI Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 ComfyUI Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/comfyui_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$PSScriptRoot/cache/comfyui_installer.ps1`" | Select-String -Pattern `"COMFYUI_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$COMFYUI_INSTALLER_VERSION) {
                    New-Item -ItemType File -Path `"`$PSScriptRoot/use_update_mode.txt`" -Force > `$null
                    Print-Msg `"检测到 ComfyUI Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"========================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 ComfyUI Installer 进行更新中`"
                        `$folder_name = Split-Path `$PSScriptRoot -Leaf
                        if (!(`$folder_name -eq `"ComfyUI`")) { # 检测脚本所在文件夹是否符合要求
                            Remove-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/update_time.txt`" 2> `$null
                            Print-Msg `"检测到 ComfyUI Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                            Print-Msg `"当前 ComfyUI Installer 管理脚本所在文件夹名称: `$folder_name`"
                            Print-Msg `"请前往 `$(Split-Path `"`$PSScriptRoot`") 路径, 将名称为 `$folder_name 的文件夹改名为 ComfyUI, 再重新更新 ComfyUI Installer 管理脚本`"
                            Print-Msg `"终止 ComfyUI Installer 的更新`"
                            Read-Host | Out-Null
                            exit 1
                        }
                        Move-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" `"`$PSScriptRoot/../comfyui_installer.ps1`" -Force
                        . `"`$PSScriptRoot/../comfyui_installer.ps1`"
                        Print-Msg `"更新结束, 需重新启动 ComfyUI Installer 管理脚本以应用更新, 回车退出 ComfyUI Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Remove-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" 2> `$null
                        Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                        Print-Msg `"跳过 ComfyUI Installer 更新`"
                    }
                } else {
                    Remove-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                    Print-Msg `"ComfyUI Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 ComfyUI Installer 更新中`"
                } else {
                    Print-Msg `"检查 ComfyUI Installer 更新失败`"
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
    try:
        nums1 = re.sub(r'[a-zA-Z]+', '', version1).replace('-', '.').replace('+', '.').split('.')
        nums2 = re.sub(r'[a-zA-Z]+', '', version2).replace('-', '.').replace('+', '.').split('.')
    except:
        return 0

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
        # 切换 uv 指定的 Python
        if (Test-Path `"`$PSScriptRoot/ComfyUI/python/python.exe`") {
            `$Env:UV_PYTHON = `"`$PSScriptRoot/ComfyUI/python/python.exe`"
        }
        `$Global:USE_UV = `$true
        Check-uv-Version
    }
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


function Main {
    Print-Msg `"初始化中`"
    Print-Msg `"ComfyUI Installer 版本: v`$COMFYUI_INSTALLER_VERSION`"
    Set-uv
    Set-Proxy
    Pip-Mirror-Status
    Check-ComfyUI-Installer-Update

    # PyTorch 版本列表
    `$content = `"
-----------------------------------------------------
- 1、Torch 1.12.1 (CUDA 11.3) + xFormers 0.0.14
- 2、Torch 1.13.1 (CUDA 11.7) + xFormers 0.0.16
- 3、Torch 2.0.0 (CUDA 11.8) + xFormers 0.0.18
- 4、Torch 2.0.1 (CUDA 11.8) + xFormers 0.0.22
- 5、Torch 2.1.1 (CUDA 11.8) + xFormers 0.0.23
- 6、Torch 2.1.1 (CUDA 12.1) + xFormers 0.0.23
- 7、Torch 2.1.2 (CUDA 11.8) + xFormers 0.0.23.post1
- 8、Torch 2.1.2 (CUDA 12.1) + xFormers 0.0.23.post1
- 9、Torch 2.2.0 (CUDA 11.8) + xFormers 0.0.24
- 10、Torch 2.2.0 (CUDA 12.1) + xFormers 0.0.24
- 11、Torch 2.2.1 (CUDA 11.8) + xFormers 0.0.25
- 12、Torch 2.2.1 (CUDA 12.1) + xFormers 0.0.25
- 13、Torch 2.2.2 (CUDA 11.8) + xFormers 0.0.25.post1
- 14、Torch 2.2.2 (CUDA 12.1) + xFormers 0.0.25.post1
- 15、Torch 2.3.0 (CUDA 11.8) + xFormers 0.0.26.post1
- 16、Torch 2.3.0 (CUDA 12.1) + xFormers 0.0.26.post1
- 17、Torch 2.3.1 (CUDA 11.8) + xFormers 0.0.27
- 18、Torch 2.3.1 (CUDA 12.1) + xFormers 0.0.27
- 19、Torch 2.4.0 (CUDA 11.8) + xFormers 0.0.27.post2
- 20、Torch 2.4.0 (CUDA 12.1) + xFormers 0.0.27.post2
- 21、Torch 2.4.1 (CUDA 12.4) + xFormers 0.0.28.post1
- 22、Torch 2.5.0 (CUDA 12.4) + xFormers 0.0.28.post2
- 23、Torch 2.5.1 (CUDA 12.4) + xFormers 0.0.28.post3
-----------------------------------------------------
    `"

    `$to_exit = 0

    while (`$True) {
        Print-Msg `"PyTorch 版本列表`"
        `$go_to = 0
        Write-Host `$content
        Print-Msg `"请选择 PyTorch 版本`"
        Print-Msg `"提示:`"
        Print-Msg `"1. PyTroch 版本通常来说选择最新版的即可`"
        Print-Msg `"2. 输入数字后回车, 或者输入 exit 退出 PyTroch 重装脚本`"
        `$arg = Read-Host `"========================================>`"

        switch (`$arg) {
            1 {
                `$torch_ver = `"torch==1.12.1+cu113 torchvision==0.13.1+cu113 torchaudio==1.12.1+cu113`"
                `$xformers_ver = `"xformers==0.0.14`"
                `$go_to = 1
            }
            2 {
                `$torch_ver = `"torch==1.13.1+cu117 torchvision==0.14.1+cu117 torchaudio==1.13.1+cu117`"
                `$xformers_ver = `"xformers==0.0.18`"
                `$go_to = 1
            }
            3 {
                `$torch_ver = `"torch==2.0.0+cu118 torchvision==0.15.1+cu118 torchaudio==2.0.0+cu118`"
                `$xformers_ver = `"xformers==0.0.14`"
                `$go_to = 1
            }
            4 {
                `$torch_ver = `"torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.1+cu118`"
                `$xformers_ver = `"xformers==0.0.22`"
                `$go_to = 1
            }
            5 {
                `$torch_ver = `"torch==2.1.1+cu118 torchvision==0.16.1+cu118 torchaudio==2.1.1+cu118`"
                `$xformers_ver = `"xformers==0.0.23+cu118`"
                `$go_to = 1
            }
            6 {
                `$torch_ver = `"torch==2.1.1+cu121 torchvision==0.16.1+cu121 torchaudio==2.1.1+cu121`"
                `$xformers_ver = `"xformers===0.0.23`"
                `$go_to = 1
            }
            7 {
                `$torch_ver = `"torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2+cu118`"
                `$xformers_ver = `"xformers==0.0.23.post1+cu118`"
                `$go_to = 1
            }
            8 {
                `$torch_ver = `"torch==2.1.2+cu121 torchvision==0.16.2+cu121 torchaudio==2.1.2+cu121`"
                `$xformers_ver = `"xformers===0.0.23.post1`"
                `$go_to = 1
            }
            9 {
                `$torch_ver = `"torch==2.2.0+cu118 torchvision==0.17.0+cu118 torchaudio==2.2.0+cu118`"
                `$xformers_ver = `"xformers==0.0.24+cu118`"
                `$go_to = 1
            }
            10 {
                `$torch_ver = `"torch==2.2.0+cu121 torchvision==0.17.0+cu121 torchaudio==2.2.0+cu121`"
                `$xformers_ver = `"xformers===0.0.24`"
                `$go_to = 1
            }
            11 {
                `$torch_ver = `"torch==2.2.1+cu118 torchvision==0.17.1+cu118 torchaudio==2.2.1+cu118`"
                `$xformers_ver = `"xformers==0.0.25+cu118`"
                `$go_to = 1
            }
            12 {
                `$torch_ver = `"torch==2.2.1+cu121 torchvision==0.17.1+cu121 torchaudio==2.2.1+cu121`"
                `$xformers_ver = `"xformers===0.0.25`"
                `$go_to = 1
            }
            13 {
                `$torch_ver = `"torch==2.2.2+cu118 torchvision==0.17.2+cu118 torchaudio==2.2.2+cu118`"
                `$xformers_ver = `"xformers==0.0.25.post1+cu118`"
                `$go_to = 1
            }
            14 {
                `$torch_ver = `"torch==2.2.2+cu121 torchvision==0.17.2+cu121 torchaudio==2.2.2+cu121`"
                `$xformers_ver = `"xformers===0.0.25.post1`"
                `$go_to = 1
            }
            15 {
                `$torch_ver = `"torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118`"
                `$xformers_ver = `"xformers==0.0.26.post1+cu118`"
                `$go_to = 1
            }
            16 {
                `$torch_ver = `"torch==2.3.0+cu121 torchvision==0.18.0+cu121 torchaudio==2.3.0+cu121`"
                `$xformers_ver = `"xformers===0.0.26.post1`"
                `$go_to = 1
            }
            17 {
                `$torch_ver = `"torch==2.3.1+cu118 torchvision==0.18.1+cu118 torchaudio==2.3.1+cu118`"
                `$xformers_ver = `"xformers==0.0.27+cu118`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
                `$go_to = 1
            }
            18 {
                `$torch_ver = `"torch==2.3.1+cu121 torchvision==0.18.1+cu121 torchaudio==2.3.1+cu121`"
                `$xformers_ver = `"xformers==0.0.27`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
                `$Env:PIP_FIND_LINKS = `" `"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            19 {
                `$torch_ver = `"torch==2.4.0+cu118 torchvision==0.19.0+cu118 torchaudio==2.4.0+cu118`"
                `$xformers_ver = `"xformers==0.0.27.post2+cu118`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
                `$go_to = 1
            }
            20 {
                `$torch_ver = `"torch==2.4.0+cu121 torchvision==0.19.0+cu121 torchaudio==2.4.0+cu121`"
                `$xformers_ver = `"xformers==0.0.27.post2`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
                `$Env:PIP_FIND_LINKS = `" `"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            21 {
                `$torch_ver = `"torch==2.4.1+cu124 torchvision==0.19.1+cu124 torchaudio==2.4.1+cu124`"
                `$xformers_ver = `"xformers===0.0.28.post1`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU124`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU124`"
                `$Env:PIP_FIND_LINKS = `" `"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            22 {
                `$torch_ver = `"torch==2.5.0+cu124 torchvision==0.20.0+cu124 torchaudio==2.5.0+cu124`"
                `$xformers_ver = `"xformers==0.0.28.post2`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU124`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU124`"
                `$Env:PIP_FIND_LINKS = `" `"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            23 {
                `$torch_ver = `"torch==2.5.1+cu124 torchvision==0.20.1+cu124 torchaudio==2.5.1+cu124`"
                `$xformers_ver = `"xformers==0.0.28.post3`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU124`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU124`"
                `$Env:PIP_FIND_LINKS = `" `"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            exit {
                Print-Msg `"退出 PyTorch 重装脚本`"
                `$to_exit = 1
                `$go_to = 1
            }
            Default {
                Print-Msg `"输入有误, 请重试`"
            }
        }

        if (`$go_to -eq 1) {
            break
        }
    }

    if (`$to_exit -eq 1) {
        Read-Host | Out-Null
        exit 0
    }

    Print-Msg `"是否选择仅强制重装 ? (通常情况下不需要)`"
    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
    `$use_force_reinstall = Read-Host `"========================================>`"

    if (`$use_force_reinstall -eq `"yes`" -or `$use_force_reinstall -eq `"y`" -or `$use_force_reinstall -eq `"YES`" -or `$use_force_reinstall -eq `"Y`") {
        `$force_reinstall_arg = `"--force-reinstall`"
        `$force_reinstall_status = `"启用`"
    } else {
        `$force_reinstall_arg = `"`"
        `$force_reinstall_status = `"禁用`"
    }

    Print-Msg `"当前的选择`"
    Print-Msg `"PyTorch: `$torch_ver`"
    Print-Msg `"xFormers: `$xformers_ver`"
    Print-Msg `"仅强制重装: `$force_reinstall_status`"
    Print-Msg `"是否确认安装?`"
    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
    `$install_torch = Read-Host `"========================================>`"

    if (`$install_torch -eq `"yes`" -or `$install_torch -eq `"y`" -or `$install_torch -eq `"YES`" -or `$install_torch -eq `"Y`") {
        Print-Msg `"重装 PyTorch 中`"
        if (`$USE_UV) {
            uv pip install `$torch_ver.ToString().Split() `$force_reinstall_arg
            if (!(`$?)) {
                Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
                python -m pip install `$torch_ver.ToString().Split() `$force_reinstall_arg
            }
        } else {
            python -m pip install `$torch_ver.ToString().Split() `$force_reinstall_arg
        }
        if (`$?) {
            Print-Msg `"安装 PyTorch 成功`"
        } else {
            Print-Msg `"安装 PyTorch 失败, 终止 PyTorch 重装进程`"
            Read-Host | Out-Null
            exit 1
        }

        if (!(`$xformers_ver -eq `"`")) {
            Print-Msg `"重装 xFormers 中`"
            if (`$USE_UV) {
                python -m pip show xformers --quiet 2> `$null
                if (`$?) {
                    Print-Msg `"卸载原有 xFormers 中`"
                    python -m pip uninstall xformers -y
                }
                uv pip install `$xformers_ver `$force_reinstall_arg --no-deps
                if (!(`$?)) {
                    Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
                    python -m pip install `$xformers_ver `$force_reinstall_arg --no-deps
                }
            } else {
                python -m pip install `$xformers_ver `$force_reinstall_arg --no-deps
            }
            if (`$?) {
                Print-Msg `"安装 xFormers 成功`"
            } else {
                Print-Msg `"安装 xFormers 失败, 终止 PyTorch 重装进程`"
                Read-Host | Out-Null
                exit 1
            }
        }
    } else {
        Print-Msg `"取消重装 PyTorch`"
    }

    Print-Msg `"退出 PyTorch 重装脚本`"
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/ComfyUI/reinstall_pytorch.ps1") {
        Print-Msg "更新 reinstall_pytorch.ps1 中"
    } else {
        Print-Msg "生成 reinstall_pytorch.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/ComfyUI/reinstall_pytorch.ps1" -Value $content
}


# 模型下载脚本
function Write-Download-Model-Script {
    $content = "
# ComfyUI Installer 版本和检查更新间隔
`$COMFYUI_INSTALLER_VERSION = $COMFYUI_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# Pip 镜像源
`$PIP_INDEX_ADDR = `"$PIP_INDEX_ADDR`"
`$PIP_INDEX_ADDR_ORI = `"$PIP_INDEX_ADDR_ORI`"
`$PIP_EXTRA_INDEX_ADDR = `"$PIP_EXTRA_INDEX_ADDR`"
`$PIP_EXTRA_INDEX_ADDR_ORI = `"$PIP_EXTRA_INDEX_ADDR_ORI`"
`$PIP_FIND_ADDR = `"$PIP_FIND_ADDR`"
`$PIP_FIND_ADDR_ORI = `"$PIP_FIND_ADDR_ORI`"
`$USE_PIP_MIRROR = if (!(Test-Path `"`$PSScriptRoot/disable_pip_mirror.txt`")) { `$true } else { `$false }
`$PIP_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_INDEX_ADDR } else { `$PIP_INDEX_ADDR_ORI }
`$PIP_EXTRA_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_EXTRA_INDEX_ADDR } else { `$PIP_EXTRA_INDEX_ADDR_ORI }
`$PIP_FIND_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_FIND_ADDR } else { `$PIP_FIND_ADDR_ORI }
# `$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/git/bin`"
`$Env:PATH = `"`$PYTHON_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$GIT_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
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
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[ComfyUI Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# Pip 镜像源状态
function Pip-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 Pip 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pip_mirror.txt 配置文件, 已将 Pip 源切换至官方源`"
    }
}


# ComfyUI Installer 更新检测
function Check-ComfyUI-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/comfyui_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/comfyui_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/comfyui_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 ComfyUI Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 ComfyUI Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/comfyui_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$PSScriptRoot/cache/comfyui_installer.ps1`" | Select-String -Pattern `"COMFYUI_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$COMFYUI_INSTALLER_VERSION) {
                    New-Item -ItemType File -Path `"`$PSScriptRoot/use_update_mode.txt`" -Force > `$null
                    Print-Msg `"检测到 ComfyUI Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"========================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 ComfyUI Installer 进行更新中`"
                        `$folder_name = Split-Path `$PSScriptRoot -Leaf
                        if (!(`$folder_name -eq `"ComfyUI`")) { # 检测脚本所在文件夹是否符合要求
                            Remove-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/update_time.txt`" 2> `$null
                            Print-Msg `"检测到 ComfyUI Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                            Print-Msg `"当前 ComfyUI Installer 管理脚本所在文件夹名称: `$folder_name`"
                            Print-Msg `"请前往 `$(Split-Path `"`$PSScriptRoot`") 路径, 将名称为 `$folder_name 的文件夹改名为 ComfyUI, 再重新更新 ComfyUI Installer 管理脚本`"
                            Print-Msg `"终止 ComfyUI Installer 的更新`"
                            Read-Host | Out-Null
                            exit 1
                        }
                        Move-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" `"`$PSScriptRoot/../comfyui_installer.ps1`" -Force
                        . `"`$PSScriptRoot/../comfyui_installer.ps1`"
                        Print-Msg `"更新结束, 需重新启动 ComfyUI Installer 管理脚本以应用更新, 回车退出 ComfyUI Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Remove-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" 2> `$null
                        Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                        Print-Msg `"跳过 ComfyUI Installer 更新`"
                    }
                } else {
                    Remove-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                    Print-Msg `"ComfyUI Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 ComfyUI Installer 更新中`"
                } else {
                    Print-Msg `"检查 ComfyUI Installer 更新失败`"
                }
            }
        }
    }
}


function Main {
    Print-Msg `"初始化中`"
    Print-Msg `"ComfyUI Installer 版本: v`$COMFYUI_INSTALLER_VERSION`"
    Pip-Mirror-Status
    Check-ComfyUI-Installer-Update

    `$to_exit = 0
    while (`$True) {
        `$go_to = 0
        Print-Msg `"可下载的模型列表`"
        `$content = `"
-----------------------------------------------------
模型序号 | 模型名称 | 模型种类

- 1、v1-5-pruned-emaonly (SD 1.5)
- 2、animefull-final-pruned (SD 1.5)
- 3、v2-1_768-ema-pruned (SD 2.1)
- 4、wd-1-4-anime_e2 (SD 2.1)
- 5、wd-mofu-fp16 (SD 2.1)
- 6、sd_xl_base_1.0_0.9vae (SDXL)
- 7、animagine-xl-3.0 (SDXL)
- 8、animagine-xl-3.1 (SDXL)
- 9、kohaku-xl-delta-rev1 (SDXL)
- 10、kohakuXLEpsilon_rev1 (SDXL)
- 11、kohaku-xl-epsilon-rev2 (SDXL)
- 12、kohaku-xl-epsilon-rev3 (SDXL)
- 13、kohaku-xl-zeta (SDXL)
- 14、ponyDiffusionV6XL_v6 (SDXL)
- 15、pdForAnime_v20 (SDXL)
- 16、starryXLV52_v52 (SDXL)
- 17、heartOfAppleXL_v20 (SDXL)
- 18、heartOfAppleXL_v30 (SDXL)
- 19、Illustrious-XL-v0.1 (SDXL)
- 20、Illustrious-XL-v0.1-GUIDED (SDXL)
- 21、noobaiXLNAIXL_earlyAccessVersion (SDXL)
- 22、noobaiXLNAIXL_epsilonPred05Version (SDXL)
- 23、noobaiXLNAIXL_vPredTestVersion (SDXL)
- 24、noobaiXLNAIXL_epsilonPred075 (SDXL)
- 25、noobaiXLNAIXL_epsilonPred077 (SDXL)
- 26、noobaiXLNAIXL_epsilonPred10Version (SDXL)
- 27、flux1-schnell (FLUX.1)
- 28、flux1-dev (FLUX.1)
- 29、ashen0209-flux1-dev2pro (FLUX.1)
- 30、nyanko7-flux-dev-de-distill (FLUX.1)
- 31、vae-ft-ema-560000-ema-pruned (SD 1.5 VAE)
- 32、vae-ft-mse-840000-ema-pruned (SD 1.5 VAE)
- 33、sdxl_fp16_fix_vae (SDXL VAE)
- 34、sdxl_vae (SDXL VAE)
- 35、ae (FLUX.1 VAE)
- 36、clip_l (FLUX.1 CLIP)
- 37、t5xxl_fp16 (FLUX.1 CLIP)

关于模型的介绍可阅读：https://github.com/licyk/README-collection/blob/main/model-info/README.md
-----------------------------------------------------
    `"

        Write-Host `$content
        Print-Msg `"请选择要下载的模型`"
        Print-Msg `"提示: 输入数字后回车, 或者输入 exit 退出模型下载脚本`"
        `$arg = Read-Host `"========================================>`"

        switch (`$arg) {
            1 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/v1-5-pruned-emaonly.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            2 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/animefull-final-pruned.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            3 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_2.1/v2-1_768-ema-pruned.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            4 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_2.1/wd-1-4-anime_e2.ckpt`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            5 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_2.1/wd-mofu-fp16.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            6 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/sd_xl_base_1.0_0.9vae.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            7 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/animagine-xl-3.0.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            8 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/animagine-xl-3.1.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            9 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohaku-xl-delta-rev1.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            10 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohakuXLEpsilon_rev1.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            11 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohaku-xl-epsilon-rev2.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            12 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohaku-xl-epsilon-rev3.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            13 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohaku-xl-zeta.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            14 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/ponyDiffusionV6XL_v6StartWithThisOne.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            15 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/pdForAnime_v20.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            16 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/starryXLV52_v52.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            17 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/heartOfAppleXL_v20.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            18 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/heartOfAppleXL_v30.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            19 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/Illustrious-XL-v0.1.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            20 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/Illustrious-XL-v0.1-GUIDED.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            21 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_earlyAccessVersion.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            22 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_epsilonPred05Version.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            23 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_vPredTestVersion.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            24 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_epsilonPred075.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            25 {
                `$url = `"https://modelsope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_epsilonPred077.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            26 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_epsilonPred10Version.safetensors`"
                `$type = `"checkpoints`"
                `$go_to = 1
            }
            27 {
                `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell.safetensors`"
                `$type = `"unet`"
                `$go_to = 1
            }
            28 {
                `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev.safetensors`"
                `$type = `"unet`"
                `$go_to = 1
            }
            29 {
                `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/ashen0209-flux1-dev2pro.safetensors`"
                `$type = `"unet`"
                `$go_to = 1
            }
            30 {
                `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/nyanko7-flux-dev-de-distill.safetensors`"
                `$type = `"unet`"
                `$go_to = 1
            }
            31 {
                `$url = `"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sd_1.5/vae-ft-ema-560000-ema-pruned.safetensors`"
                `$type = `"vae`"
                `$go_to = 1
            }
            32 {
                `$url = `"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sd_1.5/vae-ft-mse-840000-ema-pruned.safetensors`"
                `$type = `"vae`"
                `$go_to = 1
            }
            33 {
                `$url = `"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sdxl_1.0/sdxl_fp16_fix_vae.safetensors`"
                `$type = `"vae`"
                `$go_to = 1
            }
            34 {
                `$url = `"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sdxl_1.0/sdxl_vae.safetensors`"
                `$type = `"vae`"
                `$go_to = 1
            }
            35 {
                `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_vae/ae.safetensors`"
                `$type = `"vae`"
                `$go_to = 1
            }
            36 {
                `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/clip_l.safetensors`"
                `$type = `"clip`"
                `$go_to = 1
            }
            37 {
                `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5xxl_fp16.safetensors`"
                `$type = `"clip`"
                `$go_to = 1
            }
            exit {
                Print-Msg `"退出模型下载脚本`"
                `$to_exit = 1
                `$go_to = 1
            }
            Default {
                Print-Msg `"输入有误, 请重试`"
            }
        }

        if (`$go_to -eq 1) {
            break
        }
    }

    if (`$to_exit -eq 1) {
        Print-Msg `"退出模型下载脚本`"
        Read-Host | Out-Null
        exit 0
    }

    `$model_name = Split-Path `$url -Leaf
    Print-Msg `"当前选择要下载的模型: `$model_name`"
    Print-Msg `"是否确认下载模型?`"
    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
    `$download_model = Read-Host `"========================================>`"

    if (`$download_model -eq `"yes`" -or `$download_model -eq `"y`" -or `$download_model -eq `"YES`" -or `$download_model -eq `"Y`") {
        Print-Msg `"模型将下载至 `$PSScriptRoot\ComfyUI\models\`$type 目录中`"
        Print-Msg `"下载 `$model_name 模型中`"
        aria2c --file-allocation=none --summary-interval=0 --console-log-level=error -s 64 -c -x 16 `$url -d `"`$PSScriptRoot/ComfyUI/models/`$type`" -o `$model_name
        if (`$?) {
            Print-Msg `"`$model_name 模型下载成功`"
        } else {
            Print-Msg `"`$model_name 模型下载失败`"
        }
    }

    Print-Msg `"退出模型下载脚本`"
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/ComfyUI/download_models.ps1") {
        Print-Msg "更新 download_models.ps1 中"
    } else {
        Print-Msg "生成 download_models.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/ComfyUI/download_models.ps1" -Value $content
}


# ComfyUI Installer 设置脚本
function Write-ComfyUI-Installer-Settings-Script {
    $content = "
# ComfyUI Installer 版本和检查更新间隔
`$COMFYUI_INSTALLER_VERSION = $COMFYUI_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# Pip 镜像源
`$PIP_INDEX_ADDR = `"$PIP_INDEX_ADDR`"
`$PIP_INDEX_ADDR_ORI = `"$PIP_INDEX_ADDR_ORI`"
`$PIP_EXTRA_INDEX_ADDR = `"$PIP_EXTRA_INDEX_ADDR`"
`$PIP_EXTRA_INDEX_ADDR_ORI = `"$PIP_EXTRA_INDEX_ADDR_ORI`"
`$PIP_FIND_ADDR = `"$PIP_FIND_ADDR`"
`$PIP_FIND_ADDR_ORI = `"$PIP_FIND_ADDR_ORI`"
`$USE_PIP_MIRROR = if (!(Test-Path `"`$PSScriptRoot/disable_pip_mirror.txt`")) { `$true } else { `$false }
`$PIP_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_INDEX_ADDR } else { `$PIP_INDEX_ADDR_ORI }
`$PIP_EXTRA_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_EXTRA_INDEX_ADDR } else { `$PIP_EXTRA_INDEX_ADDR_ORI }
`$PIP_FIND_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_FIND_ADDR } else { `$PIP_FIND_ADDR_ORI }
# `$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/git/bin`"
`$Env:PATH = `"`$PYTHON_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$GIT_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
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
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[ComfyUI Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# Pip 镜像源状态
function Pip-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 Pip 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pip_mirror.txt 配置文件, 已将 Pip 源切换至官方源`"
    }
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


# 获取 ComfyUI Installer 自动检测更新设置
function Get-ComfyUI-Installer-Auto-Check-Update-Setting {
    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        return `"禁用`"
    } else {
        return `"启用`"
    }
}


# 获取启动参数设置
function Get-Launch-Args-Setting {
    if (Test-Path `"`$PSScriptRoot/launch_args.txt`") {
        return Get-Content `"`$PSScriptRoot/launch_args.txt`"
    } else {
        return `"无`"
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


# 获取 Pip 镜像源配置
function Get-Pip-Mirror-Setting {
    if (!(Test-Path `"`$PSScriptRoot/disable_pip_mirror.txt`")) {
        return `"启用`"
    } else {
        return `"禁用`"
    }
}


# 获取 ComfyUI 运行环境检测配置
function Get-ComfyUI-Env-Check-Setting {
    if (!(Test-Path `"`$PSScriptRoot/disable_check_env.txt`")) {
        return `"启用`"
    } else {
        return `"禁用`"
    }
}


# 获取 CUDA 内存分配器设置
function Get-PyTorch-CUDA-Memory-Alloc-Setting {
    if (!(Test-Path `"`$PSScriptRoot/disable_set_pytorch_cuda_memory_alloc.txt`")) {
        return `"启用`"
    } else {
        return `"禁用`"
    }
}


# 获取用户输入
function Get-User-Input {
    return Read-Host `"========================================>`"
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
                Print-Msg `"启用 Github 镜像成功, 在更新 ComfyUI 时将自动检测可用的 Github 镜像源并使用`"
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


# ComfyUI Installer 自动检查更新设置
function Update-ComfyUI-Installer-Auto-Check-Update-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 ComfyUI Installer 自动检测更新设置: `$(Get-ComfyUI-Installer-Auto-Check-Update-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 ComfyUI Installer 自动更新检查`"
        Print-Msg `"2. 禁用 ComfyUI Installer 自动更新检查`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_update.txt`" 2> `$null
                Print-Msg `"启用 ComfyUI Installer 自动更新检查成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_update.txt`" -Force > `$null
                Print-Msg `"禁用 ComfyUI Installer 自动更新检查成功`"
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


# ComfyUI 启动参数设置
function Update-ComfyUI-Launch-Args-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 ComfyUI 启动参数: `$(Get-Launch-Args-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 设置 ComfyUI 启动参数`"
        Print-Msg `"2. 删除 ComfyUI 启动参数`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Print-Msg `"请输入 ComfyUI 启动参数`"
                Print-Msg `"提示: ComfyUI 可用的启动参数可阅读: https://github.com/Akegarasu/ComfyUI?tab=readme-ov-file#program-arguments`"
                Print-Msg `"输入启动参数后回车保存`"
                `$comfyui_launch_args = Get-User-Input
                Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/launch_args.txt`" -Value `$comfyui_launch_args
                Print-Msg `"设置 ComfyUI 启动参数成功, 使用的 ComfyUI 启动参数为: `$comfyui_launch_args`"
                break
            }
            2 {
                Remove-Item -Path `"`$PSScriptRoot/launch_args.txt`" 2> `$null
                Print-Msg `"删除 ComfyUI 启动参数成功`"
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


# 自动创建 ComfyUI 快捷启动方式设置
function Auto-Set-Launch-Shortcut-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前自动创建 ComfyUI 快捷启动方式设置: `$(Get-Auto-Set-Launch-Shortcut-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用自动创建 ComfyUI 快捷启动方式`"
        Print-Msg `"2. 禁用自动创建 ComfyUI 快捷启动方式`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/enable_shortcut.txt`" -Force > `$null
                Print-Msg `"启用自动创建 ComfyUI 快捷启动方式成功`"
                break
            }
            2 {
                Remove-Item -Path `"`$PSScriptRoot/enable_shortcut.txt`" 2> `$null
                Print-Msg `"禁用自动创建 ComfyUI 快捷启动方式成功`"
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


# Pip 镜像源设置
function Pip-Mirror-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 Pip 镜像源设置: `$(Get-Pip-Mirror-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 Pip 镜像源`"
        Print-Msg `"2. 禁用 Pip 镜像源`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_pip_mirror.txt`" 2> `$null
                Print-Msg `"启用 Pip 镜像源成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_pip_mirror.txt`" -Force > `$null
                Print-Msg `"禁用 Pip 镜像源成功`"
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


# CUDA 内存分配器设置
function PyTorch-CUDA-Memory-Alloc-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前自动设置 CUDA 内存分配器设置: `$(Get-PyTorch-CUDA-Memory-Alloc-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用自动设置 CUDA 内存分配器`"
        Print-Msg `"2. 禁用自动设置 CUDA 内存分配器`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_set_pytorch_cuda_memory_alloc.txt`" 2> `$null
                Print-Msg `"启用自动设置 CUDA 内存分配器成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_set_pytorch_cuda_memory_alloc.txt`" -Force > `$null
                Print-Msg `"禁用自动设置 CUDA 内存分配器成功`"
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


# ComfyUI 运行环境检测设置
function ComfyUI-Env-Check-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 ComfyUI 运行环境检测设置: `$(Get-ComfyUI-Env-Check-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 ComfyUI 运行环境检测`"
        Print-Msg `"2. 禁用 ComfyUI 运行环境检测`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_check_env.txt`" 2> `$null
                Print-Msg `"启用 ComfyUI 运行环境检测成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_check_env.txt`" -Force > `$null
                Print-Msg `"禁用 ComfyUI 运行环境检测成功`"
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


# 检查 ComfyUI Installer 更新
function Check-ComfyUI-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/comfyui_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/comfyui_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/comfyui_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间
    ForEach (`$url in `$urls) {
        Print-Msg `"检查 ComfyUI Installer 更新中`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/comfyui_installer.ps1`"
        if (`$?) {
            `$latest_version = [int]`$(Get-Content `"`$PSScriptRoot/cache/comfyui_installer.ps1`" | Select-String -Pattern `"COMFYUI_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
            if (`$latest_version -gt `$COMFYUI_INSTALLER_VERSION) {
                New-Item -ItemType File -Path `"`$PSScriptRoot/use_update_mode.txt`" -Force > `$null
                Print-Msg `"ComfyUI Installer 有新版本可用`"
                Print-Msg `"调用 ComfyUI Installer 进行更新中`"
                `$folder_name = Split-Path `$PSScriptRoot -Leaf
                if (!(`$folder_name -eq `"ComfyUI`")) { # 检测脚本所在文件夹是否符合要求
                    Remove-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/update_time.txt`" 2> `$null
                    Print-Msg `"检测到 ComfyUI Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                    Print-Msg `"当前 ComfyUI Installer 管理脚本所在文件夹名称: `$folder_name`"
                    Print-Msg `"请前往 `$(Split-Path `"`$PSScriptRoot`") 路径, 将名称为 `$folder_name 的文件夹改名为 ComfyUI, 再重新更新 ComfyUI Installer 管理脚本`"
                    Print-Msg `"终止 ComfyUI Installer 的更新`"
                    return
                }
                Move-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" `"`$PSScriptRoot/../comfyui_installer.ps1`" -Force
                . `"`$PSScriptRoot/../comfyui_installer.ps1`"
                Print-Msg `"更新结束, 需重新启动 ComfyUI Installer 管理脚本以应用更新, 回车退出 ComfyUI Installer 管理脚本`"
                Read-Host | Out-Null
                exit 0
            } else {
                Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                Remove-Item -Path `"`$PSScriptRoot/cache/comfyui_installer.ps1`" 2> `$null
                Print-Msg `"ComfyUI Installer 已是最新版本`"
            }
            break
        } else {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 ComfyUI Installer 更新中`"
            } else {
                Print-Msg `"检查 ComfyUI Installer 更新失败`"
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

    if (Test-Path `"`$PSScriptRoot/git/bin/git.exe`") {
        `$git_status = `"已安装`"
    } else {
        `$git_status = `"未安装`"
        `$broken = 1
    }

    python -m pip show uv --quiet 2> `$null
    if (`$?) {
        `$uv_status = `"已安装`"
    } else {
        `$uv_status = `"未安装`"
        `$broken = 1
    }

    if (Test-Path `"`$PSScriptRoot/git/bin/aria2c.exe`") {
        `$aria2_status = `"已安装`"
    } else {
        `$aria2_status = `"未安装`"
        `$broken = 1
    }

    if (Test-Path `"`$PSScriptRoot/ComfyUI/gui.py`") {
        `$comfyui_status = `"已安装`"
    } else {
        `$comfyui_status = `"未安装`"
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
    Print-Msg `"Git: `$git_status`"
    Print-Msg `"uv: `$uv_status`"
    Print-Msg `"Aria2: `$aria2_status`"
    Print-Msg `"PyTorch: `$torch_status`"
    Print-Msg `"xFormers: `$xformers_status`"
    Print-Msg `"ComfyUI: `$comfyui_status`"
    Print-Msg `"-----------------------------------------------------`"
    if (`$broken -eq 1) {
        Print-Msg `"检测到环境出现组件缺失, 可尝试运行 ComfyUI Installer 进行安装`"
    } else {
        Print-Msg `"当前环境无缺失组件`"
    }
}


# 查看 ComfyUI Installer 文档
function Get-ComfyUI-Installer-Help-Docs {
    Print-Msg `"调用浏览器打开 ComfyUI Installer 文档中`"
    Start-Process `"https://github.com/licyk/sd-webui-all-in-one/blob/main/comfyui_installer.md`"
}


function Main {
    Print-Msg `"初始化中`"
    Print-Msg `"ComfyUI Installer 版本: v`$COMFYUI_INSTALLER_VERSION`"
    Set-Proxy
    Pip-Mirror-Status
    while (`$true) {
        `$go_to = 0
        Print-Msg `"-----------------------------------------------------`"
        Print-Msg `"当前环境配置:`"
        Print-Msg `"代理设置: `$(Get-Proxy-Setting)`"
        Print-Msg `"Python 包管理器: `$(Get-Python-Package-Manager-Setting)`"
        Print-Msg `"HuggingFace 镜像源设置: `$(Get-HuggingFace-Mirror-Setting)`"
        Print-Msg `"Github 镜像源设置: `$(Get-Github-Mirror-Setting)`"
        Print-Msg `"ComfyUI Installer 自动检查更新: `$(Get-ComfyUI-Installer-Auto-Check-Update-Setting)`"
        Print-Msg `"ComfyUI 启动参数: `$(Get-Launch-Args-Setting)`"
        Print-Msg `"自动创建 ComfyUI 快捷启动方式设置: `$(Get-Auto-Set-Launch-Shortcut-Setting)`"
        Print-Msg `"Pip 镜像源设置: `$(Get-Pip-Mirror-Setting)`"
        Print-Msg `"自动设置 CUDA 内存分配器设置: `$(Get-PyTorch-CUDA-Memory-Alloc-Setting)`"
        Print-Msg `"ComfyUI 运行环境检测设置: `$(Get-ComfyUI-Env-Check-Setting)`"
        Print-Msg `"-----------------------------------------------------`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 进入代理设置`"
        Print-Msg `"2. 进入 Python 包管理器设置`"
        Print-Msg `"3. 进入 HuggingFace 镜像源设置`"
        Print-Msg `"4. 进入 Github 镜像源设置`"
        Print-Msg `"5. 进入 ComfyUI Installer 自动检查更新设置`"
        Print-Msg `"6. 进入 ComfyUI 启动参数设置`"
        Print-Msg `"7. 进入自动创建 ComfyUI 快捷启动方式设置`"
        Print-Msg `"8. 进入 Pip 镜像源设置`"
        Print-Msg `"9. 进入自动设置 CUDA 内存分配器设置`"
        Print-Msg `"10. 进入 ComfyUI 运行环境检测设置`"
        Print-Msg `"11. 更新 ComfyUI Installer 管理脚本`"
        Print-Msg `"12. 检查环境完整性`"
        Print-Msg `"13. 查看 ComfyUI Installer 文档`"
        Print-Msg `"14. 退出 ComfyUI Installer 设置`"
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
                Update-Github-Mirror-Setting
                break
            }
            5 {
                Update-ComfyUI-Installer-Auto-Check-Update-Setting
                break
            }
            6 {
                Update-ComfyUI-Launch-Args-Setting
                break
            }
            7 {
                Auto-Set-Launch-Shortcut-Setting
                break
            }
            8 {
                Pip-Mirror-Setting
                break
            }
            9 {
                PyTorch-CUDA-Memory-Alloc-Setting
                break
            }
            10 {
                ComfyUI-Env-Check-Setting
                break
            }
            11 {
                Check-ComfyUI-Installer-Update
                break
            }
            12 {
                Check-Env
                break
            }
            13 {
                Get-ComfyUI-Installer-Help-Docs
                break
            }
            14 {
                `$go_to = 1
                break
            }
            Default {
                Print-Msg `"输入有误, 请重试`"
                break
            }
        }

        if (`$go_to -eq 1) {
            Print-Msg `"退出 ComfyUI Installer 设置`"
            break
        }
    }
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/ComfyUI/settings.ps1") {
        Print-Msg "更新 settings.ps1 中"
    } else {
        Print-Msg "生成 settings.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/ComfyUI/settings.ps1" -Value $content
}

# 虚拟环境激活脚本
function Write-Env-Activate-Script {
    $content = "
# ComfyUI Installer 版本和检查更新间隔
`$Env:COMFYUI_INSTALLER_VERSION = $COMFYUI_INSTALLER_VERSION
`$Env:UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# Pip 镜像源
`$PIP_INDEX_ADDR = `"$PIP_INDEX_ADDR`"
`$PIP_INDEX_ADDR_ORI = `"$PIP_INDEX_ADDR_ORI`"
`$PIP_EXTRA_INDEX_ADDR = `"$PIP_EXTRA_INDEX_ADDR`"
`$PIP_EXTRA_INDEX_ADDR_ORI = `"$PIP_EXTRA_INDEX_ADDR_ORI`"
`$PIP_FIND_ADDR = `"$PIP_FIND_ADDR`"
`$PIP_FIND_ADDR_ORI = `"$PIP_FIND_ADDR_ORI`"
`$USE_PIP_MIRROR = if (!(Test-Path `"`$PSScriptRoot/disable_pip_mirror.txt`")) { `$true } else { `$false }
`$PIP_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_INDEX_ADDR } else { `$PIP_INDEX_ADDR_ORI }
`$PIP_EXTRA_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_EXTRA_INDEX_ADDR } else { `$PIP_EXTRA_INDEX_ADDR_ORI }
`$PIP_FIND_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_FIND_ADDR } else { `$PIP_FIND_ADDR_ORI }
# `$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
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
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/ComfyUI/git/bin`"
`$Env:PATH = `"`$PYTHON_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$GIT_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
# 环境变量
`$Env:PIP_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
`$Env:PIP_EXTRA_INDEX_URL = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`" } else { `$PIP_EXTRA_INDEX_MIRROR }
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
`$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
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
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"
`$Env:COMFYUI_INSTALLER_ROOT = `$PSScriptRoot



# 提示符信息
function global:prompt {
    `"`$(Write-Host `"[ComfyUI Env]`" -ForegroundColor Green -NoNewLine) `$(Get-Location)> `"
}


# 消息输出
function global:Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[ComfyUI Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
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


# 更新 Aria2
function global:Update-Aria2 {
    `$url = `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/aria2c.exe`"
    Print-Msg `"下载 Aria2 中`"
    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null
    Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/aria2c.exe`"
    if (`$?) {
        Print-Msg `"更新 Aria2 中`"
        Move-Item -Path `"`$Env:CACHE_HOME/aria2c.exe`" -Destination `"`$Env:COMFYUI_INSTALLER_ROOT/git/bin/aria2c.exe`" -Force
        Print-Msg `"更新 Aria2 完成`"
    } else {
        Print-Msg `"下载 Aria2 失败, 无法进行更新, 可尝试重新运行更新命令`"
    }
}


# ComfyUI Installer 更新检测
function global:Check-ComfyUI-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/comfyui_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/comfyui_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/comfyui_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    Set-Content -Encoding UTF8 -Path `"`$Env:COMFYUI_INSTALLER_ROOT/update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间
    ForEach (`$url in `$urls) {
        Print-Msg `"检查 ComfyUI Installer 更新中`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/comfyui_installer.ps1`"
        if (`$?) {
            `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/comfyui_installer.ps1`" | Select-String -Pattern `"COMFYUI_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
            if (`$latest_version -gt `$Env:COMFYUI_INSTALLER_VERSION) {
                New-Item -ItemType File -Path `"`$Env:COMFYUI_INSTALLER_ROOT/use_update_mode.txt`" -Force > `$null
                Print-Msg `"ComfyUI Installer 有新版本可用`"
                Print-Msg `"调用 ComfyUI Installer 进行更新中`"
                `$folder_name = Split-Path `$Env:COMFYUI_INSTALLER_ROOT -Leaf
                if (!(`$folder_name -eq `"ComfyUI`")) { # 检测脚本所在文件夹是否符合要求
                    Remove-Item -Path `"`$Env:COMFYUI_INSTALLER_ROOT/cache/comfyui_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$Env:COMFYUI_INSTALLER_ROOT/use_update_mode.txt`" 2> `$null
                    Remove-Item -Path `"`$Env:COMFYUI_INSTALLER_ROOT/update_time.txt`" 2> `$null
                    Print-Msg `"检测到 ComfyUI Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                    Print-Msg `"当前 ComfyUI Installer 管理脚本所在文件夹名称: `$folder_name`"
                    Print-Msg `"请前往 `$(Split-Path `"`$(Split-Path `"`$Env:CACHE_HOME`")`") 路径, 将名称为 `$folder_name 的文件夹改名为 ComfyUI, 再重新更新 ComfyUI Installer 管理脚本`"
                    Print-Msg `"终止 ComfyUI Installer 的更新`"
                    return
                }
                Move-Item -Path `"`$Env:CACHE_HOME/comfyui_installer.ps1`" `"`$Env:COMFYUI_INSTALLER_ROOT/../comfyui_installer.ps1`" -Force
                . `"`$Env:COMFYUI_INSTALLER_ROOT/../comfyui_installer.ps1`"
                Print-Msg `"更新结束, 需重新启动 ComfyUI Installer 管理脚本以应用更新, 回车退出 ComfyUI Installer 管理脚本`"
                Read-Host | Out-Null
                exit 0
            } else {
                Remove-Item -Path `"`$Env:COMFYUI_INSTALLER_ROOT/use_update_mode.txt`" 2> `$null
                Remove-Item -Path `"`$Env:CACHE_HOME/comfyui_installer.ps1`" 2> `$null
                Print-Msg `"ComfyUI Installer 已是最新版本`"
            }
            break
        } else {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 ComfyUI Installer 更新中`"
            } else {
                Print-Msg `"检查 ComfyUI Installer 更新失败`"
            }
        }
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


# 安装 ComfyUI 自定义节点
function global:Install-ComfyUI-Node (`$url) {
    # 应用 Github 镜像源
    if (`$global:is_test_gh_mirror -ne 1) {
        Test-Github-Mirror
        `$global:is_test_gh_mirror = 1
    }

    `$node_name = `$(Split-Path `$url -Leaf) -replace `".git`", `"`"
    if (!(Test-Path `"`$Env:INVOKEAI_ROOT/ComfyUI/custom_nodes/`$node_name`")) {
        `$status = 1
    } else {
        `$items = Get-ChildItem `"`$Env:INVOKEAI_ROOT/ComfyUI/custom_nodes/`$node_name`" -Recurse
        if (`$items.Count -eq 0) {
            `$status = 1
        }
    }

    if (`$status -eq 1) {
        Print-Msg `"安装 `$node_name 自定义节点中`"
        git clone --recurse-submodules `$url `"`$Env:INVOKEAI_ROOT/ComfyUI/custom_nodes/`$node_name`"
        if (`$?) {
            Print-Msg `"`$node_name 自定义节点安装成功`"
        } else {
            Print-Msg `"`$node_name 自定义节点安装失败`"
        }
    } else {
        Print-Msg `"`$node_name 自定义节点已安装`"
    }
}


# Git 下载命令
function global:Git-Clone (`$url, `$path) {
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
            git -C `"`$path`" submodule init # 初始化 Git 子模块
            `$branch = `$(git -C `"`$path`" branch -a | Select-String -Pattern `"/HEAD`").ToString().Split(`"/`")[3] # 查询远程 HEAD 所指分支
            git -C `"`$path`" checkout `$branch # 切换到主分支
            git -C `"`$path`" reset --recurse-submodules --hard origin/`$branch # 回退到远程分支的版本
        }
    }
}


# 更新所有 ComfyUI 自定义节点
function global:Update-ComfyUI-Node {
    # 应用 Github 镜像源
    if (`$global:is_test_gh_mirror -ne 1) {
        Test-Github-Mirror
        `$global:is_test_gh_mirror = 1
    }

    `$node_list = Get-ChildItem -Path `"`$Env:COMFYUI_INSTALLER_ROOT/ComfyUI/custom_nodes`" | Select-Object -ExpandProperty FullName
    `$sum = 0
    `$count = 0
    ForEach (`$node in `$node_list) {
        if (Test-Path `"`$node/.git`") {
            `$sum += 1
        }
    }
    Print-Msg `"更新 ComfyUI 自定义节点中`"
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
    Print-Msg `"更新 ComfyUI 自定义节点完成`"
}


# 列出已安装的 ComfyUI 自定义节点
function global:List-Node {
    `$node_list = Get-ChildItem -Path `"`$Env:COMFYUI_INSTALLER_ROOT/ComfyUI/custom_nodes`" | Select-Object -ExpandProperty FullName
    Print-Msg `"当前 ComfyUI 已安装的自定义节点`"
    `$count = 0
    ForEach (`$i in `$node_list) {
        if (Test-Path `"`$i`" -PathType Container) {
            `$count += 1
            `$name = [System.IO.Path]::GetFileNameWithoutExtension(`"`$i`")
            Print-Msg `"- `$name`"
        }
    }
    Print-Msg `"ComfyUI 自定义节点路径: `$([System.IO.Path]::GetFullPath(`"`$Env:COMFYUI_INSTALLER_ROOT/ComfyUI/custom_nodes`"))`"
    Print-Msg `"ComfyUI 自定义节点数量: `$count`"
}


# 安装绘世启动器
function global:Install-Hanamizuki {
    `$urls = @(`"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/hanamizuki.exe`", `"https://github.com/licyk/term-sd/releases/download/archive/hanamizuki.exe`", `"https://gitee.com/licyk/term-sd/releases/download/archive/hanamizuki.exe`")

    if (Test-Path `"`$Env:COMFYUI_INSTALLER_ROOT/ComfyUI/hanamizuki.exe`") {
        Print-Msg `"绘世启动器已安装, 路径: `$([System.IO.Path]::GetFullPath(`"`$Env:COMFYUI_INSTALLER_ROOT/ComfyUI/hanamizuki.exe`"))`"
    } else {
        ForEach (`$url in `$urls) {
            Print-Msg `"下载绘世启动器中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/hanamizuki.exe`"
            if (`$?) {
                Move-Item -Path `"`$Env:CACHE_HOME/hanamizuki.exe`" `"`$Env:COMFYUI_INSTALLER_ROOT/ComfyUI/hanamizuki.exe`" -Force
                Print-Msg `"绘世启动器安装成功, 路径: `$([System.IO.Path]::GetFullPath(`"`$Env:COMFYUI_INSTALLER_ROOT/ComfyUI/hanamizuki.exe`"))`"
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试下载绘世启动器中`"
                } else {
                    Print-Msg `"下载绘世启动器失败`"
                }
            }
        }
    }

    Print-Msg `"检查绘世启动器运行环境`"
    if (!(Test-Path `"`$Env:COMFYUI_INSTALLER_ROOT/ComfyUI/python/python.exe`")) {
        if (Test-Path `"`$Env:COMFYUI_INSTALLER_ROOT/python`") {
            Print-Msg `"尝试将 Python 移动至 `$Env:COMFYUI_INSTALLER_ROOT\ComfyUI 中`"
            Move-Item -Path `"`$Env:COMFYUI_INSTALLER_ROOT/python`" `"`$Env:COMFYUI_INSTALLER_ROOT/ComfyUI`" -Force
            if (`$?) {
                Print-Msg `"Python 路径移动成功`"
            } else {
                Print-Msg `"Python 路径移动失败, 这将导致绘世启动器无法正确识别到 Python 环境`"
                Print-Msg `"请关闭所有占用 Python 的进程, 并重新运行该命令`"
            }
        } else {
            Print-Msg `"环境缺少 Python, 无法为绘世启动器准备 Python 环境, 请重新运行 ComfyUI Installer 修复环境`"
        }
    }

    if (!(Test-Path `"`$Env:COMFYUI_INSTALLER_ROOT/ComfyUI/git/bin/git.exe`")) {
        if (Test-Path `"`$Env:COMFYUI_INSTALLER_ROOT/git`") {
            Print-Msg `"尝试将 Git 移动至 `$Env:COMFYUI_INSTALLER_ROOT\ComfyUI 中`"
            Move-Item -Path `"`$Env:COMFYUI_INSTALLER_ROOT/git`" `"`$Env:COMFYUI_INSTALLER_ROOT/ComfyUI`" -Force
            if (`$?) {
                Print-Msg `"Git 路径移动成功`"
            } else {
                Print-Msg `"Git 路径移动失败, 这将导致绘世启动器无法正确识别到 Git 环境`"
                Print-Msg `"请关闭所有占用 Git 的进程, 并重新运行该命令`"
            }
        } else {
            Print-Msg `"环境缺少 Git, 无法为绘世启动器准备 Git 环境, 请重新运行 ComfyUI Installer 修复环境`"
        }
    }

    Print-Msg `"检查绘世启动器运行环境结束`"
}


# 设置 Python 命令别名
function global:pip {
    python -m pip @args
}

Set-Alias pip3 pip
Set-Alias pip3.10 pip
Set-Alias python3 python
Set-Alias python3.10 python


# 列出 ComfyUI Installer 内置命令
function global:List-CMD {
    Write-Host `"
==================================
ComfyUI Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
==================================

当前可用的 ComfyUI Installer 内置命令：

    Update-uv
    Update-Aria2
    Check-ComfyUI-Installer-Update
    Test-Github-Mirror
    Install-ComfyUI-Node
    Git-Clone
    Fix-Git-Point-Off-Set
    Update-ComfyUI-Node
    Install-Hanamizuki
    List-Node
    List-CMD

更多帮助信息可在 ComfyUI Installer 文档中查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/comfyui_installer.md
`"
}


# Pip 镜像源状态
function Pip-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 Pip 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pip_mirror.txt 配置文件, 已将 Pip 源切换至官方源`"
    }
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


# HuggingFace 镜像源
function Set-HuggingFace-Mirror {
    if (!(Test-Path `"`$PSScriptRoot/disable_hf_mirror.txt`")) { # 检测是否禁用了自动设置 HuggingFace 镜像源
        if (Test-Path `"`$PSScriptRoot/hf_mirror.txt`") { # 本地存在 HuggingFace 镜像源配置
            `$hf_mirror_value = Get-Content `"`$PSScriptRoot/hf_mirror.txt`"
            `$Env:HF_ENDPOINT = `$hf_mirror_value
            Print-Msg `"检测到本地存在 hf_mirror.txt 配置文件, 已读取该配置并设置 HuggingFace 镜像源`"
        } else { # 使用默认设置
            `$Env:HF_ENDPOINT = `"https://hf-mirror.com`"
            Print-Msg `"使用默认 HuggingFace 镜像源`"
        }
    } else {
        Print-Msg `"检测到本地存在 disable_hf_mirror.txt 镜像源配置文件, 禁用自动设置 HuggingFace 镜像源`"
    }
}


# Github 镜像源
function Set-Github-Mirror {
    if (Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") { # 禁用 Github 镜像源
        Print-Msg `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件, 禁用 Github 镜像源`"
    } else {
        if (Test-Path `"`$PSScriptRoot/gh_mirror.txt`") { # 使用自定义 Github 镜像源
            `$Env:GIT_CONFIG_GLOBAL = `"`$PSScriptRoot/.gitconfig`" # 设置 Git 配置文件路径
            if (Test-Path `"`$PSScriptRoot/.gitconfig`") {
                Remove-Item -Path `"`$PSScriptRoot/.gitconfig`" -Force
            }
            `$github_mirror = Get-Content `"`$PSScriptRoot/gh_mirror.txt`"
            git config --global --add safe.directory `"*`"
            git config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
            Print-Msg `"检测到本地存在 gh_mirror.txt Github 镜像源配置文件, 已读取 Github 镜像源配置文件并设置 Github 镜像源`"
        }
    }
}


function Main {
    Print-Msg `"初始化中`"
    Print-Msg `"ComfyUI Installer 版本: v`$Env:COMFYUI_INSTALLER_VERSION`"
    Set-Proxy
    Set-HuggingFace-Mirror
    Set-Github-Mirror
    Pip-Mirror-Status
    Print-Msg `"激活 ComfyUI Env`"
    Print-Msg `"更多帮助信息可在 ComfyUI Installer 项目地址查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/comfyui_installer.md`"
}

###################

Main
"

    if (Test-Path "$PSScriptRoot/ComfyUI/activate.ps1") {
        Print-Msg "更新 activate.ps1 中"
    } else {
        Print-Msg "生成 activate.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/ComfyUI/activate.ps1" -Value $content
}


# 快捷启动终端脚本, 启动后将自动运行环境激活脚本
function Write-Launch-Terminal-Script {
    $content = "
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[ComfyUI Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}

Print-Msg `"执行 ComfyUI Installer 激活环境脚本`"
powershell -NoExit -File `"`$PSScriptRoot/activate.ps1`"
"

    if (Test-Path "$PSScriptRoot/ComfyUI/terminal.ps1") {
        Print-Msg "更新 terminal.ps1 中"
    } else {
        Print-Msg "生成 terminal.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/ComfyUI/terminal.ps1" -Value $content
}


# 帮助文档
function Write-ReadMe {
    $content = "==================================
ComfyUI Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
==================================

这是关于 ComfyUI 的简单使用文档。

使用 ComfyUI Installer 进行安装并安装成功后，将在当前目录生成 ComfyUI 文件夹，以下为文件夹中不同文件 / 文件夹的作用。

cache：缓存文件夹，保存着 Pip / HuggingFace 等缓存文件。
python：Python 的存放路径。请注意，请勿将该 Python 文件夹添加到环境变量，这可能导致不良后果。
git：Git 的存放路径。
ComfyUI：ComfyUI 存放的文件夹。
models：使用模型下载脚本下载模型时模型的存放位置。
activate.ps1：虚拟环境激活脚本，使用该脚本激活虚拟环境后即可使用 Python、Pip、Git 的命令。
get_comfyui_installer.ps1：获取最新的 ComfyUI Installer 安装脚本，运行后将会在与 ComfyUI 文件夹同级的目录中生成 comfyui_installer.ps1 安装脚本。
update.ps1：更新 ComfyUI 的脚本，可使用该脚本更新 ComfyUI。
launch.ps1：启动 ComfyUI 的脚本。
reinstall_pytorch.ps1：重新安装 PyTorch 的脚本，在 PyTorch 出问题或者需要切换 PyTorch 版本时可使用。
download_model.ps1：下载模型的脚本，下载的模型将存放在 models 文件夹中。关于模型的介绍可阅读：https://github.com/licyk/README-collection/blob/main/model-info/README.md。
settings.ps1：管理 ComfyUI Installer 的设置。
terminal.ps1：启动 PowerShell 终端并自动激活虚拟环境，激活虚拟环境后即可使用 Python、Pip、Git 的命令。
help.txt：帮助文档。


要启动 ComfyUI，可在 ComfyUI 文件夹中找到 launch.ps1 脚本，右键这个脚本，选择使用 PowerShell 运行，等待 ComfyUI 启动完成，启动完成后将自动打开浏览器进入 ComfyUI 界面。

脚本为 ComfyUI 设置了 HuggingFace 镜像源，解决国内无法直接访问 HuggingFace，导致 ComfyUI 无法从 HuggingFace 下载模型的问题。
如果想自定义 HuggingFace 镜像源，可以在本地创建 hf_mirror.txt 文件，在文件中填写 HuggingFace 镜像源的地址后保存，再次启动脚本时将自动读取配置。
如果需要禁用 HuggingFace 镜像源，则创建 disable_hf_mirror.txt 文件，启动脚本时将不再设置 HuggingFace 镜像源。

以下为可用的 HuggingFace 镜像源地址：
https://hf-mirror.com
https://huggingface.sukaka.top

为了解决访问 Github 速度慢的问题，脚本默认启用 Github 镜像源，在运行 ComfyUI Installer 或者 ComfyUI 更新脚本时将自动测试可用的 Github 镜像源并设置。
如果想自定义 Github 镜像源，可以在本地创建 gh_mirror.txt 文件，在文本中填写 Github 镜像源的地址后保存，再次启动脚本时将自动读取配置。
如果需要禁用 Github 镜像源，则创建 disable_gh_mirror.txt 文件，启动脚本时将不再设置 Github 镜像源。

以下为可用的 Github 镜像源：
https://mirror.ghproxy.com/https://github.com
https://ghproxy.net/https://github.com
https://gitclone.com/github.com
https://gh-proxy.com/https://github.com
https://ghps.cc/https://github.com
https://gh.idayer.com/https://github.com

若要为脚本设置代理，则在代理软件中打开系统代理模式即可，或者在本地创建 proxy.txt 文件，在文件中填写代理地址后保存，再次启动脚本是将自动读取配置。
如果要禁用自动设置代理，可以在本地创建 disable_proxy.txt 文件，启动脚本时将不再自动设置代理。

脚本默认调用 uv 作为 Python 包管理器，相比于 Pip，安装 Python 软件包的速度更快。
如需禁用，可在脚本目录下创建 disable_uv.txt 文件，这将禁用 uv 并使用 Pip 作为 Python 包管理器。

设置 ComfyUI 的启动参数，可以在和 launch.ps1 脚本同级的目录创建一个 launch_args.txt 文件，在文件内写上启动参数，运行 ComfyUI 启动脚本时将自动读取该文件内的启动参数并应用。

ComfyUI Installer 提供了配置管理器, 运行 settings.ps1 即可管理各个配置。

ComfyUI Installer 的管理脚本在启动时会检查管理脚本的更新，如果有更新将会提示并显示具体的更新方法，如果要禁用更新，可以在脚本同级的目录创建 disable_update.txt 文件，这将禁用 ComfyUI Installer 更新检查。

ComfyUI 的使用教程：
https://sdnote.netlify.app/guide/comfyui
https://sdnote.netlify.app/help/comfyui
https://www.aigodlike.com
https://space.bilibili.com/35723238/channel/collectiondetail?sid=1320931
https://comfyanonymous.github.io/ComfyUI_examples
https://blenderneko.github.io/ComfyUI-docs

更多详细的帮助可在下面的链接查看。
ComfyUI Installer 使用帮助：https://github.com/licyk/sd-webui-all-in-one/blob/main/comfyui_installer.md
ComfyUI 项目地址：https://github.com/comfyanonymous/ComfyUI
"

    if (Test-Path "$PSScriptRoot/ComfyUI/help.txt") {
        Print-Msg "更新 help.txt 中"
    } else {
        Print-Msg "生成 help.txt 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/ComfyUI/help.txt" -Value $content
}


# 写入管理脚本和文档
function Write-Manager-Scripts {
    Write-Launch-Script
    Write-Update-Script
    Write-ComfyUI-Install-Script
    Write-PyTorch-ReInstall-Script
    Write-Download-Model-Script
    Write-ComfyUI-Installer-Settings-Script
    Write-Env-Activate-Script
    Write-Launch-Terminal-Script
    Write-ReadMe
}


# 执行安装
function Use-Install-Mode {
    Set-Proxy
    Set-uv
    Pip-Mirror-Status
    Print-Msg "启动 ComfyUI 安装程序"
    Print-Msg "提示: 若出现某个步骤执行失败, 可尝试再次运行 ComfyUI Installer, 更多的说明请阅读 ComfyUI Installer 使用文档"
    Print-Msg "ComfyUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/comfyui_installer.md"
    Print-Msg "即将进行安装的路径: $PSScriptRoot\ComfyUI"
    Check-Install
    Print-Msg "添加管理脚本和文档中"
    Write-Manager-Scripts
    Print-Msg "ComfyUI 安装结束, 安装路径为: $PSScriptRoot\ComfyUI"
    Print-Msg "帮助文档可在 ComfyUI 文件夹中查看, 双击 help.txt 文件即可查看, 更多的说明请阅读 ComfyUI Installer 使用文档"
    Print-Msg "ComfyUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/comfyui_installer.md"
    Print-Msg "退出 ComfyUI Installer"
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
    Print-Msg "ComfyUI Installer 版本: v$COMFYUI_INSTALLER_VERSION"
    if (Test-Path "$PSScriptRoot/ComfyUI/use_update_mode.txt") {
        Print-Msg "使用更新模式"
        Remove-Item -Path "$PSScriptRoot/ComfyUI/use_update_mode.txt" 2> $null
        Set-Content -Encoding UTF8 -Path "$PSScriptRoot/ComfyUI/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
        Use-Update-Mode
    } else {
        Print-Msg "使用安装模式"
        Use-Install-Mode
    }
}


###################


Main