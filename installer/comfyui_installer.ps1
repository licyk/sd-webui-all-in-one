param (
    [switch]$Help,
    [string]$CorePrefix,
    [string]$InstallPath = (Join-Path -Path "$PSScriptRoot" -ChildPath "ComfyUI"),
    [string]$PyTorchMirrorType,
    [string]$InstallPythonVersion,
    [switch]$UseUpdateMode,
    [switch]$DisablePyPIMirror,
    [switch]$DisableProxy,
    [string]$UseCustomProxy,
    [switch]$DisableUV,
    [switch]$DisableGithubMirror,
    [string]$UseCustomGithubMirror,
    [switch]$BuildMode,
    [switch]$BuildWithUpdate,
    [switch]$BuildWithUpdateNode,
    [switch]$BuildWithLaunch,
    [int]$BuildWithTorch,
    [switch]$BuildWithTorchReinstall,
    [string]$BuildWitchModel,
    [switch]$NoPreDownloadNode,
    [switch]$NoPreDownloadModel,
    [string]$PyTorchPackage,
    [string]$xFormersPackage,
    [switch]$InstallHanamizuki,
    [switch]$NoCleanCache,

    # 仅在管理脚本中生效
    [switch]$DisableUpdate,
    [switch]$DisableHuggingFaceMirror,
    [switch]$UseCustomHuggingFaceMirror,
    [string]$LaunchArg,
    [switch]$EnableShortcut,
    [switch]$DisableCUDAMalloc,
    [switch]$DisableEnvCheck
)
& {
    $target_prefix = $null
    $prefix_list = @("core", "ComfyUI*")
    if ($script:CorePrefix -or (Test-Path "$script:InstallPath/core_prefix.txt")) {
        $origin_core_prefix = if ($script:CorePrefix) { 
            $script:CorePrefix 
        } else { 
            (Get-Content "$script:InstallPath/core_prefix.txt" -Raw).Trim()
        }
        $origin_core_prefix = $origin_core_prefix.TrimEnd('\', '/')
        if ([System.IO.Path]::IsPathRooted($origin_core_prefix)) {
            $from_uri = New-Object System.Uri($script:InstallPath.Replace('\', '/') + '/')
            $to_uri = New-Object System.Uri($origin_core_prefix.Replace('\', '/'))
            $target_prefix = $from_uri.MakeRelativeUri($to_uri).ToString().Trim('/')
        } else {
            $target_prefix = $origin_core_prefix
        }
    } 
    else {
        foreach ($i in $prefix_list) {
            $found_dir = Get-ChildItem -Path $script:InstallPath -Directory -Filter $i -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($found_dir) {
                $target_prefix = $found_dir.Name
                break
            }
        }
    }
    if ([string]::IsNullOrWhiteSpace($target_prefix)) {
        $target_prefix = "core"
    }
    $env:CORE_PREFIX = $target_prefix
}
# ComfyUI Installer 版本和检查更新间隔
$script:COMFYUI_INSTALLER_VERSION = 300
$script:UPDATE_TIME_SPAN = 3600
# SD WebUI All In One 内核最低版本
$script:CORE_MINIMUM_VER = "2.0.6"
# PATH
& {
    $sep = $([System.IO.Path]::PathSeparator)
    $python_path = "$script:InstallPath/python"
    $python_extra_path = "$script:InstallPath/$env:CORE_PREFIX/python"
    $python_script_path = "$script:InstallPath/python/Scripts"
    $python_script_extra_path = "$script:InstallPath/$env:CORE_PREFIX/python/Scripts"
    $python_bin_path = "$script:InstallPath/python/bin"
    $python_bin_extra_path = "$script:InstallPath/$env:CORE_PREFIX/python/bin"
    $git_path = "$script:InstallPath/git/bin"
    $git_extra_path = "$script:InstallPath/$env:CORE_PREFIX/git/bin"
    $env:PATH = "${python_bin_extra_path}${sep}${python_extra_path}${sep}${python_script_extra_path}${sep}${git_extra_path}${sep}${python_bin_path}${sep}${python_path}${sep}${python_script_path}${sep}${git_path}${sep}${env:PATH}"
}
# 环境变量
$env:COMFYUI_PATH = "$script:InstallPath/$env:CORE_PREFIX"
$env:COMFYUI_ROOT = "$script:InstallPath/$env:CORE_PREFIX"
$env:CACHE_HOME = "$script:InstallPath/cache"
$env:PIP_CONFIG_FILE = "nul"
$env:UV_CONFIG_FILE = "nul"
$env:PIP_CACHE_DIR = "$script:InstallPath/cache/pip"
$env:UV_CACHE_DIR = "$script:InstallPath/cache/uv"
$env:PYTHONUTF8 = 1
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = 1
$env:PYTHONNOUSERSITE = 1
$env:PYTHONFAULTHANDLER = 1
$env:PIP_DISABLE_PIP_VERSION_CHECK = 1
$env:PIP_NO_WARN_SCRIPT_LOCATION = 0
$env:SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH = $script:InstallPath
$env:SD_WEBUI_ALL_IN_ONE_LOGGER_NAME = "ComfyUI Installer"
$env:SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL = 20
$env:SD_WEBUI_ALL_IN_ONE_LOGGER_COLOR = 1
$env:SD_WEBUI_ALL_IN_ONE_RETRY_TIMES = 3
$env:SD_WEBUI_ALL_IN_ONE_PATCHER = 0
$env:SD_WEBUI_ALL_IN_ONE_EXTRA_PYPI_MIRROR = 0
$env:SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH = 1
$env:SD_WEBUI_ALL_IN_ONE_SET_CONFIG = 1


# 消息输出
function Write-Log {
    [CmdletBinding()]
    param(
        [string]$Message,
        [ValidateSet("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")]
        [string]$Level = "INFO",
        [string]$Name = "ComfyUI Installer"
    )
    Write-Host "[" -NoNewline
    Write-Host $Name -ForegroundColor Blue -NoNewline
    Write-Host "]-|" -NoNewline
    Write-Host (Get-Date -Format "HH:mm:ss") -ForegroundColor Gray -NoNewline
    Write-Host "|-" -NoNewline
    switch ($Level) {
        "DEBUG"    { Write-Host "DEBUG" -ForegroundColor Cyan -NoNewline }
        "INFO"     { Write-Host "INFO" -ForegroundColor Green -NoNewline }
        "WARNING"  { Write-Host "WARNING" -ForegroundColor Yellow -NoNewline }
        "ERROR"    { Write-Host "ERROR" -ForegroundColor Red -NoNewline }
        "CRITICAL" { Write-Host "CRITICAL" -ForegroundColor White -BackgroundColor Red -NoNewline }
    }
    Write-Host ": $Message"
}


# 写入文本文件
function Write-FileWithStreamWriter {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true)][string]$Value,
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][ValidateSet("GBK", "UTF8", "UTF8BOM")][string]$Encoding
    )
    process {
        try {
            $encode = $null
            switch ($Encoding) {
                "GBK" {
                    if ($PSVersionTable.PSVersion.Major -ge 6) {
                        [System.Text.Encoding]::RegisterProvider([System.Text.CodePagesEncodingProvider]::Instance)
                    }
                    $encode = [System.Text.Encoding]::GetEncoding("GBK")
                }
                "UTF8" {
                    $encode = New-Object System.Text.UTF8Encoding($false)
                }
                "UTF8BOM" {
                    $encode = New-Object System.Text.UTF8Encoding($true)
                }
            }
            $absolute_path = [System.IO.Path]::GetFullPath($Path)
            $writer = New-Object System.IO.StreamWriter($absolute_path, $false, $encode)
            try {
                $writer.Write($Value)
            }
            finally {
                if ($null -ne $writer) {
                    $writer.Close()
                    $writer.Dispose()
                }
            }
        }
        catch {
            Write-Log "写入文件时发生错误: $($_.Exception.Message)" -Level ERROR
        }
    }
}


# 获取内核路径前缀状态
function Get-CorePrefixStatus {
    if ((Test-Path "$PSScriptRoot/core_prefix.txt") -or ($script:CorePrefix)) {
        Write-Log "检测到 core_prefix.txt 配置文件 / -CorePrefix 命令行参数, 使用自定义内核路径前缀"
        if ($script:CorePrefix) {
            $origin_core_prefix = $script:CorePrefix
        } else {
            $origin_core_prefix = (Get-Content "$PSScriptRoot/core_prefix.txt" -Raw).Trim()
        }
        if ([System.IO.Path]::IsPathRooted($origin_core_prefix.Trim('/').Trim('\'))) {
            Write-Log "转换绝对路径为内核路径前缀: $origin_core_prefix -> $env:CORE_PREFIX"
        }
    }
    Write-Log "当前内核路径前缀: $env:CORE_PREFIX"
    Write-Log "完整内核路径: $script:InstallPath\$env:CORE_PREFIX"
}


# 显示 ComfyUI Installer 版本
function Get-Version {
    $ver = $([string]$script:COMFYUI_INSTALLER_VERSION).ToCharArray()
    $major = ($ver[0..($ver.Length - 3)])
    $minor = $ver[-2]
    $micro = $ver[-1]
    Write-Log "ComfyUI Installer 版本: v${major}.${minor}.${micro}"
}


# PyPI 镜像源状态
function Set-PyPIMirror {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]$ArrayList)
    if ((!(Test-Path "$PSScriptRoot/disable_pypi_mirror.txt")) -and (!($script:DisablePyPIMirror))) {
        Write-Log "使用 PyPI 镜像源"
    } else {
        Write-Log "检测到 disable_pypi_mirror.txt 配置文件 / -DisablePyPIMirror 命令行参数, 已将 PyPI 源切换至官方源"
        $ArrayList.Add("--no-pypi-mirror") | Out-Null
    }
}


# 代理配置
function Set-Proxy {
    $env:NO_PROXY = "localhost,127.0.0.1,::1"
    if ((Test-Path "$PSScriptRoot/disable_proxy.txt") -or ($script:DisableProxy)) {
        $env:SD_WEBUI_ALL_IN_ONE_PROXY = 0
        Write-Log "检测到本地存在 disable_proxy.txt 代理配置文件 / -DisableProxy 命令行参数, 禁用自动设置代理"
        return
    }
    if ((Test-Path "$PSScriptRoot/proxy.txt") -or ($script:UseCustomProxy)) {
        if ($script:UseCustomProxy) {
            $proxy_value = $script:UseCustomProxy
        } else {
            $proxy_value = (Get-Content "$PSScriptRoot/proxy.txt" -Raw).Trim()
        }
        $env:HTTP_PROXY = $proxy_value
        $env:HTTPS_PROXY = $proxy_value
        Write-Log "检测到本地存在 proxy.txt 代理配置文件 / -UseCustomProxy 命令行参数, 已读取代理配置文件并设置代理"
    }
    $env:SD_WEBUI_ALL_IN_ONE_PROXY = 1
    Write-Log "使用自动检测代理模式进行代理配置"
}


# 设置 uv 的使用状态
function Set-uv {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]$ArrayList)
    if (($script:DisableUV) -or (Test-Path "$PSScriptRoot/disable_uv.txt")) {
        Write-Log "检测到 disable_uv.txt 配置文件 / -DisableUV 命令行参数, 已禁用 uv, 使用 Pip 作为 Python 包管理器"
        $ArrayList.Add("--no-uv") | Out-Null
    } else {
        Write-Log "默认启用 uv 作为 Python 包管理器, 加快 Python 软件包的安装速度"
        Write-Log "当 uv 安装 Python 软件包失败时, 将自动切换成 Pip 重试 Python 软件包的安装"
    }
}

# 设置 Github 镜像源
function Set-GithubMirror {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]$ArrayList)
    if (Test-Path "$script:InstallPath/.gitconfig") {
        Remove-Item -Path "$script:InstallPath/.gitconfig" -Force -Recurse
    }
    if (($script:DisableGithubMirror) -or (Test-Path "$PSScriptRoot/disable_gh_mirror.txt")) {
        Write-Log "检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件 / -DisableGithubMirror 命令行参数, 禁用 Github 镜像源"
        $ArrayList.Add("--no-github-mirror") | Out-Null
        return
    }
    if (($script:UseCustomGithubMirror) -or (Test-Path "$PSScriptRoot/gh_mirror.txt")) {
        if ($script:UseCustomGithubMirror) {
            $github_mirror = $script:UseCustomGithubMirror
        } else {
            $github_mirror = (Get-Content "$PSScriptRoot/gh_mirror.txt" -Raw).Trim()
        }
        Write-Log "检测到本地存在 gh_mirror.txt Github 镜像源配置文件 / -UseCustomGithubMirror 命令行参数, 已读取 Github 镜像源配置文件并设置 Github 镜像源"
        $ArrayList.Add("--custom-github-mirror") | Out-Null
        $ArrayList.Add($github_mirror) | Out-Null
        return
    }
}

function Get-LaunchCoreArgs {
    $launch_params = New-Object System.Collections.ArrayList
    Set-uv $launch_params
    Set-PyPIMirror $launch_params
    Set-Proxy
    Set-GithubMirror $launch_params
    if ($script:NoPreDownloadModel) {
        $launch_params.Add("--no-pre-download-model") | Out-Null
    }
    if ($script:NoPreDownloadNode) {
        $launch_params.Add("--no-pre-download-extension") | Out-Null
    }
    if ($script:PyTorchMirrorType) {
        $launch_params.Add("--pytorch-mirror-type") | Out-Null
        $launch_params.Add($script:PyTorchMirrorType) | Out-Null
    }
    if ($script:PyTorchPackage) {
        $launch_params.Add("--custom-pytorch-package") | Out-Null
        $launch_params.Add($script:PyTorchPackage) | Out-Null
    }
    if ($script:xFormersPackage) {
        $launch_params.Add("--custom-xformers-package") | Out-Null
        $launch_params.Add($script:xFormersPackage) | Out-Null
    }
    return $launch_params
}

function Update-SDWebUiAllInOne {
    $content = "
import re
from importlib.metadata import version


def compare_versions(version1: str, version2: str) -> int:
    try:
        nums1 = re.sub(r'[a-zA-Z]+', '', version1).replace('-', '.').replace('+', '.').split('.')
        nums2 = re.sub(r'[a-zA-Z]+', '', version2).replace('-', '.').replace('+', '.').split('.')
    except Exception:
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


def is_core_need_update(core_minimum_ver: str) -> bool:
    try:
        core_ver = version('sd-webui-all-in-one')
    except Exception:
        return True
    return compare_versions(core_ver, core_minimum_ver) < 0


if __name__ == '__main__':
    print(is_core_need_update('$script:CORE_MINIMUM_VER'))
".Trim()

    $pip_index_url = "https://pypi.python.org/simple"
    if ((!($script:DisablePyPIMirror)) -and (!(Test-Path "$PSScriptRoot/disable_pypi_mirror.txt"))) {
        $pip_index_url = "https://mirrors.cloud.tencent.com/pypi/simple"
    }
    Write-Log "检测 SD WebUI All In One 内核是否需要更新"
    $status = $(python -c "$content")
    if ($status -ne "True") {
        Write-Log "SD WebUI All In One 内核无需更新"
        return
    }
    Write-Log "更新 SD WebUI All In One 内核中"
    & python -m pip install -U "sd-webui-all-in-one>=$script:CORE_MINIMUM_VER" --index-url $pip_index_url
    if (!($?)) {
        Write-Log "SD WebUI All In One 内核更新失败, Installer 部分功能将无法使用" -Level ERROR
        if (!($script:BuildMode)) { Read-Host | Out-Null }
        exit 1
    }
    Write-Log "SD WebUI All In One 内核更新成功"
}



function Install-ArchiveResource {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)] [string[]]$Urls,        # 下载地址列表
        [Parameter(Mandatory=$true)] [string]$ResourceName,  # 资源名称
        [Parameter(Mandatory=$true)] [string]$DestPath,      # 最终安装路径
        [Parameter(Mandatory=$true)] [string]$ZipName        # 压缩包文件名
    )

    $cache_zip = "$env:CACHE_HOME/$ZipName"
    $cache_tmp_folder = "$env:CACHE_HOME/$($ResourceName)_tmp"
    $success = $false

    for ($i = 0; $i -lt $Urls.Length; $i++) {
        Write-Log "正在下载 $ResourceName"
        try {
            $web_request_params = @{
                Uri = $Urls[$i]
                UseBasicParsing = $true
                OutFile = $cache_zip
            }
            Invoke-WebRequest @web_request_params
            $success = $true
            break
        }
        catch {
            if ($i -lt ($Urls.Length - 1)) {
                Write-Log "重试下载 $ResourceName 中" -Level WARNING
            }
        }
    }

    if (-not $success) {
        Write-Log "$ResourceName 安装失败, 终止安装进程, 可尝试重新运行 ComfyUI Installer 重试失败的安装" -Level ERROR
        if (!($script:BuildMode)) { Read-Host | Out-Null }
        exit 1
    }

    if (Test-Path $cache_tmp_folder) {
        Remove-Item -Path $cache_tmp_folder -Force -Recurse
    }

    Write-Log "正在解压 $ResourceName"
    Expand-Archive -Path $cache_zip -DestinationPath $cache_tmp_folder -Force

    $inner_items = Get-ChildItem -Path $cache_tmp_folder
    if ($inner_items.Count -eq 1 -and $inner_items[0].PSIsContainer) {
        $move_source = $inner_items[0].FullName
    } else {
        $move_source = $cache_tmp_folder
    }

    $parent_dir = Split-Path -Path $DestPath -Parent
    if (-not (Test-Path $parent_dir)) {
        New-Item -ItemType Directory -Path $parent_dir -Force > $null
    }

    if (Test-Path $DestPath) {
        $random_string = [Guid]::NewGuid().ToString().Substring(0, 8)
        $old_backup = Join-Path $env:CACHE_HOME "backup_$random_string"
        Move-Item -Path $DestPath -Destination $old_backup -Force
    }

    Move-Item -Path $move_source -Destination $DestPath -Force

    Remove-Item -Path $cache_tmp_folder -Force -Recurse -ErrorAction SilentlyContinue
    Remove-Item -Path $cache_zip -Force -ErrorAction SilentlyContinue

    Write-Log "$ResourceName 安装成功"
}

