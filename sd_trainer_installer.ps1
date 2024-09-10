# 有关 PowerShell 脚本保存编码的问题: https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_character_encoding?view=powershell-7.4#the-byte-order-mark
# SD-Trainer Installer 版本和检查更新间隔
$SD_TRAINER_INSTALLER_VERSION = 101
$UPDATE_TIME_SPAN = 3600
# Pip 镜像源
$PIP_INDEX_MIRROR = "https://mirrors.cloud.tencent.com/pypi/simple"
# $PIP_EXTRA_INDEX_MIRROR = "https://mirror.baidu.com/pypi/simple"
$PIP_EXTRA_INDEX_MIRROR = "https://mirrors.cernet.edu.cn/pypi/web/simple"
$PIP_FIND_MIRROR = "https://mirror.sjtu.edu.cn/pytorch-wheels/torch_stable.html"
# $PIP_FIND_MIRROR_CU121 = "https://download.pytorch.org/whl/cu121/torch_stable.html"
$PIP_EXTRA_INDEX_MIRROR_PYTORCH = "https://download.pytorch.org/whl"
$PIP_EXTRA_INDEX_MIRROR_CU121 = "https://download.pytorch.org/whl/cu121"
$PIP_EXTRA_INDEX_MIRROR_CU124 = "https://download.pytorch.org/whl/cu124"
# Github 镜像源列表
$GITHUB_MIRROR_LIST = @(
    "https://mirror.ghproxy.com/https://github.com",
    "https://ghproxy.net/https://github.com",
    "https://gitclone.com/github.com",
    "https://gh-proxy.com/https://github.com",
    "https://ghps.cc/https://github.com",
    "https://gh.idayer.com/https://github.com"
)
# PyTorch 版本
$PYTORCH_VER = "torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118"
$XFORMERS_VER = "xformers==0.0.26.post1+cu118"
# SD-Trainer 仓库地址
$SD_TRAINER_REPO = "https://github.com/Akegarasu/lora-scripts"
# PATH
$PYTHON_PATH = "$PSScriptRoot/SD-Trainer/python"
$PYTHON_SCRIPTS_PATH = "$PSScriptRoot/SD-Trainer/python/Scripts"
$GIT_PATH = "$PSScriptRoot/SD-Trainer/git/bin"
$Env:PATH = "$PYTHON_PATH$([System.IO.Path]::PathSeparator)$PYTHON_SCRIPTS_PATH$([System.IO.Path]::PathSeparator)$GIT_PATH$([System.IO.Path]::PathSeparator)$Env:PATH"
# 环境变量
$Env:PIP_INDEX_URL = $PIP_INDEX_MIRROR
$Env:PIP_EXTRA_INDEX_URL = $PIP_EXTRA_INDEX_MIRROR
$Env:PIP_FIND_LINKS = $PIP_FIND_MIRROR
$Env:UV_INDEX_URL = $PIP_INDEX_MIRROR
# $Env:UV_EXTRA_INDEX_URL = $PIP_EXTRA_INDEX_MIRROR
# $Env:UV_FIND_LINKS = $PIP_FIND_MIRROR
$Env:UV_LINK_MODE = "copy"
$Env:UV_HTTP_TIMEOUT = 30
$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
$Env:PIP_TIMEOUT = 30
$Env:PIP_RETRIES = 5
$Env:PYTHONUTF8 = 1
$Env:PYTHONIOENCODING = "utf8"
$Env:CACHE_HOME = "$PSScriptRoot/SD-Trainer/cache"
$Env:HF_HOME = "$PSScriptRoot/SD-Trainer/cache/huggingface"
$Env:MATPLOTLIBRC = "$PSScriptRoot/SD-Trainer/cache"
$Env:MODELSCOPE_CACHE = "$PSScriptRoot/SD-Trainer/cache/modelscope/hub"
$Env:MS_CACHE_HOME = "$PSScriptRoot/SD-Trainer/cache/modelscope/hub"
$Env:SYCL_CACHE_DIR = "$PSScriptRoot/SD-Trainer/cache/libsycl_cache"
$Env:TORCH_HOME = "$PSScriptRoot/SD-Trainer/cache/torch"
$Env:U2NET_HOME = "$PSScriptRoot/SD-Trainer/cache/u2net"
$Env:XDG_CACHE_HOME = "$PSScriptRoot/SD-Trainer/cache"
$Env:PIP_CACHE_DIR = "$PSScriptRoot/SD-Trainer/cache/pip"
$Env:PYTHONPYCACHEPREFIX = "$PSScriptRoot/SD-Trainer/cache/pycache"
$Env:UV_CACHE_DIR = "$PSScriptRoot/SD-Trainer/cache/uv"
$Env:UV_PYTHON = "$PSScriptRoot/SD-Trainer/python/python.exe"


# 消息输出
function Print-Msg ($msg) {
    Write-Host "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")][SD-Trainer Installer]:: $msg"
}

Print-Msg "初始化中"

# 代理配置
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

# 设置 uv 的使用状态
if (Test-Path "$PSScriptRoot/disable_uv.txt") {
    Print-Msg "检测到 disable_uv.txt 配置文件, 已禁用 uv, 使用 Pip 作为 Python 包管理器"
    $USE_UV = $false
} else {
    Print-Msg "默认启用 uv 作为 Python 包管理器, 加快 Python 软件包的安装速度"
    $USE_UV = $true
}

