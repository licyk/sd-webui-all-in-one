param (
    [switch]$Help,
    [string]$CorePrefix,
    [string]$InstallPath = (Join-Path -Path "$PSScriptRoot" -ChildPath "InvokeAI"),
    [string]$InvokeAIPackage = "InvokeAI",
    [string]$PyTorchMirrorType,
    [switch]$UseUpdateMode,
    [switch]$DisablePyPIMirror,
    [switch]$DisableProxy,
    [string]$UseCustomProxy,
    [switch]$DisableUV,
    [switch]$BuildMode,
    [switch]$BuildWithUpdate,
    [switch]$BuildWithUpdateNode,
    [switch]$BuildWithLaunch,
    [switch]$BuildWithTorchReinstall,
    [string]$BuildWitchModel,
    [switch]$NoCleanCache,

    # 仅在管理脚本中生效
    [switch]$DisableUpdate,
    [switch]$DisableHuggingFaceMirror,
    [string]$UseCustomHuggingFaceMirror,
    [switch]$EnableShortcut,
    [switch]$DisableCUDAMalloc,
    [switch]$DisableEnvCheck,
    [switch]$DisableGithubMirror,
    [string]$UseCustomGithubMirror,
    [switch]$DisableAutoApplyUpdate
)
& {
    $prefix_list = @("invokeai", "InvokeAI", "core")
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
    $Env:CORE_PREFIX = "invokeai"
}
# 有关 PowerShell 脚本保存编码的问题: https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_character_encoding?view=powershell-7.4#the-byte-order-mark
# 在 PowerShell 5 中 UTF8 为 UTF8 BOM, 而在 PowerShell 7 中 UTF8 为 UTF8, 并且多出 utf8BOM 这个单独的选项: https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.management/set-content?view=powershell-7.5#-encoding
$PS_SCRIPT_ENCODING = if ($PSVersionTable.PSVersion.Major -le 5) { "UTF8" } else { "utf8BOM" }
# InvokeAI Installer 版本和检查更新间隔
$INVOKEAI_INSTALLER_VERSION = 286
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
# uv 最低版本
$UV_MINIMUM_VER = "0.8"
# Aria2 最低版本
$ARIA2_MINIMUM_VER = "1.37.0"
# PATH
$PYTHON_PATH = "$InstallPath/python"
$PYTHON_SCRIPTS_PATH = "$InstallPath/python/Scripts"
$GIT_PATH = "$InstallPath/git/bin"
$Env:PATH = "$PYTHON_PATH$([System.IO.Path]::PathSeparator)$PYTHON_SCRIPTS_PATH$([System.IO.Path]::PathSeparator)$GIT_PATH$([System.IO.Path]::PathSeparator)$Env:PATH"
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
$Env:INVOKEAI_ROOT = "$InstallPath/$Env:CORE_PREFIX"
$Env:UV_CACHE_DIR = "$InstallPath/cache/uv"
$Env:UV_PYTHON = "$InstallPath/python/python.exe"



# 消息输出
function Print-Msg ($msg) {
    Write-Host "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")]" -ForegroundColor Yellow -NoNewline
    Write-Host "[InvokeAI Installer]" -ForegroundColor Cyan -NoNewline
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


# 显示 InvokeAI Installer 版本
function Get-InvokeAI-Installer-Version {
    $ver = $([string]$INVOKEAI_INSTALLER_VERSION).ToCharArray()
    $major = ($ver[0..($ver.Length - 3)])
    $minor = $ver[-2]
    $micro = $ver[-1]
    Print-Msg "InvokeAI Installer 版本: v${major}.${minor}.${micro}"
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
        Print-Msg "检测到 disable_uv.txt 配置文件 / -DisableUV 命令行参数, 已禁用 uv, 使用 Pip 作为 Python 包管理器"
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
                Print-Msg "Python 安装失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
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
                Print-Msg "Git 安装失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
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
                Print-Msg "Aria2 安装失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
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
        Print-Msg "uv 下载失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
        if (!($BuildMode)) {
            Read-Host | Out-Null
        }
        exit 1
    }
}


# 安装 InvokeAI
function Install-InvokeAI {
    Print-Msg "正在下载 InvokeAI"
    if ($InvokeAIPackage -ne "InvokeAI") {
        Print-Msg "使用自定义 InvokeAI 版本: $InvokeAIPackage"
    }
    if ($USE_UV) {
        uv pip install $InvokeAIPackage.ToString().Split() --no-deps
        if (!($?)) {
            Print-Msg "检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装"
            python -m pip install $InvokeAIPackage.ToString().Split() --no-deps --use-pep517
        }
    } else {
        python -m pip install $InvokeAIPackage.ToString().Split() --no-deps --use-pep517
    }
    if ($?) { # 检测是否下载成功
        Print-Msg "InvokeAI 安装成功"
    } else {
        Print-Msg "InvokeAI 安装失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
        if (!($BuildMode)) {
            Read-Host | Out-Null
        }
        exit 1
    }
}


# 获取 PyTorch 镜像源
function Get-PyTorch-Mirror {
    $content = "
import re
import json
import subprocess
from importlib.metadata import requires


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


def get_invokeai_require_torch_version() -> str:
    try:
        invokeai_requires = requires('invokeai')
    except:
        return '2.2.2'

    torch_version = 'torch==2.2.2'

    for require in invokeai_requires:
        if get_package_name(require) == 'torch' and has_version(require):
            torch_version = require
            break

    if torch_version.startswith('torch>') and not torch_version.startswith('torch>='):
        return version_increment(get_package_version(torch_version))
    elif torch_version.startswith('torch<') and not torch_version.startswith('torch<='):
        return version_decrement(get_package_version(torch_version))
    elif torch_version.startswith('torch!='):
        return version_increment(get_package_version(torch_version))
    else:
        return get_package_version(torch_version)


if __name__ == '__main__':
    print(get_pytorch_mirror_type(get_invokeai_require_torch_version()))
".Trim()

    # 获取镜像类型
    if ($PyTorchMirrorType) {
        Print-Msg "使用自定义 PyTorch 镜像源类型: $PyTorchMirrorType"
        $mirror_type = $PyTorchMirrorType
    } else {
        $mirror_type = $(python -c "$content")
    }

    # 设置 PyTorch 镜像源
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


# 获取 PyTorch 版本
function Get-PyTorch-Package-Name {
    param (
        [switch]$IgnorexFormers
    )
    if ($IgnorexFormers) {
        $xformers_added = "True"
    } else {
        $xformers_added = "False"
    }
    $content = "
from importlib.metadata import requires


def get_package_name(package: str) -> str:
    return package.split('~=')[0].split('===')[0].split('!=')[0].split('<=')[0].split('>=')[0].split('<')[0].split('>')[0].split('==')[0]


pytorch_ver = []
invokeai_requires = requires('invokeai')
torch_added = False
torchvision_added = False
torchaudio_added = False
xformers_added = $xformers_added

for require in invokeai_requires:
    require = require.split(';')[0].strip()
    package_name = get_package_name(require)

    if package_name == 'torch' and not torch_added:
        pytorch_ver.append(require)
        torch_added = True

    if package_name == 'torchvision' and not torchvision_added:
        pytorch_ver.append(require)
        torchvision_added = True

    if package_name == 'torchaudio' and not torchaudio_added:
        pytorch_ver.append(require)
        torchaudio_added = True

    if package_name == 'xformers' and not xformers_added:
        pytorch_ver.append(require)
        xformers_added = True


ver_list = ' '.join([str(x).strip() for x in pytorch_ver])

print(ver_list)
".Trim()

    return $(python -c "$content")
}


# 安装 PyTorch
function Install-PyTorch {
    $has_pytorch = $false
    $has_xformers = $false
    $mirror_pip_index_url, $mirror_pip_extra_index_url, $mirror_pip_find_links, $pytorch_mirror_type = Get-PyTorch-Mirror
    switch ($pytorch_mirror_type) {
        xpu {
            $ignore_xformers = $true
            $has_xformers = $true
        }
        cpu {
            $ignore_xformers = $true
            $has_xformers = $true
        }
        Default { $ignore_xformers = $false }
    }
    if ($ignore_xformers) {
        $pytorch_package = Get-PyTorch-Package-Name -IgnorexFormers
    } else {
        $pytorch_package = Get-PyTorch-Package-Name
    }

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

    Print-Msg "将要安装的 PyTorch / xFormers: $pytorch_package"
    Print-Msg "检测是否需要安装 PyTorch / xFormers"

    python -m pip show torch --quiet 2> $null
    if ($?) { $has_pytorch = $true }
    if (!($ignore_xformers)) {
        python -m pip show xformers --quiet 2> $null
        if ($?) { $has_xformers = $true }
    }

    if (!$has_pytorch -or !$has_xformers) {
        Print-Msg "安装 PyTorch / xFormers 中"
        if ($USE_UV) {
            uv pip install $pytorch_package.ToString().Split()
            if (!($?)) {
                Print-Msg "检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装"
                python -m pip install $pytorch_package.ToString().Split() --use-pep517 --no-warn-conflicts
            }
        } else {
            python -m pip install $pytorch_package.ToString().Split() --use-pep517 --no-warn-conflicts
        }
        if ($?) {
            Print-Msg "PyTorch / xFormers 安装成功"
        } else {
            Print-Msg "PyTorch / xFormers 安装失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
            if (!($BuildMode)) {
                Read-Host | Out-Null
            }
            exit 1
        }
    } else {
        Print-Msg "PyTorch / xFormers 已安装"
    }

    # 还原镜像源配置
    $Env:PIP_INDEX_URL = $tmp_pip_index_url
    $Env:UV_DEFAULT_INDEX = $tmp_uv_default_index
    $Env:PIP_EXTRA_INDEX_URL = $tmp_pip_extra_index_url
    $Env:UV_INDEX = $tmp_uv_index
    $Env:PIP_FIND_LINKS = $tmp_pip_find_links
    $Env:UV_FIND_LINKS = $tmp_uv_find_links
}


# 安装 InvokeAI 依赖
function Install-InvokeAI-Requirements {
    $content = "
from importlib.metadata import version

try:
    print('invokeai==' + version('invokeai'))
except:
    print('invokeai')
".Trim()
    $invokeai_package = $(python -c "$content")

    Print-Msg "安装 InvokeAI 依赖中"
    if ($USE_UV) {
        uv pip install $invokeai_package.ToString().Split()
        if (!($?)) {
            Print-Msg "检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装"
            python -m pip install $invokeai_package.ToString().Split() --use-pep517
        }
    } else {
        python -m pip install $invokeai_package.ToString().Split() --use-pep517
    }
    if ($?) {
        Print-Msg "InvokeAI 依赖安装成功"
    } else {
        Print-Msg "InvokeAI 依赖安装失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
        if (!($BuildMode)) {
            Read-Host | Out-Null
        }
        exit 1
    }
}


# 安装 LibPatchMatch
function Install-LibPatchMatch {
    $urls = @(
        "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/libpatchmatch_windows_amd64.dll",
        "https://huggingface.co/licyk/invokeai-core-model/resolve/main/pypatchmatch/libpatchmatch_windows_amd64.dll"
    )
    $i = 0

    ForEach ($url in $urls) {
        Print-Msg "下载 libpatchmatch_windows_amd64.dll 中"
        try {
            Invoke-WebRequest -Uri $url -OutFile "$Env:CACHE_HOME/libpatchmatch_windows_amd64.dll"
            break
        }
        catch {
            $i += 1
            if ($i -lt $urls.Length) {
                Print-Msg "重试下载 libpatchmatch_windows_amd64.dll 中"
            } else {
                Print-Msg "下载 libpatchmatch_windows_amd64.dll 失败, 可能导致 InvokeAI 启动异常"
                return
            }
        }
    }

    Move-Item -Path "$Env:CACHE_HOME/libpatchmatch_windows_amd64.dll" -Destination "$InstallPath/python/Lib/site-packages/patchmatch/libpatchmatch_windows_amd64.dll" -Force
    Print-Msg "下载 libpatchmatch_windows_amd64.dll 成功"
}


# 安装 OpenCV World
function Install-OpenCVWorld {
    $urls = @(
        "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/opencv_world460.dll",
        "https://huggingface.co/licyk/invokeai-core-model/resolve/main/pypatchmatch/opencv_world460.dll"
    )
    $i = 0

    ForEach ($url in $urls) {
        Print-Msg "下载 opencv_world460.dll 中"
        try {
            Invoke-WebRequest -Uri $url -OutFile "$Env:CACHE_HOME/opencv_world460.dll"
            break
        }
        catch {
            $i += 1
            if ($i -lt $urls.Length) {
                Print-Msg "重试下载 opencv_world460.dll 中"
            } else {
                Print-Msg "下载 opencv_world460.dll 失败, 可能导致 InvokeAI 启动异常"
                return
            }
        }
    }

    Move-Item -Path "$Env:CACHE_HOME/opencv_world460.dll" -Destination "$InstallPath/python/Lib/site-packages/patchmatch/opencv_world460.dll" -Force
    Print-Msg "下载 opencv_world460.dll 成功"
}


# 下载 PyPatchMatch
function Install-PyPatchMatch {
    if (!(Test-Path "$InstallPath/python/Lib/site-packages/patchmatch/libpatchmatch_windows_amd64.dll")) {
        Install-LibPatchMatch
    } else {
        Print-Msg "无需下载 libpatchmatch_windows_amd64.dll"
    }

    if (!(Test-Path "$InstallPath/python/Lib/site-packages/patchmatch/opencv_world460.dll")) {
        Install-OpenCVWorld
    } else {
        Print-Msg "无需下载 opencv_world460.dll"
    }
}


# 安装
function Check-Install {
    if (!(Test-Path "$InstallPath")) {
        New-Item -ItemType Directory -Path "$InstallPath" > $null
    }

    if (!(Test-Path "$Env:CACHE_HOME")) {
        New-Item -ItemType Directory -Path "$Env:CACHE_HOME" > $null
    }

    Print-Msg "检测是否安装 Python"
    if (Test-Path "$InstallPath/python/python.exe") {
        Print-Msg "Python 已安装"
    } else {
        Print-Msg "Python 未安装"
        Install-Python
    }

    Print-Msg "检测是否安装 Git"
    if (Test-Path "$InstallPath/git/bin/git.exe") {
        Print-Msg "Git 已安装"
    } else {
        Print-Msg "Git 未安装"
        Install-Git
    }

    Print-Msg "检测是否安装 Aria2"
    if (Test-Path "$InstallPath/git/bin/aria2c.exe") {
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

    Print-Msg "检查是否安装 InvokeAI"
    python -m pip show invokeai --quiet 2> $null
    if ($?) {
        Print-Msg "InvokeAI 已安装"
    } else {
        Print-Msg "InvokeAI 未安装"
        Install-InvokeAI
    }

    Install-PyTorch
    Install-InvokeAI-Requirements

    Print-Msg "检测是否需要安装 PyPatchMatch"
    Install-PyPatchMatch

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
    [switch]`$EnableShortcut,
    [switch]`$DisableCUDAMalloc,
    [switch]`$DisableEnvCheck,
    [switch]`$DisableAutoApplyUpdate
)
& {
    `$prefix_list = @(`"invokeai`", `"InvokeAI`", `"core`")
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
    `$Env:CORE_PREFIX = `"invokeai`"
}
# InvokeAI Installer 版本和检查更新间隔
`$INVOKEAI_INSTALLER_VERSION = $INVOKEAI_INSTALLER_VERSION
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
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
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
`$Env:INVOKEAI_ROOT = `"`$PSScriptRoot/`$Env:CORE_PREFIX`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 帮助信息
function Get-InvokeAI-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-DisablePyPIMirror] [-DisableUpdate] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>] [-DisableUV] [-EnableShortcut] [-DisableCUDAMalloc] [-DisableEnvCheck] [-DisableAutoApplyUpdate]

