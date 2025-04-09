# PyPI 镜像源
$PIP_INDEX_MIRROR = "https://mirrors.cloud.tencent.com/pypi/simple"
$PIP_EXTRA_INDEX_MIRROR = "https://mirrors.cernet.edu.cn/pypi/web/simple"
$PIP_FIND_MIRROR = "https://mirror.sjtu.edu.cn/pytorch-wheels/torch_stable.html"
# PATH
$PYTHON_PATH = "$PSScriptRoot/python"
$PYTHON_SCRIPTS_PATH = "$PSScriptRoot/python/Scripts"
$Env:PATH = "$PYTHON_PATH$([System.IO.Path]::PathSeparator)$PYTHON_SCRIPTS_PATH$([System.IO.Path]::PathSeparator)$Env:PATH"
# 环境变量
$Env:PIP_INDEX_URL = $PIP_INDEX_MIRROR
$Env:PIP_EXTRA_INDEX_URL = $PIP_EXTRA_INDEX_MIRROR
$Env:PIP_FIND_LINKS = $PIP_FIND_MIRROR
$Env:PIP_DISABLE_PIP_VERSION_CHECK = 1
$Env:PIP_NO_WARN_SCRIPT_LOCATION = 0
$Env:PIP_TIMEOUT = 30
$Env:PIP_RETRIES = 5
$Env:PYTHONUTF8 = 1
$Env:PYTHONIOENCODING = "utf8"
$Env:UV_DEFAULT_INDEX = $PIP_INDEX_MIRROR
$Env:UV_INDEX = $PIP_EXTRA_INDEX_MIRROR
$Env:UV_FIND_LINKS = $PIP_FIND_MIRROR
$Env:UV_LINK_MODE = "copy"
$Env:UV_HTTP_TIMEOUT = 30
$Env:UV_CONCURRENT_DOWNLOADS = 50
$Env:UV_INDEX_STRATEGY = "unsafe-best-match"
$Env:CACHE_HOME = "$PSScriptRoot/cache"
$Env:HF_HOME = "$PSScriptRoot/python/cache/huggingface"
$Env:MATPLOTLIBRC = "$PSScriptRoot/cache"
$Env:MODELSCOPE_CACHE = "$PSScriptRoot/python/cache/modelscope/hub"
$Env:MS_CACHE_HOME = "$PSScriptRoot/python/cache/modelscope/hub"
$Env:SYCL_CACHE_DIR = "$PSScriptRoot/python/cache/libsycl_cache"
$Env:TORCH_HOME = "$PSScriptRoot/python/cache/torch"
$Env:U2NET_HOME = "$PSScriptRoot/python/cache/u2net"
$Env:XDG_CACHE_HOME = "$PSScriptRoot/cache"
$Env:PIP_CACHE_DIR = "$PSScriptRoot/python/cache/pip"
$Env:PYTHONPYCACHEPREFIX = "$PSScriptRoot/python/cache/pycache"
$Env:UV_CACHE_DIR = "$PSScriptRoot/python/cache/uv"
$Env:UV_PYTHON = "$PSScriptRoot/python/python.exe"



# 消息输出
function Print-Msg ($msg) {
    Write-Host "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")]" -ForegroundColor Yellow -NoNewline
    Write-Host "[Embed Python Installer]" -ForegroundColor Cyan -NoNewline
    Write-Host ":: " -ForegroundColor Blue -NoNewline
    Write-Host "$msg"
}


