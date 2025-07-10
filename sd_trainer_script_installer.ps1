param (
    [switch]$Help,
    [string]$InstallPath = (Join-Path -Path "$PSScriptRoot" -ChildPath "SD-Trainer-Script"),
    [string]$PyTorchMirrorType,
    [string]$InstallBranch,
    [switch]$UseUpdateMode,
    [switch]$DisablePyPIMirror,
    [switch]$DisableProxy,
    [string]$UseCustomProxy,
    [switch]$DisableUV,
    [switch]$DisableGithubMirror,
    [string]$UseCustomGithubMirror,
    [switch]$BuildMode,
    [switch]$BuildWithUpdate,
    [switch]$BuildWithLaunch,
    [int]$BuildWithTorch,
    [switch]$BuildWithTorchReinstall,
    [string]$BuildWitchModel,
    [int]$BuildWitchBranch,
    [string]$PyTorchPackage,
    [string]$xFormersPackage,

    # 仅在管理脚本中生效
    [switch]$DisableUpdate,
    [switch]$DisableHuggingFaceMirror,
    [string]$UseCustomHuggingFaceMirror,
    [switch]$DisableCUDAMalloc,
    [switch]$DisableEnvCheck
)
# 有关 PowerShell 脚本保存编码的问题: https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_character_encoding?view=powershell-7.4#the-byte-order-mark
# 在 PowerShell 5 中 UTF8 为 UTF8 BOM, 而在 PowerShell 7 中 UTF8 为 UTF8, 并且多出 utf8BOM 这个单独的选项: https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.management/set-content?view=powershell-7.5#-encoding
$PS_SCRIPT_ENCODING = if ($PSVersionTable.PSVersion.Major -le 5) { "UTF8" } else { "utf8BOM" }
# SD-Trainer-Script Installer 版本和检查更新间隔
$SD_TRAINER_SCRIPT_INSTALLER_VERSION = 180
$UPDATE_TIME_SPAN = 3600
# PyPI 镜像源
$PIP_INDEX_ADDR = "https://mirrors.cloud.tencent.com/pypi/simple"
$PIP_INDEX_ADDR_ORI = "https://pypi.python.org/simple"
$PIP_EXTRA_INDEX_ADDR = "https://mirrors.cernet.edu.cn/pypi/web/simple"
# $PIP_EXTRA_INDEX_ADDR_ORI = "https://download.pytorch.org/whl"
$PIP_EXTRA_INDEX_ADDR_ORI = ""
# $PIP_FIND_ADDR = "https://mirror.sjtu.edu.cn/pytorch-wheels/torch_stable.html"
$PIP_FIND_ADDR = "https://mirrors.aliyun.com/pytorch-wheels/torch_stable.html"
$PIP_FIND_ADDR_ORI = "https://download.pytorch.org/whl/torch_stable.html"
$USE_PIP_MIRROR = if ((!(Test-Path "$PSScriptRoot/disable_pypi_mirror.txt")) -and (!($DisablePyPIMirror))) { $true } else { $false }
$PIP_INDEX_MIRROR = if ($USE_PIP_MIRROR) { $PIP_INDEX_ADDR } else { $PIP_INDEX_ADDR_ORI }
$PIP_EXTRA_INDEX_MIRROR = if ($USE_PIP_MIRROR) { "$PIP_EXTRA_INDEX_ADDR_ORI $PIP_EXTRA_INDEX_ADDR" } else { $PIP_EXTRA_INDEX_ADDR_ORI }
$PIP_FIND_MIRROR = if ($USE_PIP_MIRROR) { $PIP_FIND_ADDR } else { $PIP_FIND_ADDR_ORI }
$PIP_FIND_MIRROR_CU121 = "https://download.pytorch.org/whl/cu121/torch_stable.html"
$PIP_EXTRA_INDEX_MIRROR_PYTORCH = "https://download.pytorch.org/whl"
$PIP_EXTRA_INDEX_MIRROR_XPU = "https://download.pytorch.org/whl/xpu"
$PIP_EXTRA_INDEX_MIRROR_CU118 = "https://download.pytorch.org/whl/cu118"
$PIP_EXTRA_INDEX_MIRROR_CU121 = "https://download.pytorch.org/whl/cu121"
$PIP_EXTRA_INDEX_MIRROR_CU124 = "https://download.pytorch.org/whl/cu124"
$PIP_EXTRA_INDEX_MIRROR_CU126 = "https://download.pytorch.org/whl/cu126"
$PIP_EXTRA_INDEX_MIRROR_CU128 = "https://download.pytorch.org/whl/cu128"
$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu118"
$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu124"
$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu126"
$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu128"
# Github 镜像源列表
$GITHUB_MIRROR_LIST = @(
    "https://ghfast.top/https://github.com",
    "https://mirror.ghproxy.com/https://github.com",
    "https://ghproxy.net/https://github.com",
    "https://gh.api.99988866.xyz/https://github.com",
    "https://gh-proxy.com/https://github.com",
    "https://ghps.cc/https://github.com",
    "https://gh.idayer.com/https://github.com",
    "https://ghproxy.1888866.xyz/github.com",
    "https://slink.ltd/https://github.com",
    "https://github.boki.moe/github.com",
    "https://github.moeyy.xyz/https://github.com",
    "https://gh-proxy.net/https://github.com",
    "https://gh-proxy.ygxz.in/https://github.com",
    "https://wget.la/https://github.com",
    "https://kkgithub.com",
    "https://gitclone.com/github.com"
)
# uv 最低版本
$UV_MINIMUM_VER = "0.7.20"
# Aria2 最低版本
$ARIA2_MINIMUM_VER = "1.37.0"
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
$Env:UV_DEFAULT_INDEX = $PIP_INDEX_MIRROR
$Env:UV_INDEX = $PIP_EXTRA_INDEX_MIRROR
$Env:UV_FIND_LINKS = $PIP_FIND_MIRROR
$Env:UV_LINK_MODE = "copy"
$Env:UV_HTTP_TIMEOUT = 30
$Env:UV_CONCURRENT_DOWNLOADS = 50
$Env:UV_INDEX_STRATEGY = "unsafe-best-match"
$Env:UV_CONFIG_FILE = "nul"
$Env:PIP_CONFIG_FILE = "nul"
$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
$Env:PIP_NO_WARN_SCRIPT_LOCATION = 0
$Env:PIP_TIMEOUT = 30
$Env:PIP_RETRIES = 5
$Env:PIP_PREFER_BINARY = 1
$Env:PIP_YES = 1
$Env:PYTHONUTF8 = 1
$Env:PYTHONIOENCODING = "utf-8"
$Env:PYTHONUNBUFFERED = 1
$Env:PYTHONNOUSERSITE = 1
$Env:PYTHONFAULTHANDLER = 1
$Env:GRADIO_ANALYTICS_ENABLED = "False"
$Env:HF_HUB_DISABLE_SYMLINKS_WARNING = 1
$Env:BITSANDBYTES_NOWELCOME = 1
$Env:ClDeviceGlobalMemSizeAvailablePercent = 100
$Env:CUDA_MODULE_LOADING = "LAZY"
$Env:TORCH_CUDNN_V8_API_ENABLED = 1
$Env:USE_LIBUV = 0
$Env:SYCL_CACHE_PERSISTENT = 1
$Env:TF_CPP_MIN_LOG_LEVEL = 3
$Env:SAFETENSORS_FAST_GPU = 1
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
$Env:TORCHINDUCTOR_CACHE_DIR = "$InstallPath/cache/torchinductor"
$Env:TRITON_CACHE_DIR = "$InstallPath/cache/triton"
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