参数:
    -Help
        获取 InvokeAI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 invokeai

    -BuildMode
        启用 InvokeAI Installer 构建模式

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableUpdate
        禁用 InvokeAI Installer 更新检查

    -DisableProxy
        禁用 InvokeAI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableHuggingFaceMirror
        禁用 HuggingFace 镜像源, 不使用 HuggingFace 镜像源下载文件

    -UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>
        使用自定义 HuggingFace 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror ```"https://hf-mirror.com```" 设置 HuggingFace 镜像源地址

    -DisableUV
        禁用 InvokeAI Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -EnableShortcut
        创建 Fooocus 启动快捷方式

    -DisableCUDAMalloc
        禁用 InvokeAI Installer 通过 PYTORCH_CUDA_ALLOC_CONF 环境变量设置 CUDA 内存分配器

    -DisableEnvCheck
        禁用 InvokeAI Installer 检查 Fooocus 运行环境中存在的问题, 禁用后可能会导致 Fooocus 环境中存在的问题无法被发现并修复

    -DisableAutoApplyUpdate
        禁用 InvokeAI Installer 自动应用新版本更新


更多的帮助信息请阅读 InvokeAI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[InvokeAI Installer]`" -ForegroundColor Cyan -NoNewline
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


# 显示 InvokeAI Installer 版本
function Get-InvokeAI-Installer-Version {
    `$ver = `$([string]`$INVOKEAI_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"InvokeAI Installer 版本: v`${major}.`${minor}.`${micro}`"
}


# PyPI 镜像源状态
function PyPI-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 PyPI 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pypi_mirror.txt 配置文件 / -DisablePyPIMirror 命令行参数, 已将 PyPI 源切换至官方源`"
    }
}


# InvokeAI Installer 更新检测
function Check-InvokeAI-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 InvokeAI Installer 的自动检查更新功能`"
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
        Print-Msg `"检查 InvokeAI Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/invokeai_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/invokeai_installer.ps1`" |
                Select-String -Pattern `"INVOKEAI_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 InvokeAI Installer 更新中`"
            } else {
                Print-Msg `"检查 InvokeAI Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -le `$INVOKEAI_INSTALLER_VERSION) {
        Print-Msg `"InvokeAI Installer 已是最新版本`"
        return
    }

    if ((`$DisableAutoApplyUpdate) -or (Test-Path `"`$PSScriptRoot/disable_auto_apply_update.txt`")) {
        Print-Msg `"检测到 InvokeAI Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"========================================>`").Trim()
        if (!(`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`")) {
            Print-Msg `"跳过 InvokeAI Installer 更新`"
            return
        }
    } else {
        Print-Msg `"检测到 InvokeAI Installer 有新版本可用`"
    }

    Print-Msg `"调用 InvokeAI Installer 进行更新中`"
    . `"`$Env:CACHE_HOME/invokeai_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
    `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
    Print-Msg `"更新结束, 重新启动 InvokeAI Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
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


# 获取 InvokeAI 的网页端口
function Get-InvokeAI-Launch-Address {
    `$port = 9090
    `$ip = `"127.0.0.1`"

    Print-Msg `"获取 InvokeAI 界面地址`"
    if (Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX/invokeai.yaml`") {
        # 读取配置文件中的端口配置
        Get-Content -Path `"`$PSScriptRoot/`$Env:CORE_PREFIX/invokeai.yaml`" | ForEach-Object {
            `$matches = [regex]::Matches(`$_, '^(\w+): (.+)')
            foreach (`$match in `$matches) {
                `$key = `$match.Groups[1].Value
                `$value = `$match.Groups[2].Value
                if ((`$key -eq `"port`") -and (!(`$match.Groups[0].Value -eq `"`"))) {
                    `$port = [int]`$value
                    break
                }
            }
        }

        Get-Content -Path `"`$PSScriptRoot/`$Env:CORE_PREFIX/invokeai.yaml`" | ForEach-Object {
            `$matches = [regex]::Matches(`$_, '^(\w+): (.+)')
            foreach (`$match in `$matches) {
                `$key = `$match.Groups[1].Value
                `$value = `$match.Groups[2].Value
                if ((`$key -eq `"host`") -and (!(`$match.Groups[0].Value -eq `"`"))) {
                    `$ip = `$value
                    break
                }
            }
        }
    }

    # 检查端口是否被占用
    while (`$true) {
        if (Get-NetTCPConnection -LocalPort `$port -ErrorAction SilentlyContinue | Where-Object {(`$_.LocalAddress -eq `"127.0.0.1`") -or (`$_.LocalAddress -eq `$ip)}) {
            `$port += 1
        } else {
            break
        }
    }

    return `"http://`${ip}:`${port}`"
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
`".Trim()

    if (!(Test-Path `"`$Env:CACHE_HOME`")) {
        New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" > `$null
    }
    Set-Content -Encoding UTF8 -Path `"`$Env:CACHE_HOME/launch_invokeai.py`" -Value `$content
}


# 设置 InvokeAI 的快捷启动方式
function Create-InvokeAI-Shortcut {
    `$filename = `"InvokeAI`"
    `$url = `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/invokeai_icon.ico`"
    `$shortcut_icon = `"`$PSScriptRoot/invokeai_icon.ico`"

    if ((!(Test-Path `"`$PSScriptRoot/enable_shortcut.txt`")) -and (!(`$EnableShortcut))) {
        return
    }

    Print-Msg `"检测到 enable_shortcut.txt 配置文件 / -EnableShortcut 命令行参数, 开始检查 InvokeAI 快捷启动方式中`"
    if (!(Test-Path `"`$shortcut_icon`")) {
        Print-Msg `"获取 InvokeAI 图标中`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/invokeai_icon.ico`"
        if (!(`$?)) {
            Print-Msg `"获取 InvokeAI 图标失败, 无法创建 InvokeAI 快捷启动方式`"
            return
        }
    }

    Print-Msg `"更新 InvokeAI 快捷启动方式`"
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


# 检查 controlnet_aux
function Check-ControlNet-Aux {
    `$content = `"
try:
    import controlnet_aux
    success = True
except:
    success = False


if not success:
    from importlib.metadata import requires
    try:
        invokeai_requires = requires('invokeai')
    except:
        invokeai_requires = []

    controlnet_aux_ver = None

    for req in invokeai_requires:
        if req.startswith('controlnet-aux=='):
            controlnet_aux_ver = req.split(';')[0].strip()
            break


if success:
    print(None)
else:
    if controlnet_aux_ver is None:
        print('controlnet_aux')
    else:
        print(controlnet_aux_ver)
`".Trim()

    Print-Msg `"检查 controlnet_aux 模块是否已安装, 这可能需要一定时间`"
    `$controlnet_aux_ver = `$(python -c `"`$content`")

    if (`$controlnet_aux_ver -eq `"None`") {
        Print-Msg `"controlnet_aux 已安装`"
    } else {
        Print-Msg `"检测到 controlnet_aux 缺失, 尝试安装中`"
        python -m pip uninstall controlnet_aux -y
        if (`$USE_UV) {
            uv pip install `$controlnet_aux_ver.ToString().Split() --no-cache-dir
            if (!(`$?)) {
                Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
                python -m pip install `$controlnet_aux_ver.ToString().Split() --use-pep517 --no-cache-dir
            }
        } else {
            python -m pip install `$controlnet_aux_ver.ToString().Split() --use-pep517 --no-cache-dir
        }

        if (`$?) {
            Print-Msg `"controlnet_aux 安装成功`"
        } else {
            Print-Msg `"controlnet_aux 安装失败, 可能会导致 InvokeAI 启动异常`"
        }
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


# 检查 InvokeAI 运行环境
function Check-InvokeAI-Env {
    if ((Test-Path `"`$PSScriptRoot/disable_check_env.txt`") -or (`$DisableEnvCheck)) {
        Print-Msg `"检测到 disable_check_env.txt 配置文件 / -DisableEnvCheck 命令行参数, 已禁用 InvokeAI 运行环境检测, 这可能会导致 InvokeAI 运行环境中存在的问题无法被发现并解决`"
        return
    } else {
        Print-Msg `"检查 InvokeAI 运行环境中`"
    }

    Fix-PyTorch
    Check-MS-VCPP-Redistributable
    # Check-ControlNet-Aux
    Check-Onnxruntime-GPU
    Print-Msg `"InvokeAI 运行环境检查完成`"
}


function Main {
    Print-Msg `"初始化中`"
    Get-InvokeAI-Installer-Version
    Get-InvokeAI-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"InvokeAI Installer 构建模式已启用, 跳过 InvokeAI Installer 更新检查`"
    } else {
        Check-InvokeAI-Installer-Update
    }
    Set-HuggingFace-Mirror
    PyPI-Mirror-Status
    Set-uv
    Create-InvokeAI-Shortcut
    Check-InvokeAI-Env
    Set-PyTorch-CUDA-Memory-Alloc

    python -m pip show invokeai --quiet 2> `$null
    if (!(`$?)) {
        Print-Msg `"检测到 InvokeAI 未正确安装, 请运行 InvokeAI Installer 进行修复`"
        return
    }

    if (`$BuildMode) {
        Print-Msg `"InvokeAI Installer 构建模式已启用, 跳过启动 InvokeAI`"
    } else {
        `$web_addr = Get-InvokeAI-Launch-Address
        Print-Msg `"将使用浏览器打开 `$web_addr 地址, 进入 InvokeAI 的界面`"
        Print-Msg `"提示: 打开浏览器后, 浏览器可能会显示连接失败, 这是因为 InvokeAI 未完成启动, 可以在弹出的 PowerShell 中查看 InvokeAI 的启动过程, 等待 InvokeAI 启动完成后刷新浏览器网页即可`"
        Print-Msg `"提示：如果 PowerShell 界面长时间不动, 并且 InvokeAI 未启动, 可以尝试按下几次回车键`"
        Print-Msg `"提示: 如果浏览器未自动打开 `$web_addr 地址, 请手动打开浏览器, 输入 `$web_addr 并打开`"

        Start-Job -ScriptBlock {
            param (`$web_addr)

            Start-Sleep -Seconds 10
            Start-Process `$web_addr
        } -ArgumentList `$web_addr | Out-Null

        Print-Msg `"启动 InvokeAI 中`"
        Write-Launch-InvokeAI-Script
        python `"`$Env:CACHE_HOME/launch_invokeai.py`"
        if (`$?) {
            Print-Msg `"InvokeAI 正常退出`"
        } else {
            Print-Msg `"InvokeAI 出现异常, 已退出`"
        }
        Read-Host | Out-Null
    }
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
    [switch]`$DisableUV,
    [string]`$InvokeAIPackage = `"InvokeAI`",
    [string]`$PyTorchMirrorType,
    [switch]`$DisableAutoApplyUpdate
)
& {
    `$prefix_list = @(`"invokeai`", `"InvokeAI`", `"core`")
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
    `$Env:CORE_PREFIX = `"invokeai`"
}
# InvokeAI Installer 版本和检查更新间隔
`$INVOKEAI_INSTALLER_VERSION = $INVOKEAI_INSTALLER_VERSION
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
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
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
`$Env:INVOKEAI_ROOT = `"`$PSScriptRoot/`$Env:CORE_PREFIX`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 帮助信息
function Get-InvokeAI-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-DisablePyPIMirror] [-DisableUpdate] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableUV] [-InvokeAIPackage <安装 InvokeAI 的软件包名>] [-PyTorchMirrorType <PyTorch 镜像源类型>] [-DisableAutoApplyUpdate]

参数:
    -Help
        获取 InvokeAI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 invokeai

    -BuildMode
        启用 InvokeAI Installer 构建模式

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableUpdate
        禁用 InvokeAI Installer 更新检查

    -DisableProxy
        禁用 InvokeAI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableUV
        禁用 InvokeAI Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -InvokeAIPackage <安装 InvokeAI 的软件包名>
        指定 InvokeAI Installer 安装的 InvokeAI 版本
        例如: .\`$(`$script:MyInvocation.MyCommand.Name) -InvokeAIPackage InvokeAI==5.0.2, 这将指定 InvokeAI Installer 安装 InvokeAI 5.0.2

    -PyTorchMirrorType <PyTorch 镜像源类型>
        指定安装 PyTorch 时使用的 PyTorch 镜像源类型, 可指定的类型: cpu, xpu, cu11x, cu118, cu121, cu124, cu126, cu128, cu129

    -DisableAutoApplyUpdate
        禁用 InvokeAI Installer 自动应用新版本更新


更多的帮助信息请阅读 InvokeAI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[InvokeAI Installer]`" -ForegroundColor Cyan -NoNewline
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


# 显示 InvokeAI Installer 版本
function Get-InvokeAI-Installer-Version {
    `$ver = `$([string]`$INVOKEAI_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"InvokeAI Installer 版本: v`${major}.`${minor}.`${micro}`"
}


