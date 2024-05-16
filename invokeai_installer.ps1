# 环境变量
$env:PIP_INDEX_URL = "https://mirror.baidu.com/pypi/simple"
$env:PIP_EXTRA_INDEX_URL="https://mirrors.bfsu.edu.cn/pypi/web/simple"
$env:PIP_FIND_LINKS="https://mirror.sjtu.edu.cn/pytorch-wheels/torch_stable.html"
$env:PIP_DISABLE_PIP_VERSION_CHECK = 1
$env:CACHE_HOME="./InvokeAI/cache"
$env:HF_HOME="./InvokeAI/cache/huggingface"
$env:MATPLOTLIBRC="./InvokeAI/cache"
$env:MODELSCOPE_CACHE="./InvokeAI/cache/modelscope/hub"
$env:MS_CACHE_HOME="./InvokeAI/cache/modelscope/hub"
$env:SYCL_CACHE_DIR="./InvokeAI/cache/libsycl_cache"
$env:TORCH_HOME="./InvokeAI/cache/torch"
$env:U2NET_HOME="./InvokeAI/cache/u2net"
$env:XDG_CACHE_HOME="./InvokeAI/cache"
$env:PIP_CACHE_DIR="./InvokeAI/cache/pip"
$env:PYTHONPYCACHEPREFIX="./InvokeAI/cache/pycache"

# 消息输出
function Print-Msg ($msg){
    Write-Host "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")][InvokeAI-Installer]:: $msg"
}


# 修改python310._pth文件的内容
function Modify-PythonPath {
    Print-Msg "修改 python310._pth 文件内容"
    $content = @("python310.zip", ".", "", "# Uncomment to run site.main() automatically", "import site")
    Set-Content -Path "./InvokeAI/python/python310._pth" -Value $content
}


# 下载并解压python
function Install-Python {
    $url = "https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/python-3.10.11-embed-amd64.zip"
    # $url = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip"

    # 下载python
    Print-Msg "正在下载 Python"
    Invoke-WebRequest -Uri $url -OutFile "./InvokeAI/python-3.10.11-embed-amd64.zip"
    if ($?){ # 检测是否下载成功并解压
        # 创建python文件夹
        if (Test-Path "./InvokeAI/python"){}else{
            New-Item -ItemType Directory -Force -Path ./InvokeAI/python > $null
        }
        # 解压python
        Print-Msg "正在解压 Python"
        Expand-Archive -Path "./InvokeAI/python-3.10.11-embed-amd64.zip" -DestinationPath "./InvokeAI/python"
        Remove-Item -Path "./InvokeAI/python-3.10.11-embed-amd64.zip"
        Modify-PythonPath
        Print-Msg "Python 安装成功"
    }else {
        Print-Msg "Python 安装失败, 终止 InvokeAI 安装进程"
        pause
        exit 1
    }
}


# 配置python的pip模块
function Install-Pip {
    $url = "https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/get-pip.py"
    # $url = "https://bootstrap.pypa.io/get-pip.py"

    # 下载get-pip.py
    Print-Msg "正在下载 get-pip.py"
    Invoke-WebRequest -Uri $url -OutFile "./InvokeAI/get-pip.py"
    if ($?){ # 检测是否下载成功
        # 执行get-pip.py
        Print-Msg "通过 get-pip.py 安装 Pip 中"
        ./InvokeAI/python/python.exe ./InvokeAI/get-pip.py --no-warn-script-location
        if ($?){ # 检测是否安装成功
            Remove-Item -Path "./InvokeAI/get-pip.py"
            Print-Msg "Pip 安装成功"
        }else {
            Remove-Item -Path "./InvokeAI/get-pip.py"
            Print-Msg "Pip 安装失败, 终止 InvokeAI 安装进程"
            pause
            exit 1
        }
    }else {
        Print-Msg "下载 get-pip.py 失败"
        Print-Msg "Pip 安装失败, 终止 InvokeAI 安装进程"
        pause
        exit 1
    }
}