# 下载并解压 Python
function Install-Python {
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/python-3.10.11-amd64.zip"

    # 下载 Python
    Print-Msg "正在下载 Python"
    Invoke-WebRequest -Uri $url -OutFile "$PSScriptRoot/SD-Trainer/cache/python-3.10.11-amd64.zip"
    if ($?) { # 检测是否下载成功并解压
        # 创建 Python 文件夹
        if (!(Test-Path "$PSScriptRoot/SD-Trainer/python")) {
            New-Item -ItemType Directory -Force -Path $PSScriptRoot/SD-Trainer/python > $null
        }
        # 解压 Python
        Print-Msg "正在解压 Python"
        Expand-Archive -Path "$PSScriptRoot/SD-Trainer/cache/python-3.10.11-amd64.zip" -DestinationPath "$PSScriptRoot/SD-Trainer/python" -Force
        Remove-Item -Path "$PSScriptRoot/SD-Trainer/cache/python-3.10.11-amd64.zip"
        Print-Msg "Python 安装成功"
    } else {
        Print-Msg "Python 安装失败, 终止 SD-Trainer 安装进程, 可尝试重新运行 SD-Trainer Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 下载并解压 Git
function Install-Git {
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/PortableGit.zip"
    Print-Msg "正在下载 Git"
    Invoke-WebRequest -Uri $url -OutFile "$PSScriptRoot/SD-Trainer/cache/PortableGit.zip"
    if ($?) { # 检测是否下载成功并解压
        # 创建 Git 文件夹
        if (!(Test-Path "$PSScriptRoot/SD-Trainer/git")) {
            New-Item -ItemType Directory -Force -Path $PSScriptRoot/SD-Trainer/git > $null
        }
        # 解压 Git
        Print-Msg "正在解压 Git"
        Expand-Archive -Path "$PSScriptRoot/SD-Trainer/cache/PortableGit.zip" -DestinationPath "$PSScriptRoot/SD-Trainer/git" -Force
        Remove-Item -Path "$PSScriptRoot/SD-Trainer/cache/PortableGit.zip"
        Print-Msg "Git 安装成功"
    } else {
        Print-Msg "Git 安装失败, 终止 SD-Trainer 安装进程, 可尝试重新运行 SD-Trainer Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 下载 Aria2
function Install-Aria2 {
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/aria2c.exe"
    Print-Msg "正在下载 Aria2"
    Invoke-WebRequest -Uri $url -OutFile "$PSScriptRoot/SD-Trainer/cache/aria2c.exe"
    if ($?) {
        Move-Item -Path "$PSScriptRoot/SD-Trainer/cache/aria2c.exe" -Destination "$PSScriptRoot/SD-Trainer/git/bin/aria2c.exe" -Force
        Print-Msg "Aria2 下载成功"
    } else {
        Print-Msg "Aria2 下载失败, 终止 SD-Trainer 安装进程, 可尝试重新运行 SD-Trainer Installer 重试失败的安装"
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
        Print-Msg "uv 下载失败, 终止 SD-Trainer 安装进程, 可尝试重新运行 SD-Trainer Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}

# Github 镜像测试
function Test-Github-Mirror {
    if (Test-Path "$PSScriptRoot/disable_gh_mirror.txt") { # 禁用 Github 镜像源
        Print-Msg "检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件, 禁用 Github 镜像源"
    } else {
        $Env:GIT_CONFIG_GLOBAL = "$PSScriptRoot/SD-Trainer/.gitconfig" # 设置 Git 配置文件路径
        if (Test-Path "$PSScriptRoot/SD-Trainer/.gitconfig") {
            Remove-Item -Path "$PSScriptRoot/SD-Trainer/.gitconfig" -Force
        }

        if (Test-Path "$PSScriptRoot/gh_mirror.txt") { # 使用自定义 Github 镜像源
            $github_mirror = Get-Content "$PSScriptRoot/gh_mirror.txt"
            git config --global url."$github_mirror".insteadOf "https://github.com"
            Print-Msg "检测到本地存在 gh_mirror.txt Github 镜像源配置文件, 已读取 Github 镜像源配置文件并设置 Github 镜像源"
        } else { # 自动检测可用镜像源并使用
            $status = 0
            ForEach($i in $GITHUB_MIRROR_LIST) {
                Print-Msg "测试 Github 镜像源: $i"
                if (Test-Path "$PSScriptRoot/SD-Trainer/cache/github-mirror-test") {
                    Remove-Item -Path "$PSScriptRoot/SD-Trainer/cache/github-mirror-test" -Force -Recurse
                }
                git clone $i/licyk/empty $PSScriptRoot/SD-Trainer/cache/github-mirror-test --quiet
                if ($?) {
                    Print-Msg "该 Github 镜像源可用"
                    $github_mirror = $i
                    $status = 1
                    break
                } else {
                    Print-Msg "镜像源不可用, 更换镜像源进行测试"
                }
            }
            if (Test-Path "$PSScriptRoot/SD-Trainer/cache/github-mirror-test") {
                Remove-Item -Path "$PSScriptRoot/SD-Trainer/cache/github-mirror-test" -Force -Recurse
            }
            if ($status -eq 0) {
                Print-Msg "无可用 Github 镜像源, 取消使用 Github 镜像源"
                Remove-Item -Path env:GIT_CONFIG_GLOBAL -Force
            } else {
                Print-Msg "设置 Github 镜像源"
                git config --global url."$github_mirror".insteadOf "https://github.com"
            }
        }
    }
}


# 安装 SD-Trainer
function Install-SD-Trainer {
    $status = 0
    if (!(Test-Path "$PSScriptRoot/SD-Trainer/lora-scripts")) {
        $status = 1
    } else {
        $items = Get-ChildItem "$PSScriptRoot/SD-Trainer/lora-scripts" -Recurse
        if ($items.Count -eq 0) {
            $status = 1
        }
    }

    if ($status -eq 1) {
        Print-Msg "正在下载 SD-Trainer"
        git clone --recurse-submodules $SD_TRAINER_REPO "$PSScriptRoot/SD-Trainer/lora-scripts"
        if ($?) { # 检测是否下载成功
            Print-Msg "SD-Trainer 安装成功"
        } else {
            Print-Msg "SD-Trainer 安装失败, 终止 SD-Trainer 安装进程, 可尝试重新运行 SD-Trainer Installer 重试失败的安装"
            Read-Host | Out-Null
            exit 1
        }
    } else {
        Print-Msg "SD-Trainer 已安装"
    }

    Print-Msg "安装 SD-Trainer 子模块中"
    git -C "$PSScriptRoot/SD-Trainer/lora-scripts" submodule init
    git -C "$PSScriptRoot/SD-Trainer/lora-scripts" submodule update
    if ($?) {
        Print-Msg "SD-Trainer 子模块安装成功"
    } else {
        Print-Msg "SD-Trainer 子模块安装失败, 终止 SD-Trainer 安装进程, 可尝试重新运行 SD-Trainer Installer 重试失败的安装"
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
            uv pip install $PYTORCH_VER.ToString().Split() --find-links $PIP_FIND_MIRROR
        } else {
            python -m pip install $PYTORCH_VER.ToString().Split() --no-warn-script-location
        }
        if ($?) {
            Print-Msg "PyTorch 安装成功"
        } else {
            Print-Msg "PyTorch 安装失败, 终止 SD-Trainer 安装进程, 可尝试重新运行 SD-Trainer Installer 重试失败的安装"
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
            uv pip install $XFORMERS_VER --no-deps --find-links $PIP_FIND_MIRROR
        } else {
            python -m pip install $XFORMERS_VER --no-deps --no-warn-script-location
        }
        if ($?) {
            Print-Msg "xFormers 安装成功"
        } else {
            Print-Msg "xFormers 安装失败, 终止 SD-Trainer 安装进程, 可尝试重新运行 SD-Trainer Installer 重试失败的安装"
            Read-Host | Out-Null
            exit 1
        }
    } else {
        Print-Msg "xFormers 已安装, 无需再次安装"
    }
}


# 安装 SD-Trainer 依赖
function Install-SD-Trainer-Dependence {
    # 记录脚本所在路径
    $current_path = $(Get-Location).ToString()
    Set-Location "$PSScriptRoot/SD-Trainer/lora-scripts/scripts"
    Print-Msg "安装 SD-Trainer 内核依赖中"
    if ($USE_UV) {
        uv pip install -r requirements.txt --find-links $PIP_FIND_MIRROR
    } else {
        python -m pip install -r requirements.txt --no-warn-script-location
    }
    if ($?) {
        Print-Msg "SD-Trainer 内核依赖安装成功"
    } else {
        Print-Msg "SD-Trainer 内核依赖安装失败, 终止 SD-Trainer 安装进程, 可尝试重新运行 SD-Trainer Installer 重试失败的安装"
        Set-Location "$current_path"
        Read-Host | Out-Null
        exit 1
    }

    Set-Location "$PSScriptRoot/SD-Trainer/lora-scripts"
    Print-Msg "安装 SD-Trainer 依赖中"
    if ($USE_UV) {
        uv pip install -r requirements.txt --find-links $PIP_FIND_MIRROR
    } else {
        python -m pip install -r requirements.txt --no-warn-script-location
    }
    if ($?) {
        Print-Msg "SD-Trainer 依赖安装成功"
    } else {
        Print-Msg "SD-Trainer 依赖安装失败, 终止 SD-Trainer 安装进程, 可尝试重新运行 SD-Trainer Installer 重试失败的安装"
        Set-Location "$current_path"
        Read-Host | Out-Null
        exit 1
    }
    Set-Location "$current_path"
}


# 安装
function Check-Install {
    New-Item -ItemType Directory -Path "$PSScriptRoot/SD-Trainer" -Force > $null
    New-Item -ItemType Directory -Path "$PSScriptRoot/SD-Trainer/cache" -Force > $null
    New-Item -ItemType Directory -Path "$PSScriptRoot/SD-Trainer/models" -Force > $null

    Print-Msg "检测是否安装 Python"
    if (Test-Path "$PSScriptRoot/SD-Trainer/python/python.exe") {
        Print-Msg "Python 已安装"
    } else {
        Print-Msg "Python 未安装"
        Install-Python
    }

    Print-Msg "检测是否安装 Git"
    if (Test-Path "$PSScriptRoot/SD-Trainer/git/bin/git.exe") {
        Print-Msg "Git 已安装"
    } else {
        Print-Msg "Git 未安装"
        Install-Git
    }

    Print-Msg "检测是否安装 Aria2"
    if (Test-Path "$PSScriptRoot/SD-Trainer/git/bin/aria2c.exe") {
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

    Test-Github-Mirror
    Install-SD-Trainer
    Install-PyTorch
    Install-SD-Trainer-Dependence

    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
}


# 启动脚本
function Write-Launch-Script {
    $content = "
# SD-Trainer Installer 版本和检查更新间隔
`$SD_TRAINER_INSTALLER_VERSION = $SD_TRAINER_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# Pip 镜像源
`$PIP_INDEX_MIRROR = `"$PIP_INDEX_MIRROR`"
`$PIP_EXTRA_INDEX_MIRROR = `"$PIP_EXTRA_INDEX_MIRROR`"
`$PIP_FIND_MIRROR = `"$PIP_FIND_MIRROR`"
# `$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
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
# `$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
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
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
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

# SD-Trainer Installer 更新检测
function Check-SD-Trainer-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 SD-Trainer Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 SD-Trainer Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" | Select-String -Pattern `"SD_TRAINER_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`"
                if (`$latest_version -gt `$SD_TRAINER_INSTALLER_VERSION) {
                    New-Item -ItemType File -Path `"`$PSScriptRoot/new_version.txt`" -Force > `$null
                    Print-Msg `"SD-Trainer Installer 有新版本可用`"
                    Print-Msg `"更新方法可阅读: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md#%E6%9B%B4%E6%96%B0-sd-trainer-%E7%AE%A1%E7%90%86%E8%84%9A%E6%9C%AC`"
                    Start-Sleep -Seconds 1
                } else {
                    Print-Msg `"SD-Trainer Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 SD-Trainer Installer 更新中`"
                } else {
                    Print-Msg `"检查 SD-Trainer Installer 更新失败`"
                }
            }
        }
    } elseif (Test-Path `"`$PSScriptRoot/new_version.txt`") {
        Print-Msg `"SD-Trainer Installer 有新版本可用`"
        Print-Msg `"更新方法可阅读: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md#%E6%9B%B4%E6%96%B0-sd-trainer-%E7%AE%A1%E7%90%86%E8%84%9A%E6%9C%AC`"
        Start-Sleep -Seconds 1
    }
}


Print-Msg `"初始化中`"

# 代理配置
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

# HuggingFace 镜像源
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

# SD-Trainer 启动参数
if (Test-Path `"`$PSScriptRoot/launch_args.txt`") {
    `$args = Get-Content `"`$PSScriptRoot/launch_args.txt`"
    Print-Msg `"检测到本地存在 launch_args.txt 启动参数配置文件, 已读取该启动参数配置文件并应用启动参数`"
    Print-Msg `"使用的启动参数: `$args`"
} else {
    `$args = `"`"
}

# 记录上次的路径
`$current_path = Get-Location
`$current_path = `$current_path.ToString()

Fix-PyTorch
Check-SD-Trainer-Installer-Update
Print-Msg `"启动 SD-Trainer 中`"
Set-Location `"`$PSScriptRoot/lora-scripts`"
python gui.py `$args.ToString().Split()
`$req = `$?
if (`$req) {
    Print-Msg `"SD-Trainer 正常退出`"
} else {
    Print-Msg `"SD-Trainer 出现异常, 已退出`"
}
Set-Location `"`$current_path`"
Read-Host | Out-Null
"

    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/launch.ps1" -Value $content
}


# 更新脚本
function Write-Update-Script {
    $content = "
# SD-Trainer Installer 版本和检查更新间隔
`$SD_TRAINER_INSTALLER_VERSION = $SD_TRAINER_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# Pip 镜像源
`$PIP_INDEX_MIRROR = `"$PIP_INDEX_MIRROR`"
`$PIP_EXTRA_INDEX_MIRROR = `"$PIP_EXTRA_INDEX_MIRROR`"
`$PIP_FIND_MIRROR = `"$PIP_FIND_MIRROR`"
# `$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
# Github 镜像源
`$GITHUB_MIRROR_LIST = @(
    `"https://mirror.ghproxy.com/https://github.com`",
    `"https://ghproxy.net/https://github.com`",
    `"https://gitclone.com/github.com`",
    `"https://gh-proxy.com/https://github.com`",
    `"https://ghps.cc/https://github.com`",
    `"https://gh.idayer.com/https://github.com`"
)
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
# `$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
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
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
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

# SD-Trainer Installer 更新检测
function Check-SD-Trainer-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 SD-Trainer Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 SD-Trainer Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" | Select-String -Pattern `"SD_TRAINER_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`"
                if (`$latest_version -gt `$SD_TRAINER_INSTALLER_VERSION) {
                    New-Item -ItemType File -Path `"`$PSScriptRoot/new_version.txt`" -Force > `$null
                    Print-Msg `"SD-Trainer Installer 有新版本可用`"
                    Print-Msg `"更新方法可阅读: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md#%E6%9B%B4%E6%96%B0-sd-trainer-%E7%AE%A1%E7%90%86%E8%84%9A%E6%9C%AC`"
                    Start-Sleep -Seconds 1
                } else {
                    Print-Msg `"SD-Trainer Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 SD-Trainer Installer 更新中`"
                } else {
                    Print-Msg `"检查 SD-Trainer Installer 更新失败`"
                }
            }
        }
    } elseif (Test-Path `"`$PSScriptRoot/new_version.txt`") {
        Print-Msg `"SD-Trainer Installer 有新版本可用`"
        Print-Msg `"更新方法可阅读: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md#%E6%9B%B4%E6%96%B0-sd-trainer-%E7%AE%A1%E7%90%86%E8%84%9A%E6%9C%AC`"
        Start-Sleep -Seconds 1
    }
}