# PyPI 镜像源状态
function PyPI-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 PyPI 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pypi_mirror.txt 配置文件 / -DisablePyPIMirror 命令行参数, 已将 PyPI 源切换至官方源`"
    }
}


# InvokeAI Installer 更新检测
function Check-InvokeAI-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 InvokeAI Installer 的自动检查更新功能`"
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
        Print-Msg `"检查 InvokeAI Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/invokeai_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/invokeai_installer.ps1`" |
                Select-String -Pattern `"INVOKEAI_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 InvokeAI Installer 更新中`"
            } else {
                Print-Msg `"检查 InvokeAI Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -le `$INVOKEAI_INSTALLER_VERSION) {
        Print-Msg `"InvokeAI Installer 已是最新版本`"
        return
    }

    if ((`$DisableAutoApplyUpdate) -or (Test-Path `"`$PSScriptRoot/disable_auto_apply_update.txt`")) {
        Print-Msg `"检测到 InvokeAI Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"========================================>`").Trim()
        if (!(`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`")) {
            Print-Msg `"跳过 InvokeAI Installer 更新`"
            return
        }
    } else {
        Print-Msg `"检测到 InvokeAI Installer 有新版本可用`"
    }

    Print-Msg `"调用 InvokeAI Installer 进行更新中`"
    . `"`$Env:CACHE_HOME/invokeai_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
    `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
    Print-Msg `"更新结束, 重新启动 InvokeAI Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
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


# 获取 PyTorch 镜像源
function Get-PyTorch-Mirror {
    `$content = `"
import re
import json
import subprocess
from importlib.metadata import requires


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


def get_invokeai_require_torch_version() -> str:
    try:
        invokeai_requires = requires('invokeai')
    except:
        return '2.2.2'

    torch_version = 'torch==2.2.2'

    for require in invokeai_requires:
        if get_package_name(require) == 'torch' and has_version(require):
            torch_version = require
            break

    if torch_version.startswith('torch>') and not torch_version.startswith('torch>='):
        return version_increment(get_package_version(torch_version))
    elif torch_version.startswith('torch<') and not torch_version.startswith('torch<='):
        return version_decrement(get_package_version(torch_version))
    elif torch_version.startswith('torch!='):
        return version_increment(get_package_version(torch_version))
    else:
        return get_package_version(torch_version)


if __name__ == '__main__':
    print(get_pytorch_mirror_type(get_invokeai_require_torch_version()))
`".Trim()

    # 获取镜像类型
    if (`$PyTorchMirrorType) {
        Print-Msg `"使用自定义 PyTorch 镜像源类型: `$PyTorchMirrorType`"
        `$mirror_type = `$PyTorchMirrorType
    } else {
        `$mirror_type = `$(python -c `"`$content`")
    }

    # 设置 PyTorch 镜像源
    switch (`$mirror_type) {
        cpu {
            Print-Msg `"设置 PyTorch 镜像源类型为 cpu`"
            `$pytorch_mirror_type = `"cpu`"
            `$mirror_index_url = if (`$USE_PIP_MIRROR) {
                `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
            } else {
                `$PIP_EXTRA_INDEX_MIRROR_CPU
            }
            `$mirror_extra_index_url = `"`"
            `$mirror_find_links = `"`"
        }
        xpu {
            Print-Msg `"设置 PyTorch 镜像源类型为 xpu`"
            `$pytorch_mirror_type = `"xpu`"
            `$mirror_index_url = if (`$USE_PIP_MIRROR) {
                `$PIP_EXTRA_INDEX_MIRROR_XPU_NJU
            } else {
                `$PIP_EXTRA_INDEX_MIRROR_XPU
            }
            `$mirror_extra_index_url = `"`"
            `$mirror_find_links = `"`"
        }
        cu11x {
            Print-Msg `"设置 PyTorch 镜像源类型为 cu11x`"
            `$pytorch_mirror_type = `"cu11x`"
            `$mirror_index_url = `$Env:PIP_INDEX_URL
            `$mirror_extra_index_url = `$Env:PIP_EXTRA_INDEX_URL
            `$mirror_find_links = `$Env:PIP_FIND_LINKS
        }
        cu118 {
            Print-Msg `"设置 PyTorch 镜像源类型为 cu118`"
            `$pytorch_mirror_type = `"cu118`"
            `$mirror_index_url = if (`$USE_PIP_MIRROR) {
                `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
            } else {
                `$PIP_EXTRA_INDEX_MIRROR_CU118
            }
            `$mirror_extra_index_url = `"`"
            `$mirror_find_links = `"`"
        }
        cu121 {
            Print-Msg `"设置 PyTorch 镜像源类型为 cu121`"
            `$pytorch_mirror_type = `"cu121`"
            `$mirror_index_url = if (`$USE_PIP_MIRROR) {
                `$PIP_EXTRA_INDEX_MIRROR_CU121_NJU
            } else {
                `$PIP_EXTRA_INDEX_MIRROR_CU121
            }
            `$mirror_extra_index_url = `"`"
            `$mirror_find_links = `"`"
        }
        cu124 {
            Print-Msg `"设置 PyTorch 镜像源类型为 cu124`"
            `$pytorch_mirror_type = `"cu124`"
            `$mirror_index_url = if (`$USE_PIP_MIRROR) {
                `$PIP_EXTRA_INDEX_MIRROR_CU124_NJU
            } else {
                `$PIP_EXTRA_INDEX_MIRROR_CU124
            }
            `$mirror_extra_index_url = `"`"
            `$mirror_find_links = `"`"
        }
        cu126 {
            Print-Msg `"设置 PyTorch 镜像源类型为 cu126`"
            `$pytorch_mirror_type = `"cu126`"
            `$mirror_index_url = if (`$USE_PIP_MIRROR) {
                `$PIP_EXTRA_INDEX_MIRROR_CU126_NJU
            } else {
                `$PIP_EXTRA_INDEX_MIRROR_CU126
            }
            `$mirror_extra_index_url = `"`"
            `$mirror_find_links = `"`"
        }
        cu128 {
            Print-Msg `"设置 PyTorch 镜像源类型为 cu128`"
            `$pytorch_mirror_type = `"cu128`"
            `$mirror_index_url = if (`$USE_PIP_MIRROR) {
                `$PIP_EXTRA_INDEX_MIRROR_CU128_NJU
            } else {
                `$PIP_EXTRA_INDEX_MIRROR_CU128
            }
            `$mirror_extra_index_url = `"`"
            `$mirror_find_links = `"`"
        }
        cu129 {
            Print-Msg `"设置 PyTorch 镜像源类型为 cu129`"
            `$pytorch_mirror_type = `"cu129`"
            `$mirror_index_url = if (`$USE_PIP_MIRROR) {
                `$PIP_EXTRA_INDEX_MIRROR_CU129_NJU
            } else {
                `$PIP_EXTRA_INDEX_MIRROR_CU129
            }
            `$mirror_extra_index_url = `"`"
            `$mirror_find_links = `"`"
        }
        Default {
            Print-Msg `"未知的 PyTorch 镜像源类型: `$mirror_type, 使用默认 PyTorch 镜像源`"
            `$pytorch_mirror_type = `"null`"
            `$mirror_index_url = `$Env:PIP_INDEX_URL
            `$mirror_extra_index_url = `$Env:PIP_EXTRA_INDEX_URL
            `$mirror_find_links = `$Env:PIP_FIND_LINKS
        }
    }
    return `$mirror_index_url, `$mirror_extra_index_url, `$mirror_find_links, `$pytorch_mirror_type
}


# 获取 PyTorch 版本
function Get-PyTorch-Package-Name {
    param (
        [switch]`$IgnorexFormers
    )
    if (`$IgnorexFormers) {
        `$xformers_added = `"True`"
    } else {
        `$xformers_added = `"False`"
    }
    `$content = `"
from importlib.metadata import requires


def get_package_name(package: str) -> str:
    return package.split('~=')[0].split('===')[0].split('!=')[0].split('<=')[0].split('>=')[0].split('<')[0].split('>')[0].split('==')[0]


pytorch_ver = []
invokeai_requires = requires('invokeai')
torch_added = False
torchvision_added = False
torchaudio_added = False
xformers_added = `$xformers_added

for require in invokeai_requires:
    require = require.split(';')[0].strip()
    package_name = get_package_name(require)

    if package_name == 'torch' and not torch_added:
        pytorch_ver.append(require)
        torch_added = True

    if package_name == 'torchvision' and not torchvision_added:
        pytorch_ver.append(require)
        torchvision_added = True

    if package_name == 'torchaudio' and not torchaudio_added:
        pytorch_ver.append(require)
        torchaudio_added = True

    if package_name == 'xformers' and not xformers_added:
        pytorch_ver.append(require)
        xformers_added = True


ver_list = ' '.join([str(x).strip() for x in pytorch_ver])

print(ver_list)
`".Trim()

    return `$(python -c `"`$content`")
}


# 获取 InvokeAI 版本号
function Get-InvokeAI-Version {
    `$content = `"
from importlib.metadata import version

try:
    print('invokeai==' + version('invokeai'))
except:
    print('invokeai==5.0.2')
`".Trim()

    `$status = `$(python -c `"`$content`")
    return `$status
}


# 更新 InvokeAI 内核
function Update-InvokeAI {
    Print-Msg `"更新 InvokeAI 中`"
    if (`$InvokeAIPackage -ne `"InvokeAI`") {
        Print-Msg `"更新到 InvokeAI 指定版本: `$InvokeAIPackage`"
    }
    if (`$USE_UV) {
        uv pip install `$InvokeAIPackage.ToString().Split() --upgrade --no-deps
        if (!(`$?)) {
            Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
            python -m pip install `$InvokeAIPackage.ToString().Split() --upgrade --no-deps --use-pep517
        }
    } else {
        python -m pip install `$InvokeAIPackage.ToString().Split() --upgrade --no-deps --use-pep517
    }

    if (`$?) {
        Print-Msg `"更新 InvokeAI 内核成功`"
        `$Global:UPDATE_INVOKEAI_STATUS = `$true
    } else {
        Print-Msg `"更新 InvokeAI 内核失败`"
        `$Global:UPDATE_INVOKEAI_STATUS = `$false
    }
}