# 下载并解压 Python
function Install-Python {
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/python-3.10.11-embed-amd64.zip"

    # 下载 Python
    Print-Msg "正在下载 Python"
    Invoke-WebRequest -Uri $url -OutFile "$PSScriptRoot/python/cache/python-3.10.11-embed-amd64.zip"
    if ($?) { # 检测是否下载成功并解压
        Print-Msg "正在解压 Python"
        Expand-Archive -Path "$PSScriptRoot/python/cache/python-3.10.11-embed-amd64.zip" -DestinationPath "$PSScriptRoot/python" -Force
        Remove-Item -Path "$PSScriptRoot/python/cache/python-3.10.11-embed-amd64.zip"
        Modify-PythonPath
        Print-Msg "Python 安装成功"
    } else {
        Print-Msg "Python 安装失败, 可重新运行安装脚本重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 修改 python310._pth 文件的内容
function Modify-PythonPath {
    Print-Msg "修改 python310._pth 文件内容"
    $content = @("python310.zip", ".", "", "# Uncomment to run site.main() automatically", "import site")
    Set-Content -Path "$PSScriptRoot/python/python310._pth" -Value $content
}


# 配置 Python 的 Pip 模块
function Install-Pip {
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/get-pip.py"

    # 下载 get-pip.py
    Print-Msg "正在下载 get-pip.py"
    Invoke-WebRequest -Uri $url -OutFile "$PSScriptRoot/python/cache/get-pip.py"
    if ($?) { # 检测是否下载成功
        # 执行 get-pip.py
        Print-Msg "通过 get-pip.py 安装 Pip 中"
        python "$PSScriptRoot/python/cache/get-pip.py"
        if ($?) { # 检测是否安装成功
            Remove-Item -Path "$PSScriptRoot/python/cache/get-pip.py"
            Print-Msg "Pip 安装成功"
        } else {
            Remove-Item -Path "$PSScriptRoot/python/cache/get-pip.py"
            Print-Msg "Pip 安装失败, 可重新运行安装脚本重试失败的安装"
            Read-Host | Out-Null
            exit 1
        }
    } else {
        Print-Msg "下载 get-pip.py 失败"
        Print-Msg "Pip 安装失败, 可重新运行安装脚本重试失败的安装"
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
        Print-Msg "uv 下载失败, 可重新运行安装脚本重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 虚拟环境激活脚本
function Write-Env-Activate-Script {
    $content = "
# PyPI 镜像源
`$PIP_INDEX_MIRROR = `"$PIP_INDEX_MIRROR`"
`$PIP_EXTRA_INDEX_MIRROR = `"$PIP_EXTRA_INDEX_MIRROR`"
`$PIP_FIND_MIRROR = `"$PIP_FIND_MIRROR`"
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/Scripts`"
`$Env:PATH = `"`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$Env:PATH`"
# 环境变量
`$Env:PIP_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
`$Env:PIP_EXTRA_INDEX_URL = `"`$PIP_EXTRA_INDEX_MIRROR`"
`$Env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_DEFAULT_INDEX = `"`$PIP_INDEX_MIRROR`"
`$Env:UV_INDEX = `"`$PIP_EXTRA_INDEX_MIRROR`"
`$Env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$Env:UV_LINK_MODE = `"copy`"
`$Env:UV_HTTP_TIMEOUT = 30
`$Env:UV_CONCURRENT_DOWNLOADS = 50
`$Env:UV_INDEX_STRATEGY = `"unsafe-best-match`"
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
`$Env:UV_PYTHON = `"`$PSScriptRoot/python.exe`"



# 提示信息
function global:prompt {
    `"`$(Write-Host `"[Env]`" -ForegroundColor Green -NoNewLine) `$(Get-Location)> `"
}


# 消息输出
function global:Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[Embed Python Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
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
    Set-Proxy
    Set-HuggingFace-Mirror
    Print-Msg `"激活 Env`"
}

###################

Main
"

    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/python/activate.ps1" -Value $content
}


# 快捷启动终端脚本, 启动后将自动运行环境激活脚本
function Write-Launch-Terminal-Script {
    $content = "
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")]`" -ForegroundColor Yellow -NoNewline
    Write-Host `"[Embed Python Installer]`" -ForegroundColor Cyan -NoNewline
    Write-Host `":: `" -ForegroundColor Blue -NoNewline
    Write-Host `"`$msg`"
}

Print-Msg `"执行激活环境脚本`"
powershell -NoExit -File `"`$PSScriptRoot/activate.ps1`"
"

    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/python/terminal.ps1" -Value $content
}


function Main {
    Print-Msg "初始化中"
    Print-Msg "即将安装 Embed Python 的路径: $PSScriptRoot\python"
    Print-Msg "提示: 提示: 若出现某个步骤执行失败, 可尝试再次运行 Embed Python 安装脚本"

    if (!(Test-Path "$PSScriptRoot/python")) {
        New-Item -ItemType Directory -Force -Path "$PSScriptRoot/python" > $null
    }
    if (!(Test-Path "$PSScriptRoot/python/cache")) {
        New-Item -ItemType Directory -Force -Path "$PSScriptRoot/python/cache" > $null
    }

    Print-Msg "检测是否安装 Python"
    if (Test-Path "$PSScriptRoot/python/python.exe") {
        Print-Msg "Python 已安装"
    } else {
        Print-Msg "Python 未安装"
        Install-Python
    }
    
    Print-Msg "检查是否安装 Pip"
    python -c "import pip" 2> $null
    if ($?) {
        Print-Msg "Pip 已安装"
    } else {
        Print-Msg "Pip 未安装"
        Install-Pip
    }

    Print-Msg "检测是否安装 uv"
    python -m pip show uv --quiet 2> $null
    if ($?) {
        Print-Msg "uv 已安装"
    } else {
        Print-Msg "uv 未安装"
        Install-uv
    }

    Write-Env-Activate-Script
    Write-Launch-Terminal-Script
    Print-Msg "安装 Embed Python 结束, 安装路径为: $PSScriptRoot\python"
    Print-Msg "$PSScriptRoot\python 目录中内置 terminal.ps1 脚本, 运行后将自动打开 PowerShell 进入 Embed Python 的环境, 或者手动打开 PowerShell 运行 activate.ps1 激活环境"
    Print-Msg "退出 Embed Python 安装脚本"
}

#################

Main
Read-Host | Out-Null