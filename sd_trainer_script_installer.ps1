﻿param (
    [string]$InstallPath = "$PSScriptRoot/SD-Trainer-Script",
    [string]$InstallBranch,
    [switch]$UseUpdateMode,
    [switch]$DisablePipMirror,
    [switch]$DisableProxy,
    [string]$UseCustomProxy,
    [switch]$DisableUV,
    [switch]$DisableGithubMirror,
    [string]$UseCustomGithubMirror,
    [switch]$Help
)
# 有关 PowerShell 脚本保存编码的问题: https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_character_encoding?view=powershell-7.4#the-byte-order-mark
# SD-Trainer-Script Installer 版本和检查更新间隔
$SD_TRAINER_SCRIPT_INSTALLER_VERSION = 101
$UPDATE_TIME_SPAN = 3600
# Pip 镜像源
$PIP_INDEX_ADDR = "https://mirrors.cloud.tencent.com/pypi/simple"
$PIP_INDEX_ADDR_ORI = "https://pypi.python.org/simple"
$PIP_EXTRA_INDEX_ADDR = "https://mirrors.cernet.edu.cn/pypi/web/simple"
$PIP_EXTRA_INDEX_ADDR_ORI = "https://download.pytorch.org/whl"
$PIP_FIND_ADDR = "https://mirror.sjtu.edu.cn/pytorch-wheels/torch_stable.html"
$PIP_FIND_ADDR_ORI = "https://download.pytorch.org/whl/torch_stable.html"
$USE_PIP_MIRROR = if ((!(Test-Path "$PSScriptRoot/disable_pip_mirror.txt")) -and (!($DisablePipMirror))) { $true } else { $false }
$PIP_INDEX_MIRROR = if ($USE_PIP_MIRROR) { $PIP_INDEX_ADDR } else { $PIP_INDEX_ADDR_ORI }
$PIP_EXTRA_INDEX_MIRROR = if ($USE_PIP_MIRROR) { "$PIP_EXTRA_INDEX_ADDR_ORI $PIP_EXTRA_INDEX_ADDR" } else { $PIP_EXTRA_INDEX_ADDR_ORI }
$PIP_FIND_MIRROR = if ($USE_PIP_MIRROR) { $PIP_FIND_ADDR } else { $PIP_FIND_ADDR_ORI }
# $PIP_FIND_MIRROR_CU121 = "https://download.pytorch.org/whl/cu121/torch_stable.html"
$PIP_EXTRA_INDEX_MIRROR_PYTORCH = "https://download.pytorch.org/whl"
$PIP_EXTRA_INDEX_MIRROR_CU121 = "https://download.pytorch.org/whl/cu121"
$PIP_EXTRA_INDEX_MIRROR_CU124 = "https://download.pytorch.org/whl/cu124"
# Github 镜像源列表
$GITHUB_MIRROR_LIST = @(
    "https://ghgo.xyz/https://github.com",
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
$UV_MINIMUM_VER = "0.5.11"
# SD-Trainer-Script 仓库地址
$SD_TRAINER_SCRIPT_REPO = if ((Test-Path "$PSScriptRoot/install_sd_scripts.txt") -or ($InstallBranch -eq "sd_scripts")) {
    "https://github.com/kohya-ss/sd-scripts"
} elseif ((Test-Path "$PSScriptRoot/install_simple_tuner.txt") -or ($InstallBranch -eq "simple_tuner")) {
    "https://github.com/bghira/SimpleTuner"
} elseif ((Test-Path "$PSScriptRoot/install_ai_toolkit.txt") -or ($InstallBranch -eq "ai_toolkit")) {
    "https://github.com/ostris/ai-toolkit"
} elseif ((Test-Path "$PSScriptRoot/install_finetrainers.txt") -or ($InstallBranch -eq "finetrainers")) {
    "https://github.com/a-r-r-o-w/finetrainers"
} elseif ((Test-Path "$PSScriptRoot/install_diffusion_pipe.txt") -or ($InstallBranch -eq "diffusion_pipe")) {
    "https://github.com/tdrussell/diffusion-pipe"
} elseif ((Test-Path "$PSScriptRoot/install_musubi_tuner.txt") -or ($InstallBranch -eq "musubi_tuner")) {
    "https://github.com/kohya-ss/musubi-tuner"
} else {
    "https://github.com/kohya-ss/sd-scripts"
}
# PATH
$PYTHON_PATH = "$InstallPath/python"
$PYTHON_EXTRA_PATH = "$InstallPath/sd-scripts/python"
$PYTHON_SCRIPTS_PATH = "$InstallPath/python/Scripts"
$PYTHON_SCRIPTS_EXTRA_PATH = "$InstallPath/sd-scripts/python/Scripts"
$GIT_PATH = "$InstallPath/git/bin"
$GIT_EXTRA_PATH = "$InstallPath/sd-scripts/git/bin"
$Env:PATH = "$PYTHON_EXTRA_PATH$([System.IO.Path]::PathSeparator)$PYTHON_SCRIPTS_EXTRA_PATH$([System.IO.Path]::PathSeparator)$GIT_EXTRA_PATH$([System.IO.Path]::PathSeparator)$PYTHON_PATH$([System.IO.Path]::PathSeparator)$PYTHON_SCRIPTS_PATH$([System.IO.Path]::PathSeparator)$GIT_PATH$([System.IO.Path]::PathSeparator)$Env:PATH"
# 环境变量
$Env:PIP_INDEX_URL = $PIP_INDEX_MIRROR
$Env:PIP_EXTRA_INDEX_URL = $PIP_EXTRA_INDEX_MIRROR
$Env:PIP_FIND_LINKS = $PIP_FIND_MIRROR
$Env:UV_INDEX_URL = $PIP_INDEX_MIRROR
$Env:UV_EXTRA_INDEX_URL = $PIP_EXTRA_INDEX_MIRROR
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
$Env:CACHE_HOME = "$InstallPath/cache"
$Env:HF_HOME = "$InstallPath/cache/huggingface"
$Env:MATPLOTLIBRC = "$InstallPath/cache"
$Env:MODELSCOPE_CACHE = "$InstallPath/cache/modelscope/hub"
$Env:MS_CACHE_HOME = "$InstallPath/cache/modelscope/hub"
$Env:SYCL_CACHE_DIR = "$InstallPath/cache/libsycl_cache"
$Env:TORCH_HOME = "$InstallPath/cache/torch"
$Env:U2NET_HOME = "$InstallPath/cache/u2net"
$Env:XDG_CACHE_HOME = "$InstallPath/cache"
$Env:PIP_CACHE_DIR = "$InstallPath/cache/pip"
$Env:PYTHONPYCACHEPREFIX = "$InstallPath/cache/pycache"
$Env:UV_CACHE_DIR = "$InstallPath/cache/uv"
$Env:UV_PYTHON = "$InstallPath/python/python.exe"



# 消息输出
function Print-Msg ($msg) {
    Write-Host "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")]" -ForegroundColor Yellow -NoNewline
    Write-Host "[SD-Trainer-Script Installer]" -ForegroundColor Cyan -NoNewline
    Write-Host ":: " -ForegroundColor Blue -NoNewline
    Write-Host "$msg"
}


# 显示 SD-Trainer-Script Installer 版本
function Get-SD-Trainer-Script-Installer-Version {
    $ver = $([string]$SD_TRAINER_SCRIPT_INSTALLER_VERSION).ToCharArray()
    $major = ($ver[0..($ver.Length - 3)])
    $minor = $ver[-2]
    $micro = $ver[-1]
    Print-Msg "SD-Trainer-Script Installer 版本: v${major}.${minor}.${micro}"
}


# Pip 镜像源状态
function Pip-Mirror-Status {
    if ($USE_PIP_MIRROR) {
        Print-Msg "使用 Pip 镜像源"
    } else {
        Print-Msg "检测到 disable_pip_mirror.txt 配置文件 / 命令行参数 -DisablePipMirror, 已将 Pip 源切换至官方源"
    }
}


# 代理配置
function Set-Proxy {
    $Env:NO_PROXY = "localhost,127.0.0.1,::1"
    # 检测是否禁用自动设置镜像源
    if ((Test-Path "$PSScriptRoot/disable_proxy.txt") -or ($DisableProxy)) {
        Print-Msg "检测到本地存在 disable_proxy.txt 代理配置文件 / 命令行参数 -DisableProxy, 禁用自动设置代理"
        return
    }

    $internet_setting = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    if ((Test-Path "$PSScriptRoot/proxy.txt") -or ($UseCustomProxy -ne "")) { # 本地存在代理配置
        if ($UseCustomProxy -ne "") {
            $proxy_value = $UseCustomProxy
        } else {
            $proxy_value = Get-Content "$PSScriptRoot/proxy.txt"
        }
        $Env:HTTP_PROXY = $proxy_value
        $Env:HTTPS_PROXY = $proxy_value
        Print-Msg "检测到本地存在 proxy.txt 代理配置文件 / 命令行参数 -UseCustomProxy, 已读取代理配置文件并设置代理"
    } elseif ($internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        $proxy_addr = $($internet_setting.ProxyServer)
        # 提取代理地址
        if (($proxy_addr -match "http=(.*?);") -or ($proxy_addr -match "https=(.*?);")) {
            $proxy_value = $matches[1]
            # 去除 http / https 前缀
            $proxy_value = $proxy_value.ToString().Replace("http://", "").Replace("https://", "")
            $proxy_value = "http://${proxy_value}"
        } elseif ($proxy_addr -match "socks=(.*)") {
            $proxy_value = $matches[1]
            # 去除 socks 前缀
            $proxy_value = $proxy_value.ToString().Replace("http://", "").Replace("https://", "")
            $proxy_value = "socks://${proxy_value}"
        } else {
            $proxy_value = "http://${proxy_addr}"
        }
        $Env:HTTP_PROXY = $proxy_value
        $Env:HTTPS_PROXY = $proxy_value
        Print-Msg "检测到系统设置了代理, 已读取系统中的代理配置并设置代理"
    }
}