# PyPI 镜像源状态
function PyPI-Mirror-Status {
    if ($USE_PIP_MIRROR) {
        Print-Msg "使用 PyPI 镜像源"
    } else {
        Print-Msg "检测到 disable_pypi_mirror.txt 配置文件 / -DisablePyPIMirror 命令行参数, 已将 PyPI 源切换至官方源"
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
    if ((Test-Path "$PSScriptRoot/proxy.txt") -or ($UseCustomProxy)) { # 本地存在代理配置
        if ($UseCustomProxy) {
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
".Trim()

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
    $urls = @(
        "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/python-3.11.11-amd64.zip",
        "https://huggingface.co/licyk/invokeai-core-model/resolve/main/pypatchmatch/python-3.11.11-amd64.zip"
    )
    $cache_path = "$Env:CACHE_HOME/python_tmp"
    $path = "$InstallPath/python"
    $i = 0

    # 下载 Python
    ForEach ($url in $urls) {
        Print-Msg "正在下载 Python"
        try {
            Invoke-WebRequest -Uri $url -OutFile "$Env:CACHE_HOME/python-amd64.zip"
            break
        }
        catch {
            $i += 1
            if ($i -lt $urls.Length) {
                Print-Msg "重试下载 Python 中"
            } else {
                Print-Msg "Python 安装失败, 终止 SD-Trainer-Script 安装进程, 可尝试重新运行 SD-Trainer-Script Installer 重试失败的安装"
                if (!($BuildMode)) {
                    Read-Host | Out-Null
                }
                exit 1
            }
        }
    }

    if (Test-Path "$cache_path") {
        Remove-Item -Path "$cache_path" -Force -Recurse
    }
    # 解压 Python
    Print-Msg "正在解压 Python"
    Expand-Archive -Path "$Env:CACHE_HOME/python-amd64.zip" -DestinationPath "$cache_path" -Force
    # 清理空文件夹
    if (Test-Path "$path") {
        $random_string = [Guid]::NewGuid().ToString().Substring(0, 18)
        Move-Item -Path "$path" -Destination "$Env:CACHE_HOME/$random_string" -Force
    }
    New-Item -ItemType Directory -Path "$([System.IO.Path]::GetDirectoryName($path))" -Force > $null
    Move-Item -Path "$cache_path" -Destination "$path" -Force
    Remove-Item -Path "$Env:CACHE_HOME/python-amd64.zip" -Force -Recurse
    Print-Msg "Python 安装成功"
}


# 下载并解压 Git
function Install-Git {
    $urls = @(
        "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/PortableGit.zip",
        "https://huggingface.co/licyk/invokeai-core-model/resolve/main/pypatchmatch/PortableGit.zip"
    )
    $cache_path = "$Env:CACHE_HOME/git_tmp"
    $path = "$InstallPath/git"
    $i = 0

    # 下载 Git
    ForEach ($url in $urls) {
        Print-Msg "正在下载 Git"
        try {
            Invoke-WebRequest -Uri $url -OutFile "$Env:CACHE_HOME/PortableGit.zip"
            break
        }
        catch {
            $i += 1
            if ($i -lt $urls.Length) {
                Print-Msg "重试下载 Git 中"
            } else {
                Print-Msg "Git 安装失败, 终止 SD-Trainer-Script 安装进程, 可尝试重新运行 SD-Trainer-Script Installer 重试失败的安装"
                if (!($BuildMode)) {
                    Read-Host | Out-Null
                }
                exit 1
            }
        }
    }

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
}


# 下载 Aria2
function Install-Aria2 {
    $urls = @(
        "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/aria2c.exe",
        "https://huggingface.co/licyk/invokeai-core-model/resolve/main/pypatchmatch/aria2c.exe"
    )
    $i = 0

    ForEach ($url in $urls) {
        Print-Msg "正在下载 Aria2"
        try {
            Invoke-WebRequest -Uri $url -OutFile "$Env:CACHE_HOME/aria2c.exe"
            break
        }
        catch {
            $i += 1
            if ($i -lt $urls.Length) {
                Print-Msg "重试下载 Aria2 中"
            } else {
                Print-Msg "Aria2 安装失败, 终止 SD-Trainer-Script 安装进程, 可尝试重新运行 SD-Trainer-Script Installer 重试失败的安装"
                if (!($BuildMode)) {
                    Read-Host | Out-Null
                }
                exit 1
            }
        }
    }

    Move-Item -Path "$Env:CACHE_HOME/aria2c.exe" -Destination "$InstallPath/git/bin/aria2c.exe" -Force
    Print-Msg "Aria2 下载成功"
}


# 下载 uv
function Install-uv {
    Print-Msg "正在下载 uv"
    python -m pip install uv
    if ($?) {
        Print-Msg "uv 下载成功"
    } else {
        Print-Msg "uv 下载失败, 终止 SD-Trainer-Script 安装进程, 可尝试重新运行 SD-Trainer-Script Installer 重试失败的安装"
        if (!($BuildMode)) {
            Read-Host | Out-Null
        }
        exit 1
    }
}


# Github 镜像测试
function Set-Github-Mirror {
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
    if ((Test-Path "$PSScriptRoot/gh_mirror.txt") -or ($UseCustomGithubMirror)) {
        if ($UseCustomGithubMirror) {
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
            if (!($BuildMode)) {
                Read-Host | Out-Null
            }
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
        if (!($BuildMode)) {
            Read-Host | Out-Null
        }
        exit 1
    }
}


# 设置 PyTorch 镜像源
function Get-PyTorch-Mirror ($pytorch_package) {
    # 获取 PyTorch 的版本
    $torch_part = @($pytorch_package -split ' ' | Where-Object { $_ -like "torch==*" })[0]

    if ($PyTorchMirrorType) {
        Print-Msg "使用指定的 PyTorch 镜像源类型: $PyTorchMirrorType"
        $mirror_type = $PyTorchMirrorType
    } elseif ($torch_part) {
        # 获取 PyTorch 镜像源类型
        if ($torch_part.split("+") -eq $torch_part) {
            $content = "
import re



def version_increment(version: str) -> str:
    version = ''.join(re.findall(r'\d|\.', version))
    ver_parts = list(map(int, version.split('.')))
    ver_parts[-1] += 1

    for i in range(len(ver_parts) - 1, 0, -1):
        if ver_parts[i] == 10:
            ver_parts[i] = 0
            ver_parts[i - 1] += 1

    return '.'.join(map(str, ver_parts))


def version_decrement(version: str) -> str:
    version = ''.join(re.findall(r'\d|\.', version))
    ver_parts = list(map(int, version.split('.')))
    ver_parts[-1] -= 1

    for i in range(len(ver_parts) - 1, 0, -1):
        if ver_parts[i] == -1:
            ver_parts[i] = 9
            ver_parts[i - 1] -= 1

    while len(ver_parts) > 1 and ver_parts[0] == 0:
        ver_parts.pop(0)

    return '.'.join(map(str, ver_parts))


def has_version(version: str) -> bool:
    return version != version.replace('~=', '').replace('===', '').replace('!=', '').replace('<=', '').replace('>=', '').replace('<', '').replace('>', '').replace('==', '')


def get_package_name(package: str) -> str:
    return package.split('~=')[0].split('===')[0].split('!=')[0].split('<=')[0].split('>=')[0].split('<')[0].split('>')[0].split('==')[0]


def get_package_version(package: str) -> str:
    return package.split('~=').pop().split('===').pop().split('!=').pop().split('<=').pop().split('>=').pop().split('<').pop().split('>').pop().split('==').pop()

def compare_versions(version1: str, version2: str) -> int:
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


def get_pytorch_mirror_type(torch_version: str) -> str:
    torch_ver = get_package_version(torch_version)

    if compare_versions(torch_ver, '2.0.0') == -1:
        # torch < 2.0.0
        return 'cu11x'
    elif (compare_versions(torch_ver, '2.0.0') == 1 or compare_versions(torch_ver, '2.0.0') == 0) and compare_versions(torch_ver, '2.3.1') == -1:
        # 2.0.0 <= torch < 2.3.1
        return 'cu118'
    elif (compare_versions(torch_ver, '2.3.0') == 1 or compare_versions(torch_ver, '2.3.0') == 0) and compare_versions(torch_ver, '2.4.1') == -1:
        # 2.3.0 <= torch < 2.4.1
        return 'cu121'
    elif (compare_versions(torch_ver, '2.4.0') == 1 or compare_versions(torch_ver, '2.4.0') == 0) and compare_versions(torch_ver, '2.6.0') == -1:
        # 2.4.0 <= torch < 2.6.0
        return 'cu124'
    elif (compare_versions(torch_ver, '2.6.0') == 1 or compare_versions(torch_ver, '2.6.0') == 0) and compare_versions(torch_ver, '2.7.0') == -1:
        # 2.6.0 <= torch < 2.7.0
        return 'cu126'
    elif (compare_versions(torch_ver, '2.7.0') == 1 or compare_versions(torch_ver, '2.7.0') == 0):
        # torch >= 2.7.0
        return 'cu128'



if __name__ == '__main__':
    print(get_pytorch_mirror_type('$torch_part'))
".Trim()

            $mirror_type = $(python -c "$content")
        } else {
            $mirror_type = $torch_part.Split("+")[-1]
        }

        Print-Msg "PyTorch 镜像源类型: $mirror_type"
    } else {
        Print-Msg "未获取到 PyTorch 版本, 无法确定镜像源类型, 可能导致 PyTorch 安装失败"
        $mirror_type = "null"
    }

    # 设置对应的镜像源
    switch ($mirror_type) {
        cu11x {
            Print-Msg "设置 PyTorch 镜像源类型为 cu11x"
            $mirror_pip_index_url = $Env:PIP_INDEX_URL
            $mirror_uv_default_index = $Env:UV_DEFAULT_INDEX
            $mirror_pip_extra_index_url = $Env:PIP_EXTRA_INDEX_URL
            $mirror_uv_index = $Env:UV_INDEX
            $mirror_pip_find_links = $Env:PIP_FIND_LINKS
            $mirror_uv_find_links = $Env:UV_FIND_LINKS
        }
        cu118 {
            Print-Msg "设置 PyTorch 镜像源类型为 cu118"
            $mirror_pip_index_url = if ($USE_PIP_MIRROR) {
                $PIP_EXTRA_INDEX_MIRROR_CU118_NJU
            } else {
                $PIP_EXTRA_INDEX_MIRROR_CU118
            }
            $mirror_uv_default_index = $mirror_pip_index_url
            $mirror_pip_extra_index_url = ""
            $mirror_uv_index = $mirror_pip_extra_index_url
            $mirror_pip_find_links = ""
            $mirror_uv_find_links = $mirror_pip_find_links
        }
        cu121 {
            Print-Msg "设置 PyTorch 镜像源类型为 cu121"
            $mirror_pip_index_url = "$PIP_EXTRA_INDEX_MIRROR_CU121"
            $mirror_uv_default_index = $mirror_pip_index_url
            $mirror_pip_extra_index_url = ""
            $mirror_uv_index = $mirror_pip_extra_index_url
            $mirror_pip_find_links = ""
            $mirror_uv_find_links = $mirror_pip_find_links
        }
        cu124 {
            Print-Msg "设置 PyTorch 镜像源类型为 cu124"
            $mirror_pip_index_url = if ($USE_PIP_MIRROR) {
                $PIP_EXTRA_INDEX_MIRROR_CU124_NJU
            } else {
                $PIP_EXTRA_INDEX_MIRROR_CU124
            }
            $mirror_uv_default_index = $mirror_pip_index_url
            $mirror_pip_extra_index_url = ""
            $mirror_uv_index = $mirror_pip_extra_index_url
            $mirror_pip_find_links = ""
            $mirror_uv_find_links = $mirror_pip_find_links
        }
        cu126 {
            Print-Msg "设置 PyTorch 镜像源类型为 cu126"
            $mirror_pip_index_url = if ($USE_PIP_MIRROR) {
                $PIP_EXTRA_INDEX_MIRROR_CU126_NJU
            } else {
                $PIP_EXTRA_INDEX_MIRROR_CU126
            }
            $mirror_uv_default_index = $mirror_pip_index_url
            $mirror_pip_extra_index_url = ""
            $mirror_uv_index = $mirror_pip_extra_index_url
            $mirror_pip_find_links = ""
            $mirror_uv_find_links = $mirror_pip_find_links
        }
        cu128 {
            Print-Msg "设置 PyTorch 镜像源类型为 cu128"
            $mirror_pip_index_url = if ($USE_PIP_MIRROR) {
                $PIP_EXTRA_INDEX_MIRROR_CU128_NJU
            } else {
                $PIP_EXTRA_INDEX_MIRROR_CU128
            }
            $mirror_uv_default_index = $mirror_pip_index_url
            $mirror_pip_extra_index_url = ""
            $mirror_uv_index = $mirror_pip_extra_index_url
            $mirror_pip_find_links = ""
            $mirror_uv_find_links = $mirror_pip_find_links
        }
        Default {
            Print-Msg "未知的 PyTorch 镜像源类型: $mirror_type, 使用默认 PyTorch 镜像源"
            $mirror_pip_index_url = $Env:PIP_INDEX_URL
            $mirror_uv_default_index = $Env:UV_DEFAULT_INDEX
            $mirror_pip_extra_index_url = $Env:PIP_EXTRA_INDEX_URL
            $mirror_uv_index = $Env:UV_INDEX
            $mirror_pip_find_links = $Env:PIP_FIND_LINKS
            $mirror_uv_find_links = $Env:UV_FIND_LINKS
        }
    }
    return $mirror_pip_index_url, $mirror_uv_default_index, $mirror_pip_extra_index_url, $mirror_uv_index, $mirror_pip_find_links, $mirror_uv_find_links
}


# 为 PyTorch 获取合适的 CUDA 版本类型
function Get-Appropriate-CUDA-Version-Type {
    $content = "
import re
import subprocess



def get_cuda_comp_cap() -> float:
    # Returns float of CUDA Compute Capability using nvidia-smi
    # Returns 0.0 on error
    # CUDA Compute Capability
    # ref https://developer.nvidia.com/cuda-gpus
    # ref https://en.wikipedia.org/wiki/CUDA
    # Blackwell consumer GPUs should return 12.0 data-center GPUs should return 10.0
    try:
        return max(map(float, subprocess.check_output(['nvidia-smi', '--query-gpu=compute_cap', '--format=noheader,csv'], text=True).splitlines()))
    except Exception as _:
        return 0.0


def get_cuda_version() -> str:
    try:
        # 获取nvidia-smi输出
        output = subprocess.check_output(['nvidia-smi', '-q'], text=True)
        match = re.search(r'CUDA Version\s+:\s+(\d+\.\d+)', output)
        if match:
            return match.group(1)
        return 0.0
    except:
        return 0.0


def compare_versions(version1: str, version2: str) -> int:
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


def is_vers_ge(ver_1: str, ver_2: str) -> bool:
    if compare_versions(ver_1, ver_2) == 1 or compare_versions(ver_1, ver_2) == 0:
        return True
    return False


def select_avaliable_cuda_type() -> str:
    cuda_comp_cap = get_cuda_comp_cap()
    cuda_support_ver = get_cuda_version()

    if is_vers_ge(cuda_support_ver, '12.8'):
        return 'cu128'
    elif is_vers_ge(cuda_support_ver, '12.6'):
        return 'cu126'
    elif is_vers_ge(cuda_support_ver, '12.4'):
        return 'cu124'
    elif is_vers_ge(cuda_support_ver, '12.1'):
        return 'cu121'
    elif is_vers_ge(cuda_support_ver, '11.8'):
        return 'cu118'

    if compare_versions(cuda_comp_cap, '10.0') == 1:
        return 'cu128' # RTX 50xx
    else:
        return 'cu118' # 其他 Nvidia 显卡



if __name__ == '__main__':
    print(select_avaliable_cuda_type())
".Trim()

    return $(python -c "$content")
}


# 获取合适的 PyTorch / xFormers 版本
function Get-PyTorch-And-xFormers-Package {
    Print-Msg "设置 PyTorch 和 xFormers 版本"

    if ($PyTorchPackage -and $xFormersPackage) {
        # 使用自定义的 PyTorch / xFormers 版本
        return $PyTorchPackage, $xFormersPackage
    }

    if ((!$PyTorchPackage -and $xFormersPackage) -or ($PyTorchPackage -and !$xFormersPackage)) {
        Print-Msg "不允许单独设置 -PyTorchPackage / -xFormersPackage 命令行参数, 将重新设置合适的 PyTorch 和 xFormers 版本"
    }

    if ($PyTorchMirrorType) {
        Print-Msg "根据 $PyTorchMirrorType 类型的 PyTorch 镜像源配置 PyTorch 组合"
        $appropriate_cuda_version = $PyTorchMirrorType
    } else {
        $appropriate_cuda_version = Get-Appropriate-CUDA-Version-Type
    }

    switch ($appropriate_cuda_version) {
        cu128 {
            $pytorch_package = "torch==2.7.0+cu128 torchvision==0.22.0+cu128 torchaudio==2.7.0+cu128"
            $xformers_package = "xformers==0.0.30"
            break
        }
        cu126 {
            $pytorch_package = "torch==2.7.0+cu126 torchvision==0.22.0+cu126 torchaudio==2.7.0+cu126"
            $xformers_package = "xformers==0.0.30"
            break
        }
        cu124 {
            $pytorch_package = "torch==2.6.0+cu124 torchvision==0.21.0+cu124 torchaudio==2.6.0+cu124"
            $xformers_package = "xformers==0.0.29.post3"
            break
        }
        cu121 {
            $pytorch_package = "torch==2.3.1+cu121 torchvision==0.18.1+cu121 torchaudio==2.3.1+cu121"
            $xformers_package = "xformers===0.0.27"
            break
        }
        cu118 {
            $pytorch_package = "torch==2.3.1+cu118 torchvision==0.18.1+cu118 torchaudio==2.3.1+cu118"
            $xformers_package = "xformers==0.0.27+cu118"
            break
        }
        Default {
            $pytorch_package = "torch==2.3.1+cu118 torchvision==0.18.1+cu118 torchaudio==2.3.1+cu118"
            $xformers_package = "xformers==0.0.27+cu118"
            break
        }
    }

    return $pytorch_package, $xformers_package
}


# 安装 PyTorch
function Install-PyTorch {
    $pytorch_package, $xformers_package = Get-PyTorch-And-xFormers-Package
    $mirror_pip_index_url, $mirror_uv_default_index, $mirror_pip_extra_index_url, $mirror_uv_index, $mirror_pip_find_links, $mirror_uv_find_links = Get-PyTorch-Mirror $pytorch_package

    # 备份镜像源配置
    $tmp_pip_index_url = $Env:PIP_INDEX_URL
    $tmp_uv_default_index = $Env:UV_DEFAULT_INDEX
    $tmp_pip_extra_index_url = $Env:PIP_EXTRA_INDEX_URL
    $tmp_uv_index = $Env:UV_INDEX
    $tmp_pip_find_links = $Env:PIP_FIND_LINKS
    $tmp_uv_find_links = $Env:UV_FIND_LINKS

    # 设置新的镜像源
    $Env:PIP_INDEX_URL = $mirror_pip_index_url
    $Env:UV_DEFAULT_INDEX = $mirror_uv_default_index
    $Env:PIP_EXTRA_INDEX_URL = $mirror_pip_extra_index_url
    $Env:UV_INDEX = $mirror_uv_index
    $Env:PIP_FIND_LINKS = $mirror_pip_find_links
    $Env:UV_FIND_LINKS = $mirror_uv_find_links

    Print-Msg "将要安装的 PyTorch: $pytorch_package"
    Print-Msg "将要安装的 xFormers: $xformers_package"
    Print-Msg "检测是否需要安装 PyTorch"
    python -m pip show torch --quiet 2> $null
    if (!($?)) {
        Print-Msg "安装 PyTorch 中"
        if ($USE_UV) {
            uv pip install $pytorch_package.ToString().Split()
            if (!($?)) {
                Print-Msg "检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装"
                python -m pip install $pytorch_package.ToString().Split()
            }
        } else {
            python -m pip install $pytorch_package.ToString().Split()
        }
        if ($?) {
            Print-Msg "PyTorch 安装成功"
        } else {
            Print-Msg "PyTorch 安装失败, 终止 SD-Trainer-Script 安装进程, 可尝试重新运行 SD-Trainer-Script Installer 重试失败的安装"
            if (!($BuildMode)) {
                Read-Host | Out-Null
            }
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
            uv pip install $xformers_package.ToString().Split() --no-deps
            if (!($?)) {
                Print-Msg "检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装"
                python -m pip install $xformers_package.ToString().Split() --no-deps
            }
        } else {
            python -m pip install $xformers_package.ToString().Split() --no-deps
        }
        if ($?) {
            Print-Msg "xFormers 安装成功"
        } else {
            Print-Msg "xFormers 安装失败, 终止 SD-Trainer-Script 安装进程, 可尝试重新运行 SD-Trainer-Script Installer 重试失败的安装"
            if (!($BuildMode)) {
                Read-Host | Out-Null
            }
            exit 1
        }
    } else {
        Print-Msg "xFormers 已安装, 无需再次安装"
    }

    # 还原镜像源配置
    $Env:PIP_INDEX_URL = $tmp_pip_index_url
    $Env:UV_DEFAULT_INDEX = $tmp_uv_default_index
    $Env:PIP_EXTRA_INDEX_URL = $tmp_pip_extra_index_url
    $Env:UV_INDEX = $tmp_uv_index
    $Env:PIP_FIND_LINKS = $tmp_pip_find_links
    $Env:UV_FIND_LINKS = $tmp_uv_find_links
}


# 安装 SD-Trainer-Script 依赖
function Install-SD-Trainer-Script-Dependence {
    # 记录脚本所在路径
    $current_path = $(Get-Location).ToString()
    Set-Location "$InstallPath/sd-scripts"
    $no_requirements_file = $false
    if (!Test-Path "$InstallPath/sd-scripts/requirements.txt") {
        $no_requirements_file = $true
    }
    Print-Msg "安装 SD-Trainer-Script 依赖中"
    if ($USE_UV) {
        if ($no_requirements_file) {
            uv pip install -e .
        } else {
            uv pip install -r requirements.txt
        }
        if (!($?)) {
            Print-Msg "检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装"
            if ($no_requirements_file) {
                python -m pip install -e .
            } else {
                python -m pip install -r requirements.txt
            }
        }
    } else {
        if ($no_requirements_file) {
            python -m pip install -e .
        } else {
            python -m pip install -r requirements.txt
        }
    }
    if ($?) {
        Print-Msg "SD-Trainer-Script 依赖安装成功"
    } else {
        Print-Msg "SD-Trainer-Script 依赖安装失败, 终止 SD-Trainer-Script 安装进程, 可尝试重新运行 SD-Trainer-Script Installer 重试失败的安装"
        Set-Location "$current_path"
        if (!($BuildMode)) {
            Read-Host | Out-Null
        }
        exit 1
    }
    Set-Location "$current_path"
}


# 安装 Python 软件包
function Install-Python-Package ($pkg) {
    Print-Msg "安装 $pkg 软件包中"
    if ($USE_UV) {
        uv pip install $pkg.ToString().Split()
        if (!($?)) {
            Print-Msg "检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装"
            python -m pip install $pkg.ToString().Split()
        }
    } else {
        python -m pip install $pkg.ToString().Split()
    }
    if ($?) {
        Print-Msg "安装 $pkg 软件包安装成功"
    } else {
        Print-Msg "安装 $pkg 软件包安装失败, 终止 SD-Trainer-Scripts 安装进程, 可尝试重新运行 SD-Trainer-Scripts Installer 重试失败的安装"
        Set-Location "$current_path"
        if (!($BuildMode)) {
            Read-Host | Out-Null
        }
        exit 1
    }
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

    Set-Github-Mirror
    Install-SD-Trainer-Script
    Install-PyTorch
    Install-SD-Trainer-Script-Dependence
    Install-Python-Package "lycoris-lora dadaptation open-clip-torch wandb tensorboard"

    # 清理缓存
    Print-Msg "清理下载 Python 软件包的缓存中"
    python -m pip cache purge
    uv cache clean

    Set-Content -Encoding UTF8 -Path "$InstallPath/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
}


# 训练模板脚本
function Write-Train-Script {
    $content = "#################################################
# 初始化基础环境变量, 以正确识别到运行环境
& `"`$PSScriptRoot/init.ps1`"
Set-Location `$PSScriptRoot
# 此处的代码不要修改或者删除, 否则可能会出现意外情况
# 
# SD-Trainer-Script 环境初始化后提供以下变量便于使用
# 
# `${ROOT_PATH}               当前目录
# `${SD_SCRIPTS_PATH}         训练脚本所在目录
# `${DATASET_PATH}            数据集目录
# `${MODEL_PATH}              模型下载器下载的模型路径
# `${GIT_EXEC}                Git 路径
# `${PYTHON_EXEC}             Python 解释器路径
# 
# 下方可编写训练代码
# 编写训练命令可参考: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md#%E7%BC%96%E5%86%99%E8%AE%AD%E7%BB%83%E8%84%9A%E6%9C%AC
# 编写结束后, 该文件必须使用 UTF-8 with BOM 编码保存
#################################################





#################################################
Write-Host `"训练结束, 退出训练脚本`"
Read-Host | Out-Null # 训练结束后保持控制台不被关闭
".Trim()

    if (!(Test-Path "$InstallPath/train.ps1")) {
        Print-Msg "生成 train.ps1 中"
        Set-Content -Encoding $PS_SCRIPT_ENCODING -Path "$InstallPath/train.ps1" -Value $content
    }
}


# 初始化脚本
function Write-Library-Script {
    $content = "
param (
    [switch]`$Help,
    [switch]`$BuildMode,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableUpdate,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisableHuggingFaceMirror,
    [string]`$UseCustomHuggingFaceMirror,
    [switch]`$DisableUV,
    [switch]`$DisableCUDAMalloc,
    [switch]`$DisableEnvCheck
)
# SD-Trainer-Script Installer 版本和检查更新间隔
`$SD_TRAINER_SCRIPT_INSTALLER_VERSION = $SD_TRAINER_SCRIPT_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# PyPI 镜像源
`$PIP_INDEX_ADDR = `"$PIP_INDEX_ADDR`"
`$PIP_INDEX_ADDR_ORI = `"$PIP_INDEX_ADDR_ORI`"
`$PIP_EXTRA_INDEX_ADDR = `"$PIP_EXTRA_INDEX_ADDR`"
`$PIP_EXTRA_INDEX_ADDR_ORI = `"$PIP_EXTRA_INDEX_ADDR_ORI`"
`$PIP_FIND_ADDR = `"$PIP_FIND_ADDR`"
`$PIP_FIND_ADDR_ORI = `"$PIP_FIND_ADDR_ORI`"
`$USE_PIP_MIRROR = if ((!(Test-Path `"`$PSScriptRoot/disable_pypi_mirror.txt`")) -and (!(`$DisablePyPIMirror))) { `$true } else { `$false }
`$PIP_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_INDEX_ADDR } else { `$PIP_INDEX_ADDR_ORI }
`$PIP_EXTRA_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_EXTRA_INDEX_ADDR } else { `$PIP_EXTRA_INDEX_ADDR_ORI }
`$PIP_FIND_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_FIND_ADDR } else { `$PIP_FIND_ADDR_ORI }
`$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_XPU = `"$PIP_EXTRA_INDEX_MIRROR_XPU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118 = `"$PIP_EXTRA_INDEX_MIRROR_CU118`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
`$PIP_EXTRA_INDEX_MIRROR_CU126 = `"$PIP_EXTRA_INDEX_MIRROR_CU126`"
`$PIP_EXTRA_INDEX_MIRROR_CU128 = `"$PIP_EXTRA_INDEX_MIRROR_CU128`"
`$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU118_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU124_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU126_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU128_NJU`"
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# Aria2 最低版本
`$ARIA2_MINIMUM_VER = `"$ARIA2_MINIMUM_VER`"
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
`$Env:PIP_EXTRA_INDEX_URL = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`".Trim() } else { `$PIP_EXTRA_INDEX_MIRROR }
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_DEFAULT_INDEX = `"`$PIP_INDEX_MIRROR`"
`$Env:UV_INDEX = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`".Trim() } else { `$PIP_EXTRA_INDEX_MIRROR }
`$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:UV_CONCURRENT_DOWNLOADS = 50
`$Env:UV_INDEX_STRATEGY = `"unsafe-best-match`"
`$Env:UV_CONFIG_FILE = `"nul`"
`$Env:PIP_CONFIG_FILE = `"nul`"
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$Env:PIP_NO_WARN_SCRIPT_LOCATION = 0
`$Env:PIP_TIMEOUT = 30
`$Env:PIP_RETRIES = 5
`$Env:PIP_PREFER_BINARY = 1
`$Env:PIP_YES = 1
`$Env:PYTHONUTF8 = 1
`$Env:PYTHONIOENCODING = `"utf-8`"
`$Env:PYTHONUNBUFFERED = 1
`$Env:PYTHONNOUSERSITE = 1
`$Env:PYTHONFAULTHANDLER = 1
`$Env:GRADIO_ANALYTICS_ENABLED = `"False`"
`$Env:HF_HUB_DISABLE_SYMLINKS_WARNING = 1
`$Env:BITSANDBYTES_NOWELCOME = 1
`$Env:ClDeviceGlobalMemSizeAvailablePercent = 100
`$Env:CUDA_MODULE_LOADING = `"LAZY`"
`$Env:TORCH_CUDNN_V8_API_ENABLED = 1
`$Env:USE_LIBUV = 0
`$Env:SYCL_CACHE_PERSISTENT = 1
`$Env:TF_CPP_MIN_LOG_LEVEL = 3
`$Env:SAFETENSORS_FAST_GPU = 1
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
`$Env:TORCHINDUCTOR_CACHE_DIR = `"`$PSScriptRoot/cache/torchinductor`"
`$Env:TRITON_CACHE_DIR = `"`$PSScriptRoot/cache/triton`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 帮助信息
function Get-SD-Trainer-Script-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\init.ps1 [-Help] [-BuildMode] [-DisablePyPIMirror] [-DisableUpdate] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>] [-DisableUV] [-DisableCUDAMalloc] [-DisableEnvCheck]

参数:
    -Help
        获取 SD-Trainer-Script Installer 的帮助信息

    -BuildMode
        启用 SD-Trainer-Script Installer 构建模式

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableUpdate
        禁用 SD-Trainer-Script Installer 更新检查

    -DisableProxy
        禁用 SD-Trainer-Script Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableHuggingFaceMirror
        禁用 HuggingFace 镜像源, 不使用 HuggingFace 镜像源下载文件

    -UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>
        使用自定义 HuggingFace 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror ```"https://hf-mirror.com```" 设置 HuggingFace 镜像源地址

    -DisableUV
        禁用 SD-Trainer-Script Installer使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -DisableCUDAMalloc
        禁用 SD-Trainer-Script Installer通过 PYTORCH_CUDA_ALLOC_CONF 环境变量设置 CUDA 内存分配器

    -DisableEnvCheck
        禁用 SD-Trainer-Script Installer检查 Fooocus 运行环境中存在的问题, 禁用后可能会导致 Fooocus 环境中存在的问题无法被发现并修复


更多的帮助信息请阅读 SD-Trainer-Script Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


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


# PyPI 镜像源状态
function PyPI-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 PyPI 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pypi_mirror.txt 配置文件 / -DisablePyPIMirror 命令行参数, 已将 PyPI 源切换至官方源`"
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
`".Trim()

    Print-Msg `"检测 PyTorch 的 libomp 问题中`"
    python -c `"`$content`"
    Print-Msg `"PyTorch 检查完成`"
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

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 SD-Trainer-Script Installer 的自动检查更新功能`"
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
    } else {
        return
    }

    ForEach (`$url in `$urls) {
        Print-Msg `"检查 SD-Trainer-Script Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" |
                Select-String -Pattern `"SD_TRAINER_SCRIPT_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 SD-Trainer-Script Installer 更新中`"
            } else {
                Print-Msg `"检查 SD-Trainer-Script Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -gt `$SD_TRAINER_SCRIPT_INSTALLER_VERSION) {
        Print-Msg `"检测到 SD-Trainer-Script Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"==================================================>`").Trim()
        if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
            Print-Msg `"调用 SD-Trainer-Script Installer 进行更新中`"
            . `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
            `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
            Print-Msg `"更新结束, 重新启动 SD-Trainer-Script Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
            Invoke-Expression `"& ```"`$PSCommandPath```" `$raw_params`"
            exit 0
        } else {
            Print-Msg `"跳过 SD-Trainer-Script Installer 更新`"
        }
    } else {
        Print-Msg `"SD-Trainer-Script Installer 已是最新版本`"
    }
}


# 代理配置
function Set-Proxy {
    `$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    # 检测是否禁用自动设置镜像源
    if ((Test-Path `"`$PSScriptRoot/disable_proxy.txt`") -or (`$DisableProxy)) {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件 / -DisableProxy 命令行参数, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if ((Test-Path `"`$PSScriptRoot/proxy.txt`") -or (`$UseCustomProxy)) { # 本地存在代理配置
        if (`$UseCustomProxy) {
            `$proxy_value = `$UseCustomProxy
        } else {
            `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        }
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件 / -UseCustomProxy 命令行参数, 已读取代理配置文件并设置代理`"
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
    if ((Test-Path `"`$PSScriptRoot/disable_hf_mirror.txt`") -or (`$DisableHuggingFaceMirror)) { # 检测是否禁用了自动设置 HuggingFace 镜像源
        Print-Msg `"检测到本地存在 disable_hf_mirror.txt 镜像源配置文件 / -DisableHuggingFaceMirror 命令行参数, 禁用自动设置 HuggingFace 镜像源`"
        return
    }

    if ((Test-Path `"`$PSScriptRoot/hf_mirror.txt`") -or (`$UseCustomHuggingFaceMirror)) { # 本地存在 HuggingFace 镜像源配置
        if (`$UseCustomHuggingFaceMirror) {
            `$hf_mirror_value = `$UseCustomHuggingFaceMirror
        } else {
            `$hf_mirror_value = Get-Content `"`$PSScriptRoot/hf_mirror.txt`"
        }
        `$Env:HF_ENDPOINT = `$hf_mirror_value
        Print-Msg `"检测到本地存在 hf_mirror.txt 配置文件 / -UseCustomHuggingFaceMirror 命令行参数, 已读取该配置并设置 HuggingFace 镜像源`"
    } else { # 使用默认设置
        `$Env:HF_ENDPOINT = `"https://hf-mirror.com`"
        Print-Msg `"使用默认 HuggingFace 镜像源`"
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
`".Trim()

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
    if ((Test-Path `"`$PSScriptRoot/disable_uv.txt`") -or (`$DisableUV)) {
        Print-Msg `"检测到 disable_uv.txt 配置文件 / -DisableUV 命令行参数, 已禁用 uv, 使用 Pip 作为 Python 包管理器`"
        `$Global:USE_UV = `$false
    } else {
        Print-Msg `"默认启用 uv 作为 Python 包管理器, 加快 Python 软件包的安装速度`"
        Print-Msg `"当 uv 安装 Python 软件包失败时, 将自动切换成 Pip 重试 Python 软件包的安装`"
        `$Global:USE_UV = `$true
        Check-uv-Version
    }
}


# 设置 CUDA 内存分配器
function Set-PyTorch-CUDA-Memory-Alloc {
    if ((!(Test-Path `"`$PSScriptRoot/disable_set_pytorch_cuda_memory_alloc.txt`")) -and (!(`$DisableCUDAMalloc))) {
        Print-Msg `"检测是否可设置 CUDA 内存分配器`"
    } else {
        Print-Msg `"检测到 disable_set_pytorch_cuda_memory_alloc.txt 配置文件 / -DisableCUDAMalloc 命令行参数, 已禁用自动设置 CUDA 内存分配器`"
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
`".Trim()

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


# 检查 SD-Trainer-Scripts 依赖完整性
function Check-SD-Trainer-Scripts-Requirements {
    `$content = `"
'''运行环境检查'''
import re
import os
import sys
import copy
import logging
import argparse
import importlib.metadata
from collections import namedtuple
from pathlib import Path
from typing import Optional, TypedDict, Union


def get_args() -> argparse.Namespace:
    '''获取命令行参数输入参数输入'''
    parser = argparse.ArgumentParser(description='运行环境检查')
    def normalized_filepath(filepath): return str(
        Path(filepath).absolute().as_posix())

    parser.add_argument(
        '--requirement-path', type=normalized_filepath, default=None, help='依赖文件路径')
    parser.add_argument('--debug-mode', action='store_true', help='显示调试信息')

    return parser.parse_args()


COMMAND_ARGS = get_args()


class ColoredFormatter(logging.Formatter):
    '''Logging 格式化'''
    COLORS = {
        'DEBUG': '\033[0;36m',          # CYAN
        'INFO': '\033[0;32m',           # GREEN
        'WARNING': '\033[0;33m',        # YELLOW
        'ERROR': '\033[0;31m',          # RED
        'CRITICAL': '\033[0;37;41m',    # WHITE ON RED
        'RESET': '\033[0m',             # RESET COLOR
    }

    def format(self, record):
        colored_record = copy.copy(record)
        levelname = colored_record.levelname
        seq = self.COLORS.get(levelname, self.COLORS['RESET'])
        colored_record.levelname = '{}{}{}'.format(
            seq, levelname, self.COLORS['RESET'])
        return super().format(colored_record)


def get_logger(
    name: str,
    level: int = logging.INFO,
) -> logging.Logger:
    '''获取 Loging 对象

    参数:
        name (str):
            Logging 名称


    '''
    logger = logging.getLogger(name)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            ColoredFormatter(
                '[%(name)s]-|%(asctime)s|-%(levelname)s: %(message)s', '%H:%M:%S'
            )
        )
        logger.addHandler(handler)

    logger.setLevel(level)
    logger.debug('Logger initialized.')

    return logger


logger = get_logger(
    'Env Checker',
    logging.DEBUG if COMMAND_ARGS.debug_mode else logging.INFO
)


# 提取版本标识符组件的正则表达式
# ref:
# https://peps.python.org/pep-0440
# https://packaging.python.org/en/latest/specifications/version-specifiers
VERSION_PATTERN = r'''
    v?
    (?:
        (?:(?P<epoch>[0-9]+)!)?                           # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
        (?P<pre>                                          # pre-release
            [-_\.]?
            (?P<pre_l>(a|b|c|rc|alpha|beta|pre|preview))
            [-_\.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>                                         # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_\.]?
                (?P<post_l>post|rev|r)
                [-_\.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>                                          # dev release
            [-_\.]?
            (?P<dev_l>dev)
            [-_\.]?
            (?P<dev_n>[0-9]+)?
        )?
    )
    (?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?       # local version
'''


# 编译正则表达式
package_version_parse_regex = re.compile(
    r'^\s*' + VERSION_PATTERN + r'\s*$',
    re.VERBOSE | re.IGNORECASE,
)


# 定义版本组件的命名元组
VersionComponent = namedtuple(
    'VersionComponent', [
        'epoch',
        'release',
        'pre_l',
        'pre_n',
        'post_n1',
        'post_l',
        'post_n2',
        'dev_l',
        'dev_n',
        'local',
        'is_wildcard'
    ]
)


def parse_version(version_str: str) -> VersionComponent:
    '''解释 Python 软件包版本号

    参数:
        version_str (str):
            Python 软件包版本号

    返回值:
        VersionComponent: 版本组件的命名元组

    异常:
        ValueError: 如果 Python 版本号不符合 PEP440 规范
    '''
    # 检测并剥离通配符
    wildcard = version_str.endswith('.*') or version_str.endswith('*')
    clean_str = version_str.rstrip(
        '*').rstrip('.') if wildcard else version_str

    match = package_version_parse_regex.match(clean_str)
    if not match:
        logger.error(f'未知的版本号字符串: {version_str}')
        raise ValueError(f'Invalid version string: {version_str}')

    components = match.groupdict()

    # 处理 release 段 (允许空字符串)
    release_str = components['release'] or '0'
    release_segments = [int(seg) for seg in release_str.split('.')]

    # 构建命名元组
    return VersionComponent(
        epoch=int(components['epoch'] or 0),
        release=release_segments,
        pre_l=components['pre_l'],
        pre_n=int(components['pre_n']) if components['pre_n'] else None,
        post_n1=int(components['post_n1']) if components['post_n1'] else None,
        post_l=components['post_l'],
        post_n2=int(components['post_n2']) if components['post_n2'] else None,
        dev_l=components['dev_l'],
        dev_n=int(components['dev_n']) if components['dev_n'] else None,
        local=components['local'],
        is_wildcard=wildcard
    )


def compare_version_objects(v1: VersionComponent, v2: VersionComponent) -> int:
    '''比较两个版本字符串 Python 软件包版本号

    参数:
        v1 (VersionComponent):
            第 1 个 Python 版本号标识符组件
        v2 (VersionComponent):
            第 2 个 Python 版本号标识符组件

    返回值:
        int: 如果版本号 1 大于 版本号 2, 则返回1, 小于则返回-1, 如果相等则返回0
    '''

    # 比较 epoch
    if v1.epoch != v2.epoch:
        return v1.epoch - v2.epoch

    # 对其 release 长度, 缺失部分补 0
    if len(v1.release) != len(v2.release):
        for _ in range(abs(len(v1.release) - len(v2.release))):
            if len(v1.release) < len(v2.release):
                v1.release.append(0)
            else:
                v2.release.append(0)

    # 比较 release
    for n1, n2 in zip(v1.release, v2.release):
        if n1 != n2:
            return n1 - n2
    # 如果 release 长度不同，较短的版本号视为较小 ?
    # 但是这样是行不通的! 比如 0.15.0 和 0.15, 处理后就会变成 [0, 15, 0] 和 [0, 15]
    # 计算结果就会变成 len([0, 15, 0]) > len([0, 15])
    # 但 0.15.0 和 0.15 实际上是一样的版本
    # if len(v1.release) != len(v2.release):
    #     return len(v1.release) - len(v2.release)

    # 比较 pre-release
    if v1.pre_l and not v2.pre_l:
        return -1  # pre-release 小于正常版本
    elif not v1.pre_l and v2.pre_l:
        return 1
    elif v1.pre_l and v2.pre_l:
        pre_order = {
            'a': 0,
            'b': 1,
            'c': 2,
            'rc': 3,
            'alpha': 0,
            'beta': 1,
            'pre': 0,
            'preview': 0
        }
        if pre_order[v1.pre_l] != pre_order[v2.pre_l]:
            return pre_order[v1.pre_l] - pre_order[v2.pre_l]
        elif v1.pre_n is not None and v2.pre_n is not None:
            return v1.pre_n - v2.pre_n
        elif v1.pre_n is None and v2.pre_n is not None:
            return -1
        elif v1.pre_n is not None and v2.pre_n is None:
            return 1

    # 比较 post-release
    if v1.post_n1 is not None:
        post_n1 = v1.post_n1
    elif v1.post_l:
        post_n1 = int(v1.post_n2) if v1.post_n2 else 0
    else:
        post_n1 = 0

    if v2.post_n1 is not None:
        post_n2 = v2.post_n1
    elif v2.post_l:
        post_n2 = int(v2.post_n2) if v2.post_n2 else 0
    else:
        post_n2 = 0

    if post_n1 != post_n2:
        return post_n1 - post_n2

    # 比较 dev-release
    if v1.dev_l and not v2.dev_l:
        return -1  # dev-release 小于 post-release 或正常版本
    elif not v1.dev_l and v2.dev_l:
        return 1
    elif v1.dev_l and v2.dev_l:
        if v1.dev_n is not None and v2.dev_n is not None:
            return v1.dev_n - v2.dev_n
        elif v1.dev_n is None and v2.dev_n is not None:
            return -1
        elif v1.dev_n is not None and v2.dev_n is None:
            return 1

    # 比较 local version
    if v1.local and not v2.local:
        return -1  # local version 小于 dev-release 或正常版本
    elif not v1.local and v2.local:
        return 1
    elif v1.local and v2.local:
        local1 = v1.local.split('.')
        local2 = v2.local.split('.')
        # 和 release 的处理方式一致, 对其 local version 长度, 缺失部分补 0
        if len(local1) != len(local2):
            for _ in range(abs(len(local1) - len(local2))):
                if len(local1) < len(local2):
                    local1.append(0)
                else:
                    local2.append(0)
        for l1, l2 in zip(local1, local2):
            if l1.isdigit() and l2.isdigit():
                l1, l2 = int(l1), int(l2)
            if l1 != l2:
                return (l1 > l2) - (l1 < l2)
        return len(local1) - len(local2)

    return 0  # 版本相同


def compare_versions(version1: str, version2: str) -> int:
    '''比较两个版本字符串 Python 软件包版本号

    参数:
        version1 (str):
            版本号 1
        version2 (str):
            版本号 2

    返回值:
        int: 如果版本号 1 大于 版本号 2, 则返回1, 小于则返回-1, 如果相等则返回0
    '''
    v1 = parse_version(version1)
    v2 = parse_version(version2)
    return compare_version_objects(v1, v2)


def compatible_version_matcher(spec_version: str):
    '''PEP 440 兼容性版本匹配 (~= 操作符)

    返回值:
        _is_compatible(version_str: str) -> bool: 一个接受 version_str (str) 参数的判断函数
    '''
    # 解析规范版本
    spec = parse_version(spec_version)

    # 获取有效release段（去除末尾的零）
    clean_release = []
    for num in spec.release:
        if num != 0 or (clean_release and clean_release[-1] != 0):
            clean_release.append(num)

    # 确定最低版本和前缀匹配规则
    if len(clean_release) == 0:
        logger.error('解析到错误的兼容性发行版本号')
        raise ValueError('Invalid version for compatible release clause')

    # 生成前缀匹配模板（忽略后缀）
    prefix_length = len(clean_release) - 1
    if prefix_length == 0:
        # 处理类似 ~= 2 的情况（实际 PEP 禁止，但这里做容错）
        prefix_pattern = [spec.release[0]]
        min_version = parse_version(f'{spec.release[0]}')
    else:
        prefix_pattern = list(spec.release[:prefix_length])
        min_version = spec

    def _is_compatible(version_str: str) -> bool:
        target = parse_version(version_str)

        # 主版本前缀检查
        target_prefix = target.release[:len(prefix_pattern)]
        if target_prefix != prefix_pattern:
            return False

        # 最低版本检查 (自动忽略 pre/post/dev 后缀)
        return compare_version_objects(target, min_version) >= 0

    return _is_compatible


def version_match(spec: str, version: str) -> bool:
    '''PEP 440 版本前缀匹配

    参数:
        spec (str): 版本匹配表达式 (e.g. '1.1.*')
        version (str): 需要检测的实际版本号 (e.g. '1.1a1')

    返回值:
        bool: 是否匹配
    '''
    # 分离通配符和本地版本
    spec_parts = spec.split('+', 1)
    spec_main = spec_parts[0].rstrip('.*')  # 移除通配符
    has_wildcard = spec.endswith('.*') and '+' not in spec

    # 解析规范版本 (不带通配符)
    try:
        spec_ver = parse_version(spec_main)
    except ValueError:
        return False

    # 解析目标版本 (忽略本地版本)
    target_ver = parse_version(version.split('+', 1)[0])

    # 前缀匹配规则
    if has_wildcard:
        # 生成补零后的 release 段
        spec_release = spec_ver.release.copy()
        while len(spec_release) < len(target_ver.release):
            spec_release.append(0)

        # 比较前 N 个 release 段 (N 为规范版本长度)
        return (
            target_ver.release[:len(spec_ver.release)] == spec_ver.release
            and target_ver.epoch == spec_ver.epoch
        )
    else:
        # 严格匹配时使用原比较函数
        return compare_versions(spec_main, version) == 0


def is_v1_ge_v2(v1: str, v2: str) -> bool:
    '''查看 Python 版本号 v1 是否大于或等于 v2

    参数:
        v1 (str):
            第 1 个 Python 软件包版本号

        v2 (str):
            第 2 个 Python 软件包版本号

    返回值:
        bool: 如果 v1 版本号大于或等于 v2 版本号则返回True
        e.g.:
            1.1, 1.0 -> True
            1.0, 1.0 -> True
            0.9, 1.0 -> False
    '''
    return compare_versions(v1, v2) >= 0


def is_v1_gt_v2(v1: str, v2: str) -> bool:
    '''查看 Python 版本号 v1 是否大于 v2

    参数:
        v1 (str):
            第 1 个 Python 软件包版本号

        v2 (str):
            第 2 个 Python 软件包版本号

    返回值:
        bool: 如果 v1 版本号大于 v2 版本号则返回True
        e.g.:
            1.1, 1.0 -> True
            1.0, 1.0 -> False
    '''
    return compare_versions(v1, v2) > 0


def is_v1_eq_v2(v1: str, v2: str) -> bool:
    '''查看 Python 版本号 v1 是否等于 v2

    参数:
        v1 (str):
            第 1 个 Python 软件包版本号

        v2 (str):
            第 2 个 Python 软件包版本号

    返回值:
        bool: 如果 v1 版本号等于 v2 版本号则返回True
        e.g.:
            1.0, 1.0 -> True
            0.9, 1.0 -> False
            1.1, 1.0 -> False
    '''
    return compare_versions(v1, v2) == 0


def is_v1_lt_v2(v1: str, v2: str) -> bool:
    '''查看 Python 版本号 v1 是否小于 v2

    参数:
        v1 (str):
            第 1 个 Python 软件包版本号

        v2 (str):
            第 2 个 Python 软件包版本号

    返回值:
        bool: 如果 v1 版本号小于 v2 版本号则返回True
        e.g.:
            0.9, 1.0 -> True
            1.0, 1.0 -> False
    '''
    return compare_versions(v1, v2) < 0


def is_v1_le_v2(v1: str, v2: str) -> bool:
    '''查看 Python 版本号 v1 是否小于或等于 v2

    参数:
        v1 (str):
            第 1 个 Python 软件包版本号

        v2 (str):
            第 2 个 Python 软件包版本号

    返回值:
        bool: 如果 v1 版本号小于或等于 v2 版本号则返回True
        e.g.:
            0.9, 1.0 -> True
            1.0, 1.0 -> True
            1.1, 1.0 -> False
    '''
    return compare_versions(v1, v2) <= 0


def is_v1_c_eq_v2(v1: str, v2: str) -> bool:
    '''查看 Python 版本号 v1 是否大于等于 v2, (兼容性版本匹配)

    参数:
        v1 (str):
            第 1 个 Python 软件包版本号, 该版本由 ~= 符号指定

        v2 (str):
            第 2 个 Python 软件包版本号

    返回值:
        bool: 如果 v1 版本号等于 v2 版本号则返回True
        e.g.:
            1.0*, 1.0a1 -> True
            0.9*, 1.0 -> False
    '''
    func = compatible_version_matcher(v1)
    return func(v2)


def version_string_is_canonical(version: str) -> bool:
    '''判断版本号标识符是否符合标准

    参数:
        version (str):
            版本号字符串

    返回值:
        bool: 如果版本号标识符符合 PEP 440 标准, 则返回True

    '''
    return re.match(
        r'^([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*((a|b|rc)(0|[1-9][0-9]*))?(\.post(0|[1-9][0-9]*))?(\.dev(0|[1-9][0-9]*))?$',
        version,
    ) is not None


def is_package_has_version(package: str) -> bool:
    '''检查 Python 软件包是否指定版本号

    参数:
        package (str):
            Python 软件包名

    返回值:
        bool: 如果 Python 软件包存在版本声明, 如torch==2.3.0, 则返回True
    '''
    return package != (
        package.replace('===', '')
        .replace('~=', '')
        .replace('!=', '')
        .replace('<=', '')
        .replace('>=', '')
        .replace('<', '')
        .replace('>', '')
        .replace('==', '')
    )


def get_package_name(package: str) -> str:
    '''获取 Python 软件包的包名, 去除末尾的版本声明

    参数:
        package (str):
            Python 软件包名

    返回值:
        str: 返回去除版本声明后的 Python 软件包名
    '''
    return (
        package.split('===')[0]
        .split('~=')[0]
        .split('!=')[0]
        .split('<=')[0]
        .split('>=')[0]
        .split('<')[0]
        .split('>')[0]
        .split('==')[0]
        .strip()
    )


def get_package_version(package: str) -> str:
    '''获取 Python 软件包的包版本号

    参数:
        package (str):
            Python 软件包名

    返回值:
        str: 返回 Python 软件包的包版本号
    '''
    return (
        package.split('===').pop()
        .split('~=').pop()
        .split('!=').pop()
        .split('<=').pop()
        .split('>=').pop()
        .split('<').pop()
        .split('>').pop()
        .split('==').pop()
        .strip()
    )


WHEEL_PATTERN = r'''
    ^                           # 字符串开始
    (?P<distribution>[^-]+)     # 包名 (匹配第一个非连字符段)
    -                           # 分隔符
    (?:                         # 版本号和可选构建号组合
        (?P<version>[^-]+)      # 版本号 (至少一个非连字符段)
        (?:-(?P<build>\d\w*))?  # 可选构建号 (以数字开头)
    )
    -                           # 分隔符
    (?P<python>[^-]+)           # Python 版本标签
    -                           # 分隔符
    (?P<abi>[^-]+)              # ABI 标签
    -                           # 分隔符
    (?P<platform>[^-]+)         # 平台标签
    \.whl$                      # 固定后缀
'''


def parse_wheel_filename(filename: str) -> str:
    '''解析 Python wheel 文件名并返回 distribution 名称

    参数:
        filename (str):
            wheel 文件名, 例如 pydantic-1.10.15-py3-none-any.whl

    返回值:
        str: distribution 名称, 例如 pydantic

    异常:
        ValueError: 如果文件名不符合 PEP491 规范
    '''
    match = re.fullmatch(WHEEL_PATTERN, filename, re.VERBOSE)
    if not match:
        logger.error('未知的 Wheel 文件名: %s', filename)
        raise ValueError(f'Invalid wheel filename: {filename}')
    return match.group('distribution')


def parse_wheel_version(filename: str) -> str:
    '''解析 Python wheel 文件名并返回 version 名称

    参数:
        filename (str):
            wheel 文件名, 例如 pydantic-1.10.15-py3-none-any.whl

    返回值:
        str: version 名称, 例如 1.10.15

    异常:
        ValueError: 如果文件名不符合 PEP491 规范
    '''
    match = re.fullmatch(WHEEL_PATTERN, filename, re.VERBOSE)
    if not match:
        logger.error('未知的 Wheel 文件名: %s', filename)
        raise ValueError(f'Invalid wheel filename: {filename}')
    return match.group('version')


def parse_wheel_to_package_name(filename: str) -> str:
    '''解析 Python wheel 文件名并返回 <distribution>==<version>

    参数:
        filename (str):
            wheel 文件名, 例如 pydantic-1.10.15-py3-none-any.whl

    返回值:
        str: <distribution>==<version> 名称, 例如 pydantic==1.10.15
    '''
    distribution = parse_wheel_filename(filename)
    version = parse_wheel_version(filename)
    return f'{distribution}=={version}'


def remove_optional_dependence_from_package(filename: str) -> str:
    '''移除 Python 软件包声明中可选依赖

    参数:
        filename (str):
            Python 软件包名

    返回值:
        str: 移除可选依赖后的软件包名, e.g. diffusers[torch]==0.10.2 -> diffusers==0.10.2
    '''
    return re.sub(r'\[.*?\]', '', filename)


def parse_requirement_list(requirements: list) -> list:
    '''将 Python 软件包声明列表解析成标准 Python 软件包名列表

    参数:
        requirements (list):
            Python 软件包名声明列表
            e.g:
            python
            requirements = [
                'torch==2.3.0',
                'diffusers[torch]==0.10.2',
                'NUMPY',
                '-e .',
                '--index-url https://pypi.python.org/simple',
                '--extra-index-url https://download.pytorch.org/whl/cu124',
                '--find-links https://download.pytorch.org/whl/torch_stable.html',
                '-e git+https://github.com/Nerogar/mgds.git@2c67a5a#egg=mgds',
                'git+https://github.com/WASasquatch/img2texture.git',
                'https://github.com/Panchovix/pydantic-fixreforge/releases/download/main_v1/pydantic-1.10.15-py3-none-any.whl',
                'prodigy-plus-schedule-free==1.9.1 # prodigy+schedulefree optimizer',
                'protobuf<5,>=4.25.3',
            ]
            

    返回值:
        list: 将 Python 软件包名声明列表解析成标准声明列表
        e.g. 上述例子中的软件包名声明列表将解析成:
        python
            requirements = [
                'torch==2.3.0',
                'diffusers==0.10.2',
                'numpy',
                'mgds',
                'img2texture',
                'pydantic==1.10.15',
                'prodigy-plus-schedule-free==1.9.1',
                'protobuf<5',
                'protobuf>=4.25.3',
            ]
            
    '''
    package_list = []
    canonical_package_list = []
    requirement: str
    for requirement in requirements:
        requirement = requirement.strip()
        logger.debug('原始 Python 软件包名: %s', requirement)

        if (
            requirement is None
            or requirement == ''
            or requirement.startswith('#')
            or '# skip_verify' in requirement
            or requirement.startswith('--index-url')
            or requirement.startswith('--extra-index-url')
            or requirement.startswith('--find-links')
            or requirement.startswith('-e .')
        ):
            continue

        # -e git+https://github.com/Nerogar/mgds.git@2c67a5a#egg=mgds -> mgds
        # git+https://github.com/WASasquatch/img2texture.git -> img2texture
        # git+https://github.com/deepghs/waifuc -> waifuc
        if requirement.startswith('-e git+http') or requirement.startswith('git+http'):
            egg_match = re.search(r'egg=([^#&]+)', requirement)
            if egg_match:
                package_list.append(egg_match.group(1).split('-')[0])
                continue

            package_name = os.path.basename(requirement)
            package_name = package_name.split(
                '.git')[0] if package_name.endswith('.git') else package_name
            package_list.append(package_name)
            continue

        # https://github.com/Panchovix/pydantic-fixreforge/releases/download/main_v1/pydantic-1.10.15-py3-none-any.whl -> pydantic==1.10.15
        if requirement.startswith('https://') or requirement.startswith('http://'):
            package_name = parse_wheel_to_package_name(
                os.path.basename(requirement))
            package_list.append(package_name)
            continue

        # 常规 Python 软件包声明
        # prodigy-plus-schedule-free==1.9.1 # prodigy+schedulefree optimizer -> prodigy-plus-schedule-free==1.9.1
        cleaned_requirements = re.sub(
            r'\s*#.*$', '', requirement).strip().split(',')
        if len(cleaned_requirements) > 1:
            package_name = get_package_name(cleaned_requirements[0].strip())
            for package_name_with_version_marked in cleaned_requirements:
                version_symbol = str.replace(
                    package_name_with_version_marked, package_name, '', 1)
                format_package_name = remove_optional_dependence_from_package(
                    f'{package_name}{version_symbol}'.strip())
                package_list.append(format_package_name)
        else:
            format_package_name = remove_optional_dependence_from_package(
                cleaned_requirements[0].strip())
            package_list.append(format_package_name)

    # 处理包名大小写并统一成小写
    for p in package_list:
        p: str = p.lower().strip()
        logger.debug('预处理后的 Python 软件包名: %s', p)
        if not is_package_has_version(p):
            logger.debug('%s 无版本声明', p)
            canonical_package_list.append(p)
            continue

        if version_string_is_canonical(get_package_version(p)):
            canonical_package_list.append(p)
        else:
            logger.debug('%s 软件包名的版本不符合标准', p)

    return canonical_package_list


def remove_duplicate_object_from_list(origin: list) -> list:
    '''对list进行去重

    参数:
        origin (list):
            原始的list

    返回值:
        list: 去重后的list, e.g. [1, 2, 3, 2] -> [1, 2, 3]
    '''
    return list(set(origin))


def read_packages_from_requirements_file(file_path: Union[str, Path]) -> list:
    '''从 requirements.txt 文件中读取 Python 软件包版本声明列表

    参数:
        file_path (str, Path):
            requirements.txt 文件路径

    返回值:
        list: 从 requirements.txt 文件中读取的 Python 软件包声明列表
    '''
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.readlines()
    except Exception as e:
        logger.error('打开 %s 时出现错误: %s\n请检查文件是否出现损坏', file_path, e)
        return []


def get_package_version_from_library(package_name: str) -> Union[str, None]:
    '''获取已安装的 Python 软件包版本号

    参数:
        package_name (str):

    返回值:
        (str | None): 如果获取到 Python 软件包版本号则返回版本号字符串, 否则返回None
    '''
    try:
        ver = importlib.metadata.version(package_name)
    except:
        ver = None

    if ver is None:
        try:
            ver = importlib.metadata.version(package_name.lower())
        except:
            ver = None

    if ver is None:
        try:
            ver = importlib.metadata.version(package_name.replace('_', '-'))
        except:
            ver = None

    return ver


def is_package_installed(package: str) -> bool:
    '''判断 Python 软件包是否已安装在环境中

    参数:
        package (str):
            Python 软件包名

    返回值:
        bool: 如果 Python 软件包未安装或者未安装正确的版本, 则返回False
    '''
    # 分割 Python 软件包名和版本号
    if '===' in package:
        pkg_name, pkg_version = [x.strip() for x in package.split('===')]
    elif '~=' in package:
        pkg_name, pkg_version = [x.strip() for x in package.split('~=')]
    elif '!=' in package:
        pkg_name, pkg_version = [x.strip() for x in package.split('!=')]
    elif '<=' in package:
        pkg_name, pkg_version = [x.strip() for x in package.split('<=')]
    elif '>=' in package:
        pkg_name, pkg_version = [x.strip() for x in package.split('>=')]
    elif '<' in package:
        pkg_name, pkg_version = [x.strip() for x in package.split('<')]
    elif '>' in package:
        pkg_name, pkg_version = [x.strip() for x in package.split('>')]
    elif '==' in package:
        pkg_name, pkg_version = [x.strip() for x in package.split('==')]
    else:
        pkg_name, pkg_version = package.strip(), None

    env_pkg_version = get_package_version_from_library(pkg_name)
    logger.debug(
        '已安装 Python 软件包检测: pkg_name: %s, env_pkg_version: %s, pkg_version: %s',
        pkg_name, env_pkg_version, pkg_version
    )

    if env_pkg_version is None:
        return False

    if pkg_version is not None:
        # ok = env_pkg_version === / == pkg_version
        if '===' in package or '==' in package:
            logger.debug('包含条件: === / ==')
            if is_v1_eq_v2(env_pkg_version, pkg_version):
                logger.debug('%s == %s', env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version ~= pkg_version
        if '~=' in package:
            logger.debug('包含条件: ~=')
            if is_v1_c_eq_v2(pkg_version, env_pkg_version):
                logger.debug('%s ~= %s', pkg_version, env_pkg_version)
                return True

        # ok = env_pkg_version != pkg_version
        if '!=' in package:
            logger.debug('包含条件: !=')
            if not is_v1_eq_v2(env_pkg_version, pkg_version):
                logger.debug('%s != %s', env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version <= pkg_version
        if '<=' in package:
            logger.debug('包含条件: <=')
            if is_v1_le_v2(env_pkg_version, pkg_version):
                logger.debug('%s <= %s', env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version >= pkg_version
        if '>=' in package:
            logger.debug('包含条件: >=')
            if is_v1_ge_v2(env_pkg_version, pkg_version):
                logger.debug('%s >= %s', env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version < pkg_version
        if '<' in package:
            logger.debug('包含条件: <')
            if is_v1_lt_v2(env_pkg_version, pkg_version):
                logger.debug('%s < %s', env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version > pkg_version
        if '>' in package:
            logger.debug('包含条件: >')
            if is_v1_gt_v2(env_pkg_version, pkg_version):
                logger.debug('%s > %s', env_pkg_version, pkg_version)
                return True

        logger.debug('%s 需要安装', package)
        return False

    return True


def validate_requirements(requirement_path: Union[str, Path]) -> bool:
    '''检测环境依赖是否完整

    参数:
        requirement_path (str, Path):
            依赖文件路径

    返回值:
        bool: 如果有缺失依赖则返回False
    '''
    origin_requires = read_packages_from_requirements_file(requirement_path)
    requires = parse_requirement_list(origin_requires)
    for package in requires:
        if not is_package_installed(package):
            return False

    return True


def main() -> None:
    requirement_path = COMMAND_ARGS.requirement_path

    if not os.path.isfile(requirement_path):
        logger.error('依赖文件未找到, 无法检查运行环境')
        sys.exit(1)

    logger.debug('检测运行环境中')
    print(validate_requirements(requirement_path))
    logger.debug('环境检查完成')


if __name__ == '__main__':
    main()
`".Trim()

    Print-Msg `"检查 SD-Trainer-Scripts 内核依赖完整性中`"
    if (!(Test-Path `"`$Env:CACHE_HOME`")) {
        New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" > `$null
    }
    Set-Content -Encoding UTF8 -Path `"`$Env:CACHE_HOME/check_sd_trainer_requirement.py`" -Value `$content

    `$dep_path = `"`$PSScriptRoot/lora-scripts/requirements_versions.txt`"
    if (!(Test-Path `"`$dep_path`")) {
        `$dep_path = `"`$PSScriptRoot/lora-scripts/requirements.txt`"
    }
    if (!(Test-Path `"`$dep_path`")) {
        Print-Msg `"未检测到 SD-Trainer-Scripts 依赖文件, 跳过依赖完整性检查`"
        return
    }

    `$status = `$(python `"`$Env:CACHE_HOME/check_sd_trainer_requirement.py`" --requirement-path `"`$dep_path`")

    if (`$status -eq `"False`") {
        Print-Msg `"检测到 SD-Trainer-Scripts 内核有依赖缺失, 安装 SD-Trainer-Scripts 依赖中`"
        if (`$USE_UV) {
            uv pip install -r `"`$PSScriptRoot/sd-scripts/requirements.txt`"
            if (!(`$?)) {
                Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
                python -m pip install -r `"`$PSScriptRoot/sd-scripts/requirements.txt`"
            }
        } else {
            python -m pip install -r `"`$PSScriptRoot/sd-scripts/requirements.txt`"
        }
        if (`$?) {
            Print-Msg `"SD-Trainer-Scripts 依赖安装成功`"
        } else {
            Print-Msg `"SD-Trainer-Scripts 依赖安装失败, 这将会导致 SD-Trainer-Scripts 缺失依赖无法正常运行`"
        }
    } else {
        Print-Msg `"SD-Trainer-Scripts 无缺失依赖`"
    }
}


# 检查 Numpy 版本
function Check-Numpy-Version {
    `$content = `"
import importlib.metadata
from importlib.metadata import version

try:
    ver = int(version('numpy').split('.')[0])
except:
    ver = -1

if ver > 1:
    print(True)
else:
    print(False)
`".Trim()

    Print-Msg `"检查 Numpy 版本中`"
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


# 检测 Microsoft Visual C++ Redistributable
function Check-MS-VCPP-Redistributable {
    Print-Msg `"检测 Microsoft Visual C++ Redistributable 是否缺失`"
    if ([string]::IsNullOrEmpty(`$Env:SYSTEMROOT)) {
        `$vc_runtime_dll_path = `"C:/Windows/System32/vcruntime140_1.dll`"
    } else {
        `$vc_runtime_dll_path = `"`$Env:SYSTEMROOT/System32/vcruntime140_1.dll`"
    }

    if (Test-Path `"`$vc_runtime_dll_path`") {
        Print-Msg `"Microsoft Visual C++ Redistributable 未缺失`"
    } else {
        Print-Msg `"检测到 Microsoft Visual C++ Redistributable 缺失, 这可能导致 PyTorch 无法正常识别 GPU 导致报错`"
        Print-Msg `"Microsoft Visual C++ Redistributable 下载: https://aka.ms/vs/17/release/vc_redist.x64.exe`"
        Print-Msg `"请下载并安装 Microsoft Visual C++ Redistributable 后重新启动`"
        Start-Sleep -Seconds 2
    }
}


# 检查 SD-Trainer-Script 运行环境
function Check-SD-Trainer-Script-Env {
    if ((Test-Path `"`$PSScriptRoot/disable_check_env.txt`") -or (`$DisableEnvCheck)) {
        Print-Msg `"检测到 disable_check_env.txt 配置文件 / -DisableEnvCheck 命令行参数, 已禁用 SD-Trainer-Script 运行环境检测, 这可能会导致 SD-Trainer-Script 运行环境中存在的问题无法被发现并解决`"
        return
    } else {
        Print-Msg `"检查 SD-Trainer-Script 运行环境中`"
    }

    Check-SD-Trainer-Scripts-Requirements
    Fix-PyTorch
    Check-Numpy-Version
    Check-MS-VCPP-Redistributable
    Print-Msg `"SD-Trainer-Script 运行环境检查完成`"
}


function Main {
    Print-Msg `"初始化中`"
    Get-SD-Trainer-Script-Installer-Version
    Get-SD-Trainer-Script-Installer-Cmdlet-Help
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"SD-Trainer-Script Installer 构建模式已启用, 跳过 SD-Trainer-Script Installer 更新检查`"
    } else {
        Check-SD-Trainer-Script-Installer-Update
    }
    Set-HuggingFace-Mirror
    Set-uv
    PyPI-Mirror-Status
    `$current_path = `$(Get-Location).ToString()
    Set-Location `"`$PSScriptRoot/sd-scripts`"
    Check-SD-Trainer-Script-Env
    Set-Location `"`$current_path`"
    Set-PyTorch-CUDA-Memory-Alloc

    `$Global:ROOT_PATH = `$PSScriptRoot
    `$Global:SD_SCRIPTS_PATH = [System.IO.Path]::GetFullPath(`"`$ROOT_PATH/sd-scripts`")
    `$Global:DATASET_PATH = [System.IO.Path]::GetFullPath(`"`$ROOT_PATH/datasets`")
    `$Global:MODEL_PATH = [System.IO.Path]::GetFullPath(`"`$ROOT_PATH/models`")
    `$Global:OUTPUT_PATH = [System.IO.Path]::GetFullPath(`"`$ROOT_PATH/outputs`")
    `$Global:GIT_EXEC = [System.IO.Path]::GetFullPath(`$(Get-Command git -ErrorAction SilentlyContinue).Source)
    `$Global:PYTHON_EXEC = [System.IO.Path]::GetFullPath(`$(Get-Command python -ErrorAction SilentlyContinue).Source)

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
".Trim()

    if (Test-Path "$InstallPath/init.ps1") {
        Print-Msg "更新 init.ps1 中"
    } else {
        Print-Msg "生成 init.ps1 中"
    }
    Set-Content -Encoding $PS_SCRIPT_ENCODING -Path "$InstallPath/init.ps1" -Value $content
}