# 安装invokeai
function Install-InvokeAI {
    # 下载InvokeAI
    Print-Msg "正在下载 InvokeAI"
    ./InvokeAI/python/python.exe -m pip install "InvokeAI[xformers]"  --no-warn-script-location --use-pep517
    if ($?){ # 检测是否下载成功
        Print-Msg "InvokeAI 安装成功"
    }else {
        Print-Msg "InvokeAI 安装失败, 终止 InvokeAI 安装进程"
        pause
        exit 1
    }
}


# 重装xformers
function Reinstall-Xformers {
    $env:PIP_EXTRA_INDEX_URL="https://mirror.sjtu.edu.cn/pytorch-wheels/cu121"
    $env:PIP_FIND_LINKS="https://mirror.sjtu.edu.cn/pytorch-wheels/cu121/torch_stable.html"
    $pip_cmd = "$PSScriptRoot/InvokeAI/python/pip.exe"
    $xformers_pkg = $(./InvokeAI/python/Scripts/pip.exe freeze | Select-String -Pattern "xformers") # 检测是否安装了xformers
    $xformers_pkg_cu118 = $xformers_pkg | Select-String -Pattern "cu118" # 检查是否版本为cu118的

    if (Test-Path "./InvokeAI/cache/xformers.txt"){
        # 读取xformers.txt文件的内容
        Print-Msg "读取上次的 xFormers 版本记录"
        $xformers_ver = Get-Content "./InvokeAI/cache/xformers.txt"
    }

    if ($xformers_ver) { # 本地存在版本记录（上次安装xformers喂未完成）
        Print-Msg "安装: $xformers_ver"
        ./InvokeAI/python/python.exe -m pip uninstall xformers -y
        ./InvokeAI/python/python.exe -m pip install $xformers_ver --no-warn-script-location --no-cache-dir
        if ($?){
            Remove-Item -Path "./InvokeAI/cache/xformers.txt"
            Print-Msg "重装 xFormers 成功"
        }else {
            Print-Msg "重装 xFormers 失败, 这可能导致使用 InvokeAI 时显存占用率增大"
        }
    }elseif ($xformers_pkg){ # 已安装了xformers
        if ($xformers_pkg_cu118){ # 确认xformers是否为cu118的版本
            Print-Msg "检测到已安装的 xFormers 为 CU118 的版本, 将进行重装"
            $xformers_pkg = $xformers_pkg.ToString().Split("+")[0]
            $xformers_pkg > ./InvokeAI/cache/xformers.txt # 将版本信息存在本地，用于安装失败时恢复
            ./InvokeAI/python/python.exe -m pip uninstall xformers -y
            ./InvokeAI/python/python.exe -m pip install $xformers_pkg --no-warn-script-location --no-cache-dir
            if ($?){
                Remove-Item -Path "./InvokeAI/cache/xformers.txt"
                Print-Msg "重装 xFormers 成功"
            }else {
                Print-Msg "重装 xFormers 失败, 这可能导致使用 InvokeAI 时显存占用率增大"
            }
        }else{
            Print-Msg "无需重装 xFormers"
        }
    }else{
        Print-Msg "未安装 xFormers, 尝试安装中"
        ./InvokeAI/python/python.exe -m pip install xformers --no-warn-script-location --no-cache-dir
        if ($?){ # 检测是否下载成功
            Print-Msg "重装 xFormers 成功"
        }else {
            Print-Msg "重装 xFormers 失败, 这可能导致使用 InvokeAI 时显存占用率增大"
        }
    }
}


