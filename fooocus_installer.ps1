param (
    [string]$InstallPath = "$PSScriptRoot/Fooocus",
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
# Fooocus Installer 版本和检查更新间隔
$FOOOCUS_INSTALLER_VERSION = 110
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
$PIP_EXTRA_INDEX_MIRROR = if ($USE_PIP_MIRROR) { $PIP_EXTRA_INDEX_ADDR } else { $PIP_EXTRA_INDEX_ADDR_ORI }
$PIP_FIND_MIRROR = if ($USE_PIP_MIRROR) { $PIP_FIND_ADDR } else { $PIP_FIND_ADDR_ORI }
# $PIP_FIND_MIRROR_CU121 = "https://download.pytorch.org/whl/cu121/torch_stable.html"
$PIP_EXTRA_INDEX_MIRROR_PYTORCH = "https://download.pytorch.org/whl"
$PIP_EXTRA_INDEX_MIRROR_CU121 = "https://download.pytorch.org/whl/cu121"
$PIP_EXTRA_INDEX_MIRROR_CU124 = "https://download.pytorch.org/whl/cu124"
# Github 镜像源列表
$GITHUB_MIRROR_LIST = @(
    "https://ghfast.top/https://github.com",
    "https://mirror.ghproxy.com/https://github.com",
    "https://ghproxy.net/https://github.com",
    "https://gh.api.99988866.xyz/https://github.com",
    "https://gitclone.com/github.com",
    "https://gh-proxy.com/https://github.com",
    "https://ghps.cc/https://github.com",
    "https://gh.idayer.com/https://github.com"
)
# PyTorch 版本
$PYTORCH_VER = "torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118"
$XFORMERS_VER = "xformers===0.0.26.post1+cu118"
# uv 最低版本
$UV_MINIMUM_VER = "0.5.22"
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
$PYTHON_EXTRA_PATH = "$InstallPath/Fooocus/python"
$PYTHON_SCRIPTS_PATH = "$InstallPath/python/Scripts"
$PYTHON_SCRIPTS_EXTRA_PATH = "$InstallPath/Fooocus/python/Scripts"
$GIT_PATH = "$InstallPath/git/bin"
$GIT_EXTRA_PATH = "$InstallPath/Fooocus/git/bin"
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
    Write-Host "[Fooocus Installer]" -ForegroundColor Cyan -NoNewline
    Write-Host ":: " -ForegroundColor Blue -NoNewline
    Write-Host "$msg"
}


# 显示 Fooocus Installer 版本
function Get-Fooocus-Installer-Version {
    $ver = $([string]$FOOOCUS_INSTALLER_VERSION).ToCharArray()
    $major = ($ver[0..($ver.Length - 3)])
    $minor = $ver[-2]
    $micro = $ver[-1]
    Print-Msg "Fooocus Installer 版本: v${major}.${minor}.${micro}"
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
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/python-3.11.11-amd64.zip"
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
        Print-Msg "Python 安装失败, 终止 Fooocus 安装进程, 可尝试重新运行 Fooocus Installer 重试失败的安装"
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
        Print-Msg "Git 安装失败, 终止 Fooocus 安装进程, 可尝试重新运行 Fooocus Installer 重试失败的安装"
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
        Print-Msg "Aria2 下载失败, 终止 Fooocus 安装进程, 可尝试重新运行 Fooocus Installer 重试失败的安装"
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
        Print-Msg "uv 下载失败, 终止 Fooocus 安装进程, 可尝试重新运行 Fooocus Installer 重试失败的安装"
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
            Print-Msg "PyTorch 安装失败, 终止 Fooocus 安装进程, 可尝试重新运行 Fooocus Installer 重试失败的安装"
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
            Print-Msg "xFormers 安装失败, 终止 Fooocus 安装进程, 可尝试重新运行 Fooocus Installer 重试失败的安装"
            Read-Host | Out-Null
            exit 1
        }
    } else {
        Print-Msg "xFormers 已安装, 无需再次安装"
    }
}


# 安装 Fooocus 依赖
function Install-Fooocus-Dependence {
    # 记录脚本所在路径
    $current_path = $(Get-Location).ToString()
    Set-Location "$InstallPath/Fooocus"
    $dep_path = "$InstallPath/Fooocus/requirements_versions.txt"

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
        Read-Host | Out-Null
        exit 1
    }
    Set-Location "$current_path"
}


# 模型预下载
function Pre-Donwload-Model ($download_task) {
    ForEach ($task in $download_task) {
        $url = $task[0]
        $path = $task[1]
        $filename = $task[2]
        if (Test-Path "$path/$filename") {
            Print-Msg "$filename 已下载, 路径: $path/$filename"
        } else {
            Print-Msg "下载 $filename 中, 路径: $path/$filename"
            aria2c --file-allocation=none --summary-interval=0 --console-log-level=error -s 64 -c -x 16 -k 1M "$url" -d "$path" -o "$filename"
            if ($?) {
                Print-Msg "$filename 下载成功"
            } else {
                Print-Msg "$filename 下载失败"
            }
        }
    }
}


