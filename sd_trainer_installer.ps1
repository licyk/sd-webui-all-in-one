# pip镜像源
$pip_index_mirror = "https://mirrors.cloud.tencent.com/pypi/simple"
$pip_extra_index_mirror = "https://mirror.baidu.com/pypi/simple"
$pip_find_mirror = "https://mirror.sjtu.edu.cn/pytorch-wheels/torch_stable.html"
$pip_extra_index_mirror_cu121 = "https://mirror.sjtu.edu.cn/pytorch-wheels/cu121"
$pip_find_mirror_cu121 = "https://mirror.sjtu.edu.cn/pytorch-wheels/cu121/torch_stable.html"
# github镜像源列表
$github_mirror_list = @(
    "https://mirror.ghproxy.com/https://github.com",
    "https://ghproxy.net/https://github.com",
    "https://gitclone.com/github.com",
    "https://gh-proxy.com/https://github.com",
    "https://ghps.cc/https://github.com",
    "https://gh.idayer.com/https://github.com"
)
# pytorch版本
$pytorch_ver = "torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118"
$xformers_ver = "xformers==0.0.26.post1+cu118"
# 环境变量
$env:PIP_INDEX_URL = $pip_index_mirror
$env:PIP_EXTRA_INDEX_URL = $pip_extra_index_mirror
$env:PIP_FIND_LINKS = $pip_find_mirror
$env:PIP_DISABLE_PIP_VERSION_CHECK = 1
$env:PIP_TIMEOUT = 30
$env:PIP_RETRIES = 5
$env:CACHE_HOME = "$PSScriptRoot/SD-Trainer/cache"
$env:HF_HOME = "$PSScriptRoot/SD-Trainer/cache/huggingface"
$env:MATPLOTLIBRC = "$PSScriptRoot/SD-Trainer/cache"
$env:MODELSCOPE_CACHE = "$PSScriptRoot/SD-Trainer/cache/modelscope/hub"
$env:MS_CACHE_HOME = "$PSScriptRoot/SD-Trainer/cache/modelscope/hub"
$env:SYCL_CACHE_DIR = "$PSScriptRoot/SD-Trainer/cache/libsycl_cache"
$env:TORCH_HOME = "$PSScriptRoot/SD-Trainer/cache/torch"
$env:U2NET_HOME = "$PSScriptRoot/SD-Trainer/cache/u2net"
$env:XDG_CACHE_HOME = "$PSScriptRoot/SD-Trainer/cache"
$env:PIP_CACHE_DIR = "$PSScriptRoot/SD-Trainer/cache/pip"
$env:PYTHONPYCACHEPREFIX = "$PSScriptRoot/SD-Trainer/cache/pycache"



# 消息输出
function Print-Msg ($msg) {
    Write-Host "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")][SD-Trainer Installer]:: $msg"
}

Print-Msg "初始化中"

# 代理配置
$env:NO_PROXY = "localhost,127.0.0.1,::1"
if (!(Test-Path "$PSScriptRoot/disable_proxy.txt")) { # 检测是否禁用自动设置镜像源
    $internet_setting = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    if (Test-Path "$PSScriptRoot/proxy.txt") { # 本地存在代理配置
        $proxy_value = Get-Content "$PSScriptRoot/proxy.txt"
        $env:HTTP_PROXY = $proxy_value
        $env:HTTPS_PROXY = $proxy_value
        Print-Msg "检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理"
    } elseif ($internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        $env:HTTP_PROXY = "http://$($internet_setting.ProxyServer)"
        $env:HTTPS_PROXY = "http://$($internet_setting.ProxyServer)"
        Print-Msg "检测到系统设置了代理, 已读取系统中的代理配置并设置代理"
    }
} else {
    Print-Msg "检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理"
}