# 下载pypatchmatch
function Install-PyPatchMatch {
    # PyPatchMatch
    # https://github.com/invoke-ai/PyPatchMatch/releases/download/0.1.1/libpatchmatch_windows_amd64.dll
    # https://github.com/invoke-ai/PyPatchMatch/releases/download/0.1.1/opencv_world460.dll
    $url_1 = "https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/libpatchmatch_windows_amd64.dll"
    $url_2 = "https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/opencv_world460.dll"

    if (Test-Path "./InvokeAI/python/Lib/site-packages/patchmatch/libpatchmatch_windows_amd64.dll"){
        Print-Msg "下载 libpatchmatch_windows_amd64.dll 中"
        Invoke-WebRequest -Uri $url_1 -OutFile "./InvokeAI/python/Lib/site-packages/patchmatch/libpatchmatch_windows_amd64.dll"
        if ($?){
            Print-Msg "下载 libpatchmatch_windows_amd64.dll 成功"
        }else {
            Print-Msg "下载 libpatchmatch_windows_amd64.dll 失败"
        }
    }

    if (Test-Path "./InvokeAI/python/Lib/site-packages/patchmatch/opencv_world460.dll"){
        Print-Msg "下载 opencv_world460.dll 中"
        Invoke-WebRequest -Uri $url_2 -OutFile "./InvokeAI/python/Lib/site-packages/patchmatch/opencv_world460.dll"
        if ($?){
            Print-Msg "下载 opencv_world460.dll 成功"
        }else {
            Print-Msg "下载 opencv_world460.dll 失败"
        }
    }
}
# 安装
function Check-Install {
    if (Test-Path "./InvokeAI"){}else{
        New-Item -ItemType Directory -Path "./InvokeAI" > $null
    }
    Print-Msg "检测是否安装了 Python"
    $pythonPath = "./InvokeAI/python/python.exe"
    if (Test-Path $pythonPath) {
        Print-Msg "Python 已安装"
    }else {
        Print-Msg "Python 未安装"
        Install-Python
    }

    Print-Msg "检查是否安装 Pip"
    $pipPath = "./InvokeAI/python/Scripts/pip.exe"
    if (Test-Path $pipPath) {
        Print-Msg "Pip 已安装"
    }else {
        Print-Msg "Pip 未安装"
        Install-Pip
    }

    Print-Msg "检查是否安装 InvokeAI"
    $invokeaiPath = "./InvokeAI/python/Scripts/invokeai-web.exe"
    if (Test-Path $invokeaiPath) {
        Print-Msg "InvokeAI 已安装"
    }else {
        Print-Msg "InvokeAI 未安装"
        Install-InvokeAI
    }

    Print-Msg "检测是否需要重装 xFormers"
    Reinstall-Xformers

    Print-Msg "检测是否需要安装 PyPatchMatch"
    Install-PyPatchMatch
}