# 更新 Fooocus 预设文件
function Update-Fooocus-Preset {
    $fooocus_preset_json_content = @{
        "default_model" = "Illustrious-XL-v0.1.safetensors"
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
        "default_sampler" = "dpmpp_2m_sde_gpu"
        "default_scheduler" = "sgm_uniform"
        "default_performance" = "Speed"
        "default_prompt" = "`nmasterpiece,best quality,newest,"
        "default_prompt_negative" = "low quality,worst quality,normal quality,text,signature,jpeg artifacts,bad anatomy,old,early,copyright name,watermark,artist name,signature,"
        "default_styles" = @()
        "default_image_number" = 1
        "default_aspect_ratio" = "1344*1008"
        "checkpoint_downloads" = @{
            "Illustrious-XL-v0.1.safetensors" = "https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/Illustrious-XL-v0.1.safetensors"
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
    $utf8Encoding = New-Object System.Text.UTF8Encoding($false)

    $fooocus_preset_json_content = $fooocus_preset_json_content | ConvertTo-Json -Depth 4
    $fooocus_language_zh_json_content = $fooocus_language_zh_json_content | ConvertTo-Json -Depth 4

    Print-Msg "更新 Fooocus 预设文件"
    $streamWriter = [System.IO.StreamWriter]::new("$InstallPath/Fooocus/presets/fooocus_installer.json", $false, $utf8Encoding)
    $streamWriter.Write($fooocus_preset_json_content)
    $streamWriter.Close()

    Print-Msg "更新 Fooocus 翻译文件"
    $streamWriter = [System.IO.StreamWriter]::new("$InstallPath/Fooocus/language/zh.json", $false, $utf8Encoding)
    $streamWriter.Write($fooocus_language_zh_json_content)
    $streamWriter.Close()
}


# 安装
function Check-Install {
    New-Item -ItemType Directory -Path "$InstallPath" -Force > $null
    New-Item -ItemType Directory -Path "$Env:CACHE_HOME" -Force > $null

    Print-Msg "检测是否安装 Python"
    if ((Test-Path "$InstallPath/python/python.exe") -or (Test-Path "$InstallPath/Fooocus/python/python.exe")) {
        Print-Msg "Python 已安装"
    } else {
        Print-Msg "Python 未安装"
        Install-Python
    }

    # 切换 uv 指定的 Python
    if (Test-Path "$InstallPath/Fooocus/python/python.exe") {
        $Env:UV_PYTHON = "$InstallPath/Fooocus/python/python.exe"
    }

    Print-Msg "检测是否安装 Git"
    if ((Test-Path "$InstallPath/git/bin/git.exe") -or (Test-Path "$InstallPath/Fooocus/git/bin/git.exe")) {
        Print-Msg "Git 已安装"
    } else {
        Print-Msg "Git 未安装"
        Install-Git
    }

    Print-Msg "检测是否安装 Aria2"
    if ((Test-Path "$InstallPath/git/bin/aria2c.exe") -or (Test-Path "$InstallPath/Fooocus/git/bin/aria2c.exe")) {
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

    # Fooocus 核心
    Git-CLone "$FOOOCUS_REPO" "$InstallPath/Fooocus"

    Install-PyTorch
    Install-Fooocus-Dependence

    if (!(Test-Path "$InstallPath/launch_args.txt")) {
        Print-Msg "设置默认 Fooocus 启动参数"
        $content = "--language zh --preset fooocus_installer --disable-offload-from-vram --disable-analytics"
        Set-Content -Encoding UTF8 -Path "$InstallPath/launch_args.txt" -Value $content
    }

    Update-Fooocus-Preset

    $model_list = @(
        @("https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/Illustrious-XL-v0.1.safetensors", "$InstallPath/Fooocus/models/checkpoints", "Illustrious-XL-v0.1.safetensors"),
        @("https://modelscope.cn/models/licyks/fooocus-model/resolve/master/vae_approx/vaeapp_sd15.pth", "$InstallPath/Fooocus/models/vae_approx", "vaeapp_sd15.pth"),
        @("https://modelscope.cn/models/licyks/fooocus-model/resolve/master/vae_approx/xlvaeapp.pth", "$InstallPath/Fooocus/models/vae_approx", "xlvaeapp.pth"),
        @("https://modelscope.cn/models/licyks/fooocus-model/resolve/master/vae_approx/xl-to-v1_interposer-v4.0.safetensors", "$InstallPath/Fooocus/models/vae_approx", "xl-to-v1_interposer-v4.0.safetensors"),
        @("https://modelscope.cn/models/licyks/fooocus-model/resolve/master/prompt_expansion/fooocus_expansion/pytorch_model.bin", "$InstallPath/Fooocus/models/prompt_expansion/fooocus_expansion", "pytorch_model.bin")
    )

    Print-Msg "预下载模型中"
    Pre-Donwload-Model $model_list

    # 清理缓存
    Print-Msg "清理下载 Python 软件包的缓存中"
    python -m pip cache purge
    uv cache clean

    Set-Content -Encoding UTF8 -Path "$InstallPath/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
}


# 启动脚本
function Write-Launch-Script {
    $content = "
# Fooocus Installer 版本和检查更新间隔
`$FOOOCUS_INSTALLER_VERSION = $FOOOCUS_INSTALLER_VERSION
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
    `"https://ghfast.top/https://github.com`",
    `"https://mirror.ghproxy.com/https://github.com`",
    `"https://ghproxy.net/https://github.com`",
    `"https://gh.api.99988866.xyz/https://github.com`",
    `"https://gitclone.com/github.com`",
    `"https://gh-proxy.com/https://github.com`",
    `"https://ghps.cc/https://github.com`",
    `"https://gh.idayer.com/https://github.com`"
)
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/git/bin`"
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

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 Fooocus Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 Fooocus Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/fooocus_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/fooocus_installer.ps1`" | Select-String -Pattern `"FOOOCUS_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$FOOOCUS_INSTALLER_VERSION) {
                    Print-Msg `"检测到 Fooocus Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"========================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 Fooocus Installer 进行更新中`"
                        . `"`$Env:CACHE_HOME/fooocus_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
                        Print-Msg `"更新结束, 需重新启动 Fooocus Installer 管理脚本以应用更新, 回车退出 Fooocus Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Print-Msg `"跳过 Fooocus Installer 更新`"
                    }
                } else {
                    Print-Msg `"Fooocus Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 Fooocus Installer 更新中`"
                } else {
                    Print-Msg `"检查 Fooocus Installer 更新失败`"
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
        if (Test-Path `"`$PSScriptRoot/Fooocus/python/python.exe`") {
            `$Env:UV_PYTHON = `"`$PSScriptRoot/Fooocus/python/python.exe`"
        }
        Check-uv-Version
    }
}


# Fooocus 启动参数
function Get-Fooocus-Launch-Args {
    if (Test-Path `"`$PSScriptRoot/launch_args.txt`") {
        `$args = Get-Content `"`$PSScriptRoot/launch_args.txt`"
        Print-Msg `"检测到本地存在 launch_args.txt 启动参数配置文件, 已读取该启动参数配置文件并应用启动参数`"
        Print-Msg `"使用的启动参数: `$args`"
    } else {
        `$args = `"`"
    }
    return `$args
}


# 设置 Fooocus 的快捷启动方式
function Create-Fooocus-Shortcut {
    `$filename = `"Fooocus`"
    `$url = `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/gradio_icon.ico`"
    `$shortcut_icon = `"`$PSScriptRoot/gradio_icon.ico`"

    if (!(Test-Path `"`$PSScriptRoot/enable_shortcut.txt`")) {
        return
    }

    Print-Msg `"检查 Fooocus 快捷启动方式中`"
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