# 设置 uv 的使用状态
if (Test-Path `"`$PSScriptRoot/disable_uv.txt`") {
    Print-Msg `"检测到 disable_uv.txt 配置文件, 已禁用 uv, 使用 Pip 作为 Python 包管理器`"
    `$USE_UV = `$false
} else {
    Print-Msg `"默认启用 uv 作为 Python 包管理器, 加快 Python 软件包的安装速度`"
    `$USE_UV = `$true
}

# 代理配置
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

# Github 镜像源
if (Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") { # 禁用 Github 镜像源
    Print-Msg `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件, 禁用 Github 镜像源`"
} else {
    `$Env:GIT_CONFIG_GLOBAL = `"`$PSScriptRoot/.gitconfig`" # 设置 Git 配置文件路径
    if (Test-Path `"`$PSScriptRoot/.gitconfig`") {
        Remove-Item -Path `"`$PSScriptRoot/.gitconfig`" -Force
    }

    if (Test-Path `"`$PSScriptRoot/gh_mirror.txt`") { # 使用自定义 Github 镜像源
        `$github_mirror = Get-Content `"`$PSScriptRoot/gh_mirror.txt`"
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
            git config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
        }
    }
}



# 记录上次的路径
`$current_path = Get-Location
`$current_path = `$current_path.ToString()

Check-SD-Trainer-Installer-Update

`$update_fail = 0
Print-Msg `"拉取 SD-Trainer 更新内容中`"
Fix-Git-Point-Off-Set `"`$PSScriptRoot/lora-scripts`"
`$core_origin_ver = `$(git -C `"`$PSScriptRoot/lora-scripts`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")
`$branch = `$(git -C `"`$PSScriptRoot/lora-scripts`" symbolic-ref --quiet HEAD 2> `$null).split(`"/`")[2]
git -C `"`$PSScriptRoot/lora-scripts`" fetch --recurse-submodules
if (`$?) {
    Print-Msg `"应用 SD-Trainer 更新中`"
    `$commit_hash = `$(git -C `"`$PSScriptRoot/lora-scripts`" log origin/`$branch --max-count 1 --format=`"%h`")
    git -C `"`$PSScriptRoot/lora-scripts`" reset --hard `$commit_hash --recurse-submodules
    `$core_latest_ver = `$(git -C `"`$PSScriptRoot/lora-scripts`" show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")
    
    if (`$core_origin_ver -eq `$core_latest_ver) {
        Print-Msg `"SD-Trainer 已为最新版`"
        `$core_update_msg = `"已为最新版, 当前版本：`$core_origin_ver`"
    } else {
        Print-Msg `"SD-Trainer 更新成功`"
        `$core_update_msg = `"更新成功, 版本：`$core_origin_ver -> `$core_latest_ver`"
    }

    Print-Msg `"更新 SD-Trainer 内核依赖中`"
    `$pytorch_ver = Get-PyTorch-Version
    Set-Pip-Extra-Index-URL-For-CUDA
    Set-Location `"`$PSScriptRoot/lora-scripts/scripts`"
    if (`$USE_UV) {
        uv pip install -r requirements.txt `$pytorch_ver.ToString().Split() --upgrade --find-links `"`$PIP_FIND_MIRROR`"
    } else {
        python -m pip install -r requirements.txt `$pytorch_ver.ToString().Split() --upgrade --no-warn-script-location
    }
    if (`$?) {
        Print-Msg `"SD-Trainer 内核依赖更新成功`"
        `$core_req_update_msg = `"更新成功`"
    } else {
        Print-Msg `"SD-Trainer 内核依赖更新失败`"
        `$core_req_update_msg = `"更新失败`"
        `$update_fail = 1
    }

    Print-Msg `"更新 SD-Trainer 依赖中`"
    Set-Location `"`$PSScriptRoot/lora-scripts`"
    if (`$USE_UV) {
        uv pip install -r requirements.txt `$pytorch_ver.ToString().Split() --upgrade --find-links `"`$PIP_FIND_MIRROR`"
    } else {
        python -m pip install -r requirements.txt `$pytorch_ver.ToString().Split() --upgrade --no-warn-script-location
    }
    if (`$?) {
        Print-Msg `"SD-Trainer 依赖更新成功`"
        `$req_update_msg = `"更新成功`"
    } else {
        Print-Msg `"SD-Trainer 依赖更新失败`"
        `$req_update_msg = `"更新失败`"
        `$update_fail = 1
    }

    Set-Location `"`$current_path`"
} else {
    Print-Msg `"拉取 SD-Trainer 更新内容失败`"
    `$core_update_msg = `"拉取 SD-Trainer 更新内容失败, 无法进行更新`"
    `$core_req_update_msg = `"因 SD-Trainer 组件新失败, 不进行更新`"
    `$req_update_msg = `"因 SD-Trainer 组件更新失败, 不进行更新`"
    `$update_fail = 1
}

Print-Msg `"SD-Trainer 更新结果：`"
Print-Msg `"SD-Trainer 组件: `$core_update_msg`"
Print-Msg `"SD-Trainer 内核依赖: `$core_req_update_msg`"
Print-Msg `"SD-Trainer 依赖: `$req_update_msg`"
if (`$update_fail -eq 0) {
    Print-Msg `"SD-Trainer 更新成功`"
} else {
    Print-Msg `"SD-Trainer 更新失败, 请检查控制台日志。可尝试重新运行 SD-Trainer 更新脚本进行重试`"
}

Print-Msg `"退出 SD-Trainer 更新脚本`"
Read-Host | Out-Null
"

    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/update.ps1" -Value $content
}


# 获取安装脚本
function Write-SD-Trainer-Install-Script {
    $content = "
# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
}


# 代理配置
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

# 可用的下载源
`$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1`")
`$i = 0

New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

ForEach (`$url in `$urls) {
    Print-Msg `"正在下载最新的 SD-Trainer Installer 脚本`"
    Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`"
    if (`$?) {
        Move-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" -Destination `"`$PSScriptRoot/../sd_trainer_installer.ps1`" -Force
        `$parentDirectory = Split-Path `$PSScriptRoot -Parent
        Print-Msg `"下载 SD-Trainer Installer 脚本成功, 脚本路径为 `$parentDirectory\sd_trainer_installer.ps1`"
        break
    } else {
        Print-Msg `"下载 SD-Trainer Installer 脚本失败`"
        `$i += 1
        if (`$i -lt `$urls.Length) {
            Print-Msg `"重试下载 SD-Trainer Installer 脚本`"
        } else {
            Print-Msg `"更新 SD-Trainer Installer 脚本失败, 可尝试重新运行 SD-Trainer Installer 下载脚本`"
        }
    }
}