# 设置 uv 的使用状态
function Set-uv {
    if ((Test-Path "$PSScriptRoot/disable_uv.txt") -or ($DisableUV)) {
        Print-Msg "检测到 disable_uv.txt 配置文件 / 命令行参数 -DisableUV, 已禁用 uv, 使用 Pip 作为 Python 包管理器"
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
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/python-3.10.15-amd64.zip"
    $cache_path = "$Env:CACHE_HOME/python_tmp"
    $path = "$InstallPath/python"

    # 下载 Python
    Print-Msg "正在下载 Python"
    Invoke-WebRequest -Uri $url -OutFile "$Env:CACHE_HOME/python-3.10.15-amd64.zip"
    if ($?) { # 检测是否下载成功并解压
        if (Test-Path "$cache_path") {
            Remove-Item -Path "$cache_path" -Force -Recurse
        }
        # 解压 Python
        Print-Msg "正在解压 Python"
        Expand-Archive -Path "$Env:CACHE_HOME/python-3.10.15-amd64.zip" -DestinationPath "$cache_path" -Force
        # 清理空文件夹
        if (Test-Path "$path") {
            $random_string = [Guid]::NewGuid().ToString().Substring(0, 18)
            Move-Item -Path "$path" -Destination "$Env:CACHE_HOME/$random_string" -Force
        }
        New-Item -ItemType Directory -Path "$([System.IO.Path]::GetDirectoryName($path))" -Force > $null
        Move-Item -Path "$cache_path" -Destination "$path" -Force
        Remove-Item -Path "$Env:CACHE_HOME/python-3.10.15-amd64.zip" -Force -Recurse
        Print-Msg "Python 安装成功"
    } else {
        Print-Msg "Python 安装失败, 终止 SD-Trainer-Script 安装进程, 可尝试重新运行 SD-Trainer-Script Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 下载并解压 Git
function Install-Git {
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/PortableGit.zip"
    $cache_path = "$Env:CACHE_HOME/git_tmp"
    $path = "$InstallPath/git"

    Print-Msg "正在下载 Git"
    Invoke-WebRequest -Uri $url -OutFile "$Env:CACHE_HOME/PortableGit.zip"
    if ($?) { # 检测是否下载成功并解压
        if (Test-Path "$cache_path") {
            Remove-Item -Path "$cache_path" -Force -Recurse
        }
        # 解压 Git
        Print-Msg "正在解压 Git"
        Expand-Archive -Path "$Env:CACHE_HOME/PortableGit.zip" -DestinationPath "$cache_path" -Force
        # 清理空文件夹
        if (Test-Path "$path") {
            $random_string = [Guid]::NewGuid().ToString().Substring(0, 18)
            Move-Item -Path "$path" -Destination "$Env:CACHE_HOME/$random_string" -Force
        }
        New-Item -ItemType Directory -Path "$([System.IO.Path]::GetDirectoryName($path))" -Force > $null
        Move-Item -Path "$cache_path" -Destination "$path" -Force
        Remove-Item -Path "$Env:CACHE_HOME/PortableGit.zip" -Force -Recurse
        Print-Msg "Git 安装成功"
    } else {
        Print-Msg "Git 安装失败, 终止 SD-Trainer-Script 安装进程, 可尝试重新运行 SD-Trainer-Script Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 下载 Aria2
function Install-Aria2 {
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/aria2c.exe"
    Print-Msg "正在下载 Aria2"
    Invoke-WebRequest -Uri $url -OutFile "$Env:CACHE_HOME/aria2c.exe"
    if ($?) {
        Move-Item -Path "$Env:CACHE_HOME/aria2c.exe" -Destination "$InstallPath/git/bin/aria2c.exe" -Force
        Print-Msg "Aria2 下载成功"
    } else {
        Print-Msg "Aria2 下载失败, 终止 SD-Trainer-Script 安装进程, 可尝试重新运行 SD-Trainer-Script Installer 重试失败的安装"
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
        Print-Msg "uv 下载失败, 终止 SD-Trainer-Script 安装进程, 可尝试重新运行 SD-Trainer-Script Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# Github 镜像测试
function Test-Github-Mirror {
    $Env:GIT_CONFIG_GLOBAL = "$InstallPath/.gitconfig" # 设置 Git 配置文件路径
    if (Test-Path "$InstallPath/.gitconfig") {
        Remove-Item -Path "$InstallPath/.gitconfig" -Force -Recurse
    }

    # 默认 Git 配置
    git config --global --add safe.directory "*"
    git config --global core.longpaths true

    if ((Test-Path "$PSScriptRoot/disable_gh_mirror.txt") -or ($DisableGithubMirror)) { # 禁用 Github 镜像源
        Print-Msg "检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件 / 命令行参数 -DisableGithubMirror, 禁用 Github 镜像源"
        return
    }

    # 使用自定义 Github 镜像源
    if ((Test-Path "$PSScriptRoot/gh_mirror.txt") -or ($UseCustomGithubMirror -ne "")) {
        if ($UseCustomGithubMirror -ne "") {
            $github_mirror = $UseCustomGithubMirror
        } else {
            $github_mirror = Get-Content "$PSScriptRoot/gh_mirror.txt"
        }
        git config --global url."$github_mirror".insteadOf "https://github.com"
        Print-Msg "检测到本地存在 gh_mirror.txt Github 镜像源配置文件 / 命令行参数 -UseCustomGithubMirror, 已读取 Github 镜像源配置文件并设置 Github 镜像源"
        return
    }

    # 自动检测可用镜像源并使用
    $status = 0
    ForEach($i in $GITHUB_MIRROR_LIST) {
        Print-Msg "测试 Github 镜像源: $i"
        if (Test-Path "$Env:CACHE_HOME/github-mirror-test") {
            Remove-Item -Path "$Env:CACHE_HOME/github-mirror-test" -Force -Recurse
        }
        git clone "$i/licyk/empty" "$Env:CACHE_HOME/github-mirror-test" --quiet
        if ($?) {
            Print-Msg "该 Github 镜像源可用"
            $github_mirror = $i
            $status = 1
            break
        } else {
            Print-Msg "镜像源不可用, 更换镜像源进行测试"
        }
    }

    if (Test-Path "$Env:CACHE_HOME/github-mirror-test") {
        Remove-Item -Path "$Env:CACHE_HOME/github-mirror-test" -Force -Recurse
    }

    if ($status -eq 0) {
        Print-Msg "无可用 Github 镜像源, 取消使用 Github 镜像源"
    } else {
        Print-Msg "设置 Github 镜像源"
        git config --global url."$github_mirror".insteadOf "https://github.com"
    }
}


# 安装 SD-Trainer-Script
function Install-SD-Trainer-Script {
    $status = 0
    if (!(Test-Path "$InstallPath/sd-scripts")) {
        $status = 1
    } else {
        $items = Get-ChildItem "$InstallPath/sd-scripts" -Recurse
        if ($items.Count -eq 0) {
            $status = 1
        }
    }

    $path = "$InstallPath/sd-scripts"
    $cache_path = "$Env:CACHE_HOME/sd-scripts_tmp"
    if ($status -eq 1) {
        Print-Msg "正在下载 SD-Trainer-Script"
        # 清理缓存路径
        if (Test-Path "$cache_path") {
            Remove-Item -Path "$cache_path" -Force -Recurse
        }
        git clone --recurse-submodules $SD_TRAINER_SCRIPT_REPO "$cache_path"
        if ($?) { # 检测是否下载成功
            # 清理空文件夹
            if (Test-Path "$path") {
                $random_string = [Guid]::NewGuid().ToString().Substring(0, 18)
                Move-Item -Path "$path" -Destination "$Env:CACHE_HOME/$random_string" -Force
            }
            # 将下载好的文件从缓存文件夹移动到指定路径
            New-Item -ItemType Directory -Path "$([System.IO.Path]::GetDirectoryName($path))" -Force > $null
            Move-Item -Path "$cache_path" -Destination "$path" -Force
            Print-Msg "SD-Trainer-Script 安装成功"
        } else {
            Print-Msg "SD-Trainer-Script 安装失败, 终止 SD-Trainer-Script 安装进程, 可尝试重新运行 SD-Trainer-Script Installer 重试失败的安装"
            Read-Host | Out-Null
            exit 1
        }
    } else {
        Print-Msg "SD-Trainer-Script 已安装"
    }

    Print-Msg "安装 SD-Trainer-Script 子模块中"
    git -C "$InstallPath/sd-scripts" submodule init
    git -C "$InstallPath/sd-scripts" submodule update
    if ($?) {
        Print-Msg "SD-Trainer-Script 子模块安装成功"
    } else {
        Print-Msg "SD-Trainer-Script 子模块安装失败, 终止 SD-Trainer-Script 安装进程, 可尝试重新运行 SD-Trainer-Script Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
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
            Print-Msg "PyTorch 安装失败, 终止 SD-Trainer-Script 安装进程, 可尝试重新运行 SD-Trainer-Script Installer 重试失败的安装"
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
            Print-Msg "xFormers 安装失败, 终止 SD-Trainer-Script 安装进程, 可尝试重新运行 SD-Trainer-Script Installer 重试失败的安装"
            Read-Host | Out-Null
            exit 1
        }
    } else {
        Print-Msg "xFormers 已安装, 无需再次安装"
    }
}


# 安装 SD-Trainer-Script 依赖
function Install-SD-Trainer-Script-Dependence {
    # 记录脚本所在路径
    $current_path = $(Get-Location).ToString()
    Set-Location "$InstallPath/sd-scripts"
    Print-Msg "安装 SD-Trainer-Script 依赖中"
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
        Print-Msg "SD-Trainer-Script 依赖安装成功"
    } else {
        Print-Msg "SD-Trainer-Script 依赖安装失败, 终止 SD-Trainer-Script 安装进程, 可尝试重新运行 SD-Trainer-Script Installer 重试失败的安装"
        Set-Location "$current_path"
        Read-Host | Out-Null
        exit 1
    }
    Set-Location "$current_path"
}


# 安装
function Check-Install {
    New-Item -ItemType Directory -Path "$InstallPath" -Force > $null
    New-Item -ItemType Directory -Path "$Env:CACHE_HOME" -Force > $null

    Print-Msg "检测是否安装 Python"
    if ((Test-Path "$InstallPath/python/python.exe") -or (Test-Path "$InstallPath/sd-scripts/python/python.exe")) {
        Print-Msg "Python 已安装"
    } else {
        Print-Msg "Python 未安装"
        Install-Python
    }

    # 切换 uv 指定的 Python
    if (Test-Path "$InstallPath/sd-scripts/python/python.exe") {
        $Env:UV_PYTHON = "$InstallPath/sd-scripts/python/python.exe"
    }

    Print-Msg "检测是否安装 Git"
    if ((Test-Path "$InstallPath/git/bin/git.exe") -or (Test-Path "$InstallPath/sd-scripts/git/bin/git.exe")) {
        Print-Msg "Git 已安装"
    } else {
        Print-Msg "Git 未安装"
        Install-Git
    }

    Print-Msg "检测是否安装 Aria2"
    if ((Test-Path "$InstallPath/git/bin/aria2c.exe") -or (Test-Path "$InstallPath/sd-scripts/git/bin/aria2c.exe")) {
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
    Install-SD-Trainer-Script
    Install-PyTorch
    Install-SD-Trainer-Script-Dependence

    # 提供初始模板
    if (!(Test-Path "$PSScriptRoot/train.ps1")) {
        $content = "#################################################
# 初始化基础环境变量, 以正确识别到运行环境
& `"`$PSScriptRoot/library.ps1`"
Set-Location `$PSScriptRoot
# 此处的代码不要修改或者删除, 否则可能会出现意外情况
# 
# SD-Trainer-Script 环境初始化后提供以下变量便于使用
# 
# `$ROOT_PATH               当前目录
# `$SD_SCRIPTS_PATH         训练脚本所在目录
# `$DATASET_PATH            数据集目录
# `$MODEL_PATH              模型下载器下载的模型路径
# `$GIT_EXEC                Git 路径
# `$PYTHON_EXEC             Python 解释器路径
# 
# 下方可编写训练代码
# 编写训练命令可参考: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md#%E7%BC%96%E5%86%99%E8%AE%AD%E7%BB%83%E8%84%9A%E6%9C%AC
# 编写结束后, 该文件必须使用 UTF-8 with BOM 编码保存
#################################################





#################################################
Read-Host | Out-Null # 训练结束后保持控制台不被关闭
"
        Set-Content -Encoding UTF8 -Path "$InstallPath/train.ps1" -Value $content
    }

    # 清理缓存
    Print-Msg "清理下载 Python 软件包的缓存中"
    python -m pip cache purge
    uv cache clean

    Set-Content -Encoding UTF8 -Path "$InstallPath/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
}


# 初始化脚本
function Write-Library-Script {
    $content = "
# SD-Trainer-Script Installer 版本和检查更新间隔
`$SD_TRAINER_SCRIPT_INSTALLER_VERSION = $SD_TRAINER_SCRIPT_INSTALLER_VERSION
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
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/git/bin`"
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
    Write-Host `"[SD-Trainer-Script Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# 显示 SD-Trainer-Script Installer 版本
function Get-SD-Trainer-Script-Installer-Version {
    `$ver = `$([string]`$SD_TRAINER_SCRIPT_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"SD-Trainer-Script Installer 版本: v`${major}.`${minor}.`${micro}`"
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


# SD-Trainer-Script Installer 更新检测
function Check-SD-Trainer-Script-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_script_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_script_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 SD-Trainer-Script Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 SD-Trainer-Script Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" | Select-String -Pattern `"SD_TRAINER_SCRIPT_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$SD_TRAINER_SCRIPT_INSTALLER_VERSION) {
                    Print-Msg `"检测到 SD-Trainer-Script Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"==================================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 SD-Trainer-Script Installer 进行更新中`"
                        . `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
                        Print-Msg `"更新结束, 需重新启动 SD-Trainer-Script Installer 管理脚本以应用更新, 回车退出 SD-Trainer-Script Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Print-Msg `"跳过 SD-Trainer-Script Installer 更新`"
                    }
                } else {
                    Print-Msg `"SD-Trainer-Script Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 SD-Trainer-Script Installer 更新中`"
                } else {
                    Print-Msg `"检查 SD-Trainer-Script Installer 更新失败`"
                }
            }
        }
    }
}


# 代理配置
function Set-Proxy {
    `$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    # 检测是否禁用自动设置镜像源
    if (Test-Path `"`$PSScriptRoot/disable_proxy.txt`") {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
        `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
    } elseif (`$internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        `$proxy_addr = `$(`$internet_setting.ProxyServer)
        # 提取代理地址
        if ((`$proxy_addr -match `"http=(.*?);`") -or (`$proxy_addr -match `"https=(.*?);`")) {
            `$proxy_value = `$matches[1]
            # 去除 http / https 前缀
            `$proxy_value = `$proxy_value.ToString().Replace(`"http://`", `"`").Replace(`"https://`", `"`")
            `$proxy_value = `"http://`${proxy_value}`"
        } elseif (`$proxy_addr -match `"socks=(.*)`") {
            `$proxy_value = `$matches[1]
            # 去除 socks 前缀
            `$proxy_value = `$proxy_value.ToString().Replace(`"http://`", `"`").Replace(`"https://`", `"`")
            `$proxy_value = `"socks://`${proxy_value}`"
        } else {
            `$proxy_value = `"http://`${proxy_addr}`"
        }
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
}


# HuggingFace 镜像源
function Set-HuggingFace-Mirror {
    if (Test-Path `"`$PSScriptRoot/disable_hf_mirror.txt`") { # 检测是否禁用了自动设置 HuggingFace 镜像源
        Print-Msg `"检测到本地存在 disable_hf_mirror.txt 镜像源配置文件, 禁用自动设置 HuggingFace 镜像源`"
        return
    }

    if (Test-Path `"`$PSScriptRoot/hf_mirror.txt`") { # 本地存在 HuggingFace 镜像源配置
        `$hf_mirror_value = Get-Content `"`$PSScriptRoot/hf_mirror.txt`"
        `$Env:HF_ENDPOINT = `$hf_mirror_value
        Print-Msg `"检测到本地存在 hf_mirror.txt 配置文件, 已读取该配置并设置 HuggingFace 镜像源`"
    } else { # 使用默认设置
        `$Env:HF_ENDPOINT = `"https://hf-mirror.com`"
        Print-Msg `"使用默认 HuggingFace 镜像源`"
    }
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


function Main {
    Print-Msg `"初始化中`"
    Get-SD-Trainer-Script-Installer-Version
    Set-Proxy
    Check-SD-Trainer-Script-Installer-Update
    Set-HuggingFace-Mirror
    Pip-Mirror-Status
    Fix-PyTorch
    Set-PyTorch-CUDA-Memory-Alloc

    `$Global:ROOT_PATH = `$PSScriptRoot
    `$Global:SD_SCRIPTS_PATH = [System.IO.Path]::GetFullPath(`"`$ROOT_PATH/sd-scripts`")
    `$Global:DATASET_PATH = [System.IO.Path]::GetFullPath(`"`$ROOT_PATH/datasets`")
    `$Global:MODEL_PATH = [System.IO.Path]::GetFullPath(`"`$ROOT_PATH/models`")
    `$Global:OUTPUT_PATH = [System.IO.Path]::GetFullPath(`"`$ROOT_PATH/outputs`")
    `$Global:GIT_EXEC = [System.IO.Path]::GetFullPath(`$(Get-Command git).Source)
    `$Global:PYTHON_EXEC = [System.IO.Path]::GetFullPath(`$(Get-Command python).Source)

    Print-Msg `"可用的预设变量`"
    Print-Msg `"ROOT_PATH: `$ROOT_PATH`"
    Print-Msg `"SD_SCRIPTS_PATH: `$SD_SCRIPTS_PATH`"
    Print-Msg `"DATASET_PATH: `$DATASET_PATH`"
    Print-Msg `"MODEL_PATH: `$MODEL_PATH`"
    Print-Msg `"OUTPUT_PATH: `$OUTPUT_PATH`"
    Print-Msg `"GIT_EXEC: `$GIT_EXEC`"
    Print-Msg `"PYTHON_EXEC: `$PYTHON_EXEC`"
    Print-Msg `"初始化环境完成`"
}