# 启动脚本
function Write-Launch-Script {
    $content = "
function Print-Msg (`$msg){
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI-Installer]:: `$msg`"
}
`$env:PIP_INDEX_URL = `"https://mirror.baidu.com/pypi/simple`"
`$env:PIP_FIND_LINKS = `"https://mirror.sjtu.edu.cn/pytorch-wheels/torch_stable.html`"
`$env:HF_ENDPOINT = `"https://hf-mirror.com`" # Huggingface 镜像源, 当不使用这个镜像源时可以注释掉
`$env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$env:CACHE_HOME = `"./invokeai/cache`"
`$env:HF_HOME = `"./invokeai/cache/huggingface`"
`$env:MATPLOTLIBRC = `"./invokeai/cache`"
`$env:MODELSCOPE_CACHE = `"./invokeai/cache/modelscope/hub`"
`$env:MS_CACHE_HOME = `"./invokeai/cache/modelscope/hub`"
`$env:SYCL_CACHE_DIR = `"./invokeai/cache/libsycl_cache`"
`$env:TORCH_HOME = `"./invokeai/cache/torch`"
`$env:U2NET_HOME = `"./invokeai/cache/u2net`"
`$env:XDG_CACHE_HOME = `"./invokeai/cache`"
`$env:PIP_CACHE_DIR = `"./invokeai/cache/pip`"
`$env:PYTHONPYCACHEPREFIX = `"./invokeai/cache/pycache`"
Print-Msg `"启动 InvokeAI 中`"
./python/Scripts/invokeai-web.exe --root invokeai
pause
    "

    Set-Content -Path "./InvokeAI/launch.ps1" -Value $content
}


# 更新脚本
function Write-Update-Script {
    $content = "
function Print-Msg (`$msg){
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI-Installer]:: `$msg`"
}
`$env:PIP_INDEX_URL = `"https://mirror.baidu.com/pypi/simple`"
`$env:PIP_FIND_LINKS = `"https://mirror.sjtu.edu.cn/pytorch-wheels/torch_stable.html`"
`$env:HF_ENDPOINT = `"https://hf-mirror.com`" # Huggingface 镜像源, 当不使用这个镜像源时可以注释掉
`$env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$env:CACHE_HOME = `"./invokeai/cache`"
`$env:HF_HOME = `"./invokeai/cache/huggingface`"
`$env:MATPLOTLIBRC = `"./invokeai/cache`"
`$env:MODELSCOPE_CACHE = `"./invokeai/cache/modelscope/hub`"
`$env:MS_CACHE_HOME = `"./invokeai/cache/modelscope/hub`"
`$env:SYCL_CACHE_DIR = `"./invokeai/cache/libsycl_cache`"
`$env:TORCH_HOME = `"./invokeai/cache/torch`"
`$env:U2NET_HOME = `"./invokeai/cache/u2net`"
`$env:XDG_CACHE_HOME = `"./invokeai/cache`"
`$env:PIP_CACHE_DIR = `"./invokeai/cache/pip`"
`$env:PYTHONPYCACHEPREFIX = `"./invokeai/cache/pycache`"
Print-Msg `"更新 InvokeAI 中`"
./python/Scripts/pip.exe install invokeai --upgrade --no-warn-script-location --use-pep517
Print-Msg `"InvokeAI 更新完成`"
pause
"

    Set-Content -Path "./InvokeAI/update.ps1" -Value $content
}


# 数据库修复
function Write-InvokeAI-DB-Fix-Script {
    $content = "
function Print-Msg (`$msg){
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI-Installer]:: `$msg`"
}
Print-Msg `"修复 InvokeAI 数据库中`"
./python/Scripts/invokeai-db-maintenance.exe --operation all --root invokeai
Print-Msg `"修复 InvokeAI 数据库完成`"
pause
"

    Set-Content -Path "./InvokeAI/fix-db.ps1" -Value $content
}


# 获取安装脚本
function Write-InvokeAI-Install-Script {
    $content = "
function Print-Msg (`$msg){
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI-Installer]:: `$msg`"
}
`$url = `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`"
Print-Msg `":: 正在下载 InvokeAI Installer 脚本`"
Invoke-WebRequest -Uri `$url -OutFile `"../invokeai_installer.ps1`"
if (`$?){
    Print-Msg `":: 下载 InvokeAI Installer 脚本成功`"
}else{
    Print-Msg `":: 下载 InvokeAI Installer 脚本失败`"
}
pause
"

    Set-Content -Path "./InvokeAI/get_invokeai_installer.ps1" -Value $content
}


# 虚拟环境激活脚本
function Write-Env-Activate-Script {
    $content = "
function global:prompt {
    `"`$(Write-Host `"[InvokeAI-Env]`" -ForegroundColor Green -NoNewLine) `$(Get-Location) > `"
}

function Print-Msg (`$msg){
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI-Installer]:: `$msg`"
}

# 环境变量
`$py_path = `"`$PSScriptRoot/python`"
`$py_scripts_path = `"`$PSScriptRoot/python/Scripts`"
`$Env:PATH = `"`$py_path`$([System.IO.Path]::PathSeparator)`$py_scripts_path`$([System.IO.Path]::PathSeparator)`$Env:PATH`" # 将python添加到环境变量
`$env:PIP_INDEX_URL = `"https://mirror.baidu.com/pypi/simple`"
`$env:PIP_FIND_LINKS = `"https://mirror.sjtu.edu.cn/pytorch-wheels/torch_stable.html`"
`$env:HF_ENDPOINT = `"https://hf-mirror.com`" # Huggingface 镜像源, 当不使用这个镜像源时可以注释掉
`$env:CACHE_HOME = `"`$PSScriptRoot/invokeai/cache`"
`$env:HF_HOME = `"`$PSScriptRoot/invokeai/cache/huggingface`"
`$env:MATPLOTLIBRC = `"`$PSScriptRoot/invokeai/cache`"
`$env:MODELSCOPE_CACHE = `"`$PSScriptRoot/invokeai/cache/modelscope/hub`"
`$env:MS_CACHE_HOME = `"`$PSScriptRoot/invokeai/cache/modelscope/hub`"
`$env:SYCL_CACHE_DIR = `"`$PSScriptRoot/invokeai/cache/libsycl_cache`"
`$env:TORCH_HOME = `"`$PSScriptRoot/invokeai/cache/torch`"
`$env:U2NET_HOME = `"`$PSScriptRoot/invokeai/cache/u2net`"
`$env:XDG_CACHE_HOME = `"`$PSScriptRoot/invokeai/cache`"
`$env:PIP_CACHE_DIR = `"`$PSScriptRoot/invokeai/cache/pip`"
`$env:PYTHONPYCACHEPREFIX = `"`$PSScriptRoot/invokeai/cache/pycache`"

Print-Msg `":: 激活 InvokeAI-Env`"
Print-Msg `":: 帮助文档可在 help.txt 文件中查看`"
Print-Msg `":: 更多帮助信息可在项目地址查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md`"
"

    Set-Content -Path "./InvokeAI/activate.ps1" -Value $content
}

# 帮助文档
function Write-ReadMe {
    $content = "
哔哩哔哩：https://space.bilibili.com/46497516
详细的使用帮助：https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md

这是关于 InvokeAI 的使用文档。

使用 InvokeAI Installer 进行安装并安装成功后，将在当前目录生成 InvokeAI 文件夹，以下为文件夹中不同文件 / 文件夹的作用。

cache：缓存文件夹，保存者 Pip / HuggingFace 等缓存文件。
python：Python 的存放路径，InvokeAI 安装的位置在此处，如果需要重装 InvokeAI，可将该文件夹删除，并使用 InvokeAI Installer 重新部署 InvokeAI。请注意，请勿将该 Python 文件夹添加到环境变量，这可能导致不良后果。
invokeai：InvokeAI 存放模型、图片等的文件夹。
activate.ps1：虚拟环境激活脚本，使用该脚本激活虚拟环境，即可使用 InvokeAI。
get_invokeai_installer.ps1：获取最新的 InvokeAI Installer 安装脚本，运行后将会在与 InvokeAI 文件夹同级的目录中生成 invokeai_installer.ps1 安装脚本。
update.ps1：更新 InvokeAI 的脚本，可使用该脚本更新 InvokeAI。
launch.ps1：启动 InvokeAI 的脚本。
fix-db.ps1：修复 InvokeAI 数据库脚本，解决删除 InvokeAI 的图片后在界面中出现无效图片的问题。
help.txt：帮助文档，使用该文件查看帮助文档。

使用 InvokeAI 前，建议阅读下列教程，以更快的了解并掌握使用 InvokeAI 的方法。
给所有想学习AI辅助绘画的人的入门课 By Yuno779：https://docs.qq.com/doc/p/9a03673f4a0493b4cd76babc901a49f0e6d52140

脚本为 InvokeAI 设置了 HuggingFace 镜像源，解决国内无法直接访问 HuggingFace 的问题，导致 InvokeAI 的模型管理无法从 HuggingFace 下载模型。
如果自己有代理，不想使用 HuggingFace 镜像源，可以将 launcher.ps1 中的 `$env:HF_ENDPOINT = `"https://hf-mirror.com`" 这一行注释掉即可。
    "
    Set-Content -Path "./InvokeAI/help.txt" -Value $content
}


# 主程序
function Main {
    Print-Msg "启动 InvokeAI 安装程序"
    Check-Install    
    Print-Msg "添加启动脚本和文档中"
    Write-Launch-Script
    Write-Update-Script
    Write-InvokeAI-DB-Fix-Script
    Write-InvokeAI-Install-Script
    Write-Env-Activate-Script
    Write-ReadMe
    Print-Msg "InvokeAI 安装结束, 安装路径为 $PSScriptRoot\InvokeAI"
    Print-Msg "帮助文档可在 InvokeAI 文件夹中查看, 双击 help.txt 文件即可查看"
}


# 调用主程序
Main

pause