Print-Msg `"退出 SD-Trainer Installer 下载脚本`"
Read-Host | Out-Null
"

    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/get_sd_trainer_installer.ps1" -Value $content
}


# 重装 PyTorch 脚本
function Write-PyTorch-ReInstall-Script {
    $content = "
# SD-Trainer Installer 版本和检查更新间隔
`$SD_TRAINER_INSTALLER_VERSION = $SD_TRAINER_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# Pip 镜像源
`$PIP_INDEX_MIRROR = `"$PIP_INDEX_MIRROR`"
`$PIP_EXTRA_INDEX_MIRROR = `"$PIP_EXTRA_INDEX_MIRROR`"
`$PIP_FIND_MIRROR = `"$PIP_FIND_MIRROR`"
# `$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
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
# `$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
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
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
}

# SD-Trainer Installer 更新检测
function Check-SD-Trainer-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 SD-Trainer Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 SD-Trainer Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" | Select-String -Pattern `"SD_TRAINER_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`"
                if (`$latest_version -gt `$SD_TRAINER_INSTALLER_VERSION) {
                    New-Item -ItemType File -Path `"`$PSScriptRoot/new_version.txt`" -Force > `$null
                    Print-Msg `"SD-Trainer Installer 有新版本可用`"
                    Print-Msg `"更新方法可阅读: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md#%E6%9B%B4%E6%96%B0-sd-trainer-%E7%AE%A1%E7%90%86%E8%84%9A%E6%9C%AC`"
                    Start-Sleep -Seconds 1
                } else {
                    Print-Msg `"SD-Trainer Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 SD-Trainer Installer 更新中`"
                } else {
                    Print-Msg `"检查 SD-Trainer Installer 更新失败`"
                }
            }
        }
    } elseif (Test-Path `"`$PSScriptRoot/new_version.txt`") {
        Print-Msg `"SD-Trainer Installer 有新版本可用`"
        Print-Msg `"更新方法可阅读: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md#%E6%9B%B4%E6%96%B0-sd-trainer-%E7%AE%A1%E7%90%86%E8%84%9A%E6%9C%AC`"
        Start-Sleep -Seconds 1
    }
}


