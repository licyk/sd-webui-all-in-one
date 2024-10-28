# 有关 PowerShell 脚本保存编码的问题: https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_character_encoding?view=powershell-7.4#the-byte-order-mark
# SD-Trainer Installer 版本和检查更新间隔
$SD_TRAINER_INSTALLER_VERSION = 141
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
$UV_MINIMUM_VER = "0.4.26"
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
    Invoke-WebRequest -Uri $url -OutFile "$PSScriptRoot/SD-Trainer/cache/python-3.10.11-amd64.zip"
    if ($?) { # 检测是否下载成功并解压
        # 创建 Python 文件夹
        if (!(Test-Path "$PSScriptRoot/SD-Trainer/python")) {
            New-Item -ItemType Directory -Force -Path "$PSScriptRoot/SD-Trainer/python" > $null
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
            git config --global --add safe.directory "*"
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
                git config --global --add safe.directory "*"
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
    Set-Location "$PSScriptRoot/SD-Trainer/lora-scripts"
    Print-Msg "安装 SD-Trainer 依赖中"
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
    Check-uv-Version

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
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
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
                if (`$latest_version -gt `$SD_TRAINER_INSTALLER_VERSION) {
                    New-Item -ItemType File -Path `"`$PSScriptRoot/use_update_mode.txt`" -Force > `$null
                    Print-Msg `"检测到 SD-Trainer Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"===========================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 SD-Trainer Installer 进行更新中`"
                        `$folder_name = Split-Path `$PSScriptRoot -Leaf
                        if (!(`$folder_name -eq `"SD-Trainer`")) { # 检测脚本所在文件夹是否符合要求
                            Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/update_time.txt`" 2> `$null
                            Print-Msg `"检测到 SD-Trainer Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                            Print-Msg `"当前 SD-Trainer Installer 管理脚本所在文件夹名称: `$folder_name`"
                            Print-Msg `"请前往 `$(Split-Path `"`$PSScriptRoot`") 路径, 将名称为 `$folder_name 的文件夹改名为 SD-Trainer, 再重新更新 SD-Trainer Installer 管理脚本`"
                            Print-Msg `"终止 SD-Trainer Installer 的更新`"
                            Read-Host | Out-Null
                            exit 1
                        }
                        Move-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" `"`$PSScriptRoot/../sd_trainer_installer.ps1`" -Force
                        powershell `"`$PSScriptRoot/../sd_trainer_installer.ps1`"
                        Print-Msg `"更新结束, 需重新启动 SD-Trainer Installer 管理脚本以应用更新, 回车退出 SD-Trainer Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" 2> `$null
                        Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                        Print-Msg `"跳过 SD-Trainer Installer 更新`"
                    }
                } else {
                    Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
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


# SD-Trainer 启动参数
function Get-SD-Trainer-Launch-Args {
    if (Test-Path `"`$PSScriptRoot/launch_args.txt`") {
        `$args = Get-Content `"`$PSScriptRoot/launch_args.txt`"
        Print-Msg `"检测到本地存在 launch_args.txt 启动参数配置文件, 已读取该启动参数配置文件并应用启动参数`"
        Print-Msg `"使用的启动参数: `$args`"
    } else {
        `$args = `"`"
    }
    return `$args
}


# 设置 SD-Trainer 的快捷启动方式
function Create-SD-Trainer-Shortcut {
    `$filename = `"SD-Trainer`"
    `$url = `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/sd_trainer_icon.ico`"
    `$shortcut_icon = `"`$PSScriptRoot/sd_trainer_icon.ico`"

    if (!(Test-Path `"`$PSScriptRoot/enable_shortcut.txt`")) {
        return
    }

    Print-Msg `"检查 SD-Trainer 快捷启动方式中`"
    if (!(Test-Path `"`$shortcut_icon`")) {
        Print-Msg `"获取 SD-Trainer 图标中`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/sd_trainer_icon.ico`"
        if (!(`$?)) {
            Print-Msg `"获取 SD-Trainer 图标失败, 无法创建 SD-Trainer 快捷启动方式`"
            return
        }
    }

    Print-Msg `"更新 SD-Trainer 快捷启动方式`"
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
    Print-Msg `"SD-Trainer Installer 版本: v`$SD_TRAINER_INSTALLER_VERSION`"
    Set-Proxy
    Set-HuggingFace-Mirror
    Pip-Mirror-Status
    `$args = Get-SD-Trainer-Launch-Args
    # 记录上次的路径
    `$current_path = Get-Location
    `$current_path = `$current_path.ToString()

    # 检测使用的启动脚本
    if (Test-Path `"`$PSScriptRoot/lora-scripts/gui.py`") {
        `$launch_script = `"gui.py`"
    } elseif (Test-Path `"`$PSScriptRoot/lora-scripts/kohya_gui.py`") {
        `$launch_script = `"kohya_gui.py`"
    } else {
        `$launch_script = `"gui.py`"
    }

    Check-SD-Trainer-Installer-Update
    Create-SD-Trainer-Shortcut
    Fix-PyTorch
    Print-Msg `"启动 SD-Trainer 中`"
    Set-Location `"`$PSScriptRoot/lora-scripts`"
    python `$launch_script.ToString() `$args.ToString().Split()
    `$req = `$?
    if (`$req) {
        Print-Msg `"SD-Trainer 正常退出`"
    } else {
        Print-Msg `"SD-Trainer 出现异常, 已退出`"
    }
    Set-Location `"`$current_path`"
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/SD-Trainer/launch.ps1") {
        Print-Msg "更新 launch.ps1 中"
    } else {
        Print-Msg "生成 launch.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/launch.ps1" -Value $content
}


# 更新脚本
function Write-Update-Script {
    $content = "
# SD-Trainer Installer 版本和检查更新间隔
`$SD_TRAINER_INSTALLER_VERSION = $SD_TRAINER_INSTALLER_VERSION
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
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
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
                if (`$latest_version -gt `$SD_TRAINER_INSTALLER_VERSION) {
                    New-Item -ItemType File -Path `"`$PSScriptRoot/use_update_mode.txt`" -Force > `$null
                    Print-Msg `"检测到 SD-Trainer Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"===========================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 SD-Trainer Installer 进行更新中`"
                        `$folder_name = Split-Path `$PSScriptRoot -Leaf
                        if (!(`$folder_name -eq `"SD-Trainer`")) { # 检测脚本所在文件夹是否符合要求
                            Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/update_time.txt`" 2> `$null
                            Print-Msg `"检测到 SD-Trainer Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                            Print-Msg `"当前 SD-Trainer Installer 管理脚本所在文件夹名称: `$folder_name`"
                            Print-Msg `"请前往 `$(Split-Path `"`$PSScriptRoot`") 路径, 将名称为 `$folder_name 的文件夹改名为 SD-Trainer, 再重新更新 SD-Trainer Installer 管理脚本`"
                            Print-Msg `"终止 SD-Trainer Installer 的更新`"
                            Read-Host | Out-Null
                            exit 1
                        }
                        Move-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" `"`$PSScriptRoot/../sd_trainer_installer.ps1`" -Force
                        powershell `"`$PSScriptRoot/../sd_trainer_installer.ps1`"
                        Print-Msg `"更新结束, 需重新启动 SD-Trainer Installer 管理脚本以应用更新, 回车退出 SD-Trainer Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" 2> `$null
                        Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                        Print-Msg `"跳过 SD-Trainer Installer 更新`"
                    }
                } else {
                    Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
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
    Print-Msg `"SD-Trainer Installer 版本: v`$SD_TRAINER_INSTALLER_VERSION`"
    Set-uv
    Set-Proxy
    Set-Github-Mirror
    Pip-Mirror-Status

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

        Print-Msg `"更新 SD-Trainer 依赖中`"
        Set-Location `"`$PSScriptRoot/lora-scripts`"
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
        `$req_update_msg = `"因 SD-Trainer 组件更新失败, 不进行更新`"
        `$update_fail = 1
    }

    Print-Msg `"==================================================================`"
    Print-Msg `"SD-Trainer 更新结果：`"
    Print-Msg `"SD-Trainer 组件: `$core_update_msg`"
    Print-Msg `"SD-Trainer 依赖: `$req_update_msg`"
    Print-Msg `"==================================================================`"
    if (`$update_fail -eq 0) {
        Print-Msg `"SD-Trainer 更新成功`"
    } else {
        Print-Msg `"SD-Trainer 更新失败, 请检查控制台日志。可尝试重新运行 SD-Trainer 更新脚本进行重试`"
    }

    Print-Msg `"退出 SD-Trainer 更新脚本`"
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/SD-Trainer/update.ps1") {
        Print-Msg "更新 update.ps1 中"
    } else {
        Print-Msg "生成 update.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/update.ps1" -Value $content
}


# 获取安装脚本
function Write-SD-Trainer-Install-Script {
    $content = "
`$SD_TRAINER_INSTALLER_VERSION = $SD_TRAINER_INSTALLER_VERSION
# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
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
    Print-Msg `"SD-Trainer Installer 版本: v`$SD_TRAINER_INSTALLER_VERSION`"
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
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/SD-Trainer/get_sd_trainer_installer.ps1") {
        Print-Msg "更新 get_sd_trainer_installer.ps1 中"
    } else {
        Print-Msg "生成 get_sd_trainer_installer.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/get_sd_trainer_installer.ps1" -Value $content
}


# 重装 PyTorch 脚本
function Write-PyTorch-ReInstall-Script {
    $content = "
# SD-Trainer Installer 版本和检查更新间隔
`$SD_TRAINER_INSTALLER_VERSION = $SD_TRAINER_INSTALLER_VERSION
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
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
}


# Pip 镜像源状态
function Pip-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 Pip 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pip_mirror.txt 配置文件, 已将 Pip 源切换至官方源`"
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
                if (`$latest_version -gt `$SD_TRAINER_INSTALLER_VERSION) {
                    New-Item -ItemType File -Path `"`$PSScriptRoot/use_update_mode.txt`" -Force > `$null
                    Print-Msg `"检测到 SD-Trainer Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"===========================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 SD-Trainer Installer 进行更新中`"
                        `$folder_name = Split-Path `$PSScriptRoot -Leaf
                        if (!(`$folder_name -eq `"SD-Trainer`")) { # 检测脚本所在文件夹是否符合要求
                            Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/update_time.txt`" 2> `$null
                            Print-Msg `"检测到 SD-Trainer Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                            Print-Msg `"当前 SD-Trainer Installer 管理脚本所在文件夹名称: `$folder_name`"
                            Print-Msg `"请前往 `$(Split-Path `"`$PSScriptRoot`") 路径, 将名称为 `$folder_name 的文件夹改名为 SD-Trainer, 再重新更新 SD-Trainer Installer 管理脚本`"
                            Print-Msg `"终止 SD-Trainer Installer 的更新`"
                            Read-Host | Out-Null
                            exit 1
                        }
                        Move-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" `"`$PSScriptRoot/../sd_trainer_installer.ps1`" -Force
                        powershell `"`$PSScriptRoot/../sd_trainer_installer.ps1`"
                        Print-Msg `"更新结束, 需重新启动 SD-Trainer Installer 管理脚本以应用更新, 回车退出 SD-Trainer Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" 2> `$null
                        Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                        Print-Msg `"跳过 SD-Trainer Installer 更新`"
                    }
                } else {
                    Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
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
    Print-Msg `"SD-Trainer Installer 版本: v`$SD_TRAINER_INSTALLER_VERSION`"
    Set-uv
    Set-Proxy
    Pip-Mirror-Status
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
- 22、Torch 2.4.1 (CUDA 11.8)
- 23、Torch 2.4.1 (CUDA 12.1)
- 24、Torch 2.4.1 (CUDA 12.4) + xFormers 0.0.28.post1
- 25、Torch 2.5.0 (CUDA 11.8)
- 26、Torch 2.5.0 (CUDA 12.1)
- 27、Torch 2.5.0 (CUDA 12.4) + xFormers 0.0.28.post2
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
                `$xformers_ver = `"xformers===0.0.23`"
                # `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
                # `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
                # `$Env:PIP_FIND_LINKS = `" `"
                # `$Env:UV_FIND_LINKS = `"`"
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
                # `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
                # `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
                # `$Env:PIP_FIND_LINKS = `" `"
                # `$Env:UV_FIND_LINKS = `"`"
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
                # `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
                # `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
                # `$Env:PIP_FIND_LINKS = `" `"
                # `$Env:UV_FIND_LINKS = `"`"
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
                # `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
                # `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
                # `$Env:PIP_FIND_LINKS = `" `"
                # `$Env:UV_FIND_LINKS = `"`"
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
                # `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
                # `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
                # `$Env:PIP_FIND_LINKS = `" `"
                # `$Env:UV_FIND_LINKS = `"`"
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
                # `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
                # `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
                # `$Env:PIP_FIND_LINKS = `" `"
                # `$Env:UV_FIND_LINKS = `"`"
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
                `$torch_ver = `"torch==2.4.0+cu124 torchvision==0.19.0+cu124 torchaudio==2.4.0+cu124`"
                `$xformers_ver = `"`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU124`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU124`"
                `$Env:PIP_FIND_LINKS = `" `"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            22 {
                `$torch_ver = `"torch==2.4.1+cu118 torchvision==0.19.1+cu118 torchaudio==2.4.1+cu118`"
                `$xformers_ver = `"`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
                `$Env:PIP_FIND_LINKS = `" `"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            23 {
                `$torch_ver = `"torch==2.4.1+cu121 torchvision==0.19.1+cu121 torchaudio==2.4.1+cu121`"
                `$xformers_ver = `"`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
                `$Env:PIP_FIND_LINKS = `" `"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            24 {
                `$torch_ver = `"torch==2.4.1+cu124 torchvision==0.19.1+cu124 torchaudio==2.4.1+cu124`"
                `$xformers_ver = `"xformers===0.0.28.post1`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU124`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU124`"
                `$Env:PIP_FIND_LINKS = `" `"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            25 {
                `$torch_ver = `"torch==2.5.0+cu118 torchvision==0.20.0+cu118 torchaudio==2.5.0+cu118`"
                `$xformers_ver = `"`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_PYTORCH`"
                `$Env:PIP_FIND_LINKS = `" `"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            26 {
                `$torch_ver = `"torch==2.5.0+cu121 torchvision==0.20.0+cu121 torchaudio==2.5.0+cu121`"
                `$xformers_ver = `"`"
                `$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_CU121`"
                `$Env:UV_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR_CU121`"
                `$Env:PIP_FIND_LINKS = `" `"
                `$Env:UV_FIND_LINKS = `"`"
                `$go_to = 1
            }
            27 {
                `$torch_ver = `"torch==2.5.0+cu124 torchvision==0.20.0+cu124 torchaudio==2.5.0+cu124`"
                `$xformers_ver = `"xformers==0.0.28.post2`"
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

    if (Test-Path "$PSScriptRoot/SD-Trainer/reinstall_pytorch.ps1") {
        Print-Msg "更新 reinstall_pytorch.ps1 中"
    } else {
        Print-Msg "生成 reinstall_pytorch.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/reinstall_pytorch.ps1" -Value $content
}


# 模型下载脚本
function Write-Download-Model-Script {
    $content = "
# SD-Trainer Installer 版本和检查更新间隔
`$SD_TRAINER_INSTALLER_VERSION = $SD_TRAINER_INSTALLER_VERSION
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
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
}


# Pip 镜像源状态
function Pip-Mirror-Status {
    if (`$USE_PIP_MIRROR) {
        Print-Msg `"使用 Pip 镜像源`"
    } else {
        Print-Msg `"检测到 disable_pip_mirror.txt 配置文件, 已将 Pip 源切换至官方源`"
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
                if (`$latest_version -gt `$SD_TRAINER_INSTALLER_VERSION) {
                    New-Item -ItemType File -Path `"`$PSScriptRoot/use_update_mode.txt`" -Force > `$null
                    Print-Msg `"检测到 SD-Trainer Installer 有新版本可用, 是否进行更新 (yes/no) ?`"
                    Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
                    `$arg = Read-Host `"===========================================>`"
                    if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
                        Print-Msg `"调用 SD-Trainer Installer 进行更新中`"
                        `$folder_name = Split-Path `$PSScriptRoot -Leaf
                        if (!(`$folder_name -eq `"SD-Trainer`")) { # 检测脚本所在文件夹是否符合要求
                            Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                            Remove-Item -Path `"`$PSScriptRoot/update_time.txt`" 2> `$null
                            Print-Msg `"检测到 SD-Trainer Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                            Print-Msg `"当前 SD-Trainer Installer 管理脚本所在文件夹名称: `$folder_name`"
                            Print-Msg `"请前往 `$(Split-Path `"`$PSScriptRoot`") 路径, 将名称为 `$folder_name 的文件夹改名为 SD-Trainer, 再重新更新 SD-Trainer Installer 管理脚本`"
                            Print-Msg `"终止 SD-Trainer Installer 的更新`"
                            Read-Host | Out-Null
                            exit 1
                        }
                        Move-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" `"`$PSScriptRoot/../sd_trainer_installer.ps1`" -Force
                        powershell `"`$PSScriptRoot/../sd_trainer_installer.ps1`"
                        Print-Msg `"更新结束, 需重新启动 SD-Trainer Installer 管理脚本以应用更新, 回车退出 SD-Trainer Installer 管理脚本`"
                        Read-Host | Out-Null
                        exit 0
                    } else {
                        Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" 2> `$null
                        Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                        Print-Msg `"跳过 SD-Trainer Installer 更新`"
                    }
                } else {
                    Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
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
}


function Main {
    Print-Msg `"初始化中`"
    Print-Msg `"SD-Trainer Installer 版本: v`$SD_TRAINER_INSTALLER_VERSION`"
    Pip-Mirror-Status
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
- 19、Illustrious-XL-v0.1 (SDXL)
- 20、Illustrious-XL-v0.1-GUIDED (SDXL)
- 21、noobaiXLNAIXL_earlyAccessVersion (SDXL)
- 22、noobaiXLNAIXL_epsilonPred05Version (SDXL)
- 23、noobaiXLNAIXL_vPredTestVersion (SDXL)
- 24、noobaiXLNAIXL_epsilonPred075 (SDXL)
- 25、noobaiXLNAIXL_epsilonPred077 (SDXL)
- 26、flux1-schnell (FLUX.1)
- 27、flux1-dev (FLUX.1)
- 28、ashen0209-flux1-dev2pro (FLUX.1)
- 29、nyanko7-flux-dev-de-distill (FLUX.1)
- 30、vae-ft-ema-560000-ema-pruned (SD 1.5 VAE)
- 31、vae-ft-mse-840000-ema-pruned (SD 1.5 VAE)
- 32、sdxl_fp16_fix_vae (SDXL VAE)
- 33、sdxl_vae (SDXL VAE)
- 34、ae (FLUX.1 VAE)
- 35、clip_l (FLUX.1 CLIP)
- 36、t5xxl_fp16 (FLUX.1 CLIP)

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
                `$go_to = 1
            }
            2 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_1.5/animefull-final-pruned.safetensors`"
                `$go_to = 1
            }
            3 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_2.1/v2-1_768-ema-pruned.safetensors`"
                `$go_to = 1
            }
            4 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_2.1/wd-1-4-anime_e2.ckpt`"
                `$go_to = 1
            }
            5 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sd_2.1/wd-mofu-fp16.safetensors`"
                `$go_to = 1
            }
            6 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/sd_xl_base_1.0_0.9vae.safetensors`"
                `$go_to = 1
            }
            7 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/animagine-xl-3.0.safetensors`"
                `$go_to = 1
            }
            8 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/animagine-xl-3.1.safetensors`"
                `$go_to = 1
            }
            9 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohaku-xl-delta-rev1.safetensors`"
                `$go_to = 1
            }
            10 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohakuXLEpsilon_rev1.safetensors`"
                `$go_to = 1
            }
            11 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohaku-xl-epsilon-rev2.safetensors`"
                `$go_to = 1
            }
            12 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohaku-xl-epsilon-rev3.safetensors`"
                `$go_to = 1
            }
            13 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/kohaku-xl-zeta.safetensors`"
                `$go_to = 1
            }
            14 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/ponyDiffusionV6XL_v6StartWithThisOne.safetensors`"
                `$go_to = 1
            }
            15 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/pdForAnime_v20.safetensors`"
                `$go_to = 1
            }
            16 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/starryXLV52_v52.safetensors`"
                `$go_to = 1
            }
            17 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/heartOfAppleXL_v20.safetensors`"
                `$go_to = 1
            }
            18 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/heartOfAppleXL_v30.safetensors`"
                `$go_to = 1
            }
            19 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/Illustrious-XL-v0.1.safetensors`"
                `$go_to = 1
            }
            20 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/Illustrious-XL-v0.1-GUIDED.safetensors`"
                `$go_to = 1
            }
            21 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_earlyAccessVersion.safetensors`"
                `$go_to = 1
            }
            22 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_epsilonPred05Version.safetensors`"
                `$go_to = 1
            }
            23 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_vPredTestVersion.safetensors`"
                `$go_to = 1
            }
            24 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_epsilonPred075.safetensors`"
                `$go_to = 1
            }
            25 {
                `$url = `"https://modelscope.cn/models/licyks/sd-model/resolve/master/sdxl_1.0/noobaiXLNAIXL_epsilonPred077.safetensors`"
                `$go_to = 1
            }
            26 {
                `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-schnell.safetensors`"
                `$go_to = 1
            }
            27 {
                `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/flux1-dev.safetensors`"
                `$go_to = 1
            }
            28 {
                `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/ashen0209-flux1-dev2pro.safetensors`"
                `$go_to = 1
            }
            29 {
                `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_1/nyanko7-flux-dev-de-distill.safetensors`"
                `$go_to = 1
            }
            30 {
                `$url = `"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sd_1.5/vae-ft-ema-560000-ema-pruned.safetensors`"
                `$go_to = 1
            }
            31 {
                `$url = `"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sd_1.5/vae-ft-mse-840000-ema-pruned.safetensors`"
                `$go_to = 1
            }
            32 {
                `$url = `"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sdxl_1.0/sdxl_fp16_fix_vae.safetensors`"
                `$go_to = 1
            }
            33 {
                `$url = `"https://modelscope.cn/models/licyks/sd-vae/resolve/master/sdxl_1.0/sdxl_vae.safetensors`"
                `$go_to = 1
            }
            34 {
                `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_vae/ae.safetensors`"
                `$go_to = 1
            }
            35 {
                `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/clip_l.safetensors`"
                `$go_to = 1
            }
            36 {
                `$url = `"https://modelscope.cn/models/licyks/flux-model/resolve/master/flux_text_encoders/t5xxl_fp16.safetensors`"
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
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/SD-Trainer/download_models.ps1") {
        Print-Msg "更新 download_models.ps1 中"
    } else {
        Print-Msg "生成 download_models.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/download_models.ps1" -Value $content
}


