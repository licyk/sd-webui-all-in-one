param (
    [switch]$Help,
    [string]$CorePrefix,
    [string]$InstallPath = (Join-Path -Path "$PSScriptRoot" -ChildPath "qwen-tts-webui"),
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
    [switch]$DisableEnvCheck
)

function Join-NormalizedPath {
    $joined = $args[0]
    for ($i = 1; $i -lt $args.Count; $i++) { $joined = Join-Path $joined $args[$i] }
    return $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($joined).TrimEnd('\', '/')
}

$script:InstallPath = Join-NormalizedPath $script:InstallPath

& {
    $target_prefix = $null
    $prefix_list = @("core", "qwen-tts-webui*")
    if ($script:CorePrefix -or (Test-Path (Join-NormalizedPath $script:InstallPath "core_prefix.txt"))) {
        $origin_core_prefix = if ($script:CorePrefix) {
            $script:CorePrefix
        } else {
            (Get-Content (Join-NormalizedPath $script:InstallPath "core_prefix.txt") -Raw).Trim()
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
# Qwen TTS WebUI Installer 版本和检查更新间隔
$script:QWEN_TTS_WEBUI_INSTALLER_VERSION = 124
$script:UPDATE_TIME_SPAN = 3600
# SD WebUI All In One 内核最低版本
$script:CORE_MINIMUM_VER = "2.0.19"
# PATH
& {
    $sep = $([System.IO.Path]::PathSeparator)
    $python_path = Join-NormalizedPath $script:InstallPath "python"
    $python_extra_path = Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX "python"
    $python_script_path = Join-NormalizedPath $script:InstallPath "python" "Scripts"
    $python_script_extra_path = Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX "python" "Scripts"
    $python_bin_path = Join-NormalizedPath $script:InstallPath "python" "bin"
    $python_bin_extra_path = Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX "python" "bin"
    $git_path = Join-NormalizedPath $script:InstallPath "git" "bin"
    $git_extra_path = Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX "git" "bin"
    $env:PATH = "${python_bin_extra_path}${sep}${python_extra_path}${sep}${python_script_extra_path}${sep}${git_extra_path}${sep}${python_bin_path}${sep}${python_path}${sep}${python_script_path}${sep}${git_path}${sep}${env:PATH}"
}
# 环境变量
$env:QWEN_TTS_WEBUI_PATH = Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX
$env:QWEN_TTS_WEBUI_ROOT = Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX
$env:CACHE_HOME = Join-NormalizedPath $script:InstallPath "cache"
$env:PIP_CONFIG_FILE = Join-NormalizedPath $script:InstallPath "cache" "pip.ini"
$env:UV_CONFIG_FILE = Join-NormalizedPath $script:InstallPath "cache" "uv.toml"
$env:PIP_CACHE_DIR = Join-NormalizedPath $script:InstallPath "cache" "pip"
$env:UV_CACHE_DIR = Join-NormalizedPath $script:InstallPath "cache" "uv"
$env:PYTHONUTF8 = 1
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = 1
$env:PYTHONNOUSERSITE = 1
$env:PYTHONFAULTHANDLER = 1
$env:PIP_DISABLE_PIP_VERSION_CHECK = 1
$env:PIP_NO_WARN_SCRIPT_LOCATION = 0
$env:SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH = $script:InstallPath
$env:SD_WEBUI_ALL_IN_ONE_LOGGER_NAME = "Qwen TTS WebUI Installer"
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
        [string]$Name = "Qwen TTS WebUI Installer"
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
    if ((Test-Path (Join-NormalizedPath $PSScriptRoot "core_prefix.txt")) -or ($script:CorePrefix)) {
        Write-Log "检测到 core_prefix.txt 配置文件 / -CorePrefix 命令行参数, 使用自定义内核路径前缀"
        if ($script:CorePrefix) {
            $origin_core_prefix = $script:CorePrefix
        } else {
            $origin_core_prefix = (Get-Content (Join-NormalizedPath $PSScriptRoot "core_prefix.txt") -Raw).Trim()
        }
        if ([System.IO.Path]::IsPathRooted($origin_core_prefix.Trim('/').Trim('\'))) {
            Write-Log "转换绝对路径为内核路径前缀: $origin_core_prefix -> $env:CORE_PREFIX"
        }
    }
    Write-Log "当前内核路径前缀: $env:CORE_PREFIX"
    Write-Log "完整内核路径: $(Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX)"
}


# 显示 Qwen TTS WebUI Installer 版本
function Get-Version {
    $ver = $([string]$script:QWEN_TTS_WEBUI_INSTALLER_VERSION).ToCharArray()
    $major = ($ver[0..($ver.Length - 3)])
    $minor = $ver[-2]
    $micro = $ver[-1]
    Write-Log "Qwen TTS WebUI Installer 版本: v${major}.${minor}.${micro}"
}


# PyPI 镜像源状态
function Set-PyPIMirror {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]$ArrayList)
    if ((!(Test-Path (Join-NormalizedPath $PSScriptRoot "disable_pypi_mirror.txt"))) -and (!($script:DisablePyPIMirror))) {
        Write-Log "使用 PyPI 镜像源"
    } else {
        Write-Log "检测到 disable_pypi_mirror.txt 配置文件 / -DisablePyPIMirror 命令行参数, 已将 PyPI 源切换至官方源"
        $ArrayList.Add("--no-pypi-mirror") | Out-Null
    }
}


# 代理配置
function Set-Proxy {
    $env:NO_PROXY = "localhost,127.0.0.1,::1"
    if ((Test-Path (Join-NormalizedPath $PSScriptRoot "disable_proxy.txt")) -or ($script:DisableProxy)) {
        $env:SD_WEBUI_ALL_IN_ONE_PROXY = 0
        Write-Log "检测到本地存在 disable_proxy.txt 代理配置文件 / -DisableProxy 命令行参数, 禁用自动设置代理"
        return
    }
    if ((Test-Path (Join-NormalizedPath $PSScriptRoot "proxy.txt")) -or ($script:UseCustomProxy)) {
        if ($script:UseCustomProxy) {
            $proxy_value = $script:UseCustomProxy
        } else {
            $proxy_value = (Get-Content (Join-NormalizedPath $PSScriptRoot "proxy.txt") -Raw).Trim()
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
    if (($script:DisableUV) -or (Test-Path (Join-NormalizedPath $PSScriptRoot "disable_uv.txt"))) {
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
    if (Test-Path (Join-NormalizedPath $script:InstallPath ".gitconfig")) {
        Remove-Item -Path (Join-NormalizedPath $script:InstallPath ".gitconfig") -Force -Recurse
    }
    if (($script:DisableGithubMirror) -or (Test-Path (Join-NormalizedPath $PSScriptRoot "disable_gh_mirror.txt"))) {
        Write-Log "检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件 / -DisableGithubMirror 命令行参数, 禁用 Github 镜像源"
        $ArrayList.Add("--no-github-mirror") | Out-Null
        return
    }
    if (($script:UseCustomGithubMirror) -or (Test-Path (Join-NormalizedPath $PSScriptRoot "gh_mirror.txt"))) {
        if ($script:UseCustomGithubMirror) {
            $github_mirror = $script:UseCustomGithubMirror
        } else {
            $github_mirror = (Get-Content (Join-NormalizedPath $PSScriptRoot "gh_mirror.txt") -Raw).Trim()
        }
        Write-Log "检测到本地存在 gh_mirror.txt Github 镜像源配置文件 / -UseCustomGithubMirror 命令行参数, 已读取 Github 镜像源配置文件并设置 Github 镜像源"
        $ArrayList.Add("--custom-github-mirror") | Out-Null
        $ArrayList.Add($github_mirror) | Out-Null
        return
    }
}

# 获取启动 SD WebUI All In One 内核的启动参数
function Get-LaunchCoreArgs {
    $launch_params = New-Object System.Collections.ArrayList
    Set-uv $launch_params
    Set-PyPIMirror $launch_params
    Set-Proxy
    Set-GithubMirror $launch_params
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

# 检查 SD WebUI ALL In One 内核版本
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
    if ((!($script:DisablePyPIMirror)) -and (!(Test-Path (Join-NormalizedPath $PSScriptRoot "disable_pypi_mirror.txt")))) {
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


# 下载并解压文件
function Install-ArchiveResource {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)] [string[]]$Urls,        # 下载地址列表
        [Parameter(Mandatory=$true)] [string]$ResourceName,  # 资源名称
        [Parameter(Mandatory=$true)] [string]$DestPath,      # 最终安装路径
        [Parameter(Mandatory=$true)] [string]$ZipName        # 压缩包文件名
    )

    $cache_zip = Join-NormalizedPath $env:CACHE_HOME $ZipName
    $cache_tmp_folder = Join-NormalizedPath $env:CACHE_HOME "$($ResourceName)_tmp"
    $success = $false

    for ($i = 0; $i -lt $Urls.Length; $i++) {
        Write-Log "正在下载 $ResourceName"
        try {
            $web_request_params = @{
                Uri = $Urls[$i]
                UseBasicParsing = $true
                OutFile = $cache_zip
                TimeoutSec = 15
                ErrorAction = "Stop"
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
    if ($PSVersionTable.PSVersion.Major -ge 6) {
        $arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLower()
    } else {
        $arch = $env:PROCESSOR_ARCHITECTURE.ToLower()
    }
    switch ($arch) {
        "amd64" { "amd64" }
        "x64"   { "amd64" }
        "arm64" { "aarch64" }
        default { $arch }
    }
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
        $py_ver = "3.11"
    }
    $platform = Get-CurrentPlatform
    $arch = Get-CurrentArchitecture
    $py_info = Get-PythonDownloadUrl -Version $py_ver -Platform $platform -Arch $arch
    if ($py_info) {
        $zip_name = $py_info.Name
        $urls = $py_info.Url
    } else {
        Write-Log "不支持当前的平台安装: ($platform, $arch)" -Level ERROR
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
    Install-ArchiveResource -Urls $urls -ResourceName "Python" -DestPath (Join-NormalizedPath $script:InstallPath "python") -ZipName $zip_name
}

function Invoke-SmartCommand {
    [CmdletBinding()]
    param (
        [string]$Command,
        [string[]]$Arguments
    )
    
    if (((Get-CurrentPlatform) -eq "linux") -and (Get-Command sudo -ErrorAction SilentlyContinue)) {
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
                "https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/git/windows/amd64/portable_git-2.53.0-x86_64.zip",
                "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/git/windows/amd64/portable_git-2.53.0-x86_64.zip"
            )
        }
        elseif ($arch -eq "arm64") {
            $urls = @(
                "https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/git/windows/aarch64/portable_git-2.53.0-aarch64.zip",
                "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/git/windows/aarch64/portable_git-2.53.0-aarch64.zip"
            )
        }
        else {
            Write-Log "不支持当前的平台安装: ($platform, $arch)" -Level ERROR
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
            if (Get-Command apt -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "apt" -Arguments @("update"); Invoke-SmartCommand -Command "apt" -Arguments $("install", "git", "-y"); return }
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
            if (Get-Command brew -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "brew" -Arguments $("install", "git"); return }
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
        "https://www.modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/aria2/windows/amd64/aria2c.exe",
        "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/aria2/windows/amd64/aria2c.exe"
    )
    $i = 0

    ForEach ($url in $urls) {
        Write-Log "正在下载 Aria2"
        try {
            $web_request_params = @{
                Uri = $url
                UseBasicParsing = $true
                OutFile = (Join-NormalizedPath $env:CACHE_HOME "aria2c.exe")
                TimeoutSec = 15
                ErrorAction = "Stop"
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

    Move-Item -Path (Join-NormalizedPath $env:CACHE_HOME "aria2c.exe") -Destination (Join-NormalizedPath $script:InstallPath "git" "bin" "aria2c.exe") -Force
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
            if (Get-Command apt -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "apt" -Arguments @("update"); Invoke-SmartCommand -Command "apt" -Arguments $("install", "aria2", "-y"); return }
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
            if (Get-Command brew -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "brew" -Arguments $("install", "aria2"); return }
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
    Write-FileWithStreamWriter -Path (Join-NormalizedPath $env:CACHE_HOME "uv.toml") -Value " " -Encoding UTF8
    Write-FileWithStreamWriter -Path (Join-NormalizedPath $env:CACHE_HOME "pip.ini") -Value " " -Encoding UTF8

    Write-Log "检测是否安装 Python"
    Install-Python

    Write-Log "检测是否安装 Git"
    Install-Git

    Write-Log "检测是否安装 Aria2"
    Install-Aria2

    Update-SDWebUiAllInOne
    $launch_params = Get-LaunchCoreArgs

    & python -m sd_webui_all_in_one.cli_manager.main qwen-tts-webui install $launch_params
    if (!($?)) {
        Write-Log "运行 SD WebUI All In One 安装 Qwen TTS WebUI 时发生了错误, 终止 Qwen TTS WebUI 安装进程, 可尝试重新运行 Qwen TTS WebUI Installer 重试失败的安装" -Level ERROR
        if (!($script:BuildMode)) { Read-Host | Out-Null }
        exit 1
    }
    if (!(Test-Path (Join-NormalizedPath $script:InstallPath "launch_args.txt"))) {
        Write-Log "设置默认 Qwen TTS WebUI 启动参数"
        $content = " "
        Write-FileWithStreamWriter -Encoding UTF8 (Join-NormalizedPath $script:InstallPath "launch_args.txt") -Value $content
    }

    if (!($script:NoCleanCache)) {
        Write-Log "清理下载 Python 软件包的缓存中"
        & python -m pip cache purge
        & uv cache clean
    }

    Set-Content -Encoding UTF8 -Path (Join-NormalizedPath $script:InstallPath "update_time.txt") -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
}


# 通用模块脚本
function Write-ModulesScript {
    $content = "
param (
    [string]`$OriginalScriptPath,
    [string]`$LaunchCommandLine,
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
# Qwen TTS WebUI Installer 版本和检查更新间隔
`$script:QWEN_TTS_WEBUI_INSTALLER_VERSION = $script:QWEN_TTS_WEBUI_INSTALLER_VERSION
`$script:UPDATE_TIME_SPAN = $script:UPDATE_TIME_SPAN
# SD WebUI All In One 内核最低版本
`$script:CORE_MINIMUM_VER = `"$script:CORE_MINIMUM_VER`"


# 初始化环境变量
function Initialize-EnvPath {
    Write-Log `"初始化环境变量`"
    `$python_path = Join-NormalizedPath `$PSScriptRoot `"python`"
    `$python_extra_path = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX `"python`"
    `$python_scripts_path = Join-NormalizedPath `$PSScriptRoot `"python`" `"Scripts`"
    `$python_scripts_extra_path = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX `"python`" `"Scripts`"
    `$python_bin_path = Join-NormalizedPath `$PSScriptRoot `"python`" `"bin`"
    `$python_bin_extra_path = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX `"python`" `"bin`"
    `$git_path = Join-NormalizedPath `$PSScriptRoot `"git`" `"bin`"
    `$git_extra_path = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX `"git`" `"bin`"
    `$sep = `$([System.IO.Path]::PathSeparator)
    `$env:PATH = `"`${python_bin_extra_path}`${sep}`${python_extra_path}`${sep}`${python_scripts_extra_path}`${sep}`${git_extra_path}`${sep}`${python_bin_path}`${sep}`${python_path}`${sep}`${python_scripts_path}`${sep}`${git_path}`${sep}`${env:PATH}`"

    `$env:UV_CONFIG_FILE = Join-NormalizedPath `$PSScriptRoot `"cache`" `"uv.toml`"
    `$env:PIP_CONFIG_FILE = Join-NormalizedPath `$PSScriptRoot `"cache`" `"pip.ini`"
    `$env:PIP_DISABLE_PIP_VERSION_CHECK = 1
    `$env:PIP_NO_WARN_SCRIPT_LOCATION = 0
    `$env:UV_LINK_MODE = `"copy`"
    `$env:PYTHONUTF8 = 1
    `$env:PYTHONIOENCODING = `"utf-8`"
    `$env:PYTHONUNBUFFERED = 1
    `$env:PYTHONNOUSERSITE = 1
    `$env:PYTHONFAULTHANDLER = 1
    `$env:CACHE_HOME = Join-NormalizedPath `$PSScriptRoot `"cache`"
    `$env:QWEN_TTS_WEBUI_PATH = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX
    `$env:QWEN_TTS_WEBUI_ROOT = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX
    `$env:SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH = `$PSScriptRoot
    `$env:SD_WEBUI_ALL_IN_ONE_LOGGER_NAME = `"Qwen TTS WebUI Installer`"
    `$env:SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL = 20
    `$env:SD_WEBUI_ALL_IN_ONE_LOGGER_COLOR = 1
    `$env:SD_WEBUI_ALL_IN_ONE_RETRY_TIMES = 3
    `$env:SD_WEBUI_ALL_IN_ONE_PATCHER = 0
    `$env:SD_WEBUI_ALL_IN_ONE_EXTRA_PYPI_MIRROR = 0
    `$env:SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH = 1
    `$env:SD_WEBUI_ALL_IN_ONE_SET_CONFIG = 1

    New-Item -ItemType Directory -Path `$env:CACHE_HOME -Force > `$null
    Write-FileWithStreamWriter -Path (Join-NormalizedPath `$env:CACHE_HOME `"uv.toml`") -Value `" `" -Encoding UTF8
    Write-FileWithStreamWriter -Path (Join-NormalizedPath `$env:CACHE_HOME `"pip.ini`") -Value `" `" -Encoding UTF8
}


# 日志输出
function Write-Log {
    [CmdletBinding()]
    param(
        [string]`$Message,
        [ValidateSet(`"DEBUG`", `"INFO`", `"WARNING`", `"ERROR`", `"CRITICAL`")]
        [string]`$Level = `"INFO`",
        [string]`$Name = `"Qwen TTS WebUI Installer`"
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


# Qwen TTS WebUI Installer 更新检测
function Update-Installer {
    [CmdletBinding()]
    param([switch]`$DisableRestart)
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/qwen_tts_webui_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `$env:CACHE_HOME -Force | Out-Null

    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_update.txt`")) -or (`$script:DisableUpdate)) {
        Write-Log `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 Qwen TTS WebUI Installer 的自动检查更新功能`"
        return
    }

    if (`$script:BuildMode) {
        Write-Log `"Qwen TTS WebUI Installer 构建模式已启用, 跳过 Qwen TTS WebUI Installer 更新检查`"
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
        Write-Log `"检查 Qwen TTS WebUI Installer 更新中`"
        try {
            `$web_request_params = @{
                Uri = `$url
                UseBasicParsing = `$true
                OutFile = (Join-NormalizedPath `$env:CACHE_HOME `"qwen_tts_webui_installer.ps1`")
                TimeoutSec = 15
                ErrorAction = `"Stop`"
            }
            Invoke-WebRequest @web_request_params
            `$latest_version = [int]`$(
                Get-Content (Join-NormalizedPath `$env:CACHE_HOME `"qwen_tts_webui_installer.ps1`") -Encoding UTF8 |
                Select-String -Pattern `"QWEN_TTS_WEBUI_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Write-Log `"重试检查 Qwen TTS WebUI Installer 更新中`" -Level WARNING
            } else {
                Write-Log `"检查 Qwen TTS WebUI Installer 更新失败`"
                return
            }
        }
    }

    if (`$latest_version -le `$script:QWEN_TTS_WEBUI_INSTALLER_VERSION) {
        Write-Log `"Qwen TTS WebUI Installer 已是最新版本`"
        return
    }

    Write-Log `"调用 Qwen TTS WebUI Installer 进行更新中`"
    & (Join-NormalizedPath `$env:CACHE_HOME `"qwen_tts_webui_installer.ps1`") -InstallPath `$PSScriptRoot -UseUpdateMode

    if (`$DisableRestart) {
        Write-Log `"更新结束, 已禁用自动重新启动`"
        return
    }

    `$raw_params = `$script:LaunchCommandLine -replace `"^.*\.ps1[\s]*`", `"`"
    Write-Log `"更新结束, 重新启动 Qwen TTS WebUI Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
    Invoke-Expression `"& ```"`$script:OriginalScriptPath```" `$raw_params`"
    exit 0
}


# 更新 Aria2 (Windows) 版本
function Update-WindowsAria2 {
    `$urls = @(
        `"https://www.modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/aria2/windows/amd64/aria2c.exe`",
        `"https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/aria2/windows/amd64/aria2c.exe`"
    )
    `$aria2_tmp_path = Join-NormalizedPath `$env:CACHE_HOME `"aria2c.exe`"
    New-Item -ItemType Directory -Path `$env:CACHE_HOME -Force > `$null

    ForEach (`$url in `$urls) {
        Write-Log `"下载 Aria2 中`"
        try {
            `$web_request_params = @{
                Uri = `$url
                UseBasicParsing = `$true
                OutFile = `$aria2_tmp_path
                TimeoutSec = 15
                ErrorAction = `"Stop`"
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

    `$git_cmd = Get-Command git -ErrorAction SilentlyContinue
    if (`$git_cmd) {
        `$git_path_prefix = Join-NormalizedPath `$script:InstallPath `"git`"
        `$git_extra_path_prefix = Join-NormalizedPath `$script:InstallPath `$env:CORE_PREFIX `"git`"
        `$git_cmd = Get-NormalizedFilePath `$git_cmd.Path
        if ((`$git_cmd) -and ((`$git_cmd.ToString().StartsWith(`$git_path_prefix, [System.StringComparison]::OrdinalIgnoreCase)) -or (`$git_cmd.ToString().StartsWith(`$git_extra_path_prefix, [System.StringComparison]::OrdinalIgnoreCase)))) {
            `$aria2_bin_path = Join-NormalizedPath (Split-Path -Path `$git_cmd -Parent) `"aria2c.exe`"
        }
        else {
            `$aria2_bin_path = Join-NormalizedPath `$PSScriptRoot `"git`" `"bin`" `"aria2c.exe`"
        }
    }
    else {
        `$aria2_bin_path = Join-NormalizedPath `$PSScriptRoot `"git`" `"bin`" `"aria2c.exe`"
    }

    New-Item -ItemType Directory -Path (Split-Path -Path `$aria2_bin_path -Parent) -Force | Out-Null
    Move-Item -Path `$aria2_tmp_path -Destination `$aria2_bin_path -Force
}


# 更新 Aria2
function Update-Aria2 {
    Write-Log `"检查 Aria2 是否需要更新`"
    & python -m sd_webui_all_in_one.cli_manager.main self-manager check-aria2
    if (`$?) {
        Write-Log `"Aria2 无需更新`"
        return
    }
    Write-Log `"更新 Aria2 中`"
    `$platform = Get-CurrentPlatform
    if (`$platform -eq `"windows`") {
        Update-WindowsAria2
    }
    elseif (`$platform -eq `"linux`") {
        try {
            if (Get-Command apt -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command `"apt`" -Arguments @(`"update`"); Invoke-SmartCommand -Command `"apt`" -Arguments @(`"install`", `"--only-upgrade`", `"aria2`", `"-y`"); return }
            if (Get-Command yum -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command `"yum`" -Arguments @(`"upgrade`", `"aria2`", `"-y`"); return }
            if (Get-Command apk -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command `"apk`" -Arguments @(`"add`", `"--upgrade`", `"aria2`"); return }
            if (Get-Command pacman -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command `"pacman`" -Arguments @(`"-S`", `"aria2`", `"--noconfirm`"); return }
            if (Get-Command zypper -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command `"zypper`" -Arguments @(`"update`", `"-y`", `"aria2`"); return }
            if (Get-Command nix-env -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command `"nix-channel`" -Arguments @(`"--update`"); Invoke-SmartCommand -Command `"nix-env`" -Arguments @(`"-u`", `"aria2`"); return }
        }
        catch {
            Write-Log `"更新 Aria2 失败, 可能会导致模型下载出现问题`" -Level ERROR
        }
    }
    elseif (`$platform -eq `"macos`") {
        try {
            if (Get-Command brew -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command `"brew`" -Arguments @(`"upgrade`", `"aria2`"); return }
            if (Get-Command port -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command `"port`" -Arguments @(`"upgrade`", `"aria2`"); return }
        }
        catch {
            Write-Log `"更新 Aria2 失败, 可能会导致模型下载出现问题`" -Level ERROR
        }
    }
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
    if (`$PSVersionTable.PSVersion.Major -ge 6) {
        `$arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLower()
    } else {
        `$arch = `$env:PROCESSOR_ARCHITECTURE.ToLower()
    }
    switch (`$arch) {
        `"amd64`" { `"amd64`" }
        `"x64`"   { `"amd64`" }
        `"arm64`" { `"aarch64`" }
        default { `$arch }
    }
}

# 获取规范化路径
function Get-NormalizedFilePath {
    [CmdletBinding()]
    param ([Parameter(Mandatory = `$false)][string]`$Filepath)
    if (-not [string]::IsNullOrWhiteSpace(`$Filepath)) { return Join-NormalizedPath `$Filepath }
    return `$null
}


# 显示 Qwen TTS WebUI Installer 版本
function Get-Version {
    `$ver = `$([string]`$script:QWEN_TTS_WEBUI_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Write-Log `"Qwen TTS WebUI Installer 版本: v`${major}.`${minor}.`${micro}`"
}


# 设置内核路径前缀
function Set-CorePrefix {
    `$target_prefix = `$null
    `$prefix_list = @(`"core`", `"qwen-tts-webui*`")
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


# 创建 Windows 快捷方式
function Add-WindowsShortcut {
    [CmdletBinding()]
    param (
        [string]`$Name,
        [string]`$IconPath
    )
    `$shell = New-Object -ComObject WScript.Shell
    `$desktop = `$([System.Environment]::GetFolderPath(`"Desktop`"))
    `$shortcut_path = Join-NormalizedPath `$desktop `"`${Name}.lnk`"
    `$shortcut = `$shell.CreateShortcut(`$shortcut_path)
    `$shortcut.TargetPath = (Get-Process -Id `$PID).Path
    `$launch_script_path = Join-NormalizedPath `$PSScriptRoot `"launch.ps1`"
    `$shortcut.Arguments = `"-ExecutionPolicy Bypass -File ```"`$launch_script_path```"`"
    `$shortcut.IconLocation = `$IconPath
    `$shortcut.Save()
    Copy-Item -Path `$shortcut_path -Destination (Join-NormalizedPath `$([System.Environment]::GetFolderPath(`"ApplicationData`")) `"Microsoft`" `"Windows`" `"Start Menu`" `"Programs`") -Force
}


# 创建 Linux 快捷方式
function Add-LinuxShortcut {
    [CmdletBinding()]
    param (
        [string]`$Name,
        [string]`$IconPath
    )
    `$pwsh_bin = (Get-Process -Id `$PID).Path
    `$launch_script_path = Join-NormalizedPath `$PSScriptRoot `"launch.ps1`"
    `$desktop = `$([System.Environment]::GetFolderPath(`"Desktop`"))
    `$shortcut_path = Join-NormalizedPath `$desktop `"`${Name}.desktop`"
    `$content = `"
[Desktop Entry]
Encoding=UTF-8
Version=1.0
Name=`$Name
Comment=Installer 启动脚本
Icon=`$IconPath
Exec=```"`$pwsh_bin```" -ExecutionPolicy Bypass -File ```"`$launch_script_path```" %f
Terminal=true
startupNotify=true
Type=Application
`".Trim()
    Write-FileWithStreamWriter -Path `$shortcut_path -Encoding UTF8 -Value `$content
    `$local_app_path = Join-NormalizedPath `$([System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::UserProfile)) `".local`" `"share`" `"applications`"
    `$local_app_shortcut_path = Join-NormalizedPath `$local_app_path `"`${Name}.desktop`"
    New-Item -ItemType Directory -Path `$local_app_path -Force | Out-Null
    Copy-Item -Path `$shortcut_path -Destination `$local_app_shortcut_path -Force
    & chmod +x `"`$shortcut_path`"
    & chmod +x `"`$local_app_shortcut_path`"
}


# 创建 MacOS 快捷方式
function Add-MacOSShortcut {
    [CmdletBinding()]
    param (
        [string]`$Name,
        [string]`$IconPath
    )

    `$pwsh_bin = (Get-Process -Id `$PID).Path
    `$launch_script_path = Join-NormalizedPath `$PSScriptRoot `"launch.ps1`"
    `$desktop = `$([System.Environment]::GetFolderPath(`"Desktop`"))

    `$app_path = Join-NormalizedPath `$desktop `"`${Name}.app`"
    `$contents_path = Join-NormalizedPath `$app_path `"Contents`"
    `$macos_path = Join-NormalizedPath `$contents_path `"MacOS`"
    `$resources_path = Join-NormalizedPath `$contents_path `"Resources`"

    New-Item -ItemType Directory -Path `$macos_path -Force | Out-Null
    New-Item -ItemType Directory -Path `$resources_path -Force | Out-Null

    `$executable_path = Join-NormalizedPath `$macos_path `"launcher`"
    `$sh_content = @`"
#!/bin/bash
`"`$pwsh_bin`" -ExecutionPolicy Bypass -File `"`$launch_script_path`"
`"@
    Write-FileWithStreamWriter -Path `$executable_path -Encoding UTF8 -Value `$sh_content
    & chmod +x `$executable_path

    `$plist_path = Join-NormalizedPath `$contents_path `"Info.plist`"
    `$plist_content = @`"
<?xml version=`"1.0`" encoding=`"UTF-8`"?>
<!DOCTYPE plist PUBLIC `"-//Apple//DTD PLIST 1.0//EN`" `"http://www.apple.com/DTDs/PropertyList-1.0.dtd`">
<plist version=`"1.0`">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon.icns</string>
    <key>CFBundleName</key>
    <string>`${Name}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSBackgroundOnly</key>
    <false/>
</dict>
</plist>
`"@
    Write-FileWithStreamWriter -Path `$plist_path -Encoding UTF8 -Value `$plist_content

    if (Test-Path `$IconPath) {
        Copy-Item -Path `$IconPath -Destination (Join-NormalizedPath `$resources_path `"AppIcon.icns`") -Force
    }

    `$applications_folder = `"/Applications`"
    if (Test-Path `$applications_folder) {
        Copy-Item -Path `$app_path -Destination `$applications_folder -Recurse -Force
    }
}


# 下载应用图标
function Get-AppIcon {
    [CmdletBinding()]
    param ([Parameter(Mandatory=`$true)][Hashtable]`$IconMap)
    `$platform = Get-CurrentPlatform
    if (-not `$IconMap.ContainsKey(`$platform)) {
        Write-Log `"未找到平台 [`$platform] 的图标配置`" -Level WARNING
        return `$null
    }
    `$config = `$IconMap[`$platform]
    `$fileName = `$config.FileName
    `$localIconPath = Join-NormalizedPath `$PSScriptRoot `$fileName
    if (Test-Path `$localIconPath) { return `$localIconPath }
    foreach (`$url in `$config.Urls) {
        try {
            Write-Log `"正在下载 `$platform 图标: `$url`"
            `$web_request_params = @{
                Uri = `$url
                UseBasicParsing = `$true
                OutFile = `$localIconPath
                TimeoutSec = 15
                ErrorAction = `"Stop`"
            }
            Invoke-WebRequest @web_request_params
            if (Test-Path `$localIconPath) { return `$localIconPath }
        }
        catch {
            Write-Log `"链接失效: `$url`" -Level WARNING
        }
    }
    return `$null
}


# 创建快捷方式
function New-AppShortcut {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=`$true)][string]`$Name,
        [Parameter(Mandatory=`$true)][Hashtable]`$IconMap
    )
    `$finalIconPath = Get-AppIcon -IconMap `$IconMap
    if (-not `$finalIconPath) {
        Write-Log `"图标获取失败，跳过创建快捷方式`" -Level ERROR
        return
    }
    `$platform = Get-CurrentPlatform
    switch (`$platform) {
        `"windows`" { Add-WindowsShortcut -Name `$Name -IconPath `$finalIconPath }
        `"linux`"   { Add-LinuxShortcut -Name `$Name -IconPath `$finalIconPath }
        `"macos`"   { Add-MacOSShortcut -Name `$Name -IconPath `$finalIconPath }
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
    Get-CurrentArchitecture, ``
    New-AppShortcut
".Trim()
    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "modules.psm1")) { "更新" } else { "生成" }) modules.psm1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "modules.psm1") -Value $content
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
    [string]`$UseCustomHuggingFaceMirror,
    [switch]`$DisableGithubMirror,
    [string]`$UseCustomGithubMirror,
    [switch]`$DisableUV,
    [string]`$LaunchArg,
    [switch]`$EnableShortcut,
    [switch]`$DisableCUDAMalloc,
    [switch]`$DisableEnvCheck
)
try {
    `$config = @{
        OriginalScriptPath = `$script:PSCommandPath
        LaunchCommandLine = `$script:MyInvocation.Line
        CorePrefix = `$script:CorePrefix
        DisableUV = `$script:DisableUV
        DisableProxy = `$script:DisableProxy
        UseCustomProxy = `$script:UseCustomProxy
        DisablePyPIMirror = `$script:DisablePyPIMirror
        DisableHuggingFaceMirror = `$script:DisableHuggingFaceMirror
        UseCustomHuggingFaceMirror = `$script:UseCustomHuggingFaceMirror
        DisableGithubMirror = `$script:DisableGithubMirror
        UseCustomGithubMirror = `$script:UseCustomGithubMirror
        DisableCUDAMalloc = `$script:DisableCUDAMalloc
        DisableUpdate = `$script:DisableUpdate
        BuildMode = `$script:BuildMode
    }
    (Import-Module `"`$PSScriptRoot/modules.psm1`" -Function `"Join-NormalizedPath`", `"Initialize-EnvPath`", `"Write-Log`", `"Set-CorePrefix`", `"Get-Version`", `"Update-Installer`", `"Set-Proxy`", `"Set-PyPIMirror`", `"Set-HuggingFaceMirror`", `"Set-GithubMirror`", `"Set-uv`", `"Set-PyTorchCUDAMemoryAlloc`", `"Update-SDWebUiAllInOne`", `"Get-CurrentPlatform`", `"New-AppShortcut`" -PassThru -Force -ErrorAction Stop).Invoke({
        param (`$cfg)
        `$script:OriginalScriptPath = `$cfg.OriginalScriptPath
        `$script:LaunchCommandLine = `$cfg.LaunchCommandLine
        `$script:CorePrefix = `$cfg.CorePrefix
        `$script:DisableUV = `$cfg.DisableUV
        `$script:DisableProxy = `$cfg.DisableProxy
        `$script:UseCustomProxy = `$cfg.UseCustomProxy
        `$script:DisablePyPIMirror = `$cfg.DisablePyPIMirror
        `$script:DisableHuggingFaceMirror = `$cfg.DisableHuggingFaceMirror
        `$script:UseCustomHuggingFaceMirror = `$cfg.UseCustomHuggingFaceMirror
        `$script:DisableGithubMirror = `$cfg.DisableGithubMirror
        `$script:UseCustomGithubMirror = `$cfg.UseCustomGithubMirror
        `$script:DisableCUDAMalloc = `$cfg.DisableCUDAMalloc
        `$script:DisableUpdate = `$cfg.DisableUpdate
        `$script:BuildMode = `$cfg.BuildMode
    }, `$config)
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White -NoNewline
    Write-Host `"launch_qwen_tts_webui_installer.ps1`" -ForegroundColor Yellow -NoNewline
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if (!(`$script:BuildMode)) { Read-Host | Out-Null }
    exit 1
}


# 帮助信息
function Get-InstallerCmdletHelp {
    `$content = `"
使用:
    ./`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-DisablePyPIMirror] [-DisableUpdate] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像源地址>] [-DisableUV] [-LaunchArg <Qwen TTS WebUI 启动参数>] [-EnableShortcut] [-DisableCUDAMalloc] [-DisableEnvCheck]

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

    -DisableGithubMirror
        禁用 Qwen TTS WebUI Installer 自动设置 Github 镜像源

    -UseCustomGithubMirror <Github 镜像站地址>
        使用自定义的 Github 镜像站地址

    -DisableUV
        禁用 Qwen TTS WebUI Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包

    -LaunchArg <Qwen TTS WebUI 启动参数>
        设置 Qwen TTS WebUI 自定义启动参数, 如启用 --fast 和 --auto-launch, 则使用 -LaunchArg ```"--fast --auto-launch```" 进行启用

    -EnableShortcut
        创建 Qwen TTS WebUI 启动快捷方式

    -DisableCUDAMalloc
        禁用 Qwen TTS WebUI Installer 通过 PYTORCH_CUDA_ALLOC_CONF / PYTORCH_ALLOC_CONF 环境变量设置 CUDA 内存分配器

    -DisableEnvCheck
        禁用 Qwen TTS WebUI Installer 检查 Qwen TTS WebUI 运行环境中存在的问题, 禁用后可能会导致 Qwen TTS WebUI 环境中存在的问题无法被发现并修复


更多的帮助信息请阅读 Qwen TTS WebUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md
`".Trim()

    if (`$script:Help) {
        Write-Host `$content
        exit 0
    }
}



# 获取启动参数
function Get-WebUILaunchArgs {
    param ([System.Collections.ArrayList]`$ArrayList)
    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"launch_args.txt`")) -or (`$script:LaunchArg)) {
        if (`$script:LaunchArg) {
            `$launch_args = `$script:LaunchArg.Trim()
        } else {
            `$launch_args = (Get-Content (Join-NormalizedPath `$PSScriptRoot `"launch_args.txt`") -Raw).Trim()
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
    `$filename = `"Qwen-TTS-WebUI`"
    `$IconConfig = @{
        `"windows`" = @{
            FileName = `"gradio_icon.ico`"
            Urls     = @(`"https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/icon/gradio_icon.ico`", `"https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/icon/gradio_icon.ico`")
        }
        `"linux`"   = @{
            FileName = `"gradio_icon.png`"
            Urls     = @(`"https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/icon/gradio_icon.png`", `"https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/icon/gradio_icon.png`")
        }
        `"macos`"   = @{
            FileName = `"gradio_icon.icns`"
            Urls     = @(`"https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/icon/gradio_icon.icns`", `"https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/icon/gradio_icon.icns`")
        }
    }
    if ((!(Test-Path (Join-NormalizedPath `$PSScriptRoot `"enable_shortcut.txt`"))) -and (!(`$script:EnableShortcut))) {
        return
    }
    Write-Log `"检测到 enable_shortcut.txt 配置文件 / -EnableShortcut 命令行参数, 开始检查 Qwen TTS WebUI 快捷启动方式中`"
    New-AppShortcut -IconMap `$IconConfig -Name `$filename
}


# 检测 Microsoft Visual C++ Redistributable
function Test-MSVCPPRedistributable {
    if ((Get-CurrentPlatform) -ne `"windows`") {
        Write-Log `"非 Windows 系统，跳过 Microsoft Visual C++ Redistributable 检测`"
        return
    }

    Write-Log `"检测 Microsoft Visual C++ Redistributable 是否缺失`"

    if ([string]::IsNullOrEmpty(`$env:SYSTEMROOT)) {
        `$vc_runtime_dll_path = Join-NormalizedPath `"C:`" `"Windows`" `"System32`" `"vcruntime140_1.dll`"
    } else {
        `$vc_runtime_dll_path = Join-NormalizedPath `$env:SYSTEMROOT `"System32`" `"vcruntime140_1.dll`"
    }

    if (Test-Path `$vc_runtime_dll_path) {
        Write-Log `"Microsoft Visual C++ Redistributable 未缺失`"
        return
    }

    Write-Log `"检测到 Microsoft Visual C++ Redistributable 缺失, 这可能导致 PyTorch 无法正常识别 GPU 导致报错`" -Level WARNING
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
    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_check_env.txt`")) -or (`$script:DisableEnvCheck)) {
        Write-Log `"检测到 disable_check_env.txt 配置文件 / -DisableEnvCheck 命令行参数, 已禁用 Qwen TTS WebUI 运行环境检测, 这可能会导致 Qwen TTS WebUI 运行环境中存在的问题无法被发现并解决`" -Level WARNING
        `$ArrayList.Add(`"--no-check-env`") | Out-Null
    }
}


# 获取启动 SD WebUI All In One 内核的启动参数
function Get-LaunchCoreArgs {
    `$launch_params = New-Object System.Collections.ArrayList
    Set-PyPIMirror `$launch_params
    Set-uv `$launch_params
    Set-GithubMirror `$launch_params
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

    if (!(Test-Path (Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX))) {
        Write-Log `"内核路径 `$(Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX) 未找到, 请检查 Qwen TTS WebUI 是否已正确安装, 或者尝试运行 Qwen TTS WebUI Installer 进行修复`" -Level ERROR
        Read-Host | Out-Null
        return
    }

    Test-MSVCPPRedistributable
    `$launch_args = Get-LaunchCoreArgs
    Add-Shortcut

    if (`$script:BuildMode) {
        Write-Log `"Qwen TTS WebUI Installer 构建模式已启用, 仅检查 Qwen TTS WebUI 运行环境`"
        & python -m sd_webui_all_in_one.cli_manager.main qwen-tts-webui check-env `$launch_args
    } else {
        & python -m sd_webui_all_in_one.cli_manager.main qwen-tts-webui launch `$launch_args
        `$req = `$?
        if (`$req) {
            Write-Log `"Qwen TTS WebUI 正常退出`"
        } else {
            Write-Log `"Qwen TTS WebUI 出现异常, 已退出`" -Level ERROR
        }
        Read-Host | Out-Null
    }
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "launch.ps1")) { "更新" } else { "生成" }) launch.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "launch.ps1") -Value $content
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

function Join-NormalizedPath {
    `$joined = `$args[0]
    for (`$i = 1; `$i -lt `$args.Count; `$i++) { `$joined = Join-Path `$joined `$args[`$i] }
    return `$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath(`$joined).TrimEnd('\', '/')
}

if (`$null -eq `$script:InstallPath) {
    `$script:InstallPath = `$PSScriptRoot
} else {
    `$script:InstallPath = Join-NormalizedPath `$script:InstallPath
}

& {
    `$target_prefix = `$null
    `$prefix_list = @(`"core`", `"qwen-tts-webui*`")
    if (`$script:CorePrefix -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"core_prefix.txt`"))) {
        `$origin_core_prefix = if (`$script:CorePrefix) {
            `$script:CorePrefix
        } else {
            (Get-Content (Join-NormalizedPath `$PSScriptRoot `"core_prefix.txt`") -Raw).Trim()
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
        [string]`$Name = `"Qwen TTS WebUI Installer`"
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


# 下载 Qwen TTS WebUI Installer
function Download-Installer {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/qwen_tts_webui_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/qwen_tts_webui_installer/qwen_tts_webui_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/qwen_tts_webui_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path (Join-NormalizedPath `$PSScriptRoot `"cache`") -Force > `$null

    ForEach (`$url in `$urls) {
        Write-Log `"正在下载最新的 Qwen TTS WebUI Installer 脚本`"
        `$web_request_params = @{
            Uri = `$url
            UseBasicParsing = `$true
            OutFile = (Join-NormalizedPath `$PSScriptRoot `"cache`" `"qwen_tts_webui_installer.ps1`")
            TimeoutSec = 15
            ErrorAction = `"Stop`"
        }
        Invoke-WebRequest @web_request_params
        if (`$?) {
            Write-Log `"下载 Qwen TTS WebUI Installer 脚本成功`"
            break
        } else {
            Write-Log `"下载 Qwen TTS WebUI Installer 脚本失败`" -Level ERROR
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Write-Log `"重试下载 Qwen TTS WebUI Installer 脚本`" -Level WARNING
            } else {
                Write-Log `"下载 Qwen TTS WebUI Installer 脚本失败, 可尝试重新运行 Qwen TTS WebUI Installer 下载脚本`" -Level ERROR
                return `$false
            }
        }
    }
    return `$true
}


# 获取本地配置文件参数
function Get-LocalSetting {
    `$arg = @{}
    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_pypi_mirror.txt`")) -or (`$script:DisablePyPIMirror)) {
        `$arg.Add(`"-DisablePyPIMirror`", `$true)
    }

    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_proxy.txt`")) -or (`$script:DisableProxy)) {
        `$arg.Add(`"-DisableProxy`", `$true)
    } else {
        if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"proxy.txt`")) -or (`$script:UseCustomProxy)) {
            if (`$script:UseCustomProxy) {
                `$proxy_value = `$script:UseCustomProxy
            } else {
                `$proxy_value = (Get-Content (Join-NormalizedPath `$PSScriptRoot `"proxy.txt`") -Raw).Trim()
            }
            `$arg.Add(`"-UseCustomProxy`", `$proxy_value)
        }
    }

    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_uv.txt`")) -or (`$script:DisableUV)) {
        `$arg.Add(`"-DisableUV`", `$true)
    }

    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_gh_mirror.txt`")) -or (`$script:DisableGithubMirror)) {
        `$arg.Add(`"-DisableGithubMirror`", `$true)
    } else {
        if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"gh_mirror.txt`")) -or (`$script:UseCustomGithubMirror)) {
            if (`$script:UseCustomGithubMirror) {
                `$github_mirror = `$script:UseCustomGithubMirror
            } else {
                `$github_mirror = (Get-Content (Join-NormalizedPath `$PSScriptRoot `"gh_mirror.txt`") -Raw).Trim()
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
    `$status = Download-Installer

    if (`$status) {
        Write-Log `"运行 Qwen TTS WebUI Installer 中`"
        `$arg = Get-LocalSetting
        `$extra_args = Get-ExtraArgs
        `$script_path = Join-NormalizedPath `$PSScriptRoot `"cache`" `"qwen_tts_webui_installer.ps1`"
        try {
            Invoke-Expression `"& ```"`$script_path```" `$extra_args @arg`"
        }
        catch {
            Write-Log `"运行 Qwen TTS WebUI Installer 时出现了错误: `$_`"
            Read-Host | Out-Null
        }
    } else {
        Read-Host | Out-Null
    }
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "launch_qwen_tts_webui_installer.ps1")) { "更新" } else { "生成" }) launch_qwen_tts_webui_installer.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "launch_qwen_tts_webui_installer.ps1") -Value $content
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
    `$config = @{
        OriginalScriptPath = `$script:PSCommandPath
        LaunchCommandLine = `$script:MyInvocation.Line
        CorePrefix = `$script:CorePrefix
        DisableUV = `$script:DisableUV
        DisableProxy = `$script:DisableProxy
        UseCustomProxy = `$script:UseCustomProxy
        DisablePyPIMirror = `$script:DisablePyPIMirror
        BuildMode = `$script:BuildMode
        DisableUpdate = `$script:DisableUpdate
    }
    (Import-Module `"`$PSScriptRoot/modules.psm1`" -Function `"Join-NormalizedPath`", `"Initialize-EnvPath`", `"Write-Log`", `"Set-CorePrefix`", `"Get-Version`", `"Set-PyPIMirror`", `"Update-Installer`", `"Set-uv`", `"Set-Proxy`", `"Update-SDWebUiAllInOne`" -PassThru -Force -ErrorAction Stop).Invoke({
        param (`$cfg)
        `$script:OriginalScriptPath = `$cfg.OriginalScriptPath
        `$script:LaunchCommandLine = `$cfg.LaunchCommandLine
        `$script:CorePrefix = `$cfg.CorePrefix
        `$script:DisableUV = `$cfg.DisableUV
        `$script:DisableProxy = `$cfg.DisableProxy
        `$script:UseCustomProxy = `$cfg.UseCustomProxy
        `$script:DisablePyPIMirror = `$cfg.DisablePyPIMirror
        `$script:BuildMode = `$cfg.BuildMode
        `$script:DisableUpdate = `$cfg.DisableUpdate
    }, `$config)
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White -NoNewline
    Write-Host `"launch_qwen_tts_webui_installer.ps1`" -ForegroundColor Yellow -NoNewline
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if (!(`$script:BuildMode)) { Read-Host | Out-Null }
    exit 1
}


# 帮助信息
function Get-InstallerCmdletHelp {
    `$content = `"
使用:
    ./`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-BuildMode] [-BuildWithTorch <PyTorch 版本编号>] [-BuildWithTorchReinstall] [-DisablePyPIMirror] [-DisableUpdate] [-DisableUV] [-DisableProxy] [-UseCustomProxy]

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


更多的帮助信息请阅读 Qwen TTS WebUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md
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
    & python -m sd_webui_all_in_one.cli_manager.main qwen-tts-webui reinstall-pytorch `$launch_args

    Write-Log `"退出 PyTorch 重装脚本`"
    if (!(`$script:BuildMode)) { Read-Host | Out-Null }
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "reinstall_pytorch.ps1")) { "更新" } else { "生成" }) reinstall_pytorch.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "reinstall_pytorch.ps1") -Value $content
}


# Qwen TTS WebUI Installer 设置脚本
function Write-SettingsScript {
    $content = "
param (
    [switch]`$Help,
    [string]`$CorePrefix,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy
)
try {
    `$config = @{
        OriginalScriptPath = `$script:PSCommandPath
        LaunchCommandLine = `$script:MyInvocation.Line
        CorePrefix = `$script:CorePrefix
        DisableProxy = `$script:DisableProxy
        UseCustomProxy = `$script:UseCustomProxy
    }
    (Import-Module `"`$PSScriptRoot/modules.psm1`" -Function `"Join-NormalizedPath`", `"Initialize-EnvPath`", `"Write-Log`", `"Set-CorePrefix`", `"Get-Version`", `"Update-Installer`", `"Set-Proxy`", `"Write-FileWithStreamWriter`" -PassThru -Force -ErrorAction Stop).Invoke({
        param (`$cfg)
        `$script:OriginalScriptPath = `$cfg.OriginalScriptPath
        `$script:LaunchCommandLine = `$cfg.LaunchCommandLine
        `$script:CorePrefix = `$cfg.CorePrefix
        `$script:DisableProxy = `$cfg.DisableProxy
        `$script:UseCustomProxy = `$cfg.UseCustomProxy
    }, `$config)
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White -NoNewline
    Write-Host `"launch_qwen_tts_webui_installer.ps1`" -ForegroundColor Yellow -NoNewline
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    Read-Host | Out-Null
    exit 1
}

# 帮助信息
function Get-InstallerCmdletHelp {
    `$content = `"
使用:
    ./`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-DisableProxy] [-UseCustomProxy]

参数:
    -Help
        获取 Qwen TTS WebUI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -DisableProxy
        禁用 Qwen TTS WebUI Installer 自动设置代理服务器

    -UseCustomProxy <代理服务器地址>
        使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址


更多的帮助信息请阅读 Qwen TTS WebUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md
`".Trim()

    if (`$script:Help) {
        Write-Host `$content
        exit 0
    }
}


# 通用开关状态获取
function Get-ToggleStatus ([string]`$file, [string]`$trueLabel = `"启用`", [string]`$falseLabel = `"禁用`", [bool]`$reverse = `$false) {
    `$exists = Test-Path (Join-NormalizedPath `$PSScriptRoot `$file)
    if (`$reverse) {
        if (`$exists) { return `$falseLabel } else { return `$trueLabel }
    }
    if (`$exists) { return `$trueLabel } else { return `$falseLabel }
}


# 通用文本配置获取
function Get-TextStatus ([string]`$file, [string]`$defaultLabel = `"无`") {
    if (Test-Path (Join-NormalizedPath `$PSScriptRoot `$file)) { return (Get-Content (Join-NormalizedPath `$PSScriptRoot `$file) -Raw).Trim() }
    return `$defaultLabel
}


# 通用开关切换逻辑
function Set-ToggleSetting ([string]`$file, [string]`$name, [bool]`$enable) {
    # 如果文件名以 disable 开头, 则 enable=true 表示删除文件, enable=false 表示创建文件
    if (`$file.ToLower().StartsWith(`"disable`")) {
        if (`$enable) {
            if (Test-Path (Join-NormalizedPath `$PSScriptRoot `$file)) { Remove-Item (Join-NormalizedPath `$PSScriptRoot `$file) -Force -ErrorAction SilentlyContinue }
        } else {
            if (!(Test-Path (Join-NormalizedPath `$PSScriptRoot `$file))) { New-Item -ItemType File -Path (Join-NormalizedPath `$PSScriptRoot `$file) -Force > `$null }
        }
    } else {
        # 普通开关: enable=true 表示创建文件, enable=false 表示删除文件
        if (`$enable) {
            if (!(Test-Path (Join-NormalizedPath `$PSScriptRoot `$file))) { New-Item -ItemType File -Path (Join-NormalizedPath `$PSScriptRoot `$file) -Force > `$null }
        } else {
            if (Test-Path (Join-NormalizedPath `$PSScriptRoot `$file)) { Remove-Item (Join-NormalizedPath `$PSScriptRoot `$file) -Force -ErrorAction SilentlyContinue }
        }
    }
    Write-Log `"`$name 设置成功`"
}


# 更新代理设置
function Update-ProxySetting {
    while (`$true) {
        `$current = if (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_proxy.txt`")) { `"禁用`" } elseif (Test-Path (Join-NormalizedPath `$PSScriptRoot `"proxy.txt`")) { `"自定义: `$((Get-Content (Join-NormalizedPath `$PSScriptRoot `"proxy.txt`") -Raw).Trim())`" } else { `"系统代理`" }
        Write-Log `"当前代理设置: `$current`"
        Write-Log `"1. 启用 (系统代理) | 2. 启用 (手动设置) | 3. 禁用 | 4. 返回`"
        `$choice = Get-UserInput
        if (`$choice -eq `"1`") { Remove-Item (Join-NormalizedPath `$PSScriptRoot `"disable_proxy.txt`"), (Join-NormalizedPath `$PSScriptRoot `"proxy.txt`") -Force -ErrorAction SilentlyContinue; break }
        elseif (`$choice -eq `"2`") { 
            Write-Log `"请输入代理地址 (如 http://127.0.0.1:10809):`"
            `$addr = Get-UserInput
            if (`$addr) {
                Remove-Item (Join-NormalizedPath `$PSScriptRoot `"disable_proxy.txt`") -Force -ErrorAction SilentlyContinue
                Set-Content -Path (Join-NormalizedPath `$PSScriptRoot `"proxy.txt`") -Value `$addr -Encoding UTF8
            }
            break 
        }
        elseif (`$choice -eq `"3`") { 
            New-Item (Join-NormalizedPath `$PSScriptRoot `"disable_proxy.txt`") -Force > `$null
            Remove-Item (Join-NormalizedPath `$PSScriptRoot `"proxy.txt`") -Force -ErrorAction SilentlyContinue
            break 
        }
        elseif (`$choice -eq `"4`") { return }
    }
}


# 更新镜像设置
function Update-Mirror-Setting ([string]`$file, [string]`$name, [string[]]`$examples) {
    while (`$true) {
        `$current = if (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_`$file`")) { `"禁用`" } elseif (Test-Path (Join-NormalizedPath `$PSScriptRoot `$file)) { `"自定义: `$((Get-Content (Join-NormalizedPath `$PSScriptRoot `$file) -Raw).Trim())`" } else { `"默认`" }
        Write-Log `"当前 `$name 设置: `$current`"
        Write-Log `"1. 默认/自动 | 2. 自定义地址 | 3. 禁用 | 4. 返回`"
        `$choice = Get-UserInput
        if (`$choice -eq `"1`") { Remove-Item (Join-NormalizedPath `$PSScriptRoot `"disable_`$file`"), (Join-NormalizedPath `$PSScriptRoot `$file) -Force -ErrorAction SilentlyContinue; break }
        elseif (`$choice -eq `"2`") {
            Write-Log `"请输入 `$name 地址, 示例:`"
            `$examples | ForEach-Object { Write-Log `"  `$_`" -Level INFO }
            `$addr = Get-UserInput
            if (`$addr) {
                Remove-Item (Join-NormalizedPath `$PSScriptRoot `"disable_`$file`") -Force -ErrorAction SilentlyContinue
                Set-Content -Path (Join-NormalizedPath `$PSScriptRoot `$file) -Value `$addr -Encoding UTF8
            }
            break
        }
        elseif (`$choice -eq `"3`") {
            New-Item (Join-NormalizedPath `$PSScriptRoot `"disable_`$file`") -Force > `$null
            Remove-Item (Join-NormalizedPath `$PSScriptRoot `$file) -Force -ErrorAction SilentlyContinue
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
            Set-Content -Path (Join-NormalizedPath `$PSScriptRoot `"core_prefix.txt`") -Value `$path -Encoding UTF8
        }
    }
    elseif (`$choice -eq `"2`") { Remove-Item (Join-NormalizedPath `$PSScriptRoot `"core_prefix.txt`") -Force -ErrorAction SilentlyContinue }
}


# 检测环境完整性
function Test-EnvIntegrity {
    `$items = @(
        @{ n=`"Python`"; p=(Join-NormalizedPath `"python`" `"python.exe`"); t=`"file`" },
        @{ n=`"Git`"; p=(Join-NormalizedPath `"git`" `"bin`" `"git.exe`"); t=`"file`" },
        @{ n=`"Aria2`"; p=(Join-NormalizedPath `"git`" `"bin`" `"aria2c.exe`"); t=`"file`" },
        @{ n=`"Qwen TTS WebUI`"; p=(Join-NormalizedPath `$env:CORE_PREFIX `"main.py`"); t=`"file`" },
        @{ n=`"uv`"; m=`"uv`" },
        @{ n=`"PyTorch`"; m=`"torch`" },
        @{ n=`"xFormers`"; m=`"xformers`" }
    )
    `$broken = `$false
    foreach (`$i in `$items) {
        `$ok = `$false
        if (`$i.p) { `$ok = (Test-Path (Join-NormalizedPath `$PSScriptRoot `$i.p)) -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX `$i.p)) }
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
    Set-Proxy -Legacy

    while (`$true) {
        Write-Log `"=== Qwen TTS WebUI 管理设置 ===`"
        `$menu = @(
            @{ id=1;  n=`"代理设置`"; v=`$(if (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_proxy.txt`")) { `"禁用`" } elseif (Test-Path (Join-NormalizedPath `$PSScriptRoot `"proxy.txt`")) { `"自定义 (地址: `$((Get-Content (Join-NormalizedPath `$PSScriptRoot `"proxy.txt`") -Raw).Trim()))`" } else { `"系统`" }) },
            @{ id=2;  n=`"包管理器`"; v=`$(Get-ToggleStatus `"disable_uv.txt`" `"Pip`" `"uv`") },
            @{ id=3;  n=`"HuggingFace 镜像源`"; v=`$(Get-ToggleStatus `"disable_hf_mirror.txt`" `"启用`" `"禁用`" `$true) },
            @{ id=4;  n=`"Github 镜像源`"; v=`$(Get-ToggleStatus `"disable_gh_mirror.txt`" `"启用`" `"禁用`" `$true) },
            @{ id=5;  n=`"自动检查更新`"; v=`$(Get-ToggleStatus `"disable_update.txt`" `"启用`" `"禁用`" `$true) },
            @{ id=6;  n=`"启动参数`"; v=`$(Get-TextStatus `"launch_args.txt`") },
            @{ id=7;  n=`"快捷方式`"; v=`$(Get-ToggleStatus `"enable_shortcut.txt`" `"启用`" `"禁用`") },
            @{ id=8;  n=`"PyPI 镜像`"; v=`$(Get-ToggleStatus `"disable_pypi_mirror.txt`" `"启用`" `"禁用`" `$true) },
            @{ id=9; n=`"CUDA 内存优化`"; v=`$(Get-ToggleStatus `"disable_set_pytorch_cuda_memory_alloc.txt`" `"启用`" `"禁用`" `$true) },
            @{ id=10; n=`"环境检测`"; v=`$(Get-ToggleStatus `"disable_check_env.txt`" `"启用`" `"禁用`" `$true) },
            @{ id=11; n=`"内核路径前缀`"; v=`$(Get-TextStatus `"core_prefix.txt`" `"自动`") }
        )

        `$menu | ForEach-Object { Write-Log `"`$(`$_.id). `$(`$_.n): `$(`$_.v)`" }
        Write-Log `"12. 检查更新 | 13. 文档 | 14. 退出`"
        Write-Log `"提示: 输入数字后回车`"

        `$choice = Get-UserInput
        switch (`$choice) {
            `"1`"  { Update-ProxySetting }
            `"2`"  { Set-ToggleSetting `"disable_uv.txt`" `"包管理器`" (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_uv.txt`")) }
            `"3`"  { Update-Mirror-Setting `"hf_mirror.txt`" `"HuggingFace`" @(`"https://hf-mirror.com`", `"https://huggingface.sukaka.top`") }
            `"4`"  { Update-Mirror-Setting `"gh_mirror.txt`" `"Github`" @(`"https://ghfast.top/https://github.com`", `"https://mirror.ghproxy.com/https://github.com`") }
            `"5`"  { Set-ToggleSetting `"disable_update.txt`" `"自动检查更新`" (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_update.txt`")) }
            `"6`"  { 
                Write-Log `"请输入启动参数 (直接回车删除):`"
                `$args = Get-UserInput
                if (`$args) { Write-FileWithStreamWriter -Path (Join-NormalizedPath `$PSScriptRoot `"launch_args.txt`") -Value `$args -Encoding UTF8 }
                else { Remove-Item (Join-NormalizedPath `$PSScriptRoot `"launch_args.txt`") -Force -ErrorAction SilentlyContinue }
            }
            `"7`"  { Set-ToggleSetting `"enable_shortcut.txt`" `"快捷方式`" (!(Test-Path (Join-NormalizedPath `$PSScriptRoot `"enable_shortcut.txt`"))) }
            `"8`"  { Set-ToggleSetting `"disable_pypi_mirror.txt`" `"PyPI 镜像`" (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_pypi_mirror.txt`")) }
            `"9`" { Set-ToggleSetting `"disable_set_pytorch_cuda_memory_alloc.txt`" `"CUDA 优化`" (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_set_pytorch_cuda_memory_alloc.txt`")) }
            `"10`" { Set-ToggleSetting `"disable_check_env.txt`" `"环境检测`" (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_check_env.txt`")) }
            `"11`" { Update-Core-Prefix }
            `"12`" { Remove-Item (Join-NormalizedPath `$PSScriptRoot `"update_time.txt`") -Force -ErrorAction SilentlyContinue; Update-Installer -DisableRestart }
            `"13`" { Start-Process `"https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md`" }
            `"14`" { Write-Log `"退出设置`"; return }
        }
    }
}

###################

Main
Read-Host | Out-Null
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "settings.ps1")) { "更新" } else { "生成" }) settings.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "settings.ps1") -Value $content
}

# 虚拟环境激活脚本
function Write-EnvActivateScript {
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
try {
    `$global:OriginalScriptPath = `$PSCommandPath
    `$global:LaunchCommandLine = `$MyInvocation.Line
    (Import-Module `"`$PSScriptRoot/modules.psm1`" -Function `"Join-NormalizedPath`", `"Initialize-EnvPath`", `"Write-Log`", `"Set-CorePrefix`", `"Get-Version`", `"Set-Proxy`", `"Get-NormalizedFilePath`" -PassThru -Force -ErrorAction Stop).Invoke({
        `$script:OriginalScriptPath = `$global:OriginalScriptPath
        `$script:LaunchCommandLine = `$global:LaunchCommandLine
        Remove-Variable OriginalScriptPath -Scope Global -Force
        Remove-Variable LaunchCommandLine -Scope Global -Force
        `$script:CorePrefix = `$script:CorePrefix
    })
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White -NoNewline
    Write-Host `"launch_qwen_tts_webui_installer.ps1`" -ForegroundColor Yellow -NoNewline
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
`$USE_PIP_MIRROR = if ((!(Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_pypi_mirror.txt`"))) -and (!(`$script:DisablePyPIMirror))) { `$true } else { `$false }
`$PIP_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_INDEX_ADDR } else { `$PIP_INDEX_ADDR_ORI }
`$PIP_EXTRA_INDEX_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_EXTRA_INDEX_ADDR } else { `$PIP_EXTRA_INDEX_ADDR_ORI }
`$PIP_FIND_MIRROR = if (`$USE_PIP_MIRROR) { `$PIP_FIND_ADDR } else { `$PIP_FIND_ADDR_ORI }
# PATH
`$PYTHON_PATH = Join-NormalizedPath `$PSScriptRoot `"python`"
`$PYTHON_EXTRA_PATH = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX `"python`"
`$PYTHON_SCRIPTS_PATH = Join-NormalizedPath `$PSScriptRoot `"python`" `"Scripts`"
`$PYTHON_SCRIPTS_EXTRA_PATH = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX `"python`" `"Scripts`"
`$GIT_PATH = Join-NormalizedPath `$PSScriptRoot `"git`" `"bin`"
`$GIT_EXTRA_PATH = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX `"git`" `"bin`"
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
`$env:CACHE_HOME = Join-NormalizedPath `$PSScriptRoot `"cache`"
`$env:HF_HOME = Join-NormalizedPath `$PSScriptRoot `"cache`" `"huggingface`"
`$env:MATPLOTLIBRC = Join-NormalizedPath `$PSScriptRoot `"cache`"
`$env:MODELSCOPE_CACHE = Join-NormalizedPath `$PSScriptRoot `"cache`" `"modelscope`" `"hub`"
`$env:MS_CACHE_HOME = Join-NormalizedPath `$PSScriptRoot `"cache`" `"modelscope`" `"hub`"
`$env:SYCL_CACHE_DIR = Join-NormalizedPath `$PSScriptRoot `"cache`" `"libsycl_cache`"
`$env:TORCH_HOME = Join-NormalizedPath `$PSScriptRoot `"cache`" `"torch`"
`$env:U2NET_HOME = Join-NormalizedPath `$PSScriptRoot `"cache`" `"u2net`"
`$env:XDG_CACHE_HOME = Join-NormalizedPath `$PSScriptRoot `"cache`"
`$env:PIP_CACHE_DIR = Join-NormalizedPath `$PSScriptRoot `"cache`" `"pip`"
`$env:PYTHONPYCACHEPREFIX = Join-NormalizedPath `$PSScriptRoot `"cache`" `"pycache`"
`$env:TORCHINDUCTOR_CACHE_DIR = Join-NormalizedPath `$PSScriptRoot `"cache`" `"torchinductor`"
`$env:TRITON_CACHE_DIR = Join-NormalizedPath `$PSScriptRoot `"cache`" `"triton`"
`$env:UV_CACHE_DIR = Join-NormalizedPath `$PSScriptRoot `"cache`" `"uv`"
`$env:QWEN_TTS_WEBUI_PATH = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX
`$env:QWEN_TTS_WEBUI_INSTALLER_ROOT = `$PSScriptRoot



# 帮助信息
function Get-InstallerCmdletHelp {
    `$content = `"
使用:
    ./`$(`$script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-DisablePyPIMirror] [-DisableGithubMirror] [-UseCustomGithubMirror <github 镜像源地址>] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>]

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


# 列出 Qwen TTS WebUI Installer 内置命令
function global:List-CMD {
    Write-Host `"
==================================
Qwen TTS WebUI Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
==================================

当前可用的 Qwen TTS WebUI Installer 内置命令：

    List-CMD

更多帮助信息可在 Qwen TTS WebUI Installer 文档中查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md
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


# HuggingFace 镜像源
function Set-HuggingFaceMirror {
    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_hf_mirror.txt`")) -or (`$script:DisableHuggingFaceMirror)) { # 检测是否禁用了自动设置 HuggingFace 镜像源
        Write-Log `"检测到本地存在 disable_hf_mirror.txt 镜像源配置文件 / -DisableHuggingFaceMirror 命令行参数, 禁用自动设置 HuggingFace 镜像源`"
        return
    }

    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"hf_mirror.txt`")) -or (`$script:UseCustomHuggingFaceMirror)) { # 本地存在 HuggingFace 镜像源配置
        if (`$script:UseCustomHuggingFaceMirror) {
            `$hf_mirror_value = `$script:UseCustomHuggingFaceMirror
        } else {
            `$hf_mirror_value = (Get-Content (Join-NormalizedPath `$PSScriptRoot `"hf_mirror.txt`") -Raw).Trim()
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
    `$env:GIT_CONFIG_GLOBAL = Join-NormalizedPath `$PSScriptRoot `".gitconfig`" # 设置 Git 配置文件路径
    if (Test-Path (Join-NormalizedPath `$PSScriptRoot `".gitconfig`")) {
        Remove-Item -Path (Join-NormalizedPath `$PSScriptRoot `".gitconfig`") -Force -Recurse
    }

    # 默认 Git 配置
    git config --global --add safe.directory '*'
    git config --global core.longpaths true

    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_gh_mirror.txt`")) -or (`$script:DisableGithubMirror)) { # 禁用 Github 镜像源
        Write-Log `"检测到本地存在 disable_gh_mirror.txt Github 镜像源配置文件 / -DisableGithubMirror 命令行参数, 禁用 Github 镜像源`"
        return
    }

    # 使用自定义 Github 镜像源
    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"gh_mirror.txt`")) -or (`$script:UseCustomGithubMirror)) {
        if (`$script:UseCustomGithubMirror) {
            `$github_mirror = `$script:UseCustomGithubMirror
        } else {
            `$github_mirror = (Get-Content (Join-NormalizedPath `$PSScriptRoot `"gh_mirror.txt`") -Raw).Trim()
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
    Set-Proxy -Legacy
    Set-HuggingFaceMirror
    Set-GithubMirrorLegecy
    Get-PyPIMirrorStatus

    `$python_cmd = Get-Command python -ErrorAction SilentlyContinue
    if (`$python_cmd) {
        `$python_path_prefix = Join-NormalizedPath `$PSScriptRoot `"python`"
        `$python_extra_path_prefix = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX `"python`"
        `$python_cmd = Get-NormalizedFilePath `$python_cmd.Path
        if ((`$python_cmd) -and ((`$python_cmd.ToString().StartsWith(`$python_path_prefix, [System.StringComparison]::OrdinalIgnoreCase)) -or (`$python_cmd.ToString().StartsWith(`$python_extra_path_prefix, [System.StringComparison]::OrdinalIgnoreCase)))) {
            `$env:UV_PYTHON = `$python_cmd
        }
    }

    Write-Log `"激活 Qwen TTS WebUI Env`"
    Write-Log `"更多帮助信息可在 Qwen TTS WebUI Installer 项目地址查看: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md`"
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "activate.ps1")) { "更新" } else { "生成" }) activate.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "activate.ps1") -Value $content
}


# 快捷启动终端脚本, 启动后将自动运行环境激活脚本
function Write-LaunchTerminalScript {
    $content = "
try {
    `$global:OriginalScriptPath = `$PSCommandPath
    `$global:LaunchCommandLine = `$MyInvocation.Line
    (Import-Module `"`$PSScriptRoot/modules.psm1`" -Function `"Join-NormalizedPath`", `"Write-Log`" -PassThru -Force -ErrorAction Stop).Invoke({
        `$script:OriginalScriptPath = `$global:OriginalScriptPath
        `$script:LaunchCommandLine = `$global:LaunchCommandLine
        Remove-Variable OriginalScriptPath -Scope Global -Force
        Remove-Variable LaunchCommandLine -Scope Global -Force
    })
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White -NoNewline
    Write-Host `"launch_qwen_tts_webui_installer.ps1`" -ForegroundColor Yellow -NoNewline
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    Read-Host | Out-Null
    exit 1
}
Write-Log `"执行 Qwen TTS WebUI Installer 激活环境脚本`"
& (Get-Process -Id `$PID).Path -NoExit -File (Join-NormalizedPath `$PSScriptRoot `"activate.ps1`")
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "terminal.ps1")) { "更新" } else { "生成" }) terminal.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "terminal.ps1") -Value $content
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

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "help.txt")) { "更新" } else { "生成" }) help.txt 中"
    Write-FileWithStreamWriter -Encoding UTF8 (Join-NormalizedPath $script:InstallPath "help.txt") -Value $content
}


# 写入管理脚本和文档
function Write-ManagerScripts {
    New-Item -ItemType Directory -Path $script:InstallPath -Force | Out-Null
    Write-ModulesScript
    Write-LaunchScript
    Write-LaunchInstallerScript
    Write-PyTorchReInstallScript
    Write-SettingsScript
    Write-EnvActivateScript
    Write-LaunchTerminalScript
    Write-ReadMe
    Write-ConfigureEnvScript
}


# 将安装器配置文件复制到管理脚本路径
function Copy-InstallerConfig {
    Write-Log "为 Qwen TTS WebUI Installer 管理脚本复制 Qwen TTS WebUI Installer 配置文件中"

    if ((!($script:DisablePyPIMirror)) -and (Test-Path (Join-NormalizedPath $PSScriptRoot "disable_pypi_mirror.txt"))) {
        Copy-Item -Path (Join-NormalizedPath $PSScriptRoot "disable_pypi_mirror.txt") -Destination $script:InstallPath -Force
        Write-Log "$(Join-NormalizedPath $PSScriptRoot "disable_pypi_mirror.txt") -> $(Join-NormalizedPath $script:InstallPath "disable_pypi_mirror.txt")"
    }

    if ((!($script:DisableProxy)) -and (Test-Path (Join-NormalizedPath $PSScriptRoot "disable_proxy.txt"))) {
        Copy-Item -Path (Join-NormalizedPath $PSScriptRoot "disable_proxy.txt") -Destination $script:InstallPath -Force
        Write-Log "$(Join-NormalizedPath $PSScriptRoot "disable_proxy.txt") -> $(Join-NormalizedPath $script:InstallPath "disable_proxy.txt")"
    } elseif ((!($script:DisableProxy)) -and ($script:UseCustomProxy -eq "") -and (Test-Path (Join-NormalizedPath $PSScriptRoot "proxy.txt")) -and (!(Test-Path (Join-NormalizedPath $PSScriptRoot "disable_proxy.txt")))) {
        Copy-Item -Path (Join-NormalizedPath $PSScriptRoot "proxy.txt") -Destination $script:InstallPath -Force
        Write-Log "$(Join-NormalizedPath $PSScriptRoot "proxy.txt") -> $(Join-NormalizedPath $script:InstallPath "proxy.txt")"
    }

    if ((!($script:DisableUV)) -and (Test-Path (Join-NormalizedPath $PSScriptRoot "disable_uv.txt"))) {
        Copy-Item -Path (Join-NormalizedPath $PSScriptRoot "disable_uv.txt") -Destination $script:InstallPath -Force
        Write-Log "$(Join-NormalizedPath $PSScriptRoot "disable_uv.txt") -> $(Join-NormalizedPath $script:InstallPath "disable_uv.txt")"
    }

    if ((!($script:DisableGithubMirror)) -and (Test-Path (Join-NormalizedPath $PSScriptRoot "disable_gh_mirror.txt"))) {
        Copy-Item -Path (Join-NormalizedPath $PSScriptRoot "disable_gh_mirror.txt") -Destination $script:InstallPath -Force
        Write-Log "$(Join-NormalizedPath $PSScriptRoot "disable_gh_mirror.txt") -> $(Join-NormalizedPath $script:InstallPath "disable_gh_mirror.txt")"
    } elseif ((!($script:DisableGithubMirror)) -and (!($script:UseCustomGithubMirror)) -and (Test-Path (Join-NormalizedPath $PSScriptRoot "gh_mirror.txt")) -and (!(Test-Path (Join-NormalizedPath $PSScriptRoot "disable_gh_mirror.txt")))) {
        Copy-Item -Path (Join-NormalizedPath $PSScriptRoot "gh_mirror.txt") -Destination $script:InstallPath -Force
        Write-Log "$(Join-NormalizedPath $PSScriptRoot "gh_mirror.txt") -> $(Join-NormalizedPath $script:InstallPath "gh_mirror.txt")"
    }

    if ((!($script:CorePrefix)) -and (Test-Path (Join-NormalizedPath $PSScriptRoot "core_prefix.txt"))) {
        Copy-Item -Path (Join-NormalizedPath $PSScriptRoot "core_prefix.txt") -Destination $script:InstallPath -Force
        Write-Log "$(Join-NormalizedPath $PSScriptRoot "core_prefix.txt") -> $(Join-NormalizedPath $script:InstallPath "core_prefix.txt")"
    }
}



# 执行安装
function Use-InstallMode {
    Write-Log "启动 Qwen TTS WebUI 安装程序"
    Write-Log "提示: 若出现某个步骤执行失败, 可尝试再次运行 Qwen TTS WebUI Installer, 更多的说明请阅读 Qwen TTS WebUI Installer 使用文档"
    Write-Log "Qwen TTS WebUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md"
    Write-Log "即将进行安装的路径: $script:InstallPath"
    Invoke-Installation
    Write-Log "添加管理脚本和文档中"
    Write-ManagerScripts
    Copy-InstallerConfig

    if ($script:BuildMode) {
        Use-BuildMode
        Write-Log "Qwen TTS WebUI 环境构建完成, 路径: $script:InstallPath"
    } else {
        Write-Log "Qwen TTS WebUI 安装结束, 安装路径为: $script:InstallPath"
    }

    Write-Log "帮助文档可在 Qwen TTS WebUI 文件夹中查看, 双击 help.txt 文件即可查看, 更多的说明请阅读 Qwen TTS WebUI Installer 使用文档"
    if (!($script:BuildMode)) { Invoke-Item (Join-NormalizedPath $script:InstallPath "help.txt") }
    Write-Log "Qwen TTS WebUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md"
    Write-Log "退出 Qwen TTS WebUI Installer"

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
        . (Join-NormalizedPath $InstallPath "reinstall_pytorch.ps1") @launch_args
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
        Write-Log "执行 Qwen TTS WebUI 更新脚本中"
        . (Join-NormalizedPath $InstallPath "update.ps1") @launch_args
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
        Write-Log "执行 Qwen TTS WebUI 启动脚本中"
        . (Join-NormalizedPath $InstallPath "launch.ps1") @launch_args
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

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "configure_env.bat")) { "更新" } else { "生成" }) configure_env.bat 中"
    Write-FileWithStreamWriter -Encoding GBK (Join-NormalizedPath $script:InstallPath "configure_env.bat") -Value $content
}


# 帮助信息
function Get-InstallerCmdletHelp {
    $content = "
使用:
    ./$($script:MyInvocation.MyCommand.Name) [-Help] [-CorePrefix <内核路径前缀>] [-InstallPath <安装 Qwen TTS WebUI 的绝对路径>] [-PyTorchMirrorType <PyTorch 镜像源类型>] [-InstallPythonVersion <Python 版本>] [-UseUpdateMode] [-DisablePyPIMirror] [-DisableProxy] [-UseCustomProxy <代理服务器地址>] [-DisableUV] [-DisableGithubMirror] [-UseCustomGithubMirror <Github 镜像站地址>] [-BuildMode] [-BuildWithUpdate] [-BuildWithLaunch] [-BuildWithTorch <PyTorch 版本编号>] [-BuildWithTorchReinstall] [-PyTorchPackage <PyTorch 软件包>] [-NoCleanCache] [-xFormersPackage <xFormers 软件包>] [-DisableUpdate] [-DisableHuggingFaceMirror] [-UseCustomHuggingFaceMirror <HuggingFace 镜像源地址>] [-LaunchArg <Qwen TTS WebUI 启动参数>] [-EnableShortcut] [-DisableCUDAMalloc] [-DisableEnvCheck]

参数:
    -Help
        获取 Qwen TTS WebUI Installer 的帮助信息

    -CorePrefix <内核路径前缀>
        设置内核的路径前缀, 默认路径前缀为 core

    -InstallPath <安装 Qwen TTS WebUI 的绝对路径>
        指定 Qwen TTS WebUI Installer 安装 Qwen TTS WebUI 的路径, 使用绝对路径表示
        例如: ./$($script:MyInvocation.MyCommand.Name) -InstallPath `"D:\Donwload`", 这将指定 Qwen TTS WebUI Installer 安装 Qwen TTS WebUI 到 D:\Donwload 这个路径

    -PyTorchMirrorType <PyTorch 镜像源类型>
        指定安装 PyTorch 时使用的 PyTorch 镜像源类型, 可指定的类型: cu113, cu117, cu118, cu121, cu124, cu126, cu128, cu129, cu130, rocm5.4.2, rocm5.6, rocm5.7, rocm6.0, rocm6.1, rocm6.2, rocm6.2.4, rocm6.3, rocm6.4, rocm7.1, xpu, ipex_legacy_arc, cpu, directml, all

    -InstallPythonVersion <Python 版本>
        指定要安装的 Python 版本, 如 -InstallPythonVersion `"3.10.11`"

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
        (仅在 Qwen TTS WebUI Installer 构建模式下生效, 并且只作用于 Qwen TTS WebUI Installer 管理脚本) 设置 Qwen TTS WebUI 自定义启动参数, 如启用 --fast 和 --auto-launch, 则使用 -LaunchArg `"--fast --auto-launch`" 进行启用

    -EnableShortcut
        (仅在 Qwen TTS WebUI Installer 构建模式下生效, 并且只作用于 Qwen TTS WebUI Installer 管理脚本) 创建 Qwen TTS WebUI 启动快捷方式

    -DisableCUDAMalloc
        (仅在 Qwen TTS WebUI Installer 构建模式下生效, 并且只作用于 Qwen TTS WebUI Installer 管理脚本) 禁用 Qwen TTS WebUI Installer 通过 PYTORCH_CUDA_ALLOC_CONF / PYTORCH_ALLOC_CONF 环境变量设置 CUDA 内存分配器

    -DisableEnvCheck
        (仅在 Qwen TTS WebUI Installer 构建模式下生效, 且只作用于 Qwen TTS WebUI Installer 管理脚本) 禁用 Qwen TTS WebUI Installer 检查 Qwen TTS WebUI 运行环境中存在的问题, 禁用后可能会导致 Qwen TTS WebUI 环境中存在的问题无法被发现并修复


更多的帮助信息请阅读 Qwen TTS WebUI Installer 使用文档: https://github.com/licyk/sd-webui-all-in-one/blob/main/docs/qwen_tts_webui_installer.md
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
        Set-Content -Encoding UTF8 -Path (Join-NormalizedPath $script:InstallPath "update_time.txt") -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
    } else {
        if ($script:BuildMode) { Write-Log "Qwen TTS WebUI Installer 构建模式已启用" }
        Write-Log "使用安装模式"
        Use-InstallMode
    }
}


###################


Main