# 设置 uv 的使用状态
if (Test-Path `"`$PSScriptRoot/disable_uv.txt`") {
    Print-Msg `"检测到 disable_uv.txt 配置文件, 已禁用 uv, 使用 Pip 作为 Python 包管理器`"
    `$USE_UV = `$false
} else {
    Print-Msg `"默认启用 uv 作为 Python 包管理器, 加快 Python 软件包的安装速度`"
    `$USE_UV = `$true
}

# 代理配置
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

Check-SD-Trainer-Installer-Update

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
- 21、Torch 2.4.0 (CUDA 12.4)
-----------------------------------------------------
`"

`$to_exit = 0
`$pip_find_links_arg = `"--find-links `$PIP_FIND_MIRROR`"

while (`$True) {
    Print-Msg `"PyTorch 版本列表`"
    `$go_to = 0
    Write-Host `$content
    Print-Msg `"请选择 PyTorch 版本`"
    Print-Msg `"提示:`"
    Print-Msg `"1. PyTroch 版本通常来说选择最新版的即可`"
    Print-Msg `"2. 输入数字后回车, 或者输入 exit 退出 PyTroch 重装脚本`"
    `$arg = Read-Host `"===========================================>`"

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
            `$xformers_ver = `"xformers==0.0.23`"
            `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
            `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
            `$Env:PIP_FIND_LINKS = `" `"
            `$pip_find_links_arg = `"`"
            `$go_to = 1
        }
        7 {
            `$torch_ver = `"torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2+cu118`"
            `$xformers_ver = `"xformers==0.0.23.post1+cu118`"
            `$go_to = 1
        }
        8 {
            `$torch_ver = `"torch==2.1.2+cu121 torchvision==0.16.2+cu121 torchaudio==2.1.2+cu121`"
            `$xformers_ver = `"xformers==0.0.23.post1`"
            `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
            `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
            `$Env:PIP_FIND_LINKS = `" `"
            `$pip_find_links_arg = `"`"
            `$go_to = 1
        }
        9 {
            `$torch_ver = `"torch==2.2.0+cu118 torchvision==0.17.0+cu118 torchaudio==2.2.0+cu118`"
            `$xformers_ver = `"xformers==0.0.24+cu118`"
            `$go_to = 1
        }
        10 {
            `$torch_ver = `"torch==2.2.0+cu121 torchvision==0.17.0+cu121 torchaudio==2.2.0+cu121`"
            `$xformers_ver = `"xformers==0.0.24`"
            `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
            `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
            `$Env:PIP_FIND_LINKS = `" `"
            `$pip_find_links_arg = `"`"
            `$go_to = 1
        }
        11 {
            `$torch_ver = `"torch==2.2.1+cu118 torchvision==0.17.1+cu118 torchaudio==2.2.1+cu118`"
            `$xformers_ver = `"xformers==0.0.25+cu118`"
            `$go_to = 1
        }
        12 {
            `$torch_ver = `"torch==2.2.1+cu121 torchvision==0.17.1+cu121 torchaudio==2.2.1+cu121`"
            `$xformers_ver = `"xformers==0.0.25`"
            `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
            `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
            `$Env:PIP_FIND_LINKS = `" `"
            `$pip_find_links_arg = `"`"
            `$go_to = 1
        }
        13 {
            `$torch_ver = `"torch==2.2.2+cu118 torchvision==0.17.2+cu118 torchaudio==2.2.2+cu118`"
            `$xformers_ver = `"xformers==0.0.25.post1+cu118`"
            `$go_to = 1
        }
        14 {
            `$torch_ver = `"torch==2.2.2+cu121 torchvision==0.17.2+cu121 torchaudio==2.2.2+cu121`"
            `$xformers_ver = `"xformers==0.0.25.post1`"
            `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
            `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
            `$Env:PIP_FIND_LINKS = `" `"
            `$pip_find_links_arg = `"`"
            `$go_to = 1
        }
        15 {
            `$torch_ver = `"torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118`"
            `$xformers_ver = `"xformers==0.0.26.post1+cu118`"
            `$go_to = 1
        }
        16 {
            `$torch_ver = `"torch==2.3.0+cu121 torchvision==0.18.0+cu121 torchaudio==2.3.0+cu121`"
            `$xformers_ver = `"xformers==0.0.26.post1`"
            `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
            `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
            `$Env:PIP_FIND_LINKS = `" `"
            `$pip_find_links_arg = `"`"
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
            `$pip_find_links_arg = `"`"
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
            `$pip_find_links_arg = `"`"
            `$go_to = 1
        }
        21 {
            `$torch_ver = `"torch==2.4.0+cu124 torchvision==0.19.0+cu124 torchaudio==2.4.0+cu124`"
            `$xformers_ver = `"`"
            `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU124`"
            `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU124`"
            `$Env:PIP_FIND_LINKS = `" `"
            `$pip_find_links_arg = `"`"
            `$go_to = 1
        }
        22 {
            `$torch_ver = `"torch==2.4.1+cu118 torchvision==0.19.1+cu118 torchaudio==2.4.1+cu118`"
            `$xformers_ver = `"xformers==0.0.26.post1+cu118`"
            `$go_to = 1
        }
        23 {
            `$torch_ver = `"torch==2.4.1+cu121 torchvision==0.19.1+cu121 torchaudio==2.4.1+cu121`"
            `$xformers_ver = `"xformers==`"
            `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
            `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
            `$Env:PIP_FIND_LINKS = `" `"
            `$pip_find_links_arg = `"`"
            `$go_to = 1
        }
        24 {
            `$torch_ver = `"torch==2.4.1+cu124 torchvision==0.19.1+cu124 torchaudio==2.4.1+cu124`"
            `$xformers_ver = `"`"
            `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU124`"
            `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU124`"
            `$Env:PIP_FIND_LINKS = `" `"
            `$pip_find_links_arg = `"`"
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
`$use_force_reinstall = Read-Host `"===========================================>`"

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
`$install_torch = Read-Host `"===========================================>`"

if (`$install_torch -eq `"yes`" -or `$install_torch -eq `"y`" -or `$install_torch -eq `"YES`" -or `$install_torch -eq `"Y`") {
    Print-Msg `"重装 PyTorch 中`"
    if (`$USE_UV) {
        uv pip install `$torch_ver.ToString().Split() `$force_reinstall_arg `$pip_find_links_arg.ToString().Split()
    } else {
        python -m pip install `$torch_ver.ToString().Split() `$force_reinstall_arg --no-warn-script-location
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
            uv pip install `$xformers_ver `$force_reinstall_arg --no-deps `$pip_find_links_arg.ToString().Split()
        } else {
            python -m pip install `$xformers_ver `$force_reinstall_arg --no-deps --no-warn-script-location
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
Read-Host | Out-Null
"

    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/reinstall_pytorch.ps1" -Value $content
}


# 模型下载脚本
function Write-Download-Model-Script {
    $content = "
# SD-Trainer Installer 版本和检查更新间隔
`$Env:SD_TRAINER_INSTALLER_VERSION = $SD_TRAINER_INSTALLER_VERSION
`$Env:UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# Pip 镜像源
`$PIP_INDEX_MIRROR = `"$PIP_INDEX_MIRROR`"
`$PIP_EXTRA_INDEX_MIRROR = `"$PIP_EXTRA_INDEX_MIRROR`"
`$PIP_FIND_MIRROR = `"$PIP_FIND_MIRROR`"
# `$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
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
# `$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
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
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
}

# SD-Trainer Installer 更新检测
function Check-SD-Trainer-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    if (Test-Path `"`$PSScriptRoot/disable_update.txt`") {
        Print-Msg `"检测到 disable_update.txt 更新配置文件, 已禁用 SD-Trainer Installer 的自动检查更新功能`"
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
            Print-Msg `"检查 SD-Trainer Installer 更新中`"
            Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`"
            if (`$?) {
                `$latest_version = [int]`$(Get-Content `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" | Select-String -Pattern `"SD_TRAINER_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
                Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`"
                if (`$latest_version -gt `$SD_TRAINER_INSTALLER_VERSION) {
                    New-Item -ItemType File -Path `"`$PSScriptRoot/new_version.txt`" -Force > `$null
                    Print-Msg `"SD-Trainer Installer 有新版本可用`"
                    Print-Msg `"更新方法可阅读: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md#%E6%9B%B4%E6%96%B0-sd-trainer-%E7%AE%A1%E7%90%86%E8%84%9A%E6%9C%AC`"
                    Start-Sleep -Seconds 1
                } else {
                    Print-Msg `"SD-Trainer Installer 已是最新版本`"
                }
                break
            } else {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Print-Msg `"重试检查 SD-Trainer Installer 更新中`"
                } else {
                    Print-Msg `"检查 SD-Trainer Installer 更新失败`"
                }
            }
        }
    } elseif (Test-Path `"`$PSScriptRoot/new_version.txt`") {
        Print-Msg `"SD-Trainer Installer 有新版本可用`"
        Print-Msg `"更新方法可阅读: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md#%E6%9B%B4%E6%96%B0-sd-trainer-%E7%AE%A1%E7%90%86%E8%84%9A%E6%9C%AC`"
        Start-Sleep -Seconds 1
    }
}