# 更新脚本
function Write-Update-Script {
    $content = "
param (
    [switch]`$Help,
    [switch]`$BuildMode,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableUpdate,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisableGithubMirror,
    [string]`$UseCustomGithubMirror
)
# SD-Trainer-Script Installer 版本和检查更新间隔
`$SD_TRAINER_SCRIPT_INSTALLER_VERSION = $SD_TRAINER_SCRIPT_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# PyPI 镜像源
`$PIP_INDEX_ADDR = `"$PIP_INDEX_ADDR`"
`$PIP_INDEX_ADDR_ORI = `"$PIP_INDEX_ADDR_ORI`"
`$PIP_EXTRA_INDEX_ADDR = `"$PIP_EXTRA_INDEX_ADDR`"
`$PIP_EXTRA_INDEX_ADDR_ORI = `"$PIP_EXTRA_INDEX_ADDR_ORI`"
`$PIP_FIND_ADDR = `"$PIP_FIND_ADDR`"
`$PIP_FIND_ADDR_ORI = `"$PIP_FIND_ADDR_ORI`"
`$USE_PIP_MIRROR = if ((!(Test-Path `"`$PSScriptRoot/disable_pypi_mirror.txt`")) -and (!(`$DisablePyPIMirror))) { `$true } else { `$false }
`$PIP_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_INDEX_ADDR } else { `$PIP_INDEX_ADDR_ORI }
`$PIP_EXTRA_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `"`$PIP_EXTRA_INDEX_ADDR_ORI `$PIP_EXTRA_INDEX_ADDR`" } else { `$PIP_EXTRA_INDEX_ADDR_ORI }
`$PIP_FIND_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_FIND_ADDR } else { `$PIP_FIND_ADDR_ORI }
`$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_XPU = `"$PIP_EXTRA_INDEX_MIRROR_XPU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118 = `"$PIP_EXTRA_INDEX_MIRROR_CU118`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
`$PIP_EXTRA_INDEX_MIRROR_CU126 = `"$PIP_EXTRA_INDEX_MIRROR_CU126`"
`$PIP_EXTRA_INDEX_MIRROR_CU128 = `"$PIP_EXTRA_INDEX_MIRROR_CU128`"
`$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU118_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU124_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU126_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU128_NJU`"
# Github 镜像源
`$GITHUB_MIRROR_LIST = @(
    `"https://ghfast.top/https://github.com`",
    `"https://mirror.ghproxy.com/https://github.com`",
    `"https://ghproxy.net/https://github.com`",
    `"https://gh.api.99988866.xyz/https://github.com`",
    `"https://gh-proxy.com/https://github.com`",
    `"https://ghps.cc/https://github.com`",
    `"https://gh.idayer.com/https://github.com`",
    `"https://ghproxy.1888866.xyz/github.com`",
    `"https://slink.ltd/https://github.com`",
    `"https://github.boki.moe/github.com`",
    `"https://github.moeyy.xyz/https://github.com`",
    `"https://gh-proxy.net/https://github.com`",
    `"https://gh-proxy.ygxz.in/https://github.com`",
    `"https://wget.la/https://github.com`",
    `"https://kkgithub.com`",
    `"https://gitclone.com/github.com`"
)
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# Aria2 最低版本
`$ARIA2_MINIMUM_VER = `"$ARIA2_MINIMUM_VER`"
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
`$Env:PIP_EXTRA_INDEX_URL = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`".Trim() } else { `$PIP_EXTRA_INDEX_MIRROR }
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_DEFAULT_INDEX = `"`$PIP_INDEX_MIRROR`"
`$Env:UV_INDEX = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`".Trim() } else { `$PIP_EXTRA_INDEX_MIRROR }
`$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:UV_CONCURRENT_DOWNLOADS = 50
`$Env:UV_INDEX_STRATEGY = `"unsafe-best-match`"
`$Env:UV_CONFIG_FILE = `"nul`"
`$Env:PIP_CONFIG_FILE = `"nul`"
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$Env:PIP_NO_WARN_SCRIPT_LOCATION = 0
`$Env:PIP_TIMEOUT = 30
`$Env:PIP_RETRIES = 5
`$Env:PIP_PREFER_BINARY = 1
`$Env:PIP_YES = 1
`$Env:PYTHONUTF8 = 1
`$Env:PYTHONIOENCODING = `"utf-8`"
`$Env:PYTHONUNBUFFERED = 1
`$Env:PYTHONNOUSERSITE = 1
`$Env:PYTHONFAULTHANDLER = 1
`$Env:GRADIO_ANALYTICS_ENABLED = `"False`"
`$Env:HF_HUB_DISABLE_SYMLINKS_WARNING = 1
`$Env:BITSANDBYTES_NOWELCOME = 1
`$Env:ClDeviceGlobalMemSizeAvailablePercent = 100
`$Env:CUDA_MODULE_LOADING = `"LAZY`"
`$Env:TORCH_CUDNN_V8_API_ENABLED = 1
`$Env:USE_LIBUV = 0
`$Env:SYCL_CACHE_PERSISTENT = 1
`$Env:TF_CPP_MIN_LOG_LEVEL = 3
`$Env:SAFETENSORS_FAST_GPU = 1
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
`$Env:TORCHINDUCTOR_CACHE_DIR = `"`$PSScriptRoot/cache/torchinductor`"
`$Env:TRITON_CACHE_DIR = `"`$PSScriptRoot/cache/triton`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 帮助信息
function Get-SD-Trainer-Script-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\update.ps1 [-Help] [-BuildMode] [-DisablePyPIMirror] [-DisableUpdate] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像源地址>]

参数:
    -Help
        获取 SD-Trainer-Script Installer 的帮助信息

    -BuildMode
        启用 SD-Trainer-Script Installer 构建模式

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableUpdate
        禁用 SD-Trainer-Script Installer 更新检查

    -DisableProxy
        禁用 SD-Trainer-Script Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableGithubMirror
        禁用 SD-Trainer-Script Installer 自动设置 Github 镜像源

    -UseCustomGithubMirror <Github 镜像站地址>
        使用自定义的 Github 镜像站地址
        可用的 Github 镜像站地址:
            https://ghfast.top/https://github.com
            https://mirror.ghproxy.com/https://github.com
            https://ghproxy.net/https://github.com
            https://gh.api.99988866.xyz/https://github.com
            https://gh-proxy.com/https://github.com
            https://ghps.cc/https://github.com
            https://gh.idayer.com/https://github.com
            https://ghproxy.1888866.xyz/github.com
            https://slink.ltd/https://github.com
            https://github.boki.moe/github.com
            https://github.moeyy.xyz/https://github.com
            https://gh-proxy.net/https://github.com
            https://gh-proxy.ygxz.in/https://github.com
            https://wget.la/https://github.com
            https://kkgithub.com
            https://gitclone.com/github.com


更多的帮助信息请阅读 SD-Trainer-Script Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


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

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 SD-Trainer-Script Installer 的自动检查更新功能`"
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
    } else {
        return
    }

    ForEach (`$url in `$urls) {
        Print-Msg `"检查 SD-Trainer-Script Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" |
                Select-String -Pattern `"SD_TRAINER_SCRIPT_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 SD-Trainer-Script Installer 更新中`"
            } else {
                Print-Msg `"检查 SD-Trainer-Script Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -gt `$SD_TRAINER_SCRIPT_INSTALLER_VERSION) {
        Print-Msg `"检测到 SD-Trainer-Script Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"==================================================>`").Trim()
        if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
            Print-Msg `"调用 SD-Trainer-Script Installer 进行更新中`"
            . `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
            `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
            Print-Msg `"更新结束, 重新启动 SD-Trainer-Script Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
            Invoke-Expression `"& ```"`$PSCommandPath```" `$raw_params`"
            exit 0
        } else {
            Print-Msg `"跳过 SD-Trainer-Script Installer 更新`"
        }
    } else {
        Print-Msg `"SD-Trainer-Script Installer 已是最新版本`"
    }
}