# SD-Trainer Installer 设置脚本
function Write-SD-Trainer-Installer-Settings-Script {
    $content = "
# SD-Trainer Installer 版本和检查更新间隔
`$SD_TRAINER_INSTALLER_VERSION = $SD_TRAINER_INSTALLER_VERSION
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
`$Env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$Env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"



# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
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


# 获取 SD-Trainer Installer 自动检测更新设置
function Get-SD-Trainer-Installer-Auto-Check-Update-Setting {
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


# Pip 镜像源配置
function Get-Pip-Mirror-Setting {
    if (!(Test-Path `"`$PSScriptRoot/disable_pip_mirror.txt`")) {
        return `"启用`"
    } else {
        return `"禁用`"
    }
}


# 获取用户输入
function Get-User-Input {
    return Read-Host `"===========================================>`"
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


# SD-Trainer Installer 自动检查更新设置
function Update-SD-Trainer-Installer-Auto-Check-Update-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 SD-Trainer Installer 自动检测更新设置: `$(Get-SD-Trainer-Installer-Auto-Check-Update-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用 SD-Trainer Installer 自动更新检查`"
        Print-Msg `"2. 禁用 SD-Trainer Installer 自动更新检查`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Remove-Item -Path `"`$PSScriptRoot/disable_update.txt`" 2> `$null
                Print-Msg `"启用 SD-Trainer Installer 自动更新检查成功`"
                break
            }
            2 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/disable_update.txt`" -Force > `$null
                Print-Msg `"禁用 SD-Trainer Installer 自动更新检查成功`"
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


# SD-Trainer 启动参数设置
function Update-SD-Trainer-Launch-Args-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前 SD-Trainer 启动参数: `$(Get-Launch-Args-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 设置 SD-Trainer 启动参数`"
        Print-Msg `"2. 删除 SD-Trainer 启动参数`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                Print-Msg `"请输入 SD-Trainer 启动参数`"
                Print-Msg `"提示: SD-Trainer 可用的启动参数可阅读: https://github.com/Akegarasu/lora-scripts?tab=readme-ov-file#program-arguments`"
                Print-Msg `"输入启动参数后回车保存`"
                `$sd_trainer_launch_args = Get-User-Input
                Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/launch_args.txt`" -Value `$sd_trainer_launch_args
                Print-Msg `"设置 SD-Trainer 启动参数成功, 使用的 SD-Trainer 启动参数为: `$sd_trainer_launch_args`"
                break
            }
            2 {
                Remove-Item -Path `"`$PSScriptRoot/launch_args.txt`" 2> `$null
                Print-Msg `"删除 SD-Trainer 启动参数成功`"
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


# 自动创建 SD-Trainer 快捷启动方式设置
function Auto-Set-Launch-Shortcut-Setting {
    while (`$true) {
        `$go_to = 0
        Print-Msg `"当前自动创建 SD-Trainer 快捷启动方式设置: `$(Get-Auto-Set-Launch-Shortcut-Setting)`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 启用自动创建 SD-Trainer 快捷启动方式`"
        Print-Msg `"2. 禁用自动创建 SD-Trainer 快捷启动方式`"
        Print-Msg `"3. 返回`"
        Print-Msg `"提示: 输入数字后回车`"

        `$arg = Get-User-Input

        switch (`$arg) {
            1 {
                New-Item -ItemType File -Path `"`$PSScriptRoot/enable_shortcut.txt`" -Force > `$null
                Print-Msg `"启用自动创建 SD-Trainer 快捷启动方式成功`"
                break
            }
            2 {
                Remove-Item -Path `"`$PSScriptRoot/enable_shortcut.txt`" 2> `$null
                Print-Msg `"禁用自动创建 SD-Trainer 快捷启动方式成功`"
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
        Print-Msg `"当前Pip 镜像源设置: `$(Get-Pip-Mirror-Setting)`"
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


# 检查 SD-Trainer Installer 更新
function Check-SD-Trainer-Installer-Update {
    # 可用的下载源
    `$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1`")
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    Set-Content -Encoding UTF8 -Path `"`$PSScriptRoot/update_time.txt`" -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间
    ForEach (`$url in `$urls) {
        Print-Msg `"检查 SD-Trainer Installer 更新中`"
        Invoke-WebRequest -Uri `$url -OutFile `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`"
        if (`$?) {
            `$latest_version = [int]`$(Get-Content `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" | Select-String -Pattern `"SD_TRAINER_INSTALLER_VERSION`" | ForEach-Object { `$_.ToString() })[0].Split(`"=`")[1].Trim()
            if (`$latest_version -gt `$SD_TRAINER_INSTALLER_VERSION) {
                New-Item -ItemType File -Path `"`$PSScriptRoot/use_update_mode.txt`" -Force > `$null
                Print-Msg `"SD-Trainer Installer 有新版本可用`"
                Print-Msg `"调用 SD-Trainer Installer 进行更新中`"
                `$folder_name = Split-Path `$PSScriptRoot -Leaf
                if (!(`$folder_name -eq `"SD-Trainer`")) { # 检测脚本所在文件夹是否符合要求
                    Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                    Remove-Item -Path `"`$PSScriptRoot/update_time.txt`" 2> `$null
                    Print-Msg `"检测到 SD-Trainer Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                    Print-Msg `"当前 SD-Trainer Installer 管理脚本所在文件夹名称: `$folder_name`"
                    Print-Msg `"请前往 `$(Split-Path `"`$PSScriptRoot`") 路径, 将名称为 `$folder_name 的文件夹改名为 SD-Trainer, 再重新更新 SD-Trainer Installer 管理脚本`"
                    Print-Msg `"终止 SD-Trainer Installer 的更新`"
                    return
                }
                Move-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" `"`$PSScriptRoot/../sd_trainer_installer.ps1`" -Force
                powershell `"`$PSScriptRoot/../sd_trainer_installer.ps1`"
                Print-Msg `"更新结束, 需重新启动 SD-Trainer Installer 管理脚本以应用更新, 回车退出 SD-Trainer Installer 管理脚本`"
                Read-Host | Out-Null
                exit 0
            } else {
                Remove-Item -Path `"`$PSScriptRoot/use_update_mode.txt`" 2> `$null
                Remove-Item -Path `"`$PSScriptRoot/cache/sd_trainer_installer.ps1`" 2> `$null
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

    if (Test-Path `"`$PSScriptRoot/lora-scripts/gui.py`") {
        `$sd_trainer_status = `"已安装`"
    } else {
        `$sd_trainer_status = `"未安装`"
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
    Print-Msg `"SD-Trainer: `$sd_trainer_status`"
    Print-Msg `"-----------------------------------------------------`"
    if (`$broken -eq 1) {
        Print-Msg `"检测到环境出现组件缺失, 可尝试运行 SD-Trainer Installer 进行安装`"
    } else {
        Print-Msg `"当前环境无缺失组件`"
    }
}


# 查看 SD-Trainer Installer 文档
function Get-SD-Trainer-Installer-Help-Docs {
    Print-Msg `"调用浏览器打开 SD-Trainer Installer 文档中`"
    Start-Process `"https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md`"
}


function Main {
    Print-Msg `"初始化中`"
    Print-Msg `"SD-Trainer Installer 版本: v`$SD_TRAINER_INSTALLER_VERSION`"
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
        Print-Msg `"SD-Trainer Installer 自动检查更新: `$(Get-SD-Trainer-Installer-Auto-Check-Update-Setting)`"
        Print-Msg `"SD-Trainer 启动参数: `$(Get-Launch-Args-Setting)`"
        Print-Msg `"自动创建 SD-Trainer 快捷启动方式设置: `$(Get-Auto-Set-Launch-Shortcut-Setting)`"
        Print-Msg `"Pip 镜像源设置: `$(Get-Pip-Mirror-Setting)`"
        Print-Msg `"-----------------------------------------------------`"
        Print-Msg `"可选操作:`"
        Print-Msg `"1. 进入代理设置`"
        Print-Msg `"2. 进入 Python 包管理器设置`"
        Print-Msg `"3. 进入 HuggingFace 镜像源设置`"
        Print-Msg `"4. 进入 Github 镜像源设置`"
        Print-Msg `"5. 进入 SD-Trainer Installer 自动检查更新设置`"
        Print-Msg `"6. 进入 SD-Trainer 启动参数设置`"
        Print-Msg `"7. 进入自动创建 SD-Trainer 快捷启动方式设置`"
        Print-Msg `"8. 进入 Pip 镜像源设置`"
        Print-Msg `"9. 更新 SD-Trainer Installer 管理脚本`"
        Print-Msg `"10. 检查环境完整性`"
        Print-Msg `"11. 查看 SD-Trainer Installer 文档`"
        Print-Msg `"12. 退出 SD-Trainer Installer 设置`"
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
                Update-SD-Trainer-Installer-Auto-Check-Update-Setting
                break
            }
            6 {
                Update-SD-Trainer-Launch-Args-Setting
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
                Check-SD-Trainer-Installer-Update
                break
            }
            10 {
                Check-Env
                break
            }
            11 {
                Get-SD-Trainer-Installer-Help-Docs
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
            Print-Msg `"退出 SD-Trainer Installer 设置`"
            break
        }
    }
}

###################

Main
Read-Host | Out-Null
"

    if (Test-Path "$PSScriptRoot/SD-Trainer/settings.ps1") {
        Print-Msg "更新 settings.ps1 中"
    } else {
        Print-Msg "生成 settings.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/settings.ps1" -Value $content
}

# 虚拟环境激活脚本
function Write-Env-Activate-Script {
    $content = "
# SD-Trainer Installer 版本和检查更新间隔
`$Env:SD_TRAINER_INSTALLER_VERSION = $SD_TRAINER_INSTALLER_VERSION
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
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
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
            if (`$latest_version -gt `$Env:SD_TRAINER_INSTALLER_VERSION) {
                New-Item -ItemType File -Path `"`$Env:CACHE_HOME/../use_update_mode.txt`" -Force > `$null
                Print-Msg `"SD-Trainer Installer 有新版本可用`"
                Print-Msg `"调用 SD-Trainer Installer 进行更新中`"
                `$folder_name = Split-Path `$Env:CACHE_HOME/.. -Leaf
                if (!(`$folder_name -eq `"SD-Trainer`")) { # 检测脚本所在文件夹是否符合要求
                    Remove-Item -Path `"`$Env:CACHE_HOME/../cache/sd_trainer_installer.ps1`" 2> `$null
                    Remove-Item -Path `"`$Env:CACHE_HOME/../use_update_mode.txt`" 2> `$null
                    Remove-Item -Path `"`$Env:CACHE_HOME/../update_time.txt`" 2> `$null
                    Print-Msg `"检测到 SD-Trainer Installer 管理脚本所在文件夹名称不符合要求, 无法直接进行更新`"
                    Print-Msg `"当前 SD-Trainer Installer 管理脚本所在文件夹名称: `$folder_name`"
                    Print-Msg `"请前往 `$(Split-Path `"`$(Split-Path `"`$Env:CACHE_HOME`")`") 路径, 将名称为 `$folder_name 的文件夹改名为 SD-Trainer, 再重新更新 SD-Trainer Installer 管理脚本`"
                    Print-Msg `"终止 SD-Trainer Installer 的更新`"
                    return
                }
                Move-Item -Path `"`$Env:CACHE_HOME/sd_trainer_installer.ps1`" `"`$Env:CACHE_HOME/../../sd_trainer_installer.ps1`" -Force
                powershell `"`$Env:CACHE_HOME/../../sd_trainer_installer.ps1`"
                Print-Msg `"更新结束, 需重新启动 SD-Trainer Installer 管理脚本以应用更新, 回车退出 SD-Trainer Installer 管理脚本`"
                Read-Host | Out-Null
                exit 0
            } else {
                Remove-Item -Path `"`$Env:CACHE_HOME/../use_update_mode.txt`" 2> `$null
                Remove-Item -Path `"`$Env:CACHE_HOME/sd_trainer_installer.ps1`" 2> `$null
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
    Print-Msg `"SD-Trainer Installer 版本: v`$Env:SD_TRAINER_INSTALLER_VERSION`"
    Set-Proxy
    Set-HuggingFace-Mirror
    Set-Github-Mirror
    Pip-Mirror-Status
    Print-Msg `"激活 SD-Trainer Env`"
    Print-Msg `"更多帮助信息可在 SD-Trainer Installer 项目地址查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md`"
}

###################

Main
"

    if (Test-Path "$PSScriptRoot/SD-Trainer/activate.ps1") {
        Print-Msg "更新 activate.ps1 中"
    } else {
        Print-Msg "生成 activate.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/activate.ps1" -Value $content
}


# 快捷启动终端脚本, 启动后将自动运行环境激活脚本
function Write-Launch-Terminal-Script {
    $content = "
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
}

Print-Msg `"执行 SD-Trainer Installer 激活环境脚本`"
powershell -NoExit -File `"`$PSScriptRoot/activate.ps1`"
"

    if (Test-Path "$PSScriptRoot/SD-Trainer/terminal.ps1") {
        Print-Msg "更新 terminal.ps1 中"
    } else {
        Print-Msg "生成 terminal.ps1 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/terminal.ps1" -Value $content
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
settings.ps1：管理 SD-Trainer Installer 的设置。
terminal.ps1：启动 PowerShell 终端并自动激活虚拟环境，激活虚拟环境后即可使用 Python、Pip、Git 的命令。
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

SD-Trainer Installer 提供了配置管理器, 运行 settings.ps1 即可管理各个配置。

SD-Trainer Installer 的管理脚本在启动时会检查管理脚本的更新，如果有更新将会提示并显示具体的更新方法，如果要禁用更新，可以在脚本同级的目录创建 disable_update.txt 文件，这将禁用 SD-Trainer Installer 更新检查。

更多详细的帮助可在下面的链接查看。
SD-Trainer Installer 使用帮助：https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md
SD-Trainer 项目地址：https://github.com/Akegarasu/lora-scripts

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

    if (Test-Path "$PSScriptRoot/SD-Trainer/help.txt") {
        Print-Msg "更新 help.txt 中"
    } else {
        Print-Msg "生成 help.txt 中"
    }
    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/help.txt" -Value $content
}


# 写入管理脚本和文档
function Write-Manager-Scripts {
    Write-Launch-Script
    Write-Update-Script
    Write-SD-Trainer-Install-Script
    Write-PyTorch-ReInstall-Script
    Write-Download-Model-Script
    Write-SD-Trainer-Installer-Settings-Script
    Write-Env-Activate-Script
    Write-Launch-Terminal-Script
    Write-ReadMe
}


# 执行安装
function Use-Install-Mode {
    Set-Proxy
    Set-uv
    Pip-Mirror-Status
    Print-Msg "启动 SD-Trainer 安装程序"
    Print-Msg "提示: 若出现某个步骤执行失败, 可尝试再次运行 SD-Trainer Installer, 更多的说明请阅读 SD-Trainer Installer 使用文档"
    Print-Msg "SD-Trainer Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md"
    Print-Msg "即将进行安装的路径: $PSScriptRoot\SD-Trainer"
    Check-Install
    Print-Msg "添加管理脚本和文档中"
    Write-Manager-Scripts
    Print-Msg "SD-Trainer 安装结束, 安装路径为: $PSScriptRoot\SD-Trainer"
    Print-Msg "帮助文档可在 SD-Trainer 文件夹中查看, 双击 help.txt 文件即可查看, 更多的说明请阅读 SD-Trainer Installer 使用文档"
    Print-Msg "SD-Trainer Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md"
    Print-Msg "退出 SD-Trainer Installer"
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
    Print-Msg "SD-Trainer Installer 版本: v$SD_TRAINER_INSTALLER_VERSION"
    if (Test-Path "$PSScriptRoot/SD-Trainer/use_update_mode.txt") {
        Print-Msg "使用更新模式"
        Remove-Item -Path "$PSScriptRoot/SD-Trainer/use_update_mode.txt" 2> $null
        Set-Content -Encoding UTF8 -Path "$PSScriptRoot/SD-Trainer/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
        Use-Update-Mode
    } else {
        Print-Msg "使用安装模式"
        Use-Install-Mode
    }
}


###################


Main