Check-SD-Trainer-Installer-Update

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
- 19、flux1-schnell (FLUX.1)
- 20、flux1-schnell-fp8 (FLUX.1)
- 21、flux1-dev (FLUX.1)
- 22、flux1-dev-fp8 (FLUX.1)
- 23、vae-ft-ema-560000-ema-pruned (SD 1.5 VAE)
- 24、vae-ft-mse-840000-ema-pruned (SD 1.5 VAE)
- 25、sdxl_fp16_fix_vae (SDXL VAE)
- 26、sdxl_vae (SDXL VAE)
- 27、ae (FLUX.1 VAE)
- 28、clip_l (FLUX.1 CLIP)
- 29、t5xxl_fp16 (FLUX.1 CLIP)
- 30、t5xxl_fp8_e4m3fn (FLUX.1 CLIP)

关于模型的介绍可阅读：https://github.com/licyk/README-collection/blob/main/model-info/README.md
-----------------------------------------------------
`"

    Write-Host `$content
    Print-Msg `"请选择要下载的模型`"
    Print-Msg `"提示: 输入数字后回车, 或者输入 exit 退出模型下载脚本`"
    `$arg = Read-Host `"===========================================>`"

    switch (`$arg) {
        1 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/v1-5-pruned-emaonly.safetensors`"
            `$model_name = `"v1-5-pruned-emaonly.safetensors`"
            `$go_to = 1
        }
        2 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/animefull-final-pruned.safetensors`"
            `$model_name = `"animefull-final-pruned.safetensors`"
            `$go_to = 1
        }
        3 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_2.1/v2-1_768-ema-pruned.safetensors`"
            `$model_name = `"v2-1_768-ema-pruned.safetensors`"
            `$go_to = 1
        }
        4 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_2.1/wd-1-4-anime_e2.ckpt`"
            `$model_name = `"wd-1-4-anime_e2.ckpt`"
            `$go_to = 1
        }
        5 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_2.1/wd-mofu-fp16.safetensors`"
            `$model_name = `"wd-mofu-fp16.safetensors`"
            `$go_to = 1
        }
        6 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/sd_xl_base_1.0_0.9vae.safetensors`"
            `$model_name = `"sd_xl_base_1.0_0.9vae.safetensors`"
            `$go_to = 1
        }
        7 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/animagine-xl-3.0.safetensors`"
            `$model_name = `"animagine-xl-3.0.safetensors`"
            `$go_to = 1
        }
        8 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/animagine-xl-3.1.safetensors`"
            `$model_name = `"animagine-xl-3.1.safetensors`"
            `$go_to = 1
        }
        9 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohaku-xl-delta-rev1.safetensors`"
            `$model_name = `"kohaku-xl-delta-rev1.safetensors`"
            `$go_to = 1
        }
        10 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohakuXLEpsilon_rev1.safetensors`"
            `$model_name = `"kohakuXLEpsilon_rev1.safetensors`"
            `$go_to = 1
        }
        11 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohaku-xl-epsilon-rev2.safetensors`"
            `$model_name = `"kohaku-xl-epsilon-rev2.safetensors`"
            `$go_to = 1
        }
        12 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohaku-xl-epsilon-rev3.safetensors`"
            `$model_name = `"kohaku-xl-epsilon-rev3.safetensors`"
            `$go_to = 1
        }
        13 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohaku-xl-zeta.safetensors`"
            `$model_name = `"kohaku-xl-zeta.safetensors`"
            `$go_to = 1
        }
        14 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/ponyDiffusionV6XL_v6StartWithThisOne.safetensors`"
            `$model_name = `"ponyDiffusionV6XL_v6.safetensors`"
            `$go_to = 1
        }
        15 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/pdForAnime_v20.safetensors`"
            `$model_name = `"pdForAnime_v20.safetensors`"
            `$go_to = 1
        }
        16 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/starryXLV52_v52.safetensors`"
            `$model_name = `"starryXLV52_v52.safetensors`"
            `$go_to = 1
        }
        17 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/heartOfAppleXL_v20.safetensors`"
            `$model_name = `"heartOfAppleXL_v20.safetensors`"
            `$go_to = 1
        }
        18 {
            `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/heartOfAppleXL_v30.safetensors`"
            `$model_name = `"heartOfAppleXL_v30.safetensors`"
            `$go_to = 1
        }
        19 {
            `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell.safetensors`"
            `$model_name = `"flux1-schnell.safetensors`"
            `$go_to = 1
        }
        20 {
            `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell-fp8.safetensors`"
            `$model_name = `"flux1-schnell-fp8.safetensors`"
            `$go_to = 1
        }
        21 {
            `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev.safetensors`"
            `$model_name = `"flux1-dev.safetensors`"
            `$go_to = 1
        }
        22 {
            `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev-fp8.safetensors`"
            `$model_name = `"flux1-dev-fp8.safetensors`"
            `$go_to = 1
        }
        23 {
            `$url = `"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sd_1.5/vae-ft-ema-560000-ema-pruned.safetensors`"
            `$model_name = `"vae-ft-ema-560000-ema-pruned.safetensors`"
            `$go_to = 1
        }
        24 {
            `$url = `"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sd_1.5/vae-ft-mse-840000-ema-pruned.safetensors`"
            `$model_name = `"vae-ft-mse-840000-ema-pruned.safetensors`"
            `$go_to = 1
        }
        25 {
            `$url = `"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sdxl_1.0/sdxl_fp16_fix_vae.safetensors`"
            `$model_name = `"sdxl_fp16_fix_vae.safetensors`"
            `$go_to = 1
        }
        26 {
            `$url = `"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sdxl_1.0/sdxl_vae.safetensors`"
            `$model_name = `"sdxl_vae.safetensors`"
            `$go_to = 1
        }
        27 {
            `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_vae/ae.safetensors`"
            `$model_name = `"ae.safetensors`"
            `$go_to = 1
        }
        28 {
            `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/clip_l.safetensors`"
            `$model_name = `"clip_l.safetensors`"
            `$go_to = 1
        }
        29 {
            `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5xxl_fp16.safetensors`"
            `$model_name = `"t5xxl_fp16.safetensors`"
            `$go_to = 1
        }
        30 {
            `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5xxl_fp8_e4m3fn.safetensors`"
            `$model_name = `"t5xxl_fp8_e4m3fn.safetensors`"
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

Print-Msg `"当前选择要下载的模型: `$model_name`"
Print-Msg `"是否确认下载模型?`"
Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
`$download_model = Read-Host `"===========================================>`"

if (`$download_model -eq `"yes`" -or `$download_model -eq `"y`" -or `$download_model -eq `"YES`" -or `$download_model -eq `"Y`") {
    Print-Msg `"模型将下载至 `$PSScriptRoot\models 目录中`"
    Print-Msg `"下载 `$model_name 模型中`"
    aria2c --file-allocation=none --summary-interval=0 --console-log-level=error -s 64 -c -x 16 `$url -d `"`$PSScriptRoot/models`" -o `$model_name
    if (`$?) {
        Print-Msg `"`$model_name 模型下载成功`"
    } else {
        Print-Msg `"`$model_name 模型下载失败`"
    }
}

