param (
    [Parameter(HelpMessage=@"
获取 SD Trainer Script Installer 的帮助信息
"@)][switch]$Help,

    [Parameter(HelpMessage=@"
设置内核的路径前缀, 默认路径前缀为 core
"@)][string]$CorePrefix,

    [Parameter(HelpMessage=@"
指定 SD Trainer Script Installer 安装 SD Trainer Script 的路径, 使用绝对路径表示
"@)][string]$InstallPath,

    [Parameter(HelpMessage=@"
指定安装 PyTorch 时使用的 PyTorch 镜像源类型, 可指定的类型: cu113, cu117, cu118, cu121, cu124, cu126, cu128, cu129, cu130, rocm5.4.2, rocm5.6, rocm5.7, rocm6.0, rocm6.1, rocm6.2, rocm6.2.4, rocm6.3, rocm6.4, rocm7.1, rocm_rdna3, rocm_rdna3.5, rocm_rdna4, rocm_win, xpu, ipex_legacy_arc, cpu, directml, all
"@)][string]$PyTorchMirrorType,

    [Parameter(HelpMessage=@"
指定要安装的 Python 版本, 可指定安装的 Python 版本: 3.10, 3.11, 3.12, 3.13, 3.14
"@)][string]$InstallPythonVersion,

    [Parameter(HelpMessage=@"
启用 SD Trainer Script Installer 快照重建模式, 将根据快照文件重新准备 Python 版本并恢复环境
"@)][switch]$RestoreFromSnapshot,

    [Parameter(HelpMessage=@"
指定用于快照重建的环境快照 JSON 文件路径
"@)][string]$SnapshotPath,

    [Parameter(HelpMessage=@"
禁用自动快照, 包括安装结束后的结果快照以及管理脚本执行前的自动快照
"@)][switch]$DisableSnapshot,

    [Parameter(HelpMessage=@"
指定 SD Trainer Script Installer 使用更新模式, 只对 SD Trainer Script Installer 的管理脚本进行更新
"@)][switch]$UseUpdateMode,

    [Parameter(HelpMessage=@"
禁用 SD Trainer Script Installer 使用 PyPI 软件包镜像源, 使用 PyPI 官方源下载 Python 软件包
"@)][switch]$DisablePyPIMirror,

    [Parameter(HelpMessage=@"
禁用 CLI 自动选择下载镜像源; 禁用后才会遵守 PyPI / GitHub / Hugging Face / 模型下载来源等手动镜像设置
"@)][switch]$DisableAutoMirror,

    [Parameter(HelpMessage=@"
禁用 SD Trainer Script Installer 自动设置代理服务器
"@)][switch]$DisableProxy,

    [Parameter(HelpMessage=@"
使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy "http://127.0.0.1:10809" 设置代理服务器地址
"@)][string]$UseCustomProxy,

    [Parameter(HelpMessage=@"
禁用 SD Trainer Script Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包
"@)][switch]$DisableUV,

    [Parameter(HelpMessage=@"
禁用 SD Trainer Script Installer 自动设置 GitHub 镜像源
"@)][switch]$DisableGithubMirror,

    [Parameter(HelpMessage=@"
使用自定义的 GitHub 镜像站地址
"@)][string]$UseCustomGithubMirror,

    [Parameter(HelpMessage=@"
指定 SD Trainer Script Installer 安装的 SD Trainer Script 分支 (sd_scripts_main, sd_scripts_dev, sd_scripts_sd3, ai_toolkit_main, finetrainers_main, diffusion_pipe_main, musubi_tuner_main)
未指定该参数时, 默认安装 kohya-ss/sd-scripts 分支
支持指定安装的分支如下:
    sd_scripts_main:        kohya-ss - sd-scripts 主分支
    sd_scripts_dev:         kohya-ss - sd-scripts 测试分支
    sd_scripts_sd3:         kohya-ss - sd-scripts SD3 分支
    ai_toolkit_main:        ostris - ai-toolkit 分支
    finetrainers_main:      a-r-r-o-w - finetrainers 分支
    diffusion_pipe_main:    tdrussell - diffusion-pipe 分支
    musubi_tuner_main:      kohya-ss - musubi-tuner 分支
"@)][string]$InstallBranch,

    [Parameter(HelpMessage=@"
启用 SD Trainer Script Installer 构建模式, 在基础安装流程结束后将调用 SD Trainer Script Installer 管理脚本执行剩余的安装任务, 并且出现错误时不再暂停 SD Trainer Script Installer 的执行, 而是直接退出
当指定调用多个 SD Trainer Script Installer 脚本时, 将按照优先顺序执行 (按从上到下的顺序)
    - reinstall_pytorch.ps1     (对应 -BuildWithTorch, -BuildWithTorchReinstall 参数)
    - download_models.ps1       (对应 -BuildWithModel 参数)
    - switch_branch.ps1         (对应 -BuildWithBranch 参数)
    - update.ps1                (对应 -BuildWithUpdate 参数)
    - init.ps1                  (对应 -BuildWithLaunch 参数)
"@)][switch]$BuildMode,

    [Parameter(HelpMessage=@"
(需添加 -BuildMode 启用 SD Trainer Script Installer 构建模式) SD Trainer Script Installer 执行完基础安装流程后调用 SD Trainer Script Installer 的 reinstall_pytorch.ps1 脚本, 根据 PyTorch 版本编号安装指定的 PyTorch 版本
PyTorch 版本编号可运行 reinstall_pytorch.ps1 脚本进行查看
"@)][int]$BuildWithTorch,

    [Parameter(HelpMessage=@"
(需添加 -BuildMode 启用 SD Trainer Script Installer 构建模式, 并且添加 -BuildWithTorch) 在 SD Trainer Script Installer 构建模式下, 执行 reinstall_pytorch.ps1 脚本对 PyTorch 进行指定版本安装时使用强制重新安装
"@)][switch]$BuildWithTorchReinstall,

    [Parameter(HelpMessage=@"
(需添加 -BuildMode 启用 SD Trainer Script Installer 构建模式) SD Trainer Script Installer 执行完基础安装流程后调用 SD Trainer Script Installer 的 download_models.ps1 脚本, 根据模型编号列表下载指定的模型
模型编号可运行 download_models.ps1 脚本进行查看
"@)][string]$BuildWithModel,

    [Parameter(HelpMessage=@"
(需添加 -BuildMode 启用 SD Trainer Script Installer 构建模式) SD Trainer Script Installer 执行完基础安装流程后调用 SD Trainer Script Installer 的 switch_branch.ps1 脚本, 根据 SD Trainer Script 分支编号切换到对应的 SD Trainer Script 分支
SD Trainer Script 分支编号可运行 switch_branch.ps1 脚本进行查看
"@)][string]$BuildWithBranch,

    [Parameter(HelpMessage=@"
(需添加 -BuildMode 启用 SD Trainer Script Installer 构建模式) SD Trainer Script Installer 执行完基础安装流程后调用 SD Trainer Script Installer 的 update.ps1 脚本, 更新 SD Trainer Script 内核
"@)][switch]$BuildWithUpdate,

    [Parameter(HelpMessage=@"
(需添加 -BuildMode 启用 SD Trainer Script Installer 构建模式) SD Trainer Script Installer 执行完基础安装流程后调用 SD Trainer Script Installer 的 launch.ps1 脚本, 执行启动 SD Trainer Script 前的环境检查流程, 但跳过启动 SD Trainer Script
"@)][switch]$BuildWithLaunch,

    [Parameter(HelpMessage=@"
安装 SD Trainer Script 时跳过预下载模型
"@)][switch]$NoPreDownloadModel,

    [Parameter(HelpMessage=@"
(需要同时搭配 -xFormersPackage 一起使用, 否则可能会出现 PyTorch 和 xFormers 不匹配的问题) 指定要安装 PyTorch 版本, 如 -PyTorchPackage "torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118"
"@)][string]$PyTorchPackage,

    [Parameter(HelpMessage=@"
(需要同时搭配 -PyTorchPackage 一起使用, 否则可能会出现 PyTorch 和 xFormers 不匹配的问题) 指定要安装 xFormers 版本, 如 -xFormersPackage "xformers===0.0.26.post1+cu118"
"@)][string]$xFormersPackage,

    [Parameter(HelpMessage=@"
安装结束后保留下载 Python 软件包缓存
"@)][switch]$NoCleanCache,

    [Parameter(HelpMessage=@"
不使用 ModelScope 下载模型, 使用 Hugging Face 下载模型
"@)][switch]$DisableModelMirror,

    [Parameter(HelpMessage=@"
脚本执行完成后不暂停, 直接退出
"@)][switch]$NoPause,


    # 仅在管理脚本中生效
    [Parameter(HelpMessage=@"
(仅在 SD Trainer Script Installer 构建模式下生效, 并且只作用于 SD Trainer Script Installer 管理脚本) 禁用 SD Trainer Script Installer 更新检查
"@)][switch]$DisableUpdate,

    [Parameter(HelpMessage=@"
(仅在 SD Trainer Script Installer 构建模式下生效, 并且只作用于 SD Trainer Script Installer 管理脚本) 禁用 Hugging Face 镜像源, 不使用 Hugging Face 镜像源下载文件
"@)][switch]$DisableHuggingFaceMirror,

    [Parameter(HelpMessage=@"
(仅在 SD Trainer Script Installer 构建模式下生效, 并且只作用于 SD Trainer Script Installer 管理脚本) 使用自定义 Hugging Face 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror "https://hf-mirror.com" 设置 Hugging Face 镜像源地址
"@)][string]$UseCustomHuggingFaceMirror,

    [Parameter(HelpMessage=@"
(仅在 SD Trainer Script Installer 构建模式下生效, 并且只作用于 SD Trainer Script Installer 管理脚本) 设置 SD Trainer Script 自定义启动参数, 如启用 --fast 和 --auto-launch, 则使用 -LaunchArg "--fast --auto-launch" 进行启用
"@)][string]$LaunchArg,

    [Parameter(HelpMessage=@"
(仅在 SD Trainer Script Installer 构建模式下生效, 并且只作用于 SD Trainer Script Installer 管理脚本) 禁用 SD Trainer Script Installer 通过 PYTORCH_CUDA_ALLOC_CONF / PYTORCH_ALLOC_CONF 环境变量设置 CUDA 内存分配器
"@)][switch]$DisableCUDAMalloc,

    [Parameter(HelpMessage=@"
(仅在 SD Trainer Script Installer 构建模式下生效, 且只作用于 SD Trainer Script Installer 管理脚本) 禁用 SD Trainer Script Installer 检查 SD Trainer Script 运行环境中存在的问题, 禁用后可能会导致 SD Trainer Script 环境中存在的问题无法被发现并修复
"@)][switch]$DisableEnvCheck,

    [Parameter(HelpMessage=@"
(仅在 SD Trainer Script Installer 构建模式下生效, 并且只作用于 SD Trainer Script Installer 管理脚本) 禁用 Hotpatcher 补丁系统注入
"@)][switch]$DisableHotpatcher,

    [Parameter(HelpMessage=@"
(仅在 SD Trainer Script Installer 构建模式下生效, 并且只作用于 SD Trainer Script Installer 管理脚本) 设置 Hotpatcher runtime 通信端口, 范围为 1 到 65535
"@)][int]$HotpatcherPort,

    [Parameter(HelpMessage=@"
启用 Hotpatcher runtime host 连接
"@)][switch]$EnableHotpatcherRuntime
)


function Join-NormalizedPath {
    $joined = $args[0]
    for ($i = 1; $i -lt $args.Count; $i++) { $joined = Join-Path $joined $args[$i] }
    return $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($joined).TrimEnd('\', '/')
}


function Get-TrimmedTextFile {
    param (
        [Parameter(Mandatory = $true)][string]$Path,
        [string]$Encoding
    )
    if (!(Test-Path $Path)) {
        return $null
    }
    if ([string]::IsNullOrWhiteSpace($Encoding)) {
        $content = Get-Content -Path $Path -Raw
    } else {
        $content = Get-Content -Path $Path -Raw -Encoding $Encoding
    }
    if ([string]::IsNullOrWhiteSpace($content)) {
        return $null
    }
    return $content.Trim()
}


function Resolve-CorePrefix {
    param (
        [Parameter(Mandatory = $true)][string]$BasePath,
        [Parameter(Mandatory = $true)][string[]]$PrefixList,
        [AllowNull()][string]$ConfiguredPrefix
    )
    $target_prefix = $null
    if (-not [string]::IsNullOrWhiteSpace($ConfiguredPrefix)) {
        $origin_core_prefix = $ConfiguredPrefix.TrimEnd('\', '/')
        if ([System.IO.Path]::IsPathRooted($origin_core_prefix)) {
            $from_uri = New-Object System.Uri($BasePath.Replace('\', '/') + '/')
            $to_uri = New-Object System.Uri($origin_core_prefix.Replace('\', '/'))
            $target_prefix = $from_uri.MakeRelativeUri($to_uri).ToString().Trim('/')
        } else {
            $target_prefix = $origin_core_prefix
        }
    }
    if ([string]::IsNullOrWhiteSpace($target_prefix)) {
        foreach ($i in $PrefixList) {
            $found_dir = Get-ChildItem -Path $BasePath -Directory -Filter $i -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($found_dir) {
                $target_prefix = $found_dir.Name
                break
            }
        }
    }
    if ([string]::IsNullOrWhiteSpace($target_prefix)) {
        $target_prefix = "core"
    }
    return $target_prefix
}

if (-not $script:InstallPath) {
    $script:InstallPath = Join-NormalizedPath $PSScriptRoot "SD-Trainer-Script"
}

$script:InstallPath = Join-NormalizedPath $script:InstallPath
$script:HotpatcherPortProvided = $PSBoundParameters.ContainsKey("HotpatcherPort")

& {
    $prefix_list = @("core", "sd-scripts*")
    $core_prefix_file = Join-NormalizedPath $script:InstallPath "core_prefix.txt"
    $origin_core_prefix = if ($script:CorePrefix) {
        $script:CorePrefix
    } else {
        Get-TrimmedTextFile $core_prefix_file -Encoding UTF8
    }
    $env:CORE_PREFIX = Resolve-CorePrefix -BasePath $script:InstallPath -PrefixList $prefix_list -ConfiguredPrefix $origin_core_prefix
}
# SD Trainer Script Installer 版本和检查更新间隔
$script:SD_TRAINER_SCRIPT_INSTALLER_VERSION = 397
$script:UPDATE_TIME_SPAN = 3600
# SD WebUI All In One 内核最低版本
$script:CORE_MINIMUM_VER = "2.2.53"
# 快照重建模式
$script:SnapshotExpectedWebUIType = "sd_scripts"
$script:SnapshotRestoreCliName = "sd-scripts"
$script:SnapshotRestorePathArgument = "--sd-scripts-path"
$script:SnapshotDisplayName = "SD Trainer Script"
$script:SnapshotRequiresGitKernel = $true
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
$env:SD_SCRIPTS_PATH = Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX
$env:SD_SCRIPTS_ROOT = Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX
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
$env:SD_WEBUI_ALL_IN_ONE_LOGGER_NAME = "SD Trainer Script Installer"
$env:SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL = 20
$env:SD_WEBUI_ALL_IN_ONE_LOGGER_COLOR = 1
$env:SD_WEBUI_ALL_IN_ONE_RETRY_TIMES = 3
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
        [string]$Name = "SD Trainer Script Installer"
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


# 获取原生命令退出码
function Get-NativeCommandExitCode {
    param ([bool]$Success)
    if ($Success) {
        return 0
    }
    if (($null -ne $global:LASTEXITCODE) -and ($global:LASTEXITCODE -ne 0)) {
        return [int]$global:LASTEXITCODE
    }
    return 1
}


# 格式化命令行参数日志
function Format-CommandLineArgumentForLog {
    param ([AllowNull()][object]$Argument)
    if ($null -eq $Argument) {
        return "''"
    }
    $value = [string]$Argument
    if ($value.Length -eq 0) {
        return "''"
    }
    if ($value -match '[\s''"]') {
        return ([string][char]39) + ($value -replace ([string][char]39), ([string][char]39 + [string][char]39)) + ([string][char]39)
    }
    return $value
}


# 格式化 SD WebUI All In One CLI 命令日志
function Format-CoreCliCommandForLog {
    param (
        [Parameter(Mandatory = $true)][object]$CommandPrefix,
        [object]$Arguments
    )
    $parts = New-Object System.Collections.ArrayList
    foreach ($item in $CommandPrefix) {
        $parts.Add((Format-CommandLineArgumentForLog $item)) | Out-Null
    }
    if ($null -ne $Arguments) {
        foreach ($item in $Arguments) {
            $parts.Add((Format-CommandLineArgumentForLog $item)) | Out-Null
        }
    }
    return ($parts -join ' ')
}


# 输出 SD WebUI All In One CLI 失败命令
function Write-CoreCliFailureCommand {
    param (
        [Parameter(Mandatory = $true)][object]$CommandPrefix,
        [object]$Arguments,
        [Parameter(Mandatory = $true)][int]$ExitCode
    )
    Write-Log "SD WebUI All In One CLI 执行失败, 退出码: $ExitCode" -Level ERROR
    $command_line = Format-CoreCliCommandForLog -CommandPrefix $CommandPrefix -Arguments $Arguments
    Write-Log "失败命令: $command_line" -Level ERROR
}


# 写入文本文件
function Write-FileWithStreamWriter {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Value,
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $false)][ValidateSet("GBK", "UTF8", "UTF8BOM")][string]$Encoding = "UTF8"
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


# 获取 Installer 内核路径前缀状态
function Get-CorePrefixStatus {
    $core_prefix_file = Join-NormalizedPath $PSScriptRoot "core_prefix.txt"
    $origin_core_prefix = if ($script:CorePrefix) {
        $script:CorePrefix
    } else {
        Get-TrimmedTextFile $core_prefix_file -Encoding UTF8
    }
    if (-not [string]::IsNullOrWhiteSpace($origin_core_prefix)) {
        Write-Log "检测到 core_prefix.txt 配置文件 / -CorePrefix 命令行参数, 使用自定义 Installer 内核路径前缀"
        if ([System.IO.Path]::IsPathRooted($origin_core_prefix.Trim('/').Trim('\'))) {
            Write-Log "转换绝对路径为 Installer 内核路径前缀: $origin_core_prefix -> $env:CORE_PREFIX"
        }
    }
    Write-Log "当前 Installer 内核路径前缀: $env:CORE_PREFIX"
    Write-Log "完整内核路径: $(Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX)"
}


# 显示 SD Trainer Script Installer 版本
function Get-Version {
    $ver = $([string]$script:SD_TRAINER_SCRIPT_INSTALLER_VERSION).ToCharArray()
    $major = ($ver[0..($ver.Length - 3)])
    $minor = $ver[-2]
    $micro = $ver[-1]
    Write-Log "SD Trainer Script Installer 版本: v${major}.${minor}.${micro}"
}


# 设置 CLI 自动选择下载镜像源状态
function Set-AutoMirror {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]$ArrayList)

    if (($script:DisableAutoMirror) -or (Test-Path (Join-NormalizedPath $PSScriptRoot "disable_auto_mirror.txt"))) {
        if (-not $ArrayList.Contains("--no-auto-mirror")) {
            $ArrayList.Add("--no-auto-mirror") | Out-Null
        }
        if (-not $script:AutoMirrorStatusLogged) {
            Write-Log "检测到 disable_auto_mirror.txt 配置文件 / -DisableAutoMirror 命令行参数, 已禁用 CLI 自动选择下载镜像源, 将遵守手动镜像源设置"
            $script:AutoMirrorStatusLogged = $true
        }
        return $true
    }

    if (-not $script:AutoMirrorStatusLogged) {
        Write-Log "CLI 自动选择下载镜像源已启用, 将由 Python CLI 根据网络检测结果强制覆盖镜像源相关参数"
        $script:AutoMirrorStatusLogged = $true
    }
    return $false
}


# PyPI 软件包镜像源状态
function Set-PyPIMirror {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]$ArrayList)
    if (!(Set-AutoMirror $ArrayList)) { return }
    if ((!(Test-Path (Join-NormalizedPath $PSScriptRoot "disable_pypi_mirror.txt"))) -and (!($script:DisablePyPIMirror))) {
        Write-Log "使用 PyPI 软件包镜像源"
    } else {
        Write-Log "检测到 disable_pypi_mirror.txt 配置文件 / -DisablePyPIMirror 命令行参数, 已将 PyPI 源切换至官方源"
        $ArrayList.Add("--no-pypi-mirror") | Out-Null
    }
}


# 设置模型下载来源
function Set-ModelMirror {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]$ArrayList)
    if (!(Set-AutoMirror $ArrayList)) { return }
    $ArrayList.Add("--model-resource") | Out-Null
    if ((!(Test-Path (Join-NormalizedPath $PSScriptRoot "disable_model_mirror.txt"))) -and (!($script:DisableModelMirror))) {
        Write-Log "使用 ModelScope 模型下载来源"
        $ArrayList.Add("modelscope") | Out-Null
    } else {
        Write-Log "检测到 disable_model_mirror.txt 配置文件 / -DisableModelMirror 命令行参数, 已将模型下载来源切换至 Hugging Face 源"
        $ArrayList.Add("huggingface") | Out-Null
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
            $proxy_value = Get-TrimmedTextFile (Join-NormalizedPath $PSScriptRoot "proxy.txt") -Encoding UTF8
        }
        if (-not [string]::IsNullOrWhiteSpace($proxy_value)) {
            $env:HTTP_PROXY = $proxy_value
            $env:HTTPS_PROXY = $proxy_value
            Write-Log "检测到本地存在 proxy.txt 代理配置文件 / -UseCustomProxy 命令行参数, 已读取代理配置文件并设置代理"
        }
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

# 设置 GitHub 镜像源
function Set-GithubMirror {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]$ArrayList)
    if (Test-Path (Join-NormalizedPath $script:InstallPath ".gitconfig")) {
        Remove-Item -Path (Join-NormalizedPath $script:InstallPath ".gitconfig") -Force -Recurse
    }
    if (!(Set-AutoMirror $ArrayList)) { return }
    if (($script:DisableGithubMirror) -or (Test-Path (Join-NormalizedPath $PSScriptRoot "disable_gh_mirror.txt"))) {
        Write-Log "检测到本地存在 disable_gh_mirror.txt GitHub 镜像源配置文件 / -DisableGithubMirror 命令行参数, 禁用 GitHub 镜像源"
        $ArrayList.Add("--no-github-mirror") | Out-Null
        return
    }
    if (($script:UseCustomGithubMirror) -or (Test-Path (Join-NormalizedPath $PSScriptRoot "gh_mirror.txt"))) {
        if ($script:UseCustomGithubMirror) {
            $github_mirror = $script:UseCustomGithubMirror
        } else {
            $github_mirror = Get-TrimmedTextFile (Join-NormalizedPath $PSScriptRoot "gh_mirror.txt") -Encoding UTF8
        }
        if (-not [string]::IsNullOrWhiteSpace($github_mirror)) {
            Write-Log "检测到本地存在 gh_mirror.txt GitHub 镜像源配置文件 / -UseCustomGithubMirror 命令行参数, 已读取 GitHub 镜像源配置文件并设置 GitHub 镜像源"
            $ArrayList.Add("--custom-github-mirror") | Out-Null
            $ArrayList.Add($github_mirror) | Out-Null
            return
        }
    }
}

function Get-InstallBranch {
    $branch_mapping_table = @(
        @{ Key = "sd_scripts";          Val = "sd_scripts_dev" }
        @{ Key = "sd_scripts_main";     Val = "sd_scripts_main" }
        @{ Key = "sd_scripts_dev";      Val = "sd_scripts_dev" }
        @{ Key = "sd_scripts_sd3";      Val = "sd_scripts_sd3" }
        @{ Key = "ai_toolkit";          Val = "ai_toolkit_main" }
        @{ Key = "ai_toolkit_main";     Val = "ai_toolkit_main" }
        @{ Key = "finetrainers";        Val = "finetrainers_main" }
        @{ Key = "finetrainers_main";   Val = "finetrainers_main" }
        @{ Key = "diffusion_pipe";      Val = "diffusion_pipe_main" }
        @{ Key = "diffusion_pipe_main"; Val = "diffusion_pipe_main" }
        @{ Key = "musubi_tuner";        Val = "musubi_tuner_main" }
        @{ Key = "musubi_tuner_main";   Val = "musubi_tuner_main" }
    )
    $target_branch = $null
    foreach ($item in $branch_mapping_table) {
        $file_path = Join-Path $PSScriptRoot "install_$($item.Key).txt"
        if ((Test-Path $file_path) -or ($script:InstallBranch -eq $item.Key)) {
            $target_branch = $item.Val
            break
        }
    }
    return $target_branch
}

# 获取启动 SD WebUI All In One 内核的启动参数
function Get-LaunchCoreArgs {
    $launch_params = New-Object System.Collections.ArrayList
    Set-uv $launch_params
    Set-PyPIMirror $launch_params
    Set-Proxy
    Set-GithubMirror $launch_params
    Set-ModelMirror $launch_params
    if ($script:NoPreDownloadModel) {
        $launch_params.Add("--no-pre-download-model") | Out-Null
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
    $target_branch = Get-InstallBranch
    if ($target_branch) {
        $launch_params.Add("--install-branch") | Out-Null
        $launch_params.Add($target_branch) | Out-Null
    }
    return $launch_params
}

# 检查 SD WebUI ALL In One 内核版本
function Get-RestoreCoreArgs {
    $restore_params = New-Object System.Collections.ArrayList
    Set-uv $restore_params
    Set-PyPIMirror $restore_params
    Set-Proxy
    Set-GithubMirror $restore_params
    $restore_params.Add("--prune-packages") | Out-Null
    $restore_params.Add("--prune-extensions") | Out-Null
    return $restore_params
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
    if (!($?)) { & python -m pip install -U "sd-webui-all-in-one>=$script:CORE_MINIMUM_VER" }
    if (!($?)) {
        Write-Log "SD WebUI All In One 内核更新失败, Installer 部分功能将无法使用" -Level ERROR
        if ((-not $script:BuildMode) -and (-not $script:NoPause)) { Read-Host | Out-Null }
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
        Write-Log "$ResourceName 安装失败, 终止安装进程, 可尝试重新运行 SD Trainer Script Installer 重试失败的安装" -Level ERROR
        if ((-not $script:BuildMode) -and (-not $script:NoPause)) { Read-Host | Out-Null }
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
    }
    else {
        if ([Environment]::Is64BitOperatingSystem) {
            if ($env:PROCESSOR_ARCHITEW6432) {
                $arch = $env:PROCESSOR_ARCHITEW6432.ToLower()
            }
            else {
                $arch = $env:PROCESSOR_ARCHITECTURE.ToLower()
            }
        }
        else {
            $arch = "x86"
        }
    }
    switch ($arch) {
        "amd64"  { return "amd64" }
        "x64"    { return "amd64" }
        "arm64"  { return "aarch64" }
        "x86_64" { return "amd64" }
        "x86"    { return "x86" }
        "i386"   { return "x86" }
        "i686"   { return "x86" }
        default  { return $arch }
    }
}



function Get-NormalizedFilePath {
    [CmdletBinding()]
    param ([Parameter(Mandatory = $false)][string]$Filepath)
    if (-not [string]::IsNullOrWhiteSpace($Filepath)) { return Join-NormalizedPath $Filepath }
    return $null
}

function Stop-SnapshotRestore {
    [CmdletBinding()]
    param ([Parameter(Mandatory = $true)][string]$Message)
    Write-Log $Message -Level ERROR
    if ((-not $script:BuildMode) -and (-not $script:NoPause)) { Read-Host | Out-Null }
    exit 1
}

function Normalize-SnapshotPlatform {
    param ([AllowNull()][string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return $null }
    switch ($Value.Trim().ToLowerInvariant()) {
        "windows" { return "windows" }
        "win32" { return "windows" }
        "linux" { return "linux" }
        "darwin" { return "macos" }
        "macos" { return "macos" }
        "osx" { return "macos" }
        default { return $Value.Trim().ToLowerInvariant() }
    }
}

function Normalize-SnapshotArchitecture {
    param ([AllowNull()][string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return $null }
    switch ($Value.Trim().ToLowerInvariant()) {
        "amd64" { return "amd64" }
        "x64" { return "amd64" }
        "x86_64" { return "amd64" }
        "arm64" { return "aarch64" }
        "aarch64" { return "aarch64" }
        "x86" { return "x86" }
        "i386" { return "x86" }
        "i686" { return "x86" }
        default { return $Value.Trim().ToLowerInvariant() }
    }
}

function Get-PythonMajorMinor {
    [CmdletBinding()]
    param ([AllowNull()][string]$Version)
    if ([string]::IsNullOrWhiteSpace($Version)) {
        Stop-SnapshotRestore "快照中的 Python 版本字段为空, 无法进行快照重建"
    }
    $version_text = $Version.Trim()
    if ($version_text -match '^(\d+)\.(\d+)') {
        return "$($Matches[1]).$($Matches[2])"
    }
    Stop-SnapshotRestore "快照中的 Python 版本字段无法识别: $version_text"
}

function Get-ManagedPythonExecutable {
    [CmdletBinding()]
    param ([Parameter(Mandatory = $true)][string]$PythonPath)
    $windows_python = Join-NormalizedPath $PythonPath "python.exe"
    if (Test-Path -LiteralPath $windows_python -PathType Leaf) { return $windows_python }
    $unix_python = Join-NormalizedPath $PythonPath "bin" "python"
    if (Test-Path -LiteralPath $unix_python -PathType Leaf) { return $unix_python }
    $portable_python = Join-NormalizedPath $PythonPath "python"
    if (Test-Path -LiteralPath $portable_python -PathType Leaf) { return $portable_python }
    return $null
}

function Get-ManagedPythonMajorMinor {
    [CmdletBinding()]
    param ([Parameter(Mandatory = $true)][string]$PythonPath)
    $python_executable = Get-ManagedPythonExecutable -PythonPath $PythonPath
    if (-not $python_executable) { return $null }
    try {
        $version = & $python_executable -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        return ($version | Select-Object -First 1).Trim()
    } catch {
        return $null
    }
}

function Remove-ManagedPythonIfVersionMismatch {
    [CmdletBinding()]
    param ([Parameter(Mandatory = $true)][string]$ExpectedVersion)
    $managed_python_paths = @(
        (Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX "python"),
        (Join-NormalizedPath $script:InstallPath "python")
    )
    foreach ($python_path in $managed_python_paths) {
        if (!(Test-Path -LiteralPath $python_path -PathType Container)) { continue }
        $current_version = Get-ManagedPythonMajorMinor -PythonPath $python_path
        if ($current_version -eq $ExpectedVersion) {
            Write-Log "受 Installer 管理的 Python 版本已匹配快照: $current_version ($python_path)"
            continue
        }
        if ($current_version) {
            Write-Log "快照要求 Python $ExpectedVersion, 删除不匹配的受管 Python ${current_version}: $python_path" -Level WARNING
        } else {
            Write-Log "无法识别受管 Python 版本, 将按快照要求重建 Python ${ExpectedVersion}: $python_path" -Level WARNING
        }
        Remove-Item -LiteralPath $python_path -Force -Recurse
    }
}

function Test-DirectoryEmpty {
    [CmdletBinding()]
    param ([Parameter(Mandatory = $true)][string]$Path)
    if (!(Test-Path -LiteralPath $Path -PathType Container)) { return $true }
    return $null -eq (Get-ChildItem -LiteralPath $Path -Force -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Test-InstallerGitKernelSnapshot {
    [CmdletBinding()]
    param ([Parameter(Mandatory = $true)]$Snapshot)
    if (-not $script:SnapshotRequiresGitKernel) { return }
    if ($null -eq $Snapshot.kernel) {
        Stop-SnapshotRestore "快照缺少内核信息, 无法在 Installer 重建模式中恢复 $script:SnapshotDisplayName"
    }
    if (-not [System.Convert]::ToBoolean($Snapshot.kernel.is_git_repo)) {
        Stop-SnapshotRestore "快照中的 $script:SnapshotDisplayName 内核不是 Git 仓库, Installer 重建模式无法恢复该内核"
    }
    if ([string]::IsNullOrWhiteSpace([string]$Snapshot.kernel.url)) {
        Stop-SnapshotRestore "快照中的 $script:SnapshotDisplayName 内核缺少 Git 远程地址, 无法从头重建环境"
    }
    if ([string]::IsNullOrWhiteSpace([string]$Snapshot.kernel.commit)) {
        Stop-SnapshotRestore "快照中的 $script:SnapshotDisplayName 内核缺少 Git commit, 无法恢复到快照版本"
    }
}

function Resolve-SnapshotRebuildConfig {
    $restore_enabled = [bool]$script:RestoreFromSnapshot
    $snapshot_path_provided = -not [string]::IsNullOrWhiteSpace($script:SnapshotPath)
    if ($restore_enabled -ne $snapshot_path_provided) {
        Stop-SnapshotRestore "启用快照重建模式时必须同时传入 -RestoreFromSnapshot 和 -SnapshotPath"
    }
    if (-not $restore_enabled) { return }

    $snapshot_path = Get-NormalizedFilePath $script:SnapshotPath
    if (!(Test-Path -LiteralPath $snapshot_path -PathType Leaf)) {
        Stop-SnapshotRestore "快照文件不存在: $snapshot_path"
    }

    try {
        $snapshot = Get-Content -Raw -Encoding UTF8 -Path $snapshot_path | ConvertFrom-Json -ErrorAction Stop
    } catch {
        Stop-SnapshotRestore "读取快照文件失败: $snapshot_path, $($_.Exception.Message)"
    }

    $snapshot_webui_type = [string]$snapshot.webui.type
    if ($snapshot_webui_type -ne $script:SnapshotExpectedWebUIType) {
        Stop-SnapshotRestore "快照 WebUI 类型不匹配: 期望 '$script:SnapshotExpectedWebUIType', 实际 '$snapshot_webui_type'"
    }

    $snapshot_platform = Normalize-SnapshotPlatform $snapshot.system.system
    $snapshot_arch = Normalize-SnapshotArchitecture $snapshot.system.architecture
    $current_platform = Get-CurrentPlatform
    $current_arch = Get-CurrentArchitecture
    if ([string]::IsNullOrWhiteSpace($snapshot_platform) -or [string]::IsNullOrWhiteSpace($snapshot_arch)) {
        Stop-SnapshotRestore "快照缺少系统或架构字段, 无法确认是否可在当前平台重建"
    }
    if (($snapshot_platform -ne $current_platform) -or ($snapshot_arch -ne $current_arch)) {
        Stop-SnapshotRestore "快照平台不匹配: 快照为 $snapshot_platform/$snapshot_arch, 当前为 $current_platform/$current_arch"
    }

    $target_python_version = Get-PythonMajorMinor $snapshot.python.version
    $python_info = Get-PythonDownloadUrl -Version $target_python_version -Platform $current_platform -Arch $current_arch
    if (-not $python_info) {
        Stop-SnapshotRestore "Installer 当前不支持安装快照要求的 Python $target_python_version ($current_platform/$current_arch)"
    }
    if ($script:InstallPythonVersion) {
        $requested_python_version = Get-PythonMajorMinor $script:InstallPythonVersion
        if ($requested_python_version -ne $target_python_version) {
            Write-Log "快照重建模式将忽略 -InstallPythonVersion $requested_python_version, 使用快照中的 Python $target_python_version" -Level WARNING
        }
    }
    $script:InstallPythonVersion = $target_python_version
    $script:SnapshotPath = $snapshot_path

    Test-InstallerGitKernelSnapshot -Snapshot $snapshot
    Write-Log "快照重建模式已启用: $snapshot_path"
    Write-Log "快照平台和架构已匹配: $current_platform/$current_arch"
    Write-Log "将按快照要求安装 Python $target_python_version"
}

function Initialize-SnapshotRestoreTarget {
    if (-not $script:RestoreFromSnapshot) { return }
    $core_path = Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX
    if (Test-Path -LiteralPath $core_path -PathType Leaf) {
        Stop-SnapshotRestore "快照恢复目标路径存在同名文件, 无法重建环境: $core_path"
    }
    if (!(Test-Path -LiteralPath $core_path -PathType Container)) {
        New-Item -ItemType Directory -Path $core_path -Force > $null
        Write-Log "已为快照恢复创建内核根目录: $core_path"
    }
    if (-not $script:SnapshotRequiresGitKernel) { return }
    if (Test-Path -LiteralPath (Join-NormalizedPath $core_path ".git") -PathType Container) { return }
    if (Test-DirectoryEmpty -Path $core_path) { return }
    Stop-SnapshotRestore "快照恢复目标路径已存在且不是空目录或 Git 仓库, 为避免覆盖本地数据已终止: $core_path"
}

# 安装 Python
function Install-Python {
    if ($script:InstallPythonVersion) {
        $py_ver = $script:InstallPythonVersion
    }
    else {
        $py_ver = "3.11"
    }
    if ($script:RestoreFromSnapshot) {
        Remove-ManagedPythonIfVersionMismatch -ExpectedVersion $py_ver
    }
    $platform = Get-CurrentPlatform
    $arch = Get-CurrentArchitecture
    $py_info = Get-PythonDownloadUrl -Version $py_ver -Platform $platform -Arch $arch
    if ($py_info) {
        $zip_name = $py_info.Name
        $urls = $py_info.Url
    } else {
        Write-Log "不支持当前的平台安装: ($platform, $arch)" -Level ERROR
        if ((-not $script:BuildMode) -and (-not $script:NoPause)) { Read-Host | Out-Null }
        exit 1
    }
    $python_cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($python_cmd) {
        $python_path_prefix = Join-NormalizedPath $script:InstallPath "python"
        $python_extra_path_prefix = Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX "python"
        $python_cmd = Get-NormalizedFilePath $python_cmd.Path
        if (($python_cmd) -and (($python_cmd.ToString().StartsWith($python_path_prefix, [System.StringComparison]::OrdinalIgnoreCase)) -or ($python_cmd.ToString().StartsWith($python_extra_path_prefix, [System.StringComparison]::OrdinalIgnoreCase)))) {
            Write-Log "Python 已安装"
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
        elseif ($arch -eq "aarch64") {
            $urls = @(
                "https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/git/windows/aarch64/portable_git-2.53.0-aarch64.zip",
                "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/git/windows/aarch64/portable_git-2.53.0-aarch64.zip"
            )
        }
        else {
            Write-Log "不支持当前的平台安装: ($platform, $arch)" -Level ERROR
            if ((-not $script:BuildMode) -and (-not $script:NoPause)) { Read-Host | Out-Null }
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
            if (Get-Command pacman -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "pacman" -Arguments $("-S", "git", "--noconfirm"); return }
            if (Get-Command zypper -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "zypper" -Arguments $("install", "git", "-y"); return }
            if (Get-Command nix-env -ErrorAction SilentlyContinue) { Invoke-SmartCommand -Command "nix-channel" -Arguments $("--update"); Invoke-SmartCommand -Command "nix-env" -Arguments $("-iA", "git"); return }
            Write-Log "无可用的 Python 包管理器安装 Git, 终止安装进程, 请手动安装 Git" -Level ERROR
            if ((-not $script:BuildMode) -and (-not $script:NoPause)) { Read-Host | Out-Null }
            exit 1
        }
        catch {
            Write-Log "安装 Git 失败, 终止安装进程, 可尝试重新运行 SD Trainer Script Installer 重试失败的安装" -Level ERROR
            if ((-not $script:BuildMode) -and (-not $script:NoPause)) { Read-Host | Out-Null }
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
            Write-Log "无可用的 Python 包管理器安装 Git, 终止安装进程, 请手动安装 Git" -Level ERROR
            if ((-not $script:BuildMode) -and (-not $script:NoPause)) { Read-Host | Out-Null }
            exit 1
        }
        catch {
            Write-Log "安装 Git 失败, 终止安装进程, 可尝试重新运行 SD Trainer Script Installer 重试失败的安装" -Level ERROR
            if ((-not $script:BuildMode) -and (-not $script:NoPause)) { Read-Host | Out-Null }
            exit 1
        }
    }
}


# 自动快照开关状态
function Test-SnapshotDisabled {
    if ((Test-Path (Join-NormalizedPath $script:InstallPath "disable_snapshot.txt")) -or ($script:DisableSnapshot)) {
        return $true
    }
    return $false
}


# 保存安装结果快照
function Save-InstallResultSnapshot {
    param (
        [Parameter(Mandatory = $true)][string]$CliName,
        [Parameter(Mandatory = $true)][string]$PathArgument,
        [Parameter(Mandatory = $true)][string]$WebUIPath
    )

    if (Test-SnapshotDisabled) {
        Write-Log "检测到 disable_snapshot.txt 配置文件 / -DisableSnapshot 命令行参数, 已跳过安装结果自动快照"
        return
    }

    if (!(Test-Path -LiteralPath $WebUIPath)) {
        Write-Log "快照目标路径不存在, 已跳过安装结果自动快照: $WebUIPath" -Level WARNING
        return
    }

    Write-Log "保存安装结果快照中"
    $core_cli_command = @("python", "-m", "sd_webui_all_in_one", $CliName, "snapshot", $PathArgument, $WebUIPath)
    & python -m sd_webui_all_in_one $CliName snapshot $PathArgument $WebUIPath
    $exit_code = Get-NativeCommandExitCode -Success $?
    if ($exit_code -ne 0) {
        $command_line = Format-CoreCliCommandForLog -CommandPrefix $core_cli_command -Arguments @()
        Write-Log "安装结果自动快照保存失败, 退出码: $exit_code" -Level WARNING
        Write-Log "失败命令: $command_line" -Level WARNING
        return
    }
    Write-Log "安装结果快照保存完成"
}

# 安装
function Invoke-Installation {
    New-Item -ItemType Directory -Path $script:InstallPath -Force > $null
    New-Item -ItemType Directory -Path $env:CACHE_HOME -Force > $null
    Write-FileWithStreamWriter -Path (Join-NormalizedPath $env:CACHE_HOME "uv.toml") -Value "" -Encoding UTF8
    Write-FileWithStreamWriter -Path (Join-NormalizedPath $env:CACHE_HOME "pip.ini") -Value "" -Encoding UTF8

    Resolve-SnapshotRebuildConfig

    Write-Log "检测是否安装 Python"
    Install-Python

    Write-Log "检测是否安装 Git"
    Install-Git

    Initialize-SnapshotRestoreTarget

    Update-SDWebUiAllInOne
    $operation_label = "安装"
    if ($script:RestoreFromSnapshot) {
        $launch_params = Get-RestoreCoreArgs
        $snapshot_path = Get-NormalizedFilePath $script:SnapshotPath
        $core_path = Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX
        $core_cli_command = @("python", "-m", "sd_webui_all_in_one", $script:SnapshotRestoreCliName, "restore", $snapshot_path, $script:SnapshotRestorePathArgument, $core_path)
        & python -m sd_webui_all_in_one $script:SnapshotRestoreCliName restore $snapshot_path $script:SnapshotRestorePathArgument $core_path $launch_params
        $operation_label = "恢复"
    } else {
        $launch_params = Get-LaunchCoreArgs
        $core_cli_command = @("python", "-m", "sd_webui_all_in_one", "sd-scripts", "install")
        & python -m sd_webui_all_in_one sd-scripts install $launch_params
    }
    $exit_code = Get-NativeCommandExitCode -Success $?
    if ($exit_code -ne 0) {
        Write-CoreCliFailureCommand -CommandPrefix $core_cli_command -Arguments $launch_params -ExitCode $exit_code
        Write-Log "运行 SD WebUI All In One ${operation_label} SD Trainer Script 时发生了错误, 终止 SD Trainer Script ${operation_label}进程, 可尝试重新运行 SD Trainer Script Installer 重试失败的操作" -Level ERROR
        if ((-not $script:BuildMode) -and (-not $script:NoPause)) { Read-Host | Out-Null }
        exit 1
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
    [switch]`$Help,
    [string]`$CorePrefix,
    [switch]`$DisableUpdate,
    [switch]`$BuildMode,
    [switch]`$DisableProxy,
    [string]`$UseCustomProxy,
    [switch]`$DisablePyPIMirror,
    [switch]`$DisableAutoMirror,
    [switch]`$DisableHuggingFaceMirror,
    [string]`$UseCustomHuggingFaceMirror,
    [switch]`$DisableGithubMirror,
    [string]`$UseCustomGithubMirror,
    [switch]`$DisableUV,
    [switch]`$DisableCUDAMalloc,
    [switch]`$DisableModelMirror,
    [switch]`$DisableHotpatcher,
    [switch]`$DisableSnapshot,
    [int]`$HotpatcherPort,
    [switch]`$HotpatcherPortProvided,
    [switch]`$EnableHotpatcherRuntime,
    [switch]`$DisableEnvCheck,
    [switch]`$NoPause
)
# SD Trainer Script Installer 版本和检查更新间隔
`$script:SD_TRAINER_SCRIPT_INSTALLER_VERSION = $script:SD_TRAINER_SCRIPT_INSTALLER_VERSION
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
    `$env:SD_SCRIPTS_ROOT = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX
    `$env:SD_TRAINER_SCRIPT_INSTALLER_ROOT = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX
    `$env:SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH = `$PSScriptRoot
    `$env:SD_WEBUI_ALL_IN_ONE_LOGGER_NAME = `"SD Trainer Script Installer`"
    `$env:SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL = 20
    `$env:SD_WEBUI_ALL_IN_ONE_LOGGER_COLOR = 1
    `$env:SD_WEBUI_ALL_IN_ONE_RETRY_TIMES = 3
    `$env:SD_WEBUI_ALL_IN_ONE_EXTRA_PYPI_MIRROR = 0
    `$env:SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH = 1
    `$env:SD_WEBUI_ALL_IN_ONE_SET_CONFIG = 1
    `$env:SD_WEBUI_ALL_IN_ONE_RAISE_WEBUI_RUNTIME_ERROR = 0
    `$env:SD_WEBUI_ALL_IN_ONE_RAISE_CHECK_ENV_ERROR_ON_LAUNCH = 0

    New-Item -ItemType Directory -Path `$env:CACHE_HOME -Force > `$null
    Write-FileWithStreamWriter -Path (Join-NormalizedPath `$env:CACHE_HOME `"uv.toml`") -Value `"`" -Encoding UTF8
    Write-FileWithStreamWriter -Path (Join-NormalizedPath `$env:CACHE_HOME `"pip.ini`") -Value `"`" -Encoding UTF8
}


# 日志输出
function Write-Log {
    [CmdletBinding()]
    param(
        [string]`$Message,
        [ValidateSet(`"DEBUG`", `"INFO`", `"WARNING`", `"ERROR`", `"CRITICAL`")]
        [string]`$Level = `"INFO`",
        [string]`$Name = `"SD Trainer Script Installer`"
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
        [Parameter(Mandatory = `$true)][AllowEmptyString()][string]`$Value,
        [Parameter(Mandatory = `$true)][string]`$Path,
        [Parameter(Mandatory = `$false)][ValidateSet(`"GBK`", `"UTF8`", `"UTF8BOM`")][string]`$Encoding = `"UTF8`"
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


function Get-TrimmedTextFile {
    param (
        [Parameter(Mandatory = `$true)][string]`$Path,
        [string]`$Encoding
    )
    if (!(Test-Path `$Path)) {
        return `$null
    }
    if ([string]::IsNullOrWhiteSpace(`$Encoding)) {
        `$content = Get-Content -Path `$Path -Raw
    } else {
        `$content = Get-Content -Path `$Path -Raw -Encoding `$Encoding
    }
    if ([string]::IsNullOrWhiteSpace(`$content)) {
        return `$null
    }
    return `$content.Trim()
}


function Resolve-CorePrefix {
    param (
        [Parameter(Mandatory = `$true)][string]`$BasePath,
        [Parameter(Mandatory = `$true)][string[]]`$PrefixList,
        [AllowNull()][string]`$ConfiguredPrefix
    )
    `$target_prefix = `$null
    if (-not [string]::IsNullOrWhiteSpace(`$ConfiguredPrefix)) {
        `$origin_core_prefix = `$ConfiguredPrefix.TrimEnd('\', '/')
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix)) {
            `$from_uri = New-Object System.Uri(`$BasePath.Replace('\', '/') + '/')
            `$to_uri = New-Object System.Uri(`$origin_core_prefix.Replace('\', '/'))
            `$target_prefix = `$from_uri.MakeRelativeUri(`$to_uri).ToString().Trim('/')
        } else {
            `$target_prefix = `$origin_core_prefix
        }
    }
    if ([string]::IsNullOrWhiteSpace(`$target_prefix)) {
        foreach (`$i in `$PrefixList) {
            `$found_dir = Get-ChildItem -Path `$BasePath -Directory -Filter `$i -ErrorAction SilentlyContinue | Select-Object -First 1
            if (`$found_dir) {
                `$target_prefix = `$found_dir.Name
                break
            }
        }
    }
    if ([string]::IsNullOrWhiteSpace(`$target_prefix)) {
        `$target_prefix = 'core'
    }
    return `$target_prefix
}


# 格式化命令行参数日志
function Format-CommandLineArgumentForLog {
    param ([AllowNull()][object]`$Argument)
    if (`$null -eq `$Argument) {
        return `"''`"
    }
    `$value = [string]`$Argument
    if (`$value.Length -eq 0) {
        return `"''`"
    }
    if (`$value -match '[\s''`"]') {
        return ([string][char]39) + (`$value -replace ([string][char]39), ([string][char]39 + [string][char]39)) + ([string][char]39)
    }
    return `$value
}


# 格式化 SD WebUI All In One CLI 命令日志
function Format-CoreCliCommandForLog {
    param (
        [Parameter(Mandatory = `$true)][object]`$CommandPrefix,
        [object]`$Arguments
    )
    `$parts = New-Object System.Collections.ArrayList
    foreach (`$item in `$CommandPrefix) {
        `$parts.Add((Format-CommandLineArgumentForLog `$item)) | Out-Null
    }
    if (`$null -ne `$Arguments) {
        foreach (`$item in `$Arguments) {
            `$parts.Add((Format-CommandLineArgumentForLog `$item)) | Out-Null
        }
    }
    return (`$parts -join ' ')
}


# 输出 SD WebUI All In One CLI 失败命令
function Write-CoreCliFailureCommand {
    param (
        [Parameter(Mandatory = `$true)][object]`$CommandPrefix,
        [object]`$Arguments,
        [Parameter(Mandatory = `$true)][int]`$ExitCode
    )
    Write-Log `"SD WebUI All In One CLI 执行失败, 退出码: `$ExitCode`" -Level ERROR
    `$command_line = Format-CoreCliCommandForLog -CommandPrefix `$CommandPrefix -Arguments `$Arguments
    Write-Log `"失败命令: `$command_line`" -Level ERROR
}


# 获取原生命令退出码
function Get-NativeCommandExitCode {
    param ([bool]`$Success)
    if (`$Success) {
        return 0
    }
    if ((`$null -ne `$global:LASTEXITCODE) -and (`$global:LASTEXITCODE -ne 0)) {
        return [int]`$global:LASTEXITCODE
    }
    return 1
}


# 按退出码退出管理脚本
function Exit-ManagerScript {
    param ([int]`$ExitCode)
    if ((-not `$script:BuildMode) -and (-not `$script:NoPause)) { Read-Host | Out-Null }
    exit `$ExitCode
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
    if (!(`$?)) { & python -m pip install -U `"sd-webui-all-in-one>=`$script:CORE_MINIMUM_VER`" }
    if (!(`$?)) {
        Write-Log `"SD WebUI All In One 内核更新失败, Installer 部分功能将无法使用`" -Level ERROR
        if ((-not `$script:BuildMode) -and (-not `$script:NoPause)) { Read-Host | Out-Null }
        exit 1
    }
    Write-Log `"SD WebUI All In One 内核更新成功`"
}


# SD Trainer Script Installer 更新检测
function Update-Installer {
    [CmdletBinding()]
    param([switch]`$DisableRestart)
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/sd_trainer_script_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/sd_trainer_script_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path `$env:CACHE_HOME -Force | Out-Null

    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_update.txt`")) -or (`$script:DisableUpdate)) {
        Write-Log `"检测到 disable_update.txt 更新配置文件 / -DisableUpdate 命令行参数, 已禁用 SD Trainer Script Installer 的自动检查 Installer 更新功能`"
        return
    }

    if (`$script:BuildMode) {
        Write-Log `"SD Trainer Script Installer 构建模式已启用, 跳过 SD Trainer Script Installer 更新检查`"
        return
    }

    # 获取更新时间间隔
    try {
        `$last_update_time_text = Get-TrimmedTextFile (Join-NormalizedPath `$PSScriptRoot `"update_time.txt`") -Encoding UTF8 2> `$null
        if ([string]::IsNullOrWhiteSpace(`$last_update_time_text)) { throw `"Missing update time`" }
        `$last_update_time = Get-Date `$last_update_time_text -Format `"yyyy-MM-dd HH:mm:ss`"
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

    foreach (`$url in `$urls) {
        Write-Log `"检查 SD Trainer Script Installer 更新中`"
        try {
            `$web_request_params = @{
                Uri = `$url
                UseBasicParsing = `$true
                OutFile = (Join-NormalizedPath `$env:CACHE_HOME `"sd_trainer_script_installer.ps1`")
                TimeoutSec = 15
                ErrorAction = `"Stop`"
            }
            Invoke-WebRequest @web_request_params
            `$latest_version = [int]`$(
                Get-Content (Join-NormalizedPath `$env:CACHE_HOME `"sd_trainer_script_installer.ps1`") -Encoding UTF8 |
                Select-String -Pattern `"SD_TRAINER_SCRIPT_INSTALLER_VERSION`" |
                ForEach-Object { `$_.ToString() }
            )[0].Split(`"=`")[1].Trim()
            break
        }
        catch {
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Write-Log `"重试检查 SD Trainer Script Installer 更新中`" -Level WARNING
            } else {
                Write-Log `"检查 SD Trainer Script Installer 更新失败`" -Level ERROR
                return
            }
        }
    }

    if (`$latest_version -le `$script:SD_TRAINER_SCRIPT_INSTALLER_VERSION) {
        Write-Log `"SD Trainer Script Installer 已是最新版本`"
        return
    }

    Write-Log `"调用 SD Trainer Script Installer 进行更新中`"
    & (Join-NormalizedPath `$env:CACHE_HOME `"sd_trainer_script_installer.ps1`") -InstallPath `$PSScriptRoot -UseUpdateMode

    if (`$DisableRestart) {
        Write-Log `"更新结束, 已禁用自动重新启动`"
        return
    }

    `$raw_params = `$script:LaunchCommandLine -replace '^.*?\.dll\s*[`"'']?\s*', '' -replace '^.*\.ps1\s*[`"'']?\s*', ''
    Write-Log `"更新结束, 重新启动 SD Trainer Script Installer 管理脚本中, 使用的命令行参数: `$raw_params`"
    try { Invoke-Expression `"& ```"`$script:OriginalScriptPath```" `$raw_params`" -ErrorAction Stop; exit `$LASTEXITCODE }
    catch { exit 1 }
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


# 检测 Windows 长路径支持是否启用
function Test-WindowsLongPathsEnabled {
    if ((Get-CurrentPlatform) -ne `"windows`") {
        return `$true
    }

    try {
        `$reg = Get-ItemProperty -Path `"HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem`" -Name `"LongPathsEnabled`" -ErrorAction Stop
        `$property = `$reg.PSObject.Properties[`"LongPathsEnabled`"]
        if (`$null -eq `$property) {
            Write-Log `"Windows 长路径支持注册表值缺失`" -Level WARNING
            return `$false
        }
        `$enabled = ([int]`$property.Value -eq 1)
        if (`$enabled) {
            Write-Log `"Windows 长路径支持已启用`"
        } else {
            Write-Log `"Windows 长路径支持未启用`" -Level WARNING
        }
        return `$enabled
    } catch {
        Write-Log `"读取 Windows 长路径支持状态失败: `$(`$_.Exception.Message)`" -Level WARNING
        return `$false
    }
}


# 获取当前 PowerShell 可执行文件
function Get-CurrentPowerShellExecutable {
    try {
        `$process = Get-Process -Id `$PID -ErrorAction Stop
        `$path = [string]`$process.Path
        if ((-not [string]::IsNullOrWhiteSpace(`$path)) -and (Test-Path -LiteralPath `$path -PathType Leaf)) {
            return `$path
        }
    } catch {
        Write-Log `"当前 PowerShell 可执行文件查找失败: `$(`$_.Exception.Message)`" -Level WARNING
    }

    `$pwsh = Get-Command pwsh -ErrorAction SilentlyContinue
    if (`$pwsh) {
        return `$pwsh.Source
    }
    `$powershell = Get-Command powershell -ErrorAction SilentlyContinue
    if (`$powershell) {
        return `$powershell.Source
    }
    return `$null
}


function Quote-ProcessArgument {
    param ([AllowNull()][string]`$Argument)
    if (`$null -eq `$Argument) {
        return ([string][char]34 + [string][char]34)
    }
    if (`$Argument.Length -eq 0) {
        return ([string][char]34 + [string][char]34)
    }
    `$quote = [string][char]34
    `$needs_quote = (`$Argument -match '\s') -or `$Argument.Contains(`$quote)
    if (-not `$needs_quote) {
        return `$Argument
    }
    `$escaped = `$Argument -replace `$quote, ([string][char]96 + `$quote)
    return (`$quote + `$escaped + `$quote)
}


function Join-ProcessArguments {
    param ([AllowNull()][string[]]`$Arguments)
    if (`$null -eq `$Arguments) {
        return [string]::Empty
    }
    return ((`$Arguments | ForEach-Object { Quote-ProcessArgument `$_ }) -join ' ')
}


# 以管理员权限启用 Windows 长路径支持
function Enable-WindowsLongPathsElevated {
    `$id = [guid]::NewGuid().ToString(`"N`")
    `$temp_dir = [System.IO.Path]::GetTempPath()
    `$worker_path = Join-Path `$temp_dir `"sd-webui-all-in-one-enable-long-paths-`$id.ps1`"
    `$status_path = Join-Path `$temp_dir `"sd-webui-all-in-one-enable-long-paths-`$id.status`"
    `$worker_script = @'
param(
    [Parameter(Mandatory=`$true)][string]`$StatusPath
)
`$ErrorActionPreference = 'Stop'
try {
    New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force | Out-Null
    Set-Content -LiteralPath `$StatusPath -Encoding UTF8 -Value 'SUCCESS'
    exit 0
} catch {
    try { Set-Content -LiteralPath `$StatusPath -Encoding UTF8 -Value ('FAILURE: ' + `$_.Exception.Message) } catch {}
    exit 1
}
'@

    try {
        Set-Content -LiteralPath `$worker_path -Encoding UTF8 -Value `$worker_script
        `$command = Get-CurrentPowerShellExecutable
        if ([string]::IsNullOrWhiteSpace(`$command)) {
            throw `"未找到 PowerShell 可执行文件`"
        }
        `$argument_line = Join-ProcessArguments @(`"-NoLogo`", `"-NoProfile`", `"-ExecutionPolicy`", `"Bypass`", `"-File`", `$worker_path, `"-StatusPath`", `$status_path)
        Write-Log `"正在请求管理员权限以启用 Windows 长路径支持`"
        `$process = Start-Process -FilePath `$command -ArgumentList `$argument_line -Verb RunAs -Wait -PassThru -ErrorAction Stop
        `$exit_code = if (`$null -ne `$process) { [int]`$process.ExitCode } else { -1 }
        `$status = `$null
        if (Test-Path -LiteralPath `$status_path -PathType Leaf) {
            `$status = Get-Content -LiteralPath `$status_path -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        }
        if (Test-WindowsLongPathsEnabled) {
            Write-Log `"Windows 长路径支持已成功启用`"
            return [PSCustomObject]@{ Success = `$true; Canceled = `$false; Message = `"Windows 长路径支持已启用。`"; ExitCode = `$exit_code }
        }
        `$message = if (-not [string]::IsNullOrWhiteSpace(`$status)) { `$status.Trim() } else { `"管理员进程未能启用 Windows 长路径支持。退出代码: `$exit_code`" }
        Write-Log `"Windows 长路径支持启用失败: `$message`" -Level WARNING
        return [PSCustomObject]@{ Success = `$false; Canceled = `$false; Message = `$message; ExitCode = `$exit_code }
    } catch {
        `$exception = `$_.Exception
        `$is_canceled = `$false
        if (`$exception -is [System.ComponentModel.Win32Exception] -and `$exception.NativeErrorCode -eq 1223) {
            `$is_canceled = `$true
        }
        if (`$exception.Message -match `"cancel|取消`") {
            `$is_canceled = `$true
        }
        if (`$is_canceled) {
            Write-Log `"用户取消了启用 Windows 长路径支持的管理员权限请求`" -Level WARNING
            return [PSCustomObject]@{ Success = `$false; Canceled = `$true; Message = `"用户取消了管理员权限请求。`"; ExitCode = -1 }
        }
        Write-Log `"启动管理员进程启用 Windows 长路径支持失败: `$(`$exception.Message)`" -Level WARNING
        return [PSCustomObject]@{ Success = `$false; Canceled = `$false; Message = `$exception.Message; ExitCode = -1 }
    } finally {
        Remove-Item -LiteralPath `$worker_path -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath `$status_path -Force -ErrorAction SilentlyContinue
    }
}


# 启动时检查 Windows 长路径支持
function Invoke-WindowsLongPathsStartupCheck {
    if ((Get-CurrentPlatform) -ne `"windows`") {
        return
    }
    if (`$script:BuildMode) {
        Write-Log `"构建模式已启用, 跳过 Windows 长路径支持弹窗检查`"
        return
    }
    if (Test-WindowsLongPathsEnabled) {
        return
    }

    Write-Log `"检测到 Windows 长路径支持未启用, 建议启用以避免路径过长导致安装或启动失败`" -Level WARNING
    try {
        Add-Type -AssemblyName PresentationFramework
        `$msg_title = `"启用 Windows 长路径支持`"
        `$msg_text = `"检测到当前系统尚未启用 Windows 长路径支持。``n``nAI WebUI / 训练工具的依赖、扩展、模型缓存目录可能很深，未启用时可能导致下载、解压、安装或启动失败。``n``n是否现在以管理员权限启用 Windows 长路径支持？`"
        `$result = [System.Windows.MessageBox]::Show(`$msg_text, `$msg_title, [System.Windows.MessageBoxButton]::YesNo, [System.Windows.MessageBoxImage]::Warning)
        if (`$result -ne [System.Windows.MessageBoxResult]::Yes) {
            Write-Log `"已跳过启用 Windows 长路径支持。之后可以运行 configure_env.bat, 或手动执行 New-ItemProperty 命令启用 LongPathsEnabled`" -Level WARNING
            return
        }

        `$enable_result = Enable-WindowsLongPathsElevated
        if (`$enable_result.Success) {
            [System.Windows.MessageBox]::Show(`"Windows 长路径支持已启用。``n``n部分程序可能需要重新启动后才能完全识别该系统设置。`", `"启用完成`", [System.Windows.MessageBoxButton]::OK, [System.Windows.MessageBoxImage]::Information) | Out-Null
            return
        }

        if (`$enable_result.Canceled) {
            Write-Log `"管理员权限请求已取消, Windows 长路径支持未启用。之后可以运行 configure_env.bat 或手动执行 New-ItemProperty 命令启用 LongPathsEnabled`" -Level WARNING
            [System.Windows.MessageBox]::Show(`"未获得管理员权限，Windows 长路径支持尚未启用。``n``n启动脚本会继续运行；之后可以运行 configure_env.bat，或手动执行注册表命令启用。`", `"未启用长路径支持`", [System.Windows.MessageBoxButton]::OK, [System.Windows.MessageBoxImage]::Warning) | Out-Null
            return
        }

        Write-Log `"启用 Windows 长路径支持失败: `$(`$enable_result.Message)`" -Level WARNING
        [System.Windows.MessageBox]::Show(`"启用 Windows 长路径支持失败。``n``n`$(`$enable_result.Message)``n``n启动脚本会继续运行；之后可以运行 configure_env.bat，或手动执行注册表命令启用。`", `"启用失败`", [System.Windows.MessageBoxButton]::OK, [System.Windows.MessageBoxImage]::Warning) | Out-Null
    } catch {
        Write-Log `"Windows 长路径支持弹窗检查失败: `$(`$_.Exception.Message)`" -Level WARNING
    }
}


# 获取当前架构
function Get-CurrentArchitecture {
    if (`$PSVersionTable.PSVersion.Major -ge 6) {
        `$arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLower()
    }
    else {
        if ([Environment]::Is64BitOperatingSystem) {
            if (`$env:PROCESSOR_ARCHITEW6432) {
                `$arch = `$env:PROCESSOR_ARCHITEW6432.ToLower()
            }
            else {
                `$arch = `$env:PROCESSOR_ARCHITECTURE.ToLower()
            }
        }
        else {
            `$arch = `"x86`"
        }
    }
    switch (`$arch) {
        `"amd64`"  { return `"amd64`" }
        `"x64`"    { return `"amd64`" }
        `"arm64`"  { return `"aarch64`" }
        `"x86_64`" { return `"amd64`" }
        `"x86`"    { return `"x86`" }
        `"i386`"   { return `"x86`" }
        `"i686`"   { return `"x86`" }
        default  { return `$arch }
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
    `$ver = `$([string]`$script:SD_TRAINER_SCRIPT_INSTALLER_VERSION).ToCharArray()
    `$major = (`$ver[0..(`$ver.Length - 3)])
    `$minor = `$ver[-2]
    `$micro = `$ver[-1]
    Write-Log `"SD Trainer Script Installer 版本: v`${major}.`${minor}.`${micro}`"
}


# 获取帮助信息
function Get-HelpMessage {
    if (!(`$script:Help)) { return }
    `$script = Get-Command `$script:OriginalScriptPath
    `$common = [System.Management.Automation.Internal.CommonParameters].GetProperties().Name
    `$display_params = `$script.Parameters.Values | Where-Object { `$_.Name -notin `$common } | ForEach-Object {
        `$p_name = `$_.Name
        `$p_type = `$_.ParameterType.Name
        if (`$_.ParameterType -eq [switch]) {
            `$format = `"-`$p_name`"
        }
        else {
            # 处理数组类型的显示逻辑
            # 如果是数组, PowerShell 习惯在类型名后加 []
            if (`$_.ParameterType.IsArray) {
                # 移除原类型名中的 [] 或 System. 前缀, 统一格式
                `$clean_type = `"`$(`$_.ParameterType.GetElementType().Name)[]`"
            } else {
                `$clean_type = `$p_type
            }
            `$format = `"-`$p_name <`$clean_type>`"
        }
        `$help_msg = `$_.Attributes.HelpMessage
        [PSCustomObject]@{
            Name = `$format
            HelpMessage = `$help_msg
        }
    }
    `$usage = @`"
使用:
    `$((Get-Process -Id `$PID).Path) `${script:OriginalScriptPath} `$(foreach (`$i in `$display_params.Name) { `"[`$i]`" })
`"@
    `$param_info = @`"
参数:
`$(
    foreach (`$i in `$display_params) {
        `$text = `"    `$(`$i.Name)`"
        if (`$i.HelpMessage) {
            `$indented_help = (`$i.HelpMessage -split `"```r?```n`" | ForEach-Object { `"        `$_`" }) -join `"```n`"
            `$text += `"```n`$indented_help`"
        }
        `$text + `"```n```n`"
    }
)
`"@
    `$docs_url = `"更多的帮助信息请阅读 SD Trainer Script Installer 使用文档: https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/`"
    Write-Host `$(`$usage + `"```n```n`" + `$param_info + `"```n`" + `$docs_url)
    exit 0
}


# 设置 Installer 内核路径前缀
function Set-CorePrefix {
    `$prefix_list = @(`"core`", `"sd-scripts*`")
    `$core_prefix_file = Join-NormalizedPath `$PSScriptRoot `"core_prefix.txt`"
    `$origin_core_prefix = if (`$script:CorePrefix) {
        `$script:CorePrefix
    } else {
        Get-TrimmedTextFile `$core_prefix_file -Encoding UTF8
    }
    if (-not [string]::IsNullOrWhiteSpace(`$origin_core_prefix)) {
        Write-Log `"检测到 core_prefix.txt 配置文件 / -CorePrefix 命令行参数, 使用自定义 Installer 内核路径前缀`"
        `$normalized_core_prefix = `$origin_core_prefix.TrimEnd('\', '/')
        if ([System.IO.Path]::IsPathRooted(`$normalized_core_prefix)) {
            `$from_uri = New-Object System.Uri(`$PSScriptRoot.Replace('\', '/') + '/')
            `$to_uri = New-Object System.Uri(`$normalized_core_prefix.Replace('\', '/'))
            `$target_prefix = `$from_uri.MakeRelativeUri(`$to_uri).ToString().Trim('/')
            Write-Log `"转换绝对路径为 Installer 内核路径前缀: `$origin_core_prefix -> `$target_prefix`"
        }
    }
    `$target_prefix = Resolve-CorePrefix -BasePath `$PSScriptRoot -PrefixList `$prefix_list -ConfiguredPrefix `$origin_core_prefix
    `$env:CORE_PREFIX = `$target_prefix
    `$full_core_path = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX
    Write-Log `"当前 Installer 内核路径前缀: `$env:CORE_PREFIX`"
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
            `$proxy_value = Get-TrimmedTextFile (Join-NormalizedPath `$PSScriptRoot `"proxy.txt`") -Encoding UTF8
        }
        if (-not [string]::IsNullOrWhiteSpace(`$proxy_value)) {
            `$env:HTTP_PROXY = `$proxy_value
            `$env:HTTPS_PROXY = `$proxy_value
            Write-Log `"检测到本地存在 proxy.txt 代理配置文件 / -UseCustomProxy 命令行参数, 已读取代理配置文件并设置代理`"
            return
        }
    }
    if (`$Legacy) {
        `$proxy_value = & python -m sd_webui_all_in_one self-manager get proxy
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


# 设置 CLI 自动选择下载镜像源状态
function Set-AutoMirror {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]`$ArrayList)

    if ((`$script:DisableAutoMirror) -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_auto_mirror.txt`"))) {
        if (-not `$ArrayList.Contains(`"--no-auto-mirror`")) {
            `$ArrayList.Add(`"--no-auto-mirror`") | Out-Null
        }
        if (-not `$script:AutoMirrorStatusLogged) {
            Write-Log `"检测到 disable_auto_mirror.txt 配置文件 / -DisableAutoMirror 命令行参数, 已禁用 CLI 自动选择下载镜像源, 将遵守手动镜像源设置`"
            `$script:AutoMirrorStatusLogged = `$true
        }
        return `$true
    }

    if (-not `$script:AutoMirrorStatusLogged) {
        Write-Log `"CLI 自动选择下载镜像源已启用, 将由 Python CLI 根据网络检测结果强制覆盖镜像源相关参数`"
        `$script:AutoMirrorStatusLogged = `$true
    }
    return `$false
}


# 配置 PyPI 软件包镜像源
function Set-PyPIMirror {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]`$ArrayList)
    if (!(Set-AutoMirror `$ArrayList)) { return }
    if (`$script:DisablePyPIMirror -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_pypi_mirror.txt`"))) {
        Write-Log `"检测到 disable_pypi_mirror.txt 配置文件 / -DisablePyPIMirror 命令行参数, 已将 PyPI 源切换至官方源`"
        `$ArrayList.Add(`"--no-pypi-mirror`") | Out-Null
        return
    }
    Write-Log `"使用 PyPI 软件包镜像源`"
}


# 设置模型下载来源
function Set-ModelMirror {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]`$ArrayList)
    if (!(Set-AutoMirror `$ArrayList)) { return }
    `$ArrayList.Add(`"--source`") | Out-Null
    if ((!(Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_model_mirror.txt`"))) -and (!(`$script:DisableModelMirror))) {
        Write-Log `"使用 ModelScope 模型下载来源`"
        `$ArrayList.Add(`"modelscope`") | Out-Null
    } else {
        Write-Log `"检测到 disable_model_mirror.txt 配置文件 / -DisableModelMirror 命令行参数, 已将模型下载来源切换至 Hugging Face 源`"
        `$ArrayList.Add(`"huggingface`") | Out-Null
    }
}


# Hugging Face 镜像源
function Set-HuggingFaceMirror {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]`$ArrayList)
    if (!(Set-AutoMirror `$ArrayList)) { return }
    if (`$script:DisableHuggingFaceMirror -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_hf_mirror.txt`"))) {
        Write-Log `"检测到本地存在 disable_hf_mirror.txt 镜像源配置文件 / -DisableHuggingFaceMirror 命令行参数, 禁用自动设置 Hugging Face 镜像源`"
        `$ArrayList.Add(`"--no-hf-mirror`") | Out-Null
        return
    }
    if (`$script:UseCustomHuggingFaceMirror -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"hf_mirror.txt`"))) {
        if (`$script:UseCustomHuggingFaceMirror) {
            `$hf_mirror_value = `$script:UseCustomHuggingFaceMirror
        } else {
            `$hf_mirror_value = Get-TrimmedTextFile (Join-NormalizedPath `$PSScriptRoot `"hf_mirror.txt`") -Encoding UTF8
        }
        if (-not [string]::IsNullOrWhiteSpace(`$hf_mirror_value)) {
            `$ArrayList.Add(`"--custom-hf-mirror`") | Out-Null
            `$ArrayList.Add(`$hf_mirror_value) | Out-Null
            Write-Log `"检测到本地存在 hf_mirror.txt 配置文件 / -UseCustomHuggingFaceMirror 命令行参数, 已读取该配置并设置 Hugging Face 镜像源`"
            return
        }
    }
    Write-Log `"使用默认 Hugging Face 镜像源`"
}


# 设置 GitHub 镜像源
function Set-GithubMirror {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]`$ArrayList)
    if (Test-Path (Join-NormalizedPath `$PSScriptRoot `".gitconfig`")) {
        Remove-Item -Path (Join-NormalizedPath `$PSScriptRoot `".gitconfig`") -Force -Recurse
    }
    if (!(Set-AutoMirror `$ArrayList)) { return }
    if (`$script:DisableGithubMirror -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_gh_mirror.txt`"))) {
        Write-Log `"检测到本地存在 disable_gh_mirror.txt GitHub 镜像源配置文件 / -DisableGithubMirror 命令行参数, 禁用 GitHub 镜像源`"
        `$ArrayList.Add(`"--no-github-mirror`") | Out-Null
        return
    }
    if (`$script:UseCustomGithubMirror -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"gh_mirror.txt`"))) {
        if (`$script:UseCustomGithubMirror) {
            `$github_mirror = `$script:UseCustomGithubMirror
        } else {
            `$github_mirror = Get-TrimmedTextFile (Join-NormalizedPath `$PSScriptRoot `"gh_mirror.txt`") -Encoding UTF8
        }
        if (-not [string]::IsNullOrWhiteSpace(`$github_mirror)) {
            Write-Log `"检测到本地存在 gh_mirror.txt GitHub 镜像源配置文件 / -UseCustomGithubMirror 命令行参数, 已读取 GitHub 镜像源配置文件并设置 GitHub 镜像源`"
            `$ArrayList.Add(`"--custom-github-mirror`") | Out-Null
            `$ArrayList.Add(`$github_mirror) | Out-Null
        }
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


# 创建 Windows 创建启动快捷方式
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


# 创建 Linux 创建启动快捷方式
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


# 创建 MacOS 创建启动快捷方式
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

    `$working_dir_for_shell = `$PSScriptRoot.Replace('`"', '\`"').Replace('$', '\$')
    `$pwsh_bin_for_shell = `$pwsh_bin.Replace('`"', '\`"').Replace('$', '\$')
    `$launch_script_for_shell = `$launch_script_path.Replace('`"', '\`"').Replace('$', '\$')

    `$executable_path = Join-NormalizedPath `$macos_path `"launcher`"
    `$sh_content = @`"
#!/bin/bash

osascript <<'APPLESCRIPT'
tell application `"Terminal`"
    activate
    do script `"cd \`"`$working_dir_for_shell\`" || exit 1; exec \`"`$pwsh_bin_for_shell\`" -NoExit -ExecutionPolicy Bypass -File \`"`$launch_script_for_shell\`"`"
end tell
APPLESCRIPT
`"@
    `$sh_content = `$sh_content.Replace(`"```r```n`", `"```n`").Replace(`"```r`", `"```n`")
    Write-FileWithStreamWriter -Path `$executable_path -Encoding UTF8 -Value `$sh_content
    & chmod +x `"`$executable_path`"

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
    <key>CFBundleDisplayName</key>
    <string>`${Name}</string>
    <key>CFBundleIdentifier</key>
    <string>local.sdwebuiallinone.`$(`$Name.ToLower() -replace '[^a-z0-9]', '')</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>LSBackgroundOnly</key>
    <false/>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
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


# 创建创建启动快捷方式
function New-AppShortcut {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=`$true)][string]`$Name,
        [Parameter(Mandatory=`$true)][Hashtable]`$IconMap
    )
    `$finalIconPath = Get-AppIcon -IconMap `$IconMap
    if (-not `$finalIconPath) {
        Write-Log `"图标获取失败，跳过创建创建启动快捷方式`" -Level ERROR
        return
    }
    `$platform = Get-CurrentPlatform
    switch (`$platform) {
        `"windows`" { Add-WindowsShortcut -Name `$Name -IconPath `$finalIconPath }
        `"linux`"   { Add-LinuxShortcut -Name `$Name -IconPath `$finalIconPath }
        `"macos`"   { Add-MacOSShortcut -Name `$Name -IconPath `$finalIconPath }
    }
}


# 测试 Python 和 Git 可用性
function Test-PythonAndGit {
    # Python
    `$python_cmd = Get-Command python -ErrorAction SilentlyContinue
    if (`$python_cmd) {
        `$python_cmd = Get-NormalizedFilePath `$python_cmd.Path
        `$python_path_prefix = Join-NormalizedPath `$PSScriptRoot `"python`"
        `$python_extra_path_prefix = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX `"python`"
        if (-not ((`$python_cmd) -and ((`$python_cmd.ToString().StartsWith(`$python_path_prefix, [System.StringComparison]::OrdinalIgnoreCase)) -or (`$python_cmd.ToString().StartsWith(`$python_extra_path_prefix, [System.StringComparison]::OrdinalIgnoreCase))))) {
            Write-Log `"检测到当前使用的 Python 路径为 `${python_cmd}, 但未在 `${python_path_prefix} 或 `${python_extra_path_prefix} 这两个受 SD Trainer Script Installer 管理的 Python 路径, 即当前正在使用外部的 Python 环境, 这可能会导致一些运行环境问题, 可尝试运行 launch_sd_trainer_script_installer.ps1 修复运行环境`" -Level ERROR
        }
    } else {
        Write-Log `"检测到当前环境中未安装任何 Python, 这将导致运行时发生异常, 请运行 launch_sd_trainer_script_installer.ps1 修复运行环境`" -Level ERROR
    }

    # Git
    `$git_cmd = Get-Command git -ErrorAction SilentlyContinue
    if (`$git_cmd) {
        if ((Get-CurrentPlatform) -eq `"windows`") {
            `$git_cmd = Get-NormalizedFilePath `$git_cmd.Path
            `$git_path_prefix = Join-NormalizedPath `$PSScriptRoot `"git`"
            `$git_extra_path_prefix = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX `"git`"
            if (-not ((`$git_cmd) -and ((`$git_cmd.ToString().StartsWith(`$git_path_prefix, [System.StringComparison]::OrdinalIgnoreCase)) -or (`$git_cmd.ToString().StartsWith(`$git_extra_path_prefix, [System.StringComparison]::OrdinalIgnoreCase))))) {
                Write-Log `"检测到当前使用的 Git 路径为 `${git_cmd}, 但未在 `${git_path_prefix} 或 `${git_extra_path_prefix} 这两个受 SD Trainer Script Installer 管理的 Git 路径, 即当前正在使用外部的 Git 环境, 这可能会导致一些运行环境问题, 可尝试运行 launch_sd_trainer_script_installer.ps1 修复运行环境`" -Level ERROR
            }
        }
    } else {
        Write-Log `"检测到当前环境中未安装任何 Git, 这将导致运行时发生异常, 请运行 launch_sd_trainer_script_installer.ps1 修复运行环境`" -Level ERROR
    }
}


# 检测 Microsoft Visual C++ Redistributable
function Test-MSVCPPRedistributable {
    if ((Get-CurrentPlatform) -ne `"windows`") {
        Write-Log `"非 Windows 系统，跳过 Microsoft Visual C++ Redistributable 检测`"
        return
    }

    Write-Log `"检测 Microsoft Visual C++ Redistributable 是否缺失`"

    `$vc_runtime_dll_names = @(
        `"concrt140.dll`",
        `"msvcp140.dll`",
        `"msvcp140_1.dll`",
        `"msvcp140_2.dll`",
        `"msvcp140_atomic_wait.dll`",
        `"msvcp140_codecvt_ids.dll`",
        `"vcamp140.dll`",
        `"vccorlib140.dll`",
        `"vcomp140.dll`",
        `"vcruntime140.dll`",
        `"vcruntime140_1.dll`",
        `"vcruntime140_threads.dll`"
    )

    if ([string]::IsNullOrEmpty(`$env:SYSTEMROOT)) {
        `$windows_dir = Join-NormalizedPath `"C:/`" `"Windows`"
    } else {
        `$windows_dir = `$env:SYSTEMROOT
    }

    if ([Environment]::Is64BitOperatingSystem -and (-not [Environment]::Is64BitProcess)) {
        `$vc_runtime_dir = Join-NormalizedPath `$windows_dir `"Sysnative`"
    } else {
        `$vc_runtime_dir = Join-NormalizedPath `$windows_dir `"System32`"
    }

    `$missing_vc_runtime_dll_names = @()
    foreach (`$vc_runtime_dll_name in `$vc_runtime_dll_names) {
        `$vc_runtime_dll_path = Join-NormalizedPath `$vc_runtime_dir `$vc_runtime_dll_name
        if (-not (Test-Path -LiteralPath `$vc_runtime_dll_path -PathType Leaf)) {
            `$missing_vc_runtime_dll_names += `$vc_runtime_dll_name
        }
    }

    if (`$missing_vc_runtime_dll_names.Count -eq 0) {
        Write-Log `"Microsoft Visual C++ Redistributable 未缺失`"
        return
    }

    `$missing_vc_runtime_dll_list = `$missing_vc_runtime_dll_names -join `", `"
    Write-Log `"检测到 Microsoft Visual C++ Redistributable 缺失的核心 DLL: `$missing_vc_runtime_dll_list`" -Level WARNING
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


# 设置 CUDA 内存分配器
function Set-PyTorch-CUDA-Memory-Alloc {
    if ((!(Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_set_pytorch_cuda_memory_alloc.txt`"))) -and (!(`$DisableCUDAMalloc))) {
        Write-Log `"检测是否可设置 CUDA 内存分配器`"
    } else {
        Write-Log `"检测到 disable_set_pytorch_cuda_memory_alloc.txt 配置文件 / -DisableCUDAMalloc 命令行参数, 已禁用自动设置 CUDA 内存分配器`"
        return
    }

    `$conf = `$(python -m sd_webui_all_in_one self-manager get cuda-malloc)

    if (`$conf) {
        Write-Log `"配置 CUDA 内存分配器`"
        `$Env:PYTORCH_CUDA_ALLOC_CONF = `$conf
        `$Env:PYTORCH_ALLOC_CONF = `$conf
    } else {
        Write-Log `"显卡非 Nvidia 显卡, 无法设置 CUDA 内存分配器`" -Level WARNING
    }
}


# 清理 Hotpatcher 环境变量
function Clear-Hotpatcher-Env {
    Get-ChildItem Env:SD_WEBUI_ALL_IN_ONE_HOTPATCHER_* -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item `"Env:`$(`$_.Name)`" -ErrorAction SilentlyContinue
    }
}


# 检测 Hotpatcher 端口
function Test-HotpatcherPort {
    param ([int]`$Port)
    return ((`$Port -ge 1) -and (`$Port -le 65535))
}


# 获取 Hotpatcher 端口
function Get-HotpatcherPort {
    if (`$script:HotpatcherPortProvided) {
        if (Test-HotpatcherPort `$script:HotpatcherPort) {
            return `$script:HotpatcherPort
        }
        Write-Log `"Hotpatcher 端口无效, 已使用默认端口 8765: `$(`$script:HotpatcherPort). 可用范围为 1 ~ 65535`" -Level WARNING
        return 8765
    }

    `$port_file = Join-NormalizedPath `$PSScriptRoot `"hotpatcher_port.txt`"
    if (!(Test-Path `$port_file)) {
        return 8765
    }

    `$port_text = Get-TrimmedTextFile `$port_file -Encoding UTF8
    `$port_value = 0
    if (([int]::TryParse(`$port_text, [ref]`$port_value)) -and (Test-HotpatcherPort `$port_value)) {
        return `$port_value
    }

    Write-Log `"hotpatcher_port.txt 中的 Hotpatcher 端口无效, 已使用默认端口 8765: `$port_text. 可用范围为 1 ~ 65535`" -Level WARNING
    return 8765
}


# 自动快照开关状态
function Test-SnapshotDisabled {
    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_snapshot.txt`")) -or (`$script:DisableSnapshot)) {
        return `$true
    }
    return `$false
}


# 为会触发自动快照的 CLI 命令配置快照参数
function Set-SnapshotCliArgs {
    [CmdletBinding()]
    param ([System.Collections.ArrayList]`$ArrayList)
    if (Test-SnapshotDisabled) {
        if (-not `$ArrayList.Contains(`"--no-snapshot`")) {
            `$ArrayList.Add(`"--no-snapshot`") | Out-Null
        }
        Write-Log `"检测到 disable_snapshot.txt 配置文件 / -DisableSnapshot 命令行参数, 已禁用自动快照`"
    }
}


# 保存安装结果快照
function Save-InstallResultSnapshot {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = `$true)][string]`$CliName,
        [Parameter(Mandatory = `$true)][string]`$PathArgument,
        [Parameter(Mandatory = `$true)][string]`$WebUIPath
    )

    if (Test-SnapshotDisabled) {
        Write-Log `"检测到 disable_snapshot.txt 配置文件 / -DisableSnapshot 命令行参数, 已跳过安装结果自动快照`"
        return
    }

    if (!(Test-Path -LiteralPath `$WebUIPath)) {
        Write-Log `"快照目标路径不存在, 已跳过安装结果自动快照: `$WebUIPath`" -Level WARNING
        return
    }

    Write-Log `"保存安装结果快照中`"
    `$core_cli_command = @(`"python`", `"-m`", `"sd_webui_all_in_one`", `$CliName, `"snapshot`", `$PathArgument, `$WebUIPath)
    & python -m sd_webui_all_in_one `$CliName snapshot `$PathArgument `$WebUIPath
    `$exit_code = Get-NativeCommandExitCode -Success `$?
    if (`$exit_code -ne 0) {
        `$command_line = Format-CoreCliCommandForLog -CommandPrefix `$core_cli_command -Arguments @()
        Write-Log `"安装结果自动快照保存失败, 退出码: `$exit_code`" -Level WARNING
        Write-Log `"失败命令: `$command_line`" -Level WARNING
        return
    }
    Write-Log `"安装结果快照保存完成`"
}

# 设置 Hotpatcher 补丁系统环境变量
function Set-Hotpatcher-Env {
    Clear-Hotpatcher-Env
    if ((`$script:DisableHotpatcher) -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_hotpatcher.txt`"))) {
        Write-Log `"检测到 disable_hotpatcher.txt 配置文件 / -DisableHotpatcher 命令行参数, 已禁用 Hotpatcher 补丁系统`"
        return
    }

    `$pythonpath = `$(python -m sd_webui_all_in_one self-manager patcher get-pythonpath)
    `$exit_code = Get-NativeCommandExitCode -Success `$?
    if ((`$exit_code -ne 0) -or ([string]::IsNullOrWhiteSpace(`$pythonpath))) {
        Write-Log `"获取 Hotpatcher PYTHONPATH 失败, 终止 SD Trainer Script 环境初始化`" -Level ERROR
        Exit-ManagerScript -ExitCode `$exit_code
    }
    `$Env:PYTHONPATH = `$pythonpath

    `$config_path = Join-NormalizedPath `$PSScriptRoot `"patcher_config.json`"
    if (!(Test-Path `$config_path)) {
        Write-Log `"Hotpatcher 默认配置不存在, 正在导出默认配置: `$config_path`"
        & python -m sd_webui_all_in_one self-manager patcher export-config *> `$null
        `$exit_code = Get-NativeCommandExitCode -Success `$?
        if (`$exit_code -ne 0) {
            Write-Log `"导出 Hotpatcher 默认配置失败, 终止 SD Trainer Script 环境初始化`" -Level ERROR
            Exit-ManagerScript -ExitCode `$exit_code
        }
    }

    `$Env:SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE = `"env`"
    `$Env:SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON = Get-Content -Raw -Encoding UTF8 -Path `$config_path

    `$hotpatcher_runtime_enabled = `$script:EnableHotpatcherRuntime -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"enable_hotpatcher_runtime.txt`"))
    if (`$hotpatcher_runtime_enabled) {
        `$hotpatcher_port = Get-HotpatcherPort
        `$Env:SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME = `"1`"
        `$Env:SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST = `"127.0.0.1`"
        `$Env:SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT = [string]`$hotpatcher_port
        `$Env:SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES = `"1`"
        Write-Log `"检测到 enable_hotpatcher_runtime.txt 配置文件 / -EnableHotpatcherRuntime 命令行参数, 已启用 Hotpatcher runtime host 连接`"
        Write-Log `"Hotpatcher runtime 通信端口: `$hotpatcher_port`"
    } elseif (`$script:HotpatcherPortProvided -or (Test-Path (Join-NormalizedPath `$PSScriptRoot `"hotpatcher_port.txt`"))) {
        Write-Log `"检测到 Hotpatcher 端口配置, 但未启用 Hotpatcher runtime, 已忽略该端口配置`" -Level WARNING
    }

    Write-Log `"Hotpatcher 补丁系统默认启用`"
    Write-Log `"Hotpatcher 使用默认配置文件内容: `$config_path`"
}


Export-ModuleMember -Function ``
    Initialize-EnvPath, ``
    Write-Log, ``
    Format-CommandLineArgumentForLog, ``
    Format-CoreCliCommandForLog, ``
    Write-CoreCliFailureCommand, ``
    Write-FileWithStreamWriter, ``
    Update-SDWebUiAllInOne, ``
    Update-Installer, ``
    Get-Version, ``
    Get-HelpMessage, ``
    Set-CorePrefix, ``
    Set-Proxy, ``
    Set-PyPIMirror, ``
    Set-ModelMirror, ``
    Set-HuggingFaceMirror, ``
    Set-GithubMirror, ``
    Set-uv, ``
    Set-PyTorchCUDAMemoryAlloc, ``
    Test-MSVCPPRedistributable, ``
    Set-PyTorch-CUDA-Memory-Alloc, ``
    Clear-Hotpatcher-Env, ``
    Test-HotpatcherPort, ``
    Get-HotpatcherPort, ``
    Test-SnapshotDisabled, ``
    Set-SnapshotCliArgs, ``
    Save-InstallResultSnapshot, ``
    Set-Hotpatcher-Env, ``
    Join-NormalizedPath, ``
    Get-NormalizedFilePath, ``
    Get-CurrentPlatform, ``
    Invoke-WindowsLongPathsStartupCheck, ``
    Get-CurrentArchitecture, ``
    New-AppShortcut, ``
    Test-PythonAndGit, ``
    Get-NativeCommandExitCode, ``
    Exit-ManagerScript, ``
    Get-TrimmedTextFile
".Trim()
    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "modules.psm1")) { "更新" } else { "生成" }) modules.psm1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "modules.psm1") -Value $content
}


# 训练模板脚本
function Write-TrainScript {
    $content = "
param(
    [switch]`$Help,
    [switch]`$NoPause,
    [Parameter(ValueFromRemainingArguments=`$true)]
    [string[]]`$Arguments
)
#################################################
`$pass_args = @()
if (`$script:NoPause) { `$pass_args += `"-NoPause`" }
if (`$script:Help) { `$pass_args += `"-Help`" }
if (`$Arguments) { `$pass_args += `$Arguments }
`$init_path = Join-Path `$PSScriptRoot `"init.ps1`"
# 初始化基础环境变量, 以正确识别到运行环境
if (Test-Path `$init_path) {
    & `"`$init_path`" @pass_args
} else {
    Write-Error `"初始化脚本未找到, 无法初始化环境`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White -NoNewline
    Write-Host `"launch_sd_trainer_installer.ps1`" -ForegroundColor Yellow -NoNewline
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if (!(`$script:NoPause)) { Read-Host | Out-Null }
    exit 1
}
Set-Location `$PSScriptRoot
# 此处的代码不要修改或者删除, 否则可能会出现意外情况
#
# SD Trainer Script 环境初始化后提供以下变量便于使用
#
# `${ROOT_PATH}               当前目录
# `${SD_SCRIPTS_PATH}         训练脚本所在目录
# `${DATASET_PATH}            数据集目录
# `${MODEL_PATH}              模型下载器下载的模型路径
# `${GIT_EXEC}                Git 路径
# `${PYTHON_EXEC}             Python 解释器路径
#
# 下方可编写训练代码
# 编写训练命令可参考: https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/advanced/#_2
# 编写结束后, 该文件必须使用 UTF-8 with BOM 编码保存
#################################################





#################################################
Write-Host `"训练结束, 退出训练脚本`"
if (!(`$script:NoPause)) { Read-Host | Out-Null } # 训练结束后保持控制台不被关闭
".Trim()

    if (!(Test-Path (Join-NormalizedPath $InstallPath "train.ps1"))) {
        Write-Log "生成 train.ps1 中"
        Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $InstallPath "train.ps1") -Value $content
    }
}


# 启动脚本
function Write-InitScript {
    $content = "
param (
    [Parameter(HelpMessage=@`"
获取 SD Trainer Script Installer 的帮助信息
`"@)][switch]`$Help,

    [Parameter(HelpMessage=@`"
设置内核的路径前缀, 默认路径前缀为 core
`"@)][string]`$CorePrefix,

    [Parameter(HelpMessage=@`"
启用 SD Trainer Script Installer 构建模式
`"@)][switch]`$BuildMode,

    [Parameter(HelpMessage=@`"
禁用 PyPI 软件包镜像源, 使用 PyPI 官方源下载 Python 软件包
`"@)][switch]`$DisablePyPIMirror,

    [Parameter(HelpMessage=@`"
禁用 CLI 自动选择下载镜像源; 禁用后才会遵守 PyPI / GitHub / Hugging Face / 模型下载来源等手动镜像设置
`"@)][switch]`$DisableAutoMirror,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 更新检查
`"@)][switch]`$DisableUpdate,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 自动设置代理服务器
`"@)][switch]`$DisableProxy,

    [Parameter(HelpMessage=@`"
使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址
`"@)][string]`$UseCustomProxy,

    [Parameter(HelpMessage=@`"
禁用 Hugging Face 镜像源, 不使用 Hugging Face 镜像源下载文件
`"@)][switch]`$DisableHuggingFaceMirror,

    [Parameter(HelpMessage=@`"
使用自定义 Hugging Face 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror ```"https://hf-mirror.com```" 设置 Hugging Face 镜像源地址
`"@)][string]`$UseCustomHuggingFaceMirror,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 自动设置 GitHub 镜像源
`"@)][switch]`$DisableGithubMirror,

    [Parameter(HelpMessage=@`"
使用自定义的 GitHub 镜像站地址
`"@)][string]`$UseCustomGithubMirror,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包
`"@)][switch]`$DisableUV,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 通过 PYTORCH_CUDA_ALLOC_CONF / PYTORCH_ALLOC_CONF 环境变量设置 CUDA 内存分配器
`"@)][switch]`$DisableCUDAMalloc,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 检查 SD Trainer Script 运行环境中存在的问题, 禁用后可能会导致 SD Trainer Script 环境中存在的问题无法被发现并修复
`"@)][switch]`$DisableEnvCheck,

    [Parameter(HelpMessage=@`"
禁用 Hotpatcher 补丁系统注入
`"@)][switch]`$DisableHotpatcher,

    [Parameter(HelpMessage=@`"
设置 Hotpatcher runtime 通信端口, 范围为 1 到 65535
`"@)][int]`$HotpatcherPort,

    [Parameter(HelpMessage=@`"
启用 Hotpatcher runtime host 连接
`"@)][switch]`$EnableHotpatcherRuntime,

    [Parameter(HelpMessage=@`"
禁用自动快照, 包括安装结束后的结果快照以及管理脚本执行前的自动快照
`"@)][switch]`$DisableSnapshot,

    [Parameter(HelpMessage=@`"
脚本执行完成后不暂停, 直接退出
`"@)][switch]`$NoPause
)
try {
    `$config = @{
        OriginalScriptPath = `$script:PSCommandPath
        LaunchCommandLine = if (`$script:MyInvocation.Line) { `$script:MyInvocation.Line } else { `$([Environment]::CommandLine) }
        Help = `$script:Help
        CorePrefix = `$script:CorePrefix
        DisableUV = `$script:DisableUV
        DisableProxy = `$script:DisableProxy
        UseCustomProxy = `$script:UseCustomProxy
        DisablePyPIMirror = `$script:DisablePyPIMirror
        DisableAutoMirror = `$script:DisableAutoMirror
        DisableHuggingFaceMirror = `$script:DisableHuggingFaceMirror
        UseCustomHuggingFaceMirror = `$script:UseCustomHuggingFaceMirror
        DisableGithubMirror = `$script:DisableGithubMirror
        UseCustomGithubMirror = `$script:UseCustomGithubMirror
        DisableCUDAMalloc = `$script:DisableCUDAMalloc
        DisableHotpatcher = `$script:DisableHotpatcher
        HotpatcherPort = `$script:HotpatcherPort
        HotpatcherPortProvided = `$PSBoundParameters.ContainsKey(`"HotpatcherPort`")
        EnableHotpatcherRuntime = `$script:EnableHotpatcherRuntime
        DisableUpdate = `$script:DisableUpdate
        BuildMode = `$script:BuildMode
        DisableEnvCheck = `$script:DisableEnvCheck
        DisableSnapshot = `$script:DisableSnapshot
        NoPause = `$script:NoPause
    }
    (Import-Module (Join-Path `$PSScriptRoot `"modules.psm1`") -Function `"Join-NormalizedPath`", `"Get-TrimmedTextFile`", `"Resolve-CorePrefix`", `"Initialize-EnvPath`", `"Invoke-WindowsLongPathsStartupCheck`", `"Write-Log`", `"Format-CommandLineArgumentForLog`", `"Format-CoreCliCommandForLog`", `"Write-CoreCliFailureCommand`", `"Set-CorePrefix`", `"Get-Version`", `"Update-Installer`", `"Set-Proxy`", `"Set-PyPIMirror`", `"Set-GithubMirror`", `"Set-uv`", `"Test-MSVCPPRedistributable`", `"Set-PyTorch-CUDA-Memory-Alloc`", `"Set-Hotpatcher-Env`", `"Update-SDWebUiAllInOne`", `"Get-CurrentPlatform`", `"Set-SnapshotCliArgs`", `"Get-HelpMessage`", `"Test-PythonAndGit`", `"Get-NativeCommandExitCode`", `"Exit-ManagerScript`" -PassThru -Force -ErrorAction Stop).Invoke({
        param (`$cfg)
        `$script:OriginalScriptPath = `$cfg.OriginalScriptPath
        `$script:LaunchCommandLine = `$cfg.LaunchCommandLine
        `$script:Help = `$cfg.Help
        `$script:CorePrefix = `$cfg.CorePrefix
        `$script:DisableUV = `$cfg.DisableUV
        `$script:DisableProxy = `$cfg.DisableProxy
        `$script:UseCustomProxy = `$cfg.UseCustomProxy
        `$script:DisablePyPIMirror = `$cfg.DisablePyPIMirror
        `$script:DisableAutoMirror = `$cfg.DisableAutoMirror
        `$script:DisableHuggingFaceMirror = `$cfg.DisableHuggingFaceMirror
        `$script:UseCustomHuggingFaceMirror = `$cfg.UseCustomHuggingFaceMirror
        `$script:DisableGithubMirror = `$cfg.DisableGithubMirror
        `$script:UseCustomGithubMirror = `$cfg.UseCustomGithubMirror
        `$script:DisableCUDAMalloc = `$cfg.DisableCUDAMalloc
        `$script:DisableHotpatcher = `$cfg.DisableHotpatcher
        `$script:HotpatcherPort = `$cfg.HotpatcherPort
        `$script:HotpatcherPortProvided = `$cfg.HotpatcherPortProvided
        `$script:EnableHotpatcherRuntime = `$cfg.EnableHotpatcherRuntime
        `$script:DisableUpdate = `$cfg.DisableUpdate
        `$script:BuildMode = `$cfg.BuildMode
        `$script:DisableEnvCheck = `$cfg.DisableEnvCheck
        `$script:DisableSnapshot = `$cfg.DisableSnapshot
        `$script:NoPause = `$cfg.NoPause
    }, `$config)
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White -NoNewline
    Write-Host `"launch_sd_trainer_script_installer.ps1`" -ForegroundColor Yellow -NoNewline
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if ((-not `$script:BuildMode) -and (-not `$script:NoPause)) { Read-Host | Out-Null }
    exit 1
}


# 获取启动 SD WebUI All In One 内核的启动参数
function Get-LaunchCoreArgs {
    `$launch_params = New-Object System.Collections.ArrayList
    Set-PyPIMirror `$launch_params
    Set-GithubMirror `$launch_params
    Set-uv `$launch_params
    return `$launch_params
}


function Main {
    Get-HelpMessage
    Get-Version
    Set-CorePrefix
    Initialize-EnvPath
    if (!(`$script:BuildMode)) {
        Invoke-WindowsLongPathsStartupCheck
    }
    Test-PythonAndGit
    Set-Proxy
    Update-Installer
    Update-SDWebUiAllInOne

    if (!(Test-Path (Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX))) {
        Write-Log `"内核路径 `$(Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX) 未找到, 请检查 SD Trainer Script 是否已正确安装, 或者尝试运行 SD Trainer Script Installer 进行修复`" -Level ERROR
        Exit-ManagerScript -ExitCode 1
    }

    if (!(`$script:BuildMode)) {
        Test-MSVCPPRedistributable
    }
    `$launch_args = Get-LaunchCoreArgs
    Set-PyTorch-CUDA-Memory-Alloc
    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_check_env.txt`")) -or (`$script:DisableEnvCheck)) {
        Write-Log `"检测到 disable_check_env.txt 配置文件 / -DisableEnvCheck 命令行参数, 已禁用 SD Trainer Script 启动前环境检测, 这可能会导致 SD Trainer Script 运行环境中存在的问题无法被发现并解决`" -Level WARNING
    } else {
        `$core_cli_command = @(`"python`", `"-m`", `"sd_webui_all_in_one`", `"sd-scripts`", `"check-env`")
        & python -m sd_webui_all_in_one sd-scripts check-env `$launch_args
        `$exit_code = Get-NativeCommandExitCode -Success `$?
        if (`$exit_code -ne 0) { Write-CoreCliFailureCommand -CommandPrefix `$core_cli_command -Arguments `$launch_args -ExitCode `$exit_code }
        if (`$exit_code -ne 0) {
            Exit-ManagerScript -ExitCode `$exit_code
        }
    }

    Set-Hotpatcher-Env

    `$Global:ROOT_PATH = `$PSScriptRoot
    `$Global:SD_SCRIPTS_PATH = Join-NormalizedPath `$ROOT_PATH `$Env:CORE_PREFIX
    `$Global:DATASET_PATH = Join-NormalizedPath `$ROOT_PATH `"datasets`"
    `$Global:MODEL_PATH = Join-NormalizedPath `$ROOT_PATH `"models`"
    `$Global:OUTPUT_PATH = Join-NormalizedPath `$ROOT_PATH `"outputs`"
    `$Global:GIT_EXEC = [System.IO.Path]::GetFullPath(`$(Get-Command git -ErrorAction SilentlyContinue).Source)
    `$Global:PYTHON_EXEC = [System.IO.Path]::GetFullPath(`$(Get-Command python -ErrorAction SilentlyContinue).Source)

    Write-Log `"可用的预设变量`"
    Write-Log `"ROOT_PATH: `$ROOT_PATH`"
    Write-Log `"SD_SCRIPTS_PATH: `$SD_SCRIPTS_PATH`"
    Write-Log `"DATASET_PATH: `$DATASET_PATH`"
    Write-Log `"MODEL_PATH: `$MODEL_PATH`"
    Write-Log `"OUTPUT_PATH: `$OUTPUT_PATH`"
    Write-Log `"GIT_EXEC: `$GIT_EXEC`"
    Write-Log `"PYTHON_EXEC: `$PYTHON_EXEC`"
    Write-Log `"初始化环境完成`"
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "init.ps1")) { "更新" } else { "生成" }) init.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "init.ps1") -Value $content
}


# 更新脚本
function Write-UpdateScript {
    $content = "
param (
    [Parameter(HelpMessage=@`"
获取 SD Trainer Script Installer 的帮助信息
`"@)][switch]`$Help,

    [Parameter(HelpMessage=@`"
设置内核的路径前缀, 默认路径前缀为 core
`"@)][string]`$CorePrefix,

    [Parameter(HelpMessage=@`"
启用 SD Trainer Script Installer 构建模式
`"@)][switch]`$BuildMode,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 更新检查
`"@)][switch]`$DisableUpdate,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 自动设置代理服务器
`"@)][switch]`$DisableProxy,

    [Parameter(HelpMessage=@`"
使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址
`"@)][string]`$UseCustomProxy,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 自动设置 GitHub 镜像源
`"@)][switch]`$DisableGithubMirror,

    [Parameter(HelpMessage=@`"
禁用 CLI 自动选择下载镜像源; 禁用后才会遵守 PyPI / GitHub / Hugging Face / 模型下载来源等手动镜像设置
`"@)][switch]`$DisableAutoMirror,

    [Parameter(HelpMessage=@`"
使用自定义的 GitHub 镜像站地址
`"@)][string]`$UseCustomGithubMirror,

    [Parameter(HelpMessage=@`"
禁用自动快照, 包括安装结束后的结果快照以及管理脚本执行前的自动快照
`"@)][switch]`$DisableSnapshot,

    [Parameter(HelpMessage=@`"
脚本执行完成后不暂停, 直接退出
`"@)][switch]`$NoPause
)
try {
    `$config = @{
        OriginalScriptPath = `$script:PSCommandPath
        LaunchCommandLine = if (`$script:MyInvocation.Line) { `$script:MyInvocation.Line } else { `$([Environment]::CommandLine) }
        Help = `$script:Help
        CorePrefix = `$script:CorePrefix
        DisableProxy = `$script:DisableProxy
        UseCustomProxy = `$script:UseCustomProxy
        DisableGithubMirror = `$script:DisableGithubMirror
        DisableAutoMirror = `$script:DisableAutoMirror
        UseCustomGithubMirror = `$script:UseCustomGithubMirror
        DisableUpdate = `$script:DisableUpdate
        BuildMode = `$script:BuildMode
        DisableSnapshot = `$script:DisableSnapshot
        NoPause = `$script:NoPause
    }
    (Import-Module (Join-Path `$PSScriptRoot `"modules.psm1`") -Function `"Join-NormalizedPath`", `"Get-TrimmedTextFile`", `"Resolve-CorePrefix`", `"Initialize-EnvPath`", `"Write-Log`", `"Format-CommandLineArgumentForLog`", `"Format-CoreCliCommandForLog`", `"Write-CoreCliFailureCommand`", `"Set-CorePrefix`", `"Get-Version`", `"Update-Installer`", `"Set-Proxy`", `"Set-GithubMirror`", `"Update-SDWebUiAllInOne`", `"Set-SnapshotCliArgs`", `"Get-HelpMessage`", `"Test-PythonAndGit`", `"Get-NativeCommandExitCode`", `"Exit-ManagerScript`" -PassThru -Force -ErrorAction Stop).Invoke({
        param (`$cfg)
        `$script:OriginalScriptPath = `$cfg.OriginalScriptPath
        `$script:LaunchCommandLine = `$cfg.LaunchCommandLine
        `$script:Help = `$cfg.Help
        `$script:CorePrefix = `$cfg.CorePrefix
        `$script:DisableProxy = `$cfg.DisableProxy
        `$script:UseCustomProxy = `$cfg.UseCustomProxy
        `$script:DisableGithubMirror = `$cfg.DisableGithubMirror
        `$script:DisableAutoMirror = `$cfg.DisableAutoMirror
        `$script:UseCustomGithubMirror = `$cfg.UseCustomGithubMirror
        `$script:DisableUpdate = `$cfg.DisableUpdate
        `$script:BuildMode = `$cfg.BuildMode
        `$script:DisableSnapshot = `$cfg.DisableSnapshot
        `$script:NoPause = `$cfg.NoPause
    }, `$config)
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White -NoNewline
    Write-Host `"launch_sd_trainer_script_installer.ps1`" -ForegroundColor Yellow -NoNewline
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if ((-not `$script:BuildMode) -and (-not `$script:NoPause)) { Read-Host | Out-Null }
    exit 1
}


# 获取启动 SD WebUI All In One 内核的启动参数
function Get-LaunchCoreArgs {
    `$launch_params = New-Object System.Collections.ArrayList
    Set-GithubMirror `$launch_params
    return `$launch_params
}


function Main {
    Get-HelpMessage
    Get-Version
    Set-CorePrefix
    Initialize-EnvPath
    Test-PythonAndGit
    Set-Proxy
    Update-Installer
    Update-SDWebUiAllInOne

    if (!(Test-Path (Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX))) {
        Write-Log `"内核路径 `$(Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX) 未找到, 请检查 SD Trainer Script 是否已正确安装, 或者尝试运行 SD Trainer Script Installer 进行修复`" -Level ERROR
        Exit-ManagerScript -ExitCode 1
    }

    `$launch_args = Get-LaunchCoreArgs
    `$core_cli_command = @(`"python`", `"-m`", `"sd_webui_all_in_one`", `"sd-scripts`", `"update`")
    Set-SnapshotCliArgs `$launch_args
    & python -m sd_webui_all_in_one sd-scripts update `$launch_args
    `$exit_code = Get-NativeCommandExitCode -Success `$?
    if (`$exit_code -ne 0) { Write-CoreCliFailureCommand -CommandPrefix `$core_cli_command -Arguments `$launch_args -ExitCode `$exit_code }

    Write-Log `"退出 SD Trainer Script 更新脚本`"
    Exit-ManagerScript -ExitCode `$exit_code
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "update.ps1")) { "更新" } else { "生成" }) update.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "update.ps1") -Value $content
}


# 切换分支脚本
function Write-SwitchBranchScript {
    $content = "
param (
    [Parameter(HelpMessage=@`"
获取 SD Trainer Script Installer 的帮助信息
`"@)][switch]`$Help,

    [Parameter(HelpMessage=@`"
设置内核的路径前缀, 默认路径前缀为 core
`"@)][string]`$CorePrefix,

    [Parameter(HelpMessage=@`"
启用 SD Trainer Script Installer 构建模式
`"@)][switch]`$BuildMode,

    [Parameter(HelpMessage=@`"
(需添加 -BuildMode 启用 SD Trainer Script Installer 构建模式) SD Trainer Script Installer 执行完基础安装流程后调用 SD Trainer Script Installer 的 switch_branch.ps1 脚本, 根据 SD Trainer Script 分支编号切换到对应的 SD Trainer Script 分支
SD Trainer Script 分支编号可运行 switch_branch.ps1 脚本进行查看
`"@)][string]`$BuildWithBranch,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 更新检查
`"@)][switch]`$DisableUpdate,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 自动设置代理服务器
`"@)][switch]`$DisableProxy,

    [Parameter(HelpMessage=@`"
使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址
`"@)][string]`$UseCustomProxy,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 自动设置 GitHub 镜像源
`"@)][switch]`$DisableGithubMirror,

    [Parameter(HelpMessage=@`"
禁用 CLI 自动选择下载镜像源; 禁用后才会遵守 PyPI / GitHub / Hugging Face / 模型下载来源等手动镜像设置
`"@)][switch]`$DisableAutoMirror,

    [Parameter(HelpMessage=@`"
使用自定义的 GitHub 镜像站地址
`"@)][string]`$UseCustomGithubMirror,

    [Parameter(HelpMessage=@`"
禁用自动快照, 包括安装结束后的结果快照以及管理脚本执行前的自动快照
`"@)][switch]`$DisableSnapshot,

    [Parameter(HelpMessage=@`"
脚本执行完成后不暂停, 直接退出
`"@)][switch]`$NoPause
)
try {
    `$config = @{
        OriginalScriptPath = `$script:PSCommandPath
        LaunchCommandLine = if (`$script:MyInvocation.Line) { `$script:MyInvocation.Line } else { `$([Environment]::CommandLine) }
        Help = `$script:Help
        CorePrefix = `$script:CorePrefix
        DisableProxy = `$script:DisableProxy
        UseCustomProxy = `$script:UseCustomProxy
        DisableGithubMirror = `$script:DisableGithubMirror
        DisableAutoMirror = `$script:DisableAutoMirror
        UseCustomGithubMirror = `$script:UseCustomGithubMirror
        DisableUpdate = `$script:DisableUpdate
        BuildMode = `$script:BuildMode
        DisableSnapshot = `$script:DisableSnapshot
        NoPause = `$script:NoPause
    }
    (Import-Module (Join-Path `$PSScriptRoot `"modules.psm1`") -Function `"Join-NormalizedPath`", `"Get-TrimmedTextFile`", `"Resolve-CorePrefix`", `"Initialize-EnvPath`", `"Write-Log`", `"Format-CommandLineArgumentForLog`", `"Format-CoreCliCommandForLog`", `"Write-CoreCliFailureCommand`", `"Set-CorePrefix`", `"Get-Version`", `"Update-Installer`", `"Set-Proxy`", `"Set-GithubMirror`", `"Update-SDWebUiAllInOne`", `"Set-SnapshotCliArgs`", `"Get-HelpMessage`", `"Test-PythonAndGit`", `"Get-NativeCommandExitCode`", `"Exit-ManagerScript`" -PassThru -Force -ErrorAction Stop).Invoke({
        param (`$cfg)
        `$script:OriginalScriptPath = `$cfg.OriginalScriptPath
        `$script:LaunchCommandLine = `$cfg.LaunchCommandLine
        `$script:Help = `$cfg.Help
        `$script:CorePrefix = `$cfg.CorePrefix
        `$script:DisableProxy = `$cfg.DisableProxy
        `$script:UseCustomProxy = `$cfg.UseCustomProxy
        `$script:DisableGithubMirror = `$cfg.DisableGithubMirror
        `$script:DisableAutoMirror = `$cfg.DisableAutoMirror
        `$script:UseCustomGithubMirror = `$cfg.UseCustomGithubMirror
        `$script:DisableUpdate = `$cfg.DisableUpdate
        `$script:BuildMode = `$cfg.BuildMode
        `$script:DisableSnapshot = `$cfg.DisableSnapshot
        `$script:NoPause = `$cfg.NoPause
    }, `$config)
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White -NoNewline
    Write-Host `"launch_sd_trainer_installer.ps1`" -ForegroundColor Yellow -NoNewline
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if ((-not `$script:BuildMode) -and (-not `$script:NoPause)) { Read-Host | Out-Null }
    exit 1
}


# 获取启动 SD WebUI All In One 内核的启动参数
function Get-LaunchCoreArgs {
    `$launch_params = New-Object System.Collections.ArrayList
    if (`$script:BuildMode) {
        `$launch_params.Add(`"--branch`") | Out-Null
        `$launch_params.Add(`$script:BuildWithBranch) | Out-Null
    } else {
        `$launch_params.Add(`"--interactive`") | Out-Null
    }
    Set-GithubMirror `$launch_params
    return `$launch_params
}


function Main {
    Get-HelpMessage
    Get-Version
    Set-CorePrefix
    Initialize-EnvPath
    Test-PythonAndGit
    Set-Proxy
    Update-Installer
    Update-SDWebUiAllInOne

    if (!(Test-Path (Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX))) {
        Write-Log `"内核路径 `$(Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX) 未找到, 请检查 SD Trainer Script 是否已正确安装, 或者尝试运行 SD Trainer Script Installer 进行修复`" -Level ERROR
        Exit-ManagerScript -ExitCode 1
    }

    `$launch_args = Get-LaunchCoreArgs
    `$core_cli_command = @(`"python`", `"-m`", `"sd_webui_all_in_one`", `"sd-scripts`", `"switch`")
    Set-SnapshotCliArgs `$launch_args
    & python -m sd_webui_all_in_one sd-scripts switch `$launch_args
    `$exit_code = Get-NativeCommandExitCode -Success `$?
    if (`$exit_code -ne 0) { Write-CoreCliFailureCommand -CommandPrefix `$core_cli_command -Arguments `$launch_args -ExitCode `$exit_code }

    Write-Log `"退出 SD Trainer Script 分支切换脚本`"

    Exit-ManagerScript -ExitCode `$exit_code
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "switch_branch.ps1")) { "更新" } else { "生成" }) switch_branch.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "switch_branch.ps1") -Value $content
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
    [string]`$InstallBranch,
    [string]`$CorePrefix,
    [switch]`$RestoreFromSnapshot,
    [string]`$SnapshotPath,
    [switch]`$DisableSnapshot,
    [switch]`$NoPause,
    [Parameter(ValueFromRemainingArguments=`$true)]`$ExtraArgs
)

function Join-NormalizedPath {
    `$joined = `$args[0]
    for (`$i = 1; `$i -lt `$args.Count; `$i++) { `$joined = Join-Path `$joined `$args[`$i] }
    return `$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath(`$joined).TrimEnd('\', '/')
}


function Get-TrimmedTextFile {
    param (
        [Parameter(Mandatory = `$true)][string]`$Path,
        [string]`$Encoding
    )
    if (!(Test-Path `$Path)) {
        return `$null
    }
    if ([string]::IsNullOrWhiteSpace(`$Encoding)) {
        `$content = Get-Content -Path `$Path -Raw
    } else {
        `$content = Get-Content -Path `$Path -Raw -Encoding `$Encoding
    }
    if ([string]::IsNullOrWhiteSpace(`$content)) {
        return `$null
    }
    return `$content.Trim()
}


function Resolve-CorePrefix {
    param (
        [Parameter(Mandatory = `$true)][string]`$BasePath,
        [Parameter(Mandatory = `$true)][string[]]`$PrefixList,
        [AllowNull()][string]`$ConfiguredPrefix
    )
    `$target_prefix = `$null
    if (-not [string]::IsNullOrWhiteSpace(`$ConfiguredPrefix)) {
        `$origin_core_prefix = `$ConfiguredPrefix.TrimEnd('\', '/')
        if ([System.IO.Path]::IsPathRooted(`$origin_core_prefix)) {
            `$from_uri = New-Object System.Uri(`$BasePath.Replace('\', '/') + '/')
            `$to_uri = New-Object System.Uri(`$origin_core_prefix.Replace('\', '/'))
            `$target_prefix = `$from_uri.MakeRelativeUri(`$to_uri).ToString().Trim('/')
        } else {
            `$target_prefix = `$origin_core_prefix
        }
    }
    if ([string]::IsNullOrWhiteSpace(`$target_prefix)) {
        foreach (`$i in `$PrefixList) {
            `$found_dir = Get-ChildItem -Path `$BasePath -Directory -Filter `$i -ErrorAction SilentlyContinue | Select-Object -First 1
            if (`$found_dir) {
                `$target_prefix = `$found_dir.Name
                break
            }
        }
    }
    if ([string]::IsNullOrWhiteSpace(`$target_prefix)) {
        `$target_prefix = 'core'
    }
    return `$target_prefix
}

if (`$null -eq `$script:InstallPath) {
    `$script:InstallPath = `$PSScriptRoot
} else {
    `$script:InstallPath = Join-NormalizedPath `$script:InstallPath
}

& {
    `$prefix_list = @(`"core`", `"sd-scripts*`")
    `$core_prefix_file = Join-NormalizedPath `$PSScriptRoot `"core_prefix.txt`"
    `$origin_core_prefix = if (`$script:CorePrefix) {
        `$script:CorePrefix
    } else {
        Get-TrimmedTextFile `$core_prefix_file -Encoding UTF8
    }
    `$env:CORE_PREFIX = Resolve-CorePrefix -BasePath `$PSScriptRoot -PrefixList `$prefix_list -ConfiguredPrefix `$origin_core_prefix
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
        [string]`$Name = `"SD Trainer Script Installer`"
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


# 下载 SD Trainer Script Installer
function Download-Installer {
    # 可用的下载源
    `$urls = @(
        `"https://github.com/licyk/sd-webui-all-in-one/raw/main/installer/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/raw/main/installer/sd_trainer_script_installer.ps1`",
        `"https://github.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitee.com/licyk/sd-webui-all-in-one/releases/download/sd_trainer_script_installer/sd_trainer_script_installer.ps1`",
        `"https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/installer/sd_trainer_script_installer.ps1`"
    )
    `$i = 0

    New-Item -ItemType Directory -Path (Join-NormalizedPath `$PSScriptRoot `"cache`") -Force > `$null

    foreach (`$url in `$urls) {
        Write-Log `"正在下载最新的 SD Trainer Script Installer 脚本`"
        `$web_request_params = @{
            Uri = `$url
            UseBasicParsing = `$true
            OutFile = (Join-NormalizedPath `$PSScriptRoot `"cache`" `"sd_trainer_script_installer.ps1`")
            TimeoutSec = 15
            ErrorAction = `"Stop`"
        }
        try {
            Invoke-WebRequest @web_request_params
            Write-Log `"下载 SD Trainer Script Installer 脚本成功`"
            break
        } catch {
            Write-Log `"下载 SD Trainer Script Installer 脚本失败: `$(`$_.Exception.Message)`" -Level ERROR
            `$i += 1
            if (`$i -lt `$urls.Length) {
                Write-Log `"重试下载 SD Trainer Script Installer 脚本`" -Level WARNING
            } else {
                Write-Log `"下载 SD Trainer Script Installer 脚本失败, 可尝试重新运行 SD Trainer Script Installer 下载脚本`" -Level ERROR
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
                `$proxy_value = Get-TrimmedTextFile (Join-NormalizedPath `$PSScriptRoot `"proxy.txt`") -Encoding UTF8
            }
            if (-not [string]::IsNullOrWhiteSpace(`$proxy_value)) {
                `$arg.Add(`"-UseCustomProxy`", `$proxy_value)
            }
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
                `$github_mirror = Get-TrimmedTextFile (Join-NormalizedPath `$PSScriptRoot `"gh_mirror.txt`") -Encoding UTF8
            }
            if (-not [string]::IsNullOrWhiteSpace(`$github_mirror)) {
                `$arg.Add(`"-UseCustomGithubMirror`", `$github_mirror)
            }
        }
    }

    `$git_repo_map = @{
        `"kohya-ss/sd-scripts`"         = `"sd_scripts_dev`"
        `"ostris/ai-toolkit`"           = `"ai_toolkit_main`"
        `"a-r-r-o-w/finetrainers`"      = `"finetrainers_main`"
        `"tdrussell/diffusion-pipe`"    = `"diffusion_pipe_main`"
        `"kohya-ss/musubi-tuner`"       = `"musubi_tuner_main`"
    }
    `$fallback_check_list = @(
        @{ Key = `"sd_scripts`";          Val = `"sd_scripts_dev`" }
        @{ Key = `"sd_scripts_main`";     Val = `"sd_scripts_main`" }
        @{ Key = `"sd_scripts_dev`";      Val = `"sd_scripts_dev`" }
        @{ Key = `"sd_scripts_sd3`";      Val = `"sd_scripts_sd3`" }
        @{ Key = `"ai_toolkit`";          Val = `"ai_toolkit_main`" }
        @{ Key = `"ai_toolkit_main`";     Val = `"ai_toolkit_main`" }
        @{ Key = `"finetrainers`";        Val = `"finetrainers_main`" }
        @{ Key = `"finetrainers_main`";   Val = `"finetrainers_main`" }
        @{ Key = `"diffusion_pipe`";      Val = `"diffusion_pipe_main`" }
        @{ Key = `"diffusion_pipe_main`"; Val = `"diffusion_pipe_main`" }
        @{ Key = `"musubi_tuner`";        Val = `"musubi_tuner_main`" }
        @{ Key = `"musubi_tuner_main`";   Val = `"musubi_tuner_main`" }
    )
    `$detected_branch = `$null
    if ((Get-Command git -ErrorAction SilentlyContinue) -and (Test-Path (Join-NormalizedPath `$PSScriptRoot `$Env:CORE_PREFIX `".git`"))) {
        try {
            `$remoteUrl = (git -C `"`$(Join-NormalizedPath `$PSScriptRoot `$Env:CORE_PREFIX)`" remote get-url origin).Trim() -replace '\.git`$', ''
            `$urlParts = `$remoteUrl -split '/'
            `$repoKey = `"`$(`$urlParts[-2])/`$(`$urlParts[-1])`"
            if (`$git_repo_map.ContainsKey(`$repoKey)) {
                `$detected_branch = `$git_repo_map[`$repoKey]
            }
        } catch {}
    }
    if (-not `$detected_branch) {
        foreach (`$item in `$fallback_check_list) {
            `$file_path = Join-Path `$PSScriptRoot `"install_`$(`$item.Key).txt`"
            if ((Test-Path `$file_path) -or (`$script:InstallBranch -eq `$item.Key)) {
                `$detected_branch = `$item.Val
                break
            }
        }
    }
    if (`$detected_branch) {
        `$arg.Add(`"-InstallBranch`", `$detected_branch)
    }

    `$arg.Add(`"-InstallPath`", `$script:InstallPath)
    `$arg.Add(`"-CorePrefix`", `$script:CorePrefix)
    if (`$script:RestoreFromSnapshot) {
        `$arg.Add(`"-RestoreFromSnapshot`", `$true)
    }
    if (-not [string]::IsNullOrWhiteSpace(`$script:SnapshotPath)) {
        `$arg.Add(`"-SnapshotPath`", `$script:SnapshotPath)
    }
    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_snapshot.txt`")) -or (`$script:DisableSnapshot)) {
        `$arg.Add(`"-DisableSnapshot`", `$true)
    }

    return `$arg
}


# 处理额外命令行参数
function Get-ExtraArgs {
    `$extra_args = New-Object System.Collections.ArrayList

    foreach (`$a in `$ExtraArgs) {
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
        Write-Log `"运行 SD Trainer Script Installer 中`"
        `$arg = Get-LocalSetting
        `$extra_args = Get-ExtraArgs
        `$script_path = Join-NormalizedPath `$PSScriptRoot `"cache`" `"sd_trainer_script_installer.ps1`"
        try {
            Invoke-Expression `"& ```"`$script_path```" `$extra_args @arg`" -ErrorAction Stop
        }
        catch {
            Write-Log `"运行 SD Trainer Script Installer 时出现了错误: `$_`" -Level ERROR
            if (!(`$script:NoPause)) { Read-Host | Out-Null }
            exit 1
        }
    } else {
        if (!(`$script:NoPause)) { Read-Host | Out-Null }
        exit 1
    }
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "launch_sd_trainer_script_installer.ps1")) { "更新" } else { "生成" }) launch_sd_trainer_script_installer.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "launch_sd_trainer_script_installer.ps1") -Value $content
}


# 重装 PyTorch 脚本
function Write-PyTorchReInstallScript {
    $content = "
param (
    [Parameter(HelpMessage=@`"
获取 SD Trainer Script Installer 的帮助信息
`"@)][switch]`$Help,

    [Parameter(HelpMessage=@`"
设置内核的路径前缀, 默认路径前缀为 core
`"@)][string]`$CorePrefix,

    [Parameter(HelpMessage=@`"
启用 SD Trainer Script Installer 构建模式
`"@)][switch]`$BuildMode,

    [Parameter(HelpMessage=@`"
(需添加 -BuildMode 启用 SD Trainer Script Installer 构建模式) SD Trainer Script Installer 执行完基础安装流程后调用 SD Trainer Script Installer 的 reinstall_pytorch.ps1 脚本, 根据 PyTorch 版本编号安装指定的 PyTorch 版本
PyTorch 版本编号可运行 reinstall_pytorch.ps1 脚本进行查看
`"@)][int]`$BuildWithTorch,

    [Parameter(HelpMessage=@`"
(需添加 -BuildMode 启用 SD Trainer Script Installer 构建模式, 并且添加 -BuildWithTorch) 在 SD Trainer Script Installer 构建模式下, 执行 reinstall_pytorch.ps1 脚本对 PyTorch 进行指定版本安装时使用强制重新安装
`"@)][switch]`$BuildWithTorchReinstall,

    [Parameter(HelpMessage=@`"
禁用 PyPI 软件包镜像源, 使用 PyPI 官方源下载 Python 软件包
`"@)][switch]`$DisablePyPIMirror,

    [Parameter(HelpMessage=@`"
禁用 CLI 自动选择下载镜像源; 禁用后才会遵守 PyPI / GitHub / Hugging Face / 模型下载来源等手动镜像设置
`"@)][switch]`$DisableAutoMirror,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 更新检查
`"@)][switch]`$DisableUpdate,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 使用 uv 安装 Python 软件包, 使用 Pip 安装 Python 软件包
`"@)][switch]`$DisableUV,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 自动设置代理服务器
`"@)][switch]`$DisableProxy,

    [Parameter(HelpMessage=@`"
使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址
`"@)][string]`$UseCustomProxy,

    [Parameter(HelpMessage=@`"
禁用自动快照, 包括安装结束后的结果快照以及管理脚本执行前的自动快照
`"@)][switch]`$DisableSnapshot,

    [Parameter(HelpMessage=@`"
脚本执行完成后不暂停, 直接退出
`"@)][switch]`$NoPause
)
try {
    `$config = @{
        OriginalScriptPath = `$script:PSCommandPath
        LaunchCommandLine = if (`$script:MyInvocation.Line) { `$script:MyInvocation.Line } else { `$([Environment]::CommandLine) }
        Help = `$script:Help
        CorePrefix = `$script:CorePrefix
        DisableUV = `$script:DisableUV
        DisableProxy = `$script:DisableProxy
        UseCustomProxy = `$script:UseCustomProxy
        DisablePyPIMirror = `$script:DisablePyPIMirror
        DisableAutoMirror = `$script:DisableAutoMirror
        BuildMode = `$script:BuildMode
        DisableUpdate = `$script:DisableUpdate
        DisableSnapshot = `$script:DisableSnapshot
        NoPause = `$script:NoPause
    }
    (Import-Module (Join-Path `$PSScriptRoot `"modules.psm1`") -Function `"Join-NormalizedPath`", `"Get-TrimmedTextFile`", `"Resolve-CorePrefix`", `"Initialize-EnvPath`", `"Write-Log`", `"Format-CommandLineArgumentForLog`", `"Format-CoreCliCommandForLog`", `"Write-CoreCliFailureCommand`", `"Set-CorePrefix`", `"Get-Version`", `"Set-PyPIMirror`", `"Update-Installer`", `"Set-uv`", `"Set-Proxy`", `"Update-SDWebUiAllInOne`", `"Set-SnapshotCliArgs`", `"Get-HelpMessage`", `"Test-PythonAndGit`", `"Get-NativeCommandExitCode`", `"Exit-ManagerScript`" -PassThru -Force -ErrorAction Stop).Invoke({
        param (`$cfg)
        `$script:OriginalScriptPath = `$cfg.OriginalScriptPath
        `$script:LaunchCommandLine = `$cfg.LaunchCommandLine
        `$script:Help = `$cfg.Help
        `$script:CorePrefix = `$cfg.CorePrefix
        `$script:DisableUV = `$cfg.DisableUV
        `$script:DisableProxy = `$cfg.DisableProxy
        `$script:UseCustomProxy = `$cfg.UseCustomProxy
        `$script:DisablePyPIMirror = `$cfg.DisablePyPIMirror
        `$script:DisableAutoMirror = `$cfg.DisableAutoMirror
        `$script:BuildMode = `$cfg.BuildMode
        `$script:DisableUpdate = `$cfg.DisableUpdate
        `$script:DisableSnapshot = `$cfg.DisableSnapshot
        `$script:NoPause = `$cfg.NoPause
    }, `$config)
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White -NoNewline
    Write-Host `"launch_sd_trainer_script_installer.ps1`" -ForegroundColor Yellow -NoNewline
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if ((-not `$script:BuildMode) -and (-not `$script:NoPause)) { Read-Host | Out-Null }
    exit 1
}


# 获取启动 SD WebUI All In One 内核的启动参数
function Get-LaunchCoreArgs {
    `$launch_params = New-Object System.Collections.ArrayList
    Set-PyPIMirror `$launch_params
    Set-uv `$launch_params
    if (`$script:BuildWithTorch) {
        `$launch_params.Add(`"--index`") | Out-Null
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
    Get-HelpMessage
    Get-Version
    Set-CorePrefix
    Initialize-EnvPath
    Test-PythonAndGit
    Set-Proxy
    Update-Installer
    Update-SDWebUiAllInOne

    `$launch_args = Get-LaunchCoreArgs
    `$core_cli_command = @(`"python`", `"-m`", `"sd_webui_all_in_one`", `"sd-scripts`", `"reinstall-pytorch`")
    Set-SnapshotCliArgs `$launch_args
    & python -m sd_webui_all_in_one sd-scripts reinstall-pytorch `$launch_args
    `$exit_code = Get-NativeCommandExitCode -Success `$?
    if (`$exit_code -ne 0) { Write-CoreCliFailureCommand -CommandPrefix `$core_cli_command -Arguments `$launch_args -ExitCode `$exit_code }

    Write-Log `"退出 PyTorch 重装脚本`"
    Exit-ManagerScript -ExitCode `$exit_code
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "reinstall_pytorch.ps1")) { "更新" } else { "生成" }) reinstall_pytorch.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "reinstall_pytorch.ps1") -Value $content
}


# 模型下载脚本
function Write-DownloadModelScript {
    $content = "
param (
    [Parameter(HelpMessage=@`"
获取 SD Trainer Script Installer 的帮助信息
`"@)][switch]`$Help,

    [Parameter(HelpMessage=@`"
设置内核的路径前缀, 默认路径前缀为 core
`"@)][string]`$CorePrefix,

    [Parameter(HelpMessage=@`"
启用 SD Trainer Script Installer 构建模式
`"@)][switch]`$BuildMode,

    [Parameter(HelpMessage=@`"
(需添加 -BuildMode 启用 SD Trainer Script Installer 构建模式) SD Trainer Script Installer 执行完基础安装流程后调用 SD Trainer Script Installer 的 download_models.ps1 脚本, 根据模型编号列表下载指定的模型
模型编号可运行 download_models.ps1 脚本进行查看
`"@)][string]`$BuildWithModel,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 自动设置代理服务器
`"@)][switch]`$DisableProxy,

    [Parameter(HelpMessage=@`"
使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址
`"@)][string]`$UseCustomProxy,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 更新检查
`"@)][switch]`$DisableUpdate,

    [Parameter(HelpMessage=@`"
不使用 ModelScope 下载模型, 使用 Hugging Face 下载模型
`"@)][switch]`$DisableModelMirror,

    [Parameter(HelpMessage=@`"
禁用 CLI 自动选择下载镜像源; 禁用后才会遵守 PyPI / GitHub / Hugging Face / 模型下载来源等手动镜像设置
`"@)][switch]`$DisableAutoMirror,


    [Parameter(HelpMessage=@`"
脚本执行完成后不暂停, 直接退出
`"@)][switch]`$NoPause
)
try {
    `$config = @{
        OriginalScriptPath = `$script:PSCommandPath
        LaunchCommandLine = if (`$script:MyInvocation.Line) { `$script:MyInvocation.Line } else { `$([Environment]::CommandLine) }
        Help = `$script:Help
        CorePrefix = `$script:CorePrefix
        DisableProxy = `$script:DisableProxy
        UseCustomProxy = `$script:UseCustomProxy
        DisableUpdate = `$script:DisableUpdate
        BuildMode = `$script:BuildMode
        DisableModelMirror = `$script:DisableModelMirror
        DisableAutoMirror = `$script:DisableAutoMirror
        NoPause = `$script:NoPause
    }
    (Import-Module (Join-Path `$PSScriptRoot `"modules.psm1`") -Function `"Join-NormalizedPath`", `"Get-TrimmedTextFile`", `"Resolve-CorePrefix`", `"Initialize-EnvPath`", `"Write-Log`", `"Format-CommandLineArgumentForLog`", `"Format-CoreCliCommandForLog`", `"Write-CoreCliFailureCommand`", `"Set-CorePrefix`", `"Get-Version`", `"Set-PyPIMirror`", `"Update-Installer`", `"Set-Proxy`", `"Update-SDWebUiAllInOne`", `"Get-HelpMessage`", `"Set-ModelMirror`", `"Test-PythonAndGit`", `"Get-NativeCommandExitCode`", `"Exit-ManagerScript`" -PassThru -Force -ErrorAction Stop).Invoke({
        param (`$cfg)
        `$script:OriginalScriptPath = `$cfg.OriginalScriptPath
        `$script:LaunchCommandLine = `$cfg.LaunchCommandLine
        `$script:Help = `$cfg.Help
        `$script:CorePrefix = `$cfg.CorePrefix
        `$script:DisableProxy = `$cfg.DisableProxy
        `$script:UseCustomProxy = `$cfg.UseCustomProxy
        `$script:DisableUpdate = `$cfg.DisableUpdate
        `$script:BuildMode = `$cfg.BuildMode
        `$script:DisableModelMirror = `$cfg.DisableModelMirror
        `$script:DisableAutoMirror = `$cfg.DisableAutoMirror
        `$script:NoPause = `$cfg.NoPause
    }, `$config)
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White -NoNewline
    Write-Host `"launch_sd_trainer_script_installer.ps1`" -ForegroundColor Yellow -NoNewline
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if ((-not `$script:BuildMode) -and (-not `$script:NoPause)) { Read-Host | Out-Null }
    exit 1
}


# 获取启动 SD WebUI All In One 内核的启动参数
function Get-LaunchCoreArgs {
    `$launch_params = New-Object System.Collections.ArrayList
    if (`$script:BuildWithModel) {
        `$launch_params.Add(`"--index`") | Out-Null
        `$launch_params.Add(`$script:BuildWithModel) | Out-Null
    }
    if (!(`$script:BuildMode)) {
        `$launch_params.Add(`"--interactive`") | Out-Null
    }
    Set-ModelMirror `$launch_params
    return `$launch_params
}


function Main {
    Get-HelpMessage
    Get-Version
    Set-CorePrefix
    Initialize-EnvPath
    Test-PythonAndGit
    Set-Proxy
    Update-Installer
    Update-SDWebUiAllInOne

    if (!(Test-Path (Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX))) {
        Write-Log `"内核路径 `$(Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX) 未找到, 请检查 SD Trainer Script 是否已正确安装, 或者尝试运行 SD Trainer Script Installer 进行修复`" -Level ERROR
        Exit-ManagerScript -ExitCode 1
    }

    `$launch_args = Get-LaunchCoreArgs
    `$core_cli_command = @(`"python`", `"-m`", `"sd_webui_all_in_one`", `"sd-scripts`", `"model`", `"install-library`")
    & python -m sd_webui_all_in_one sd-scripts model install-library `$launch_args
    `$exit_code = Get-NativeCommandExitCode -Success `$?
    if (`$exit_code -ne 0) { Write-CoreCliFailureCommand -CommandPrefix `$core_cli_command -Arguments `$launch_args -ExitCode `$exit_code }

    Write-Log `"退出模型下载脚本`"
    Exit-ManagerScript -ExitCode `$exit_code
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "download_models.ps1")) { "更新" } else { "生成" }) download_models.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "download_models.ps1") -Value $content
}


# 版本管理脚本
function Write-VersionManagerScript {
    $content = "
param (
    [Parameter(HelpMessage=@`"
获取 SD Trainer Script Installer 的帮助信息
`"@)][switch]`$Help,

    [Parameter(HelpMessage=@`"
设置内核的路径前缀, 默认路径前缀为 core
`"@)][string]`$CorePrefix,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 更新检查
`"@)][switch]`$DisableUpdate,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 自动设置代理服务器
`"@)][switch]`$DisableProxy,

    [Parameter(HelpMessage=@`"
使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址
`"@)][string]`$UseCustomProxy,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 自动设置 GitHub 镜像源
`"@)][switch]`$DisableGithubMirror,

    [Parameter(HelpMessage=@`"
禁用 CLI 自动选择下载镜像源; 禁用后才会遵守 PyPI / GitHub / Hugging Face / 模型下载来源等手动镜像设置
`"@)][switch]`$DisableAutoMirror,

    [Parameter(HelpMessage=@`"
使用自定义的 GitHub 镜像站地址
`"@)][string]`$UseCustomGithubMirror,

    [Parameter(HelpMessage=@`"
禁用自动快照, 包括安装结束后的结果快照以及管理脚本执行前的自动快照
`"@)][switch]`$DisableSnapshot,

    [Parameter(HelpMessage=@`"
脚本执行完成后不暂停, 直接退出
`"@)][switch]`$NoPause
)
try {
    `$config = @{
        OriginalScriptPath = `$script:PSCommandPath
        LaunchCommandLine = if (`$script:MyInvocation.Line) { `$script:MyInvocation.Line } else { `$([Environment]::CommandLine) }
        Help = `$script:Help
        CorePrefix = `$script:CorePrefix
        DisableProxy = `$script:DisableProxy
        UseCustomProxy = `$script:UseCustomProxy
        DisableGithubMirror = `$script:DisableGithubMirror
        DisableAutoMirror = `$script:DisableAutoMirror
        UseCustomGithubMirror = `$script:UseCustomGithubMirror
        DisableUpdate = `$script:DisableUpdate
        DisableSnapshot = `$script:DisableSnapshot
        NoPause = `$script:NoPause
    }
    (Import-Module (Join-Path `$PSScriptRoot `"modules.psm1`") -Function `"Join-NormalizedPath`", `"Get-TrimmedTextFile`", `"Resolve-CorePrefix`", `"Initialize-EnvPath`", `"Write-Log`", `"Format-CommandLineArgumentForLog`", `"Format-CoreCliCommandForLog`", `"Write-CoreCliFailureCommand`", `"Set-CorePrefix`", `"Get-Version`", `"Update-Installer`", `"Set-Proxy`", `"Set-GithubMirror`", `"Update-SDWebUiAllInOne`", `"Set-SnapshotCliArgs`", `"Get-HelpMessage`", `"Test-PythonAndGit`", `"Get-NativeCommandExitCode`", `"Exit-ManagerScript`" -PassThru -Force -ErrorAction Stop).Invoke({
        param (`$cfg)
        `$script:OriginalScriptPath = `$cfg.OriginalScriptPath
        `$script:LaunchCommandLine = `$cfg.LaunchCommandLine
        `$script:Help = `$cfg.Help
        `$script:CorePrefix = `$cfg.CorePrefix
        `$script:DisableProxy = `$cfg.DisableProxy
        `$script:UseCustomProxy = `$cfg.UseCustomProxy
        `$script:DisableGithubMirror = `$cfg.DisableGithubMirror
        `$script:DisableAutoMirror = `$cfg.DisableAutoMirror
        `$script:UseCustomGithubMirror = `$cfg.UseCustomGithubMirror
        `$script:DisableUpdate = `$cfg.DisableUpdate
        `$script:DisableSnapshot = `$cfg.DisableSnapshot
        `$script:NoPause = `$cfg.NoPause
    }, `$config)
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White -NoNewline
    Write-Host `"launch_sd_trainer_script_installer.ps1`" -ForegroundColor Yellow -NoNewline
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if ((-not `$script:BuildMode) -and (-not `$script:NoPause)) { Read-Host | Out-Null }
    exit 1
}


# 获取启动 SD WebUI All In One 内核的启动参数
function Get-LaunchCoreArgs {
    `$launch_params = New-Object System.Collections.ArrayList
    Set-GithubMirror `$launch_params
    return `$launch_params
}


function Main {
    Get-HelpMessage
    Get-Version
    Set-CorePrefix
    Initialize-EnvPath
    Test-PythonAndGit
    Set-Proxy
    Update-Installer
    Update-SDWebUiAllInOne

    if (!(Test-Path (Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX))) {
        Write-Log `"内核路径 `$(Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX) 未找到, 请检查 SD Trainer Script 是否已正确安装, 或者尝试运行 SD Trainer Script Installer 进行修复`" -Level ERROR
        Exit-ManagerScript -ExitCode 1
    }

    `$launch_args = Get-LaunchCoreArgs
    `$core_cli_command = @(`"python`", `"-m`", `"sd_webui_all_in_one`", `"sd-scripts`", `"gui`", `"version-manager`")
    Set-SnapshotCliArgs `$launch_args
    & python -m sd_webui_all_in_one sd-scripts gui version-manager `$launch_args
    `$exit_code = Get-NativeCommandExitCode -Success `$?
    if (`$exit_code -ne 0) { Write-CoreCliFailureCommand -CommandPrefix `$core_cli_command -Arguments `$launch_args -ExitCode `$exit_code }

    Write-Log `"退出 SD Trainer Script 版本管理脚本`"

    Exit-ManagerScript -ExitCode `$exit_code
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "version_manager.ps1")) { "更新" } else { "生成" }) version_manager.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "version_manager.ps1") -Value $content
}


# 快照管理脚本
function Write-SnapshotManagerScript {
    $content = "
param (
    [Parameter(HelpMessage=@`"
获取 SD Trainer Script Installer 的帮助信息
`"@)][switch]`$Help,

    [Parameter(HelpMessage=@`"
设置内核的路径前缀, 默认路径前缀为 core
`"@)][string]`$CorePrefix,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 更新检查
`"@)][switch]`$DisableUpdate,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 自动设置代理服务器
`"@)][switch]`$DisableProxy,

    [Parameter(HelpMessage=@`"
使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址
`"@)][string]`$UseCustomProxy,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 自动设置 GitHub 镜像源
`"@)][switch]`$DisableGithubMirror,

    [Parameter(HelpMessage=@`"
禁用 CLI 自动选择下载镜像源; 禁用后才会遵守 PyPI / GitHub / Hugging Face / 模型下载来源等手动镜像设置
`"@)][switch]`$DisableAutoMirror,

    [Parameter(HelpMessage=@`"
使用自定义的 GitHub 镜像站地址
`"@)][string]`$UseCustomGithubMirror,

    [Parameter(HelpMessage=@`"
脚本执行完成后不暂停, 直接退出
`"@)][switch]`$NoPause
)
try {
    `$config = @{
        OriginalScriptPath = `$script:PSCommandPath
        LaunchCommandLine = if (`$script:MyInvocation.Line) { `$script:MyInvocation.Line } else { `$([Environment]::CommandLine) }
        Help = `$script:Help
        CorePrefix = `$script:CorePrefix
        DisableProxy = `$script:DisableProxy
        UseCustomProxy = `$script:UseCustomProxy
        DisableGithubMirror = `$script:DisableGithubMirror
        DisableAutoMirror = `$script:DisableAutoMirror
        UseCustomGithubMirror = `$script:UseCustomGithubMirror
        DisableUpdate = `$script:DisableUpdate
        NoPause = `$script:NoPause
    }
    (Import-Module (Join-Path `$PSScriptRoot `"modules.psm1`") -Function `"Join-NormalizedPath`", `"Get-TrimmedTextFile`", `"Resolve-CorePrefix`", `"Initialize-EnvPath`", `"Write-Log`", `"Format-CommandLineArgumentForLog`", `"Format-CoreCliCommandForLog`", `"Write-CoreCliFailureCommand`", `"Set-CorePrefix`", `"Get-Version`", `"Update-Installer`", `"Set-Proxy`", `"Set-PyPIMirror`", `"Set-uv`", `"Set-GithubMirror`", `"Update-SDWebUiAllInOne`", `"Get-HelpMessage`", `"Test-PythonAndGit`", `"Get-NativeCommandExitCode`", `"Exit-ManagerScript`" -PassThru -Force -ErrorAction Stop).Invoke({
        param (`$cfg)
        `$script:OriginalScriptPath = `$cfg.OriginalScriptPath
        `$script:LaunchCommandLine = `$cfg.LaunchCommandLine
        `$script:Help = `$cfg.Help
        `$script:CorePrefix = `$cfg.CorePrefix
        `$script:DisableProxy = `$cfg.DisableProxy
        `$script:UseCustomProxy = `$cfg.UseCustomProxy
        `$script:DisableGithubMirror = `$cfg.DisableGithubMirror
        `$script:DisableAutoMirror = `$cfg.DisableAutoMirror
        `$script:UseCustomGithubMirror = `$cfg.UseCustomGithubMirror
        `$script:DisableUpdate = `$cfg.DisableUpdate
        `$script:NoPause = `$cfg.NoPause
    }, `$config)
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White -NoNewline
    Write-Host `"launch_sd_trainer_script_installer.ps1`" -ForegroundColor Yellow -NoNewline
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if ((-not `$script:BuildMode) -and (-not `$script:NoPause)) { Read-Host | Out-Null }
    exit 1
}


# 获取启动 SD WebUI All In One 内核的启动参数
function Get-LaunchCoreArgs {
    `$launch_params = New-Object System.Collections.ArrayList
    Set-uv `$launch_params
    Set-PyPIMirror `$launch_params
    Set-GithubMirror `$launch_params
    return `$launch_params
}


function Main {
    Get-HelpMessage
    Get-Version
    Set-CorePrefix
    Initialize-EnvPath
    Test-PythonAndGit
    Set-Proxy
    Update-Installer
    Update-SDWebUiAllInOne

    if (!(Test-Path (Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX))) {
        Write-Log `"内核路径 `$(Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX) 未找到, 请检查 SD Trainer Script 是否已正确安装, 或者尝试运行 SD Trainer Script Installer 进行修复`" -Level ERROR
        Exit-ManagerScript -ExitCode 1
    }

    `$launch_args = Get-LaunchCoreArgs
    `$core_cli_command = @(`"python`", `"-m`", `"sd_webui_all_in_one`", `"sd-scripts`", `"gui`", `"snapshot-manager`")
    & python -m sd_webui_all_in_one sd-scripts gui snapshot-manager `$launch_args
    `$exit_code = Get-NativeCommandExitCode -Success `$?
    if (`$exit_code -ne 0) { Write-CoreCliFailureCommand -CommandPrefix `$core_cli_command -Arguments `$launch_args -ExitCode `$exit_code }

    Write-Log `"退出 SD Trainer Script 快照管理脚本`"

    Exit-ManagerScript -ExitCode `$exit_code
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "snapshot_manager.ps1")) { "更新" } else { "生成" }) snapshot_manager.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "snapshot_manager.ps1") -Value $content
}


# SD Trainer Script Installer 设置脚本
function Write-SettingsScript {
    $content = "
param (
    [Parameter(HelpMessage=@`"
获取 SD Trainer Script Installer 的帮助信息
`"@)][switch]`$Help,

    [Parameter(HelpMessage=@`"
设置内核的路径前缀, 默认路径前缀为 core
`"@)][string]`$CorePrefix,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 自动设置代理服务器
`"@)][switch]`$DisableProxy,

    [Parameter(HelpMessage=@`"
使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址
`"@)][string]`$UseCustomProxy,

    [Parameter(HelpMessage=@`"
脚本执行完成后不暂停, 直接退出
`"@)][switch]`$NoPause
)
try {
    `$config = @{
        OriginalScriptPath = `$script:PSCommandPath
        LaunchCommandLine = if (`$script:MyInvocation.Line) { `$script:MyInvocation.Line } else { `$([Environment]::CommandLine) }
        Help = `$script:Help
        CorePrefix = `$script:CorePrefix
        DisableProxy = `$script:DisableProxy
        UseCustomProxy = `$script:UseCustomProxy
        NoPause = `$script:NoPause
    }
    (Import-Module (Join-Path `$PSScriptRoot `"modules.psm1`") -Function `"Join-NormalizedPath`", `"Get-TrimmedTextFile`", `"Resolve-CorePrefix`", `"Initialize-EnvPath`", `"Write-Log`", `"Format-CommandLineArgumentForLog`", `"Format-CoreCliCommandForLog`", `"Write-CoreCliFailureCommand`", `"Set-CorePrefix`", `"Get-Version`", `"Update-Installer`", `"Set-Proxy`", `"Write-FileWithStreamWriter`", `"Get-HelpMessage`", `"Test-PythonAndGit`", `"Get-NativeCommandExitCode`", `"Exit-ManagerScript`" -PassThru -Force -ErrorAction Stop).Invoke({
        param (`$cfg)
        `$script:OriginalScriptPath = `$cfg.OriginalScriptPath
        `$script:LaunchCommandLine = `$cfg.LaunchCommandLine
        `$script:Help = `$cfg.Help
        `$script:CorePrefix = `$cfg.CorePrefix
        `$script:DisableProxy = `$cfg.DisableProxy
        `$script:UseCustomProxy = `$cfg.UseCustomProxy
        `$script:NoPause = `$cfg.NoPause
    }, `$config)
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White -NoNewline
    Write-Host `"launch_sd_trainer_script_installer.ps1`" -ForegroundColor Yellow -NoNewline
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if (!(`$script:NoPause)) { Read-Host | Out-Null }
    exit 1
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
    `$value = Get-TrimmedTextFile (Join-NormalizedPath `$PSScriptRoot `$file) -Encoding UTF8
    if (-not [string]::IsNullOrWhiteSpace(`$value)) { return `$value }
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


# 更新网络代理设置
function Update-ProxySetting {
    while (`$true) {
        `$proxy_status = Get-TextStatus `"proxy.txt`" `$null
        `$current = if (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_proxy.txt`")) { `"禁用`" } elseif (-not [string]::IsNullOrWhiteSpace(`$proxy_status)) { `"自定义: `$proxy_status`" } else { `"系统代理`" }
        Write-Log `"当前网络代理设置: `$current`"
        Write-Log `"1. 使用系统代理 | 2. 手动输入代理地址 | 3. 禁用代理 | 4. 返回上一级`"
        `$choice = Get-UserInput
        if (`$choice -eq `"1`") { Remove-Item (Join-NormalizedPath `$PSScriptRoot `"disable_proxy.txt`"), (Join-NormalizedPath `$PSScriptRoot `"proxy.txt`") -Force -ErrorAction SilentlyContinue; break }
        elseif (`$choice -eq `"2`") {
            `$addr = Read-SingleLineSettingEditor -Prompt `"代理地址 (如 http://127.0.0.1:10809):`" -InitialText `$proxy_status
            if (`$null -eq `$addr) { Write-Log `"已取消修改代理地址`"; return }
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
        `$mirror_status = Get-TextStatus `$file `$null
        `$current = if (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_`$file`")) { `"禁用`" } elseif (-not [string]::IsNullOrWhiteSpace(`$mirror_status)) { `"自定义: `$mirror_status`" } else { `"默认`" }
        Write-Log `"当前 `$name 设置: `$current`"
        Write-Log `"1. 使用默认或自动镜像 | 2. 手动输入镜像地址 | 3. 禁用该镜像 | 4. 返回上一级`"
        `$choice = Get-UserInput
        if (`$choice -eq `"1`") { Remove-Item (Join-NormalizedPath `$PSScriptRoot `"disable_`$file`"), (Join-NormalizedPath `$PSScriptRoot `$file) -Force -ErrorAction SilentlyContinue; break }
        elseif (`$choice -eq `"2`") {
            Write-Log `"`$name 地址示例:`"
            `$examples | ForEach-Object { Write-Log `"  `$_`" -Level INFO }
            `$addr = Read-SingleLineSettingEditor -Prompt `"`$name 地址:`" -InitialText `$mirror_status
            if (`$null -eq `$addr) { Write-Log `"已取消修改`$name 地址`"; return }
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
    Write-Log `"当前 Installer 内核路径前缀: `$(Get-TextStatus `"core_prefix.txt`" `"自动选择`")`"
    Write-Log `"1. 使用自定义路径前缀 | 2. 自动选择路径前缀 | 3. 返回上一级`"
    `$choice = Get-UserInput
    if (`$choice -eq `"1`") {
        `$current_path = Get-TextStatus `"core_prefix.txt`" `$null
        `$path = Read-SingleLineSettingEditor -Prompt `"Installer 内核路径前缀或绝对路径:`" -InitialText `$current_path
        if (`$null -eq `$path) { Write-Log `"已取消修改 Installer 内核路径前缀`"; return }
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


# 更新 Hotpatcher 端口设置
function Update-Hotpatcher-Port {
    Write-Log `"当前 Hotpatcher runtime 通信端口: `$(Get-TextStatus `"hotpatcher_port.txt`" `"默认`")`"
    `$current_port = Get-TextStatus `"hotpatcher_port.txt`" `$null
    `$port_text = Read-SingleLineSettingEditor -Prompt `"Hotpatcher 运行时通信端口 (1 ~ 65535, 清空后保存可恢复默认):`" -InitialText `$current_port
    if (`$null -eq `$port_text) { Write-Log `"已取消修改 Hotpatcher runtime 通信端口`"; return }
    if ([string]::IsNullOrWhiteSpace(`$port_text)) {
        Remove-Item (Join-NormalizedPath `$PSScriptRoot `"hotpatcher_port.txt`") -Force -ErrorAction SilentlyContinue
        Write-Log `"Hotpatcher runtime 通信端口已恢复默认`"
        return
    }

    `$port_value = 0
    if ((!([int]::TryParse(`$port_text, [ref]`$port_value))) -or (`$port_value -lt 1) -or (`$port_value -gt 65535)) {
        Write-Log `"Hotpatcher runtime 通信端口无效, 可用范围为 1 ~ 65535`" -Level WARNING
        return
    }

    Set-Content -Path (Join-NormalizedPath `$PSScriptRoot `"hotpatcher_port.txt`") -Value `$port_value -Encoding UTF8
    Write-Log `"Hotpatcher runtime 通信端口设置成功`"
}


# 多行文本编辑器
function Read-MultiLineEditor {
    param (
        [string]`$Prompt,
        [string]`$InitialText = `"`"
    )

    if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected) {
        Write-Host `$Prompt -NoNewline
        return (Read-Host).Trim()
    }

    function Get-CharacterDisplayWidth {
        param ([char]`$Character)

        `$code = [int][char]`$Character
        if ([char]::IsControl(`$Character)) { return 0 }
        if ((`$code -ge 0x1100 -and `$code -le 0x115F) -or
            (`$code -ge 0x2329 -and `$code -le 0x232A) -or
            (`$code -ge 0x2E80 -and `$code -le 0xA4CF) -or
            (`$code -ge 0xAC00 -and `$code -le 0xD7A3) -or
            (`$code -ge 0xF900 -and `$code -le 0xFAFF) -or
            (`$code -ge 0xFE10 -and `$code -le 0xFE19) -or
            (`$code -ge 0xFE30 -and `$code -le 0xFE6F) -or
            (`$code -ge 0xFF00 -and `$code -le 0xFF60) -or
            (`$code -ge 0xFFE0 -and `$code -le 0xFFE6)) {
            return 2
        }
        return 1
    }

    function Get-TextDisplayWidth {
        param (
            [string]`$Text,
            [int]`$EndIndex = -1
        )

        if ([string]::IsNullOrEmpty(`$Text)) { return 0 }
        if (`$EndIndex -lt 0 -or `$EndIndex -gt `$Text.Length) { `$EndIndex = `$Text.Length }
        `$width = 0
        for (`$i = 0; `$i -lt `$EndIndex; `$i++) {
            `$width += Get-CharacterDisplayWidth `$Text[`$i]
        }
        return `$width
    }

    function Get-VisibleTextByDisplayColumn {
        param (
            [string]`$Text,
            [int]`$StartColumn,
            [int]`$MaxWidth
        )

        if ([string]::IsNullOrEmpty(`$Text) -or `$MaxWidth -le 0) { return `"`" }
        `$column = 0
        `$visible_width = 0
        `$result = [System.Text.StringBuilder]::new()
        for (`$i = 0; `$i -lt `$Text.Length; `$i++) {
            `$char_width = Get-CharacterDisplayWidth `$Text[`$i]
            `$next_column = `$column + `$char_width
            if (`$next_column -le `$StartColumn) {
                `$column = `$next_column
                continue
            }
            if (`$column -lt `$StartColumn) {
                `$column = `$next_column
                continue
            }
            if (`$visible_width + `$char_width -gt `$MaxWidth) {
                break
            }
            [void]`$result.Append(`$Text[`$i])
            `$visible_width += `$char_width
            `$column = `$next_column
        }
        return `$result.ToString()
    }

    function Get-DisplayColumnBoundary {
        param (
            [string]`$Text,
            [int]`$Column
        )

        if ([string]::IsNullOrEmpty(`$Text) -or `$Column -le 0) { return 0 }
        `$current_column = 0
        for (`$i = 0; `$i -lt `$Text.Length; `$i++) {
            `$next_column = `$current_column + (Get-CharacterDisplayWidth `$Text[`$i])
            if (`$Column -le `$next_column) {
                if (`$Column -le `$current_column) { return `$current_column }
                return `$next_column
            }
            `$current_column = `$next_column
        }
        return `$current_column
    }

    function Get-DisplayPaddedText {
        param (
            [string]`$Text,
            [int]`$Width
        )

        if (`$Width -le 0) { return `"`" }
        `$display_width = Get-TextDisplayWidth `$Text
        if (`$display_width -gt `$Width) {
            `$Text = Get-VisibleTextByDisplayColumn `$Text 0 `$Width
            `$display_width = Get-TextDisplayWidth `$Text
        }
        if (`$display_width -lt `$Width) {
            return `$Text + (`" `" * (`$Width - `$display_width))
        }
        return `$Text
    }

    `$normalized_text = `$InitialText.Replace([string][char]13 + [string][char]10, [string][char]10).Replace([string][char]13, [string][char]10)
    `$lines = [System.Collections.Generic.List[string]]::new()
    foreach (`$line in [regex]::Split(`$normalized_text, [string][char]10)) {
        [void]`$lines.Add(`$line)
    }
    if (`$lines.Count -eq 0) { [void]`$lines.Add(`"`") }

    `$cursor_row = `$lines.Count - 1
    `$cursor_col = `$lines[`$cursor_row].Length
    `$view_row = 0
    `$view_col = 0
    `$editor_height = [Math]::Max(3, [Math]::Min(10, [Console]::WindowHeight - 5))

    [Console]::WriteLine(`$Prompt)
    for (`$i = 0; `$i -lt (`$editor_height + 3); `$i++) {
        [Console]::WriteLine()
    }
    `$top_separator_row = [Math]::Max(0, [Console]::CursorTop - `$editor_height - 3)
    `$editor_top = `$top_separator_row + 1
    `$previous_frame_rows = `$null

    while (`$true) {
        `$window_width = [Math]::Max(20, [Console]::WindowWidth)
        `$render_height = [Math]::Max(1, [Math]::Min(`$editor_height, [Console]::WindowHeight - `$editor_top - 3))
        `$text_width = [Math]::Max(1, `$window_width - 3)
        `$separator = `"-`" * (`$window_width - 1)

        `$cursor_display_col = Get-TextDisplayWidth `$lines[`$cursor_row] `$cursor_col
        if (`$cursor_row -lt `$view_row) { `$view_row = `$cursor_row }
        if (`$cursor_row -ge (`$view_row + `$render_height)) { `$view_row = `$cursor_row - `$render_height + 1 }
        if (`$cursor_display_col -lt `$view_col) { `$view_col = `$cursor_display_col }
        if (`$cursor_display_col -gt (`$view_col + `$text_width)) { `$view_col = `$cursor_display_col - `$text_width }
        `$view_col = Get-DisplayColumnBoundary `$lines[`$cursor_row] `$view_col

        `$frame_rows = [System.Collections.Generic.List[string]]::new()
        [void]`$frame_rows.Add(`$separator)
        for (`$i = 0; `$i -lt `$render_height; `$i++) {
            `$line_index = `$view_row + `$i
            if (`$line_index -lt `$lines.Count) {
                `$marker = if (`$line_index -eq `$cursor_row) { `"> `" } else { `"  `" }
                `$line_text = `$lines[`$line_index]
                `$visible_text = Get-VisibleTextByDisplayColumn `$line_text `$view_col `$text_width
                `$row_text = `$marker + `$visible_text
            } else {
                `$row_text = `"`"
            }
            [void]`$frame_rows.Add((Get-DisplayPaddedText `$row_text (`$window_width - 1)))
        }

        `$status_row = `$editor_top + `$render_height
        `$help_row = `$status_row + 2
        `$cursor_status = `"行 `$(`$cursor_row + 1)/`$(`$lines.Count) | 字符 `$(`$cursor_col + 1)`"
        `$shortcut_help = `"F10/Ctrl+O 保存 | Esc 取消 | Enter 换行 | Ctrl+U 清空 | PageUp/PageDown 翻页 | Home/End/方向键移动`"
        `$cursor_status = Get-VisibleTextByDisplayColumn `$cursor_status 0 (`$window_width - 1)
        `$shortcut_help = Get-VisibleTextByDisplayColumn `$shortcut_help 0 (`$window_width - 1)
        [void]`$frame_rows.Add(`$separator)
        [void]`$frame_rows.Add((Get-DisplayPaddedText `$cursor_status (`$window_width - 1)))
        [void]`$frame_rows.Add((Get-DisplayPaddedText `$shortcut_help (`$window_width - 1)))

        `$cursor_screen_col = [Math]::Min(`$window_width - 1, 2 + (`$cursor_display_col - `$view_col))
        `$cursor_screen_row = `$editor_top + (`$cursor_row - `$view_row)
        try { [Console]::CursorVisible = `$false } catch {}
        for (`$i = 0; `$i -lt `$frame_rows.Count; `$i++) {
            if ((`$null -eq `$previous_frame_rows) -or (`$previous_frame_rows.Count -le `$i) -or (`$previous_frame_rows[`$i] -ne `$frame_rows[`$i])) {
                [Console]::SetCursorPosition(0, `$top_separator_row + `$i)
                [Console]::Write(`$frame_rows[`$i])
            }
        }
        if ((`$null -ne `$previous_frame_rows) -and (`$previous_frame_rows.Count -gt `$frame_rows.Count)) {
            for (`$i = `$frame_rows.Count; `$i -lt `$previous_frame_rows.Count; `$i++) {
                [Console]::SetCursorPosition(0, `$top_separator_row + `$i)
                [Console]::Write(`" `" * (`$window_width - 1))
            }
        }
        `$previous_frame_rows = [System.Collections.Generic.List[string]]::new()
        foreach (`$frame_row in `$frame_rows) {
            [void]`$previous_frame_rows.Add(`$frame_row)
        }
        [Console]::SetCursorPosition(`$cursor_screen_col, `$cursor_screen_row)
        try { [Console]::CursorVisible = `$true } catch {}

        `$key = [Console]::ReadKey(`$true)
        if (`$key.Key -eq [ConsoleKey]::F10) {
            try { [Console]::CursorVisible = `$true } catch {}
            [Console]::SetCursorPosition(0, `$help_row)
            [Console]::WriteLine()
            return ([string]::Join([Environment]::NewLine, `$lines)).Trim()
        }
        if (((`$key.Modifiers -band [ConsoleModifiers]::Control) -ne 0) -and (`$key.Key -eq [ConsoleKey]::O)) {
            try { [Console]::CursorVisible = `$true } catch {}
            [Console]::SetCursorPosition(0, `$help_row)
            [Console]::WriteLine()
            return ([string]::Join([Environment]::NewLine, `$lines)).Trim()
        }
        if (((`$key.Modifiers -band [ConsoleModifiers]::Control) -ne 0) -and (`$key.Key -eq [ConsoleKey]::U)) {
            `$lines.Clear()
            [void]`$lines.Add(`"`")
            `$cursor_row = 0
            `$cursor_col = 0
            `$view_row = 0
            `$view_col = 0
            continue
        }
        if (((`$key.Modifiers -band [ConsoleModifiers]::Control) -ne 0) -and (`$key.Key -eq [ConsoleKey]::A)) {
            `$cursor_col = 0
            continue
        }
        if (((`$key.Modifiers -band [ConsoleModifiers]::Control) -ne 0) -and (`$key.Key -eq [ConsoleKey]::E)) {
            `$cursor_col = `$lines[`$cursor_row].Length
            continue
        }

        switch (`$key.Key) {
            ([ConsoleKey]::Enter) {
                `$line = `$lines[`$cursor_row]
                `$before = `$line.Substring(0, `$cursor_col)
                `$after = `$line.Substring(`$cursor_col)
                `$lines[`$cursor_row] = `$before
                `$lines.Insert(`$cursor_row + 1, `$after)
                `$cursor_row++
                `$cursor_col = 0
            }
            ([ConsoleKey]::Escape) {
                try { [Console]::CursorVisible = `$true } catch {}
                [Console]::SetCursorPosition(0, `$help_row)
                [Console]::WriteLine()
                return `$null
            }
            ([ConsoleKey]::LeftArrow) {
                if (`$cursor_col -gt 0) {
                    `$cursor_col--
                } elseif (`$cursor_row -gt 0) {
                    `$cursor_row--
                    `$cursor_col = `$lines[`$cursor_row].Length
                }
            }
            ([ConsoleKey]::RightArrow) {
                if (`$cursor_col -lt `$lines[`$cursor_row].Length) {
                    `$cursor_col++
                } elseif (`$cursor_row -lt (`$lines.Count - 1)) {
                    `$cursor_row++
                    `$cursor_col = 0
                }
            }
            ([ConsoleKey]::UpArrow) {
                if (`$cursor_row -gt 0) {
                    `$cursor_row--
                    `$cursor_col = [Math]::Min(`$cursor_col, `$lines[`$cursor_row].Length)
                }
            }
            ([ConsoleKey]::DownArrow) {
                if (`$cursor_row -lt (`$lines.Count - 1)) {
                    `$cursor_row++
                    `$cursor_col = [Math]::Min(`$cursor_col, `$lines[`$cursor_row].Length)
                }
            }
            ([ConsoleKey]::PageUp) {
                `$page_size = [Math]::Max(1, `$render_height)
                `$cursor_row = [Math]::Max(0, `$cursor_row - `$page_size)
                `$cursor_col = [Math]::Min(`$cursor_col, `$lines[`$cursor_row].Length)
                `$view_row = [Math]::Max(0, `$view_row - `$page_size)
            }
            ([ConsoleKey]::PageDown) {
                `$page_size = [Math]::Max(1, `$render_height)
                `$cursor_row = [Math]::Min(`$lines.Count - 1, `$cursor_row + `$page_size)
                `$cursor_col = [Math]::Min(`$cursor_col, `$lines[`$cursor_row].Length)
                `$max_view_row = [Math]::Max(0, `$lines.Count - `$render_height)
                `$view_row = [Math]::Min(`$max_view_row, `$view_row + `$page_size)
            }
            ([ConsoleKey]::Home) { `$cursor_col = 0 }
            ([ConsoleKey]::End) { `$cursor_col = `$lines[`$cursor_row].Length }
            ([ConsoleKey]::Backspace) {
                if (`$cursor_col -gt 0) {
                    `$line = `$lines[`$cursor_row]
                    `$lines[`$cursor_row] = `$line.Remove(`$cursor_col - 1, 1)
                    `$cursor_col--
                } elseif (`$cursor_row -gt 0) {
                    `$previous_length = `$lines[`$cursor_row - 1].Length
                    `$lines[`$cursor_row - 1] = `$lines[`$cursor_row - 1] + `$lines[`$cursor_row]
                    `$lines.RemoveAt(`$cursor_row)
                    `$cursor_row--
                    `$cursor_col = `$previous_length
                }
            }
            ([ConsoleKey]::Delete) {
                if (`$cursor_col -lt `$lines[`$cursor_row].Length) {
                    `$line = `$lines[`$cursor_row]
                    `$lines[`$cursor_row] = `$line.Remove(`$cursor_col, 1)
                } elseif (`$cursor_row -lt (`$lines.Count - 1)) {
                    `$lines[`$cursor_row] = `$lines[`$cursor_row] + `$lines[`$cursor_row + 1]
                    `$lines.RemoveAt(`$cursor_row + 1)
                }
            }
            default {
                if (-not [char]::IsControl(`$key.KeyChar)) {
                    `$line = `$lines[`$cursor_row]
                    `$lines[`$cursor_row] = `$line.Insert(`$cursor_col, `$key.KeyChar)
                    `$cursor_col++
                }
            }
        }
    }
}


# 单行文本设置编辑器
function Read-SingleLineSettingEditor {
    param (
        [string]`$Prompt,
        [string]`$InitialText = `"`"
    )

    `$value = Read-MultiLineEditor -Prompt `$Prompt -InitialText `$InitialText
    if (`$null -eq `$value) { return `$null }

    `$normalized_value = `$value.Replace([string][char]13 + [string][char]10, [string][char]10).Replace([string][char]13, [string][char]10)
    `$line_values = @(
        [regex]::Split(`$normalized_value, [string][char]10) |
            ForEach-Object { `$_.Trim() } |
            Where-Object { -not [string]::IsNullOrWhiteSpace(`$_) }
    )

    if (`$line_values.Count -gt 1) {
        Write-Log `"该设置只支持单行文本, 已使用第一行内容`" -Level WARNING
    }
    if (`$line_values.Count -eq 0) { return `"`" }
    return `$line_values[0]
}


# 更新启动参数
function Update-LaunchArgs {
    `$path = Join-NormalizedPath `$PSScriptRoot `"launch_args.txt`"
    `$current_args = Get-TrimmedTextFile `$path -Encoding UTF8
    Write-Log `"编辑应用启动参数: F10/Ctrl+O 保存, Esc 取消, Enter 换行, Ctrl+U 清空, PageUp/PageDown 翻页, Home/End/方向键移动`"
    `$launch_args = Read-MultiLineEditor -Prompt `"启动参数:`" -InitialText `$current_args
    if (`$null -eq `$launch_args) {
        Write-Log `"已取消修改应用启动参数`"
        return
    }
    if (-not [string]::IsNullOrWhiteSpace(`$launch_args)) {
        Write-FileWithStreamWriter -Path `$path -Value `$launch_args -Encoding UTF8
        Write-Log `"应用启动参数已保存`"
    } else {
        Remove-Item `$path -Force -ErrorAction SilentlyContinue
        Write-Log `"应用启动参数已清空`"
    }
}


# 打开 Hotpatcher 配置管理 GUI
function Open-Hotpatcher-Gui {
    `$config_path = Join-NormalizedPath `$PSScriptRoot `"patcher_config.json`"
    if (!(Test-Path `$config_path)) {
        Write-Log `"未找到 Hotpatcher 默认配置文件, 正在导出默认配置到 `$config_path`"
        & python -m sd_webui_all_in_one self-manager patcher export-config
        `$exit_code = Get-NativeCommandExitCode -Success `$?
        if (`$exit_code -ne 0) {
            Write-Log `"导出 Hotpatcher 默认配置失败`" -Level ERROR
            return
        }
    }

    Write-Log `"正在打开 Hotpatcher 补丁系统 GUI: `$config_path`"
    & python -m sd_webui_all_in_one self-manager patcher gui --config `"`$config_path`"
    `$exit_code = Get-NativeCommandExitCode -Success `$?
    if (`$exit_code -ne 0) {
        Write-Log `"Hotpatcher 补丁系统 GUI 退出异常: `$exit_code`" -Level WARNING
    }
}


# 获取用户输入
function Get-UserInput {
    return (Read-Host `"============================================>`").Trim()
}


function Main {
    Get-HelpMessage
    Get-Version
    Set-CorePrefix
    Initialize-EnvPath
    Test-PythonAndGit
    Set-Proxy -Legacy

    while (`$true) {
        Write-Log `"=== SD Trainer Script 本地设置菜单 ===`"
        `$menu = @(
            @{ id=0;  n=`"自动选择下载镜像源`"; v=`$(Get-ToggleStatus `"disable_auto_mirror.txt`" `"启用`" `"禁用`" `$true) },
            @{ id=1;  n=`"网络代理设置`"; v=`$(if (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_proxy.txt`")) { `"禁用`" } else { `$proxy_status = Get-TextStatus `"proxy.txt`" `$null; if (-not [string]::IsNullOrWhiteSpace(`$proxy_status)) { `"手动设置 (地址: `$proxy_status)`" } else { `"使用系统代理`" } }) },
            @{ id=2;  n=`"Python 包管理器`"; v=`$(Get-ToggleStatus `"disable_uv.txt`" `"Pip`" `"uv`") },
            @{ id=3;  n=`"Hugging Face 下载镜像源`"; v=`$(Get-ToggleStatus `"disable_hf_mirror.txt`" `"启用`" `"禁用`" `$true) },
            @{ id=4;  n=`"GitHub 下载镜像源`"; v=`$(Get-ToggleStatus `"disable_gh_mirror.txt`" `"启用`" `"禁用`" `$true) },
            @{ id=5;  n=`"自动检查 Installer 更新`"; v=`$(Get-ToggleStatus `"disable_update.txt`" `"启用`" `"禁用`" `$true) },
            @{ id=6;  n=`"模型下载来源`"; v=`$(Get-ToggleStatus `"disable_model_mirror.txt`" `"ModelScope`" `"Hugging Face`" `$true) },
            @{ id=7;  n=`"应用启动参数`"; v=`$(Get-TextStatus `"launch_args.txt`") },
            @{ id=8;  n=`"PyPI 软件包镜像`"; v=`$(Get-ToggleStatus `"disable_pypi_mirror.txt`" `"启用`" `"禁用`" `$true) },
            @{ id=9;  n=`"PyTorch CUDA 内存分配优化`"; v=`$(Get-ToggleStatus `"disable_set_pytorch_cuda_memory_alloc.txt`" `"启用`" `"禁用`" `$true) },
            @{ id=10; n=`"启动前环境检测`"; v=`$(Get-ToggleStatus `"disable_check_env.txt`" `"启用`" `"禁用`" `$true) },
            @{ id=11; n=`"Installer 内核路径前缀`"; v=`$(Get-TextStatus `"core_prefix.txt`" `"自动`") },
            @{ id=12; n=`"Hotpatcher 补丁系统`"; v=`$(Get-ToggleStatus `"disable_hotpatcher.txt`" `"启用`" `"禁用`" `$true) },
            @{ id=13; n=`"Hotpatcher 运行时服务`"; v=`$(Get-ToggleStatus `"enable_hotpatcher_runtime.txt`" `"启用`" `"禁用`") },
            @{ id=14; n=`"Hotpatcher 运行时端口`"; v=`$(Get-TextStatus `"hotpatcher_port.txt`" `"默认`") },
            @{ id=15; n=`"自动快照`"; v=`$(Get-ToggleStatus `"disable_snapshot.txt`" `"启用`" `"禁用`" `$true) },
            @{ id=16; n=`"打开 Hotpatcher 补丁系统 GUI`" }
        )

        `$menu | ForEach-Object {
            if (`$_.ContainsKey(`"v`")) {
                Write-Log `"`$(`$_.id). `$(`$_.n): `$(`$_.v)`"
            } else {
                Write-Log `"`$(`$_.id). `$(`$_.n)`"
            }
        }
        Write-Log `"17. 立即检查 Installer 更新 | 18. 打开在线文档 | 19. 退出设置`"
        Write-Log `"提示: 输入菜单编号后回车`"

        `$choice = Get-UserInput
        switch (`$choice) {
            `"0`"  { Write-Log `"提示: 启用「自动选择下载镜像源」时, PyPI、GitHub、Hugging Face、模型下载来源等手动镜像设置会被 Python CLI 自动覆盖; 如需手动调整这些设置, 请先禁用本项`"; Set-ToggleSetting `"disable_auto_mirror.txt`" `"自动选择下载镜像源`" (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_auto_mirror.txt`")) }
            `"1`"  { Update-ProxySetting }
            `"2`"  { Set-ToggleSetting `"disable_uv.txt`" `"Python 包管理器`" (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_uv.txt`")) }
            `"3`"  { Update-Mirror-Setting `"hf_mirror.txt`" `"Hugging Face 下载镜像源`" @(`"https://hf-mirror.com`", `"https://huggingface.sukaka.top`") }
            `"4`"  { Update-Mirror-Setting `"gh_mirror.txt`" `"GitHub 下载镜像源`" @(`"https://ghfast.top/https://github.com`", `"https://mirror.ghproxy.com/https://github.com`") }
            `"5`"  { Set-ToggleSetting `"disable_update.txt`" `"自动检查 Installer 更新`" (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_update.txt`")) }
            `"6`"  { Set-ToggleSetting `"disable_model_mirror.txt`" `"模型下载来源`" (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_model_mirror.txt`")) }
            `"7`"  { Update-LaunchArgs }
            `"8`"  { Set-ToggleSetting `"disable_pypi_mirror.txt`" `"PyPI 软件包镜像`" (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_pypi_mirror.txt`")) }
            `"9`"  { Set-ToggleSetting `"disable_set_pytorch_cuda_memory_alloc.txt`" `"PyTorch CUDA 内存分配优化`" (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_set_pytorch_cuda_memory_alloc.txt`")) }
            `"10`" { Set-ToggleSetting `"disable_check_env.txt`" `"启动前环境检测`" (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_check_env.txt`")) }
            `"11`" { Update-Core-Prefix }
            `"12`" { Set-ToggleSetting `"disable_hotpatcher.txt`" `"Hotpatcher 补丁系统`" (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_hotpatcher.txt`")) }
            `"13`" { Set-ToggleSetting `"enable_hotpatcher_runtime.txt`" `"Hotpatcher 运行时服务`" (!(Test-Path (Join-NormalizedPath `$PSScriptRoot `"enable_hotpatcher_runtime.txt`"))) }
            `"14`" { Update-Hotpatcher-Port }
            `"15`" { Set-ToggleSetting `"disable_snapshot.txt`" `"自动快照`" (Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_snapshot.txt`")) }
            `"16`" { Open-Hotpatcher-Gui }
            `"17`" { Remove-Item (Join-NormalizedPath `$PSScriptRoot `"update_time.txt`") -Force -ErrorAction SilentlyContinue; Update-Installer -DisableRestart }
            `"18`" { Start-Process `"https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/`" }
            `"19`" { Write-Log `"退出设置菜单`"; return }
        }
    }
    if (!(`$script:NoPause)) { Read-Host | Out-Null }
}

###################

Main
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "settings.ps1")) { "更新" } else { "生成" }) settings.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "settings.ps1") -Value $content
}

# 虚拟环境激活脚本
function Write-EnvActivateScript {
    $content = "
param (
    [Parameter(HelpMessage=@`"
获取 SD Trainer Script Installer 的帮助信息
`"@)][switch]`$Help,

    [Parameter(HelpMessage=@`"
设置内核的路径前缀, 默认路径前缀为 core
`"@)][string]`$CorePrefix,

    [Parameter(HelpMessage=@`"
禁用 PyPI 软件包镜像源, 使用 PyPI 官方源下载 Python 软件包
`"@)][switch]`$DisablePyPIMirror,

    [Parameter(HelpMessage=@`"
禁用 CLI 自动选择下载镜像源; 禁用后才会遵守 PyPI / GitHub / Hugging Face / 模型下载来源等手动镜像设置
`"@)][switch]`$DisableAutoMirror,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 自动设置 GitHub 镜像源
`"@)][switch]`$DisableGithubMirror,

    [Parameter(HelpMessage=@`"
使用自定义的 GitHub 镜像站地址
`"@)][string]`$UseCustomGithubMirror,

    [Parameter(HelpMessage=@`"
禁用 SD Trainer Script Installer 自动设置代理服务器
`"@)][switch]`$DisableProxy,

    [Parameter(HelpMessage=@`"
使用自定义的代理服务器地址, 例如代理服务器地址为 http://127.0.0.1:10809, 则使用 -UseCustomProxy ```"http://127.0.0.1:10809```" 设置代理服务器地址
`"@)][string]`$UseCustomProxy,

    [Parameter(HelpMessage=@`"
禁用 Hugging Face 镜像源, 不使用 Hugging Face 镜像源下载文件
`"@)][switch]`$DisableHuggingFaceMirror,

    [Parameter(HelpMessage=@`"
使用自定义 Hugging Face 镜像源地址, 例如代理服务器地址为 https://hf-mirror.com, 则使用 -UseCustomHuggingFaceMirror ```"https://hf-mirror.com```" 设置 Hugging Face 镜像源地址
`"@)][string]`$UseCustomHuggingFaceMirror,

    [Parameter(HelpMessage=@`"
脚本执行完成后不暂停, 直接退出
`"@)][switch]`$NoPause
)
try {
    `$config = @{
        OriginalScriptPath = `$script:PSCommandPath
        LaunchCommandLine = if (`$script:MyInvocation.Line) { `$script:MyInvocation.Line } else { `$([Environment]::CommandLine) }
        Help = `$script:Help
        CorePrefix = `$script:CorePrefix
        DisablePyPIMirror = `$script:DisablePyPIMirror
        DisableAutoMirror = `$script:DisableAutoMirror
        DisableGithubMirror = `$script:DisableGithubMirror
        UseCustomGithubMirror = `$script:UseCustomGithubMirror
        DisableProxy = `$script:DisableProxy
        UseCustomProxy = `$script:UseCustomProxy
        DisableHuggingFaceMirror = `$script:DisableHuggingFaceMirror
        UseCustomHuggingFaceMirror = `$script:UseCustomHuggingFaceMirror
        NoPause = `$script:NoPause
    }
    (Import-Module (Join-Path `$PSScriptRoot `"modules.psm1`") -Function `"Join-NormalizedPath`", `"Get-TrimmedTextFile`", `"Resolve-CorePrefix`", `"Initialize-EnvPath`", `"Write-Log`", `"Format-CommandLineArgumentForLog`", `"Format-CoreCliCommandForLog`", `"Write-CoreCliFailureCommand`", `"Set-CorePrefix`", `"Get-Version`", `"Set-Proxy`", `"Get-NormalizedFilePath`", `"Get-HelpMessage`", `"Test-PythonAndGit`", `"Get-NativeCommandExitCode`", `"Exit-ManagerScript`" -PassThru -Force -ErrorAction Stop).Invoke({
        param (`$cfg)
        `$script:OriginalScriptPath = `$cfg.OriginalScriptPath
        `$script:LaunchCommandLine = `$cfg.LaunchCommandLine
        `$script:Help = `$cfg.Help
        `$script:CorePrefix = `$cfg.CorePrefix
        `$script:DisablePyPIMirror = `$cfg.DisablePyPIMirror
        `$script:DisableAutoMirror = `$cfg.DisableAutoMirror
        `$script:DisableGithubMirror = `$cfg.DisableGithubMirror
        `$script:UseCustomGithubMirror = `$cfg.UseCustomGithubMirror
        `$script:DisableProxy = `$cfg.DisableProxy
        `$script:UseCustomProxy = `$cfg.UseCustomProxy
        `$script:DisableHuggingFaceMirror = `$cfg.DisableHuggingFaceMirror
        `$script:UseCustomHuggingFaceMirror = `$cfg.UseCustomHuggingFaceMirror
        `$script:NoPause = `$cfg.NoPause
    }, `$config)
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White -NoNewline
    Write-Host `"launch_sd_trainer_script_installer.ps1`" -ForegroundColor Yellow -NoNewline
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if (!(`$script:NoPause)) { Read-Host | Out-Null }
    exit 1
}


# PyPI 软件包镜像源
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
`$env:SD_SCRIPTS_PATH = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX
`$Env:SD_TRAINER_SCRIPT_INSTALLER_ROOT = `$PSScriptRoot


# 提示符信息
function global:prompt {
    `"`$(Write-Host `"[SD Trainer Script Env]`" -ForegroundColor Green -NoNewLine) `$(Get-Location)> `"
}


function global:pip {
    python -m pip @args
}

function global:sd-webui-all-in-one {
    & python -m sd_webui_all_in_one @args
}

Set-Alias pip3 pip
Set-Alias python3 python


# 列出 SD Trainer Script Installer 内置命令
function global:List-CMD {
    Write-Host `"
==================================
SD Trainer Script Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
==================================

当前可用的 SD Trainer Script Installer 内置命令：

    List-CMD

更多帮助信息可在 SD Trainer Script Installer 文档中查看: https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/
`"
}


# PyPI 软件包镜像源状态
function Get-PyPIMirrorStatus {
    if (`$USE_PIP_MIRROR) {
        Write-Log `"使用 PyPI 软件包镜像源`"
    } else {
        Write-Log `"检测到 disable_pypi_mirror.txt 配置文件 / -DisablePyPIMirror, 命令行参数 已将 PyPI 源切换至官方源`"
    }
}


# Hugging Face 镜像源
function Set-HuggingFaceMirror {
    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_hf_mirror.txt`")) -or (`$script:DisableHuggingFaceMirror)) { # 检测是否禁用了自动设置 Hugging Face 镜像源
        Write-Log `"检测到本地存在 disable_hf_mirror.txt 镜像源配置文件 / -DisableHuggingFaceMirror 命令行参数, 禁用自动设置 Hugging Face 镜像源`"
        return
    }

    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"hf_mirror.txt`")) -or (`$script:UseCustomHuggingFaceMirror)) { # 本地存在 Hugging Face 镜像源配置
        if (`$script:UseCustomHuggingFaceMirror) {
            `$hf_mirror_value = `$script:UseCustomHuggingFaceMirror
        } else {
            `$hf_mirror_value = Get-TrimmedTextFile (Join-NormalizedPath `$PSScriptRoot `"hf_mirror.txt`") -Encoding UTF8
        }
        if (-not [string]::IsNullOrWhiteSpace(`$hf_mirror_value)) {
            `$env:HF_ENDPOINT = `$hf_mirror_value
            Write-Log `"检测到本地存在 hf_mirror.txt 配置文件 / -UseCustomHuggingFaceMirror 命令行参数, 已读取该配置并设置 Hugging Face 镜像源`"
        } else {
            `$env:HF_ENDPOINT = `"https://hf-mirror.com`"
            Write-Log `"使用默认 Hugging Face 镜像源`"
        }
    } else { # 使用默认设置
        `$env:HF_ENDPOINT = `"https://hf-mirror.com`"
        Write-Log `"使用默认 Hugging Face 镜像源`"
    }
}


# GitHub 镜像源
function Set-GithubMirrorLegecy {
    `$env:GIT_CONFIG_GLOBAL = Join-NormalizedPath `$PSScriptRoot `".gitconfig`" # 设置 Git 配置文件路径
    if (Test-Path (Join-NormalizedPath `$PSScriptRoot `".gitconfig`")) {
        Remove-Item -Path (Join-NormalizedPath `$PSScriptRoot `".gitconfig`") -Force -Recurse
    }
    # 默认 Git 配置
    git config --global --add safe.directory '*'
    git config --global core.longpaths true

    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"disable_gh_mirror.txt`")) -or (`$script:DisableGithubMirror)) { # 禁用 GitHub 镜像源
        Write-Log `"检测到本地存在 disable_gh_mirror.txt GitHub 镜像源配置文件 / -DisableGithubMirror 命令行参数, 禁用 GitHub 镜像源`"
        return
    }

    # 使用自定义 GitHub 镜像源
    if ((Test-Path (Join-NormalizedPath `$PSScriptRoot `"gh_mirror.txt`")) -or (`$script:UseCustomGithubMirror)) {
        if (`$script:UseCustomGithubMirror) {
            `$github_mirror = `$script:UseCustomGithubMirror
        } else {
            `$github_mirror = Get-TrimmedTextFile (Join-NormalizedPath `$PSScriptRoot `"gh_mirror.txt`") -Encoding UTF8
        }
        if (-not [string]::IsNullOrWhiteSpace(`$github_mirror)) {
            git config --global url.`"`$github_mirror`".insteadOf `"https://github.com`"
            Write-Log `"检测到本地存在 gh_mirror.txt GitHub 镜像源配置文件 / -UseCustomGithubMirror 命令行参数, 已读取 GitHub 镜像源配置文件并设置 GitHub 镜像源`"
        }
    }
}


function Main {
    Get-HelpMessage
    Get-Version
    Set-CorePrefix
    Initialize-EnvPath
    Test-PythonAndGit
    Set-Proxy -Legacy
    Set-HuggingFaceMirror
    Set-GithubMirrorLegecy
    Get-PyPIMirrorStatus

    if (Get-Command Set-PSReadLineKeyHandler -ErrorAction SilentlyContinue) {
        Set-PSReadLineKeyHandler -Chord Ctrl+d -ScriptBlock {
            [Microsoft.PowerShell.PSConsoleReadLine]::RevertLine()
            [Microsoft.PowerShell.PSConsoleReadLine]::Insert(`"exit`")
            [Microsoft.PowerShell.PSConsoleReadLine]::AcceptLine()
        }
    }

    `$python_cmd = Get-Command python -ErrorAction SilentlyContinue
    if (`$python_cmd) {
        `$python_path_prefix = Join-NormalizedPath `$PSScriptRoot `"python`"
        `$python_extra_path_prefix = Join-NormalizedPath `$PSScriptRoot `$env:CORE_PREFIX `"python`"
        `$python_cmd = Get-NormalizedFilePath `$python_cmd.Path
        if ((`$python_cmd) -and ((`$python_cmd.ToString().StartsWith(`$python_path_prefix, [System.StringComparison]::OrdinalIgnoreCase)) -or (`$python_cmd.ToString().StartsWith(`$python_extra_path_prefix, [System.StringComparison]::OrdinalIgnoreCase)))) {
            `$env:UV_PYTHON = `$python_cmd
        }
    }

    Write-Log `"激活 SD Trainer Script Env`"
    Write-Log `"更多帮助信息可在 SD Trainer Script Installer 项目地址查看: https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/`"
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
param(
    [switch]`$Help,
    [switch]`$NoPause,
    [Parameter(ValueFromRemainingArguments=`$true)]
    [string[]]`$Arguments
)
try {
    `$config = @{
        OriginalScriptPath = `$script:PSCommandPath
        LaunchCommandLine = if (`$script:MyInvocation.Line) { `$script:MyInvocation.Line } else { `$([Environment]::CommandLine) }
        Help = `$script:Help
        NoPause = `$script:NoPause
    }
    (Import-Module (Join-Path `$PSScriptRoot `"modules.psm1`") -Function `"Join-NormalizedPath`", `"Write-Log`" -PassThru -Force -ErrorAction Stop).Invoke({
        param (`$cfg)
        `$script:OriginalScriptPath = `$cfg.OriginalScriptPath
        `$script:LaunchCommandLine = `$cfg.LaunchCommandLine
        `$script:Help = `$cfg.Help
        `$script:NoPause = `$cfg.NoPause
    }, `$config)
}
catch {
    Write-Error `"导入 Installer 模块发生错误: `$_`"
    Write-Host `"这可能是 Installer 文件出现了损坏, 请运行 `" -ForegroundColor White -NoNewline
    Write-Host `"launch_sd_trainer_script_installer.ps1`" -ForegroundColor Yellow -NoNewline
    Write-Host `" 脚本修复该问题`" -ForegroundColor White
    if (!(`$script:NoPause)) { Read-Host | Out-Null }
    exit 1
}
`$pass_args = @()
if (`$script:NoPause) { `$pass_args += `"-NoPause`" }
if (`$script:Help) { `$pass_args += `"-Help`" }
if (`$Arguments) { `$pass_args += `$Arguments }
if (`$script:Help) {
    & `"`$((Get-Process -Id `$PID).Path)`" -File `"`$(Join-NormalizedPath `$PSScriptRoot `"activate.ps1`")`" @pass_args
} else {
    Write-Log `"执行 SD Trainer Script Installer 激活环境脚本`"
    & `"`$((Get-Process -Id `$PID).Path)`" -NoExit -File `"`$(Join-NormalizedPath `$PSScriptRoot `"activate.ps1`")`" @pass_args
}
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "terminal.ps1")) { "更新" } else { "生成" }) terminal.ps1 中"
    Write-FileWithStreamWriter -Encoding UTF8BOM -Path (Join-NormalizedPath $script:InstallPath "terminal.ps1") -Value $content
}


# 帮助文档
function Write-ReadMe {
    $content = "
====================================================================
SD Trainer Script Installer created by licyk
哔哩哔哩：https://space.bilibili.com/46497516
Github：https://github.com/licyk
====================================================================
########## 安装后速查 ##########

这是 SD Trainer Script 的安装后速查说明。完整安装、初始化、训练脚本、模型、更新和故障排查说明请阅读文档站。
SD Trainer Script Installer 文档：https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/

一、安装完成后先做什么
1. 先运行 init.ps1 初始化训练环境。
2. 编辑 train.ps1 写入训练命令，再运行 train.ps1 开始训练。
3. 训练命令写法请阅读：https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/advanced/#%E7%BC%96%E5%86%99%E8%AE%AD%E7%BB%83%E8%84%9A%E6%9C%AC
4. 需要训练用模型时运行 download_models.ps1；模型放置位置和推荐资源见模型与资源文档。
5. 需要执行 Python、Pip、Git 命令时运行 terminal.ps1，或先运行 activate.ps1 激活环境。

二、常用脚本速查
- init.ps1：初始化 SD Trainer Script 运行环境。
- train.ps1：训练命令脚本，按文档修改后运行。
- update.ps1：更新 SD Trainer Script 和管理脚本。
- download_models.ps1：下载训练用模型到 models 目录。
- reinstall_pytorch.ps1：PyTorch 损坏、版本不匹配或需要切换 CUDA / ROCm / XPU 版本时使用。
- switch_branch.ps1：切换 sd-scripts、ai-toolkit、finetrainers、diffusion-pipe、musubi-tuner 等训练后端。
- version_manager.ps1：管理 SD Trainer Script 版本。
- snapshot_manager.ps1：创建和恢复当前环境快照。
- settings.ps1：调整网络代理、下载镜像、Python 包管理器、应用启动参数、Installer 内核路径前缀等本地设置。
- terminal.ps1：打开已配置好的 PowerShell 终端。
- activate.ps1：在当前终端激活安装器环境。
- launch_sd_trainer_script_installer.ps1：重新获取并运行最新 SD Trainer Script Installer。
- configure_env.bat：修复 Windows 运行 .ps1 后立刻闪退、PowerShell 脚本运行限制和长路径支持问题。

三、目录说明
- cache：Pip / Hugging Face 等缓存目录。
- python：安装器自带 Python。请勿添加到系统环境变量。
- git：安装器自带 Git。
- core：训练脚本程序和主要数据目录。

四、遇到问题
- Windows 下运行 .ps1 后立刻闪退：先运行 configure_env.bat，再重新运行原脚本。
- 初始化、训练、安装或更新报错：https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/troubleshooting/
- 不确定脚本参数：https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/commands/
- 下载器或 Launcher 出错：https://licyk.github.io/sd-webui-all-in-one/tools/troubleshooting/

五、详细文档
- 启动与使用：https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/usage/
- 模型与资源：https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/resources/
- 配置与镜像：https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/config/
- 维护与迁移：https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/maintenance/
- 高级功能：https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/advanced/
- 常用命令：https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/commands/
- Windows GUI Launcher：https://licyk.github.io/sd-webui-all-in-one/tools/launcher-gui/
- Bash TUI / CLI Launcher：https://licyk.github.io/sd-webui-all-in-one/tools/launcher-tui/

====================================================================
########## GitHub 项目 ##########

sd-webui-all-in-one 项目地址：https://github.com/licyk/sd-webui-all-in-one
sd-scripts 项目地址：https://github.com/kohya-ss/sd-scripts
支持的训练后端列表：https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/


====================================================================
########## 用户协议 ##########

使用该整合包代表您已阅读并同意以下用户协议：
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
    Write-InitScript
    Write-TrainScript
    Write-UpdateScript
    Write-SwitchBranchScript
    Write-LaunchInstallerScript
    Write-PyTorchReInstallScript
    Write-DownloadModelScript
    Write-VersionManagerScript
    Write-SnapshotManagerScript
    Write-SettingsScript
    Write-EnvActivateScript
    Write-LaunchTerminalScript
    Write-ReadMe
    Write-ConfigureEnvScript
}


# 将安装器配置文件复制到管理脚本路径
function Copy-InstallerConfig {
    if ((!($script:DisableAutoMirror)) -and (Test-Path (Join-NormalizedPath $PSScriptRoot "disable_auto_mirror.txt"))) {
        Copy-Item -Path (Join-NormalizedPath $PSScriptRoot "disable_auto_mirror.txt") -Destination $script:InstallPath -Force
        Write-Log "$(Join-NormalizedPath $PSScriptRoot "disable_auto_mirror.txt") -> $(Join-NormalizedPath $script:InstallPath "disable_auto_mirror.txt")"
    }
    Write-Log "为 SD Trainer Script Installer 管理脚本复制 SD Trainer Script Installer 配置文件中"

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

    if ((!($script:DisableModelMirror)) -and (Test-Path (Join-NormalizedPath $PSScriptRoot "disable_model_mirror.txt"))) {
        Copy-Item -Path (Join-NormalizedPath $PSScriptRoot "disable_model_mirror.txt") -Destination $script:InstallPath -Force
        Write-Log "$(Join-NormalizedPath $PSScriptRoot "disable_model_mirror.txt") -> $(Join-NormalizedPath $script:InstallPath "disable_model_mirror.txt")"
    }

    if ((!($script:DisableHotpatcher)) -and (Test-Path (Join-NormalizedPath $PSScriptRoot "disable_hotpatcher.txt"))) {
        Copy-Item -Path (Join-NormalizedPath $PSScriptRoot "disable_hotpatcher.txt") -Destination $script:InstallPath -Force
        Write-Log "$(Join-NormalizedPath $PSScriptRoot "disable_hotpatcher.txt") -> $(Join-NormalizedPath $script:InstallPath "disable_hotpatcher.txt")"
    }

    if ((!($script:EnableHotpatcherRuntime)) -and (Test-Path (Join-NormalizedPath $PSScriptRoot "enable_hotpatcher_runtime.txt"))) {
        Copy-Item -Path (Join-NormalizedPath $PSScriptRoot "enable_hotpatcher_runtime.txt") -Destination $script:InstallPath -Force
        Write-Log "$(Join-NormalizedPath $PSScriptRoot "enable_hotpatcher_runtime.txt") -> $(Join-NormalizedPath $script:InstallPath "enable_hotpatcher_runtime.txt")"
    }



    if ((!($script:HotpatcherPortProvided)) -and (Test-Path (Join-NormalizedPath $PSScriptRoot "hotpatcher_port.txt"))) {
        Copy-Item -Path (Join-NormalizedPath $PSScriptRoot "hotpatcher_port.txt") -Destination $script:InstallPath -Force
        Write-Log "$(Join-NormalizedPath $PSScriptRoot "hotpatcher_port.txt") -> $(Join-NormalizedPath $script:InstallPath "hotpatcher_port.txt")"
    }


    if ((!($script:DisableSnapshot)) -and (Test-Path (Join-NormalizedPath $PSScriptRoot "disable_snapshot.txt"))) {
        Copy-Item -Path (Join-NormalizedPath $PSScriptRoot "disable_snapshot.txt") -Destination $script:InstallPath -Force
        Write-Log "$(Join-NormalizedPath $PSScriptRoot "disable_snapshot.txt") -> $(Join-NormalizedPath $script:InstallPath "disable_snapshot.txt")"
    }
    $hotpatcher_config_source = Join-NormalizedPath $PSScriptRoot "patcher_config.json"
    if (Test-Path $hotpatcher_config_source) {
        Copy-Item -Path $hotpatcher_config_source -Destination (Join-NormalizedPath $script:InstallPath "patcher_config.json") -Force
        Write-Log "$hotpatcher_config_source -> $(Join-NormalizedPath $script:InstallPath "patcher_config.json")"
    }
}


# 执行安装
function Use-InstallMode {
    Write-Log "启动 SD Trainer Script 安装程序"
    Write-Log "提示: 若出现某个步骤执行失败, 可尝试再次运行 SD Trainer Script Installer, 更多的说明请阅读 SD Trainer Script Installer 使用文档"
    Write-Log "SD Trainer Script Installer 使用文档: https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/"
    Write-Log "即将进行安装的路径: $script:InstallPath"
    Invoke-Installation
    Write-Log "添加管理脚本和文档中"
    Write-ManagerScripts
    Copy-InstallerConfig

    if ($script:BuildMode) {
        Use-BuildMode
        Write-Log "SD Trainer Script 环境构建完成, 路径: $script:InstallPath"
    } else {
        Write-Log "SD Trainer Script 安装结束, 安装路径为: $script:InstallPath"
    }

    Save-InstallResultSnapshot -CliName $script:SnapshotRestoreCliName -PathArgument $script:SnapshotRestorePathArgument -WebUIPath (Join-NormalizedPath $script:InstallPath $env:CORE_PREFIX)

    Write-Log "帮助文档可在 SD Trainer Script 文件夹中查看, 双击 help.txt 文件即可查看, 更多的说明请阅读 SD Trainer Script Installer 使用文档"
    if (!($script:BuildMode)) { Invoke-Item (Join-NormalizedPath $script:InstallPath "help.txt") }
    Write-Log "SD Trainer Script Installer 使用文档: https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/"
    Write-Log "退出 SD Trainer Script Installer"

    if ((-not $script:BuildMode) -and (-not $script:NoPause)) { Read-Host | Out-Null }
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
        $launch_args.Add("-DisableSnapshot", $true)
        if ($script:DisableAutoMirror) { $launch_args.Add("-DisableAutoMirror", $true) }
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

    if ($script:BuildWithModel) {
        $launch_args = @{}
        $launch_args.Add("-BuildMode", $true)
        if ($script:DisableAutoMirror) { $launch_args.Add("-DisableAutoMirror", $true) }
        $launch_args.Add("-BuildWithModel", $script:BuildWithModel)
        if ($script:DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($script:DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($script:UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $script:UseCustomProxy) }
        if ($script:DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($script:CorePrefix) { $launch_args.Add("-CorePrefix", $script:CorePrefix) }
        if ($script:DisableModelMirror) { $launch_args.Add("-DisableModelMirror", $true) }
        Write-Log "执行模型安装脚本中"
        . (Join-NormalizedPath $script:InstallPath "download_models.ps1") @launch_args
    }

    if ($script:BuildWithBranch) {
        $launch_args = @{}
        $launch_args.Add("-BuildMode", $true)
        $launch_args.Add("-DisableSnapshot", $true)
        if ($script:DisableAutoMirror) { $launch_args.Add("-DisableAutoMirror", $true) }
        $launch_args.Add("-BuildWithBranch", $script:BuildWithBranch)
        if ($script:DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($script:DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($script:DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($script:UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $script:UseCustomProxy) }
        if ($script:DisableGithubMirror) { $launch_args.Add("-DisableGithubMirror", $true) }
        if ($script:UseCustomGithubMirror) { $launch_args.Add("-UseCustomGithubMirror", $script:UseCustomGithubMirror) }
        if ($script:DisableAutoApplyUpdate) { $launch_args.Add("-DisableAutoApplyUpdate", $true) }
        if ($script:CorePrefix) { $launch_args.Add("-CorePrefix", $script:CorePrefix) }
        Write-Log "执行 SD Trainer Script 分支切换脚本中"
        . (Join-NormalizedPath $InstallPath "switch_branch.ps1") @launch_args
    }

    if ($script:BuildWithUpdate) {
        $launch_args = @{}
        $launch_args.Add("-BuildMode", $true)
        $launch_args.Add("-DisableSnapshot", $true)
        if ($script:DisableAutoMirror) { $launch_args.Add("-DisableAutoMirror", $true) }
        if ($script:DisablePyPIMirror) { $launch_args.Add("-DisablePyPIMirror", $true) }
        if ($script:DisableUpdate) { $launch_args.Add("-DisableUpdate", $true) }
        if ($script:DisableProxy) { $launch_args.Add("-DisableProxy", $true) }
        if ($script:UseCustomProxy) { $launch_args.Add("-UseCustomProxy", $script:UseCustomProxy) }
        if ($script:DisableGithubMirror) { $launch_args.Add("-DisableGithubMirror", $true) }
        if ($script:UseCustomGithubMirror) { $launch_args.Add("-UseCustomGithubMirror", $script:UseCustomGithubMirror) }
        if ($script:CorePrefix) { $launch_args.Add("-CorePrefix", $script:CorePrefix) }
        Write-Log "执行 SD Trainer Script 更新脚本中"
        . (Join-NormalizedPath $InstallPath "update.ps1") @launch_args
    }

    if ($script:BuildWithLaunch) {
        $launch_args = @{}
        $launch_args.Add("-BuildMode", $true)
        if ($script:DisableAutoMirror) { $launch_args.Add("-DisableAutoMirror", $true) }
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
        if ($script:DisableCUDAMalloc) { $launch_args.Add("-DisableCUDAMalloc", $true) }
        if ($script:DisableEnvCheck) { $launch_args.Add("-DisableEnvCheck", $true) }
        if ($script:DisableHotpatcher) { $launch_args.Add("-DisableHotpatcher", $true) }
        if ($script:EnableHotpatcherRuntime) { $launch_args.Add("-EnableHotpatcherRuntime", $true) }
        if ($script:HotpatcherPortProvided) { $launch_args.Add("-HotpatcherPort", $script:HotpatcherPort) }
        if ($script:CorePrefix) { $launch_args.Add("-CorePrefix", $script:CorePrefix) }
        Write-Log "执行 SD Trainer Script 初始化脚本中"
        . (Join-NormalizedPath $InstallPath "init.ps1") @launch_args
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
    powershell -NoLogo -NoProfile -Command `"Set-ExecutionPolicy Unrestricted -Scope CurrentUser`"
    echo :: Enable long paths supported
    echo :: Executing command: `"New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force`"
    powershell -NoLogo -NoProfile -Command `"New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force`"
    echo :: Set .ps1 default open method to PowerShell
    echo :: Download set_ps1_default_powershell.ps1 from mirrors and execute it
    powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command `"& { `$ErrorActionPreference = 'Stop'; `$scriptPath = `$null; `$tempPath = `$null; try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12; `$urls = @('https://github.com/licyk/sd-webui-all-in-one/raw/main/.github/set_ps1_default_powershell.ps1', 'https://gitee.com/licyk/sd-webui-all-in-one/raw/main/.github/set_ps1_default_powershell.ps1', 'https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/.github/set_ps1_default_powershell.ps1'); `$localAppData = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData); `$cacheDir = Join-Path `$localAppData 'Temp'; New-Item -ItemType Directory -Path `$cacheDir -Force | Out-Null; `$scriptPath = Join-Path `$cacheDir 'set_ps1_default_powershell.ps1'; `$downloaded = `$false; foreach (`$url in `$urls) { Write-Host (':: Trying to download: ' + `$url); try { `$tempPath = `$scriptPath + '.download'; if (Test-Path -LiteralPath `$tempPath) { Remove-Item -LiteralPath `$tempPath -Force }; `$downloadParams = @{ Uri = `$url; OutFile = `$tempPath; UseBasicParsing = `$true; TimeoutSec = 15; ErrorAction = 'Stop' }; Invoke-WebRequest @downloadParams; if ((Test-Path -LiteralPath `$tempPath) -and ((Get-Item -LiteralPath `$tempPath).Length -gt 0)) { Move-Item -LiteralPath `$tempPath -Destination `$scriptPath -Force; `$downloaded = `$true; Write-Host (':: Downloaded to: ' + `$scriptPath); break } } catch { Write-Warning ('Download failed: ' + `$url + ' - ' + `$_.Exception.Message) } }; if (-not `$downloaded) { throw 'Failed to download set_ps1_default_powershell.ps1 from all mirrors.' }; & `$scriptPath -Force } finally { foreach (`$path in @(`$tempPath, `$scriptPath)) { if (`$path -and (Test-Path -LiteralPath `$path)) { try { Remove-Item -LiteralPath `$path -Force -ErrorAction Stop; Write-Host (':: Removed temporary file: ' + `$path) } catch { Write-Warning ('Failed to remove temporary file: ' + `$path + ' - ' + `$_.Exception.Message) } } } } }`"
    if `"%errorlevel%`" NEQ `"0`" (
        echo :: Failed to set .ps1 default open method, please check network or run set_ps1_default_powershell.ps1 manually
    )
    echo :: Configure completed
    echo :: Exit environment configuration script
    pause
".Trim()

    Write-Log "$(if (Test-Path (Join-NormalizedPath $script:InstallPath "configure_env.bat")) { "更新" } else { "生成" }) configure_env.bat 中"
    Write-FileWithStreamWriter -Encoding GBK (Join-NormalizedPath $script:InstallPath "configure_env.bat") -Value $content
}


# 获取帮助信息
function Get-HelpMessage {
    if (!($script:Help)) { return }
    $script = Get-Command $script:PSCommandPath
    $common = [System.Management.Automation.Internal.CommonParameters].GetProperties().Name
    $display_params = $script.Parameters.Values | Where-Object { $_.Name -notin $common } | ForEach-Object {
        $p_name = $_.Name
        $p_type = $_.ParameterType.Name
        if ($_.ParameterType -eq [switch]) {
            $format = "-$p_name"
        }
        else {
            # 处理数组类型的显示逻辑
            # 如果是数组, PowerShell 习惯在类型名后加 []
            if ($_.ParameterType.IsArray) {
                # 移除原类型名中的 [] 或 System. 前缀, 统一格式
                $clean_type = "$($_.ParameterType.GetElementType().Name)[]"
            } else {
                $clean_type = $p_type
            }
            $format = "-$p_name <$clean_type>"
        }
        $help_msg = $_.Attributes.HelpMessage
        [PSCustomObject]@{
            Name = $format
            HelpMessage = $help_msg
        }
    }
    $usage = @"
使用:
    $((Get-Process -Id $PID).Path) ${script:PSCommandPath} $(foreach ($i in $display_params.Name) { "[$i]" })
"@
    $param_info = @"
参数:
$(
    foreach ($i in $display_params) {
        $text = "    $($i.Name)"
        if ($i.HelpMessage) {
            $indented_help = ($i.HelpMessage -split "`r?`n" | ForEach-Object { "        $_" }) -join "`n"
            $text += "`n$indented_help"
        }
        $text + "`n`n"
    }
)
"@
    $docs_url = "更多的帮助信息请阅读 SD Trainer Script Installer 使用文档: https://licyk.github.io/sd-webui-all-in-one/installer/sd-trainer-script/"
    Write-Host $($usage + "`n`n" + $param_info + "`n" + $docs_url)
    exit 0
}


# 主程序
function Main {
    Get-HelpMessage
    Get-Version
    Get-CorePrefixStatus

    if ($script:RestoreFromSnapshot -and $script:UseUpdateMode) {
        Write-Log "-RestoreFromSnapshot 不能和 -UseUpdateMode 同时使用" -Level ERROR
        if ((-not $script:BuildMode) -and (-not $script:NoPause)) { Read-Host | Out-Null }
        exit 1
    }

    if ($script:UseUpdateMode) {
        Write-Log "使用更新模式"
        Use-UpdateMode
        Set-Content -Encoding UTF8 -Path (Join-NormalizedPath $script:InstallPath "update_time.txt") -Value $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") # 记录更新时间
    } else {
        if ($script:BuildMode) { Write-Log "SD Trainer Script Installer 构建模式已启用" }
        Write-Log "使用安装模式"
        Use-InstallMode
    }
}


###################


Main