# 更新 PyTorch
function Update-PyTorch {
    `$mirror_pip_index_url, `$mirror_pip_extra_index_url, `$mirror_pip_find_links, `$pytorch_mirror_type = Get-PyTorch-Mirror
    switch (`$pytorch_mirror_type) {
        xpu {
            `$ignore_xformers = `$true
        }
        cpu {
            `$ignore_xformers = `$true
        }
        Default { `$ignore_xformers = `$false }
    }
    if (`$ignore_xformers) {
        `$pytorch_package = Get-PyTorch-Package-Name -IgnorexFormers
    } else {
        `$pytorch_package = Get-PyTorch-Package-Name
    }

    # 备份镜像源配置
    `$tmp_pip_index_url = `$Env:PIP_INDEX_URL
    `$tmp_uv_default_index = `$Env:UV_DEFAULT_INDEX
    `$tmp_pip_extra_index_url = `$Env:PIP_EXTRA_INDEX_URL
    `$tmp_uv_index = `$Env:UV_INDEX
    `$tmp_pip_find_links = `$Env:PIP_FIND_LINKS
    `$tmp_uv_find_links = `$Env:UV_FIND_LINKS

    # 设置新的镜像源
    `$Env:PIP_INDEX_URL = `$mirror_pip_index_url
    `$Env:UV_DEFAULT_INDEX = `$mirror_pip_index_url
    `$Env:PIP_EXTRA_INDEX_URL = `$mirror_pip_extra_index_url
    `$Env:UV_INDEX = `$mirror_pip_extra_index_url
    `$Env:PIP_FIND_LINKS = `$mirror_pip_find_links
    `$Env:UV_FIND_LINKS = `$mirror_pip_find_links

    Print-Msg `"将要安装的 PyTorch / xFormers: `$pytorch_package`"
    Print-Msg `"更新 PyTorch / xFormers 中`"
    if (`$USE_UV) {
        uv pip install `$pytorch_package.ToString().Split()
        if (!(`$?)) {
            Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
            python -m pip install `$pytorch_package.ToString().Split() --use-pep517 --no-warn-conflicts
        }
    } else {
        python -m pip install `$pytorch_package.ToString().Split() --use-pep517 --no-warn-conflicts
    }

    if (`$?) {
        Print-Msg `"PyTorch / xFormers 更新成功`"
        `$Global:UPDATE_PYTORCH_STATUS = `$true
    } else {
        Print-Msg `"PyTorch / xFormers 更新失败`"
        `$Global:UPDATE_PYTORCH_STATUS = `$false
    }

    # 还原镜像源配置
    `$Env:PIP_INDEX_URL = `$tmp_pip_index_url
    `$Env:UV_DEFAULT_INDEX = `$tmp_uv_default_index
    `$Env:PIP_EXTRA_INDEX_URL = `$tmp_pip_extra_index_url
    `$Env:UV_INDEX = `$tmp_uv_index
    `$Env:PIP_FIND_LINKS = `$tmp_pip_find_links
    `$Env:UV_FIND_LINKS = `$tmp_uv_find_links
}


# 更新 InvokeAI 依赖
function Update-InvokeAI-Requirements {
    `$invokeai_core_ver = Get-InvokeAI-Version

    Print-Msg `"更新 InvokeAI 依赖中`"
    if (`$USE_UV) {
        uv pip install `$invokeai_core_ver.ToString().Split()
        if (!(`$?)) {
            Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
            python -m pip install `$invokeai_core_ver.ToString().Split() --use-pep517
        }
    } else {
        python -m pip install `$invokeai_core_ver.ToString().Split() --use-pep517
    }

    if (`$?) {
        Print-Msg `"更新 InvokeAI 依赖成功`"
        `$Global:UPDATE_INVOKEAI_REQ_STATUS = `$true
    } else {
        Print-Msg `"更新 InvokeAI 依赖失败`"
        `$Global:UPDATE_INVOKEAI_REQ_STATUS = `$false
    }
}


# 处理 InvokeAI 更新流程
function Process-InvokeAI-Update {
    `$invokeai_current_ver = Get-InvokeAI-Version
    `$fallback_invokeai_ver = `$false
    `$Global:PROCESS_INVOKEAI_UPDATE_STATUS = `$false

    Print-Msg `"开始更新 InvokeAI`"
    while (`$true) {
        Update-InvokeAI
        if (`$UPDATE_INVOKEAI_STATUS) {
            `$Global:UPDATE_CORE_INFO = `"更新成功`"
        } else {
            `$Global:UPDATE_CORE_INFO = `"更新失败`"
            `$Global:UPDATE_PYTORCH_INFO = `"由于内核更新失败, 不进行 PyTorch 更新`"
            `$Global:UPDATE_REQ_INFO = `"由于内核更新失败, 不进行依赖更新`"
            break
        }

        Update-PyTorch
        if (`$UPDATE_PYTORCH_STATUS) {
            `$Global:UPDATE_PYTORCH_INFO = `"更新成功`"
        } else {
            `$Global:UPDATE_PYTORCH_INFO = `"更新失败`"
            `$Global:UPDATE_REQ_INFO = `"由于 PyTorch 更新失败, 不进行依赖更新`"
            `$fallback_invokeai_ver = `$true
            break
        }

        Update-InvokeAI-Requirements
        if (`$UPDATE_INVOKEAI_REQ_STATUS) {
            `$Global:UPDATE_REQ_INFO = `"更新成功`"
        } else {
            `$Global:UPDATE_REQ_INFO = `"更新成功`"
            `$fallback_invokeai_ver = `$true
            break
        }

        `$Global:PROCESS_INVOKEAI_UPDATE_STATUS = `$true
        break
    }

    if (`$fallback_invokeai_ver) {
        Print-Msg `"尝试回退 InvokeAI 内核版本`"
        if (`$USE_UV) {
            uv pip install `$invokeai_current_ver.ToString().Split() --no-deps
            if (!(`$?)) {
                Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
                python -m pip install `$invokeai_current_ver.ToString().Split() --use-pep517 --no-deps
            }
        } else {
            python -m pip install `$invokeai_current_ver.ToString().Split() --use-pep517 --no-deps
        }
        if (`$?) {
            Print-Msg `"回退 InvokeAI 内核版本成功`"
            `$Global:UPDATE_CORE_INFO = `"由于 InvokeAI 依赖 / PyTorch 更新失败, 已尝试回退内核版本`"
        } else {
            Print-Msg `"回退 InvokeAI 内核版本失败`"
            `$Global:UPDATE_CORE_INFO = `"由于 InvokeAI 依赖 / PyTorch 更新失败, 已尝试回退内核版本, 但出现回退失败`"
        }
    }
}


function Main {
    Print-Msg `"初始化中`"
    Get-InvokeAI-Installer-Version
    Get-InvokeAI-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"InvokeAI Installer 构建模式已启用, 跳过 InvokeAI Installer 更新检查`"
    } else {
        Check-InvokeAI-Installer-Update
    }
    Set-uv
    PyPI-Mirror-Status
    `$ver = `$(python -m pip freeze | Select-String -Pattern `"invokeai`" | Out-String).trim().split(`"==`")[2]
    Process-InvokeAI-Update
    `$ver_ = `$(python -m pip freeze | Select-String -Pattern `"invokeai`" | Out-String).Trim().Split(`"==`")[2]

    Print-Msg `"============================================================================`"
    Print-Msg `"InvokeAI 更新结果：`"
    Print-Msg `"InvokeAI 核心: `$UPDATE_CORE_INFO`"
    Print-Msg `"PyTorch: `$UPDATE_PYTORCH_INFO`"
    Print-Msg `"InvokeAI 依赖: `$UPDATE_REQ_INFO`"
    Print-Msg `"============================================================================`"
    if (`$PROCESS_INVOKEAI_UPDATE_STATUS) {
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


# 更新脚本
function Write-Update-Node-Script {
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
    `$prefix_list = @(`"invokeai`", `"InvokeAI`", `"core`")
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
    `$Env:CORE_PREFIX = `"invokeai`"
}
# InvokeAI Installer 版本和检查更新间隔
`$INVOKEAI_INSTALLER_VERSION = $INVOKEAI_INSTALLER_VERSION
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
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
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
`$Env:INVOKEAI_ROOT = `"`$PSScriptRoot/`$Env:CORE_PREFIX`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 帮助信息
function Get-InvokeAI-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-DisablePyPIMirror] [-DisableUpdate] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像源地址>] [-DisableAutoApplyUpdate]

参数:
    -Help
        获取 InvokeAI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 invokeai

    -BuildMode
        启用 InvokeAI Installer 构建模式

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableUpdate
        禁用 InvokeAI Installer 更新检查

    -DisableProxy
        禁用 InvokeAI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableGithubMirror
        禁用 InvokeAI Installer 自动设置 Github 镜像源

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
        禁用 InvokeAI Installer 自动应用新版本更新


更多的帮助信息请阅读 InvokeAI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[InvokeAI Installer]`" -ForegroundColor Cyan -NoNewline
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


# 显示 InvokeAI Installer 版本
function Get-InvokeAI-Installer-Version {
    `$ver = `$([string]`$INVOKEAI_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"InvokeAI Installer 版本: v`${major}.`${minor}.`${micro}`"
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


# InvokeAI Installer 更新检测
function Check-InvokeAI-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 InvokeAI Installer 的自动检查更新功能`"
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
        Print-Msg `"检查 InvokeAI Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/invokeai_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/invokeai_installer.ps1`" |
                Select-String -Pattern `"INVOKEAI_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 InvokeAI Installer 更新中`"
            } else {
                Print-Msg `"检查 InvokeAI Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -le `$INVOKEAI_INSTALLER_VERSION) {
        Print-Msg `"InvokeAI Installer 已是最新版本`"
        return
    }

    if ((`$DisableAutoApplyUpdate) -or (Test-Path `"`$PSScriptRoot/disable_auto_apply_update.txt`")) {
        Print-Msg `"检测到 InvokeAI Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"========================================>`").Trim()
        if (!(`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`")) {
            Print-Msg `"跳过 InvokeAI Installer 更新`"
            return
        }
    } else {
        Print-Msg `"检测到 InvokeAI Installer 有新版本可用`"
    }

    Print-Msg `"调用 InvokeAI Installer 进行更新中`"
    . `"`$Env:CACHE_HOME/invokeai_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
    `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
    Print-Msg `"更新结束, 重新启动 InvokeAI Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
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


# 列出更新结果
function List-Update-Status (`$update_status) {
    `$success = 0
    `$failed = 0
    `$sum = 0
    Print-Msg `"当前 InvokeAI 自定义节点更新结果`"
    Write-Host `"-----------------------------------------------------`"
    Write-Host `"自定义节点名称`" -ForegroundColor White -NoNewline
    Write-Host `" | `" -NoNewline
    Write-Host `"更新结果`" -ForegroundColor Cyan
    Write-Host
    for (`$i = 0; `$i -lt `$update_status.Count; `$i++) {
        `$content = `$update_status[`$i]
        `$name = `$content[0]
        `$ver = `$content[1]
        `$status = `$content[2]
        `$sum += 1
        if (`$status) {
            `$success += 1
        } else {
            `$failed += 1
        }
        Write-Host `"- `" -ForegroundColor Yellow -NoNewline
        Write-Host `"`${name}: `" -ForegroundColor White -NoNewline
        if (`$status) {
            Write-Host `"`$ver `" -ForegroundColor Cyan
        } else {
            Write-Host `"`$ver `" -ForegroundColor Red
        }
    }
    Write-Host
    Write-Host `"[●: `$sum | ✓: `$success | ×: `$failed]`" -ForegroundColor White
    Write-Host `"-----------------------------------------------------`"
}


function Main {
    Print-Msg `"初始化中`"
    Get-InvokeAI-Installer-Version
    Get-InvokeAI-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"InvokeAI Installer 构建模式已启用, 跳过 InvokeAI Installer 更新检查`"
    } else {
        Check-InvokeAI-Installer-Update
    }
    Set-Github-Mirror

    if (!(Test-Path `"`$PSScriptRoot/`$Env:CORE_PREFIX/nodes`")) {
        Print-Msg `"内核所对应扩展路径 `$PSScriptRoot\`$Env:CORE_PREFIX\nodes 未找到, 无法更新 InvokeAI 自定义节点`"
        Read-Host | Out-Null
        return
    }

    `$node_list = Get-ChildItem -Path `"`$PSScriptRoot/`$Env:CORE_PREFIX/nodes`" | Select-Object -ExpandProperty FullName
    `$sum = 0
    `$count = 0
    ForEach (`$node in `$node_list) {
        if (Test-Path `"`$node/.git`") {
            `$sum += 1
        }
    }

    Print-Msg `"更新 InvokeAI 自定义节点中`"
    `$update_status = New-Object System.Collections.ArrayList
    ForEach (`$node in `$node_list) {
        if (!(Test-Path `"`$node/.git`")) {
            continue
        }

        `$count += 1
        `$node_name = `$(`$(Get-Item `$node).Name)
        Print-Msg `"[`$count/`$sum] 更新 `$node_name 自定义节点中`"
        Fix-Git-Point-Off-Set `"`$node`"
        `$origin_ver = `$(git -C `"`$node`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")
        `$branch = `$(git -C `"`$node`" symbolic-ref --quiet HEAD 2> `$null).split(`"/`")[2]

        git -C `"`$node`" show-ref --verify --quiet `"refs/remotes/origin/`$(git -C `"`$node`" branch --show-current)`"
        if (`$?) {
            `$remote_branch = `"origin/`$branch`"
        } else {
            `$author=`$(git -C `"`$node`" config --get `"branch.`${branch}.remote`")
            if (`$author) {
                `$remote_branch = `$(git -C `"`$node`" rev-parse --abbrev-ref `"`${branch}@{upstream}`")
            } else {
                `$remote_branch = `$branch
            }
        }

        git -C `"`$node`" fetch --recurse-submodules --all
        if (`$?) {
            `$commit_hash = `$(git -C `"`$node`" log `"`$remote_branch`" --max-count 1 --format=`"%h`")
            git -C `"`$node`" reset --hard `"`$remote_branch`" --recurse-submodules
            `$latest_ver = `$(git -C `"`$node`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")
            if (`$origin_ver -eq `$latest_ver) {
                Print-Msg `"[`$count/`$sum] `$node_name 自定义节点已为最新版`"
                `$update_status.Add(@(`$node_name, `"已为最新版`", `$true)) | Out-Null
            } else {
                Print-Msg `"[`$count/`$sum] `$node_name 自定义节点更新成功, 版本：`$origin_ver -> `$latest_ver`"
                `$update_status.Add(@(`$node_name, `"更新成功, 版本：`$origin_ver -> `$latest_ver`", `$true)) | Out-Null
            }
        } else {
            Print-Msg `"[`$count/`$sum] `$node_name 自定义节点更新失败`"
            `$update_status.Add(@(`$node_name, `"更新失败`", `$false)) | Out-Null
        }
    }

    List-Update-Status `$update_status

    Print-Msg `"退出 InvokeAI 自定义节点更新脚本`"
    if (!(`$BuildMode)) {
        Read-Host | Out-Null
    }
}

###################

Main
".Trim()

    if (Test-Path "$InstallPath/update_node.ps1") {
        Print-Msg "更新 update_node.ps1 中"
    } else {
        Print-Msg "生成 update_node.ps1 中"
    }
    Set-Content -Encoding $PS_SCRIPT_ENCODING -Path "$InstallPath/update_node.ps1" -Value $content
}


# 获取安装脚本
function Write-Launch-InvokeAI-Install-Script {
    $content = "
param (
    [string]`$InstallPath,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableUV,
    [Parameter(ValueFromRemainingArguments=`$true)]`$ExtraArgs
)
`$INVOKEAI_INSTALLER_VERSION = $INVOKEAI_INSTALLER_VERSION
if (-not `$InstallPath) {
    `$InstallPath = `$PSScriptRoot
}



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[InvokeAI Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}


# 显示 InvokeAI Installer 版本
function Get-InvokeAI-Installer-Version {
    `$ver = `$([string]`$INVOKEAI_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"InvokeAI Installer 版本: v`${major}.`${minor}.`${micro}`"
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


# 下载 InvokeAI Installer
function Download-InvokeAI-Installer {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    ForEach (`$url in `$urls) {
        Print-Msg `"正在下载最新的 InvokeAI Installer 脚本`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/invokeai_installer.ps1`"
        if (`$?) {
            Print-Msg `"下载 InvokeAI Installer 脚本成功`"
            break
        } else {
            Print-Msg `"下载 InvokeAI Installer 脚本失败`"
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试下载 InvokeAI Installer 脚本`"
            } else {
                Print-Msg `"下载 InvokeAI Installer 脚本失败, 可尝试重新运行 InvokeAI Installer 下载脚本`"
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
    Get-InvokeAI-Installer-Version
    Set-Proxy

    `$status = Download-InvokeAI-Installer

    if (`$status) {
        Print-Msg `"运行 InvokeAI Installer 中`"
        `$arg = Get-Local-Setting
        `$extra_args = Get-ExtraArgs
        try {
            Invoke-Expression `"& ```"`$PSScriptRoot/cache/invokeai_installer.ps1```" `$extra_args @arg`"
        }
        catch {
            Print-Msg `"运行 InvokeAI Installer 时出现了错误: `$_`"
            Read-Host | Out-Null
        }
    } else {
        Read-Host | Out-Null
    }
}

###################

Main
".Trim()

    if (Test-Path "$InstallPath/launch_invokeai_installer.ps1") {
        Print-Msg "更新 launch_invokeai_installer.ps1 中"
    } else {
        Print-Msg "生成 launch_invokeai_installer.ps1 中"
    }
    Set-Content -Encoding $PS_SCRIPT_ENCODING -Path "$InstallPath/launch_invokeai_installer.ps1" -Value $content
}


# PyTorch 重装脚本
function Write-PyTorch-ReInstall-Script {
    $content = "
param (
    [switch]`$Help,
    [string]`$CorePrefix,
    [switch]`$BuildMode,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisableUpdate,
    [switch]`$DisableUV,
    [string]`$InvokeAIPackage = `"InvokeAI`",
    [string]`$PyTorchMirrorType,
    [switch]`$DisableAutoApplyUpdate
)
& {
    `$prefix_list = @(`"invokeai`", `"InvokeAI`", `"core`")
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
    `$Env:CORE_PREFIX = `"invokeai`"
}
# InvokeAI Installer 版本和检查更新间隔
`$INVOKEAI_INSTALLER_VERSION = $INVOKEAI_INSTALLER_VERSION
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
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
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
`$Env:INVOKEAI_ROOT = `"`$PSScriptRoot/`$Env:CORE_PREFIX`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 帮助信息
function Get-InvokeAI-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-DisablePyPIMirror] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableUpdate] [-DisableUV] [-InvokeAIPackage <安装 InvokeAI 的软件包名>] [-PyTorchMirrorType <PyTorch 镜像源类型>] [-DisableAutoApplyUpdate]

参数:
    -Help
        获取 InvokeAI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 invokeai

    -BuildMode
        启用 InvokeAI Installer 构建模式

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableProxy
        禁用 InvokeAI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableUpdate
        禁用 InvokeAI Installer 更新检查

    -DisableUV
        禁用 InvokeAI Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -InvokeAIPackage <安装 InvokeAI 的软件包名>
        指定 InvokeAI Installer 安装的 InvokeAI 版本
        例如: .\`$(`$script:MyInvocation.MyCommand.Name) -InvokeAIPackage InvokeAI==5.0.2, 这将指定 InvokeAI Installer 安装 InvokeAI 5.0.2

    -PyTorchMirrorType <PyTorch 镜像源类型>
        指定安装 PyTorch 时使用的 PyTorch 镜像源类型, 可指定的类型: cpu, xpu, cu11x, cu118, cu121, cu124, cu126, cu128, cu129

    -DisableAutoApplyUpdate
        禁用 InvokeAI Installer 自动应用新版本更新


更多的帮助信息请阅读 InvokeAI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[InvokeAI Installer]`" -ForegroundColor Cyan -NoNewline
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


# 显示 InvokeAI Installer 版本
function Get-InvokeAI-Installer-Version {
    `$ver = `$([string]`$INVOKEAI_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"InvokeAI Installer 版本: v`${major}.`${minor}.`${micro}`"
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


# 获取 PyTorch 镜像源
function Get-PyTorch-Mirror {
    `$content = `"
import re
import json
import subprocess
from importlib.metadata import requires


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


def get_invokeai_require_torch_version() -> str:
    try:
        invokeai_requires = requires('invokeai')
    except:
        return '2.2.2'

    torch_version = 'torch==2.2.2'

    for require in invokeai_requires:
        if get_package_name(require) == 'torch' and has_version(require):
            torch_version = require
            break

    if torch_version.startswith('torch>') and not torch_version.startswith('torch>='):
        return version_increment(get_package_version(torch_version))
    elif torch_version.startswith('torch<') and not torch_version.startswith('torch<='):
        return version_decrement(get_package_version(torch_version))
    elif torch_version.startswith('torch!='):
        return version_increment(get_package_version(torch_version))
    else:
        return get_package_version(torch_version)


if __name__ == '__main__':
    print(get_pytorch_mirror_type(get_invokeai_require_torch_version()))
`".Trim()

    # 获取镜像类型
    if (`$PyTorchMirrorType) {
        Print-Msg `"使用自定义 PyTorch 镜像源类型: `$PyTorchMirrorType`"
        `$mirror_type = `$PyTorchMirrorType
    } else {
        `$mirror_type = `$(python -c `"`$content`")
    }

    # 设置 PyTorch 镜像源
    switch (`$mirror_type) {
        cpu {
            Print-Msg `"设置 PyTorch 镜像源类型为 cpu`"
            `$pytorch_mirror_type = `"cpu`"
            `$mirror_index_url = if (`$USE_PIP_MIRROR) {
                `$PIP_EXTRA_INDEX_MIRROR_CPU_NJU
            } else {
                `$PIP_EXTRA_INDEX_MIRROR_CPU
            }
            `$mirror_extra_index_url = `"`"
            `$mirror_find_links = `"`"
        }
        xpu {
            Print-Msg `"设置 PyTorch 镜像源类型为 xpu`"
            `$pytorch_mirror_type = `"xpu`"
            `$mirror_index_url = if (`$USE_PIP_MIRROR) {
                `$PIP_EXTRA_INDEX_MIRROR_XPU_NJU
            } else {
                `$PIP_EXTRA_INDEX_MIRROR_XPU
            }
            `$mirror_extra_index_url = `"`"
            `$mirror_find_links = `"`"
        }
        cu11x {
            Print-Msg `"设置 PyTorch 镜像源类型为 cu11x`"
            `$pytorch_mirror_type = `"cu11x`"
            `$mirror_index_url = `$Env:PIP_INDEX_URL
            `$mirror_extra_index_url = `$Env:PIP_EXTRA_INDEX_URL
            `$mirror_find_links = `$Env:PIP_FIND_LINKS
        }
        cu118 {
            Print-Msg `"设置 PyTorch 镜像源类型为 cu118`"
            `$pytorch_mirror_type = `"cu118`"
            `$mirror_index_url = if (`$USE_PIP_MIRROR) {
                `$PIP_EXTRA_INDEX_MIRROR_CU118_NJU
            } else {
                `$PIP_EXTRA_INDEX_MIRROR_CU118
            }
            `$mirror_extra_index_url = `"`"
            `$mirror_find_links = `"`"
        }
        cu121 {
            Print-Msg `"设置 PyTorch 镜像源类型为 cu121`"
            `$pytorch_mirror_type = `"cu121`"
            `$mirror_index_url = if (`$USE_PIP_MIRROR) {
                `$PIP_EXTRA_INDEX_MIRROR_CU121_NJU
            } else {
                `$PIP_EXTRA_INDEX_MIRROR_CU121
            }
            `$mirror_extra_index_url = `"`"
            `$mirror_find_links = `"`"
        }
        cu124 {
            Print-Msg `"设置 PyTorch 镜像源类型为 cu124`"
            `$pytorch_mirror_type = `"cu124`"
            `$mirror_index_url = if (`$USE_PIP_MIRROR) {
                `$PIP_EXTRA_INDEX_MIRROR_CU124_NJU
            } else {
                `$PIP_EXTRA_INDEX_MIRROR_CU124
            }
            `$mirror_extra_index_url = `"`"
            `$mirror_find_links = `"`"
        }
        cu126 {
            Print-Msg `"设置 PyTorch 镜像源类型为 cu126`"
            `$pytorch_mirror_type = `"cu126`"
            `$mirror_index_url = if (`$USE_PIP_MIRROR) {
                `$PIP_EXTRA_INDEX_MIRROR_CU126_NJU
            } else {
                `$PIP_EXTRA_INDEX_MIRROR_CU126
            }
            `$mirror_extra_index_url = `"`"
            `$mirror_find_links = `"`"
        }
        cu128 {
            Print-Msg `"设置 PyTorch 镜像源类型为 cu128`"
            `$pytorch_mirror_type = `"cu128`"
            `$mirror_index_url = if (`$USE_PIP_MIRROR) {
                `$PIP_EXTRA_INDEX_MIRROR_CU128_NJU
            } else {
                `$PIP_EXTRA_INDEX_MIRROR_CU128
            }
            `$mirror_extra_index_url = `"`"
            `$mirror_find_links = `"`"
        }
        cu129 {
            Print-Msg `"设置 PyTorch 镜像源类型为 cu129`"
            `$pytorch_mirror_type = `"cu129`"
            `$mirror_index_url = if (`$USE_PIP_MIRROR) {
                `$PIP_EXTRA_INDEX_MIRROR_CU129_NJU
            } else {
                `$PIP_EXTRA_INDEX_MIRROR_CU129
            }
            `$mirror_extra_index_url = `"`"
            `$mirror_find_links = `"`"
        }
        Default {
            Print-Msg `"未知的 PyTorch 镜像源类型: `$mirror_type, 使用默认 PyTorch 镜像源`"
            `$pytorch_mirror_type = `"null`"
            `$mirror_index_url = `$Env:PIP_INDEX_URL
            `$mirror_extra_index_url = `$Env:PIP_EXTRA_INDEX_URL
            `$mirror_find_links = `$Env:PIP_FIND_LINKS
        }
    }
    return `$mirror_index_url, `$mirror_extra_index_url, `$mirror_find_links, `$pytorch_mirror_type
}