function Get-PythonDownloadUrl {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true)]
        [string]$Version,
        [Parameter(Mandatory = $true)]
        [string]$Platform,
        [Parameter(Mandatory = $true)]
        [string]$Arch
    )

    $python_data = @(
        @{ Name = "cpython-3.10.19+20260203-aarch64-unknown-linux-gnu-install_only.zip"; Ver = "3.10"; Platform = "linux"; Arch = "aarch64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/linux/aarch64/cpython-3.10.19+20260203-aarch64-unknown-linux-gnu-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/linux/aarch64/cpython-3.10.19+20260203-aarch64-unknown-linux-gnu-install_only.zip") }
        @{ Name = "cpython-3.11.14+20260203-aarch64-unknown-linux-gnu-install_only.zip"; Ver = "3.11"; Platform = "linux"; Arch = "aarch64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/linux/aarch64/cpython-3.11.14+20260203-aarch64-unknown-linux-gnu-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/linux/aarch64/cpython-3.11.14+20260203-aarch64-unknown-linux-gnu-install_only.zip") }
        @{ Name = "cpython-3.12.12+20260203-aarch64-unknown-linux-gnu-install_only.zip"; Ver = "3.12"; Platform = "linux"; Arch = "aarch64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/linux/aarch64/cpython-3.12.12+20260203-aarch64-unknown-linux-gnu-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/linux/aarch64/cpython-3.12.12+20260203-aarch64-unknown-linux-gnu-install_only.zip") }
        @{ Name = "cpython-3.13.12+20260203-aarch64-unknown-linux-gnu-install_only.zip"; Ver = "3.13"; Platform = "linux"; Arch = "aarch64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/linux/aarch64/cpython-3.13.12+20260203-aarch64-unknown-linux-gnu-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/linux/aarch64/cpython-3.13.12+20260203-aarch64-unknown-linux-gnu-install_only.zip") }
        @{ Name = "cpython-3.14.3+20260203-aarch64-unknown-linux-gnu-install_only.zip"; Ver = "3.14"; Platform = "linux"; Arch = "aarch64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/linux/aarch64/cpython-3.14.3+20260203-aarch64-unknown-linux-gnu-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/linux/aarch64/cpython-3.14.3+20260203-aarch64-unknown-linux-gnu-install_only.zip") }
        @{ Name = "cpython-3.10.19+20260203-x86_64-unknown-linux-gnu-install_only.zip"; Ver = "3.10"; Platform = "linux"; Arch = "amd64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/linux/amd64/cpython-3.10.19+20260203-x86_64-unknown-linux-gnu-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/linux/amd64/cpython-3.10.19+20260203-x86_64-unknown-linux-gnu-install_only.zip") }
        @{ Name = "cpython-3.11.14+20260203-x86_64-unknown-linux-gnu-install_only.zip"; Ver = "3.11"; Platform = "linux"; Arch = "amd64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/linux/amd64/cpython-3.11.14+20260203-x86_64-unknown-linux-gnu-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/linux/amd64/cpython-3.11.14+20260203-x86_64-unknown-linux-gnu-install_only.zip") }
        @{ Name = "cpython-3.12.12+20260203-x86_64-unknown-linux-gnu-install_only.zip"; Ver = "3.12"; Platform = "linux"; Arch = "amd64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/linux/amd64/cpython-3.12.12+20260203-x86_64-unknown-linux-gnu-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/linux/amd64/cpython-3.12.12+20260203-x86_64-unknown-linux-gnu-install_only.zip") }
        @{ Name = "cpython-3.13.12+20260203-x86_64-unknown-linux-gnu-install_only.zip"; Ver = "3.13"; Platform = "linux"; Arch = "amd64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/linux/amd64/cpython-3.13.12+20260203-x86_64-unknown-linux-gnu-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/linux/amd64/cpython-3.13.12+20260203-x86_64-unknown-linux-gnu-install_only.zip") }
        @{ Name = "cpython-3.14.3+20260203-x86_64-unknown-linux-gnu-install_only.zip"; Ver = "3.14"; Platform = "linux"; Arch = "amd64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/linux/amd64/cpython-3.14.3+20260203-x86_64-unknown-linux-gnu-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/linux/amd64/cpython-3.14.3+20260203-x86_64-unknown-linux-gnu-install_only.zip") }
        @{ Name = "cpython-3.10.19+20260203-aarch64-apple-darwin-install_only.zip"; Ver = "3.10"; Platform = "macos"; Arch = "aarch64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/macos/aarch64/cpython-3.10.19+20260203-aarch64-apple-darwin-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/macos/aarch64/cpython-3.10.19+20260203-aarch64-apple-darwin-install_only.zip") }
        @{ Name = "cpython-3.11.14+20260203-aarch64-apple-darwin-install_only.zip"; Ver = "3.11"; Platform = "macos"; Arch = "aarch64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/macos/aarch64/cpython-3.11.14+20260203-aarch64-apple-darwin-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/macos/aarch64/cpython-3.11.14+20260203-aarch64-apple-darwin-install_only.zip") }
        @{ Name = "cpython-3.12.12+20260203-aarch64-apple-darwin-install_only.zip"; Ver = "3.12"; Platform = "macos"; Arch = "aarch64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/macos/aarch64/cpython-3.12.12+20260203-aarch64-apple-darwin-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/macos/aarch64/cpython-3.12.12+20260203-aarch64-apple-darwin-install_only.zip") }
        @{ Name = "cpython-3.13.12+20260203-aarch64-apple-darwin-install_only.zip"; Ver = "3.13"; Platform = "macos"; Arch = "aarch64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/macos/aarch64/cpython-3.13.12+20260203-aarch64-apple-darwin-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/macos/aarch64/cpython-3.13.12+20260203-aarch64-apple-darwin-install_only.zip") }
        @{ Name = "cpython-3.14.3+20260203-aarch64-apple-darwin-install_only.zip"; Ver = "3.14"; Platform = "macos"; Arch = "aarch64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/macos/aarch64/cpython-3.14.3+20260203-aarch64-apple-darwin-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/macos/aarch64/cpython-3.14.3+20260203-aarch64-apple-darwin-install_only.zip") }
        @{ Name = "cpython-3.10.19+20260203-x86_64-apple-darwin-install_only.zip"; Ver = "3.10"; Platform = "macos"; Arch = "amd64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/macos/amd64/cpython-3.10.19+20260203-x86_64-apple-darwin-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/macos/amd64/cpython-3.10.19+20260203-x86_64-apple-darwin-install_only.zip") }
        @{ Name = "cpython-3.11.14+20260203-x86_64-apple-darwin-install_only.zip"; Ver = "3.11"; Platform = "macos"; Arch = "amd64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/macos/amd64/cpython-3.11.14+20260203-x86_64-apple-darwin-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/macos/amd64/cpython-3.11.14+20260203-x86_64-apple-darwin-install_only.zip") }
        @{ Name = "cpython-3.12.12+20260203-x86_64-apple-darwin-install_only.zip"; Ver = "3.12"; Platform = "macos"; Arch = "amd64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/macos/amd64/cpython-3.12.12+20260203-x86_64-apple-darwin-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/macos/amd64/cpython-3.12.12+20260203-x86_64-apple-darwin-install_only.zip") }
        @{ Name = "cpython-3.13.12+20260203-x86_64-apple-darwin-install_only.zip"; Ver = "3.13"; Platform = "macos"; Arch = "amd64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/macos/amd64/cpython-3.13.12+20260203-x86_64-apple-darwin-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/macos/amd64/cpython-3.13.12+20260203-x86_64-apple-darwin-install_only.zip") }
        @{ Name = "cpython-3.14.3+20260203-x86_64-apple-darwin-install_only.zip"; Ver = "3.14"; Platform = "macos"; Arch = "amd64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/macos/amd64/cpython-3.14.3+20260203-x86_64-apple-darwin-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/macos/amd64/cpython-3.14.3+20260203-x86_64-apple-darwin-install_only.zip") }
        @{ Name = "cpython-3.11.14+20260203-aarch64-pc-windows-msvc-install_only.zip"; Ver = "3.11"; Platform = "windows"; Arch = "aarch64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/windows/aarch64/cpython-3.11.14+20260203-aarch64-pc-windows-msvc-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/windows/aarch64/cpython-3.11.14+20260203-aarch64-pc-windows-msvc-install_only.zip") }
        @{ Name = "cpython-3.12.12+20260203-aarch64-pc-windows-msvc-install_only.zip"; Ver = "3.12"; Platform = "windows"; Arch = "aarch64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/windows/aarch64/cpython-3.12.12+20260203-aarch64-pc-windows-msvc-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/windows/aarch64/cpython-3.12.12+20260203-aarch64-pc-windows-msvc-install_only.zip") }
        @{ Name = "cpython-3.13.12+20260203-aarch64-pc-windows-msvc-install_only.zip"; Ver = "3.13"; Platform = "windows"; Arch = "aarch64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/windows/aarch64/cpython-3.13.12+20260203-aarch64-pc-windows-msvc-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/windows/aarch64/cpython-3.13.12+20260203-aarch64-pc-windows-msvc-install_only.zip") }
        @{ Name = "cpython-3.14.3+20260203-aarch64-pc-windows-msvc-install_only.zip"; Ver = "3.14"; Platform = "windows"; Arch = "aarch64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/windows/aarch64/cpython-3.14.3+20260203-aarch64-pc-windows-msvc-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/windows/aarch64/cpython-3.14.3+20260203-aarch64-pc-windows-msvc-install_only.zip") }
        @{ Name = "cpython-3.10.19+20260203-x86_64-pc-windows-msvc-install_only.zip"; Ver = "3.10"; Platform = "windows"; Arch = "amd64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/windows/amd64/cpython-3.10.19+20260203-x86_64-pc-windows-msvc-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/windows/amd64/cpython-3.10.19+20260203-x86_64-pc-windows-msvc-install_only.zip") }
        @{ Name = "cpython-3.11.14+20260203-x86_64-pc-windows-msvc-install_only.zip"; Ver = "3.11"; Platform = "windows"; Arch = "amd64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/windows/amd64/cpython-3.11.14+20260203-x86_64-pc-windows-msvc-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/windows/amd64/cpython-3.11.14+20260203-x86_64-pc-windows-msvc-install_only.zip") }
        @{ Name = "cpython-3.12.12+20260203-x86_64-pc-windows-msvc-install_only.zip"; Ver = "3.12"; Platform = "windows"; Arch = "amd64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/windows/amd64/cpython-3.12.12+20260203-x86_64-pc-windows-msvc-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/windows/amd64/cpython-3.12.12+20260203-x86_64-pc-windows-msvc-install_only.zip") }
        @{ Name = "cpython-3.13.12+20260203-x86_64-pc-windows-msvc-install_only.zip"; Ver = "3.13"; Platform = "windows"; Arch = "amd64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/windows/amd64/cpython-3.13.12+20260203-x86_64-pc-windows-msvc-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/windows/amd64/cpython-3.13.12+20260203-x86_64-pc-windows-msvc-install_only.zip") }
        @{ Name = "cpython-3.14.3+20260203-x86_64-pc-windows-msvc-install_only.zip"; Ver = "3.14"; Platform = "windows"; Arch = "amd64"; Url = @("https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/python/windows/amd64/cpython-3.14.3+20260203-x86_64-pc-windows-msvc-install_only.zip", "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/python/windows/amd64/cpython-3.14.3+20260203-x86_64-pc-windows-msvc-install_only.zip") }
    )

    $result = $python_data | Where-Object { $_.Ver -eq $Version -and $_.Platform -eq $Platform -and $_.Arch -eq $Arch }
    if ($result) {
        return [PSCustomObject]$result | Select-Object Name, Url
    }
    else {
        Write-Log "未找到匹配的 Python: $Version, 平台: $Platform, 架构: $Arch" -Level WARNING
        return $null
    }
}

function Get-CurrentPlatform {
    if ([System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)) {
        return "windows"
    }
    elseif ([System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Linux)) {
        return "linux"
    }
    elseif ([System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::OSX)) {
        return "macos"
    }
    else {
        return "unknown"
    }
}

function Get-CurrentArchitecture {
    $architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLower()
    if ($architecture -eq "x64") {
        return "amd64" 
    }
    elseif ($architecture -eq "arm64") {
        return "aarch64"
    }
    else {
        return $architecture 
    }
}

function Join-NormalizedPath {
    $joined = $args[0]
    for ($i = 1; $i -lt $args.Count; $i++) { $joined = Join-Path $joined $args[$i] }
    return $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($joined).TrimEnd('\', '/')
}

function Get-NormalizedFilePath {
    [CmdletBinding()]
    param ([Parameter(Mandatory = $false)][string]$Filepath)
    if (-not [string]::IsNullOrWhiteSpace($Filepath)) { return Join-NormalizedPath $Filepath }
    return $null
}

# 安装 Python
function Install-Python {
    if ($script:InstallPythonVersion) {
        $py_ver = $script:InstallPythonVersion
    }
    else {
        $py_ver = "3.12"
    }
    $platform = Get-CurrentPlatform
    $arch = Get-CurrentArchitecture
    $py_info = Get-PythonDownloadUrl -Version $py_ver -Platform $platform -Arch $arch
    if ($py_info) {
        $zip_name = $py_info.Name
        $urls = $py_info.Url
    } else {
        Write-Log "不支持当前的平台安装: ($platform, $arch)"
        if (!($script:BuildMode)) { Read-Host | Out-Null }
        exit 1
    }
    $python_cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($python_cmd) {
        $python_path_prefix = Join-NormalizedPath $script:InstallPath "python"
        $python_extra_path_prefix = Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX "python"
        $python_cmd = Get-NormalizedFilePath $python_cmd.Path
        if (($python_cmd) -and (($python_cmd.ToString().StartsWith($python_path_prefix, [System.StringComparison]::OrdinalIgnoreCase)) -or ($python_cmd.ToString().StartsWith($python_extra_path_prefix, [System.StringComparison]::OrdinalIgnoreCase)))) {
            Write-Log "python 已安装"
            return
        }
    }
    Install-ArchiveResource -Urls $urls -ResourceName "Python" -DestPath "$script:InstallPath/python" -ZipName $zip_name
}

function Invoke-SmartCommand {
    [CmdletBinding()]
    param (
        [string]$Command,
        [string[]]$Arguments
    )
    
    if ((Get-CurrentPlatform -ne "windows") -and (Get-Command sudo -ErrorAction SilentlyContinue)) {
        & sudo $Command @Arguments
    } else {
        & $Command @Arguments
    }
}

# 安装 Git
function Install-Git {
    $platform = Get-CurrentPlatform
    $arch = Get-CurrentArchitecture
    Write-Log "检测 Git 是否已安装"
    if ($platform -eq "windows") {
        $git_cmd = Get-Command git -ErrorAction SilentlyContinue
        if ($git_cmd) {
            $git_path_prefix = Join-NormalizedPath $script:InstallPath "git"
            $git_extra_path_prefix = Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX "git"
            $git_cmd = Get-NormalizedFilePath $git_cmd.Path
            if (($git_cmd) -and (($git_cmd.ToString().StartsWith($git_path_prefix, [System.StringComparison]::OrdinalIgnoreCase)) -or ($git_cmd.ToString().StartsWith($git_extra_path_prefix, [System.StringComparison]::OrdinalIgnoreCase)))) {
                Write-Log "Git 已安装"
                return
            }
        }
        if ($arch -eq "amd64") {
            $urls = @(
                "https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/git/windows/amd64/git-2.53.0-x86_64.zip",
                "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/git/windows/amd64/git-2.53.0-x86_64.zip"
            )
        }
        elseif ($arch -eq "arm64") {
            $urls = @(
                "https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/git/windows/aarch64/git-2.53.0-aarch64.zip",
                "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/git/windows/aarch64/git-2.53.0-aarch64.zip"
            )
        }
        else {
            Write-Log "不支持当前的平台安装: ($platform, $arch)"
            if (!($script:BuildMode)) { Read-Host | Out-Null }
            exit 1
        }
        Install-ArchiveResource -Urls $urls -ResourceName "Git" -DestPath (Join-NormalizedPath $script:InstallPath "git") -ZipName "PortableGit.zip"
    }
    elseif ($platform -eq "linux") {
        if (Get-Command git -ErrorAction SilentlyContinue) {
            Write-Log "Git 已安装"
            return
        }
        try {
            Write-Log "安装 Git 中"
            if (Get-Command apt -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "apt" -Arguments $("install", "git", "-y"); return }
            if (Get-Command yum -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "yum" -Arguments $("install", "git", "-y"); return }
            if (Get-Command apk -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "apk" -Arguments $("add", "git"); return }
            if (Get-Command pacman -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "pacman" -Arguments $("-Syyu", "git", "--noconfirm"); return }
            if (Get-Command zypper -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "zypper" -Arguments $("install", "git", "-y"); return }
            if (Get-Command nix-env -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "nix-channel" -Arguments $("--update"); Invoke-SmartCommand -Command "nix-env" -Arguments $("-iA", "git"); return }
        }
        catch {
            Write-Log "安装 Git 失败, 终止安装进程, 可尝试重新运行 ComfyUI Installer 重试失败的安装" -Level ERROR
            if (!($script:BuildMode)) { Read-Host | Out-Null }
            exit 1
        }
    }
    elseif ($platform -eq "macos") {
        if (Get-Command git -ErrorAction SilentlyContinue) {
            Write-Log "Git 已安装"
            return
        }
        try {
            Write-Log "安装 Git 中"
            if (Get-Command apt -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "brew" -Arguments $("install", "git", "-y"); return }
            if (Get-Command port -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "port" -Arguments $("install", "git", "-y"); return }
            if (Get-Command xcode-select -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "xcode-select" -Arguments $("--install"); return }
        }
        catch {
            Write-Log "安装 Git 失败, 终止安装进程, 可尝试重新运行 ComfyUI Installer 重试失败的安装" -Level ERROR
            if (!($script:BuildMode)) { Read-Host | Out-Null }
            exit 1
        }
    }
}


# 下载 Aria2
function Install-WindowsAria2 {
    $urls = @(
        "https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/aria2c.exe",
        "https://huggingface.co/licyk/invokeai-core-model/resolve/main/pypatchmatch/aria2c.exe"
    )
    $i = 0

    ForEach ($url in $urls) {
        Write-Log "正在下载 Aria2"
        try {
            $web_request_params = @{
                Uri = $url
                UseBasicParsing = $true
                OutFile = (Join-NormalizedPath $env:CACHE_HOME "aria2c.exe")
            }
            Invoke-WebRequest @web_request_params
            break
        }
        catch {
            $i += 1
            if ($i -lt $urls.Length) {
                Write-Log "重试下载 Aria2 中" -Level WARNING
            } else {
                Write-Log "Aria2 安装失败, 终止 ComfyUI 安装进程, 可尝试重新运行 ComfyUI Installer 重试失败的安装" -Level ERROR
                if (!($script:BuildMode)) { Read-Host | Out-Null }
                exit 1
            }
        }
    }

    Move-Item -Path "$env:CACHE_HOME/aria2c.exe" -Destination "$script:InstallPath/git/bin/aria2c.exe" -Force
    Write-Log "Aria2 下载成功"
}

function Install-Aria2 {
    $platform = Get-CurrentPlatform
    if ($platform -eq "windows") {
        $aria2_cmd = Get-Command aria2c -ErrorAction SilentlyContinue
        if ($aria2_cmd) {
            $aria2_path_prefix = Join-NormalizedPath $script:InstallPath "git"
            $aria2_extra_path_prefix = Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX "git"
            $aria2_cmd = Get-NormalizedFilePath $aria2_cmd.Path
            if (($aria2_cmd) -and (($aria2_cmd.ToString().StartsWith($aria2_path_prefix, [System.StringComparison]::OrdinalIgnoreCase)) -or ($aria2_cmd.ToString().StartsWith($aria2_extra_path_prefix, [System.StringComparison]::OrdinalIgnoreCase)))) {
                Write-Log "aria2 已安装"
                return
            }
        }
        Install-WindowsAria2
    }
    elseif ($platform -eq "linux") {
        if (Get-Command aria2c -ErrorAction SilentlyContinue) {
            Write-Log "Aria2 已安装"
            return
        }
        try {
            Write-Log "安装 Aria2 中"
            if (Get-Command apt -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "apt" -Arguments $("install", "aria2", "-y"); return }
            if (Get-Command yum -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "yum" -Arguments $("install", "aria2", "-y"); return }
            if (Get-Command apk -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "apk" -Arguments $("add", "aria2"); return }
            if (Get-Command pacman -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "pacman" -Arguments $("-Syyu", "aria2", "--noconfirm"); return }
            if (Get-Command zypper -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "zypper" -Arguments $("install", "aria2", "-y"); return }
            if (Get-Command nix-env -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "nix-channel" -Arguments $("--update"); Invoke-SmartCommand -Command "nix-env" -Arguments $("-iA", "aria2"); return }
        }
        catch {
            Write-Log "安装 Aria2 失败, 终止安装进程, 可尝试重新运行 ComfyUI Installer 重试失败的安装" -Level ERROR
            if (!($script:BuildMode)) { Read-Host | Out-Null }
            exit 1
        }
    }
    elseif ($platform -eq "macos") {
        if (Get-Command aria2c -ErrorAction SilentlyContinue) {
            Write-Log "Aria2 已安装"
            return
        }
        try {
            Write-Log "安装 Aria2 中"
            if (Get-Command apt -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "brew" -Arguments $("install", "aria2", "-y"); return }
            if (Get-Command port -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "port" -Arguments $("install", "aria2", "-y"); return }
        }
        catch {
            Write-Log "安装 Aria2 失败, 终止安装进程, 可尝试重新运行 ComfyUI Installer 重试失败的安装" -Level ERROR
            if (!($script:BuildMode)) { Read-Host | Out-Null }
            exit 1
        }
    }
}

# 安装
function Invoke-Installation {
    New-Item -ItemType Directory -Path $script:InstallPath -Force > $null
    New-Item -ItemType Directory -Path $env:CACHE_HOME -Force > $null

    Write-Log "检测是否安装 Python"
    Install-Python

    Write-Log "检测是否安装 Git"
    Install-Git

    Write-Log "检测是否安装 Aria2"
    Install-Aria2

    Update-SDWebUiAllInOne
    $launch_params = Get-LaunchCoreArgs

    & python -m sd_webui_all_in_one.cli_manager.main comfyui install $launch_params
    if (!($?)) {
        Write-Log "运行 SD WebUI All In One 安装 ComfyUI 时发生了错误, 终止 ComfyUI 安装进程, 可尝试重新运行 ComfyUI Installer 重试失败的安装" -Level ERROR
        if (!($script:BuildMode)) { Read-Host | Out-Null }
        exit 1
    }
    if (!(Test-Path "$script:InstallPath/launch_args.txt")) {
        Write-Log "设置默认 ComfyUI 启动参数"
        $content = "--auto-launch --preview-method auto --disable-cuda-malloc"
        Write-FileWithStreamWriter -Encoding UTF8 "$script:InstallPath/launch_args.txt" -Value $content
    }

    if (!($script:NoCleanCache)) {
        Write-Log "清理下载 Python 软件包的缓存中"
        & python -m pip cache purge
        & uv cache clean
    }

    Set-Content -Encoding UTF8 -Path "$script:InstallPath/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
}


# 通用模块脚本
function Write-ModulesScript {
    $content = "
param (
    [string]`$CorePrefix,
    [switch]`$DisableUpdate,
    [switch]`$BuildMode,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableHuggingFaceMirror,
    [string]`$UseCustomHuggingFaceMirror,
    [switch]`$DisableGithubMirror,
    [string]`$UseCustomGithubMirror,
    [switch]`$DisableUV,
    [switch]`$DisableCUDAMalloc
)
# ComfyUI Installer 版本和检查更新间隔
`$script:COMFYUI_INSTALLER_VERSION = $script:COMFYUI_INSTALLER_VERSION
`$script:UPDATE_TIME_SPAN = $script:UPDATE_TIME_SPAN
# SD WebUI All In One 内核最低版本
`$script:CORE_MINIMUM_VER = `"$script:CORE_MINIMUM_VER`"


# 初始化环境变量
function Initialize-EnvPath {
    Write-Log `"初始化环境变量`"
    `$python_path = Join-NormalizedPath `$PSScriptRoot `"python`"
    `$python_extra_path = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX `"python`"
    `$python_scripts_path = Join-NormalizedPath `$PSScriptRoot `"python`" `"Scripts`"
    `$python_scripts_extra_path = Join-NormalizedPath `"`$PSScriptRoot `$env:CORE_PREFIX `"python`" `"Scripts`"
    `$python_scripts_path = Join-NormalizedPath `$PSScriptRoot `"python`" `"bin`"
    `$python_scripts_extra_path = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX `"python`" `"bin`"
    `$git_path = Join-NormalizedPath `$PSScriptRoot `"git`" `"bin`"
    `$git_extra_path = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX `"git`" `"bin`"
    `$sep = `$([System.IO.Path]::PathSeparator)
    `$env:PATH = `"`${python_bin_extra_path}`${sep}`${python_extra_path}`${sep}`${python_script_extra_path}`${sep}`${git_extra_path}`${sep}`${python_bin_path}`${sep}`${python_path}`${sep}`${python_script_path}`${sep}`${git_path}`${sep}`${env:PATH}`"

    `$env:UV_CONFIG_FILE = Join-NormalizedPath `$PSScriptRoot `"cache`" `"uv.toml`"
    `$env:PIP_CONFIG_FILE = `"nul`"
    `$env:PIP_DISABLE_PIP_VERSION_CHECK = 1
    `$env:PIP_NO_WARN_SCRIPT_LOCATION = 0
    `$env:UV_LINK_MODE = `"copy`"
    `$env:PYTHONUTF8 = 1
    `$env:PYTHONIOENCODING = `"utf-8`"
    `$env:PYTHONUNBUFFERED = 1
    `$env:PYTHONNOUSERSITE = 1
    `$env:PYTHONFAULTHANDLER = 1
    `$env:CACHE_HOME = Join-NormalizedPath `$PSScriptRoot `"cache`"
    `$env:COMFYUI_PATH = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX
    `$env:COMFYUI_ROOT = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX
    `$env:SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH = `$PSScriptRoot
    `$env:SD_WEBUI_ALL_IN_ONE_LOGGER_NAME = `"ComfyUI Installer`"
    `$env:SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL = 20
    `$env:SD_WEBUI_ALL_IN_ONE_LOGGER_COLOR = 1
    `$env:SD_WEBUI_ALL_IN_ONE_RETRY_TIMES = 3
    `$env:SD_WEBUI_ALL_IN_ONE_PATCHER = 0
    `$env:SD_WEBUI_ALL_IN_ONE_EXTRA_PYPI_MIRROR = 0
    `$env:SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH = 1
    `$env:SD_WEBUI_ALL_IN_ONE_SET_CONFIG = 1
}


# 日志输出
function Write-Log {
    [CmdletBinding()]
    param(
        [string]`$Message,
        [ValidateSet(`"DEBUG`", `"INFO`", `"WARNING`", `"ERROR`", `"CRITICAL`")]
        [string]`$Level = `"INFO`",
        [string]`$Name = `"ComfyUI Installer`"
    )
    Write-Host `"[`" -NoNewline
    Write-Host `$Name -ForegroundColor Blue -NoNewline
    Write-Host `"]-|`" -NoNewline
    Write-Host (Get-Date -Format `"HH:mm:ss`") -ForegroundColor Gray -NoNewline
    Write-Host `"|-`" -NoNewline
    switch (`$Level) {
        `"DEBUG`"    { Write-Host `"DEBUG`" -ForegroundColor Cyan -NoNewline }
        `"INFO`"     { Write-Host `"INFO`" -ForegroundColor Green -NoNewline }
        `"WARNING`"  { Write-Host `"WARNING`" -ForegroundColor Yellow -NoNewline }
        `"ERROR`"    { Write-Host `"ERROR`" -ForegroundColor Red -NoNewline }
        `"CRITICAL`" { Write-Host `"CRITICAL`" -ForegroundColor White -BackgroundColor Red -NoNewline }
    }
    Write-Host `": `$Message`"
}


# 将文本写入文件
function Write-FileWithStreamWriter {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = `$true)][string]`$Value,
        [Parameter(Mandatory = `$true)][string]`$Path,
        [Parameter(Mandatory = `$true)][ValidateSet(`"GBK`", `"UTF8`", `"UTF8BOM`")][string]`$Encoding
    )
    process {
        try {
            `$encode = `$null
            switch (`$Encoding.ToLower()) {
                `"GBK`" {
                    if (`$PSVersionTable.PSVersion.Major -ge 6) {
                        [System.Text.Encoding]::RegisterProvider([System.Text.CodePagesEncodingProvider]::Instance)
                    }
                    `$encode = [System.Text.Encoding]::GetEncoding(`"GBK`")
                }
                `"UTF8`" {
                    `$encode = New-Object System.Text.UTF8Encoding(`$false)
                }
                `"UTF8BOM`" {
                    `$encode = New-Object System.Text.UTF8Encoding(`$true)
                }
            }
            `$absolute_path = Get-NormalizedFilePath `$Path
            `$writer = New-Object System.IO.StreamWriter(`$absolute_path, `$false, `$encode)
            try {
                `$writer.Write(`$Value)
            }
            finally {
                if (`$null -ne `$writer) {
                    `$writer.Close()
                    `$writer.Dispose()
                }
            }
        }
        catch {
            Write-Log `"写入文件时发生错误: `$(`$_.Exception.Message)`" -Level ERROR
        }
    }
}