# 代理配置
function Set-Proxy {
    `$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    # 检测是否禁用自动设置镜像源
    if ((Test-Path `"`$PSScriptRoot/disable_proxy.txt`") -or (`$DisableProxy)) {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件 / -DisableProxy 命令行参数, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if ((Test-Path `"`$PSScriptRoot/proxy.txt`") -or (`$UseCustomProxy)) { # 本地存在代理配置
        if (`$UseCustomProxy) {
            `$proxy_value = `$UseCustomProxy
        } else {
            `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        }
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件 / -UseCustomProxy 命令行参数, 已读取代理配置文件并设置代理`"
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

    if ((Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") -or (`$DisableGithubMirror)) { # 禁用 Github 镜像源
        Print-Msg `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件 / -DisableGithubMirror 命令行参数, 禁用 Github 镜像源`"
        return
    }

    # 使用自定义 Github 镜像源
    if ((Test-Path `"`$PSScriptRoot/gh_mirror.txt`") -or (`$UseCustomGithubMirror)) {
        if (`$UseCustomGithubMirror) {
            `$github_mirror = `$UseCustomGithubMirror
        } else {
            `$github_mirror = Get-Content `"`$PSScriptRoot/gh_mirror.txt`"
        }
        git config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
        Print-Msg `"检测到本地存在 gh_mirror.txt Github 镜像源配置文件 / -UseCustomGithubMirror 命令行参数, 已读取 Github 镜像源配置文件并设置 Github 镜像源`"
        return
    }

    # 自动检测可用镜像源并使用
    `$status = 0
    ForEach(`$i in `$GITHUB_MIRROR_LIST) {
        Print-Msg `"测试 Github 镜像源: `$i`"
        if (Test-Path `"`$Env:CACHE_HOME/github-mirror-test`") {
            Remove-Item -Path `"`$Env:CACHE_HOME/github-mirror-test`" -Force -Recurse
        }
        git clone `"`$i/licyk/empty`" `"`$Env:CACHE_HOME/github-mirror-test`" --quiet
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
    Get-SD-Trainer-Script-Installer-Cmdlet-Help
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"SD-Trainer-Script Installer 构建模式已启用, 跳过 SD-Trainer-Script Installer 更新检查`"
    } else {
        Check-SD-Trainer-Script-Installer-Update
    }
    Set-Github-Mirror

    if (!(Test-Path `"`$PSScriptRoot/sd-scripts`")) {
        Print-Msg `"在 `$PSScriptRoot 路径中未找到 sd-scripts 文件夹, 请检查 SD-Trainer-Script 是否已正确安装, 或者尝试运行 SD-Trainer-Script Installer 进行修复`"
        Read-Host | Out-Null
        return
    }

    Print-Msg `"拉取 SD-Trainer-Script 更新内容中`"
    Fix-Git-Point-Off-Set `"`$PSScriptRoot/sd-scripts`"
    `$core_origin_ver = `$(git -C `"`$PSScriptRoot/sd-scripts`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")
    `$branch = `$(git -C `"`$PSScriptRoot/sd-scripts`" symbolic-ref --quiet HEAD 2> `$null).split(`"/`")[2]

    git -C `"`$PSScriptRoot/sd-scripts`" show-ref --verify --quiet `"refs/remotes/origin/`$(git -C `"`$PSScriptRoot/sd-scripts`" branch --show-current)`"
    if (`$?) {
        `$remote_branch = `"origin/`$branch`"
    } else {
        `$author=`$(git -C `"`$PSScriptRoot/sd-scripts`" config --get `"branch.`${branch}.remote`")
        if (`$author) {
            `$remote_branch = `$(git -C `"`$PSScriptRoot/sd-scripts`" rev-parse --abbrev-ref `"`${branch}@{upstream}`")
        } else {
            `$remote_branch = `$branch
        }
    }

    git -C `"`$PSScriptRoot/sd-scripts`" fetch --recurse-submodules --all
    if (`$?) {
        Print-Msg `"应用 SD-Trainer-Script 更新中`"
        `$commit_hash = `$(git -C `"`$PSScriptRoot/sd-scripts`" log `"`$remote_branch`" --max-count 1 --format=`"%h`")
        git -C `"`$PSScriptRoot/sd-scripts`" reset --hard `"`$remote_branch`" --recurse-submodules
        `$core_latest_ver = `$(git -C `"`$PSScriptRoot/sd-scripts`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")

        if (`$core_origin_ver -eq `$core_latest_ver) {
            Print-Msg `"SD-Trainer-Script 已为最新版`"
            `$core_update_msg = `"已为最新版, 当前版本：`$core_origin_ver`"
        } else {
            Print-Msg `"SD-Trainer-Script 更新成功`"
            `$core_update_msg = `"更新成功, 版本：`$core_origin_ver -> `$core_latest_ver`"
        }
    } else {
        Print-Msg `"拉取 SD-Trainer-Script 更新内容失败`"
        Print-Msg `"更新 SD-Trainer-Script 失败, 请检查控制台日志。可尝试重新运行 SD-Trainer-Script Installer 更新脚本进行重试`"
    }

    Print-Msg `"退出 SD-Trainer-Script 更新脚本`"

    if (!(`$BuildMode)) {
        Read-Host | Out-Null
    }
}

###################

Main
".Trim()

    if (Test-Path "$InstallPath/update.ps1") {
        Print-Msg "更新 update.ps1 中"
    } else {
        Print-Msg "生成 update.ps1 中"
    }
    Set-Content -Encoding $PS_SCRIPT_ENCODING -Path "$InstallPath/update.ps1" -Value $content
}


# 分支切换脚本
function Write-Switch-Branch-Script {
    $content = "
param (
    [switch]`$Help,
    [switch]`$BuildMode,
    [int]`$BuildWitchBranch,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableUpdate,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisableGithubMirror,
    [string]`$UseCustomGithubMirror
)
# SD-Trainer-Script Installer 版本和检查更新间隔
`$SD_TRAINER_SCRIPT_INSTALLER_VERSION = $SD_TRAINER_SCRIPT_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# PyPI 镜像源
`$PIP_INDEX_ADDR = `"$PIP_INDEX_ADDR`"
`$PIP_INDEX_ADDR_ORI = `"$PIP_INDEX_ADDR_ORI`"
`$PIP_EXTRA_INDEX_ADDR = `"$PIP_EXTRA_INDEX_ADDR`"
`$PIP_EXTRA_INDEX_ADDR_ORI = `"$PIP_EXTRA_INDEX_ADDR_ORI`"
`$PIP_FIND_ADDR = `"$PIP_FIND_ADDR`"
`$PIP_FIND_ADDR_ORI = `"$PIP_FIND_ADDR_ORI`"
`$USE_PIP_MIRROR = if ((!(Test-Path `"`$PSScriptRoot/disable_pypi_mirror.txt`")) -and (!(`$DisablePyPIMirror))) { `$true } else { `$false }
`$PIP_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_INDEX_ADDR } else { `$PIP_INDEX_ADDR_ORI }
`$PIP_EXTRA_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_EXTRA_INDEX_ADDR } else { `$PIP_EXTRA_INDEX_ADDR_ORI }
`$PIP_FIND_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_FIND_ADDR } else { `$PIP_FIND_ADDR_ORI }
`$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_XPU = `"$PIP_EXTRA_INDEX_MIRROR_XPU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118 = `"$PIP_EXTRA_INDEX_MIRROR_CU118`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
`$PIP_EXTRA_INDEX_MIRROR_CU126 = `"$PIP_EXTRA_INDEX_MIRROR_CU126`"
`$PIP_EXTRA_INDEX_MIRROR_CU128 = `"$PIP_EXTRA_INDEX_MIRROR_CU128`"
`$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU118_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU124_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU126_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU128_NJU`"
# Github 镜像源
`$GITHUB_MIRROR_LIST = @(
    `"https://ghfast.top/https://github.com`",
    `"https://mirror.ghproxy.com/https://github.com`",
    `"https://ghproxy.net/https://github.com`",
    `"https://gh.api.99988866.xyz/https://github.com`",
    `"https://gh-proxy.com/https://github.com`",
    `"https://ghps.cc/https://github.com`",
    `"https://gh.idayer.com/https://github.com`",
    `"https://ghproxy.1888866.xyz/github.com`",
    `"https://slink.ltd/https://github.com`",
    `"https://github.boki.moe/github.com`",
    `"https://github.moeyy.xyz/https://github.com`",
    `"https://gh-proxy.net/https://github.com`",
    `"https://gh-proxy.ygxz.in/https://github.com`",
    `"https://wget.la/https://github.com`",
    `"https://kkgithub.com`",
    `"https://gitclone.com/github.com`"
)
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# Aria2 最低版本
`$ARIA2_MINIMUM_VER = `"$ARIA2_MINIMUM_VER`"
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
`$Env:PIP_EXTRA_INDEX_URL = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`".Trim() } else { `$PIP_EXTRA_INDEX_MIRROR }
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_DEFAULT_INDEX = `"`$PIP_INDEX_MIRROR`"
`$Env:UV_INDEX = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`".Trim() } else { `$PIP_EXTRA_INDEX_MIRROR }
`$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:UV_CONCURRENT_DOWNLOADS = 50
`$Env:UV_INDEX_STRATEGY = `"unsafe-best-match`"
`$Env:UV_CONFIG_FILE = `"nul`"
`$Env:PIP_CONFIG_FILE = `"nul`"
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$Env:PIP_NO_WARN_SCRIPT_LOCATION = 0
`$Env:PIP_TIMEOUT = 30
`$Env:PIP_RETRIES = 5
`$Env:PIP_PREFER_BINARY = 1
`$Env:PIP_YES = 1
`$Env:PYTHONUTF8 = 1
`$Env:PYTHONIOENCODING = `"utf-8`"
`$Env:PYTHONUNBUFFERED = 1
`$Env:PYTHONNOUSERSITE = 1
`$Env:PYTHONFAULTHANDLER = 1
`$Env:GRADIO_ANALYTICS_ENABLED = `"False`"
`$Env:HF_HUB_DISABLE_SYMLINKS_WARNING = 1
`$Env:BITSANDBYTES_NOWELCOME = 1
`$Env:ClDeviceGlobalMemSizeAvailablePercent = 100
`$Env:CUDA_MODULE_LOADING = `"LAZY`"
`$Env:TORCH_CUDNN_V8_API_ENABLED = 1
`$Env:USE_LIBUV = 0
`$Env:SYCL_CACHE_PERSISTENT = 1
`$Env:TF_CPP_MIN_LOG_LEVEL = 3
`$Env:SAFETENSORS_FAST_GPU = 1
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
`$Env:TORCHINDUCTOR_CACHE_DIR = `"`$PSScriptRoot/cache/torchinductor`"
`$Env:TRITON_CACHE_DIR = `"`$PSScriptRoot/cache/triton`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 帮助信息
function Get-SD-Trainer-Script-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\switch_branch.ps1 [-Help] [-BuildMode] [-BuildWitchBranch <Fooocus 分支编号>] [-DisablePyPIMirror] [-DisableUpdate] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像源地址>]

参数:
    -Help
        获取 SD-Trainer-Script Installer 的帮助信息

    -BuildMode
        启用 SD-Trainer-Script Installer 构建模式

    -BuildWitchBranch <Fooocus 分支编号>
        (需添加 -BuildMode 启用 SD-Trainer-Script Installer构建模式) SD-Trainer-Script Installer执行完基础安装流程后调用 SD-Trainer-Script Installer的 switch_branch.ps1 脚本, 根据 Fooocus 分支编号切换到对应的 Fooocus 分支
        Fooocus 分支编号可运行 switch_branch.ps1 脚本进行查看

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableUpdate
        禁用 SD-Trainer-Script Installer 更新检查

    -DisableProxy
        禁用 SD-Trainer-Script Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableGithubMirror
        禁用 SD-Trainer-Script Installer 自动设置 Github 镜像源

    -UseCustomGithubMirror <Github 镜像站地址>
        使用自定义的 Github 镜像站地址
        可用的 Github 镜像站地址:
            https://ghfast.top/https://github.com
            https://mirror.ghproxy.com/https://github.com
            https://ghproxy.net/https://github.com
            https://gh.api.99988866.xyz/https://github.com
            https://gh-proxy.com/https://github.com
            https://ghps.cc/https://github.com
            https://gh.idayer.com/https://github.com
            https://ghproxy.1888866.xyz/github.com
            https://slink.ltd/https://github.com
            https://github.boki.moe/github.com
            https://github.moeyy.xyz/https://github.com
            https://gh-proxy.net/https://github.com
            https://gh-proxy.ygxz.in/https://github.com
            https://wget.la/https://github.com
            https://kkgithub.com
            https://gitclone.com/github.com


更多的帮助信息请阅读 SD-Trainer-Script Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


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

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 SD-Trainer-Script Installer 的自动检查更新功能`"
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
    } else {
        return
    }

    ForEach (`$url in `$urls) {
        Print-Msg `"检查 SD-Trainer-Script Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" |
                Select-String -Pattern `"SD_TRAINER_SCRIPT_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 SD-Trainer-Script Installer 更新中`"
            } else {
                Print-Msg `"检查 SD-Trainer-Script Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -gt `$SD_TRAINER_SCRIPT_INSTALLER_VERSION) {
        Print-Msg `"检测到 SD-Trainer-Script Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"==================================================>`").Trim()
        if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
            Print-Msg `"调用 SD-Trainer-Script Installer 进行更新中`"
            . `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
            `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
            Print-Msg `"更新结束, 重新启动 SD-Trainer-Script Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
            Invoke-Expression `"& ```"`$PSCommandPath```" `$raw_params`"
            exit 0
        } else {
            Print-Msg `"跳过 SD-Trainer-Script Installer 更新`"
        }
    } else {
        Print-Msg `"SD-Trainer-Script Installer 已是最新版本`"
    }
}