# 获取 PyTorch 版本
function Get-PyTorch-Package-Name {
    param (
        [switch]`$IgnorexFormers
    )
    if (`$IgnorexFormers) {
        `$xformers_added = `"True`"
    } else {
        `$xformers_added = `"False`"
    }
    `$content = `"
from importlib.metadata import requires


def get_package_name(package: str) -> str:
    return package.split('~=')[0].split('===')[0].split('!=')[0].split('<=')[0].split('>=')[0].split('<')[0].split('>')[0].split('==')[0]


pytorch_ver = []
invokeai_requires = requires('invokeai')
torch_added = False
torchvision_added = False
torchaudio_added = False
xformers_added = `$xformers_added

for require in invokeai_requires:
    require = require.split(';')[0].strip()
    package_name = get_package_name(require)

    if package_name == 'torch' and not torch_added:
        pytorch_ver.append(require)
        torch_added = True

    if package_name == 'torchvision' and not torchvision_added:
        pytorch_ver.append(require)
        torchvision_added = True

    if package_name == 'torchaudio' and not torchaudio_added:
        pytorch_ver.append(require)
        torchaudio_added = True

    if package_name == 'xformers' and not xformers_added:
        pytorch_ver.append(require)
        xformers_added = True


ver_list = ' '.join([str(x).strip() for x in pytorch_ver])

print(ver_list)
`".Trim()

    return `$(python -c `"`$content`")
}