###################

Main
"

    if (Test-Path "$InstallPath/library.ps1") {
        Print-Msg "更新 library.ps1 中"
    } else {
        Print-Msg "生成 library.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$InstallPath/library.ps1" -Value $content
}


# 更新脚本
function Write-Update-Script {
    $content = "
# SD-Trainer-Script Installer 版本和检查更新间隔
`$SD_TRAINER_SCRIPT_INSTALLER_VERSION = $SD_TRAINER_SCRIPT_INSTALLER_VERSION
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
`$PIP_EXTRA_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `"`$PIP_EXTRA_INDEX_ADDR_ORI `$PIP_EXTRA_INDEX_ADDR`" } else { `$PIP_EXTRA_INDEX_ADDR_ORI }
`$PIP_FIND_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_FIND_ADDR } else { `$PIP_FIND_ADDR_ORI }
# `$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
# Github 镜像源
`$GITHUB_MIRROR_LIST = @(
    `"https://ghgo.xyz/https://github.com`",
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
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/git/bin`"
`$Env:PATH = `"`$PYTHON_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$GIT_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
# 环境变量
`$Env:PIP_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
`$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR`"
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
`$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR`"
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
    Write-Host `"[SD-Trainer-Script Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# 显示 SD-Trainer-Script Installer 版本
