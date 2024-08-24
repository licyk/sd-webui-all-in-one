# 有关 PowerShell 脚本保存编码的问题: https://learn.microsoft.com/zh-cn/powershell/module/microsoft.powershell.core/about/about_character_encoding?view=powershell-7.4#the-byte-order-mark
Set-Location "$PSScriptRoot"
# Pip 镜像源
$pip_index_mirror = "https://mirrors.cloud.tencent.com/pypi/simple"
$pip_extra_index_mirror = "https://mirror.baidu.com/pypi/simple"
$pip_find_mirror = "https://mirror.sjtu.edu.cn/pytorch-wheels/cu118/torch_stable.html"
$pip_extra_index_mirror_cu121 = "https://mirror.sjtu.edu.cn/pytorch-wheels/cu121"
$pip_find_mirror_cu121 = "https://mirror.sjtu.edu.cn/pytorch-wheels/cu121/torch_stable.html"
# 环境变量
$env:PIP_INDEX_URL = $pip_index_mirror
$env:PIP_EXTRA_INDEX_URL = $pip_extra_index_mirror
$env:PIP_FIND_LINKS = $pip_find_mirror
$env:PIP_DISABLE_PIP_VERSION_CHECK = 1
$env:PIP_TIMEOUT = 30
$env:PIP_RETRIES = 5
$env:CACHE_HOME = "$PSScriptRoot/InvokeAI/cache"
$env:HF_HOME = "$PSScriptRoot/InvokeAI/cache/huggingface"
$env:MATPLOTLIBRC = "$PSScriptRoot/InvokeAI/cache"
$env:MODELSCOPE_CACHE = "$PSScriptRoot/InvokeAI/cache/modelscope/hub"
$env:MS_CACHE_HOME = "$PSScriptRoot/InvokeAI/cache/modelscope/hub"
$env:SYCL_CACHE_DIR = "$PSScriptRoot/InvokeAI/cache/libsycl_cache"
$env:TORCH_HOME = "$PSScriptRoot/InvokeAI/cache/torch"
$env:U2NET_HOME = "$PSScriptRoot/InvokeAI/cache/u2net"
$env:XDG_CACHE_HOME = "$PSScriptRoot/InvokeAI/cache"
$env:PIP_CACHE_DIR = "$PSScriptRoot/InvokeAI/cache/pip"
$env:PYTHONPYCACHEPREFIX = "$PSScriptRoot/InvokeAI/cache/pycache"
$env:INVOKEAI_ROOT = "$PSScriptRoot/InvokeAI/invokeai"


# 消息输出
function Print-Msg ($msg) {
    Write-Host "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")][InvokeAI Installer]:: $msg"
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