# 检查 Fooocus 依赖完整性
function Check-Fooocus-Requirements {
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
            elif '!=' in pkg:
                pkg_name, pkg_version = [x.strip() for x in pkg.split('!=')]
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
                    elif '!=' in pkg:
                        # ok = version != pkg_version
                        if compare_versions(version, pkg_version) != 0:
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
    Print-Msg `"检查 Fooocus 内核依赖完整性中`"
    if (!(Test-Path `"`$Env:CACHE_HOME`")) {
        New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" > `$null
    }
    Set-Content -Encoding UTF8 -Path `"`$Env:CACHE_HOME/check_fooocus_requirement.py`" -Value `$content

    `$dep_path = `"`$PSScriptRoot/Fooocus/requirements_versions.txt`"
    # SD Next
    if (!(Test-Path `"`$dep_path`")) {
        `$dep_path = `"`$PSScriptRoot/Fooocus/requirements.txt`"
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
    return ''.join(re.findall(r'[\d.]+', ver.split('=').pop().strip()))


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
    if (Test-Path `"`$PSScriptRoot/disable_check_env.txt`") {
        Print-Msg `"检测到 disable_check_env.txt 配置文件, 已禁用 Fooocus 运行环境检测, 这可能会导致 Fooocus 运行环境中存在的问题无法被发现并解决`"
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


function Main {
    Print-Msg `"初始化中`"
    Get-Fooocus-Installer-Version
    Set-Proxy
    Check-Fooocus-Installer-Update
    Set-HuggingFace-Mirror
    Set-uv
    Pip-Mirror-Status

    if (!(Test-Path `"`$PSScriptRoot/Fooocus`")) {
        Print-Msg `"在 `$PSScriptRoot 路径中未找到 Fooocus 文件夹, 请检查 Fooocus 是否已正确安装, 或者尝试运行 Fooocus Installer 进行修复`"
        return
    }

    `$args = Get-Fooocus-Launch-Args
    # 记录上次的路径
    `$current_path = `$(Get-Location).ToString()

    if (!(Test-Path `"`$PSScriptRoot/disable_hf_mirror.txt`")) {
        `$hf_mirror_arg = `"--hf-mirror `$Env:HF_ENDPOINT`"
    } else {
        `$hf_mirror_arg = `"`"
    }

    Create-Fooocus-Shortcut
    Check-Fooocus-Env
    Set-PyTorch-CUDA-Memory-Alloc
    Print-Msg `"启动 Fooocus 中`"
    Set-Location `"`$PSScriptRoot/Fooocus`"
    python launch.py `$args.ToString().Split() `$hf_mirror_arg.ToString().Split()
    `$req = `$?
    if (`$req) {
        Print-Msg `"Fooocus 正常退出`"
    } else {
        Print-Msg `"Fooocus 出现异常, 已退出`"
    }
    Set-Location `"`$current_path`"
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$InstallPath/launch.ps1") {
        Print-Msg "更新 launch.ps1 中"
    } else {
        Print-Msg "生成 launch.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$InstallPath/launch.ps1" -Value $content
}


# 更新脚本
function Write-Update-Script {
    $content = "
# Fooocus Installer 版本和检查更新间隔
`$FOOOCUS_INSTALLER_VERSION = $FOOOCUS_INSTALLER_VERSION
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
    `"https://ghfast.top/https://github.com`",
    `"https://mirror.ghproxy.com/https://github.com`",
    `"https://ghproxy.net/https://github.com`",
    `"https://gh.api.99988866.xyz/https://github.com`",
    `"https://gitclone.com/github.com`",
    `"https://gh-proxy.com/https://github.com`",
    `"https://ghps.cc/https://github.com`",
    `"https://gh.idayer.com/https://github.com`"
)
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/git/bin`"
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

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 Fooocus Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 Fooocus Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/fooocus_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/fooocus_installer.ps1`" | Select-String -Pattern `"FOOOCUS_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$FOOOCUS_INSTALLER_VERSION) {
                    Print-Msg `"检测到 Fooocus Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"========================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 Fooocus Installer 进行更新中`"
                        . `"`$Env:CACHE_HOME/fooocus_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
                        Print-Msg `"更新结束, 需重新启动 Fooocus Installer 管理脚本以应用更新, 回车退出 Fooocus Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Print-Msg `"跳过 Fooocus Installer 更新`"
                    }
                } else {
                    Print-Msg `"Fooocus Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 Fooocus Installer 更新中`"
                } else {
                    Print-Msg `"检查 Fooocus Installer 更新失败`"
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
        if (Test-Path `"`$PSScriptRoot/Fooocus/python/python.exe`") {
            `$Env:UV_PYTHON = `"`$PSScriptRoot/Fooocus/python/python.exe`"
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
    Get-Fooocus-Installer-Version
    Set-Proxy
    Check-Fooocus-Installer-Update
    Set-uv
    Set-Github-Mirror
    Pip-Mirror-Status

    if (!(Test-Path `"`$PSScriptRoot/Fooocus`")) {
        Print-Msg `"在 `$PSScriptRoot 路径中未找到 Fooocus 文件夹, 请检查 Fooocus 是否已正确安装, 或者尝试运行 Fooocus Installer 进行修复`"
        return
    }

    Print-Msg `"拉取 Fooocus 更新内容中`"
    Fix-Git-Point-Off-Set `"`$PSScriptRoot/Fooocus`"
    `$core_origin_ver = `$(git -C `"`$PSScriptRoot/Fooocus`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")
    `$branch = `$(git -C `"`$PSScriptRoot/Fooocus`" symbolic-ref --quiet HEAD 2> `$null).split(`"/`")[2]
    git -C `"`$PSScriptRoot/Fooocus`" fetch --recurse-submodules
    if (`$?) {
        Print-Msg `"应用 Fooocus 更新中`"
        `$commit_hash = `$(git -C `"`$PSScriptRoot/Fooocus`" log origin/`$branch --max-count 1 --format=`"%h`")
        git -C `"`$PSScriptRoot/Fooocus`" reset --hard `$commit_hash --recurse-submodules
        `$core_latest_ver = `$(git -C `"`$PSScriptRoot/Fooocus`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")

        if (`$core_origin_ver -eq `$core_latest_ver) {
            Print-Msg `"Fooocus 已为最新版, 当前版本：`$core_origin_ver`"
        } else {
            Print-Msg `"Fooocus 更新成功, 版本：`$core_origin_ver -> `$core_latest_ver`"
        }
    } else {
        Print-Msg `"拉取 Fooocus 更新内容失败`"
    }

    Print-Msg `"退出 Fooocus 更新脚本`"
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
# Fooocus Installer 版本和检查更新间隔
`$FOOOCUS_INSTALLER_VERSION = $FOOOCUS_INSTALLER_VERSION
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
    `"https://ghfast.top/https://github.com`",
    `"https://mirror.ghproxy.com/https://github.com`",
    `"https://ghproxy.net/https://github.com`",
    `"https://gh.api.99988866.xyz/https://github.com`",
    `"https://gitclone.com/github.com`",
    `"https://gh-proxy.com/https://github.com`",
    `"https://ghps.cc/https://github.com`",
    `"https://gh.idayer.com/https://github.com`"
)
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/git/bin`"
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


# Pip 镜像源状态
function Pip-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 Pip 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pip_mirror.txt 配置文件, 已将 Pip 源切换至官方源`"
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

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 Fooocus Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 Fooocus Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/fooocus_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/fooocus_installer.ps1`" | Select-String -Pattern `"FOOOCUS_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$FOOOCUS_INSTALLER_VERSION) {
                    Print-Msg `"检测到 Fooocus Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"========================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 Fooocus Installer 进行更新中`"
                        . `"`$Env:CACHE_HOME/fooocus_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
                        Print-Msg `"更新结束, 需重新启动 Fooocus Installer 管理脚本以应用更新, 回车退出 Fooocus Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Print-Msg `"跳过 Fooocus Installer 更新`"
                    }
                } else {
                    Print-Msg `"Fooocus Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 Fooocus Installer 更新中`"
                } else {
                    Print-Msg `"检查 Fooocus Installer 更新失败`"
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
        if (Test-Path `"`$PSScriptRoot/Fooocus/python/python.exe`") {
            `$Env:UV_PYTHON = `"`$PSScriptRoot/Fooocus/python/python.exe`"
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


# 获取 Fooocus 分支
function Get-Fooocus-Branch {
    `$remote = `$(git -C `"`$PSScriptRoot/Fooocus`" remote get-url origin)
    `$ref = `$(git -C `"`$PSScriptRoot/Fooocus`" symbolic-ref --quiet HEAD 2> `$null)
    if (`$ref -eq `$null) {
        `$ref = `$(git -C `"`$PSScriptRoot/Fooocus`" show -s --format=`"%h`")
    }

    return `"`$(`$remote.Split(`"/`")[-2])/`$(`$remote.Split(`"/`")[-1]) `$([System.IO.Path]::GetFileName(`$ref))`"
}