# 代理配置
function Set-Proxy {
    `$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    # 检测是否禁用自动设置镜像源
    if ((Test-Path `"`$PSScriptRoot/disable_proxy.txt`") -or (`$DisableProxy)) {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件 / -DisableProxy 命令行参数, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if ((Test-Path `"`$PSScriptRoot/proxy.txt`") -or (`$UseCustomProxy)) { # 本地存在代理配置
        if (`$UseCustomProxy) {
            `$proxy_value = `$UseCustomProxy
        } else {
            `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        }
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件 / -UseCustomProxy 命令行参数, 已读取代理配置文件并设置代理`"
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

    if ((Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") -or (`$DisableGithubMirror)) { # 禁用 Github 镜像源
        Print-Msg `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件 / -DisableGithubMirror 命令行参数, 禁用 Github 镜像源`"
        return
    }

    # 使用自定义 Github 镜像源
    if ((Test-Path `"`$PSScriptRoot/gh_mirror.txt`") -or (`$UseCustomGithubMirror)) {
        if (`$UseCustomGithubMirror) {
            `$github_mirror = `$UseCustomGithubMirror
        } else {
            `$github_mirror = Get-Content `"`$PSScriptRoot/gh_mirror.txt`"
        }
        git config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
        Print-Msg `"检测到本地存在 gh_mirror.txt Github 镜像源配置文件 / -UseCustomGithubMirror 命令行参数, 已读取 Github 镜像源配置文件并设置 Github 镜像源`"
        return
    }

    # 自动检测可用镜像源并使用
    `$status = 0
    ForEach(`$i in `$GITHUB_MIRROR_LIST) {
        Print-Msg `"测试 Github 镜像源: `$i`"
        if (Test-Path `"`$Env:CACHE_HOME/github-mirror-test`") {
            Remove-Item -Path `"`$Env:CACHE_HOME/github-mirror-test`" -Force -Recurse
        }
        git clone `"`$i/licyk/empty`" `"`$Env:CACHE_HOME/github-mirror-test`" --quiet
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

        # 本地分支不存在时创建一个分支
        git -C `"`$sd_trainer_script_path`" show-ref --verify --quiet `"refs/heads/`${branch}`"
        if (!(`$?)) {
            git -C `"`$sd_trainer_script_path`" branch `"`${branch}`"
        }

        git -C `"`$sd_trainer_script_path`" checkout `"`${branch}`" --force # 切换分支
        Print-Msg `"应用 SD-Trainer-Script 远程源的更新`"
        if (`$use_submod) {
            Print-Msg `"更新 SD-Trainer-Script 的 Git 子模块信息`"
            git -C `"`$sd_trainer_script_path`" reset --hard `"origin/`$branch`"
            git -C `"`$sd_trainer_script_path`" submodule deinit --all -f
            git -C `"`$sd_trainer_script_path`" submodule update --init --recursive
        }
        if (`$use_submod) {
            git -C `"`$sd_trainer_script_path`" reset --recurse-submodules --hard `"origin/`$branch`" # 切换到最新的提交内容上
        } else {
            git -C `"`$sd_trainer_script_path`" reset --hard `"origin/`$branch`" # 切换到最新的提交内容上
        }
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
    Get-SD-Trainer-Script-Installer-Cmdlet-Help
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"SD-Trainer-Script Installer 构建模式已启用, 跳过 SD-Trainer-Script Installer 更新检查`"
    } else {
        Check-SD-Trainer-Script-Installer-Update
    }

    if (!(Test-Path `"`$PSScriptRoot/sd-scripts`")) {
        Print-Msg `"在 `$PSScriptRoot 路径中未找到 sd-scripts 文件夹, 请检查 SD-Trainer-Script 是否已正确安装, 或者尝试运行 SD-Trainer-Script Installer 进行修复`"
        Read-Host | Out-Null
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
`".Trim()

    `$to_exit = 0

    while (`$True) {
        Print-Msg `"SD-Trainer-Script 分支列表`"
        `$go_to = 0
        Write-Host `$content
        Print-Msg `"当前 SD-Trainer-Script 分支: `$(Get-SD-Trainer-Script-Branch)`"
        Print-Msg `"请选择 SD-Trainer-Script 分支`"
        Print-Msg `"提示: 输入数字后回车, 或者输入 exit 退出 SD-Trainer-Script 分支切换脚本`"
        if (`$BuildMode) {
            `$arg = `$BuildWitchBranch
            `$go_to = 1
        } else {
            `$arg = (Read-Host `"==================================================>`").Trim()
        }

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
                `$branch = `"main`"
                `$branch_name = `"bghira - SimpleTuner 分支`"
                `$use_submod = `$false
                `$go_to = 1
            }
            4 {
                `$remote = `"https://github.com/ostris/ai-toolkit`"
                `$branch = `"main`"
                `$branch_name = `"ostris - ai-toolkit 分支`"
                `$use_submod = `$true
                `$go_to = 1
            }
            5 {
                `$remote = `"https://github.com/a-r-r-o-w/finetrainers`"
                `$branch = `"main`"
                `$branch_name = `"a-r-r-o-w - finetrainers 分支`"
                `$use_submod = `$false
                `$go_to = 1
            }
            6 {
                `$remote = `"https://github.com/tdrussell/diffusion-pipe`"
                `$branch = `"main`"
                `$branch_name = `"tdrussell - diffusion-pipe 分支`"
                `$use_submod = `$true
                `$go_to = 1
            }
            7 {
                `$remote = `"https://github.com/kohya-ss/musubi-tuner`"
                `$branch = `"main`"
                `$branch_name = `"kohya-ss - musubi-tuner 分支`"
                `$use_submod = `$false
                `$go_to = 1
            }
            exit {
                Print-Msg `"退出 SD-Trainer-Script 分支切换脚本`"
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
    if (`$BuildMode) {
        `$operate = `"yes`"
    } else {
        `$operate = (Read-Host `"==================================================>`").Trim()
    }

    if (`$operate -eq `"yes`" -or `$operate -eq `"y`" -or `$operate -eq `"YES`" -or `$operate -eq `"Y`") {
        Print-Msg `"开始切换 SD-Trainer-Script 分支`"
        Switch-SD-Trainer-Script-Branch `$remote `$branch `$use_submod
    } else {
        Print-Msg `"取消切换 SD-Trainer-Script 分支`"
    }
    Print-Msg `"退出 SD-Trainer-Script 分支切换脚本`"

    if (!(`$BuildMode)) {
        Read-Host | Out-Null
    }
}

###################

Main
".Trim()

    if (Test-Path "$InstallPath/switch_branch.ps1") {
        Print-Msg "更新 switch_branch.ps1 中"
    } else {
        Print-Msg "生成 switch_branch.ps1 中"
    }
    Set-Content -Encoding $PS_SCRIPT_ENCODING -Path "$InstallPath/switch_branch.ps1" -Value $content
}


# 获取安装脚本
function Write-Launch-SD-Trainer-Script-Install-Script {
    $content = "
param (
    [string]`$InstallPath = `$PSScriptRoot,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableUV,
    [switch]`$DisableGithubMirror,
    [string]`$UseCustomGithubMirror,
    [string]`$InstallBranch,
    [Parameter(ValueFromRemainingArguments=`$true)]`$ExtraArgs
)
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
    if ((Test-Path `"`$PSScriptRoot/disable_proxy.txt`") -or (`$DisableProxy)) {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件 / -DisableProxy 命令行参数, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if ((Test-Path `"`$PSScriptRoot/proxy.txt`") -or (`$UseCustomProxy)) { # 本地存在代理配置
        if (`$UseCustomProxy) {
            `$proxy_value = `$UseCustomProxy
        } else {
            `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        }
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件 / -UseCustomProxy 命令行参数, 已读取代理配置文件并设置代理`"
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
    if ((Test-Path `"`$PSScriptRoot/disable_pypi_mirror.txt`") -or (`$DisablePyPIMirror)) {
        `$arg.Add(`"-DisablePyPIMirror`", `$true)
    }

    if ((Test-Path `"`$PSScriptRoot/disable_proxy.txt`") -or (`$DisableProxy)) {
        `$arg.Add(`"-DisableProxy`", `$true)
    } else {
        if ((Test-Path `"`$PSScriptRoot/proxy.txt`") -or (`$UseCustomProxy)) {
            if (`$UseCustomProxy) {
                `$proxy_value = `$UseCustomProxy
            } else {
                `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
            }
            `$arg.Add(`"-UseCustomProxy`", `$proxy_value)
        }
    }

    if ((Test-Path `"`$PSScriptRoot/disable_uv.txt`") -or (`$DisableUV)) {
        `$arg.Add(`"-DisableUV`", `$true)
    }

    if ((Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") -or (`$DisableGithubMirror)) {
        `$arg.Add(`"-DisableGithubMirror`", `$true)
    } else {
        if ((Test-Path `"`$PSScriptRoot/gh_mirror.txt`") -or (`$UseCustomGithubMirror)) {
            if (`$UseCustomGithubMirror) {
                `$github_mirror = `$UseCustomGithubMirror
            } else {
                `$github_mirror = Get-Content `"`$PSScriptRoot/gh_mirror.txt`"
            }
            `$arg.Add(`"-UseCustomGithubMirror`", `$github_mirror)
        }
    }

    if ((Get-Command git -ErrorAction SilentlyContinue) -and (Test-Path `"`$PSScriptRoot/sd-scripts/.git`")) {
        `$git_remote = `$(git -C `"`$PSScriptRoot/sd-scripts`" remote get-url origin)
        `$array = `$git_remote -split `"/`"
        `$branch = `"`$(`$array[-2])/`$(`$array[-1])`"
        if ((`$branch -eq `"kohya-ss/sd-scripts`") -or (`$branch -eq `"kohya-ss/sd-scripts.git`")) {
            `$arg.Add(`"-InstallBranch`", `"sd_scripts`")
        } elseif ((`$branch -eq `"bghira/SimpleTuner`") -or (`$branch -eq `"bghira/SimpleTuner.git`")) {
            `$arg.Add(`"-InstallBranch`", `"simple_tuner`")
        } elseif ((`$branch -eq `"ostris/ai-toolkit`") -or (`$branch -eq `"ostris/ai-toolkit.git`")) {
            `$arg.Add(`"-InstallBranch`", `"ai_toolkit`")
        } elseif ((`$branch -eq `"a-r-r-o-w/finetrainers`") -or (`$branch -eq `"a-r-r-o-w/finetrainers.git`")) {
            `$arg.Add(`"-InstallBranch`", `"finetrainers`")
        } elseif ((`$branch -eq `"tdrussell/diffusion-pipe`") -or (`$branch -eq `"tdrussell/diffusion-pipe.git`")) {
            `$arg.Add(`"-InstallBranch`", `"diffusion_pipe`")
        } elseif ((`$branch -eq `"kohya-ss/musubi-tuner`") -or (`$branch -eq `"kohya-ss/musubi-tuner.git`")) {
            `$arg.Add(`"-InstallBranch`", `"musubi_tuner`")
        }
    } elseif ((Test-Path `"`$PSScriptRoot/install_sd_scripts.txt`") -or (`$InstallBranch -eq `"sd_scripts`")) {
        `$arg.Add(`"-InstallBranch`", `"sd_scripts`")
    } elseif ((Test-Path `"`$PSScriptRoot/install_simple_tuner.txt`") -or (`$InstallBranch -eq `"simple_tuner`")) {
        `$arg.Add(`"-InstallBranch`", `"simple_tuner`")
    } elseif ((Test-Path `"`$PSScriptRoot/install_ai_toolkit.txt`") -or (`$InstallBranch -eq `"ai_toolkit`")) {
        `$arg.Add(`"-InstallBranch`", `"ai_toolkit`")
    } elseif ((Test-Path `"`$PSScriptRoot/install_finetrainers.txt`") -or (`$InstallBranch -eq `"finetrainers`")) {
        `$arg.Add(`"-InstallBranch`", `"finetrainers`")
    } elseif ((Test-Path `"`$PSScriptRoot/install_diffusion_pipe.txt`") -or (`$InstallBranch -eq `"diffusion_pipe`")) {
        `$arg.Add(`"-InstallBranch`", `"diffusion_pipe`")
    } elseif ((Test-Path `"`$PSScriptRoot/install_musubi_tuner.txt`") -or (`$InstallBranch -eq `"musubi_tuner`")) {
        `$arg.Add(`"-InstallBranch`", `"musubi_tuner`")
    }

    `$arg.Add(`"-InstallPath`", `$InstallPath)

    return `$arg
}


# 处理额外命令行参数
function Get-ExtraArgs {
    `$extra_args = New-Object System.Collections.ArrayList

    ForEach (`$a in `$ExtraArgs) {
        `$extra_args.Add(`$a) | Out-Null
    }

    `$params = `$extra_args.ForEach{ 
        if (`$_ -match '\s|`"') { `"'{0}'`" -f (`$_ -replace `"'`", `"''`") } 
        else { `$_ } 
    } -join ' '

    return `$params
}


function Main {
    Print-Msg `"初始化中`"
    Get-SD-Trainer-Script-Installer-Version
    Set-Proxy

    `$status = Download-SD-Trainer-Script-Installer

    if (`$status) {
        Print-Msg `"运行 SD-Trainer-Script Installer 中`"
        `$arg = Get-Local-Setting
        `$extra_args = Get-ExtraArgs
        try {
            Invoke-Expression `"& ```"`$PSScriptRoot/cache/sd_trainer_script_installer.ps1```" `$extra_args @arg`"
        }
        catch {
            Print-Msg `"运行 SD-Trainer-Script Installer 时出现了错误: `$_`"
            Read-Host | Out-Null
        }
    } else {
        Read-Host | Out-Null
    }
}

###################

Main
".Trim()

    if (Test-Path "$InstallPath/launch_sd_trainer_script_installer.ps1") {
        Print-Msg "更新 launch_sd_trainer_script_installer.ps1 中"
    } else {
        Print-Msg "生成 launch_sd_trainer_script_installer.ps1 中"
    }
    Set-Content -Encoding $PS_SCRIPT_ENCODING -Path "$InstallPath/launch_sd_trainer_script_installer.ps1" -Value $content
}


# 重装 PyTorch 脚本
function Write-PyTorch-ReInstall-Script {
    $content = "
param (
    [switch]`$Help,
    [switch]`$BuildMode,
    [int]`$BuildWithTorch,
    [switch]`$BuildWithTorchReinstall,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableUpdate,
    [switch]`$DisableUV,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy
)
# SD-Trainer-Script Installer 版本和检查更新间隔
`$SD_TRAINER_SCRIPT_INSTALLER_VERSION = $SD_TRAINER_SCRIPT_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# PyPI 镜像源
`$PIP_INDEX_ADDR = `"$PIP_INDEX_ADDR`"
`$PIP_INDEX_ADDR_ORI = `"$PIP_INDEX_ADDR_ORI`"
`$PIP_EXTRA_INDEX_ADDR = `"$PIP_EXTRA_INDEX_ADDR`"
`$PIP_EXTRA_INDEX_ADDR_ORI = `"$PIP_EXTRA_INDEX_ADDR_ORI`"
`$PIP_FIND_ADDR = `"$PIP_FIND_ADDR`"
`$PIP_FIND_ADDR_ORI = `"$PIP_FIND_ADDR_ORI`"
`$USE_PIP_MIRROR = if ((!(Test-Path `"`$PSScriptRoot/disable_pypi_mirror.txt`")) -and (!(`$DisablePyPIMirror))) { `$true } else { `$false }
`$PIP_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_INDEX_ADDR } else { `$PIP_INDEX_ADDR_ORI }
`$PIP_EXTRA_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_EXTRA_INDEX_ADDR } else { `$PIP_EXTRA_INDEX_ADDR_ORI }
`$PIP_FIND_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_FIND_ADDR } else { `$PIP_FIND_ADDR_ORI }
`$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_XPU = `"$PIP_EXTRA_INDEX_MIRROR_XPU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118 = `"$PIP_EXTRA_INDEX_MIRROR_CU118`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
`$PIP_EXTRA_INDEX_MIRROR_CU126 = `"$PIP_EXTRA_INDEX_MIRROR_CU126`"
`$PIP_EXTRA_INDEX_MIRROR_CU128 = `"$PIP_EXTRA_INDEX_MIRROR_CU128`"
`$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU118_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU124_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU126_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU128_NJU`"
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# Aria2 最低版本
`$ARIA2_MINIMUM_VER = `"$ARIA2_MINIMUM_VER`"
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
`$Env:PIP_EXTRA_INDEX_URL = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`".Trim() } else { `$PIP_EXTRA_INDEX_MIRROR }
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_DEFAULT_INDEX = `"`$PIP_INDEX_MIRROR`"
`$Env:UV_INDEX = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`".Trim() } else { `$PIP_EXTRA_INDEX_MIRROR }
`$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:UV_CONCURRENT_DOWNLOADS = 50
`$Env:UV_INDEX_STRATEGY = `"unsafe-best-match`"
`$Env:UV_CONFIG_FILE = `"nul`"
`$Env:PIP_CONFIG_FILE = `"nul`"
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$Env:PIP_NO_WARN_SCRIPT_LOCATION = 0
`$Env:PIP_TIMEOUT = 30
`$Env:PIP_RETRIES = 5
`$Env:PIP_PREFER_BINARY = 1
`$Env:PIP_YES = 1
`$Env:PYTHONUTF8 = 1
`$Env:PYTHONIOENCODING = `"utf-8`"
`$Env:PYTHONUNBUFFERED = 1
`$Env:PYTHONNOUSERSITE = 1
`$Env:PYTHONFAULTHANDLER = 1
`$Env:GRADIO_ANALYTICS_ENABLED = `"False`"
`$Env:HF_HUB_DISABLE_SYMLINKS_WARNING = 1
`$Env:BITSANDBYTES_NOWELCOME = 1
`$Env:ClDeviceGlobalMemSizeAvailablePercent = 100
`$Env:CUDA_MODULE_LOADING = `"LAZY`"
`$Env:TORCH_CUDNN_V8_API_ENABLED = 1
`$Env:USE_LIBUV = 0
`$Env:SYCL_CACHE_PERSISTENT = 1
`$Env:TF_CPP_MIN_LOG_LEVEL = 3
`$Env:SAFETENSORS_FAST_GPU = 1
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
`$Env:TORCHINDUCTOR_CACHE_DIR = `"`$PSScriptRoot/cache/torchinductor`"
`$Env:TRITON_CACHE_DIR = `"`$PSScriptRoot/cache/triton`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 帮助信息
function Get-SD-Trainer-Script-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\reinstall_pytorch.ps1 [-Help] [-BuildMode] [-BuildWithTorch <PyTorch 版本编号>] [-BuildWithTorchReinstall] [-DisablePyPIMirror] [-DisableUpdate] [-DisableUV] [-DisableProxy] [-UseCustomProxy <代理服务器地址>]

参数:
    -Help
        获取 SD-Trainer-Script Installer 的帮助信息

    -BuildMode
        启用 SD-Trainer-Script Installer 构建模式

    -BuildWithTorch <PyTorch 版本编号>
        (需添加 -BuildMode 启用 SD-Trainer-Script Installer构建模式) SD-Trainer-Script Installer执行完基础安装流程后调用 SD-Trainer-Script Installer的 reinstall_pytorch.ps1 脚本, 根据 PyTorch 版本编号安装指定的 PyTorch 版本
        PyTorch 版本编号可运行 reinstall_pytorch.ps1 脚本进行查看

    -BuildWithTorchReinstall
        (需添加 -BuildMode 启用 SD-Trainer-Script Installer构建模式, 并且添加 -BuildWithTorch) 在 SD-Trainer-Script Installer构建模式下, 执行 reinstall_pytorch.ps1 脚本对 PyTorch 进行指定版本安装时使用强制重新安装

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableUpdate
        禁用 SD-Trainer-Script Installer 更新检查

    -DisableUV
        禁用 SD-Trainer-Script Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -DisableProxy
        禁用 SD-Trainer-Script Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址


更多的帮助信息请阅读 SD-Trainer-Script Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


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


# PyPI 镜像源状态
function PyPI-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 PyPI 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pypi_mirror.txt 配置文件 / -DisablePyPIMirror 命令行参数, 已将 PyPI 源切换至官方源`"
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

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 SD-Trainer-Script Installer 的自动检查更新功能`"
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
    } else {
        return
    }

    ForEach (`$url in `$urls) {
        Print-Msg `"检查 SD-Trainer-Script Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" |
                Select-String -Pattern `"SD_TRAINER_SCRIPT_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 SD-Trainer-Script Installer 更新中`"
            } else {
                Print-Msg `"检查 SD-Trainer-Script Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -gt `$SD_TRAINER_SCRIPT_INSTALLER_VERSION) {
        Print-Msg `"检测到 SD-Trainer-Script Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"==================================================>`").Trim()
        if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
            Print-Msg `"调用 SD-Trainer-Script Installer 进行更新中`"
            . `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
            `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
            Print-Msg `"更新结束, 重新启动 SD-Trainer-Script Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
            Invoke-Expression `"& ```"`$PSCommandPath```" `$raw_params`"
            exit 0
        } else {
            Print-Msg `"跳过 SD-Trainer-Script Installer 更新`"
        }
    } else {
        Print-Msg `"SD-Trainer-Script Installer 已是最新版本`"
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
`".Trim()

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
    if ((Test-Path `"`$PSScriptRoot/disable_uv.txt`") -or (`$DisableUV)) {
        Print-Msg `"检测到 disable_uv.txt 配置文件 / -DisableUV 命令行参数, 已禁用 uv, 使用 Pip 作为 Python 包管理器`"
        `$Global:USE_UV = `$false
    } else {
        Print-Msg `"默认启用 uv 作为 Python 包管理器, 加快 Python 软件包的安装速度`"
        Print-Msg `"当 uv 安装 Python 软件包失败时, 将自动切换成 Pip 重试 Python 软件包的安装`"
        `$Global:USE_UV = `$true
        Check-uv-Version
    }
}


# 代理配置
function Set-Proxy {
    `$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    # 检测是否禁用自动设置镜像源
    if ((Test-Path `"`$PSScriptRoot/disable_proxy.txt`") -or (`$DisableProxy)) {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件 / -DisableProxy 命令行参数, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if ((Test-Path `"`$PSScriptRoot/proxy.txt`") -or (`$UseCustomProxy)) { # 本地存在代理配置
        if (`$UseCustomProxy) {
            `$proxy_value = `$UseCustomProxy
        } else {
            `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        }
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件 / -UseCustomProxy 命令行参数, 已读取代理配置文件并设置代理`"
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
`".Trim()

    `$status = `$(python -c `"`$content`")
    return `$status
}


# 获取驱动支持的最高 CUDA 版本
function Get-Drive-Support-CUDA-Version {
    Print-Msg `"获取显卡驱动支持的最高 CUDA 版本`"
    if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
        `$cuda_ver = `$(nvidia-smi -q | Select-String -Pattern 'CUDA Version\s*:\s*([\d.]+)').Matches.Groups[1].Value
    } else {
        `$cuda_ver = `"未知`"
    }
    return `$cuda_ver
}


# 显示 PyTorch 和 xFormers 版本
function Get-PyTorch-And-xFormers-Version {
    `$content = `"
from importlib.metadata import version

try:
    print(version('torch'))
except:
    print(None)
`".Trim()

    `$torch_ver = `$(python -c `"`$content`")

    `$content = `"
from importlib.metadata import version

try:
    print(version('xformers'))
except:
    print(None)
`".Trim()

    `$xformers_ver = `$(python -c `"`$content`")

    if (`$torch_ver -eq `"None`") { `$torch_ver = `"未安装`" }
    if (`$xformers_ver -eq `"None`") { `$xformers_ver = `"未安装`" }

    Print-Msg `"当前 PyTorch 版本: `$torch_ver`"
    Print-Msg `"当前 xFormers 版本: `$xformers_ver`"
}


function Main {
    Print-Msg `"初始化中`"
    Get-SD-Trainer-Script-Installer-Version
    Get-SD-Trainer-Script-Installer-Cmdlet-Help
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"SD-Trainer-Script Installer 构建模式已启用, 跳过 SD-Trainer-Script Installer 更新检查`"
    } else {
        Check-SD-Trainer-Script-Installer-Update
    }
    Set-uv
    PyPI-Mirror-Status

    # PyTorch 版本列表
    `$content = `"
-----------------------------------------------------
- 1、Torch 1.12.1 (CUDA 11.3) + xFormers 0.0.14
- 2、Torch 1.13.1 (DirectML)
- 3、Torch 1.13.1 (CUDA 11.7) + xFormers 0.0.16
- 4、Torch 2.0.0 (DirectML)
- 5、Torch 2.0.0 (Intel Arc)
- 6、Torch 2.0.0 (CUDA 11.8) + xFormers 0.0.18
- 7、Torch 2.0.1 (CUDA 11.8) + xFormers 0.0.22
- 8、Torch 2.1.0 (Intel Arc)
- 9、Torch 2.1.0 (Intel Core Ultra)
- 10、Torch 2.1.1 (CUDA 11.8) + xFormers 0.0.23
- 11、Torch 2.1.1 (CUDA 12.1) + xFormers 0.0.23
- 12、Torch 2.1.2 (CUDA 11.8) + xFormers 0.0.23.post1
- 13、Torch 2.1.2 (CUDA 12.1) + xFormers 0.0.23.post1
- 14、Torch 2.2.0 (CUDA 11.8) + xFormers 0.0.24
- 15、Torch 2.2.0 (CUDA 12.1) + xFormers 0.0.24
- 16、Torch 2.2.1 (CUDA 11.8) + xFormers 0.0.25
- 17、Torch 2.2.1 (DirectML)
- 18、Torch 2.2.1 (CUDA 12.1) + xFormers 0.0.25
- 19、Torch 2.2.2 (CUDA 11.8) + xFormers 0.0.25.post1
- 20、Torch 2.2.2 (CUDA 12.1) + xFormers 0.0.25.post1
- 21、Torch 2.3.0 (CUDA 11.8) + xFormers 0.0.26.post1
- 22、Torch 2.3.0 (CUDA 12.1) + xFormers 0.0.26.post1
- 23、Torch 2.3.1 (DirectML)
- 24、Torch 2.3.1 (CUDA 11.8) + xFormers 0.0.27
- 25、Torch 2.3.1 (CUDA 12.1) + xFormers 0.0.27
- 26、Torch 2.4.0 (CUDA 11.8) + xFormers 0.0.27.post2
- 27、Torch 2.4.0 (CUDA 12.1) + xFormers 0.0.27.post2
- 28、Torch 2.4.1 (CUDA 12.4) + xFormers 0.0.28.post1
- 29、Torch 2.5.0 (CUDA 12.4) + xFormers 0.0.28.post2
- 30、Torch 2.5.1 (CUDA 12.4) + xFormers 0.0.28.post3
- 31、Torch 2.6.0 (Intel Arc)
- 32、Torch 2.6.0 (CUDA 12.4) + xFormers 0.0.29.post3
- 33、Torch 2.6.0 (CUDA 12.6) + xFormers 0.0.29.post3
- 34、Torch 2.7.0 (Intel Arc)
- 35、Torch 2.7.0 (CUDA 11.8)
- 36、Torch 2.7.0 (CUDA 12.6) + xFormers 0.0.30
- 37、Torch 2.7.0 (CUDA 12.8) + xFormers 0.0.30
- 38、Torch 2.7.1 (Intel Arc)
- 39、Torch 2.7.1 (CUDA 11.8)
- 40、Torch 2.7.1 (CUDA 12.6) + xFormers 0.0.31.post1
- 41、Torch 2.7.1 (CUDA 12.8) + xFormers 0.0.31.post1
-----------------------------------------------------
    `".Trim()

    `$to_exit = 0
    `$torch_ver = `"`"
    `$xformers_ver = `"`"
    `$cuda_support_ver = Get-Drive-Support-CUDA-Version

    while (`$True) {
        Print-Msg `"PyTorch 版本列表`"
        `$go_to = 0
        Write-Host `$content
        Get-PyTorch-And-xFormers-Version
        Print-Msg `"当前显卡驱动支持的最高 CUDA 版本: `$cuda_support_ver`"
        Print-Msg `"请选择 PyTorch 版本`"
        Print-Msg `"提示:`"
        Print-Msg `"1. PyTroch 版本通常来说选择最新版的即可`"
        Print-Msg `"2. 驱动支持的最高 CUDA 版本需要大于或等于要安装的 PyTorch 中所带的 CUDA 版本, 若驱动支持的最高 CUDA 版本低于要安装的 PyTorch 中所带的 CUDA 版本, 可尝试更新显卡驱动, 或者选择 CUDA 版本更低的 PyTorch`"
        Print-Msg `"3. 输入数字后回车, 或者输入 exit 退出 PyTroch 重装脚本`"
        if (`$BuildMode) {
            Print-Msg `"SD-Trainer-Script Installer 构建已启用, 指定安装的 PyTorch 序号: `$BuildWithTorch`"
            `$arg = `$BuildWithTorch
            `$go_to = 1
        } else {
            `$arg = (Read-Host `"==================================================>`").Trim()
        }

        switch (`$arg) {
            1 {
                `$torch_ver = `"torch==1.12.1+cu113 torchvision==0.13.1+cu113 torchaudio==1.12.1+cu113`"
                `$xformers_ver = `"xformers==0.0.14`"
                `$go_to = 1
            }
            2 {
                `$torch_ver = `"torch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1 torch-directml==0.1.13.1.dev230413`"
                `$xformers_ver = `"`"
                `$go_to = 1
            }
            3 {
                `$torch_ver = `"torch==1.13.1+cu117 torchvision==0.14.1+cu117 torchaudio==1.13.1+cu117`"
                `$xformers_ver = `"xformers==0.0.18`"
                `$go_to = 1
            }
            4 {
                `$torch_ver = `"torch==2.0.0 torchvision==0.15.1 torchaudio==2.0.0 torch-directml==0.2.0.dev230426`"
                `$xformers_ver = `"`"
                `$go_to = 1
            }
            5 {
                `$torch_ver = `"torch==2.0.0a0+gite9ebda2 torchvision==0.15.2a0+fa99a53 intel_extension_for_pytorch==2.0.110+gitc6ea20b`"
                `$xformers_ver = `"`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"https://licyk.github.io/t/pypi/index.html`"
                `$Env:UV_FIND_LINKS = `"https://licyk.github.io/t/pypi/index.html`"
                `$go_to = 1
            }
            6 {
                `$torch_ver = `"torch==2.0.0+cu118 torchvision==0.15.1+cu118 torchaudio==2.0.0+cu118`"
                `$xformers_ver = `"xformers==0.0.14`"
                `$go_to = 1
            }
            7 {
                `$torch_ver = `"torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.1+cu118`"
                `$xformers_ver = `"xformers==0.0.22`"
                `$go_to = 1
            }
            8 {
                `$torch_ver = `"torch==2.1.0a0+cxx11.abi torchvision==0.16.0a0+cxx11.abi torchaudio==2.1.0a0+cxx11.abi intel_extension_for_pytorch==2.1.10+xpu`"
                `$xformers_ver = `"`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"https://licyk.github.io/t/pypi/index.html`"
                `$Env:UV_FIND_LINKS = `"https://licyk.github.io/t/pypi/index.html`"
                `$go_to = 1
            }
            9 {
                `$torch_ver = `"torch==2.1.0a0+git7bcf7da torchvision==0.16.0+fbb4cc5 torchaudio==2.1.0+6ea1133 intel_extension_for_pytorch==2.1.20+git4849f3b`"
                `$xformers_ver = `"`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"https://licyk.github.io/t/pypi/index.html`"
                `$Env:UV_FIND_LINKS = `"https://licyk.github.io/t/pypi/index.html`"
                `$go_to = 1
            }
            10 {
                `$torch_ver = `"torch==2.1.1+cu118 torchvision==0.16.1+cu118 torchaudio==2.1.1+cu118`"
                `$xformers_ver = `"xformers==0.0.23+cu118`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            11 {
                `$torch_ver = `"torch==2.1.1+cu121 torchvision==0.16.1+cu121 torchaudio==2.1.1+cu121`"
                `$xformers_ver = `"xformers===0.0.23`"
                `$go_to = 1
            }
            12 {
                `$torch_ver = `"torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2+cu118`"
                `$xformers_ver = `"xformers==0.0.23.post1+cu118`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            13 {
                `$torch_ver = `"torch==2.1.2+cu121 torchvision==0.16.2+cu121 torchaudio==2.1.2+cu121`"
                `$xformers_ver = `"xformers===0.0.23.post1`"
                `$go_to = 1
            }
            14 {
                `$torch_ver = `"torch==2.2.0+cu118 torchvision==0.17.0+cu118 torchaudio==2.2.0+cu118`"
                `$xformers_ver = `"xformers==0.0.24+cu118`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            15 {
                `$torch_ver = `"torch==2.2.0+cu121 torchvision==0.17.0+cu121 torchaudio==2.2.0+cu121`"
                `$xformers_ver = `"xformers===0.0.24`"
                `$go_to = 1
            }
            16 {
                `$torch_ver = `"torch==2.2.1+cu118 torchvision==0.17.1+cu118 torchaudio==2.2.1+cu118`"
                `$xformers_ver = `"xformers==0.0.25+cu118`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            17 {
                `$torch_ver = `"torch==2.2.1 torchvision==0.17.1 torchaudio==2.2.1 torch-directml==0.2.1.dev240521`"
                `$xformers_ver = `"`"
                `$go_to = 1
            }
            18 {
                `$torch_ver = `"torch==2.2.1+cu121 torchvision==0.17.1+cu121 torchaudio==2.2.1+cu121`"
                `$xformers_ver = `"xformers===0.0.25`"
                `$go_to = 1
            }
            19 {
                `$torch_ver = `"torch==2.2.2+cu118 torchvision==0.17.2+cu118 torchaudio==2.2.2+cu118`"
                `$xformers_ver = `"xformers==0.0.25.post1+cu118`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            20 {
                `$torch_ver = `"torch==2.2.2+cu121 torchvision==0.17.2+cu121 torchaudio==2.2.2+cu121`"
                `$xformers_ver = `"xformers===0.0.25.post1`"
                `$go_to = 1
            }
            21 {
                `$torch_ver = `"torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118`"
                `$xformers_ver = `"xformers==0.0.26.post1+cu118`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            22 {
                `$torch_ver = `"torch==2.3.0+cu121 torchvision==0.18.0+cu121 torchaudio==2.3.0+cu121`"
                `$xformers_ver = `"xformers===0.0.26.post1`"
                `$go_to = 1
            }
            23 {
                `$torch_ver = `"torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 torch-directml==0.2.3.dev240715`"
                `$xformers_ver = `"torch==2.3.1 torchvision==0.18.1 torch-directml==0.2.3.dev240715`"
                `$go_to = 1
            }
            24 {
                `$torch_ver = `"torch==2.3.1+cu118 torchvision==0.18.1+cu118 torchaudio==2.3.1+cu118`"
                `$xformers_ver = `"xformers==0.0.27+cu118`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            25 {
                `$torch_ver = `"torch==2.3.1+cu121 torchvision==0.18.1+cu121 torchaudio==2.3.1+cu121`"
                `$xformers_ver = `"xformers===0.0.27`"
                `$Env:PIP_INDEX_URL = `$PIP_EXTRA_INDEX_MIRROR_CU121
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            26 {
                `$torch_ver = `"torch==2.4.0+cu118 torchvision==0.19.0+cu118 torchaudio==2.4.0+cu118`"
                `$xformers_ver = `"xformers==0.0.27.post2+cu118`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            27 {
                `$torch_ver = `"torch==2.4.0+cu121 torchvision==0.19.0+cu121 torchaudio==2.4.0+cu121`"
                `$xformers_ver = `"xformers==0.0.27.post2`"
                `$Env:PIP_INDEX_URL = `$PIP_EXTRA_INDEX_MIRROR_CU121
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            28 {
                `$torch_ver = `"torch==2.4.1+cu124 torchvision==0.19.1+cu124 torchaudio==2.4.1+cu124`"
                `$xformers_ver = `"xformers==0.0.28.post1`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU124_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU124
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            29 {
                `$torch_ver = `"torch==2.5.0+cu124 torchvision==0.20.0+cu124 torchaudio==2.5.0+cu124`"
                `$xformers_ver = `"xformers==0.0.28.post2`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU124_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU124
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            30 {
                `$torch_ver = `"torch==2.5.1+cu124 torchvision==0.20.1+cu124 torchaudio==2.5.1+cu124`"
                `$xformers_ver = `"xformers==0.0.28.post3`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU124_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU124
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            31 {
                `$torch_ver = `"torch==2.6.0+xpu torchvision==0.21.0+xpu torchaudio==2.6.0+xpu`"
                `$xformers_ver = `"`"
                `$Env:PIP_INDEX_URL = `$PIP_EXTRA_INDEX_MIRROR_XPU
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            32 {
                `$torch_ver = `"torch==2.6.0+cu124 torchvision==0.21.0+cu124 torchaudio==2.6.0+cu124`"
                `$xformers_ver = `"xformers==0.0.29.post3`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU124_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU124
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            33 {
                `$torch_ver = `"torch==2.6.0+cu126 torchvision==0.21.0+cu126 torchaudio==2.6.0+cu126`"
                `$xformers_ver = `"xformers==0.0.29.post3`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU126_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU126
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            34 {
                `$torch_ver = `"torch==2.7.0+xpu torchvision==0.22.0+xpu torchaudio==2.7.0+xpu`"
                `$xformers_ver = `"`"
                `$Env:PIP_INDEX_URL = `$PIP_EXTRA_INDEX_MIRROR_XPU
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            35 {
                `$torch_ver = `"torch==2.7.0+cu118 torchvision==0.22.0+cu118 torchaudio==2.7.0+cu118`"
                `$xformers_ver = `"`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            36 {
                `$torch_ver = `"torch==2.7.0+cu126 torchvision==0.22.0+cu126 torchaudio==2.7.0+cu126`"
                `$xformers_ver = `"xformers==0.0.30`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU126_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU126
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            37 {
                `$torch_ver = `"torch==2.7.0+cu128 torchvision==0.22.0+cu128 torchaudio==2.7.0+cu128`"
                `$xformers_ver = `"xformers==0.0.30`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU128_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU128
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            38 {
                `$torch_ver = `"torch==2.7.1+xpu torchvision==0.22.1+xpu torchaudio==2.7.1+xpu`"
                `$xformers_ver = `"`"
                `$Env:PIP_INDEX_URL = `$PIP_EXTRA_INDEX_MIRROR_XPU
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            39 {
                `$torch_ver = `"torch==2.7.1+cu118 torchvision==0.22.1+cu118 torchaudio==2.7.1+cu118`"
                `$xformers_ver = `"`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU118
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            40 {
                `$torch_ver = `"torch==2.7.1+cu126 torchvision==0.22.1+cu126 torchaudio==2.7.1+cu126`"
                `$xformers_ver = `"xformers==0.0.31.post1`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU126_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU126
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            41 {
                `$torch_ver = `"torch==2.7.1+cu128 torchvision==0.22.1+cu128 torchaudio==2.7.1+cu128`"
                `$xformers_ver = `"xformers==0.0.31.post1`"
                `$Env:PIP_INDEX_URL = if (`$USE_PIP_MIRROR) {
                    `$PIP_EXTRA_INDEX_MIRROR_CU128_NJU
                } else {
                    `$PIP_EXTRA_INDEX_MIRROR_CU128
                }
                `$Env:UV_DEFAULT_INDEX = `$Env:PIP_INDEX_URL
                `$Env:PIP_EXTRA_INDEX_URL = `"`"
                `$Env:UV_INDEX = `"`"
                `$Env:PIP_FIND_LINKS = `"`"
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
    if (`$BuildMode) {
        if (`$BuildWithTorchReinstall) {
            `$use_force_reinstall = `"yes`"
        } else {
            `$use_force_reinstall = `"no`"
        }
    } else {
        `$use_force_reinstall = (Read-Host `"==================================================>`").Trim()
    }

    if (`$use_force_reinstall -eq `"yes`" -or `$use_force_reinstall -eq `"y`" -or `$use_force_reinstall -eq `"YES`" -or `$use_force_reinstall -eq `"Y`") {
        `$force_reinstall_arg = `"--force-reinstall`"
        `$force_reinstall_status = `"启用`"
    } else {
        `$force_reinstall_arg = New-Object System.Collections.ArrayList
        `$force_reinstall_status = `"禁用`"
    }

    Print-Msg `"当前的选择`"
    Print-Msg `"PyTorch: `$torch_ver`"
    Print-Msg `"xFormers: `$xformers_ver`"
    Print-Msg `"仅强制重装: `$force_reinstall_status`"
    Print-Msg `"是否确认安装?`"
    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
    if (`$BuildMode) {
        `$install_torch = `"yes`"
    } else {
        `$install_torch = (Read-Host `"==================================================>`").Trim()
    }

    if (`$install_torch -eq `"yes`" -or `$install_torch -eq `"y`" -or `$install_torch -eq `"YES`" -or `$install_torch -eq `"Y`") {
        Print-Msg `"重装 PyTorch 中`"
        if (`$USE_UV) {
            uv pip install `$torch_ver.ToString().Split() `$force_reinstall_arg
            if (!(`$?)) {
                Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
                python -m pip install `$torch_ver.ToString().Split() `$force_reinstall_arg --no-warn-conflicts
            }
        } else {
            python -m pip install `$torch_ver.ToString().Split() `$force_reinstall_arg --no-warn-conflicts
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
                    python -m pip install `$xformers_ver `$force_reinstall_arg --no-deps --no-warn-conflicts
                }
            } else {
                python -m pip install `$xformers_ver `$force_reinstall_arg --no-deps --no-warn-conflicts
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

    if (!(`$BuildMode)) {
        Read-Host | Out-Null
    }
}

###################

Main
".Trim()

    if (Test-Path "$InstallPath/reinstall_pytorch.ps1") {
        Print-Msg "更新 reinstall_pytorch.ps1 中"
    } else {
        Print-Msg "生成 reinstall_pytorch.ps1 中"
    }
    Set-Content -Encoding $PS_SCRIPT_ENCODING -Path "$InstallPath/reinstall_pytorch.ps1" -Value $content
}


# 模型下载脚本
function Write-Download-Model-Script {
    $content = "
param (
    [switch]`$Help,
    [switch]`$BuildMode,
    [string]`$BuildWitchModel,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisableUpdate
)
# SD-Trainer-Script Installer 版本和检查更新间隔
`$SD_TRAINER_SCRIPT_INSTALLER_VERSION = $SD_TRAINER_SCRIPT_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# PyPI 镜像源
`$PIP_INDEX_ADDR = `"$PIP_INDEX_ADDR`"
`$PIP_INDEX_ADDR_ORI = `"$PIP_INDEX_ADDR_ORI`"
`$PIP_EXTRA_INDEX_ADDR = `"$PIP_EXTRA_INDEX_ADDR`"
`$PIP_EXTRA_INDEX_ADDR_ORI = `"$PIP_EXTRA_INDEX_ADDR_ORI`"
`$PIP_FIND_ADDR = `"$PIP_FIND_ADDR`"
`$PIP_FIND_ADDR_ORI = `"$PIP_FIND_ADDR_ORI`"
`$USE_PIP_MIRROR = if ((!(Test-Path `"`$PSScriptRoot/disable_pypi_mirror.txt`")) -and (!(`$DisablePyPIMirror))) { `$true } else { `$false }
`$PIP_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_INDEX_ADDR } else { `$PIP_INDEX_ADDR_ORI }
`$PIP_EXTRA_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_EXTRA_INDEX_ADDR } else { `$PIP_EXTRA_INDEX_ADDR_ORI }
`$PIP_FIND_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_FIND_ADDR } else { `$PIP_FIND_ADDR_ORI }
`$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_XPU = `"$PIP_EXTRA_INDEX_MIRROR_XPU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118 = `"$PIP_EXTRA_INDEX_MIRROR_CU118`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
`$PIP_EXTRA_INDEX_MIRROR_CU126 = `"$PIP_EXTRA_INDEX_MIRROR_CU126`"
`$PIP_EXTRA_INDEX_MIRROR_CU128 = `"$PIP_EXTRA_INDEX_MIRROR_CU128`"
`$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU118_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU124_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU126_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU128_NJU`"
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# Aria2 最低版本
`$ARIA2_MINIMUM_VER = `"$ARIA2_MINIMUM_VER`"
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
`$Env:PIP_EXTRA_INDEX_URL = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`".Trim() } else { `$PIP_EXTRA_INDEX_MIRROR }
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_DEFAULT_INDEX = `"`$PIP_INDEX_MIRROR`"
`$Env:UV_INDEX = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`".Trim() } else { `$PIP_EXTRA_INDEX_MIRROR }
`$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:UV_CONCURRENT_DOWNLOADS = 50
`$Env:UV_INDEX_STRATEGY = `"unsafe-best-match`"
`$Env:UV_CONFIG_FILE = `"nul`"
`$Env:PIP_CONFIG_FILE = `"nul`"
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$Env:PIP_NO_WARN_SCRIPT_LOCATION = 0
`$Env:PIP_TIMEOUT = 30
`$Env:PIP_RETRIES = 5
`$Env:PIP_PREFER_BINARY = 1
`$Env:PIP_YES = 1
`$Env:PYTHONUTF8 = 1
`$Env:PYTHONIOENCODING = `"utf-8`"
`$Env:PYTHONUNBUFFERED = 1
`$Env:PYTHONNOUSERSITE = 1
`$Env:PYTHONFAULTHANDLER = 1
`$Env:GRADIO_ANALYTICS_ENABLED = `"False`"
`$Env:HF_HUB_DISABLE_SYMLINKS_WARNING = 1
`$Env:BITSANDBYTES_NOWELCOME = 1
`$Env:ClDeviceGlobalMemSizeAvailablePercent = 100
`$Env:CUDA_MODULE_LOADING = `"LAZY`"
`$Env:TORCH_CUDNN_V8_API_ENABLED = 1
`$Env:USE_LIBUV = 0
`$Env:SYCL_CACHE_PERSISTENT = 1
`$Env:TF_CPP_MIN_LOG_LEVEL = 3
`$Env:SAFETENSORS_FAST_GPU = 1
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
`$Env:TORCHINDUCTOR_CACHE_DIR = `"`$PSScriptRoot/cache/torchinductor`"
`$Env:TRITON_CACHE_DIR = `"`$PSScriptRoot/cache/triton`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 帮助信息
function Get-SD-Trainer-Script-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\download_models.ps1 [-Help] [-BuildMode] [-BuildWitchModel <模型编号列表>] [-DisablePyPIMirror] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableUpdate]

参数:
    -Help
        获取 SD-Trainer-Script Installer 的帮助信息

    -BuildMode
        启用 SD-Trainer-Script Installer 构建模式

    -BuildWitchModel <模型编号列表>
        (需添加 -BuildMode 启用 SD-Trainer-Script Installer构建模式) SD-Trainer-Script Installer执行完基础安装流程后调用 SD-Trainer-Script Installer的 download_models.ps1 脚本, 根据模型编号列表下载指定的模型
        模型编号可运行 download_models.ps1 脚本进行查看

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableProxy
        禁用 SD-Trainer-Script Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableUpdate
        禁用 SD-Trainer-Script Installer 更新检查


更多的帮助信息请阅读 SD-Trainer-Script Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


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
    if ((Test-Path `"`$PSScriptRoot/disable_proxy.txt`") -or (`$DisableProxy)) {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件 / -DisableProxy 命令行参数, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if ((Test-Path `"`$PSScriptRoot/proxy.txt`") -or (`$UseCustomProxy)) { # 本地存在代理配置
        if (`$UseCustomProxy) {
            `$proxy_value = `$UseCustomProxy
        } else {
            `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        }
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件 / -UseCustomProxy 命令行参数, 已读取代理配置文件并设置代理`"
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

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 SD-Trainer-Script Installer 的自动检查更新功能`"
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
    } else {
        return
    }

    ForEach (`$url in `$urls) {
        Print-Msg `"检查 SD-Trainer-Script Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" |
                Select-String -Pattern `"SD_TRAINER_SCRIPT_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 SD-Trainer-Script Installer 更新中`"
            } else {
                Print-Msg `"检查 SD-Trainer-Script Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -gt `$SD_TRAINER_SCRIPT_INSTALLER_VERSION) {
        Print-Msg `"检测到 SD-Trainer-Script Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"==================================================>`").Trim()
        if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
            Print-Msg `"调用 SD-Trainer-Script Installer 进行更新中`"
            . `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
            `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
            Print-Msg `"更新结束, 重新启动 SD-Trainer-Script Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
            Invoke-Expression `"& ```"`$PSCommandPath```" `$raw_params`"
            exit 0
        } else {
            Print-Msg `"跳过 SD-Trainer-Script Installer 更新`"
        }
    } else {
        Print-Msg `"SD-Trainer-Script Installer 已是最新版本`"
    }
}


# 检查 Aria2 版本并更新
function Check-Aria2-Version {
    `$content = `"
import re
import subprocess



def get_aria2_ver() -> str:
    try:
        aria2_output = subprocess.check_output(['aria2c', '--version'], text=True).splitlines()
    except:
        return None

    for text in aria2_output:
        version_match = re.search(r'aria2 version (\d+\.\d+\.\d+)', text)
        if version_match:
            return version_match.group(1)

    return None


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


def aria2_need_update(aria2_min_ver: str) -> bool:
    aria2_ver = get_aria2_ver()

    if aria2_ver:
        if compare_versions(aria2_ver, aria2_min_ver) == -1:
            return True
        else:
            return False
    else:
        return True


print(aria2_need_update('`$ARIA2_MINIMUM_VER'))
`".Trim()

    Print-Msg `"检查 Aria2 是否需要更新`"
    `$urls = @(
        `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/aria2c.exe`",
        `"https://huggingface.co/licyk/invokeai-core-model/resolve/main/pypatchmatch/aria2c.exe`"
    )
    `$aria2_tmp_path = `"`$Env:CACHE_HOME/aria2c.exe`"
    `$status = `$(python -c `"`$content`")
    `$i = 0

    if (`$status -eq `"True`") {
        Print-Msg `"更新 Aria2 中`"
        New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null
    } else {
        Print-Msg `"Aria2 无需更新`"
        return
    }

    ForEach (`$url in `$urls) {
        Print-Msg `"下载 Aria2 中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$aria2_tmp_path`"
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试下载 Aria2 中`"
            } else {
                Print-Msg `"Aria2 下载失败, 无法更新 Aria2, 可能会导致模型下载出现问题`"
                return
            }
        }
    }

    if ((Test-Path `"`$PSScriptRoot/git/bin/aria2c.exe`") -or (Test-Path `"`$PSScriptRoot/git/bin/git.exe`")) {
        Move-Item -Path `"`$Env:CACHE_HOME/aria2c.exe`" -Destination `"`$PSScriptRoot/git/bin/aria2c.exe`" -Force
    } else {
        New-Item -ItemType Directory -Path `"`$PSScriptRoot/git/bin`" -Force > `$null
        Move-Item -Path `"`$Env:CACHE_HOME/aria2c.exe`" -Destination `"`$PSScriptRoot/git/bin/aria2c.exe`" -Force
    }
    Print-Msg `"Aria2 更新完成`"
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
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/animagine-xl-4.0.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/animagine-xl-4.0-opt.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/animagine-xl-4.0-zero.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
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
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/Illustrious-XL-v1.0.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/Illustrious-XL-v1.1.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/Illustrious-XL-v2.0-stable.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/jruTheJourneyRemains_v25XL.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/PVCStyleModelMovable_illustriousxl10.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/miaomiaoHarem_v15a.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
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
        Print-Msg `"[`$(`$i + 1)/`$sum] 下载 `$name (`$type) 模型到 `$path 中`"
        aria2c --file-allocation=none --summary-interval=0 --console-log-level=error -s 64 -c -x 16 -k 1M `$url -d `"`$path`" -o `"`$model_name`"
        if (`$?) {
            Print-Msg `"[`$(`$i + 1)/`$sum] `$name (`$type) 下载成功`"
        } else {
            Print-Msg `"[`$(`$i + 1)/`$sum] `$name (`$type) 下载失败`"
        }
    }
}


# 获取用户输入
function Get-User-Input {
    return (Read-Host `"==================================================>`").Trim()
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
    Get-SD-Trainer-Script-Installer-Cmdlet-Help
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"SD-Trainer-Script Installer 构建模式已启用, 跳过 SD-Trainer-Script Installer 更新检查`"
    } else {
        Check-SD-Trainer-Script-Installer-Update
    }
    Check-Aria2-Version

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
        if (`$BuildMode) {
            `$arg = `$BuildWitchModel
            `$go_to = 1
        } else {
            `$arg = Get-User-Input
        }

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
    if (`$BuildMode) {
        `$download_operate = `"yes`"
    } else {
        `$download_operate = Get-User-Input
    }

    if (`$download_operate -eq `"yes`" -or `$download_operate -eq `"y`" -or `$download_operate -eq `"YES`" -or `$download_operate -eq `"Y`") {
        Model-Downloader `$download_list
    }

    Print-Msg `"退出模型下载脚本`"

    if (!(`$BuildMode)) {
        Read-Host | Out-Null
    }
}

###################

Main
".Trim()

    if (Test-Path "$InstallPath/download_models.ps1") {
        Print-Msg "更新 download_models.ps1 中"
    } else {
        Print-Msg "生成 download_models.ps1 中"
    }
    Set-Content -Encoding $PS_SCRIPT_ENCODING -Path "$InstallPath/download_models.ps1" -Value $content
}


# SD-Trainer-Script Installer 设置脚本
function Write-SD-Trainer-Script-Installer-Settings-Script {
    $content = "
param (
    [switch]`$Help,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy
)
# SD-Trainer-Script Installer 版本和检查更新间隔
`$SD_TRAINER_SCRIPT_INSTALLER_VERSION = $SD_TRAINER_SCRIPT_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# PyPI 镜像源
`$PIP_INDEX_ADDR = `"$PIP_INDEX_ADDR`"
`$PIP_INDEX_ADDR_ORI = `"$PIP_INDEX_ADDR_ORI`"
`$PIP_EXTRA_INDEX_ADDR = `"$PIP_EXTRA_INDEX_ADDR`"
`$PIP_EXTRA_INDEX_ADDR_ORI = `"$PIP_EXTRA_INDEX_ADDR_ORI`"
`$PIP_FIND_ADDR = `"$PIP_FIND_ADDR`"
`$PIP_FIND_ADDR_ORI = `"$PIP_FIND_ADDR_ORI`"
`$USE_PIP_MIRROR = if ((!(Test-Path `"`$PSScriptRoot/disable_pypi_mirror.txt`")) -and (!(`$DisablePyPIMirror))) { `$true } else { `$false }
`$PIP_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_INDEX_ADDR } else { `$PIP_INDEX_ADDR_ORI }
`$PIP_EXTRA_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_EXTRA_INDEX_ADDR } else { `$PIP_EXTRA_INDEX_ADDR_ORI }
`$PIP_FIND_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_FIND_ADDR } else { `$PIP_FIND_ADDR_ORI }
`$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_XPU = `"$PIP_EXTRA_INDEX_MIRROR_XPU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118 = `"$PIP_EXTRA_INDEX_MIRROR_CU118`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
`$PIP_EXTRA_INDEX_MIRROR_CU126 = `"$PIP_EXTRA_INDEX_MIRROR_CU126`"
`$PIP_EXTRA_INDEX_MIRROR_CU128 = `"$PIP_EXTRA_INDEX_MIRROR_CU128`"
`$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU118_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU124_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU126_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU128_NJU`"
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# Aria2 最低版本
`$ARIA2_MINIMUM_VER = `"$ARIA2_MINIMUM_VER`"
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
`$Env:PIP_EXTRA_INDEX_URL = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`".Trim() } else { `$PIP_EXTRA_INDEX_MIRROR }
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_DEFAULT_INDEX = `"`$PIP_INDEX_MIRROR`"
`$Env:UV_INDEX = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`".Trim() } else { `$PIP_EXTRA_INDEX_MIRROR }
`$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:UV_CONCURRENT_DOWNLOADS = 50
`$Env:UV_INDEX_STRATEGY = `"unsafe-best-match`"
`$Env:UV_CONFIG_FILE = `"nul`"
`$Env:PIP_CONFIG_FILE = `"nul`"
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$Env:PIP_NO_WARN_SCRIPT_LOCATION = 0
`$Env:PIP_TIMEOUT = 30
`$Env:PIP_RETRIES = 5
`$Env:PIP_PREFER_BINARY = 1
`$Env:PIP_YES = 1
`$Env:PYTHONUTF8 = 1
`$Env:PYTHONIOENCODING = `"utf-8`"
`$Env:PYTHONUNBUFFERED = 1
`$Env:PYTHONNOUSERSITE = 1
`$Env:PYTHONFAULTHANDLER = 1
`$Env:GRADIO_ANALYTICS_ENABLED = `"False`"
`$Env:HF_HUB_DISABLE_SYMLINKS_WARNING = 1
`$Env:BITSANDBYTES_NOWELCOME = 1
`$Env:ClDeviceGlobalMemSizeAvailablePercent = 100
`$Env:CUDA_MODULE_LOADING = `"LAZY`"
`$Env:TORCH_CUDNN_V8_API_ENABLED = 1
`$Env:USE_LIBUV = 0
`$Env:SYCL_CACHE_PERSISTENT = 1
`$Env:TF_CPP_MIN_LOG_LEVEL = 3
`$Env:SAFETENSORS_FAST_GPU = 1
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
`$Env:TORCHINDUCTOR_CACHE_DIR = `"`$PSScriptRoot/cache/torchinductor`"
`$Env:TRITON_CACHE_DIR = `"`$PSScriptRoot/cache/triton`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 帮助信息
function Get-SD-Trainer-Script-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\settings.ps1 [-Help] [-DisablePyPIMirror] [-DisableProxy] [-UseCustomProxy <代理服务器地址>]

参数:
    -Help
        获取 SD-Trainer-Script Installer 的帮助信息

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableProxy
        禁用 SD-Trainer-Script Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址


更多的帮助信息请阅读 SD-Trainer-Script Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


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
    if ((Test-Path `"`$PSScriptRoot/disable_proxy.txt`") -or (`$DisableProxy)) {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件 / -DisableProxy 命令行参数, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if ((Test-Path `"`$PSScriptRoot/proxy.txt`") -or (`$UseCustomProxy)) { # 本地存在代理配置
        if (`$UseCustomProxy) {
            `$proxy_value = `$UseCustomProxy
        } else {
            `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        }
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件 / -UseCustomProxy 命令行参数, 已读取代理配置文件并设置代理`"
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


# 获取 PyPI 镜像源配置
function Get-PyPI-Mirror-Setting {
    if (!(Test-Path `"`$PSScriptRoot/disable_pypi_mirror.txt`")) {
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


# 获取 SD-Trainer-Script 运行环境检测配置
function Get-SD-Trainer-Script-Env-Check-Setting {
    if (!(Test-Path `"`$PSScriptRoot/disable_check_env.txt`")) {
        return `"启用`"
    } else {
        return `"禁用`"
    }
}


# 获取用户输入
function Get-User-Input {
    return (Read-Host `"==================================================>`").Trim()
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
                Print-Msg `" https://hf-mirror.com`"
                Print-Msg `" https://huggingface.sukaka.top`"
                Print-Msg `"提示: 输入 HuggingFace 镜像源地址后回车保存`"
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
                Print-Msg `" https://ghfast.top/https://github.com`"
                Print-Msg `" https://mirror.ghproxy.com/https://github.com`"
                Print-Msg `" https://ghproxy.net/https://github.com`"
                Print-Msg `" https://gh.api.99988866.xyz/https://github.com`"
                Print-Msg `" https://ghproxy.1888866.xyz/github.com`"
                Print-Msg `" https://slink.ltd/https://github.com`"
                Print-Msg `" https://github.boki.moe/github.com`"
                Print-Msg `" https://github.moeyy.xyz/https://github.com`"
                Print-Msg `" https://gh-proxy.net/https://github.com`"
                Print-Msg `" https://gh-proxy.ygxz.in/https://github.com`"
                Print-Msg `" https://wget.la/https://github.com`"
                Print-Msg `" https://kkgithub.com`"
                Print-Msg `" https://gh-proxy.com/https://github.com`"
                Print-Msg `" https://ghps.cc/https://github.com`"
                Print-Msg `" https://gh.idayer.com/https://github.com`"
                Print-Msg `" https://gitclone.com/github.com`"
                Print-Msg `"提示: 输入 Github 镜像源地址后回车保存`"
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
        Print-Msg `"警告: 当 SD-Trainer-Script Installer 有重要更新(如功能性修复)时, 禁用自动更新检查后将得不到及时提示`"

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


# PyPI 镜像源设置
function PyPI-Mirror-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 PyPI 镜像源设置: `$(Get-PyPI-Mirror-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 PyPI 镜像源`"
        Print-Msg `"2. 禁用 PyPI 镜像源`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_pypi_mirror.txt`" -Force -Recurse 2> `$null
                Print-Msg `"启用 PyPI 镜像源成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_pypi_mirror.txt`" -Force > `$null
                Print-Msg `"禁用 PyPI 镜像源成功`"
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
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" |
                Select-String -Pattern `"SD_TRAINER_SCRIPT_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 SD-Trainer-Script Installer 更新中`"
            } else {
                Print-Msg `"检查 SD-Trainer-Script Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -gt `$SD_TRAINER_SCRIPT_INSTALLER_VERSION) {
        Print-Msg `"SD-Trainer-Script Installer 有新版本可用`"
        Print-Msg `"调用 SD-Trainer-Script Installer 进行更新中`"
        . `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
        `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
        Print-Msg `"更新结束, 重新启动 SD-Trainer-Script Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
        Invoke-Expression `"& ```"`$PSCommandPath```" `$raw_params`"
        exit 0
    } else {
        Print-Msg `"SD-Trainer-Script Installer 已是最新版本`"
    }
}


# SD-Trainer-Script 运行环境检测设置
function SD-Trainer-Script-Env-Check-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 SD-Trainer-Script 运行环境检测设置: `$(Get-SD-Trainer-Script-Env-Check-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 SD-Trainer-Script 运行环境检测`"
        Print-Msg `"2. 禁用 SD-Trainer-Script 运行环境检测`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_check_env.txt`" -Force -Recurse 2> `$null
                Print-Msg `"启用 SD-Trainer-Script 运行环境检测成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_check_env.txt`" -Force > `$null
                Print-Msg `"禁用 SD-Trainer-Script 运行环境检测成功`"
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
    Get-SD-Trainer-Script-Installer-Cmdlet-Help
    Set-Proxy

    while (`$true) {
        `$go_to = 0
        Print-Msg `"-----------------------------------------------------`"
        Print-Msg `"当前环境配置:`"
        Print-Msg `"代理设置: `$(Get-Proxy-Setting)`"
        Print-Msg `"Python 包管理器: `$(Get-Python-Package-Manager-Setting)`"
        Print-Msg `"HuggingFace 镜像源设置: `$(Get-HuggingFace-Mirror-Setting)`"
        Print-Msg `"Github 镜像源设置: `$(Get-Github-Mirror-Setting)`"
        Print-Msg `"SD-Trainer-Script Installer 自动检查更新: `$(Get-SD-Trainer-Script-Installer-Auto-Check-Update-Setting)`"
        Print-Msg `"PyPI 镜像源设置: `$(Get-PyPI-Mirror-Setting)`"
        Print-Msg `"自动设置 CUDA 内存分配器设置: `$(Get-PyTorch-CUDA-Memory-Alloc-Setting)`"
        Print-Msg `"SD-Trainer-Script 运行环境检测设置: `$(Get-SD-Trainer-Script-Env-Check-Setting)`"
        Print-Msg `"-----------------------------------------------------`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 进入代理设置`"
        Print-Msg `"2. 进入 Python 包管理器设置`"
        Print-Msg `"3. 进入 HuggingFace 镜像源设置`"
        Print-Msg `"4. 进入 Github 镜像源设置`"
        Print-Msg `"5. 进入 SD-Trainer-Script Installer 自动检查更新设置`"
        Print-Msg `"6. 进入 PyPI 镜像源设置`"
        Print-Msg `"7. 进入自动设置 CUDA 内存分配器设置`"
        Print-Msg `"8. 进入 SD-Trainer-Scripts 运行环境检测设置`"
        Print-Msg `"9. 更新 SD-Trainer-Script Installer 管理脚本`"
        Print-Msg `"10. 检查环境完整性`"
        Print-Msg `"11. 查看 SD-Trainer-Script Installer 文档`"
        Print-Msg `"12. 退出 SD-Trainer-Script Installer 设置`"
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
                PyPI-Mirror-Setting
                break
            }
            7 {
                PyTorch-CUDA-Memory-Alloc-Setting
                break
            }
            8 {
                SD-Trainer-Script-Env-Check-Setting
                break
            }
            9 {
                Check-SD-Trainer-Script-Installer-Update
                break
            }
            10 {
                Check-Env
                break
            }
            11 {
                Get-SD-Trainer-Script-Installer-Help-Docs
                break
            }
            12 {
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
".Trim()

    if (Test-Path "$InstallPath/settings.ps1") {
        Print-Msg "更新 settings.ps1 中"
    } else {
        Print-Msg "生成 settings.ps1 中"
    }
    Set-Content -Encoding $PS_SCRIPT_ENCODING -Path "$InstallPath/settings.ps1" -Value $content
}

# 虚拟环境激活脚本
function Write-Env-Activate-Script {
    $content = "
param (
    [switch]`$Help,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisableHuggingFaceMirror,
    [string]`$UseCustomHuggingFaceMirror,
    [switch]`$DisableGithubMirror,
    [string]`$UseCustomGithubMirror
)
# SD-Trainer-Script Installer 版本和检查更新间隔
`$Env:SD_TRAINER_SCRIPT_INSTALLER_VERSION = $SD_TRAINER_SCRIPT_INSTALLER_VERSION
`$Env:UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# PyPI 镜像源
`$PIP_INDEX_ADDR = `"$PIP_INDEX_ADDR`"
`$PIP_INDEX_ADDR_ORI = `"$PIP_INDEX_ADDR_ORI`"
`$PIP_EXTRA_INDEX_ADDR = `"$PIP_EXTRA_INDEX_ADDR`"
`$PIP_EXTRA_INDEX_ADDR_ORI = `"$PIP_EXTRA_INDEX_ADDR_ORI`"
`$PIP_FIND_ADDR = `"$PIP_FIND_ADDR`"
`$PIP_FIND_ADDR_ORI = `"$PIP_FIND_ADDR_ORI`"
`$USE_PIP_MIRROR = if ((!(Test-Path `"`$PSScriptRoot/disable_pypi_mirror.txt`")) -and (!(`$DisablePyPIMirror))) { `$true } else { `$false }
`$PIP_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_INDEX_ADDR } else { `$PIP_INDEX_ADDR_ORI }
`$PIP_EXTRA_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_EXTRA_INDEX_ADDR } else { `$PIP_EXTRA_INDEX_ADDR_ORI }
`$PIP_FIND_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_FIND_ADDR } else { `$PIP_FIND_ADDR_ORI }
`$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_XPU = `"$PIP_EXTRA_INDEX_MIRROR_XPU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118 = `"$PIP_EXTRA_INDEX_MIRROR_CU118`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
`$PIP_EXTRA_INDEX_MIRROR_CU126 = `"$PIP_EXTRA_INDEX_MIRROR_CU126`"
`$PIP_EXTRA_INDEX_MIRROR_CU128 = `"$PIP_EXTRA_INDEX_MIRROR_CU128`"
`$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU118_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU124_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU126_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU128_NJU`"
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# Aria2 最低版本
`$ARIA2_MINIMUM_VER = `"$ARIA2_MINIMUM_VER`"
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
`$Env:PIP_EXTRA_INDEX_URL = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`".Trim() } else { `$PIP_EXTRA_INDEX_MIRROR }
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_DEFAULT_INDEX = `"`$PIP_INDEX_MIRROR`"
`$Env:UV_INDEX = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`".Trim() } else { `$PIP_EXTRA_INDEX_MIRROR }
`$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:UV_CONCURRENT_DOWNLOADS = 50
`$Env:UV_INDEX_STRATEGY = `"unsafe-best-match`"
`$Env:UV_CONFIG_FILE = `"nul`"
`$Env:PIP_CONFIG_FILE = `"nul`"
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$Env:PIP_NO_WARN_SCRIPT_LOCATION = 0
`$Env:PIP_TIMEOUT = 30
`$Env:PIP_RETRIES = 5
`$Env:PIP_PREFER_BINARY = 1
`$Env:PIP_YES = 1
`$Env:PYTHONUTF8 = 1
`$Env:PYTHONIOENCODING = `"utf-8`"
`$Env:PYTHONUNBUFFERED = 1
`$Env:PYTHONNOUSERSITE = 1
`$Env:PYTHONFAULTHANDLER = 1
`$Env:GRADIO_ANALYTICS_ENABLED = `"False`"
`$Env:HF_HUB_DISABLE_SYMLINKS_WARNING = 1
`$Env:BITSANDBYTES_NOWELCOME = 1
`$Env:ClDeviceGlobalMemSizeAvailablePercent = 100
`$Env:CUDA_MODULE_LOADING = `"LAZY`"
`$Env:TORCH_CUDNN_V8_API_ENABLED = 1
`$Env:USE_LIBUV = 0
`$Env:SYCL_CACHE_PERSISTENT = 1
`$Env:TF_CPP_MIN_LOG_LEVEL = 3
`$Env:SAFETENSORS_FAST_GPU = 1
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
`$Env:TORCHINDUCTOR_CACHE_DIR = `"`$PSScriptRoot/cache/torchinductor`"
`$Env:TRITON_CACHE_DIR = `"`$PSScriptRoot/cache/triton`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"
`$Env:SD_TRAINER_SCRIPT_INSTALLER_ROOT = `$PSScriptRoot



# 帮助信息
function Get-SD-Trainer-Script-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\activate.ps1 [-Help] [-DisablePyPIMirror] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像源地址>] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>]

参数:
    -Help
        获取 SD-Trainer-Script Installer 的帮助信息

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableProxy
        禁用 SD-Trainer-Script Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableHuggingFaceMirror
        禁用 HuggingFace 镜像源, 不使用 HuggingFace 镜像源下载文件

    -UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>
        使用自定义 HuggingFace 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror ```"https://hf-mirror.com```" 设置 HuggingFace 镜像源地址

    -DisableGithubMirror
        禁用 SD-Trainer-Script Installer 自动设置 Github 镜像源

    -UseCustomGithubMirror <Github 镜像站地址>
        使用自定义的 Github 镜像站地址
        可用的 Github 镜像站地址:
            https://ghfast.top/https://github.com
            https://mirror.ghproxy.com/https://github.com
            https://ghproxy.net/https://github.com
            https://gh.api.99988866.xyz/https://github.com
            https://gh-proxy.com/https://github.com
            https://ghps.cc/https://github.com
            https://gh.idayer.com/https://github.com
            https://ghproxy.1888866.xyz/github.com
            https://slink.ltd/https://github.com
            https://github.boki.moe/github.com
            https://github.moeyy.xyz/https://github.com
            https://gh-proxy.net/https://github.com
            https://gh-proxy.ygxz.in/https://github.com
            https://wget.la/https://github.com
            https://kkgithub.com
            https://gitclone.com/github.com


更多的帮助信息请阅读 SD-Trainer-Script Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


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
    `$urls = @(
        `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/aria2c.exe`",
        `"https://huggingface.co/licyk/invokeai-core-model/resolve/main/pypatchmatch/aria2c.exe`"
    )
    `$aria2_tmp_path = `"`$Env:CACHE_HOME/aria2c.exe`"
    `$i = 0
    Print-Msg `"下载 Aria2 中`"
    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null
    ForEach (`$url in `$urls) {
        Print-Msg `"下载 Aria2 中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$aria2_tmp_path`"
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试下载 Aria2 中`"
            } else {
                Print-Msg `"下载 Aria2 失败, 无法进行更新, 可尝试重新运行更新命令`"
                return
            }
        }
    }

    Move-Item -Path `"`$Env:CACHE_HOME/aria2c.exe`" -Destination `"`$Env:SD_TRAINER_SCRIPT_INSTALLER_ROOT/git/bin/aria2c.exe`" -Force
    Print-Msg `"更新 Aria2 完成`"
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
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/sd_trainer_script_installer.ps1`" |
                Select-String -Pattern `"SD_TRAINER_SCRIPT_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 SD-Trainer-Script Installer 更新中`"
            } else {
                Print-Msg `"检查 SD-Trainer-Script Installer 更新失败`"
                return
            }
        }
    }

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
}


# 设置 Python 命令别名
function global:pip {
    python -m pip @args
}

Set-Alias pip3 pip
Set-Alias pip3.11 pip
Set-Alias python3 python
Set-Alias python3.11 python


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


# PyPI 镜像源状态
function PyPI-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 PyPI 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pypi_mirror.txt 配置文件 / -DisablePyPIMirror 命令行参数, 已将 PyPI 源切换至官方源`"
    }
}


# 代理配置
function Set-Proxy {
    `$Env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    # 检测是否禁用自动设置镜像源
    if ((Test-Path `"`$PSScriptRoot/disable_proxy.txt`") -or (`$DisableProxy)) {
        Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件 / -DisableProxy 命令行参数, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if ((Test-Path `"`$PSScriptRoot/proxy.txt`") -or (`$UseCustomProxy)) { # 本地存在代理配置
        if (`$UseCustomProxy) {
            `$proxy_value = `$UseCustomProxy
        } else {
            `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        }
        `$Env:HTTP_PROXY = `$proxy_value
        `$Env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件 / -UseCustomProxy 命令行参数, 已读取代理配置文件并设置代理`"
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
    if ((Test-Path `"`$PSScriptRoot/disable_hf_mirror.txt`") -or (`$DisableHuggingFaceMirror)) { # 检测是否禁用了自动设置 HuggingFace 镜像源
        Print-Msg `"检测到本地存在 disable_hf_mirror.txt 镜像源配置文件 / -DisableHuggingFaceMirror 命令行参数, 禁用自动设置 HuggingFace 镜像源`"
        return
    }

    if ((Test-Path `"`$PSScriptRoot/hf_mirror.txt`") -or (`$UseCustomHuggingFaceMirror)) { # 本地存在 HuggingFace 镜像源配置
        if (`$UseCustomHuggingFaceMirror) {
            `$hf_mirror_value = `$UseCustomHuggingFaceMirror
        } else {
            `$hf_mirror_value = Get-Content `"`$PSScriptRoot/hf_mirror.txt`"
        }
        `$Env:HF_ENDPOINT = `$hf_mirror_value
        Print-Msg `"检测到本地存在 hf_mirror.txt 配置文件 / -UseCustomHuggingFaceMirror 命令行参数, 已读取该配置并设置 HuggingFace 镜像源`"
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

    if ((Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") -or (`$DisableGithubMirror)) { # 禁用 Github 镜像源
        Print-Msg `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件 / -DisableGithubMirror 命令行参数, 禁用 Github 镜像源`"
        return
    }

    # 使用自定义 Github 镜像源
    if ((Test-Path `"`$PSScriptRoot/gh_mirror.txt`") -or (`$UseCustomGithubMirror)) {
        if (`$UseCustomGithubMirror) {
            `$github_mirror = `$UseCustomGithubMirror
        } else {
            `$github_mirror = Get-Content `"`$PSScriptRoot/gh_mirror.txt`"
        }
        git config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
        Print-Msg `"检测到本地存在 gh_mirror.txt Github 镜像源配置文件 / -UseCustomGithubMirror 命令行参数, 已读取 Github 镜像源配置文件并设置 Github 镜像源`"
    }
}


function Main {
    Print-Msg `"初始化中`"
    Get-SD-Trainer-Script-Installer-Version
    Get-SD-Trainer-Script-Installer-Cmdlet-Help
    Set-Proxy
    Set-HuggingFace-Mirror
    Set-Github-Mirror
    PyPI-Mirror-Status
    Print-Msg `"激活 SD-Trainer-Script Env`"
    Print-Msg `"更多帮助信息可在 SD-Trainer-Script Installer 项目地址查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md`"
}

###################

Main
".Trim()

    if (Test-Path "$InstallPath/activate.ps1") {
        Print-Msg "更新 activate.ps1 中"
    } else {
        Print-Msg "生成 activate.ps1 中"
    }
    Set-Content -Encoding $PS_SCRIPT_ENCODING -Path "$InstallPath/activate.ps1" -Value $content
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
".Trim()

    if (Test-Path "$InstallPath/terminal.ps1") {
        Print-Msg "更新 terminal.ps1 中"
    } else {
        Print-Msg "生成 terminal.ps1 中"
    }
    Set-Content -Encoding $PS_SCRIPT_ENCODING -Path "$InstallPath/terminal.ps1" -Value $content
}


# 帮助文档
function Write-ReadMe {
    $content = "
====================================================================
SD-Trainer-Script Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
====================================================================
########## 使用帮助 ##########

这是关于 SD-Trainer-Script 的简单使用文档。

使用 SD-Trainer-Script Installer 进行安装并安装成功后，将在当前目录生成 SD-Trainer-Script 文件夹，以下为文件夹中不同文件 / 文件夹的作用。

init.ps1：初始化 SD-Trainer-Script 运行环境的脚本。
train.ps1：初始训练脚本，用于编写训练命令，训练命令编写方法可查看：https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md#%E7%BC%96%E5%86%99%E8%AE%AD%E7%BB%83%E8%84%9A%E6%9C%AC
update.ps1：更新 SD-Trainer-Script 的脚本，可使用该脚本更新 SD-Trainer-Script。
download_models.ps1：下载模型的脚本，下载的模型将存放在 models 文件夹中。关于模型的介绍可阅读：https://github.com/licyk/README-collection/blob/main/model-info/README.md。
reinstall_pytorch.ps1：重新安装 PyTorch 的脚本，在 PyTorch 出问题或者需要切换 PyTorch 版本时可使用。
switch_branch.ps1：切换 SD-Trainer-Script 分支。
settings.ps1：管理 SD-Trainer-Script Installer 的设置。
terminal.ps1：启动 PowerShell 终端并自动激活虚拟环境，激活虚拟环境后即可使用 Python、Pip、Git 的命令。
activate.ps1：虚拟环境激活脚本，使用该脚本激活虚拟环境后即可使用 Python、Pip、Git 的命令。
launch_sd_trainer_script_installer.ps1：获取最新的 SD-Trainer-Script Installer 安装脚本并运行。
configure_env.bat：配置环境脚本，解决 PowerShell 运行闪退和启用 Windows 长路径支持。
help.txt：帮助文档。
cache：缓存文件夹，保存着 Pip / HuggingFace 等缓存文件。
python：Python 的存放路径。请注意，请勿将该 Python 文件夹添加到环境变量，这可能导致不良后果。
git：Git 的存放路径。
sd-scripts：SD-Trainer-Script 存放的文件夹。
models：使用模型下载脚本下载模型时模型的存放位置。

详细的 SD-Trainer-Script Installer 使用帮助：https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md

其他的一些训练模型的教程：
https://sd-moadel-doc.maozi.io
https://rentry.org/59xed3
https://civitai.com/articles/2056
https://civitai.com/articles/124/lora-analogy-about-lora-trainning-and-using
https://civitai.com/articles/143/some-shallow-understanding-of-lora-training-lora
https://civitai.com/articles/632/why-this-lora-can-not-bring-good-result-lora
https://civitai.com/articles/726/an-easy-way-to-make-a-cosplay-lora-cosplay-lora
https://civitai.com/articles/2135/lora-quality-improvement-some-experiences-about-datasets-and-captions-lora
https://civitai.com/articles/2297/ways-to-make-a-character-lora-that-is-easier-to-change-clothes-lora

推荐的哔哩哔哩 UP 主：
青龙圣者：https://space.bilibili.com/219296
秋葉aaaki：https://space.bilibili.com/12566101
琥珀青葉：https://space.bilibili.com/507303431
观看这些 UP 主的视频可获得一些训练模型的教程。


====================================================================
########## Github 项目 ##########

sd-webui-all-in-one 项目地址：https://github.com/licyk/sd-webui-all-in-one
sd-scripts 项目地址：https://github.com/kohya-ss/sd-scripts
SimpleTuner 项目地址：https://github.com/bghira/SimpleTuner
ai-toolkit 项目地址：https://github.com/ostris/ai-toolkit
finetrainers 项目地址：https://github.com/a-r-r-o-w/finetrainers
diffusion-pipe 项目地址：https://github.com/tdrussell/diffusion-pipe
musubi-tuner 项目地址：https://github.com/kohya-ss/musubi-tuner


====================================================================
########## 用户协议 ##########

使用该整合包代表您已阅读并同意以下用户协议：
您不得实施包括但不限于以下行为，也不得为任何违反法律法规的行为提供便利：
    反对宪法所规定的基本原则的。
    危害国家安全，泄露国家秘密，颠覆国家政权，破坏国家统一的。
    损害国家荣誉和利益的。
    煽动民族仇恨、民族歧视，破坏民族团结的。
    破坏国家宗教政策，宣扬邪教和封建迷信的。
    散布谣言，扰乱社会秩序，破坏社会稳定的。
    散布淫秽、色情、赌博、暴力、凶杀、恐怖或教唆犯罪的。
    侮辱或诽谤他人，侵害他人合法权益的。
    实施任何违背`“七条底线`”的行为。
    含有法律、行政法规禁止的其他内容的。
因您的数据的产生、收集、处理、使用等任何相关事项存在违反法律法规等情况而造成的全部结果及责任均由您自行承担。
".Trim()

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
    Write-Train-Script
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
    Write-Configure-Env-Script
}


# 将安装器配置文件复制到管理脚本路径
function Copy-SD-Trainer-Script-Installer-Config {
    Print-Msg "为 SD-Trainer-Script Installer 管理脚本复制 SD-Trainer-Script Installer 配置文件中"

    if ((!($DisablePyPIMirror)) -and (Test-Path "$PSScriptRoot/disable_pypi_mirror.txt")) {
        Copy-Item -Path "$PSScriptRoot/disable_pypi_mirror.txt" -Destination "$InstallPath"
        Print-Msg "$PSScriptRoot/disable_pypi_mirror.txt -> $InstallPath/disable_pypi_mirror.txt" -Force
    }

    if ((!($DisableProxy)) -and (Test-Path "$PSScriptRoot/disable_proxy.txt")) {
        Copy-Item -Path "$PSScriptRoot/disable_proxy.txt" -Destination "$InstallPath" -Force
        Print-Msg "$PSScriptRoot/disable_proxy.txt -> $InstallPath/disable_proxy.txt" -Force
    } elseif ((!($DisableProxy)) -and ($UseCustomProxy -eq "") -and (Test-Path "$PSScriptRoot/proxy.txt") -and (!(Test-Path "$PSScriptRoot/disable_proxy.txt"))) {
        Copy-Item -Path "$PSScriptRoot/proxy.txt" -Destination "$InstallPath" -Force
        Print-Msg "$PSScriptRoot/proxy.txt -> $InstallPath/proxy.txt"
    }

    if ((!($DisableUV)) -and (Test-Path "$PSScriptRoot/disable_uv.txt")) {
        Copy-Item -Path "$PSScriptRoot/disable_uv.txt" -Destination "$InstallPath" -Force
        Print-Msg "$PSScriptRoot/disable_uv.txt -> $InstallPath/disable_uv.txt" -Force
    }

    if ((!($DisableGithubMirror)) -and (Test-Path "$PSScriptRoot/disable_gh_mirror.txt")) {
        Copy-Item -Path "$PSScriptRoot/disable_gh_mirror.txt" -Destination "$InstallPath" -Force
        Print-Msg "$PSScriptRoot/disable_gh_mirror.txt -> $InstallPath/disable_gh_mirror.txt"
    } elseif ((!($DisableGithubMirror)) -and (!($UseCustomGithubMirror)) -and (Test-Path "$PSScriptRoot/gh_mirror.txt") -and (!(Test-Path "$PSScriptRoot/disable_gh_mirror.txt"))) {
        Copy-Item -Path "$PSScriptRoot/gh_mirror.txt" -Destination "$InstallPath" -Force
        Print-Msg "$PSScriptRoot/gh_mirror.txt -> $InstallPath/gh_mirror.txt"
    }
}


# 执行安装
function Use-Install-Mode {
    Set-Proxy
    Set-uv
    PyPI-Mirror-Status
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
    Copy-SD-Trainer-Script-Installer-Config

    if ($BuildMode) {
        Use-Build-Mode
        Print-Msg "SD-Trainer-Script 环境构建完成, 路径: $InstallPath"
    } else {
        Print-Msg "SD-Trainer-Script 安装结束, 安装路径为: $InstallPath"
    }

    Print-Msg "帮助文档可在 SD-Trainer-Script 文件夹中查看, 双击 help.txt 文件即可查看, 更多的说明请阅读 SD-Trainer-Script Installer 使用文档"
    Print-Msg "SD-Trainer-Script Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md"
    Print-Msg "退出 SD-Trainer-Script Installer"

    if (!($BuildMode)) {
        Read-Host | Out-Null
    }
}


# 执行管理脚本更新
function Use-Update-Mode {
    Print-Msg "更新管理脚本和文档中"
    Write-Manager-Scripts
    Print-Msg "更新管理脚本和文档完成"
}


# 执行管理脚本完成其他环境构建
function Use-Build-Mode {
    Print-Msg "执行其他环境构建脚本中"

    if ($BuildWithTorch) {
        $launch_args = @{}
        $launch_args.Add("-BuildWithTorch", $BuildWithTorch)
        if ($BuildWithTorchReinstall) { $launch_args.Add("-BuildWithTorchReinstall", $true) }
        if ($DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($DisableUV) { $launch_args.Add("-DisableUV", $true) }
        if ($DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $UseCustomProxy) }
        Print-Msg "执行重装 PyTorch 脚本中"
        . "$InstallPath/reinstall_pytorch.ps1" -BuildMode @launch_args
    }

    if ($BuildWitchModel) {
        $launch_args = @{}
        $launch_args.Add("-BuildWitchModel", $BuildWitchModel)
        if ($DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $UseCustomProxy) }
        if ($DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        Print-Msg "执行模型安装脚本中"
        . "$InstallPath/download_models.ps1" -BuildMode @launch_args
    }

    if ($BuildWitchBranch) {
        $launch_args = @{}
        $launch_args.Add("-BuildWitchBranch", $BuildWitchBranch)
        if ($DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $UseCustomProxy) }
        if ($DisableGithubMirror) { $launch_args.Add("-DisableGithubMirror", $true) }
        if ($UseCustomGithubMirror) { $launch_args.Add("-UseCustomGithubMirror", $UseCustomGithubMirror) }
        Print-Msg "执行 SD-Trainer-Script 分支切换脚本中"
        . "$InstallPath/switch_branch.ps1" -BuildMode @launch_args
    }

    if ($BuildWithUpdate) {
        $launch_args = @{}
        if ($DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $UseCustomProxy) }
        if ($DisableGithubMirror) { $launch_args.Add("-DisableGithubMirror", $true) }
        if ($UseCustomGithubMirror) { $launch_args.Add("-UseCustomGithubMirror", $UseCustomGithubMirror) }
        Print-Msg "执行 SD-Trainer-Script 更新脚本中"
        . "$InstallPath/update.ps1" -BuildMode @launch_args
    }

    if ($BuildWithLaunch) {
        $launch_args = @{}
        if ($DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $UseCustomProxy) }
        if ($DisableHuggingFaceMirror) { $launch_args.Add("-DisableHuggingFaceMirror", $true) }
        if ($UseCustomHuggingFaceMirror) { $launch_args.Add("-UseCustomHuggingFaceMirror", $UseCustomHuggingFaceMirror) }
        if ($DisableGithubMirror) { $launch_args.Add("-DisableGithubMirror", $true) }
        if ($UseCustomGithubMirror) { $launch_args.Add("-UseCustomGithubMirror", $UseCustomGithubMirror) }
        if ($DisableUV) { $launch_args.Add("-DisableUV", $true) }
        if ($DisableCUDAMalloc) { $launch_args.Add("-DisableCUDAMalloc", $true) }
        if ($DisableEnvCheck) { $launch_args.Add("-DisableEnvCheck", $true) }
        Print-Msg "执行 SD-Trainer-Script 启动脚本中"
        . "$InstallPath/init.ps1" -BuildMode @launch_args
    }

    # 清理缓存
    Print-Msg "清理下载 Python 软件包的缓存中"
    python -m pip cache purge
    uv cache clean
}


# 环境配置脚本
function Write-Configure-Env-Script {
    $content = "
@echo off

echo =================================================================
echo :: More information: https://github.com/licyk/sd-webui-all-in-one
echo =================================================================
>nul 2>&1 `"%SYSTEMROOT%\system32\icacls.exe`" `"%SYSTEMROOT%\system32\config\system`"
if '%errorlevel%' NEQ '0' (
    echo :: Requesting administrative privileges
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo :: Write vbs script to request administrative privileges
    echo Set UAC = CreateObject^(`"Shell.Application`"^) > `"%temp%\getadmin.vbs`"
    echo :: Executing vbs script
    echo UAC.ShellExecute `"%~s0`", `"`", `"`", `"runas`", 1 >> `"%temp%\getadmin.vbs`"
    `"%temp%\getadmin.vbs`"
    exit /B

:gotAdmin
    echo :: Launch CMD with administrative privileges
    if exist `"%temp%\getadmin.vbs`" ( del `"%temp%\getadmin.vbs`" )
    pushd `"%CD%`" 
    CD /D `"%~dp0`"
    goto configureEnv

:configureEnv
    title Configure environment
    echo :: Set PowerShell execution policies
    echo :: Executing command: `"Set-ExecutionPolicy Unrestricted -Scope CurrentUser`"
    powershell `"Set-ExecutionPolicy Unrestricted -Scope CurrentUser`"
    echo :: Enable long paths supported
    echo :: Executing command: `"New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force`"
    powershell `"New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force`"
    echo :: Configure completed
    echo :: Exit environment configuration script 
    pause
".Trim()

    if (Test-Path "$InstallPath/configure_env.bat") {
        Print-Msg "更新 configure_env.bat 中"
    } else {
        Print-Msg "生成 configure_env.bat 中"
    }
    Set-Content -Encoding Default -Path "$InstallPath/configure_env.bat" -Value $content
}


# 帮助信息
function Get-SD-Trainer-Script-Installer-Cmdlet-Help {
    $content = "
使用:
    .\sd_trainer_script_installer.ps1 [-Help] [-InstallPath <安装 SD-Trainer-Script 的绝对路径>] [-PyTorchMirrorType <PyTorch 镜像源类型>] [-InstallBranch <安装的 SD-Trainer-Script 分支>] [-UseUpdateMode] [-DisablePyPIMirror] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableUV] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像站地址>] [-BuildMode] [-BuildWithUpdate] [-BuildWithLaunch] [-BuildWithTorch <PyTorch 版本编号>] [-BuildWithTorchReinstall] [-BuildWitchModel <模型编号列表>] [-BuildWitchBranch <SD-Trainer-Script 分支编号>] [-PyTorchPackage <PyTorch 软件包>] [-xFormersPackage <xFormers 软件包>] [-DisableUpdate] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>] [-DisableCUDAMalloc] [-DisableEnvCheck]

参数:
    -Help
        获取 SD-Trainer-Script Installer 的帮助信息

    -InstallPath <安装 SD-Trainer-Script 的绝对路径>
        指定 SD-Trainer-Script Installer 安装 SD-Trainer-Script 的路径, 使用绝对路径表示
        例如: .\sd_trainer_script_installer.ps1 -InstallPath `"D:\Donwload`", 这将指定 SD-Trainer-Script Installer 安装 SD-Trainer-Script 到 D:\Donwload 这个路径

    -PyTorchMirrorType <PyTorch 镜像源类型>
        指定安装 PyTorch 时使用的 PyTorch 镜像源类型, 可指定的类型: cu11x, cu118, cu121, cu124, cu126, cu128

    -InstallBranch <安装的 SD-Trainer-Script 分支>
        指定 SD-Trainer-Script Installer 安装的 SD-Trainer-Script 分支 (sd_scripts, simple_tuner, ai_toolkit, finetrainers, diffusion_pipe, musubi_tuner)
        例如: .\sd_trainer_script_installer.ps1 -InstallBranch `"simple_tuner`", 这将指定 SD-Trainer-Script Installer 安装 bghira/SimpleTuner 分支
        未指定该参数时, 默认安装 kohya-ss/sd-scripts 分支
        支持指定安装的分支如下:
            sd_scripts:     kohya-ss/sd-scripts
            simple_tuner:   bghira/SimpleTuner
            ai_toolkit:     ostris/ai-toolkit
            finetrainers:   a-r-r-o-w/finetrainers
            diffusion_pipe: tdrussell/diffusion-pipe
            musubi_tuner:   kohya-ss/musubi-tuner

    -UseUpdateMode
        指定 SD-Trainer-Script Installer 使用更新模式, 只对 SD-Trainer-Script Installer 的管理脚本进行更新

    -DisablePyPIMirror
        禁用 SD-Trainer-Script Installer 使用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableProxy
        禁用 SD-Trainer-Script Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy `"http://127.0.0.1:10809`" 设置代理服务器地址

    -DisableUV
        禁用 SD-Trainer-Script Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -DisableGithubMirror
        禁用 SD-Trainer-Script Installer 自动设置 Github 镜像源

    -UseCustomGithubMirror <Github 镜像站地址>
        使用自定义的 Github 镜像站地址
        可用的 Github 镜像站地址:
            https://ghfast.top/https://github.com
            https://mirror.ghproxy.com/https://github.com
            https://ghproxy.net/https://github.com
            https://gh.api.99988866.xyz/https://github.com
            https://gh-proxy.com/https://github.com
            https://ghps.cc/https://github.com
            https://gh.idayer.com/https://github.com
            https://ghproxy.1888866.xyz/github.com
            https://slink.ltd/https://github.com
            https://github.boki.moe/github.com
            https://github.moeyy.xyz/https://github.com
            https://gh-proxy.net/https://github.com
            https://gh-proxy.ygxz.in/https://github.com
            https://wget.la/https://github.com
            https://kkgithub.com
            https://gitclone.com/github.com

    -BuildMode
        启用 SD-Trainer-Script Installer 构建模式, 在基础安装流程结束后将调用 SD-Trainer-Script Installer 管理脚本执行剩余的安装任务, 并且出现错误时不再暂停 SD-Trainer-Script Installer 的执行, 而是直接退出
        当指定调用多个 SD-Trainer-Script Installer 脚本时, 将按照优先顺序执行 (按从上到下的顺序)
            - reinstall_pytorch.ps1     (对应 -BuildWithTorch, -BuildWithTorchReinstall 参数)
            - switch_branch.ps1         (对应 -BuildWitchBranch 参数)
            - download_models.ps1       (对应 -BuildWitchModel 参数)
            - update.ps1                (对应 -BuildWithUpdate 参数)
            - init.ps1                  (对应 -BuildWithLaunch 参数)

    -BuildWithUpdate
        (需添加 -BuildMode 启用 SD-Trainer-Script Installer 构建模式) SD-Trainer-Script Installer 执行完基础安装流程后调用 SD-Trainer-Script Installer 的 update.ps1 脚本, 更新 SD-Trainer-Script 内核

    -BuildWithLaunch
        (需添加 -BuildMode 启用 SD-Trainer-Script Installer 构建模式) SD-Trainer-Script Installer 执行完基础安装流程后调用 SD-Trainer-Script Installer 的 init.ps1 脚本, 执行启动 SD-Trainer-Script 前的环境检查流程, 但跳过启动 SD-Trainer-Script

    -BuildWithTorch <PyTorch 版本编号>
        (需添加 -BuildMode 启用 SD-Trainer-Script Installer 构建模式) SD-Trainer-Script Installer 执行完基础安装流程后调用 SD-Trainer-Script Installer 的 reinstall_pytorch.ps1 脚本, 根据 PyTorch 版本编号安装指定的 PyTorch 版本
        PyTorch 版本编号可运行 reinstall_pytorch.ps1 脚本进行查看

    -BuildWithTorchReinstall
        (需添加 -BuildMode 启用 SD-Trainer-Script Installer 构建模式, 并且添加 -BuildWithTorch) 在 SD-Trainer-Script Installer 构建模式下, 执行 reinstall_pytorch.ps1 脚本对 PyTorch 进行指定版本安装时使用强制重新安装

    -BuildWitchModel <模型编号列表>
        (需添加 -BuildMode 启用 SD-Trainer-Script Installer 构建模式) SD-Trainer-Script Installer 执行完基础安装流程后调用 SD-Trainer-Script Installer 的 download_models.ps1 脚本, 根据模型编号列表下载指定的模型
        模型编号可运行 download_models.ps1 脚本进行查看

    -BuildWitchBranch <SD-Trainer-Script 分支编号>
        (需添加 -BuildMode 启用 SD-Trainer-Script Installer 构建模式) SD-Trainer-Script Installer 执行完基础安装流程后调用 SD-Trainer-Script Installer 的 switch_branch.ps1 脚本, 根据 SD-Trainer-Script 分支编号切换到对应的 SD-Trainer-Script 分支
        SD-Trainer-Script 分支编号可运行 switch_branch.ps1 脚本进行查看

    -PyTorchPackage <PyTorch 软件包>
        (需要同时搭配 -xFormersPackage 一起使用, 否则可能会出现 PyTorch 和 xFormers 不匹配的问题) 指定要安装 PyTorch 版本, 如 -PyTorchPackage `"torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118`"

    -xFormersPackage <xFormers 软件包>
        (需要同时搭配 -PyTorchPackage 一起使用, 否则可能会出现 PyTorch 和 xFormers 不匹配的问题) 指定要安装 xFormers 版本, 如 -xFormersPackage `"xformers===0.0.26.post1+cu118`"

    -DisableUpdate
        (仅在 SD-Trainer-Script Installer 构建模式下生效, 并且只作用于 SD-Trainer-Script Installer 管理脚本) 禁用 SD-Trainer-Script Installer 更新检查

    -DisableHuggingFaceMirror
        (仅在 SD-Trainer-Script Installer 构建模式下生效, 并且只作用于 SD-Trainer-Script Installer 管理脚本) 禁用 HuggingFace 镜像源, 不使用 HuggingFace 镜像源下载文件

    -UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>
        (仅在 SD-Trainer-Script Installer 构建模式下生效, 并且只作用于 SD-Trainer-Script Installer 管理脚本) 使用自定义 HuggingFace 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror `"https://hf-mirror.com`" 设置 HuggingFace 镜像源地址

    -DisableCUDAMalloc
        (仅在 SD-Trainer-Script Installer 构建模式下生效, 并且只作用于 SD-Trainer-Script Installer 管理脚本) 禁用 SD-Trainer-Script Installer 通过 PYTORCH_CUDA_ALLOC_CONF 环境变量设置 CUDA 内存分配器

    -DisableEnvCheck
        (仅在 SD-Trainer-Script Installer 构建模式下生效, 并且只作用于 SD-Trainer-Script Installer 管理脚本) 禁用 SD-Trainer-Script Installer 检查 SD-Trainer-Script 运行环境中存在的问题, 禁用后可能会导致 SD-Trainer-Script 环境中存在的问题无法被发现并修复


更多的帮助信息请阅读 SD-Trainer-Script Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_script_installer.md
".Trim()

    if ($Help) {
        Write-Host $content
        exit 0
    }
}


# 主程序
function Main {
    Print-Msg "初始化中"
    Get-SD-Trainer-Script-Installer-Version
    Get-SD-Trainer-Script-Installer-Cmdlet-Help

    if ($UseUpdateMode) {
        Print-Msg "使用更新模式"
        Use-Update-Mode
        Set-Content -Encoding UTF8 -Path "$InstallPath/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
    } else {
        if ($BuildMode) {
            Print-Msg "SD-Trainer-Script Installer 构建模式已启用"
        }
        Print-Msg "使用安装模式"
        Use-Install-Mode
    }
}


###################


Main