# 路径拼接并规范化
function Join-NormalizedPath {
    `$joined = `$args[0]
    for (`$i = 1; `$i -lt `$args.Count; `$i++) { `$joined = Join-Path `$joined `$args[`$i] }
    return `$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath(`$joined).TrimEnd('\', '/')
}


# 更新 SD WebUI All In One 内核
function Update-SDWebUiAllInOne {
    `$content = `"
import re
from importlib.metadata import version


def compare_versions(version1: str, version2: str) -> int:
    try:
        nums1 = re.sub(r'[a-zA-Z]+', '', version1).replace('-', '.').replace('+', '.').split('.')
        nums2 = re.sub(r'[a-zA-Z]+', '', version2).replace('-', '.').replace('+', '.').split('.')
    except Exception:
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


def is_core_need_update(core_minimum_ver: str) -> bool:
    try:
        core_ver = version('sd-webui-all-in-one')
    except Exception:
        return True
    return compare_versions(core_ver, core_minimum_ver) < 0


if __name__ == '__main__':
    print(is_core_need_update('`$script:CORE_MINIMUM_VER'))
`".Trim()

    `$pip_index_url = `"https://pypi.python.org/simple`"
    if ((!(`$script:DisablePyPIMirror)) -and (!(Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_pypi_mirror.txt`")))) {
        `$pip_index_url = `"https://mirrors.cloud.tencent.com/pypi/simple`"
    }
    Write-Log `"检测 SD WebUI All In One 内核是否需要更新`"
    `$status = `$(python -c `"`$content`")
    if (`$status -ne `"True`") {
        Write-Log `"SD WebUI All In One 内核无需更新`"
        return
    }
    Write-Log `"更新 SD WebUI All In One 内核中`"
    & python -m pip install -U `"sd-webui-all-in-one>=`$script:CORE_MINIMUM_VER`" --index-url `$pip_index_url
    if (!(`$?)) {
        Write-Log `"SD WebUI All In One 内核更新失败, Installer 部分功能将无法使用`" -Level ERROR
        if (!(`$script:BuildMode)) { Read-Host | Out-Null }
        exit 1
    }
    Write-Log `"SD WebUI All In One 内核更新成功`"
}


# ComfyUI Installer 更新检测
function Update-Installer {
    [CmdletBinding()]
    param([switch]`$DisableRestart)
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/comfyui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/comfyui_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/comfyui_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `$env:CACHE_HOME -Force | Out-Null

    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_update.txt`")) -or (`$script:DisableUpdate)) {
        Write-Log `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 ComfyUI Installer 的自动检查更新功能`"
        return
    }

    if (`$script:BuildMode) {
        Write-Log `"ComfyUI Installer 构建模式已启用, 跳过 ComfyUI Installer 更新检查`"
        return
    }

    # 获取更新时间间隔
    try {
        `$last_update_time = (Get-Content (Join-NormalizedPath `$PSScriptRoot `"update_time.txt`") -Raw).Trim() 2> `$null
        `$last_update_time = Get-Date `$last_update_time -Format `"yyyy-MM-dd HH:mm:ss`"
    }
    catch {
        `$last_update_time = Get-Date 0 -Format `"yyyy-MM-dd HH:mm:ss`"
    }
    finally {
        `$update_time = Get-Date -Format `"yyyy-MM-dd HH:mm:ss`"
        `$time_span = New-TimeSpan -Start `$last_update_time -End `$update_time
    }

    if (`$time_span.TotalSeconds -gt `$script:UPDATE_TIME_SPAN) {
        Set-Content -Encoding UTF8 -Path (Join-NormalizedPath `$PSScriptRoot `"update_time.txt`") -Value `$(Get-Date -Format `"yyyy-MM-dd HH:mm:ss`") # 记录更新时间
    } else {
        return
    }

    ForEach (`$url in `$urls) {
        Write-Log `"检查 ComfyUI Installer 更新中`"
        try {
            `$web_request_params = @{
                Uri = `$url
                UseBasicParsing = `$true
                OutFile = (Join-NormalizedPath `$env:CACHE_HOME `"comfyui_installer.ps1`")
            }
            Invoke-WebRequest @web_request_params
            `$latest_version = [int]`$(
                Get-Content (Join-NormalizedPath `$env:CACHE_HOME `"comfyui_installer.ps1`") -Encoding UTF8 |
                Select-String -Pattern `"COMFYUI_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Write-Log `"重试检查 ComfyUI Installer 更新中`" -Level WARNING
            } else {
                Write-Log `"检查 ComfyUI Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -le `$script:COMFYUI_INSTALLER_VERSION) {
        Write-Log `"ComfyUI Installer 已是最新版本`"
        return
    }

    Write-Log `"调用 ComfyUI Installer 进行更新中`"
    & (Join-NormalizedPath `$env:CACHE_HOME `"comfyui_installer.ps1`") -InstallPath `$PSScriptRoot -UseUpdateMode

    if (`$DisableRestart) {
        Write-Log `"更新结束, 已禁用自动重新启动`"
        return
    }

    `$raw_params = `$script:LaunchCommandLine -replace `"^.*\.ps1[\s]*`", `"`"
    Write-Log `"更新结束, 重新启动 ComfyUI Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
    Invoke-Expression `"& ```"`$script:OriginalScriptPath```" `$raw_params`"
    exit 0
}


# 检查 Aria2 版本并更新
function Update-Aria2 {
    Write-Log `"检查 Aria2 是否需要更新`"
    `$urls = @(
        `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/aria2c.exe`",
        `"https://huggingface.co/licyk/invokeai-core-model/resolve/main/pypatchmatch/aria2c.exe`"
    )
    `$aria2_tmp_path = Join-NormalizedPath `$env:CACHE_HOME `"aria2c.exe`"
    & python -m sd_webui_all_in_one.cli_manager.main self-manager check-aria2
    if (`$?) {
        Write-Log `"Aria2 无需更新`"
        return
    }
    Write-Log `"更新 Aria2 中`"
    New-Item -ItemType Directory -Path `$env:CACHE_HOME -Force > `$null

    ForEach (`$url in `$urls) {
        Write-Log `"下载 Aria2 中`"
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
                Write-Log `"重试下载 Aria2 中`" -Level WARNING
            } else {
                Write-Log `"Aria2 下载失败, 无法更新 Aria2, 可能会导致模型下载出现问题`" -Level ERROR
                return
            }
        }
    }

    if ((Test-Path `"`$PSScriptRoot/`$env:CORE_PREFIX/git/bin/aria2c.exe`") -or (Test-Path `"`$PSScriptRoot/`$env:CORE_PREFIX/git/bin/git.exe`")) {
        Move-Item -Path `"`$env:CACHE_HOME/aria2c.exe`" -Destination `"`$PSScriptRoot/`$env:CORE_PREFIX/git/bin/aria2c.exe`" -Force
    } elseif ((Test-Path `"`$PSScriptRoot/git/bin/aria2c.exe`") -or (Test-Path `"`$PSScriptRoot/git/bin/git.exe`")) {
        Move-Item -Path `"`$env:CACHE_HOME/aria2c.exe`" -Destination `"`$PSScriptRoot/git/bin/aria2c.exe`" -Force
    } else {
        New-Item -ItemType Directory -Path `"`$PSScriptRoot/git/bin`" -Force > `$null
        Move-Item -Path `"`$env:CACHE_HOME/aria2c.exe`" -Destination `"`$PSScriptRoot/git/bin/aria2c.exe`" -Force
    }
    Write-Log `"Aria2 更新完成`"
}


# 获取当前平台
function Get-CurrentPlatform {
    if ([System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)) {
        return `"windows`"
    }
    elseif ([System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Linux)) {
        return `"linux`"
    }
    elseif ([System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::OSX)) {
        return `"macos`"
    }
    else {
        return `"unknown`"
    }
}


# 获取当前架构
function Get-CurrentArchitecture {
    `$architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLower()
    if (`$architecture -eq `"x64`") {
        return `"amd64`" 
    }
    elseif (`$architecture -eq `"arm64`") {
        return `"aarch64`"
    }
    else {
        return `$architecture 
    }
}

# 获取规范化路径
function Get-NormalizedFilePath {
    [CmdletBinding()]
    param ([Parameter(Mandatory = `$false)][string]`$Filepath)
    if (-not [string]::IsNullOrWhiteSpace(`$Filepath)) { return Join-NormalizedPath `$Filepath }
    return `$null
}


# 显示版本信息
function Get-Version {
    `$ver = `$([string]`$script:COMFYUI_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Write-Log `"ComfyUI Installer 版本: v`${major}.`${minor}.`${micro}`"
}


# 设置内核路径前缀
function Set-CorePrefix {
    `$target_prefix = `$null
    `$prefix_list = @(`"core`", `"ComfyUI*`")
    if (`$script:CorePrefix -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"core_prefix.txt`"))) {
        Write-Log `"检测到 core_prefix.txt 配置文件 / -CorePrefix 命令行参数, 使用自定义内核路径前缀`"
        `$origin_core_prefix = if (`$script:CorePrefix) { 
            `$script:CorePrefix 
        } else { 
            (Get-Content (Join-NormalizedPath `$PSScriptRoot `"core_prefix.txt`") -Raw -Encoding UTF8).Trim() 
        }
        `$origin_core_prefix = `$origin_core_prefix.TrimEnd('\', '/')
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix)) {
            `$from_uri = New-Object System.Uri(`$PSScriptRoot.Replace('\', '/') + '/')
            `$to_uri = New-Object System.Uri(`$origin_core_prefix.Replace('\', '/'))
            `$target_prefix = `$from_uri.MakeRelativeUri(`$to_uri).ToString().Trim('/')
            Write-Log `"转换绝对路径为内核路径前缀: `$origin_core_prefix -> `$target_prefix`"
        } else {
            `$target_prefix = `$origin_core_prefix
        }
    } 
    else {
        foreach (`$i in `$prefix_list) {
            `$found_dir = Get-ChildItem -Path `$PSScriptRoot -Directory -Filter `$i -ErrorAction SilentlyContinue | Select-Object -First 1
            if (`$found_dir) {
                `$target_prefix = `$found_dir.Name
                break
            }
        }
    }
    if ([string]::IsNullOrWhiteSpace(`$target_prefix)) {
        `$target_prefix = `"core`"
    }
    `$env:CORE_PREFIX = `$target_prefix
    `$full_core_path = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX
    Write-Log `"当前内核路径前缀: `$env:CORE_PREFIX`"
    Write-Log `"完整内核路径: `$full_core_path`"
}


# 代理配置
function Set-Proxy {
    [CmdletBinding()]
    param ([Parameter()][switch]`$Legacy)
    `$env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    if (`$script:DisableProxy -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_proxy.txt`"))) {
        Write-Log `"检测到本地存在 disable_proxy.txt 代理配置文件 / -DisableProxy 命令行参数, 禁用自动设置代理`"
        return
    }
    if (`$script:UseCustomProxy -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"proxy.txt`"))) {
        if (`$script:UseCustomProxy) {
            `$proxy_value = `$script:UseCustomProxy
        } else {
            `$proxy_value = (Get-Content (Join-NormalizedPath `$PSScriptRoot `"proxy.txt`") -Raw -Encoding UTF8).Trim()
        }
        `$env:HTTP_PROXY = `$proxy_value
        `$env:HTTPS_PROXY = `$proxy_value
        Write-Log `"检测到本地存在 proxy.txt 代理配置文件 / -UseCustomProxy 命令行参数, 已读取代理配置文件并设置代理`"
        return
    }
    if (`$Legacy) {
        `$proxy_value = & python -m sd_webui_all_in_one.cli_manager.main self-manager get-proxy
        if (![string]::IsNullOrWhiteSpace(`$proxy_value)) {
            `$env:HTTP_PROXY = `$proxy_value
            `$env:HTTPS_PROXY = `$proxy_value
            Write-Log `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
        }
    } else {
        `$env:SD_WEBUI_ALL_IN_ONE_PROXY = 1
        Write-Log `"使用自动检测代理模式进行代理配置`"
    }
}


# 配置 PyPI 镜像源
function Set-PyPIMirror {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]`$ArrayList)
    if (`$script:DisablePyPIMirror -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_pypi_mirror.txt`"))) {
        Write-Log `"检测到 disable_pypi_mirror.txt 配置文件 / -DisablePyPIMirror 命令行参数, 已将 PyPI 源切换至官方源`"
        `$ArrayList.Add(`"--no-pypi-mirror`") | Out-Null
        return
    }
    Write-Log `"使用 PyPI 镜像源`"
}


