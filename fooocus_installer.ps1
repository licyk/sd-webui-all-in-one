﻿param (
    [switch]$Help,
    [string]$CorePrefix,
    [string]$InstallPath = (Join-Path -Path "$PSScriptRoot" -ChildPath "Fooocus"),
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
    [switch]$NoPreDownloadModel,
    [string]$PyTorchPackage,
    [string]$xFormersPackage,
    [switch]$InstallHanamizuki,
    [switch]$NoCleanCache,

    # 仅在管理脚本中生效
    [switch]$DisableUpdate,
    [switch]$DisableHuggingFaceMirror,
    [string]$UseCustomHuggingFaceMirror,
    [string]$LaunchArg,
    [switch]$EnableShortcut,
    [switch]$DisableCUDAMalloc,
    [switch]$DisableEnvCheck,
    [switch]$DisableAutoApplyUpdate
)
& {
    $prefix_list = @("core", "Fooocus", "fooocus", "fooocus_portable")
    if ((Test-Path "$PSScriptRoot/core_prefix.txt") -or ($CorePrefix)) {
        if ($CorePrefix) {
            $origin_core_prefix = $CorePrefix
        } else {
            $origin_core_prefix = Get-Content "$PSScriptRoot/core_prefix.txt"
        }
        $origin_core_prefix = $origin_core_prefix.Trim('/').Trim('\')
        if ([System.IO.Path]::IsPathRooted($origin_core_prefix)) {
            $to_path = $origin_core_prefix
            $from_uri = New-Object System.Uri($InstallPath.Replace('\', '/') + '/')
            $to_uri = New-Object System.Uri($to_path.Replace('\', '/'))
            $origin_core_prefix = $from_uri.MakeRelativeUri($to_uri).ToString().Trim('/')
        }
        $Env:CORE_PREFIX = $origin_core_prefix
        return
    }
    ForEach ($i in $prefix_list) {
        if (Test-Path "$InstallPath/$i") {
            $Env:CORE_PREFIX = $i
            return
        }
    }
    $Env:CORE_PREFIX = "core"
}
# 有关 PowerShell 脚本保存编码的问题: https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_character_encoding?view=powershell-7.4#the-byte-order-mark
# 在 PowerShell 5 中 UTF8 为 UTF8 BOM, 而在 PowerShell 7 中 UTF8 为 UTF8, 并且多出 utf8BOM 这个单独的选项: https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.management/set-content?view=powershell-7.5#-encoding
$PS_SCRIPT_ENCODING = if ($PSVersionTable.PSVersion.Major -le 5) { "UTF8" } else { "utf8BOM" }
# Fooocus Installer 版本和检查更新间隔
$FOOOCUS_INSTALLER_VERSION = 201
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
$PIP_EXTRA_INDEX_MIRROR = if ($USE_PIP_MIRROR) { $PIP_EXTRA_INDEX_ADDR } else { $PIP_EXTRA_INDEX_ADDR_ORI }
$PIP_FIND_MIRROR = if ($USE_PIP_MIRROR) { $PIP_FIND_ADDR } else { $PIP_FIND_ADDR_ORI }
$PIP_FIND_MIRROR_CU121 = "https://download.pytorch.org/whl/cu121/torch_stable.html"
$PIP_EXTRA_INDEX_MIRROR_PYTORCH = "https://download.pytorch.org/whl"
$PIP_EXTRA_INDEX_MIRROR_CPU = "https://download.pytorch.org/whl/cpu"
$PIP_EXTRA_INDEX_MIRROR_XPU = "https://download.pytorch.org/whl/xpu"
$PIP_EXTRA_INDEX_MIRROR_CU118 = "https://download.pytorch.org/whl/cu118"
$PIP_EXTRA_INDEX_MIRROR_CU121 = "https://download.pytorch.org/whl/cu121"
$PIP_EXTRA_INDEX_MIRROR_CU124 = "https://download.pytorch.org/whl/cu124"
$PIP_EXTRA_INDEX_MIRROR_CU126 = "https://download.pytorch.org/whl/cu126"
$PIP_EXTRA_INDEX_MIRROR_CU128 = "https://download.pytorch.org/whl/cu128"
$PIP_EXTRA_INDEX_MIRROR_CU129 = "https://download.pytorch.org/whl/cu129"
$PIP_EXTRA_INDEX_MIRROR_CPU_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cpu"
$PIP_EXTRA_INDEX_MIRROR_XPU_NJU = "https://mirror.nju.edu.cn/pytorch/whl/xpu"
$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu118"
$PIP_EXTRA_INDEX_MIRROR_CU121_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu121"
$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu124"
$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu126"
$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu128"
$PIP_EXTRA_INDEX_MIRROR_CU129_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu129"
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
$UV_MINIMUM_VER = "0.8"
# Aria2 最低版本
$ARIA2_MINIMUM_VER = "1.37.0"
# Fooocus 仓库地址
$FOOOCUS_REPO = if ((Test-Path "$PSScriptRoot/install_fooocus.txt") -or ($InstallBranch -eq "fooocus")) {
    "https://github.com/lllyasviel/Fooocus"
} elseif ((Test-Path "$PSScriptRoot/install_fooocus_mre.txt") -or ($InstallBranch -eq "fooocus_mre")) {
    "https://github.com/MoonRide303/Fooocus-MRE"
} elseif ((Test-Path "$PSScriptRoot/install_ruined_fooocus.txt") -or ($InstallBranch -eq "ruined_fooocus")) {
    "https://github.com/runew0lf/RuinedFooocus"
} else {
    "https://github.com/lllyasviel/Fooocus"
}
# PATH
$PYTHON_PATH = "$InstallPath/python"
$PYTHON_EXTRA_PATH = "$InstallPath/$Env:CORE_PREFIX/python"
$PYTHON_SCRIPTS_PATH = "$InstallPath/python/Scripts"
$PYTHON_SCRIPTS_EXTRA_PATH = "$InstallPath/$Env:CORE_PREFIX/python/Scripts"
$GIT_PATH = "$InstallPath/git/bin"
$GIT_EXTRA_PATH = "$InstallPath/$Env:CORE_PREFIX/git/bin"
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
    Write-Host "[Fooocus Installer]" -ForegroundColor Cyan -NoNewline
    Write-Host ":: " -ForegroundColor Blue -NoNewline
    Write-Host "$msg"
}


# 获取内核路径前缀状态
function Get-Core-Prefix-Status {
    if ((Test-Path "$PSScriptRoot/core_prefix.txt") -or ($CorePrefix)) {
        Print-Msg "检测到 core_prefix.txt 配置文件 / -CorePrefix 命令行参数, 使用自定义内核路径前缀"
        if ($CorePrefix) {
            $origin_core_prefix = $CorePrefix
        } else {
            $origin_core_prefix = Get-Content "$PSScriptRoot/core_prefix.txt"
        }
        if ([System.IO.Path]::IsPathRooted($origin_core_prefix.Trim('/').Trim('\'))) {
            Print-Msg "转换绝对路径为内核路径前缀: $origin_core_prefix -> $Env:CORE_PREFIX"
        }
    }
    Print-Msg "当前内核路径前缀: $Env:CORE_PREFIX"
    Print-Msg "完整内核路径: $InstallPath\$Env:CORE_PREFIX"
}


# 显示 Fooocus Installer 版本
function Get-Fooocus-Installer-Version {
    $ver = $([string]$FOOOCUS_INSTALLER_VERSION).ToCharArray()
    $major = ($ver[0..($ver.Length - 3)])
    $minor = $ver[-2]
    $micro = $ver[-1]
    Print-Msg "Fooocus Installer 版本: v${major}.${minor}.${micro}"
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
        Print-Msg "检测到本地存在 disable_proxy.txt 代理配置文件 / -DisableProxy 命令行参数, 禁用自动设置代理"
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
        Print-Msg "检测到本地存在 proxy.txt 代理配置文件 / -UseCustomProxy 命令行参数, 已读取代理配置文件并设置代理"
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
        Print-Msg "检测到 disable_uv.txt 配置文件 / -DisableUV, 命令行参数 已禁用 uv, 使用 Pip 作为 Python 包管理器"
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
    version1 = str(version1)
    version2 = str(version2)
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
                Print-Msg "Python 安装失败, 终止 Fooocus 安装进程, 可尝试重新运行 Fooocus Installer 重试失败的安装"
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
                Print-Msg "Git 安装失败, 终止 Fooocus 安装进程, 可尝试重新运行 Fooocus Installer 重试失败的安装"
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
                Print-Msg "Aria2 安装失败, 终止 Fooocus 安装进程, 可尝试重新运行 Fooocus Installer 重试失败的安装"
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
        Print-Msg "uv 下载失败, 终止 Fooocus 安装进程, 可尝试重新运行 Fooocus Installer 重试失败的安装"
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
        Print-Msg "检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件 / -DisableGithubMirror 命令行参数, 禁用 Github 镜像源"
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
        Print-Msg "检测到本地存在 gh_mirror.txt Github 镜像源配置文件 / -UseCustomGithubMirror 命令行参数, 已读取 Github 镜像源配置文件并设置 Github 镜像源"
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


# Git 仓库下载
function Git-CLone {
    param (
        [String]$url,
        [String]$path
    )

    $name = [System.IO.Path]::GetFileNameWithoutExtension("$url")
    $folder_name = [System.IO.Path]::GetFileName("$path")
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
        $cache_path = "$Env:CACHE_HOME/${folder_name}_tmp"
        # 清理缓存路径
        if (Test-Path "$cache_path") {
            Remove-Item -Path "$cache_path" -Force -Recurse
        }
        git clone --recurse-submodules $url "$cache_path"
        if ($?) { # 检测是否下载成功
            # 清理空文件夹
            if (Test-Path "$path") {
                $random_string = [Guid]::NewGuid().ToString().Substring(0, 18)
                Move-Item -Path "$path" -Destination "$Env:CACHE_HOME/$random_string" -Force
            }
            # 将下载好的文件从缓存文件夹移动到指定路径
            New-Item -ItemType Directory -Path "$([System.IO.Path]::GetDirectoryName($path))" -Force > $null
            Move-Item -Path "$cache_path" -Destination "$path" -Force
            Print-Msg "$name 安装成功"
        } else {
            Print-Msg "$name 安装失败, 终止 Fooocus 安装进程, 可尝试重新运行 Fooocus Installer 重试失败的安装"
            if (!($BuildMode)) {
                Read-Host | Out-Null
            }
            exit 1
        }
    } else {
        Print-Msg "$name 已安装"
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
import json
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


def get_cuda_version() -> float:
    try:
        # 获取 nvidia-smi 输出
        output = subprocess.check_output(['nvidia-smi', '-q'], text=True)
        match = re.search(r'CUDA Version\s+:\s+(\d+\.\d+)', output)
        if match:
            return float(match.group(1))
        return 0.0
    except:
        return 0.0


def get_gpu_list() -> list[dict[str, str]]:
    try:
        cmd = [
            'powershell',
            '-Command',
            'Get-CimInstance Win32_VideoController | Select-Object Name, AdapterCompatibility, AdapterRAM, DriverVersion | ConvertTo-Json'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        gpus = json.loads(result.stdout)
        if isinstance(gpus, dict):
            gpus = [gpus]

        gpu_info = []
        for gpu in gpus:
            gpu_info.append({
                'Name': gpu.get('Name', None),
                'AdapterCompatibility': gpu.get('AdapterCompatibility', None),
                'AdapterRAM': gpu.get('AdapterRAM', None),
                'DriverVersion': gpu.get('DriverVersion', None),
            })
        return gpu_info
    except Exception as _:
        return []


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
    version1 = str(version1)
    version2 = str(version2)
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


def get_pytorch_mirror_type(
    torch_version: str,
    use_xpu: bool = False,
    use_rocm: bool = False,
) -> str:
    # cu118: 2.0.0 ~ 2.4.0
    # cu121: 2.1.1 ~ 2.4.0
    # cu124: 2.4.0 ~ 2.6.0
    # cu126: 2.6.0 ~ 2.7.1
    # cu128: 2.7.0 ~ 2.7.1
    # cu129: 2.8.0 ~
    torch_ver = get_package_version(torch_version)
    cuda_comp_cap = get_cuda_comp_cap()
    cuda_support_ver = get_cuda_version()
    gpu_list = get_gpu_list()
    has_gpus = any([
        x for x in gpu_list
        if 'Intel' in x.get('AdapterCompatibility', '')
        or 'NVIDIA' in x.get('AdapterCompatibility', '')
        or 'Advanced Micro Devices' in x.get('AdapterCompatibility', '')
    ])
    has_xpu = any([
        x for x in gpu_list
        if 'Intel' in x.get('AdapterCompatibility', '')
        and (
            x.get('Name', '').startswith('Intel(R) Arc')
            or
            x.get('Name', '').startswith('Intel(R) Core Ultra')
        )
    ])

    if compare_versions(torch_ver, '2.0.0') == -1:
        # torch < 2.0.0: default cu11x
        if has_gpus:
            return 'cu11x'
    if compare_versions(torch_ver, '2.0.0') >= 0 and compare_versions(torch_ver, '2.3.1') == -1:
        # 2.0.0 <= torch < 2.3.1: default cu118
        if has_gpus:
            return 'cu118'
    if compare_versions(torch_ver, '2.3.0') >= 0 and compare_versions(torch_ver, '2.4.1') == -1:
        # 2.3.0 <= torch < 2.4.1: default cu121
        if compare_versions(str(int(cuda_support_ver * 10)), 'cu121') < 0:
            if compare_versions(str(int(cuda_support_ver * 10)), 'cu118') >= 0:
                return 'cu118'
        if has_gpus:
            return 'cu121'
    if compare_versions(torch_ver, '2.4.0') >= 0 and compare_versions(torch_ver, '2.6.0') == -1:
        # 2.4.0 <= torch < 2.6.0: default cu124
        if compare_versions(str(int(cuda_support_ver * 10)), 'cu124') < 0:
            if compare_versions(str(int(cuda_support_ver * 10)), 'cu121') >= 0:
                return 'cu121'
            if compare_versions(str(int(cuda_support_ver * 10)), 'cu118') >= 0:
                return 'cu118'
        if has_gpus:
            return 'cu124'
    if compare_versions(torch_ver, '2.6.0') >= 0 and compare_versions(torch_ver, '2.7.0') == -1:
        # 2.6.0 <= torch < 2.7.0: default cu126
        if compare_versions(str(int(cuda_support_ver * 10)), 'cu126') < 0:
            if compare_versions(str(int(cuda_support_ver * 10)), 'cu124') >= 0:
                return 'cu124'
        if compare_versions(cuda_comp_cap, '10.0') > 0:
            if compare_versions(str(int(cuda_support_ver * 10)), 'cu128') >= 0:
                return 'cu128'
        if use_xpu and has_xpu:
            return 'xpu'
        if has_gpus:
            return 'cu126'
    if compare_versions(torch_ver, '2.7.0') >= 0 and compare_versions(torch_ver, '2.8.0') == -1:
        # 2.7.0 <= torch < 2.8.0: default cu128
        if compare_versions(str(int(cuda_support_ver * 10)), 'cu128') < 0:
            if compare_versions(str(int(cuda_support_ver * 10)), 'cu126') >= 0:
                return 'cu126'
        if use_xpu and has_xpu:
            return 'xpu'
        if has_gpus:
            return 'cu128'
    if compare_versions(torch_ver, '2.8.0') >= 0:
        # torch >= 2.8.0: default cu129
        if has_gpus:
            return 'cu129'

    return 'cpu'


if __name__ == '__main__':
    print(get_pytorch_mirror_type('$torch_part', use_xpu=True))
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
        cpu {
            Print-Msg "设置 PyTorch 镜像源类型为 cpu"
            $pytorch_mirror_type = "cpu"
            $mirror_index_url = if ($USE_PIP_MIRROR) {
                $PIP_EXTRA_INDEX_MIRROR_CPU_NJU
            } else {
                $PIP_EXTRA_INDEX_MIRROR_CPU
            }
            $mirror_extra_index_url = ""
            $mirror_find_links = ""
        }
        xpu {
            Print-Msg "设置 PyTorch 镜像源类型为 xpu"
            $pytorch_mirror_type = "xpu"
            $mirror_index_url = if ($USE_PIP_MIRROR) {
                $PIP_EXTRA_INDEX_MIRROR_XPU_NJU
            } else {
                $PIP_EXTRA_INDEX_MIRROR_XPU
            }
            $mirror_extra_index_url = ""
            $mirror_find_links = ""
        }
        cu11x {
            Print-Msg "设置 PyTorch 镜像源类型为 cu11x"
            $pytorch_mirror_type = "cu11x"
            $mirror_index_url = $Env:PIP_INDEX_URL
            $mirror_extra_index_url = $Env:PIP_EXTRA_INDEX_URL
            $mirror_find_links = $Env:PIP_FIND_LINKS
        }
        cu118 {
            Print-Msg "设置 PyTorch 镜像源类型为 cu118"
            $pytorch_mirror_type = "cu118"
            $mirror_index_url = if ($USE_PIP_MIRROR) {
                $PIP_EXTRA_INDEX_MIRROR_CU118_NJU
            } else {
                $PIP_EXTRA_INDEX_MIRROR_CU118
            }
            $mirror_extra_index_url = ""
            $mirror_find_links = ""
        }
        cu121 {
            Print-Msg "设置 PyTorch 镜像源类型为 cu121"
            $pytorch_mirror_type = "cu121"
            $mirror_index_url = if ($USE_PIP_MIRROR) {
                $PIP_EXTRA_INDEX_MIRROR_CU121_NJU
            } else {
                $PIP_EXTRA_INDEX_MIRROR_CU121
            }
            $mirror_extra_index_url = ""
            $mirror_find_links = ""
        }
        cu124 {
            Print-Msg "设置 PyTorch 镜像源类型为 cu124"
            $pytorch_mirror_type = "cu124"
            $mirror_index_url = if ($USE_PIP_MIRROR) {
                $PIP_EXTRA_INDEX_MIRROR_CU124_NJU
            } else {
                $PIP_EXTRA_INDEX_MIRROR_CU124
            }
            $mirror_extra_index_url = ""
            $mirror_find_links = ""
        }
        cu126 {
            Print-Msg "设置 PyTorch 镜像源类型为 cu126"
            $pytorch_mirror_type = "cu126"
            $mirror_index_url = if ($USE_PIP_MIRROR) {
                $PIP_EXTRA_INDEX_MIRROR_CU126_NJU
            } else {
                $PIP_EXTRA_INDEX_MIRROR_CU126
            }
            $mirror_extra_index_url = ""
            $mirror_find_links = ""
        }
        cu128 {
            Print-Msg "设置 PyTorch 镜像源类型为 cu128"
            $pytorch_mirror_type = "cu128"
            $mirror_index_url = if ($USE_PIP_MIRROR) {
                $PIP_EXTRA_INDEX_MIRROR_CU128_NJU
            } else {
                $PIP_EXTRA_INDEX_MIRROR_CU128
            }
            $mirror_extra_index_url = ""
            $mirror_find_links = ""
        }
        cu129 {
            Print-Msg "设置 PyTorch 镜像源类型为 cu129"
            $pytorch_mirror_type = "cu129"
            $mirror_index_url = if ($USE_PIP_MIRROR) {
                $PIP_EXTRA_INDEX_MIRROR_CU129_NJU
            } else {
                $PIP_EXTRA_INDEX_MIRROR_CU129
            }
            $mirror_extra_index_url = ""
            $mirror_find_links = ""
        }
        Default {
            Print-Msg "未知的 PyTorch 镜像源类型: $mirror_type, 使用默认 PyTorch 镜像源"
            $pytorch_mirror_type = "null"
            $mirror_index_url = $Env:PIP_INDEX_URL
            $mirror_extra_index_url = $Env:PIP_EXTRA_INDEX_URL
            $mirror_find_links = $Env:PIP_FIND_LINKS
        }
    }
    return $mirror_index_url, $mirror_extra_index_url, $mirror_find_links, $pytorch_mirror_type
}


# 为 PyTorch 获取合适的 CUDA 版本类型
function Get-Appropriate-CUDA-Version-Type {
    $content = "
import re
import json
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


def get_cuda_version() -> float:
    try:
        # 获取 nvidia-smi 输出
        output = subprocess.check_output(['nvidia-smi', '-q'], text=True)
        match = re.search(r'CUDA Version\s+:\s+(\d+\.\d+)', output)
        if match:
            return float(match.group(1))
        return 0.0
    except:
        return 0.0


def get_gpu_list() -> list[dict[str, str]]:
    try:
        cmd = [
            'powershell',
            '-Command',
            'Get-CimInstance Win32_VideoController | Select-Object Name, AdapterCompatibility, AdapterRAM, DriverVersion | ConvertTo-Json'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        gpus = json.loads(result.stdout)
        if isinstance(gpus, dict):
            gpus = [gpus]

        gpu_info = []
        for gpu in gpus:
            gpu_info.append({
                'Name': gpu.get('Name', None),
                'AdapterCompatibility': gpu.get('AdapterCompatibility', None),
                'AdapterRAM': gpu.get('AdapterRAM', None),
                'DriverVersion': gpu.get('DriverVersion', None),
            })
        return gpu_info
    except Exception as _:
        return []


def compare_versions(version1: str, version2: str) -> int:
    version1 = str(version1)
    version2 = str(version2)
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


def select_avaliable_type() -> str:
    cuda_comp_cap = get_cuda_comp_cap()
    cuda_support_ver = get_cuda_version()

    if compare_versions(cuda_support_ver, '12.9') >= 0:
        return 'cu129'
    elif compare_versions(cuda_support_ver, '12.8') >= 0:
        return 'cu128'
    elif compare_versions(cuda_support_ver, '12.6') >= 0:
        return 'cu126'
    elif compare_versions(cuda_support_ver, '12.4') >= 0:
        return 'cu124'
    elif compare_versions(cuda_support_ver, '12.1') >= 0:
        return 'cu121'
    elif compare_versions(cuda_support_ver, '11.8') >= 0:
        return 'cu118'
    elif compare_versions(cuda_comp_cap, '10.0') > 0:
        return 'cu128' # RTX 50xx
    elif compare_versions(cuda_comp_cap, '0.0') > 0:
        return 'cu118' # 其他 Nvidia 显卡
    else:
        gpus = get_gpu_list()
        if any([
            x for x in gpus
            if 'Intel' in x.get('AdapterCompatibility', '')
            and (
                x.get('Name', '').startswith('Intel(R) Arc')
                or
                x.get('Name', '').startswith('Intel(R) Core Ultra')
            )
        ]):
            return 'xpu'

        if any([
            x for x in gpus
            if 'NVIDIA' in x.get('AdapterCompatibility', '')
            or 'Advanced Micro Devices' in x.get('AdapterCompatibility', '')
        ]):
            return 'cu118'

    return 'cpu'


if __name__ == '__main__':
    print(select_avaliable_type())
".Trim()

    return $(python -c "$content")
}


# 获取合适的 PyTorch / xFormers 版本
function Get-PyTorch-And-xFormers-Package {
    Print-Msg "设置 PyTorch 和 xFormers 版本"

    if ($PyTorchPackage) {
        # 使用自定义的 PyTorch / xFormers 版本
        if ($xFormersPackage){
            return $PyTorchPackage, $xFormersPackage
        } else {
            return $PyTorchPackage, $null
        }
    }

    if ($PyTorchMirrorType) {
        Print-Msg "根据 $PyTorchMirrorType 类型的 PyTorch 镜像源配置 PyTorch 组合"
        $appropriate_cuda_version = $PyTorchMirrorType
    } else {
        $appropriate_cuda_version = Get-Appropriate-CUDA-Version-Type
    }

    switch ($appropriate_cuda_version) {
        cu129 {
            $pytorch_package = "torch==2.8.0+cu129 torchvision==0.23.0+cu129 torchaudio==2.8.0+cu129"
            $xformers_package = "xformers==0.0.32.post2"
            break
        }
        cu128 {
            $pytorch_package = "torch==2.8.0+cu128 torchvision==0.23.0+cu128 torchaudio==2.8.0+cu128"
            $xformers_package = "xformers==0.0.32.post2"
            break
        }
        cu126 {
            $pytorch_package = "torch==2.8.0+cu126 torchvision==0.23.0+cu126 torchaudio==2.8.0+cu126"
            $xformers_package = "xformers==0.0.32.post2"
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
        xpu {
            $pytorch_package = "torch==2.8.0+xpu torchvision==0.23.0+xpu torchaudio==2.8.0+xpu"
            $xformers_package = $null
            break
        }
        cpu {
            $pytorch_package = "torch==2.8.0+cpu torchvision==0.23.0+cpu torchaudio==2.8.0+cpu"
            $xformers_package = $null
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
    $mirror_pip_index_url, $mirror_pip_extra_index_url, $mirror_pip_find_links, $pytorch_mirror_type = Get-PyTorch-Mirror $pytorch_package

    # 备份镜像源配置
    $tmp_pip_index_url = $Env:PIP_INDEX_URL
    $tmp_uv_default_index = $Env:UV_DEFAULT_INDEX
    $tmp_pip_extra_index_url = $Env:PIP_EXTRA_INDEX_URL
    $tmp_uv_index = $Env:UV_INDEX
    $tmp_pip_find_links = $Env:PIP_FIND_LINKS
    $tmp_uv_find_links = $Env:UV_FIND_LINKS

    # 设置新的镜像源
    $Env:PIP_INDEX_URL = $mirror_pip_index_url
    $Env:UV_DEFAULT_INDEX = $mirror_pip_index_url
    $Env:PIP_EXTRA_INDEX_URL = $mirror_pip_extra_index_url
    $Env:UV_INDEX = $mirror_pip_extra_index_url
    $Env:PIP_FIND_LINKS = $mirror_pip_find_links
    $Env:UV_FIND_LINKS = $mirror_pip_find_links

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
            Print-Msg "PyTorch 安装失败, 终止 Fooocus 安装进程, 可尝试重新运行 Fooocus Installer 重试失败的安装"
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
        if ($xformers_package) {
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
                Print-Msg "xFormers 安装失败, 终止 ComfyUI 安装进程, 可尝试重新运行 ComfyUI Installer 重试失败的安装"
                if (!($BuildMode)) {
                    Read-Host | Out-Null
                }
                exit 1
            }
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


# 安装 Fooocus 依赖
function Install-Fooocus-Dependence {
    # 记录脚本所在路径
    $current_path = $(Get-Location).ToString()
    Set-Location "$InstallPath/$Env:CORE_PREFIX"
    $dep_path = "$InstallPath/$Env:CORE_PREFIX/requirements_versions.txt"

    Print-Msg "安装 Fooocus 依赖中"
    if ($USE_UV) {
        uv pip install -r "$dep_path"
        if (!($?)) {
            Print-Msg "检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装"
            python -m pip install -r "$dep_path"
        }
    } else {
        python -m pip install -r "$dep_path"
    }
    if ($?) {
        Print-Msg "Fooocus 依赖安装成功"
    } else {
        Print-Msg "Fooocus 依赖安装失败, 终止 Fooocus 安装进程, 可尝试重新运行 Fooocus Installer 重试失败的安装"
        Set-Location "$current_path"
        if (!($BuildMode)) {
            Read-Host | Out-Null
        }
        exit 1
    }
    Set-Location "$current_path"
}


# 模型下载器
function Model-Downloader ($download_list) {
    $sum = $download_list.Count
    for ($i = 0; $i -lt $download_list.Count; $i++) {
        $content = $download_list[$i]
        $url = $content[0]
        $path = $content[1]
        $file = $content[2]
        $model_full_path = Join-Path -Path $path -ChildPath $file
        if (Test-Path $model_full_path) {
            Print-Msg "[$($i + 1)/$sum] $file 模型已存在于 $path 中"
        } else {
            Print-Msg "[$($i + 1)/$sum] 下载 $file 模型到 $path 中"
            aria2c --file-allocation=none --summary-interval=0 --console-log-level=error -s 64 -c -x 16 -k 1M $url -d "$path" -o "$file"
            if ($?) {
                Print-Msg "[$($i + 1)/$sum] $file 下载成功"
            } else {
                Print-Msg "[$($i + 1)/$sum] $file 下载失败"
            }
        }
    }
}


# 更新 Fooocus 预设文件
function Update-Fooocus-Preset {
    $fooocus_preset_json_content = @{
        "default_model" = "Illustrious-XL-v1.0.safetensors"
        "default_refiner" = "None"
        "default_refiner_switch" = 0.8
        "default_loras" = @(
            @("None", 1.0),
            @("None", 1.0),
            @("None", 1.0),
            @("None", 1.0),
            @("None", 1.0)
        )
        "default_cfg_scale" = 5.0
        "default_sample_sharpness" = 2.0
        "default_sampler" = "euler_ancestral"
        "default_scheduler" = "sgm_uniform"
        "default_performance" = "Speed"
        "default_prompt" = "`nmasterpiece,best quality,newest,"
        "default_prompt_negative" = "low quality,worst quality,normal quality,text,signature,jpeg artifacts,bad anatomy,old,early,copyright name,watermark,artist name,signature,"
        "default_styles" = @()
        "default_image_number" = 1
        "default_aspect_ratio" = "1344*1008"
        "checkpoint_downloads" = @{
            "Illustrious-XL-v1.0.safetensors" = "https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/Illustrious-XL-v1.0.safetensors"
        }
        "embeddings_downloads" = @{}
        "lora_downloads" = @{}
        "available_aspect_ratios" = @(
            "704*1408", "704*1344", "768*1344", "768*1280", "832*1216", "1216*832", "832*1152", "896*1152", "896*1088", "960*1088", 
            "960*1024", "1024*1024", "1024*960", "1088*960", "1088*896", "1152*896", "1152*832", "1216*832", "1280*768", "1344*768", 
            "1344*704", "1408*704", "1472*704", "1536*640", "1600*640", "1664*576", "1728*576", "1920*1080", "1080*1920", "576*1024", 
            "768*1024", "1024*576", "1024*768", "1024*1024", "2048*2048", "1536*864", "864*1536", "1472*828", "828*1472", "1344*756", 
            "756*1344", "1344*1008", "1008*1344", "1536*1152", "1152*1536", "1472*1104", "1104*1472", "1920*640", "1920*824", "824*1920", 
            "1920*768", "1536*768", "1488*640", "1680*720"
        )
        "default_save_metadata_to_images" = $true
        "default_metadata_scheme" = "a1111"
        "default_clip_skip" = 2
        "default_black_out_nsfw" = $false
        "metadata_created_by" = "Fooocus"
        "default_developer_debug_mode_checkbox" = $true
        "default_describe_apply_prompts_checkbox" = $false
        "default_describe_content_type" = @(
            "Art/Anime"
        )
    }

    $fooocus_language_zh_json_content = @{
        "Preview" = "预览"
        "Gallery" = "相册"
        "Generate" = "生成"
        "Skip" = "跳过"
        "Stop" = "停止"
        "Input Image" = "图生图"
        "Advanced" = "高级设置"
        "Upscale or Variation" = "放大或重绘"
        "Image Prompt" = "参考图"
        "Inpaint or Outpaint (beta)" = "内部重绘或外部扩展（测试版）"
        "Drag above image to here" = "将图像拖到这里"
        "Upscale or Variation:" = "放大或重绘："
        "Disabled" = "禁用"
        "Vary (Subtle)" = "变化（微妙）"
        "Vary (Strong)" = "变化（强烈）"
        "Upscale (1.5x)" = "放大（1.5 倍）"
        "Upscale (2x)" = "放大（2 倍）"
        "Upscale (Fast 2x)" = "快速放大（2 倍）"
        "📔 Document" = "📔 说明文档"
        "Image" = "图像"
        "Stop At" = "停止于"
        "Weight" = "权重"
        "Type" = "类型"
        "PyraCanny" = "边缘检测"
        "CPDS" = "深度结构检测"
        "* `"Image Prompt`" is powered by Fooocus Image Mixture Engine (v1.0.1)." = "* `“图生图`”由 Fooocus 图像混合引擎提供支持（v1.0.1）。"
        "The scaler multiplied to positive ADM (use 1.0 to disable)." = "正向 ADM 的缩放倍数（使用 1.0 禁用）。"
        "The scaler multiplied to negative ADM (use 1.0 to disable)." = "反向 ADM 的缩放倍数（使用 1.0 禁用）。"
        "When to end the guidance from positive/negative ADM." = "何时结束来自正向 / 反向 ADM 的指导。"
        "Similar to the Control Mode in A1111 (use 0.0 to disable)." = "类似于 SD WebUI 中的控制模式（使用 0.0 禁用）。"
        "Outpaint Expansion (" = "外部扩展 ("
        "Outpaint" = "外部重绘"
        "Left" = "向左扩展"
        "Right" = "向右扩展"
        "Top" = "向上扩展"
        "Bottom" = "向下扩展"
        "* `"Inpaint or Outpaint`" is powered by the sampler `"DPMPP Fooocus Seamless 2M SDE Karras Inpaint Sampler`" (beta)" = "* `“内部填充或外部填充`”由`“DPMPP Fooocus Seamless 2M SDE Karras Inpaint Sampler`”（测试版）采样器提供支持"
        "Setting" = "设置"
        "Style" = "样式"
        "Performance" = "性能"
        "Speed" = "均衡"
        "Quality" = "质量"
        "Extreme Speed" = "LCM 加速"
        "Lightning" = "SDXL Lightning 加速"
        "Hyper-SD" = "Hyper SD 加速"
        "Aspect Ratios" = "宽高比"
        "896×1152" = "896×1152"
        "width × height" = "宽 × 高"
        "704×1408" = "704×1408"
        "704×1344" = "704×1344"
        "768×1344" = "768×1344"
        "768×1280" = "768×1280"
        "832×1216" = "832×1216"
        "832×1152" = "832×1152"
        "896×1088" = "896×1088"
        "960×1088" = "960×1088"
        "960×1024" = "960×1024"
        "1024×1024" = "1024×1024"
        "1024×960" = "1024×960"
        "1088×960" = "1088×960"
        "1088×896" = "1088×896"
        "1152×832" = "1152×832"
        "1216×832" = "1216×832"
        "1280×768" = "1280×768"
        "1344×768" = "1344×768"
        "1344×704" = "1344×704"
        "1408×704" = "1408×704"
        "1472×704" = "1472×704"
        "1536×640" = "1536×640"
        "1600×640" = "1600×640"
        "1664×576" = "1664×576"
        "1728×576" = "1728×576"
        "Image Number" = "出图数量"
        "Negative Prompt" = "反向提示词"
        "Describing what you do not want to see." = "描述你不想看到的内容。"
        "Random" = "随机种子"
        "Seed" = "种子"
        "📚 History Log" = "📚 历史记录"
        "Image Style" = "图像风格"
        "Fooocus V2" = "Fooocus V2 风格"
        "Default (Slightly Cinematic)" = "默认（轻微的电影感）"
        "Fooocus Masterpiece" = "Fooocus - 杰作"
        "Random Style" = "随机风格"
        "Fooocus Photograph" = "Fooocus - 照片"
        "Fooocus Negative" = "Fooocus - 反向提示词"
        "SAI 3D Model" = "SAI - 3D模型"
        "SAI Analog Film" = "SAI - 模拟电影"
        "SAI Anime" = "SAI - 动漫"
        "SAI Cinematic" = "SAI - 电影片段"
        "SAI Comic Book" = "SAI - 漫画"
        "SAI Craft Clay" = "SAI - 工艺粘土"
        "SAI Digital Art" = "SAI - 数字艺术"
        "SAI Enhance" = "SAI - 增强"
        "SAI Fantasy Art" = "SAI - 奇幻艺术"
        "SAI Isometric" = "SAI - 等距风格"
        "SAI Line Art" = "SAI - 线条艺术"
        "SAI Lowpoly" = "SAI - 低多边形"
        "SAI Neonpunk" = "SAI - 霓虹朋克"
        "SAI Origami" = "SAI - 折纸"
        "SAI Photographic" = "SAI - 摄影"
        "SAI Pixel Art" = "SAI - 像素艺术"
        "SAI Texture" = "SAI - 纹理"
        "MRE Cinematic Dynamic" = "MRE - 史诗电影"
        "MRE Spontaneous Picture" = "MRE - 自发图片"
        "MRE Artistic Vision" = "MRE - 艺术视觉"
        "MRE Dark Dream" = "MRE - 黑暗梦境"
        "MRE Gloomy Art" = "MRE - 阴郁艺术"
        "MRE Bad Dream" = "MRE - 噩梦"
        "MRE Underground" = "MRE - 阴森地下"
        "MRE Surreal Painting" = "MRE - 超现实主义绘画"
        "MRE Dynamic Illustration" = "MRE - 动态插画"
        "MRE Undead Art" = "MRE - 遗忘艺术家作品"
        "MRE Elemental Art" = "MRE - 元素艺术"
        "MRE Space Art" = "MRE - 空间艺术"
        "MRE Ancient Illustration" = "MRE - 古代插图"
        "MRE Brave Art" = "MRE - 勇敢艺术"
        "MRE Heroic Fantasy" = "MRE - 英雄幻想"
        "MRE Dark Cyberpunk" = "MRE - 黑暗赛博朋克"
        "MRE Lyrical Geometry" = "MRE - 抒情几何抽象画"
        "MRE Sumi E Symbolic" = "MRE - 墨绘长笔画"
        "MRE Sumi E Detailed" = "MRE - 精细墨绘画"
        "MRE Manga" = "MRE - 日本漫画"
        "MRE Anime" = "MRE - 日本动画片"
        "MRE Comic" = "MRE - 成人漫画书插画"
        "Ads Advertising" = "广告 - 广告"
        "Ads Automotive" = "广告 - 汽车"
        "Ads Corporate" = "广告 - 企业品牌"
        "Ads Fashion Editorial" = "广告 - 时尚编辑"
        "Ads Food Photography" = "广告 - 美食摄影"
        "Ads Gourmet Food Photography" = "广告 - 美食摄影"
        "Ads Luxury" = "广告 - 奢侈品"
        "Ads Real Estate" = "广告 - 房地产"
        "Ads Retail" = "广告 - 零售"
        "Artstyle Abstract" = "艺术风格 - 抽象"
        "Artstyle Abstract Expressionism" = "艺术风格 - 抽象表现主义"
        "Artstyle Art Deco" = "艺术风格 - 装饰艺术"
        "Artstyle Art Nouveau" = "艺术风格 - 新艺术"
        "Artstyle Constructivist" = "艺术风格 - 构造主义"
        "Artstyle Cubist" = "艺术风格 - 立体主义"
        "Artstyle Expressionist" = "艺术风格 - 表现主义"
        "Artstyle Graffiti" = "艺术风格 - 涂鸦"
        "Artstyle Hyperrealism" = "艺术风格 - 超写实主义"
        "Artstyle Impressionist" = "艺术风格 - 印象派"
        "Artstyle Pointillism" = "艺术风格 - 点彩派"
        "Artstyle Pop Art" = "艺术风格 - 波普艺术"
        "Artstyle Psychedelic" = "艺术风格 - 迷幻"
        "Artstyle Renaissance" = "艺术风格 - 文艺复兴"
        "Artstyle Steampunk" = "艺术风格 - 蒸汽朋克"
        "Artstyle Surrealist" = "艺术风格 - 超现实主义"
        "Artstyle Typography" = "艺术风格 - 字体设计"
        "Artstyle Watercolor" = "艺术风格 - 水彩"
        "Futuristic Biomechanical" = "未来主义 - 生物机械"
        "Futuristic Biomechanical Cyberpunk" = "未来主义 - 生物机械 - 赛博朋克"
        "Futuristic Cybernetic" = "未来主义 - 人机融合"
        "Futuristic Cybernetic Robot" = "未来主义 - 人机融合 - 机器人"
        "Futuristic Cyberpunk Cityscape" = "未来主义 - 赛博朋克城市"
        "Futuristic Futuristic" = "未来主义 - 未来主义"
        "Futuristic Retro Cyberpunk" = "未来主义 - 复古赛博朋克"
        "Futuristic Retro Futurism" = "未来主义 - 复古未来主义"
        "Futuristic Sci Fi" = "未来主义 - 科幻"
        "Futuristic Vaporwave" = "未来主义 - 蒸汽波"
        "Game Bubble Bobble" = "游戏 - 泡泡龙"
        "Game Cyberpunk Game" = "游戏 - 赛博朋克游戏"
        "Game Fighting Game" = "游戏 - 格斗游戏"
        "Game Gta" = "游戏 - 侠盗猎车手"
        "Game Mario" = "游戏 - 马里奥"
        "Game Minecraft" = "游戏 - 我的世界"
        "Game Pokemon" = "游戏 - 宝可梦"
        "Game Retro Arcade" = "游戏 - 复古街机"
        "Game Retro Game" = "游戏 - 复古游戏"
        "Game Rpg Fantasy Game" = "游戏 - 角色扮演幻想游戏"
        "Game Strategy Game" = "游戏 - 策略游戏"
        "Game Streetfighter" = "游戏 - 街头霸王"
        "Game Zelda" = "游戏 - 塞尔达传说"
        "Misc Architectural" = "其他 - 建筑"
        "Misc Disco" = "其他 - 迪斯科"
        "Misc Dreamscape" = "其他 - 梦境"
        "Misc Dystopian" = "其他 - 反乌托邦"
        "Misc Fairy Tale" = "其他 - 童话故事"
        "Misc Gothic" = "其他 - 哥特风"
        "Misc Grunge" = "其他 - 垮掉的"
        "Misc Horror" = "其他 - 恐怖"
        "Misc Kawaii" = "其他 - 可爱"
        "Misc Lovecraftian" = "其他 - 洛夫克拉夫特"
        "Misc Macabre" = "其他 - 恐怖"
        "Misc Manga" = "其他 - 漫画"
        "Misc Metropolis" = "其他 - 大都市"
        "Misc Minimalist" = "其他 - 极简主义"
        "Misc Monochrome" = "其他 - 单色"
        "Misc Nautical" = "其他 - 航海"
        "Misc Space" = "其他 - 太空"
        "Misc Stained Glass" = "其他 - 彩色玻璃"
        "Misc Techwear Fashion" = "其他 - 科技时尚"
        "Misc Tribal" = "其他 - 部落"
        "Misc Zentangle" = "其他 - 禅绕画"
        "Papercraft Collage" = "手工艺 - 拼贴"
        "Papercraft Flat Papercut" = "手工艺 - 平面剪纸"
        "Papercraft Kirigami" = "手工艺 - 切纸"
        "Papercraft Paper Mache" = "手工艺 - 纸浆塑造"
        "Papercraft Paper Quilling" = "手工艺 - 纸艺卷轴"
        "Papercraft Papercut Collage" = "手工艺 - 剪纸拼贴"
        "Papercraft Papercut Shadow Box" = "手工艺 - 剪纸影箱"
        "Papercraft Stacked Papercut" = "手工艺 - 层叠剪纸"
        "Papercraft Thick Layered Papercut" = "手工艺 - 厚层剪纸"
        "Photo Alien" = "摄影 - 外星人"
        "Photo Film Noir" = "摄影 - 黑色电影"
        "Photo Glamour" = "摄影 - 魅力"
        "Photo Hdr" = "摄影 - 高动态范围"
        "Photo Iphone Photographic" = "摄影 - 苹果手机摄影"
        "Photo Long Exposure" = "摄影 - 长曝光"
        "Photo Neon Noir" = "摄影 - 霓虹黑色"
        "Photo Silhouette" = "摄影 - 轮廓"
        "Photo Tilt Shift" = "摄影 - 移轴"
        "Cinematic Diva" = "电影女主角"
        "Abstract Expressionism" = "抽象表现主义"
        "Academia" = "学术"
        "Action Figure" = "动作人偶"
        "Adorable 3D Character" = "可爱的3D角色"
        "Adorable Kawaii" = "可爱的卡哇伊"
        "Art Deco" = "装饰艺术"
        "Art Nouveau" = "新艺术，美丽艺术"
        "Astral Aura" = "星体光环"
        "Avant Garde" = "前卫"
        "Baroque" = "巴洛克"
        "Bauhaus Style Poster" = "包豪斯风格海报"
        "Blueprint Schematic Drawing" = "蓝图示意图"
        "Caricature" = "漫画"
        "Cel Shaded Art" = "卡通渲染"
        "Character Design Sheet" = "角色设计表"
        "Classicism Art" = "古典主义艺术"
        "Color Field Painting" = "色彩领域绘画"
        "Colored Pencil Art" = "彩色铅笔艺术"
        "Conceptual Art" = "概念艺术"
        "Constructivism" = "建构主义"
        "Cubism" = "立体主义"
        "Dadaism" = "达达主义"
        "Dark Fantasy" = "黑暗奇幻"
        "Dark Moody Atmosphere" = "黑暗忧郁气氛"
        "Dmt Art Style" = "迷幻艺术风格"
        "Doodle Art" = "涂鸦艺术"
        "Double Exposure" = "双重曝光"
        "Dripping Paint Splatter Art" = "滴漆飞溅艺术"
        "Expressionism" = "表现主义"
        "Faded Polaroid Photo" = "褪色的宝丽来照片"
        "Fauvism" = "野兽派"
        "Flat 2d Art" = "平面 2D 艺术"
        "Fortnite Art Style" = "堡垒之夜艺术风格"
        "Futurism" = "未来派"
        "Glitchcore" = "故障核心"
        "Glo Fi" = "光明高保真"
        "Googie Art Style" = "古吉艺术风格"
        "Graffiti Art" = "涂鸦艺术"
        "Harlem Renaissance Art" = "哈莱姆文艺复兴艺术"
        "High Fashion" = "高级时装"
        "Idyllic" = "田园诗般"
        "Impressionism" = "印象派"
        "Infographic Drawing" = "信息图表绘图"
        "Ink Dripping Drawing" = "滴墨绘画"
        "Japanese Ink Drawing" = "日式水墨画"
        "Knolling Photography" = "规律摆放摄影"
        "Light Cheery Atmosphere" = "轻松愉快的气氛"
        "Logo Design" = "标志设计"
        "Luxurious Elegance" = "奢华优雅"
        "Macro Photography" = "微距摄影"
        "Mandola Art" = "曼陀罗艺术"
        "Marker Drawing" = "马克笔绘图"
        "Medievalism" = "中世纪主义"
        "Minimalism" = "极简主义"
        "Neo Baroque" = "新巴洛克"
        "Neo Byzantine" = "新拜占庭"
        "Neo Futurism" = "新未来派"
        "Neo Impressionism" = "新印象派"
        "Neo Rococo" = "新洛可可"
        "Neoclassicism" = "新古典主义"
        "Op Art" = "欧普艺术"
        "Ornate And Intricate" = "华丽而复杂"
        "Pencil Sketch Drawing" = "铅笔素描"
        "Pop Art 2" = "流行艺术2"
        "Rococo" = "洛可可"
        "Silhouette Art" = "剪影艺术"
        "Simple Vector Art" = "简单矢量艺术"
        "Sketchup" = "草图"
        "Steampunk 2" = "赛博朋克2"
        "Surrealism" = "超现实主义"
        "Suprematism" = "至上主义"
        "Terragen" = "地表风景"
        "Tranquil Relaxing Atmosphere" = "宁静轻松的氛围"
        "Sticker Designs" = "贴纸设计"
        "Vibrant Rim Light" = "生动的边缘光"
        "Volumetric Lighting" = "体积照明"
        "Watercolor 2" = "水彩2"
        "Whimsical And Playful" = "异想天开、俏皮"
        "Fooocus Cinematic" = "Fooocus - 电影"
        "Fooocus Enhance" = "Fooocus - 增强"
        "Fooocus Sharp" = "Fooocus - 锐化"
        "Mk Chromolithography" = "MK - 彩色平版印刷"
        "Mk Cross Processing Print" = "MK - 交叉处理"
        "Mk Dufaycolor Photograph" = "MK - 杜菲色"
        "Mk Herbarium" = "MK - 标本"
        "Mk Punk Collage" = "MK - 拼贴朋克"
        "Mk Mosaic" = "MK - 马赛克"
        "Mk Van Gogh" = "MK - 梵高"
        "Mk Coloring Book" = "MK - 简笔画"
        "Mk Singer Sargent" = "MK - 辛格·萨金特"
        "Mk Pollock" = "MK - 波洛克"
        "Mk Basquiat" = "MK - 巴斯奇亚"
        "Mk Andy Warhol" = "MK - 安迪·沃霍尔"
        "Mk Halftone Print" = "MK - 半色调"
        "Mk Gond Painting" = "MK - 贡德艺术"
        "Mk Albumen Print" = "MK - 蛋白银印相"
        "Mk Inuit Carving" = "MK - 因纽特雕塑艺术"
        "Mk Bromoil Print" = "MK - 溴油印"
        "Mk Calotype Print" = "MK - 卡洛型"
        "Mk Color Sketchnote" = "MK - 涂鸦"
        "Mk Cibulak Porcelain" = "MK - 蓝洋葱"
        "Mk Alcohol Ink Art" = "MK - 墨画"
        "Mk One Line Art" = "MK - 单线艺术"
        "Mk Blacklight Paint" = "MK - 黑白艺术"
        "Mk Carnival Glass" = "MK - 彩虹色玻璃"
        "Mk Cyanotype Print" = "MK - 蓝晒"
        "Mk Cross Stitching" = "MK - 十字绣"
        "Mk Encaustic Paint" = "MK - 热蜡画"
        "Mk Embroidery" = "MK - 刺绣"
        "Mk Gyotaku" = "MK - 鱼拓"
        "Mk Luminogram" = "MK - 发光图"
        "Mk Lite Brite Art" = "MK - 灯光创意"
        "Mk Mokume Gane" = "MK - 木目金"
        "Pebble Art" = "鹅卵石艺术"
        "Mk Palekh" = "MK - 缩影"
        "Mk Suminagashi" = "MK - 漂浮墨水"
        "Mk Scrimshaw" = "MK - 斯克林肖"
        "Mk Shibori" = "MK - 手工扎染"
        "Mk Vitreous Enamel" = "MK - 搪瓷"
        "Mk Ukiyo E" = "MK - 浮世绘"
        "Mk Vintage Airline Poster" = "MK - 复古艺术"
        "Mk Vintage Travel Poster" = "MK - 复古艺术旅行"
        "Mk Bauhaus Style" = "MK - 包豪斯设计风格"
        "Mk Afrofuturism" = "MK - 未来主义"
        "Mk Atompunk" = "MK - 原子朋克"
        "Mk Constructivism" = "MK - 建构"
        "Mk Chicano Art" = "MK - 奇卡诺艺术"
        "Mk De Stijl" = "MK - 荷兰风格"
        "Mk Dayak Art" = "MK - 达雅克艺术"
        "Mk Fayum Portrait" = "MK - 法尤姆风格"
        "Mk Illuminated Manuscript" = "MK - 泥金装饰手抄"
        "Mk Kalighat Painting" = "MK - 卡利加特绘画"
        "Mk Madhubani Painting" = "MK - 马杜巴尼艺术"
        "Mk Pictorialism" = "MK - 绘画摄影"
        "Mk Pichwai Painting" = "MK - 皮切瓦伊"
        "Mk Patachitra Painting" = "MK - 粘土艺术"
        "Mk Samoan Art Inspired" = "MK - 萨摩亚艺术"
        "Mk Tlingit Art" = "MK - 特林吉特艺术"
        "Mk Adnate Style" = "MK - 具象艺术"
        "Mk Ron English Style" = "MK - 罗恩·英格利斯"
        "Mk Shepard Fairey Style" = "MK - 街头艺术"
        "Fooocus Semi Realistic" = "Fooocus - 半现实风格"
        "Mk Anthotype Print" = "MK - 花汁印相"
        "Mk Aquatint Print" = "MK - 飞尘腐蚀版画"
        "Model" = "模型"
        "Base Model (SDXL only)" = "基础模型（只支持 SDXL）"
        "Refiner (SDXL or SD 1.5)" = "精修模型 （支持 SDXL 或 SD 1.5）"
        "None" = "无"
        "LoRAs" = "LoRAs 模型"
        "SDXL LoRA 1" = "SDXL LoRA 模型 1"
        "SDXL LoRA 2" = "SDXL LoRA 模型 2"
        "SDXL LoRA 3" = "SDXL LoRA 模型 3"
        "SDXL LoRA 4" = "SDXL LoRA 模型 4"
        "SDXL LoRA 5" = "SDXL LoRA 模型 5"
        "LoRA 1" = "LoRA 模型 1"
        "LoRA 2" = "LoRA 模型 2"
        "LoRA 3" = "LoRA 模型 3"
        "LoRA 4" = "LoRA 模型 4"
        "LoRA 5" = "LoRA 模型 5"
        "Refresh" = "Refresh"
        "🔄 Refresh All Files" = "🔄 刷新全部文件"
        "Sampling Sharpness" = "采样清晰度"
        "Higher value means image and texture are sharper." = "值越大，图像和纹理越清晰。"
        "Guidance Scale" = "提示词引导系数"
        "Higher value means style is cleaner, vivider, and more artistic." = "提示词作用的强度，值越大，风格越干净、生动、更具艺术感。"
        "Developer Debug Mode" = "开发者调试模式"
        "Developer Debug Tools" = "开发者调试工具"
        "Positive ADM Guidance Scaler" = "正向 ADM 引导系数"
        "The scaler multiplied to positive ADM (use 1.0 to disable). " = "正向 ADM 引导的倍率 （使用 1.0 以禁用）。 "
        "Negative ADM Guidance Scaler" = "负向 ADM 引导系数"
        "The scaler multiplied to negative ADM (use 1.0 to disable). " = "负向 ADM 引导的倍率（使用 1.0 以禁用）。 "
        "ADM Guidance End At Step" = "ADM 引导结束步长"
        "When to end the guidance from positive/negative ADM. " = "正向 / 负向 ADM 结束引导的时间。 "
        "Refiner swap method" = "Refiner 精炼模型交换方式"
        "joint" = "joint 联合"
        "separate" = "separate 分离"
        "CFG Mimicking from TSNR" = "从 TSNR 模拟 CFG"
        "Enabling Fooocus's implementation of CFG mimicking for TSNR (effective when real CFG > mimicked CFG)." = "启用 Fooocus 的 TSNR 模拟 CFG 的功能（当真实的 CFG 大于模拟的 CFG 时生效）。"
        "Sampler" = "采样器"
        "dpmpp_2m_sde_gpu" = "dpmpp_2m_sde_gpu"
        "Only effective in non-inpaint mode." = "仅在非重绘模式下有效。"
        "euler" = "euler"
        "euler_ancestral" = "euler_ancestral"
        "heun" = "heun"
        "dpm_2" = "dpm_2"
        "dpm_2_ancestral" = "dpm_2_ancestral"
        "lms" = "lms"
        "dpm_fast" = "dpm_fast"
        "dpm_adaptive" = "dpm_adaptive"
        "dpmpp_2s_ancestral" = "dpmpp_2s_ancestral"
        "dpmpp_sde" = "dpmpp_sde"
        "dpmpp_sde_gpu" = "dpmpp_sde_gpu"
        "dpmpp_2m" = "dpmpp_2m"
        "dpmpp_2m_sde" = "dpmpp_2m_sde"
        "dpmpp_3m_sde" = "dpmpp_3m_sde"
        "dpmpp_3m_sde_gpu" = "dpmpp_3m_sde_gpu"
        "ddpm" = "ddpm"
        "ddim" = "ddim"
        "uni_pc" = "uni_pc"
        "uni_pc_bh2" = "uni_pc_bh2"
        "Scheduler" = "调度器"
        "karras" = "karras"
        "Scheduler of Sampler." = "采样器的调度器。"
        "normal" = "normal"
        "exponential" = "exponential"
        "sgm_uniform" = "sgm_uniform"
        "simple" = "simple"
        "ddim_uniform" = "ddim_uniform"
        "Forced Overwrite of Sampling Step" = "强制覆盖采样步长"
        "Set as -1 to disable. For developer debugging." = "设为 -1 以禁用。用于开发者调试。"
        "Forced Overwrite of Refiner Switch Step" = "强制重写精炼器开关步数"
        "Forced Overwrite of Generating Width" = "强制覆盖生成宽度"
        "Set as -1 to disable. For developer debugging. Results will be worse for non-standard numbers that SDXL is not trained on." = "设为 -1 以禁用。用于开发者调试。对于 SDXL 没有训练过的非标准数字，结果会差。"
        "Forced Overwrite of Generating Height" = "强制覆盖生成高度"
        "Forced Overwrite of Denoising Strength of `"Vary`"" = "强制覆盖`“变化`”的去噪强度"
        "Set as negative number to disable. For developer debugging." = "设为负数以禁用。用于开发者调试。"
        "Forced Overwrite of Denoising Strength of `"Upscale`"" = "强制覆盖`“放大`”去噪强度"
        "Inpaint Engine" = "重绘引擎"
        "v1" = "v1"
        "Version of Fooocus inpaint model" = "重绘模型的版本选择"
        "v2.5" = "v2.5"
        "Control Debug" = "控制调试"
        "Debug Preprocessors" = "启用预处理器结果展示"
        "Mixing Image Prompt and Vary/Upscale" = "混合图生图和变化 / 放大"
        "Mixing Image Prompt and Inpaint" = "混合图生图和重绘"
        "Softness of ControlNet" = "ControlNet 控制权重"
        "Similar to the Control Mode in A1111 (use 0.0 to disable). " = "类似于 SD WebUI 中的控制模式（使用 0.0 来禁用）。 "
        "Canny" = "Canny 边缘检测算法"
        "Canny Low Threshold" = "Canny 最低阈值"
        "Canny High Threshold" = "Canny 最高阈值"
        "FreeU" = "FreeU 提示词精准性优化"
        "Enabled" = "启用"
        "B1" = "B1"
        "B2" = "B2"
        "S1" = "S1"
        "S2" = "S2"
        "Type prompt here." = "在这里输入反向提示词（请用英文逗号分隔）"
        "wheel" = "滚轮"
        "Zoom canvas" = "画布缩放"
        "Adjust brush size" = "调整笔刷尺寸"
        "Reset zoom" = "画布复位"
        "Fullscreen mode" = "全屏模式"
        "Move canvas" = "移动画布"
        "Overlap" = "图层重叠"
        "Preset" = "预设配置"
        "Output Format" = "图片保存格式"
        "Type prompt here or paste parameters." = "在这里输入提示词（请用英文逗号分隔）"
        "🔎 Type here to search styles ..." = "🔎 搜索风格预设 ..."
        "Image Sharpness" = "图像锐化"
        "Debug Tools" = "调试工具"
        "Control" = "ControlNet 设置"
        "See the results from preprocessors." = "显示预处理处理结果选项"
        "Do not preprocess images. (Inputs are already canny/depth/cropped-face/etc.)" = "不对图像进行预处理 (导入的图像要求是 边缘控制图 / 深度图 / 面部特征图 / 其他)"
        "Skip Preprocessors" = "禁用图片预处理"
        "Inpaint" = "重绘设置"
        "Debug Inpaint Preprocessing" = "启用重绘预处理功能调试"
        "Disable initial latent in inpaint" = "禁用在重绘中初始化潜空间"
        "Inpaint Denoising Strength" = "重绘幅度"
        "Same as the denoising strength in A1111 inpaint. Only used in inpaint, not used in outpaint. (Outpaint always use 1.0)" = "该选项和 A1111 SD WebUI 中重绘功能的重绘幅度相同。该选项仅应用于图生图重绘功能中，在文生图中该设置无效（在文生图中该值为 1.0）"
        "Inpaint Respective Field" = "重绘蒙版区域范围"
        "The area to inpaint. Value 0 is same as `"Only Masked`" in A1111. Value 1 is same as `"Whole Image`" in A1111. Only used in inpaint, not used in outpaint. (Outpaint always use 1.0)" = "调整重绘区域的范围。该值为 0 时和 A1111 SD WebUI 中`“重绘区域`”选项的`“仅蒙版区域`”的效果相同，为 1 时和`“整张图片`”效果相同。该选项仅应用于图生图重绘功能中，在文生图中该设置无效（在文生图中该值为 1.0）"
        "Mask Erode or Dilate" = "蒙版范围调整"
        "Positive value will make white area in the mask larger, negative value will make white area smaller.(default is 0, always process before any mask invert)" = "正值将使蒙版中的白色区域变大，负值将使白色区域变小。（默认值为 0，始终在任何蒙版反转之前进行处理）"
        "Enable Mask Upload" = "启用蒙版上传功能"
        "Invert Mask" = "反转蒙版（重绘非蒙版内容）"
        "ImagePrompt" = "图像作为提示次输入"
        "FaceSwap" = "面部更改"
        "Drag inpaint or outpaint image to here" = "导入需要重绘的图片"
        "Inpaint or Outpaint" = "图片重绘"
        "Method" = "功能"
        "Inpaint or Outpaint (default)" = "图片重绘（默认）"
        "Improve Detail (face, hand, eyes, etc.)" = "提升细节（面部，手，眼睛等）"
        "Modify Content (add objects, change background, etc.)" = "修改内容（添加对象、更改背景等）"
        "Outpaint Direction" = "图片扩充方向"
        "Additional Prompt Quick List" = "附加提示词快速添加列表"
        "Inpaint Additional Prompt" = "重绘附加提示词"
        "Describe what you want to inpaint." = "描述你想要重绘的"
        "* Powered by Fooocus Inpaint Engine" = "* 由 Fooocus 重绘引擎驱动"
        "Describe" = "图像提示词反推"
        "Drag any image to here" = "导入任意图片"
        "Content Type" = "图片内容种类"
        "Photograph" = "照片"
        "Art/Anime" = "画作 / 动漫图片"
        "Describe this Image into Prompt" = "反推图片的提示词"
        "Metadata" = "图片信息查看"
        "Drag any image generated by Fooocus here" = "导入由 Fooocus 生成的图片"
        "Apply Metadata" = "应用图片信息"
        "(Experimental) This may cause performance problems on some computers and certain internet conditions." = "（实验性）这可能会在某些计算机和某些互联网条件下导致性能问题。"
        "Generate Image Grid for Each Batch" = "为每个批次生成图像网格"
        "Disable preview during generation." = "在图片生成时禁用过程预览"
        "Disable Preview" = "禁用预览"
        "Disable intermediate results during generation, only show final gallery." = "在生成过程中禁用生成的中间结果，仅显示最终图库。"
        "Disable Intermediate Results" = "禁用中间生成结果"
        "Disable automatic seed increment when image number is > 1." = "当图片生成批次大于 1 时禁用种子增量"
        "Disable seed increment" = "禁用种子增量"
        "Read wildcards in order" = "按顺序读取通配符"
        "Adds parameters to generated images allowing manual regeneration." = "在生成的图片中添加元数据（提示词信息等）便于复现原图"
        "Save Metadata to Images" = "保存元数据到图像中"
        "Metadata Scheme" = "元数据格式"
        "Image Prompt parameters are not included. Use png and a1111 for compatibility with Civitai." = "使用默认设置时图片提示词参数不包括在内。使用 png 图片保存格式和 A1111 SD WebUI 的图片信息保存风格的图片更适合在 Civitai 进行分享。"
        "fooocus (json)" = "Fooocus 风格（json）"
        "a1111 (plain text)" = "A1111 SD WebUI 风格（纯文本）"
        "Refiner Switch At" = "Refind 切换时机"
        "Use 0.4 for SD1.5 realistic models; or 0.667 for SD1.5 anime models; or 0.8 for XL-refiners; or any value for switching two SDXL models." = "SD 1.5 真实模型使用 0.4，SD1.5 动漫模型为 0.667，XLRefind 机为 0.8，或用于切换两个 SDXL 模型的任何值。"
        "Waiting for task to start ..." = "等待任务开始 ..."
        "Connection errored out." = "连接超时"
        "Error" = "错误"
        "Loading..." = "加载中 ..."
        "Moving model to GPU ..." = "将模型移至 GPU ..."
        "Loading models ..." = "加载模型 ..."
        "VAE encoding ..." = "VAE 编码 ..."
        "Image processing ..." = "处理图像 ..."
        "Processing prompts ..." = "处理提示词 ..."
        "Download" = "下载"
        "Downloading control models ..." = "下载 ControlNet 模型 ..."
        "Loading control models ..." = "加载 ControlNet 模型 ..."
        "processing" = "处理中"
        "Downloading upscale models ..." = "下载放大模型 ..."
        "Downloading inpainter ..." = "下载重绘模型 ..."
        "Use via API" = "通过 API 调用"
        "Lost connection due to leaving page. Rejoining queue..." = "由于离开页面而失去连接。正在重新加入队列 ..."
        "Warning" = "警告"
        "Finished Images" = "已完成的图像"
        "On mobile, the connection can break if this tab is unfocused or the device sleeps, losing your position in queue." = "在移动端上，如果此选项卡无焦点或设备休眠，连接可能中断，从而失去队列中的位置。"
        "Initializing ..." = "初始化 ..."
        "Downloading LCM components ..." = "下载 LCM 组件 ..."
        "Downloading Lightning components ..." = "下载 Lightning 组件 ..."
        "Start drawing" = "开始涂鸦"
        "VAE Inpaint encoding ..." = "VAE 重绘编码 ..."
        "JSON.parse: unexpected character at line 2 column 1 of the JSON data" = "JSON 分析：JSON 数据中第 2 行第 1 列出现不期望字符"
        "API documentation" = "API 文档"
        "fn_index:" = "主要方法: "
        "Use the" = "使用"
        "Python library or the" = "Python 库或者"
        "Javascript package to query the demo via API." = "Javascript 包来查询演示 API。"
        "Unnamed Endpoints" = "未命名接口"
        "Return Type(s)" = "返回类型"
        "47 API endpoints" = "47 个 API 接口"
        "copy" = "复制"
        "copied!" = "已复制！"
        "JSON.parse: unexpected character at line 1 column 1 of the JSON data" = "JAVA 解析：JSON 数据第 1 行第 1 列出现意外字符"
        "Generate forever" = "无限生成"
        "Downloading Hyper-SD components ..." = "下载 Hyper SD 组件中 ..."
        "Inpaint brush color" = "重绘画笔颜色"
        "CLIP Skip" = "CLIP 跳过层数"
        "Bypass CLIP layers to avoid overfitting (use 1 to not skip any layers, 2 is recommended)." = "CLIP 跳过层数可避免过拟合的情况（使用 1 为不跳过任何层，2 为推荐值）"
        "VAE" = "VAE 模型"
        "Default (model)" = "默认（模型）"
        "Use black image if NSFW is detected." = "当检测到图片存在 NSFW 内容时将屏蔽图片"
        "Black Out NSFW" = "屏蔽 NSFW"
        "For images created by Fooocus" = "导入由 Fooocus 生成的图片"
        "- Zoom canvas" = " - 缩放画布"
        "- Adjust brush size" = " - 调整画笔大小"
        "- Undo last action" = "- 撤回上一次的操作"
        "- Reset zoom" = " - 重置缩放"
        "- Fullscreen mode" = " - 全屏模式"
        "- Move canvas" = " - 移动画布"
        "Image Size and Recommended Size" = "图片分辨率和推荐的生图分辨率"
        "Enhance" = "增强"
        "Enable" = "启用"
        "Detection prompt" = "检测提示词"
        "Use singular whenever possible" = "尽量使用单词进行描述"
        "Describe what you want to detect." = "描述你想要检测的。"
        "Detection Prompt Quick List" = "检测提示词快速选择列表"
        "Enhancement positive prompt" = "增强正面提示词"
        "Uses original prompt instead if empty." = "如果提示词为空，则使用原有的提示词。"
        "Enhancement negative prompt" = "增强负面提示词"
        "Uses original negative prompt instead if empty." = "如果提示词为空，则使用原有的负面提示词。"
        "Detection" = "检测"
        "Mask generation model" = "蒙版生成模型"
        "SAM Options" = "SAM 模型选项"
        "SAM model" = "SAM 模型"
        "Box Threshold" = "箱体阈值"
        "Text Threshold" = "文本阈值"
        "Maximum number of detections" = "检测最大数量"
        "Set to 0 to detect all" = "设置为 0 时检测所有"
        "Version of Fooocus inpaint model. If set, use performance Quality or Speed (no performance LoRAs) for best results." = "Fooocus 重绘模型的版本。如果已设置，在性能选项选择质量或者均衡（无加速 LoRA）以达到最佳效果。"
        "Positive value will make white area in the mask larger, negative value will make white area smaller. (default is 0, always processed before any mask invert)" = "该值为正值时会使遮罩中的白色区域变大，为负值时会使白色区域变小。（默认值为 0，并且在任何蒙版反转之前处理）"
        "#1" = "单元 1"
        "#2" = "单元 2"
        "#3" = "单元 3"
        "📔 Documentation" = "📔 文档"
        "Use with Enhance, skips image generation" = "使用增强功能后，跳过图像生成"
        "Settings" = "设置"
        "Styles" = "风格"
        "Fooocus Pony" = "Fooocus - 小马"
        "Models" = "模型"
        "Show enhance masks in preview and final results" = "在预览中展示增强蒙版和最后结果"
        "Debug Enhance Masks" = "启用增强蒙版调试"
        "Use GroundingDINO boxes instead of more detailed SAM masks" = "使用 GroundingDINO 箱体代替更多的细节 SAM 蒙版"
        "Debug GroundingDINO" = "启用 GroundingDINO 调试"
        "GroundingDINO Box Erode or Dilate" = "GroundingDINO 箱体侵蚀和扩张"
        "Enable Advanced Masking Features" = "启用高级蒙版特性"
        "Mask Upload" = "上传蒙版"
        "Invert Mask When Generating" = "在生成时反转蒙版"
        "Generate mask from image" = "为图像生成蒙版"
        "Order of Processing" = "处理顺序"
        "Use before to enhance small details and after to enhance large areas." = "在使用前可增强小细节，在使用后可增大面积。"
        "Before First Enhancement" = "在第一次增强前"
        "After Last Enhancement" = "在最后一次增强后"
        "Save only final enhanced image" = "仅保存最后一次增强后的图像"
        "Positive value will make white area in the mask larger, negative value will make white area smaller. (default is 0, processed before SAM)" = "该值为正值时会使遮罩中的白色区域变大，为负值时会使白色区域变小。（默认值为 0，并且在使用 SAM 之前处理）"
        "Apply Styles" = "应用风格预设"
    }

    # 创建一个不带 BOM 的 UTF-8 编码器
    $utf8_encoding = New-Object System.Text.UTF8Encoding($false)

    $fooocus_preset_json_content = $fooocus_preset_json_content | ConvertTo-Json -Depth 4
    $fooocus_language_zh_json_content = $fooocus_language_zh_json_content | ConvertTo-Json -Depth 4

    Print-Msg "更新 Fooocus 预设文件"
    $stream_writer = [System.IO.StreamWriter]::new("$InstallPath/$Env:CORE_PREFIX/presets/fooocus_installer.json", $false, $utf8_encoding)
    $stream_writer.Write($fooocus_preset_json_content)
    $stream_writer.Close()

    Print-Msg "更新 Fooocus 翻译文件"
    $stream_writer = [System.IO.StreamWriter]::new("$InstallPath/$Env:CORE_PREFIX/language/zh.json", $false, $utf8_encoding)
    $stream_writer.Write($fooocus_language_zh_json_content)
    $stream_writer.Close()
}


# 安装
function Check-Install {
    New-Item -ItemType Directory -Path "$InstallPath" -Force > $null
    New-Item -ItemType Directory -Path "$Env:CACHE_HOME" -Force > $null

    Print-Msg "检测是否安装 Python"
    if ((Test-Path "$InstallPath/python/python.exe") -or (Test-Path "$InstallPath/$Env:CORE_PREFIX/python/python.exe")) {
        Print-Msg "Python 已安装"
    } else {
        Print-Msg "Python 未安装"
        Install-Python
    }

    # 切换 uv 指定的 Python
    if (Test-Path "$InstallPath/$Env:CORE_PREFIX/python/python.exe") {
        $Env:UV_PYTHON = "$InstallPath/$Env:CORE_PREFIX/python/python.exe"
    }

    Print-Msg "检测是否安装 Git"
    if ((Test-Path "$InstallPath/git/bin/git.exe") -or (Test-Path "$InstallPath/$Env:CORE_PREFIX/git/bin/git.exe")) {
        Print-Msg "Git 已安装"
    } else {
        Print-Msg "Git 未安装"
        Install-Git
    }

    Print-Msg "检测是否安装 Aria2"
    if ((Test-Path "$InstallPath/git/bin/aria2c.exe") -or (Test-Path "$InstallPath/$Env:CORE_PREFIX/git/bin/aria2c.exe")) {
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

    # Fooocus 核心
    Git-CLone "$FOOOCUS_REPO" "$InstallPath/$Env:CORE_PREFIX"

    Install-PyTorch
    Install-Fooocus-Dependence

    if (!(Test-Path "$InstallPath/launch_args.txt")) {
        Print-Msg "设置默认 Fooocus 启动参数"
        $content = "--language zh --preset fooocus_installer --disable-offload-from-vram --disable-analytics"
        Set-Content -Encoding UTF8 -Path "$InstallPath/launch_args.txt" -Value $content
    }

    Update-Fooocus-Preset

    if ($NoPreDownloadModel) {
        Print-Msg "检测到 -NoPreDownloadModel 命令行参数, 跳过下载模型"
    } else {
        Print-Msg "预下载模型中"
        $model_list = New-Object System.Collections.ArrayList

        $model_list.Add(@("https://modelscope.cn/models/licyks/fooocus-model/resolve/master/vae_approx/vaeapp_sd15.pth", "$InstallPath/$Env:CORE_PREFIX/models/vae_approx", "vaeapp_sd15.pth")) | Out-Null
        $model_list.Add(@("https://modelscope.cn/models/licyks/fooocus-model/resolve/master/vae_approx/xlvaeapp.pth", "$InstallPath/$Env:CORE_PREFIX/models/vae_approx", "xlvaeapp.pth")) | Out-Null
        $model_list.Add(@("https://modelscope.cn/models/licyks/fooocus-model/resolve/master/vae_approx/xl-to-v1_interposer-v4.0.safetensors", "$InstallPath/$Env:CORE_PREFIX/models/vae_approx", "xl-to-v1_interposer-v4.0.safetensors")) | Out-Null
        $model_list.Add(@("https://modelscope.cn/models/licyks/fooocus-model/resolve/master/prompt_expansion/fooocus_expansion/pytorch_model.bin", "$InstallPath/$Env:CORE_PREFIX/models/prompt_expansion/fooocus_expansion", "pytorch_model.bin")) | Out-Null

        $checkpoint_path = "$InstallPath/$Env:CORE_PREFIX/models/checkpoints"
        $url = "https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/Illustrious-XL-v1.0.safetensors"
        $name = Split-Path -Path $url -Leaf
        if ((!(Get-ChildItem -Path $checkpoint_path -Include "*.safetensors", "*.pth", "*.ckpt" -Recurse)) -or (Test-Path "$checkpoint_path/${name}.aria2")){
            $model_list.Add(@("$url", "$checkpoint_path", "$name")) | Out-Null
        }

        Model-Downloader $model_list
    }

    # 清理缓存
    if ($NoCleanCache) {
        Print-Msg "跳过清理下载 Python 软件包的缓存"
    } else {
        Print-Msg "清理下载 Python 软件包的缓存中"
        python -m pip cache purge
        uv cache clean
    }

    Set-Content -Encoding UTF8 -Path "$InstallPath/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
}


# 启动脚本
function Write-Launch-Script {
    $content = "
param (
    [switch]`$Help,
    [string]`$CorePrefix,
    [switch]`$BuildMode,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableUpdate,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisableHuggingFaceMirror,
    [string]`$UseCustomHuggingFaceMirror,
    [switch]`$DisableUV,
    [string]`$LaunchArg,
    [switch]`$EnableShortcut,
    [switch]`$DisableCUDAMalloc,
    [switch]`$DisableEnvCheck,
    [switch]`$DisableAutoApplyUpdate
)
& {
    `$prefix_list = @(`"core`", `"Fooocus`", `"fooocus`", `"fooocus_portable`")
    if ((Test-Path `"`$PSScriptRoot/core_prefix.txt`") -or (`$CorePrefix)) {
        if (`$CorePrefix) {
            `$origin_core_prefix = `$CorePrefix
        } else {
            `$origin_core_prefix = Get-Content `"`$PSScriptRoot/core_prefix.txt`"
        }
        `$origin_core_prefix = `$origin_core_prefix.Trim('/').Trim('\')
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix)) {
            `$to_path = `$origin_core_prefix
            `$from_uri = New-Object System.Uri(`$PSScriptRoot.Replace('\', '/') + '/')
            `$to_uri = New-Object System.Uri(`$to_path.Replace('\', '/'))
            `$origin_core_prefix = `$from_uri.MakeRelativeUri(`$to_uri).ToString().Trim('/')
        }
        `$Env:CORE_PREFIX = `$origin_core_prefix
        return
    }
    ForEach (`$i in `$prefix_list) {
        if (Test-Path `"`$PSScriptRoot/`$i`") {
            `$Env:CORE_PREFIX = `$i
            return
        }
    }
    `$Env:CORE_PREFIX = `"core`"
}
# Fooocus Installer 版本和检查更新间隔
`$FOOOCUS_INSTALLER_VERSION = $FOOOCUS_INSTALLER_VERSION
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
`$PIP_EXTRA_INDEX_MIRROR_CPU = `"$PIP_EXTRA_INDEX_MIRROR_CPU`"
`$PIP_EXTRA_INDEX_MIRROR_XPU = `"$PIP_EXTRA_INDEX_MIRROR_XPU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118 = `"$PIP_EXTRA_INDEX_MIRROR_CU118`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
`$PIP_EXTRA_INDEX_MIRROR_CU126 = `"$PIP_EXTRA_INDEX_MIRROR_CU126`"
`$PIP_EXTRA_INDEX_MIRROR_CU128 = `"$PIP_EXTRA_INDEX_MIRROR_CU128`"
`$PIP_EXTRA_INDEX_MIRROR_CU129 = `"$PIP_EXTRA_INDEX_MIRROR_CU129`"
`$PIP_EXTRA_INDEX_MIRROR_CPU_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CPU_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_XPU_NJU = `"$PIP_EXTRA_INDEX_MIRROR_XPU_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU118_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU121_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU121_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU124_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU126_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU128_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU129_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU129_NJU`"
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
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/git/bin`"
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
function Get-Fooocus-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-DisablePyPIMirror] [-DisableUpdate] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>] [-DisableUV] [-LaunchArg <Fooocus 启动参数>] [-EnableShortcut] [-DisableCUDAMalloc] [-DisableEnvCheck] [-DisableAutoApplyUpdate]

参数:
    -Help
        获取 Fooocus Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -BuildMode
        启用 Fooocus Installer 构建模式

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableUpdate
        禁用 Fooocus Installer 更新检查

    -DisableProxy
        禁用 Fooocus Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableHuggingFaceMirror
        禁用 HuggingFace 镜像源, 不使用 HuggingFace 镜像源下载文件

    -UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>
        使用自定义 HuggingFace 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror ```"https://hf-mirror.com```" 设置 HuggingFace 镜像源地址

    -DisableUV
        禁用 Fooocus Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -LaunchArg <Fooocus 启动参数>
        设置 Fooocus 自定义启动参数, 如启用 --disable-offload-from-vram 和 --disable-analytics, 则使用 -LaunchArg ```"--disable-offload-from-vram --disable-analytics```" 进行启用

    -EnableShortcut
        创建 Fooocus 启动快捷方式

    -DisableCUDAMalloc
        禁用 Fooocus Installer 通过 PYTORCH_CUDA_ALLOC_CONF 环境变量设置 CUDA 内存分配器

    -DisableEnvCheck
        禁用 Fooocus Installer 检查 Fooocus 运行环境中存在的问题, 禁用后可能会导致 Fooocus 环境中存在的问题无法被发现并修复

    -DisableAutoApplyUpdate
        禁用 Fooocus Installer 自动应用新版本更新


更多的帮助信息请阅读 Fooocus Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[Fooocus Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# 获取内核路径前缀状态
function Get-Core-Prefix-Status {
    if ((Test-Path `"`$PSScriptRoot/core_prefix.txt`") -or (`$CorePrefix)) {
        Print-Msg `"检测到 core_prefix.txt 配置文件 / -CorePrefix 命令行参数, 使用自定义内核路径前缀`"
        if (`$CorePrefix) {
            `$origin_core_prefix = `$CorePrefix
        } else {
            `$origin_core_prefix = Get-Content `"`$PSScriptRoot/core_prefix.txt`"
        }
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix.Trim('/').Trim('\'))) {
            Print-Msg `"转换绝对路径为内核路径前缀: `$origin_core_prefix -> `$Env:CORE_PREFIX`"
        }
    }
    Print-Msg `"当前内核路径前缀: `$Env:CORE_PREFIX`"
    Print-Msg `"完整内核路径: `$PSScriptRoot\`$Env:CORE_PREFIX`"
}


# 显示 Fooocus Installer 版本
function Get-Fooocus-Installer-Version {
    `$ver = `$([string]`$FOOOCUS_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"Fooocus Installer 版本: v`${major}.`${minor}.`${micro}`"
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


try:
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
except Exception as _:
    pass
`".Trim()

    Print-Msg `"检测 PyTorch 的 libomp 问题中`"
    python -c `"`$content`"
    Print-Msg `"PyTorch 检查完成`"
}


# Fooocus Installer 更新检测
function Check-Fooocus-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/fooocus_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/fooocus_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/fooocus_installer/fooocus_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/fooocus_installer/fooocus_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/fooocus_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 Fooocus Installer 的自动检查更新功能`"
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
        Print-Msg `"检查 Fooocus Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/fooocus_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/fooocus_installer.ps1`" |
                Select-String -Pattern `"FOOOCUS_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 Fooocus Installer 更新中`"
            } else {
                Print-Msg `"检查 Fooocus Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -le `$FOOOCUS_INSTALLER_VERSION) {
        Print-Msg `"Fooocus Installer 已是最新版本`"
        return
    }

    if ((`$DisableAutoApplyUpdate) -or (Test-Path `"`$PSScriptRoot/disable_auto_apply_update.txt`")) {
        Print-Msg `"检测到 Fooocus Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"========================================>`").Trim()
        if (!(`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`")) {
            Print-Msg `"跳过 Fooocus Installer 更新`"
            return
        }
    } else {
        Print-Msg `"检测到 Fooocus Installer 有新版本可用`"
    }

    Print-Msg `"调用 Fooocus Installer 进行更新中`"
    . `"`$Env:CACHE_HOME/fooocus_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
    `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
    Print-Msg `"更新结束, 重新启动 Fooocus Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
    Invoke-Expression `"& ```"`$PSCommandPath```" `$raw_params`"
    exit 0
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
    version1 = str(version1)
    version2 = str(version2)
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
    # 切换 uv 指定的 Python
    if (Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX/python/python.exe`") {
        `$Env:UV_PYTHON = `"`$PSScriptRoot/`$Env:CORE_PREFIX/python/python.exe`"
    }

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


# Fooocus 启动参数
function Get-Fooocus-Launch-Args {
    `$arguments = New-Object System.Collections.ArrayList
    if ((Test-Path `"`$PSScriptRoot/launch_args.txt`") -or (`$LaunchArg)) {
        if (`$LaunchArg) {
            `$launch_args = `$LaunchArg
        } else {
            `$launch_args = Get-Content `"`$PSScriptRoot/launch_args.txt`"
        }
        if (`$launch_args.Trim().Split().Length -le 1) {
            `$arguments = `$launch_args.Trim().Split()
        } else {
            `$arguments = [regex]::Matches(`$launch_args, '(`"[^`"]*`"|''[^'']*''|\S+)') | ForEach-Object {
                `$_.Value -replace '^[`"'']|[`"'']`$', ''
            }
        }
        Print-Msg `"检测到本地存在 launch_args.txt 启动参数配置文件 / -LaunchArg 命令行参数, 已读取该启动参数配置文件并应用启动参数`"
        Print-Msg `"使用的启动参数: `$arguments`"
    }
    return `$arguments
}


# 设置 Fooocus 的快捷启动方式
function Create-Fooocus-Shortcut {
    # 设置快捷方式名称
    if ((Get-Command git -ErrorAction SilentlyContinue) -and (Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX/.git`")) {
        `$git_remote = `$(git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" remote get-url origin)
        `$array = `$git_remote -split `"/`"
        `$branch = `"`$(`$array[-2])/`$(`$array[-1])`"
        if ((`$branch -eq `"lllyasviel/Fooocus`") -or (`$branch -eq `"lllyasviel/Fooocus.git`")) {
            `$filename = `"Fooocus`"
        } elseif ((`$branch -eq `"MoonRide303/Fooocus-MRE`") -or (`$branch -eq `"MoonRide303/Fooocus-MRE.git`")) {
            `$filename = `"Fooocus-MRE`"
        } elseif ((`$branch -eq `"runew0lf/RuinedFooocus`") -or (`$branch -eq `"runew0lf/RuinedFooocus.git`")) {
            `$filename = `"RuinedFooocus`"
        } else {
            `$filename = `"Fooocus`"
        }
    } else {
        `$filename = `"Fooocus`"
    }

    `$url = `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/gradio_icon.ico`"
    `$shortcut_icon = `"`$PSScriptRoot/gradio_icon.ico`"

    if ((!(Test-Path `"`$PSScriptRoot/enable_shortcut.txt`")) -and (!(`$EnableShortcut))) {
        return
    }

    Print-Msg `"检测到 enable_shortcut.txt 配置文件 / -EnableShortcut 命令行参数, 开始检查 Fooocus 快捷启动方式中`"
    if (!(Test-Path `"`$shortcut_icon`")) {
        Print-Msg `"获取 Fooocus 图标中`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/gradio_icon.ico`"
        if (!(`$?)) {
            Print-Msg `"获取 Fooocus 图标失败, 无法创建 Fooocus 快捷启动方式`"
            return
        }
    }

    Print-Msg `"更新 Fooocus 快捷启动方式`"
    `$shell = New-Object -ComObject WScript.Shell
    `$desktop = [System.Environment]::GetFolderPath(`"Desktop`")
    `$shortcut_path = `"`$desktop\`$filename.lnk`"
    `$shortcut = `$shell.CreateShortcut(`$shortcut_path)
    `$shortcut.TargetPath = `"`$PSHome\powershell.exe`"
    `$launch_script_path = `$(Get-Item `"`$PSScriptRoot/launch.ps1`").FullName
    `$shortcut.Arguments = `"-ExecutionPolicy Bypass -File ```"`$launch_script_path```"`"
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


def get_pytorch_cuda_alloc_conf(is_cuda = True):
    if is_nvidia_device():
        if cuda_malloc_supported():
            if is_cuda:
                return 'cuda_malloc'
            else:
                return 'pytorch_malloc'
        else:
            return 'pytorch_malloc'
    else:
        return None


def main():
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
            if '+cu' in version: #only on cuda torch
                print(get_pytorch_cuda_alloc_conf())
            else:
                print(get_pytorch_cuda_alloc_conf(False))
        else:
            print(None)
    except Exception as _:
        print(None)


if __name__ == '__main__':
    main()
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


# 检查 Fooocus 依赖完整性
function Check-Fooocus-Requirements {
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

    Print-Msg `"检查 Fooocus 内核依赖完整性中`"
    if (!(Test-Path `"`$Env:CACHE_HOME`")) {
        New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" > `$null
    }
    Set-Content -Encoding UTF8 -Path `"`$Env:CACHE_HOME/check_fooocus_requirement.py`" -Value `$content

    `$dep_path = `"`$PSScriptRoot/`$Env:CORE_PREFIX/requirements_versions.txt`"
    if (!(Test-Path `"`$dep_path`")) {
        `$dep_path = `"`$PSScriptRoot/`$Env:CORE_PREFIX/requirements.txt`"
    }
    if (!(Test-Path `"`$dep_path`")) {
        Print-Msg `"未检测到 Fooocus 依赖文件, 跳过依赖完整性检查`"
        return
    }

    `$status = `$(python `"`$Env:CACHE_HOME/check_fooocus_requirement.py`" --requirement-path `"`$dep_path`")

    if (`$status -eq `"False`") {
        Print-Msg `"检测到 Fooocus 内核有依赖缺失, 安装 Fooocus 依赖中`"
        if (`$USE_UV) {
            uv pip install -r `"`$dep_path`"
            if (!(`$?)) {
                Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
                python -m pip install -r `"`$dep_path`"
            }
        } else {
            python -m pip install -r `"`$dep_path`"
        }
        if (`$?) {
            Print-Msg `"Fooocus 依赖安装成功`"
        } else {
            Print-Msg `"Fooocus 依赖安装失败, 这将会导致 Fooocus 缺失依赖无法正常运行`"
        }
    } else {
        Print-Msg `"Fooocus 无缺失依赖`"
    }
}


# 检查 onnxruntime-gpu 版本问题
function Check-Onnxruntime-GPU {
    `$content = `"
import re
import argparse
import importlib.metadata
from pathlib import Path
from enum import Enum


def get_args() -> argparse.Namespace:
    '''获取命令行参数

    :return argparse.Namespace: 命令行参数命名空间
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument('--ignore-ort-install', action='store_true', help='忽略 onnxruntime-gpu 未安装的状态, 强制进行检查')

    return parser.parse_args()


def get_onnxruntime_version_file() -> Path | None:
    '''获取记录 onnxruntime 版本的文件路径

    :return Path | None: 记录 onnxruntime 版本的文件路径
    '''
    package = 'onnxruntime-gpu'
    version_file = 'onnxruntime/capi/version_info.py'
    try:
        util = [
            p for p in importlib.metadata.files(package)
            if version_file in str(p)
        ][0]
        info_path = Path(util.locate())
    except Exception as _:
        info_path = None

    return info_path


def get_onnxruntime_support_cuda_version() -> tuple[str | None, str | None]:
    '''获取 onnxruntime 支持的 CUDA, cuDNN 版本

    :return tuple[str | None, str | None]: onnxruntime 支持的 CUDA, cuDNN 版本
    '''
    ver_path = get_onnxruntime_version_file()
    cuda_ver = None
    cudnn_ver = None
    try:
        with open(ver_path, 'r', encoding='utf8') as f:
            for line in f:
                if 'cuda_version' in line:
                    cuda_ver = get_value_from_variable(line, 'cuda_version')
                if 'cudnn_version' in line:
                    cudnn_ver = get_value_from_variable(line, 'cudnn_version')
    except Exception as _:
        pass

    return cuda_ver, cudnn_ver


def get_value_from_variable(content: str, var_name: str) -> str | None:
    '''从字符串 (Python 代码片段) 中找出指定字符串变量的值

    :param content(str): 待查找的内容
    :param var_name(str): 待查找的字符串变量
    :return str | None: 返回字符串变量的值
    '''
    pattern = fr'^\s*{var_name}\s*=\s*.*\s*$'
    match = re.findall(pattern, content, flags=re.MULTILINE)
    if match:
        match_str = ''.join(re.findall(r'[\d.]+', match[0].split('=').pop().strip()))
    return match_str if len(match_str) != 0 else None


def compare_versions(version1: str, version2: str) -> int:
    '''对比两个版本号大小

    :param version1(str): 第一个版本号
    :param version2(str): 第二个版本号
    :return int: 版本对比结果, 1 为第一个版本号大, -1 为第二个版本号大, 0 为两个版本号一样
    '''
    version1 = str(version1)
    version2 = str(version2)
    # 将版本号拆分成数字列表
    try:
        nums1 = (
            re.sub(r'[a-zA-Z]+', '', version1)
            .replace('-', '.')
            .replace('_', '.')
            .replace('+', '.')
            .split('.')
        )
        nums2 = (
            re.sub(r'[a-zA-Z]+', '', version2)
            .replace('-', '.')
            .replace('_', '.')
            .replace('+', '.')
            .split('.')
        )
    except Exception as _:
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


def get_torch_cuda_ver() -> tuple[str | None, str | None, str | None]:
    '''获取 Torch 的本体, CUDA, cuDNN 版本

    :return tuple[str | None, str | None, str | None]: Torch, CUDA, cuDNN 版本
    '''
    try:
        import torch
        torch_ver = torch.__version__
        cuda_ver = torch.version.cuda
        cudnn_ver = torch.backends.cudnn.version()
        return (
            str(torch_ver) if torch_ver is not None else None,
            str(cuda_ver) if cuda_ver is not None else None,
            str(cudnn_ver) if cudnn_ver is not None else None,
        )
    except Exception as _:
        return None, None, None


class OrtType(str, Enum):
    '''onnxruntime-gpu 的类型

    版本说明: 
    - CU121CUDNN8: CUDA 12.1 + cuDNN8
    - CU121CUDNN9: CUDA 12.1 + cuDNN9
    - CU118: CUDA 11.8
    '''
    CU121CUDNN8 = 'cu121cudnn8'
    CU121CUDNN9 = 'cu121cudnn9'
    CU118 = 'cu118'

    def __str__(self):
        return self.value


def need_install_ort_ver(ignore_ort_install: bool = True) -> OrtType | None:
    '''判断需要安装的 onnxruntime 版本

    :param ignore_ort_install(bool): 当 onnxruntime 未安装时跳过检查
    :return OrtType: 需要安装的 onnxruntime-gpu 类型
    '''
    # 检测是否安装了 Torch
    torch_ver, cuda_ver, cuddn_ver = get_torch_cuda_ver()
    # 缺少 Torch / CUDA / cuDNN 版本时取消判断
    if (
        torch_ver is None
        or cuda_ver is None
        or cuddn_ver is None
    ):
        if not ignore_ort_install:
            try:
                _ = importlib.metadata.version('onnxruntime-gpu')
            except Exception as _:
                # onnxruntime-gpu 没有安装时
                return OrtType.CU121CUDNN9
        return None

    # onnxruntime 记录的 cuDNN 支持版本只有一位数, 所以 Torch 的 cuDNN 版本只能截取一位
    cuddn_ver = cuddn_ver[0]

    # 检测是否安装了 onnxruntime-gpu
    ort_support_cuda_ver, ort_support_cudnn_ver = get_onnxruntime_support_cuda_version()
    # 通常 onnxruntime 的 CUDA 版本和 cuDNN 版本会同时存在, 所以只需要判断 CUDA 版本是否存在即可
    if ort_support_cuda_ver is not None:
        # 当 onnxruntime 已安装

        # 判断 Torch 中的 CUDA 版本
        if compare_versions(cuda_ver, '12.0') >= 0:
            # CUDA >= 12.0

            # 比较 onnxtuntime 支持的 CUDA 版本是否和 Torch 中所带的 CUDA 版本匹配
            if compare_versions(ort_support_cuda_ver, '12.0') >= 0:
                # CUDA 版本为 12.x, torch 和 ort 的 CUDA 版本匹配

                # 判断 Torch 和 onnxruntime 的 cuDNN 是否匹配
                if compare_versions(ort_support_cudnn_ver, cuddn_ver) > 0:
                    # ort cuDNN 版本 > torch cuDNN 版本
                    return OrtType.CU121CUDNN8
                elif compare_versions(ort_support_cudnn_ver, cuddn_ver) < 0:
                    # ort cuDNN 版本 < torch cuDNN 版本
                    return OrtType.CU121CUDNN9
                else:
                    # 版本相等, 无需重装
                    return None
            else:
                # CUDA 版本非 12.x, 不匹配
                if compare_versions(cuddn_ver, '8') > 0:
                    return OrtType.CU121CUDNN9
                else:
                    return OrtType.CU121CUDNN8
        else:
            # CUDA <= 11.8
            if compare_versions(ort_support_cuda_ver, '12.0') < 0:
                return None
            else:
                return OrtType.CU118
    else:
        if ignore_ort_install:
            return None

        if compare_versions(cuda_ver, '12.0') >= 0:
            if compare_versions(cuddn_ver, '8') > 0:
                return OrtType.CU121CUDNN9
            else:
                return OrtType.CU121CUDNN8
        else:
            return OrtType.CU118


if __name__ == '__main__':
    arg = get_args()
    # print(need_install_ort_ver(not arg.ignore_ort_install))
    print(need_install_ort_ver())
`".Trim()

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
            `$tmp_uv_index_url = `$Env:UV_DEFAULT_INDEX
            `$tmp_UV_extra_index_url = `$Env:UV_INDEX
            `$Env:PIP_INDEX_URL = `"https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/`"
            `$Env:PIP_EXTRA_INDEX_URL = `"https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple`"
            `$Env:UV_DEFAULT_INDEX = `"https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/`"
            `$Env:UV_INDEX = `"https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple`"
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
            `$Env:UV_DEFAULT_INDEX = `$tmp_uv_index_url
            `$Env:UV_INDEX = `$tmp_UV_extra_index_url
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


# 检查 Fooocus 运行环境
function Check-Fooocus-Env {
    if ((Test-Path `"`$PSScriptRoot/disable_check_env.txt`") -or (`$DisableEnvCheck)) {
        Print-Msg `"检测到 disable_check_env.txt 配置文件 / -DisableEnvCheck 命令行参数, 已禁用 Fooocus 运行环境检测, 这可能会导致 Fooocus 运行环境中存在的问题无法被发现并解决`"
        return
    } else {
        Print-Msg `"检查 Fooocus 运行环境中`"
    }

    Check-Fooocus-Requirements
    Fix-PyTorch
    Check-Onnxruntime-GPU
    Check-Numpy-Version
    Check-MS-VCPP-Redistributable
    Print-Msg `"Fooocus 运行环境检查完成`"
}


# 设置 Fooocus 的 HuggingFace 镜像
function Get-Fooocus-HuggingFace-Mirror-Arg {
    `$hf_mirror_arg = New-Object System.Collections.ArrayList

    if ((Get-Command git -ErrorAction SilentlyContinue) -and (Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX/.git`")) {
        `$git_remote = `$(git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" remote get-url origin)
        `$array = `$git_remote -split `"/`"
        `$branch = `"`$(`$array[-2])/`$(`$array[-1])`"
        if (!((`$branch -eq `"lllyasviel/Fooocus`") -or (`$branch -eq `"lllyasviel/Fooocus.git`"))) {
            return `$hf_mirror_arg
        }
    }

    if ((!(Test-Path `"`$PSScriptRoot/disable_hf_mirror.txt`")) -and (!(`$DisableHuggingFaceMirror))) {
        `$hf_mirror_arg.Add(`"--hf-mirror`") | Out-Null
        `$hf_mirror_arg.Add(`"`$Env:HF_ENDPOINT`") | Out-Null
    }

    return `$hf_mirror_arg
}


function Main {
    Print-Msg `"初始化中`"
    Get-Fooocus-Installer-Version
    Get-Fooocus-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"Fooocus Installer 构建模式已启用, 跳过 Fooocus Installer 更新检查`"
    } else {
        Check-Fooocus-Installer-Update
    }
    Set-HuggingFace-Mirror
    Set-uv
    PyPI-Mirror-Status

    if (!(Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX`")) {
        Print-Msg `"内核路径 `$PSScriptRoot\`$Env:CORE_PREFIX 未找到, 请检查 Fooocus 是否已正确安装, 或者尝试运行 Fooocus Installer 进行修复`"
        Read-Host | Out-Null
        return
    }

    `$launch_args = Get-Fooocus-Launch-Args
    `$hf_mirror_arg = Get-Fooocus-HuggingFace-Mirror-Arg
    # 记录上次的路径
    `$current_path = `$(Get-Location).ToString()
    Set-Location `"`$PSScriptRoot/`$Env:CORE_PREFIX`"

    Create-Fooocus-Shortcut
    Check-Fooocus-Env
    Set-PyTorch-CUDA-Memory-Alloc
    Print-Msg `"启动 Fooocus 中`"
    if (`$BuildMode) {
        Print-Msg `"Fooocus Installer 构建模式已启用, 跳过启动 Fooocus`"
    } else {
        python launch.py `$launch_args `$hf_mirror_arg
        `$req = `$?
        if (`$req) {
            Print-Msg `"Fooocus 正常退出`"
        } else {
            Print-Msg `"Fooocus 出现异常, 已退出`"
        }
        Read-Host | Out-Null
    }
    Set-Location `"`$current_path`"
}

###################

Main
".Trim()

    if (Test-Path "$InstallPath/launch.ps1") {
        Print-Msg "更新 launch.ps1 中"
    } else {
        Print-Msg "生成 launch.ps1 中"
    }
    Set-Content -Encoding $PS_SCRIPT_ENCODING -Path "$InstallPath/launch.ps1" -Value $content
}


# 更新脚本
function Write-Update-Script {
    $content = "
param (
    [switch]`$Help,
    [string]`$CorePrefix,
    [switch]`$BuildMode,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableUpdate,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisableGithubMirror,
    [string]`$UseCustomGithubMirror,
    [switch]`$DisableAutoApplyUpdate
)
& {
    `$prefix_list = @(`"core`", `"Fooocus`", `"fooocus`", `"fooocus_portable`")
    if ((Test-Path `"`$PSScriptRoot/core_prefix.txt`") -or (`$CorePrefix)) {
        if (`$CorePrefix) {
            `$origin_core_prefix = `$CorePrefix
        } else {
            `$origin_core_prefix = Get-Content `"`$PSScriptRoot/core_prefix.txt`"
        }
        `$origin_core_prefix = `$origin_core_prefix.Trim('/').Trim('\')
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix)) {
            `$to_path = `$origin_core_prefix
            `$from_uri = New-Object System.Uri(`$PSScriptRoot.Replace('\', '/') + '/')
            `$to_uri = New-Object System.Uri(`$to_path.Replace('\', '/'))
            `$origin_core_prefix = `$from_uri.MakeRelativeUri(`$to_uri).ToString().Trim('/')
        }
        `$Env:CORE_PREFIX = `$origin_core_prefix
        return
    }
    ForEach (`$i in `$prefix_list) {
        if (Test-Path `"`$PSScriptRoot/`$i`") {
            `$Env:CORE_PREFIX = `$i
            return
        }
    }
    `$Env:CORE_PREFIX = `"core`"
}
# Fooocus Installer 版本和检查更新间隔
`$FOOOCUS_INSTALLER_VERSION = $FOOOCUS_INSTALLER_VERSION
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
`$PIP_EXTRA_INDEX_MIRROR_CPU = `"$PIP_EXTRA_INDEX_MIRROR_CPU`"
`$PIP_EXTRA_INDEX_MIRROR_XPU = `"$PIP_EXTRA_INDEX_MIRROR_XPU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118 = `"$PIP_EXTRA_INDEX_MIRROR_CU118`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
`$PIP_EXTRA_INDEX_MIRROR_CU126 = `"$PIP_EXTRA_INDEX_MIRROR_CU126`"
`$PIP_EXTRA_INDEX_MIRROR_CU128 = `"$PIP_EXTRA_INDEX_MIRROR_CU128`"
`$PIP_EXTRA_INDEX_MIRROR_CU129 = `"$PIP_EXTRA_INDEX_MIRROR_CU129`"
`$PIP_EXTRA_INDEX_MIRROR_CPU_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CPU_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_XPU_NJU = `"$PIP_EXTRA_INDEX_MIRROR_XPU_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU118_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU121_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU121_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU124_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU126_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU128_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU129_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU129_NJU`"
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
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/git/bin`"
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
function Get-Fooocus-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-DisablePyPIMirror] [-DisableUpdate] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像源地址>] [-DisableAutoApplyUpdate]

参数:
    -Help
        获取 Fooocus Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -BuildMode
        启用 Fooocus Installer 构建模式

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableUpdate
        禁用 Fooocus Installer 更新检查

    -DisableProxy
        禁用 Fooocus Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableGithubMirror
        禁用 Fooocus Installer 自动设置 Github 镜像源

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

    -DisableAutoApplyUpdate
        禁用 Fooocus Installer 自动应用新版本更新


更多的帮助信息请阅读 Fooocus Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[Fooocus Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# 获取内核路径前缀状态
function Get-Core-Prefix-Status {
    if ((Test-Path `"`$PSScriptRoot/core_prefix.txt`") -or (`$CorePrefix)) {
        Print-Msg `"检测到 core_prefix.txt 配置文件 / -CorePrefix 命令行参数, 使用自定义内核路径前缀`"
        if (`$CorePrefix) {
            `$origin_core_prefix = `$CorePrefix
        } else {
            `$origin_core_prefix = Get-Content `"`$PSScriptRoot/core_prefix.txt`"
        }
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix.Trim('/').Trim('\'))) {
            Print-Msg `"转换绝对路径为内核路径前缀: `$origin_core_prefix -> `$Env:CORE_PREFIX`"
        }
    }
    Print-Msg `"当前内核路径前缀: `$Env:CORE_PREFIX`"
    Print-Msg `"完整内核路径: `$PSScriptRoot\`$Env:CORE_PREFIX`"
}


# 显示 Fooocus Installer 版本
function Get-Fooocus-Installer-Version {
    `$ver = `$([string]`$FOOOCUS_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"Fooocus Installer 版本: v`${major}.`${minor}.`${micro}`"
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


# Fooocus Installer 更新检测
function Check-Fooocus-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/fooocus_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/fooocus_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/fooocus_installer/fooocus_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/fooocus_installer/fooocus_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/fooocus_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 Fooocus Installer 的自动检查更新功能`"
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
        Print-Msg `"检查 Fooocus Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/fooocus_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/fooocus_installer.ps1`" |
                Select-String -Pattern `"FOOOCUS_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 Fooocus Installer 更新中`"
            } else {
                Print-Msg `"检查 Fooocus Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -le `$FOOOCUS_INSTALLER_VERSION) {
        Print-Msg `"Fooocus Installer 已是最新版本`"
        return
    }

    if ((`$DisableAutoApplyUpdate) -or (Test-Path `"`$PSScriptRoot/disable_auto_apply_update.txt`")) {
        Print-Msg `"检测到 Fooocus Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"========================================>`").Trim()
        if (!(`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`")) {
            Print-Msg `"跳过 Fooocus Installer 更新`"
            return
        }
    } else {
        Print-Msg `"检测到 Fooocus Installer 有新版本可用`"
    }

    Print-Msg `"调用 Fooocus Installer 进行更新中`"
    . `"`$Env:CACHE_HOME/fooocus_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
    `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
    Print-Msg `"更新结束, 重新启动 Fooocus Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
    Invoke-Expression `"& ```"`$PSCommandPath```" `$raw_params`"
    exit 0
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
    Get-Fooocus-Installer-Version
    Get-Fooocus-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"Fooocus Installer 构建模式已启用, 跳过 Fooocus Installer 更新检查`"
    } else {
        Check-Fooocus-Installer-Update
    }
    Set-Github-Mirror

    if (!(Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX`")) {
        Print-Msg `"内核路径 `$PSScriptRoot\`$Env:CORE_PREFIX 未找到, 请检查 Fooocus 是否已正确安装, 或者尝试运行 Fooocus Installer 进行修复`"
        Read-Host | Out-Null
        return
    }

    Print-Msg `"拉取 Fooocus 更新内容中`"
    Fix-Git-Point-Off-Set `"`$PSScriptRoot/`$Env:CORE_PREFIX`"
    `$core_origin_ver = `$(git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")
    `$branch = `$(git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" symbolic-ref --quiet HEAD 2> `$null).split(`"/`")[2]

    git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" show-ref --verify --quiet `"refs/remotes/origin/`$(git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" branch --show-current)`"
    if (`$?) {
        `$remote_branch = `"origin/`$branch`"
    } else {
        `$author=`$(git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" config --get `"branch.`${branch}.remote`")
        if (`$author) {
            `$remote_branch = `$(git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" rev-parse --abbrev-ref `"`${branch}@{upstream}`")
        } else {
            `$remote_branch = `$branch
        }
    }

    git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" fetch --recurse-submodules --all
    if (`$?) {
        Print-Msg `"应用 Fooocus 更新中`"
        `$commit_hash = `$(git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" log `"`$remote_branch`" --max-count 1 --format=`"%h`")
        git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" reset --hard `"`$remote_branch`" --recurse-submodules
        `$core_latest_ver = `$(git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")

        if (`$core_origin_ver -eq `$core_latest_ver) {
            Print-Msg `"Fooocus 已为最新版, 当前版本：`$core_origin_ver`"
        } else {
            Print-Msg `"Fooocus 更新成功, 版本：`$core_origin_ver -> `$core_latest_ver`"
        }
    } else {
        Print-Msg `"拉取 Fooocus 更新内容失败`"
        Print-Msg `"更新 Fooocus 失败, 请检查控制台日志。可尝试重新运行 Fooocus Installer 更新脚本进行重试`"
    }

    Print-Msg `"退出 Fooocus 更新脚本`"
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
    [string]`$CorePrefix,
    [switch]`$BuildMode,
    [int]`$BuildWitchBranch,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableUpdate,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisableGithubMirror,
    [string]`$UseCustomGithubMirror,
    [switch]`$DisableAutoApplyUpdate
)
& {
    `$prefix_list = @(`"core`", `"Fooocus`", `"fooocus`", `"fooocus_portable`")
    if ((Test-Path `"`$PSScriptRoot/core_prefix.txt`") -or (`$CorePrefix)) {
        if (`$CorePrefix) {
            `$origin_core_prefix = `$CorePrefix
        } else {
            `$origin_core_prefix = Get-Content `"`$PSScriptRoot/core_prefix.txt`"
        }
        `$origin_core_prefix = `$origin_core_prefix.Trim('/').Trim('\')
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix)) {
            `$to_path = `$origin_core_prefix
            `$from_uri = New-Object System.Uri(`$PSScriptRoot.Replace('\', '/') + '/')
            `$to_uri = New-Object System.Uri(`$to_path.Replace('\', '/'))
            `$origin_core_prefix = `$from_uri.MakeRelativeUri(`$to_uri).ToString().Trim('/')
        }
        `$Env:CORE_PREFIX = `$origin_core_prefix
        return
    }
    ForEach (`$i in `$prefix_list) {
        if (Test-Path `"`$PSScriptRoot/`$i`") {
            `$Env:CORE_PREFIX = `$i
            return
        }
    }
    `$Env:CORE_PREFIX = `"core`"
}
# Fooocus Installer 版本和检查更新间隔
`$FOOOCUS_INSTALLER_VERSION = $FOOOCUS_INSTALLER_VERSION
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
`$PIP_EXTRA_INDEX_MIRROR_CPU = `"$PIP_EXTRA_INDEX_MIRROR_CPU`"
`$PIP_EXTRA_INDEX_MIRROR_XPU = `"$PIP_EXTRA_INDEX_MIRROR_XPU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118 = `"$PIP_EXTRA_INDEX_MIRROR_CU118`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
`$PIP_EXTRA_INDEX_MIRROR_CU126 = `"$PIP_EXTRA_INDEX_MIRROR_CU126`"
`$PIP_EXTRA_INDEX_MIRROR_CU128 = `"$PIP_EXTRA_INDEX_MIRROR_CU128`"
`$PIP_EXTRA_INDEX_MIRROR_CU129 = `"$PIP_EXTRA_INDEX_MIRROR_CU129`"
`$PIP_EXTRA_INDEX_MIRROR_CPU_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CPU_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_XPU_NJU = `"$PIP_EXTRA_INDEX_MIRROR_XPU_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU118_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU121_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU121_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU124_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU126_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU128_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU129_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU129_NJU`"
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
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/git/bin`"
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
function Get-Fooocus-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-BuildWitchBranch <Fooocus 分支编号>] [-DisablePyPIMirror] [-DisableUpdate] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像源地址>] [-DisableAutoApplyUpdate]

参数:
    -Help
        获取 Fooocus Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -BuildMode
        启用 Fooocus Installer 构建模式

    -BuildWitchBranch <Fooocus 分支编号>
        (需添加 -BuildMode 启用 Fooocus Installer 构建模式) Fooocus Installer 执行完基础安装流程后调用 Fooocus Installer 的 switch_branch.ps1 脚本, 根据 Fooocus 分支编号切换到对应的 Fooocus 分支
        Fooocus 分支编号可运行 switch_branch.ps1 脚本进行查看

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableUpdate
        禁用 Fooocus Installer 更新检查

    -DisableProxy
        禁用 Fooocus Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableGithubMirror
        禁用 Fooocus Installer 自动设置 Github 镜像源

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

    -DisableAutoApplyUpdate
        禁用 Fooocus Installer 自动应用新版本更新


更多的帮助信息请阅读 Fooocus Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[Fooocus Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# 获取内核路径前缀状态
function Get-Core-Prefix-Status {
    if ((Test-Path `"`$PSScriptRoot/core_prefix.txt`") -or (`$CorePrefix)) {
        Print-Msg `"检测到 core_prefix.txt 配置文件 / -CorePrefix 命令行参数, 使用自定义内核路径前缀`"
        if (`$CorePrefix) {
            `$origin_core_prefix = `$CorePrefix
        } else {
            `$origin_core_prefix = Get-Content `"`$PSScriptRoot/core_prefix.txt`"
        }
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix.Trim('/').Trim('\'))) {
            Print-Msg `"转换绝对路径为内核路径前缀: `$origin_core_prefix -> `$Env:CORE_PREFIX`"
        }
    }
    Print-Msg `"当前内核路径前缀: `$Env:CORE_PREFIX`"
    Print-Msg `"完整内核路径: `$PSScriptRoot\`$Env:CORE_PREFIX`"
}


# 显示 Fooocus Installer 版本
function Get-Fooocus-Installer-Version {
    `$ver = `$([string]`$FOOOCUS_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"Fooocus Installer 版本: v`${major}.`${minor}.`${micro}`"
}


# Fooocus Installer 更新检测
function Check-Fooocus-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/fooocus_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/fooocus_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/fooocus_installer/fooocus_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/fooocus_installer/fooocus_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/fooocus_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 Fooocus Installer 的自动检查更新功能`"
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
        Print-Msg `"检查 Fooocus Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/fooocus_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/fooocus_installer.ps1`" |
                Select-String -Pattern `"FOOOCUS_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 Fooocus Installer 更新中`"
            } else {
                Print-Msg `"检查 Fooocus Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -le `$FOOOCUS_INSTALLER_VERSION) {
        Print-Msg `"Fooocus Installer 已是最新版本`"
        return
    }

    if ((`$DisableAutoApplyUpdate) -or (Test-Path `"`$PSScriptRoot/disable_auto_apply_update.txt`")) {
        Print-Msg `"检测到 Fooocus Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"========================================>`").Trim()
        if (!(`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`")) {
            Print-Msg `"跳过 Fooocus Installer 更新`"
            return
        }
    } else {
        Print-Msg `"检测到 Fooocus Installer 有新版本可用`"
    }

    Print-Msg `"调用 Fooocus Installer 进行更新中`"
    . `"`$Env:CACHE_HOME/fooocus_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
    `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
    Print-Msg `"更新结束, 重新启动 Fooocus Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
    Invoke-Expression `"& ```"`$PSCommandPath```" `$raw_params`"
    exit 0
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


# 获取 Fooocus 分支
function Get-Fooocus-Branch {
    `$remote = `$(git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" remote get-url origin)
    `$ref = `$(git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" symbolic-ref --quiet HEAD 2> `$null)
    if (`$ref -eq `$null) {
        `$ref = `$(git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" show -s --format=`"%h`")
    }

    return `"`$(`$remote.Split(`"/`")[-2])/`$(`$remote.Split(`"/`")[-1]) `$([System.IO.Path]::GetFileName(`$ref))`"
}


# 切换 Fooocus 分支
function Switch-Fooocus-Branch (`$remote, `$branch, `$use_submod) {
    `$fooocus_path = `"`$PSScriptRoot/`$Env:CORE_PREFIX`"
    `$preview_url = `$(git -C `"`$fooocus_path`" remote get-url origin)

    Set-Github-Mirror # 设置 Github 镜像源

    Print-Msg `"Fooocus 远程源替换: `$preview_url -> `$remote`"
    git -C `"`$fooocus_path`" remote set-url origin `"`$remote`" # 替换远程源

    # 处理 Git 子模块
    if (`$use_submod) {
        Print-Msg `"更新 Fooocus 的 Git 子模块信息`"
        git -C `"`$fooocus_path`" submodule update --init --recursive
    } else {
        Print-Msg `"禁用 Fooocus 的 Git 子模块`"
        git -C `"`$fooocus_path`" submodule deinit --all -f
    }

    Print-Msg `"拉取 Fooocus 远程源更新`"
    git -C `"`$fooocus_path`" fetch # 拉取远程源内容
    if (`$?) {
        if (`$use_submod) {
            Print-Msg `"清理原有的 Git 子模块`"
            git -C `"`$fooocus_path`" submodule deinit --all -f
        }
        Print-Msg `"切换 Fooocus 分支至 `$branch`"

        # 本地分支不存在时创建一个分支
        git -C `"`$fooocus_path`" show-ref --verify --quiet `"refs/heads/`${branch}`"
        if (!(`$?)) {
            git -C `"`$fooocus_path`" branch `"`${branch}`"
        }

        git -C `"`$fooocus_path`" checkout `"`${branch}`" --force # 切换分支
        Print-Msg `"应用 Fooocus 远程源的更新`"
        if (`$use_submod) {
            Print-Msg `"更新 Fooocus 的 Git 子模块信息`"
            git -C `"`$fooocus_path`" reset --hard `"origin/`$branch`"
            git -C `"`$fooocus_path`" submodule deinit --all -f
            git -C `"`$fooocus_path`" submodule update --init --recursive
        }
        if (`$use_submod) {
            git -C `"`$fooocus_path`" reset --recurse-submodules --hard `"origin/`$branch`" # 切换到最新的提交内容上
        } else {
            git -C `"`$fooocus_path`" reset --hard `"origin/`$branch`" # 切换到最新的提交内容上
        }
        Print-Msg `"切换 Fooocus 分支完成`"
        `$global:status = `$true
    } else {
        Print-Msg `"拉取 Fooocus 远程源更新失败, 取消分支切换`"
        Print-Msg `"尝试回退 Fooocus 的更改`"
        git -C `"`$fooocus_path`" remote set-url origin `"`$preview_url`"
        if (`$use_submod) {
            git -C `"`$fooocus_path`" submodule deinit --all -f
        } else {
            git -C `"`$fooocus_path`" submodule update --init --recursive
        }
        Print-Msg `"回退 Fooocus 分支更改完成`"
        Print-Msg `"切换 Fooocus 分支更改失败`"
        `$global:status = `$false
    }
}


function Main {
    Print-Msg `"初始化中`"
    Get-Fooocus-Installer-Version
    Get-Fooocus-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"Fooocus Installer 构建模式已启用, 跳过 Fooocus Installer 更新检查`"
    } else {
        Check-Fooocus-Installer-Update
    }

    if (!(Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX`")) {
        Print-Msg `"内核路径 `$PSScriptRoot\`$Env:CORE_PREFIX 未找到, 请检查 Fooocus 是否已正确安装, 或者尝试运行 Fooocus Installer 进行修复`"
        Read-Host | Out-Null
        return
    }

    `$content = `"
-----------------------------------------------------
- 1、lllyasviel - Fooocus 分支
- 2、runew0lf - RuinedFooocus 分支
- 3、MoonRide303 - Fooocus-MRE 分支
-----------------------------------------------------
`".Trim()

    `$to_exit = 0

    while (`$True) {
        Print-Msg `"Fooocus 分支列表`"
        `$go_to = 0
        Write-Host `$content
        Print-Msg `"当前 Fooocus 分支: `$(Get-Fooocus-Branch)`"
        Print-Msg `"请选择 Fooocus 分支`"
        Print-Msg `"提示: 输入数字后回车, 或者输入 exit 退出 Fooocus 分支切换脚本`"
        if (`$BuildMode) {
            `$go_to = 1
            `$arg = `$BuildWitchBranch
        } else {
            `$arg = (Read-Host `"========================================>`").Trim()
        }

        switch (`$arg) {
            1 {
                `$remote = `"https://github.com/lllyasviel/Fooocus`"
                `$branch = `"main`"
                `$branch_name = `"lllyasviel - Fooocus 分支`"
                `$use_submod = `$false
                `$go_to = 1
            }
            2 {
                `$remote = `"https://github.com/runew0lf/RuinedFooocus`"
                `$branch = `"main`"
                `$branch_name = `"runew0lf - RuinedFooocus 分支`"
                `$use_submod = `$false
                `$go_to = 1
            }
            3 {
                `$remote = `"https://github.com/MoonRide303/Fooocus-MRE`"
                `$branch = `"moonride-main`"
                `$branch_name = `"MoonRide303 - Fooocus-MRE 分支`"
                `$use_submod = `$false
                `$go_to = 1
            }
            exit {
                Print-Msg `"退出 Fooocus 分支切换脚本`"
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

    Print-Msg `"是否切换 Fooocus 分支到 `$branch_name ?`"
    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
    if (`$BuildMode) {
        `$operate = `"yes`"
    } else {
        `$operate = (Read-Host `"========================================>`").Trim()
    }

    if (`$operate -eq `"yes`" -or `$operate -eq `"y`" -or `$operate -eq `"YES`" -or `$operate -eq `"Y`") {
        Print-Msg `"开始切换 Fooocus 分支`"
        Switch-Fooocus-Branch `$remote `$branch `$use_submod
        if (`$status) {
            Print-Msg `"切换 Fooocus 分支成功`"
        } else {
            Print-Msg `"切换 Fooocus 分支失败, 可尝试重新运行 Fooocus 分支切换脚本`"
        }
    } else {
        Print-Msg `"取消切换 Fooocus 分支`"
    }
    Print-Msg `"退出 Fooocus 分支切换脚本`"

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
function Write-Launch-Fooocus-Install-Script {
    $content = "
param (
    [string]`$InstallPath,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableUV,
    [switch]`$DisableGithubMirror,
    [string]`$UseCustomGithubMirror,
    [string]`$InstallBranch,
    [Parameter(ValueFromRemainingArguments=`$true)]`$ExtraArgs
)
`$FOOOCUS_INSTALLER_VERSION = $FOOOCUS_INSTALLER_VERSION
if (-not `$InstallPath) {
    `$InstallPath = `$PSScriptRoot
}



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[Fooocus Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# 显示 Fooocus Installer 版本
function Get-Fooocus-Installer-Version {
    `$ver = `$([string]`$FOOOCUS_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"Fooocus Installer 版本: v`${major}.`${minor}.`${micro}`"
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


# 下载 Fooocus Installer
function Download-Fooocus-Installer {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/fooocus_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/fooocus_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/fooocus_installer/fooocus_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/fooocus_installer/fooocus_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/fooocus_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    ForEach (`$url in `$urls) {
        Print-Msg `"正在下载最新的 Fooocus Installer 脚本`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/fooocus_installer.ps1`"
        if (`$?) {
            Print-Msg `"下载 Fooocus Installer 脚本成功`"
            break
        } else {
            Print-Msg `"下载 Fooocus Installer 脚本失败`"
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试下载 Fooocus Installer 脚本`"
            } else {
                Print-Msg `"下载 Fooocus Installer 脚本失败, 可尝试重新运行 Fooocus Installer 下载脚本`"
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

    if ((Get-Command git -ErrorAction SilentlyContinue) -and (Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX/.git`")) {
        `$git_remote = `$(git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" remote get-url origin)
        `$array = `$git_remote -split `"/`"
        `$branch = `"`$(`$array[-2])/`$(`$array[-1])`"
        if ((`$branch -eq `"lllyasviel/Fooocus`") -or (`$branch -eq `"lllyasviel/Fooocus.git`")) {
            `$arg.Add(`"-InstallBranch`", `"fooocus`")
        } elseif ((`$branch -eq `"MoonRide303/Fooocus-MRE`") -or (`$branch -eq `"MoonRide303/Fooocus-MRE.git`")) {
            `$arg.Add(`"-InstallBranch`", `"fooocus_mre`")
        } elseif ((`$branch -eq `"runew0lf/RuinedFooocus`") -or (`$branch -eq `"runew0lf/RuinedFooocus.git`")) {
            `$arg.Add(`"-InstallBranch`", `"ruined_fooocus`")
        }
    } elseif ((Test-Path `"`$PSScriptRoot/install_fooocus.txt`") -or (`$InstallBranch -eq `"fooocus`")) {
        `$arg.Add(`"-InstallBranch`", `"fooocus`")
    } elseif ((Test-Path `"`$PSScriptRoot/install_fooocus_mre.txt`") -or (`$InstallBranch -eq `"fooocus_mre`")) {
        `$arg.Add(`"-InstallBranch`", `"fooocus_mre`")
    } elseif ((Test-Path `"`$PSScriptRoot/install_ruined_fooocus.txt`") -or (`$InstallBranch -eq `"ruined_fooocus`")) {
        `$arg.Add(`"-InstallBranch`", `"ruined_fooocus`")
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
    Get-Fooocus-Installer-Version
    Set-Proxy

    `$status = Download-Fooocus-Installer

    if (`$status) {
        Print-Msg `"运行 Fooocus Installer 中`"
        `$arg = Get-Local-Setting
        `$extra_args = Get-ExtraArgs
        try {
            Invoke-Expression `"& ```"`$PSScriptRoot/cache/fooocus_installer.ps1```" `$extra_args @arg`"
        }
        catch {
            Print-Msg `"运行 Fooocus Installer 时出现了错误: `$_`"
            Read-Host | Out-Null
        }
    } else {
        Read-Host | Out-Null
    }
}

###################

Main
".Trim()

    if (Test-Path "$InstallPath/launch_fooocus_installer.ps1") {
        Print-Msg "更新 launch_fooocus_installer.ps1 中"
    } else {
        Print-Msg "生成 launch_fooocus_installer.ps1 中"
    }
    Set-Content -Encoding $PS_SCRIPT_ENCODING -Path "$InstallPath/launch_fooocus_installer.ps1" -Value $content
}


# 重装 PyTorch 脚本
function Write-PyTorch-ReInstall-Script {
    $content = "
param (
    [switch]`$Help,
    [string]`$CorePrefix,
    [switch]`$BuildMode,
    [int]`$BuildWithTorch,
    [switch]`$BuildWithTorchReinstall,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableUpdate,
    [switch]`$DisableUV,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisableAutoApplyUpdate
)
& {
    `$prefix_list = @(`"core`", `"Fooocus`", `"fooocus`", `"fooocus_portable`")
    if ((Test-Path `"`$PSScriptRoot/core_prefix.txt`") -or (`$CorePrefix)) {
        if (`$CorePrefix) {
            `$origin_core_prefix = `$CorePrefix
        } else {
            `$origin_core_prefix = Get-Content `"`$PSScriptRoot/core_prefix.txt`"
        }
        `$origin_core_prefix = `$origin_core_prefix.Trim('/').Trim('\')
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix)) {
            `$to_path = `$origin_core_prefix
            `$from_uri = New-Object System.Uri(`$PSScriptRoot.Replace('\', '/') + '/')
            `$to_uri = New-Object System.Uri(`$to_path.Replace('\', '/'))
            `$origin_core_prefix = `$from_uri.MakeRelativeUri(`$to_uri).ToString().Trim('/')
        }
        `$Env:CORE_PREFIX = `$origin_core_prefix
        return
    }
    ForEach (`$i in `$prefix_list) {
        if (Test-Path `"`$PSScriptRoot/`$i`") {
            `$Env:CORE_PREFIX = `$i
            return
        }
    }
    `$Env:CORE_PREFIX = `"core`"
}
# Fooocus Installer 版本和检查更新间隔
`$FOOOCUS_INSTALLER_VERSION = $FOOOCUS_INSTALLER_VERSION
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
`$PIP_EXTRA_INDEX_MIRROR_CPU = `"$PIP_EXTRA_INDEX_MIRROR_CPU`"
`$PIP_EXTRA_INDEX_MIRROR_XPU = `"$PIP_EXTRA_INDEX_MIRROR_XPU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118 = `"$PIP_EXTRA_INDEX_MIRROR_CU118`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
`$PIP_EXTRA_INDEX_MIRROR_CU126 = `"$PIP_EXTRA_INDEX_MIRROR_CU126`"
`$PIP_EXTRA_INDEX_MIRROR_CU128 = `"$PIP_EXTRA_INDEX_MIRROR_CU128`"
`$PIP_EXTRA_INDEX_MIRROR_CU129 = `"$PIP_EXTRA_INDEX_MIRROR_CU129`"
`$PIP_EXTRA_INDEX_MIRROR_CPU_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CPU_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_XPU_NJU = `"$PIP_EXTRA_INDEX_MIRROR_XPU_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU118_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU121_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU121_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU124_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU126_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU128_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU129_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU129_NJU`"
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# Aria2 最低版本
`$ARIA2_MINIMUM_VER = `"$ARIA2_MINIMUM_VER`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/git/bin`"
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
function Get-Fooocus-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-BuildWithTorch <PyTorch 版本编号>] [-BuildWithTorchReinstall] [-DisablePyPIMirror] [-DisableUpdate] [-DisableUV] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableAutoApplyUpdate]

参数:
    -Help
        获取 Fooocus Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -BuildMode
        启用 Fooocus Installer 构建模式

    -BuildWithTorch <PyTorch 版本编号>
        (需添加 -BuildMode 启用 Fooocus Installer 构建模式) Fooocus Installer 执行完基础安装流程后调用 Fooocus Installer 的 reinstall_pytorch.ps1 脚本, 根据 PyTorch 版本编号安装指定的 PyTorch 版本
        PyTorch 版本编号可运行 reinstall_pytorch.ps1 脚本进行查看

    -BuildWithTorchReinstall
        (需添加 -BuildMode 启用 Fooocus Installer 构建模式, 并且添加 -BuildWithTorch) 在 Fooocus Installer 构建模式下, 执行 reinstall_pytorch.ps1 脚本对 PyTorch 进行指定版本安装时使用强制重新安装

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableUpdate
        禁用 Fooocus Installer 更新检查

    -DisableUV
        禁用 Fooocus Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -DisableProxy
        禁用 Fooocus Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableAutoApplyUpdate
        禁用 Fooocus Installer 自动应用新版本更新


更多的帮助信息请阅读 Fooocus Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[Fooocus Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# 获取内核路径前缀状态
function Get-Core-Prefix-Status {
    if ((Test-Path `"`$PSScriptRoot/core_prefix.txt`") -or (`$CorePrefix)) {
        Print-Msg `"检测到 core_prefix.txt 配置文件 / -CorePrefix 命令行参数, 使用自定义内核路径前缀`"
        if (`$CorePrefix) {
            `$origin_core_prefix = `$CorePrefix
        } else {
            `$origin_core_prefix = Get-Content `"`$PSScriptRoot/core_prefix.txt`"
        }
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix.Trim('/').Trim('\'))) {
            Print-Msg `"转换绝对路径为内核路径前缀: `$origin_core_prefix -> `$Env:CORE_PREFIX`"
        }
    }
    Print-Msg `"当前内核路径前缀: `$Env:CORE_PREFIX`"
    Print-Msg `"完整内核路径: `$PSScriptRoot\`$Env:CORE_PREFIX`"
}


# 显示 Fooocus Installer 版本
function Get-Fooocus-Installer-Version {
    `$ver = `$([string]`$FOOOCUS_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"Fooocus Installer 版本: v`${major}.`${minor}.`${micro}`"
}


# PyPI 镜像源状态
function PyPI-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 PyPI 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pypi_mirror.txt 配置文件 / -DisablePyPIMirror 命令行参数, 已将 PyPI 源切换至官方源`"
    }
}


# Fooocus Installer 更新检测
function Check-Fooocus-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/fooocus_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/fooocus_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/fooocus_installer/fooocus_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/fooocus_installer/fooocus_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/fooocus_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 Fooocus Installer 的自动检查更新功能`"
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
        Print-Msg `"检查 Fooocus Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/fooocus_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/fooocus_installer.ps1`" |
                Select-String -Pattern `"FOOOCUS_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 Fooocus Installer 更新中`"
            } else {
                Print-Msg `"检查 Fooocus Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -le `$FOOOCUS_INSTALLER_VERSION) {
        Print-Msg `"Fooocus Installer 已是最新版本`"
        return
    }

    if ((`$DisableAutoApplyUpdate) -or (Test-Path `"`$PSScriptRoot/disable_auto_apply_update.txt`")) {
        Print-Msg `"检测到 Fooocus Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"========================================>`").Trim()
        if (!(`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`")) {
            Print-Msg `"跳过 Fooocus Installer 更新`"
            return
        }
    } else {
        Print-Msg `"检测到 Fooocus Installer 有新版本可用`"
    }

    Print-Msg `"调用 Fooocus Installer 进行更新中`"
    . `"`$Env:CACHE_HOME/fooocus_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
    `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
    Print-Msg `"更新结束, 重新启动 Fooocus Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
    Invoke-Expression `"& ```"`$PSCommandPath```" `$raw_params`"
    exit 0
}


# 检查 uv 是否需要更新
function Check-uv-Version {
    `$content = `"
import re
from importlib.metadata import version



def compare_versions(version1, version2) -> int:
    version1 = str(version1)
    version2 = str(version2)
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
    # 切换 uv 指定的 Python
    if (Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX/python/python.exe`") {
        `$Env:UV_PYTHON = `"`$PSScriptRoot/`$Env:CORE_PREFIX/python/python.exe`"
    }

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

    return `$torch_ver, `$xformers_ver
}


# 获取 HashTable 的值
function Get-HashValue {
    param(
        [hashtable]`$Hashtable,
        [string]`$Key,
        [object]`$Default = `$null
    )

    if (`$Hashtable.ContainsKey(`$Key)) {
        return `$Hashtable[`$Key]
    } else {
        return `$Default
    }
}


# 获取可用的 PyTorch 类型
function Get-Avaliable-PyTorch-Type {
    `$content = `"
import re
import json
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


def get_cuda_version() -> float:
    try:
        # 获取 nvidia-smi 输出
        output = subprocess.check_output(['nvidia-smi', '-q'], text=True)
        match = re.search(r'CUDA Version\s+:\s+(\d+\.\d+)', output)
        if match:
            return float(match.group(1))
        return 0.0
    except:
        return 0.0


def get_gpu_list() -> list[dict[str, str]]:
    try:
        cmd = [
            'powershell',
            '-Command',
            'Get-CimInstance Win32_VideoController | Select-Object Name, AdapterCompatibility, AdapterRAM, DriverVersion | ConvertTo-Json'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        gpus = json.loads(result.stdout)
        if isinstance(gpus, dict):
            gpus = [gpus]

        gpu_info = []
        for gpu in gpus:
            gpu_info.append({
                'Name': gpu.get('Name', None),
                'AdapterCompatibility': gpu.get('AdapterCompatibility', None),
                'AdapterRAM': gpu.get('AdapterRAM', None),
                'DriverVersion': gpu.get('DriverVersion', None),
            })
        return gpu_info
    except Exception as _:
        return []


def compare_versions(version1: str, version2: str) -> int:
    version1 = str(version1)
    version2 = str(version2)
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


CUDA_TYPE = [
    'cu113', 'cu117', 'cu118', 'cu121',
    'cu124', 'cu126', 'cu128', 'cu129',
]

def get_avaliable_device() -> str:
    cuda_comp_cap = get_cuda_comp_cap()
    cuda_support_ver = get_cuda_version()
    gpu_list = get_gpu_list()
    device_list = ['cpu']
    if any([
        x for x in gpu_list
        if 'Intel' in x.get('AdapterCompatibility', '')
        and (
            x.get('Name', '').startswith('Intel(R) Arc')
            or
            x.get('Name', '').startswith('Intel(R) Core Ultra')
        )
    ]):
        device_list.append('xpu')

    if any([
        x for x in gpu_list
        if 'Intel' in x.get('AdapterCompatibility', '')
        or 'NVIDIA' in x.get('AdapterCompatibility', '')
        or 'Advanced Micro Devices' in x.get('AdapterCompatibility', '')
    ]):
        device_list.append('directml')

    if compare_versions(cuda_comp_cap, '10.0') > 0:
        for ver in CUDA_TYPE:
            if compare_versions(ver, str(int(12.8 * 10))) >= 0:
                device_list.append(ver)
    else:
        for ver in CUDA_TYPE:
            if compare_versions(ver, str(int(cuda_support_ver * 10))) <= 0:
                device_list.append(ver)

    return ','.join(list(set(device_list)))


if __name__ == '__main__':
    print(get_avaliable_device())
`".Trim()
    Print-Msg `"获取可用的 PyTorch 类型`"
    `$res = `$(python -c `"`$content`")
    return `$res -split ',' | ForEach-Object { `$_.Trim() }
}


# 获取 PyTorch 列表
function Get-PyTorch-List {
    `$pytorch_list = New-Object System.Collections.ArrayList
    `$supported_type = Get-Avaliable-PyTorch-Type
    # >>>>>>>>>> Start
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 1.12.1 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==1.12.1+cpu torchvision==0.13.1+cpu torchaudio==1.12.1+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 1.12.1 (CUDA 11.3) + xFormers 0.0.14`"
        `"type`" = `"cu113`"
        `"supported`" = `"cu113`" -in `$supported_type
        `"torch`" = `"torch==1.12.1+cu113 torchvision==0.13.1+cu113 torchaudio==1.12.1+cu113`"
        `"xformers`" = `"xformers==0.0.14`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 1.13.1 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==1.13.1+cpu torchvision==0.14.1+cpu torchaudio==0.13.1+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 1.13.1 (DirectML)`"
        `"type`" = `"directml`"
        `"supported`" = `"directml`" -in `$supported_type
        `"torch`" = `"torch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1 torch-directml==0.1.13.1.dev230413`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 1.13.1 (CUDA 11.7) + xFormers 0.0.16`"
        `"type`" = `"cu117`"
        `"supported`" = `"cu117`" -in `$supported_type
        `"torch`" = `"torch==1.13.1+cu117 torchvision==0.14.1+cu117 torchaudio==1.13.1+cu117`"
        `"xformers`" = `"xformers==0.0.18`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.0.0 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.0.0+cpu torchvision==0.15.1+cpu torchaudio==2.0.0+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.0.0 (DirectML)`"
        `"type`" = `"directml`"
        `"supported`" = `"directml`" -in `$supported_type
        `"torch`" = `"torch==2.0.0 torchvision==0.15.1 torchaudio==2.0.0 torch-directml==0.2.0.dev230426`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.0.0 (Intel Arc)`"
        `"type`" = `"xpu`"
        `"supported`" = `"xpu`" -in `$supported_type
        `"torch`" = `"torch==2.0.0a0+gite9ebda2 torchvision==0.15.2a0+fa99a53 intel_extension_for_pytorch==2.0.110+gitc6ea20b`"
        `"find_links`" = `"https://licyk.github.io/t/pypi/index.html`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.0.0 (CUDA 11.8) + xFormers 0.0.18`"
        `"type`" = `"cu118`"
        `"supported`" = `"cu118`" -in `$supported_type
        `"torch`" = `"torch==2.0.0+cu118 torchvision==0.15.1+cu118 torchaudio==2.0.0+cu118`"
        `"xformers`" = `"xformers==0.0.14`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.0.1 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.0.1+cpu torchvision==0.15.2+cpu torchaudio==2.0.1+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.0.1 (CUDA 11.8) + xFormers 0.0.22`"
        `"type`" = `"cu118`"
        `"supported`" = `"cu118`" -in `$supported_type
        `"torch`" = `"torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.1+cu118`"
        `"xformers`" = `"xformers==0.0.22`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.1.0 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.1.0+cpu torchvision==0.16.0+cpu torchaudio==2.1.0+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.1.0 (Intel Arc)`"
        `"type`" = `"xpu`"
        `"supported`" = `"xpu`" -in `$supported_type
        `"torch`" = `"torch==2.1.0a0+cxx11.abi torchvision==0.16.0a0+cxx11.abi torchaudio==2.1.0a0+cxx11.abi intel_extension_for_pytorch==2.1.10+xpu`"
        `"find_links`" = `"https://licyk.github.io/t/pypi/index.html`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.1.0 (Intel Core Ultra)`"
        `"type`" = `"xpu`"
        `"supported`" = `"xpu`" -in `$supported_type
        `"torch`" = `"torch==2.1.0a0+git7bcf7da torchvision==0.16.0+fbb4cc5 torchaudio==2.1.0+6ea1133 intel_extension_for_pytorch==2.1.20+git4849f3b`"
        `"find_links`" = `"https://licyk.github.io/t/pypi/index.html`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.1.1 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.1.1+cpu torchvision==0.16.1+cpu torchaudio==2.1.1+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.1.1 (CUDA 11.8) + xFormers 0.0.23`"
        `"type`" = `"cu118`"
        `"supported`" = `"cu118`" -in `$supported_type
        `"torch`" = `"torch==2.1.1+cu118 torchvision==0.16.1+cu118 torchaudio==2.1.1+cu118`"
        `"xformers`" = `"xformers==0.0.23+cu118`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU118
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.1.1 (CUDA 12.1) + xFormers 0.0.23`"
        `"type`" = `"cu121`"
        `"supported`" = `"cu121`" -in `$supported_type
        `"torch`" = `"torch==2.1.1+cu121 torchvision==0.16.1+cu121 torchaudio==2.1.1+cu121`"
        `"xformers`" = `"xformers===0.0.23`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.1.2 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.1.2+cpu torchvision==0.16.2+cpu torchaudio==2.1.2+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.1.2 (CUDA 11.8) + xFormers 0.0.23.post1`"
        `"type`" = `"cu118`"
        `"supported`" = `"cu118`" -in `$supported_type
        `"torch`" = `"torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2+cu118`"
        `"xformers`" = `"xformers==0.0.23.post1+cu118`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU118
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.1.2 (CUDA 12.1) + xFormers 0.0.23.post1`"
        `"type`" = `"cu121`"
        `"supported`" = `"cu121`" -in `$supported_type
        `"torch`" = `"torch==2.1.2+cu121 torchvision==0.16.2+cu121 torchaudio==2.1.2+cu121`"
        `"xformers`" = `"xformers===0.0.23.post1`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.2.0 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.2.0+cpu torchvision==0.17.0+cpu torchaudio==2.2.0+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.2.0 (CUDA 11.8) + xFormers 0.0.24`"
        `"type`" = `"cu118`"
        `"supported`" = `"cu118`" -in `$supported_type
        `"torch`" = `"torch==2.2.0+cu118 torchvision==0.17.0+cu118 torchaudio==2.2.0+cu118`"
        `"xformers`" = `"xformers==0.0.24+cu118`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU118
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.2.0 (CUDA 12.1) + xFormers 0.0.24`"
        `"type`" = `"cu121`"
        `"supported`" = `"cu121`" -in `$supported_type
        `"torch`" = `"torch==2.2.0+cu121 torchvision==0.17.0+cu121 torchaudio==2.2.0+cu121`"
        `"xformers`" = `"xformers===0.0.24`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.2.1 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.2.1+cpu torchvision==0.17.1+cpu torchaudio==2.2.1+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.2.1 (CUDA 11.8) + xFormers 0.0.25`"
        `"type`" = `"cu118`"
        `"supported`" = `"cu118`" -in `$supported_type
        `"torch`" = `"torch==2.2.1+cu118 torchvision==0.17.1+cu118 torchaudio==2.2.1+cu118`"
        `"xformers`" = `"xformers==0.0.25+cu118`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU118
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.2.1 (DirectML)`"
        `"type`" = `"directml`"
        `"supported`" = `"directml`" -in `$supported_type
        `"torch`" = `"torch==2.2.1 torchvision==0.17.1 torchaudio==2.2.1 torch-directml==0.2.1.dev240521`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.2.1 (CUDA 12.1) + xFormers 0.0.25`"
        `"type`" = `"cu121`"
        `"supported`" = `"cu121`" -in `$supported_type
        `"torch`" = `"torch==2.2.1+cu121 torchvision==0.17.1+cu121 torchaudio==2.2.1+cu121`"
        `"xformers`" = `"xformers===0.0.25`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.2.2 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.2.2+cpu torchvision==0.17.2+cpu torchaudio==2.2.2+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.2.2 (CUDA 11.8) + xFormers 0.0.25.post1`"
        `"type`" = `"cu118`"
        `"supported`" = `"cu118`" -in `$supported_type
        `"torch`" = `"torch==2.2.2+cu118 torchvision==0.17.2+cu118 torchaudio==2.2.2+cu118`"
        `"xformers`" = `"xformers==0.0.25.post1+cu118`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU118
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.2.2 (CUDA 12.1) + xFormers 0.0.25.post1`"
        `"type`" = `"cu121`"
        `"supported`" = `"cu121`" -in `$supported_type
        `"torch`" = `"torch==2.2.2+cu121 torchvision==0.17.2+cu121 torchaudio==2.2.2+cu121`"
        `"xformers`" = `"xformers===0.0.25.post1`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.3.0 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.3.0+cpu torchvision==0.18.0+cpu torchaudio==2.3.0+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.3.0 (CUDA 11.8) + xFormers 0.0.26.post1`"
        `"type`" = `"cu118`"
        `"supported`" = `"cu118`" -in `$supported_type
        `"torch`" = `"torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118`"
        `"xformers`" = `"xformers==0.0.26.post1+cu118`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU118
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.3.0 (CUDA 12.1) + xFormers 0.0.26.post1`"
        `"type`" = `"cu121`"
        `"supported`" = `"cu121`" -in `$supported_type
        `"torch`" = `"torch==2.3.0+cu121 torchvision==0.18.0+cu121 torchaudio==2.3.0+cu121`"
        `"xformers`" = `"xformers===0.0.26.post1`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.3.1 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.3.1+cpu torchvision==0.18.1+cpu torchaudio==2.3.1+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.3.1 (DirectML)`"
        `"type`" = `"directml`"
        `"supported`" = `"directml`" -in `$supported_type
        `"torch`" = `"torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 torch-directml==0.2.3.dev240715`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.3.1 (CUDA 11.8) + xFormers 0.0.27`"
        `"type`" = `"cu118`"
        `"supported`" = `"cu118`" -in `$supported_type
        `"torch`" = `"torch==2.3.1+cu118 torchvision==0.18.1+cu118 torchaudio==2.3.1+cu118`"
        `"xformers`" = `"xformers==0.0.27+cu118`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU118
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.3.1 (CUDA 12.1) + xFormers 0.0.27`"
        `"type`" = `"cu121`"
        `"supported`" = `"cu121`" -in `$supported_type
        `"torch`" = `"torch==2.3.1+cu121 torchvision==0.18.1+cu121 torchaudio==2.3.1+cu121`"
        `"xformers`" = `"xformers===0.0.27`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU121_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU121
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.4.0 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.4.0+cpu torchvision==0.19.0+cpu torchaudio==2.4.0+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.4.0 (CUDA 11.8) + xFormers 0.0.27.post2`"
        `"type`" = `"cu118`"
        `"supported`" = `"cu118`" -in `$supported_type
        `"torch`" = `"torch==2.4.0+cu118 torchvision==0.19.0+cu118 torchaudio==2.4.0+cu118`"
        `"xformers`" = `"xformers==0.0.27.post2+cu118`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU118
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.4.0 (CUDA 12.1) + xFormers 0.0.27.post2`"
        `"type`" = `"cu121`"
        `"supported`" = `"cu121`" -in `$supported_type
        `"torch`" = `"torch==2.4.0+cu121 torchvision==0.19.0+cu121 torchaudio==2.4.0+cu121`"
        `"xformers`" = `"xformers==0.0.27.post2`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU121_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU121
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.4.1 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.4.1+cpu torchvision==0.19.1+cpu torchaudio==2.4.1+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.4.1 (CUDA 12.4) + xFormers 0.0.28.post1`"
        `"type`" = `"cu124`"
        `"supported`" = `"cu124`" -in `$supported_type
        `"torch`" = `"torch==2.4.1+cu124 torchvision==0.19.1+cu124 torchaudio==2.4.1+cu124`"
        `"xformers`" = `"xformers==0.0.28.post1`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU124_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU124
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.5.0 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.5.0+cpu torchvision==0.20.0+cpu torchaudio==2.5.0+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.5.0 (CUDA 12.4) + xFormers 0.0.28.post2`"
        `"type`" = `"cu124`"
        `"supported`" = `"cu124`" -in `$supported_type
        `"torch`" = `"torch==2.5.0+cu124 torchvision==0.20.0+cu124 torchaudio==2.5.0+cu124`"
        `"xformers`" = `"xformers==0.0.28.post2`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU124_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU124
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.5.1 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.5.1+cpu torchvision==0.20.1+cpu torchaudio==2.5.1+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.5.1 (CUDA 12.4) + xFormers 0.0.28.post3`"
        `"type`" = `"cu124`"
        `"supported`" = `"cu124`" -in `$supported_type
        `"torch`" = `"torch==2.5.1+cu124 torchvision==0.20.1+cu124 torchaudio==2.5.1+cu124`"
        `"xformers`" = `"xformers==0.0.28.post3`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU124_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU124
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.6.0 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.6.0+cpu torchvision==0.21.0+cpu torchaudio==2.6.0+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.6.0 (Intel Arc)`"
        `"type`" = `"xpu`"
        `"supported`" = `"xpu`" -in `$supported_type
        `"torch`" = `"torch==2.6.0+xpu torchvision==0.21.0+xpu torchaudio==2.6.0+xpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_XPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_XPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.6.0 (CUDA 12.4) + xFormers 0.0.29.post3`"
        `"type`" = `"cu124`"
        `"supported`" = `"cu124`" -in `$supported_type
        `"torch`" = `"torch==2.6.0+cu124 torchvision==0.21.0+cu124 torchaudio==2.6.0+cu124`"
        `"xformers`" = `"xformers==0.0.29.post3`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU124_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU124
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.6.0 (CUDA 12.6) + xFormers 0.0.29.post3`"
        `"type`" = `"cu126`"
        `"supported`" = `"cu126`" -in `$supported_type
        `"torch`" = `"torch==2.6.0+cu126 torchvision==0.21.0+cu126 torchaudio==2.6.0+cu126`"
        `"xformers`" = `"xformers==0.0.29.post3`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU126_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU126
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.7.0 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.7.0+cpu torchvision==0.22.0+cpu torchaudio==2.7.0+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.7.0 (Intel Arc)`"
        `"type`" = `"xpu`"
        `"supported`" = `"xpu`" -in `$supported_type
        `"torch`" = `"torch==2.7.0+xpu torchvision==0.22.0+xpu torchaudio==2.7.0+xpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_XPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_XPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.7.0 (CUDA 11.8)`"
        `"type`" = `"cu118`"
        `"supported`" = `"cu118`" -in `$supported_type
        `"torch`" = `"torch==2.7.0+cu118 torchvision==0.22.0+cu118 torchaudio==2.7.0+cu118`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU118
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.7.0 (CUDA 12.6) + xFormers 0.0.30`"
        `"type`" = `"cu126`"
        `"supported`" = `"cu126`" -in `$supported_type
        `"torch`" = `"torch==2.7.0+cu126 torchvision==0.22.0+cu126 torchaudio==2.7.0+cu126`"
        `"xformers`" = `"xformers==0.0.30`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU126_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU126
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.7.0 (CUDA 12.8) + xFormers 0.0.30`"
        `"type`" = `"cu128`"
        `"supported`" = `"cu128`" -in `$supported_type
        `"torch`" = `"torch==2.7.0+cu128 torchvision==0.22.0+cu128 torchaudio==2.7.0+cu128`"
        `"xformers`" = `"xformers==0.0.30`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU128_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU128
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.7.1 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.7.1+cpu torchvision==0.22.1+cpu torchaudio==2.7.1+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.7.1 (Intel Arc)`"
        `"type`" = `"xpu`"
        `"supported`" = `"xpu`" -in `$supported_type
        `"torch`" = `"torch==2.7.1+xpu torchvision==0.22.1+xpu torchaudio==2.7.1+xpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_XPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_XPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.7.1 (CUDA 11.8)`"
        `"type`" = `"cu118`"
        `"supported`" = `"cu118`" -in `$supported_type
        `"torch`" = `"torch==2.7.1+cu118 torchvision==0.22.1+cu118 torchaudio==2.7.1+cu118`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU118
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.7.1 (CUDA 12.6) + xFormers 0.0.31.post1`"
        `"type`" = `"cu126`"
        `"supported`" = `"cu126`" -in `$supported_type
        `"torch`" = `"torch==2.7.1+cu126 torchvision==0.22.1+cu126 torchaudio==2.7.1+cu126`"
        `"xformers`" = `"xformers==0.0.31.post1`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU126_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU126
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.7.1 (CUDA 12.8) + xFormers 0.0.31.post1`"
        `"type`" = `"cu128`"
        `"supported`" = `"cu128`" -in `$supported_type
        `"torch`" = `"torch==2.7.1+cu128 torchvision==0.22.1+cu128 torchaudio==2.7.1+cu128`"
        `"xformers`" = `"xformers==0.0.31.post1`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU128_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU128
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.8.0 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.8.0+cpu torchvision==0.23.0+cpu torchaudio==2.8.0+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.8.0 (Intel Arc)`"
        `"type`" = `"xpu`"
        `"supported`" = `"xpu`" -in `$supported_type
        `"torch`" = `"torch==2.8.0+xpu torchvision==0.23.0+xpu torchaudio==2.8.0+xpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_XPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_XPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.8.0 (CUDA 12.6)`"
        `"type`" = `"cu126`"
        `"supported`" = `"cu126`" -in `$supported_type
        `"torch`" = `"torch==2.8.0+cu126 torchvision==0.23.0+cu126 torchaudio==2.8.0+cu126`"
        `"xformers`" = `"xformers==0.0.32.post2`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU126_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU126
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.8.0 (CUDA 12.8)`"
        `"type`" = `"cu128`"
        `"supported`" = `"cu128`" -in `$supported_type
        `"torch`" = `"torch==2.8.0+cu128 torchvision==0.23.0+cu128 torchaudio==2.8.0+cu128`"
        `"xformers`" = `"xformers==0.0.32.post2`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU126_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU126
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.8.0 (CUDA 12.9)`"
        `"type`" = `"cu129`"
        `"supported`" = `"cu129`" -in `$supported_type
        `"torch`" = `"torch==2.8.0+cu129 torchvision==0.23.0+cu129 torchaudio==2.8.0+cu129`"
        # `"xformers`" = `"xformers==0.0.32.post2`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU129_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU129
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    # <<<<<<<<<< End
    return `$pytorch_list
}


# 列出 PyTorch 列表
function List-PyTorch (`$pytorch_list) {
    Print-Msg `"PyTorch 版本列表`"
    Write-Host `"-----------------------------------------------------`"
    Write-Host `"版本序号`" -ForegroundColor Yellow -NoNewline
    Write-Host `" | `" -NoNewline
    Write-Host `"PyTorch 版本`" -ForegroundColor White -NoNewline
    Write-Host `" | `" -NoNewline
    Write-Host `"支持当前设备情况`" -ForegroundColor Blue
    for (`$i = 0; `$i -lt `$pytorch_list.Count; `$i++) {
        `$pytorch_hashtables = `$pytorch_list[`$i]
        `$count += 1
        `$name = Get-HashValue -Hashtable `$pytorch_hashtables -Key `"name`"
        `$supported = Get-HashValue -Hashtable `$pytorch_hashtables -Key `"supported`"
        Write-Host `"- `${count}、`" -ForegroundColor Yellow -NoNewline
        Write-Host `"`$name `" -ForegroundColor White -NoNewline
        if (`$supported) {
            Write-Host `"(支持✓)`" -ForegroundColor Green
        } else {
            Write-Host `"(不支持×)`" -ForegroundColor Red
        }
    }
    Write-Host `"-----------------------------------------------------`"
}


function Main {
    Print-Msg `"初始化中`"
    Get-Fooocus-Installer-Version
    Get-Fooocus-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"Fooocus Installer 构建模式已启用, 跳过 Fooocus Installer 更新检查`"
    } else {
        Check-Fooocus-Installer-Update
    }
    Set-uv
    PyPI-Mirror-Status

    `$pytorch_list = Get-PyTorch-List
    `$go_to = 0
    `$to_exit = 0
    `$torch_ver = `"`"
    `$xformers_ver = `"`"
    `$cuda_support_ver = Get-Drive-Support-CUDA-Version
    `$current_torch_ver, `$current_xformers_ver = Get-PyTorch-And-xFormers-Version
    `$after_list_model_option = `"`"

    while (`$True) {
        switch (`$after_list_model_option) {
            display_input_error {
                Print-Msg `"输入有误, 请重试`"
            }
            Default {
                break
            }
        }
        `$after_list_model_option = `"`"
        List-PyTorch `$pytorch_list
        Print-Msg `"当前 PyTorch 版本: `$current_torch_ver`"
        Print-Msg `"当前 xFormers 版本: `$current_xformers_ver`"
        Print-Msg `"当前显卡驱动支持的最高 CUDA 版本: `$cuda_support_ver`"
        Print-Msg `"请选择 PyTorch 版本`"
        Print-Msg `"提示:`"
        Print-Msg `"1. PyTorch 版本通常来说选择最新版的即可`"
        Print-Msg `"2. 驱动支持的最高 CUDA 版本需要大于或等于要安装的 PyTorch 中所带的 CUDA 版本, 若驱动支持的最高 CUDA 版本低于要安装的 PyTorch 中所带的 CUDA 版本, 可尝试更新显卡驱动, 或者选择 CUDA 版本更低的 PyTorch`"
        Print-Msg `"3. 输入数字后回车, 或者输入 exit 退出 PyTorch 重装脚本`"
        if (`$BuildMode) {
            Print-Msg `"Fooocus Installer 构建已启用, 指定安装的 PyTorch 序号: `$BuildWithTorch`"
            `$arg = `$BuildWithTorch
            `$go_to = 1
        } else {
            `$arg = (Read-Host `"========================================>`").Trim()
        }

        switch (`$arg) {
            exit {
                Print-Msg `"退出 PyTorch 重装脚本`"
                `$to_exit = 1
                `$go_to = 1
            }
            Default {
                try {
                    # 检测输入是否符合列表
                    `$i = [int]`$arg
                    if (!((`$i -ge 1) -and (`$i -le `$pytorch_list.Count))) {
                        `$after_list_model_option = `"display_input_error`"
                        break
                    }

                    `$pytorch_info = `$pytorch_list[(`$i - 1)]
                    `$combination_name = Get-HashValue -Hashtable `$pytorch_info -Key `"name`"
                    `$torch_ver = Get-HashValue -Hashtable `$pytorch_info -Key `"torch`"
                    `$xformers_ver = Get-HashValue -Hashtable `$pytorch_info -Key `"xformers`"
                    `$index_mirror = Get-HashValue -Hashtable `$pytorch_info -Key `"index_mirror`"
                    `$extra_index_mirror = Get-HashValue -Hashtable `$pytorch_info -Key `"extra_index_mirror`"
                    `$find_links = Get-HashValue -Hashtable `$pytorch_info -Key `"find_links`"

                    if (`$null -ne `$index_mirror) {
                        `$Env:PIP_INDEX_URL = `$index_mirror
                        `$Env:UV_DEFAULT_INDEX = `$index_mirror
                    }
                    if (`$null -ne `$extra_index_mirror) {
                        `$Env:PIP_EXTRA_INDEX_URL = `$extra_index_mirror
                        `$Env:UV_INDEX = `$extra_index_mirror
                    }
                    if (`$null -ne `$find_links) {
                        `$Env:PIP_FIND_LINKS = `$find_links
                        `$Env:UV_FIND_LINKS = `$find_links
                    }
                }
                catch {
                    `$after_list_model_option = `"display_input_error`"
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
        `$use_force_reinstall = (Read-Host `"========================================>`").Trim()
    }

    if (`$use_force_reinstall -eq `"yes`" -or `$use_force_reinstall -eq `"y`" -or `$use_force_reinstall -eq `"YES`" -or `$use_force_reinstall -eq `"Y`") {
        `$force_reinstall_arg = `"--force-reinstall`"
        `$force_reinstall_status = `"启用`"
    } else {
        `$force_reinstall_arg = New-Object System.Collections.ArrayList
        `$force_reinstall_status = `"禁用`"
    }

    Print-Msg `"当前的选择: `$combination_name`"
    Print-Msg `"PyTorch: `$torch_ver`"
    Print-Msg `"xFormers: `$xformers_ver`"
    Print-Msg `"仅强制重装: `$force_reinstall_status`"
    Print-Msg `"是否确认安装?`"
    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
    if (`$BuildMode) {
        `$install_torch = `"yes`"
    } else {
        `$install_torch = (Read-Host `"========================================>`").Trim()
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
            if (!(`$BuildMode)) {
                Read-Host | Out-Null
            }
            exit 1
        }

        if (`$null -ne `$xformers_ver) {
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
                if (!(`$BuildMode)) {
                    Read-Host | Out-Null
                }
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
    [string]`$CorePrefix,
    [switch]`$BuildMode,
    [string]`$BuildWitchModel,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisableUpdate,
    [switch]`$DisableAutoApplyUpdate
)
& {
    `$prefix_list = @(`"core`", `"Fooocus`", `"fooocus`", `"fooocus_portable`")
    if ((Test-Path `"`$PSScriptRoot/core_prefix.txt`") -or (`$CorePrefix)) {
        if (`$CorePrefix) {
            `$origin_core_prefix = `$CorePrefix
        } else {
            `$origin_core_prefix = Get-Content `"`$PSScriptRoot/core_prefix.txt`"
        }
        `$origin_core_prefix = `$origin_core_prefix.Trim('/').Trim('\')
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix)) {
            `$to_path = `$origin_core_prefix
            `$from_uri = New-Object System.Uri(`$PSScriptRoot.Replace('\', '/') + '/')
            `$to_uri = New-Object System.Uri(`$to_path.Replace('\', '/'))
            `$origin_core_prefix = `$from_uri.MakeRelativeUri(`$to_uri).ToString().Trim('/')
        }
        `$Env:CORE_PREFIX = `$origin_core_prefix
        return
    }
    ForEach (`$i in `$prefix_list) {
        if (Test-Path `"`$PSScriptRoot/`$i`") {
            `$Env:CORE_PREFIX = `$i
            return
        }
    }
    `$Env:CORE_PREFIX = `"core`"
}
# Fooocus Installer 版本和检查更新间隔
`$FOOOCUS_INSTALLER_VERSION = $FOOOCUS_INSTALLER_VERSION
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
`$PIP_EXTRA_INDEX_MIRROR_CPU = `"$PIP_EXTRA_INDEX_MIRROR_CPU`"
`$PIP_EXTRA_INDEX_MIRROR_XPU = `"$PIP_EXTRA_INDEX_MIRROR_XPU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118 = `"$PIP_EXTRA_INDEX_MIRROR_CU118`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
`$PIP_EXTRA_INDEX_MIRROR_CU126 = `"$PIP_EXTRA_INDEX_MIRROR_CU126`"
`$PIP_EXTRA_INDEX_MIRROR_CU128 = `"$PIP_EXTRA_INDEX_MIRROR_CU128`"
`$PIP_EXTRA_INDEX_MIRROR_CU129 = `"$PIP_EXTRA_INDEX_MIRROR_CU129`"
`$PIP_EXTRA_INDEX_MIRROR_CPU_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CPU_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_XPU_NJU = `"$PIP_EXTRA_INDEX_MIRROR_XPU_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU118_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU121_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU121_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU124_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU126_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU128_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU129_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU129_NJU`"
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# Aria2 最低版本
`$ARIA2_MINIMUM_VER = `"$ARIA2_MINIMUM_VER`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/git/bin`"
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
function Get-Fooocus-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-BuildWitchModel <模型编号列表>] [-DisablePyPIMirror] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableUpdate] [-DisableAutoApplyUpdate]

参数:
    -Help
        获取 Fooocus Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -BuildMode
        启用 Fooocus Installer 构建模式

    -BuildWitchModel <模型编号列表>
        (需添加 -BuildMode 启用 Fooocus Installer 构建模式) Fooocus Installer 执行完基础安装流程后调用 Fooocus Installer 的 download_models.ps1 脚本, 根据模型编号列表下载指定的模型
        模型编号可运行 download_models.ps1 脚本进行查看

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableProxy
        禁用 Fooocus Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableUpdate
        禁用 Fooocus Installer 更新检查

    -DisableAutoApplyUpdate
        禁用 Fooocus Installer 自动应用新版本更新


更多的帮助信息请阅读 Fooocus Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[Fooocus Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# 获取内核路径前缀状态
function Get-Core-Prefix-Status {
    if ((Test-Path `"`$PSScriptRoot/core_prefix.txt`") -or (`$CorePrefix)) {
        Print-Msg `"检测到 core_prefix.txt 配置文件 / -CorePrefix 命令行参数, 使用自定义内核路径前缀`"
        if (`$CorePrefix) {
            `$origin_core_prefix = `$CorePrefix
        } else {
            `$origin_core_prefix = Get-Content `"`$PSScriptRoot/core_prefix.txt`"
        }
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix.Trim('/').Trim('\'))) {
            Print-Msg `"转换绝对路径为内核路径前缀: `$origin_core_prefix -> `$Env:CORE_PREFIX`"
        }
    }
    Print-Msg `"当前内核路径前缀: `$Env:CORE_PREFIX`"
    Print-Msg `"完整内核路径: `$PSScriptRoot\`$Env:CORE_PREFIX`"
}


# 显示 Fooocus Installer 版本
function Get-Fooocus-Installer-Version {
    `$ver = `$([string]`$FOOOCUS_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"Fooocus Installer 版本: v`${major}.`${minor}.`${micro}`"
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


# Fooocus Installer 更新检测
function Check-Fooocus-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/fooocus_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/fooocus_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/fooocus_installer/fooocus_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/fooocus_installer/fooocus_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/fooocus_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 Fooocus Installer 的自动检查更新功能`"
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
        Print-Msg `"检查 Fooocus Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/fooocus_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/fooocus_installer.ps1`" |
                Select-String -Pattern `"FOOOCUS_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 Fooocus Installer 更新中`"
            } else {
                Print-Msg `"检查 Fooocus Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -le `$FOOOCUS_INSTALLER_VERSION) {
        Print-Msg `"Fooocus Installer 已是最新版本`"
        return
    }

    if ((`$DisableAutoApplyUpdate) -or (Test-Path `"`$PSScriptRoot/disable_auto_apply_update.txt`")) {
        Print-Msg `"检测到 Fooocus Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"========================================>`").Trim()
        if (!(`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`")) {
            Print-Msg `"跳过 Fooocus Installer 更新`"
            return
        }
    } else {
        Print-Msg `"检测到 Fooocus Installer 有新版本可用`"
    }

    Print-Msg `"调用 Fooocus Installer 进行更新中`"
    . `"`$Env:CACHE_HOME/fooocus_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
    `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
    Print-Msg `"更新结束, 重新启动 Fooocus Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
    Invoke-Expression `"& ```"`$PSCommandPath```" `$raw_params`"
    exit 0
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
    version1 = str(version1)
    version2 = str(version2)
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

    if ((Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX/git/bin/aria2c.exe`") -or (Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX/git/bin/git.exe`")) {
        Move-Item -Path `"`$Env:CACHE_HOME/aria2c.exe`" -Destination `"`$PSScriptRoot/`$Env:CORE_PREFIX/git/bin/aria2c.exe`" -Force
    } elseif ((Test-Path `"`$PSScriptRoot/git/bin/aria2c.exe`") -or (Test-Path `"`$PSScriptRoot/git/bin/git.exe`")) {
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
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/nai1-artist_all_in_one_merge.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/Counterfeit-V3.0_fp16.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/cetusMix_Whalefall2.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/cuteyukimixAdorable_neochapter3.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/ekmix-pastel-fp16-no-ema.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/ex2K_sse2.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/kohakuV5_rev2.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/meinamix_meinaV11.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/oukaStar_10.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/pastelMixStylizedAnime_pastelMixPrunedFP16.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/rabbit_v6.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/sweetSugarSyndrome_rev15.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/AnythingV5Ink_ink.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/bartstyledbBlueArchiveArtStyleFineTunedModel_v10.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/meinapastel_v6Pastel.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/qteamixQ_omegaFp16.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/tmndMix_tmndMixSPRAINBOW.safetensors`", `"SD 1.5`", `"checkpoints`")) | Out-Null
    # SD 2.1
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_2.1/v2-1_768-ema-pruned.safetensors`", `"SD 2.1`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_2.1/wd-1-4-anime_e2.ckpt`", `"SD 2.1`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_2.1/wd-mofu-fp16.safetensors`", `"SD 2.1`", `"checkpoints`")) | Out-Null
    # SDXL
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-lora/resolve/master/sdxl/sd_xl_offset_example-lora_1.0.safetensors`", `"SDXL`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/sd_xl_base_1.0_0.9vae.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/sd_xl_refiner_1.0_0.9vae.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/sd_xl_turbo_1.0_fp16.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/cosxl.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/cosxl_edit.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
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
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/ponyDiffusionV6XL_v6StartWithThisOne.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/pdForAnime_v20.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/tPonynai3_v51WeightOptimized.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/omegaPonyXLAnime_v20.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/animeIllustDiffusion_v061.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/artiwaifuDiffusion_v10.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/artiwaifu-diffusion-v2.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/AnythingXL_xl.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/abyssorangeXLElse_v10.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/animaPencilXL_v200.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/bluePencilXL_v401.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/nekorayxl_v06W3.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/CounterfeitXL-V1.0.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
    # SD 3
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/sd3_medium.safetensors`", `"SD 3`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/sd3_medium_incl_clips.safetensors`", `"SD 3`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/sd3_medium_incl_clips_t5xxlfp8.safetensors`", `"SD 3`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/sd3.5_large.safetensors`", `"SD 3`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/sd3.5_large_fp8_scaled.safetensors`", `"SD 3`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/sd3.5_large_turbo.safetensors`", `"SD 3`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/sd3.5_medium.safetensors`", `"SD 3`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/sd3.5_medium_incl_clips_t5xxlfp8scaled.safetensors`", `"SD 3`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/emi3.safetensors`", `"SD 3`", `"checkpoints`")) | Out-Null
    # SD 3 Text Encoder
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/text_encoders/clip_g.safetensors`", `"SD 3 Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/text_encoders/clip_l.safetensors`", `"SD 3 Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/text_encoders/t5xxl_fp16.safetensors`", `"SD 3 Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/text_encoders/t5xxl_fp8_e4m3fn.safetensors`", `"SD 3 Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors`", `"SD 3 Text Encoder`", `"clip`")) | Out-Null
    # HunyuanDiT
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/comfyui-extension-models/resolve/master/hunyuan_dit_comfyui/hunyuan_dit_1.2.safetensors`", `"HunyuanDiT`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/comfyui-extension-models/resolve/master/hunyuan_dit_comfyui/comfy_freeway_animation_hunyuan_dit_180w.safetensors`", `"HunyuanDiT`", `"checkpoints`")) | Out-Null
    # FLUX
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev.safetensors`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-fp8.safetensors`", `"FLUX`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux_dev_fp8_scaled_diffusion_model.safetensors`", `"FLUX`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-bnb-nf4-v2.safetensors`", `"FLUX`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-bnb-nf4.safetensors`", `"FLUX`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q2_K.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q3_K_S.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q4_0.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q4_1.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q4_K_S.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q5_0.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q5_1.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q5_K_S.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q6_K.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q8_0.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-F16.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell.safetensors`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-fp8.safetensors`", `"FLUX`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q2_K.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q3_K_S.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q4_0.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q4_1.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q4_K_S.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q5_0.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q5_1.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q5_K_S.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q6_K.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q8_0.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-F16.gguf`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/ashen0209-flux1-dev2pro.safetensors`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/jimmycarter-LibreFLUX.safetensors`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/nyanko7-flux-dev-de-distill.safetensors`", `"FLUX`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/shuttle-3-diffusion.safetensors`", `"FLUX`", `"unet`")) | Out-Null
    # FLUX Text Encoder
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/clip_l.safetensors`", `"FLUX Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5xxl_fp16.safetensors`", `"FLUX Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5xxl_fp8_e4m3fn.safetensors`", `"FLUX Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q3_K_L.gguf`", `"FLUX Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q3_K_M.gguf`", `"FLUX Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q3_K_S.gguf`", `"FLUX Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q4_K_M.gguf`", `"FLUX Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q4_K_S.gguf`", `"FLUX Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q5_K_M.gguf`", `"FLUX Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q5_K_S.gguf`", `"FLUX Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q6_K.gguf`", `"FLUX Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q8_0.gguf`", `"FLUX Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-f16.gguf`", `"FLUX Text Encoder`", `"clip`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-f32.gguf`", `"FLUX Text Encoder`", `"clip`")) | Out-Null
    # FLUX VAE
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_vae/ae.safetensors`", `"FLUX VAE`", `"vae`")) | Out-Null
    # SD 1.5 VAE
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sd_1.5/vae-ft-ema-560000-ema-pruned.safetensors`", `"SD 1.5 VAE`", `"vae`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sd_1.5/vae-ft-mse-840000-ema-pruned.safetensors`", `"SD 1.5 VAE`", `"vae`")) | Out-Null
    # SDXL VAE
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sdxl_1.0/sdxl_vae.safetensors`", `"SDXL VAE`", `"vae`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sdxl_1.0/sdxl_fp16_fix_vae.safetensors`", `"SDXL VAE`", `"vae`")) | Out-Null
    # VAE approx
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-vae/resolve/master/vae-approx/model.pt`", `"VAE approx`", `"vae_approx`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-vae/resolve/master/vae-approx/vaeapprox-sdxl.pt`", `"VAE approx`", `"vae_approx`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-vae/resolve/master/vae-approx/vaeapprox-sd3.pt`", `"VAE approx`", `"vae_approx`")) | Out-Null
    # Upscale
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/Codeformer/codeformer-v0.1.0.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/DAT/DAT_2_x2.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/DAT/DAT_2_x3.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/DAT/DAT_2_x4.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/DAT/DAT_S_x2.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/DAT/DAT_S_x3.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/DAT/DAT_S_x4.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/DAT/DAT_light_x2.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/DAT/DAT_light_x3.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/DAT/DAT_light_x4.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/DAT/DAT_x2.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/DAT/DAT_x3.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/DAT/DAT_x4.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/16xPSNR.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/1x-ITF-SkinDiffDetail-Lite-v1.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/1x_NMKD-BrightenRedux_200k.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/1x_NMKD-YandereInpaint_375000_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/1x_NMKDDetoon_97500_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/1x_NoiseToner-Poisson-Detailed_108000_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/1x_NoiseToner-Uniform-Detailed_100000_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4x-UltraSharp.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4xPSNR.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4x_CountryRoads_377000_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4x_Fatality_Comix_260000_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4x_NMKD-Siax_200k.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4x_NMKD-Superscale-Artisoftject_210000_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4x_NMKD-Superscale-SP_178000_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4x_NMKD-UltraYandere-Lite_280k.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4x_NMKD-UltraYandere_300k.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4x_NMKD-YandereNeoXL_200k.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4x_NMKDSuperscale_Artisoft_120000_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4x_NickelbackFS_72000_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4x_Nickelback_70000G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4x_RealisticRescaler_100000_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4x_Valar_v1.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4x_fatal_Anime_500000_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/4x_foolhardy_Remacri.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/8xPSNR.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/8x_NMKD-Superscale_150000_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/8x_NMKD-Typescale_175k.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/A_ESRGAN_Single.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/BSRGAN.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/BSRGANx2.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/BSRNet.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/ESRGAN_4x.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/LADDIER1_282500_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/UniversalUpscaler/4x_UniversalUpscalerV2-Neutral_115000_swaG.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/UniversalUpscaler/4x_UniversalUpscalerV2-Sharp_101000_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/UniversalUpscaler/4x_UniversalUpscalerV2-Sharper_103000_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/UniversalUpscaler/Legacy/4x_UniversalUpscaler-Detailed_155000_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/UniversalUpscaler/Legacy/4x_UniversalUpscaler-Soft_190000_G.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/WaifuGAN_v3_30000.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/lollypop.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/ESRGAN/sudo_rife4_269.662_testV1_scale1.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/GFPGAN/GFPGANv1.3.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/GFPGAN/GFPGANv1.4.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/GFPGAN/detection_Resnet50_Final.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/GFPGAN/parsing_bisenet.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/GFPGAN/parsing_parsenet.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/RealESRGAN/RealESRGAN_x4plus.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/RealESRGAN/RealESRGAN_x4plus_anime_6B.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/SwinIR/001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/SwinIR/001_classicalSR_DF2K_s64w8_SwinIR-M_x3.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/SwinIR/001_classicalSR_DF2K_s64w8_SwinIR-M_x4.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/SwinIR/001_classicalSR_DF2K_s64w8_SwinIR-M_x8.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/SwinIR/001_classicalSR_DIV2K_s48w8_SwinIR-M_x2.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/SwinIR/001_classicalSR_DIV2K_s48w8_SwinIR-M_x3.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/SwinIR/001_classicalSR_DIV2K_s48w8_SwinIR-M_x4.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/SwinIR/001_classicalSR_DIV2K_s48w8_SwinIR-M_x8.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/SwinIR/003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN-with-dict-keys-params-and-params_ema.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/SwinIR/003_realSR_BSRGAN_DFO_s64w8_SwinIR-M_x2_GAN-with-dict-keys-params-and-params_ema.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/SwinIR/Swin2SR_ClassicalSR_X2_64.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/SwinIR/Swin2SR_ClassicalSR_X4_64.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/SwinIR/Swin2SR_CompressedSR_X4_48.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/SwinIR/Swin2SR_RealworldSR_X4_64_BSRGAN_PSNR.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-upscaler-models/resolve/master/SwinIR/SwinIR_4x.pth`", `"Upscale`", `"upscale_models`")) | Out-Null
    # Embedding
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-embeddings/resolve/master/sd_1.5/EasyNegativeV2.safetensors`", `"Embedding`", `"embeddings`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-embeddings/resolve/master/sd_1.5/bad-artist-anime.pt`", `"Embedding`", `"embeddings`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-embeddings/resolve/master/sd_1.5/bad-artist.pt`", `"Embedding`", `"embeddings`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-embeddings/resolve/master/sd_1.5/bad-hands-5.pt`", `"Embedding`", `"embeddings`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-embeddings/resolve/master/sd_1.5/bad-image-v2-39000.pt`", `"Embedding`", `"embeddings`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-embeddings/resolve/master/sd_1.5/bad_prompt_version2.pt`", `"Embedding`", `"embeddings`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-embeddings/resolve/master/sd_1.5/ng_deepnegative_v1_75t.pt`", `"Embedding`", `"embeddings`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-embeddings/resolve/master/sd_1.5/verybadimagenegative_v1.3.pt`", `"Embedding`", `"embeddings`")) | Out-Null
    # SD 1.5 ControlNet
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v11e_sd15_ip2p_fp16.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v11e_sd15_shuffle_fp16.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v11f1e_sd15_tile_fp16.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v11f1p_sd15_depth_fp16.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v11p_sd15_canny_fp16.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v11p_sd15_inpaint_fp16.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v11p_sd15_lineart_fp16.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v11p_sd15_mlsd_fp16.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v11p_sd15_normalbae_fp16.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v11p_sd15_openpose_fp16.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v11p_sd15_scribble_fp16.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v11p_sd15_seg_fp16.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v11p_sd15_softedge_fp16.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v11p_sd15s2_lineart_anime_fp16.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v1p_sd15_brightness.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v1p_sd15_illumination.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/control_v1p_sd15_qrcode_monster.safetensors`", `"SD 1.5 ControlNet`", `"controlnet`")) | Out-Null
    # SDXL ControlNet
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/monster-labs-control_v1p_sdxl_qrcode_monster.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/mistoLine_fp16.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/destitech-controlnet-inpaint-dreamer-sdxl.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/control-lora/resolve/master/control-lora-recolor-rank128-sdxl.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/xinsir-controlnet-union-sdxl-1.0-promax.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/kohakuXLControlnet_canny.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/animagineXL40_canny.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLCanny_v10.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLLineart_v10.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLDepth_v10.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLSoftedge_v10.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLLineartRrealistic_v10.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLShuffle_v10.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLOpenPose_v10.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLTile_v10.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLv0.1_inpainting_fp16.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLv1.1_canny_fp16.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLv1.1_depth_midas_fp16.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLv1.1_inpainting_fp16.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLv1.1_tile_fp16.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/noobaiXLControlnet_epsCanny.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/noobaiXLControlnet_epsDepthMidas.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/noobaiXLControlnet_epsLineartAnime.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/noobaiXLControlnet_epsNormalMidas.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/noobaiXLControlnet_epsSoftedgeHed.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/noobaiXLControlnet_epsMangaLine.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/noobaiXLControlnet_epsLineartRealistic.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/noobaiXLControlnet_epsDepthMidasV11.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/noobaiXLControlnet_epsScribbleHed.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/noobaiXLControlnet_epsScribblePidinet.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/noobaiXLControlnet_openposeModel.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/noobaiXLControlnet_epsTile.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/NoobAI_Inpainting_ControlNet.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    # SD 3.5 ControlNet
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd3_controlnet/resolve/master/sd3.5_large_controlnet_blur.safetensors`", `"SD 3.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd3_controlnet/resolve/master/sd3.5_large_controlnet_canny.safetensors`", `"SD 3.5 ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd3_controlnet/resolve/master/sd3.5_large_controlnet_depth.safetensors`", `"SD 3.5 ControlNet`", `"controlnet`")) | Out-Null
    # FLUX ControlNet
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-redux-dev.safetensors`", `"FLUX ControlNet`", `"style_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev.safetensors`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q3_K_S.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q4_0.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q4_1.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q4_K_S.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q5_0.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q5_1.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q5_K_S.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q6_K.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q8_0.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-fp16-F16-GGUF.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-fp16-Q4_0-GGUF.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-fp16-Q5_0-GGUF.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-fp16-Q8_0-GGUF.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-lora-rank128.safetensors`", `"FLUX ControlNet`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-lora-rank256.safetensors`", `"FLUX ControlNet`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-lora-rank32.safetensors`", `"FLUX ControlNet`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-lora-rank4.safetensors`", `"FLUX ControlNet`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-lora-rank64.safetensors`", `"FLUX ControlNet`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-lora-rank8.safetensors`", `"FLUX ControlNet`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-canny-dev-lora.safetensors`", `"FLUX ControlNet`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-canny-dev.safetensors`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-canny-dev-fp16-F16-GGUF.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-canny-dev-fp16-Q4_0-GGUF.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-canny-dev-fp16-Q5_0-GGUF.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-canny-dev-fp16-Q8_0-GGUF.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-depth-dev-fp16-F16-GGUF.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-depth-dev-fp16-Q4_0-GGUF.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-depth-dev-fp16-Q5_0-GGUF.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-depth-dev-fp16-Q8_0-GGUF.gguf`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-depth-dev-lora.safetensors`", `"FLUX ControlNet`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-depth-dev.safetensors`", `"FLUX ControlNet`", `"unet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-xlabs-canny-controlnet-v3.safetensors`", `"FLUX ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-xlabs-depth-controlnet-v3.safetensors`", `"FLUX ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-xlabs-hed-controlnet-v3.safetensors`", `"FLUX ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-dev-jasperai-Controlnet-Depth.safetensors`", `"FLUX ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-dev-jasperai-Controlnet-Surface-Normals.safetensors`", `"FLUX ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-dev-jasperai-Controlnet-Upscaler.safetensors`", `"FLUX ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-dev-instantx-controlnet-union.safetensors`", `"FLUX ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-dev-mistoline.safetensors`", `"FLUX ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-dev-shakker-labs-controlnet-union-pro.safetensors`", `"FLUX ControlNet`", `"controlnet`")) | Out-Null
    # CLIP Vision
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1_annotator/resolve/master/clip_vision/clip_g.pth`", `"CLIP Vision`", `"clip_vision`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1_annotator/resolve/master/clip_vision/clip_h.pth`", `"CLIP Vision`", `"clip_vision`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1_annotator/resolve/master/clip_vision/clip_vitl.pth`", `"CLIP Vision`", `"clip_vision`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/sigclip_vision_patch14_384.safetensors`", `"CLIP Vision`", `"clip_vision`")) | Out-Null
    # IP Adapter
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/ip-adapter_sd15.pth`", `"SD 1.5 IP Adapter`", `"ipadapter`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/ip-adapter_sd15_light.pth`", `"SD 1.5 IP Adapter`", `"ipadapter`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/ip-adapter_sd15_plus.pth`", `"SD 1.5 IP Adapter`", `"ipadapter`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/ip-adapter_sd15_vit-G.safetensors`", `"SD 1.5 IP Adapter`", `"ipadapter`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/ip-adapter-plus_sdxl_vit-h.safetensors`", `"SDXL IP Adapter`", `"ipadapter`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/ip-adapter_sdxl.safetensors`", `"SDXL IP Adapter`", `"ipadapter`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/ip-adapter_sdxl_vit-h.safetensors`", `"SDXL IP Adapter`", `"ipadapter`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/controlnet_v1.1/resolve/master/noobIPAMARK1_mark1.safetensors`", `"SDXL IP Adapter`", `"ipadapter`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-xlabs-ip-adapter.safetensors`", `"FLUX IP Adapter`", `"controlnet`")) | Out-Null
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
    return (Read-Host `"========================================>`").Trim()
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
    Get-Fooocus-Installer-Version
    Get-Fooocus-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"Fooocus Installer 构建模式已启用, 跳过 Fooocus Installer 更新检查`"
    } else {
        Check-Fooocus-Installer-Update
    }
    Check-Aria2-Version

    if (!(Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX`")) {
        Print-Msg `"内核路径 `$PSScriptRoot\`$Env:CORE_PREFIX 未找到, 请检查 Fooocus 是否已正确安装, 或者尝试运行 Fooocus Installer 进行修复`"
        Read-Host | Out-Null
        return
    }

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
                        `$path = `"`$PSScriptRoot/`$Env:CORE_PREFIX/models/`$(`$content[2])`" # 模型放置路径
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


# Fooocus Installer 设置脚本
function Write-Fooocus-Installer-Settings-Script {
    $content = "
param (
    [switch]`$Help,
    [string]`$CorePrefix,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy
)
& {
    `$prefix_list = @(`"core`", `"Fooocus`", `"fooocus`", `"fooocus_portable`")
    if ((Test-Path `"`$PSScriptRoot/core_prefix.txt`") -or (`$CorePrefix)) {
        if (`$CorePrefix) {
            `$origin_core_prefix = `$CorePrefix
        } else {
            `$origin_core_prefix = Get-Content `"`$PSScriptRoot/core_prefix.txt`"
        }
        `$origin_core_prefix = `$origin_core_prefix.Trim('/').Trim('\')
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix)) {
            `$to_path = `$origin_core_prefix
            `$from_uri = New-Object System.Uri(`$PSScriptRoot.Replace('\', '/') + '/')
            `$to_uri = New-Object System.Uri(`$to_path.Replace('\', '/'))
            `$origin_core_prefix = `$from_uri.MakeRelativeUri(`$to_uri).ToString().Trim('/')
        }
        `$Env:CORE_PREFIX = `$origin_core_prefix
        return
    }
    ForEach (`$i in `$prefix_list) {
        if (Test-Path `"`$PSScriptRoot/`$i`") {
            `$Env:CORE_PREFIX = `$i
            return
        }
    }
    `$Env:CORE_PREFIX = `"core`"
}
# Fooocus Installer 版本和检查更新间隔
`$FOOOCUS_INSTALLER_VERSION = $FOOOCUS_INSTALLER_VERSION
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
`$PIP_EXTRA_INDEX_MIRROR_CPU = `"$PIP_EXTRA_INDEX_MIRROR_CPU`"
`$PIP_EXTRA_INDEX_MIRROR_XPU = `"$PIP_EXTRA_INDEX_MIRROR_XPU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118 = `"$PIP_EXTRA_INDEX_MIRROR_CU118`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
`$PIP_EXTRA_INDEX_MIRROR_CU126 = `"$PIP_EXTRA_INDEX_MIRROR_CU126`"
`$PIP_EXTRA_INDEX_MIRROR_CU128 = `"$PIP_EXTRA_INDEX_MIRROR_CU128`"
`$PIP_EXTRA_INDEX_MIRROR_CU129 = `"$PIP_EXTRA_INDEX_MIRROR_CU129`"
`$PIP_EXTRA_INDEX_MIRROR_CPU_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CPU_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_XPU_NJU = `"$PIP_EXTRA_INDEX_MIRROR_XPU_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU118_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU121_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU121_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU124_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU126_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU128_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU129_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU129_NJU`"
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# Aria2 最低版本
`$ARIA2_MINIMUM_VER = `"$ARIA2_MINIMUM_VER`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/git/bin`"
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
function Get-Fooocus-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-DisablePyPIMirror] [-DisableProxy] [-UseCustomProxy <代理服务器地址>]

参数:
    -Help
        获取 Fooocus Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableProxy
        禁用 Fooocus Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址


更多的帮助信息请阅读 Fooocus Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[Fooocus Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# 获取内核路径前缀状态
function Get-Core-Prefix-Status {
    if ((Test-Path `"`$PSScriptRoot/core_prefix.txt`") -or (`$CorePrefix)) {
        Print-Msg `"检测到 core_prefix.txt 配置文件 / -CorePrefix 命令行参数, 使用自定义内核路径前缀`"
        if (`$CorePrefix) {
            `$origin_core_prefix = `$CorePrefix
        } else {
            `$origin_core_prefix = Get-Content `"`$PSScriptRoot/core_prefix.txt`"
        }
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix.Trim('/').Trim('\'))) {
            Print-Msg `"转换绝对路径为内核路径前缀: `$origin_core_prefix -> `$Env:CORE_PREFIX`"
        }
    }
    Print-Msg `"当前内核路径前缀: `$Env:CORE_PREFIX`"
    Print-Msg `"完整内核路径: `$PSScriptRoot\`$Env:CORE_PREFIX`"
}


# 显示 Fooocus Installer 版本
function Get-Fooocus-Installer-Version {
    `$ver = `$([string]`$FOOOCUS_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"Fooocus Installer 版本: v`${major}.`${minor}.`${micro}`"
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


# 获取 Fooocus Installer 自动检测更新设置
function Get-Fooocus-Installer-Auto-Check-Update-Setting {
    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        return `"禁用`"
    } else {
        return `"启用`"
    }
}


# 获取 Fooocus Installer 自动应用更新设置
function Get-Fooocus-Installer-Auto-Apply-Update-Setting {
    if (Test-Path `"`$PSScriptRoot/disable_auto_apply_update.txt`") {
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


# 获取 PyPI 镜像源配置
function Get-PyPI-Mirror-Setting {
    if (!(Test-Path `"`$PSScriptRoot/disable_pypi_mirror.txt`")) {
        return `"启用`"
    } else {
        return `"禁用`"
    }
}


# 获取 Fooocus 运行环境检测配置
function Get-Fooocus-Env-Check-Setting {
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


# 获取路径前缀设置
function Get-Core-Prefix-Setting {
    if (Test-Path `"`$PSScriptRoot/core_prefix.txt`") {
        return `"自定义 (使用自定义路径前缀: `$(Get-Content `"`$PSScriptRoot/core_prefix.txt`"))`"
    } else {
        return `"自动`"
    }
}


# 获取用户输入
function Get-User-Input {
    return (Read-Host `"========================================>`").Trim()
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
                Print-Msg `"启用 Github 镜像成功, 在更新 Fooocus 时将自动检测可用的 Github 镜像源并使用`"
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


# Fooocus Installer 自动检查更新设置
function Update-Fooocus-Installer-Auto-Check-Update-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 Fooocus Installer 自动检测更新设置: `$(Get-Fooocus-Installer-Auto-Check-Update-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 Fooocus Installer 自动更新检查`"
        Print-Msg `"2. 禁用 Fooocus Installer 自动更新检查`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"
        Print-Msg `"警告: 当 Fooocus Installer 有重要更新(如功能性修复)时, 禁用自动更新检查后将得不到及时提示`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_update.txt`" -Force -Recurse 2> `$null
                Print-Msg `"启用 Fooocus Installer 自动更新检查成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_update.txt`" -Force > `$null
                Print-Msg `"禁用 Fooocus Installer 自动更新检查成功`"
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


# Fooocus Installer 自动应用更新设置
function Update-Fooocus-Installer-Auto-Apply-Update-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 Fooocus Installer 自动应用更新设置: `$(Get-Fooocus-Installer-Auto-Apply-Update-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 Fooocus Installer 自动应用更新`"
        Print-Msg `"2. 禁用 Fooocus Installer 自动应用更新`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_auto_apply_update.txt`" -Force -Recurse 2> `$null
                Print-Msg `"启用 Fooocus Installer 自动应用更新成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_auto_apply_update.txt`" -Force > `$null
                Print-Msg `"禁用 Fooocus Installer 自动应用更新成功`"
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


# Fooocus 启动参数设置
function Update-Fooocus-Launch-Args-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 Fooocus 启动参数: `$(Get-Launch-Args-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 设置 Fooocus 启动参数`"
        Print-Msg `"2. 删除 Fooocus 启动参数`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Print-Msg `"请输入 Fooocus 启动参数`"
                Print-Msg `"提示: 保存启动参数后原有的启动参数将被覆盖, Fooocus 可用的启动参数可阅读: https://github.com/lllyasviel/Fooocus?tab=readme-ov-file#all-cmd-flags`"
                Print-Msg `"输入启动参数后回车保存`"
                `$fooocus_launch_args = Get-User-Input
                Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/launch_args.txt`" -Value `$fooocus_launch_args
                Print-Msg `"设置 Fooocus 启动参数成功, 使用的 Fooocus 启动参数为: `$fooocus_launch_args`"
                break
            }
            2 {
                Remove-Item -Path `"`$PSScriptRoot/launch_args.txt`" -Force -Recurse 2> `$null
                Print-Msg `"删除 Fooocus 启动参数成功`"
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


# 自动创建 Fooocus 快捷启动方式设置
function Auto-Set-Launch-Shortcut-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前自动创建 Fooocus 快捷启动方式设置: `$(Get-Auto-Set-Launch-Shortcut-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用自动创建 Fooocus 快捷启动方式`"
        Print-Msg `"2. 禁用自动创建 Fooocus 快捷启动方式`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/enable_shortcut.txt`" -Force > `$null
                Print-Msg `"启用自动创建 Fooocus 快捷启动方式成功`"
                break
            }
            2 {
                Remove-Item -Path `"`$PSScriptRoot/enable_shortcut.txt`" -Force -Recurse 2> `$null
                Print-Msg `"禁用自动创建 Fooocus 快捷启动方式成功`"
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


# Fooocus 运行环境检测设置
function Fooocus-Env-Check-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 Fooocus 运行环境检测设置: `$(Get-Fooocus-Env-Check-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 Fooocus 运行环境检测`"
        Print-Msg `"2. 禁用 Fooocus 运行环境检测`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_check_env.txt`" -Force -Recurse 2> `$null
                Print-Msg `"启用 Fooocus 运行环境检测成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_check_env.txt`" -Force > `$null
                Print-Msg `"禁用 Fooocus 运行环境检测成功`"
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


# 内核路径前缀设置
function Update-Core-Prefix-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前内核路径前缀设置: `$(Get-Core-Prefix-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 配置自定义路径前缀`"
        Print-Msg `"2. 启用自动选择路径前缀`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Print-Msg `"请输入自定义内核路径前缀`"
                Print-Msg `"提示: 路径前缀为内核在当前脚本目录中的名字 (也可以通过绝对路径指定当前脚本目录外的内核), 输入后回车保存`"
                `$custom_core_prefix = Get-User-Input
                `$origin_path = `$origin_core_prefix
                `$origin_core_prefix = `$origin_core_prefix.Trim('/').Trim('\')
                if ([System.IO.Path]::IsPathRooted(`$custom_core_prefix)) {
                    Print-Msg `"将绝对路径转换为内核路径前缀中`"
                    `$from_path = `$PSScriptRoot
                    `$to_path = `$custom_core_prefix
                    `$from_uri = New-Object System.Uri(`$from_path.Replace('\', '/') + '/')
                    `$to_uri = New-Object System.Uri(`$to_path.Replace('\', '/'))
                    `$custom_core_prefix = `$from_uri.MakeRelativeUri(`$to_uri).ToString().Trim('/')
                    Print-Msg `"`$origin_path -> `$custom_core_prefix`"
                }
                Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/core_prefix.txt`" -Value `$custom_core_prefix
                Print-Msg `"自定义内核路径前缀成功, 使用的路径前缀为: `$custom_core_prefix`"
                break
            }
            2 {
                Remove-Item -Path `"`$PSScriptRoot/core_prefix.txt`" -Force -Recurse 2> `$null
                Print-Msg `"启用自动选择内核路径前缀成功`"
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


# 检查 Fooocus Installer 更新
function Check-Fooocus-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/fooocus_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/fooocus_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/fooocus_installer/fooocus_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/fooocus_installer/fooocus_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/fooocus_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null
    Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间

    ForEach (`$url in `$urls) {
        Print-Msg `"检查 Fooocus Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/fooocus_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/fooocus_installer.ps1`" |
                Select-String -Pattern `"FOOOCUS_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 Fooocus Installer 更新中`"
            } else {
                Print-Msg `"检查 Fooocus Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -gt `$FOOOCUS_INSTALLER_VERSION) {
        Print-Msg `"Fooocus Installer 有新版本可用`"
        Print-Msg `"调用 Fooocus Installer 进行更新中`"
        . `"`$Env:CACHE_HOME/fooocus_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
        `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
        Print-Msg `"更新结束, 重新启动 Fooocus Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
        Invoke-Expression `"& ```"`$PSCommandPath```" `$raw_params`"
        exit 0
    } else {
        Print-Msg `"Fooocus Installer 已是最新版本`"
    }
}


# 检查环境完整性
function Check-Env {
    Print-Msg `"检查环境完整性中`"
    `$broken = 0
    if ((Test-Path `"`$PSScriptRoot/python/python.exe`") -or (Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX/python/python.exe`")) {
        `$python_status = `"已安装`"
    } else {
        `$python_status = `"未安装`"
        `$broken = 1
    }

    if ((Test-Path `"`$PSScriptRoot/git/bin/git.exe`") -or (Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX/git/bin/git.exe`")) {
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

    if ((Test-Path `"`$PSScriptRoot/git/bin/aria2c.exe`") -or (Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX/git/bin/aria2c.exe`")) {
        `$aria2_status = `"已安装`"
    } else {
        `$aria2_status = `"未安装`"
        `$broken = 1
    }

    if (Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX/launch.py`") {
        `$fooocus_status = `"已安装`"
    } else {
        `$fooocus_status = `"未安装`"
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
    Print-Msg `"Fooocus: `$fooocus_status`"
    Print-Msg `"-----------------------------------------------------`"
    if (`$broken -eq 1) {
        Print-Msg `"检测到环境出现组件缺失, 可尝试运行 Fooocus Installer 进行安装`"
    } else {
        Print-Msg `"当前环境无缺失组件`"
    }
}


# 查看 Fooocus Installer 文档
function Get-Fooocus-Installer-Help-Docs {
    Print-Msg `"调用浏览器打开 Fooocus Installer 文档中`"
    Start-Process `"https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md`"
}


function Main {
    Print-Msg `"初始化中`"
    Get-Fooocus-Installer-Version
    Get-Fooocus-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy

    while (`$true) {
        `$go_to = 0
        Print-Msg `"-----------------------------------------------------`"
        Print-Msg `"当前环境配置:`"
        Print-Msg `"代理设置: `$(Get-Proxy-Setting)`"
        Print-Msg `"Python 包管理器: `$(Get-Python-Package-Manager-Setting)`"
        Print-Msg `"HuggingFace 镜像源设置: `$(Get-HuggingFace-Mirror-Setting)`"
        Print-Msg `"Github 镜像源设置: `$(Get-Github-Mirror-Setting)`"
        Print-Msg `"Fooocus Installer 自动检查更新: `$(Get-Fooocus-Installer-Auto-Check-Update-Setting)`"
        Print-Msg `"Fooocus Installer 自动应用更新: `$(Get-Fooocus-Installer-Auto-Apply-Update-Setting)`"
        Print-Msg `"Fooocus 启动参数: `$(Get-Launch-Args-Setting)`"
        Print-Msg `"自动创建 Fooocus 快捷启动方式设置: `$(Get-Auto-Set-Launch-Shortcut-Setting)`"
        Print-Msg `"PyPI 镜像源设置: `$(Get-PyPI-Mirror-Setting)`"
        Print-Msg `"自动设置 CUDA 内存分配器设置: `$(Get-PyTorch-CUDA-Memory-Alloc-Setting)`"
        Print-Msg `"Fooocus 运行环境检测设置: `$(Get-Fooocus-Env-Check-Setting)`"
        Print-Msg `"Fooocus 内核路径前缀设置: `$(Get-Core-Prefix-Setting)`"
        Print-Msg `"-----------------------------------------------------`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 进入代理设置`"
        Print-Msg `"2. 进入 Python 包管理器设置`"
        Print-Msg `"3. 进入 HuggingFace 镜像源设置`"
        Print-Msg `"4. 进入 Github 镜像源设置`"
        Print-Msg `"5. 进入 Fooocus Installer 自动检查更新设置`"
        Print-Msg `"6. 进入 Fooocus Installer 自动应用更新设置`"
        Print-Msg `"7. 进入 Fooocus 启动参数设置`"
        Print-Msg `"8. 进入自动创建 Fooocus 快捷启动方式设置`"
        Print-Msg `"9. 进入 PyPI 镜像源设置`"
        Print-Msg `"10. 进入自动设置 CUDA 内存分配器设置`"
        Print-Msg `"11. 进入 Fooocus 运行环境检测设置`"
        Print-Msg `"12. 进入 Fooocus 内核路径前缀设置`"
        Print-Msg `"13. 更新 Fooocus Installer 管理脚本`"
        Print-Msg `"14. 检查环境完整性`"
        Print-Msg `"15. 查看 Fooocus Installer 文档`"
        Print-Msg `"16. 退出 Fooocus Installer 设置`"
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
                Update-Fooocus-Installer-Auto-Check-Update-Setting
                break
            }
            6 {
                Update-Fooocus-Installer-Auto-Apply-Update-Setting
                break
            }
            7 {
                Update-Fooocus-Launch-Args-Setting
                break
            }
            8 {
                Auto-Set-Launch-Shortcut-Setting
                break
            }
            9 {
                PyPI-Mirror-Setting
                break
            }
            10 {
                PyTorch-CUDA-Memory-Alloc-Setting
                break
            }
            11 {
                Fooocus-Env-Check-Setting
                break
            }
            12 {
                Update-Core-Prefix-Setting
                break
            }
            13 {
                Check-Fooocus-Installer-Update
                break
            }
            14 {
                Check-Env
                break
            }
            15 {
                Get-Fooocus-Installer-Help-Docs
                break
            }
            16 {
                `$go_to = 1
                break
            }
            Default {
                Print-Msg `"输入有误, 请重试`"
                break
            }
        }

        if (`$go_to -eq 1) {
            Print-Msg `"退出 Fooocus Installer 设置`"
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
    [string]`$CorePrefix,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableGithubMirror,
    [string]`$UseCustomGithubMirror,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisableHuggingFaceMirror,
    [string]`$UseCustomHuggingFaceMirror
)
& {
    `$prefix_list = @(`"core`", `"Fooocus`", `"fooocus`", `"fooocus_portable`")
    if ((Test-Path `"`$PSScriptRoot/core_prefix.txt`") -or (`$CorePrefix)) {
        if (`$CorePrefix) {
            `$origin_core_prefix = `$CorePrefix
        } else {
            `$origin_core_prefix = Get-Content `"`$PSScriptRoot/core_prefix.txt`"
        }
        `$origin_core_prefix = `$origin_core_prefix.Trim('/').Trim('\')
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix)) {
            `$to_path = `$origin_core_prefix
            `$from_uri = New-Object System.Uri(`$PSScriptRoot.Replace('\', '/') + '/')
            `$to_uri = New-Object System.Uri(`$to_path.Replace('\', '/'))
            `$origin_core_prefix = `$from_uri.MakeRelativeUri(`$to_uri).ToString().Trim('/')
        }
        `$Env:CORE_PREFIX = `$origin_core_prefix
        return
    }
    ForEach (`$i in `$prefix_list) {
        if (Test-Path `"`$PSScriptRoot/`$i`") {
            `$Env:CORE_PREFIX = `$i
            return
        }
    }
    `$Env:CORE_PREFIX = `"core`"
}
# Fooocus Installer 版本和检查更新间隔
`$Env:FOOOCUS_INSTALLER_VERSION = $FOOOCUS_INSTALLER_VERSION
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
`$PIP_EXTRA_INDEX_MIRROR_CPU = `"$PIP_EXTRA_INDEX_MIRROR_CPU`"
`$PIP_EXTRA_INDEX_MIRROR_XPU = `"$PIP_EXTRA_INDEX_MIRROR_XPU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118 = `"$PIP_EXTRA_INDEX_MIRROR_CU118`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
`$PIP_EXTRA_INDEX_MIRROR_CU126 = `"$PIP_EXTRA_INDEX_MIRROR_CU126`"
`$PIP_EXTRA_INDEX_MIRROR_CU128 = `"$PIP_EXTRA_INDEX_MIRROR_CU128`"
`$PIP_EXTRA_INDEX_MIRROR_CU129 = `"$PIP_EXTRA_INDEX_MIRROR_CU129`"
`$PIP_EXTRA_INDEX_MIRROR_CPU_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CPU_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_XPU_NJU = `"$PIP_EXTRA_INDEX_MIRROR_XPU_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU118_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU121_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU121_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU124_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU126_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU128_NJU`"
`$PIP_EXTRA_INDEX_MIRROR_CU129_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU129_NJU`"
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
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/`$Env:CORE_PREFIX/git/bin`"
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
`$Env:FOOOCUS_INSTALLER_ROOT = `$PSScriptRoot



# 帮助信息
function Get-Fooocus-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-DisablePyPIMirror] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像源地址>] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>]

参数:
    -Help
        获取 Fooocus Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableGithubMirror
        禁用 Fooocus Installer 自动设置 Github 镜像源

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

    -DisableProxy
        禁用 Fooocus Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableHuggingFaceMirror
        禁用 HuggingFace 镜像源, 不使用 HuggingFace 镜像源下载文件

    -UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>
        使用自定义 HuggingFace 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror ```"https://hf-mirror.com```" 设置 HuggingFace 镜像源地址


更多的帮助信息请阅读 Fooocus Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 提示符信息
function global:prompt {
    `"`$(Write-Host `"[Fooocus Env]`" -ForegroundColor Green -NoNewLine) `$(Get-Location)> `"
}


# 消息输出
function global:Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[Fooocus Installer]`" -ForegroundColor Cyan -NoNewline
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

    Move-Item -Path `"`$Env:CACHE_HOME/aria2c.exe`" -Destination `"`$Env:FOOOCUS_INSTALLER_ROOT/git/bin/aria2c.exe`" -Force
    Print-Msg `"更新 Aria2 完成`"
}


# Fooocus Installer 更新检测
function global:Check-Fooocus-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/fooocus_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/fooocus_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/fooocus_installer/fooocus_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/fooocus_installer/fooocus_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/fooocus_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null
    Set-Content -Encoding UTF8 -Path `"`$Env:FOOOCUS_INSTALLER_ROOT/update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间

    ForEach (`$url in `$urls) {
        Print-Msg `"检查 Fooocus Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/fooocus_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/fooocus_installer.ps1`" |
                Select-String -Pattern `"FOOOCUS_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 Fooocus Installer 更新中`"
            } else {
                Print-Msg `"检查 Fooocus Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -gt `$Env:FOOOCUS_INSTALLER_VERSION) {
        Print-Msg `"Fooocus Installer 有新版本可用`"
        Print-Msg `"调用 Fooocus Installer 进行更新中`"
        . `"`$Env:CACHE_HOME/fooocus_installer.ps1`" -InstallPath `"`$Env:FOOOCUS_INSTALLER_ROOT`" -UseUpdateMode
        Print-Msg `"更新结束, 需重新启动 Fooocus Installer 管理脚本以应用更新, 回车退出 Fooocus Installer 管理脚本`"
        Read-Host | Out-Null
        exit 0
    } else {
        Print-Msg `"Fooocus Installer 已是最新版本`"
    }
}


# 安装绘世启动器
function global:Install-Hanamizuki {
    `$urls = @(
        `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/hanamizuki.exe`",
        `"https://github.com/licyk/term-sd/releases/download/archive/hanamizuki.exe`",
        `"https://gitee.com/licyk/term-sd/releases/download/archive/hanamizuki.exe`"
    )
    `$i = 0

    if (!(Test-Path `"`$Env:FOOOCUS_INSTALLER_ROOT/`$Env:CORE_PREFIX`")) {
        Print-Msg `"内核路径 `$Env:FOOOCUS_INSTALLER_ROOT/`$Env:CORE_PREFIX 未找到, 无法安装绘世启动器, 请检查 Fooocus 是否已正确安装, 或者尝试运行 Fooocus Installer 进行修复`"
        return
    }

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if (Test-Path `"`$Env:FOOOCUS_INSTALLER_ROOT/`$Env:CORE_PREFIX/hanamizuki.exe`") {
        Print-Msg `"绘世启动器已安装, 路径: `$([System.IO.Path]::GetFullPath(`"`$Env:FOOOCUS_INSTALLER_ROOT/`$Env:CORE_PREFIX/hanamizuki.exe`"))`"
        Print-Msg `"可以进入该路径启动绘世启动器, 也可运行 hanamizuki.bat 启动绘世启动器`"
    } else {
        ForEach (`$url in `$urls) {
            Print-Msg `"下载绘世启动器中`"
            try {
                Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/hanamizuki_tmp.exe`"
                Move-Item -Path `"`$Env:CACHE_HOME/hanamizuki_tmp.exe`" `"`$Env:FOOOCUS_INSTALLER_ROOT/`$Env:CORE_PREFIX/hanamizuki.exe`" -Force
                Print-Msg `"绘世启动器安装成功, 路径: `$([System.IO.Path]::GetFullPath(`"`$Env:FOOOCUS_INSTALLER_ROOT/`$Env:CORE_PREFIX/hanamizuki.exe`"))`"
                Print-Msg `"可以进入该路径启动绘世启动器, 也可运行 hanamizuki.bat 启动绘世启动器`"
                break
            }
            catch {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试下载绘世启动器中`"
                } else {
                    Print-Msg `"下载绘世启动器失败`"
                    return
                }
            }
        }
    }

    `$content = `"
@echo off
echo Initialize configuration
setlocal enabledelayedexpansion
set CurrentPath=%~dp0
set DefaultCorePrefix=Fooocus
if exist ```"%~dp0%DefaultCorePrefix%```" (
    set CorePrefix=%DefaultCorePrefix%
) else (
    set CorePrefix=core
)
set CorePrefixFile=%~dp0core_prefix.txt

set ArgIndex=0
set NextIsValue=0
for %%i in (%*) do (
    set /a ArgIndex+=1
    if !NextIsValue!==1 (
        set CorePrefix=%%i
        set NextIsValue=0
        goto :convert
    ) else (
        if ```"%%i```"==```"-CorePrefix```" (
            set NextIsValue=1
        )
    )
)

if exist ```"%CorePrefixFile%```" (
    for /f ```"delims=```" %%i in ('powershell -command ```"Get-Content -Path '%CorePrefixFile%'```"') do (
        set CorePrefix=%%i
        goto :convert
    )
)

:convert
for /f ```"delims=```" %%i in ('powershell -command ```"```$current_path = '%CurrentPath%'.Trim('/').Trim('\'); ```$origin_core_prefix = '%CorePrefix%'.Trim('/').Trim('\'); if ([System.IO.Path]::IsPathRooted(```$origin_core_prefix)) { ```$to_path = ```$origin_core_prefix; ```$from_uri = New-Object System.Uri(```$current_path.Replace('\', '/') + '/'); ```$to_uri = New-Object System.Uri(```$to_path.Replace('\', '/')); ```$origin_core_prefix = ```$from_uri.MakeRelativeUri(```$to_uri).ToString().Trim('/') }; Write-Host ```$origin_core_prefix```"') do (
    set CorePrefix=%%i
    goto :continue
)

:continue
set RootPath=%~dp0%CorePrefix%
echo CorePrefix: %CorePrefix%
echo RootPath: %RootPath%
if exist ```"%RootPath%```" (
    cd /d ```"%RootPath%```"
) else (
    echo %CorePrefix% not found
    echo Please check if Fooocus is installed, or if the CorePrefix is set correctly
    pause
    exit 1
)
if exist .\hanamizuki.exe (
    echo Launch Hanamizuki
    start /B .\hanamizuki.exe
    cd /d ```"%CurrentPath%```"
) else (
    echo Hanamizuki not found
    echo Try running terminal.ps1 to open the terminal and execute the Install-Hanamizuki command to install Hanamizuki
    cd /d ```"%CurrentPath%```"
    pause
    exit 1
)
    `".Trim()

    Set-Content -Encoding Default -Path `"`$Env:FOOOCUS_INSTALLER_ROOT/hanamizuki.bat`" -Value `$content

    Print-Msg `"检查绘世启动器运行环境`"
    if (!(Test-Path `"`$Env:FOOOCUS_INSTALLER_ROOT/`$Env:CORE_PREFIX/python/python.exe`")) {
        if (Test-Path `"`$Env:FOOOCUS_INSTALLER_ROOT/python`") {
            Print-Msg `"尝试将 Python 移动至 `$Env:FOOOCUS_INSTALLER_ROOT\`$Env:CORE_PREFIX 中`"
            Move-Item -Path `"`$Env:FOOOCUS_INSTALLER_ROOT/python`" `"`$Env:FOOOCUS_INSTALLER_ROOT/`$Env:CORE_PREFIX`" -Force
            if (`$?) {
                Print-Msg `"Python 路径移动成功`"
            } else {
                Print-Msg `"Python 路径移动失败, 这将导致绘世启动器无法正确识别到 Python 环境`"
                Print-Msg `"请关闭所有占用 Python 的进程, 并重新运行该命令`"
            }
        } else {
            Print-Msg `"环境缺少 Python, 无法为绘世启动器准备 Python 环境, 请重新运行 Fooocus Installer 修复环境`"
        }
    }

    if (!(Test-Path `"`$Env:FOOOCUS_INSTALLER_ROOT/`$Env:CORE_PREFIX/git/bin/git.exe`")) {
        if (Test-Path `"`$Env:FOOOCUS_INSTALLER_ROOT/git`") {
            Print-Msg `"尝试将 Git 移动至 `$Env:FOOOCUS_INSTALLER_ROOT\`$Env:CORE_PREFIX 中`"
            Move-Item -Path `"`$Env:FOOOCUS_INSTALLER_ROOT/git`" `"`$Env:FOOOCUS_INSTALLER_ROOT/`$Env:CORE_PREFIX`" -Force
            if (`$?) {
                Print-Msg `"Git 路径移动成功`"
            } else {
                Print-Msg `"Git 路径移动失败, 这将导致绘世启动器无法正确识别到 Git 环境`"
                Print-Msg `"请关闭所有占用 Git 的进程, 并重新运行该命令`"
            }
        } else {
            Print-Msg `"环境缺少 Git, 无法为绘世启动器准备 Git 环境, 请重新运行 Fooocus Installer 修复环境`"
        }
    }

    Print-Msg `"检查绘世启动器运行环境结束`"
}


# 获取指定路径的内核路径前缀
function global:Get-Core-Prefix (`$to_path) {
    `$from_path = `$Env:FOOOCUS_INSTALLER_ROOT
    `$from_uri = New-Object System.Uri(`$from_path.Replace('\', '/') + '/')
    `$to_uri = New-Object System.Uri(`$to_path.Trim('/').Trim('\').Replace('\', '/'))
    `$relative_path = `$from_uri.MakeRelativeUri(`$to_uri).ToString().Trim('/')
    Print-Msg `"`$to_path 路径的内核路径前缀: `$relative_path`"
    Print-Msg `"提示: 可使用 settings.ps1 设置内核路径前缀`"
}


# 设置 Python 命令别名
function global:pip {
    python -m pip @args
}

Set-Alias pip3 pip
Set-Alias pip3.11 pip
Set-Alias python3 python
Set-Alias python3.11 python


# 列出 Fooocus Installer 内置命令
function global:List-CMD {
    Write-Host `"
==================================
Fooocus Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
==================================

当前可用的 Fooocus Installer 内置命令：

    Update-uv
    Update-Aria2
    Check-Fooocus-Installer-Update
    Install-Hanamizuki
    Get-Core-Prefix
    List-CMD

更多帮助信息可在 Fooocus Installer 文档中查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md
`"
}


# 显示 Fooocus Installer 版本
function Get-Fooocus-Installer-Version {
    `$ver = `$([string]`$Env:FOOOCUS_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"Fooocus Installer 版本: v`${major}.`${minor}.`${micro}`"
}


# 获取内核路径前缀状态
function Get-Core-Prefix-Status {
    if ((Test-Path `"`$PSScriptRoot/core_prefix.txt`") -or (`$CorePrefix)) {
        Print-Msg `"检测到 core_prefix.txt 配置文件 / -CorePrefix 命令行参数, 使用自定义内核路径前缀`"
        if (`$CorePrefix) {
            `$origin_core_prefix = `$CorePrefix
        } else {
            `$origin_core_prefix = Get-Content `"`$PSScriptRoot/core_prefix.txt`"
        }
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix.Trim('/').Trim('\'))) {
            Print-Msg `"转换绝对路径为内核路径前缀: `$origin_core_prefix -> `$Env:CORE_PREFIX`"
        }
    }
    Print-Msg `"当前内核路径前缀: `$Env:CORE_PREFIX`"
    Print-Msg `"完整内核路径: `$PSScriptRoot\`$Env:CORE_PREFIX`"
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
    Get-Fooocus-Installer-Version
    Get-Fooocus-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy
    Set-HuggingFace-Mirror
    Set-Github-Mirror
    PyPI-Mirror-Status
    # 切换 uv 指定的 Python
    if (Test-Path `"`$Env:FOOOCUS_INSTALLER_ROOT/`$Env:CORE_PREFIX/python/python.exe`") {
        `$Env:UV_PYTHON = `"`$Env:FOOOCUS_INSTALLER_ROOT/`$Env:CORE_PREFIX/python/python.exe`"
    }
    Print-Msg `"激活 Fooocus Env`"
    Print-Msg `"更多帮助信息可在 Fooocus Installer 项目地址查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md`"
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
    Write-Host `"[Fooocus Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}

Print-Msg `"执行 Fooocus Installer 激活环境脚本`"
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
Fooocus Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
====================================================================
########## 使用帮助 ##########

这是关于 Fooocus 的简单使用文档。

使用 Fooocus Installer 进行安装并安装成功后，将在当前目录生成 Fooocus 文件夹，以下为文件夹中不同文件 / 文件夹的作用。

- launch.ps1：启动 Fooocus。
- update.ps1：更新 Fooocus。
- download_models.ps1：下载模型的脚本，下载的模型将存放在 Fooocus 的模型文件夹中。
- reinstall_pytorch.ps1：重新安装 PyTorch 的脚本，在 PyTorch 出问题或者需要切换 PyTorch 版本时可使用。
- switch_branch.ps1：切换 Fooocus 分支。
- settings.ps1：管理 Fooocus Installer 的设置。
- terminal.ps1：启动 PowerShell 终端并自动激活虚拟环境，激活虚拟环境后即可使用 Python、Pip、Git 的命令。
- activate.ps1：虚拟环境激活脚本，使用该脚本激活虚拟环境后即可使用 Python、Pip、Git 的命令。
- launch_fooocus_installer.ps1：获取最新的 Fooocus Installer 安装脚本并运行。
- configure_env.bat：配置环境脚本，修复 PowerShell 运行闪退和启用 Windows 长路径支持。

- cache：缓存文件夹，保存着 Pip / HuggingFace 等缓存文件。
- python：Python 的存放路径。请注意，请勿将该 Python 文件夹添加到环境变量，这可能导致不良后果。
- git：Git 的存放路径。
- Fooocus / core：Fooocus 内核。

详细的 Fooocus Installer 使用帮助：https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md

Fooocus 一些使用方法：
https://github.com/lllyasviel/Fooocus/discussions/117
https://github.com/lllyasviel/Fooocus/discussions/830


====================================================================
########## Github 项目 ##########

sd-webui-all-in-one 项目地址：https://github.com/licyk/sd-webui-all-in-one
Fooocus 项目地址：https://github.com/lllyasviel/Fooocus
Fooocus-MRE 项目地址：https://github.com/MoonRide303/Fooocus-MRE
RuinedFooocus 项目地址：https://github.com/runew0lf/RuinedFooocus


====================================================================
########## 用户协议 ##########

使用该软件代表您已阅读并同意以下用户协议：
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
    Write-Launch-Script
    Write-Update-Script
    Write-Switch-Branch-Script
    Write-Launch-Fooocus-Install-Script
    Write-PyTorch-ReInstall-Script
    Write-Download-Model-Script
    Write-Fooocus-Installer-Settings-Script
    Write-Env-Activate-Script
    Write-Launch-Terminal-Script
    Write-ReadMe
    Write-Configure-Env-Script
    Write-Hanamizuki-Script
}


# 将安装器配置文件复制到管理脚本路径
function Copy-Fooocus-Installer-Config {
    Print-Msg "为 Fooocus Installer 管理脚本复制 Fooocus Installer 配置文件中"

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

    if ((!($CorePrefix)) -and (Test-Path "$PSScriptRoot/core_prefix.txt")) {
        Copy-Item -Path "$PSScriptRoot/core_prefix.txt" -Destination "$InstallPath" -Force
        Print-Msg "$PSScriptRoot/core_prefix.txt -> $InstallPath/core_prefix.txt" -Force
    }
}


# 写入启动绘世启动器脚本
function Write-Hanamizuki-Script {
    param (
        [switch]$Force
    )
    $content = "
@echo off
echo Initialize configuration
setlocal enabledelayedexpansion
set CurrentPath=%~dp0
set DefaultCorePrefix=Fooocus
if exist `"%~dp0%DefaultCorePrefix%`" (
    set CorePrefix=%DefaultCorePrefix%
) else (
    set CorePrefix=core
)
set CorePrefixFile=%~dp0core_prefix.txt

set ArgIndex=0
set NextIsValue=0
for %%i in (%*) do (
    set /a ArgIndex+=1
    if !NextIsValue!==1 (
        set CorePrefix=%%i
        set NextIsValue=0
        goto :convert
    ) else (
        if `"%%i`"==`"-CorePrefix`" (
            set NextIsValue=1
        )
    )
)

if exist `"%CorePrefixFile%`" (
    for /f `"delims=`" %%i in ('powershell -command `"Get-Content -Path '%CorePrefixFile%'`"') do (
        set CorePrefix=%%i
        goto :convert
    )
)

:convert
for /f `"delims=`" %%i in ('powershell -command `"`$current_path = '%CurrentPath%'.Trim('/').Trim('\'); `$origin_core_prefix = '%CorePrefix%'.Trim('/').Trim('\'); if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix)) { `$to_path = `$origin_core_prefix; `$from_uri = New-Object System.Uri(`$current_path.Replace('\', '/') + '/'); `$to_uri = New-Object System.Uri(`$to_path.Replace('\', '/')); `$origin_core_prefix = `$from_uri.MakeRelativeUri(`$to_uri).ToString().Trim('/') }; Write-Host `$origin_core_prefix`"') do (
    set CorePrefix=%%i
    goto :continue
)

:continue
set RootPath=%~dp0%CorePrefix%
echo CorePrefix: %CorePrefix%
echo RootPath: %RootPath%
if exist `"%RootPath%`" (
    cd /d `"%RootPath%`"
) else (
    echo %CorePrefix% not found
    echo Please check if Fooocus is installed, or if the CorePrefix is set correctly
    pause
    exit 1
)
if exist .\hanamizuki.exe (
    echo Launch Hanamizuki
    start /B .\hanamizuki.exe
    cd /d `"%CurrentPath%`"
) else (
    echo Hanamizuki not found
    echo Try running terminal.ps1 to open the terminal and execute the Install-Hanamizuki command to install Hanamizuki
    cd /d `"%CurrentPath%`"
    pause
    exit 1
)
    ".Trim()

    if ((!($Force)) -and (!(Test-Path "$InstallPath/hanamizuki.bat"))) {
        return
    }

    if (Test-Path "$InstallPath/hanamizuki.bat") {
        Print-Msg "更新 hanamizuki.bat 中"
    } else {
        Print-Msg "生成 hanamizuki.bat 中"
    }
    Set-Content -Encoding Default -Path "$InstallPath/hanamizuki.bat" -Value $content
}


# 安装绘世启动器
function Install-Hanamizuki {
    $urls = @(
        "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/hanamizuki.exe",
        "https://github.com/licyk/term-sd/releases/download/archive/hanamizuki.exe",
        "https://gitee.com/licyk/term-sd/releases/download/archive/hanamizuki.exe"
    )
    $i = 0

    if (!($InstallHanamizuki)) {
        return
    }

    New-Item -ItemType Directory -Path "$Env:CACHE_HOME" -Force > $null

    if (Test-Path "$InstallPath/$Env:CORE_PREFIX/hanamizuki.exe") {
        Print-Msg "绘世启动器已安装, 路径: $([System.IO.Path]::GetFullPath("$InstallPath/$Env:CORE_PREFIX/hanamizuki.exe"))"
        Print-Msg "可以进入该路径启动绘世启动器, 也可运行 hanamizuki.bat 启动绘世启动器"
    } else {
        ForEach ($url in $urls) {
            Print-Msg "下载绘世启动器中"
            try {
                Invoke-WebRequest -Uri $url -OutFile "$Env:CACHE_HOME/hanamizuki_tmp.exe"
                Move-Item -Path "$Env:CACHE_HOME/hanamizuki_tmp.exe" "$InstallPath/$Env:CORE_PREFIX/hanamizuki.exe" -Force
                Print-Msg "绘世启动器安装成功, 路径: $([System.IO.Path]::GetFullPath("$InstallPath/$Env:CORE_PREFIX/hanamizuki.exe"))"
                Print-Msg "可以进入该路径启动绘世启动器, 也可运行 hanamizuki.bat 启动绘世启动器"
                break
            }
            catch {
                $i += 1
                if ($i -lt $urls.Length) {
                    Print-Msg "重试下载绘世启动器中"
                } else {
                    Print-Msg "下载绘世启动器失败"
                    return
                }
            }
        }
    }

    Write-Hanamizuki-Script -Force

    Print-Msg "检查绘世启动器运行环境"
    if (!(Test-Path "$InstallPath/$Env:CORE_PREFIX/python/python.exe")) {
        if (Test-Path "$InstallPath/python") {
            Print-Msg "尝试将 Python 移动至 $InstallPath\$Env:CORE_PREFIX 中"
            Move-Item -Path "$InstallPath/python" "$InstallPath/$Env:CORE_PREFIX" -Force
            if ($?) {
                Print-Msg "Python 路径移动成功"
            } else {
                Print-Msg "Python 路径移动失败, 这将导致绘世启动器无法正确识别到 Python 环境"
                Print-Msg "请关闭所有占用 Python 的进程, 并重新运行该命令"
            }
        } else {
            Print-Msg "环境缺少 Python, 无法为绘世启动器准备 Python 环境, 请重新运行 Fooocus Installer 修复环境"
        }
    }

    if (!(Test-Path "$InstallPath/$Env:CORE_PREFIX/git/bin/git.exe")) {
        if (Test-Path "$InstallPath/git") {
            Print-Msg "尝试将 Git 移动至 $InstallPath\$Env:CORE_PREFIX 中"
            Move-Item -Path "$InstallPath/git" "$InstallPath/$Env:CORE_PREFIX" -Force
            if ($?) {
                Print-Msg "Git 路径移动成功"
            } else {
                Print-Msg "Git 路径移动失败, 这将导致绘世启动器无法正确识别到 Git 环境"
                Print-Msg "请关闭所有占用 Git 的进程, 并重新运行该命令"
            }
        } else {
            Print-Msg "环境缺少 Git, 无法为绘世启动器准备 Git 环境, 请重新运行 Fooocus Installer 修复环境"
        }
    }

    Print-Msg "检查绘世启动器运行环境结束"
}


# 执行安装
function Use-Install-Mode {
    Set-Proxy
    Set-uv
    PyPI-Mirror-Status
    Print-Msg "启动 Fooocus 安装程序"
    Print-Msg "提示: 若出现某个步骤执行失败, 可尝试再次运行 Fooocus Installer, 更多的说明请阅读 Fooocus Installer 使用文档"
    Print-Msg "Fooocus Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md"
    Print-Msg "即将进行安装的路径: $InstallPath"
    if ((Test-Path "$PSScriptRoot/install_fooocus.txt") -or ($InstallBranch -eq "fooocus")) {
        Print-Msg "检测到 install_fooocus.txt 配置文件 / -InstallBranch fooocus 命令行参数, 选择安装 lllyasviel/Fooocus"
    } elseif ((Test-Path "$PSScriptRoot/install_fooocus_mre.txt") -or ($InstallBranch -eq "fooocus_mre")) {
        Print-Msg "检测到 install_fooocus_mre.txt 配置文件 / -InstallBranch fooocus_mre 命令行参数, 选择安装 MoonRide303/Fooocus-MRE"
    } elseif ((Test-Path "$PSScriptRoot/install_ruined_fooocus.txt") -or ($InstallBranch -eq "ruined_fooocus")) {
        Print-Msg "检测到 install_ruined_fooocus.txt 配置文件 / -InstallBranch ruined_fooocus 命令行参数, 选择安装 runew0lf/RuinedFooocus"
    } else {
        Print-Msg "未指定安装的 Fooocus 分支, 默认选择安装 lllyasviel/Fooocus"
    }
    Check-Install
    Print-Msg "添加管理脚本和文档中"
    Write-Manager-Scripts
    Copy-Fooocus-Installer-Config

    if ($BuildMode) {
        Use-Build-Mode
        Install-Hanamizuki
        Print-Msg "Fooocus 环境构建完成, 路径: $InstallPath"
    } else {
        Install-Hanamizuki
        Print-Msg "Fooocus 安装结束, 安装路径为: $InstallPath"
    }

    Print-Msg "帮助文档可在 Fooocus 文件夹中查看, 双击 help.txt 文件即可查看, 更多的说明请阅读 Fooocus Installer 使用文档"
    Print-Msg "Fooocus Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md"
    Print-Msg "退出 Fooocus Installer"

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
        $launch_args.Add("-BuildMode", $true)
        $launch_args.Add("-BuildWithTorch", $BuildWithTorch)
        if ($BuildWithTorchReinstall) { $launch_args.Add("-BuildWithTorchReinstall", $true) }
        if ($DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($DisableUV) { $launch_args.Add("-DisableUV", $true) }
        if ($DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $UseCustomProxy) }
        if ($DisableAutoApplyUpdate) { $launch_args.Add("-DisableAutoApplyUpdate", $true) }
        if ($CorePrefix) { $launch_args.Add("-CorePrefix", $CorePrefix) }
        Print-Msg "执行重装 PyTorch 脚本中"
        . "$InstallPath/reinstall_pytorch.ps1" @launch_args
    }

    if ($BuildWitchModel) {
        $launch_args = @{}
        $launch_args.Add("-BuildMode", $true)
        $launch_args.Add("-BuildWitchModel", $BuildWitchModel)
        if ($DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $UseCustomProxy) }
        if ($DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($DisableAutoApplyUpdate) { $launch_args.Add("-DisableAutoApplyUpdate", $true) }
        if ($CorePrefix) { $launch_args.Add("-CorePrefix", $CorePrefix) }
        Print-Msg "执行模型安装脚本中"
        . "$InstallPath/download_models.ps1" @launch_args
    }

    if ($BuildWitchBranch) {
        $launch_args = @{}
        $launch_args.Add("-BuildMode", $true)
        $launch_args.Add("-BuildWitchBranch", $BuildWitchBranch)
        if ($DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $UseCustomProxy) }
        if ($DisableGithubMirror) { $launch_args.Add("-DisableGithubMirror", $true) }
        if ($UseCustomGithubMirror) { $launch_args.Add("-UseCustomGithubMirror", $UseCustomGithubMirror) }
        if ($DisableAutoApplyUpdate) { $launch_args.Add("-DisableAutoApplyUpdate", $true) }
        if ($CorePrefix) { $launch_args.Add("-CorePrefix", $CorePrefix) }
        Print-Msg "执行 Fooocus 分支切换脚本中"
        . "$InstallPath/switch_branch.ps1" @launch_args
    }

    if ($BuildWithUpdate) {
        $launch_args = @{}
        $launch_args.Add("-BuildMode", $true)
        if ($DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $UseCustomProxy) }
        if ($DisableGithubMirror) { $launch_args.Add("-DisableGithubMirror", $true) }
        if ($UseCustomGithubMirror) { $launch_args.Add("-UseCustomGithubMirror", $UseCustomGithubMirror) }
        if ($DisableAutoApplyUpdate) { $launch_args.Add("-DisableAutoApplyUpdate", $true) }
        if ($CorePrefix) { $launch_args.Add("-CorePrefix", $CorePrefix) }
        Print-Msg "执行 Fooocus 更新脚本中"
        . "$InstallPath/update.ps1" @launch_args
    }

    if ($BuildWithLaunch) {
        $launch_args = @{}
        $launch_args.Add("-BuildMode", $true)
        if ($DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $UseCustomProxy) }
        if ($DisableHuggingFaceMirror) { $launch_args.Add("-DisableHuggingFaceMirror", $true) }
        if ($UseCustomHuggingFaceMirror) { $launch_args.Add("-UseCustomHuggingFaceMirror", $UseCustomHuggingFaceMirror) }
        if ($DisableGithubMirror) { $launch_args.Add("-DisableGithubMirror", $true) }
        if ($UseCustomGithubMirror) { $launch_args.Add("-UseCustomGithubMirror", $UseCustomGithubMirror) }
        if ($DisableUV) { $launch_args.Add("-DisableUV", $true) }
        if ($LaunchArg) { $launch_args.Add("-LaunchArg", $LaunchArg) }
        if ($EnableShortcut) { $launch_args.Add("-EnableShortcut", $true) }
        if ($DisableCUDAMalloc) { $launch_args.Add("-DisableCUDAMalloc", $true) }
        if ($DisableEnvCheck) { $launch_args.Add("-DisableEnvCheck", $true) }
        if ($DisableAutoApplyUpdate) { $launch_args.Add("-DisableAutoApplyUpdate", $true) }
        if ($CorePrefix) { $launch_args.Add("-CorePrefix", $CorePrefix) }
        Print-Msg "执行 Fooocus 启动脚本中"
        . "$InstallPath/launch.ps1" @launch_args
    }

    # 清理缓存
    if ($NoCleanCache) {
        Print-Msg "跳过清理下载 Python 软件包的缓存"
    } else {
        Print-Msg "清理下载 Python 软件包的缓存中"
        python -m pip cache purge
        uv cache clean
    }
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
function Get-Fooocus-Installer-Cmdlet-Help {
    $content = "
使用:
    .\$($script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-InstallPath <安装 Fooocus 的绝对路径>] [-PyTorchMirrorType <PyTorch 镜像源类型>] [-InstallBranch <安装的 Fooocus 分支>] [-UseUpdateMode] [-DisablePyPIMirror] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableUV] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像站地址>] [-BuildMode] [-BuildWithUpdate] [-BuildWithLaunch] [-BuildWithTorch <PyTorch 版本编号>] [-BuildWithTorchReinstall] [-BuildWitchModel <模型编号列表>] [-BuildWitchBranch <Fooocus 分支编号>] [-NoPreDownloadModel] [-PyTorchPackage <PyTorch 软件包>] [-InstallHanamizuki] [-NoCleanCache] [-xFormersPackage <xFormers 软件包>] [-DisableUpdate] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>] [-LaunchArg <Fooocus 启动参数>] [-EnableShortcut] [-DisableCUDAMalloc] [-DisableEnvCheck] [-DisableAutoApplyUpdate]

参数:
    -Help
        获取 Fooocus Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -InstallPath <安装 Fooocus 的绝对路径>
        指定 Fooocus Installer 安装 Fooocus 的路径, 使用绝对路径表示
        例如: .\$($script:MyInvocation.MyCommand.Name) -InstallPath `"D:\Donwload`", 这将指定 Fooocus Installer 安装 Fooocus 到 D:\Donwload 这个路径

    -PyTorchMirrorType <PyTorch 镜像源类型>
        指定安装 PyTorch 时使用的 PyTorch 镜像源类型, 可指定的类型: cpu, xpu, cu11x, cu118, cu121, cu124, cu126, cu128, cu129

    -InstallBranch <安装的 Fooocus 分支>
        指定 Fooocus Installer 安装的 Fooocus 分支 (fooocus, fooocus_mre, ruined_fooocus)
        例如: .\$($script:MyInvocation.MyCommand.Name) -InstallBranch `"fooocus_mre`", 这将指定 Fooocus Installer 安装 MoonRide303/Fooocus-MRE 分支
        未指定该参数时, 默认安装 lllyasviel/Fooocus 分支
        支持指定安装的分支如下:
            fooocus:        lllyasviel/Fooocus
            fooocus_mre:    MoonRide303/Fooocus-MRE
            ruined_fooocus: runew0lf/RuinedFooocus

    -UseUpdateMode
        指定 Fooocus Installer 使用更新模式, 只对 Fooocus Installer 的管理脚本进行更新

    -DisablePyPIMirror
        禁用 Fooocus Installer 使用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableProxy
        禁用 Fooocus Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy `"http://127.0.0.1:10809`" 设置代理服务器地址

    -DisableUV
        禁用 Fooocus Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -DisableGithubMirror
        禁用 Fooocus Installer 自动设置 Github 镜像源

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
        启用 Fooocus Installer 构建模式, 在基础安装流程结束后将调用 Fooocus Installer 管理脚本执行剩余的安装任务, 并且出现错误时不再暂停 Fooocus Installer 的执行, 而是直接退出
        当指定调用多个 Fooocus Installer 脚本时, 将按照优先顺序执行 (按从上到下的顺序)
            - reinstall_pytorch.ps1     (对应 -BuildWithTorch, -BuildWithTorchReinstall 参数)
            - switch_branch.ps1         (对应 -BuildWitchBranch 参数)
            - download_models.ps1       (对应 -BuildWitchModel 参数)
            - update.ps1                (对应 -BuildWithUpdate 参数)
            - launch.ps1                (对应 -BuildWithLaunch 参数)

    -BuildWithUpdate
        (需添加 -BuildMode 启用 Fooocus Installer 构建模式) Fooocus Installer 执行完基础安装流程后调用 Fooocus Installer 的 update.ps1 脚本, 更新 Fooocus 内核

    -BuildWithLaunch
        (需添加 -BuildMode 启用 Fooocus Installer 构建模式) Fooocus Installer 执行完基础安装流程后调用 Fooocus Installer 的 launch.ps1 脚本, 执行启动 Fooocus 前的环境检查流程, 但跳过启动 Fooocus

    -BuildWithTorch <PyTorch 版本编号>
        (需添加 -BuildMode 启用 Fooocus Installer 构建模式) Fooocus Installer 执行完基础安装流程后调用 Fooocus Installer 的 reinstall_pytorch.ps1 脚本, 根据 PyTorch 版本编号安装指定的 PyTorch 版本
        PyTorch 版本编号可运行 reinstall_pytorch.ps1 脚本进行查看

    -BuildWithTorchReinstall
        (需添加 -BuildMode 启用 Fooocus Installer 构建模式, 并且添加 -BuildWithTorch) 在 Fooocus Installer 构建模式下, 执行 reinstall_pytorch.ps1 脚本对 PyTorch 进行指定版本安装时使用强制重新安装

    -BuildWitchModel <模型编号列表>
        (需添加 -BuildMode 启用 Fooocus Installer 构建模式) Fooocus Installer 执行完基础安装流程后调用 Fooocus Installer 的 download_models.ps1 脚本, 根据模型编号列表下载指定的模型
        模型编号可运行 download_models.ps1 脚本进行查看

    -BuildWitchBranch <Fooocus 分支编号>
        (需添加 -BuildMode 启用 Fooocus Installer 构建模式) Fooocus Installer 执行完基础安装流程后调用 Fooocus Installer 的 switch_branch.ps1 脚本, 根据 Fooocus 分支编号切换到对应的 Fooocus 分支
        Fooocus 分支编号可运行 switch_branch.ps1 脚本进行查看

    -NoPreDownloadModel
        安装 Fooocus 时跳过预下载模型

    -PyTorchPackage <PyTorch 软件包>
        (需要同时搭配 -xFormersPackage 一起使用, 否则可能会出现 PyTorch 和 xFormers 不匹配的问题) 指定要安装 PyTorch 版本, 如 -PyTorchPackage `"torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118`"

    -xFormersPackage <xFormers 软件包>
        (需要同时搭配 -PyTorchPackage 一起使用, 否则可能会出现 PyTorch 和 xFormers 不匹配的问题) 指定要安装 xFormers 版本, 如 -xFormersPackage `"xformers===0.0.26.post1+cu118`"

    -InstallHanamizuki
        安装绘世启动器, 并生成 hanamizuki.bat 用于启动绘世启动器

    -NoCleanCache
        安装结束后保留下载 Python 软件包缓存

    -DisableUpdate
        (仅在 Fooocus Installer 构建模式下生效, 并且只作用于 Fooocus Installer 管理脚本) 禁用 Fooocus Installer 更新检查

    -DisableHuggingFaceMirror
        (仅在 Fooocus Installer 构建模式下生效, 并且只作用于 Fooocus Installer 管理脚本) 禁用 HuggingFace 镜像源, 不使用 HuggingFace 镜像源下载文件

    -UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>
        (仅在 Fooocus Installer 构建模式下生效, 并且只作用于 Fooocus Installer 管理脚本) 使用自定义 HuggingFace 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror `"https://hf-mirror.com`" 设置 HuggingFace 镜像源地址

    -LaunchArg <Fooocus 启动参数>
        (仅在 Fooocus Installer 构建模式下生效, 并且只作用于 Fooocus Installer 管理脚本) 设置 Fooocus 自定义启动参数, 如启用 --in-browser 和 --async-cuda-allocation, 则使用 -LaunchArg `"--in-browser --async-cuda-allocation`" 进行启用

    -EnableShortcut
        (仅在 Fooocus Installer 构建模式下生效, 并且只作用于 Fooocus Installer 管理脚本) 创建 Fooocus 启动快捷方式

    -DisableCUDAMalloc
        (仅在 Fooocus Installer 构建模式下生效, 并且只作用于 Fooocus Installer 管理脚本) 禁用 Fooocus Installer 通过 PYTORCH_CUDA_ALLOC_CONF 环境变量设置 CUDA 内存分配器

    -DisableEnvCheck
        (仅在 Fooocus Installer 构建模式下生效, 并且只作用于 Fooocus Installer 管理脚本) 禁用 Fooocus Installer 检查 Fooocus 运行环境中存在的问题, 禁用后可能会导致 Fooocus 环境中存在的问题无法被发现并修复

    -DisableAutoApplyUpdate
        (仅在 Fooocus Installer 构建模式下生效, 并且只作用于 Fooocus Installer 管理脚本) 禁用 Fooocus Installer 自动应用新版本更新


更多的帮助信息请阅读 Fooocus Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md
".Trim()

    if ($Help) {
        Write-Host $content
        exit 0
    }
}


# 主程序
function Main {
    Print-Msg "初始化中"
    Get-Fooocus-Installer-Version
    Get-Fooocus-Installer-Cmdlet-Help
    Get-Core-Prefix-Status

    if ($UseUpdateMode) {
        Print-Msg "使用更新模式"
        Use-Update-Mode
        Set-Content -Encoding UTF8 -Path "$InstallPath/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
    } else {
        if ($BuildMode) {
            Print-Msg "Fooocus Installer 构建模式已启用"
        }
        Print-Msg "使用安装模式"
        Use-Install-Mode
    }
}


###################


Main