Print-Msg `"退出模型下载脚本`"
Read-Host | Out-Null
"

    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/download_models.ps1" -Value $content
}


# 虚拟环境激活脚本
function Write-Env-Activate-Script {
    $content = "
# SD-Trainer Installer 版本和检查更新间隔
`$SD_TRAINER_INSTALLER_VERSION = $SD_TRAINER_INSTALLER_VERSION
`$UPDATE_TIME_SPAN = $UPDATE_TIME_SPAN
# Pip 镜像源
`$PIP_INDEX_MIRROR = `"$PIP_INDEX_MIRROR`"
`$PIP_EXTRA_INDEX_MIRROR = `"$PIP_EXTRA_INDEX_MIRROR`"
`$PIP_FIND_MIRROR = `"$PIP_FIND_MIRROR`"
# `$PIP_FIND_MIRROR_CU121 = `"$PIP_FIND_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_PYTORCH = `"$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
`$PIP_EXTRA_INDEX_MIRROR_CU121 = `"$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$PIP_EXTRA_INDEX_MIRROR_CU124 = `"$PIP_EXTRA_INDEX_MIRROR_CU124`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
# 环境变量
`$Env:PIP_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
`$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
`$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
# `$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
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


# 提示符信息
function global:prompt {
    `"`$(Write-Host `"[SD-Trainer Env]`" -ForegroundColor Green -NoNewLine) `$(Get-Location)> `"
}

# 消息输出
function global:Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
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
        Move-Item -Path `"`$Env:CACHE_HOME/aria2c.exe`" -Destination `"`$Env:CACHE_HOME/../git/bin/aria2c.exe`" -Force
        Print-Msg `"更新 Aria2 完成`"
    } else {
        Print-Msg `"下载 Aria2 失败, 无法进行更新, 可尝试重新运行更新命令`"
    }
}

# SD-Trainer Installer 更新检测
function global:Check-SD-Trainer-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$Env:CACHE_HOME`" -Force > `$null

    Set-Content -Encoding UTF8 -Path `"`$Env:CACHE_HOME/../update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间
    ForEach (`$url in `$urls) {
        Print-Msg `"检查 SD-Trainer Installer 更新中`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$Env:CACHE_HOME/sd_trainer_installer.ps1`"
        if (`$?) {
            `$latest_version = [int]`$(Get-Content `"`$Env:CACHE_HOME/sd_trainer_installer.ps1`" | Select-String -Pattern `"SD_TRAINER_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
            Remove-Item -Path `"`$Env:CACHE_HOME/sd_trainer_installer.ps1`"
            if (`$latest_version -gt `$SD_TRAINER_INSTALLER_VERSION) {
                New-Item -ItemType File -Path `"`$Env:CACHE_HOME/../new_version.txt`" -Force > `$null
                Print-Msg `"SD-Trainer Installer 有新版本可用`"
                Print-Msg `"更新方法可阅读: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md#%E6%9B%B4%E6%96%B0-sd-trainer-%E7%AE%A1%E7%90%86%E8%84%9A%E6%9C%AC`"
                Start-Sleep -Seconds 1
            } else {
                Print-Msg `"SD-Trainer Installer 已是最新版本`"
            }
            break
        } else {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Print-Msg `"重试检查 SD-Trainer Installer 更新中`"
            } else {
                Print-Msg `"检查 SD-Trainer Installer 更新失败`"
            }
        }
    }
}

