param (
    [switch]$Help,
    [string]$CorePrefix,
    [string]$InstallPath = (Join-Path -Path "$PSScriptRoot" -ChildPath "qwen-tts-webui"),
    [string]$PyTorchMirrorType,
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
    [string]$PyTorchPackage,
    [string]$xFormersPackage,
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
    $prefix_list = @("core", "QwenTTSWebUI", "qwen-tts-webui", "qwen_tts_webui_portable")
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
# Qwen TTS WebUI Installer 版本和检查更新间隔
$QWEN_TTS_WEBUI_INSTALLER_VERSION = 100
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
$PIP_EXTRA_INDEX_MIRROR_CU130 = "https://download.pytorch.org/whl/cu130"
$PIP_EXTRA_INDEX_MIRROR_CPU_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cpu"
$PIP_EXTRA_INDEX_MIRROR_XPU_NJU = "https://mirror.nju.edu.cn/pytorch/whl/xpu"
$PIP_EXTRA_INDEX_MIRROR_CU118_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu118"
$PIP_EXTRA_INDEX_MIRROR_CU121_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu121"
$PIP_EXTRA_INDEX_MIRROR_CU124_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu124"
$PIP_EXTRA_INDEX_MIRROR_CU126_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu126"
$PIP_EXTRA_INDEX_MIRROR_CU128_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu128"
$PIP_EXTRA_INDEX_MIRROR_CU129_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu129"
$PIP_EXTRA_INDEX_MIRROR_CU130_NJU = "https://mirror.nju.edu.cn/pytorch/whl/cu130"
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
$UV_MINIMUM_VER = "0.9.9"
# Aria2 最低版本
$ARIA2_MINIMUM_VER = "1.37.0"
# Qwen TTS WebUI 仓库地址
$QWEN_TTS_WEBUI_REPO = "https://github.com/licyk/qwen-tts-webui"
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
$Env:PYTHONWARNINGS = "ignore:::torchvision.transforms.functional_tensor,ignore::UserWarning,ignore::FutureWarning,ignore::DeprecationWarning"
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
    Write-Host "[Qwen TTS WebUI Installer]" -ForegroundColor Cyan -NoNewline
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


# 显示 Qwen TTS WebUI Installer 版本
function Get-Qwen-TTS-WebUI-Installer-Version {
    $ver = $([string]$QWEN_TTS_WEBUI_INSTALLER_VERSION).ToCharArray()
    $major = ($ver[0..($ver.Length - 3)])
    $minor = $ver[-2]
    $micro = $ver[-1]
    Print-Msg "Qwen TTS WebUI Installer 版本: v${major}.${minor}.${micro}"
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
    
    if compare_versions(uv_ver, uv_minimum_ver) < 0:
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
            $web_request_params = @{
                Uri = $url
                UseBasicParsing = $true
                OutFile = "$Env:CACHE_HOME/python-amd64.zip"
            }
            Invoke-WebRequest @web_request_params
            break
        }
        catch {
            $i += 1
            if ($i -lt $urls.Length) {
                Print-Msg "重试下载 Python 中"
            } else {
                Print-Msg "Python 安装失败, 终止 Qwen TTS WebUI 安装进程, 可尝试重新运行 Qwen TTS WebUI Installer 重试失败的安装"
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
            $web_request_params = @{
                Uri = $url
                UseBasicParsing = $true
                OutFile = "$Env:CACHE_HOME/PortableGit.zip"
            }
            Invoke-WebRequest @web_request_params
            break
        }
        catch {
            $i += 1
            if ($i -lt $urls.Length) {
                Print-Msg "重试下载 Git 中"
            } else {
                Print-Msg "Git 安装失败, 终止 Qwen TTS WebUI 安装进程, 可尝试重新运行 Qwen TTS WebUI Installer 重试失败的安装"
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
            $web_request_params = @{
                Uri = $url
                UseBasicParsing = $true
                OutFile = "$Env:CACHE_HOME/aria2c.exe"
            }
            Invoke-WebRequest @web_request_params
            break
        }
        catch {
            $i += 1
            if ($i -lt $urls.Length) {
                Print-Msg "重试下载 Aria2 中"
            } else {
                Print-Msg "Aria2 安装失败, 终止 Qwen TTS WebUI 安装进程, 可尝试重新运行 Qwen TTS WebUI Installer 重试失败的安装"
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
        Print-Msg "uv 下载失败, 终止 Qwen TTS WebUI 安装进程, 可尝试重新运行 Qwen TTS WebUI Installer 重试失败的安装"
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
        $items = Get-ChildItem "$path"
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
            Print-Msg "$name 安装失败, 终止 Qwen TTS WebUI 安装进程, 可尝试重新运行 Qwen TTS WebUI Installer 重试失败的安装"
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
    # cu129: 2.8.0
    # cu130: 2.9.0 ~
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

    if compare_versions(torch_ver, '2.0.0') < 0:
        # torch < 2.0.0: default cu11x
        if has_gpus:
            return 'cu11x'
    if compare_versions(torch_ver, '2.0.0') >= 0 and compare_versions(torch_ver, '2.3.1') < 0:
        # 2.0.0 <= torch < 2.3.1: default cu118
        if has_gpus:
            return 'cu118'
    if compare_versions(torch_ver, '2.3.0') >= 0 and compare_versions(torch_ver, '2.4.1') < 0:
        # 2.3.0 <= torch < 2.4.1: default cu121
        if compare_versions(str(int(cuda_support_ver * 10)), 'cu121') < 0:
            if compare_versions(str(int(cuda_support_ver * 10)), 'cu118') >= 0:
                return 'cu118'
        if has_gpus:
            return 'cu121'
    if compare_versions(torch_ver, '2.4.0') >= 0 and compare_versions(torch_ver, '2.6.0') < 0:
        # 2.4.0 <= torch < 2.6.0: default cu124
        if compare_versions(str(int(cuda_support_ver * 10)), 'cu124') < 0:
            if compare_versions(str(int(cuda_support_ver * 10)), 'cu121') >= 0:
                return 'cu121'
            if compare_versions(str(int(cuda_support_ver * 10)), 'cu118') >= 0:
                return 'cu118'
        if has_gpus:
            return 'cu124'
    if compare_versions(torch_ver, '2.6.0') >= 0 and compare_versions(torch_ver, '2.7.0') < 0:
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
    if compare_versions(torch_ver, '2.7.0') >= 0 and compare_versions(torch_ver, '2.8.0') < 0:
        # 2.7.0 <= torch < 2.8.0: default cu128
        if compare_versions(str(int(cuda_support_ver * 10)), 'cu128') < 0:
            if compare_versions(str(int(cuda_support_ver * 10)), 'cu126') >= 0:
                return 'cu126'
        if use_xpu and has_xpu:
            return 'xpu'
        if has_gpus:
            return 'cu128'
    if compare_versions(torch_ver, '2.8.0') >= 0 and compare_versions(torch_ver, '2.9.0') < 0:
        # torch ~= 2.8.0: default cu129
        if compare_versions(str(int(cuda_support_ver * 10)), 'cu129') < 0:
            if compare_versions(str(int(cuda_support_ver * 10)), 'cu128') >= 0:
                return 'cu128'
            if compare_versions(str(int(cuda_support_ver * 10)), 'cu126') >= 0:
                return 'cu126'
        if use_xpu and has_xpu:
            return 'xpu'
        if has_gpus:
            return 'cu129'
    if compare_versions(torch_ver, '2.9.0') >= 0:
        # torch >= 2.9.0: default cu130
        if compare_versions(str(int(cuda_support_ver * 10)), 'cu130') < 0:
            if compare_versions(str(int(cuda_support_ver * 10)), 'cu128') >= 0:
                return 'cu128'
            if compare_versions(str(int(cuda_support_ver * 10)), 'cu126') >= 0:
                return 'cu126'
        if use_xpu and has_xpu:
            return 'xpu'
        if has_gpus:
            return 'cu130'

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
        cu130 {
            Print-Msg "设置 PyTorch 镜像源类型为 cu130"
            $pytorch_mirror_type = "cu130"
            $mirror_index_url = if ($USE_PIP_MIRROR) {
                $PIP_EXTRA_INDEX_MIRROR_CU130_NJU
            } else {
                $PIP_EXTRA_INDEX_MIRROR_CU130
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

    if compare_versions(cuda_support_ver, '13.0') >= 0:
        return 'cu130'
    elif compare_versions(cuda_support_ver, '12.9') >= 0:
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
        cu130 {
            $pytorch_package = "torch==2.10.0+cu130 torchvision==0.25.0+cu130 torchaudio==2.10.0+cu130"
            $xformers_package = "xformers==0.0.34"
            break
        }
        cu129 {
            $pytorch_package = "torch==2.8.0+cu129 torchvision==0.23.0+cu129 torchaudio==2.8.0+cu129"
            $xformers_package = "xformers==0.0.32.post2"
            break
        }
        cu128 {
            $pytorch_package = "torch==2.10.0+cu128 torchvision==0.25.0+cu128 torchaudio==2.10.0+cu128"
            $xformers_package = "xformers==0.0.34"
            break
        }
        cu126 {
            $pytorch_package = "torch==2.10.0+cu126 torchvision==0.25.0+cu126 torchaudio==2.10.0+cu126"
            $xformers_package = "xformers==0.0.34"
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
            $pytorch_package = "torch==2.10.0+xpu torchvision==0.25.0+xpu torchaudio==2.10.0+xpu"
            $xformers_package = $null
            break
        }
        cpu {
            $pytorch_package = "torch==2.10.0+cpu torchvision==0.25.0+cpu torchaudio==2.10.0+cpu"
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
            Print-Msg "PyTorch 安装失败, 终止 Qwen TTS WebUI 安装进程, 可尝试重新运行 Qwen TTS WebUI Installer 重试失败的安装"
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


# 安装 Qwen TTS WebUI 依赖
function Install-Qwen-TTS-WebUI-Dependence {
    # 记录脚本所在路径
    $current_path = $(Get-Location).ToString()
    Set-Location "$InstallPath/$Env:CORE_PREFIX"
    $dep_path = "$InstallPath/$Env:CORE_PREFIX/requirements.txt"

    Print-Msg "安装 Qwen TTS WebUI 依赖中"
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
        Print-Msg "Qwen TTS WebUI 依赖安装成功"
    } else {
        Print-Msg "Qwen TTS WebUI 依赖安装失败, 终止 Qwen TTS WebUI 安装进程, 可尝试重新运行 Qwen TTS WebUI Installer 重试失败的安装"
        Set-Location "$current_path"
        if (!($BuildMode)) {
            Read-Host | Out-Null
        }
        exit 1
    }
    Set-Location "$current_path"
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

    # Qwen TTS WebUI 核心
    Git-CLone "$QWEN_TTS_WEBUI_REPO" "$InstallPath/$Env:CORE_PREFIX"

    Install-PyTorch
    Install-Qwen-TTS-WebUI-Dependence

    if (!(Test-Path "$InstallPath/launch_args.txt")) {
        Print-Msg "设置默认 Qwen TTS WebUI 启动参数"
        $content = ""
        Set-Content -Encoding UTF8 -Path "$InstallPath/launch_args.txt" -Value $content
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
    `$prefix_list = @(`"core`", `"QwenTTSWebUI`", `"qwen-tts-webui`", `"qwen_tts_webui_portable`")
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
# Qwen TTS WebUI Installer 版本和检查更新间隔
`$QWEN_TTS_WEBUI_INSTALLER_VERSION = $QWEN_TTS_WEBUI_INSTALLER_VERSION
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
`$PIP_EXTRA_INDEX_MIRROR_CU130_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU130_NJU`"
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
`$Env:PYTHONWARNINGS = `"$Env:PYTHONWARNINGS`"
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
function Get-Qwen-TTS-WebUI-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-DisablePyPIMirror] [-DisableUpdate] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>] [-DisableUV] [-LaunchArg <Qwen TTS WebUI 启动参数>] [-EnableShortcut] [-DisableCUDAMalloc] [-DisableEnvCheck] [-DisableAutoApplyUpdate]

参数:
    -Help
        获取 Qwen TTS WebUI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -BuildMode
        启用 Qwen TTS WebUI Installer 构建模式

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableUpdate
        禁用 Qwen TTS WebUI Installer 更新检查

    -DisableProxy
        禁用 Qwen TTS WebUI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableHuggingFaceMirror
        禁用 HuggingFace 镜像源, 不使用 HuggingFace 镜像源下载文件

    -UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>
        使用自定义 HuggingFace 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror ```"https://hf-mirror.com```" 设置 HuggingFace 镜像源地址

    -DisableUV
        禁用 Qwen TTS WebUI Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -LaunchArg <Qwen TTS WebUI 启动参数>
        设置 Qwen TTS WebUI 自定义启动参数, 如启用 --disable-offload-from-vram 和 --disable-analytics, 则使用 -LaunchArg ```"--disable-offload-from-vram --disable-analytics```" 进行启用

    -EnableShortcut
        创建 Qwen TTS WebUI 启动快捷方式

    -DisableCUDAMalloc
        禁用 Qwen TTS WebUI Installer 通过 PYTORCH_CUDA_ALLOC_CONF / PYTORCH_ALLOC_CONF 环境变量设置 CUDA 内存分配器

    -DisableEnvCheck
        禁用 Qwen TTS WebUI Installer 检查 Qwen TTS WebUI 运行环境中存在的问题, 禁用后可能会导致 Qwen TTS WebUI 环境中存在的问题无法被发现并修复

    -DisableAutoApplyUpdate
        禁用 Qwen TTS WebUI Installer 自动应用新版本更新


更多的帮助信息请阅读 Qwen TTS WebUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[Qwen TTS WebUI Installer]`" -ForegroundColor Cyan -NoNewline
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


# 显示 Qwen TTS WebUI Installer 版本
function Get-Qwen-TTS-WebUI-Installer-Version {
    `$ver = `$([string]`$QWEN_TTS_WEBUI_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"Qwen TTS WebUI Installer 版本: v`${major}.`${minor}.`${micro}`"
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


# Qwen TTS WebUI Installer 更新检测
function Check-Qwen-TTS-WebUI-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/qwen_tts_webui_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 Qwen TTS WebUI Installer 的自动检查更新功能`"
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
        Print-Msg `"检查 Qwen TTS WebUI Installer 更新中`"
        try {
            `$web_request_params = @{
                Uri = `$url
                UseBasicParsing = `$true
                OutFile = `"`$Env:CACHE_HOME/qwen_tts_webui_installer.ps1`"
            }
            Invoke-WebRequest @web_request_params
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/qwen_tts_webui_installer.ps1`" |
                Select-String -Pattern `"QWEN_TTS_WEBUI_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 Qwen TTS WebUI Installer 更新中`"
            } else {
                Print-Msg `"检查 Qwen TTS WebUI Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -le `$QWEN_TTS_WEBUI_INSTALLER_VERSION) {
        Print-Msg `"Qwen TTS WebUI Installer 已是最新版本`"
        return
    }

    if ((`$DisableAutoApplyUpdate) -or (Test-Path `"`$PSScriptRoot/disable_auto_apply_update.txt`")) {
        Print-Msg `"检测到 Qwen TTS WebUI Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"===============================================>`").Trim()
        if (!(`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`")) {
            Print-Msg `"跳过 Qwen TTS WebUI Installer 更新`"
            return
        }
    } else {
        Print-Msg `"检测到 Qwen TTS WebUI Installer 有新版本可用`"
    }

    Print-Msg `"调用 Qwen TTS WebUI Installer 进行更新中`"
    . `"`$Env:CACHE_HOME/qwen_tts_webui_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
    `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
    Print-Msg `"更新结束, 重新启动 Qwen TTS WebUI Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
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
    
    if compare_versions(uv_ver, uv_minimum_ver) < 0:
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


# Qwen TTS WebUI 启动参数
function Get-Qwen-TTS-WebUI-Launch-Args {
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


# 设置 Qwen TTS WebUI 的快捷启动方式
function Create-Qwen-TTS-WebUI-Shortcut {
    `$filename = `"qwen-tts-webui`"
    `$url = `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/gradio_icon.ico`"
    `$shortcut_icon = `"`$PSScriptRoot/gradio_icon.ico`"

    if ((!(Test-Path `"`$PSScriptRoot/enable_shortcut.txt`")) -and (!(`$EnableShortcut))) {
        return
    }

    Print-Msg `"检测到 enable_shortcut.txt 配置文件 / -EnableShortcut 命令行参数, 开始检查 Qwen TTS WebUI 快捷启动方式中`"
    if (!(Test-Path `"`$shortcut_icon`")) {
        Print-Msg `"获取 Qwen TTS WebUI 图标中`"
        `$web_request_params = @{
            Uri = `$url
            UseBasicParsing = `$true
            OutFile = `"`$PSScriptRoot/gradio_icon.ico`"
        }
        Invoke-WebRequest @web_request_params
        if (!(`$?)) {
            Print-Msg `"获取 Qwen TTS WebUI 图标失败, 无法创建 Qwen TTS WebUI 快捷启动方式`"
            return
        }
    }

    Print-Msg `"更新 Qwen TTS WebUI 快捷启动方式`"
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
            `$Env:PYTORCH_CUDA_ALLOC_CONF = `"backend:cudaMallocAsync`" # PyTorch 将弃用该参数
            `$Env:PYTORCH_ALLOC_CONF = `"backend:cudaMallocAsync`"
        }
        pytorch_malloc {
            Print-Msg `"设置 CUDA 内存分配器为 PyTorch 原生分配器`"
            `$Env:PYTORCH_CUDA_ALLOC_CONF = `"garbage_collection_threshold:0.9,max_split_size_mb:512`" # PyTorch 将弃用该参数
            `$Env:PYTORCH_ALLOC_CONF = `"garbage_collection_threshold:0.9,max_split_size_mb:512`"
        }
        Default {
            Print-Msg `"显卡非 Nvidia 显卡, 无法设置 CUDA 内存分配器`"
        }
    }
}


# 检查 Qwen TTS WebUI 依赖完整性
function Check-Qwen-TTS-WebUI-Requirements {
    `$content = `"
import inspect
import platform
import re
import os
import sys
import copy
import logging
import argparse
import importlib.metadata
from pathlib import Path
from typing import Any, Callable, NamedTuple


def get_args() -> argparse.Namespace:
    ```"```"```"获取命令行参数输入参数输入```"```"```"
    parser = argparse.ArgumentParser(description=```"运行环境检查```")

    def _normalized_filepath(filepath):
        return Path(filepath).absolute().as_posix()

    parser.add_argument(
        ```"--requirement-path```",
        type=_normalized_filepath,
        default=None,
        help=```"依赖文件路径```",
    )
    parser.add_argument(```"--debug-mode```", action=```"store_true```", help=```"显示调试信息```")

    return parser.parse_args()


COMMAND_ARGS = get_args()


class LoggingColoredFormatter(logging.Formatter):
    ```"```"```"Logging 格式化类

    Attributes:
        color (bool): 是否启用日志颜色
        COLORS (dict[str, str]): 颜色类型字典
    ```"```"```"

    COLORS = {
        ```"DEBUG```": ```"\033[0;36m```",  # CYAN
        ```"INFO```": ```"\033[0;32m```",  # GREEN
        ```"WARNING```": ```"\033[0;33m```",  # YELLOW
        ```"ERROR```": ```"\033[0;31m```",  # RED
        ```"CRITICAL```": ```"\033[0;37;41m```",  # WHITE ON RED
        ```"RESET```": ```"\033[0m```",  # RESET COLOR
    }

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        color: bool | None = True,
    ) -> None:
        ```"```"```"Logging 初始化

        Args:
            fmt (str | None): 日志消息的格式字符串
            datefmt (str | None): 日期 / 时间的显示格式
            color (bool | None): 是否启用彩色日志输出. 默认为 True
        ```"```"```"
        super().__init__(fmt, datefmt)
        self.color = color

    def format(self, record: logging.LogRecord) -> str:
        colored_record = copy.copy(record)
        levelname = colored_record.levelname

        if self.color:
            seq = self.COLORS.get(levelname, self.COLORS[```"RESET```"])
            colored_record.levelname = f```"{seq}{levelname}{self.COLORS['RESET']}```"

        return super().format(colored_record)


def get_logger(
    name: str | None = None, level: int | None = logging.INFO, color: bool | None = True
) -> logging.Logger:
    ```"```"```"获取 Loging 对象

    Args:
        name (str | None): Logging 名称
        level (int | None): 日志级别
        color (bool | None): 是否启用彩色日志
    Returns:
        logging.Logger: Logging 对象
    ```"```"```"
    stack = inspect.stack()
    calling_filename = os.path.basename(stack[1].filename)
    if name is None:
        name = calling_filename

    _logger = logging.getLogger(name)
    _logger.propagate = False

    if not _logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            LoggingColoredFormatter(
                r```"[%(name)s]-|%(asctime)s|-%(levelname)s: %(message)s```",
                r```"%Y-%m-%d %H:%M:%S```",
                color=color,
            )
        )
        _logger.addHandler(handler)

    _logger.setLevel(level)
    _logger.debug(```"Logger 初始化完成```")

    return _logger


logger = get_logger(
    name=```"Requirement Checker```",
    level=logging.DEBUG if COMMAND_ARGS.debug_mode else logging.INFO,
)


class PyWhlVersionComponent(NamedTuple):
    ```"```"```"Python 版本号组件

    参考: https://peps.python.org/pep-0440

    Attributes:
        epoch (int): 版本纪元号, 用于处理不兼容的重大更改, 默认为 0
        release (list[int]): 发布版本号段, 主版本号的数字部分, 如 [1, 2, 3]
        pre_l (str | None): 预发布标签, 包括 'a', 'b', 'rc', 'alpha' 等
        pre_n (int | None): 预发布版本编号, 与预发布标签配合使用
        post_n1 (int | None): 后发布版本编号, 格式如 1.0-1 中的数字
        post_l (str | None): 后发布标签, 如 'post', 'rev', 'r' 等
        post_n2 (int | None): 后发布版本编号, 格式如 1.0-post1 中的数字
        dev_l (str | None): 开发版本标签, 通常为 'dev'
        dev_n (int | None): 开发版本编号, 如 dev1 中的数字
        local (str | None): 本地版本标识符, 加号后面的部分
        is_wildcard (bool): 标记是否包含通配符, 用于版本范围匹配
    ```"```"```"

    epoch: int
    ```"```"```"版本纪元号, 用于处理不兼容的重大更改, 默认为 0```"```"```"

    release: list[int]
    ```"```"```"发布版本号段, 主版本号的数字部分, 如 [1, 2, 3]```"```"```"

    pre_l: str | None
    ```"```"```"预发布标签, 包括 'a', 'b', 'rc', 'alpha' 等```"```"```"

    pre_n: int | None
    ```"```"```"预发布版本编号, 与预发布标签配合使用```"```"```"

    post_n1: int | None
    ```"```"```"后发布版本编号, 格式如 1.0-1 中的数字```"```"```"

    post_l: str | None
    ```"```"```"后发布标签, 如 'post', 'rev', 'r' 等```"```"```"

    post_n2: int | None
    ```"```"```"post_n2 (int | None): 后发布版本编号, 格式如 1.0-post1 中的数字```"```"```"

    dev_l: str | None
    ```"```"```"开发版本标签, 通常为 'dev'```"```"```"

    dev_n: int | None
    ```"```"```"开发版本编号, 如 dev1 中的数字```"```"```"

    local: str | None
    ```"```"```"本地版本标识符, 加号后面的部分```"```"```"

    is_wildcard: bool
    ```"```"```"标记是否包含通配符, 用于版本范围匹配```"```"```"


class PyWhlVersionComparison:
    ```"```"```"Python 版本号比较工具

    使用:
    ````````````python
    # 常规版本匹配
    PyWhlVersionComparison(```"2.0.0```") < PyWhlVersionComparison(```"2.3.0+cu118```") # True
    PyWhlVersionComparison(```"2.0```") > PyWhlVersionComparison(```"0.9```") # True
    PyWhlVersionComparison(```"1.3```") <= PyWhlVersionComparison(```"1.2.2```") # False

    # 通配符版本匹配, 需要在不包含通配符的版本对象中使用 ~ 符号
    PyWhlVersionComparison(```"1.0*```") == ~PyWhlVersionComparison(```"1.0a1```") # True
    PyWhlVersionComparison(```"0.9*```") == ~PyWhlVersionComparison(```"1.0```") # False
    ````````````

    Attributes:
        VERSION_PATTERN (str): 提去 Wheel 版本号的正则表达式
        WHL_VERSION_PARSE_REGEX (re.Pattern): 编译后的用于解析 Wheel 版本号的工具
        version (str): 版本号字符串
    ```"```"```"

    def __init__(self, version: str) -> None:
        ```"```"```"初始化 Python 版本号比较工具

        Args:
            version (str): 版本号字符串
        ```"```"```"
        self.version = version

    def __lt__(self, other: object) -> bool:
        ```"```"```"实现 < 符号的版本比较

        Args:
            other (object): 用于比较的对象
        Returns:
            bool: 如果此版本小于另一个版本
        ```"```"```"
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return self.is_v1_lt_v2(self.version, other.version)

    def __gt__(self, other: object) -> bool:
        ```"```"```"实现 > 符号的版本比较

        Args:
            other (object): 用于比较的对象
        Returns:
            bool: 如果此版本大于另一个版本
        ```"```"```"
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return self.is_v1_gt_v2(self.version, other.version)

    def __le__(self, other: object) -> bool:
        ```"```"```"实现 <= 符号的版本比较

        Args:
            other (object): 用于比较的对象
        Returns:
            bool: 如果此版本小于等于另一个版本
        ```"```"```"
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return self.is_v1_le_v2(self.version, other.version)

    def __ge__(self, other: object) -> bool:
        ```"```"```"实现 >= 符号的版本比较

        Args:
            other (object): 用于比较的对象
        Returns:
            bool: 如果此版本大于等于另一个版本
        ```"```"```"
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return self.is_v1_ge_v2(self.version, other.version)

    def __eq__(self, other: object) -> bool:
        ```"```"```"实现 == 符号的版本比较

        Args:
            other (object): 用于比较的对象
        Returns:
            bool: 如果此版本等于另一个版本
        ```"```"```"
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return self.is_v1_eq_v2(self.version, other.version)

    def __ne__(self, other: object) -> bool:
        ```"```"```"实现 != 符号的版本比较

        Args:
            other (object): 用于比较的对象
        Returns:
            bool: 如果此版本不等于另一个版本
        ```"```"```"
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return not self.is_v1_eq_v2(self.version, other.version)

    def __invert__(self) -> ```"PyWhlVersionMatcher```":
        ```"```"```"使用 ~ 操作符实现兼容性版本匹配 (~= 的语义)

        Returns:
            PyWhlVersionMatcher: 兼容性版本匹配器
        ```"```"```"
        return PyWhlVersionMatcher(self.version)

    # 提取版本标识符组件的正则表达式
    # ref:
    # https://peps.python.org/pep-0440
    # https://packaging.python.org/en/latest/specifications/version-specifiers
    VERSION_PATTERN = r```"```"```"
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
    ```"```"```"

    # 编译正则表达式
    WHL_VERSION_PARSE_REGEX = re.compile(
        r```"^\s*```" + VERSION_PATTERN + r```"\s*$```",
        re.VERBOSE | re.IGNORECASE,
    )

    def parse_version(self, version_str: str) -> PyWhlVersionComponent:
        ```"```"```"解释 Python 软件包版本号

        Args:
            version_str (str): Python 软件包版本号

        Returns:
            PyWhlVersionComponent: 版本组件的命名元组

        Raises:
            ValueError: 如果 Python 版本号不符合 PEP440 规范
        ```"```"```"
        # 检测并剥离通配符
        wildcard = version_str.endswith(```".*```") or version_str.endswith(```"*```")
        clean_str = version_str.rstrip(```"*```").rstrip(```".```") if wildcard else version_str

        match = self.WHL_VERSION_PARSE_REGEX.match(clean_str)
        if not match:
            logger.debug(```"未知的版本号字符串: %s```", version_str)
            raise ValueError(f```"未知的版本号字符串: {version_str}```")

        components = match.groupdict()

        # 处理 release 段 (允许空字符串)
        release_str = components[```"release```"] or ```"0```"
        release_segments = [int(seg) for seg in release_str.split(```".```")]

        # 构建命名元组
        return PyWhlVersionComponent(
            epoch=int(components[```"epoch```"] or 0),
            release=release_segments,
            pre_l=components[```"pre_l```"],
            pre_n=int(components[```"pre_n```"]) if components[```"pre_n```"] else None,
            post_n1=int(components[```"post_n1```"]) if components[```"post_n1```"] else None,
            post_l=components[```"post_l```"],
            post_n2=int(components[```"post_n2```"]) if components[```"post_n2```"] else None,
            dev_l=components[```"dev_l```"],
            dev_n=int(components[```"dev_n```"]) if components[```"dev_n```"] else None,
            local=components[```"local```"],
            is_wildcard=wildcard,
        )

    def compare_version_objects(
        self, v1: PyWhlVersionComponent, v2: PyWhlVersionComponent
    ) -> int:
        ```"```"```"比较两个版本字符串 Python 软件包版本号

        Args:
            v1 (PyWhlVersionComponent): 第 1 个 Python 版本号标识符组件
            v2 (PyWhlVersionComponent): 第 2 个 Python 版本号标识符组件

        Returns:
            int: 如果版本号 1 大于 版本号 2, 则返回````1````, 小于则返回````-1````, 如果相等则返回````0````
        ```"```"```"

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
        # 如果 release 长度不同, 较短的版本号视为较小 ?
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
                ```"a```": 0,
                ```"b```": 1,
                ```"c```": 2,
                ```"rc```": 3,
                ```"alpha```": 0,
                ```"beta```": 1,
                ```"pre```": 0,
                ```"preview```": 0,
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
            local1 = v1.local.split(```".```")
            local2 = v2.local.split(```".```")
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

    def compare_versions(self, version1: str, version2: str) -> int:
        ```"```"```"比较两个版本字符串 Python 软件包版本号

        Args:
            version1 (str): 版本号 1
            version2 (str): 版本号 2

        Returns:
            int: 如果版本号 1 大于 版本号 2, 则返回````1````, 小于则返回````-1````, 如果相等则返回````0````
        ```"```"```"
        v1 = self.parse_version(version1)
        v2 = self.parse_version(version2)
        return self.compare_version_objects(v1, v2)

    def compatible_version_matcher(self, spec_version: str) -> Callable[[str], bool]:
        ```"```"```"PEP 440 兼容性版本匹配 (~= 操作符)

        Returns:
            (Callable[[str], bool]): 一个接受 version_str (````str````) 参数的判断函数
        ```"```"```"
        # 解析规范版本
        spec = self.parse_version(spec_version)

        # 获取有效 release 段 (去除末尾的零)
        clean_release = []
        for num in spec.release:
            if num != 0 or (clean_release and clean_release[-1] != 0):
                clean_release.append(num)

        # 确定最低版本和前缀匹配规则
        if len(clean_release) == 0:
            logger.debug(```"解析到错误的兼容性发行版本号```")
            raise ValueError(```"解析到错误的兼容性发行版本号```")

        # 生成前缀匹配模板 (忽略后缀)
        prefix_length = len(clean_release) - 1
        if prefix_length == 0:
            # 处理类似 ~= 2 的情况 (实际 PEP 禁止, 但这里做容错)
            prefix_pattern = [spec.release[0]]
            min_version = self.parse_version(f```"{spec.release[0]}```")
        else:
            prefix_pattern = list(spec.release[:prefix_length])
            min_version = spec

        def _is_compatible(version_str: str) -> bool:
            target = self.parse_version(version_str)

            # 主版本前缀检查
            target_prefix = target.release[: len(prefix_pattern)]
            if target_prefix != prefix_pattern:
                return False

            # 最低版本检查 (自动忽略 pre/post/dev 后缀)
            return self.compare_version_objects(target, min_version) >= 0

        return _is_compatible

    def version_match(self, spec: str, version: str) -> bool:
        ```"```"```"PEP 440 版本前缀匹配

        Args:
            spec (str): 版本匹配表达式 (e.g. '1.1.*')
            version (str): 需要检测的实际版本号 (e.g. '1.1a1')

        Returns:
            bool: 是否匹配
        ```"```"```"
        # 分离通配符和本地版本
        spec_parts = spec.split(```"+```", 1)
        spec_main = spec_parts[0].rstrip(```".*```")  # 移除通配符
        has_wildcard = spec.endswith(```".*```") and ```"+```" not in spec

        # 解析规范版本 (不带通配符)
        try:
            spec_ver = self.parse_version(spec_main)
        except ValueError:
            return False

        # 解析目标版本 (忽略本地版本)
        target_ver = self.parse_version(version.split(```"+```", 1)[0])

        # 前缀匹配规则
        if has_wildcard:
            # 生成补零后的 release 段
            spec_release = spec_ver.release.copy()
            while len(spec_release) < len(target_ver.release):
                spec_release.append(0)

            # 比较前 N 个 release 段 (N 为规范版本长度)
            return (
                target_ver.release[: len(spec_ver.release)] == spec_ver.release
                and target_ver.epoch == spec_ver.epoch
            )
        else:
            # 严格匹配时使用原比较函数
            return self.compare_versions(spec_main, version) == 0

    def is_v1_ge_v2(self, v1: str, v2: str) -> bool:
        ```"```"```"查看 Python 版本号 v1 是否大于或等于 v2

        例如:
        ````````````
        1.1, 1.0 -> True
        1.0, 1.0 -> True
        0.9, 1.0 -> False
        ````````````

        Args:
            v1 (str): 第 1 个 Python 软件包版本号

            v2 (str): 第 2 个 Python 软件包版本号

        Returns:
            bool: 如果 v1 版本号大于或等于 v2 版本号则返回````True````
        ```"```"```"
        return self.compare_versions(v1, v2) >= 0

    def is_v1_gt_v2(self, v1: str, v2: str) -> bool:
        ```"```"```"查看 Python 版本号 v1 是否大于 v2

        例如:
        ````````````
        1.1, 1.0 -> True
        1.0, 1.0 -> False
        ````````````

        Args:
            v1 (str): 第 1 个 Python 软件包版本号
            v2 (str): 第 2 个 Python 软件包版本号

        Returns:
            bool: 如果 v1 版本号大于 v2 版本号则返回````True````
        ```"```"```"
        return self.compare_versions(v1, v2) > 0

    def is_v1_eq_v2(self, v1: str, v2: str) -> bool:
        ```"```"```"查看 Python 版本号 v1 是否等于 v2

        例如:
        ````````````
        1.0, 1.0 -> True
        0.9, 1.0 -> False
        1.1, 1.0 -> False
        ````````````

        Args:
            v1 (str): 第 1 个 Python 软件包版本号
            v2 (str): 第 2 个 Python 软件包版本号

        Returns:
            ````bool````: 如果 v1 版本号等于 v2 版本号则返回````True````
        ```"```"```"
        return self.compare_versions(v1, v2) == 0

    def is_v1_lt_v2(self, v1: str, v2: str) -> bool:
        ```"```"```"查看 Python 版本号 v1 是否小于 v2

        例如:
        ````````````
        0.9, 1.0 -> True
        1.0, 1.0 -> False
        ````````````

        Args:
            v1 (str): 第 1 个 Python 软件包版本号
            v2 (str): 第 2 个 Python 软件包版本号

        Returns:
            bool: 如果 v1 版本号小于 v2 版本号则返回````True````
        ```"```"```"
        return self.compare_versions(v1, v2) < 0

    def is_v1_le_v2(self, v1: str, v2: str) -> bool:
        ```"```"```"查看 Python 版本号 v1 是否小于或等于 v2

        例如:
        ````````````
        0.9, 1.0 -> True
        1.0, 1.0 -> True
        1.1, 1.0 -> False
        ````````````

        Args:
            v1 (str): 第 1 个 Python 软件包版本号
            v2 (str): 第 2 个 Python 软件包版本号

        Returns:
            bool: 如果 v1 版本号小于或等于 v2 版本号则返回````True````
        ```"```"```"
        return self.compare_versions(v1, v2) <= 0

    def is_v1_c_eq_v2(self, v1: str, v2: str) -> bool:
        ```"```"```"查看 Python 版本号 v1 是否大于等于 v2, (兼容性版本匹配)

        例如:
        ````````````
        1.0*, 1.0a1 -> True
        0.9*, 1.0 -> False
        ````````````

        Args:
            v1 (str): 第 1 个 Python 软件包版本号, 该版本由 ~= 符号指定
            v2 (str): 第 2 个 Python 软件包版本号

        Returns:
            bool: 如果 v1 版本号等于 v2 版本号则返回````True````
        ```"```"```"
        func = self.compatible_version_matcher(v1)
        return func(v2)


class PyWhlVersionMatcher:
    ```"```"```"Python 兼容性版本匹配器, 用于实现 ~= 操作符的语义

    Attributes:
        spec_version (str): 版本号
        comparison (PyWhlVersionComparison): Python 版本号比较工具
        _matcher_func (Callable[[str], bool]): 兼容性版本匹配函数
    ```"```"```"

    def __init__(self, spec_version: str) -> None:
        ```"```"```"初始化 Python 兼容性版本匹配器

        Args:
            spec_version (str): 版本号
        ```"```"```"
        self.spec_version = spec_version
        self.comparison = PyWhlVersionComparison(spec_version)
        self._matcher_func = self.comparison.compatible_version_matcher(spec_version)

    def __eq__(self, other: object) -> bool:
        ```"```"```"实现 ~version == other_version 的语义
        Args:
            other (object): 用于比较的对象
        Returns:
            bool: 如果此版本不等于另一个版本
        ```"```"```"
        if isinstance(other, str):
            return self._matcher_func(other)
        elif isinstance(other, PyWhlVersionComparison):
            return self._matcher_func(other.version)
        elif isinstance(other, PyWhlVersionMatcher):
            # 允许 ~v1 == ~v2 的比较 (比较规范版本)
            return self.spec_version == other.spec_version
        return NotImplemented

    def __repr__(self) -> str:
        return f```"~{self.spec_version}```"


class ParsedPyWhlRequirement(NamedTuple):
    ```"```"```"解析后的依赖声明信息

    参考: https://peps.python.org/pep-0508
    ```"```"```"

    name: str
    ```"```"```"软件包名称```"```"```"

    extras: list[str]
    ```"```"```"extras 列表，例如 ['fred', 'bar']```"```"```"

    specifier: list[tuple[str, str]] | str
    ```"```"```"版本约束列表或 URL 地址

    如果是版本依赖，则为版本约束列表，例如 [('>=', '1.0'), ('<', '2.0')]
    如果是 URL 依赖，则为 URL 字符串，例如 'http://example.com/package.tar.gz'
    ```"```"```"

    marker: Any
    ```"```"```"环境标记表达式，用于条件依赖```"```"```"


class Parser:
    ```"```"```"语法解析器

    Attributes:
        text (str): 待解析的字符串
        pos (int): 字符起始位置
        len (int): 字符串长度
    ```"```"```"

    def __init__(self, text: str) -> None:
        ```"```"```"初始化解析器

        Args:
            text (str): 要解析的文本
        ```"```"```"
        self.text = text
        self.pos = 0
        self.len = len(text)

    def peek(self) -> str:
        ```"```"```"查看当前位置的字符但不移动指针

        Returns:
            str: 当前位置的字符，如果到达末尾则返回空字符串
        ```"```"```"
        if self.pos < self.len:
            return self.text[self.pos]
        return ```"```"

    def consume(self, expected: str | None = None) -> str:
        ```"```"```"消耗当前字符并移动指针

        Args:
            expected (str | None): 期望的字符，如果提供但不匹配会抛出异常

        Returns:
            str: 实际消耗的字符

        Raises:
            ValueError: 当字符不匹配或到达文本末尾时
        ```"```"```"
        if self.pos >= self.len:
            raise ValueError(f```"不期望的输入内容结尾, 期望: {expected}```")

        char = self.text[self.pos]
        if expected and char != expected:
            raise ValueError(f```"期望 '{expected}', 得到 '{char}' 在位置 {self.pos}```")

        self.pos += 1
        return char

    def skip_whitespace(self):
        ```"```"```"跳过空白字符（空格和制表符）```"```"```"
        while self.pos < self.len and self.text[self.pos] in ```" \t```":
            self.pos += 1

    def match(self, pattern: str) -> str | None:
        ```"```"```"尝试匹配指定模式, 成功则移动指针

        Args:
            pattern (str): 要匹配的模式字符串

        Returns:
            (str | None): 匹配成功的字符串, 否则为 None
        ```"```"```"
        # 跳过空格再匹配
        original_pos = self.pos
        self.skip_whitespace()

        if self.text.startswith(pattern, self.pos):
            result = self.text[self.pos : self.pos + len(pattern)]
            self.pos += len(pattern)
            return result

        # 如果没有匹配，恢复位置
        self.pos = original_pos
        return None

    def read_while(self, condition) -> str:
        ```"```"```"读取满足条件的字符序列

        Args:
            condition: 判断字符是否满足条件的函数

        Returns:
            str: 满足条件的字符序列
        ```"```"```"
        start = self.pos
        while self.pos < self.len and condition(self.text[self.pos]):
            self.pos += 1
        return self.text[start : self.pos]

    def eof(self) -> bool:
        ```"```"```"检查是否到达文本末尾

        Returns:
            bool: 如果到达末尾返回 True, 否则返回 False
        ```"```"```"
        return self.pos >= self.len


class RequirementParser(Parser):
    ```"```"```"Python 软件包解析工具

    Attributes:
        bindings (dict[str, str] | None): 解析语法
    ```"```"```"

    def __init__(self, text: str, bindings: dict[str, str] | None = None):
        ```"```"```"初始化依赖声明解析器

        Args:
            text (str): 覫解析的依赖声明文本
            bindings (dict[str, str] | None): 环境变量绑定字典
        ```"```"```"
        super().__init__(text)
        self.bindings = bindings or {}

    def parse(self) -> ParsedPyWhlRequirement:
        ```"```"```"解析依赖声明，返回 (name, extras, version_specs / url, marker)

        Returns:
            ParsedPyWhlRequirement: 解析结果元组
        ```"```"```"
        self.skip_whitespace()

        # 首先解析名称
        name = self.parse_identifier()
        self.skip_whitespace()

        # 解析 extras
        extras = []
        if self.peek() == ```"[```":
            extras = self.parse_extras()
            self.skip_whitespace()

        # 检查是 URL 依赖还是版本依赖
        if self.peek() == ```"@```":
            # URL依赖
            self.consume(```"@```")
            self.skip_whitespace()
            url = self.parse_url()
            self.skip_whitespace()

            # 解析可选的 marker
            marker = None
            if self.match(```";```"):
                marker = self.parse_marker()

            return ParsedPyWhlRequirement(name, extras, url, marker)
        else:
            # 版本依赖
            versions = []
            # 检查是否有版本约束 (不是以分号开头)
            if not self.eof() and self.peek() not in (```";```", ```",```"):
                versions = self.parse_versionspec()
                self.skip_whitespace()

            # 解析可选的 marker
            marker = None
            if self.match(```";```"):
                marker = self.parse_marker()

            return ParsedPyWhlRequirement(name, extras, versions, marker)

    def parse_identifier(self) -> str:
        ```"```"```"解析标识符

        Returns:
            str: 解析得到的标识符
        ```"```"```"

        def is_identifier_char(c):
            return c.isalnum() or c in ```"-_.```"

        result = self.read_while(is_identifier_char)
        if not result:
            raise ValueError(```"应为预期标识符```")
        return result

    def parse_extras(self) -> list[str]:
        ```"```"```"解析 extras 列表

        Returns:
            list[str]: extras 列表
        ```"```"```"
        self.consume(```"[```")
        self.skip_whitespace()

        extras = []
        if self.peek() != ```"]```":
            extras.append(self.parse_identifier())
            self.skip_whitespace()

            while self.match(```",```"):
                self.skip_whitespace()
                extras.append(self.parse_identifier())
                self.skip_whitespace()

        self.consume(```"]```")
        return extras

    def parse_versionspec(self) -> list[tuple[str, str]]:
        ```"```"```"解析版本约束

        Returns:
            list[tuple[str, str]]: 版本约束列表
        ```"```"```"
        if self.match(```"(```"):
            versions = self.parse_version_many()
            self.consume(```")```")
            return versions
        else:
            return self.parse_version_many()

    def parse_version_many(self) -> list[tuple[str, str]]:
        ```"```"```"解析多个版本约束

        Returns:
            list[tuple[str, str]]: 多个版本约束组成的列表
        ```"```"```"
        versions = [self.parse_version_one()]
        self.skip_whitespace()

        while self.match(```",```"):
            self.skip_whitespace()
            versions.append(self.parse_version_one())
            self.skip_whitespace()

        return versions

    def parse_version_one(self) -> tuple[str, str]:
        ```"```"```"解析单个版本约束

        Returns:
            tuple[str, str]: (操作符, 版本号) 元组
        ```"```"```"
        op = self.parse_version_cmp()
        self.skip_whitespace()
        version = self.parse_version()
        return (op, version)

    def parse_version_cmp(self) -> str:
        ```"```"```"解析版本比较操作符

        Returns:
            str: 版本比较操作符

        Raises:
            ValueError: 当找不到有效的版本比较操作符时
        ```"```"```"
        operators = [```"<=```", ```">=```", ```"==```", ```"!=```", ```"~=```", ```"===```", ```"<```", ```">```"]

        for op in operators:
            if self.match(op):
                return op

        raise ValueError(f```"预期在位置 {self.pos} 处出现版本比较符```")

    def parse_version(self) -> str:
        ```"```"```"解析版本号

        Returns:
            str: 版本号字符串

        Raises:
            ValueError: 当找不到有效版本号时
        ```"```"```"

        def is_version_char(c):
            return c.isalnum() or c in ```"-_.*+!```"

        version = self.read_while(is_version_char)
        if not version:
            raise ValueError(```"期望为版本字符串```")
        return version

    def parse_url(self) -> str:
        ```"```"```"解析 URL (简化版本)

        Returns:
            str: URL 字符串

        Raises:
            ValueError: 当找不到有效 URL 时
        ```"```"```"
        # 读取直到遇到空白或分号
        start = self.pos
        while self.pos < self.len and self.text[self.pos] not in ```" \t;```":
            self.pos += 1
        url = self.text[start : self.pos]

        if not url:
            raise ValueError(```"@ 后的预期 URL```")

        return url

    def parse_marker(self) -> Any:
        ```"```"```"解析 marker 表达式

        Returns:
            Any: 解析后的 marker 表达式
        ```"```"```"
        self.skip_whitespace()
        return self.parse_marker_or()

    def parse_marker_or(self) -> Any:
        ```"```"```"解析 OR 表达式

        Returns:
            Any: 解析后的 OR 表达式
        ```"```"```"
        left = self.parse_marker_and()
        self.skip_whitespace()

        if self.match(```"or```"):
            self.skip_whitespace()
            right = self.parse_marker_or()
            return (```"or```", left, right)

        return left

    def parse_marker_and(self) -> Any:
        ```"```"```"解析 AND 表达式

        Returns:
            Any: 解析后的 AND 表达式
        ```"```"```"
        left = self.parse_marker_expr()
        self.skip_whitespace()

        if self.match(```"and```"):
            self.skip_whitespace()
            right = self.parse_marker_and()
            return (```"and```", left, right)

        return left

    def parse_marker_expr(self) -> Any:
        ```"```"```"解析基础 marker 表达式

        Returns:
            Any: 解析后的基础表达式
        ```"```"```"
        self.skip_whitespace()

        if self.peek() == ```"(```":
            self.consume(```"(```")
            expr = self.parse_marker()
            self.consume(```")```")
            return expr

        left = self.parse_marker_var()
        self.skip_whitespace()

        op = self.parse_marker_op()
        self.skip_whitespace()

        right = self.parse_marker_var()

        return (op, left, right)

    def parse_marker_var(self) -> str:
        ```"```"```"解析 marker 变量

        Returns:
            str: 解析得到的变量值
        ```"```"```"
        self.skip_whitespace()

        # 检查是否是环境变量
        env_vars = [
            ```"python_version```",
            ```"python_full_version```",
            ```"os_name```",
            ```"sys_platform```",
            ```"platform_release```",
            ```"platform_system```",
            ```"platform_version```",
            ```"platform_machine```",
            ```"platform_python_implementation```",
            ```"implementation_name```",
            ```"implementation_version```",
            ```"extra```",
        ]

        for var in env_vars:
            if self.match(var):
                # 返回绑定的值，如果不存在则返回变量名
                return self.bindings.get(var, var)

        # 否则解析为字符串
        return self.parse_python_str()

    def parse_marker_op(self) -> str:
        ```"```"```"解析 marker 操作符

        Returns:
            str: marker 操作符

        Raises:
            ValueError: 当找不到有效操作符时
        ```"```"```"
        # 版本比较操作符
        version_ops = [```"<=```", ```">=```", ```"==```", ```"!=```", ```"~=```", ```"===```", ```"<```", ```">```"]
        for op in version_ops:
            if self.match(op):
                return op

        # in 操作符
        if self.match(```"in```"):
            return ```"in```"

        # not in 操作符
        if self.match(```"not```"):
            self.skip_whitespace()
            if self.match(```"in```"):
                return ```"not in```"
            raise ValueError(```"预期在 'not' 之后出现 'in'```")

        raise ValueError(f```"在位置 {self.pos} 处应出现标记运算符```")

    def parse_python_str(self) -> str:
        ```"```"```"解析 Python 字符串

        Returns:
            str: 解析得到的字符串
        ```"```"```"
        self.skip_whitespace()

        if self.peek() == '```"':
            return self.parse_quoted_string('```"')
        elif self.peek() == ```"'```":
            return self.parse_quoted_string(```"'```")
        else:
            # 如果没有引号，读取标识符
            return self.parse_identifier()

    def parse_quoted_string(self, quote: str) -> str:
        ```"```"```"解析引号字符串

        Args:
            quote (str): 引号字符

        Returns:
            str: 解析得到的字符串

        Raises:
            ValueError: 当字符串未正确闭合时
        ```"```"```"
        self.consume(quote)
        result = []

        while self.pos < self.len and self.text[self.pos] != quote:
            if self.text[self.pos] == ```"\\```":  # 处理转义
                self.pos += 1
                if self.pos < self.len:
                    result.append(self.text[self.pos])
                    self.pos += 1
            else:
                result.append(self.text[self.pos])
                self.pos += 1

        if self.pos >= self.len:
            raise ValueError(f```"未闭合的字符串字面量，预期为 '{quote}'```")

        self.consume(quote)
        return ```"```".join(result)


def format_full_version(info: str) -> str:
    ```"```"```"格式化完整的版本信息

    Args:
        info (str): 版本信息

    Returns:
        str: 格式化后的版本字符串
    ```"```"```"
    version = f```"{info.major}.{info.minor}.{info.micro}```"
    kind = info.releaselevel
    if kind != ```"final```":
        version += kind[0] + str(info.serial)
    return version


def get_parse_bindings() -> dict[str, str]:
    ```"```"```"获取用于解析 Python 软件包名的语法

    Returns:
        (dict[str, str]): 解析 Python 软件包名的语法字典
    ```"```"```"
    # 创建环境变量绑定
    if hasattr(sys, ```"implementation```"):
        implementation_version = format_full_version(sys.implementation.version)
        implementation_name = sys.implementation.name
    else:
        implementation_version = ```"0```"
        implementation_name = ```"```"

    bindings = {
        ```"implementation_name```": implementation_name,
        ```"implementation_version```": implementation_version,
        ```"os_name```": os.name,
        ```"platform_machine```": platform.machine(),
        ```"platform_python_implementation```": platform.python_implementation(),
        ```"platform_release```": platform.release(),
        ```"platform_system```": platform.system(),
        ```"platform_version```": platform.version(),
        ```"python_full_version```": platform.python_version(),
        ```"python_version```": ```".```".join(platform.python_version_tuple()[:2]),
        ```"sys_platform```": sys.platform,
    }
    return bindings


def version_string_is_canonical(version: str) -> bool:
    ```"```"```"判断版本号标识符是否符合标准

    Args:
        version (str): 版本号字符串
    Returns:
        bool: 如果版本号标识符符合 PEP 440 标准, 则返回````True````
    ```"```"```"
    return (
        re.match(
            r```"^([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*((a|b|rc)(0|[1-9][0-9]*))?(\.post(0|[1-9][0-9]*))?(\.dev(0|[1-9][0-9]*))?$```",
            version,
        )
        is not None
    )


def is_package_has_version(package: str) -> bool:
    ```"```"```"检查 Python 软件包是否指定版本号

    Args:
        package (str): Python 软件包名

    Returns:
        bool: 如果 Python 软件包存在版本声明, 如````torch==2.3.0````, 则返回````True````
    ```"```"```"
    return package != (
        package.replace(```"===```", ```"```")
        .replace(```"~=```", ```"```")
        .replace(```"!=```", ```"```")
        .replace(```"<=```", ```"```")
        .replace(```">=```", ```"```")
        .replace(```"<```", ```"```")
        .replace(```">```", ```"```")
        .replace(```"==```", ```"```")
    )


def get_package_name(package: str) -> str:
    ```"```"```"获取 Python 软件包的包名, 去除末尾的版本声明

    Args:
        package (str): Python 软件包名

    Returns:
        str: 返回去除版本声明后的 Python 软件包名
    ```"```"```"
    return (
        package.split(```"===```")[0]
        .split(```"~=```")[0]
        .split(```"!=```")[0]
        .split(```"<=```")[0]
        .split(```">=```")[0]
        .split(```"<```")[0]
        .split(```">```")[0]
        .split(```"==```")[0]
        .strip()
    )


def get_package_version(package: str) -> str:
    ```"```"```"获取 Python 软件包的包版本号

    Args:
        package (str): Python 软件包名

    返回值:
        str: 返回 Python 软件包的包版本号
    ```"```"```"
    return (
        package.split(```"===```")
        .pop()
        .split(```"~=```")
        .pop()
        .split(```"!=```")
        .pop()
        .split(```"<=```")
        .pop()
        .split(```">=```")
        .pop()
        .split(```"<```")
        .pop()
        .split(```">```")
        .pop()
        .split(```"==```")
        .pop()
        .strip()
    )


WHEEL_PATTERN = r```"```"```"
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
```"```"```"
```"```"```"解析 Python Wheel 名的的正则表达式```"```"```"

REPLACE_PACKAGE_NAME_DICT = {
    ```"sam2```": ```"SAM-2```",
}
```"```"```"Python 软件包名替换表```"```"```"


def parse_wheel_filename(filename: str) -> str:
    ```"```"```"解析 Python wheel 文件名并返回 distribution 名称

    Args:
        filename (str): wheel 文件名, 例如 pydantic-1.10.15-py3-none-any.whl
    Returns:
        str: distribution 名称, 例如 pydantic
    Raises:
        ValueError: 如果文件名不符合 PEP491 规范
    ```"```"```"
    match = re.fullmatch(WHEEL_PATTERN, filename, re.VERBOSE)
    if not match:
        logger.debug(```"未知的 Wheel 文件名: %s```", filename)
        raise ValueError(f```"未知的 Wheel 文件名: {filename}```")
    return match.group(```"distribution```")


def parse_wheel_version(filename: str) -> str:
    ```"```"```"解析 Python wheel 文件名并返回 version 名称

    Args:
        filename (str): wheel 文件名, 例如 pydantic-1.10.15-py3-none-any.whl
    Returns:
        str: version 名称, 例如 1.10.15
    Raises:
        ValueError: 如果文件名不符合 PEP491 规范
    ```"```"```"
    match = re.fullmatch(WHEEL_PATTERN, filename, re.VERBOSE)
    if not match:
        logger.debug(```"未知的 Wheel 文件名: %s```", filename)
        raise ValueError(f```"未知的 Wheel 文件名: {filename}```")
    return match.group(```"version```")


def parse_wheel_to_package_name(filename: str) -> str:
    ```"```"```"解析 Python wheel 文件名并返回 <distribution>==<version>

    Args:
        filename (str): wheel 文件名, 例如 pydantic-1.10.15-py3-none-any.whl

    Returns:
        str: <distribution>==<version> 名称, 例如 pydantic==1.10.15
    ```"```"```"
    distribution = parse_wheel_filename(filename)
    version = parse_wheel_version(filename)
    return f```"{distribution}=={version}```"


def remove_optional_dependence_from_package(filename: str) -> str:
    ```"```"```"移除 Python 软件包声明中可选依赖

    Args:
        filename (str): Python 软件包名

    Returns:
        str: 移除可选依赖后的软件包名, e.g. diffusers[torch]==0.10.2 -> diffusers==0.10.2
    ```"```"```"
    return re.sub(r```"\[.*?\]```", ```"```", filename)


def get_correct_package_name(name: str) -> str:
    ```"```"```"将原 Python 软件包名替换成正确的 Python 软件包名

    Args:
        name (str): 原 Python 软件包名
    Returns:
        str: 替换成正确的软件包名, 如果原有包名正确则返回原包名
    ```"```"```"
    return REPLACE_PACKAGE_NAME_DICT.get(name, name)


def parse_requirement(
    text: str,
    bindings: dict[str, str],
) -> ParsedPyWhlRequirement:
    ```"```"```"解析依赖声明的主函数

    Args:
        text (str): 依赖声明文本
        bindings (dict[str, str]): 解析 Python 软件包名的语法字典

    Returns:
        ParsedPyWhlRequirement: 解析结果元组
    ```"```"```"
    parser = RequirementParser(text, bindings)
    return parser.parse()


def evaluate_marker(marker: Any) -> bool:
    ```"```"```"评估 marker 表达式, 判断当前环境是否符合要求

    Args:
        marker (Any): marker 表达式
    Returns:
        bool: 评估结果
    ```"```"```"
    if marker is None:
        return True

    if isinstance(marker, tuple):
        op = marker[0]

        if op in (```"and```", ```"or```"):
            left = evaluate_marker(marker[1])
            right = evaluate_marker(marker[2])

            if op == ```"and```":
                return left and right
            else:  # 'or'
                return left or right
        else:
            # 处理比较操作
            left = marker[1]
            right = marker[2]

            if op in [```"<```", ```"<=```", ```">```", ```">=```", ```"==```", ```"!=```", ```"~=```", ```"===```"]:
                try:
                    left_ver = PyWhlVersionComparison(str(left).lower())
                    right_ver = PyWhlVersionComparison(str(right).lower())

                    if op == ```"<```":
                        return left_ver < right_ver
                    elif op == ```"<=```":
                        return left_ver <= right_ver
                    elif op == ```">```":
                        return left_ver > right_ver
                    elif op == ```">=```":
                        return left_ver >= right_ver
                    elif op == ```"==```":
                        return left_ver == right_ver
                    elif op == ```"!=```":
                        return left_ver != right_ver
                    elif op == ```"~=```":
                        return left_ver >= ~right_ver
                    elif op == ```"===```":
                        # 任意相等, 直接比较字符串
                        return str(left).lower() == str(right).lower()
                except Exception:
                    # 如果版本比较失败, 回退到字符串比较
                    left_str = str(left).lower()
                    right_str = str(right).lower()
                    if op == ```"<```":
                        return left_str < right_str
                    elif op == ```"<=```":
                        return left_str <= right_str
                    elif op == ```">```":
                        return left_str > right_str
                    elif op == ```">=```":
                        return left_str >= right_str
                    elif op == ```"==```":
                        return left_str == right_str
                    elif op == ```"!=```":
                        return left_str != right_str
                    elif op == ```"~=```":
                        # 简化处理
                        return left_str >= right_str
                    elif op == ```"===```":
                        return left_str == right_str

            # 处理 in 和 not in 操作
            elif op == ```"in```":
                # 将右边按逗号分割, 检查左边是否在其中
                values = [v.strip() for v in str(right).lower().split(```",```")]
                return str(left).lower() in values

            elif op == ```"not in```":
                # 将右边按逗号分割, 检查左边是否不在其中
                values = [v.strip() for v in str(right).lower().split(```",```")]
                return str(left).lower() not in values

    return False


def parse_requirement_to_list(text: str) -> list[str]:
    ```"```"```"解析依赖声明并返回依赖列表

    Args:
        text (str): 依赖声明
    Returns:
        list[str]: 解析后的依赖声明表
    ```"```"```"
    try:
        bindings = get_parse_bindings()
        name, _, version_specs, marker = parse_requirement(text, bindings)
    except Exception as e:
        logger.debug(```"解析失败: %s```", e)
        return []

    # 检查marker条件
    if not evaluate_marker(marker):
        return []

    # 构建依赖列表
    dependencies = []

    # 如果是 URL 依赖
    if isinstance(version_specs, str):
        # URL 依赖只返回包名
        dependencies.append(name)
    else:
        # 版本依赖
        if version_specs:
            # 有版本约束, 为每个约束创建一个依赖项
            for op, version in version_specs:
                dependencies.append(f```"{name}{op}{version}```")
        else:
            # 没有版本约束, 只返回包名
            dependencies.append(name)

    return dependencies


def parse_requirement_list(requirements: list[str]) -> list[str]:
    ```"```"```"将 Python 软件包声明列表解析成标准 Python 软件包名列表

    例如有以下的 Python 软件包声明列表:
    ````````````python
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
    ````````````

    上述例子中的软件包名声明列表将解析成:
    ````````````python
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
    ````````````

    Args:
        requirements (list[str]): Python 软件包名声明列表

    Returns:
        list[str]: 将 Python 软件包名声明列表解析成标准声明列表
    ```"```"```"

    def _extract_repo_name(url_string: str) -> str | None:
        ```"```"```"从包含 Git 仓库 URL 的字符串中提取仓库名称

        Args:
            url_string (str): 包含 Git 仓库 URL 的字符串

        Returns:
            (str | None): 提取到的仓库名称, 如果未找到则返回 None
        ```"```"```"
        # 模式1: 匹配 git+https:// 或 git+ssh:// 开头的 URL
        # 模式2: 匹配直接以 git+ 开头的 URL
        patterns = [
            # 匹配 git+protocol://host/path/to/repo.git 格式
            r```"git\+[a-z]+://[^/]+/(?:[^/]+/)*([^/@]+?)(?:\.git)?(?:@|$)```",
            # 匹配 git+https://host/owner/repo.git 格式
            r```"git\+https://[^/]+/[^/]+/([^/@]+?)(?:\.git)?(?:@|$)```",
            # 匹配 git+ssh://git@host:owner/repo.git 格式
            r```"git\+ssh://git@[^:]+:[^/]+/([^/@]+?)(?:\.git)?(?:@|$)```",
            # 通用模式: 匹配最后一个斜杠后的内容, 直到遇到 @ 或 .git 或字符串结束
            r```"/([^/@]+?)(?:\.git)?(?:@|$)```",
        ]

        for pattern in patterns:
            match = re.search(pattern, url_string)
            if match:
                return match.group(1)

        return None

    package_list: list[str] = []
    canonical_package_list: list[str] = []
    for requirement in requirements:
        # 清理注释内容
        # prodigy-plus-schedule-free==1.9.1 # prodigy+schedulefree optimizer -> prodigy-plus-schedule-free==1.9.1
        requirement = re.sub(r```"\s*#.*$```", ```"```", requirement).strip()
        logger.debug(```"原始 Python 软件包名: %s```", requirement)

        if (
            requirement is None
            or requirement == ```"```"
            or requirement.startswith(```"#```")
            or ```"# skip_verify```" in requirement
            or requirement.startswith(```"--index-url```")
            or requirement.startswith(```"--extra-index-url```")
            or requirement.startswith(```"--find-links```")
            or requirement.startswith(```"-e .```")
            or requirement.startswith(```"-r ```")
        ):
            continue

        # -e git+https://github.com/Nerogar/mgds.git@2c67a5a#egg=mgds -> mgds
        # git+https://github.com/WASasquatch/img2texture.git -> img2texture
        # git+https://github.com/deepghs/waifuc -> waifuc
        # -e git+https://github.com/Nerogar/mgds.git@2c67a5a -> mgds
        # git+ssh://git@github.com:licyk/sd-webui-all-in-one@dev -> sd-webui-all-in-one
        # git+https://gitlab.com/user/my-project.git@main -> my-project
        # git+ssh://git@bitbucket.org:team/repo-name.git@develop -> repo-name
        # https://github.com/another/repo.git -> repo
        # git@github.com:user/repository.git -> repository
        if (
            requirement.startswith(```"-e git+http```")
            or requirement.startswith(```"git+http```")
            or requirement.startswith(```"-e git+ssh://```")
            or requirement.startswith(```"git+ssh://```")
        ):
            egg_match = re.search(r```"egg=([^#&]+)```", requirement)
            if egg_match:
                package_list.append(egg_match.group(1).split(```"-```")[0])
                continue

            repo_name_match = _extract_repo_name(requirement)
            if repo_name_match is not None:
                package_list.append(repo_name_match)
                continue

            package_name = os.path.basename(requirement)
            package_name = (
                package_name.split(```".git```")[0]
                if package_name.endswith(```".git```")
                else package_name
            )
            package_list.append(package_name)
            continue

        # https://github.com/Panchovix/pydantic-fixreforge/releases/download/main_v1/pydantic-1.10.15-py3-none-any.whl -> pydantic==1.10.15
        if requirement.startswith(```"https://```") or requirement.startswith(```"http://```"):
            package_name = parse_wheel_to_package_name(os.path.basename(requirement))
            package_list.append(package_name)
            continue

        # 常规 Python 软件包声明
        # 解析版本列表
        possble_requirement = parse_requirement_to_list(requirement)
        if len(possble_requirement) == 0:
            continue
        elif len(possble_requirement) == 1:
            requirement = possble_requirement[0]
        else:
            requirements_list = parse_requirement_list(possble_requirement)
            package_list += requirements_list
            continue

        multi_requirements = requirement.split(```",```")
        if len(multi_requirements) > 1:
            package_name = get_package_name(multi_requirements[0].strip())
            for package_name_with_version_marked in multi_requirements:
                version_symbol = str.replace(
                    package_name_with_version_marked, package_name, ```"```", 1
                )
                format_package_name = remove_optional_dependence_from_package(
                    f```"{package_name}{version_symbol}```".strip()
                )
                package_list.append(format_package_name)
        else:
            format_package_name = remove_optional_dependence_from_package(
                multi_requirements[0].strip()
            )
            package_list.append(format_package_name)

    # 处理包名大小写并统一成小写
    for p in package_list:
        p = p.lower().strip()
        logger.debug(```"预处理后的 Python 软件包名: %s```", p)
        if not is_package_has_version(p):
            logger.debug(```"%s 无版本声明```", p)
            new_p = get_correct_package_name(p)
            logger.debug(```"包名处理: %s -> %s```", p, new_p)
            canonical_package_list.append(new_p)
            continue

        if version_string_is_canonical(get_package_version(p)):
            canonical_package_list.append(p)
        else:
            logger.debug(```"%s 软件包名的版本不符合标准```", p)

    return canonical_package_list


def read_packages_from_requirements_file(file_path: str | Path) -> list[str]:
    ```"```"```"从 requirements.txt 文件中读取 Python 软件包版本声明列表

    Args:
        file_path (str | Path): requirements.txt 文件路径

    Returns:
        list[str]: 从 requirements.txt 文件中读取的 Python 软件包声明列表
    ```"```"```"
    try:
        with open(file_path, ```"r```", encoding=```"utf-8```") as f:
            return f.readlines()
    except Exception as e:
        logger.debug(```"打开 %s 时出现错误: %s\n请检查文件是否出现损坏```", file_path, e)
        return []


def get_package_version_from_library(package_name: str) -> str | None:
    ```"```"```"获取已安装的 Python 软件包版本号

    Args:
        package_name (str): Python 软件包名

    Returns:
        (str | None): 如果获取到 Python 软件包版本号则返回版本号字符串, 否则返回````None````
    ```"```"```"
    try:
        ver = importlib.metadata.version(package_name)
    except Exception as _:
        ver = None

    if ver is None:
        try:
            ver = importlib.metadata.version(package_name.lower())
        except Exception as _:
            ver = None

    if ver is None:
        try:
            ver = importlib.metadata.version(package_name.replace(```"_```", ```"-```"))
        except Exception as _:
            ver = None

    return ver


def is_package_installed(package: str) -> bool:
    ```"```"```"判断 Python 软件包是否已安装在环境中

    Args:
        package (str): Python 软件包名

    Returns:
        bool: 如果 Python 软件包未安装或者未安装正确的版本, 则返回````False````
    ```"```"```"
    # 分割 Python 软件包名和版本号
    if ```"===```" in package:
        pkg_name, pkg_version = [x.strip() for x in package.split(```"===```")]
    elif ```"~=```" in package:
        pkg_name, pkg_version = [x.strip() for x in package.split(```"~=```")]
    elif ```"!=```" in package:
        pkg_name, pkg_version = [x.strip() for x in package.split(```"!=```")]
    elif ```"<=```" in package:
        pkg_name, pkg_version = [x.strip() for x in package.split(```"<=```")]
    elif ```">=```" in package:
        pkg_name, pkg_version = [x.strip() for x in package.split(```">=```")]
    elif ```"<```" in package:
        pkg_name, pkg_version = [x.strip() for x in package.split(```"<```")]
    elif ```">```" in package:
        pkg_name, pkg_version = [x.strip() for x in package.split(```">```")]
    elif ```"==```" in package:
        pkg_name, pkg_version = [x.strip() for x in package.split(```"==```")]
    else:
        pkg_name, pkg_version = package.strip(), None

    env_pkg_version = get_package_version_from_library(pkg_name)
    logger.debug(
        ```"已安装 Python 软件包检测: pkg_name: %s, env_pkg_version: %s, pkg_version: %s```",
        pkg_name,
        env_pkg_version,
        pkg_version,
    )

    if env_pkg_version is None:
        return False

    if pkg_version is not None:
        # ok = env_pkg_version === / == pkg_version
        if ```"===```" in package or ```"==```" in package:
            logger.debug(```"包含条件: === / ==```")
            logger.debug(```"%s == %s ?```", env_pkg_version, pkg_version)
            if PyWhlVersionComparison(env_pkg_version) == PyWhlVersionComparison(
                pkg_version
            ):
                logger.debug(```"%s == %s 条件成立```", env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version ~= pkg_version
        if ```"~=```" in package:
            logger.debug(```"包含条件: ~=```")
            logger.debug(```"%s ~= %s ?```", env_pkg_version, pkg_version)
            if PyWhlVersionComparison(env_pkg_version) == ~PyWhlVersionComparison(
                pkg_version
            ):
                logger.debug(```"%s == %s 条件成立```", env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version != pkg_version
        if ```"!=```" in package:
            logger.debug(```"包含条件: !=```")
            logger.debug(```"%s != %s ?```", env_pkg_version, pkg_version)
            if PyWhlVersionComparison(env_pkg_version) != PyWhlVersionComparison(
                pkg_version
            ):
                logger.debug(```"%s != %s 条件成立```", env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version <= pkg_version
        if ```"<=```" in package:
            logger.debug(```"包含条件: <=```")
            logger.debug(```"%s <= %s ?```", env_pkg_version, pkg_version)
            if PyWhlVersionComparison(env_pkg_version) <= PyWhlVersionComparison(
                pkg_version
            ):
                logger.debug(```"%s <= %s 条件成立```", env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version >= pkg_version
        if ```">=```" in package:
            logger.debug(```"包含条件: >=```")
            logger.debug(```"%s >= %s ?```", env_pkg_version, pkg_version)
            if PyWhlVersionComparison(env_pkg_version) >= PyWhlVersionComparison(
                pkg_version
            ):
                logger.debug(```"%s >= %s 条件成立```", env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version < pkg_version
        if ```"<```" in package:
            logger.debug(```"包含条件: <```")
            logger.debug(```"%s < %s ?```", env_pkg_version, pkg_version)
            if PyWhlVersionComparison(env_pkg_version) < PyWhlVersionComparison(
                pkg_version
            ):
                logger.debug(```"%s < %s 条件成立```", env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version > pkg_version
        if ```">```" in package:
            logger.debug(```"包含条件: >```")
            logger.debug(```"%s > %s ?```", env_pkg_version, pkg_version)
            if PyWhlVersionComparison(env_pkg_version) > PyWhlVersionComparison(
                pkg_version
            ):
                logger.debug(```"%s > %s 条件成立```", env_pkg_version, pkg_version)
                return True

        logger.debug(```"%s 需要安装```", package)
        return False

    return True


def validate_requirements(requirement_path: str | Path) -> bool:
    ```"```"```"检测环境依赖是否完整

    Args:
        requirement_path (str | Path): 依赖文件路径

    Returns:
        bool: 如果有缺失依赖则返回````False````
    ```"```"```"
    origin_requires = read_packages_from_requirements_file(requirement_path)
    requires = parse_requirement_list(origin_requires)
    for package in requires:
        if not is_package_installed(package):
            return False

    return True


def main() -> None:
    requirement_path = COMMAND_ARGS.requirement_path

    if not os.path.isfile(requirement_path):
        logger.error(```"依赖文件未找到, 无法检查运行环境```")
        sys.exit(1)

    logger.debug(```"检测运行环境中```")
    print(validate_requirements(requirement_path))
    logger.debug(```"环境检查完成```")


if __name__ == ```"__main__```":
    main()
`".Trim()

    Print-Msg `"检查 Qwen TTS WebUI 内核依赖完整性中`"
    if (!(Test-Path `"`$Env:CACHE_HOME`")) {
        New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" > `$null
    }
    Set-Content -Encoding UTF8 -Path `"`$Env:CACHE_HOME/check_qwen_tts_webui_requirement.py`" -Value `$content

    `$dep_path = `"`$PSScriptRoot/`$Env:CORE_PREFIX/requirements_versions.txt`"
    if (!(Test-Path `"`$dep_path`")) {
        `$dep_path = `"`$PSScriptRoot/`$Env:CORE_PREFIX/requirements.txt`"
    }
    if (!(Test-Path `"`$dep_path`")) {
        Print-Msg `"未检测到 Qwen TTS WebUI 依赖文件, 跳过依赖完整性检查`"
        return
    }

    `$status = `$(python `"`$Env:CACHE_HOME/check_qwen_tts_webui_requirement.py`" --requirement-path `"`$dep_path`")

    if (`$status -eq `"False`") {
        Print-Msg `"检测到 Qwen TTS WebUI 内核有依赖缺失, 安装 Qwen TTS WebUI 依赖中`"
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
            Print-Msg `"Qwen TTS WebUI 依赖安装成功`"
        } else {
            Print-Msg `"Qwen TTS WebUI 依赖安装失败, 这将会导致 Qwen TTS WebUI 缺失依赖无法正常运行`"
        }
    } else {
        Print-Msg `"Qwen TTS WebUI 无缺失依赖`"
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


# 检查 Qwen TTS WebUI 运行环境
function Check-Qwen-TTS-WebUI-Env {
    if ((Test-Path `"`$PSScriptRoot/disable_check_env.txt`") -or (`$DisableEnvCheck)) {
        Print-Msg `"检测到 disable_check_env.txt 配置文件 / -DisableEnvCheck 命令行参数, 已禁用 Qwen TTS WebUI 运行环境检测, 这可能会导致 Qwen TTS WebUI 运行环境中存在的问题无法被发现并解决`"
        return
    } else {
        Print-Msg `"检查 Qwen TTS WebUI 运行环境中`"
    }

    Check-Qwen-TTS-WebUI-Requirements
    Fix-PyTorch
    Check-Numpy-Version
    Check-MS-VCPP-Redistributable
    Print-Msg `"Qwen TTS WebUI 运行环境检查完成`"
}


function Main {
    Print-Msg `"初始化中`"
    Get-Qwen-TTS-WebUI-Installer-Version
    Get-Qwen-TTS-WebUI-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"Qwen TTS WebUI Installer 构建模式已启用, 跳过 Qwen TTS WebUI Installer 更新检查`"
    } else {
        Check-Qwen-TTS-WebUI-Installer-Update
    }
    Set-HuggingFace-Mirror
    Set-uv
    PyPI-Mirror-Status

    if (!(Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX`")) {
        Print-Msg `"内核路径 `$PSScriptRoot\`$Env:CORE_PREFIX 未找到, 请检查 Qwen TTS WebUI 是否已正确安装, 或者尝试运行 Qwen TTS WebUI Installer 进行修复`"
        Read-Host | Out-Null
        return
    }

    `$launch_args = Get-Qwen-TTS-WebUI-Launch-Args
    # 记录上次的路径
    `$current_path = `$(Get-Location).ToString()
    Set-Location `"`$PSScriptRoot/`$Env:CORE_PREFIX`"

    Create-Qwen-TTS-WebUI-Shortcut
    Check-Qwen-TTS-WebUI-Env
    Set-PyTorch-CUDA-Memory-Alloc
    Print-Msg `"启动 Qwen TTS WebUI 中`"
    if (`$BuildMode) {
        Print-Msg `"Qwen TTS WebUI Installer 构建模式已启用, 跳过启动 Qwen TTS WebUI`"
    } else {
        python launch.py `$launch_args
        `$req = `$?
        if (`$req) {
            Print-Msg `"Qwen TTS WebUI 正常退出`"
        } else {
            Print-Msg `"Qwen TTS WebUI 出现异常, 已退出`"
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
    `$prefix_list = @(`"core`", `"QwenTTSWebUI`", `"qwen-tts-webui`", `"qwen_tts_webui_portable`")
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
# Qwen TTS WebUI Installer 版本和检查更新间隔
`$QWEN_TTS_WEBUI_INSTALLER_VERSION = $QWEN_TTS_WEBUI_INSTALLER_VERSION
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
`$PIP_EXTRA_INDEX_MIRROR_CU130_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU130_NJU`"
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
`$Env:PYTHONWARNINGS = `"$Env:PYTHONWARNINGS`"
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
function Get-Qwen-TTS-WebUI-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-DisablePyPIMirror] [-DisableUpdate] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像源地址>] [-DisableAutoApplyUpdate]

参数:
    -Help
        获取 Qwen TTS WebUI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -BuildMode
        启用 Qwen TTS WebUI Installer 构建模式

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableUpdate
        禁用 Qwen TTS WebUI Installer 更新检查

    -DisableProxy
        禁用 Qwen TTS WebUI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableGithubMirror
        禁用 Qwen TTS WebUI Installer 自动设置 Github 镜像源

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
        禁用 Qwen TTS WebUI Installer 自动应用新版本更新


更多的帮助信息请阅读 Qwen TTS WebUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[Qwen TTS WebUI Installer]`" -ForegroundColor Cyan -NoNewline
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


# 显示 Qwen TTS WebUI Installer 版本
function Get-Qwen-TTS-WebUI-Installer-Version {
    `$ver = `$([string]`$QWEN_TTS_WEBUI_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"Qwen TTS WebUI Installer 版本: v`${major}.`${minor}.`${micro}`"
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


# Qwen TTS WebUI Installer 更新检测
function Check-Qwen-TTS-WebUI-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/qwen_tts_webui_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 Qwen TTS WebUI Installer 的自动检查更新功能`"
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
        Print-Msg `"检查 Qwen TTS WebUI Installer 更新中`"
        try {
            `$web_request_params = @{
                Uri = `$url
                UseBasicParsing = `$true
                OutFile = `"`$Env:CACHE_HOME/qwen_tts_webui_installer.ps1`"
            }
            Invoke-WebRequest @web_request_params
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/qwen_tts_webui_installer.ps1`" |
                Select-String -Pattern `"QWEN_TTS_WEBUI_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 Qwen TTS WebUI Installer 更新中`"
            } else {
                Print-Msg `"检查 Qwen TTS WebUI Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -le `$QWEN_TTS_WEBUI_INSTALLER_VERSION) {
        Print-Msg `"Qwen TTS WebUI Installer 已是最新版本`"
        return
    }

    if ((`$DisableAutoApplyUpdate) -or (Test-Path `"`$PSScriptRoot/disable_auto_apply_update.txt`")) {
        Print-Msg `"检测到 Qwen TTS WebUI Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"===============================================>`").Trim()
        if (!(`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`")) {
            Print-Msg `"跳过 Qwen TTS WebUI Installer 更新`"
            return
        }
    } else {
        Print-Msg `"检测到 Qwen TTS WebUI Installer 有新版本可用`"
    }

    Print-Msg `"调用 Qwen TTS WebUI Installer 进行更新中`"
    . `"`$Env:CACHE_HOME/qwen_tts_webui_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
    `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
    Print-Msg `"更新结束, 重新启动 Qwen TTS WebUI Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
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
    Get-Qwen-TTS-WebUI-Installer-Version
    Get-Qwen-TTS-WebUI-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"Qwen TTS WebUI Installer 构建模式已启用, 跳过 Qwen TTS WebUI Installer 更新检查`"
    } else {
        Check-Qwen-TTS-WebUI-Installer-Update
    }
    Set-Github-Mirror

    if (!(Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX`")) {
        Print-Msg `"内核路径 `$PSScriptRoot\`$Env:CORE_PREFIX 未找到, 请检查 Qwen TTS WebUI 是否已正确安装, 或者尝试运行 Qwen TTS WebUI Installer 进行修复`"
        Read-Host | Out-Null
        return
    }

    Print-Msg `"拉取 Qwen TTS WebUI 更新内容中`"
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
        Print-Msg `"应用 Qwen TTS WebUI 更新中`"
        `$commit_hash = `$(git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" log `"`$remote_branch`" --max-count 1 --format=`"%h`")
        git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" reset --hard `"`$remote_branch`" --recurse-submodules
        `$core_latest_ver = `$(git -C `"`$PSScriptRoot/`$Env:CORE_PREFIX`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")

        if (`$core_origin_ver -eq `$core_latest_ver) {
            Print-Msg `"Qwen TTS WebUI 已为最新版, 当前版本：`$core_origin_ver`"
        } else {
            Print-Msg `"Qwen TTS WebUI 更新成功, 版本：`$core_origin_ver -> `$core_latest_ver`"
        }
    } else {
        Print-Msg `"拉取 Qwen TTS WebUI 更新内容失败`"
        Print-Msg `"更新 Qwen TTS WebUI 失败, 请检查控制台日志。可尝试重新运行 Qwen TTS WebUI Installer 更新脚本进行重试`"
    }

    Print-Msg `"退出 Qwen TTS WebUI 更新脚本`"
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


# 获取安装脚本
function Write-Launch-Qwen-TTS-WebUI-Install-Script {
    $content = "
param (
    [string]`$InstallPath,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableUV,
    [switch]`$DisableGithubMirror,
    [string]`$UseCustomGithubMirror,
    [Parameter(ValueFromRemainingArguments=`$true)]`$ExtraArgs
)
& {
    `$prefix_list = @(`"core`", `"QwenTTSWebUI`", `"qwen-tts-webui`", `"qwen_tts_webui_portable`")
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
`$QWEN_TTS_WEBUI_INSTALLER_VERSION = $QWEN_TTS_WEBUI_INSTALLER_VERSION
if (-not `$InstallPath) {
    `$InstallPath = `$PSScriptRoot
}



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[Qwen TTS WebUI Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# 显示 Qwen TTS WebUI Installer 版本
function Get-Qwen-TTS-WebUI-Installer-Version {
    `$ver = `$([string]`$QWEN_TTS_WEBUI_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"Qwen TTS WebUI Installer 版本: v`${major}.`${minor}.`${micro}`"
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


# 下载 Qwen TTS WebUI Installer
function Download-Qwen-TTS-WebUI-Installer {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/qwen_tts_webui_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    ForEach (`$url in `$urls) {
        Print-Msg `"正在下载最新的 Qwen TTS WebUI Installer 脚本`"
        `$web_request_params = @{
            Uri = `$url
            UseBasicParsing = `$true
            OutFile = `"`$PSScriptRoot/cache/qwen_tts_webui_installer.ps1`"
        }
        Invoke-WebRequest @web_request_params
        if (`$?) {
            Print-Msg `"下载 Qwen TTS WebUI Installer 脚本成功`"
            break
        } else {
            Print-Msg `"下载 Qwen TTS WebUI Installer 脚本失败`"
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试下载 Qwen TTS WebUI Installer 脚本`"
            } else {
                Print-Msg `"下载 Qwen TTS WebUI Installer 脚本失败, 可尝试重新运行 Qwen TTS WebUI Installer 下载脚本`"
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
    Get-Qwen-TTS-WebUI-Installer-Version
    Set-Proxy

    `$status = Download-Qwen-TTS-WebUI-Installer

    if (`$status) {
        Print-Msg `"运行 Qwen TTS WebUI Installer 中`"
        `$arg = Get-Local-Setting
        `$extra_args = Get-ExtraArgs
        try {
            Invoke-Expression `"& ```"`$PSScriptRoot/cache/qwen_tts_webui_installer.ps1```" `$extra_args @arg`"
        }
        catch {
            Print-Msg `"运行 Qwen TTS WebUI Installer 时出现了错误: `$_`"
            Read-Host | Out-Null
        }
    } else {
        Read-Host | Out-Null
    }
}

###################

Main
".Trim()

    if (Test-Path "$InstallPath/launch_qwen_tts_webui_installer.ps1") {
        Print-Msg "更新 launch_qwen_tts_webui_installer.ps1 中"
    } else {
        Print-Msg "生成 launch_qwen_tts_webui_installer.ps1 中"
    }
    Set-Content -Encoding $PS_SCRIPT_ENCODING -Path "$InstallPath/launch_qwen_tts_webui_installer.ps1" -Value $content
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
    `$prefix_list = @(`"core`", `"QwenTTSWebUI`", `"qwen-tts-webui`", `"qwen_tts_webui_portable`")
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
# Qwen TTS WebUI Installer 版本和检查更新间隔
`$QWEN_TTS_WEBUI_INSTALLER_VERSION = $QWEN_TTS_WEBUI_INSTALLER_VERSION
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
`$PIP_EXTRA_INDEX_MIRROR_CU130_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU130_NJU`"
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
`$Env:PYTHONWARNINGS = `"$Env:PYTHONWARNINGS`"
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
function Get-Qwen-TTS-WebUI-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-BuildWithTorch <PyTorch 版本编号>] [-BuildWithTorchReinstall] [-DisablePyPIMirror] [-DisableUpdate] [-DisableUV] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableAutoApplyUpdate]

参数:
    -Help
        获取 Qwen TTS WebUI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -BuildMode
        启用 Qwen TTS WebUI Installer 构建模式

    -BuildWithTorch <PyTorch 版本编号>
        (需添加 -BuildMode 启用 Qwen TTS WebUI Installer 构建模式) Qwen TTS WebUI Installer 执行完基础安装流程后调用 Qwen TTS WebUI Installer 的 reinstall_pytorch.ps1 脚本, 根据 PyTorch 版本编号安装指定的 PyTorch 版本
        PyTorch 版本编号可运行 reinstall_pytorch.ps1 脚本进行查看

    -BuildWithTorchReinstall
        (需添加 -BuildMode 启用 Qwen TTS WebUI Installer 构建模式, 并且添加 -BuildWithTorch) 在 Qwen TTS WebUI Installer 构建模式下, 执行 reinstall_pytorch.ps1 脚本对 PyTorch 进行指定版本安装时使用强制重新安装

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableUpdate
        禁用 Qwen TTS WebUI Installer 更新检查

    -DisableUV
        禁用 Qwen TTS WebUI Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -DisableProxy
        禁用 Qwen TTS WebUI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableAutoApplyUpdate
        禁用 Qwen TTS WebUI Installer 自动应用新版本更新


更多的帮助信息请阅读 Qwen TTS WebUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[Qwen TTS WebUI Installer]`" -ForegroundColor Cyan -NoNewline
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


# 显示 Qwen TTS WebUI Installer 版本
function Get-Qwen-TTS-WebUI-Installer-Version {
    `$ver = `$([string]`$QWEN_TTS_WEBUI_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"Qwen TTS WebUI Installer 版本: v`${major}.`${minor}.`${micro}`"
}


# PyPI 镜像源状态
function PyPI-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 PyPI 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pypi_mirror.txt 配置文件 / -DisablePyPIMirror 命令行参数, 已将 PyPI 源切换至官方源`"
    }
}


# Qwen TTS WebUI Installer 更新检测
function Check-Qwen-TTS-WebUI-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/qwen_tts_webui_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 Qwen TTS WebUI Installer 的自动检查更新功能`"
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
        Print-Msg `"检查 Qwen TTS WebUI Installer 更新中`"
        try {
            `$web_request_params = @{
                Uri = `$url
                UseBasicParsing = `$true
                OutFile = `"`$Env:CACHE_HOME/qwen_tts_webui_installer.ps1`"
            }
            Invoke-WebRequest @web_request_params
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/qwen_tts_webui_installer.ps1`" |
                Select-String -Pattern `"QWEN_TTS_WEBUI_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 Qwen TTS WebUI Installer 更新中`"
            } else {
                Print-Msg `"检查 Qwen TTS WebUI Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -le `$QWEN_TTS_WEBUI_INSTALLER_VERSION) {
        Print-Msg `"Qwen TTS WebUI Installer 已是最新版本`"
        return
    }

    if ((`$DisableAutoApplyUpdate) -or (Test-Path `"`$PSScriptRoot/disable_auto_apply_update.txt`")) {
        Print-Msg `"检测到 Qwen TTS WebUI Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"===============================================>`").Trim()
        if (!(`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`")) {
            Print-Msg `"跳过 Qwen TTS WebUI Installer 更新`"
            return
        }
    } else {
        Print-Msg `"检测到 Qwen TTS WebUI Installer 有新版本可用`"
    }

    Print-Msg `"调用 Qwen TTS WebUI Installer 进行更新中`"
    . `"`$Env:CACHE_HOME/qwen_tts_webui_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
    `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
    Print-Msg `"更新结束, 重新启动 Qwen TTS WebUI Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
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
    
    if compare_versions(uv_ver, uv_minimum_ver) < 0:
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
    'cu130',
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
            `$PIP_EXTRA_INDEX_MIRROR_CU128_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU128
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
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.9.0 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.9.0+cpu torchvision==0.24.0+cpu torchaudio==2.9.0+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.9.0 (Intel Arc)`"
        `"type`" = `"xpu`"
        `"supported`" = `"xpu`" -in `$supported_type
        `"torch`" = `"torch==2.9.0+xpu torchvision==0.24.0+xpu torchaudio==2.9.0+xpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_XPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_XPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.9.0 (CUDA 12.6)`"
        `"type`" = `"cu126`"
        `"supported`" = `"cu126`" -in `$supported_type
        `"torch`" = `"torch==2.9.0+cu126 torchvision==0.24.0+cu126 torchaudio==2.9.0+cu126`"
        `"xformers`" = `"xformers==0.0.33`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU126_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU126
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.9.0 (CUDA 12.8)`"
        `"type`" = `"cu128`"
        `"supported`" = `"cu128`" -in `$supported_type
        `"torch`" = `"torch==2.9.0+cu128 torchvision==0.24.0+cu128 torchaudio==2.9.0+cu128`"
        `"xformers`" = `"xformers==0.0.33`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU128_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU128
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.9.0 (CUDA 13.0)`"
        `"type`" = `"cu130`"
        `"supported`" = `"cu130`" -in `$supported_type
        `"torch`" = `"torch==2.9.0+cu130 torchvision==0.24.0+cu130 torchaudio==2.9.0+cu130`"
        `"xformers`" = `"xformers==0.0.33`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU130_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU130
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.9.1 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.9.1+cpu torchvision==0.24.1+cpu torchaudio==2.9.1+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.9.1 (Intel Arc)`"
        `"type`" = `"xpu`"
        `"supported`" = `"xpu`" -in `$supported_type
        `"torch`" = `"torch==2.9.1+xpu torchvision==0.24.1+xpu torchaudio==2.9.1+xpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_XPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_XPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.9.1 (CUDA 12.6)`"
        `"type`" = `"cu126`"
        `"supported`" = `"cu126`" -in `$supported_type
        `"torch`" = `"torch==2.9.1+cu126 torchvision==0.24.1+cu126 torchaudio==2.9.1+cu126`"
        `"xformers`" = `"xformers==0.0.33.post2`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU126_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU126
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.9.1 (CUDA 12.8)`"
        `"type`" = `"cu128`"
        `"supported`" = `"cu128`" -in `$supported_type
        `"torch`" = `"torch==2.9.1+cu128 torchvision==0.24.1+cu128 torchaudio==2.9.1+cu128`"
        `"xformers`" = `"xformers==0.0.33.post2`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU128_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU128
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.9.1 (CUDA 13.0)`"
        `"type`" = `"cu130`"
        `"supported`" = `"cu130`" -in `$supported_type
        `"torch`" = `"torch==2.9.1+cu130 torchvision==0.24.1+cu130 torchaudio==2.9.1+cu130`"
        `"xformers`" = `"xformers==0.0.33.post2`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU130_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU130
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.10.0 (CPU)`"
        `"type`" = `"cpu`"
        `"supported`" = `"cpu`" -in `$supported_type
        `"torch`" = `"torch==2.10.0+cpu torchvision==0.25.0+cpu torchaudio==2.10.0+cpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.10.0 (Intel Arc)`"
        `"type`" = `"xpu`"
        `"supported`" = `"xpu`" -in `$supported_type
        `"torch`" = `"torch==2.10.0+xpu torchvision==0.25.0+xpu torchaudio==2.10.0+xpu`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_XPU_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_XPU
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.10.0 (CUDA 12.6)`"
        `"type`" = `"cu126`"
        `"supported`" = `"cu126`" -in `$supported_type
        `"torch`" = `"torch==2.10.0+cu126 torchvision==0.25.0+cu126 torchaudio==2.10.0+cu126`"
        `"xformers`" = `"xformers==0.0.34`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU126_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU126
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.10.0 (CUDA 12.8)`"
        `"type`" = `"cu128`"
        `"supported`" = `"cu128`" -in `$supported_type
        `"torch`" = `"torch==2.10.0+cu128 torchvision==0.25.0+cu128 torchaudio==2.10.0+cu128`"
        `"xformers`" = `"xformers==0.0.34`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU128_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU128
        }
        `"extra_index_mirror`" = `"`"
        `"find_links`" = `"`"
    }) | Out-Null
    `$pytorch_list.Add(@{
        `"name`" = `"Torch 2.10.0 (CUDA 13.0)`"
        `"type`" = `"cu130`"
        `"supported`" = `"cu130`" -in `$supported_type
        `"torch`" = `"torch==2.10.0+cu130 torchvision==0.25.0+cu130 torchaudio==2.10.0+cu130`"
        `"xformers`" = `"xformers==0.0.34`"
        `"index_mirror`" = if (`$USE_PIP_MIRROR) {
            `$PIP_EXTRA_INDEX_MIRROR_CU130_NJU
        } else {
            `$PIP_EXTRA_INDEX_MIRROR_CU130
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
    Get-Qwen-TTS-WebUI-Installer-Version
    Get-Qwen-TTS-WebUI-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"Qwen TTS WebUI Installer 构建模式已启用, 跳过 Qwen TTS WebUI Installer 更新检查`"
    } else {
        Check-Qwen-TTS-WebUI-Installer-Update
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
            Print-Msg `"Qwen TTS WebUI Installer 构建已启用, 指定安装的 PyTorch 序号: `$BuildWithTorch`"
            `$arg = `$BuildWithTorch
            `$go_to = 1
        } else {
            `$arg = (Read-Host `"===============================================>`").Trim()
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
        `$use_force_reinstall = (Read-Host `"===============================================>`").Trim()
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
        `$install_torch = (Read-Host `"===============================================>`").Trim()
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


# Qwen TTS WebUI Installer 设置脚本
function Write-Qwen-TTS-WebUI-Installer-Settings-Script {
    $content = "
param (
    [switch]`$Help,
    [string]`$CorePrefix,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy
)
& {
    `$prefix_list = @(`"core`", `"QwenTTSWebUI`", `"qwen-tts-webui`", `"qwen_tts_webui_portable`")
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
# Qwen TTS WebUI Installer 版本和检查更新间隔
`$QWEN_TTS_WEBUI_INSTALLER_VERSION = $QWEN_TTS_WEBUI_INSTALLER_VERSION
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
`$PIP_EXTRA_INDEX_MIRROR_CU130_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU130_NJU`"
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
`$Env:PYTHONWARNINGS = `"$Env:PYTHONWARNINGS`"
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
function Get-Qwen-TTS-WebUI-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-DisablePyPIMirror] [-DisableProxy] [-UseCustomProxy <代理服务器地址>]

参数:
    -Help
        获取 Qwen TTS WebUI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableProxy
        禁用 Qwen TTS WebUI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址


更多的帮助信息请阅读 Qwen TTS WebUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[Qwen TTS WebUI Installer]`" -ForegroundColor Cyan -NoNewline
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


# 显示 Qwen TTS WebUI Installer 版本
function Get-Qwen-TTS-WebUI-Installer-Version {
    `$ver = `$([string]`$QWEN_TTS_WEBUI_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"Qwen TTS WebUI Installer 版本: v`${major}.`${minor}.`${micro}`"
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


# 获取 Qwen TTS WebUI Installer 自动检测更新设置
function Get-Qwen-TTS-WebUI-Installer-Auto-Check-Update-Setting {
    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        return `"禁用`"
    } else {
        return `"启用`"
    }
}


# 获取 Qwen TTS WebUI Installer 自动应用更新设置
function Get-Qwen-TTS-WebUI-Installer-Auto-Apply-Update-Setting {
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


# 获取 Qwen TTS WebUI 运行环境检测配置
function Get-Qwen-TTS-WebUI-Env-Check-Setting {
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
    return (Read-Host `"===============================================>`").Trim()
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
                Print-Msg `"启用 Github 镜像成功, 在更新 Qwen TTS WebUI 时将自动检测可用的 Github 镜像源并使用`"
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


# Qwen TTS WebUI Installer 自动检查更新设置
function Update-Qwen-TTS-WebUI-Installer-Auto-Check-Update-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 Qwen TTS WebUI Installer 自动检测更新设置: `$(Get-Qwen-TTS-WebUI-Installer-Auto-Check-Update-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 Qwen TTS WebUI Installer 自动更新检查`"
        Print-Msg `"2. 禁用 Qwen TTS WebUI Installer 自动更新检查`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"
        Print-Msg `"警告: 当 Qwen TTS WebUI Installer 有重要更新(如功能性修复)时, 禁用自动更新检查后将得不到及时提示`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_update.txt`" -Force -Recurse 2> `$null
                Print-Msg `"启用 Qwen TTS WebUI Installer 自动更新检查成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_update.txt`" -Force > `$null
                Print-Msg `"禁用 Qwen TTS WebUI Installer 自动更新检查成功`"
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


# Qwen TTS WebUI Installer 自动应用更新设置
function Update-Qwen-TTS-WebUI-Installer-Auto-Apply-Update-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 Qwen TTS WebUI Installer 自动应用更新设置: `$(Get-Qwen-TTS-WebUI-Installer-Auto-Apply-Update-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 Qwen TTS WebUI Installer 自动应用更新`"
        Print-Msg `"2. 禁用 Qwen TTS WebUI Installer 自动应用更新`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_auto_apply_update.txt`" -Force -Recurse 2> `$null
                Print-Msg `"启用 Qwen TTS WebUI Installer 自动应用更新成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_auto_apply_update.txt`" -Force > `$null
                Print-Msg `"禁用 Qwen TTS WebUI Installer 自动应用更新成功`"
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


# Qwen TTS WebUI 启动参数设置
function Update-Qwen-TTS-WebUI-Launch-Args-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 Qwen TTS WebUI 启动参数: `$(Get-Launch-Args-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 设置 Qwen TTS WebUI 启动参数`"
        Print-Msg `"2. 删除 Qwen TTS WebUI 启动参数`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Print-Msg `"请输入 Qwen TTS WebUI 启动参数`"
                Print-Msg `"提示: 保存启动参数后原有的启动参数将被覆盖, Qwen TTS WebUI 可用的启动参数可阅读: https://github.com/licyk/qwen-tts-webui?tab=readme-ov-file#%E5%90%AF%E5%8A%A8%E5%8F%82%E6%95%B0`"
                Print-Msg `"输入启动参数后回车保存`"
                `$qwen_tts_webui_launch_args = Get-User-Input
                Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/launch_args.txt`" -Value `$qwen_tts_webui_launch_args
                Print-Msg `"设置 Qwen TTS WebUI 启动参数成功, 使用的 Qwen TTS WebUI 启动参数为: `$qwen_tts_webui_launch_args`"
                break
            }
            2 {
                Remove-Item -Path `"`$PSScriptRoot/launch_args.txt`" -Force -Recurse 2> `$null
                Print-Msg `"删除 Qwen TTS WebUI 启动参数成功`"
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


# 自动创建 Qwen TTS WebUI 快捷启动方式设置
function Auto-Set-Launch-Shortcut-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前自动创建 Qwen TTS WebUI 快捷启动方式设置: `$(Get-Auto-Set-Launch-Shortcut-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用自动创建 Qwen TTS WebUI 快捷启动方式`"
        Print-Msg `"2. 禁用自动创建 Qwen TTS WebUI 快捷启动方式`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/enable_shortcut.txt`" -Force > `$null
                Print-Msg `"启用自动创建 Qwen TTS WebUI 快捷启动方式成功`"
                break
            }
            2 {
                Remove-Item -Path `"`$PSScriptRoot/enable_shortcut.txt`" -Force -Recurse 2> `$null
                Print-Msg `"禁用自动创建 Qwen TTS WebUI 快捷启动方式成功`"
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


# Qwen TTS WebUI 运行环境检测设置
function Qwen-TTS-WebUI-Env-Check-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 Qwen TTS WebUI 运行环境检测设置: `$(Get-Qwen-TTS-WebUI-Env-Check-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 Qwen TTS WebUI 运行环境检测`"
        Print-Msg `"2. 禁用 Qwen TTS WebUI 运行环境检测`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_check_env.txt`" -Force -Recurse 2> `$null
                Print-Msg `"启用 Qwen TTS WebUI 运行环境检测成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_check_env.txt`" -Force > `$null
                Print-Msg `"禁用 Qwen TTS WebUI 运行环境检测成功`"
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


# 检查 Qwen TTS WebUI Installer 更新
function Check-Qwen-TTS-WebUI-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/qwen_tts_webui_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null
    Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间

    ForEach (`$url in `$urls) {
        Print-Msg `"检查 Qwen TTS WebUI Installer 更新中`"
        try {
            `$web_request_params = @{
                Uri = `$url
                UseBasicParsing = `$true
                OutFile = `"`$Env:CACHE_HOME/qwen_tts_webui_installer.ps1`"
            }
            Invoke-WebRequest @web_request_params
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/qwen_tts_webui_installer.ps1`" |
                Select-String -Pattern `"QWEN_TTS_WEBUI_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 Qwen TTS WebUI Installer 更新中`"
            } else {
                Print-Msg `"检查 Qwen TTS WebUI Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -gt `$QWEN_TTS_WEBUI_INSTALLER_VERSION) {
        Print-Msg `"Qwen TTS WebUI Installer 有新版本可用`"
        Print-Msg `"调用 Qwen TTS WebUI Installer 进行更新中`"
        . `"`$Env:CACHE_HOME/qwen_tts_webui_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
        `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
        Print-Msg `"更新结束, 重新启动 Qwen TTS WebUI Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
        Invoke-Expression `"& ```"`$PSCommandPath```" `$raw_params`"
        exit 0
    } else {
        Print-Msg `"Qwen TTS WebUI Installer 已是最新版本`"
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
        `$qwen_tts_webui_status = `"已安装`"
    } else {
        `$qwen_tts_webui_status = `"未安装`"
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
    Print-Msg `"qwen-tts-webui: `$qwen_tts_webui_status`"
    Print-Msg `"-----------------------------------------------------`"
    if (`$broken -eq 1) {
        Print-Msg `"检测到环境出现组件缺失, 可尝试运行 Qwen TTS WebUI Installer 进行安装`"
    } else {
        Print-Msg `"当前环境无缺失组件`"
    }
}


# 查看 Qwen TTS WebUI Installer 文档
function Get-Qwen-TTS-WebUI-Installer-Help-Docs {
    Print-Msg `"调用浏览器打开 Qwen TTS WebUI Installer 文档中`"
    Start-Process `"https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md`"
}


function Main {
    Print-Msg `"初始化中`"
    Get-Qwen-TTS-WebUI-Installer-Version
    Get-Qwen-TTS-WebUI-Installer-Cmdlet-Help
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
        Print-Msg `"Qwen TTS WebUI Installer 自动检查更新: `$(Get-Qwen-TTS-WebUI-Installer-Auto-Check-Update-Setting)`"
        Print-Msg `"Qwen TTS WebUI Installer 自动应用更新: `$(Get-Qwen-TTS-WebUI-Installer-Auto-Apply-Update-Setting)`"
        Print-Msg `"Qwen TTS WebUI 启动参数: `$(Get-Launch-Args-Setting)`"
        Print-Msg `"自动创建 Qwen TTS WebUI 快捷启动方式设置: `$(Get-Auto-Set-Launch-Shortcut-Setting)`"
        Print-Msg `"PyPI 镜像源设置: `$(Get-PyPI-Mirror-Setting)`"
        Print-Msg `"自动设置 CUDA 内存分配器设置: `$(Get-PyTorch-CUDA-Memory-Alloc-Setting)`"
        Print-Msg `"Qwen TTS WebUI 运行环境检测设置: `$(Get-Qwen-TTS-WebUI-Env-Check-Setting)`"
        Print-Msg `"Qwen TTS WebUI 内核路径前缀设置: `$(Get-Core-Prefix-Setting)`"
        Print-Msg `"-----------------------------------------------------`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 进入代理设置`"
        Print-Msg `"2. 进入 Python 包管理器设置`"
        Print-Msg `"3. 进入 HuggingFace 镜像源设置`"
        Print-Msg `"4. 进入 Github 镜像源设置`"
        Print-Msg `"5. 进入 Qwen TTS WebUI Installer 自动检查更新设置`"
        Print-Msg `"6. 进入 Qwen TTS WebUI Installer 自动应用更新设置`"
        Print-Msg `"7. 进入 Qwen TTS WebUI 启动参数设置`"
        Print-Msg `"8. 进入自动创建 Qwen TTS WebUI 快捷启动方式设置`"
        Print-Msg `"9. 进入 PyPI 镜像源设置`"
        Print-Msg `"10. 进入自动设置 CUDA 内存分配器设置`"
        Print-Msg `"11. 进入 Qwen TTS WebUI 运行环境检测设置`"
        Print-Msg `"12. 进入 Qwen TTS WebUI 内核路径前缀设置`"
        Print-Msg `"13. 更新 Qwen TTS WebUI Installer 管理脚本`"
        Print-Msg `"14. 检查环境完整性`"
        Print-Msg `"15. 查看 Qwen TTS WebUI Installer 文档`"
        Print-Msg `"16. 退出 Qwen TTS WebUI Installer 设置`"
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
                Update-Qwen-TTS-WebUI-Installer-Auto-Check-Update-Setting
                break
            }
            6 {
                Update-Qwen-TTS-WebUI-Installer-Auto-Apply-Update-Setting
                break
            }
            7 {
                Update-Qwen-TTS-WebUI-Launch-Args-Setting
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
                Qwen-TTS-WebUI-Env-Check-Setting
                break
            }
            12 {
                Update-Core-Prefix-Setting
                break
            }
            13 {
                Check-Qwen-TTS-WebUI-Installer-Update
                break
            }
            14 {
                Check-Env
                break
            }
            15 {
                Get-Qwen-TTS-WebUI-Installer-Help-Docs
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
            Print-Msg `"退出 Qwen TTS WebUI Installer 设置`"
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
    `$prefix_list = @(`"core`", `"QwenTTSWebUI`", `"qwen-tts-webui`", `"qwen_tts_webui_portable`")
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
# Qwen TTS WebUI Installer 版本和检查更新间隔
`$Env:QWEN_TTS_WEBUI_INSTALLER_VERSION = $QWEN_TTS_WEBUI_INSTALLER_VERSION
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
`$PIP_EXTRA_INDEX_MIRROR_CU130_NJU = `"$PIP_EXTRA_INDEX_MIRROR_CU130_NJU`"
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
`$Env:PYTHONWARNINGS = `"$Env:PYTHONWARNINGS`"
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
`$Env:QWEN_TTS_WEBUI_INSTALLER_ROOT = `$PSScriptRoot



# 帮助信息
function Get-Qwen-TTS-WebUI-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-DisablePyPIMirror] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像源地址>] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>]

参数:
    -Help
        获取 Qwen TTS WebUI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableGithubMirror
        禁用 Qwen TTS WebUI Installer 自动设置 Github 镜像源

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
        禁用 Qwen TTS WebUI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableHuggingFaceMirror
        禁用 HuggingFace 镜像源, 不使用 HuggingFace 镜像源下载文件

    -UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>
        使用自定义 HuggingFace 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror ```"https://hf-mirror.com```" 设置 HuggingFace 镜像源地址


更多的帮助信息请阅读 Qwen TTS WebUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 提示符信息
function global:prompt {
    `"`$(Write-Host `"[Qwen TTS WebUI Env]`" -ForegroundColor Green -NoNewLine) `$(Get-Location)> `"
}


# 消息输出
function global:Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[Qwen TTS WebUI Installer]`" -ForegroundColor Cyan -NoNewline
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
            `$web_request_params = @{
                Uri = `$url
                UseBasicParsing = `$true
                OutFile = `"`$aria2_tmp_path`"
            }
            Invoke-WebRequest @web_request_params
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

    Move-Item -Path `"`$Env:CACHE_HOME/aria2c.exe`" -Destination `"`$Env:QWEN_TTS_WEBUI_INSTALLER_ROOT/git/bin/aria2c.exe`" -Force
    Print-Msg `"更新 Aria2 完成`"
}


# Qwen TTS WebUI Installer 更新检测
function global:Check-Qwen-TTS-WebUI-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/qwen_tts_webui_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null
    Set-Content -Encoding UTF8 -Path `"`$Env:QWEN_TTS_WEBUI_INSTALLER_ROOT/update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间

    ForEach (`$url in `$urls) {
        Print-Msg `"检查 Qwen TTS WebUI Installer 更新中`"
        try {
            `$web_request_params = @{
                Uri = `$url
                UseBasicParsing = `$true
                OutFile = `"`$Env:CACHE_HOME/qwen_tts_webui_installer.ps1`"
            }
            Invoke-WebRequest @web_request_params
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/qwen_tts_webui_installer.ps1`" |
                Select-String -Pattern `"QWEN_TTS_WEBUI_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 Qwen TTS WebUI Installer 更新中`"
            } else {
                Print-Msg `"检查 Qwen TTS WebUI Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -gt `$Env:QWEN_TTS_WEBUI_INSTALLER_VERSION) {
        Print-Msg `"Qwen TTS WebUI Installer 有新版本可用`"
        Print-Msg `"调用 Qwen TTS WebUI Installer 进行更新中`"
        . `"`$Env:CACHE_HOME/qwen_tts_webui_installer.ps1`" -InstallPath `"`$Env:QWEN_TTS_WEBUI_INSTALLER_ROOT`" -UseUpdateMode
        Print-Msg `"更新结束, 需重新启动 Qwen TTS WebUI Installer 管理脚本以应用更新, 回车退出 Qwen TTS WebUI Installer 管理脚本`"
        Read-Host | Out-Null
        exit 0
    } else {
        Print-Msg `"Qwen TTS WebUI Installer 已是最新版本`"
    }
}


# 获取指定路径的内核路径前缀
function global:Get-Core-Prefix (`$to_path) {
    `$from_path = `$Env:QWEN_TTS_WEBUI_INSTALLER_ROOT
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


# 列出 Qwen TTS WebUI Installer 内置命令
function global:List-CMD {
    Write-Host `"
==================================
Qwen TTS WebUI Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
==================================

当前可用的 Qwen TTS WebUI Installer 内置命令：

    Update-uv
    Update-Aria2
    Check-Qwen-TTS-WebUI-Installer-Update
    Get-Core-Prefix
    List-CMD

更多帮助信息可在 Qwen TTS WebUI Installer 文档中查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md
`"
}


# 显示 Qwen TTS WebUI Installer 版本
function Get-Qwen-TTS-WebUI-Installer-Version {
    `$ver = `$([string]`$Env:QWEN_TTS_WEBUI_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"Qwen TTS WebUI Installer 版本: v`${major}.`${minor}.`${micro}`"
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
    Get-Qwen-TTS-WebUI-Installer-Version
    Get-Qwen-TTS-WebUI-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy
    Set-HuggingFace-Mirror
    Set-Github-Mirror
    PyPI-Mirror-Status
    # 切换 uv 指定的 Python
    if (Test-Path `"`$Env:QWEN_TTS_WEBUI_INSTALLER_ROOT/`$Env:CORE_PREFIX/python/python.exe`") {
        `$Env:UV_PYTHON = `"`$Env:QWEN_TTS_WEBUI_INSTALLER_ROOT/`$Env:CORE_PREFIX/python/python.exe`"
    }
    Print-Msg `"激活 Qwen TTS WebUI Env`"
    Print-Msg `"更多帮助信息可在 Qwen TTS WebUI Installer 项目地址查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md`"
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
    Write-Host `"[Qwen TTS WebUI Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}

Print-Msg `"执行 Qwen TTS WebUI Installer 激活环境脚本`"
& `"`$((Get-Process -Id $PID).Path)`" -NoExit -File `"`$PSScriptRoot/activate.ps1`"
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
Qwen TTS WebUI Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
====================================================================
########## 使用帮助 ##########

这是关于 Qwen TTS WebUI 的简单使用文档。

使用 Qwen TTS WebUI Installer 进行安装并安装成功后，将在当前目录生成 Qwen TTS WebUI 文件夹，以下为文件夹中不同文件 / 文件夹的作用。

- launch.ps1：启动 Qwen TTS WebUI。
- update.ps1：更新 Qwen TTS WebUI。
- reinstall_pytorch.ps1：重新安装 PyTorch 的脚本，在 PyTorch 出问题或者需要切换 PyTorch 版本时可使用。
- settings.ps1：管理 Qwen TTS WebUI Installer 的设置。
- terminal.ps1：启动 PowerShell 终端并自动激活虚拟环境，激活虚拟环境后即可使用 Python、Pip、Git 的命令。
- activate.ps1：虚拟环境激活脚本，使用该脚本激活虚拟环境后即可使用 Python、Pip、Git 的命令。
- launch_qwen_tts_webui_installer.ps1：获取最新的 Qwen TTS WebUI Installer 安装脚本并运行。
- configure_env.bat：配置环境脚本，修复 PowerShell 运行闪退和启用 Windows 长路径支持。

- cache：缓存文件夹，保存着 Pip / HuggingFace 等缓存文件。
- python：Python 的存放路径。请注意，请勿将该 Python 文件夹添加到环境变量，这可能导致不良后果。
- git：Git 的存放路径。
- qwen-tts-webui / core：Qwen TTS WebUI 内核。

详细的 Qwen TTS WebUI Installer 使用帮助：https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md



====================================================================
########## Github 项目 ##########

sd-webui-all-in-one 项目地址：https://github.com/licyk/sd-webui-all-in-one
Qwen TTS WebUI 项目地址：https://github.com/licyk/qwen-tts-webui


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
    Write-Launch-Qwen-TTS-WebUI-Install-Script
    Write-PyTorch-ReInstall-Script
    Write-Qwen-TTS-WebUI-Installer-Settings-Script
    Write-Env-Activate-Script
    Write-Launch-Terminal-Script
    Write-ReadMe
    Write-Configure-Env-Script
}


# 将安装器配置文件复制到管理脚本路径
function Copy-Qwen-TTS-WebUI-Installer-Config {
    Print-Msg "为 Qwen TTS WebUI Installer 管理脚本复制 Qwen TTS WebUI Installer 配置文件中"

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


# 执行安装
function Use-Install-Mode {
    Set-Proxy
    Set-uv
    PyPI-Mirror-Status
    Print-Msg "启动 Qwen TTS WebUI 安装程序"
    Print-Msg "提示: 若出现某个步骤执行失败, 可尝试再次运行 Qwen TTS WebUI Installer, 更多的说明请阅读 Qwen TTS WebUI Installer 使用文档"
    Print-Msg "Qwen TTS WebUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md"
    Print-Msg "即将进行安装的路径: $InstallPath"
    Check-Install
    Print-Msg "添加管理脚本和文档中"
    Write-Manager-Scripts
    Copy-Qwen-TTS-WebUI-Installer-Config

    if ($BuildMode) {
        Use-Build-Mode
        Print-Msg "Qwen TTS WebUI 环境构建完成, 路径: $InstallPath"
    } else {
        Print-Msg "Qwen TTS WebUI 安装结束, 安装路径为: $InstallPath"
    }

    Print-Msg "帮助文档可在 Qwen TTS WebUI 文件夹中查看, 双击 help.txt 文件即可查看, 更多的说明请阅读 Qwen TTS WebUI Installer 使用文档"
    Print-Msg "Qwen TTS WebUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md"
    Print-Msg "退出 Qwen TTS WebUI Installer"

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
        Print-Msg "执行 Qwen TTS WebUI 更新脚本中"
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
        Print-Msg "执行 Qwen TTS WebUI 启动脚本中"
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
function Get-Qwen-TTS-WebUI-Installer-Cmdlet-Help {
    $content = "
使用:
    .\$($script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-InstallPath <安装 Qwen TTS WebUI 的绝对路径>] [-PyTorchMirrorType <PyTorch 镜像源类型>] [-UseUpdateMode] [-DisablePyPIMirror] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableUV] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像站地址>] [-BuildMode] [-BuildWithUpdate] [-BuildWithLaunch] [-BuildWithTorch <PyTorch 版本编号>] [-BuildWithTorchReinstall] [-NoPreDownloadModel] [-PyTorchPackage <PyTorch 软件包>] [-NoCleanCache] [-xFormersPackage <xFormers 软件包>] [-DisableUpdate] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>] [-LaunchArg <Qwen TTS WebUI 启动参数>] [-EnableShortcut] [-DisableCUDAMalloc] [-DisableEnvCheck] [-DisableAutoApplyUpdate]

参数:
    -Help
        获取 Qwen TTS WebUI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -InstallPath <安装 Qwen TTS WebUI 的绝对路径>
        指定 Qwen TTS WebUI Installer 安装 Qwen TTS WebUI 的路径, 使用绝对路径表示
        例如: .\$($script:MyInvocation.MyCommand.Name) -InstallPath `"D:\Donwload`", 这将指定 Qwen TTS WebUI Installer 安装 Qwen TTS WebUI 到 D:\Donwload 这个路径

    -PyTorchMirrorType <PyTorch 镜像源类型>
        指定安装 PyTorch 时使用的 PyTorch 镜像源类型, 可指定的类型: cpu, xpu, cu11x, cu118, cu121, cu124, cu126, cu128, cu129, cu130

    -UseUpdateMode
        指定 Qwen TTS WebUI Installer 使用更新模式, 只对 Qwen TTS WebUI Installer 的管理脚本进行更新

    -DisablePyPIMirror
        禁用 Qwen TTS WebUI Installer 使用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableProxy
        禁用 Qwen TTS WebUI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy `"http://127.0.0.1:10809`" 设置代理服务器地址

    -DisableUV
        禁用 Qwen TTS WebUI Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -DisableGithubMirror
        禁用 Qwen TTS WebUI Installer 自动设置 Github 镜像源

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
        启用 Qwen TTS WebUI Installer 构建模式, 在基础安装流程结束后将调用 Qwen TTS WebUI Installer 管理脚本执行剩余的安装任务, 并且出现错误时不再暂停 Qwen TTS WebUI Installer 的执行, 而是直接退出
        当指定调用多个 Qwen TTS WebUI Installer 脚本时, 将按照优先顺序执行 (按从上到下的顺序)
            - reinstall_pytorch.ps1     (对应 -BuildWithTorch, -BuildWithTorchReinstall 参数)
            - update.ps1                (对应 -BuildWithUpdate 参数)
            - launch.ps1                (对应 -BuildWithLaunch 参数)

    -BuildWithUpdate
        (需添加 -BuildMode 启用 Qwen TTS WebUI Installer 构建模式) Qwen TTS WebUI Installer 执行完基础安装流程后调用 Qwen TTS WebUI Installer 的 update.ps1 脚本, 更新 Qwen TTS WebUI 内核

    -BuildWithLaunch
        (需添加 -BuildMode 启用 Qwen TTS WebUI Installer 构建模式) Qwen TTS WebUI Installer 执行完基础安装流程后调用 Qwen TTS WebUI Installer 的 launch.ps1 脚本, 执行启动 Qwen TTS WebUI 前的环境检查流程, 但跳过启动 Qwen TTS WebUI

    -BuildWithTorch <PyTorch 版本编号>
        (需添加 -BuildMode 启用 Qwen TTS WebUI Installer 构建模式) Qwen TTS WebUI Installer 执行完基础安装流程后调用 Qwen TTS WebUI Installer 的 reinstall_pytorch.ps1 脚本, 根据 PyTorch 版本编号安装指定的 PyTorch 版本
        PyTorch 版本编号可运行 reinstall_pytorch.ps1 脚本进行查看

    -BuildWithTorchReinstall
        (需添加 -BuildMode 启用 Qwen TTS WebUI Installer 构建模式, 并且添加 -BuildWithTorch) 在 Qwen TTS WebUI Installer 构建模式下, 执行 reinstall_pytorch.ps1 脚本对 PyTorch 进行指定版本安装时使用强制重新安装

    -NoPreDownloadModel
        安装 Qwen TTS WebUI 时跳过预下载模型

    -PyTorchPackage <PyTorch 软件包>
        (需要同时搭配 -xFormersPackage 一起使用, 否则可能会出现 PyTorch 和 xFormers 不匹配的问题) 指定要安装 PyTorch 版本, 如 -PyTorchPackage `"torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118`"

    -xFormersPackage <xFormers 软件包>
        (需要同时搭配 -PyTorchPackage 一起使用, 否则可能会出现 PyTorch 和 xFormers 不匹配的问题) 指定要安装 xFormers 版本, 如 -xFormersPackage `"xformers===0.0.26.post1+cu118`"

    -NoCleanCache
        安装结束后保留下载 Python 软件包缓存

    -DisableUpdate
        (仅在 Qwen TTS WebUI Installer 构建模式下生效, 并且只作用于 Qwen TTS WebUI Installer 管理脚本) 禁用 Qwen TTS WebUI Installer 更新检查

    -DisableHuggingFaceMirror
        (仅在 Qwen TTS WebUI Installer 构建模式下生效, 并且只作用于 Qwen TTS WebUI Installer 管理脚本) 禁用 HuggingFace 镜像源, 不使用 HuggingFace 镜像源下载文件

    -UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>
        (仅在 Qwen TTS WebUI Installer 构建模式下生效, 并且只作用于 Qwen TTS WebUI Installer 管理脚本) 使用自定义 HuggingFace 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror `"https://hf-mirror.com`" 设置 HuggingFace 镜像源地址

    -LaunchArg <Qwen TTS WebUI 启动参数>
        (仅在 Qwen TTS WebUI Installer 构建模式下生效, 并且只作用于 Qwen TTS WebUI Installer 管理脚本) 设置 Qwen TTS WebUI 自定义启动参数, 如启用 --in-browser 和 --async-cuda-allocation, 则使用 -LaunchArg `"--in-browser --async-cuda-allocation`" 进行启用

    -EnableShortcut
        (仅在 Qwen TTS WebUI Installer 构建模式下生效, 并且只作用于 Qwen TTS WebUI Installer 管理脚本) 创建 Qwen TTS WebUI 启动快捷方式

    -DisableCUDAMalloc
        (仅在 Qwen TTS WebUI Installer 构建模式下生效, 并且只作用于 Qwen TTS WebUI Installer 管理脚本) 禁用 Qwen TTS WebUI Installer 通过 PYTORCH_CUDA_ALLOC_CONF / PYTORCH_ALLOC_CONF 环境变量设置 CUDA 内存分配器

    -DisableEnvCheck
        (仅在 Qwen TTS WebUI Installer 构建模式下生效, 并且只作用于 Qwen TTS WebUI Installer 管理脚本) 禁用 Qwen TTS WebUI Installer 检查 Qwen TTS WebUI 运行环境中存在的问题, 禁用后可能会导致 Qwen TTS WebUI 环境中存在的问题无法被发现并修复

    -DisableAutoApplyUpdate
        (仅在 Qwen TTS WebUI Installer 构建模式下生效, 并且只作用于 Qwen TTS WebUI Installer 管理脚本) 禁用 Qwen TTS WebUI Installer 自动应用新版本更新


更多的帮助信息请阅读 Qwen TTS WebUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md
".Trim()

    if ($Help) {
        Write-Host $content
        exit 0
    }
}


# 主程序
function Main {
    Print-Msg "初始化中"
    Get-Qwen-TTS-WebUI-Installer-Version
    Get-Qwen-TTS-WebUI-Installer-Cmdlet-Help
    Get-Core-Prefix-Status

    if ($UseUpdateMode) {
        Print-Msg "使用更新模式"
        Use-Update-Mode
        Set-Content -Encoding UTF8 -Path "$InstallPath/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
    } else {
        if ($BuildMode) {
            Print-Msg "Qwen TTS WebUI Installer 构建模式已启用"
        }
        Print-Msg "使用安装模式"
        Use-Install-Mode
    }
}


###################


Main