# HuggingFace 镜像源
function Set-HuggingFaceMirror {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]`$ArrayList)
    if (`$script:DisableHuggingFaceMirror -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_hf_mirror.txt`"))) {
        Write-Log `"检测到本地存在 disable_hf_mirror.txt 镜像源配置文件 / -DisableHuggingFaceMirror 命令行参数, 禁用自动设置 HuggingFace 镜像源`"
        `$ArrayList.Add(`"--no-hf-mirror`") | Out-Null
        return
    }
    if (`$script:UseCustomHuggingFaceMirror -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"hf_mirror.txt`"))) {
        if (`$script:UseCustomHuggingFaceMirror) {
            `$hf_mirror_value = `$script:UseCustomHuggingFaceMirror
        } else {
            `$hf_mirror_value = (Get-Content (Join-NormalizedPath `$PSScriptRoot `"hf_mirror.txt`") -Raw -Encoding UTF8).Trim()
        }
        `$ArrayList.Add(`"--custom-hf-mirror`") | Out-Null
        `$ArrayList.Add(`$hf_mirror_value) | Out-Null
        Write-Log `"检测到本地存在 hf_mirror.txt 配置文件 / -UseCustomHuggingFaceMirror 命令行参数, 已读取该配置并设置 HuggingFace 镜像源`"
        return
    }
    Write-Log `"使用默认 HuggingFace 镜像源`"
}


# 设置 Github 镜像源
function Set-GithubMirror {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]`$ArrayList)
    if (Test-Path (Join-NormalizedPath `$PSScriptRoot `".gitconfig`")) {
        Remove-Item -Path (Join-NormalizedPath `$PSScriptRoot `".gitconfig`") -Force -Recurse
    }
    if (`$script:DisableGithubMirror -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_gh_mirror.txt`"))) {
        Write-Log `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件 / -DisableGithubMirror 命令行参数, 禁用 Github 镜像源`"
        `$ArrayList.Add(`"--no-github-mirror`") | Out-Null
        return
    }
    if (`$script:UseCustomGithubMirror -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"gh_mirror.txt`"))) {
        if (`$script:UseCustomGithubMirror) {
            `$github_mirror = `$script:UseCustomGithubMirror
        } else {
            `$github_mirror = (Get-Content (Join-NormalizedPath `$PSScriptRoot `"gh_mirror.txt`") -Raw -Encoding UTF8).Trim()
        }
        Write-Log `"检测到本地存在 gh_mirror.txt Github 镜像源配置文件 / -UseCustomGithubMirror 命令行参数, 已读取 Github 镜像源配置文件并设置 Github 镜像源`"
        `$ArrayList.Add(`"--custom-github-mirror`") | Out-Null
        `$ArrayList.Add(`$github_mirror) | Out-Null
    }
}


# 设置 uv 的使用状态
function Set-uv {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]`$ArrayList)
    if (`$script:DisableUV -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_uv.txt`"))) {
        Write-Log `"检测到 disable_uv.txt 配置文件 / -DisableUV 命令行参数, 已禁用 uv, 使用 Pip 作为 Python 包管理器`"
        `$ArrayList.Add(`"--no-uv`") | Out-Null
    } else {
        Write-Log `"默认启用 uv 作为 Python 包管理器, 加快 Python 软件包的安装速度`"
        Write-Log `"当 uv 安装 Python 软件包失败时, 将自动切换成 Pip 重试 Python 软件包的安装`"
    }
}


# 设置 CUDA 内存分配器
function Set-PyTorchCUDAMemoryAlloc {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]`$ArrayList)
    if (`$script:DisableCUDAMalloc -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_set_pytorch_cuda_memory_alloc.txt`"))) {
        Write-Log `"检测到 disable_set_pytorch_cuda_memory_alloc.txt 配置文件 / -DisableCUDAMalloc 命令行参数, 已禁用自动设置 CUDA 内存分配器`"
        `$ArrayList.Add(`"--no-cuda-malloc`") | Out-Null
    }
}


Export-ModuleMember -Function ``
    Initialize-EnvPath, ``
    Write-Log, ``
    Write-FileWithStreamWriter, ``
    Update-SDWebUiAllInOne, ``
    Update-Installer, ``
    Update-Aria2, ``
    Get-Version, ``
    Set-CorePrefix, ``
    Set-Proxy, ``
    Set-PyPIMirror, ``
    Set-HuggingFaceMirror, ``
    Set-GithubMirror, ``
    Set-uv, ``
    Set-PyTorchCUDAMemoryAlloc, ``
    Join-NormalizedPath, ``
    Get-NormalizedFilePath, ``
    Get-CurrentPlatform, ``
    Get-CurrentArchitecture
".Trim()
    Write-Log "$(if (Test-Path "$script:InstallPath/modules.psm1") { "更新" } else { "生成" }) modules.psm1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path "$script:InstallPath/modules.psm1" -Value $content
}