# 列出 SD-Trainer Installer 内置命令
function global:List-CMD {
    Write-Host `"
==================================
SD-Trainer Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
==================================

当前可用的 SD-Trainer Installer 内置命令：

    Update-uv
    Update-Aria2
    Check-SD-Trainer-Installer-Update
    List-CMD

更多帮助信息可在 SD-Trainer Installer 文档中查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md
`"
}


# 代理配置
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

# HuggingFace 镜像源
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

# Github 镜像源
if (Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") { # 禁用 Github 镜像源
    Print-Msg `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件, 禁用 Github 镜像源`"
} else {
    if (Test-Path `"`$PSScriptRoot/gh_mirror.txt`") { # 使用自定义 Github 镜像源
        `$Env:GIT_CONFIG_GLOBAL = `"`$PSScriptRoot/.gitconfig`" # 设置 Git 配置文件路径
        if (Test-Path `"`$PSScriptRoot/.gitconfig`") {
            Remove-Item -Path `"`$PSScriptRoot/.gitconfig`" -Force
        }
        `$github_mirror = Get-Content `"`$PSScriptRoot/gh_mirror.txt`"
        git config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
        Print-Msg `"检测到本地存在 gh_mirror.txt Github 镜像源配置文件, 已读取 Github 镜像源配置文件并设置 Github 镜像源`"
    }
}


Print-Msg `"激活 SD-Trainer Env`"
Print-Msg `"更多帮助信息可在 SD-Trainer Installer 项目地址查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md`"
"

    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/activate.ps1" -Value $content
}


# 帮助文档
function Write-ReadMe {
    $content = "==================================
SD-Trainer Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
==================================

这是关于 SD-Trainer 的简单使用文档。

使用 SD-Trainer Installer 进行安装并安装成功后，将在当前目录生成 SD-Trainer 文件夹，以下为文件夹中不同文件 / 文件夹的作用。

cache：缓存文件夹，保存着 Pip / HuggingFace 等缓存文件。
python：Python 的存放路径。请注意，请勿将该 Python 文件夹添加到环境变量，这可能导致不良后果。
git：Git 的存放路径。
lora-scripts：SD-Trainer 存放的文件夹。
models：使用模型下载脚本下载模型时模型的存放位置。
activate.ps1：虚拟环境激活脚本，使用该脚本激活虚拟环境后即可使用 Python、Pip、Git 的命令。
get_sd_trainer_installer.ps1：获取最新的 SD-Trainer Installer 安装脚本，运行后将会在与 SD-Trainer 文件夹同级的目录中生成 sd_trainer_installer.ps1 安装脚本。
update.ps1：更新 SD-Trainer 的脚本，可使用该脚本更新 SD-Trainer。
launch.ps1：启动 SD-Trainer 的脚本。
reinstall_pytorch.ps1：重新安装 PyTorch 的脚本，在 PyTorch 出问题或者需要切换 PyTorch 版本时可使用。
download_model.ps1：下载模型的脚本，下载的模型将存放在 models 文件夹中。关于模型的介绍可阅读：https://github.com/licyk/README-collection/blob/main/model-info/README.md。
help.txt：帮助文档。


要启动 SD-Trainer，可在 SD-Trainer 文件夹中找到 launch.ps1 脚本，右键这个脚本，选择使用 PowerShell 运行，等待 SD-Trainer 启动完成，启动完成后将自动打开浏览器进入 SD-Trainer 界面。

脚本为 SD-Trainer 设置了 HuggingFace 镜像源，解决国内无法直接访问 HuggingFace，导致 SD-Trainer 无法从 HuggingFace 下载模型的问题。
如果想自定义 HuggingFace 镜像源，可以在本地创建 hf_mirror.txt 文件，在文件中填写 HuggingFace 镜像源的地址后保存，再次启动脚本时将自动读取配置。
如果需要禁用 HuggingFace 镜像源，则创建 disable_hf_mirror.txt 文件，启动脚本时将不再设置 HuggingFace 镜像源。

以下为可用的 HuggingFace 镜像源地址：
https://hf-mirror.com
https://huggingface.sukaka.top

为了解决访问 Github 速度慢的问题，脚本默认启用 Github 镜像源，在运行 SD-Trainer Installer 或者 SD-Trainer 更新脚本时将自动测试可用的 Github 镜像源并设置。
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

设置 SD-Trainer 的启动参数，可以在和 launch.ps1 脚本同级的目录创建一个 launch_args.txt 文件，在文件内写上启动参数，运行 SD-Trainer 启动脚本时将自动读取该文件内的启动参数并应用。

更多详细的帮助可在下面的链接查看。
SD-Trainer Installer 使用帮助：https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md
SD-Trainer 项目地址：https://github.com/Akegarasu/lora-scripts

推荐的哔哩哔哩 UP 主：
青龙圣者：https://space.bilibili.com/219296
秋葉aaaki：https://space.bilibili.com/12566101
琥珀青葉：https://space.bilibili.com/507303431

一些训练模型的教程：
https://rentry.org/59xed3
https://civitai.com/articles/2056
https://civitai.com/articles/124/lora-analogy-about-lora-trainning-and-using
https://civitai.com/articles/143/some-shallow-understanding-of-lora-training-lora
https://civitai.com/articles/632/why-this-lora-can-not-bring-good-result-lora
https://civitai.com/articles/726/an-easy-way-to-make-a-cosplay-lora-cosplay-lora
https://civitai.com/articles/2135/lora-quality-improvement-some-experiences-about-datasets-and-captions-lora
https://civitai.com/articles/2297/ways-to-make-a-character-lora-that-is-easier-to-change-clothes-lora
"

    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/help.txt" -Value $content
}


# 主程序
function Main {
    Print-Msg "启动 SD-Trainer 安装程序"
    Print-Msg "提示: 若出现某个步骤执行失败, 可尝试再次运行 SD-Trainer Installer"
    Print-Msg "SD-Trainer Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md"
    Check-Install
    Print-Msg "添加启动脚本和文档中"
    Write-Launch-Script
    Write-Update-Script
    Write-SD-Trainer-Install-Script
    Write-PyTorch-ReInstall-Script
    Write-Download-Model-Script
    Write-Env-Activate-Script
    Write-ReadMe
    Print-Msg "SD-Trainer 安装结束, 安装路径为 $PSScriptRoot\SD-Trainer"
    Print-Msg "帮助文档可在 SD-Trainer 文件夹中查看, 双击 help.txt 文件即可查看"
    Print-Msg "退出 SD-Trainer Installer"
}


###################


Main
Read-Host | Out-Null