# 下载并解压 Python
function Install-Python {
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/python-3.10.11-embed-amd64.zip"

    # 下载 Python
    Print-Msg "正在下载 Python"
    Invoke-WebRequest -Uri $url -OutFile "./InvokeAI/python-3.10.11-embed-amd64.zip"
    if ($?) { # 检测是否下载成功并解压
        # 创建 Python 文件夹
        if (!(Test-Path "./InvokeAI/python")) {
            New-Item -ItemType Directory -Force -Path ./InvokeAI/python > $null
        }
        # 解压 Python
        Print-Msg "正在解压 Python"
        Expand-Archive -Path "./InvokeAI/python-3.10.11-embed-amd64.zip" -DestinationPath "./InvokeAI/python" -Force
        Remove-Item -Path "./InvokeAI/python-3.10.11-embed-amd64.zip"
        Modify-PythonPath
        Print-Msg "Python 安装成功"
    } else {
        Print-Msg "Python 安装失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 修改 python310._pth 文件的内容
function Modify-PythonPath {
    Print-Msg "修改 python310._pth 文件内容"
    $content = @("python310.zip", ".", "", "# Uncomment to run site.main() automatically", "import site")
    Set-Content -Path "./InvokeAI/python/python310._pth" -Value $content
}


# 配置 Python 的 Pip 模块
function Install-Pip {
    $url = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/get-pip.py"

    # 下载 get-pip.py
    Print-Msg "正在下载 get-pip.py"
    Invoke-WebRequest -Uri $url -OutFile "./InvokeAI/get-pip.py"
    if ($?) { # 检测是否下载成功
        # 执行 get-pip.py
        Print-Msg "通过 get-pip.py 安装 Pip 中"
        ./InvokeAI/python/python.exe ./InvokeAI/get-pip.py --no-warn-script-location
        if ($?) { # 检测是否安装成功
            Remove-Item -Path "./InvokeAI/get-pip.py"
            Print-Msg "Pip 安装成功"
        } else {
            Remove-Item -Path "./InvokeAI/get-pip.py"
            Print-Msg "Pip 安装失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
            Read-Host | Out-Null
            exit 1
        }
    } else {
        Print-Msg "下载 get-pip.py 失败"
        Print-Msg "Pip 安装失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 安装 InvokeAI
function Install-InvokeAI {
    # 下载 InvokeAI
    Print-Msg "正在下载 InvokeAI"
    ./InvokeAI/python/python.exe -m pip install "InvokeAI[xformers]"  --no-warn-script-location --use-pep517
    if ($?) { # 检测是否下载成功
        Print-Msg "InvokeAI 安装成功"
    } else {
        Print-Msg "InvokeAI 安装失败, 终止 InvokeAI 安装进程, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
        Read-Host | Out-Null
        exit 1
    }
}


# 重装 xFormers
function Reinstall-Xformers {
    $env:PIP_EXTRA_INDEX_URL = $pip_extra_index_mirror_cu121
    $env:PIP_FIND_LINKS = $pip_find_mirror_cu121
    $xformers_pkg = $(./InvokeAI/python/python.exe -m pip freeze | Select-String -Pattern "xformers") # 检测是否安装了 xFormers
    $xformers_pkg_cu118 = $xformers_pkg | Select-String -Pattern "cu118" # 检查是否版本为 cu118 的
    $torch_ver = $(./InvokeAI/python/python.exe -m pip show torch | Select-String -Pattern "version") # 获取 PyTorch 版本信息
    $torch_ver = $torch_ver.ToString().Split(":")[1].Split("+")[0].Trim() # 截取 PyTorch 版本号

    if (Test-Path "./InvokeAI/cache/xformers.txt") {
        # 读取 xformers.txt 文件的内容
        Print-Msg "读取上次的 xFormers 版本记录"
        $xformers_ver = Get-Content "./InvokeAI/cache/xformers.txt"
    }

    for ($i = 1; $i -le 3; $i++) {
        if ($xformers_ver) { # 本地存在版本记录（上次安装 xFormers 未完成）
            Print-Msg "安装: $xformers_ver"
            ./InvokeAI/python/python.exe -m pip uninstall xformers -y
            ./InvokeAI/python/python.exe -m pip install $xformers_ver --no-warn-script-location --no-cache-dir --no-deps
            if ($?) {
                Remove-Item -Path "./InvokeAI/cache/xformers.txt"
                Print-Msg "重装 xFormers 成功"
                break
            } else {
                Print-Msg "重装 xFormers 失败"
            }
        } elseif ($xformers_pkg) { # 已安装了 xFormers
            if ($xformers_pkg_cu118) { # 确认 xFormers 是否为 cu118 的版本
                Print-Msg "检测到已安装的 xFormers 为 CU118 的版本, 将进行重装"
                $xformers_pkg = $xformers_pkg.ToString().Split("+")[0]
                $xformers_pkg > ./InvokeAI/cache/xformers.txt # 将版本信息存在本地, 用于安装失败时恢复
                ./InvokeAI/python/python.exe -m pip uninstall xformers -y
                ./InvokeAI/python/python.exe -m pip install $xformers_pkg --no-warn-script-location --no-cache-dir --no-deps
                if ($?) {
                    Remove-Item -Path "./InvokeAI/cache/xformers.txt"
                    Print-Msg "重装 xFormers 成功"
                    break
                } else {
                    Print-Msg "重装 xFormers 失败"
                }
            } else {
                Print-Msg "无需重装 xFormers"
                break
            }
        } else {
            Print-Msg "未安装 xFormers, 尝试安装中"
            switch ($torch_ver) { # 判断适合安装的 xFormers 版本
                1.12.1 {
                    $install_xformers_ver = "0.0.14"
                }
                1.13.1 {
                    $install_xformers_ver = "0.0.16"
                }
                2.0.0 {
                    $install_xformers_ver = "0.0.18"
                }
                2.0.1 {
                    $install_xformers_ver = "0.0.22"
                }
                2.1.1 {
                    $install_xformers_ver = "0.0.23"
                }
                2.1.1 {
                    $install_xformers_ver = "0.0.23"
                }
                2.1.2 {
                    $install_xformers_ver = "0.0.23.post1"
                }
                2.2.0 {
                    $install_xformers_ver = "0.0.24"
                }
                2.2.1 {
                    $install_xformers_ver = "0.0.25"
                }
                2.2.2 {
                    $install_xformers_ver = "0.0.25"
                }
                2.3.0 {
                    $install_xformers_ver = "0.0.26.post1"
                }
                Default {
                    $install_xformers_ver = ""
                }
            }

            if ($install_xformers_ver -eq "") {
                ./InvokeAI/python/python.exe -m pip install xformers --no-warn-script-location --no-cache-dir --no-deps
            } else {
                ./InvokeAI/python/python.exe -m pip install xformers==$install_xformers_ver --no-warn-script-location --no-cache-dir --no-deps
            }

            if ($?) { # 检测是否下载成功
                Print-Msg "重装 xFormers 成功"
                break
            } else {
                Print-Msg "重装 xFormers 失败"
            }
        }

        if ($i -ge 3) { # 超出重试次数时进行提示
            Print-Msg "xFormers 未能成功安装, 这可能导致使用 InvokeAI 时显存占用率增大, 可尝试重新运行 InvokeAI Installer 重试失败的安装"
            break
        } else {
            Print-Msg "尝试重新安装 xFormers 中"
        }
    }
}


# 下载 PyPatchMatch
function Install-PyPatchMatch {
    # PyPatchMatch
    $url_1 = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/libpatchmatch_windows_amd64.dll"
    $url_2 = "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/opencv_world460.dll"

    if (!(Test-Path "./InvokeAI/python/Lib/site-packages/patchmatch/libpatchmatch_windows_amd64.dll")) {
        Print-Msg "下载 libpatchmatch_windows_amd64.dll 中"
        Invoke-WebRequest -Uri $url_1 -OutFile "./InvokeAI/cache/libpatchmatch_windows_amd64.dll"
        if ($?) {
            Move-Item -Path "./InvokeAI/cache/libpatchmatch_windows_amd64.dll" -Destination "./InvokeAI/python/Lib/site-packages/patchmatch/libpatchmatch_windows_amd64.dll"
            Print-Msg "下载 libpatchmatch_windows_amd64.dll 成功"
        } else {
            Print-Msg "下载 libpatchmatch_windows_amd64.dll 失败"
        }
    } else {
        Print-Msg "无需下载 libpatchmatch_windows_amd64.dll"
    }

    if (!(Test-Path "./InvokeAI/python/Lib/site-packages/patchmatch/opencv_world460.dll")) {
        Print-Msg "下载 opencv_world460.dll 中"
        Invoke-WebRequest -Uri $url_2 -OutFile "./InvokeAI/cache/opencv_world460.dll"
        if ($?) {
            Move-Item -Path "./InvokeAI/cache/opencv_world460.dll" -Destination "./InvokeAI/python/Lib/site-packages/patchmatch/opencv_world460.dll"
            Print-Msg "下载 opencv_world460.dll 成功"
        } else {
            Print-Msg "下载 opencv_world460.dll 失败"
        }
    } else {
        Print-Msg "无需下载 opencv_world460.dll"
    }
}


# 下载配置文件
function Download-Config-File($url, $path) {
    $length = $url.split("/").length
    $name = $url.split("/")[$length - 1]
    if (!(Test-Path $path)) {
        Print-Msg "下载 $name 中"
        Invoke-WebRequest -Uri $url.ToString() -OutFile "./InvokeAI/cache/$name"
        if ($?) {
            Move-Item -Path "./InvokeAI/cache/$name" -Destination "$path"
            Print-Msg "$name 下载成功"
        } else {
            Print-Msg "$name 下载失败"
        }
    } else {
        Print-Msg "$name 已存在"
    }
}


# 预下载模型配置文件
function Get-Model-Config-File {
    Print-Msg "预下载模型配置文件中"
    New-Item -ItemType Directory -Path "./InvokeAI/invokeai/configs/stable-diffusion" -Force > $null
    New-Item -ItemType Directory -Path "./InvokeAI/invokeai/configs/controlnet" -Force > $null
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_base.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/sd_xl_base.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_inpaint.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/sd_xl_inpaint.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_refiner.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/sd_xl_refiner.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-finetune.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v1-finetune.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-finetune_style.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v1-finetune_style.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inference-v.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v1-inference-v.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inference.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v1-inference.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inpainting-inference.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v1-inpainting-inference.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-m1-finetune.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v1-m1-finetune.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inference-v.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v2-inference-v.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inference.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v2-inference.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inpainting-inference-v.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v2-inpainting-inference-v.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inpainting-inference.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v2-inpainting-inference.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-midas-inference.yaml" "./InvokeAI/invokeai/configs/stable-diffusion/v2-midas-inference.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/controlnet/cldm_v15.yaml" "./InvokeAI/invokeai/configs/controlnet/cldm_v15.yaml"
    Download-Config-File "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/controlnet/cldm_v21.yaml" "./InvokeAI/invokeai/configs/controlnet/cldm_v21.yaml"
    Print-Msg "模型配置文件下载完成"
}


# 安装
function Check-Install {
    if (!(Test-Path "./InvokeAI")) {
        New-Item -ItemType Directory -Path "./InvokeAI" > $null
    }

    if (!(Test-Path "./InvokeAI/cache")) {
        New-Item -ItemType Directory -Path "./InvokeAI/cache" > $null
    }

    Print-Msg "检测是否安装 Python"
    $python_path = "./InvokeAI/python/python.exe"
    if (Test-Path $python_path) {
        Print-Msg "Python 已安装"
    } else {
        Print-Msg "Python 未安装"
        Install-Python
    }

    Print-Msg "检查是否安装 Pip"
    ./InvokeAI/python/python.exe -c "import pip" 2> $null
    if ($?) {
        Print-Msg "Pip 已安装"
    } else {
        Print-Msg "Pip 未安装"
        Install-Pip
    }

    Print-Msg "检查是否安装 InvokeAI"
    $invokeai_path = "./InvokeAI/python/Scripts/invokeai-web.exe"
    if (Test-Path $invokeai_path) {
        Print-Msg "InvokeAI 已安装"
    } else {
        Print-Msg "InvokeAI 未安装"
        Install-InvokeAI
    }

    # Print-Msg "检测是否需要重装 xFormers"
    # Reinstall-Xformers

    Print-Msg "检测是否需要安装 PyPatchMatch"
    Install-PyPatchMatch

    Print-Msg "检测是否需要下载模型配置文件"
    Get-Model-Config-File
}


# 启动脚本
function Write-Launch-Script {
    $content = "
Set-Location `"`$PSScriptRoot`"
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
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
if (!(Test-Path `"`$PSScriptRoot/disable_mirror.txt`")) { # 检测是否禁用了自动设置huggingface镜像源
    if (Test-Path `"`$PSScriptRoot/mirror.txt`") { # 本地存在huggingface镜像源配置
        `$hf_mirror_value = Get-Content `"`$PSScriptRoot/mirror.txt`"
        `$env:HF_ENDPOINT = `$hf_mirror_value
        Print-Msg `"检测到本地存在 mirror.txt 配置文件, 已读取该配置并设置 HuggingFace 镜像源`"
    } else { # 使用默认设置
        `$env:HF_ENDPOINT = `"https://hf-mirror.com`"
        Print-Msg `"使用默认 HuggingFace 镜像源`"
    }
} else {
    Print-Msg `"检测到本地存在 disable_mirror.txt 镜像源配置文件, 禁用自动设置 HuggingFace 镜像源`"
}

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
`$env:INVOKEAI_ROOT = `"`$PSScriptRoot/invokeai`"

Print-Msg `"将使用浏览器打开 http://127.0.0.1:9090 地址，进入 InvokeAI 的界面`"
Print-Msg `"提示: 打开浏览器后, 浏览器可能会显示连接失败，这是因为 InvokeAI 未完成启动, 可以在弹出的 PowerShell 中查看 InvokeAI 的启动过程, 等待 InvokeAI 启动完成后刷新浏览器网页即可`"
Print-Msg `"提示：如果 PowerShell 界面长时间不动，并且 InvokeAI 未启动，可以尝试按下几次回车键`"
Start-Sleep -Seconds 2
Print-Msg `"调用浏览器打开地址中`"
Start-Process `"http://127.0.0.1:9090`"
Print-Msg `"启动 InvokeAI 中`"
./python/Scripts/invokeai-web.exe --root `"`$PSScriptRoot/invokeai`"
`$req = `$?
if (`$req) {
    Print-Msg `"InvokeAI 正常退出`"
} else {
    Print-Msg `"InvokeAI 出现异常, 已退出`"
}
Read-Host | Out-Null
"

    Set-Content -Encoding UTF8 -Path "./InvokeAI/launch.ps1" -Value $content
}


# 更新脚本
function Write-Update-Script {
    $content = "
Set-Location `"`$PSScriptRoot`"
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
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
`$env:INVOKEAI_ROOT = `"`$PSScriptRoot/invokeai`"

Print-Msg `"更新 InvokeAI 中`"
`$ver = `$(./python/python.exe -m pip freeze | Select-String -Pattern `"invokeai`" | Out-String).trim().split(`"==`")[2]
./python/python.exe -m pip install `"InvokeAI[xformers]`" --upgrade --no-warn-script-location --use-pep517
if (`$?) {
    `$ver_ = `$(./python/python.exe -m pip freeze | Select-String -Pattern `"invokeai`" | Out-String).trim().split(`"==`")[2]
    if (`$ver -eq `$ver_) {
        Print-Msg `"InvokeAI 已为最新版，当前版本：`$ver_`"
    } else {
        Print-Msg `"InvokeAI 更新成功，版本：`$ver -> `$ver_`"
    }
    Print-Msg `"该版本更新日志：https://github.com/invoke-ai/InvokeAI/releases/latest`"
} else {
    Print-Msg `"InvokeAI 更新失败`"
}
Read-Host | Out-Null
"

    Set-Content -Encoding UTF8 -Path "./InvokeAI/update.ps1" -Value $content
}


# 数据库修复
function Write-InvokeAI-DB-Fix-Script {
    $content = "
Set-Location `"`$PSScriptRoot`"
`$env:INVOKEAI_ROOT = `"`$PSScriptRoot/invokeai`"
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
}

Print-Msg `"修复 InvokeAI 数据库中`"
./python/Scripts/invokeai-db-maintenance.exe --operation all --root `"`$PSScriptRoot/invokeai`"
Print-Msg `"修复 InvokeAI 数据库完成`"
Read-Host | Out-Null
"

    Set-Content -Encoding UTF8 -Path "$PSScriptRoot/InvokeAI/fix_db.ps1" -Value $content
}


# 获取安装脚本
function Write-InvokeAI-Install-Script {
    $content = "
Set-Location `"`$PSScriptRoot`"
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
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

# 可用的下载源
`$urls = @(`"https://github.com/licyk/sd-webui-all-in-one/raw/main/invokeai_installer.ps1`", `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/invokeai_installer.ps1`", `"https://github.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`", `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/invokeai_installer/invokeai_installer.ps1`")
`$count = `$urls.Length
`$i = 0

ForEach (`$url in `$urls) {
    Print-Msg `"正在下载最新的 InvokeAI Installer 脚本`"
    Invoke-WebRequest -Uri `$url -OutFile `"./cache/invokeai_installer.ps1`"
    if (`$?) {
        if (Test-Path `"../invokeai_installer.ps1`") {
            Print-Msg `"删除原有的 InvokeAI Installer 脚本`"
            Remove-Item `"../invokeai_installer.ps1`" -Force
        }
        Move-Item -Path `"./cache/invokeai_installer.ps1`" -Destination `"../invokeai_installer.ps1`"
        `$parentDirectory = Split-Path `$PSScriptRoot -Parent
        Print-Msg `"下载 InvokeAI Installer 脚本成功, 脚本路径为 `$parentDirectory\invokeai_installer.ps1`"
        break
    } else {
        Print-Msg `"下载 InvokeAI Installer 脚本失败`"
        `$i += 1
        if (`$i -lt `$count) {
            Print-Msg `"重试下载 InvokeAI Installer 脚本`"
        }
    }
}
Read-Host | Out-Null
"

    Set-Content -Encoding UTF8 -Path "./InvokeAI/get_invokeai_installer.ps1" -Value $content
}