# 启动脚本
function Write-LaunchScript {
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
    [switch]`$UseCustomHuggingFaceMirror,
    [switch]`$DisableGithubMirror,
    [string]`$UseCustomGithubMirror,
    [switch]`$DisableUV,
    [string]`$LaunchArg,
    [switch]`$EnableShortcut,
    [switch]`$DisableCUDAMalloc,
    [switch]`$DisableEnvCheck
)
try {
    `$global:OriginalScriptPath = `$PSCommandPath
    `$global:LaunchCommandLine = `$MyInvocation.Line
    (Import-Module `"`$PSScriptRoot/modules.psm1`" -Function `"Initialize-EnvPath`", `"Write-Log`", `"Set-CorePrefix`", `"Get-Version`", `"Update-Installer`", `"Set-Proxy`", `"Set-PyPIMirror`", `"Set-HuggingFaceMirror`", `"Set-GithubMirror`", `"Set-uv`", `"Set-PyTorchCUDAMemoryAlloc`", `"Update-SDWebUiAllInOne`" -PassThru -Force -ErrorAction Stop).Invoke({
        `$script:OriginalScriptPath = `$global:OriginalScriptPath
        `$script:LaunchCommandLine = `$global:LaunchCommandLine
        Remove-Variable OriginalScriptPath -Scope Global -Force
        Remove-Variable LaunchCommandLine -Scope Global -Force
        `$script:CorePrefix = `$CorePrefix
        `$script:DisableUV = `$script:DisableUV
        `$script:DisableProxy = `$script:DisableProxy
        `$script:UseCustomProxy = `$script:UseCustomProxy
        `$script:DisablePyPIMirror = `$script:DisablePyPIMirror
        `$script:DisableHuggingFaceMirror = `$script:DisableHuggingFaceMirror
        `$script:UseCustomHuggingFaceMirror = `$script:UseCustomHuggingFaceMirror
        `$script:DisableGithubMirror = `$script:DisableGithubMirror
        `$script:UseCustomGithubMirror = `$script:UseCustomGithubMirror
        `$script:DisableCUDAMalloc = `$script:DisableCUDAMalloc
        `$script:DisableUpdate = `$script:DisableUpdate
        `$script:BuildMode = `$script:BuildMode
    })
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White
    Write-Host `"launch_comfyui_installer.ps1`" -ForegroundColor Yellow
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if (!(`$script:BuildMode)) { Read-Host | Out-Null }
    exit 1
}


# 帮助信息
function Get-InstallerCmdletHelp {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-DisablePyPIMirror] [-DisableUpdate] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像源地址>] [-DisableUV] [-LaunchArg <ComfyUI 启动参数>] [-EnableShortcut] [-DisableCUDAMalloc] [-DisableEnvCheck]

参数:
    -Help
        获取 ComfyUI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -BuildMode
        启用 ComfyUI Installer 构建模式

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableUpdate
        禁用 ComfyUI Installer 更新检查

    -DisableProxy
        禁用 ComfyUI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableHuggingFaceMirror
        禁用 HuggingFace 镜像源, 不使用 HuggingFace 镜像源下载文件

    -UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>
        使用自定义 HuggingFace 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror ```"https://hf-mirror.com```" 设置 HuggingFace 镜像源地址

    -DisableGithubMirror
        禁用 ComfyUI Installer 自动设置 Github 镜像源

    -UseCustomGithubMirror <Github 镜像站地址>
        使用自定义的 Github 镜像站地址

    -DisableUV
        禁用 ComfyUI Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -LaunchArg <ComfyUI 启动参数>
        设置 ComfyUI 自定义启动参数, 如启用 --fast 和 --auto-launch, 则使用 -LaunchArg ```"--fast --auto-launch```" 进行启用

    -EnableShortcut
        创建 ComfyUI 启动快捷方式

    -DisableCUDAMalloc
        禁用 ComfyUI Installer 通过 PYTORCH_CUDA_ALLOC_CONF / PYTORCH_ALLOC_CONF 环境变量设置 CUDA 内存分配器

    -DisableEnvCheck
        禁用 ComfyUI Installer 检查 ComfyUI 运行环境中存在的问题, 禁用后可能会导致 ComfyUI 环境中存在的问题无法被发现并修复


更多的帮助信息请阅读 ComfyUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/comfyui_installer.md
`".Trim()

    if (`$script:Help) {
        Write-Host `$content
        exit 0
    }
}



# 获取启动参数
function Get-WebUILaunchArgs {
    param ([System.Collections.ArrayList]`$ArrayList)
    if ((Test-Path `"`$PSScriptRoot/launch_args.txt`") -or (`$script:LaunchArg)) {
        if (`$script:LaunchArg) {
            `$launch_args = `$script:LaunchArg.Trim()
        } else {
            `$launch_args = (Get-Content `"`$PSScriptRoot/launch_args.txt`" -Raw).Trim()
        }
        if ([string]::IsNullOrEmpty(`$launch_args)) {
            return
        }
        `$ArrayList.Add(`"--launch-args`") | Out-Null
        `$ArrayList.Add(`$launch_args + `" `") | Out-Null
        Write-Log `"检测到本地存在 launch_args.txt 启动参数配置文件 / -LaunchArg 命令行参数, 已读取该启动参数配置文件并应用启动参数`"
        Write-Log `"使用的启动参数: `$launch_args`"
    }
}


# 设置快捷启动方式
function Add-Shortcut {
    `$filename = `"ComfyUI`"
    `$url = `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/comfyui_icon.ico`"
    `$shortcut_icon = `"`$PSScriptRoot/comfyui_icon.ico`"

    if ((!(Test-Path `"`$PSScriptRoot/enable_shortcut.txt`")) -and (!(`$script:EnableShortcut))) {
        return
    }

    Write-Log `"检测到 enable_shortcut.txt 配置文件 / -EnableShortcut 命令行参数, 开始检查 ComfyUI 快捷启动方式中`"
    if (!(Test-Path `"`$shortcut_icon`")) {
        Write-Log `"获取 ComfyUI 图标中`"
        `$web_request_params = @{
            Uri = `$url
            UseBasicParsing = `$true
            OutFile = `"`$PSScriptRoot/comfyui_icon.ico`"
        }
        Invoke-WebRequest @web_request_params
        if (!(`$?)) {
            Write-Log `"获取 ComfyUI 图标失败, 无法创建 ComfyUI 快捷启动方式`"
            return
        }
    }

    Write-Log `"更新 ComfyUI 快捷启动方式`"
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
    `$start_menu_path = `"`$env:APPDATA/Microsoft/Windows/Start Menu/Programs`"
    # 保存到开始菜单
    Copy-Item -Path `"`$shortcut_path`" -Destination `"`$start_menu_path`" -Force
}


# 检测 Microsoft Visual C++ Redistributable
function Test-MSVCPPRedistributable {
    if (!(`$env:OS -like `"*Windows*`" -or `$IsWindows)) {
        Write-Log `"非 Windows 系统，跳过 Microsoft Visual C++ Redistributable 检测`"
        return
    }

    Write-Log `"检测 Microsoft Visual C++ Redistributable 是否缺失`"

    if ([string]::IsNullOrEmpty(`$env:SYSTEMROOT)) {
        `$vc_runtime_dll_path = `"C:/Windows/System32/vcruntime140_1.dll`"
    } else {
        `$vc_runtime_dll_path = `"`$env:SYSTEMROOT/System32/vcruntime140_1.dll`"
    }

    if (Test-Path `$vc_runtime_dll_path) {
        Write-Log `"Microsoft Visual C++ Redistributable 未缺失`"
        return
    }

    Write-Log `"检测到 Microsoft Visual C++ Redistributable 缺失, 这可能导致 PyTorch 无法正常识别 GPU 导致报错`"
    Write-Log `"请下载并安装 Microsoft Visual C++ Redistributable 后重新启动`"

    Add-Type -AssemblyName PresentationFramework
    `$msg_text = `"检测到系统缺失 Microsoft Visual C++ Redistributable, 这可能导致程序无法正常运行。请下载并安装该组件, 并重新启动以解决问题。``n``n是否立即打开下载页面?`"
    `$msg_title = `"缺失系统组件`"
    `$result = [System.Windows.MessageBox]::Show(`$msg_text, `$msg_title, [System.Windows.MessageBoxButton]::YesNo, [System.Windows.MessageBoxImage]::Warning)
    
    if (`$result -eq [System.Windows.MessageBoxResult]::Yes) {
        `$download_url = `"https://aka.ms/vs/17/release/vc_redist.x64.exe`"
        Write-Log `"正在打开下载链接: `$download_url`"
        Start-Process `$download_url
    }
}


# 检查运行环境
function Test-WebUIEnv {
    param ([System.Collections.ArrayList]`$ArrayList)
    if ((Test-Path `"`$PSScriptRoot/disable_check_env.txt`") -or (`$script:DisableEnvCheck)) {
        Write-Log `"检测到 disable_check_env.txt 配置文件 / -DisableEnvCheck 命令行参数, 已禁用 ComfyUI 运行环境检测, 这可能会导致 ComfyUI 运行环境中存在的问题无法被发现并解决`"
        `$ArrayList.Add(`"--no-check-env`") | Out-Null
    }
}


# 获取启动 SD WebUI All In One 内核的启动参数
function Get-LaunchCoreArgs {
    `$launch_params = New-Object System.Collections.ArrayList
    Set-uv `$launch_params
    Set-GithubMirror `$launch_params
    Set-PyPIMirror `$launch_params
    if (!(`$script:BuildMode)) {
        Set-HuggingFaceMirror `$launch_params
        Get-WebUILaunchArgs `$launch_params
        Set-PyTorchCUDAMemoryAlloc `$launch_params
        Test-WebUIEnv `$launch_params
    }
    return `$launch_params
}


function Main {
    Get-InstallerCmdletHelp
    Get-Version
    Set-CorePrefix
    Initialize-EnvPath
    Set-Proxy
    Update-Installer
    Update-SDWebUiAllInOne

    if (!(Test-Path `"`$PSScriptRoot/`$env:CORE_PREFIX`")) {
        Write-Log `"内核路径 `$PSScriptRoot\`$env:CORE_PREFIX 未找到, 请检查 ComfyUI 是否已正确安装, 或者尝试运行 ComfyUI Installer 进行修复`"
        Read-Host | Out-Null
        return
    }

    Test-MSVCPPRedistributable
    `$launch_args = Get-LaunchCoreArgs
    Add-Shortcut

    if (`$script:BuildMode) {
        Write-Log `"ComfyUI Installer 构建模式已启用, 仅检查 ComfyUI 运行环境`"
        & python -m sd_webui_all_in_one.cli_manager.main comfyui check-env `$launch_args
    } else {
        & python -m sd_webui_all_in_one.cli_manager.main comfyui launch `$launch_args
        `$req = `$?
        if (`$req) {
            Write-Log `"ComfyUI 正常退出`"
        } else {
            Write-Log `"ComfyUI 出现异常, 已退出`"
        }
        Read-Host | Out-Null
    }
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path "$script:InstallPath/launch.ps1") { "更新" } else { "生成" }) launch.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path "$script:InstallPath/launch.ps1" -Value $content
}


# 更新脚本
function Write-UpdateScript {
    $content = "
param (
    [switch]`$Help,
    [string]`$CorePrefix,
    [switch]`$BuildMode,
    [switch]`$DisableUpdate,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisableGithubMirror,
    [string]`$UseCustomGithubMirror
)
try {
    `$global:OriginalScriptPath = `$PSCommandPath
    `$global:LaunchCommandLine = `$MyInvocation.Line
    (Import-Module `"`$PSScriptRoot/modules.psm1`" -Function `"Initialize-EnvPath`", `"Write-Log`", `"Set-CorePrefix`", `"Get-Version`", `"Update-Installer`", `"Set-Proxy`", `"Set-GithubMirror`", `"Update-SDWebUiAllInOne`" -PassThru -Force -ErrorAction Stop).Invoke({
        `$script:OriginalScriptPath = `$global:OriginalScriptPath
        `$script:LaunchCommandLine = `$global:LaunchCommandLine
        Remove-Variable OriginalScriptPath -Scope Global -Force
        Remove-Variable LaunchCommandLine -Scope Global -Force
        `$script:CorePrefix = `$script:CorePrefix
        `$script:DisableProxy = `$script:DisableProxy
        `$script:UseCustomProxy = `$script:UseCustomProxy
        `$script:DisableGithubMirror = `$script:DisableGithubMirror
        `$script:UseCustomGithubMirror = `$script:UseCustomGithubMirror
        `$script:DisableUpdate = `$script:DisableUpdate
        `$script:BuildMode = `$script:BuildMode
    })
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White
    Write-Host `"launch_comfyui_installer.ps1`" -ForegroundColor Yellow
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if (!(`$script:BuildMode)) { Read-Host | Out-Null }
    exit 1
}


# 帮助信息
function Get-InstallerCmdletHelp {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-DisableUpdate] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像源地址>]

参数:
    -Help
        获取 ComfyUI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -BuildMode
        启用 ComfyUI Installer 构建模式

    -DisableUpdate
        禁用 ComfyUI Installer 更新检查

    -DisableProxy
        禁用 ComfyUI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableGithubMirror
        禁用 ComfyUI Installer 自动设置 Github 镜像源

    -UseCustomGithubMirror <Github 镜像站地址>
        使用自定义的 Github 镜像站地址


更多的帮助信息请阅读 ComfyUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/comfyui_installer.md
`".Trim()

    if (`$script:Help) {
        Write-Host `$content
        exit 0
    }
}


# 获取启动 SD WebUI All In One 内核的启动参数
function Get-LaunchCoreArgs {
    `$launch_params = New-Object System.Collections.ArrayList
    Set-GithubMirror `$launch_params
    return `$launch_params
}


function Main {
    Get-InstallerCmdletHelp
    Get-Version
    Set-CorePrefix
    Initialize-EnvPath
    Set-Proxy
    Update-Installer
    Update-SDWebUiAllInOne

    if (!(Test-Path `"`$PSScriptRoot/`$env:CORE_PREFIX`")) {
        Write-Log `"内核路径 `$PSScriptRoot\`$env:CORE_PREFIX 未找到, 请检查 ComfyUI 是否已正确安装, 或者尝试运行 ComfyUI Installer 进行修复`"
        Read-Host | Out-Null
        return
    }

    `$launch_args = Get-LaunchCoreArgs
    & python -m sd_webui_all_in_one.cli_manager.main comfyui update `$launch_args

    Write-Log `"退出 ComfyUI 更新脚本`"
    if (!(`$script:BuildMode)) { Read-Host | Out-Null }
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path "$script:InstallPath/update.ps1") { "更新" } else { "生成" }) update.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path "$script:InstallPath/update.ps1" -Value $content
}


# 更新扩展脚本
function Write-UpdateNodeScript {
    $content = "
param (
    [switch]`$Help,
    [string]`$CorePrefix,
    [switch]`$BuildMode,
    [switch]`$DisableUpdate,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisableGithubMirror,
    [string]`$UseCustomGithubMirror
)
try {
    `$global:OriginalScriptPath = `$PSCommandPath
    `$global:LaunchCommandLine = `$MyInvocation.Line
    (Import-Module `"`$PSScriptRoot/modules.psm1`" -Function `"Initialize-EnvPath`", `"Write-Log`", `"Set-CorePrefix`", `"Get-Version`", `"Update-Installer`", `"Set-Proxy`", `"Set-GithubMirror`", `"Update-SDWebUiAllInOne`" -PassThru -Force -ErrorAction Stop).Invoke({
        `$script:OriginalScriptPath = `$global:OriginalScriptPath
        `$script:LaunchCommandLine = `$global:LaunchCommandLine
        Remove-Variable OriginalScriptPath -Scope Global -Force
        Remove-Variable LaunchCommandLine -Scope Global -Force
        `$script:CorePrefix = `$script:CorePrefix
        `$script:DisableProxy = `$script:DisableProxy
        `$script:UseCustomProxy = `$script:UseCustomProxy
        `$script:DisableGithubMirror = `$script:DisableGithubMirror
        `$script:UseCustomGithubMirror = `$script:UseCustomGithubMirror
        `$script:DisableUpdate = `$script:DisableUpdate
        `$script:BuildMode = `$script:BuildMode
    })
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White
    Write-Host `"launch_comfyui_installer.ps1`" -ForegroundColor Yellow
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if (!(`$script:BuildMode)) { Read-Host | Out-Null }
    exit 1
}


# 帮助信息
function Get-InstallerCmdletHelp {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-DisableUpdate] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像源地址>]

参数:
    -Help
        获取 ComfyUI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -BuildMode
        启用 ComfyUI Installer 构建模式

    -DisableUpdate
        禁用 ComfyUI Installer 更新检查

    -DisableProxy
        禁用 ComfyUI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableGithubMirror
        禁用 ComfyUI Installer 自动设置 Github 镜像源

    -UseCustomGithubMirror <Github 镜像站地址>
        使用自定义的 Github 镜像站地址


更多的帮助信息请阅读 ComfyUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/comfyui_installer.md
`".Trim()

    if (`$script:Help) {
        Write-Host `$content
        exit 0
    }
}


# 获取启动 SD WebUI All In One 内核的启动参数
function Get-LaunchCoreArgs {
    `$launch_params = New-Object System.Collections.ArrayList
    Set-GithubMirror `$launch_params
    return `$launch_params
}


function Main {
    Get-InstallerCmdletHelp
    Get-Version
    Set-CorePrefix
    Initialize-EnvPath
    Set-Proxy
    Update-Installer
    Update-SDWebUiAllInOne

    if (!(Test-Path `"`$PSScriptRoot/`$env:CORE_PREFIX`")) {
        Write-Log `"内核路径 `$PSScriptRoot\`$env:CORE_PREFIX 未找到, 请检查 ComfyUI 是否已正确安装, 或者尝试运行 ComfyUI Installer 进行修复`"
        Read-Host | Out-Null
        return
    }

    `$launch_args = Get-LaunchCoreArgs
    & python -m sd_webui_all_in_one.cli_manager.main comfyui custom-node update `$launch_args

    Write-Log `"退出 ComfyUI 扩展更新脚本`"

    if (!(`$script:BuildMode)) { Read-Host | Out-Null }
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path "$script:InstallPath/update_node.ps1") { "更新" } else { "生成" }) update_node.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path "$script:InstallPath/update_node.ps1" -Value $content
}


# 获取安装脚本
function Write-LaunchInstallerScript {
    $content = "
param (
    [string]`$InstallPath,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableUV,
    [switch]`$DisableGithubMirror,
    [string]`$UseCustomGithubMirror,
    [string]`$CorePrefix,
    [Parameter(ValueFromRemainingArguments=`$true)]`$ExtraArgs
)
& {
    `$target_prefix = `$null
    `$prefix_list = @(`"core`", `"ComfyUI*`")
    if (`$script:CorePrefix -or (Test-Path `"`$PSScriptRoot/core_prefix.txt`")) {
        `$origin_core_prefix = if (`$script:CorePrefix) { 
            `$script:CorePrefix 
        } else { 
            (Get-Content `"`$PSScriptRoot/core_prefix.txt`" -Raw).Trim() 
        }
        `$origin_core_prefix = `$origin_core_prefix.TrimEnd('\', '/')
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix)) {
            `$from_uri = New-Object System.Uri(`$PSScriptRoot.Replace('\', '/') + '/')
            `$to_uri = New-Object System.Uri(`$origin_core_prefix.Replace('\', '/'))
            `$target_prefix = `$from_uri.MakeRelativeUri(`$to_uri).ToString().Trim('/')
        } else {
            `$target_prefix = `$origin_core_prefix
        }
    } 
    else {
        foreach (`$i in `$prefix_list) {
            `$found_dir = Get-ChildItem -Path `$PSScriptRoot -Directory -Filter `$i -ErrorAction SilentlyContinue | Select-Object -First 1
            if (`$found_dir) {
                `$target_prefix = `$found_dir.Name
                break
            }
        }
    }
    if ([string]::IsNullOrWhiteSpace(`$target_prefix)) {
        `$target_prefix = `"core`"
    }
    `$env:CORE_PREFIX = `$target_prefix
}
if (-not `$script:InstallPath) {
    `$script:InstallPath = `$PSScriptRoot
}



# 消息输出
function Write-Log {
    [CmdletBinding()]
    param(
        [string]`$Message,
        [ValidateSet(`"DEBUG`", `"INFO`", `"WARNING`", `"ERROR`", `"CRITICAL`")]
        [string]`$Level = `"INFO`",
        [string]`$Name = `"ComfyUI Installer`"
    )
    Write-Host `"[`" -NoNewline
    Write-Host `$Name -ForegroundColor Blue -NoNewline
    Write-Host `"]-|`" -NoNewline
    Write-Host (Get-Date -Format `"HH:mm:ss`") -ForegroundColor Gray -NoNewline
    Write-Host `"|-`" -NoNewline
    switch (`$Level) {
        `"DEBUG`"    { Write-Host `"DEBUG`" -ForegroundColor Cyan -NoNewline }
        `"INFO`"     { Write-Host `"INFO`" -ForegroundColor Green -NoNewline }
        `"WARNING`"  { Write-Host `"WARNING`" -ForegroundColor Yellow -NoNewline }
        `"ERROR`"    { Write-Host `"ERROR`" -ForegroundColor Red -NoNewline }
        `"CRITICAL`" { Write-Host `"CRITICAL`" -ForegroundColor White -BackgroundColor Red -NoNewline }
    }
    Write-Host `": `$Message`"
}


# 代理配置
function Set-Proxy {
    `$env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    # 检测是否禁用自动设置镜像源
    if ((Test-Path `"`$PSScriptRoot/disable_proxy.txt`") -or (`$script:DisableProxy)) {
        Write-Log `"检测到本地存在 disable_proxy.txt 代理配置文件 / -DisableProxy 命令行参数, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if ((Test-Path `"`$PSScriptRoot/proxy.txt`") -or (`$script:UseCustomProxy)) { # 本地存在代理配置
        if (`$script:UseCustomProxy) {
            `$proxy_value = `$script:UseCustomProxy
        } else {
            `$proxy_value = (Get-Content `"`$PSScriptRoot/proxy.txt`" -Raw).Trim()
        }
        `$env:HTTP_PROXY = `$proxy_value
        `$env:HTTPS_PROXY = `$proxy_value
        Write-Log `"检测到本地存在 proxy.txt 代理配置文件 / -UseCustomProxy 命令行参数, 已读取代理配置文件并设置代理`"
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
        `$env:HTTP_PROXY = `$proxy_value
        `$env:HTTPS_PROXY = `$proxy_value
        Write-Log `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
}


# 下载 ComfyUI Installer
function Download-Installer {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/comfyui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/comfyui_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/comfyui_installer/comfyui_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/comfyui_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `"`$PSScriptRoot/cache`" -Force > `$null

    ForEach (`$url in `$urls) {
        Write-Log `"正在下载最新的 ComfyUI Installer 脚本`"
        `$web_request_params = @{
            Uri = `$url
            UseBasicParsing = `$true
            OutFile = `"`$PSScriptRoot/cache/comfyui_installer.ps1`"
        }
        Invoke-WebRequest @web_request_params
        if (`$?) {
            Write-Log `"下载 ComfyUI Installer 脚本成功`"
            break
        } else {
            Write-Log `"下载 ComfyUI Installer 脚本失败`" -Level ERROR
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Write-Log `"重试下载 ComfyUI Installer 脚本`" -Level WARNING
            } else {
                Write-Log `"下载 ComfyUI Installer 脚本失败, 可尝试重新运行 ComfyUI Installer 下载脚本`" -Level ERROR
                return `$false
            }
        }
    }
    return `$true
}


# 获取本地配置文件参数
function Get-LocalSetting {
    `$arg = @{}
    if ((Test-Path `"`$PSScriptRoot/disable_pypi_mirror.txt`") -or (`$script:DisablePyPIMirror)) {
        `$arg.Add(`"-DisablePyPIMirror`", `$true)
    }

    if ((Test-Path `"`$PSScriptRoot/disable_proxy.txt`") -or (`$script:DisableProxy)) {
        `$arg.Add(`"-DisableProxy`", `$true)
    } else {
        if ((Test-Path `"`$PSScriptRoot/proxy.txt`") -or (`$script:UseCustomProxy)) {
            if (`$script:UseCustomProxy) {
                `$proxy_value = `$script:UseCustomProxy
            } else {
                `$proxy_value = (Get-Content `"`$PSScriptRoot/proxy.txt`" -Raw).Trim()
            }
            `$arg.Add(`"-UseCustomProxy`", `$proxy_value)
        }
    }

    if ((Test-Path `"`$PSScriptRoot/disable_uv.txt`") -or (`$script:DisableUV)) {
        `$arg.Add(`"-DisableUV`", `$true)
    }

    if ((Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") -or (`$script:DisableGithubMirror)) {
        `$arg.Add(`"-DisableGithubMirror`", `$true)
    } else {
        if ((Test-Path `"`$PSScriptRoot/gh_mirror.txt`") -or (`$script:UseCustomGithubMirror)) {
            if (`$script:UseCustomGithubMirror) {
                `$github_mirror = `$script:UseCustomGithubMirror
            } else {
                `$github_mirror = (Get-Content `"`$PSScriptRoot/gh_mirror.txt`" -Raw).Trim()
            }
            `$arg.Add(`"-UseCustomGithubMirror`", `$github_mirror)
        }
    }

    `$arg.Add(`"-InstallPath`", `$script:InstallPath)
    `$arg.Add(`"-CorePrefix`", `$script:CorePrefix)

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
    Set-Proxy

    `$status = Download-Installer

    if (`$status) {
        Write-Log `"运行 ComfyUI Installer 中`"
        `$arg = Get-LocalSetting
        `$extra_args = Get-ExtraArgs
        try {
            Invoke-Expression `"& ```"`$PSScriptRoot/cache/comfyui_installer.ps1```" `$extra_args @arg`"
        }
        catch {
            Write-Log `"运行 ComfyUI Installer 时出现了错误: `$_`"
            Read-Host | Out-Null
        }
    } else {
        Read-Host | Out-Null
    }
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path "$script:InstallPath/launch_comfyui_installer.ps1") { "更新" } else { "生成" }) launch_comfyui_installer.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path "$script:InstallPath/launch_comfyui_installer.ps1" -Value $content
}


# 重装 PyTorch 脚本
function Write-PyTorchReInstallScript {
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
    [string]`$UseCustomProxy
)
try {
    `$global:OriginalScriptPath = `$PSCommandPath
    `$global:LaunchCommandLine = `$MyInvocation.Line
    (Import-Module `"`$PSScriptRoot/modules.psm1`" -Function `"Initialize-EnvPath`", `"Write-Log`", `"Set-CorePrefix`", `"Get-Version`", `"Set-PyPIMirror`", `"Update-Installer`", `"Set-uv`", `"Set-Proxy`", `"Update-SDWebUiAllInOne`" -PassThru -Force -ErrorAction Stop).Invoke({
        `$script:OriginalScriptPath = `$global:OriginalScriptPath
        `$script:LaunchCommandLine = `$global:LaunchCommandLine
        Remove-Variable OriginalScriptPath -Scope Global -Force
        Remove-Variable LaunchCommandLine -Scope Global -Force
        `$script:CorePrefix = `$script:CorePrefix
        `$script:DisableUV = `$script:DisableUV
        `$script:DisableProxy = `$script:DisableProxy
        `$script:UseCustomProxy = `$script:UseCustomProxy
        `$script:DisablePyPIMirror = `$script:DisablePyPIMirror
        `$script:BuildMode = `$script:BuildMode
        `$script:DisableUpdate = `$script:DisableUpdate
    })
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White
    Write-Host `"launch_comfyui_installer.ps1`" -ForegroundColor Yellow
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if (!(`$script:BuildMode)) { Read-Host | Out-Null }
    exit 1
}


# 帮助信息
function Get-InstallerCmdletHelp {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-BuildWithTorch <PyTorch 版本编号>] [-BuildWithTorchReinstall] [-DisablePyPIMirror] [-DisableUpdate] [-DisableUV] [-DisableProxy] [-UseCustomProxy]

参数:
    -Help
        获取 ComfyUI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -BuildMode
        启用 ComfyUI Installer 构建模式

    -BuildWithTorch <PyTorch 版本编号>
        (需添加 -BuildMode 启用 ComfyUI Installer 构建模式) ComfyUI Installer 执行完基础安装流程后调用 ComfyUI Installer 的 reinstall_pytorch.ps1 脚本, 根据 PyTorch 版本编号安装指定的 PyTorch 版本
        PyTorch 版本编号可运行 reinstall_pytorch.ps1 脚本进行查看

    -BuildWithTorchReinstall
        (需添加 -BuildMode 启用 ComfyUI Installer 构建模式, 并且添加 -BuildWithTorch) 在 ComfyUI Installer 构建模式下, 执行 reinstall_pytorch.ps1 脚本对 PyTorch 进行指定版本安装时使用强制重新安装

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableUpdate
        禁用 ComfyUI Installer 更新检查

    -DisableUV
        禁用 ComfyUI Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -DisableProxy
        禁用 ComfyUI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址


更多的帮助信息请阅读 ComfyUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/comfyui_installer.md
`".Trim()

    if (`$script:Help) {
        Write-Host `$content
        exit 0
    }
}


# 获取启动 SD WebUI All In One 内核的启动参数
function Get-LaunchCoreArgs {
    `$launch_params = New-Object System.Collections.ArrayList
    Set-PyPIMirror `$launch_params
    Set-uv `$launch_params
    if (`$script:BuildWithTorch) {
        `$launch_params.Add(`"--pytorch-index`") | Out-Null
        `$launch_params.Add(`$BuildWithTorch) | Out-Null
    }
    if (`$script:BuildWithTorchReinstall) {
        `$launch_params.Add(`"--force-reinstall`") | Out-Null
    }
    if (!(`$script:BuildMode)) {
        `$launch_params.Add(`"--interactive`") | Out-Null
    }
    return `$launch_params
}


function Main {
    Get-InstallerCmdletHelp
    Get-Version
    Set-CorePrefix
    Initialize-EnvPath
    Set-Proxy
    Update-Installer
    Update-SDWebUiAllInOne

    `$launch_args = Get-LaunchCoreArgs
    & python -m sd_webui_all_in_one.cli_manager.main comfyui reinstall-pytorch `$launch_args

    Write-Log `"退出 PyTorch 重装脚本`"
    if (!(`$script:BuildMode)) { Read-Host | Out-Null }
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path "$script:InstallPath/reinstall_pytorch.ps1") { "更新" } else { "生成" }) reinstall_pytorch.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path "$script:InstallPath/reinstall_pytorch.ps1" -Value $content
}


# 模型下载脚本
function Write-DownloadModelScript {
    $content = "
param (
    [switch]`$Help,
    [string]`$CorePrefix,
    [switch]`$BuildMode,
    [string]`$BuildWitchModel,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisableUpdate
)
try {
    `$global:OriginalScriptPath = `$PSCommandPath
    `$global:LaunchCommandLine = `$MyInvocation.Line
    (Import-Module `"`$PSScriptRoot/modules.psm1`" -Function `"Initialize-EnvPath`", `"Write-Log`", `"Set-CorePrefix`", `"Get-Version`", `"Set-PyPIMirror`", `"Update-Installer`", `"Set-Proxy`", `"Update-SDWebUiAllInOne`", `"Update-Aria2`" -PassThru -Force -ErrorAction Stop).Invoke({
        `$script:OriginalScriptPath = `$global:OriginalScriptPath
        `$script:LaunchCommandLine = `$global:LaunchCommandLine
        Remove-Variable OriginalScriptPath -Scope Global -Force
        Remove-Variable LaunchCommandLine -Scope Global -Force
        `$script:CorePrefix = `$script:CorePrefix
        `$script:DisableProxy = `$script:DisableProxy
        `$script:UseCustomProxy = `$script:UseCustomProxy
        `$script:DisableUpdate = `$script:DisableUpdate
        `$script:BuildMode = `$script:BuildMode
    })
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White
    Write-Host `"launch_comfyui_installer.ps1`" -ForegroundColor Yellow
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if (!(`$script:BuildMode)) { Read-Host | Out-Null }
    exit 1
}


# 帮助信息
function Get-InstallerCmdletHelp {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-BuildWitchModel <模型编号列表>] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableUpdate]

参数:
    -Help
        获取 ComfyUI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -BuildMode
        启用 ComfyUI Installer 构建模式

    -BuildWitchModel <模型编号列表>
        (需添加 -BuildMode 启用 ComfyUI Installer 构建模式) ComfyUI Installer 执行完基础安装流程后调用 ComfyUI Installer 的 download_models.ps1 脚本, 根据模型编号列表下载指定的模型
        模型编号可运行 download_models.ps1 脚本进行查看

    -DisableProxy
        禁用 ComfyUI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableUpdate
        禁用 ComfyUI Installer 更新检查


更多的帮助信息请阅读 ComfyUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/comfyui_installer.md
`".Trim()

    if (`$script:Help) {
        Write-Host `$content
        exit 0
    }
}


# 获取启动 SD WebUI All In One 内核的启动参数
function Get-LaunchCoreArgs {
    `$launch_params = New-Object System.Collections.ArrayList
    if (`$script:BuildWitchModel) {
        `$launch_params.Add(`"--index`") | Out-Null
        `$launch_params.Add(`$script:BuildWitchModel) | Out-Null
    }
    if (!(`$script:BuildMode)) {
        `$launch_params.Add(`"--interactive`") | Out-Null
    }
    `$launch_params.Add(`"--source`") | Out-Null
    `$launch_params.Add(`"modelscope`") | Out-Null
    `$launch_params.Add(`"--downloader`") | Out-Null
    `$launch_params.Add(`"aria2`") | Out-Null
    return `$launch_params
}


function Main {
    Get-InstallerCmdletHelp
    Get-Version
    Set-CorePrefix
    Initialize-EnvPath
    Set-Proxy
    Update-Installer
    Update-SDWebUiAllInOne
    Update-Aria2

    if (!(Test-Path `"`$PSScriptRoot/`$env:CORE_PREFIX`")) {
        Write-Log `"内核路径 `$PSScriptRoot\`$env:CORE_PREFIX 未找到, 请检查 ComfyUI 是否已正确安装, 或者尝试运行 ComfyUI Installer 进行修复`"
        Read-Host | Out-Null
        return
    }

    `$launch_args = Get-LaunchCoreArgs
    & python -m sd_webui_all_in_one.cli_manager.main comfyui model install-library `$launch_args

    Write-Log `"退出模型下载脚本`"
    if (!(`$script:BuildMode)) { Read-Host | Out-Null }
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path "$script:InstallPath/download_models.ps1") { "更新" } else { "生成" }) download_models.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path "$script:InstallPath/download_models.ps1" -Value $content
}


# ComfyUI Installer 设置脚本
function Write-SettingsScript {
    $content = "
param (
    [switch]`$Help,
    [string]`$CorePrefix,
    [switch]`$DisableProxy,
    [switch]`$UseCustomProxy
)
try {
    `$global:OriginalScriptPath = `$PSCommandPath
    `$global:LaunchCommandLine = `$MyInvocation.Line
    (Import-Module `"`$PSScriptRoot/modules.psm1`" -Function `"Initialize-EnvPath`", `"Write-Log`", `"Set-CorePrefix`", `"Get-Version`", `"Update-Installer`", `"Set-ProxyLegecy`", `"Write-FileWithStreamWriter`" -PassThru -Force -ErrorAction Stop).Invoke({
        `$script:OriginalScriptPath = `$global:OriginalScriptPath
        `$script:LaunchCommandLine = `$global:LaunchCommandLine
        Remove-Variable OriginalScriptPath -Scope Global -Force
        Remove-Variable LaunchCommandLine -Scope Global -Force
        `$script:CorePrefix = `$script:CorePrefix
        `$script:DisableProxy = `$script:DisableProxy
        `$script:UseCustomProxy = `$script:UseCustomProxy
    })
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White
    Write-Host `"launch_comfyui_installer.ps1`" -ForegroundColor Yellow
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    Read-Host | Out-Null
    exit 1
}

# 帮助信息
function Get-InstallerCmdletHelp {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-DisableProxy] [-UseCustomProxy]

参数:
    -Help
        获取 ComfyUI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -DisableProxy
        禁用 ComfyUI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址


更多的帮助信息请阅读 ComfyUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/comfyui_installer.md
`".Trim()

    if (`$script:Help) {
        Write-Host `$content
        exit 0
    }
}


# 通用开关状态获取
function Get-ToggleStatus ([string]`$file, [string]`$trueLabel = `"启用`", [string]`$falseLabel = `"禁用`", [bool]`$reverse = `$false) {
    `$exists = Test-Path `"`$PSScriptRoot/`$file`"
    if (`$reverse) {
        if (`$exists) { return `$falseLabel } else { return `$trueLabel }
    }
    if (`$exists) { return `$trueLabel } else { return `$falseLabel }
}


# 通用文本配置获取
function Get-TextStatus ([string]`$file, [string]`$defaultLabel = `"无`") {
    if (Test-Path `"`$PSScriptRoot/`$file`") { return (Get-Content `"`$PSScriptRoot/`$file`" -Raw).Trim() }
    return `$defaultLabel
}


# 通用开关切换逻辑
function Set-ToggleSetting ([string]`$file, [string]`$name, [bool]`$enable) {
    # 如果文件名以 disable 开头, 则 enable=true 表示删除文件, enable=false 表示创建文件
    if (`$file.ToLower().StartsWith(`"disable`")) {
        if (`$enable) {
            if (Test-Path `"`$PSScriptRoot/`$file`") { Remove-Item `"`$PSScriptRoot/`$file`" -Force -ErrorAction SilentlyContinue }
        } else {
            if (!(Test-Path `"`$PSScriptRoot/`$file`")) { New-Item -ItemType File -Path `"`$PSScriptRoot/`$file`" -Force > `$null }
        }
    } else {
        # 普通开关: enable=true 表示创建文件, enable=false 表示删除文件
        if (`$enable) {
            if (!(Test-Path `"`$PSScriptRoot/`$file`")) { New-Item -ItemType File -Path `"`$PSScriptRoot/`$file`" -Force > `$null }
        } else {
            if (Test-Path `"`$PSScriptRoot/`$file`") { Remove-Item `"`$PSScriptRoot/`$file`" -Force -ErrorAction SilentlyContinue }
        }
    }
    Write-Log `"`$name 设置成功`"
}


# 更新代理设置
function Update-ProxySetting {
    while (`$true) {
        `$current = if (Test-Path `"`$PSScriptRoot/disable_proxy.txt`") { `"禁用`" } elseif (Test-Path `"`$PSScriptRoot/proxy.txt`") { `"自定义: `$((Get-Content `"`$PSScriptRoot/proxy.txt`" -Raw).Trim())`" } else { `"系统代理`" }
        Write-Log `"当前代理设置: `$current`"
        Write-Log `"1. 启用 (系统代理) | 2. 启用 (手动设置) | 3. 禁用 | 4. 返回`"
        `$choice = Get-UserInput
        if (`$choice -eq `"1`") { Remove-Item `"`$PSScriptRoot/disable_proxy.txt`", `"`$PSScriptRoot/proxy.txt`" -Force -ErrorAction SilentlyContinue; break }
        elseif (`$choice -eq `"2`") { 
            Write-Log `"请输入代理地址 (如 http://127.0.0.1:10809):`"
            `$addr = Get-UserInput
            if (`$addr) {
                Remove-Item `"`$PSScriptRoot/disable_proxy.txt`" -Force -ErrorAction SilentlyContinue
                Set-Content -Path `"`$PSScriptRoot/proxy.txt`" -Value `$addr -Encoding UTF8
            }
            break 
        }
        elseif (`$choice -eq `"3`") { 
            New-Item `"`$PSScriptRoot/disable_proxy.txt`" -Force > `$null
            Remove-Item `"`$PSScriptRoot/proxy.txt`" -Force -ErrorAction SilentlyContinue
            break 
        }
        elseif (`$choice -eq `"4`") { return }
    }
}


# 更新镜像设置
function Update-Mirror-Setting ([string]`$file, [string]`$name, [string[]]`$examples) {
    while (`$true) {
        `$current = if (Test-Path `"`$PSScriptRoot/disable_`$file`") { `"禁用`" } elseif (Test-Path `"`$PSScriptRoot/`$file`") { `"自定义: `$((Get-Content `"`$PSScriptRoot/`$file`" -Raw).Trim())`" } else { `"默认`" }
        Write-Log `"当前 `$name 设置: `$current`"
        Write-Log `"1. 默认/自动 | 2. 自定义地址 | 3. 禁用 | 4. 返回`"
        `$choice = Get-UserInput
        if (`$choice -eq `"1`") { Remove-Item `"`$PSScriptRoot/disable_`$file`", `"`$PSScriptRoot/`$file`" -Force -ErrorAction SilentlyContinue; break }
        elseif (`$choice -eq `"2`") {
            Write-Log `"请输入 `$name 地址, 示例:`"
            `$examples | ForEach-Object { Write-Log `"  `$_`" -Level ERROR }
            `$addr = Get-UserInput
            if (`$addr) {
                Remove-Item `"`$PSScriptRoot/disable_`$file`" -Force -ErrorAction SilentlyContinue
                Set-Content -Path `"`$PSScriptRoot/`$file`" -Value `$addr -Encoding UTF8
            }
            break
        }
        elseif (`$choice -eq `"3`") {
            New-Item `"`$PSScriptRoot/disable_`$file`" -Force > `$null
            Remove-Item `"`$PSScriptRoot/`$file`" -Force -ErrorAction SilentlyContinue
            break
        }
        elseif (`$choice -eq `"4`") { return }
    }
}


# 更新内核前缀设置
function Update-Core-Prefix {
    Write-Log `"当前内核路径前缀: `$(Get-TextStatus `"core_prefix.txt`" `"自动选择`")`"
    Write-Log `"1. 配置自定义 | 2. 自动选择 | 3. 返回`"
    `$choice = Get-UserInput
    if (`$choice -eq `"1`") {
        Write-Log `"请输入前缀或绝对路径:`"
        `$path = Get-UserInput
        if (`$path) {
            if ([System.IO.Path]::IsPathRooted(`$path)) {
                `$from = New-Object System.Uri(`$PSScriptRoot.Replace('\', '/') + '/')
                `$path = `$from.MakeRelativeUri((New-Object System.Uri(`$path.Replace('\', '/')))).ToString().Trim('/')
            }
            Set-Content -Path `"`$PSScriptRoot/core_prefix.txt`" -Value `$path -Encoding UTF8
        }
    }
    elseif (`$choice -eq `"2`") { Remove-Item `"`$PSScriptRoot/core_prefix.txt`" -Force -ErrorAction SilentlyContinue }
}


# 检测环境完整性
function Test-EnvIntegrity {
    `$items = @(
        @{ n=`"Python`"; p=`"python/python.exe`"; t=`"file`" },
        @{ n=`"Git`"; p=`"git/bin/git.exe`"; t=`"file`" },
        @{ n=`"Aria2`"; p=`"git/bin/aria2c.exe`"; t=`"file`" },
        @{ n=`"ComfyUI`"; p=`"`$env:CORE_PREFIX/main.py`"; t=`"file`" },
        @{ n=`"uv`"; m=`"uv`" },
        @{ n=`"PyTorch`"; m=`"torch`" },
        @{ n=`"xFormers`"; m=`"xformers`" }
    )
    `$broken = `$false
    foreach (`$i in `$items) {
        `$ok = `$false
        if (`$i.p) { `$ok = (Test-Path `"`$PSScriptRoot/`$(`$i.p)`") -or (Test-Path `"`$PSScriptRoot/`$env:CORE_PREFIX/`$(`$i.p)`") }
        else { python -m pip show `$(`$i.m) --quiet 2> `$null; `$ok = `$? }
        Write-Log `"`$(`$i.n): `$(if (`$ok) { `"OK`" } else { `$broken=`$true; `"缺失`" })`" -Level `$(if (`$ok) { `"INFO`" } else { `"ERROR`" })
    }
    if (`$broken) { Write-Log `"检测到组件缺失, 请运行安装程序修复`" -Level WARNING }
}


# 获取用户输入
function Get-UserInput {
    return (Read-Host `"==================================>`").Trim()
}


function Main {
    Get-InstallerCmdletHelp
    Get-Version
    Set-CorePrefix
    Initialize-EnvPath
    Set-ProxyLegecy

    while (`$true) {
        Write-Log `"=== ComfyUI 管理设置 ===`"
        `$menu = @(
            @{ id=1;  n=`"代理设置`"; v=`$(if (Test-Path `"`$PSScriptRoot/disable_proxy.txt`") { `"禁用`" } elseif (Test-Path `"`$PSScriptRoot/proxy.txt`") { `"自定义 (地址: `$((Get-Content `"`$PSScriptRoot/proxy.txt`" -Raw).Trim()))`" } else { `"系统`" }) },
            @{ id=2;  n=`"包管理器`"; v=`$(Get-ToggleStatus `"disable_uv.txt`" `"Pip`" `"uv`") },
            @{ id=3;  n=`"HuggingFace 镜像源`"; v=`$(Get-ToggleStatus `"disable_hf_mirror.txt`" `"禁用`" `"启用`" `$true) },
            @{ id=4;  n=`"Github 镜像源`"; v=`$(Get-ToggleStatus `"disable_gh_mirror.txt`" `"禁用`" `"启用`" `$true) },
            @{ id=5;  n=`"自动检查更新`"; v=`$(Get-ToggleStatus `"disable_update.txt`" `"禁用`" `"启用`" `$true) },
            @{ id=6;  n=`"启动参数`"; v=`$(Get-TextStatus `"launch_args.txt`") },
            @{ id=7;  n=`"快捷方式`"; v=`$(Get-ToggleStatus `"enable_shortcut.txt`" `"启用`" `"禁用`") },
            @{ id=8;  n=`"PyPI 镜像`"; v=`$(Get-ToggleStatus `"disable_pypi_mirror.txt`" `"禁用`" `"启用`" `$true) },
            @{ id=9; n=`"CUDA 内存优化`"; v=`$(Get-ToggleStatus `"disable_set_pytorch_cuda_memory_alloc.txt`" `"禁用`" `"启用`" `$true) },
            @{ id=10; n=`"环境检测`"; v=`$(Get-ToggleStatus `"disable_check_env.txt`" `"禁用`" `"启用`" `$true) },
            @{ id=11; n=`"内核路径前缀`"; v=`$(Get-TextStatus `"core_prefix.txt`" `"自动`") }
        )

        `$menu | ForEach-Object { Write-Log `"`$(`$_.id). `$(`$_.n): `$(`$_.v)`" }
        Write-Log `"12. 检查更新 | 13. 环境检查 | 14. 文档 | 15. 退出`"
        Write-Log `"提示: 输入数字后回车`"

        `$choice = Get-UserInput
        switch (`$choice) {
            `"1`"  { Update-ProxySetting }
            `"2`"  { Set-ToggleSetting `"disable_uv.txt`" `"包管理器`" (Test-Path `"`$PSScriptRoot/disable_uv.txt`") }
            `"3`"  { Update-Mirror-Setting `"hf_mirror.txt`" `"HuggingFace`" @(`"https://hf-mirror.com`", `"https://huggingface.sukaka.top`") }
            `"4`"  { Update-Mirror-Setting `"gh_mirror.txt`" `"Github`" @(`"https://ghfast.top/https://github.com`", `"https://mirror.ghproxy.com/https://github.com`") }
            `"5`"  { Set-ToggleSetting `"disable_update.txt`" `"自动检查更新`" (Test-Path `"`$PSScriptRoot/disable_update.txt`") }
            `"6`"  { 
                Write-Log `"请输入启动参数 (直接回车删除):`"
                `$args = Get-UserInput
                if (`$args) { Write-FileWithStreamWriter -Path `"`$PSScriptRoot/launch_args.txt`" -Value `$args -Encoding UTF8 }
                else { Remove-Item `"`$PSScriptRoot/launch_args.txt`" -Force -ErrorAction SilentlyContinue }
            }
            `"7`"  { Set-ToggleSetting `"enable_shortcut.txt`" `"快捷方式`" (!(Test-Path `"`$PSScriptRoot/enable_shortcut.txt`")) }
            `"8`"  { Set-ToggleSetting `"disable_pypi_mirror.txt`" `"PyPI 镜像`" (Test-Path `"`$PSScriptRoot/disable_pypi_mirror.txt`") }
            `"9`" { Set-ToggleSetting `"disable_set_pytorch_cuda_memory_alloc.txt`" `"CUDA 优化`" (Test-Path `"`$PSScriptRoot/disable_set_pytorch_cuda_memory_alloc.txt`") }
            `"10`" { Set-ToggleSetting `"disable_check_env.txt`" `"环境检测`" (Test-Path `"`$PSScriptRoot/disable_check_env.txt`") }
            `"11`" { Update-Core-Prefix }
            `"12`" { Update-Installer -DisableRestart }
            `"13`" { Test-EnvIntegrity }
            `"14`" { Start-Process `"https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/comfyui_installer.md`" }
            `"15`" { return }
        }
    }
}

###################

Main
Read-Host | Out-Null
".Trim()

    Write-Log "$(if (Test-Path "$script:InstallPath/settings.ps1") { "更新" } else { "生成" }) settings.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path "$script:InstallPath/settings.ps1" -Value $content
}

# 虚拟环境激活脚本
function Write-EnvActivateScript {
    $content = "
param (
    [switch]`$Help,
    [string]`$CorePrefix,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableGithubMirror,
    [switch]`$UseCustomGithubMirror,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisableHuggingFaceMirror,
    [string]`$UseCustomHuggingFaceMirror
)
try {
    `$global:OriginalScriptPath = `$PSCommandPath
    `$global:LaunchCommandLine = `$MyInvocation.Line
    (Import-Module `"`$PSScriptRoot/modules.psm1`" -Function `"Initialize-EnvPath`", `"Write-Log`", `"Set-CorePrefix`", `"Get-Version`" -PassThru -Force -ErrorAction Stop).Invoke({
        `$script:OriginalScriptPath = `$global:OriginalScriptPath
        `$script:LaunchCommandLine = `$global:LaunchCommandLine
        Remove-Variable OriginalScriptPath -Scope Global -Force
        Remove-Variable LaunchCommandLine -Scope Global -Force
        `$script:CorePrefix = `$script:CorePrefix
    })
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White
    Write-Host `"launch_comfyui_installer.ps1`" -ForegroundColor Yellow
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    Read-Host | Out-Null
    exit 1
}


# PyPI 镜像源
`$PIP_INDEX_ADDR = `"https://mirrors.cloud.tencent.com/pypi/simple`"
`$PIP_INDEX_ADDR_ORI = `"https://pypi.python.org/simple`"
`$PIP_EXTRA_INDEX_ADDR = `"https://mirrors.cernet.edu.cn/pypi/web/simple`"
`$PIP_EXTRA_INDEX_ADDR_ORI = `"https://download.pytorch.org/whl`"
`$PIP_FIND_ADDR = `"https://mirrors.aliyun.com/pytorch-wheels/torch_stable.html`"
`$PIP_FIND_ADDR_ORI = `"https://download.pytorch.org/whl/torch_stable.html`"
`$USE_PIP_MIRROR = if ((!(Test-Path `"`$PSScriptRoot/disable_pypi_mirror.txt`")) -and (!(`$script:DisablePyPIMirror))) { `$true } else { `$false }
`$PIP_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_INDEX_ADDR } else { `$PIP_INDEX_ADDR_ORI }
`$PIP_EXTRA_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_EXTRA_INDEX_ADDR } else { `$PIP_EXTRA_INDEX_ADDR_ORI }
`$PIP_FIND_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_FIND_ADDR } else { `$PIP_FIND_ADDR_ORI }
# PATH
`$PYTHON_PATH = `"`$PSScriptRoot/python`"
`$PYTHON_EXTRA_PATH = `"`$PSScriptRoot/`$env:CORE_PREFIX/python`"
`$PYTHON_SCRIPTS_PATH = `"`$PSScriptRoot/python/Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = `"`$PSScriptRoot/`$env:CORE_PREFIX/python/Scripts`"
`$GIT_PATH = `"`$PSScriptRoot/git/bin`"
`$GIT_EXTRA_PATH = `"`$PSScriptRoot/`$env:CORE_PREFIX/git/bin`"
`$env:PATH = `"`$PYTHON_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$GIT_EXTRA_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_PATH`$([System.IO.Path]::PathSeparator)`$PYTHON_SCRIPTS_PATH`$([System.IO.Path]::PathSeparator)`$GIT_PATH`$([System.IO.Path]::PathSeparator)`$env:PATH`"
# 环境变量
`$env:PIP_INDEX_URL = `"`$PIP_INDEX_MIRROR`"
`$env:PIP_EXTRA_INDEX_URL = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`".Trim() } else { `$PIP_EXTRA_INDEX_MIRROR }
`$env:PIP_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$env:UV_DEFAULT_INDEX = `"`$PIP_INDEX_MIRROR`"
`$env:UV_INDEX = if (`$PIP_EXTRA_INDEX_MIRROR -ne `$PIP_EXTRA_INDEX_MIRROR_PYTORCH) { `"`$PIP_EXTRA_INDEX_MIRROR `$PIP_EXTRA_INDEX_MIRROR_PYTORCH`".Trim() } else { `$PIP_EXTRA_INDEX_MIRROR }
`$env:UV_FIND_LINKS = `"`$PIP_FIND_MIRROR`"
`$env:UV_LINK_MODE = `"copy`"
`$env:UV_HTTP_TIMEOUT = 30
`$env:UV_CONCURRENT_DOWNLOADS = 50
`$env:UV_INDEX_STRATEGY = `"unsafe-best-match`"
`$env:PIP_DISABLE_PIP_VERSION_CHECK = 1
`$env:PIP_NO_WARN_SCRIPT_LOCATION = 0
`$env:PIP_TIMEOUT = 30
`$env:PIP_RETRIES = 5
`$env:PIP_PREFER_BINARY = 1
`$env:PIP_YES = 1
`$env:PYTHONUTF8 = 1
`$env:PYTHONIOENCODING = `"utf-8`"
`$env:PYTHONUNBUFFERED = 1
`$env:PYTHONNOUSERSITE = 1
`$env:PYTHONFAULTHANDLER = 1
`$env:PYTHONWARNINGS = `"ignore:::torchvision.transforms.functional_tensor,ignore::UserWarning,ignore::FutureWarning,ignore::DeprecationWarning`"
`$env:GRADIO_ANALYTICS_ENABLED = `"False`"
`$env:HF_HUB_DISABLE_SYMLINKS_WARNING = 1
`$env:BITSANDBYTES_NOWELCOME = 1
`$env:ClDeviceGlobalMemSizeAvailablePercent = 100
`$env:CUDA_MODULE_LOADING = `"LAZY`"
`$env:TORCH_CUDNN_V8_API_ENABLED = 1
`$env:USE_LIBUV = 0
`$env:SYCL_CACHE_PERSISTENT = 1
`$env:TF_CPP_MIN_LOG_LEVEL = 3
`$env:SAFETENSORS_FAST_GPU = 1
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
`$env:TORCHINDUCTOR_CACHE_DIR = `"`$PSScriptRoot/cache/torchinductor`"
`$env:TRITON_CACHE_DIR = `"`$PSScriptRoot/cache/triton`"
`$env:UV_CACHE_DIR = `"`$PSScriptRoot/cache/uv`"
`$env:UV_PYTHON = `"`$PSScriptRoot/python/python.exe`"
`$env:COMFYUI_PATH = `"`$PSScriptRoot/`$env:CORE_PREFIX`"
`$env:COMFYUI_INSTALLER_ROOT = `$PSScriptRoot



# 帮助信息
function Get-InstallerCmdletHelp {
    `$content = `"
使用:
    .\`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-DisablePyPIMirror] [-DisableGithubMirror] [-UseCustomGithubMirror <github 镜像源地址>] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>]

参数:
    -Help
        获取 ComfyUI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -DisablePyPIMirror
        禁用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableGithubMirror
        禁用 ComfyUI Installer 自动设置 Github 镜像源

    -UseCustomGithubMirror <Github 镜像站地址>
        使用自定义的 Github 镜像站地址

    -DisableProxy
        禁用 ComfyUI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址

    -DisableHuggingFaceMirror
        禁用 HuggingFace 镜像源, 不使用 HuggingFace 镜像源下载文件

    -UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>
        使用自定义 HuggingFace 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror ```"https://hf-mirror.com```" 设置 HuggingFace 镜像源地址


更多的帮助信息请阅读 ComfyUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/comfyui_installer.md
`".Trim()

    if (`$Help) {
        Write-Host `$content
        exit 0
    }
}


# 提示符信息
function global:prompt {
    `"`$(Write-Host `"[SD Trainer Scripts Env]`" -ForegroundColor Green -NoNewLine) `$(Get-Location)> `"
}


# 安装绘世启动器
function global:Install-Hanamizuki {
    `$urls = @(
        `"https://modelscope.cn/models/licyks/invokeai-core-model/resolve/master/pypatchmatch/hanamizuki.exe`",
        `"https://github.com/licyk/term-sd/releases/download/archive/hanamizuki.exe`",
        `"https://gitee.com/licyk/term-sd/releases/download/archive/hanamizuki.exe`"
    )
    `$i = 0

    if (!(Test-Path `"`$env:COMFYUI_INSTALLER_ROOT/`$env:CORE_PREFIX`")) {
        Write-Log `"内核路径 `$env:COMFYUI_INSTALLER_ROOT/`$env:CORE_PREFIX 未找到, 无法安装绘世启动器, 请检查 ComfyUI 是否已正确安装, 或者尝试运行 ComfyUI Installer 进行修复`"
        return
    }

    New-Item -ItemType Directory -Path `"`$env:CACHE_HOME`" -Force > `$null

    if (Test-Path `"`$env:COMFYUI_INSTALLER_ROOT/`$env:CORE_PREFIX/hanamizuki.exe`") {
        Write-Log `"绘世启动器已安装, 路径: `$([System.IO.Path]::GetFullPath(`"`$env:COMFYUI_INSTALLER_ROOT/`$env:CORE_PREFIX/hanamizuki.exe`"))`"
        Write-Log `"可以进入该路径启动绘世启动器, 也可运行 hanamizuki.bat 启动绘世启动器`"
    } else {
        ForEach (`$url in `$urls) {
            Write-Log `"下载绘世启动器中`"
            try {
                `$web_request_params = @{
                    Uri = `$url
                    UseBasicParsing = `$true
                    OutFile = `"`$env:CACHE_HOME/hanamizuki_tmp.exe`"
                }
                Invoke-WebRequest @web_request_params
                Move-Item -Path `"`$env:CACHE_HOME/hanamizuki_tmp.exe`" `"`$env:COMFYUI_INSTALLER_ROOT/`$env:CORE_PREFIX/hanamizuki.exe`" -Force
                Write-Log `"绘世启动器安装成功, 路径: `$([System.IO.Path]::GetFullPath(`"`$env:COMFYUI_INSTALLER_ROOT/`$env:CORE_PREFIX/hanamizuki.exe`"))`"
                Write-Log `"可以进入该路径启动绘世启动器, 也可运行 hanamizuki.bat 启动绘世启动器`"
                break
            }
            catch {
                `$i += 1
                if (`$i -lt `$urls.Length) {
                    Write-Log `"重试下载绘世启动器中`" -Level WARNING
                } else {
                    Write-Log `"下载绘世启动器失败`"
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
set DefaultCorePrefix=ComfyUI
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
    for /f ```"delims=```" %%i in ('powershell -NoProfile -Command ```"(Get-Content -Path '%CorePrefixFile%' -Raw).Trim()```"') do (
        set CorePrefix=%%i
        goto :convert
    )
)

:convert
for /f ```"delims=```" %%i in ('powershell -NoProfile -Command ```"```$current_path = '%CurrentPath%'.Trim('/').Trim('\'); ```$origin_core_prefix = '%CorePrefix%'.Trim('/').Trim('\'); if ([System.IO.Path]::IsPathRooted(```$origin_core_prefix)) { ```$to_path = ```$origin_core_prefix; ```$from_uri = New-Object System.Uri(```$current_path.Replace('\', '/') + '/'); ```$to_uri = New-Object System.Uri(```$to_path.Replace('\', '/')); ```$origin_core_prefix = ```$from_uri.MakeRelativeUri(```$to_uri).ToString().Trim('/') }; Write-Host ```$origin_core_prefix```"') do (
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
    echo Please check if ComfyUI is installed, or if the CorePrefix is set correctly
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

    Set-Content -Encoding Default -Path `"`$env:COMFYUI_INSTALLER_ROOT/hanamizuki.bat`" -Value `$content

    Write-Log `"检查绘世启动器运行环境`"
    if (!(Test-Path `"`$env:COMFYUI_INSTALLER_ROOT/`$env:CORE_PREFIX/python/python.exe`")) {
        if (Test-Path `"`$env:COMFYUI_INSTALLER_ROOT/python`") {
            Write-Log `"尝试将 Python 移动至 `$env:COMFYUI_INSTALLER_ROOT\`$env:CORE_PREFIX 中`"
            Move-Item -Path `"`$env:COMFYUI_INSTALLER_ROOT/python`" `"`$env:COMFYUI_INSTALLER_ROOT/`$env:CORE_PREFIX`" -Force
            if (`$?) {
                Write-Log `"Python 路径移动成功`"
            } else {
                Write-Log `"Python 路径移动失败, 这将导致绘世启动器无法正确识别到 Python 环境`"
                Write-Log `"请关闭所有占用 Python 的进程, 并重新运行该命令`"
            }
        } else {
            Write-Log `"环境缺少 Python, 无法为绘世启动器准备 Python 环境, 请重新运行 ComfyUI Installer 修复环境`"
        }
    }

    if (!(Test-Path `"`$env:COMFYUI_INSTALLER_ROOT/`$env:CORE_PREFIX/git/bin/git.exe`")) {
        if (Test-Path `"`$env:COMFYUI_INSTALLER_ROOT/git`") {
            Write-Log `"尝试将 Git 移动至 `$env:COMFYUI_INSTALLER_ROOT\`$env:CORE_PREFIX 中`"
            Move-Item -Path `"`$env:COMFYUI_INSTALLER_ROOT/git`" `"`$env:COMFYUI_INSTALLER_ROOT/`$env:CORE_PREFIX`" -Force
            if (`$?) {
                Write-Log `"Git 路径移动成功`"
            } else {
                Write-Log `"Git 路径移动失败, 这将导致绘世启动器无法正确识别到 Git 环境`"
                Write-Log `"请关闭所有占用 Git 的进程, 并重新运行该命令`"
            }
        } else {
            Write-Log `"环境缺少 Git, 无法为绘世启动器准备 Git 环境, 请重新运行 ComfyUI Installer 修复环境`"
        }
    }

    Write-Log `"检查绘世启动器运行环境结束`"
}


function global:pip {
    python -m pip @args
}

function global:sd-webui-all-in-one {
    & python -m sd_webui_all_in_one.cli_manager.main @args
}

Set-Alias pip3 pip
Set-Alias pip3.11 pip
Set-Alias python3 python
Set-Alias python3.11 python


# 列出 ComfyUI Installer 内置命令
function global:List-CMD {
    Write-Host `"
==================================
ComfyUI Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
==================================

当前可用的 ComfyUI Installer 内置命令：

    Install-Hanamizuki
    List-CMD

更多帮助信息可在 ComfyUI Installer 文档中查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/comfyui_installer.md
`"
}


# PyPI 镜像源状态
function Get-PyPIMirrorStatus {
    if (`$USE_PIP_MIRROR) {
        Write-Log `"使用 PyPI 镜像源`"
    } else {
        Write-Log `"检测到 disable_pypi_mirror.txt 配置文件 / -DisablePyPIMirror, 命令行参数 已将 PyPI 源切换至官方源`"
    }
}


# 代理配置
function Set-Proxy {
    `$env:NO_PROXY = `"localhost,127.0.0.1,::1`"
    # 检测是否禁用自动设置镜像源
    if ((Test-Path `"`$PSScriptRoot/disable_proxy.txt`") -or (`$script:DisableProxy)) {
        Write-Log `"检测到本地存在 disable_proxy.txt 代理配置文件 / -DisableProxy 命令行参数, 禁用自动设置代理`"
        return
    }

    `$internet_setting = Get-ItemProperty -Path `"HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings`"
    if ((Test-Path `"`$PSScriptRoot/proxy.txt`") -or (`$script:UseCustomProxy)) { # 本地存在代理配置
        if (`$script:UseCustomProxy) {
            `$proxy_value = `$script:UseCustomProxy
        } else {
            `$proxy_value = (Get-Content `"`$PSScriptRoot/proxy.txt`" -Raw).Trim()
        }
        `$env:HTTP_PROXY = `$proxy_value
        `$env:HTTPS_PROXY = `$proxy_value
        Write-Log `"检测到本地存在 proxy.txt 代理配置文件 / -UseCustomProxy 命令行参数, 已读取代理配置文件并设置代理`"
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
        `$env:HTTP_PROXY = `$proxy_value
        `$env:HTTPS_PROXY = `$proxy_value
        Write-Log `"检测到系统设置了代理, 已读取系统中的代理配置并设置代理`"
    }
}


# HuggingFace 镜像源
function Set-HuggingFaceMirror {
    if ((Test-Path `"`$PSScriptRoot/disable_hf_mirror.txt`") -or (`$script:DisableHuggingFaceMirror)) { # 检测是否禁用了自动设置 HuggingFace 镜像源
        Write-Log `"检测到本地存在 disable_hf_mirror.txt 镜像源配置文件 / -DisableHuggingFaceMirror 命令行参数, 禁用自动设置 HuggingFace 镜像源`"
        return
    }

    if ((Test-Path `"`$PSScriptRoot/hf_mirror.txt`") -or (`$script:UseCustomHuggingFaceMirror)) { # 本地存在 HuggingFace 镜像源配置
        if (`$script:UseCustomHuggingFaceMirror) {
            `$hf_mirror_value = `$script:UseCustomHuggingFaceMirror
        } else {
            `$hf_mirror_value = (Get-Content `"`$PSScriptRoot/hf_mirror.txt`" -Raw).Trim()
        }
        `$env:HF_ENDPOINT = `$hf_mirror_value
        Write-Log `"检测到本地存在 hf_mirror.txt 配置文件 / -UseCustomHuggingFaceMirror 命令行参数, 已读取该配置并设置 HuggingFace 镜像源`"
    } else { # 使用默认设置
        `$env:HF_ENDPOINT = `"https://hf-mirror.com`"
        Write-Log `"使用默认 HuggingFace 镜像源`"
    }
}


# Github 镜像源
function Set-GithubMirrorLegecy {
    `$env:GIT_CONFIG_GLOBAL = `"`$PSScriptRoot/.gitconfig`" # 设置 Git 配置文件路径
    if (Test-Path `"`$PSScriptRoot/.gitconfig`") {
        Remove-Item -Path `"`$PSScriptRoot/.gitconfig`" -Force -Recurse
    }

    # 默认 Git 配置
    git config --global --add safe.directory '*'
    git config --global core.longpaths true

    if ((Test-Path `"`$PSScriptRoot/disable_gh_mirror.txt`") -or (`$script:DisableGithubMirror)) { # 禁用 Github 镜像源
        Write-Log `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件 / -DisableGithubMirror 命令行参数, 禁用 Github 镜像源`"
        return
    }

    # 使用自定义 Github 镜像源
    if ((Test-Path `"`$PSScriptRoot/gh_mirror.txt`") -or (`$script:UseCustomGithubMirror)) {
        if (`$script:UseCustomGithubMirror) {
            `$github_mirror = `$script:UseCustomGithubMirror
        } else {
            `$github_mirror = (Get-Content `"`$PSScriptRoot/gh_mirror.txt`" -Raw).Trim()
        }
        git config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
        Write-Log `"检测到本地存在 gh_mirror.txt Github 镜像源配置文件 / -UseCustomGithubMirror 命令行参数, 已读取 Github 镜像源配置文件并设置 Github 镜像源`"
    }
}


function Main {
    Get-InstallerCmdletHelp
    Get-Version
    Set-CorePrefix
    Initialize-EnvPath
    Set-Proxy
    Set-HuggingFaceMirror
    Set-GithubMirrorLegecy
    Get-PyPIMirrorStatus

    if (Test-Path `"`$env:COMFYUI_INSTALLER_ROOT/`$env:CORE_PREFIX/python/python.exe`") {
        `$env:UV_PYTHON = `"`$env:COMFYUI_INSTALLER_ROOT/`$env:CORE_PREFIX/python/python.exe`"
    }
    Write-Log `"激活 SD Trainer Scripts Env`"
    Write-Log `"更多帮助信息可在 ComfyUI Installer 项目地址查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/comfyui_installer.md`"
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path "$script:InstallPath/activate.ps1") { "更新" } else { "生成" }) activate.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path "$script:InstallPath/activate.ps1" -Value $content
}


# 快捷启动终端脚本, 启动后将自动运行环境激活脚本
function Write-LaunchTerminalScript {
    $content = "
try {
    `$global:OriginalScriptPath = `$PSCommandPath
    `$global:LaunchCommandLine = `$MyInvocation.Line
    (Import-Module `"`$PSScriptRoot/modules.psm1`" -Function `"Write-Log`" -PassThru -Force -ErrorAction Stop).Invoke({
        `$script:OriginalScriptPath = `$global:OriginalScriptPath
        `$script:LaunchCommandLine = `$global:LaunchCommandLine
        Remove-Variable OriginalScriptPath -Scope Global -Force
        Remove-Variable LaunchCommandLine -Scope Global -Force
    })
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White
    Write-Host `"launch_comfyui_installer.ps1`" -ForegroundColor Yellow
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    Read-Host | Out-Null
    exit 1
}
Write-Log `"执行 ComfyUI Installer 激活环境脚本`"
powershell -NoExit -File `"`$PSScriptRoot/activate.ps1`"
".Trim()

    Write-Log "$(if (Test-Path "$script:InstallPath/terminal.ps1") { "更新" } else { "生成" }) terminal.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path "$script:InstallPath/terminal.ps1" -Value $content
}


# 帮助文档
function Write-ReadMe {
    $content = "
====================================================================
ComfyUI Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
====================================================================
########## 使用帮助 ##########

这是关于 ComfyUI 的简单使用文档。

使用 ComfyUI Installer 进行安装并安装成功后，将在当前目录生成 ComfyUI 文件夹，以下为文件夹中不同文件 / 文件夹的作用。

- launch.ps1：启动 ComfyUI。
- update.ps1：更新 ComfyUI。
- update_node.ps1：更新 ComfyUI 扩展。
- download_models.ps1：下载模型的脚本，下载的模型将存放在 ComfyUI 的模型文件夹中。
- reinstall_pytorch.ps1：重新安装 PyTorch 的脚本，在 PyTorch 出问题或者需要切换 PyTorch 版本时可使用。
- settings.ps1：管理 ComfyUI Installer 的设置。
- terminal.ps1：启动 PowerShell 终端并自动激活虚拟环境，激活虚拟环境后即可使用 Python、Pip、Git 的命令
- activate.ps1：虚拟环境激活脚本，使用该脚本激活虚拟环境后即可使用 Python、Pip、Git 的命令。
- launch_comfyui_installer.ps1：获取最新的 ComfyUI Installer 安装脚本并运行。
- configure_env.bat：配置环境脚本，修复 PowerShell 运行闪退和启用 Windows 长路径支持。

- cache：缓存文件夹，保存着 Pip / HuggingFace 等缓存文件。
- python：Python 的存放路径。请注意，请勿将该 Python 文件夹添加到环境变量，这可能导致不良后果。
- git：Git 的存放路径。
- ComfyUI / core：ComfyUI 内核。

详细的 ComfyUI Installer 使用帮助：https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/comfyui_installer.md

ComfyUI 的使用教程：
https://sdnote.netlify.app/guide/comfyui
https://sdnote.netlify.app/help/comfyui
https://docs.comfy.org/zh-CN/get_started/first_generation
https://www.aigodlike.com
https://space.bilibili.com/35723238/channel/collectiondetail?sid=1320931
https://comfyanonymous.github.io/ComfyUI_examples
https://blenderneko.github.io/ComfyUI-docs
https://comfyui-wiki.com/zh


====================================================================
########## Github 项目 ##########

sd-webui-all-in-one 项目地址：https://github.com/licyk/sd-webui-all-in-one
ComfyUI 项目地址：https://github.com/comfyanonymous/ComfyUI


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

    Write-Log "$(if (Test-Path "$script:InstallPath/help.txt") { "更新" } else { "生成" }) help.txt 中"
    Write-FileWithStreamWriter -Encoding UTF8 "$script:InstallPath/help.txt" -Value $content
}


# 写入管理脚本和文档
function Write-ManagerScripts {
    New-Item -ItemType Directory -Path $script:InstallPath -Force | Out-Null
    Write-ModulesScript
    Write-LaunchScript
    Write-UpdateScript
    Write-UpdateNodeScript
    Write-LaunchInstallerScript
    Write-PyTorchReInstallScript
    Write-DownloadModelScript
    Write-SettingsScript
    Write-EnvActivateScript
    Write-LaunchTerminalScript
    Write-ReadMe
    Write-ConfigureEnvScript
    Write-HanamizukiScript
}


# 将安装器配置文件复制到管理脚本路径
function Copy-InstallerConfig {
    Write-Log "为 ComfyUI Installer 管理脚本复制 ComfyUI Installer 配置文件中"

    if ((!($script:DisablePyPIMirror)) -and (Test-Path "$PSScriptRoot/disable_pypi_mirror.txt")) {
        Copy-Item -Path "$PSScriptRoot/disable_pypi_mirror.txt" -Destination "$script:InstallPath"
        Write-Log "$PSScriptRoot/disable_pypi_mirror.txt -> $script:InstallPath/disable_pypi_mirror.txt" -Force
    }

    if ((!($script:DisableProxy)) -and (Test-Path "$PSScriptRoot/disable_proxy.txt")) {
        Copy-Item -Path "$PSScriptRoot/disable_proxy.txt" -Destination "$script:InstallPath" -Force
        Write-Log "$PSScriptRoot/disable_proxy.txt -> $script:InstallPath/disable_proxy.txt" -Force
    } elseif ((!($script:DisableProxy)) -and ($script:UseCustomProxy -eq "") -and (Test-Path "$PSScriptRoot/proxy.txt") -and (!(Test-Path "$PSScriptRoot/disable_proxy.txt"))) {
        Copy-Item -Path "$PSScriptRoot/proxy.txt" -Destination "$script:InstallPath" -Force
        Write-Log "$PSScriptRoot/proxy.txt -> $script:InstallPath/proxy.txt"
    }

    if ((!($script:DisableUV)) -and (Test-Path "$PSScriptRoot/disable_uv.txt")) {
        Copy-Item -Path "$PSScriptRoot/disable_uv.txt" -Destination "$script:InstallPath" -Force
        Write-Log "$PSScriptRoot/disable_uv.txt -> $script:InstallPath/disable_uv.txt" -Force
    }

    if ((!($script:DisableGithubMirror)) -and (Test-Path "$PSScriptRoot/disable_gh_mirror.txt")) {
        Copy-Item -Path "$PSScriptRoot/disable_gh_mirror.txt" -Destination "$script:InstallPath" -Force
        Write-Log "$PSScriptRoot/disable_gh_mirror.txt -> $script:InstallPath/disable_gh_mirror.txt"
    } elseif ((!($script:DisableGithubMirror)) -and (!($script:UseCustomGithubMirror)) -and (Test-Path "$PSScriptRoot/gh_mirror.txt") -and (!(Test-Path "$PSScriptRoot/disable_gh_mirror.txt"))) {
        Copy-Item -Path "$PSScriptRoot/gh_mirror.txt" -Destination "$script:InstallPath" -Force
        Write-Log "$PSScriptRoot/gh_mirror.txt -> $script:InstallPath/gh_mirror.txt"
    }

    if ((!($script:CorePrefix)) -and (Test-Path "$PSScriptRoot/core_prefix.txt")) {
        Copy-Item -Path "$PSScriptRoot/core_prefix.txt" -Destination "$script:InstallPath" -Force
        Write-Log "$PSScriptRoot/core_prefix.txt -> $script:InstallPath/core_prefix.txt" -Force
    }
}


# 写入启动绘世启动器脚本
function Write-HanamizukiScript {
    param ([switch]$Force)
    $content = "
@echo off
echo Initialize configuration
setlocal enabledelayedexpansion
set CurrentPath=%~dp0
set DefaultCorePrefix=ComfyUI
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
    for /f `"delims=`" %%i in ('powershell -NoProfile -Command `"(Get-Content -Path '%CorePrefixFile%' -Raw).Trim()`"') do (
        set CorePrefix=%%i
        goto :convert
    )
)

:convert
for /f `"delims=`" %%i in ('powershell -NoProfile -Command `"`$current_path = '%CurrentPath%'.Trim('/').Trim('\'); `$origin_core_prefix = '%CorePrefix%'.Trim('/').Trim('\'); if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix)) { `$to_path = `$origin_core_prefix; `$from_uri = New-Object System.Uri(`$current_path.Replace('\', '/') + '/'); `$to_uri = New-Object System.Uri(`$to_path.Replace('\', '/')); `$origin_core_prefix = `$from_uri.MakeRelativeUri(`$to_uri).ToString().Trim('/') }; Write-Host `$origin_core_prefix`"') do (
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
    echo Please check if ComfyUI is installed, or if the CorePrefix is set correctly
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

    if ((!($Force)) -and (!(Test-Path "$script:InstallPath/hanamizuki.bat"))) {
        return
    }

    Write-Log "$(if (Test-Path "$script:InstallPath/hanamizuki.bat") { "更新" } else { "生成" }) hanamizuki.bat 中"
    Write-FileWithStreamWriter -Encoding GBK "$script:InstallPath/hanamizuki.bat" -Value $content
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

    New-Item -ItemType Directory -Path "$env:CACHE_HOME" -Force > $null

    if (Test-Path "$script:InstallPath/$env:CORE_PREFIX/hanamizuki.exe") {
        Write-Log "绘世启动器已安装, 路径: $([System.IO.Path]::GetFullPath("$script:InstallPath/$env:CORE_PREFIX/hanamizuki.exe"))"
        Write-Log "可以进入该路径启动绘世启动器, 也可运行 hanamizuki.bat 启动绘世启动器"
    } else {
        ForEach ($url in $urls) {
            Write-Log "下载绘世启动器中"
            try {
                $web_request_params = @{
                    Uri = $url
                    UseBasicParsing = $true
                    OutFile = "$env:CACHE_HOME/hanamizuki_tmp.exe"
                }
                Invoke-WebRequest @web_request_params
                Move-Item -Path "$env:CACHE_HOME/hanamizuki_tmp.exe" "$script:InstallPath/$env:CORE_PREFIX/hanamizuki.exe" -Force
                Write-Log "绘世启动器安装成功, 路径: $([System.IO.Path]::GetFullPath("$script:InstallPath/$env:CORE_PREFIX/hanamizuki.exe"))"
                Write-Log "可以进入该路径启动绘世启动器, 也可运行 hanamizuki.bat 启动绘世启动器"
                break
            }
            catch {
                $i += 1
                if ($i -lt $urls.Length) {
                    Write-Log "重试下载绘世启动器中" -Level WARNING
                } else {
                    Write-Log "下载绘世启动器失败"
                    return
                }
            }
        }
    }
}


# 配置绘世启动器运行环境
function Initialize-HanamizukiEnv {
    if (!(Test-Path "$script:InstallPath/$env:CORE_PREFIX/hanamizuki.exe")) {
        return
    }

    Write-HanamizukiScript -Force

    Write-Log "检查绘世启动器运行环境"
    if (!(Test-Path "$script:InstallPath/$env:CORE_PREFIX/python/python.exe")) {
        if (Test-Path "$script:InstallPath/python") {
            Write-Log "尝试将 Python 移动至 $script:InstallPath\$env:CORE_PREFIX 中"
            Move-Item -Path "$script:InstallPath/python" "$script:InstallPath/$env:CORE_PREFIX" -Force
            if ($?) {
                Write-Log "Python 路径移动成功"
            } else {
                Write-Log "Python 路径移动失败, 这将导致绘世启动器无法正确识别到 Python 环境"
                Write-Log "请关闭所有占用 Python 的进程, 并重新运行该命令"
            }
        } else {
            Write-Log "环境缺少 Python, 无法为绘世启动器准备 Python 环境, 请重新运行 ComfyUI Installer 修复环境"
        }
    }

    if (!(Test-Path "$script:InstallPath/$env:CORE_PREFIX/git/bin/git.exe")) {
        if (Test-Path "$script:InstallPath/git") {
            Write-Log "尝试将 Git 移动至 $script:InstallPath\$env:CORE_PREFIX 中"
            Move-Item -Path "$script:InstallPath/git" "$script:InstallPath/$env:CORE_PREFIX" -Force
            if ($?) {
                Write-Log "Git 路径移动成功"
            } else {
                Write-Log "Git 路径移动失败, 这将导致绘世启动器无法正确识别到 Git 环境"
                Write-Log "请关闭所有占用 Git 的进程, 并重新运行该命令"
            }
        } else {
            Write-Log "环境缺少 Git, 无法为绘世启动器准备 Git 环境, 请重新运行 ComfyUI Installer 修复环境"
        }
    }

    Write-Log "检查绘世启动器运行环境结束"
}


# 执行安装
function Use-InstallMode {
    Write-Log "启动 ComfyUI 安装程序"
    Write-Log "提示: 若出现某个步骤执行失败, 可尝试再次运行 ComfyUI Installer, 更多的说明请阅读 ComfyUI Installer 使用文档"
    Write-Log "ComfyUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/comfyui_installer.md"
    Write-Log "即将进行安装的路径: $script:InstallPath"
    Invoke-Installation
    Write-Log "添加管理脚本和文档中"
    Write-ManagerScripts
    Copy-InstallerConfig

    if ($script:BuildMode) {
        Use-BuildMode
        Install-Hanamizuki
        Initialize-HanamizukiEnv
        Write-Log "ComfyUI 环境构建完成, 路径: $script:InstallPath"
    } else {
        Install-Hanamizuki
        Initialize-HanamizukiEnv
        Write-Log "ComfyUI 安装结束, 安装路径为: $script:InstallPath"
    }

    Write-Log "帮助文档可在 ComfyUI 文件夹中查看, 双击 help.txt 文件即可查看, 更多的说明请阅读 ComfyUI Installer 使用文档"
    Write-Log "ComfyUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/comfyui_installer.md"
    Write-Log "退出 ComfyUI Installer"

    if (!($script:BuildMode)) { Read-Host | Out-Null }
}


# 执行管理脚本更新
function Use-UpdateMode {
    Write-Log "更新管理脚本和文档中"
    Write-ManagerScripts
    Write-Log "更新管理脚本和文档完成"
}


# 执行管理脚本完成其他环境构建
function Use-BuildMode {
    Write-Log "执行其他环境构建脚本中"

    if ($script:BuildWithTorch) {
        $launch_args = @{}
        $launch_args.Add("-BuildMode", $true)
        $launch_args.Add("-BuildWithTorch", $script:BuildWithTorch)
        if ($script:BuildWithTorchReinstall) { $launch_args.Add("-BuildWithTorchReinstall", $true) }
        if ($script:DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($script:DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($script:DisableUV) { $launch_args.Add("-DisableUV", $true) }
        if ($script:DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($script:UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $script:UseCustomProxy) }
        if ($script:CorePrefix) { $launch_args.Add("-CorePrefix", $script:CorePrefix) }
        Write-Log "执行重装 PyTorch 脚本中"
        . "$InstallPath/reinstall_pytorch.ps1" @launch_args
    }

    if ($script:BuildWitchModel) {
        $launch_args = @{}
        $launch_args.Add("-BuildMode", $true)
        $launch_args.Add("-BuildWitchModel", $script:BuildWitchModel)
        if ($script:DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($script:DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($script:UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $script:UseCustomProxy) }
        if ($script:DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($script:CorePrefix) { $launch_args.Add("-CorePrefix", $script:CorePrefix) }
        Write-Log "执行模型安装脚本中"
        . "$script:InstallPath/download_models.ps1" @launch_args
    }

    if ($script:BuildWithUpdate) {
        $launch_args = @{}
        $launch_args.Add("-BuildMode", $true)
        if ($script:DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($script:DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($script:DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($script:UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $script:UseCustomProxy) }
        if ($script:DisableGithubMirror) { $launch_args.Add("-DisableGithubMirror", $true) }
        if ($script:UseCustomGithubMirror) { $launch_args.Add("-UseCustomGithubMirror", $script:UseCustomGithubMirror) }
        if ($script:CorePrefix) { $launch_args.Add("-CorePrefix", $script:CorePrefix) }
        Write-Log "执行 ComfyUI 更新脚本中"
        . "$InstallPath/update.ps1" @launch_args
    }

    if ($script:BuildWithUpdateNode) {
        $launch_args = @{}
        $launch_args.Add("-BuildMode", $true)
        if ($script:DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($script:DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($script:DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($script:UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $script:UseCustomProxy) }
        if ($script:DisableGithubMirror) { $launch_args.Add("-DisableGithubMirror", $true) }
        if ($script:UseCustomGithubMirror) { $launch_args.Add("-UseCustomGithubMirror", $script:UseCustomGithubMirror) }
        if ($script:CorePrefix) { $launch_args.Add("-CorePrefix", $script:CorePrefix) }
        Write-Log "执行 ComfyUI 扩展更新脚本中"
        . "$InstallPath/update_node.ps1" @launch_args
    }

    if ($script:BuildWithLaunch) {
        $launch_args = @{}
        $launch_args.Add("-BuildMode", $true)
        if ($script:DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($script:DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($script:DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($script:UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $script:UseCustomProxy) }
        if ($script:DisableHuggingFaceMirror) { $launch_args.Add("-DisableHuggingFaceMirror", $true) }
        if ($script:UseCustomHuggingFaceMirror) { $launch_args.Add("-UseCustomHuggingFaceMirror", $script:UseCustomHuggingFaceMirror) }
        if ($script:DisableGithubMirror) { $launch_args.Add("-DisableGithubMirror", $true) }
        if ($script:UseCustomGithubMirror) { $launch_args.Add("-UseCustomGithubMirror", $script:UseCustomGithubMirror) }
        if ($script:DisableUV) { $launch_args.Add("-DisableUV", $true) }
        if ($script:LaunchArg) { $launch_args.Add("-LaunchArg", $script:LaunchArg) }
        if ($script:EnableShortcut) { $launch_args.Add("-EnableShortcut", $true) }
        if ($script:DisableCUDAMalloc) { $launch_args.Add("-DisableCUDAMalloc", $true) }
        if ($script:DisableEnvCheck) { $launch_args.Add("-DisableEnvCheck", $true) }
        if ($script:CorePrefix) { $launch_args.Add("-CorePrefix", $script:CorePrefix) }
        Write-Log "执行 ComfyUI 启动脚本中"
        . "$InstallPath/launch.ps1" @launch_args
    }

    # 清理缓存
    if (!($script:NoCleanCache)) {
        Write-Log "清理下载 Python 软件包的缓存中"
        & python -m pip cache purge
        & uv cache clean
    }
}


# 环境配置脚本
function Write-ConfigureEnvScript {
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
    powershell -NoProfile -Command `"Set-ExecutionPolicy Unrestricted -Scope CurrentUser`"
    echo :: Enable long paths supported
    echo :: Executing command: `"New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force`"
    powershell -NoProfile -Command `"New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force`"
    echo :: Configure completed
    echo :: Exit environment configuration script 
    pause
".Trim()

    Write-Log "$(if (Test-Path "$script:InstallPath/configure_env.bat") { "更新" } else { "生成" }) configure_env.bat 中"
    Write-FileWithStreamWriter -Encoding GBK "$script:InstallPath/configure_env.bat" -Value $content
}


# 帮助信息
function Get-InstallerCmdletHelp {
    $content = "
使用:
    .\$($script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-InstallPath <安装 ComfyUI 的绝对路径>] [-PyTorchMirrorType <PyTorch 镜像源类型>] [-UseUpdateMode] [-DisablePyPIMirror] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableUV] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像站地址>] [-BuildMode] [-BuildWithUpdate] [-BuildWithUpdateNode] [-BuildWithLaunch] [-BuildWithTorch <PyTorch 版本编号>] [-BuildWithTorchReinstall] [-BuildWitchModel <模型编号列表>] [-NoPreDownloadNode] [-NoPreDownloadModel] [-PyTorchPackage <PyTorch 软件包>] [-InstallHanamizuki] [-NoCleanCache] [-xFormersPackage <xFormers 软件包>] [-DisableUpdate] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>] [-LaunchArg <ComfyUI 启动参数>] [-EnableShortcut] [-DisableCUDAMalloc] [-DisableEnvCheck]

参数:
    -Help
        获取 ComfyUI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -InstallPath <安装 ComfyUI 的绝对路径>
        指定 ComfyUI Installer 安装 ComfyUI 的路径, 使用绝对路径表示
        例如: .\$($script:MyInvocation.MyCommand.Name) -InstallPath `"D:\Donwload`", 这将指定 ComfyUI Installer 安装 ComfyUI 到 D:\Donwload 这个路径

    -PyTorchMirrorType <PyTorch 镜像源类型>
        指定安装 PyTorch 时使用的 PyTorch 镜像源类型, 可指定的类型: cpu, xpu, cu11x, cu118, cu121, cu124, cu126, cu128, cu129, cu130

    -UseUpdateMode
        指定 ComfyUI Installer 使用更新模式, 只对 ComfyUI Installer 的管理脚本进行更新

    -DisablePyPIMirror
        禁用 ComfyUI Installer 使用 PyPI 镜像源, 使用 PyPI 官方源下载 Python 软件包

    -DisableProxy
        禁用 ComfyUI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy `"http://127.0.0.1:10809`" 设置代理服务器地址

    -DisableUV
        禁用 ComfyUI Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -DisableGithubMirror
        禁用 ComfyUI Installer 自动设置 Github 镜像源

    -UseCustomGithubMirror <Github 镜像站地址>
        使用自定义的 Github 镜像站地址

    -BuildMode
        启用 ComfyUI Installer 构建模式, 在基础安装流程结束后将调用 ComfyUI Installer 管理脚本执行剩余的安装任务, 并且出现错误时不再暂停 ComfyUI Installer 的执行, 而是直接退出
        当指定调用多个 ComfyUI Installer 脚本时, 将按照优先顺序执行 (按从上到下的顺序)
            - reinstall_pytorch.ps1     (对应 -BuildWithTorch, -BuildWithTorchReinstall 参数)
            - download_models.ps1       (对应 -BuildWitchModel 参数)
            - update.ps1                (对应 -BuildWithUpdate 参数)
            - update_node.ps1           (对应 -BuildWithUpdateNode 参数)
            - launch.ps1                (对应 -BuildWithLaunch 参数)

    -BuildWithUpdate
        (需添加 -BuildMode 启用 ComfyUI Installer 构建模式) ComfyUI Installer 执行完基础安装流程后调用 ComfyUI Installer 的 update.ps1 脚本, 更新 ComfyUI 内核

    -BuildWithUpdateNode
        (需添加 -BuildMode 启用 ComfyUI Installer 构建模式) ComfyUI Installer 执行完基础安装流程后调用 ComfyUI Installer 的 update_node.ps1 脚本, 更新 ComfyUI 扩展

    -BuildWithLaunch
        (需添加 -BuildMode 启用 ComfyUI Installer 构建模式) ComfyUI Installer 执行完基础安装流程后调用 ComfyUI Installer 的 launch.ps1 脚本, 执行启动 ComfyUI 前的环境检查流程, 但跳过启动 ComfyUI

    -BuildWithTorch <PyTorch 版本编号>
        (需添加 -BuildMode 启用 ComfyUI Installer 构建模式) ComfyUI Installer 执行完基础安装流程后调用 ComfyUI Installer 的 reinstall_pytorch.ps1 脚本, 根据 PyTorch 版本编号安装指定的 PyTorch 版本
        PyTorch 版本编号可运行 reinstall_pytorch.ps1 脚本进行查看

    -BuildWithTorchReinstall
        (需添加 -BuildMode 启用 ComfyUI Installer 构建模式, 并且添加 -BuildWithTorch) 在 ComfyUI Installer 构建模式下, 执行 reinstall_pytorch.ps1 脚本对 PyTorch 进行指定版本安装时使用强制重新安装

    -BuildWitchModel <模型编号列表>
        (需添加 -BuildMode 启用 ComfyUI Installer 构建模式) ComfyUI Installer 执行完基础安装流程后调用 ComfyUI Installer 的 download_models.ps1 脚本, 根据模型编号列表下载指定的模型
        模型编号可运行 download_models.ps1 脚本进行查看

    -NoPreDownloadNode
        安装 ComfyUI 时跳过安装 ComfyUI 扩展

    -NoPreDownloadModel
        安装 ComfyUI 时跳过预下载模型

    -PyTorchPackage <PyTorch 软件包>
        (需要同时搭配 -xFormersPackage 一起使用, 否则可能会出现 PyTorch 和 xFormers 不匹配的问题) 指定要安装 PyTorch 版本, 如 -PyTorchPackage `"torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118`"

    -xFormersPackage <xFormers 软件包>
        (需要同时搭配 -PyTorchPackage 一起使用, 否则可能会出现 PyTorch 和 xFormers 不匹配的问题) 指定要安装 xFormers 版本, 如 -xFormersPackage `"xformers===0.0.26.post1+cu118`"

    -InstallHanamizuki
        安装绘世启动器, 并生成 hanamizuki.bat 用于启动绘世启动器

    -NoCleanCache
        安装结束后保留下载 Python 软件包缓存

    -DisableUpdate
        (仅在 ComfyUI Installer 构建模式下生效, 并且只作用于 ComfyUI Installer 管理脚本) 禁用 ComfyUI Installer 更新检查

    -DisableHuggingFaceMirror
        (仅在 ComfyUI Installer 构建模式下生效, 并且只作用于 ComfyUI Installer 管理脚本) 禁用 HuggingFace 镜像源, 不使用 HuggingFace 镜像源下载文件

    -UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>
        (仅在 ComfyUI Installer 构建模式下生效, 并且只作用于 ComfyUI Installer 管理脚本) 使用自定义 HuggingFace 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror `"https://hf-mirror.com`" 设置 HuggingFace 镜像源地址

    -LaunchArg <ComfyUI 启动参数>
        (仅在 ComfyUI Installer 构建模式下生效, 并且只作用于 ComfyUI Installer 管理脚本) 设置 ComfyUI 自定义启动参数, 如启用 --fast 和 --auto-launch, 则使用 -LaunchArg `"--fast --auto-launch`" 进行启用

    -EnableShortcut
        (仅在 ComfyUI Installer 构建模式下生效, 并且只作用于 ComfyUI Installer 管理脚本) 创建 ComfyUI 启动快捷方式

    -DisableCUDAMalloc
        (仅在 ComfyUI Installer 构建模式下生效, 并且只作用于 ComfyUI Installer 管理脚本) 禁用 ComfyUI Installer 通过 PYTORCH_CUDA_ALLOC_CONF / PYTORCH_ALLOC_CONF 环境变量设置 CUDA 内存分配器

    -DisableEnvCheck
        (仅在 ComfyUI Installer 构建模式下生效, 且只作用于 ComfyUI Installer 管理脚本) 禁用 ComfyUI Installer 检查 ComfyUI 运行环境中存在的问题, 禁用后可能会导致 ComfyUI 环境中存在的问题无法被发现并修复


更多的帮助信息请阅读 ComfyUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/comfyui_installer.md
".Trim()

    if ($script:Help) {
        Write-Host $content
        exit 0
    }
}


# 主程序
function Main {
    Get-InstallerCmdletHelp
    Get-Version
    Get-CorePrefixStatus

    if ($script:UseUpdateMode) {
        Write-Log "使用更新模式"
        Use-UpdateMode
        Set-Content -Encoding UTF8 -Path "$script:InstallPath/update_time.txt" -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
    } else {
        if ($script:BuildMode) { Write-Log "ComfyUI Installer 构建模式已启用" }
        
        Write-Log "使用安装模式"
        Use-InstallMode
    }
}


###################


Main