# 切换 Fooocus 分支
function Switch-Fooocus-Branch (`$remote, `$branch, `$use_submod) {
    `$fooocus_path = `"`$PSScriptRoot/Fooocus`"
    `$preview_url = `$(git -C `"`$fooocus_path`" remote get-url origin)

    Set-Github-Mirror # 设置 Github 镜像源

    if (`$use_submod) {
        `$use_submodules = `"--recurse-submodules`"
    } else {
        `$use_submodules = `"`"
    }

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
        git -C `"`$fooocus_path`" checkout `"`${branch}`" --force # 切换分支
        Print-Msg `"应用 Fooocus 远程源的更新`"
        if (`$use_submod) {
            Print-Msg `"更新 Fooocus 的 Git 子模块信息`"
            git -C `"`$fooocus_path`" reset --hard `"origin/`$branch`"
            git -C `"`$fooocus_path`" submodule deinit --all -f
            git -C `"`$fooocus_path`" submodule update --init --recursive
        }
        git -C `"`$fooocus_path`" reset `$use_submodules.ToString() --hard `"origin/`$branch`" # 切换到最新的提交内容上
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
    Set-Proxy
    Check-Fooocus-Installer-Update
    Set-uv
    Pip-Mirror-Status

    if (!(Test-Path `"`$PSScriptRoot/Fooocus`")) {
        Print-Msg `"在 `$PSScriptRoot 路径中未找到 Fooocus 文件夹, 请检查 Fooocus 是否已正确安装, 或者尝试运行 Fooocus Installer 进行修复`"
        return
    }

    `$content = `"
-----------------------------------------------------
- 1、lllyasviel - Fooocus 分支
- 2、runew0lf - RuinedFooocus 分支
- 3、MoonRide303 - Fooocus-MRE 分支
-----------------------------------------------------
`"

    `$to_exit = 0

    while (`$True) {
        Print-Msg `"Fooocus 分支列表`"
        `$go_to = 0
        Write-Host `$content
        Print-Msg `"当前 Fooocus 分支: `$(Get-Fooocus-Branch)`"
        Print-Msg `"请选择 Fooocus 分支`"
        Print-Msg `"提示: 输入数字后回车, 或者输入 exit 退出 Fooocus 分支切换脚本`"
        `$arg = Read-Host `"========================================>`"

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
    `$operate = Read-Host `"========================================>`"

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
function Write-Launch-Fooocus-Install-Script {
    $content = "
`$FOOOCUS_INSTALLER_VERSION = $FOOOCUS_INSTALLER_VERSION



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

    if (Test-Path `"`$PSScriptRoot/install_fooocus.txt`") {
        `$arg.Add(`"-InstallBranch`", `"fooocus`")
    } elseif (Test-Path `"`$PSScriptRoot/install_fooocus_mre.txt`") {
        `$arg.Add(`"-InstallBranch`", `"fooocus_mre`")
    } elseif (Test-Path `"`$PSScriptRoot/install_ruined_fooocus.txt`") {
        `$arg.Add(`"-InstallBranch`", `"ruined_fooocus`")
    }

    return `$arg
}


function Main {
    Print-Msg `"初始化中`"
    Get-Fooocus-Installer-Version
    Set-Proxy

    `$status = Download-Fooocus-Installer

    if (`$status) {
        Print-Msg `"运行 Fooocus Installer 中`"
        `$arg = Get-Local-Setting
        . `"`$PSScriptRoot/cache/fooocus_installer.ps1`" -InstallPath `"`$PSScriptRoot`" @arg
    } else {
        Read-Host | Out-Null
    }
}

###################

Main
"

    if (Test-Path "$InstallPath/launch_fooocus_installer.ps1") {
        Print-Msg "更新 launch_fooocus_installer.ps1 中"
    } else {
        Print-Msg "生成 launch_fooocus_installer.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$InstallPath/launch_fooocus_installer.ps1" -Value $content
}


# 重装 PyTorch 脚本
function Write-PyTorch-ReInstall-Script {
    $content = "
# Fooocus Installer 版本和检查更新间隔
`$FOOOCUS_INSTALLER_VERSION = $FOOOCUS_INSTALLER_VERSION
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
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/git/bin`"
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


# Pip 镜像源状态
function Pip-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 Pip 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pip_mirror.txt 配置文件, 已将 Pip 源切换至官方源`"
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

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 Fooocus Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 Fooocus Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/fooocus_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/fooocus_installer.ps1`" | Select-String -Pattern `"FOOOCUS_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$FOOOCUS_INSTALLER_VERSION) {
                    Print-Msg `"检测到 Fooocus Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"========================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 Fooocus Installer 进行更新中`"
                        . `"`$Env:CACHE_HOME/fooocus_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
                        Print-Msg `"更新结束, 需重新启动 Fooocus Installer 管理脚本以应用更新, 回车退出 Fooocus Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Print-Msg `"跳过 Fooocus Installer 更新`"
                    }
                } else {
                    Print-Msg `"Fooocus Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 Fooocus Installer 更新中`"
                } else {
                    Print-Msg `"检查 Fooocus Installer 更新失败`"
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
        if (Test-Path `"`$PSScriptRoot/Fooocus/python/python.exe`") {
            `$Env:UV_PYTHON = `"`$PSScriptRoot/Fooocus/python/python.exe`"
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
    Get-Fooocus-Installer-Version
    Set-Proxy
    Check-Fooocus-Installer-Update
    Set-uv
    Pip-Mirror-Status

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
- 31、Torch 2.6.0 (CUDA 12.4) + xFormers 0.0.29.post2
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
                `$Env:PIP_EXTRA_INDEX_URL = `" `"
                `$Env:UV_EXTRA_INDEX_URL = `"`"
                `$Env:PIP_FIND_LINKS = `"https://licyk.github.io/t/pypi/index_ms_mirror.html`"
                `$Env:UV_FIND_LINKS = `"https://licyk.github.io/t/pypi/index_ms_mirror.html`"
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
                `$Env:PIP_EXTRA_INDEX_URL = `" `"
                `$Env:UV_EXTRA_INDEX_URL = `"`"
                `$Env:PIP_FIND_LINKS = `"https://licyk.github.io/t/pypi/index_ms_mirror.html`"
                `$Env:UV_FIND_LINKS = `"https://licyk.github.io/t/pypi/index_ms_mirror.html`"
                `$go_to = 1
            }
            9 {
                `$torch_ver = `"torch==2.1.0a0+git7bcf7da torchvision==0.16.0+fbb4cc5 torchaudio==2.1.0+6ea1133 intel_extension_for_pytorch==2.1.20+git4849f3b`"
                `$xformers_ver = `"`"
                `$Env:PIP_EXTRA_INDEX_URL = `" `"
                `$Env:UV_EXTRA_INDEX_URL = `"`"
                `$Env:PIP_FIND_LINKS = `"https://licyk.github.io/t/pypi/index_ms_mirror.html`"
                `$Env:UV_FIND_LINKS = `"https://licyk.github.io/t/pypi/index_ms_mirror.html`"
                `$go_to = 1
            }
            10 {
                `$torch_ver = `"torch==2.1.1+cu118 torchvision==0.16.1+cu118 torchaudio==2.1.1+cu118`"
                `$xformers_ver = `"xformers==0.0.23+cu118`"
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
                `$go_to = 1
            }
            17 {
                `$torch_ver = `"torch==2.2.1 torchvision==0.17.1  torchaudio==2.2.1 torch-directml==0.2.1.dev240521`"
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
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
                `$go_to = 1
            }
            25 {
                `$torch_ver = `"torch==2.3.1+cu121 torchvision==0.18.1+cu121 torchaudio==2.3.1+cu121`"
                `$xformers_ver = `"xformers==0.0.27`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
                `$Env:PIP_FIND_LINKS = `" `"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            26 {
                `$torch_ver = `"torch==2.4.0+cu118 torchvision==0.19.0+cu118 torchaudio==2.4.0+cu118`"
                `$xformers_ver = `"xformers==0.0.27.post2+cu118`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
                `$go_to = 1
            }
            27 {
                `$torch_ver = `"torch==2.4.0+cu121 torchvision==0.19.0+cu121 torchaudio==2.4.0+cu121`"
                `$xformers_ver = `"xformers==0.0.27.post2`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
                `$Env:PIP_FIND_LINKS = `" `"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            28 {
                `$torch_ver = `"torch==2.4.1+cu124 torchvision==0.19.1+cu124 torchaudio==2.4.1+cu124`"
                `$xformers_ver = `"xformers===0.0.28.post1`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU124`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU124`"
                `$Env:PIP_FIND_LINKS = `" `"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            29 {
                `$torch_ver = `"torch==2.5.0+cu124 torchvision==0.20.0+cu124 torchaudio==2.5.0+cu124`"
                `$xformers_ver = `"xformers==0.0.28.post2`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU124`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU124`"
                `$Env:PIP_FIND_LINKS = `" `"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            30 {
                `$torch_ver = `"torch==2.5.1+cu124 torchvision==0.20.1+cu124 torchaudio==2.5.1+cu124`"
                `$xformers_ver = `"xformers==0.0.28.post3`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU124`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU124`"
                `$Env:PIP_FIND_LINKS = `" `"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            31 {
                `$torch_ver = `"torch==2.6.0+cu124 torchvision==0.21.0+cu124 torchaudio==2.6.0+cu124`"
                `$xformers_ver = `"xformers==0.0.29.post2`"
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
# Fooocus Installer 版本和检查更新间隔
`$FOOOCUS_INSTALLER_VERSION = $FOOOCUS_INSTALLER_VERSION
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
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/git/bin`"
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

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 Fooocus Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 Fooocus Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/fooocus_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/fooocus_installer.ps1`" | Select-String -Pattern `"FOOOCUS_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                if (`$latest_version -gt `$FOOOCUS_INSTALLER_VERSION) {
                    Print-Msg `"检测到 Fooocus Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"========================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 Fooocus Installer 进行更新中`"
                        . `"`$Env:CACHE_HOME/fooocus_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
                        Print-Msg `"更新结束, 需重新启动 Fooocus Installer 管理脚本以应用更新, 回车退出 Fooocus Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Print-Msg `"跳过 Fooocus Installer 更新`"
                    }
                } else {
                    Print-Msg `"Fooocus Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 Fooocus Installer 更新中`"
                } else {
                    Print-Msg `"检查 Fooocus Installer 更新失败`"
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
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLCanny_v10.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLLineart_v10.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLDepth_v10.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLSoftedge_v10.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLLineartRrealistic_v10.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLShuffle_v10.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLOpenPose_v10.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
    `$model_list.Add(@(`"https://modelscope.cn/models/licyks/sd_control_collection/resolve/master/illustriousXLTile_v10.safetensors`", `"SDXL ControlNet`", `"controlnet`")) | Out-Null
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
    return Read-Host `"========================================>`"
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
    Set-Proxy
    Check-Fooocus-Installer-Update
    Pip-Mirror-Status

    if (!(Test-Path `"`$PSScriptRoot/Fooocus`")) {
        Print-Msg `"在 `$PSScriptRoot 路径中未找到 Fooocus 文件夹, 请检查 Fooocus 是否已正确安装, 或者尝试运行 Fooocus Installer 进行修复`"
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
                        `$path = `"`$PSScriptRoot/Fooocus/models/`$(`$content[2])`" # 模型放置路径
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


# Fooocus Installer 设置脚本
function Write-Fooocus-Installer-Settings-Script {
    $content = "
# Fooocus Installer 版本和检查更新间隔
`$FOOOCUS_INSTALLER_VERSION = $FOOOCUS_INSTALLER_VERSION
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
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/git/bin`"
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


# 获取 Fooocus Installer 自动检测更新设置
function Get-Fooocus-Installer-Auto-Check-Update-Setting {
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
                Print-Msg `" https://gitclone.com/github.com`"
                Print-Msg `" https://gh-proxy.com/https://github.com`"
                Print-Msg `" https://ghps.cc/https://github.com`"
                Print-Msg `" https://gh.idayer.com/https://github.com`"
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
                Print-Msg `"提示: 保存启动参数后原有的启动参数将被覆盖, Fooocus 可用的启动参数可阅读: https://github.com/AUTOMATIC1111/Fooocus/wiki/Command-Line-Arguments-and-Settings`"
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
        Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/fooocus_installer.ps1`"
        if (`$?) {
            `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/fooocus_installer.ps1`" | Select-String -Pattern `"FOOOCUS_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
            if (`$latest_version -gt `$FOOOCUS_INSTALLER_VERSION) {
                Print-Msg `"Fooocus Installer 有新版本可用`"
                Print-Msg `"调用 Fooocus Installer 进行更新中`"
                . `"`$Env:CACHE_HOME/fooocus_installer.ps1`" -InstallPath `"`$PSScriptRoot`" -UseUpdateMode
                Print-Msg `"更新结束, 需重新启动 Fooocus Installer 管理脚本以应用更新, 回车退出 Fooocus Installer 管理脚本`"
                Read-Host | Out-Null
                exit 0
            } else {
                Print-Msg `"Fooocus Installer 已是最新版本`"
            }
            break
        } else {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 Fooocus Installer 更新中`"
            } else {
                Print-Msg `"检查 Fooocus Installer 更新失败`"
            }
        }
    }
}


# 检查环境完整性
function Check-Env {
    Print-Msg `"检查环境完整性中`"
    `$broken = 0
    if ((Test-Path `"`$PSScriptRoot/python/python.exe`") -or (Test-Path `"`$PSScriptRoot/Fooocus/python/python.exe`")) {
        `$python_status = `"已安装`"
    } else {
        `$python_status = `"未安装`"
        `$broken = 1
    }

    if ((Test-Path `"`$PSScriptRoot/git/bin/git.exe`") -or (Test-Path `"`$PSScriptRoot/Fooocus/git/bin/git.exe`")) {
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

    if ((Test-Path `"`$PSScriptRoot/git/bin/aria2c.exe`") -or (Test-Path `"`$PSScriptRoot/Fooocus/git/bin/aria2c.exe`")) {
        `$aria2_status = `"已安装`"
    } else {
        `$aria2_status = `"未安装`"
        `$broken = 1
    }

    if (Test-Path `"`$PSScriptRoot/Fooocus/launch.py`") {
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
        Print-Msg `"Fooocus Installer 自动检查更新: `$(Get-Fooocus-Installer-Auto-Check-Update-Setting)`"
        Print-Msg `"Fooocus 启动参数: `$(Get-Launch-Args-Setting)`"
        Print-Msg `"自动创建 Fooocus 快捷启动方式设置: `$(Get-Auto-Set-Launch-Shortcut-Setting)`"
        Print-Msg `"Pip 镜像源设置: `$(Get-Pip-Mirror-Setting)`"
        Print-Msg `"自动设置 CUDA 内存分配器设置: `$(Get-PyTorch-CUDA-Memory-Alloc-Setting)`"
        Print-Msg `"Fooocus 运行环境检测设置: `$(Get-Fooocus-Env-Check-Setting)`"
        Print-Msg `"-----------------------------------------------------`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 进入代理设置`"
        Print-Msg `"2. 进入 Python 包管理器设置`"
        Print-Msg `"3. 进入 HuggingFace 镜像源设置`"
        Print-Msg `"4. 进入 Github 镜像源设置`"
        Print-Msg `"5. 进入 Fooocus Installer 自动检查更新设置`"
        Print-Msg `"6. 进入 Fooocus 启动参数设置`"
        Print-Msg `"7. 进入自动创建 Fooocus 快捷启动方式设置`"
        Print-Msg `"8. 进入 Pip 镜像源设置`"
        Print-Msg `"9. 进入自动设置 CUDA 内存分配器设置`"
        Print-Msg `"10. 进入 Fooocus 运行环境检测设置`"
        Print-Msg `"11. 更新 Fooocus Installer 管理脚本`"
        Print-Msg `"12. 检查环境完整性`"
        Print-Msg `"13. 查看 Fooocus Installer 文档`"
        Print-Msg `"14. 退出 Fooocus Installer 设置`"
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
                Update-Fooocus-Launch-Args-Setting
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
                Fooocus-Env-Check-Setting
                break
            }
            11 {
                Check-Fooocus-Installer-Update
                break
            }
            12 {
                Check-Env
                break
            }
            13 {
                Get-Fooocus-Installer-Help-Docs
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
            Print-Msg `"退出 Fooocus Installer 设置`"
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
# Fooocus Installer 版本和检查更新间隔
`$Env:FOOOCUS_INSTALLER_VERSION = $FOOOCUS_INSTALLER_VERSION
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
    `"https://ghfast.top/https://github.com`",
    `"https://mirror.ghproxy.com/https://github.com`",
    `"https://ghproxy.net/https://github.com`",
    `"https://gh.api.99988866.xyz/https://github.com`",
    `"https://gitclone.com/github.com`",
    `"https://gh-proxy.com/https://github.com`",
    `"https://ghps.cc/https://github.com`",
    `"https://gh.idayer.com/https://github.com`"
)
# uv 最低版本
`$UV_MINIMUM_VER = `"$UV_MINIMUM_VER`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/Fooocus/git/bin`"
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
`$Env:FOOOCUS_INSTALLER_ROOT = `$PSScriptRoot



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
    `$url = `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/aria2c.exe`"
    Print-Msg `"下载 Aria2 中`"
    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null
    Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/aria2c.exe`"
    if (`$?) {
        Print-Msg `"更新 Aria2 中`"
        Move-Item -Path `"`$Env:CACHE_HOME/aria2c.exe`" -Destination `"`$Env:FOOOCUS_INSTALLER_ROOT/git/bin/aria2c.exe`" -Force
        Print-Msg `"更新 Aria2 完成`"
    } else {
        Print-Msg `"下载 Aria2 失败, 无法进行更新, 可尝试重新运行更新命令`"
    }
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
        Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/fooocus_installer.ps1`"
        if (`$?) {
            `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/fooocus_installer.ps1`" | Select-String -Pattern `"FOOOCUS_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
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
            break
        } else {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 Fooocus Installer 更新中`"
            } else {
                Print-Msg `"检查 Fooocus Installer 更新失败`"
            }
        }
    }
}


# 启用 Github 镜像源
function global:Test-Github-Mirror {
    `$Env:GIT_CONFIG_GLOBAL = `"`$Env:FOOOCUS_INSTALLER_ROOT/.gitconfig`" # 设置 Git 配置文件路径
    if (Test-Path `"`$Env:FOOOCUS_INSTALLER_ROOT/.gitconfig`") {
        Remove-Item -Path `"`$Env:FOOOCUS_INSTALLER_ROOT/.gitconfig`" -Force -Recurse
    }

    # 默认 Git 配置
    git config --global --add safe.directory `"*`"
    git config --global core.longpaths true

    if (Test-Path `"`$Env:FOOOCUS_INSTALLER_ROOT/disable_gh_mirror.txt`") { # 禁用 Github 镜像源
        Print-Msg `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件, 禁用 Github 镜像源`"
        return
    }

    if (Test-Path `"`$Env:FOOOCUS_INSTALLER_ROOT/gh_mirror.txt`") { # 使用自定义 Github 镜像源
        `$github_mirror = Get-Content `"`$Env:FOOOCUS_INSTALLER_ROOT/gh_mirror.txt`"
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


# 安装绘世启动器
function global:Install-Hanamizuki {
    `$urls = @(
        `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/hanamizuki.exe`",
        `"https://github.com/licyk/term-sd/releases/download/archive/hanamizuki.exe`",
        `"https://gitee.com/licyk/term-sd/releases/download/archive/hanamizuki.exe`"
    )

    if (Test-Path `"`$Env:FOOOCUS_INSTALLER_ROOT/Fooocus/hanamizuki.exe`") {
        Print-Msg `"绘世启动器已安装, 路径: `$([System.IO.Path]::GetFullPath(`"`$Env:FOOOCUS_INSTALLER_ROOT/Fooocus/hanamizuki.exe`"))`"
    } else {
        ForEach (`$url in `$urls) {
            Print-Msg `"下载绘世启动器中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/hanamizuki.exe`"
            if (`$?) {
                Move-Item -Path `"`$Env:CACHE_HOME/hanamizuki.exe`" `"`$Env:FOOOCUS_INSTALLER_ROOT/Fooocus/hanamizuki.exe`" -Force
                Print-Msg `"绘世启动器安装成功, 路径: `$([System.IO.Path]::GetFullPath(`"`$Env:FOOOCUS_INSTALLER_ROOT/Fooocus/hanamizuki.exe`"))`"
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
    if (!(Test-Path `"`$Env:FOOOCUS_INSTALLER_ROOT/Fooocus/python/python.exe`")) {
        if (Test-Path `"`$Env:FOOOCUS_INSTALLER_ROOT/python`") {
            Print-Msg `"尝试将 Python 移动至 `$Env:FOOOCUS_INSTALLER_ROOT\Fooocus 中`"
            Move-Item -Path `"`$Env:FOOOCUS_INSTALLER_ROOT/python`" `"`$Env:FOOOCUS_INSTALLER_ROOT/Fooocus`" -Force
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

    if (!(Test-Path `"`$Env:FOOOCUS_INSTALLER_ROOT/Fooocus/git/bin/git.exe`")) {
        if (Test-Path `"`$Env:FOOOCUS_INSTALLER_ROOT/git`") {
            Print-Msg `"尝试将 Git 移动至 `$Env:FOOOCUS_INSTALLER_ROOT\Fooocus 中`"
            Move-Item -Path `"`$Env:FOOOCUS_INSTALLER_ROOT/git`" `"`$Env:FOOOCUS_INSTALLER_ROOT/Fooocus`" -Force
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


# 设置 Python 命令别名
function global:pip {
    python -m pip @args
}

Set-Alias pip3 pip
Set-Alias pip3.10 pip
Set-Alias python3 python
Set-Alias python3.10 python


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
    Test-Github-Mirror
    Git-Clone
    Install-Hanamizuki
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
    Get-Fooocus-Installer-Version
    Set-Proxy
    Set-HuggingFace-Mirror
    Set-Github-Mirror
    Pip-Mirror-Status
    # 切换 uv 指定的 Python
    if (Test-Path `"`$Env:FOOOCUS_INSTALLER_ROOT/Fooocus/python/python.exe`") {
        `$Env:UV_PYTHON = `"`$Env:FOOOCUS_INSTALLER_ROOT/Fooocus/python/python.exe`"
    }
    Print-Msg `"激活 Fooocus Env`"
    Print-Msg `"更多帮助信息可在 Fooocus Installer 项目地址查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md`"
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
    Write-Host `"[Fooocus Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}

Print-Msg `"执行 Fooocus Installer 激活环境脚本`"
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
Fooocus Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
==================================

这是关于 Fooocus 的简单使用文档。

使用 Fooocus Installer 进行安装并安装成功后，将在当前目录生成 Fooocus 文件夹，以下为文件夹中不同文件 / 文件夹的作用。

cache：缓存文件夹，保存着 Pip / HuggingFace 等缓存文件。
python：Python 的存放路径。请注意，请勿将该 Python 文件夹添加到环境变量，这可能导致不良后果。
git：Git 的存放路径。
Fooocus：Fooocus 存放的文件夹。
activate.ps1：虚拟环境激活脚本，使用该脚本激活虚拟环境后即可使用 Python、Pip、Git 的命令。
launch_fooocus_installer.ps1：获取最新的 Fooocus Installer 安装脚本并运行。
update.ps1：更新 Fooocus 的脚本，可使用该脚本更新 Fooocus。
switch_branch.ps1：切换 Fooocus 分支。
launch.ps1：启动 Fooocus 的脚本。
reinstall_pytorch.ps1：重新安装 PyTorch 的脚本，在 PyTorch 出问题或者需要切换 PyTorch 版本时可使用。
download_model.ps1：下载模型的脚本，下载的模型将存放在 Fooocus 的模型文件夹中。关于模型的介绍可阅读：https://github.com/licyk/README-collection/blob/main/model-info/README.md。
settings.ps1：管理 Fooocus Installer 的设置。
terminal.ps1：启动 PowerShell 终端并自动激活虚拟环境，激活虚拟环境后即可使用 Python、Pip、Git 的命令。
help.txt：帮助文档。


要启动 Fooocus，可在 Fooocus 文件夹中找到 launch.ps1 脚本，右键这个脚本，选择使用 PowerShell 运行，等待 Fooocus 启动完成，启动完成后将自动打开浏览器进入 Fooocus 界面。

脚本为 Fooocus 设置了 HuggingFace 镜像源，解决国内无法直接访问 HuggingFace，导致 Fooocus 无法从 HuggingFace 下载模型的问题。
如果想自定义 HuggingFace 镜像源，可以在本地创建 hf_mirror.txt 文件，在文件中填写 HuggingFace 镜像源的地址后保存，再次启动脚本时将自动读取配置。
如果需要禁用 HuggingFace 镜像源，则创建 disable_hf_mirror.txt 文件，启动脚本时将不再设置 HuggingFace 镜像源。

以下为可用的 HuggingFace 镜像源地址：
https://hf-mirror.com
https://huggingface.sukaka.top

为了解决访问 Github 速度慢的问题，脚本默认启用 Github 镜像源，在运行 Fooocus Installer 或者 Fooocus 更新脚本时将自动测试可用的 Github 镜像源并设置。
如果想自定义 Github 镜像源，可以在本地创建 gh_mirror.txt 文件，在文本中填写 Github 镜像源的地址后保存，再次启动脚本时将自动读取配置。
如果需要禁用 Github 镜像源，则创建 disable_gh_mirror.txt 文件，启动脚本时将不再设置 Github 镜像源。

以下为可用的 Github 镜像源：
https://ghfast.top/https://github.com
https://mirror.ghproxy.com/https://github.com
https://ghproxy.net/https://github.com
https://gh.api.99988866.xyz/https://github.com
https://gitclone.com/github.com
https://gh-proxy.com/https://github.com
https://ghps.cc/https://github.com
https://gh.idayer.com/https://github.com

若要为脚本设置代理，则在代理软件中打开系统代理模式即可，或者在本地创建 proxy.txt 文件，在文件中填写代理地址后保存，再次启动脚本是将自动读取配置。
如果要禁用自动设置代理，可以在本地创建 disable_proxy.txt 文件，启动脚本时将不再自动设置代理。

脚本默认调用 uv 作为 Python 包管理器，相比于 Pip，安装 Python 软件包的速度更快。
如需禁用，可在脚本目录下创建 disable_uv.txt 文件，这将禁用 uv 并使用 Pip 作为 Python 包管理器。

设置 Fooocus 的启动参数，可以在和 launch.ps1 脚本同级的目录创建一个 launch_args.txt 文件，在文件内写上启动参数，运行 Fooocus 启动脚本时将自动读取该文件内的启动参数并应用。

Fooocus Installer 提供了配置管理器, 运行 settings.ps1 即可管理各个配置。

Fooocus Installer 的管理脚本在启动时会检查管理脚本的更新，如果有更新将会提示并显示具体的更新方法，如果要禁用更新，可以在脚本同级的目录创建 disable_update.txt 文件，这将禁用 Fooocus Installer 更新检查。

Fooocus 一些使用方法：
https://github.com/lllyasviel/Fooocus/discussions/117
https://github.com/lllyasviel/Fooocus/discussions/830

更多详细的帮助可在下面的链接查看。
Fooocus Installer 使用帮助：https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md
Fooocus 项目地址：https://github.com/AUTOMATIC1111/Fooocus
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
}


# 执行安装
function Use-Install-Mode {
    Set-Proxy
    Set-uv
    Pip-Mirror-Status
    Print-Msg "启动 Fooocus 安装程序"
    Print-Msg "提示: 若出现某个步骤执行失败, 可尝试再次运行 Fooocus Installer, 更多的说明请阅读 Fooocus Installer 使用文档"
    Print-Msg "Fooocus Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md"
    Print-Msg "即将进行安装的路径: $InstallPath"
    if ((Test-Path "$PSScriptRoot/install_fooocus.txt") -or ($InstallBranch -eq "fooocus")) {
        Print-Msg "检测到 install_fooocus.txt 配置文件 / 命令行参数 -InstallBranch fooocus, 选择安装 lllyasviel/Fooocus"
    } elseif ((Test-Path "$PSScriptRoot/install_fooocus_mre.txt") -or ($InstallBranch -eq "fooocus_mre")) {
        Print-Msg "检测到 install_fooocus_mre.txt 配置文件 / 命令行参数 -InstallBranch fooocus_mre, 选择安装 MoonRide303/Fooocus-MRE"
    } elseif ((Test-Path "$PSScriptRoot/install_ruined_fooocus.txt") -or ($InstallBranch -eq "ruined_fooocus")) {
        Print-Msg "检测到 install_ruined_fooocus.txt 配置文件 / 命令行参数 -InstallBranch ruined_fooocus, 选择安装 runew0lf/RuinedFooocus"
    } else {
        Print-Msg "未指定安装的 Fooocus 分支, 默认选择安装 lllyasviel/Fooocus"
    }
    Check-Install
    Print-Msg "添加管理脚本和文档中"
    Write-Manager-Scripts
    Print-Msg "Fooocus 安装结束, 安装路径为: $InstallPath"
    Print-Msg "帮助文档可在 Fooocus 文件夹中查看, 双击 help.txt 文件即可查看, 更多的说明请阅读 Fooocus Installer 使用文档"
    Print-Msg "Fooocus Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md"
    Print-Msg "退出 Fooocus Installer"
    Read-Host | Out-Null
}


# 执行管理脚本更新
function Use-Update-Mode {
    Print-Msg "更新管理脚本和文档中"
    Write-Manager-Scripts
    Print-Msg "更新管理脚本和文档完成"
}


# 帮助信息
function Get-Fooocus-Installer-Cmdlet-Help {
    $content = "
使用:
    .\fooocus_installer.ps1 -Help -InstallPath <安装 Fooocus 的绝对路径> -InstallBranch <安装的 Fooocus 分支> -UseUpdateMode -DisablePipMirror -DisableProxy -UseCustomProxy <代理服务器地址> -DisableUV -DisableGithubMirror -UseCustomGithubMirror <Github 镜像站地址>

参数:
    -Help
        获取 Fooocus Installer 的帮助信息

    -InstallPath <安装 Fooocus 的绝对路径>
        指定 Fooocus Installer 安装 Fooocus 的路径, 使用绝对路径表示
        例如: .\fooocus_installer.ps1 -InstallPath `"D:\Donwload`", 这将指定 Fooocus Installer 安装 Fooocus 到 D:\Donwload 这个路径

    -InstallBranch (fooocus, fooocus_mre, ruined_fooocus)
        指定 Fooocus Installer 安装的 Fooocus 分支
        支持指定安装的分支如下:
            fooocus:        lllyasviel/Fooocus
            fooocus_mre:    MoonRide303/Fooocus-MRE
            ruined_fooocus: runew0lf/RuinedFooocus

    -UseUpdateMode
        指定 Fooocus Installer 使用更新模式, 只对 Fooocus Installer 的管理脚本进行更新

    -DisablePipMirror
        禁用 Fooocus Installer 使用 Pip 镜像源, 使用 Pip 官方源下载 Python 软件包

    -DisableProxy
        禁用 Fooocus Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 --UseCustomProxy `"http://127.0.0.1:10809`" 设置代理服务器地址

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
            https://gitclone.com/github.com
            https://gh-proxy.com/https://github.com
            https://ghps.cc/https://github.com
            https://gh.idayer.com/https://github.com


更多的帮助信息请阅读 Fooocus Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/fooocus_installer.md
"
    Write-Host $content
    exit 0
}


# 主程序
function Main {
    Print-Msg "初始化中"
    Get-Fooocus-Installer-Version
    if ($Help) {
        Get-Fooocus-Installer-Cmdlet-Help
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