# 虚拟环境激活脚本
function Write-Env-Activate-Script {
    $content = "
function global:prompt {
    `"`$(Write-Host `"[InvokeAI Env]`" -ForegroundColor Green -NoNewLine) `$(Get-Location)> `"
}

function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
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

# HuggingFace 镜像源
if (!(Test-Path `"`$PSScriptRoot/disable_mirror.txt`")) { # 检测是否禁用了自动设置 HuggingFace 镜像源
    if (Test-Path `"`$PSScriptRoot/mirror.txt`") { # 本地存在 HuggingFace 镜像源配置
        `$hf_mirror_value = Get-Content `"`$PSScriptRoot/mirror.txt`"
        `$env:HF_ENDPOINT = `$hf_mirror_value
        Print-Msg `"检测到本地存在 mirror.txt 配置文件, 已读取该配置并设置 HuggingFace 镜像源`"
    } else { # 使用默认设置
        `$env:HF_ENDPOINT = `"https://hf-mirror.com`"
        Print-Msg `"使用默认 HuggingFace 镜像源`"
    }
} else {
    Print-Msg `"检测到本地存在 disable_mirror.txt 镜像源配置文件, 禁用自动设置 HuggingFace 镜像源`"
}

# 环境变量
`$py_path = `"`$PSScriptRoot/python`"
`$py_scripts_path = `"`$PSScriptRoot/python/Scripts`"
`$Env:PATH = `"`$py_path`$([System.IO.Path]::PathSeparator)`$py_scripts_path`$([System.IO.Path]::PathSeparator)`$Env:PATH`" # 将python添加到环境变量
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
`$env:INVOKEAI_ROOT = `"`$PSScriptRoot/invokeai`"

Print-Msg `"激活 InvokeAI Env`"
Print-Msg `"更多帮助信息可在 InvokeAI Installer 项目地址查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md`"
"

    Set-Content -Encoding UTF8 -Path "./InvokeAI/activate.ps1" -Value $content
}


# PyTorch 重装脚本
function Write-PyTorch-ReInstall-Script {
    $content = "
Set-Location `"`$PSScriptRoot`"
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
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
`$env:INVOKEAI_ROOT = `"`$PSScriptRoot/invokeai`"

Print-Msg `"是否重新安装 PyTorch (yes/no)?`"
Print-Msg `"提示: 输入 yes 确认或 no 取消 (默认为 no)`"
`$arg = Read-Host `"=========================================>`"
if (`$arg -eq `"yes`" -or `$arg -eq `"y`" -or `$arg -eq `"YES`" -or `$arg -eq `"Y`") {
    Print-Msg `"卸载原有的 PyTorch`"
    ./python/python.exe -m pip uninstall torch torchvision torchaudio xformers -y
    Print-Msg `"重新安装 PyTorch`"
    ./python/python.exe -m pip install `"InvokeAI[xformers]`" --no-warn-script-location --use-pep517
    if (`$?) {
        Print-Msg `"重新安装 PyTorch 成功`"
    } else {
        Print-Msg `"重新安装 PyTorch 失败, 请重新运行 PyTorch 重装脚本`"
    }
} else {
    Print-Msg `"取消重装 PyTorch`"
}

Read-Host | Out-Null
"

    Set-Content -Encoding UTF8 -Path "./InvokeAI/reinstall_pytorch.ps1" -Value $content
}


# 下载模型配置文件脚本
function Wirte-Download-Config-Script {
    $content = "
Set-Location `"`$PSScriptRoot`"

# 消息输出
function Print-Msg (`$msg) {
    Write-Host `"[`$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`")][InvokeAI Installer]:: `$msg`"
}

# 下载配置文件
function Download-Config-File(`$url, `$path) {
    `$length = `$url.split(`"/`").length
    `$name = `$url.split(`"/`")[`$length - 1]
    if (!(Test-Path `$path)) {
        Print-Msg `"下载 `$name 中`"
        Invoke-WebRequest -Uri `$url.ToString() -OutFile `"./cache/`$name`"
        if (`$?) {
            Move-Item -Path `"./cache/`$name`" -Destination `"`$path`"
            Print-Msg `"`$name 下载成功`"
        } else {
            Print-Msg `"`$name 下载失败`"
        }
    } else {
        Print-Msg `"`$name 已存在`"
    }
}


# 预下载模型配置文件
function Get-Model-Config-File {
    Print-Msg `"预下载模型配置文件中`"
    New-Item -ItemType Directory -Path `"./cache`" -Force > `$null
    New-Item -ItemType Directory -Path `"./invokeai/configs/stable-diffusion`" -Force > `$null
    New-Item -ItemType Directory -Path `"./invokeai/configs/controlnet`" -Force > `$null
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_base.yaml`" `"./invokeai/configs/stable-diffusion/sd_xl_base.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_inpaint.yaml`" `"./invokeai/configs/stable-diffusion/sd_xl_inpaint.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/sd_xl_refiner.yaml`" `"./invokeai/configs/stable-diffusion/sd_xl_refiner.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-finetune.yaml`" `"./invokeai/configs/stable-diffusion/v1-finetune.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-finetune_style.yaml`" `"./invokeai/configs/stable-diffusion/v1-finetune_style.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inference-v.yaml`" `"./invokeai/configs/stable-diffusion/v1-inference-v.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inference.yaml`" `"./invokeai/configs/stable-diffusion/v1-inference.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-inpainting-inference.yaml`" `"./invokeai/configs/stable-diffusion/v1-inpainting-inference.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v1-m1-finetune.yaml`" `"./invokeai/configs/stable-diffusion/v1-m1-finetune.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inference-v.yaml`" `"./invokeai/configs/stable-diffusion/v2-inference-v.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inference.yaml`" `"./invokeai/configs/stable-diffusion/v2-inference.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inpainting-inference-v.yaml`" `"./invokeai/configs/stable-diffusion/v2-inpainting-inference-v.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-inpainting-inference.yaml`" `"./invokeai/configs/stable-diffusion/v2-inpainting-inference.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/stable-diffusion/v2-midas-inference.yaml`" `"./invokeai/configs/stable-diffusion/v2-midas-inference.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/controlnet/cldm_v15.yaml`" `"./invokeai/configs/controlnet/cldm_v15.yaml`"
    Download-Config-File `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/configs/controlnet/cldm_v21.yaml`" `"./invokeai/configs/controlnet/cldm_v21.yaml`"
    Print-Msg `"模型配置文件下载完成`"
}

Get-Model-Config-File
Read-Host | Out-Null
"
    Set-Content -Encoding UTF8 -Path "./InvokeAI/download_config.ps1" -Value $content
}

# 帮助文档
function Write-ReadMe {
    $content = "==================================
InvokeAI Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
==================================

这是关于 InvokeAI 的简单使用文档。

使用 InvokeAI Installer 进行安装并安装成功后，将在当前目录生成 InvokeAI 文件夹，以下为文件夹中不同文件 / 文件夹的作用。

cache：缓存文件夹，保存着 Pip / HuggingFace 等缓存文件。
python：Python 的存放路径，InvokeAI 安装的位置在此处，如果需要重装 InvokeAI，可将该文件夹删除，并使用 InvokeAI Installer 重新部署 InvokeAI。请注意，请勿将该 Python 文件夹添加到环境变量，这可能导致不良后果。
invokeai：InvokeAI 存放模型、图片等的文件夹。
activate.ps1：虚拟环境激活脚本，使用该脚本激活虚拟环境后即可使用 Python、Pip、InvokeAI 的命令。
get_invokeai_installer.ps1：获取最新的 InvokeAI Installer 安装脚本，运行后将会在与 InvokeAI 文件夹同级的目录中生成 invokeai_installer.ps1 安装脚本。
update.ps1：更新 InvokeAI 的脚本，可使用该脚本更新 InvokeAI。
launch.ps1：启动 InvokeAI 的脚本。
fix_db.ps1：修复 InvokeAI 数据库脚本，解决删除 InvokeAI 的图片后在界面中出现无效图片的问题。
reinstall_pytorch.ps1：重装 PyTorch 脚本，解决 PyTorch 无法正常使用或者 xFormers 版本不匹配导致无法调用的问题。
download_config.ps1：下载模型配置文件，当删除 invokeai 文件夹后，InvokeAI 将重新下载模型配置文件，但在无代理的情况下可能下载失败，所以可以通过该脚本进行下载。
help.txt：帮助文档。


要启动 InvokeAI，在 InvokeAI 文件夹中找到 launch.ps1 脚本，右键这个脚本，选择使用 PowerShell 运行，等待 InvokeAI 启动完成，启动完成后将在控制台显示访问地址，地址为 http://127.0.0.1:9090，将该地址输入浏览器地址栏并回车后进入 InvokeAI 界面。

InvokeAI 默认的界面语言为英文，在 InvokeAI 左下角的齿轮图标，点进 Settings，在 Language 选项选择简体中文即可将界面语言设置为中文。

使用 InvokeAI 时，建议阅读下列教程，以更快的了解并掌握使用 InvokeAI 的方法。
给所有想学习AI辅助绘画的人的入门课 By Yuno779：https://docs.qq.com/doc/p/9a03673f4a0493b4cd76babc901a49f0e6d52140

脚本为 InvokeAI 设置了 HuggingFace 镜像源，解决国内无法直接访问 HuggingFace，导致 InvokeAI 的模型管理无法从 HuggingFace 下载模型的问题。
如果想自定义 HuggingFace 镜像源，可以在本地创建 mirror.txt 文件，在文件中填写 HuggingFace 镜像源的地址后保存，再次启动脚本时将自动读取配置。
如果需要禁用 HuggingFace 镜像源，则创建 disable_mirror.txt 文件，启动脚本时将不再设置 HuggingFace 镜像源。

以下为可用的 HuggingFace 镜像源地址：
https://hf-mirror.com
https://huggingface.sukaka.top

若要为脚本设置代理，则在代理软件中打开系统代理模式即可，或者在本地创建 proxy.txt 文件，在文件中填写代理地址后保存，再次启动脚本是将自动读取配置。
如果要禁用自动设置代理，可以在本地创建 disable_proxy.txt 文件，启动脚本时将不再自动设置代理。

更多详细的帮助可在下面的链接查看。
InvokeAI Installer 使用帮助：https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md
InvokeAI 官方文档：https://invoke-ai.github.io/InvokeAI
InvokeAI 官方视频教程：https://www.youtube.com/@invokeai
Reddit 社区：https://www.reddit.com/r/invokeai
"

    Set-Content -Encoding UTF8 -Path "./InvokeAI/help.txt" -Value $content
}


# 主程序
function Main {
    Print-Msg "启动 InvokeAI 安装程序"
    Print-Msg "提示: 若出现某个步骤执行失败, 可尝试再次运行 InvokeAI Installer"
    Print-Msg "InvokeAI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/invokeai_installer.md"
    Check-Install
    Print-Msg "添加启动脚本和文档中"
    Write-Launch-Script
    Write-Update-Script
    Write-InvokeAI-DB-Fix-Script
    Write-InvokeAI-Install-Script
    Write-Env-Activate-Script
    Write-PyTorch-ReInstall-Script
    Wirte-Download-Config-Script
    Write-ReadMe
    Print-Msg "InvokeAI 安装结束, 安装路径为 $PSScriptRoot\InvokeAI"
    Print-Msg "关于该 InvokeAI 版本的更新日志：https://github.com/invoke-ai/InvokeAI/releases/latest"
    Print-Msg "帮助文档可在 InvokeAI 文件夹中查看, 双击 help.txt 文件即可查看"
    Print-Msg "退出 InvokeAI Installer"
}


###################


Main
Read-Host | Out-Null