function Get-SD-Trainer-Script-Installer-Version {
    `$ver = `$([string]`$SD_TRAINER_SCRIPT_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"SD-Trainer-Script Installer 版本: v`${major}.`${minor}.`${micro}`"
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


# SD-Trainer-Script Installer 更新检测
function Check-SD-Trainer-Script-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_script_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_script_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 SD-Trainer-Script Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 SD-Trainer-Script Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" | Select-String -Pattern `"SD_TRAINER_SCRIPT_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$SD_TRAINER_SCRIPT_INSTALLER_VERSION) {
                    Print-Msg `"检测到 SD-Trainer-Script Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"==================================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 SD-Trainer-Script Installer 进行更新中`"
                        . `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
                        Print-Msg `"更新结束, 需重新启动 SD-Trainer-Script Installer 管理脚本以应用更新, 回车退出 SD-Trainer-Script Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Print-Msg `"跳过 SD-Trainer-Script Installer 更新`"
                    }
                } else {
                    Print-Msg `"SD-Trainer-Script Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 SD-Trainer-Script Installer 更新中`"
                } else {
                    Print-Msg `"检查 SD-Trainer-Script Installer 更新失败`"
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
        if (Test-Path `"`$PSScriptRoot/sd-scripts/python/python.exe`") {
            `$Env:UV_PYTHON = `"`$PSScriptRoot/sd-scripts/python/python.exe`"
        }
        `$Global:USE_UV = `$true
        Check-uv-Version
    }
}


# 代理配置
function Set-Proxy {
    `$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    # 检测是否禁用自动设置镜像源
    if (Test-Path `"`$PSScriptRoot/disable_proxy.txt`") {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
        `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
    } elseif (`$internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        `$proxy_addr = `$(`$internet_setting.ProxyServer)
        # 提取代理地址
        if ((`$proxy_addr -match `"http=(.*?);`") -or (`$proxy_addr -match `"https=(.*?);`")) {
            `$proxy_value = `$matches[1]
            # 去除 http / https 前缀
            `$proxy_value = `$proxy_value.ToString().Replace(`"http://`", `"`").Replace(`"https://`", `"`")
            `$proxy_value = `"http://`${proxy_value}`"
        } elseif (`$proxy_addr -match `"socks=(.*)`") {
            `$proxy_value = `$matches[1]
            # 去除 socks 前缀
            `$proxy_value = `$proxy_value.ToString().Replace(`"http://`", `"`").Replace(`"https://`", `"`")
            `$proxy_value = `"socks://`${proxy_value}`"
        } else {
            `$proxy_value = `"http://`${proxy_addr}`"
        }
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
}


# Github 镜像源
function Set-Github-Mirror {
    `$Env:GIT_CONFIG_GLOBAL = `"`$PSScriptRoot/.gitconfig`" # 设置 Git 配置文件路径
    if (Test-Path `"`$PSScriptRoot/.gitconfig`") {
        Remove-Item -Path `"`$PSScriptRoot/.gitconfig`" -Force -Recurse
    }

    # 默认 Git 配置
    git config --global --add safe.directory `"*`"
    git config --global core.longpaths true

    if (Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") { # 禁用 Github 镜像源
        Print-Msg `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件, 禁用 Github 镜像源`"
        return
    }

    if (Test-Path `"`$PSScriptRoot/gh_mirror.txt`") { # 使用自定义 Github 镜像源
        `$github_mirror = Get-Content `"`$PSScriptRoot/gh_mirror.txt`"
        git config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
        Print-Msg `"检测到本地存在 gh_mirror.txt Github 镜像源配置文件, 已读取 Github 镜像源配置文件并设置 Github 镜像源`"
        return
    }

    # 自动检测可用镜像源并使用
    `$status = 0
    ForEach(`$i in `$GITHUB_MIRROR_LIST) {
        Print-Msg `"测试 Github 镜像源: `$i`"
        if (Test-Path `"`$Env:CACHE_HOME/github-mirror-test`") {
            Remove-Item -Path `"`$Env:CACHE_HOME/github-mirror-test`" -Force -Recurse
        }
        git clone `$i/licyk/empty `"`$Env:CACHE_HOME/github-mirror-test`" --quiet
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
    } else {
        Print-Msg `"设置 Github 镜像源`"
        git config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
    }
}


function Main {
    Print-Msg `"初始化中`"
    Get-SD-Trainer-Script-Installer-Version
    Set-Proxy
    Check-SD-Trainer-Script-Installer-Update
    Set-uv
    Set-Github-Mirror
    Pip-Mirror-Status

    if (!(Test-Path `"`$PSScriptRoot/sd-scripts`")) {
        Print-Msg `"在 `$PSScriptRoot 路径中未找到 sd-scripts 文件夹, 请检查 SD-Trainer-Script 是否已正确安装, 或者尝试运行 SD-Trainer-Script Installer 进行修复`"
        return
    }

    # 记录上次的路径
    `$current_path = `$(Get-Location).ToString()

    `$update_fail = 0
    Print-Msg `"拉取 SD-Trainer-Script 更新内容中`"
    Fix-Git-Point-Off-Set `"`$PSScriptRoot/sd-scripts`"
    `$core_origin_ver = `$(git -C `"`$PSScriptRoot/sd-scripts`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")
    `$branch = `$(git -C `"`$PSScriptRoot/sd-scripts`" symbolic-ref --quiet HEAD 2> `$null).split(`"/`")[2]
    git -C `"`$PSScriptRoot/sd-scripts`" fetch --recurse-submodules
    if (`$?) {
        Print-Msg `"应用 SD-Trainer-Script 更新中`"
        `$commit_hash = `$(git -C `"`$PSScriptRoot/sd-scripts`" log origin/`$branch --max-count 1 --format=`"%h`")
        git -C `"`$PSScriptRoot/sd-scripts`" reset --hard `$commit_hash --recurse-submodules
        `$core_latest_ver = `$(git -C `"`$PSScriptRoot/sd-scripts`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")
        
        if (`$core_origin_ver -eq `$core_latest_ver) {
            Print-Msg `"SD-Trainer-Script 已为最新版`"
            `$core_update_msg = `"已为最新版, 当前版本：`$core_origin_ver`"
        } else {
            Print-Msg `"SD-Trainer-Script 更新成功`"
            `$core_update_msg = `"更新成功, 版本：`$core_origin_ver -> `$core_latest_ver`"
        }

        Print-Msg `"更新 SD-Trainer-Script 依赖中`"
        Set-Location `"`$PSScriptRoot/sd-scripts`"
        if (`$USE_UV) {
            uv pip install -r requirements.txt `$(Get-PyTorch-Version).ToString().Split() --upgrade
            if (!(`$?)) {
                Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
                python -m pip install -r requirements.txt --upgrade
            }
        } else {
            python -m pip install -r requirements.txt --upgrade
        }
        if (`$?) {
            Print-Msg `"SD-Trainer-Script 依赖更新成功`"
            `$req_update_msg = `"更新成功`"
        } else {
            Print-Msg `"SD-Trainer-Script 依赖更新失败`"
            `$req_update_msg = `"更新失败`"
            `$update_fail = 1
        }

        Set-Location `"`$current_path`"
    } else {
        Print-Msg `"拉取 SD-Trainer-Script 更新内容失败`"
        `$core_update_msg = `"拉取 SD-Trainer-Script 更新内容失败, 无法进行更新`"
        `$req_update_msg = `"因 SD-Trainer-Script 组件更新失败, 不进行更新`"
        `$update_fail = 1
    }

    Print-Msg `"==================================================================`"
    Print-Msg `"SD-Trainer-Script 更新结果：`"
    Print-Msg `"SD-Trainer-Script 组件: `$core_update_msg`"
    Print-Msg `"SD-Trainer-Script 依赖: `$req_update_msg`"
    Print-Msg `"==================================================================`"
    if (`$update_fail -eq 0) {
        Print-Msg `"SD-Trainer-Script 更新成功`"
    } else {
        Print-Msg `"SD-Trainer-Script 更新失败, 请检查控制台日志。可尝试重新运行 SD-Trainer-Script 更新脚本进行重试`"
    }

    Print-Msg `"退出 SD-Trainer-Script 更新脚本`"
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$InstallPath/update.ps1") {
        Print-Msg "更新 update.ps1 中"
    } else {
        Print-Msg "生成 update.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$InstallPath/update.ps1" -Value $content
}


# 分支切换脚本
function Write-Switch-Branch-Script {
    $content = "
# SD-Trainer-Script Installer 版本和检查更新间隔
`$SD_TRAINER_SCRIPT_INSTALLER_VERSION = $SD_TRAINER_SCRIPT_INSTALLER_VERSION
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
    `"https://ghgo.xyz/https://github.com`",
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
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/git/bin`"
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
    Write-Host `"[SD-Trainer-Script Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# 显示 SD-Trainer-Script Installer 版本
function Get-SD-Trainer-Script-Installer-Version {
    `$ver = `$([string]`$SD_TRAINER_SCRIPT_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"SD-Trainer-Script Installer 版本: v`${major}.`${minor}.`${micro}`"
}


# Pip 镜像源状态
function Pip-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 Pip 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pip_mirror.txt 配置文件, 已将 Pip 源切换至官方源`"
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


# SD-Trainer-Script Installer 更新检测
function Check-SD-Trainer-Script-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_script_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_script_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 SD-Trainer-Script Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 SD-Trainer-Script Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" | Select-String -Pattern `"SD_TRAINER_SCRIPT_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$SD_TRAINER_SCRIPT_INSTALLER_VERSION) {
                    Print-Msg `"检测到 SD-Trainer-Script Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"==================================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 SD-Trainer-Script Installer 进行更新中`"
                        . `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
                        Print-Msg `"更新结束, 需重新启动 SD-Trainer-Script Installer 管理脚本以应用更新, 回车退出 SD-Trainer-Script Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Print-Msg `"跳过 SD-Trainer-Script Installer 更新`"
                    }
                } else {
                    Print-Msg `"SD-Trainer-Script Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 SD-Trainer-Script Installer 更新中`"
                } else {
                    Print-Msg `"检查 SD-Trainer-Script Installer 更新失败`"
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
        if (Test-Path `"`$PSScriptRoot/sd-scripts/python/python.exe`") {
            `$Env:UV_PYTHON = `"`$PSScriptRoot/sd-scripts/python/python.exe`"
        }
        `$Global:USE_UV = `$true
        Check-uv-Version
    }
}


# 代理配置
function Set-Proxy {
    `$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    # 检测是否禁用自动设置镜像源
    if (Test-Path `"`$PSScriptRoot/disable_proxy.txt`") {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
        `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
    } elseif (`$internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        `$proxy_addr = `$(`$internet_setting.ProxyServer)
        # 提取代理地址
        if ((`$proxy_addr -match `"http=(.*?);`") -or (`$proxy_addr -match `"https=(.*?);`")) {
            `$proxy_value = `$matches[1]
            # 去除 http / https 前缀
            `$proxy_value = `$proxy_value.ToString().Replace(`"http://`", `"`").Replace(`"https://`", `"`")
            `$proxy_value = `"http://`${proxy_value}`"
        } elseif (`$proxy_addr -match `"socks=(.*)`") {
            `$proxy_value = `$matches[1]
            # 去除 socks 前缀
            `$proxy_value = `$proxy_value.ToString().Replace(`"http://`", `"`").Replace(`"https://`", `"`")
            `$proxy_value = `"socks://`${proxy_value}`"
        } else {
            `$proxy_value = `"http://`${proxy_addr}`"
        }
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
}


# Github 镜像源
function Set-Github-Mirror {
    `$Env:GIT_CONFIG_GLOBAL = `"`$PSScriptRoot/.gitconfig`" # 设置 Git 配置文件路径
    if (Test-Path `"`$PSScriptRoot/.gitconfig`") {
        Remove-Item -Path `"`$PSScriptRoot/.gitconfig`" -Force -Recurse
    }

    # 默认 Git 配置
    git config --global --add safe.directory `"*`"
    git config --global core.longpaths true

    if (Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") { # 禁用 Github 镜像源
        Print-Msg `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件, 禁用 Github 镜像源`"
        return
    }

    if (Test-Path `"`$PSScriptRoot/gh_mirror.txt`") { # 使用自定义 Github 镜像源
        `$github_mirror = Get-Content `"`$PSScriptRoot/gh_mirror.txt`"
        git config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
        Print-Msg `"检测到本地存在 gh_mirror.txt Github 镜像源配置文件, 已读取 Github 镜像源配置文件并设置 Github 镜像源`"
        return
    }

    # 自动检测可用镜像源并使用
    `$status = 0
    ForEach(`$i in `$GITHUB_MIRROR_LIST) {
        Print-Msg `"测试 Github 镜像源: `$i`"
        if (Test-Path `"`$Env:CACHE_HOME/github-mirror-test`") {
            Remove-Item -Path `"`$Env:CACHE_HOME/github-mirror-test`" -Force -Recurse
        }
        git clone `$i/licyk/empty `"`$Env:CACHE_HOME/github-mirror-test`" --quiet
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
    } else {
        Print-Msg `"设置 Github 镜像源`"
        git config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
    }
}


# 获取 SD-Trainer-Script 分支
function Get-SD-Trainer-Script-Branch {
    `$remote = `$(git -C `"`$PSScriptRoot/sd-scripts`" remote get-url origin)
    `$ref = `$(git -C `"`$PSScriptRoot/sd-scripts`" symbolic-ref --quiet HEAD 2> `$null)
    if (`$ref -eq `$null) {
        `$ref = `$(git -C `"`$PSScriptRoot/sd-scripts`" show -s --format=`"%h`")
    }

    return `"`$(`$remote.Split(`"/`")[-2])/`$(`$remote.Split(`"/`")[-1]) `$([System.IO.Path]::GetFileName(`$ref))`"
}


# 切换 SD-Trainer-Script 分支
function Switch-SD-Trainer-Script-Branch (`$remote, `$branch, `$use_submod) {
    `$sd_trainer_script_path = `"`$PSScriptRoot/sd-scripts`"
    `$preview_url = `$(git -C `"`$sd_trainer_script_path`" remote get-url origin)

    Set-Github-Mirror # 设置 Github 镜像源

    if (`$use_submod) {
        `$use_submodules = `"--recurse-submodules`"
    } else {
        `$use_submodules = `"`"
    }

    Print-Msg `"SD-Trainer-Script 远程源替换: `$preview_url -> `$remote`"
    git -C `"`$sd_trainer_script_path`" remote set-url origin `"`$remote`" # 替换远程源

    # 处理 Git 子模块
    if (`$use_submod) {
        Print-Msg `"更新 SD-Trainer-Script 的 Git 子模块信息`"
        git -C `"`$sd_trainer_script_path`" submodule update --init --recursive
    } else {
        Print-Msg `"禁用 SD-Trainer-Script 的 Git 子模块`"
        git -C `"`$sd_trainer_script_path`" submodule deinit --all -f
    }

    Print-Msg `"拉取 SD-Trainer-Script 远程源更新`"
    git -C `"`$sd_trainer_script_path`" fetch # 拉取远程源内容
    if (`$?) {
        if (`$use_submod) {
            Print-Msg `"清理原有的 Git 子模块`"
            git -C `"`$sd_trainer_script_path`" submodule deinit --all -f
        }
        Print-Msg `"切换 SD-Trainer-Script 分支至 `$branch`"
        git -C `"`$sd_trainer_script_path`" checkout `"`${branch}`" --force # 切换分支
        Print-Msg `"应用 SD-Trainer-Script 远程源的更新`"
        if (`$use_submod) {
            Print-Msg `"更新 SD-Trainer-Script 的 Git 子模块信息`"
            git -C `"`$sd_trainer_script_path`" reset --hard `"origin/`$branch`"
            git -C `"`$sd_trainer_script_path`" submodule deinit --all -f
            git -C `"`$sd_trainer_script_path`" submodule update --init --recursive
        }
        git -C `"`$sd_trainer_script_path`" reset `$use_submodules.ToString() --hard `"origin/`$branch`" # 切换到最新的提交内容上
        Print-Msg `"切换 SD-Trainer-Script 分支成功`"
    } else {
        Print-Msg `"拉取 SD-Trainer-Script 远程源更新失败, 取消分支切换`"
        Print-Msg `"尝试回退 SD-Trainer-Script 的更改`"
        git -C `"`$sd_trainer_script_path`" remote set-url origin `"`$preview_url`"
        if (`$use_submod) {
            git -C `"`$sd_trainer_script_path`" submodule deinit --all -f
        } else {
            git -C `"`$sd_trainer_script_path`" submodule update --init --recursive
        }
        Print-Msg `"回退 SD-Trainer-Script 分支更改完成`"
        Print-Msg `"切换 SD-Trainer-Script 分支更改失败, 可尝试重新运行 SD-Trainer-Script 分支切换脚本`"
    }
}


function Main {
    Print-Msg `"初始化中`"
    Get-SD-Trainer-Script-Installer-Version
    Set-Proxy
    Check-SD-Trainer-Script-Installer-Update
    Set-uv
    Pip-Mirror-Status

    if (!(Test-Path `"`$PSScriptRoot/sd-scripts`")) {
        Print-Msg `"在 `$PSScriptRoot 路径中未找到 sd-scripts 文件夹, 请检查 SD-Trainer-Script 是否已正确安装, 或者尝试运行 SD-Trainer-Script Installer 进行修复`"
        return
    }

    `$content = `"
-----------------------------------------------------
- 1、kohya-ss - sd-scripts 主分支
- 2、kohya-ss - sd-scripts 测试分支
- 3、bghira - SimpleTuner 分支
- 4、ostris - ai-toolkit 分支
- 5、a-r-r-o-w - finetrainers 分支
- 6、tdrussell - diffusion-pipe 分支
- 7、kohya-ss - musubi-tuner 分支
-----------------------------------------------------
`"

    `$to_exit = 0

    while (`$True) {
        Print-Msg `"SD-Trainer-Script 分支列表`"
        `$go_to = 0
        Write-Host `$content
        Print-Msg `"当前 SD-Trainer-Script 分支: `$(Get-SD-Trainer-Script-Branch)`"
        Print-Msg `"请选择 SD-Trainer-Script 分支`"
        Print-Msg `"提示:`"
        Print-Msg `"1. 输入数字后回车, 或者输入 exit 退出 SD-Trainer-Script 分支切换脚本`"
        Print-Msg `"2. 切换分支后, 需要更新依赖, 可通过运行 update.ps1 进行依赖更新`"
        `$arg = Read-Host `"==================================================>`"

        switch (`$arg) {
            1 {
                `$remote = `"https://github.com/kohya-ss/sd-scripts`"
                `$branch = `"main`"
                `$branch_name = `"kohya-ss - sd-scripts 主分支`"
                `$use_submod = `$false
                `$go_to = 1
            }
            2 {
                `$remote = `"https://github.com/kohya-ss/sd-scripts`"
                `$branch = `"dev`"
                `$branch_name = `"kohya-ss - sd-scripts 测试分支`"
                `$use_submod = `$false
                `$go_to = 1
            }
            3 {
                `$remote = `"https://github.com/bghira/SimpleTuner`"
                `$branch = `"master`"
                `$branch_name = `"bghira - SimpleTuner 分支`"
                `$use_submod = `$false
                `$go_to = 1
            }
            4 {
                `$remote = `"https://github.com/ostris/ai-toolkit`"
                `$branch = `"master`"
                `$branch_name = `"ostris - ai-toolkit 分支`"
                `$use_submod = `$true
                `$go_to = 1
            }
            5 {
                `$remote = `"https://github.com/a-r-r-o-w/finetrainers`"
                `$branch = `"master`"
                `$branch_name = `"a-r-r-o-w - finetrainers 分支`"
                `$use_submod = `$false
                `$go_to = 1
            }
            6 {
                `$remote = `"https://github.com/tdrussell/diffusion-pipe`"
                `$branch = `"master`"
                `$branch_name = `"tdrussell - diffusion-pipe 分支`"
                `$use_submod = `$true
                `$go_to = 1
            }
            7 {
                `$remote = `"https://github.com/kohya-ss/musubi-tuner`"
                `$branch = `"master`"
                `$branch_name = `"kohya-ss - musubi-tuner 分支`"
                `$use_submod = `$false
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

    Print-Msg `"是否切换 SD-Trainer-Script 分支到 `$branch_name ?`"
    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
    `$operate = Read-Host `"==================================================>`"

    if (`$operate -eq `"yes`" -or `$operate -eq `"y`" -or `$operate -eq `"YES`" -or `$operate -eq `"Y`") {
        Print-Msg `"开始切换 SD-Trainer-Script 分支`"
        Switch-SD-Trainer-Script-Branch `$remote `$branch `$use_submod
    } else {
        Print-Msg `"取消切换 SD-Trainer-Script 分支`"
    }
    Print-Msg `"退出 SD-Trainer-Script 分支切换脚本`"
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$InstallPath/switch_branch.ps1") {
        Print-Msg "更新 switch_branch.ps1 中"
    } else {
        Print-Msg "生成 switch_branch.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$InstallPath/switch_branch.ps1" -Value $content
}


# 获取安装脚本
function Write-Launch-SD-Trainer-Script-Install-Script {
    $content = "
`$SD_TRAINER_SCRIPT_INSTALLER_VERSION = $SD_TRAINER_SCRIPT_INSTALLER_VERSION



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[SD-Trainer-Script Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# 显示 SD-Trainer-Script Installer 版本
function Get-SD-Trainer-Script-Installer-Version {
    `$ver = `$([string]`$SD_TRAINER_SCRIPT_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"SD-Trainer-Script Installer 版本: v`${major}.`${minor}.`${micro}`"
}


# 代理配置
function Set-Proxy {
    `$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    # 检测是否禁用自动设置镜像源
    if (Test-Path `"`$PSScriptRoot/disable_proxy.txt`") {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
        `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
    } elseif (`$internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        `$proxy_addr = `$(`$internet_setting.ProxyServer)
        # 提取代理地址
        if ((`$proxy_addr -match `"http=(.*?);`") -or (`$proxy_addr -match `"https=(.*?);`")) {
            `$proxy_value = `$matches[1]
            # 去除 http / https 前缀
            `$proxy_value = `$proxy_value.ToString().Replace(`"http://`", `"`").Replace(`"https://`", `"`")
            `$proxy_value = `"http://`${proxy_value}`"
        } elseif (`$proxy_addr -match `"socks=(.*)`") {
            `$proxy_value = `$matches[1]
            # 去除 socks 前缀
            `$proxy_value = `$proxy_value.ToString().Replace(`"http://`", `"`").Replace(`"https://`", `"`")
            `$proxy_value = `"socks://`${proxy_value}`"
        } else {
            `$proxy_value = `"http://`${proxy_addr}`"
        }
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
}


# 下载 SD-Trainer-Script Installer
function Download-SD-Trainer-Script-Installer {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_script_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_script_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    ForEach (`$url in `$urls) {
        Print-Msg `"正在下载最新的 SD-Trainer-Script Installer 脚本`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/sd_trainer_script_installer.ps1`"
        if (`$?) {
            Print-Msg `"下载 SD-Trainer-Script Installer 脚本成功`"
            break
        } else {
            Print-Msg `"下载 SD-Trainer-Script Installer 脚本失败`"
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试下载 SD-Trainer-Script Installer 脚本`"
            } else {
                Print-Msg `"下载 SD-Trainer-Script Installer 脚本失败, 可尝试重新运行 SD-Trainer-Script Installer 下载脚本`"
                return `$false
            }
        }
    }
    return `$true
}


# 获取本地配置文件参数
function Get-Local-Setting {
    `$arg = @{}
    if (Test-Path `"`$PSScriptRoot/disable_pip_mirror.txt`") {
        `$arg.Add(`"-DisablePipMirror`", `$true)
    }

    if (Test-Path `"`$PSScriptRoot/disable_proxy.txt`") {
        `$arg.Add(`"-DisableProxy`", `$true)
    } else {
        if (Test-Path `"`$PSScriptRoot/proxy.txt`") {
            `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
            `$arg.Add(`"-UseCustomProxy`", `$proxy_value)
        }
    }

    if (Test-Path `"`$PSScriptRoot/disable_uv.txt`") {
        `$arg.Add(`"-DisableUV`", `$true)
    }

    if (Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") {
        `$arg.Add(`"-DisableGithubMirror`", `$true)
    } else {
        if (Test-Path `"`$PSScriptRoot/gh_mirror.txt`") {
            `$github_mirror = Get-Content `"`$PSScriptRoot/gh_mirror.txt`"
            `$arg.Add(`"-UseCustomGithubMirror`", `$github_mirror)
        }
    }

    if (Test-Path `"`$PSScriptRoot/install_sd_trainer_script.txt`") {
        `$arg.Add(`"-InstallBranch`", `"sd_trainer_script`")
    } elseif (Test-Path `"`$PSScriptRoot/install_kohya_gui.txt`") {
        `$arg.Add(`"-InstallBranch`", `"kohya_gui`")
    }

    return `$arg
}


function Main {
    Print-Msg `"初始化中`"
    Get-SD-Trainer-Script-Installer-Version
    Set-Proxy

    `$status = Download-SD-Trainer-Script-Installer
    if (`$status) {
        Print-Msg `"运行 SD-Trainer-Script Installer 中`"
        `$arg = Get-Local-Setting
        . `"`$PSScriptRoot/cache/sd_trainer_script_installer.ps1`" -InstallPath `"`$PSScriptRoot`" @arg
    } else {
        Read-Host | Out-Null
    }
}

###################

Main
"

    if (Test-Path "$InstallPath/launch_sd_trainer_script_installer.ps1") {
        Print-Msg "更新 launch_sd_trainer_script_installer.ps1 中"
    } else {
        Print-Msg "生成 launch_sd_trainer_script_installer.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$InstallPath/launch_sd_trainer_script_installer.ps1" -Value $content
}


# 重装 PyTorch 脚本
function Write-PyTorch-ReInstall-Script {
    $content = "
# SD-Trainer-Script Installer 版本和检查更新间隔
`$SD_TRAINER_SCRIPT_INSTALLER_VERSION = $SD_TRAINER_SCRIPT_INSTALLER_VERSION
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
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/git/bin`"
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
    Write-Host `"[SD-Trainer-Script Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# 显示 SD-Trainer-Script Installer 版本
function Get-SD-Trainer-Script-Installer-Version {
    `$ver = `$([string]`$SD_TRAINER_SCRIPT_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"SD-Trainer-Script Installer 版本: v`${major}.`${minor}.`${micro}`"
}


# Pip 镜像源状态
function Pip-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 Pip 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pip_mirror.txt 配置文件, 已将 Pip 源切换至官方源`"
    }
}


# SD-Trainer-Script Installer 更新检测
function Check-SD-Trainer-Script-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_script_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_script_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 SD-Trainer-Script Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 SD-Trainer-Script Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" | Select-String -Pattern `"SD_TRAINER_SCRIPT_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$SD_TRAINER_SCRIPT_INSTALLER_VERSION) {
                    Print-Msg `"检测到 SD-Trainer-Script Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"==================================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 SD-Trainer-Script Installer 进行更新中`"
                        . `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
                        Print-Msg `"更新结束, 需重新启动 SD-Trainer-Script Installer 管理脚本以应用更新, 回车退出 SD-Trainer-Script Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Print-Msg `"跳过 SD-Trainer-Script Installer 更新`"
                    }
                } else {
                    Print-Msg `"SD-Trainer-Script Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 SD-Trainer-Script Installer 更新中`"
                } else {
                    Print-Msg `"检查 SD-Trainer-Script Installer 更新失败`"
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
        if (Test-Path `"`$PSScriptRoot/sd-scripts/python/python.exe`") {
            `$Env:UV_PYTHON = `"`$PSScriptRoot/sd-scripts/python/python.exe`"
        }
        `$Global:USE_UV = `$true
        Check-uv-Version
    }
}


# 代理配置
function Set-Proxy {
    `$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    # 检测是否禁用自动设置镜像源
    if (Test-Path `"`$PSScriptRoot/disable_proxy.txt`") {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
        `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
    } elseif (`$internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        `$proxy_addr = `$(`$internet_setting.ProxyServer)
        # 提取代理地址
        if ((`$proxy_addr -match `"http=(.*?);`") -or (`$proxy_addr -match `"https=(.*?);`")) {
            `$proxy_value = `$matches[1]
            # 去除 http / https 前缀
            `$proxy_value = `$proxy_value.ToString().Replace(`"http://`", `"`").Replace(`"https://`", `"`")
            `$proxy_value = `"http://`${proxy_value}`"
        } elseif (`$proxy_addr -match `"socks=(.*)`") {
            `$proxy_value = `$matches[1]
            # 去除 socks 前缀
            `$proxy_value = `$proxy_value.ToString().Replace(`"http://`", `"`").Replace(`"https://`", `"`")
            `$proxy_value = `"socks://`${proxy_value}`"
        } else {
            `$proxy_value = `"http://`${proxy_addr}`"
        }
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
}


# 获取 xFormers 版本
function Get-xFormers-Version {
    `$content = `"
from importlib.metadata import version

try:
    ver = version('xformers')
except:
    ver = None

print(ver)
`"
    `$status = `$(python -c `"`$content`")
    return `$status
}


function Main {
    Print-Msg `"初始化中`"
    Get-SD-Trainer-Script-Installer-Version
    Set-Proxy
    Check-SD-Trainer-Script-Installer-Update
    Set-uv
    Pip-Mirror-Status

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
        `$arg = Read-Host `"==================================================>`"

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
    `$use_force_reinstall = Read-Host `"==================================================>`"

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
    `$install_torch = Read-Host `"==================================================>`"

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

        if (`$xformers_ver -ne `"`") {
            Print-Msg `"重装 xFormers 中`"
            if (`$USE_UV) {
                `$current_xf_ver = Get-xFormers-Version
                if (`$xformers_ver.Split(`"=`")[-1] -ne `$current_xf_ver) {
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

    if (Test-Path "$InstallPath/reinstall_pytorch.ps1") {
        Print-Msg "更新 reinstall_pytorch.ps1 中"
    } else {
        Print-Msg "生成 reinstall_pytorch.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$InstallPath/reinstall_pytorch.ps1" -Value $content
}


# 模型下载脚本
function Write-Download-Model-Script {
    $content = "
# SD-Trainer-Script Installer 版本和检查更新间隔
`$SD_TRAINER_SCRIPT_INSTALLER_VERSION = $SD_TRAINER_SCRIPT_INSTALLER_VERSION
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
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/git/bin`"
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
    Write-Host `"[SD-Trainer-Script Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# 显示 SD-Trainer-Script Installer 版本
function Get-SD-Trainer-Script-Installer-Version {
    `$ver = `$([string]`$SD_TRAINER_SCRIPT_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"SD-Trainer-Script Installer 版本: v`${major}.`${minor}.`${micro}`"
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
    # 检测是否禁用自动设置镜像源
    if (Test-Path `"`$PSScriptRoot/disable_proxy.txt`") {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
        `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
    } elseif (`$internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        `$proxy_addr = `$(`$internet_setting.ProxyServer)
        # 提取代理地址
        if ((`$proxy_addr -match `"http=(.*?);`") -or (`$proxy_addr -match `"https=(.*?);`")) {
            `$proxy_value = `$matches[1]
            # 去除 http / https 前缀
            `$proxy_value = `$proxy_value.ToString().Replace(`"http://`", `"`").Replace(`"https://`", `"`")
            `$proxy_value = `"http://`${proxy_value}`"
        } elseif (`$proxy_addr -match `"socks=(.*)`") {
            `$proxy_value = `$matches[1]
            # 去除 socks 前缀
            `$proxy_value = `$proxy_value.ToString().Replace(`"http://`", `"`").Replace(`"https://`", `"`")
            `$proxy_value = `"socks://`${proxy_value}`"
        } else {
            `$proxy_value = `"http://`${proxy_addr}`"
        }
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
}


# SD-Trainer-Script Installer 更新检测
function Check-SD-Trainer-Script-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_script_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_script_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 SD-Trainer-Script Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 SD-Trainer-Script Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" | Select-String -Pattern `"SD_TRAINER_SCRIPT_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$SD_TRAINER_SCRIPT_INSTALLER_VERSION) {
                    Print-Msg `"检测到 SD-Trainer-Script Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"==================================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 SD-Trainer-Script Installer 进行更新中`"
                        . `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
                        Print-Msg `"更新结束, 需重新启动 SD-Trainer-Script Installer 管理脚本以应用更新, 回车退出 SD-Trainer-Script Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Print-Msg `"跳过 SD-Trainer-Script Installer 更新`"
                    }
                } else {
                    Print-Msg `"SD-Trainer-Script Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 SD-Trainer-Script Installer 更新中`"
                } else {
                    Print-Msg `"检查 SD-Trainer-Script Installer 更新失败`"
                }
            }
        }
    }
}


# 模型列表
function Get-Model-List {
    `$model_list = New-Object System.Collections.ArrayList

    # >>>>>>>>>> Start
    # SD 1.5
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/v1-5-pruned-emaonly.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/animefull-final-pruned.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    # SD 2.1
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_2.1/v2-1_768-ema-pruned.safetensors`", `"SD 2.1`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_2.1/wd-1-4-anime_e2.ckpt`", `"SD 2.1`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_2.1/wd-mofu-fp16.safetensors`", `"SD 2.1`", `"checkpoints`")) | Out-Null
    # SDXL
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/sd_xl_base_1.0_0.9vae.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/sd_xl_refiner_1.0_0.9vae.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/sd_xl_turbo_1.0_fp16.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/animagine-xl-3.0-base.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/animagine-xl-3.0.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/animagine-xl-3.1.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/holodayo-xl-2.1.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kivotos-xl-2.0.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/clandestine-xl-1.0.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/UrangDiffusion-1.1.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/RaeDiffusion-XL-v2.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/sd_xl_anime_V52.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohaku-xl-delta-rev1.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohakuXLEpsilon_rev1.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohaku-xl-epsilon-rev2.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohaku-xl-epsilon-rev3.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohaku-xl-zeta.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/starryXLV52_v52.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/heartOfAppleXL_v20.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/heartOfAppleXL_v30.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/baxlBartstylexlBlueArchiveFlatCelluloid_xlv1.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/baxlBlueArchiveFlatCelluloidStyle_xlv3.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/sanaexlAnimeV10_v10.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/sanaexlAnimeV10_v11.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/SanaeXL-Anime-v1.2-aesthetic.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/SanaeXL-Anime-v1.3-aesthetic.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/Illustrious-XL-v0.1.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/Illustrious-XL-v0.1-GUIDED.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/jruTheJourneyRemains_v25XL.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/PVCStyleModelMovable_illustriousxl10.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/waiNSFWIllustrious_v80.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/tIllunai3_v4.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_earlyAccessVersion.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_epsilonPred05Version.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_epsilonPred075.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_epsilonPred077.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_epsilonPred10Version.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_epsilonPred11Version.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_vPredTestVersion.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_vPred05Version.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_vPred06Version.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_vPred065SVersion.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_vPred075SVersion.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_vPred09RVersion.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_vPred10Version.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/PVCStyleModelMovable_nbxl12.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/PVCStyleModelMovable_nbxlVPredV10.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/ponyDiffusionV6XL_v6.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/pdForAnime_v20.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/tPonynai3_v51WeightOptimized.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/omegaPonyXLAnime_v20.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/animeIllustDiffusion_v061.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/artiwaifuDiffusion_v10.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/artiwaifu-diffusion-v2.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    # FLUX
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell.safetensors`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev.safetensors`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/ashen0209-flux1-dev2pro.safetensors`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/jimmycarter-LibreFLUX.safetensors`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/nyanko7-flux-dev-de-distill.safetensors`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/shuttle-3-diffusion.safetensors`", `"FLUX`", `"unet`")) | Out-Null
    # SD 1.5 VAE
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sd_1.5/vae-ft-ema-560000-ema-pruned.safetensors`", `"SD 1.5 VAE`", `"vae`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sd_1.5/vae-ft-mse-840000-ema-pruned.safetensors`", `"SD 1.5 VAE`", `"vae`")) | Out-Null
    # SDXL VAE
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sdxl_1.0/sdxl_fp16_fix_vae.safetensors`", `"SDXL VAE`", `"vae`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sdxl_1.0/sdxl_vae.safetensors`", `"SDXL VAE`", `"vae`")) | Out-Null
    # FLUX VAE
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_vae/ae.safetensors`", `"FLUX VAE`", `"vae`")) | Out-Null
    # FLUX CLIP
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/clip_l.safetensors`", `"FLUX Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5xxl_fp16.safetensors`", `"FLUX Text Encoder`", `"clip`")) | Out-Null
    # <<<<<<<<<< End

    return `$model_list
}


# 展示模型列表
function List-Model(`$model_list) {
    `$count = 0
    `$point = `"None`"
    Print-Msg `"可下载的模型列表`"
    Write-Host `"-----------------------------------------------------`"
    Write-Host `"模型序号`" -ForegroundColor Yellow -NoNewline
    Write-Host `" | `" -NoNewline
    Write-Host `"模型名称`" -ForegroundColor White -NoNewline
    Write-Host `" | `" -NoNewline
    Write-Host `"模型种类`" -ForegroundColor Cyan
    for (`$i = 0; `$i -lt `$model_list.Count; `$i++) {
        `$content = `$model_list[`$i]
        `$count += 1
        `$url = `$content[0]
        # `$name = [System.IO.Path]::GetFileNameWithoutExtension(`$url)
        `$name = [System.IO.Path]::GetFileName(`$url)
        `$ver = `$content[1]
        if (`$point -ne `$ver) {
            Write-Host
            Write-Host `"- `$ver`" -ForegroundColor Cyan
        }
        `$point = `$ver
        Write-Host `"  - `${count}、`" -ForegroundColor Yellow -NoNewline
        Write-Host `"`$name `" -ForegroundColor White -NoNewline
        Write-Host `"(`$ver)`" -ForegroundColor Cyan
    }
    Write-Host
    Write-Host `"关于部分模型的介绍可阅读：https://github.com/licyk/README-collection/blob/main/model-info/README.md`"
    Write-Host `"-----------------------------------------------------`"
}


# 列出要下载的模型
function List-Download-Task (`$download_list) {
    Print-Msg `"当前选择要下载的模型`"
    Write-Host `"-----------------------------------------------------`"
    Write-Host `"模型名称`" -ForegroundColor White -NoNewline
    Write-Host `" | `" -NoNewline
    Write-Host `"模型种类`" -ForegroundColor Cyan
    Write-Host
    for (`$i = 0; `$i -lt `$download_list.Count; `$i++) {
        `$content = `$download_list[`$i]
        `$name = `$content[0]
        `$type = `$content[2]
        Write-Host `"- `" -ForegroundColor Yellow -NoNewline
        Write-Host `"`$name`" -ForegroundColor White -NoNewline
        Write-Host `" (`$type) `" -ForegroundColor Cyan
    }
    Write-Host
    Write-Host `"总共要下载的模型数量: `$(`$i)`" -ForegroundColor White
    Write-Host `"-----------------------------------------------------`"
}


# 模型下载器
function Model-Downloader (`$download_list) {
    `$sum = `$download_list.Count
    for (`$i = 0; `$i -lt `$download_list.Count; `$i++) {
        `$content = `$download_list[`$i]
        `$name = `$content[0]
        `$url = `$content[1]
        `$type = `$content[2]
        `$path = ([System.IO.Path]::GetFullPath(`$content[3]))
        `$model_name = Split-Path `$url -Leaf
        Print-Msg `"[`$(`$i + 1)/`$sum]:: 下载 `$name (`$type) 模型到 `$path 中`"
        aria2c --file-allocation=none --summary-interval=0 --console-log-level=error -s 64 -c -x 16 -k 1M `$url -d `"`$path`" -o `"`$model_name`"
        if (`$?) {
            Print-Msg `"[`$(`$i + 1)/`$sum]:: `$name (`$type) 下载成功`"
        } else {
            Print-Msg `"[`$(`$i + 1)/`$sum]:: `$name (`$type) 下载失败`"
        }
    }
}


# 获取用户输入
function Get-User-Input {
    return Read-Host `"==================================================>`"
}


# 搜索模型列表
function Search-Model-List (`$model_list, `$key) {
    `$count = 0
    `$result = 0
    Print-Msg `"模型列表搜索结果`"
    Write-Host `"-----------------------------------------------------`"
    Write-Host `"模型序号`" -ForegroundColor Yellow -NoNewline
    Write-Host `" | `" -NoNewline
    Write-Host `"模型名称`" -ForegroundColor White -NoNewline
    Write-Host `" | `" -NoNewline
    Write-Host `"模型种类`" -ForegroundColor Cyan
    for (`$i = 0; `$i -lt `$model_list.Count; `$i++) {
        `$content = `$model_list[`$i]
        `$count += 1
        `$url = `$content[0]
        # `$name = [System.IO.Path]::GetFileNameWithoutExtension(`$url)
        `$name = [System.IO.Path]::GetFileName(`$url)
        `$ver = `$content[1]

        if (`$name -like `"*`$key*`") {
            Write-Host `" - `${count}、`" -ForegroundColor Yellow -NoNewline
            Write-Host `"`$name `" -ForegroundColor White -NoNewline
            Write-Host `"(`$ver)`" -ForegroundColor Cyan
            `$result += 1
        }
    }
    Write-Host
    Write-Host `"搜索 `$key 得到的结果数量: `$result`" -ForegroundColor White
    Write-Host `"-----------------------------------------------------`"
}


function Main {
    Print-Msg `"初始化中`"
    Get-SD-Trainer-Script-Installer-Version
    Set-Proxy
    Check-SD-Trainer-Script-Installer-Update
    Pip-Mirror-Status

    `$to_exit = 0
    `$go_to = 0
    `$has_error = `$false
    `$model_list = Get-Model-List
    `$download_list = New-Object System.Collections.ArrayList
    `$after_list_model_option = `"`"

    while (`$True) {
        List-Model `$model_list
        switch (`$after_list_model_option) {
            list_search_result {
                Search-Model-List `$model_list `$find_key
                break
            }
            display_input_error {
                Print-Msg `"输入有误, 请重试`"
            }
            Default {
                break
            }
        }
        `$after_list_model_option = `"`"
        Print-Msg `"请选择要下载的模型`"
        Print-Msg `"提示:`"
        Print-Msg `"1. 输入数字后回车`"
        Print-Msg `"2. 如果需要下载多个模型, 可以输入多个数字并使用空格隔开`"
        Print-Msg `"3. 输入 search 可以进入列表搜索模式, 可搜索列表中已有的模型`"
        Print-Msg `"4. 输入 exit 退出模型下载脚本`"
        `$arg = Get-User-Input

        switch (`$arg) {
            exit {
                `$to_exit = 1
                `$go_to = 1
                break
            }
            search {
                Print-Msg `"请输入要从模型列表搜索的模型名称`"
                `$find_key = Get-User-Input
                `$after_list_model_option = `"list_search_result`"
            }
            Default {
                `$arg = `$arg.Split() # 拆分成列表
                ForEach (`$i in `$arg) {
                    try {
                        # 检测输入是否符合列表
                        `$i = [int]`$i
                        if ((!((`$i -ge 1) -and (`$i -le `$model_list.Count)))) {
                            `$has_error = `$true
                            break
                        }

                        # 创建下载列表
                        `$content = `$model_list[(`$i - 1)]
                        `$url = `$content[0] # 下载链接
                        `$type = `$content[1] # 类型
                        `$path = `"`$PSScriptRoot/models`" # 模型放置路径
                        # `$name = [System.IO.Path]::GetFileNameWithoutExtension(`$url) # 模型名称
                        `$name = [System.IO.Path]::GetFileName(`$url) # 模型名称
                        `$task = @(`$name, `$url, `$type, `$path)
                        # 检查重复元素
                        `$has_duplicate = `$false
                        for (`$j = 0; `$j -lt `$download_list.Count; `$j++) {
                            `$task_tmp = `$download_list[`$j]
                            `$comparison = Compare-Object -ReferenceObject `$task_tmp -DifferenceObject `$task
                            if (`$comparison.Count -eq 0) {
                                `$has_duplicate = `$true
                                break
                            }
                        }
                        if (!(`$has_duplicate)) {
                            `$download_list.Add(`$task) | Out-Null # 添加列表
                        }
                        `$has_duplicate = `$false
                    }
                    catch {
                        `$has_error = `$true
                        break
                    }
                }

                if (`$has_error) {
                    `$after_list_model_option = `"display_input_error`"
                    `$has_error = `$false
                    `$download_list.Clear() # 出现错误时清除下载列表
                    break
                }

                `$go_to = 1
                break
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

    List-Download-Task `$download_list
    Print-Msg `"是否确认下载模型?`"
    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
    `$download_operate = Get-User-Input
    if (`$download_operate -eq `"yes`" -or `$download_operate -eq `"y`" -or `$download_operate -eq `"YES`" -or `$download_operate -eq `"Y`") {
        Model-Downloader `$download_list
    }

    Print-Msg `"退出模型下载脚本`"
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$InstallPath/download_models.ps1") {
        Print-Msg "更新 download_models.ps1 中"
    } else {
        Print-Msg "生成 download_models.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$InstallPath/download_models.ps1" -Value $content
}


# SD-Trainer-Script Installer 设置脚本
function Write-SD-Trainer-Script-Installer-Settings-Script {
    $content = "
# SD-Trainer-Script Installer 版本和检查更新间隔
`$SD_TRAINER_SCRIPT_INSTALLER_VERSION = $SD_TRAINER_SCRIPT_INSTALLER_VERSION
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
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/git/bin`"
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
    Write-Host `"[SD-Trainer-Script Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# 显示 SD-Trainer-Script Installer 版本
function Get-SD-Trainer-Script-Installer-Version {
    `$ver = `$([string]`$SD_TRAINER_SCRIPT_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"SD-Trainer-Script Installer 版本: v`${major}.`${minor}.`${micro}`"
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
    # 检测是否禁用自动设置镜像源
    if (Test-Path `"`$PSScriptRoot/disable_proxy.txt`") {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
        `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
    } elseif (`$internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        `$proxy_addr = `$(`$internet_setting.ProxyServer)
        # 提取代理地址
        if ((`$proxy_addr -match `"http=(.*?);`") -or (`$proxy_addr -match `"https=(.*?);`")) {
            `$proxy_value = `$matches[1]
            # 去除 http / https 前缀
            `$proxy_value = `$proxy_value.ToString().Replace(`"http://`", `"`").Replace(`"https://`", `"`")
            `$proxy_value = `"http://`${proxy_value}`"
        } elseif (`$proxy_addr -match `"socks=(.*)`") {
            `$proxy_value = `$matches[1]
            # 去除 socks 前缀
            `$proxy_value = `$proxy_value.ToString().Replace(`"http://`", `"`").Replace(`"https://`", `"`")
            `$proxy_value = `"socks://`${proxy_value}`"
        } else {
            `$proxy_value = `"http://`${proxy_addr}`"
        }
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
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


# 获取 SD-Trainer-Script Installer 自动检测更新设置
function Get-SD-Trainer-Script-Installer-Auto-Check-Update-Setting {
    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        return `"禁用`"
    } else {
        return `"启用`"
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
    return Read-Host `"==================================================>`"
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
                Remove-Item -Path `"`$PSScriptRoot/disable_proxy.txt`" -Force -Recurse 2> `$null
                Remove-Item -Path `"`$PSScriptRoot/proxy.txt`" -Force -Recurse 2> `$null
                Print-Msg `"启用代理成功, 当设置了系统代理后将自动读取并使用`"
                break
            }
            2 {
                Print-Msg `"请输入代理服务器地址`"
                Print-Msg `"提示: 代理地址可查看代理软件获取, 代理地址的格式如 http://127.0.0.1:10809、socks://127.0.0.1:7890 等, 输入后回车保存`"
                `$proxy_address = Get-User-Input
                Remove-Item -Path `"`$PSScriptRoot/disable_proxy.txt`" -Force -Recurse 2> `$null
                Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/proxy.txt`" -Value `$proxy_address
                Print-Msg `"启用代理成功, 使用的代理服务器为: `$proxy_address`"
                break
            }
            3 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_proxy.txt`" -Force > `$null
                Remove-Item -Path `"`$PSScriptRoot/proxy.txt`" -Force -Recurse 2> `$null
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
                Remove-Item -Path `"`$PSScriptRoot/disable_uv.txt`" -Force -Recurse 2> `$null
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
                Remove-Item -Path `"`$PSScriptRoot/disable_hf_mirror.txt`" -Force -Recurse 2> `$null
                Remove-Item -Path `"`$PSScriptRoot/hf_mirror.txt`" -Force -Recurse 2> `$null
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
                Remove-Item -Path `"`$PSScriptRoot/disable_hf_mirror.txt`" -Force -Recurse 2> `$null
                Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/hf_mirror.txt`" -Value `$huggingface_mirror_address
                Print-Msg `"启用 HuggingFace 镜像成功, 使用的 HuggingFace 镜像源为: `$huggingface_mirror_address`"
                break
            }
            3 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_hf_mirror.txt`" -Force > `$null
                Remove-Item -Path `"`$PSScriptRoot/hf_mirror.txt`" -Force -Recurse 2> `$null
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
                Remove-Item -Path `"`$PSScriptRoot/disable_gh_mirror.txt`" -Force -Recurse 2> `$null
                Remove-Item -Path `"`$PSScriptRoot/gh_mirror.txt`" -Force -Recurse 2> `$null
                Print-Msg `"启用 Github 镜像成功, 在更新 SD-Trainer-Script 时将自动检测可用的 Github 镜像源并使用`"
                break
            }
            2 {
                Print-Msg `"请输入 Github 镜像源地址`"
                Print-Msg `"提示: 可用的 Github 镜像源有: `"
                Print-Msg `"1. https://ghgo.xyz/https://github.com`"
                Print-Msg `"2. https://mirror.ghproxy.com/https://github.com`"
                Print-Msg `"3. https://ghproxy.net/https://github.com`"
                Print-Msg `"4. https://gitclone.com/github.com`"
                Print-Msg `"5. https://gh-proxy.com/https://github.com`"
                Print-Msg `"6. https://ghps.cc/https://github.com`"
                Print-Msg `"7. https://gh.idayer.com/https://github.com`"
                Print-Msg `"输入 Github 镜像源地址后回车保存`"
                `$github_mirror_address = Get-User-Input
                Remove-Item -Path `"`$PSScriptRoot/disable_gh_mirror.txt`" -Force -Recurse 2> `$null
                Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/gh_mirror.txt`" -Value `$github_mirror_address
                Print-Msg `"启用 Github 镜像成功, 使用的 Github 镜像源为: `$github_mirror_address`"
                break
            }
            3 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_gh_mirror.txt`" -Force > `$null
                Remove-Item -Path `"`$PSScriptRoot/gh_mirror.txt`" -Force -Recurse 2> `$null
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


# SD-Trainer-Script Installer 自动检查更新设置
function Update-SD-Trainer-Script-Installer-Auto-Check-Update-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 SD-Trainer-Script Installer 自动检测更新设置: `$(Get-SD-Trainer-Script-Installer-Auto-Check-Update-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 SD-Trainer-Script Installer 自动更新检查`"
        Print-Msg `"2. 禁用 SD-Trainer-Script Installer 自动更新检查`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_update.txt`" -Force -Recurse 2> `$null
                Print-Msg `"启用 SD-Trainer-Script Installer 自动更新检查成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_update.txt`" -Force > `$null
                Print-Msg `"禁用 SD-Trainer-Script Installer 自动更新检查成功`"
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
                Remove-Item -Path `"`$PSScriptRoot/disable_pip_mirror.txt`" -Force -Recurse 2> `$null
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
                Remove-Item -Path `"`$PSScriptRoot/disable_set_pytorch_cuda_memory_alloc.txt`" -Force -Recurse 2> `$null
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


# 检查 SD-Trainer-Script Installer 更新
function Check-SD-Trainer-Script-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_script_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_script_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间
    ForEach (`$url in `$urls) {
        Print-Msg `"检查 SD-Trainer-Script Installer 更新中`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`"
        if (`$?) {
            `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" | Select-String -Pattern `"SD_TRAINER_SCRIPT_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
            if (`$latest_version -gt `$SD_TRAINER_SCRIPT_INSTALLER_VERSION) {
                Print-Msg `"SD-Trainer-Script Installer 有新版本可用`"
                Print-Msg `"调用 SD-Trainer-Script Installer 进行更新中`"
                . `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
                Print-Msg `"更新结束, 需重新启动 SD-Trainer-Script Installer 管理脚本以应用更新, 回车退出 SD-Trainer-Script Installer 管理脚本`"
                Read-Host | Out-Null
                exit 0
            } else {
                Print-Msg `"SD-Trainer-Script Installer 已是最新版本`"
            }
            break
        } else {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 SD-Trainer-Script Installer 更新中`"
            } else {
                Print-Msg `"检查 SD-Trainer-Script Installer 更新失败`"
            }
        }
    }
}


# 检查环境完整性
function Check-Env {
    Print-Msg `"检查环境完整性中`"
    `$broken = 0
    if ((Test-Path `"`$PSScriptRoot/python/python.exe`") -or (Test-Path `"`$PSScriptRoot/sd-scripts/python/python.exe`")) {
        `$python_status = `"已安装`"
    } else {
        `$python_status = `"未安装`"
        `$broken = 1
    }

    if ((Test-Path `"`$PSScriptRoot/git/bin/git.exe`") -or (Test-Path `"`$PSScriptRoot/sd-scripts/git/bin/git.exe`")) {
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

    if ((Test-Path `"`$PSScriptRoot/git/bin/aria2c.exe`") -or (Test-Path `"`$PSScriptRoot/sd-scripts/git/bin/aria2c.exe`")) {
        `$aria2_status = `"已安装`"
    } else {
        `$aria2_status = `"未安装`"
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
    Print-Msg `"-----------------------------------------------------`"
    if (`$broken -eq 1) {
        Print-Msg `"检测到环境出现组件缺失, 可尝试运行 SD-Trainer-Script Installer 进行安装`"
    } else {
        Print-Msg `"当前环境无缺失组件`"
    }
}


# 查看 SD-Trainer-Script Installer 文档
function Get-SD-Trainer-Script-Installer-Help-Docs {
    Print-Msg `"调用浏览器打开 SD-Trainer-Script Installer 文档中`"
    Start-Process `"https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md`"
}


function Main {
    Print-Msg `"初始化中`"
    Get-SD-Trainer-Script-Installer-Version
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
        Print-Msg `"SD-Trainer-Script Installer 自动检查更新: `$(Get-SD-Trainer-Script-Installer-Auto-Check-Update-Setting)`"
        Print-Msg `"Pip 镜像源设置: `$(Get-Pip-Mirror-Setting)`"
        Print-Msg `"自动设置 CUDA 内存分配器设置: `$(Get-PyTorch-CUDA-Memory-Alloc-Setting)`"
        Print-Msg `"-----------------------------------------------------`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 进入代理设置`"
        Print-Msg `"2. 进入 Python 包管理器设置`"
        Print-Msg `"3. 进入 HuggingFace 镜像源设置`"
        Print-Msg `"4. 进入 Github 镜像源设置`"
        Print-Msg `"5. 进入 SD-Trainer-Script Installer 自动检查更新设置`"
        Print-Msg `"6. 进入 Pip 镜像源设置`"
        Print-Msg `"7. 进入自动设置 CUDA 内存分配器设置`"
        Print-Msg `"8. 更新 SD-Trainer-Script Installer 管理脚本`"
        Print-Msg `"9. 检查环境完整性`"
        Print-Msg `"10. 查看 SD-Trainer-Script Installer 文档`"
        Print-Msg `"11. 退出 SD-Trainer-Script Installer 设置`"
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
                Update-SD-Trainer-Script-Installer-Auto-Check-Update-Setting
                break
            }
            6 {
                Pip-Mirror-Setting
                break
            }
            7 {
                PyTorch-CUDA-Memory-Alloc-Setting
                break
            }
            8 {
                Check-SD-Trainer-Script-Installer-Update
                break
            }
            9 {
                Check-Env
                break
            }
            10 {
                Get-SD-Trainer-Script-Installer-Help-Docs
                break
            }
            11 {
                `$go_to = 1
                break
            }
            Default {
                Print-Msg `"输入有误, 请重试`"
                break
            }
        }

        if (`$go_to -eq 1) {
            Print-Msg `"退出 SD-Trainer-Script Installer 设置`"
            break
        }
    }
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$InstallPath/settings.ps1") {
        Print-Msg "更新 settings.ps1 中"
    } else {
        Print-Msg "生成 settings.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$InstallPath/settings.ps1" -Value $content
}

# 虚拟环境激活脚本
function Write-Env-Activate-Script {
    $content = "
# SD-Trainer-Script Installer 版本和检查更新间隔
`$Env:SD_TRAINER_SCRIPT_INSTALLER_VERSION = $SD_TRAINER_SCRIPT_INSTALLER_VERSION
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
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/sd-scripts/git/bin`"
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
`$Env:SD_TRAINER_SCRIPT_INSTALLER_ROOT = `$PSScriptRoot



# 提示符信息
function global:prompt {
    `"`$(Write-Host `"[SD-Trainer-Script Env]`" -ForegroundColor Green -NoNewLine) `$(Get-Location)> `"
}


# 消息输出
function global:Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[SD-Trainer-Script Installer]`" -ForegroundColor Cyan -NoNewline
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
        Move-Item -Path `"`$Env:CACHE_HOME/aria2c.exe`" -Destination `"`$Env:SD_TRAINER_SCRIPT_INSTALLER_ROOT/git/bin/aria2c.exe`" -Force
        Print-Msg `"更新 Aria2 完成`"
    } else {
        Print-Msg `"下载 Aria2 失败, 无法进行更新, 可尝试重新运行更新命令`"
    }
}


# SD-Trainer-Script Installer 更新检测
function global:Check-SD-Trainer-Script-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_script_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_script_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    Set-Content -Encoding UTF8 -Path `"`$Env:SD_TRAINER_SCRIPT_INSTALLER_ROOT/update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间
    ForEach (`$url in `$urls) {
        Print-Msg `"检查 SD-Trainer-Script Installer 更新中`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`"
        if (`$?) {
            `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" | Select-String -Pattern `"SD_TRAINER_SCRIPT_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
            if (`$latest_version -gt `$Env:SD_TRAINER_SCRIPT_INSTALLER_VERSION) {
                Print-Msg `"SD-Trainer-Script Installer 有新版本可用`"
                Print-Msg `"调用 SD-Trainer-Script Installer 进行更新中`"
                . `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" -InstallPath `"`$Env:SD_TRAINER_SCRIPT_INSTALLER_ROOT`" -UseUpdateMode
                Print-Msg `"更新结束, 需重新启动 SD-Trainer-Script Installer 管理脚本以应用更新, 回车退出 SD-Trainer-Script Installer 管理脚本`"
                Read-Host | Out-Null
                exit 0
            } else {
                Print-Msg `"SD-Trainer-Script Installer 已是最新版本`"
            }
            break
        } else {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 SD-Trainer-Script Installer 更新中`"
            } else {
                Print-Msg `"检查 SD-Trainer-Script Installer 更新失败`"
            }
        }
    }
}


# 设置 Python 命令别名
function global:pip {
    python -m pip @args
}

Set-Alias pip3 pip
Set-Alias pip3.10 pip
Set-Alias python3 python
Set-Alias python3.10 python


# 列出 SD-Trainer-Script Installer 内置命令
function global:List-CMD {
    Write-Host `"
==================================
SD-Trainer-Script Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
==================================

当前可用的 SD-Trainer-Script Installer 内置命令：

    Update-uv
    Update-Aria2
    Check-SD-Trainer-Script-Installer-Update
    List-CMD

更多帮助信息可在 SD-Trainer-Script Installer 文档中查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md
`"
}


# 显示 SD-Trainer-Script Installer 版本
function Get-SD-Trainer-Script-Installer-Version {
    `$ver = `$([string]`$Env:SD_TRAINER_SCRIPT_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"SD-Trainer-Script Installer 版本: v`${major}.`${minor}.`${micro}`"
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
    # 检测是否禁用自动设置镜像源
    if (Test-Path `"`$PSScriptRoot/disable_proxy.txt`") {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
        `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
    } elseif (`$internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        `$proxy_addr = `$(`$internet_setting.ProxyServer)
        # 提取代理地址
        if ((`$proxy_addr -match `"http=(.*?);`") -or (`$proxy_addr -match `"https=(.*?);`")) {
            `$proxy_value = `$matches[1]
            # 去除 http / https 前缀
            `$proxy_value = `$proxy_value.ToString().Replace(`"http://`", `"`").Replace(`"https://`", `"`")
            `$proxy_value = `"http://`${proxy_value}`"
        } elseif (`$proxy_addr -match `"socks=(.*)`") {
            `$proxy_value = `$matches[1]
            # 去除 socks 前缀
            `$proxy_value = `$proxy_value.ToString().Replace(`"http://`", `"`").Replace(`"https://`", `"`")
            `$proxy_value = `"socks://`${proxy_value}`"
        } else {
            `$proxy_value = `"http://`${proxy_addr}`"
        }
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
}


# HuggingFace 镜像源
function Set-HuggingFace-Mirror {
    if (Test-Path `"`$PSScriptRoot/disable_hf_mirror.txt`") { # 检测是否禁用了自动设置 HuggingFace 镜像源
        Print-Msg `"检测到本地存在 disable_hf_mirror.txt 镜像源配置文件, 禁用自动设置 HuggingFace 镜像源`"
        return
    }

    if (Test-Path `"`$PSScriptRoot/hf_mirror.txt`") { # 本地存在 HuggingFace 镜像源配置
        `$hf_mirror_value = Get-Content `"`$PSScriptRoot/hf_mirror.txt`"
        `$Env:HF_ENDPOINT = `$hf_mirror_value
        Print-Msg `"检测到本地存在 hf_mirror.txt 配置文件, 已读取该配置并设置 HuggingFace 镜像源`"
    } else { # 使用默认设置
        `$Env:HF_ENDPOINT = `"https://hf-mirror.com`"
        Print-Msg `"使用默认 HuggingFace 镜像源`"
    }
}


# Github 镜像源
function Set-Github-Mirror {
    `$Env:GIT_CONFIG_GLOBAL = `"`$PSScriptRoot/.gitconfig`" # 设置 Git 配置文件路径
    if (Test-Path `"`$PSScriptRoot/.gitconfig`") {
        Remove-Item -Path `"`$PSScriptRoot/.gitconfig`" -Force -Recurse
    }

    # 默认 Git 配置
    git config --global --add safe.directory `"*`"
    git config --global core.longpaths true

    if (Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") { # 禁用 Github 镜像源
        Print-Msg `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件, 禁用 Github 镜像源`"
        return
    }

    if (Test-Path `"`$PSScriptRoot/gh_mirror.txt`") { # 使用自定义 Github 镜像源
        `$github_mirror = Get-Content `"`$PSScriptRoot/gh_mirror.txt`"
        git config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
        Print-Msg `"检测到本地存在 gh_mirror.txt Github 镜像源配置文件, 已读取 Github 镜像源配置文件并设置 Github 镜像源`"
    }
}


function Main {
    Print-Msg `"初始化中`"
    Get-SD-Trainer-Script-Installer-Version
    Set-Proxy
    Set-HuggingFace-Mirror
    Set-Github-Mirror
    Pip-Mirror-Status
    if (Test-Path `"`$Env:SD_TRAINER_SCRIPT_INSTALLER_ROOT/sd-scripts/python/python.exe`") {
        `$Env:UV_PYTHON = `"`$Env:SD_TRAINER_SCRIPT_INSTALLER_ROOT/sd-scripts/python/python.exe`"
    }
    Print-Msg `"激活 SD-Trainer-Script Env`"
    Print-Msg `"更多帮助信息可在 SD-Trainer-Script Installer 项目地址查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md`"
}

###################

Main
"

    if (Test-Path "$InstallPath/activate.ps1") {
        Print-Msg "更新 activate.ps1 中"
    } else {
        Print-Msg "生成 activate.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$InstallPath/activate.ps1" -Value $content
}


# 快捷启动终端脚本, 启动后将自动运行环境激活脚本
function Write-Launch-Terminal-Script {
    $content = "
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[SD-Trainer-Script Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}

Print-Msg `"执行 SD-Trainer-Script Installer 激活环境脚本`"
powershell -NoExit -File `"`$PSScriptRoot/activate.ps1`"
"

    if (Test-Path "$InstallPath/terminal.ps1") {
        Print-Msg "更新 terminal.ps1 中"
    } else {
        Print-Msg "生成 terminal.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$InstallPath/terminal.ps1" -Value $content
}


# 帮助文档
function Write-ReadMe {
    $content = "==================================
SD-Trainer-Script Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
==================================

这是关于 SD-Trainer-Script 的简单使用文档。

使用 SD-Trainer-Script Installer 进行安装并安装成功后，将在当前目录生成 SD-Trainer-Script 文件夹，以下为文件夹中不同文件 / 文件夹的作用。

cache：缓存文件夹，保存着 Pip / HuggingFace 等缓存文件。
python：Python 的存放路径。请注意，请勿将该 Python 文件夹添加到环境变量，这可能导致不良后果。
git：Git 的存放路径。
sd-scripts：SD-Trainer-Script 存放的文件夹。
models：使用模型下载脚本下载模型时模型的存放位置。
activate.ps1：虚拟环境激活脚本，使用该脚本激活虚拟环境后即可使用 Python、Pip、Git 的命令。
launch_sd_trainer_script_installer.ps1：获取最新的 SD-Trainer-Script Installer 安装脚本并运行。
update.ps1：更新 SD-Trainer-Script 的脚本，可使用该脚本更新 SD-Trainer-Script。
library.ps1：初始化 SD-Trainer-Script 运行环境的脚本。
train.ps1：初始训练脚本，用于编写训练命令。
switch_branch.ps1：切换 SD-Trainer-Script 分支。
reinstall_pytorch.ps1：重新安装 PyTorch 的脚本，在 PyTorch 出问题或者需要切换 PyTorch 版本时可使用。
download_model.ps1：下载模型的脚本，下载的模型将存放在 models 文件夹中。关于模型的介绍可阅读：https://github.com/licyk/README-collection/blob/main/model-info/README.md。
settings.ps1：管理 SD-Trainer-Script Installer 的设置。
terminal.ps1：启动 PowerShell 终端并自动激活虚拟环境，激活虚拟环境后即可使用 Python、Pip、Git 的命令。
help.txt：帮助文档。


SD-Trainer-Script 默认生成了一个 train.ps1 脚本用于编写训练命令，训练命令编写方法可查看：https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md#%E7%BC%96%E5%86%99%E8%AE%AD%E7%BB%83%E8%84%9A%E6%9C%AC

脚本为 SD-Trainer-Script 设置了 HuggingFace 镜像源，解决国内无法直接访问 HuggingFace，导致 SD-Trainer-Script 无法从 HuggingFace 下载模型的问题。
如果想自定义 HuggingFace 镜像源，可以在本地创建 hf_mirror.txt 文件，在文件中填写 HuggingFace 镜像源的地址后保存，再次启动脚本时将自动读取配置。
如果需要禁用 HuggingFace 镜像源，则创建 disable_hf_mirror.txt 文件，启动脚本时将不再设置 HuggingFace 镜像源。

以下为可用的 HuggingFace 镜像源地址：
https://hf-mirror.com
https://huggingface.sukaka.top

为了解决访问 Github 速度慢的问题，脚本默认启用 Github 镜像源，在运行 SD-Trainer-Script Installer 或者 SD-Trainer-Script 更新脚本时将自动测试可用的 Github 镜像源并设置。
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

设置 SD-Trainer-Script 的启动参数，可以在和 launch.ps1 脚本同级的目录创建一个 launch_args.txt 文件，在文件内写上启动参数，运行 SD-Trainer-Script 启动脚本时将自动读取该文件内的启动参数并应用。

SD-Trainer-Script Installer 提供了配置管理器, 运行 settings.ps1 即可管理各个配置。

SD-Trainer-Script Installer 的管理脚本在启动时会检查管理脚本的更新，如果有更新将会提示并显示具体的更新方法，如果要禁用更新，可以在脚本同级的目录创建 disable_update.txt 文件，这将禁用 SD-Trainer-Script Installer 更新检查。

更多详细的帮助可在下面的链接查看。
SD-Trainer-Script Installer 使用帮助：https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md
SD-Trainer-Script 项目地址：https://github.com/Akegarasu/sd-scripts

推荐的哔哩哔哩 UP 主：
青龙圣者：https://space.bilibili.com/219296
秋葉aaaki：https://space.bilibili.com/12566101
琥珀青葉：https://space.bilibili.com/507303431
观看这些 UP 主的视频可获得一些训练模型的教程。

其他的一些训练模型的教程：
https://rentry.org/59xed3
https://civitai.com/articles/2056
https://civitai.com/articles/124/lora-analogy-about-lora-trainning-and-using
https://civitai.com/articles/143/some-shallow-understanding-of-lora-training-lora
https://civitai.com/articles/632/why-this-lora-can-not-bring-good-result-lora
https://civitai.com/articles/726/an-easy-way-to-make-a-cosplay-lora-cosplay-lora
https://civitai.com/articles/2135/lora-quality-improvement-some-experiences-about-datasets-and-captions-lora
https://civitai.com/articles/2297/ways-to-make-a-character-lora-that-is-easier-to-change-clothes-lora
"

    if (Test-Path "$InstallPath/help.txt") {
        Print-Msg "更新 help.txt 中"
    } else {
        Print-Msg "生成 help.txt 中"
    }
    Set-Content -Encoding UTF8 -Path "$InstallPath/help.txt" -Value $content
}


# 写入管理脚本和文档
function Write-Manager-Scripts {
    New-Item -ItemType Directory -Path "$InstallPath" -Force > $null
    Write-Library-Script
    Write-Update-Script
    Write-Switch-Branch-Script
    Write-Launch-SD-Trainer-Script-Install-Script
    Write-PyTorch-ReInstall-Script
    Write-Download-Model-Script
    Write-SD-Trainer-Script-Installer-Settings-Script
    Write-Env-Activate-Script
    Write-Launch-Terminal-Script
    Write-ReadMe
}


# 执行安装
function Use-Install-Mode {
    Set-Proxy
    Set-uv
    Pip-Mirror-Status
    Print-Msg "启动 SD-Trainer-Script 安装程序"
    Print-Msg "提示: 若出现某个步骤执行失败, 可尝试再次运行 SD-Trainer-Script Installer, 更多的说明请阅读 SD-Trainer-Script Installer 使用文档"
    Print-Msg "SD-Trainer-Script Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md"
    Print-Msg "即将进行安装的路径: $InstallPath"
    if ((Test-Path "$PSScriptRoot/install_sd_scripts.txt") -or ($InstallBranch -eq "sd_scripts")) {
        Print-Msg "检测到 install_sd_scripts.txt 配置文件 / 命令行参数 -InstallBranch sd_scripts, 选择安装 kohya-ss/sd-scripts"
    } elseif ((Test-Path "$PSScriptRoot/install_simple_tuner.txt") -or ($InstallBranch -eq "simple_tuner")) {
        Print-Msg "检测到 install_simple_tuner.txt 配置文件 / 命令行参数 -InstallBranch simple_tuner, 选择安装 bghira/SimpleTuner"
    } elseif ((Test-Path "$PSScriptRoot/install_ai_toolkit.txt") -or ($InstallBranch -eq "ai_toolkit")) {
        Print-Msg "检测到 install_ai_toolkit.txt 配置文件 / 命令行参数 -InstallBranch ai_toolkit, 选择安装 ostris/ai-toolkit"
    } elseif ((Test-Path "$PSScriptRoot/install_finetrainers.txt") -or ($InstallBranch -eq "finetrainers")) {
        Print-Msg "检测到 install_finetrainers.txt 配置文件 / 命令行参数 -InstallBranch finetrainers, 选择安装 a-r-r-o-w/finetrainers"
    } elseif ((Test-Path "$PSScriptRoot/install_diffusion_pipe.txt") -or ($InstallBranch -eq "diffusion_pipe")) {
        Print-Msg "检测到 install_diffusion_pipe.txt 配置文件 / 命令行参数 -InstallBranch diffusion_pipe, 选择安装 tdrussell/diffusion-pipe"
    } elseif ((Test-Path "$PSScriptRoot/install_musubi_tuner.txt") -or ($InstallBranch -eq "musubi_tuner")) {
        Print-Msg "检测到 install_musubi_tuner.txt 配置文件 / 命令行参数 -InstallBranch musubi_tuner, 选择安装 kohya-ss/musubi-tuner"
    } else {
        Print-Msg "未指定安装的训练器, 默认选择安装 kohya-ss/sd-scripts"
    }
    Check-Install
    Print-Msg "添加管理脚本和文档中"
    Write-Manager-Scripts
    Print-Msg "SD-Trainer-Script 安装结束, 安装路径为: $InstallPath"
    Print-Msg "帮助文档可在 SD-Trainer-Script 文件夹中查看, 双击 help.txt 文件即可查看, 更多的说明请阅读 SD-Trainer-Script Installer 使用文档"
    Print-Msg "SD-Trainer-Script Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md"
    Print-Msg "退出 SD-Trainer-Script Installer"
    Read-Host | Out-Null
}


# 执行管理脚本更新
function Use-Update-Mode {
    Print-Msg "更新管理脚本和文档中"
    Write-Manager-Scripts
    Print-Msg "更新管理脚本和文档完成"
}


# 帮助信息
function Get-SD-Trainer-Script-Installer-Cmdlet-Help {
    $content = "
使用:
    .\sd_trainer_script_installer.ps1 -Help -InstallPath <安装 SD-Trainer-Script 的绝对路径> -InstallBranch <安装的 SD-Trainer-Script 分支> -UseUpdateMode -DisablePipMirror -DisableProxy -UseCustomProxy <代理服务器地址> -DisableUV -DisableGithubMirror -UseCustomGithubMirror <Github 镜像站地址>

参数:
    -Help
        获取 SD-Trainer-Script Installer 的帮助信息

    -InstallPath <安装 SD-Trainer-Script 的绝对路径>
        指定 SD-Trainer-Script Installer 安装 SD-Trainer-Script 的路径, 使用绝对路径表示
        例如: .\sd_trainer_script_installer.ps1 -InstallPath `"D:\Donwload`", 这将指定 SD-Trainer-Script Installer 安装 SD-Trainer-Script 到 D:\Donwload 这个路径

    -InstallBranch (sd_scripts, simple_tuner, ai_toolkit, finetrainers, diffusion_pipe, musubi_tuner)
        指定 SD-Trainer-Script Installer 安装的 SD-Trainer-Script 分支
        支持指定安装的分支如下:
            sd_scripts:     kohya-ss/sd-scripts
            simple_tuner:   bghira/SimpleTuner
            ai_toolkit:     ostris/ai-toolkit
            finetrainers:   a-r-r-o-w/finetrainers
            diffusion_pipe: tdrussell/diffusion-pipe
            musubi_tuner:   kohya-ss/musubi-tuner

    -UseUpdateMode
        指定 SD-Trainer-Script Installer 使用更新模式, 只对 SD-Trainer-Script Installer 的管理脚本进行更新

    -DisablePipMirror
        禁用 SD-Trainer-Script Installer 使用 Pip 镜像源, 使用 Pip 官方源下载 Python 软件包

    -DisableProxy
        禁用 SD-Trainer-Script Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 --UseCustomProxy `"http://127.0.0.1:10809`" 设置代理服务器地址

    -DisableUV
        禁用 SD-Trainer-Script Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -DisableGithubMirror
        禁用 SD-Trainer-Script Installer 自动设置 Github 镜像源

    -UseCustomGithubMirror <Github 镜像站地址>
        使用自定义的 Github 镜像站地址
        可用的 Github 镜像站地址:
            https://ghgo.xyz/https://github.com
            https://mirror.ghproxy.com/https://github.com
            https://ghproxy.net/https://github.com
            https://gitclone.com/github.com
            https://gh-proxy.com/https://github.com
            https://ghps.cc/https://github.com
            https://gh.idayer.com/https://github.com


更多的帮助信息请阅读 SD-Trainer-Script Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md
"
    Write-Host $content
    exit 0
}


# 主程序
function Main {
    Print-Msg "初始化中"
    Get-SD-Trainer-Script-Installer-Version
    if ($Help) {
        Get-SD-Trainer-Script-Installer-Cmdlet-Help
    }

    if ($UseUpdateMode) {
        Print-Msg "使用更新模式"
        Use-Update-Mode
        Set-Content -Encoding UTF8 -Path "$InstallPath/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
    } else {
        Print-Msg "使用安装模式"
        Use-Install-Mode
    }
}


###################


Main