# InvokeAI Installer 更新检测
function Check-InvokeAI-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 InvokeAI Installer 的自动检查更新功能`"
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
        Print-Msg `"检查 InvokeAI Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/invokeai_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/invokeai_installer.ps1`" |
                Select-String -Pattern `"INVOKEAI_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 InvokeAI Installer 更新中`"
            } else {
                Print-Msg `"检查 InvokeAI Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -le `$INVOKEAI_INSTALLER_VERSION) {
        Print-Msg `"InvokeAI Installer 已是最新版本`"
        return
    }

    if ((`$DisableAutoApplyUpdate) -or (Test-Path `"`$PSScriptRoot/disable_auto_apply_update.txt`")) {
        Print-Msg `"检测到 InvokeAI Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"========================================>`").Trim()
        if (!(`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`")) {
            Print-Msg `"跳过 InvokeAI Installer 更新`"
            return
        }
    } else {
        Print-Msg `"检测到 InvokeAI Installer 有新版本可用`"
    }

    Print-Msg `"调用 InvokeAI Installer 进行更新中`"
    . `"`$Env:CACHE_HOME/invokeai_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
    `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
    Print-Msg `"更新结束, 重新启动 InvokeAI Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
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
    Get-InvokeAI-Installer-Version
    Get-InvokeAI-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"InvokeAI Installer 构建模式已启用, 跳过 InvokeAI Installer 更新检查`"
    } else {
        Check-InvokeAI-Installer-Update
    }
    Set-uv
    PyPI-Mirror-Status

    Get-PyTorch-And-xFormers-Version
    Print-Msg `"是否重新安装 PyTorch (yes/no)?`"
    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
    if (`$BuildMode) {
        `$arg = `"yes`"
    } else {
        `$arg = (Read-Host `"=========================================>`").Trim()
    }
    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
        Print-Msg `"卸载原有的 PyTorch`"
        python -m pip uninstall torch torchvision xformers -y

        python -m pip show invokeai --quiet 2> `$null
        if (!(`$?)) {
            Print-Msg `"检测到 InvokeAI 未安装, 尝试安装中`"
            if (`$InvokeAIPackage -ne `"InvokeAI`") {
                Print-Msg `"安装 InvokeAI 指定版本: `$InvokeAIPackage`"
            }
            if (`$USE_UV) {
                uv pip install `$InvokeAIPackage.ToString().Split() --no-deps
                if (!(`$?)) {
                    Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
                    python -m pip install `$InvokeAIPackage.ToString().Split() --no-deps --use-pep517
                }
            } else {
                python -m pip install `$InvokeAIPackage.ToString().Split() --no-deps --use-pep517
            }
            if (`$?) { # 检测是否下载成功
                Print-Msg `"InvokeAI 安装成功`"
            } else {
                Print-Msg `"InvokeAI 安装失败, 无法进行 PyTorch 重装`"
                if (!(`$BuildMode)) {
                    Read-Host | Out-Null
                }
                exit 1
            }
        }

        `$mirror_pip_index_url, `$mirror_pip_extra_index_url, `$mirror_pip_find_links, `$pytorch_mirror_type = Get-PyTorch-Mirror
        switch (`$pytorch_mirror_type) {
            xpu {
                `$ignore_xformers = `$true
            }
            cpu {
                `$ignore_xformers = `$true
            }
            Default { `$ignore_xformers = `$false }
        }
        if (`$ignore_xformers) {
            `$pytorch_package = Get-PyTorch-Package-Name -IgnorexFormers
        } else {
            `$pytorch_package = Get-PyTorch-Package-Name
        }

        # 备份镜像源配置
        `$tmp_pip_index_url = `$Env:PIP_INDEX_URL
        `$tmp_uv_default_index = `$Env:UV_DEFAULT_INDEX
        `$tmp_pip_extra_index_url = `$Env:PIP_EXTRA_INDEX_URL
        `$tmp_uv_index = `$Env:UV_INDEX
        `$tmp_pip_find_links = `$Env:PIP_FIND_LINKS
        `$tmp_uv_find_links = `$Env:UV_FIND_LINKS

        # 设置新的镜像源
        `$Env:PIP_INDEX_URL = `$mirror_pip_index_url
        `$Env:UV_DEFAULT_INDEX = `$mirror_pip_index_url
        `$Env:PIP_EXTRA_INDEX_URL = `$mirror_pip_extra_index_url
        `$Env:UV_INDEX = `$mirror_pip_extra_index_url
        `$Env:PIP_FIND_LINKS = `$mirror_pip_find_links
        `$Env:UV_FIND_LINKS = `$mirror_pip_find_links

        Print-Msg `"将要安装的 PyTorch / xFormers: `$pytorch_package`"
        Print-Msg `"重新安装 PyTorch`"
        if (`$USE_UV) {
            uv pip install `$pytorch_package.ToString().Split()
            if (!(`$?)) {
                Print-Msg `"检测到 uv 安装 Python 软件包失败, 尝试回滚至 Pip 重试 Python 软件包安装`"
                python -m pip install `$pytorch_package.ToString().Split() --use-pep517
            }
        } else {
            python -m pip install `$pytorch_package.ToString().Split() --use-pep517
        }
        if (`$?) {
            Print-Msg `"重新安装 PyTorch 成功`"
        } else {
            Print-Msg `"重新安装 PyTorch 失败, 请重新运行 PyTorch 重装脚本`"
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
    `$prefix_list = @(`"invokeai`", `"InvokeAI`", `"core`")
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
    `$Env:CORE_PREFIX = `"invokeai`"
}
# InvokeAI Installer 版本和检查更新间隔
`$INVOKEAI_INSTALLER_VERSION = $INVOKEAI_INSTALLER_VERSION
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
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
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
`$Env:INVOKEAI_ROOT = `"`$PSScriptRoot/`$Env:CORE_PREFIX`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 帮助信息
function Get-InvokeAI-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-BuildWitchModel <模型编号列表>] [-DisablePyPIMirror] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableUpdate] [-DisableAutoApplyUpdate]

参数:
    -Help
        获取 InvokeAI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 invokeai

    -BuildMode
        启用 InvokeAI Installer 构建模式

    -BuildWitchModel <模型编号列表>
        (需添加 -BuildMode 启用 InvokeAI Installer 构建模式) InvokeAI Installer 执行完基础安装流程后调用 InvokeAI Installer 的 download_models.ps1 脚本, 根据模型编号列表下载指定的模型
        模型编号可运行 download_models.ps1 脚本进行查看

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableProxy
        禁用 InvokeAI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableUpdate
        禁用 InvokeAI Installer 更新检查

    -DisableAutoApplyUpdate
        禁用 InvokeAI Installer 自动应用新版本更新


更多的帮助信息请阅读 InvokeAI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[InvokeAI Installer]`" -ForegroundColor Cyan -NoNewline
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


# 显示 InvokeAI Installer 版本
function Get-InvokeAI-Installer-Version {
    `$ver = `$([string]`$INVOKEAI_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"InvokeAI Installer 版本: v`${major}.`${minor}.`${micro}`"
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


# InvokeAI Installer 更新检测
function Check-InvokeAI-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    if ((Test-Path `"`$PSScriptRoot/disable_update.txt`") -or (`$DisableUpdate)) {
        Print-Msg `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 InvokeAI Installer 的自动检查更新功能`"
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
        Print-Msg `"检查 InvokeAI Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/invokeai_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/invokeai_installer.ps1`" |
                Select-String -Pattern `"INVOKEAI_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 InvokeAI Installer 更新中`"
            } else {
                Print-Msg `"检查 InvokeAI Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -le `$INVOKEAI_INSTALLER_VERSION) {
        Print-Msg `"InvokeAI Installer 已是最新版本`"
        return
    }

    if ((`$DisableAutoApplyUpdate) -or (Test-Path `"`$PSScriptRoot/disable_auto_apply_update.txt`")) {
        Print-Msg `"检测到 InvokeAI Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
        Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
        `$arg = (Read-Host `"========================================>`").Trim()
        if (!(`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`")) {
            Print-Msg `"跳过 InvokeAI Installer 更新`"
            return
        }
    } else {
        Print-Msg `"检测到 InvokeAI Installer 有新版本可用`"
    }

    Print-Msg `"调用 InvokeAI Installer 进行更新中`"
    . `"`$Env:CACHE_HOME/invokeai_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
    `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
    Print-Msg `"更新结束, 重新启动 InvokeAI Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
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
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/Illustrious-XL-v2.0.safetensors`", `"SDXL`", `"checkpoints`")) | Out-Null
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
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/text_encoders/clip_g.safetensors`", `"SD 3 Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/text_encoders/clip_l.safetensors`", `"SD 3 Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/text_encoders/t5xxl_fp16.safetensors`", `"SD 3 Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/text_encoders/t5xxl_fp8_e4m3fn.safetensors`", `"SD 3 Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd-3-model/resolve/master/text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors`", `"SD 3 Text Encoder`", `"text_encoders`")) | Out-Null
    # FLUX
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev.safetensors`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-fp8.safetensors`", `"FLUX`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux_dev_fp8_scaled_diffusion_model.safetensors`", `"FLUX`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-bnb-nf4-v2.safetensors`", `"FLUX`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-bnb-nf4.safetensors`", `"FLUX`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q2_K.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q3_K_S.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q4_0.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q4_1.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q4_K_S.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q5_0.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q5_1.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q5_K_S.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q6_K.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-Q8_0.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-F16.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell.safetensors`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-fp8.safetensors`", `"FLUX`", `"checkpoints`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q2_K.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q3_K_S.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q4_0.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q4_1.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q4_K_S.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q5_0.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q5_1.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q5_K_S.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q6_K.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-Q8_0.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-F16.gguf`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/ashen0209-flux1-dev2pro.safetensors`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/jimmycarter-LibreFLUX.safetensors`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/nyanko7-flux-dev-de-distill.safetensors`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/shuttle-3-diffusion.safetensors`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-krea-dev_fp8_scaled.safetensors`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-krea-dev.safetensors`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-kontext_fp8_scaled.safetensors`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-kontext-dev.safetensors`", `"FLUX`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/chroma-unlocked-v50.safetensors`", `"FLUX`", `"diffusion_models`")) | Out-Null
    # FLUX Text Encoder
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/clip_l.safetensors`", `"FLUX Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5xxl_fp16.safetensors`", `"FLUX Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5xxl_fp8_e4m3fn.safetensors`", `"FLUX Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q3_K_L.gguf`", `"FLUX Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q3_K_M.gguf`", `"FLUX Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q3_K_S.gguf`", `"FLUX Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q4_K_M.gguf`", `"FLUX Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q4_K_S.gguf`", `"FLUX Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q5_K_M.gguf`", `"FLUX Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q5_K_S.gguf`", `"FLUX Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q6_K.gguf`", `"FLUX Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-Q8_0.gguf`", `"FLUX Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-f16.gguf`", `"FLUX Text Encoder`", `"text_encoders`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5-v1_1-xxl-encoder-f32.gguf`", `"FLUX Text Encoder`", `"text_encoders`")) | Out-Null
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
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev.safetensors`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q3_K_S.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q4_0.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q4_1.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q4_K_S.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q5_0.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q5_1.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q5_K_S.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q6_K.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-Q8_0.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-fp16-F16-GGUF.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-fp16-Q4_0-GGUF.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-fp16-Q5_0-GGUF.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-fp16-Q8_0-GGUF.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-lora-rank128.safetensors`", `"FLUX ControlNet`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-lora-rank256.safetensors`", `"FLUX ControlNet`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-lora-rank32.safetensors`", `"FLUX ControlNet`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-lora-rank4.safetensors`", `"FLUX ControlNet`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-lora-rank64.safetensors`", `"FLUX ControlNet`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-fill-dev-lora-rank8.safetensors`", `"FLUX ControlNet`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-canny-dev-lora.safetensors`", `"FLUX ControlNet`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-canny-dev.safetensors`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-canny-dev-fp16-F16-GGUF.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-canny-dev-fp16-Q4_0-GGUF.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-canny-dev-fp16-Q5_0-GGUF.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-canny-dev-fp16-Q8_0-GGUF.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-depth-dev-fp16-F16-GGUF.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-depth-dev-fp16-Q4_0-GGUF.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-depth-dev-fp16-Q5_0-GGUF.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-depth-dev-fp16-Q8_0-GGUF.gguf`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-depth-dev-lora.safetensors`", `"FLUX ControlNet`", `"loras`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/flux_controlnet/resolve/master/flux1-depth-dev.safetensors`", `"FLUX ControlNet`", `"diffusion_models`")) | Out-Null
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
    `$Global:model_path_list = New-Object System.Collections.ArrayList
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
            `$model_full_path = Join-Path -Path `"`$path`" -ChildPath `"`$model_name`"
            `$model_path_list.Add(`"`$model_full_path`") | Out-Null
        } else {
            Print-Msg `"[`$(`$i + 1)/`$sum] `$name (`$type) 下载失败`"
        }
    }
}


# 获取用户输入
function Get-User-Input {
    return (Read-Host `"=========================================>`").Trim()
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


# InvokeAI 模型导入脚本
function Write-InvokeAI-Import-Model-Script {
    `$content = `"
import os
import asyncio
import argparse
from pathlib import Path
from typing import Union
from invokeai.app.services.model_manager.model_manager_default import ModelManagerService
from invokeai.app.services.model_install.model_install_common import InstallStatus
from invokeai.app.services.model_records.model_records_sql import ModelRecordServiceSQL
from invokeai.app.services.download.download_default import DownloadQueueService
from invokeai.app.services.events.events_fastapievents import FastAPIEventService
from invokeai.app.services.config.config_default import get_config
from invokeai.app.services.shared.sqlite.sqlite_util import init_db
from invokeai.app.services.image_files.image_files_disk import DiskImageFileStorage
from invokeai.backend.util.logging import InvokeAILogger
from invokeai.app.services.invoker import Invoker



invokeai_logger = InvokeAILogger.get_logger('InvokeAI Installer')


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    normalized_filepath = lambda filepath: str(Path(filepath).absolute().as_posix())

    parser.add_argument('--invokeai-path', type = normalized_filepath, default = os.path.join(os.getcwd(), 'invokeai'), help = 'InvokeAI 根路径')
    parser.add_argument('--model-path', type=str, nargs='+', help = '安装的模型路径列表')
    parser.add_argument('--no-link', action='store_true', help = '不使用链接模式, 直接将模型安装在 InvokeAI 目录中')

    return parser.parse_args()


def get_invokeai_model_manager() -> ModelManagerService:
    invokeai_logger.info('初始化 InvokeAI 模型管理服务中')
    configuration = get_config()
    output_folder = configuration.outputs_path
    image_files = DiskImageFileStorage(f'{output_folder}/images')
    logger = InvokeAILogger.get_logger('InvokeAI', config=configuration)
    db = init_db(config=configuration, logger=logger, image_files=image_files)
    event_handler_id = 1234
    loop = asyncio.get_event_loop()
    events=FastAPIEventService(event_handler_id, loop=loop)

    model_manager = ModelManagerService.build_model_manager(
        app_config=configuration,
        model_record_service=ModelRecordServiceSQL(db=db, logger=logger),
        download_queue=DownloadQueueService(app_config=configuration, event_bus=events),
        events=FastAPIEventService(event_handler_id, loop=loop)
    )

    invokeai_logger.info('初始化 InvokeAI 模型管理服务完成')
    return model_manager


def import_model(model_manager: ModelManagerService, inplace: bool, model_path: Union[str, Path]) -> bool:
    file_name = os.path.basename(model_path)
    try:
        invokeai_logger.info(f'导入 {file_name} 模型到 InvokeAI 中')
        job = model_manager.install.heuristic_import(
            source=str(model_path),
            inplace=inplace
        )
        result = model_manager.install.wait_for_job(job)
        if result.status == InstallStatus.COMPLETED:
            invokeai_logger.info(f'导入 {file_name} 模型到 InvokeAI 成功')
            return True
        else:
            invokeai_logger.error(f'导入 {file_name} 模型到 InvokeAI 时出现了错误: {result.error}')
            return False
    except Exception as e:
        invokeai_logger.error(f'导入 {file_name} 模型到 InvokeAI 时出现了错误: {e}')
        return False


def main() -> None:
    args = get_args()
    if not os.environ.get('INVOKEAI_ROOT'):
        os.environ['INVOKEAI_ROOT'] = args.invokeai_path
    model_list = args.model_path
    install_model_to_local = args.no_link
    install_result = []
    count = 0
    task_sum = len(model_list)
    if task_sum == 0:
        invokeai_logger.info('无需要导入的模型')
        return
    invokeai_logger.info('InvokeAI 根目录: {}'.format(os.environ.get('INVOKEAI_ROOT')))
    model_manager = get_invokeai_model_manager()
    invokeai_logger.info('启动 InvokeAI 模型管理服务')
    model_manager.start(Invoker)
    invokeai_logger.info('就地安装 (仅本地) 模式: {}'.format('禁用' if install_model_to_local else '启用'))
    for model in model_list:
        count += 1
        file_name = os.path.basename(model)
        invokeai_logger.info(f'[{count}/{task_sum}] 添加模型: {file_name}')
        result = import_model(
            model_manager=model_manager,
            inplace=not install_model_to_local,
            model_path=model
        )
        install_result.append([model, file_name, result])
    invokeai_logger.info('关闭 InvokeAI 模型管理服务')
    model_manager.stop(Invoker)
    invokeai_logger.info('导入 InvokeAI 模型结果')
    print('-' * 70)
    for _, file, status in install_result:
        status = '导入成功' if status else '导入失败'
        print(f'- {file}: {status}')

    print('-' * 70)
    has_failed = False
    for _, _, x in install_result:
        if not x:
            has_failed = True
            break

    if has_failed:
        invokeai_logger.warning('导入失败的模型列表和模型路径')
        print('-' * 70)
        for model, file_name, status in install_result:
            if not status:
                print(f'- {file_name}: {model}')
        print('-' * 70)
        invokeai_logger.warning(f'导入失败的模型可尝试通过在 InvokeAI 的模型管理 -> 添加模型 -> 链接和本地路径, 手动输入模型路径并添加')

    invokeai_logger.info('导入模型结束')


if __name__ == '__main__':
    main()
`".Trim()

    Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/cache/import_model.py`" -Value `$content
}


# 导入模型到 InvokeAI
function Import-Model-To-InvokeAI (`$model_list) {
    if (`$model_list.Count -eq 0) {
        return
    }

    `$script_args = New-Object System.Collections.ArrayList
    `$script_args.Add(`"--invokeai-path`") | Out-Null
    `$script_args.Add(`"`$Env:INVOKEAI_ROOT`") | Out-Null
    `$script_args.Add(`"--model-path`") | Out-Null
    for (`$i = 0; `$i -lt `$model_list.Count; `$i++) {
        `$content = `$model_list[`$i]
        `$script_args.Add(`"`$content`") | Out-Null
    }
    Write-InvokeAI-Import-Model-Script

    Print-Msg `"执行模型导入脚本中`"
    python `"`$PSScriptRoot/cache/import_model.py`" @script_args
    if (`$?) {
        Print-Msg `"执行模型导入脚本完成`"
    } else {
        Print-Msg `"执行模型导入脚本出现错误, 可能是 InvokeAI 运行环境出现问题, 可尝试重新运行 InvokeAI Installer 进行修复`"
    }
}


function Main {
    Print-Msg `"初始化中`"
    Get-InvokeAI-Installer-Version
    Get-InvokeAI-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy
    if (`$BuildMode) {
        Print-Msg `"InvokeAI Installer 构建模式已启用, 跳过 InvokeAI Installer 更新检查`"
    } else {
        Check-InvokeAI-Installer-Update
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
                        `$path = `"`$PSScriptRoot/models/`$(`$content[2])`" # 模型放置路径
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
        Import-Model-To-InvokeAI `$model_path_list
    }
    Print-Msg `"退出模型下载脚本`"\

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


# InvokeAI Installer 设置脚本
function Write-InvokeAI-Installer-Settings-Script {
    $content = "
param (
    [switch]`$Help,
    [string]`$CorePrefix,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy
)
& {
    `$prefix_list = @(`"invokeai`", `"InvokeAI`", `"core`")
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
    `$Env:CORE_PREFIX = `"invokeai`"
}
# InvokeAI Installer 版本和检查更新间隔
`$INVOKEAI_INSTALLER_VERSION = $INVOKEAI_INSTALLER_VERSION
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
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
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
`$Env:INVOKEAI_ROOT = `"`$PSScriptRoot/`$Env:CORE_PREFIX`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 帮助信息
function Get-InvokeAI-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-DisablePyPIMirror] [-DisableProxy] [-UseCustomProxy <代理服务器地址>]

参数:
    -Help
        获取 InvokeAI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 invokeai

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableProxy
        禁用 InvokeAI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址


更多的帮助信息请阅读 InvokeAI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[InvokeAI Installer]`" -ForegroundColor Cyan -NoNewline
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


# 显示 InvokeAI Installer 版本
function Get-InvokeAI-Installer-Version {
    `$ver = `$([string]`$INVOKEAI_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"InvokeAI Installer 版本: v`${major}.`${minor}.`${micro}`"
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


# 获取 InvokeAI Installer 自动检测更新设置
function Get-InvokeAI-Installer-Auto-Check-Update-Setting {
    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        return `"禁用`"
    } else {
        return `"启用`"
    }
}


# 获取 InvokeAI Installer 自动应用更新设置
function Get-InvokeAI-Installer-Auto-Apply-Update-Setting {
    if (Test-Path `"`$PSScriptRoot/disable_auto_apply_update.txt`") {
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


# PyPI 镜像源配置
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


# 获取 InvokeAI 运行环境检测配置
function Get-InvokeAI-Env-Check-Setting {
    if (!(Test-Path `"`$PSScriptRoot/disable_check_env.txt`")) {
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
    return (Read-Host `"=========================================>`").Trim()
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
        Print-Msg `"警告: 当 InvokeAI Installer 有重要更新(如功能性修复)时, 禁用自动更新检查后将得不到及时提示`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_update.txt`" -Force -Recurse 2> `$null
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


# InvokeAI Installer 自动应用更新设置
function Update-InvokeAI-Installer-Auto-Apply-Update-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 InvokeAI Installer 自动应用更新设置: `$(Get-InvokeAI-Installer-Auto-Apply-Update-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 InvokeAI Installer 自动应用更新`"
        Print-Msg `"2. 禁用 InvokeAI Installer 自动应用更新`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_auto_apply_update.txt`" -Force -Recurse 2> `$null
                Print-Msg `"启用 InvokeAI Installer 自动应用更新成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_auto_apply_update.txt`" -Force > `$null
                Print-Msg `"禁用 InvokeAI Installer 自动应用更新成功`"
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
                Remove-Item -Path `"`$PSScriptRoot/enable_shortcut.txt`" -Force -Recurse 2> `$null
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
                Remove-Item -Path `"`$PSScriptRoot/disable_gh_mirror.txt`" -Force -Recurse 2> `$null
                Remove-Item -Path `"`$PSScriptRoot/gh_mirror.txt`" -Force -Recurse 2> `$null
                Print-Msg `"启用 Github 镜像成功, 在更新 InvokeAI 时将自动检测可用的 Github 镜像源并使用`"
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


# 检查 InvokeAI Installer 更新
function Check-InvokeAI-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null
    Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间

    ForEach (`$url in `$urls) {
        Print-Msg `"检查 InvokeAI Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/invokeai_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/invokeai_installer.ps1`" |
                Select-String -Pattern `"INVOKEAI_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 InvokeAI Installer 更新中`"
            } else {
                Print-Msg `"检查 InvokeAI Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -gt `$INVOKEAI_INSTALLER_VERSION) {
        Print-Msg `"InvokeAI Installer 有新版本可用`"
        Print-Msg `"调用 InvokeAI Installer 进行更新中`"
        . `"`$Env:CACHE_HOME/invokeai_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
        `$raw_params = `$script:MyInvocation.Line -replace `"^.*\.ps1[\s]*`", `"`"
        Print-Msg `"更新结束, 重新启动 InvokeAI Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
        Invoke-Expression `"& ```"`$PSCommandPath```" `$raw_params`"
        exit 0
    } else {
        Print-Msg `"InvokeAI Installer 已是最新版本`"
    }
}


# InvokeAI 运行环境检测设置
function InvokeAI-Env-Check-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 InvokeAI 运行环境检测设置: `$(Get-InvokeAI-Env-Check-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 InvokeAI 运行环境检测`"
        Print-Msg `"2. 禁用 InvokeAI 运行环境检测`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_check_env.txt`" -Force -Recurse 2> `$null
                Print-Msg `"启用 InvokeAI 运行环境检测成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_check_env.txt`" -Force > `$null
                Print-Msg `"禁用 InvokeAI 运行环境检测成功`"
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
    Print-Msg `"Git: `$git_status`"
    Print-Msg `"uv: `$uv_status`"
    Print-Msg `"Aria2: `$aria2_status`"
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
    Get-InvokeAI-Installer-Version
    Get-InvokeAI-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy

    while (`$true) {
        `$go_to = 0
        Print-Msg `"-----------------------------------------------------`"
        Print-Msg `"当前环境配置:`"
        Print-Msg `"代理设置: `$(Get-Proxy-Setting)`"
        Print-Msg `"Python 包管理器: `$(Get-Python-Package-Manager-Setting)`"
        Print-Msg `"HuggingFace 镜像源设置: `$(Get-HuggingFace-Mirror-Setting)`"
        Print-Msg `"InvokeAI Installer 自动检查更新: `$(Get-InvokeAI-Installer-Auto-Check-Update-Setting)`"
        Print-Msg `"InvokeAI Installer 自动应用更新: `$(Get-InvokeAI-Installer-Auto-Apply-Update-Setting)`"
        Print-Msg `"自动创建 InvokeAI 快捷启动方式: `$(Get-Auto-Set-Launch-Shortcut-Setting)`"
        Print-Msg `"Github 镜像源设置: `$(Get-Github-Mirror-Setting)`"
        Print-Msg `"PyPI 镜像源设置: `$(Get-PyPI-Mirror-Setting)`"
        Print-Msg `"自动设置 CUDA 内存分配器设置: `$(Get-PyTorch-CUDA-Memory-Alloc-Setting)`"
        Print-Msg `"InvokeAI 运行环境检测设置: `$(Get-InvokeAI-Env-Check-Setting)`"
        Print-Msg `"InvokeAI 内核路径前缀设置: `$(Get-Core-Prefix-Setting)`"
        Print-Msg `"-----------------------------------------------------`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 进入代理设置`"
        Print-Msg `"2. 进入 Python 包管理器设置`"
        Print-Msg `"3. 进入 HuggingFace 镜像源设置`"
        Print-Msg `"4. 进入 InvokeAI Installer 自动检查更新设置`"
        Print-Msg `"5. 进入 InvokeAI Installer 自动应用更新设置`"
        Print-Msg `"6. 进入自动创建 InvokeAI 快捷启动方式设置`"
        Print-Msg `"7. 进入 Github 镜像源设置`"
        Print-Msg `"8. 进入 PyPI 镜像源设置`"
        Print-Msg `"9. 进入自动设置 CUDA 内存分配器设置`"
        Print-Msg `"10. 进入 InvokeAI 运行环境检测设置`"
        Print-Msg `"11. 进入 InvokeAI 内核路径前缀设置`"
        Print-Msg `"12. 更新 InvokeAI Installer 管理脚本`"
        Print-Msg `"13. 检查环境完整性`"
        Print-Msg `"14. 查看 InvokeAI Installer 文档`"
        Print-Msg `"15. 退出 InvokeAI Installer 设置`"
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
                Update-InvokeAI-Installer-Auto-Apply-Update-Setting
                break
            }
            6 {
                Auto-Set-Launch-Shortcut-Setting
                break
            }
            7 {
                Update-Github-Mirror-Setting
                break
            }
            8 {
                PyPI-Mirror-Setting
                break
            }
            9 {
                PyTorch-CUDA-Memory-Alloc-Setting
                break
            }
            10 {
                InvokeAI-Env-Check-Setting
                break
            }
            11 {
                Update-Core-Prefix-Setting
                break
            }
            12 {
                Check-InvokeAI-Installer-Update
                break
            }
            13 {
                Check-Env
                break
            }
            14 {
                Get-InvokeAI-Installer-Help-Docs
                break
            }
            15 {
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
    `$prefix_list = @(`"invokeai`", `"InvokeAI`", `"core`")
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
    `$Env:CORE_PREFIX = `"invokeai`"
}
# InvokeAI Installer 版本和检查更新间隔
`$Env:INVOKEAI_INSTALLER_VERSION = $INVOKEAI_INSTALLER_VERSION
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
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
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
`$Env:INVOKEAI_ROOT = `"`$PSScriptRoot/`$Env:CORE_PREFIX`"
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"
`$Env:INVOKEAI_INSTALLER_ROOT = `$PSScriptRoot



# 帮助信息
function Get-InvokeAI-Installer-Cmdlet-Help {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-DisablePyPIMirror] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像源地址>] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>]

参数:
    -Help
        获取 InvokeAI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 invokeai

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableGithubMirror
        禁用 InvokeAI Installer 自动设置 Github 镜像源

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
        禁用 InvokeAI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableHuggingFaceMirror
        禁用 HuggingFace 镜像源, 不使用 HuggingFace 镜像源下载文件

    -UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>
        使用自定义 HuggingFace 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror ```"https://hf-mirror.com```" 设置 HuggingFace 镜像源地址


更多的帮助信息请阅读 InvokeAI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 提示信息
function global:prompt {
    `"`$(Write-Host `"[InvokeAI Env]`" -ForegroundColor Green -NoNewLine) `$(Get-Location)> `"
}


# 消息输出
function global:Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[InvokeAI Installer]`" -ForegroundColor Cyan -NoNewline
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

    Move-Item -Path `"`$Env:CACHE_HOME/aria2c.exe`" -Destination `"`$Env:INVOKEAI_INSTALLER_ROOT/git/bin/aria2c.exe`" -Force
    Print-Msg `"更新 Aria2 完成`"
}


# InvokeAI Installer 更新检测
function global:Check-InvokeAI-Installer-Update {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null
    Set-Content -Encoding UTF8 -Path `"`$Env:INVOKEAI_INSTALLER_ROOT/update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间

    ForEach (`$url in `$urls) {
        Print-Msg `"检查 InvokeAI Installer 更新中`"
        try {
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/invokeai_installer.ps1`"
            `$latest_version = [int]`$(
                Get-Content `"`$Env:CACHE_HOME/invokeai_installer.ps1`" |
                Select-String -Pattern `"INVOKEAI_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 InvokeAI Installer 更新中`"
            } else {
                Print-Msg `"检查 InvokeAI Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -gt `$Env:INVOKEAI_INSTALLER_VERSION) {
        Print-Msg `"InvokeAI Installer 有新版本可用`"
        Print-Msg `"调用 InvokeAI Installer 进行更新中`"
        . `"`$Env:CACHE_HOME/invokeai_installer.ps1`" -InstallPath `"`$Env:INVOKEAI_INSTALLER_ROOT`" -UseUpdateMode
        Print-Msg `"更新结束, 需重新启动 InvokeAI Installer 管理脚本以应用更新, 回车退出 InvokeAI Installer 管理脚本`"
        Read-Host | Out-Null
        exit 0
    } else {
        Print-Msg `"InvokeAI Installer 已是最新版本`"
    }
}


# 启用 Github 镜像源
function global:Test-Github-Mirror {
    `$Env:GIT_CONFIG_GLOBAL = `"`$Env:INVOKEAI_INSTALLER_ROOT/.gitconfig`" # 设置 Git 配置文件路径
    if (Test-Path `"`$Env:INVOKEAI_INSTALLER_ROOT/.gitconfig`") {
        Remove-Item -Path `"`$Env:INVOKEAI_INSTALLER_ROOT/.gitconfig`" -Force -Recurse
    }

    # 默认 Git 配置
    git config --global --add safe.directory `"*`"
    git config --global core.longpaths true

    if ((Test-Path `"`$Env:INVOKEAI_INSTALLER_ROOT/disable_gh_mirror.txt`") -or (`$DisableGithubMirror)) { # 禁用 Github 镜像源
        Print-Msg `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件 / -DisableGithubMirror 命令行参数, 禁用 Github 镜像源`"
        return
    }

    if ((Test-Path `"`$Env:INVOKEAI_INSTALLER_ROOT/gh_mirror.txt`") -or (`$UseCustomGithubMirror)) { # 使用自定义 Github 镜像源
        if (`$UseCustomGithubMirror) {
            `$github_mirror = `$UseCustomGithubMirror
        } else {
            `$github_mirror = Get-Content `"`$Env:INVOKEAI_INSTALLER_ROOT/gh_mirror.txt`"
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


# 安装 InvokeAI 自定义节点
function global:Install-InvokeAI-Node (`$url) {
    # 应用 Github 镜像源
    if (`$global:is_test_gh_mirror -ne 1) {
        Test-Github-Mirror
        `$global:is_test_gh_mirror = 1
    }

    `$node_name = `$(Split-Path `$url -Leaf) -replace `".git`", `"`"
    `$cache_path = `"`$Env:CACHE_HOME/`${node_name}_tmp`"
    `$path = `"`$Env:INVOKEAI_ROOT/nodes/`$node_name`"
    if (!(Test-Path `"`$path`")) {
        `$status = 1
    } else {
        `$items = Get-ChildItem `"`$path`" -Recurse
        if (`$items.Count -eq 0) {
            `$status = 1
        }
    }

    if (`$status -eq 1) {
        Print-Msg `"安装 `$node_name 自定义节点中`"
        # 清理缓存路径
        if (Test-Path `"`$cache_path`") {
            Remove-Item -Path `"`$cache_path`" -Force -Recurse
        }
        git clone --recurse-submodules `$url `"`$cache_path`"
        if (`$?) {
            # 清理空文件夹
            if (Test-Path `"`$path`") {
                `$random_string = [Guid]::NewGuid().ToString().Substring(0, 18)
                Move-Item -Path `"`$path`" -Destination `"`$Env:CACHE_HOME/`$random_string`" -Force
            }
            # 将下载好的文件从缓存文件夹移动到指定路径
            New-Item -ItemType Directory -Path `"`$([System.IO.Path]::GetDirectoryName(`$path))`" -Force > `$null
            Move-Item -Path `"`$cache_path`" -Destination `"`$path`" -Force
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


# 列出已安装的 InvokeAI 自定义节点
function global:List-Node {
    `$node_list = Get-ChildItem -Path `"`$Env:INVOKEAI_INSTALLER_ROOT/`$Env:CORE_PREFIX/nodes`" | Select-Object -ExpandProperty FullName
    Print-Msg `"当前 InvokeAI 已安装的自定义节点`"
    `$count = 0
    ForEach (`$i in `$node_list) {
        if (Test-Path `"`$i`" -PathType Container) {
            `$count += 1
            `$name = [System.IO.Path]::GetFileNameWithoutExtension(`"`$i`")
            Print-Msg `"- `$name`"
        }
    }
    Print-Msg `"InvokeAI 自定义节点路径: `$([System.IO.Path]::GetFullPath(`"`$Env:INVOKEAI_INSTALLER_ROOT/`$Env:CORE_PREFIX/nodes`"))`"
    Print-Msg `"InvokeAI 自定义节点数量: `$count`"
}


# 获取指定路径的内核路径前缀
function global:Get-Core-Prefix (`$to_path) {
    `$from_path = `$Env:INVOKEAI_INSTALLER_ROOT
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
    Update-Aria2
    Check-InvokeAI-Installer-Update
    Install-InvokeAI-Node
    Git-Clone
    Test-Github-Mirror
    List-Node
    Get-Core-Prefix
    List-CMD

更多帮助信息可在 InvokeAI Installer 文档中查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md
`"
}


# PyPI 镜像源状态
function PyPI-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 PyPI 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pypi_mirror.txt 配置文件 / -DisablePyPIMirror 命令行参数, 已将 PyPI 源切换至官方源`"
    }
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


# 显示 InvokeAI Installer 版本
function Get-InvokeAI-Installer-Version {
    `$ver = `$([string]`$Env:INVOKEAI_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Print-Msg `"InvokeAI Installer 版本: v`${major}.`${minor}.`${micro}`"
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


function Main {
    Print-Msg `"初始化中`"
    Get-InvokeAI-Installer-Version
    Get-InvokeAI-Installer-Cmdlet-Help
    Get-Core-Prefix-Status
    Set-Proxy
    Set-HuggingFace-Mirror
    PyPI-Mirror-Status
    Print-Msg `"激活 InvokeAI Env`"
    Print-Msg `"更多帮助信息可在 InvokeAI Installer 项目地址查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md`"
}

###################

Main
".Trim()

    if (Test-Path "$InstallPath/activate.ps1") {
        Print-Msg "更新 activate.ps1 中"
    } else {
        Print-Msg "生成 activates.ps1 中"
    }
    Set-Content -Encoding $PS_SCRIPT_ENCODING -Path "$InstallPath/activate.ps1" -Value $content
}


# 快捷启动终端脚本, 启动后将自动运行环境激活脚本
function Write-Launch-Terminal-Script {
    $content = "
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[InvokeAI Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}

Print-Msg `"执行 InvokeAI Installer 激活环境脚本`"
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
InvokeAI Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
====================================================================
########## 使用帮助 ##########

这是关于 InvokeAI 的简单使用文档。

使用 InvokeAI Installer 进行安装并安装成功后，将在当前目录生成 InvokeAI 文件夹，以下为文件夹中不同文件 / 文件夹的作用。

- launch.ps1：启动 InvokeAI。
- update.ps1：更新 InvokeAI。
- update_node.ps1：更新 InvokeAI 自定义节点。
- download_models.ps1：下载模型的脚本，下载的模型将存放在 models 文件夹中。
- reinstall_pytorch.ps1：重装 PyTorch 脚本，解决 PyTorch 无法正常使用或者 xFormers 版本不匹配导致无法调用的问题。
- settings.ps1：管理 InvokeAI Installer 的设置。
- terminal.ps1：启动 PowerShell 终端并自动激活虚拟环境，激活虚拟环境后即可使用 Python、Pip、InvokeAI 的命令。
- activate.ps1：虚拟环境激活脚本，使用该脚本激活虚拟环境后即可使用 Python、Pip、InvokeAI 的命令。
- launch_invokeai_installer.ps1：获取最新的 InvokeAI Installer 安装脚本并运行。
- configure_env.bat：配置环境脚本，修复 PowerShell 运行闪退和启用 Windows 长路径支持。

- cache：缓存文件夹，保存着 Pip / HuggingFace 等缓存文件。
- python：Python 的存放路径，InvokeAI 安装的位置在此处，如果需要重装 InvokeAI，可将该文件夹删除，并使用 InvokeAI Installer 重新部署 InvokeAI。请注意，请勿将该 Python 文件夹添加到环境变量，这可能导致不良后果。
- git：Git 的存放路径。
- invokeai：InvokeAI 存放模型、图片、配置文件等的文件夹。
- models：使用模型下载脚本下载模型时模型的存放位置。

详细的 InvokeAI Installer 使用帮助：https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md

InvokeAI 的使用教程：
SDNote：https://sdnote.netlify.app/guide/invokeai/
InvokeAI 官方文档 1：https://invoke-ai.github.io/InvokeAI
InvokeAI 官方文档 2：https://support.invoke.ai/support/solutions
InvokeAI 官方视频教程：https://www.youtube.com/@invokeai
Reddit 社区：https://www.reddit.com/r/invokeai


====================================================================
########## Github 项目 ##########

sd-webui-all-in-one 项目地址：https://github.com/licyk/sd-webui-all-in-one
InvokeAI 项目地址：https://github.com/invoke-ai/InvokeAI


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
    Write-Update-Node-Script
    Write-Launch-InvokeAI-Install-Script
    Write-Env-Activate-Script
    Write-PyTorch-ReInstall-Script
    Write-Download-Model-Script
    Write-InvokeAI-Installer-Settings-Script
    Write-Launch-Terminal-Script
    Write-ReadMe
    Write-Configure-Env-Script
}


# 将安装器配置文件复制到管理脚本路径
function Copy-InvokeAI-Installer-Config {
    Print-Msg "为 InvokeAI Installer 管理脚本复制 InvokeAI Installer 配置文件中"

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
    Print-Msg "启动 InvokeAI 安装程序"
    Print-Msg "提示: 若出现某个步骤执行失败, 可尝试再次运行 InvokeAI Installer, 更多的说明请阅读 InvokeAI Installer 使用文档"
    Print-Msg "InvokeAI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md"
    Print-Msg "即将进行安装的路径: $InstallPath"
    Check-Install
    Print-Msg "添加管理脚本和文档中"
    Write-Manager-Scripts
    Copy-InvokeAI-Installer-Config

    if ($BuildMode) {
        Use-Build-Mode
        Print-Msg "InvokeAI 环境构建完成, 路径: $InstallPath"
    } else {
        Print-Msg "InvokeAI 安装结束, 安装路径为: $InstallPath"
    }

    Print-Msg "帮助文档可在 InvokeAI 文件夹中查看, 双击 help.txt 文件即可查看, 更多的说明请阅读 InvokeAI Installer 使用文档"
    Print-Msg "InvokeAI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md"
    Print-Msg "退出 InvokeAI Installer"

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

    if ($BuildWithTorchReinstall) {
        $launch_args = @{}
        $launch_args.Add("-BuildMode", $true)
        if ($DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $UseCustomProxy) }
        if ($DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($DisableUV) { $launch_args.Add("-DisableUV", $true) }
        if ($InvokeAIPackage) { $launch_args.Add("-InvokeAIPackage", $InvokeAIPackage) }
        if ($PyTorchMirrorType) { $launch_args.Add("-PyTorchMirrorType", $PyTorchMirrorType) }
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

    if ($BuildWithUpdate) {
        $launch_args = @{}
        $launch_args.Add("-BuildMode", $true)
        if ($DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $UseCustomProxy) }
        if ($DisableUV) { $launch_args.Add("-DisableUV", $true) }
        if ($InvokeAIPackage) { $launch_args.Add("-InvokeAIPackage", $InvokeAIPackage) }
        if ($PyTorchMirrorType) { $launch_args.Add("-PyTorchMirrorType", $PyTorchMirrorType) }
        if ($DisableAutoApplyUpdate) { $launch_args.Add("-DisableAutoApplyUpdate", $true) }
        if ($CorePrefix) { $launch_args.Add("-CorePrefix", $CorePrefix) }
        Print-Msg "执行 InvokeAI 更新脚本中"
        . "$InstallPath/update.ps1" @launch_args
    }

    if ($BuildWithUpdateNode) {
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
        Print-Msg "执行 InvokeAI 自定义节点更新脚本中"
        . "$InstallPath/update_node.ps1" @launch_args
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
        if ($DisableUV) { $launch_args.Add("-DisableUV", $true) }
        if ($EnableShortcut) { $launch_args.Add("-EnableShortcut", $true) }
        if ($DisableCUDAMalloc) { $launch_args.Add("-DisableCUDAMalloc", $true) }
        if ($DisableEnvCheck) { $launch_args.Add("-DisableEnvCheck", $true) }
        if ($DisableAutoApplyUpdate) { $launch_args.Add("-DisableAutoApplyUpdate", $true) }
        if ($CorePrefix) { $launch_args.Add("-CorePrefix", $CorePrefix) }
        Print-Msg "执行 InvokeAI 启动脚本中"
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
function Get-InvokeAI-Installer-Cmdlet-Help {
    $content = "
使用:
    .\$($script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-InstallPath <安装 InvokeAI 的绝对路径>] [-InvokeAIPackage <安装 InvokeAI 的软件包名>] [-PyTorchMirrorType <PyTorch 镜像源类型>] [-UseUpdateMode] [-DisablePyPIMirror] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableUV] [-BuildMode] [-BuildWithUpdate] [-BuildWithUpdateNode] [-BuildWithLaunch] [-BuildWithTorchReinstall] [-BuildWitchModel <模型编号列表>] [-NoCleanCache] [-DisableAutoApplyUpdate]

参数:
    -Help
        获取 InvokeAI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 invokeai

    -InstallPath <安装 InvokeAI 的绝对路径>
        指定 InvokeAI Installer 安装 InvokeAI 的路径, 使用绝对路径表示
        例如: .\$($script:MyInvocation.MyCommand.Name) -InstallPath `"D:\Donwload`", 这将指定 InvokeAI Installer 安装 InvokeAI 到 D:\Donwload 这个路径

    -InvokeAIPackage <安装 InvokeAI 的软件包名>
        指定 InvokeAI Installer 安装的 InvokeAI 版本
        例如: .\$($script:MyInvocation.MyCommand.Name) -InvokeAIPackage InvokeAI==5.0.2, 这将指定 InvokeAI Installer 安装 InvokeAI 5.0.2

    -PyTorchMirrorType <PyTorch 镜像源类型>
        指定安装 PyTorch 时使用的 PyTorch 镜像源类型, 可指定的类型: cpu, xpu, cu11x, cu118, cu121, cu124, cu126, cu128, cu129

    -UseUpdateMode
        指定 InvokeAI Installer 使用更新模式, 只对 InvokeAI Installer 的管理脚本进行更新

    -DisablePyPIMirror
        禁用 InvokeAI Installer 使用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableProxy
        禁用 InvokeAI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy `"http://127.0.0.1:10809`" 设置代理服务器地址

    -DisableUV
        禁用 InvokeAI Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -BuildMode
        启用 InvokeAI Installer 构建模式, 在基础安装流程结束后将调用 InvokeAI Installer 管理脚本执行剩余的安装任务, 并且出现错误时不再暂停 InvokeAI Installer 的执行, 而是直接退出
        当指定调用多个 InvokeAI Installer 脚本时, 将按照优先顺序执行 (按从上到下的顺序)
            - reinstall_pytorch.ps1     (对应 -BuildWithTorchReinstall 参数)
            - download_models.ps1       (对应 -BuildWitchModel 参数)
            - update.ps1                (对应 -BuildWithUpdate 参数)
            - update_node.ps1           (对应 -BuildWithUpdateNode 参数)
            - launch.ps1                (对应 -BuildWithLaunch 参数)

    -BuildWithUpdate
        (需添加 -BuildMode 启用 InvokeAI Installer 构建模式) InvokeAI Installer 执行完基础安装流程后调用 InvokeAI Installer 的 update.ps1 脚本, 更新 InvokeAI 内核

    -BuildWithUpdateNode
        (需添加 -BuildMode 启用 InvokeAI Installer 构建模式) InvokeAI Installer 执行完基础安装流程后调用 InvokeAI Installer 的 update_node.ps1 脚本, 更新 InvokeAI 自定义节点

    -BuildWithLaunch
        (需添加 -BuildMode 启用 InvokeAI Installer 构建模式) InvokeAI Installer 执行完基础安装流程后调用 InvokeAI Installer 的 launch.ps1 脚本, 执行启动 InvokeAI 前的环境检查流程, 但跳过启动 InvokeAI

    -BuildWithTorchReinstall
        (需添加 -BuildMode 启用 InvokeAI Installer 构建模式) InvokeAI Installer 执行完基础安装流程后调用 InvokeAI Installer 的 reinstall_pytorch.ps1 脚本, 卸载并重新安装 PyTorch

    -BuildWitchModel <模型编号列表>
        (需添加 -BuildMode 启用 InvokeAI Installer 构建模式) InvokeAI Installer 执行完基础安装流程后调用 InvokeAI Installer 的 download_models.ps1 脚本, 根据模型编号列表下载指定的模型
        模型编号可运行 download_models.ps1 脚本进行查看

    -NoCleanCache
        安装结束后保留下载 Python 软件包缓存

    -DisableUpdate
        (仅在 InvokeAI Installer 构建模式下生效, 并且只作用于 InvokeAI Installer 管理脚本) 禁用 InvokeAI Installer 更新检查

    -DisableHuggingFaceMirror
        (仅在 InvokeAI Installer 构建模式下生效, 并且只作用于 InvokeAI Installer 管理脚本) 禁用 HuggingFace 镜像源, 不使用 HuggingFace 镜像源下载文件

    -UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>
        (仅在 InvokeAI Installer 构建模式下生效, 并且只作用于 InvokeAI Installer 管理脚本) 使用自定义 HuggingFace 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror `"https://hf-mirror.com`" 设置 HuggingFace 镜像源地址

    -EnableShortcut
        (仅在 InvokeAI Installer 构建模式下生效, 并且只作用于 InvokeAI Installer 管理脚本) 创建 InvokeAI 启动快捷方式

    -DisableCUDAMalloc
        (仅在 InvokeAI Installer 构建模式下生效, 并且只作用于 InvokeAI Installer 管理脚本) 禁用 InvokeAI Installer 通过 PYTORCH_CUDA_ALLOC_CONF 环境变量设置 CUDA 内存分配器

    -DisableEnvCheck
        (仅在 InvokeAI Installer 构建模式下生效, 并且只作用于 InvokeAI Installer 管理脚本) 禁用 InvokeAI Installer 检查 InvokeAI 运行环境中存在的问题, 禁用后可能会导致 InvokeAI 环境中存在的问题无法被发现并修复

    -DisableGithubMirror
        (仅在 InvokeAI Installer 构建模式下生效, 并且只作用于 InvokeAI Installer 管理脚本) 禁用 Fooocus Installer 自动设置 Github 镜像源

    -UseCustomGithubMirror <Github 镜像站地址>
        (仅在 InvokeAI Installer 构建模式下生效, 并且只作用于 InvokeAI Installer 管理脚本) 使用自定义的 Github 镜像站地址
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
        (仅在 InvokeAI Installer 构建模式下生效, 并且只作用于 InvokeAI Installer 管理脚本) 禁用 InvokeAI Installer 自动应用新版本更新


更多的帮助信息请阅读 InvokeAI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md
".Trim()

    if ($Help) {
        Write-Host $content
        exit 0
    }
}


# 主程序
function Main {
    Print-Msg "初始化中"
    Get-InvokeAI-Installer-Version
    Get-InvokeAI-Installer-Cmdlet-Help
    Get-Core-Prefix-Status

    if ($UseUpdateMode) {
        Print-Msg "使用更新模式"
        Use-Update-Mode
        Set-Content -Encoding UTF8 -Path "$InstallPath/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
    } else {
        if ($BuildMode) {
            Print-Msg "InvokeAI Installer 构建模式已启用"
        }
        Print-Msg "使用安装模式"
        Use-Install-Mode
    }
}


###################


Main