# 下载并解压python
function Install-Python {
    $url = "https://modelscope.cn/api/v1/models/licyks/invokeai-core-model/repo?Revision=master&FilePath=pypatchmatch%2Fpython-3.10.11-amd64.zip"

    # 下载python
    Print-Msg "正在下载 Python"
    Invoke-WebRequest -Uri $url -OutFile "./SD-Trainer/python-3.10.11-amd64.zip"
    if ($?) { # 检测是否下载成功并解压
        # 创建python文件夹
        if (!(Test-Path "./SD-Trainer/python")) {
            New-Item -ItemType Directory -Force -Path ./SD-Trainer/python > $null
        }
        # 解压python
        Print-Msg "正在解压 Python"
        Expand-Archive -Path "./SD-Trainer/python-3.10.11-amd64.zip" -DestinationPath "./SD-Trainer/python" -Force
        Remove-Item -Path "./SD-Trainer/python-3.10.11-amd64.zip"
        Print-Msg "Python 安装成功"
    } else {
        Print-Msg "Python 安装失败, 终止 SD-Trainer 安装进程, 可尝试重新运行 SD-Trainer Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 下载并解压git
function Install-Git {
    $url = "https://modelscope.cn/api/v1/models/licyks/invokeai-core-model/repo?Revision=master&FilePath=pypatchmatch%2FPortableGit-2.45.2-64-bit.zip"
    Print-Msg "正在下载 Git"
    Invoke-WebRequest -Uri $url -OutFile "./SD-Trainer/PortableGit-2.45.2-64-bit.zip"
    if ($?) { # 检测是否下载成功并解压
        # 创建git文件夹
        if (!(Test-Path "./SD-Trainer/git")) {
            New-Item -ItemType Directory -Force -Path ./SD-Trainer/git > $null
        }
        # 解压git
        Print-Msg "正在解压 Git"
        Expand-Archive -Path "./SD-Trainer/PortableGit-2.45.2-64-bit.zip" -DestinationPath "./SD-Trainer/git" -Force
        Remove-Item -Path "./SD-Trainer/PortableGit-2.45.2-64-bit.zip"
        Print-Msg "Git 安装成功"
    } else {
        Print-Msg "Git 安装失败, 终止 SD-Trainer 安装进程, 可尝试重新运行 SD-Trainer Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 下载aria2
function Install-Aria2 {
    $url = "https://modelscope.cn/api/v1/models/licyks/invokeai-core-model/repo?Revision=master&FilePath=pypatchmatch%2Faria2c.exe"
    Print-Msg "正在下载 Aria2"
    Invoke-WebRequest -Uri $url -OutFile "./SD-Trainer/cache/aria2c.exe"
    if ($?) {
        Move-Item -Path "./SD-Trainer/cache/aria2c.exe" -Destination "./SD-Trainer/git/bin/aria2c.exe"
        Print-Msg "Aria2 下载成功"
    } else {
        Print-Msg "Aria2 下载失败"
    }
}


# github镜像测试
function Test-Github-Mirror {
    if (Test-Path "./disable_gh_mirror.txt") { # 禁用github镜像源
        Print-Msg "检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件, 禁用 Github 镜像源"
    } else {
        $env:GIT_CONFIG_GLOBAL = "$PSScriptRoot/SD-Trainer/.gitconfig" # 设置git配置文件路径
        if (Test-Path "$PSScriptRoot/SD-Trainer/.gitconfig") {
            Remove-Item -Path "$PSScriptRoot/SD-Trainer/.gitconfig" -Force
        }

        if (Test-Path "./gh_mirror.txt") { # 使用自定义github镜像源
            $github_mirror = Get-Content "./gh_mirror.txt"
            ./SD-Trainer/git/bin/git.exe config --global url."$github_mirror".insteadOf "https://github.com"
            Print-Msg "检测到本地存在 gh_mirror.txt Github 镜像源配置文件, 已读取 Github 镜像源配置文件并设置 Github 镜像源"
        } else { # 自动检测可用镜像源并使用
            $status = 0
            ForEach($i in $github_mirror_list) {
                Print-Msg "测试 Github 镜像源: $i"
                if (Test-Path "./SD-Trainer/github-mirror-test") {
                    Remove-Item -Path "./SD-Trainer/github-mirror-test" -Force -Recurse
                }
                ./SD-Trainer/git/bin/git.exe clone $i/licyk/empty ./SD-Trainer/github-mirror-test --quiet
                if ($?) {
                    Print-Msg "该 Github 镜像源可用"
                    $github_mirror = $i
                    $status = 1
                    break
                } else {
                    Print-Msg "镜像源不可用, 更换镜像源进行测试"
                }
            }
            if (Test-Path "./SD-Trainer/github-mirror-test") {
                Remove-Item -Path "./SD-Trainer/github-mirror-test" -Force -Recurse
            }
            if ($status -eq 0) {
                Print-Msg "无可用 Github 镜像源, 取消使用 Github 镜像源"
                Remove-Item -Path env:GIT_CONFIG_GLOBAL -Force
            } else {
                Print-Msg "设置 Github 镜像源"
                ./SD-Trainer/git/bin/git.exe config --global url."$github_mirror".insteadOf "https://github.com"
            }
        }
    }
}


# 安装sd-trainer
function Install-SD-Trainer {
    $status = 0
    if (!(Test-Path "./SD-Trainer/lora-scripts")) {
        $status = 1
    } else {
        $items = Get-ChildItem "./SD-Trainer/lora-scripts" -Recurse
        if ($items.Count -eq 0) {
            $status = 1
        }
    }

    if ($status -eq 1) {
        Print-Msg "正在下载 SD-Trainer"
        ./SD-Trainer/git/bin/git.exe clone --recurse-submodules https://github.com/Akegarasu/lora-scripts ./SD-Trainer/lora-scripts
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
    ./SD-Trainer/git/bin/git.exe -C ./SD-Trainer/lora-scripts submodule init
    ./SD-Trainer/git/bin/git.exe -C ./SD-Trainer/lora-scripts submodule update
    if ($?) {
        Print-Msg "SD-Trainer 子模块安装成功"
    } else {
        Print-Msg "SD-Trainer 子模块安装失败, 终止 SD-Trainer 安装进程, 可尝试重新运行 SD-Trainer Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 安装pytorch
function Install-PyTorch {
    Print-Msg "检测是否需要安装 PyTorch"
    ./SD-Trainer/python/python.exe -m pip show torch --quiet 2> $null
    if (!($?)) {
        Print-Msg "安装 PyTorch 中"
        ./SD-Trainer/python/python.exe -m pip install $pytorch_ver.ToString().Split() --no-warn-script-location
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
    ./SD-Trainer/python/python.exe -m pip show xformers --quiet 2> $null
    if (!($?)) {
        ./SD-Trainer/python/python.exe -m pip install $xformers_ver --no-deps --no-warn-script-location
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

# 安装sd-trainer依赖
function Install-SD-Trainer-Dependence {
    Set-Location "$PSScriptRoot/SD-Trainer/lora-scripts/sd-scripts"
    Print-Msg "安装 SD-Trainer 内核依赖中"
    ../../python/python.exe -m pip install --upgrade -r requirements.txt --no-warn-script-location
    if ($?) {
        Print-Msg "SD-Trainer 内核依赖安装成功"
    } else {
        Print-Msg "SD-Trainer 内核依赖安装失败, 终止 SD-Trainer 安装进程, 可尝试重新运行 SD-Trainer Installer 重试失败的安装"
        Set-Location "$PSScriptRoot"
        Read-Host | Out-Null
        exit 1
    }

    Set-Location "$PSScriptRoot/SD-Trainer/lora-scripts"
    Print-Msg "安装 SD-Trainer 依赖中"
    ../python/python.exe -m pip install --upgrade -r requirements.txt --no-warn-script-location
    if ($?) {
        Print-Msg "SD-Trainer 依赖安装成功"
    } else {
        Print-Msg "SD-Trainer 依赖安装失败, 终止 SD-Trainer 安装进程, 可尝试重新运行 SD-Trainer Installer 重试失败的安装"
        Set-Location "$PSScriptRoot"
        Read-Host | Out-Null
        exit 1
    }
    Set-Location "$PSScriptRoot"
}



# 安装
function Check-Install {
    if (!(Test-Path "./SD-Trainer")) {
        New-Item -ItemType Directory -Path "./SD-Trainer" > $null
    }

    if (!(Test-Path "./SD-Trainer/cache")) {
        New-Item -ItemType Directory -Path "./SD-Trainer/cache" > $null
    }

    if (!(Test-Path "./SD-Trainer/models")) {
        New-Item -ItemType Directory -Path "./SD-Trainer/models" > $null
    }

    Print-Msg "检测是否安装 Python"
    $pythonPath = "./SD-Trainer/python/python.exe"
    if (Test-Path $pythonPath) {
        Print-Msg "Python 已安装"
    } else {
        Print-Msg "Python 未安装"
        Install-Python
    }

    Print-Msg "检测是否安装 Git"
    $gitPath = "./SD-Trainer/git/bin/git.exe"
    if (Test-Path $gitPath) {
        Print-Msg "Git 已安装"
    } else {
        Print-Msg "Git 未安装"
        Install-Git
    }

    Print-Msg "检测是否安装 Aria2"
    $aria2Path = "./SD-Trainer/git/bin/aria2c.exe"
    if (Test-Path $aria2Path) {
        Print-Msg "Aria2 已安装"
    } else {
        Print-Msg "Aria2 未安装"
        Install-Aria2
    }

    Test-Github-Mirror
    Install-SD-Trainer
    Install-PyTorch
    Install-SD-Trainer-Dependence
}


# 启动脚本
function Write-Launch-Script {
    $content = "
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
}
Print-Msg `"初始化中`"

# 代理配置
`$env:NO_PROXY = `"localhost,127.0.0.1,::1`"
if (!(Test-Path `"`$PSScriptRoot/disable_proxy.txt`")) { # 检测是否禁用自动设置镜像源
    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
        `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        `$env:HTTP_PROXY = `$proxy_value
        `$env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
    } elseif (`$internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        `$env:HTTP_PROXY = `"http://`$(`$internet_setting.ProxyServer)`"
        `$env:HTTPS_PROXY = `"http://`$(`$internet_setting.ProxyServer)`"
        Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
} else {
    Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
}

# Huggingface 镜像源
if (!(Test-Path `"`$PSScriptRoot/disable_hf_mirror.txt`")) { # 检测是否禁用了自动设置huggingface镜像源
    if (Test-Path `"`$PSScriptRoot/hf_mirror.txt`") { # 本地存在huggingface镜像源配置
        `$hf_mirror_value = Get-Content `"`$PSScriptRoot/hf_mirror.txt`"
        `$env:HF_ENDPOINT = `$hf_mirror_value
        Print-Msg `"检测到本地存在 hf_mirror.txt 配置文件, 已读取该配置并设置 HuggingFace 镜像源`"
    } else { # 使用默认设置
        `$env:HF_ENDPOINT = `"https://hf-mirror.com`"
        Print-Msg `"使用默认 HuggingFace 镜像源`"
    }
} else {
    Print-Msg `"检测到本地存在 disable_hf_mirror.txt 镜像源配置文件, 禁用自动设置 HuggingFace 镜像源`"
}

if (Test-Path `"`$PSScriptRoot/launch_args.txt`") {
    `$args = Get-Content `"`$PSScriptRoot/launch_args.txt`"
    Print-Msg `"检测到本地存在 launch_args.txt 启动参数配置文件, 已读取该启动参数配置文件并应用启动参数`"
    Print-Msg `"使用的启动参数: `$args`"
}

`$py_path = `"`$PSScriptRoot/python`"
`$py_scripts_path = `"`$PSScriptRoot/python/Scripts`"
`$git_path = `"`$PSScriptRoot/git/bin`"
`$Env:PATH = `"`$py_path`$([System.IO.Path]::PathSeparator)`$py_scripts_path`$([System.IO.Path]::PathSeparator)`$git_path`$([System.IO.Path]::PathSeparator)`$Env:PATH`" # 将python添加到环境变量
`$env:PIP_INDEX_URL = `"$pip_index_mirror`"
`$env:PIP_EXTRA_INDEX_URL = `"$pip_extra_index_mirror`"
`$env:PIP_FIND_LINKS = `"$pip_find_mirror`"
`$env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$env:PIP_TIMEOUT = 30
`$env:PIP_RETRIES = 5
`$env:CACHE_HOME = `"`$PSScriptRoot/cache`"
`$env:HF_HOME = `"`$PSScriptRoot/cache/huggingface`"
`$env:MATPLOTLIBRC = `"`$PSScriptRoot/cache`"
`$env:MODELSCOPE_CACHE = `"`$PSScriptRoot/cache/modelscope/hub`"
`$env:MS_CACHE_HOME = `"`$PSScriptRoot/cache/modelscope/hub`"
`$env:SYCL_CACHE_DIR = `"`$PSScriptRoot/cache/libsycl_cache`"
`$env:TORCH_HOME = `"`$PSScriptRoot/cache/torch`"
`$env:U2NET_HOME = `"`$PSScriptRoot/cache/u2net`"
`$env:XDG_CACHE_HOME = `"`$PSScriptRoot/cache`"
`$env:PIP_CACHE_DIR = `"`$PSScriptRoot/cache/pip`"
`$env:PYTHONPYCACHEPREFIX = `"`$PSScriptRoot/cache/pycache`"

Print-Msg `"启动 SD-Trainer 中`"
Set-Location `"`$PSScriptRoot/lora-scripts`"
../python/python gui.py `$args.ToString().Split()
Set-Location `"`$PSScriptRoot`"
Print-Msg `"SD-Trainer 已结束运行`"
Read-Host | Out-Null
"

    Set-Content -Path "./SD-Trainer/launch.ps1" -Value $content
}


# 更新脚本
function Write-Update-Script {
    $content = "
`$github_mirror_list = @(
    `"https://mirror.ghproxy.com/https://github.com`",
    `"https://ghproxy.net/https://github.com`",
    `"https://gitclone.com/github.com`",
    `"https://gh-proxy.com/https://github.com`",
    `"https://ghps.cc/https://github.com`",
    `"https://gh.idayer.com/https://github.com`"
)

function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
}

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
            git -C `"`$path`" reset --recurse-submodules --hard HEAD # 回退版本,解决git pull异常
            git -C `"`$path`" restore --recurse-submodules --source=HEAD :/ # 重置工作区
        }
    }
}

# 代理配置
`$env:NO_PROXY = `"localhost,127.0.0.1,::1`"
if (!(Test-Path `"`$PSScriptRoot/disable_proxy.txt`")) { # 检测是否禁用自动设置镜像源
    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
        `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        `$env:HTTP_PROXY = `$proxy_value
        `$env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
    } elseif (`$internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        `$env:HTTP_PROXY = `"http://`$(`$internet_setting.ProxyServer)`"
        `$env:HTTPS_PROXY = `"http://`$(`$internet_setting.ProxyServer)`"
        Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
} else {
    Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
}

# github 镜像源
if (Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") { # 禁用github镜像源
    Print-Msg `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件, 禁用 Github 镜像源`"
} else {
    `$env:GIT_CONFIG_GLOBAL = `"`$PSScriptRoot/.gitconfig`" # 设置git配置文件路径
    if (Test-Path `"`$PSScriptRoot/.gitconfig`") {
        Remove-Item -Path `"`$PSScriptRoot/.gitconfig`" -Force
    }

    if (Test-Path `"`$PSScriptRoot/gh_mirror.txt`") { # 使用自定义github镜像源
        `$github_mirror = Get-Content `"`$PSScriptRoot/gh_mirror.txt`"
        ./git/bin/git.exe config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
        Print-Msg `"检测到本地存在 gh_mirror.txt Github 镜像源配置文件, 已读取 Github 镜像源配置文件并设置 Github 镜像源`"
    } else { # 自动检测可用镜像源并使用
        `$status = 0
        ForEach(`$i in `$github_mirror_list) {
            Print-Msg `"测试 Github 镜像源: `$i`"
            if (Test-Path `"./github-mirror-test`") {
                Remove-Item -Path `"./github-mirror-test`" -Force -Recurse
            }
            ./git/bin/git.exe clone `$i/licyk/empty ./github-mirror-test --quiet
            if (`$?) {
                Print-Msg `"该 Github 镜像源可用`"
                `$github_mirror = `$i
                `$status = 1
                break
            } else {
                Print-Msg `"镜像源不可用, 更换镜像源进行测试`"
            }
        }
        if (Test-Path `"./github-mirror-test`") {
            Remove-Item -Path `"./github-mirror-test`" -Force -Recurse
        }
        if (`$status -eq 0) {
            Print-Msg `"无可用 Github 镜像源, 取消使用 Github 镜像源`"
            Remove-Item -Path env:GIT_CONFIG_GLOBAL -Force
        } else {
            Print-Msg `"设置 Github 镜像源`"
            ./git/bin/git.exe config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
        }
    }
}

# 环境变量
`$env:PIP_INDEX_URL = `"$pip_index_mirror`"
`$env:PIP_EXTRA_INDEX_URL = `"$pip_extra_index_mirror`"
`$env:PIP_FIND_LINKS = `"$pip_find_mirror`"
`$env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$env:PIP_TIMEOUT = 30
`$env:PIP_RETRIES = 5
`$env:CACHE_HOME = `"`$PSScriptRoot/cache`"
`$env:HF_HOME = `"`$PSScriptRoot/cache/huggingface`"
`$env:MATPLOTLIBRC = `"`$PSScriptRoot/cache`"
`$env:MODELSCOPE_CACHE = `"`$PSScriptRoot/cache/modelscope/hub`"
`$env:MS_CACHE_HOME = `"`$PSScriptRoot/cache/modelscope/hub`"
`$env:SYCL_CACHE_DIR = `"`$PSScriptRoot/cache/libsycl_cache`"
`$env:TORCH_HOME = `"`$PSScriptRoot/cache/torch`"
`$env:U2NET_HOME = `"`$PSScriptRoot/cache/u2net`"
`$env:XDG_CACHE_HOME = `"`$PSScriptRoot/cache`"
`$env:PIP_CACHE_DIR = `"`$PSScriptRoot/cache/pip`"
`$env:PYTHONPYCACHEPREFIX = `"`$PSScriptRoot/cache/pycache`"

Print-Msg `"更新 SD-Trainer 中`"
Fix-Git-Point-Off-Set `"./lora-scripts`"
`$ver = `$(./git/bin/git.exe -C lora-scripts show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")
./git/bin/git.exe -C lora-scripts reset --hard --recurse-submodules
./git/bin/git.exe -C lora-scripts pull --recurse-submodules
if (`$?) {
    `$ver_ = `$(./git/bin/git.exe -C lora-scripts show -s --format=`"%h %cd`" --date=format:`"%Y-%m-%d %H:%M:%S`")
    if (`$ver -eq `$ver_) {
        Print-Msg `"SD-Trainer 已为最新版，当前版本：`$ver`"
    } else {
        Print-Msg `"SD-Trainer 更新成功，版本：`$ver -> `$ver_`"
    }
} else {
    Print-Msg `"SD-Trainer 更新失败`"
}

Print-Msg `"退出 SD-Trainer 更新脚本`"
Read-Host | Out-Null
"

    Set-Content -Path "./SD-Trainer/update.ps1" -Value $content
}



# 获取安装脚本
function Write-SD-Trainer-Install-Script {
    $content = "
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
}

# 代理配置
`$env:NO_PROXY = `"localhost,127.0.0.1,::1`"
if (!(Test-Path `"`$PSScriptRoot/disable_proxy.txt`")) { # 检测是否禁用自动设置镜像源
    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
        `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        `$env:HTTP_PROXY = `$proxy_value
        `$env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
    } elseif (`$internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        `$env:HTTP_PROXY = `"http://`$(`$internet_setting.ProxyServer)`"
        `$env:HTTPS_PROXY = `"http://`$(`$internet_setting.ProxyServer)`"
        Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
} else {
    Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
}

# Huggingface 镜像源
if (!(Test-Path `"`$PSScriptRoot/disable_hf_mirror.txt`")) { # 检测是否禁用了自动设置huggingface镜像源
    if (Test-Path `"`$PSScriptRoot/hf_mirror.txt`") { # 本地存在huggingface镜像源配置
        `$hf_mirror_value = Get-Content `"`$PSScriptRoot/hf_mirror.txt`"
        `$env:HF_ENDPOINT = `$hf_mirror_value
        Print-Msg `"检测到本地存在 hf_mirror.txt 配置文件, 已读取该配置并设置 HuggingFace 镜像源`"
    } else { # 使用默认设置
        `$env:HF_ENDPOINT = `"https://hf-mirror.com`"
        Print-Msg `"使用默认 HuggingFace 镜像源`"
    }
} else {
    Print-Msg `"检测到本地存在 disable_hf_mirror.txt 镜像源配置文件, 禁用自动设置 HuggingFace 镜像源`"
}

# 可用的下载源
`$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_trainer_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/sd_trainer_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_installer/sd_trainer_installer.ps1`")
`$count = `$urls.Length
`$i = 0

ForEach (`$url in `$urls) {
    Print-Msg `"正在下载最新的 SD-Trainer Installer 脚本`"
    Invoke-WebRequest -Uri `$url -OutFile `"./cache/sd_trainer_installer.ps1`"
    if (`$?) {
        if (Test-Path `"../sd_trainer_installer.ps1`") {
            Print-Msg `"删除原有的 SD-Trainer Installer 脚本`"
            Remove-Item `"../sd_trainer_installer.ps1`" -Force
        }
        Move-Item -Path `"./cache/sd_trainer_installer.ps1`" -Destination `"../sd_trainer_installer.ps1`"
        `$parentDirectory = Split-Path `$PSScriptRoot -Parent
        Print-Msg `"下载 SD-Trainer Installer 脚本成功, 脚本路径为 `$parentDirectory\sd_trainer_installer.ps1`"
        break
    } else {
        Print-Msg `"下载 SD-Trainer Installer 脚本失败`"
        `$i += 1
        if (`$i -lt `$count) {
            Print-Msg `"重试下载 SD-Trainer Installer 脚本`"
        }
    }
}

Print-Msg `"退出 SD-Trainer Installer 下载脚本`"
Read-Host | Out-Null
"

    Set-Content -Path "./SD-Trainer/get_sd_trainer_installer.ps1" -Value $content
}

# 重装pytorch脚本
function Write-PyTorch-Reinstall-Script {
    $content = "
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
}

# 环境变量
`$env:PIP_INDEX_URL = `"$pip_index_mirror`"
`$env:PIP_EXTRA_INDEX_URL = `"$pip_extra_index_mirror`"
`$env:PIP_FIND_LINKS = `"$pip_find_mirror`"
`$env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$env:PIP_TIMEOUT = 30
`$env:PIP_RETRIES = 5
`$env:CACHE_HOME = `"`$PSScriptRoot/cache`"
`$env:HF_HOME = `"`$PSScriptRoot/cache/huggingface`"
`$env:MATPLOTLIBRC = `"`$PSScriptRoot/cache`"
`$env:MODELSCOPE_CACHE = `"`$PSScriptRoot/cache/modelscope/hub`"
`$env:MS_CACHE_HOME = `"`$PSScriptRoot/cache/modelscope/hub`"
`$env:SYCL_CACHE_DIR = `"`$PSScriptRoot/cache/libsycl_cache`"
`$env:TORCH_HOME = `"`$PSScriptRoot/cache/torch`"
`$env:U2NET_HOME = `"`$PSScriptRoot/cache/u2net`"
`$env:XDG_CACHE_HOME = `"`$PSScriptRoot/cache`"
`$env:PIP_CACHE_DIR = `"`$PSScriptRoot/cache/pip`"
`$env:PYTHONPYCACHEPREFIX = `"`$PSScriptRoot/cache/pycache`"

`$to_exit = 0
while (`$True) {
    Print-Msg `"PyTorch 版本列表`"
    `$go_to = 0

    `$content = `"
-----------------------------------------------------
- 1、Torch 1.12.1 (CUDA11.3)+ xFormers 0.0.14
- 2、Torch 1.13.1 (CUDA11.7)+ xFormers 0.0.16
- 3、Torch 2.0.0 (CUDA11.8) + xFormers 0.0.18
- 4、Torch 2.0.1 (CUDA11.8) + xFormers 0.0.22
- 5、Torch 2.1.1 (CUDA11.8) + xFormers 0.0.23
- 6、Torch 2.1.2 (CUDA11.8) + xFormers 0.0.23.post1
- 7、Torch 2.2.0 (CUDA11.8) + xFormers 0.0.24
- 8、Torch 2.2.1 (CUDA11.8) + xFormers 0.0.25
- 9、Torch 2.2.2 (CUDA11.8) + xFormers 0.0.25.post1
- 10、Torch 2.3.0 (CUDA11.8) + xFormers 0.0.26.post1
-----------------------------------------------------
    `"

    Write-Host `$content
    Print-Msg `"请选择 PyTorch 版本`"
    Print-Msg `"提示: 输入数字后回车, 或者输入 exit 退出 PyTroch 重装脚本`"
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
            `$torch_ver = `"torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2+cu118`"
            `$xformers_ver = `"xformers==0.0.23.post1+cu118`"
            `$go_to = 1
        }
        7 {
            `$torch_ver = `"torch==2.2.0+cu118 torchvision==0.17.0+cu118 torchaudio==2.2.0+cu118`"
            `$xformers_ver = `"xformers==0.0.24+cu118`"
            `$go_to = 1
        }
        8 {
            `$torch_ver = `"torch==2.2.1+cu118 torchvision==0.17.1+cu118 torchaudio==2.2.1+cu118`"
            `$xformers_ver = `"xformers==0.0.25+cu118`"
            `$go_to = 1
        }
        9 {
            `$torch_ver = `"torch==2.2.2+cu118 torchvision==0.17.2+cu118 torchaudio==2.2.2+cu118`"
            `$xformers_ver = `"xformers==0.0.25.post1+cu118`"
            `$go_to = 1
        }
        10 {
            `$torch_ver = `"torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118`"
            `$xformers_ver = `"xformers==0.0.26.post1+cu118`"
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

Print-Msg `"是否选择仅强制重装? (通常情况下不需要)`"
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
    ./python/python.exe -m pip install `$torch_ver.ToString().Split() `$force_reinstall_arg --no-warn-script-location
    if (`$?) {
        Print-Msg `"安装 PyTorch 成功`"
    } else {
        Print-Msg `"安装 PyTorch 失败, 终止重装进程`"
        Read-Host | Out-Null
        exit 1
    }
    Print-Msg `"重装 xFormers 中`"
    ./python/python.exe -m pip install `$xformers_ver `$force_reinstall_arg --no-deps --no-warn-script-location
    if (`$?) {
        Print-Msg `"安装 xFormers 成功`"
    } else {
        Print-Msg `"安装 xFormers 失败, 终止重装进程`"
        Read-Host | Out-Null
        exit 1
    }
} else {
    Print-Msg `"取消重装 PyTorch`"
}

Print-Msg `"退出 PyTorch 重装脚本`"
Read-Host | Out-Null
"

    Set-Content -Path "./SD-Trainer/reinstall_pytorch.ps1" -Value $content
}


# 模型下载脚本
function Write-Doenload-Model-Script {
    $content = "
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
}

`$to_exit = 0
while (`$True) {
    `$go_to = 0
    Print-Msg `"可下载的模型列表`"
    `$content = `"
-----------------------------------------------------
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
- 11、ponyDiffusionV6XL_v6 (SDXL)
- 12、kohaku-xl-epsilon-rev2 (SDXL)
- 13、pdForAnime_v20 (SDXL)
- 14、starryXLV52_v52 (SDXL)
- 15、heartOfAppleXL_v20 (SDXL)
- 16、heartOfAppleXL_v30 (SDXL)
- 17、vae-ft-ema-560000-ema-pruned (SD 1.5 VAE)
- 18、vae-ft-mse-840000-ema-pruned (SD 1.5 VAE)
- 19、sdxl_fp16_fix_vae (SDXL VAE)
- 20、sdxl_vae (SDXL VAE)
-----------------------------------------------------
`"

    Write-Host `$content
    Print-Msg `"请选择要下载的模型`"
    Print-Msg `"提示: 输入数字后回车, 或者输入 exit 退出模型下载脚本`"
    `$arg = Read-Host `"===========================================>`"

    switch (`$arg) {
        1 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-model/repo?Revision=master&FilePath=sd_1.5%2Fv1-5-pruned-emaonly.safetensors`"
            `$model_name = `"v1-5-pruned-emaonly.safetensors`"
            `$go_to = 1
        }
        2 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-model/repo?Revision=master&FilePath=sd_1.5%2Fanimefull-final-pruned.safetensors`"
            `$model_name = `"animefull-final-pruned.safetensors`"
            `$go_to = 1
        }
        3 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-model/repo?Revision=master&FilePath=sd_2.1%2Fv2-1_768-ema-pruned.safetensors`"
            `$model_name = `"v2-1_768-ema-pruned.safetensors`"
            `$go_to = 1
        }
        4 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-model/repo?Revision=master&FilePath=sd_2.1%2Fwd-1-4-anime_e2.ckpt`"
            `$model_name = `"wd-1-4-anime_e2.ckpt`"
            `$go_to = 1
        }
        5 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-model/repo?Revision=master&FilePath=sd_2.1%2Fwd-mofu-fp16.safetensors`"
            `$model_name = `"wd-mofu-fp16.safetensors`"
            `$go_to = 1
        }
        6 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-model/repo?Revision=master&FilePath=sdxl_1.0%2Fsd_xl_base_1.0_0.9vae.safetensors`"
            `$model_name = `"sd_xl_base_1.0_0.9vae.safetensors`"
            `$go_to = 1
        }
        7 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-model/repo?Revision=master&FilePath=sdxl_1.0%2Fanimagine-xl-3.0.safetensors`"
            `$model_name = `"animagine-xl-3.0.safetensors`"
            `$go_to = 1
        }
        8 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-model/repo?Revision=master&FilePath=sdxl_1.0%2Fanimagine-xl-3.1.safetensors`"
            `$model_name = `"animagine-xl-3.1.safetensors`"
            `$go_to = 1
        }
        9 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-model/repo?Revision=master&FilePath=sdxl_1.0%2Fkohaku-xl-delta-rev1.safetensors`"
            `$model_name = `"kohaku-xl-delta-rev1.safetensors`"
            `$go_to = 1
        }
        10 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-model/repo?Revision=master&FilePath=sdxl_1.0%2FkohakuXLEpsilon_rev1.safetensors`"
            `$model_name = `"kohakuXLEpsilon_rev1.safetensors`"
            `$go_to = 1
        }
        11 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-model/repo?Revision=master&FilePath=sdxl_1.0%2FponyDiffusionV6XL_v6StartWithThisOne.safetensors`"
            `$model_name = `"ponyDiffusionV6XL_v6.safetensors`"
            `$go_to = 1
        }
        12 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-model/repo?Revision=master&FilePath=sdxl_1.0%2Fkohaku-xl-epsilon-rev2.safetensors`"
            `$model_name = `"kohaku-xl-epsilon-rev2.safetensors`"
            `$go_to = 1
        }
        13 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-model/repo?Revision=master&FilePath=sdxl_1.0%2FpdForAnime_v20.safetensors`"
            `$model_name = `"pdForAnime_v20.safetensors`"
            `$go_to = 1
        }
        14 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-model/repo?Revision=master&FilePath=sdxl_1.0%2FstarryXLV52_v52.safetensors`"
            `$model_name = `"starryXLV52_v52.safetensors`"
            `$go_to = 1
        }
        15 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-model/repo?Revision=master&FilePath=sdxl_1.0%2FheartOfAppleXL_v20.safetensors`"
            `$model_name = `"heartOfAppleXL_v20.safetensors`"
            `$go_to = 1
        }
        16 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-model/repo?Revision=master&FilePath=sdxl_1.0%2FheartOfAppleXL_v30.safetensors`"
            `$model_name = `"heartOfAppleXL_v30.safetensors`"
            `$go_to = 1
        }
        17 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-vae/repo?Revision=master&FilePath=sd_1.5%2Fvae-ft-ema-560000-ema-pruned.safetensors`"
            `$model_name = `"vae-ft-ema-560000-ema-pruned.safetensors`"
            `$go_to = 1
        }
        18 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-vae/repo?Revision=master&FilePath=sd_1.5%2Fvae-ft-mse-840000-ema-pruned.safetensors`"
            `$model_name = `"vae-ft-mse-840000-ema-pruned.safetensors`"
            `$go_to = 1
        }
        19 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-vae/repo?Revision=master&FilePath=sdxl_1.0%2Fsdxl_fp16_fix_vae.safetensors`"
            `$model_name = `"sdxl_fp16_fix_vae.safetensors`"
            `$go_to = 1
        }
        20 {
            `$url = `"https://modelscope.cn/api/v1/models/licyks/sd-vae/repo?Revision=master&FilePath=sdxl_1.0%2Fsdxl_vae.safetensors`"
            `$model_name = `"sdxl_vae.safetensors`"
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
    ./git/bin/aria2c --console-log-level=error -c -x 16 -s 16 `$url -d ./models -o `$model_name
    if (`$?) {
        Print-Msg `"`$model_name 模型下载成功`"
    } else {
        Print-Msg `"`$model_name 模型下载失败`"
    }
}

Print-Msg `"退出模型下载脚本`"
Read-Host | Out-Null
"

    Set-Content -Path "./SD-Trainer/download_models.ps1" -Value $content
}


# 虚拟环境激活脚本
function Write-Env-Activate-Script {
    $content = "
function global:prompt {
    `"`$(Write-Host `"[SD-Trainer Env]`" -ForegroundColor Green -NoNewLine) `$(Get-Location)>`"
}

function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][SD-Trainer Installer]:: `$msg`"
}

# 代理配置
`$env:NO_PROXY = `"localhost,127.0.0.1,::1`"
if (!(Test-Path `"`$PSScriptRoot/disable_proxy.txt`")) { # 检测是否禁用自动设置镜像源
    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if (Test-Path `"`$PSScriptRoot/proxy.txt`") { # 本地存在代理配置
        `$proxy_value = Get-Content `"`$PSScriptRoot/proxy.txt`"
        `$env:HTTP_PROXY = `$proxy_value
        `$env:HTTPS_PROXY = `$proxy_value
        Print-Msg `"检测到本地存在 proxy.txt 代理配置文件, 已读取代理配置文件并设置代理`"
    } elseif (`$internet_setting.ProxyEnable -eq 1) { # 系统已设置代理
        `$env:HTTP_PROXY = `"http://`$(`$internet_setting.ProxyServer)`"
        `$env:HTTPS_PROXY = `"http://`$(`$internet_setting.ProxyServer)`"
        Print-Msg `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
} else {
    Print-Msg `"检测到本地存在 disable_proxy.txt 代理配置文件, 禁用自动设置代理`"
}

# Huggingface 镜像源
if (!(Test-Path `"`$PSScriptRoot/disable_hf_mirror.txt`")) { # 检测是否禁用了自动设置huggingface镜像源
    if (Test-Path `"`$PSScriptRoot/hf_mirror.txt`") { # 本地存在huggingface镜像源配置
        `$hf_mirror_value = Get-Content `"`$PSScriptRoot/hf_mirror.txt`"
        `$env:HF_ENDPOINT = `$hf_mirror_value
        Print-Msg `"检测到本地存在 hf_mirror.txt 配置文件, 已读取该配置并设置 HuggingFace 镜像源`"
    } else { # 使用默认设置
        `$env:HF_ENDPOINT = `"https://hf-mirror.com`"
        Print-Msg `"使用默认 HuggingFace 镜像源`"
    }
} else {
    Print-Msg `"检测到本地存在 disable_hf_mirror.txt 镜像源配置文件, 禁用自动设置 HuggingFace 镜像源`"
}

# github 镜像源
if (Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") { # 禁用github镜像源
    Print-Msg `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件, 禁用 Github 镜像源`"
} else {
    `$env:GIT_CONFIG_GLOBAL = `"`$PSScriptRoot/.gitconfig`" # 设置git配置文件路径
    if (Test-Path `"`$PSScriptRoot/.gitconfig`") {
        Remove-Item -Path `"`$PSScriptRoot/.gitconfig`" -Force
    }

    if (Test-Path `"`$PSScriptRoot/gh_mirror.txt`") { # 使用自定义github镜像源
        `$github_mirror = Get-Content `"`$PSScriptRoot/gh_mirror.txt`"
        ./git/bin/git.exe config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
        Print-Msg `"检测到本地存在 gh_mirror.txt Github 镜像源配置文件, 已读取 Github 镜像源配置文件并设置 Github 镜像源`"
    }
}

# 环境变量
`$py_path = `"`$PSScriptRoot/python`"
`$py_scripts_path = `"`$PSScriptRoot/python/Scripts`"
`$git_path = `"`$PSScriptRoot/git/bin`"
`$Env:PATH = `"`$py_path`$([System.IO.Path]::PathSeparator)`$py_scripts_path`$([System.IO.Path]::PathSeparator)`$git_path`$([System.IO.Path]::PathSeparator)`$Env:PATH`" # 将python添加到环境变量
`$env:PIP_INDEX_URL = `"$pip_index_mirror`"
`$env:PIP_EXTRA_INDEX_URL = `"$pip_extra_index_mirror`"
`$env:PIP_FIND_LINKS = `"$pip_find_mirror`"
`$env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$env:PIP_TIMEOUT = 30
`$env:PIP_RETRIES = 5
`$env:CACHE_HOME = `"`$PSScriptRoot/cache`"
`$env:HF_HOME = `"`$PSScriptRoot/cache/huggingface`"
`$env:MATPLOTLIBRC = `"`$PSScriptRoot/cache`"
`$env:MODELSCOPE_CACHE = `"`$PSScriptRoot/cache/modelscope/hub`"
`$env:MS_CACHE_HOME = `"`$PSScriptRoot/cache/modelscope/hub`"
`$env:SYCL_CACHE_DIR = `"`$PSScriptRoot/cache/libsycl_cache`"
`$env:TORCH_HOME = `"`$PSScriptRoot/cache/torch`"
`$env:U2NET_HOME = `"`$PSScriptRoot/cache/u2net`"
`$env:XDG_CACHE_HOME = `"`$PSScriptRoot/cache`"
`$env:PIP_CACHE_DIR = `"`$PSScriptRoot/cache/pip`"
`$env:PYTHONPYCACHEPREFIX = `"`$PSScriptRoot/cache/pycache`"

Print-Msg `"激活 SD-Trainer Env`"
Print-Msg `"更多帮助信息可在 SD-Trainer Installer 项目地址查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md`"
"

    Set-Content -Path "./SD-Trainer/activate.ps1" -Value $content
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
get_sd_trainer_installer.ps1：获取最新的 SD-Trainer Installer 安装脚本，运行后将会在与 SD-Trainer 文件夹同级的目录中生成 invokeai_installer.ps1 安装脚本。
update.ps1：更新 SD-Trainer 的脚本，可使用该脚本更新 SD-Trainer。
launch.ps1：启动 SD-Trainer 的脚本。
reinstall_pytorch.ps1：重新安装 PyTorch 的脚本，在 PyTorch 出问题或者需要切换 PyTorch 版本时可使用。
download_model.ps1：下载模型的脚本，下载的模型将存放在 models 文件夹中。
help.txt：帮助文档。


要启动 SD-Trainer，可在 SD-Trainer 文件夹中找到 launch.ps1 脚本，右键这个脚本，选择使用 PowerShell 运行，等待 SD-Trainer 启动完成，启动完成后将自动打开浏览器进入 SD-Trainer 界面。

脚本为 SD-Trainer，可在 设置了 HuggingFace 镜像源，解决国内无法直接访问 HuggingFace 的问题，导致 SD-Trainer 无法从 HuggingFace 下载模型。
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

设置 SD-Trainer 的启动参数，可以在和 launch.ps1 脚本同级的目录创建一个 launch_args.txt 文件，在文件内写上启动参数，运行 SD-Trainer 启动脚本时将自动读取该文件内的启动参数并应用。

更多详细的帮助可在下面的链接查看。
SD-Trainer Installer 使用帮助：https://github.com/licyk/sd-webui-all-in-one/blob/main/sd_trainer_installer.md
SD-Trainer 项目地址：https://github.com/Akegarasu/lora-scripts

推荐的哔哩哔哩 UP 主：
青龙圣者：https://space.bilibili.com/219296
琥珀青葉：https://space.bilibili.com/507303431

一些训练模型的教程：
https://civitai.com/articles/124/lora-analogy-about-lora-trainning-and-using
https://civitai.com/articles/143/some-shallow-understanding-of-lora-training-lora
https://civitai.com/articles/632/why-this-lora-can-not-bring-good-result-lora
https://civitai.com/articles/726/an-easy-way-to-make-a-cosplay-lora-cosplay-lora
https://civitai.com/articles/2135/lora-quality-improvement-some-experiences-about-datasets-and-captions-lora
https://civitai.com/articles/2297/ways-to-make-a-character-lora-that-is-easier-to-change-clothes-lora
"
    Set-Content -Path "./SD-Trainer/help.txt" -Value $content
}


# 主程序
function Main {
    Print-Msg "启动 SD-Trainer 安装程序"
    Print-Msg "提示: 若出现某个步骤执行失败, 可尝试再次运行 SD-Trainer Installer"
    Check-Install
    Print-Msg "添加启动脚本和文档中"
    Write-Launch-Script
    Write-Update-Script
    Write-SD-Trainer-Install-Script
    Write-PyTorch-Reinstall-Script
    Write-Doenload-Model-Script
    Write-Env-Activate-Script
    Write-ReadMe
    Print-Msg "SD-Trainer 安装结束, 安装路径为 $PSScriptRoot\SD-Trainer"
    Print-Msg "帮助文档可在 SD-Trainer 文件夹中查看, 双击 help.txt 文件即可查看"
    Print-Msg "退出 SD-Trainer Installer"
}


###################


Main
Read-Host | Out-Null
