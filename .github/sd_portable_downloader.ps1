<#
.SYNOPSIS
    AI整合包可视化下载管理工具

.DESCRIPTION
    这是一个功能完整的WPF GUI应用，用于下载和管理各类AI模型应用的可发行包。

    主要功能：
    - 支持多源下载：HuggingFace、ModelScope
    - 版本选择：稳定版(Stable)、夜间构建版(Nightly)
    - 智能队列管理：支持任务排队、自动调度、中断控制
    - 自动解压：下载完成后可自动提取压缩包
    - 磁盘监控：实时显示目标路径的磁盘空间占用
    - 系统主题适配：自动检测Windows深色/浅色模式
    - 代理配置：自动读取系统代理设置
    - 断点续传：使用Aria2核心支持多线程下载

.PARAMETER ScriptRootPath
    脚本执行的根路径。如果未指定，将使用当前工作目录。
    类型: [string]
    示例: "C:\Downloads"

.NOTES
    环境要求:
    - Windows 7 (SP1) 或更高版本
    - PowerShell 5.0 或更高版本
    - 需要 .NET Framework 4.5+ (WPF支持)
    - 可选：系统已安装Aria2和7-Zip工具

    外部依赖:
    - Aria2c.exe: 高性能下载引擎，支持多线程和断点续传
      下载源: https://gitee.com/licyk/sd-webui-all-in-one/raw/master/aria2/windows/amd64/aria2c.exe
    - 7za.exe: 轻量级解压工具，支持7z/zip等多种格式
      下载源: https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/7za/windows/amd64/7za.exe
    - portable_list.json: 云端资源配置文件
      源地址: https://licyk.github.io/resources/portable_list.json

    主要类和函数:
    - Get-Aria2-Executable: 获取或下载Aria2可执行文件
    - Get-7za-Executable: 获取或下载7-Zip可执行文件
    - Invoke-DownloadTask: 执行单个下载任务
    - Start-ExtractionTask: 执行解压任务
    - Invoke-Refresh: 从云端刷新可用资源列表
    - Set-Proxy: 配置系统代理
    - Find-Visual-Element: WPF可视树搜索辅助函数

.EXAMPLE
    # 标准使用方式
    .\sd_portable_downloader.ps1

.EXAMPLE
    # 指定下载保存路径
    .\sd_portable_downloader.ps1 -ScriptRootPath "E:\AIModels"

.EXAMPLE
    # 在批处理中调用（cmd.exe）
    powershell -ExecutionPolicy Bypass -File ".\sd_portable_downloader.ps1" -ScriptRootPath "C:\Download"

.INPUTS
    [string] ScriptRootPath - 可选的脚本根路径参数

.OUTPUTS
    无直接输出。返回GUI窗口交互式界面。
    下载的文件保存到用户指定的目录。

.LINK
    项目仓库: https://github.com/licyk/sd-webui-all-in-one
    讨论区: https://github.com/licyk/sd-webui-all-in-one/discussions/1

.AUTHOR
    licyk

.VERSION
    1.0.2

.HISTORY

#>
param (
    [string]$ScriptRootPath
)
$script:SD_PORTABLE_DOWNLOADER_VERSION = 102
Add-Type -AssemblyName PresentationFramework, System.Windows.Forms, System.Drawing

# 注入 Win32 API 用于实现毛玻璃效果
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

[StructLayout(LayoutKind.Sequential)]
public struct AccentPolicy {
    public int AccentState;
    public int AccentFlags;
    public int GradientColor;
    public int AnimationId;
}

[StructLayout(LayoutKind.Sequential)]
public struct WindowCompositionAttributeData {
    public int Attribute;
    public IntPtr Data;
    public int SizeOfData;
}

public class BlurHelper {
    [DllImport("user32.dll")]
    public static extern int SetWindowCompositionAttribute(IntPtr hwnd, ref WindowCompositionAttributeData data);

    [DllImport("dwmapi.dll")]
    public static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int attrValue, int attrSize);

    public static void SetBlurState(IntPtr hwnd, int state) {
        var accent = new AccentPolicy();
        accent.AccentState = state; // 0: Disabled, 3: Blur

        var accentStructSize = Marshal.SizeOf(accent);
        var accentPtr = Marshal.AllocHGlobal(accentStructSize);
        Marshal.StructureToPtr(accent, accentPtr, false);

        var data = new WindowCompositionAttributeData();
        data.Attribute = 19; // WCA_ACCENT_POLICY
        data.SizeOfData = accentStructSize;
        data.Data = accentPtr;

        SetWindowCompositionAttribute(hwnd, ref data);
        Marshal.FreeHGlobal(accentPtr);
    }

    public static void EnableBlur(IntPtr hwnd) {
        SetBlurState(hwnd, 3);
    }

    public static void SetRounding(IntPtr hwnd, bool enabled) {
        // DWMWA_WINDOW_CORNER_PREFERENCE = 33
        // DWMWCP_ROUND = 2, DWMWCP_DONOTROUND = 1
        int preference = enabled ? 2 : 1;
        DwmSetWindowAttribute(hwnd, 33, ref preference, sizeof(int));
    }

    public static void SetDarkMode(IntPtr hwnd, bool enabled) {
        // DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        int preference = enabled ? 1 : 0;
        DwmSetWindowAttribute(hwnd, 20, ref preference, sizeof(int));
    }
}
"@ -PassThru | Out-Null

function Show-Update-Popup {
    param([string]$LatestVersion, [string]$CurrentVersion, [bool]$IsDarkMode)

    $github = "https://github.com/licyk/sd-webui-all-in-one/releases/download/portable/sd_portable_downloader.bat"
    $gitee = "https://gitee.com/licyk/sd-webui-all-in-one/releases/download/portable/sd_portable_downloader.bat"

    # 根据主题定义颜色
    $theme = if ($IsDarkMode) {
        @{ BG = "#2D2D2D"; TextMain = "#FFFFFF"; TextSec = "#AAAAAA"; Border = "#444444"; BtnGray = "#4A4A4A"; BtnGrayText = "#FFFFFF" }
    } else {
        @{ BG = "#FFFFFF"; TextMain = "#333333"; TextSec = "Gray"; Border = "#0078D4"; BtnGray = "#E1E1E1"; BtnGrayText = "#333333" }
    }

    $rs = [runspacefactory]::CreateRunspace()
    $rs.ApartmentState = "STA"
    $rs.Open()
    $ps = [powershell]::Create().AddScript({
        param($v, $cv, $gh, $gt, $t, $dark)
        Add-Type -AssemblyName PresentationFramework

        [xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        Title="更新提示" Height="200" Width="420" WindowStartupLocation="CenterScreen"
        WindowStyle="None" AllowsTransparency="True" Background="Transparent" Topmost="True">
    <Border CornerRadius="12" Background="$($t.BG)" BorderBrush="$($t.Border)" BorderThickness="1.5">
        <Border.Effect>
            <DropShadowEffect BlurRadius="15" ShadowDepth="0" Opacity="0.4"/>
        </Border.Effect>
        <StackPanel Margin="25">
            <TextBlock Text="发现新版本！" FontSize="20" FontWeight="Bold" Foreground="#0078D4" Margin="0,0,0,8"/>
            <TextBlock Text="最新版本: $v  (当前版本: $cv)" FontSize="12" Foreground="$($t.TextSec)" Margin="0,0,0,15"/>
            <TextBlock Text="建议下载最新的 .bat 启动器以获得更好的体验。" FontSize="13" Foreground="$($t.TextMain)" Margin="0,0,0,20" TextWrapping="Wrap"/>
            <StackPanel Orientation="Horizontal" HorizontalAlignment="Right">
                <Button Name="GithubBtn" Content="GitHub 下载" Margin="0,0,10,0" Cursor="Hand" Background="#0078D4" Foreground="White" Padding="12,6" BorderThickness="0">
                    <Button.Resources><Style TargetType="Border"><Setter Property="CornerRadius" Value="6"/></Style></Button.Resources>
                </Button>
                <Button Name="GiteeBtn" Content="Gitee 下载" Margin="0,0,10,0" Cursor="Hand" Background="#0078D4" Foreground="White" Padding="12,6" BorderThickness="0">
                    <Button.Resources><Style TargetType="Border"><Setter Property="CornerRadius" Value="6"/></Style></Button.Resources>
                </Button>
                <Button Name="CloseBtn" Content="稍后" Cursor="Hand" Background="$($t.BtnGray)" Foreground="$($t.BtnGrayText)" Padding="15,6" BorderThickness="0">
                    <Button.Resources><Style TargetType="Border"><Setter Property="CornerRadius" Value="6"/></Style></Button.Resources>
                </Button>
            </StackPanel>
        </StackPanel>
    </Border>
</Window>
"@
        $reader = New-Object System.Xml.XmlNodeReader $xaml
        $win = [Windows.Markup.XamlReader]::Load($reader)

        # 处理 Win32 句柄以设置沉浸式深色模式标题栏（虽然是无边框，但有助于系统集成）
        if ($dark) {
            try {
                (New-Object System.Windows.Interop.WindowInteropHelper($win)).EnsureHandle()
                # 此处由于是子 Runspace，不方便调用主进程定义的 BlurHelper，仅通过 XAML 颜色适配
            } catch {}
        }

        $win.FindName("GithubBtn").Add_Click({ Start-Process $gh; $win.Close() }.GetNewClosure())
        $win.FindName("GiteeBtn").Add_Click({ Start-Process $gt; $win.Close() }.GetNewClosure())
        $win.FindName("CloseBtn").Add_Click({ $win.Close() }.GetNewClosure())
        $win.Add_MouseLeftButtonDown({ $win.DragMove() }.GetNewClosure())

        $win.ShowDialog() | Out-Null
    }).AddArgument($LatestVersion).AddArgument($CurrentVersion).AddArgument($github).AddArgument($gitee).AddArgument($theme).AddArgument($IsDarkMode)
    $ps.Runspace = $rs
    $ps.BeginInvoke()
}

function Show-Async-MsgBox {
    param([string]$Message, [string]$Title = "提示", [string]$Icon = "Information")

    $rs = [runspacefactory]::CreateRunspace()
    $rs.Open()
    $ps = [powershell]::Create().AddScript({
        param($msg, $title, $icon)
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show($msg, $title, "OK", $icon)
    }).AddArgument($Message).AddArgument($Title).AddArgument($Icon)
    $ps.Runspace = $rs
    $ps.BeginInvoke()
}

function Invoke-Update-Async {
    param([bool]$IsDarkMode)
    Write-Host "[更新] 正在后台检查新版本..." -ForegroundColor Cyan
    $urls = @(
        "https://github.com/licyk/sd-webui-all-in-one/raw/main/.github/sd_portable_downloader.ps1",
        "https://gitee.com/licyk/sd-webui-all-in-one/raw/main/.github/sd_portable_downloader.ps1"
    )

    if ($null -eq $Global:DownloadRunspacePool) {
        $Global:DownloadRunspacePool = [runspacefactory]::CreateRunspacePool(1, 2)
        $Global:DownloadRunspacePool.Open()
    }

    $ps = [powershell]::Create().AddScript({
        param($urls, $currentVersion)
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $errors = @()
        foreach ($url in $urls) {
            try {
                $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 10 -ErrorAction Stop
                if ($response.Content -match '\$script:SD_PORTABLE_DOWNLOADER_VERSION\s*=\s*(\d+)') {
                    $latestVersion = [int]$matches[1]
                    if ($latestVersion -gt $currentVersion) {
                        return @{ Success = $true; LatestVersion = $latestVersion }
                    } else {
                        return @{ Success = $false; UpToDate = $true }
                    }
                } else {
                    $errors += "无法在源中解析到版本号: $url"
                }
            } catch {
                $errors += "访问源失败 ($url): $($_.Exception.Message)"
            }
        }
        return @{ Success = $false; Error = ($errors -join "`n") }
    }).AddArgument($urls).AddArgument($script:SD_PORTABLE_DOWNLOADER_VERSION)

    $ps.RunspacePool = $Global:DownloadRunspacePool
    $asyncResult = $ps.BeginInvoke()
    $currentVer = $script:SD_PORTABLE_DOWNLOADER_VERSION
    # 显式捕获函数引用，以便 PS5.1 的闭包能够识别
    $ShowPopup = Get-Command Show-Update-Popup

    $monitorTimer = New-Object System.Windows.Threading.DispatcherTimer
    $monitorTimer.Interval = [TimeSpan]::FromSeconds(1)
    $monitorTimer.Add_Tick({
        if ($asyncResult.IsCompleted) {
            $monitorTimer.Stop()
            try {
                $result = $ps.EndInvoke($asyncResult)
                if ($result.Success) {
                    Write-Host "[更新] 发现新版本: $($result.LatestVersion) (当前: $currentVer)" -ForegroundColor Green
                    # 使用 & 符号调用捕获的函数变量
                    & $ShowPopup -LatestVersion $result.LatestVersion -CurrentVersion $currentVer -IsDarkMode $IsDarkMode
                } elseif ($result.UpToDate) {
                    Write-Host "[更新] 当前已是最新版本 ($currentVer)" -ForegroundColor Gray
                } elseif ($result.Error) {
                    Write-Host "[更新] 检查更新失败: $($result.Error)" -ForegroundColor Red
                } else {
                    Write-Host "[更新] 检查更新任务完成，但未发现有效版本信息。" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "[更新] 检查更新时发生异常: $($_.Exception.Message)" -ForegroundColor Red
            } finally {
                $ps.Dispose()
            }
        }
    }.GetNewClosure())
    $monitorTimer.Start()
}

function Open-Url {
    param([string]$Url)
    try { Start-Process $Url } catch { Write-Warning "无法打开链接: $Url" }
}

function Invoke-WebRequest-Async {
    param([string]$Uri, [string]$OutFile)

    # 检查当前线程是否有关联的 Dispatcher (UI 线程)
    $dispatcher = [System.Windows.Threading.Dispatcher]::FromThread([System.Threading.Thread]::CurrentThread)
    if ($null -eq $dispatcher) {
        # 非 UI 线程，直接同步执行
        Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $OutFile
    } else {
        # UI 线程，使用后台运行空间下载，并保持 UI 响应
        $rs = [runspacefactory]::CreateRunspace()
        $rs.Open()
        $ps = [powershell]::Create().AddScript({
            param($u, $o)
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $o
        }).AddArgument($Uri).AddArgument($OutFile)
        $ps.Runspace = $rs
        $async = $ps.BeginInvoke()
        while (-not $async.IsCompleted) {
            # 允许 UI 处理事件循环
            $dispatcher.Invoke([Action]{}, [System.Windows.Threading.DispatcherPriority]::Background)
            Start-Sleep -Milliseconds 100
        }
        try {
            $ps.EndInvoke($async)
        } finally {
            $ps.Dispose()
            $rs.Close()
        }
    }
}

function Get-Aria2-Executable {
    $binUrl = "https://www.modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/aria2/windows/amd64/aria2c.exe"
    $binPath = Join-Path ([IO.Path]::GetTempPath()) "aria2c.exe"
    $localBinPath = Get-Command aria2c -ErrorAction SilentlyContinue

    if ($null -ne $localBinPath) {
        Write-Host "[环境] 发现系统安装的 Aria2: $($localBinPath.Source)" -ForegroundColor Gray
        return $localBinPath.Source
    }
    if (Test-Path $binPath) {
        try {
            & "$binPath" --version > $null
            if ($?) {
                Write-Host "[环境] 使用缓存的 Aria2 核心: $binPath" -ForegroundColor Gray
                return $binPath
            }
        } catch { }
    }

    Write-Host "[环境] 正在下发 Aria2 核心组件..." -ForegroundColor Yellow
    Invoke-WebRequest-Async -Uri $binUrl -OutFile $binPath
    return $binPath
}

function Get-7za-Executable {
    $binUrl = "https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/7za/windows/amd64/7za.exe"
    $binPath = Join-Path ([IO.Path]::GetTempPath()) "7za.exe"
    $localBinPath = Get-Command 7za -ErrorAction SilentlyContinue
    $localBinPath7z = Get-Command 7z -ErrorAction SilentlyContinue

    if ($null -ne $localBinPath) {
        Write-Host "[环境] 发现系统安装的 7za: $($localBinPath.Source)" -ForegroundColor Gray
        return $localBinPath.Source
    }
    if ($null -ne $localBinPath7z) {
        Write-Host "[环境] 发现系统安装的 7z: $($localBinPath7z.Source)" -ForegroundColor Gray
        return $localBinPath7z.Source
    }
    if (Test-Path $binPath) {
        try {
            & "$binPath" > $null
            if ($?) {
                Write-Host "[环境] 使用缓存的 7-Zip 组件: $binPath" -ForegroundColor Gray
                return $binPath
            }
        } catch { }
    }

    Write-Host "[环境] 正在下发 7-Zip 解压组件..." -ForegroundColor Yellow
    Invoke-WebRequest-Async -Uri $binUrl -OutFile $binPath
    return $binPath
}

function Invoke-DownloadTask {
    param(
        [Parameter(Mandatory)] [string]$Url,
        [Parameter(Mandatory)] [string]$OutDir,
        [Parameter(Mandatory)] [string]$SaveName,
        [Parameter(Mandatory)] [Object]$State,
        [Parameter(Mandatory)] [Object]$QueueTask
    )

    $bin = Get-Aria2-Executable
    $launch_args = "-c -x 16 -s 64 -k 1M --file-allocation=none --summary-interval=0 --console-log-level=error -d `"$($OutDir.TrimEnd('\', '/'))`" `"$Url`" -o `"$SaveName`""

    try {
        Write-Host "[任务] 正在启动 Aria2 下载引擎..." -ForegroundColor Blue
        Write-Host "[任务] 目标: $SaveName" -ForegroundColor Gray

        $process = Start-Process -FilePath $bin -ArgumentList $launch_args -PassThru -NoNewWindow
        $process.EnableRaisingEvents = $true

        $taskInfo = [PSCustomObject]@{
            Id        = "Task-" + [guid]::NewGuid().Guid.Substring(0, 8)
            Process   = $process;
            SaveName  = $SaveName;
            OutDir    = $OutDir;
            QueueTask = $QueueTask
        }

        $State.CurrentTask = $taskInfo
        $State.IsCancelled = $false
        Write-Host "[任务] 引擎启动成功 [PID: $($process.Id)]" -ForegroundColor Green

        Show-Async-MsgBox -Message "任务已开始下载：`n$SaveName`n`n保存路径：`n$OutDir" -Title "下载启动"
        return $taskInfo.Id
    }
    catch {
        Write-Host "[任务] 启动下载任务失败: $($_.Exception.Message)" -ForegroundColor Red
        $QueueTask.Status = "失败"
        Show-Async-MsgBox -Message "无法启动下载任务：`n$($_.Exception.Message)`n`n报告问题与寻求帮助请前往: `nhttps://github.com/licyk/sd-webui-all-in-one/issues" -Title "启动失败" -Icon "Error"
        return $null
    }
}

function Start-ExtractionTask {
    param([string]$FilePath, [string]$ExtractDir, [Object]$State, [Object]$QueueTask)

    $bin = Get-7za-Executable
    Write-Host "[后处理] 正在启动解压任务: $FilePath ..." -ForegroundColor Cyan

    try {
        $process = Start-Process -FilePath $bin -ArgumentList "x `"$FilePath`" -o`"$($ExtractDir.TrimEnd('\', '/'))`" -y" -PassThru -NoNewWindow
        $process.EnableRaisingEvents = $true

        $State.CurrentExtractionTask = [PSCustomObject]@{
            Process    = $process;
            FilePath   = $FilePath;
            ExtractDir = $ExtractDir;
            QueueTask  = $QueueTask
        }
        Write-Host "[后处理] 解压引擎启动成功 [PID: $($process.Id)]" -ForegroundColor Green
        return $process
    }
    catch {
        Write-Host "[后处理] 启动解压失败: $($_.Exception.Message)" -ForegroundColor Red
        $QueueTask.Status = "失败"
        Show-Async-MsgBox -Message "无法启动解压任务：`n$($_.Exception.Message)`n`n报告问题与寻求帮助请前往: `nhttps://github.com/licyk/sd-webui-all-in-one/issues" -Title "解压失败" -Icon "Error"
        return $null
    }
}

function Find-Visual-Element {
    param([System.Windows.DependencyObject]$Parent, [string]$Name)
    if ($null -eq $Parent) { return $null }
    for ($i = 0; $i -lt [System.Windows.Media.VisualTreeHelper]::GetChildrenCount($Parent); $i++) {
        $child = [System.Windows.Media.VisualTreeHelper]::GetChild($Parent, $i)
        if ($child -is [System.Windows.FrameworkElement] -and $child.Name -eq $Name) { return $child }
        $result = Find-Visual-Element -Parent $child -Name $Name
        if ($null -ne $result) { return $result }
    }
    return $null
}

# 将同步逻辑封装为自包含的脚本块（PS5.1 兼容性最佳方案）
$script:SyncDataGridLogic = {
    param($UI, $State)
    if ($null -eq $State.Metadata) {
        Write-Host "[数据] 无法同步：元数据为空" -ForegroundColor Red
        return
    }

    $versionType = if ($UI.StableRadio.IsChecked) { "stable" } else { "nightly" }
    $sourceName  = if ($UI.HFRadio.IsChecked) { "huggingface" } else { "modelscope" }

    Write-Host "[数据] 正在切换视图: $sourceName -> $versionType" -ForegroundColor Magenta
    $gridSource = @()
    $sourceNode = $State.Metadata."$sourceName"
    if ($null -ne $sourceNode) {
        $vNode = $sourceNode."$versionType"
        if ($null -ne $vNode) {
            foreach ($comp in $vNode.PSObject.Properties) {
                $versions = @()
                if ($null -ne $comp.Value -and $comp.Value -is [System.Array]) {
                    foreach ($vEntry in $comp.Value) {
                        if ($vEntry.Count -ge 2) {
                            $versions += [PSCustomObject]@{ Name = $vEntry[0]; Url = $vEntry[1] }
                        }
                    }
                }
                if ($versions.Count -gt 0) {
                    $gridSource += [PSCustomObject]@{
                        Type            = $comp.Name
                        Versions        = $versions
                        SelectedVersion = $versions[0]
                    }
                }
            }
        }
    }
    Write-Host "[数据] 已加载 $($gridSource.Count) 个资源条目" -ForegroundColor Gray
    $UI.MainGrid.ItemsSource = $null
    $UI.MainGrid.ItemsSource = $gridSource
}

function Invoke-Refresh {
    param($UI, $State)

    # 显式引用脚本块，确保它在当前函数的局部作用域内，以便闭包捕获
    $SyncLogic = $script:SyncDataGridLogic

    # 显示加载状态
    $UI.LoadingOverlay.Visibility = "Visible"
    $UI.MainGrid.Visibility = "Collapsed"
    $UI.RefreshBtn.IsEnabled = $false
    $UI.UpdateTimeText.Text = "状态: 正在同步云端数据..."
    Write-Host "[UI] 用户触发同步请求，正在发起异步任务..." -ForegroundColor Cyan

    # 确保全局 RunspacePool 存在
    if ($null -eq $Global:DownloadRunspacePool) {
        $Global:DownloadRunspacePool = [runspacefactory]::CreateRunspacePool(1, 2)
        $Global:DownloadRunspacePool.Open()
    }

    $ps = [powershell]::Create().AddScript({
        param([string[]]$Uris)
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $lastError = ""
        foreach ($Uri in $Uris) {
            try {
                $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 15 -ErrorAction Stop
                $json = $response.Content | ConvertFrom-Json
                if ($null -ne $json) { return $json }
            } catch {
                $lastError = $_.Exception.Message
            }
        }
        return "ERROR: " + $lastError
    }).AddArgument(@(
        "https://licyk.github.io/resources/portable_list.json",
        "https://gitee.com/licyk/resources/raw/gh-pages/portable_list.json"
    ))

    $ps.RunspacePool = $Global:DownloadRunspacePool
    $asyncResult = $ps.BeginInvoke()

    $monitorTimer = New-Object System.Windows.Threading.DispatcherTimer
    $monitorTimer.Interval = [TimeSpan]::FromMilliseconds(200)

    $tickAction = {
        if ($asyncResult.IsCompleted) {
            $monitorTimer.Stop()
            Write-Host "[UI] 云端数据已到达 [OK]" -ForegroundColor Green
            try {
                $result = $ps.EndInvoke($asyncResult)

                if ($null -ne $result -and $null -ne $result.update_time) {
                    Write-Host "[数据] 解析成功，更新时间: $($result.update_time)" -ForegroundColor Gray
                    $State.Metadata = $result
                    $UI.UpdateTimeText.Text = "更新时间: $($result.update_time)"
                    # 调用捕获到的脚本块
                    & $SyncLogic -UI $UI -State $State
                    $UI.UpdateTimeText.Foreground = [System.Windows.Media.Brushes]::Gray
                } elseif ($result -is [string] -and $result.StartsWith("ERROR:")) {
                    Write-Host "[数据] 同步异常: $result" -ForegroundColor Red
                    $UI.UpdateTimeText.Text = "同步失败: " + $result.Substring(6)
                    $UI.UpdateTimeText.Foreground = [System.Windows.Media.Brushes]::Red
                } else {
                    Write-Host "[数据] 获取到的数据格式不匹配" -ForegroundColor Red
                    $UI.UpdateTimeText.Text = "同步失败: 获取到的数据格式不正确"
                    $UI.UpdateTimeText.Foreground = [System.Windows.Media.Brushes]::Red
                }
            } catch {
                Write-Host "[数据] 内部解析错误: $($_.Exception.Message)" -ForegroundColor Red
                $UI.UpdateTimeText.Text = "内部错误: $($_.Exception.Message)"
                $UI.UpdateTimeText.Foreground = [System.Windows.Media.Brushes]::Red
            } finally {
                $ps.Dispose()
                $UI.LoadingOverlay.Visibility = "Collapsed"
                $UI.MainGrid.Visibility = "Visible"
                $UI.RefreshBtn.IsEnabled = $true
            }
        }
    }.GetNewClosure()

    $monitorTimer.Add_Tick($tickAction)
    $monitorTimer.Start()
}

function Invoke-DownloadAction {
    param($UI, $State, $Button)
    $savePath = $UI.PathInput.Text
    if (-not (Test-Path $savePath -PathType Container)) {
        Write-Host "[UI] 拦截下载请求：保存路径无效 [$savePath]" -ForegroundColor Red
        Show-Async-MsgBox -Message "下载路径无效。" -Title "错误" -Icon "Error"
        return
    }

    $rowData = $Button.DataContext
    $selected = $rowData.SelectedVersion
    Write-Host "[UI] 用户点击添加任务: $($selected.Name)" -ForegroundColor Cyan

    $newTask = [PSCustomObject]@{
        Name        = $selected.Name
        Url         = $selected.Url
        OutDir      = $savePath
        AutoExtract = $UI.AutoExtract.IsChecked
        AutoDelete  = $UI.AutoDelete.IsChecked
        Status      = "等待中"
        Progress    = "0%"
    }

    $State.TaskQueue += $newTask
    & $script:UpdateQueueUI -UI $UI -State $State
    Show-Async-MsgBox -Message "任务已加入队列：`n$($selected.Name)`n`n队列任务将按顺序自动执行。" -Title "任务已添加"
}

function Set-Proxy {
    $Env:NO_PROXY = "localhost,127.0.0.1,::1"

    $internet_setting = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    if ($internet_setting.ProxyEnable -ne 1) {
        Write-Host "[环境] 未从系统中检测到代理，跳过设置代理" -ForegroundColor Blue
        return
    }
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
    Write-Host "[环境] 检测到系统设置了代理，已读取系统中的代理配置并设置代理，代理地址: $proxy_value" -ForegroundColor Green
}

function Start-App {
    Write-Host "[APP] 初始化中..." -ForegroundColor Yellow
    Set-Proxy
    # 实时检测 Windows 深色模式
    $isDarkMode = $false
    try {
        $reg = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize" -ErrorAction SilentlyContinue
        if ($null -ne $reg -and $reg.AppsUseLightTheme -eq 0) { $isDarkMode = $true }
    } catch {}

    # 主题颜色定义
    $colors = if ($isDarkMode) {
        Write-Host "[环境] 应用深色主题 [Dark Mode]" -ForegroundColor Gray
        @{
            WinBG1="#CC1E1E1E"; WinBG2="#CC121212"; PanelBG="#44000000"; TextMain="#FFFFFF"; TextSec="#AAAAAA"; Border="#44FFFFFF"; InputBG="#333333"; BtnNormal="#4A4A4A"; BtnHover="#5A5A5A"; ItemHover="#33FFFFFF"; HeaderBG="#11FFFFFF";
            ScrollBG="#11FFFFFF"; ScrollThumb="#66FFFFFF"
        }
    } else {
        Write-Host "[环境] 应用浅色主题 [Light Mode]" -ForegroundColor Gray
        @{
            WinBG1="#CCF9FAFB"; WinBG2="#CCF3F4F6"; PanelBG="#44FFFFFF"; TextMain="#323130"; TextSec="#666666"; Border="#88C1C1C1"; InputBG="#FFFFFF"; BtnNormal="#FFFFFF"; BtnHover="#F9F9F9"; ItemHover="#F2F7FF"; HeaderBG="#F9FAFB";
            ScrollBG="#05000000"; ScrollThumb="#AAAAAA"
        }
    }

    [xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="AI 整合包下载器" Height="700" Width="900"
        MinHeight="500" MinWidth="700"
        WindowStartupLocation="CenterScreen" WindowStyle="None" AllowsTransparency="True"
        Background="Transparent" ResizeMode="CanResizeWithGrip">
    <Window.Resources>
        <!-- 基础色彩注入 -->
        <SolidColorBrush x:Key="PrimaryBrush" Color="#0078D4"/>
        <SolidColorBrush x:Key="TextMainBrush" Color="$($colors.TextMain)"/>
        <SolidColorBrush x:Key="TextSecBrush" Color="$($colors.TextSec)"/>
        <SolidColorBrush x:Key="BorderBrush" Color="$($colors.Border)"/>
        <SolidColorBrush x:Key="InputBGBrush" Color="$($colors.InputBG)"/>
        <SolidColorBrush x:Key="BtnNormalBrush" Color="$($colors.BtnNormal)"/>
        <SolidColorBrush x:Key="PanelBGBrush" Color="$($colors.PanelBG)"/>

        <!-- 现代滚动条样式 -->
        <Style TargetType="ScrollBar">
            <Setter Property="Background" Value="$($colors.ScrollBG)"/>
            <Setter Property="Width" Value="8"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="ScrollBar">
                        <Grid Name="Bg" Background="{TemplateBinding Background}" SnapsToDevicePixels="true">
                            <Track Name="PART_Track" IsDirectionReversed="true" IsEnabled="{TemplateBinding IsEnabled}">
                                <Track.Thumb>
                                    <Thumb>
                                        <Thumb.Template>
                                            <ControlTemplate TargetType="Thumb">
                                                <Border Background="$($colors.ScrollThumb)" CornerRadius="4" Margin="1,0"/>
                                            </ControlTemplate>
                                        </Thumb.Template>
                                    </Thumb>
                                </Track.Thumb>
                            </Track>
                        </Grid>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <!-- 按钮样式 -->
        <Style TargetType="Button">
            <Setter Property="Background" Value="{DynamicResource BtnNormalBrush}"/>
            <Setter Property="Foreground" Value="{DynamicResource TextMainBrush}"/>
            <Setter Property="BorderThickness" Value="1"/>
            <Setter Property="BorderBrush" Value="{DynamicResource BorderBrush}"/>
            <Setter Property="Padding" Value="12,6"/>
            <Setter Property="FontSize" Value="13"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="Button">
                        <Border Name="border" Background="{TemplateBinding Background}"
                                BorderBrush="{TemplateBinding BorderBrush}"
                                BorderThickness="{TemplateBinding BorderThickness}"
                                CornerRadius="6" SnapsToDevicePixels="True">
                            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" Margin="{TemplateBinding Padding}">
                                <ContentPresenter.Resources>
                                    <Style TargetType="TextBlock">
                                        <Setter Property="Foreground" Value="{Binding Foreground, RelativeSource={RelativeSource AncestorType=Button}}"/>
                                    </Style>
                                </ContentPresenter.Resources>
                            </ContentPresenter>
                        </Border>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsMouseOver" Value="True">
                                <Setter TargetName="border" Property="Background" Value="$($colors.BtnHover)"/>
                            </Trigger>
                            <Trigger Property="IsPressed" Value="True">
                                <Setter TargetName="border" Property="RenderTransform">
                                    <Setter.Value><ScaleTransform ScaleX="0.98" ScaleY="0.98"/></Setter.Value>
                                </Setter>
                            </Trigger>
                            <Trigger Property="IsEnabled" Value="False">
                                <Setter Property="Opacity" Value="0.5"/>
                            </Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <!-- 主按钮样式 (蓝色) -->
        <Style x:Key="PrimaryButton" TargetType="Button">
            <Setter Property="Background" Value="#0078D4"/>
            <Setter Property="Foreground" Value="White"/>
            <Setter Property="BorderThickness" Value="0"/>
            <Setter Property="Padding" Value="12,6"/>
            <Setter Property="FontSize" Value="13"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="Button">
                        <Border Name="border" Background="{TemplateBinding Background}" CornerRadius="6" SnapsToDevicePixels="True">
                            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" Margin="{TemplateBinding Padding}"/>
                        </Border>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsMouseOver" Value="True">
                                <Setter TargetName="border" Property="Background" Value="#2B88D8"/>
                            </Trigger>
                            <Trigger Property="IsPressed" Value="True">
                                <Setter TargetName="border" Property="Background" Value="#005A9E"/>
                                <Setter TargetName="border" Property="RenderTransform">
                                    <Setter.Value><ScaleTransform ScaleX="0.97" ScaleY="0.97"/></Setter.Value>
                                </Setter>
                            </Trigger>
                            <Trigger Property="IsEnabled" Value="False">
                                <Setter Property="Opacity" Value="0.5"/>
                            </Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <!-- 输入框样式 -->
        <Style TargetType="TextBox">
            <Setter Property="Padding" Value="8,5"/>
            <Setter Property="VerticalContentAlignment" Value="Center"/>
            <Setter Property="Foreground" Value="{DynamicResource TextMainBrush}"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="TextBox">
                        <Border Name="border" Background="{DynamicResource InputBGBrush}" BorderBrush="{DynamicResource BorderBrush}" BorderThickness="1" CornerRadius="4">
                            <ScrollViewer x:Name="PART_ContentHost" Focusable="false" HorizontalScrollBarVisibility="Hidden" VerticalScrollBarVisibility="Hidden"/>
                        </Border>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsFocused" Value="True">
                                <Setter TargetName="border" Property="BorderBrush" Value="#0078D4"/>
                                <Setter TargetName="border" Property="BorderThickness" Value="2"/>
                            </Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <!-- 下拉框样式 -->
        <Style TargetType="ComboBox">
            <Setter Property="Padding" Value="8,4"/>
            <Setter Property="MinHeight" Value="28"/>
            <Setter Property="VerticalContentAlignment" Value="Center"/>
            <Setter Property="Background" Value="{DynamicResource InputBGBrush}"/>
            <Setter Property="Foreground" Value="{DynamicResource TextMainBrush}"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="ComboBox">
                        <Grid>
                            <ToggleButton Name="ToggleButton" Background="{TemplateBinding Background}"
                                          BorderBrush="{DynamicResource BorderBrush}" BorderThickness="1"
                                          IsChecked="{Binding IsDropDownOpen, RelativeSource={RelativeSource TemplatedParent}}"
                                          Focusable="False" ClickMode="Press">
                                <ToggleButton.Style>
                                    <Style TargetType="ToggleButton">
                                        <Setter Property="Template">
                                            <Setter.Value>
                                                <ControlTemplate TargetType="ToggleButton">
                                                    <Border Name="border" Background="{TemplateBinding Background}"
                                                            BorderBrush="{TemplateBinding BorderBrush}"
                                                            BorderThickness="{TemplateBinding BorderThickness}" CornerRadius="6">
                                                        <Path Name="Arrow" Fill="{DynamicResource TextSecBrush}" HorizontalAlignment="Right" VerticalAlignment="Center"
                                                              Margin="0,0,8,0" Data="M 0 0 L 4 4 L 8 0 Z"/>
                                                    </Border>
                                                    <ControlTemplate.Triggers>
                                                        <Trigger Property="IsMouseOver" Value="True">
                                                            <Setter TargetName="border" Property="Background" Value="$($colors.BtnHover)"/>
                                                        </Trigger>
                                                        <Trigger Property="IsChecked" Value="True">
                                                            <Setter TargetName="Arrow" Property="RenderTransform">
                                                                <Setter.Value><RotateTransform Angle="180" CenterX="4" CenterY="2"/></Setter.Value>
                                                            </Setter>
                                                        </Trigger>
                                                    </ControlTemplate.Triggers>
                                                </ControlTemplate>
                                            </Setter.Value>
                                        </Setter>
                                    </Style>
                                </ToggleButton.Style>
                            </ToggleButton>
                            <ContentPresenter Name="ContentSite" IsHitTestVisible="False"
                                              Content="{TemplateBinding SelectionBoxItem}"
                                              ContentTemplate="{TemplateBinding SelectionBoxItemTemplate}"
                                              ContentTemplateSelector="{TemplateBinding ItemTemplateSelector}"
                                              Margin="{TemplateBinding Padding}" VerticalAlignment="Center"/>
                            <Popup Name="Popup" Placement="Bottom" IsOpen="{TemplateBinding IsDropDownOpen}" AllowsTransparency="True" Focusable="False" PopupAnimation="Slide">
                                <Grid Name="DropDown" SnapsToDevicePixels="True" MinWidth="{TemplateBinding ActualWidth}" MaxHeight="{TemplateBinding MaxDropDownHeight}">
                                    <Border Name="DropDownBorder" Background="{DynamicResource InputBGBrush}" BorderThickness="1" BorderBrush="{DynamicResource BorderBrush}" CornerRadius="6" Margin="0,2,0,5">
                                        <Border.Effect><DropShadowEffect BlurRadius="5" ShadowDepth="2" Opacity="0.15"/></Border.Effect>
                                        <ScrollViewer Margin="2" SnapsToDevicePixels="True">
                                            <StackPanel IsItemsHost="True" KeyboardNavigation.DirectionalNavigation="Contained"/>
                                        </ScrollViewer>
                                    </Border>
                                </Grid>
                            </Popup>
                        </Grid>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsMouseOver" Value="True">
                                <Setter Property="BorderBrush" Value="#A1A1A1"/>
                            </Trigger>
                            <Trigger Property="IsFocused" Value="True">
                                <Setter Property="BorderBrush" Value="#0078D4"/>
                            </Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <!-- 下拉列表项样式 -->
        <Style TargetType="ComboBoxItem">
            <Setter Property="Padding" Value="10,12"/>
            <Setter Property="MinHeight" Value="34"/>
            <Setter Property="Foreground" Value="{DynamicResource TextMainBrush}"/>
            <Setter Property="SnapsToDevicePixels" Value="True"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="ComboBoxItem">
                        <Border Name="Border" Background="Transparent" CornerRadius="4" Margin="2,1">
                            <ContentPresenter VerticalAlignment="Center" Margin="{TemplateBinding Padding}"/>
                        </Border>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsMouseOver" Value="True"><Setter TargetName="Border" Property="Background" Value="$($colors.ItemHover)"/></Trigger>
                            <Trigger Property="IsSelected" Value="True"><Setter TargetName="Border" Property="Background" Value="#0078D4"/><Setter Property="TextElement.Foreground" Value="White"/></Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <!-- 单选按钮药丸样式 -->
        <Style TargetType="RadioButton">
            <Setter Property="FontSize" Value="12"/>
            <Setter Property="Height" Value="26"/>
            <Setter Property="Cursor" Value="Hand"/>
            <Setter Property="Foreground" Value="{DynamicResource TextSecBrush}"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="RadioButton">
                        <Border Name="border" Background="{DynamicResource BtnNormalBrush}" BorderBrush="{DynamicResource BorderBrush}" BorderThickness="1" CornerRadius="13" Padding="12,2" Margin="0,0,5,0">
                            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
                        </Border>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsChecked" Value="True">
                                <Setter TargetName="border" Property="Background" Value="#0078D4"/>
                                <Setter TargetName="border" Property="BorderBrush" Value="#0078D4"/>
                                <Setter Property="Foreground" Value="White"/>
                                <Setter Property="FontWeight" Value="SemiBold"/>
                            </Trigger>
                            <MultiTrigger>
                                <MultiTrigger.Conditions>
                                    <Condition Property="IsMouseOver" Value="True"/>
                                    <Condition Property="IsChecked" Value="False"/>
                                </MultiTrigger.Conditions>
                                <Setter TargetName="border" Property="Background" Value="$($colors.BtnHover)"/>
                            </MultiTrigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <!-- 开关样式 (之前定义的) -->
        <Style x:Key="ToggleSwitchStyle" TargetType="CheckBox">
            <Setter Property="Foreground" Value="{DynamicResource TextMainBrush}"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="CheckBox">
                        <StackPanel Orientation="Horizontal" VerticalAlignment="Center">
                            <Grid Name="SwitchRoot" Width="42" Height="22" Cursor="Hand">
                                <Border Name="Track" Background="{DynamicResource BorderBrush}" CornerRadius="11" BorderThickness="0"/>
                                <Border Name="Thumb" Background="White" Width="18" Height="18" CornerRadius="9" HorizontalAlignment="Left" Margin="2,0,0,0">
                                    <Border.Effect><DropShadowEffect ShadowDepth="1" BlurRadius="3" Opacity="0.2"/></Border.Effect>
                                </Border>
                            </Grid>
                            <ContentPresenter Name="Content" Margin="10,0,0,0" VerticalAlignment="Center"/>
                        </StackPanel>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsChecked" Value="True">
                                <Trigger.EnterActions><BeginStoryboard><Storyboard>
                                    <ColorAnimation Storyboard.TargetName="Track" Storyboard.TargetProperty="(Border.Background).(SolidColorBrush.Color)" To="#0078D4" Duration="0:0:0.2"/>
                                    <ThicknessAnimation Storyboard.TargetName="Thumb" Storyboard.TargetProperty="Margin" To="22,0,0,0" Duration="0:0:0.2"/>
                                </Storyboard></BeginStoryboard></Trigger.EnterActions>
                                <Trigger.ExitActions><BeginStoryboard><Storyboard>
                                    <ColorAnimation Storyboard.TargetName="Track" Storyboard.TargetProperty="(Border.Background).(SolidColorBrush.Color)" To="$($colors.Border)" Duration="0:0:0.2"/>
                                    <ThicknessAnimation Storyboard.TargetName="Thumb" Storyboard.TargetProperty="Margin" To="2,0,0,0" Duration="0:0:0.2"/>
                                </Storyboard></BeginStoryboard></Trigger.ExitActions>
                            </Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>
    </Window.Resources>

    <!-- 主容器 -->
    <Border x:Name="MainBorder" CornerRadius="12" BorderThickness="1" BorderBrush="{DynamicResource BorderBrush}" ClipToBounds="True">
        <Border.Background>
            <LinearGradientBrush StartPoint="0,0" EndPoint="1,1">
                <GradientStop Color="$($colors.WinBG1)" Offset="0.0"/>
                <GradientStop Color="$($colors.WinBG2)" Offset="1.0"/>
            </LinearGradientBrush>
        </Border.Background>

        <Grid>
            <Grid.RowDefinitions><RowDefinition Height="32"/><RowDefinition Height="*"/></Grid.RowDefinitions>
            <Grid Name="TitleBar" Grid.Row="0" Background="Transparent">
                <StackPanel Orientation="Horizontal" VerticalAlignment="Center" Margin="12,0,0,0">
                    <!-- 现代化的下载图标 (圆形+箭头) -->
                    <Path Data="M12,2C6.48,2 2,6.48 2,12C2,17.52 6.48,22 12,22C17.52,22 22,17.52 22,12C22,6.48 17.52,2 12,2M12,17L7,12H10V8H14V12H17L12,17Z"
                          Fill="{DynamicResource PrimaryBrush}" Width="18" Height="18" Stretch="Uniform" Margin="0,0,8,0"/>
                    <TextBlock Text="AI 整合包下载器" FontSize="12" Foreground="{DynamicResource TextSecBrush}" IsHitTestVisible="False"/>
                </StackPanel>
                <StackPanel Orientation="Horizontal" HorizontalAlignment="Right">
                    <!-- 最小化 -->
                    <Button Name="MinBtn" Content="—" Width="45" Height="32" Background="Transparent" BorderThickness="0" Foreground="{DynamicResource TextSecBrush}">
                        <Button.Style><Style TargetType="Button"><Setter Property="Template"><Setter.Value><ControlTemplate TargetType="Button"><Border Name="b" Background="{TemplateBinding Background}"><ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/></Border><ControlTemplate.Triggers><Trigger Property="IsMouseOver" Value="True"><Setter TargetName="b" Property="Background" Value="$($colors.BtnHover)"/></Trigger></ControlTemplate.Triggers></ControlTemplate></Setter.Value></Setter></Style></Button.Style>
                    </Button>
                    <!-- 最大化/还原 -->
                    <Button Name="MaxBtn" Content="⬜" Width="45" Height="32" Background="Transparent" BorderThickness="0" Foreground="{DynamicResource TextSecBrush}">
                        <Button.Style><Style TargetType="Button"><Setter Property="Template"><Setter.Value><ControlTemplate TargetType="Button"><Border Name="b" Background="{TemplateBinding Background}"><ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" Margin="0,2,0,0"/></Border><ControlTemplate.Triggers><Trigger Property="IsMouseOver" Value="True"><Setter TargetName="b" Property="Background" Value="$($colors.BtnHover)"/></Trigger></ControlTemplate.Triggers></ControlTemplate></Setter.Value></Setter></Style></Button.Style>
                    </Button>
                    <!-- 关闭 -->
                    <Button Name="CloseBtn" Content="✕" Width="45" Height="32" Background="Transparent" BorderThickness="0" Foreground="{DynamicResource TextSecBrush}">
                        <Button.Style><Style TargetType="Button"><Setter Property="Template"><Setter.Value><ControlTemplate TargetType="Button"><Border Name="b" Background="{TemplateBinding Background}"><ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/></Border><ControlTemplate.Triggers><Trigger Property="IsMouseOver" Value="True"><Setter TargetName="b" Property="Background" Value="#E81123"/><Setter Property="Foreground" Value="White"/></Trigger></ControlTemplate.Triggers></ControlTemplate></Setter.Value></Setter></Style></Button.Style>
                    </Button>
                </StackPanel>
            </Grid>

            <Grid Grid.Row="1" Margin="20,5,20,20">
                <Grid.RowDefinitions>
                    <RowDefinition Height="Auto"/>
                    <RowDefinition Height="*"/>
                    <RowDefinition Height="Auto"/>
                </Grid.RowDefinitions>

                <!-- 顶部信息 -->
                <Grid Grid.Row="0" Margin="0,0,0,15">
                    <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                    <StackPanel Grid.Column="0">
                        <TextBlock Name="UpdateTime" Text="状态: 正在初始化..." FontSize="11" Foreground="{DynamicResource TextSecBrush}"/>
                        <StackPanel Orientation="Horizontal" Margin="0,12">
                            <TextBlock Text="版本:" VerticalAlignment="Center" Foreground="{DynamicResource TextMainBrush}" Margin="0,0,10,0"/>
                            <RadioButton Name="Stable" Content="Stable" GroupName="V" VerticalAlignment="Center"/>
                            <RadioButton Name="Nightly" Content="Nightly" IsChecked="True" GroupName="V" Margin="12,0" VerticalAlignment="Center"/>
                            <Border Width="1" Height="14" Background="{DynamicResource BorderBrush}" Margin="10,0,20,0"/>
                            <TextBlock Text="下载源:" VerticalAlignment="Center" Foreground="{DynamicResource TextMainBrush}" Margin="0,0,10,0"/>
                            <RadioButton Name="HF" Content="HuggingFace" GroupName="S" VerticalAlignment="Center"/>
                            <RadioButton Name="MS" Content="ModelScope" IsChecked="True" GroupName="S" Margin="12,0" VerticalAlignment="Center"/>
                        </StackPanel>
                    </StackPanel>
                    <StackPanel Grid.Column="1" Orientation="Horizontal" VerticalAlignment="Top">
                        <Button Name="ProjBtn" Content="项目主页" Margin="0,0,8,0" Padding="10,4" Background="{DynamicResource BtnNormalBrush}"/>
                        <Button Name="DocBtn" Content="使用说明" Padding="10,4" Background="{DynamicResource BtnNormalBrush}"/>
                    </StackPanel>
                </Grid>

                <!-- 数据与队列容器 -->
                <Grid Name="DataQueueGrid" Grid.Row="1">
                    <Grid.RowDefinitions>
                        <RowDefinition Height="*"/>
                        <RowDefinition Height="Auto"/>
                        <RowDefinition Height="Auto"/>
                    </Grid.RowDefinitions>

                    <!-- 数据表格 -->
                    <Border Grid.Row="0" Background="{DynamicResource PanelBGBrush}" CornerRadius="8" BorderThickness="1" BorderBrush="{DynamicResource BorderBrush}">
                        <Grid>
                            <DataGrid Name="MainGrid" AutoGenerateColumns="False" IsReadOnly="True"
                                      HeadersVisibility="Column" GridLinesVisibility="None" Background="Transparent"
                                      BorderThickness="0" RowHeight="42" Visibility="Collapsed"
                                      SelectionMode="Single" SelectionUnit="FullRow">
                                <DataGrid.Resources>
                                    <Style TargetType="DataGridCell">
                                        <Setter Property="Background" Value="Transparent"/>
                                        <Setter Property="BorderThickness" Value="0"/>
                                        <Setter Property="FocusVisualStyle" Value="{x:Null}"/>
                                        <Setter Property="VerticalContentAlignment" Value="Center"/>
                                        <Setter Property="Foreground" Value="{DynamicResource TextMainBrush}"/>
                                        <Setter Property="Template">
                                            <Setter.Value>
                                                <ControlTemplate TargetType="DataGridCell">
                                                    <Border Background="{TemplateBinding Background}" BorderThickness="0" SnapsToDevicePixels="True">
                                                        <ContentPresenter VerticalAlignment="Center" Margin="10,0,0,0"/>
                                                    </Border>
                                                </ControlTemplate>
                                            </Setter.Value>
                                        </Setter>
                                        <Style.Triggers>
                                            <Trigger Property="IsSelected" Value="True"><Setter Property="Background" Value="Transparent"/><Setter Property="Foreground" Value="{DynamicResource TextMainBrush}"/></Trigger>
                                        </Style.Triggers>
                                    </Style>
                                    <Style TargetType="DataGridColumnHeader">
                                        <Setter Property="Background" Value="{DynamicResource PanelBGBrush}"/>
                                        <Setter Property="Foreground" Value="{DynamicResource TextSecBrush}"/>
                                        <Setter Property="Padding" Value="10,8"/>
                                        <Setter Property="FontSize" Value="12"/>
                                        <Setter Property="FontWeight" Value="SemiBold"/>
                                        <Setter Property="BorderThickness" Value="0,0,0,1"/>
                                        <Setter Property="BorderBrush" Value="{DynamicResource BorderBrush}"/>
                                    </Style>
                                    <Style TargetType="DataGridRow">
                                        <Setter Property="Background" Value="Transparent"/>
                                        <Setter Property="Focusable" Value="False"/>
                                        <Style.Triggers>
                                            <Trigger Property="IsMouseOver" Value="True"><Setter Property="Background" Value="$($colors.ItemHover)"/></Trigger>
                                            <Trigger Property="IsSelected" Value="True"><Setter Property="Background" Value="Transparent"/></Trigger>
                                        </Style.Triggers>
                                    </Style>
                                </DataGrid.Resources>
                                <DataGrid.Columns>
                                    <DataGridTextColumn Header="资源类型" Binding="{Binding Type}" Width="250"/>
                                    <DataGridTemplateColumn Header="版本选择" Width="*">
                                        <DataGridTemplateColumn.CellTemplate>
                                            <DataTemplate>
                                                <ComboBox Name="VersionSelector" ItemsSource="{Binding Versions}"
                                                          DisplayMemberPath="Name" SelectedItem="{Binding SelectedVersion, UpdateSourceTrigger=PropertyChanged}"
                                                          Margin="5,4" VerticalContentAlignment="Center"/>
                                            </DataTemplate>
                                        </DataGridTemplateColumn.CellTemplate>
                                    </DataGridTemplateColumn>
                                    <DataGridTemplateColumn Header="操作" Width="100">
                                        <DataGridTemplateColumn.CellTemplate>
                                            <DataTemplate>
                                                <Button Name="RowDL" Content="下载" Style="{StaticResource PrimaryButton}" Height="28" Padding="15,2"/>
                                            </DataTemplate>
                                        </DataGridTemplateColumn.CellTemplate>
                                    </DataGridTemplateColumn>
                                </DataGrid.Columns>
                            </DataGrid>

                            <!-- 加载遮罩 (放在此处确保只覆盖主列表) -->
                            <StackPanel Name="LoadingOverlay" VerticalAlignment="Center" HorizontalAlignment="Center">
                                <ProgressBar IsIndeterminate="True" Width="220" Height="4" Background="{DynamicResource BorderBrush}" Foreground="#0078D4" BorderThickness="0"/>
                                <TextBlock Text="正在同步云端元数据..." Margin="0,15,0,0" HorizontalAlignment="Center" Foreground="{DynamicResource TextSecBrush}" FontSize="13"/>
                            </StackPanel>
                        </Grid>
                    </Border>

                    <!-- 分割标题 -->
                    <Grid Name="QueueHeader" Grid.Row="1" Margin="0,15,0,8" Opacity="1">
                        <TextBlock Text="任务队列" Foreground="{DynamicResource TextSecBrush}" FontSize="12" FontWeight="SemiBold" VerticalAlignment="Center"/>
                        <TextBlock Name="StatText" Text="队列统计: 总计 0 | 运行中 0 | 已完成 0" HorizontalAlignment="Right" FontSize="11" Foreground="{DynamicResource TextSecBrush}" VerticalAlignment="Center"/>
                    </Grid>

                    <!-- 任务队列表格 -->
                    <Border Name="QueueBorder" Grid.Row="2" Height="140" Background="{DynamicResource PanelBGBrush}" CornerRadius="8" BorderThickness="1" BorderBrush="{DynamicResource BorderBrush}" Opacity="1">
                        <DataGrid Name="QueueGrid" AutoGenerateColumns="False" IsReadOnly="True"
                                  HeadersVisibility="Column" GridLinesVisibility="None" Background="Transparent"
                                  BorderThickness="0" RowHeight="36"
                                  SelectionMode="Single" SelectionUnit="FullRow">
                            <DataGrid.Resources>
                                <Style TargetType="DataGridCell">
                                    <Setter Property="Background" Value="Transparent"/>
                                    <Setter Property="BorderThickness" Value="0"/>
                                    <Setter Property="VerticalContentAlignment" Value="Center"/>
                                    <Setter Property="Foreground" Value="{DynamicResource TextMainBrush}"/>
                                    <Setter Property="Template">
                                        <Setter.Value>
                                            <ControlTemplate TargetType="DataGridCell">
                                                <Border Background="{TemplateBinding Background}" BorderThickness="0" SnapsToDevicePixels="True">
                                                    <ContentPresenter VerticalAlignment="Center" Margin="10,0,0,0"/>
                                                </Border>
                                            </ControlTemplate>
                                        </Setter.Value>
                                    </Setter>
                                </Style>
                                <Style TargetType="DataGridColumnHeader">
                                    <Setter Property="Background" Value="{DynamicResource PanelBGBrush}"/>
                                    <Setter Property="Foreground" Value="{DynamicResource TextSecBrush}"/>
                                    <Setter Property="Padding" Value="10,6"/>
                                    <Setter Property="FontSize" Value="11"/>
                                    <Setter Property="FontWeight" Value="SemiBold"/>
                                    <Setter Property="BorderThickness" Value="0,0,0,1"/>
                                    <Setter Property="BorderBrush" Value="{DynamicResource BorderBrush}"/>
                                </Style>
                                <Style TargetType="DataGridRow">
                                    <Setter Property="Background" Value="Transparent"/>
                                    <Style.Triggers>
                                        <Trigger Property="IsMouseOver" Value="True"><Setter Property="Background" Value="$($colors.ItemHover)"/></Trigger>
                                    </Style.Triggers>
                                </Style>
                            </DataGrid.Resources>
                            <DataGrid.Columns>
                                <DataGridTextColumn Header="任务名称" Binding="{Binding Name}" Width="2*"/>
                                <DataGridTextColumn Header="状态" Binding="{Binding Status}" Width="100">
                                    <DataGridTextColumn.ElementStyle>
                                        <Style TargetType="TextBlock">
                                            <Style.Triggers>
                                                <Trigger Property="Text" Value="下载中"><Setter Property="Foreground" Value="#0078D4"/><Setter Property="FontWeight" Value="Bold"/></Trigger>
                                                <Trigger Property="Text" Value="解压中"><Setter Property="Foreground" Value="#038387"/><Setter Property="FontWeight" Value="Bold"/></Trigger>
                                                <Trigger Property="Text" Value="已完成"><Setter Property="Foreground" Value="#107C10"/></Trigger>
                                                <Trigger Property="Text" Value="失败"><Setter Property="Foreground" Value="#E81123"/></Trigger>
                                                <Trigger Property="Text" Value="已取消"><Setter Property="Foreground" Value="Gray"/></Trigger>
                                            </Style.Triggers>
                                        </Style>
                                    </DataGridTextColumn.ElementStyle>
                                </DataGridTextColumn>
                                <DataGridTextColumn Header="进度" Binding="{Binding Progress}" Width="80"/>
                                <DataGridTemplateColumn Header="操作" Width="80">
                                    <DataGridTemplateColumn.CellTemplate>
                                        <DataTemplate>
                                            <Button Name="KillTask" Content="终止" Height="22" Padding="8,0" FontSize="11"
                                                    Background="#FFF1F0" Foreground="#E81123" BorderBrush="#FFCCC7">
                                                <Button.Style>
                                                    <Style TargetType="Button">
                                                        <Style.Triggers>
                                                            <DataTrigger Binding="{Binding Status}" Value="已完成"><Setter Property="IsEnabled" Value="False"/></DataTrigger>
                                                            <DataTrigger Binding="{Binding Status}" Value="失败"><Setter Property="IsEnabled" Value="False"/></DataTrigger>
                                                            <DataTrigger Binding="{Binding Status}" Value="已取消"><Setter Property="IsEnabled" Value="False"/></DataTrigger>
                                                        </Style.Triggers>
                                                    </Style>
                                                </Button.Style>
                                            </Button>
                                        </DataTemplate>
                                    </DataGridTemplateColumn.CellTemplate>
                                </DataGridTemplateColumn>
                            </DataGrid.Columns>
                        </DataGrid>
                    </Border>
                </Grid>

                <!-- 底部控制 -->
                <StackPanel Grid.Row="2" Margin="0,20,0,0">
                    <Grid Margin="0,0,0,8">
                        <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                        <TextBox Name="PathInput" Grid.Column="0" Margin="0,0,10,0"/>
                        <Button Name="BrowseBtn" Grid.Column="1" Content="更改保存路径" Background="{DynamicResource BtnNormalBrush}"/>
                    </Grid>

                    <!-- 磁盘空间显示 -->
                    <StackPanel Margin="0,0,0,8">
                        <Grid Margin="2,0">
                            <TextBlock Name="DiskLabel" Text="磁盘空间: 计算中..." FontSize="11" Foreground="{DynamicResource TextSecBrush}"/>
                            <TextBlock Name="DiskPercent" Text="0%" HorizontalAlignment="Right" FontSize="11" Foreground="{DynamicResource TextSecBrush}"/>
                        </Grid>
                        <ProgressBar Name="DiskBar" Height="4" Margin="0,5,0,0" Background="{DynamicResource BorderBrush}" Foreground="#0078D4" BorderThickness="0"/>
                    </StackPanel>

                    <!-- 底部队列统计 (隐藏队列时显示) -->
                    <TextBlock Name="StatTextBottom" Text="队列统计: 总计 0 | 运行中 0 | 已完成 0" FontSize="11" Foreground="{DynamicResource TextSecBrush}" Margin="2,0,0,10" Visibility="Collapsed"/>

                    <DockPanel>
                        <StackPanel Orientation="Horizontal" DockPanel.Dock="Left">
                            <CheckBox Name="AutoExtract" Content="下载完成后自动解压到当前目录" IsChecked="True" Style="{StaticResource ToggleSwitchStyle}" Margin="0,0,20,0"/>
                            <CheckBox Name="AutoDelete" Content="解压成功后删除压缩包" IsChecked="True" Style="{StaticResource ToggleSwitchStyle}" />
                        </StackPanel>
                        <StackPanel Orientation="Horizontal" HorizontalAlignment="Right">
                            <Button Name="RefreshBtn" Content="刷新同步" Style="{StaticResource PrimaryButton}" Width="100" Height="34" Margin="0,0,10,0"/>
                            <Button Name="ToggleQueueBtn" Content="隐藏/展开队列" Width="120" Height="34" Style="{StaticResource PrimaryButton}"/>
                        </StackPanel>
                    </DockPanel>
                </StackPanel>
            </Grid>
        </Grid>
    </Border>
</Window>
"@
    $reader = New-Object System.Xml.XmlNodeReader $xaml
    $window = [Windows.Markup.XamlReader]::Load($reader)

    $UI = [PSCustomObject]@{
        Window = $window; MainGrid = $window.FindName("MainGrid"); QueueGrid = $window.FindName("QueueGrid"); UpdateTimeText = $window.FindName("UpdateTime"); PathInput = $window.FindName("PathInput")
        StableRadio = $window.FindName("Stable"); NightlyRadio = $window.FindName("Nightly"); HFRadio = $window.FindName("HF"); MSRadio = $window.FindName("MS")
        RefreshBtn = $window.FindName("RefreshBtn"); ToggleQueueBtn = $window.FindName("ToggleQueueBtn"); BrowseBtn = $window.FindName("BrowseBtn")
        AutoExtract = $window.FindName("AutoExtract"); AutoDelete = $window.FindName("AutoDelete")
        ProjBtn = $window.FindName("ProjBtn"); DocBtn = $window.FindName("DocBtn")
        LoadingOverlay = $window.FindName("LoadingOverlay")
        TitleBar = $window.FindName("TitleBar"); CloseBtn = $window.FindName("CloseBtn")
        MinBtn = $window.FindName("MinBtn"); MaxBtn = $window.FindName("MaxBtn")
        DiskLabel = $window.FindName("DiskLabel"); DiskBar = $window.FindName("DiskBar"); DiskPercent = $window.FindName("DiskPercent")
        QueueHeader = $window.FindName("QueueHeader"); QueueBorder = $window.FindName("QueueBorder"); StatText = $window.FindName("StatText"); StatTextBottom = $window.FindName("StatTextBottom")
        DataQueueGrid = $window.FindName("DataQueueGrid")
        MainBorder = $window.FindName("MainBorder")
    }

    # 统计更新逻辑
    $script:UpdateStatistics = {
        param($UI, $State)

        $queue = $State.TaskQueue
        if ($null -eq $queue) {
            $total = 0
            $running = 0
            $completed = 0
        } else {
            $total = $queue.Count
            $running = (@($queue | Where-Object { $_.Status -eq "下载中" -or $_.Status -eq "解压中" })).Count
            $completed = (@($queue | Where-Object { $_.Status -eq "已完成" })).Count
        }

        $text = "队列统计: 总计 $total | 运行中 $running | 已完成 $completed"
        $UI.Window.Dispatcher.Invoke([Action]{
            $UI.StatText.Text = $text
            $UI.StatTextBottom.Text = $text
        })
    }

    # 队列刷新逻辑
    $script:UpdateQueueUI = {
        param($UI, $State)
        $UI.Window.Dispatcher.Invoke([Action]{
            $UI.QueueGrid.ItemsSource = $null
            $UI.QueueGrid.ItemsSource = $State.TaskQueue
        })
        & $script:UpdateStatistics -UI $UI -State $State
    }

    # 磁盘空间更新逻辑
    $script:UpdateDiskInfo = {
        param($UI)
        try {
            $path = $UI.PathInput.Text
            if (Test-Path $path) {
                # 路径合法：恢复正常颜色
                $UI.PathInput.BorderBrush = [System.Windows.Media.Brushes]::DodgerBlue
                $UI.PathInput.Background = [System.Windows.Media.Brushes]::White

                $drive = Get-PSDrive -PSProvider FileSystem | Where-Object { $path.StartsWith($_.Root) } | Select-Object -First 1
                if ($null -ne $drive) {
                    $total = $drive.Used + $drive.Free
                    $usedPercent = ($drive.Used / $total) * 100
                    $freeGB = [Math]::Round($drive.Free / 1GB, 2)
                    $totalGB = [Math]::Round($total / 1GB, 2)

                    $UI.DiskLabel.Text = "可用空间: $freeGB GB / 总量: $totalGB GB"
                    $UI.DiskBar.Value = $usedPercent
                    $UI.DiskPercent.Text = "$([Math]::Round($usedPercent, 0))%"

                    if ($freeGB -lt 10) {
                        $UI.DiskBar.Foreground = [System.Windows.Media.Brushes]::Red
                        Write-Host "[状态] 磁盘空间严重不足: $freeGB GB" -ForegroundColor Red
                    }
                    else { $UI.DiskBar.Foreground = [System.Windows.Media.Brushes]::DodgerBlue }
                }
            } else {
                # 路径非法：变红提示
                Write-Host "[状态] 当前路径无效: $path" -ForegroundColor Red
                $UI.PathInput.BorderBrush = [System.Windows.Media.Red]
                $UI.PathInput.Background = [System.Windows.Media.SolidColorBrush]::new([System.Windows.Media.Color]::FromArgb(30, 255, 0, 0)) # 浅红背景
                $UI.DiskLabel.Text = "磁盘空间: 路径无效"
                $UI.DiskBar.Value = 0
                $UI.DiskPercent.Text = "ERR"
                $UI.DiskBar.Foreground = [System.Windows.Media.Brushes]::Gray
            }
        } catch {}
    }

    # 处理无边框窗口逻辑 (手动模拟最大化以解决毛玻璃遮挡任务栏)
    $script:RestoreBounds = $null

    $UI.TitleBar.Add_MouseLeftButtonDown({
        if ($null -ne $script:RestoreBounds) {
            # 如果在最大化状态拖动，先还原
            $UI.MaxBtn.RaiseEvent((New-Object System.Windows.RoutedEventArgs([System.Windows.Controls.Button]::ClickEvent)))
        }
        $window.DragMove()
    })
    $UI.TitleBar.Add_MouseLeftButtonDown({ if ($_.ClickCount -eq 2) { $UI.MaxBtn.RaiseEvent((New-Object System.Windows.RoutedEventArgs([System.Windows.Controls.Button]::ClickEvent))) } })

    $UI.MinBtn.Add_Click({ $window.WindowState = "Minimized" })

    $UI.MaxBtn.Add_Click({
        $handle = (New-Object System.Windows.Interop.WindowInteropHelper($window)).Handle
        if ($null -ne $script:RestoreBounds) {
            # 还原逻辑
            $window.Left = $script:RestoreBounds.Left
            $window.Top = $script:RestoreBounds.Top
            $window.Width = $script:RestoreBounds.Width
            $window.Height = $script:RestoreBounds.Height
            $script:RestoreBounds = $null

            $UI.MaxBtn.Content = "⬜"
            if ($null -ne $UI.MainBorder) { $UI.MainBorder.CornerRadius = 12 }
            # 开启系统圆角裁切以解决毛玻璃穿透
            [BlurHelper]::SetRounding($handle, $true)
        } else {
            # 手动模拟最大化逻辑 (不使用 WindowState = Maximized)
            $script:RestoreBounds = [PSCustomObject]@{
                Left = $window.Left; Top = $window.Top; Width = $window.Width; Height = $window.Height
            }

            # 获取当前屏幕工作区 (Win32 Pixels)
            $screen = [System.Windows.Forms.Screen]::FromHandle($handle)
            $workingArea = $screen.WorkingArea

            # 考虑 DPI 缩放转换
            $source = [System.Windows.PresentationSource]::FromVisual($window)
            if ($null -ne $source) {
                $matrix = $source.CompositionTarget.TransformToDevice
                $window.Left = $workingArea.X / $matrix.M11
                $window.Top = $workingArea.Y / $matrix.M22
                $window.Width = $workingArea.Width / $matrix.M11
                $window.Height = $workingArea.Height / $matrix.M22
            }

            $UI.MaxBtn.Content = "❐"
            if ($null -ne $UI.MainBorder) { $UI.MainBorder.CornerRadius = 0 }
            # 关闭系统圆角裁切
            [BlurHelper]::SetRounding($handle, $false)
        }
    })
    $UI.CloseBtn.Add_Click({ $window.Close() })

    $State = [PSCustomObject]@{ Metadata = $null; TaskQueue = @(); CurrentTask = $null; CurrentExtractionTask = $null; IsCancelled = $false }

    $UI.RefreshBtn.Add_Click({ Invoke-Refresh -UI $UI -State $State })
    $onStateChanged = { & $script:SyncDataGridLogic -UI $UI -State $State }
    $UI.StableRadio.Add_Checked($onStateChanged); $UI.NightlyRadio.Add_Checked($onStateChanged); $UI.HFRadio.Add_Checked($onStateChanged); $UI.MSRadio.Add_Checked($onStateChanged)

    # 实时验证路径
    $UI.PathInput.Add_TextChanged({ & $script:UpdateDiskInfo -UI $UI })

    $UI.BrowseBtn.Add_Click({
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog;
        if ($dialog.ShowDialog() -eq "OK") {
            $UI.PathInput.Text = $dialog.SelectedPath
        }
    })
    $UI.MainGrid.AddHandler([System.Windows.Controls.Button]::ClickEvent, [System.Windows.RoutedEventHandler]{ param($s, $e) if ($e.OriginalSource.Name -eq "RowDL") { Invoke-DownloadAction -UI $UI -State $State -Button $e.OriginalSource } })

    $UI.ProjBtn.Add_Click({ Open-Url -Url "https://github.com/licyk/sd-webui-all-in-one" })
    $UI.DocBtn.Add_Click({ Open-Url -Url "https://github.com/licyk/sd-webui-all-in-one/discussions/1" })

    # 队列显隐切换 (增加过渡动画)
    $UI.ToggleQueueBtn.Add_Click({
        $duration = [TimeSpan]::FromMilliseconds(300)
        $targetHeight = 140 # 设定的展开高度

        if ($UI.QueueBorder.Visibility -eq "Visible" -and $UI.QueueBorder.Height -gt 0) {
            # 收起动画
            $animHeight = New-Object System.Windows.Media.Animation.DoubleAnimation(0, $duration)
            $animOpacity = New-Object System.Windows.Media.Animation.DoubleAnimation(0, $duration)

            $animHeight.add_Completed({
                $UI.QueueBorder.Visibility = "Collapsed"
                $UI.QueueHeader.Visibility = "Collapsed"
                $UI.StatTextBottom.Visibility = "Visible"
            })

            $UI.QueueBorder.BeginAnimation([System.Windows.Controls.Border]::HeightProperty, $animHeight)
            $UI.QueueBorder.BeginAnimation([System.Windows.Controls.Border]::OpacityProperty, $animOpacity)
            $UI.QueueHeader.BeginAnimation([System.Windows.Controls.Grid]::OpacityProperty, $animOpacity)
        } else {
            # 展开动画
            $UI.QueueBorder.Visibility = "Visible"
            $UI.QueueHeader.Visibility = "Visible"
            $UI.StatTextBottom.Visibility = "Collapsed"

            $animHeight = New-Object System.Windows.Media.Animation.DoubleAnimation($targetHeight, $duration)
            $animOpacity = New-Object System.Windows.Media.Animation.DoubleAnimation(1, $duration)

            $UI.QueueBorder.BeginAnimation([System.Windows.Controls.Border]::HeightProperty, $animHeight)
            $UI.QueueBorder.BeginAnimation([System.Windows.Controls.Border]::OpacityProperty, $animOpacity)
            $UI.QueueHeader.BeginAnimation([System.Windows.Controls.Grid]::OpacityProperty, $animOpacity)
        }
    })

    # 个体任务终止逻辑
    $UI.QueueGrid.AddHandler([System.Windows.Controls.Button]::ClickEvent, [System.Windows.RoutedEventHandler]{
        param($s, $e)
        if ($e.OriginalSource.Name -eq "KillTask") {
            $task = $e.OriginalSource.DataContext
            Write-Host "[UI] 用户请求终止任务: $($task.Name)" -ForegroundColor Yellow

            # 如果是当前运行的下载任务
            if ($null -ne $State.CurrentTask -and $State.CurrentTask.QueueTask -eq $task) {
                $task.Status = "已取消"
                try { Stop-Process -Id $State.CurrentTask.Process.Id -Force -ErrorAction SilentlyContinue } catch {}
            }
            # 如果是当前运行的解压任务
            elseif ($null -ne $State.CurrentExtractionTask -and $State.CurrentExtractionTask.QueueTask -eq $task) {
                $task.Status = "已取消"
                try { Stop-Process -Id $State.CurrentExtractionTask.Process.Id -Force -ErrorAction SilentlyContinue } catch {}
            }
            # 等待中任务
            else {
                $task.Status = "已取消"
            }
            & $script:UpdateQueueUI -UI $UI -State $State
        }
    })

    # 定时器：主调度器与磁盘空间刷新
    $script:tickCounter = 0
    $timer = New-Object System.Windows.Threading.DispatcherTimer
    $timer.Interval = [TimeSpan]::FromMilliseconds(100)
    $timer.Add_Tick({
        # 1. 磁盘空间刷新 (1s)
        $script:tickCounter++
        if ($script:tickCounter -ge 10) {
            $script:tickCounter = 0
            & $script:UpdateDiskInfo -UI $UI
        }

        # 2. 任务调度逻辑
        $isAnyBusy = ($null -ne $State.CurrentTask -or $null -ne $State.CurrentExtractionTask)
        if (-not $isAnyBusy) {
            # 查找队列中第一个等待中的任务
            $nextTask = $State.TaskQueue | Where-Object { $_.Status -eq "等待中" } | Select-Object -First 1
            if ($null -ne $nextTask) {
                $nextTask.Status = "下载中"
                & $script:UpdateQueueUI -UI $UI -State $State
                Invoke-DownloadTask -Url $nextTask.Url -OutDir $nextTask.OutDir -SaveName $nextTask.Name -State $State -QueueTask $nextTask | Out-Null
            }
        }

        # 3. 下载进程监控
        if ($null -ne $State.CurrentTask) {
            $task = $State.CurrentTask
            if ($task.Process.HasExited) {
                $exitCode = $task.Process.ExitCode
                Write-Host "[任务] 下载进程退出 [代码: $exitCode]" -ForegroundColor Blue

                if ($task.QueueTask.Status -ne "已取消") {
                    if ($exitCode -eq 0) {
                        if ($task.QueueTask.AutoExtract) {
                            $task.QueueTask.Progress = "50%"
                            $task.QueueTask.Status = "解压中"
                            $fullPath = Join-Path $task.OutDir $task.SaveName
                            Write-Host "[后处理] 下载完成，开始解压: $fullPath" -ForegroundColor Cyan
                            Show-Async-MsgBox -Message "下载已完成，正在后台启动解压...`n`n源文件：`n$fullPath`n`n解压目录：`n$($task.OutDir)" -Title "下载完成"
                            Start-ExtractionTask -FilePath $fullPath -ExtractDir $task.OutDir -State $State -QueueTask $task.QueueTask | Out-Null
                        } else {
                            $task.QueueTask.Progress = "100%"
                            $task.QueueTask.Status = "已完成"
                            Show-Async-MsgBox -Message "任务已全部完成！`n`n保存文件：`n$($task.SaveName)`n`n保存路径：`n$($task.OutDir)" -Title "任务完成"
                        }
                    } else {
                        $task.QueueTask.Status = "失败"
                        Show-Async-MsgBox -Message "任务下载失败，请检查控制台日志。`n退出码: ${exitCode}`n`n报告问题与寻求帮助请前往: `nhttps://github.com/licyk/sd-webui-all-in-one/issues" -Title "下载失败" -Icon "Error"
                    }
                }
                $State.CurrentTask = $null
                & $script:UpdateQueueUI -UI $UI -State $State
            }
        }

        # 4. 解压进程监控
        if ($null -ne $State.CurrentExtractionTask) {
            $task = $State.CurrentExtractionTask
            if ($task.Process.HasExited) {
                $exitCode = $task.Process.ExitCode
                Write-Host "[后处理] 解压进程退出 [代码: $exitCode]" -ForegroundColor Blue

                if ($task.QueueTask.Status -ne "已取消") {
                    if ($exitCode -eq 0) {
                        $task.QueueTask.Status = "已完成"
                        $task.QueueTask.Progress = "100%"
                        if ($task.QueueTask.AutoDelete) {
                            try {
                                Remove-Item $task.FilePath -Force
                                Write-Host "[后处理] 已删除压缩包: $($task.FilePath)" -ForegroundColor Gray
                            } catch {
                                Write-Host "[后处理] 删除压缩包失败: $($_.Exception.Message)" -ForegroundColor Red
                            }
                        }
                        Show-Async-MsgBox -Message "解压已成功完成！`n`n源文件：`n$($task.FilePath)`n`n解压至：`n$($task.ExtractDir)" -Title "解压成功"
                    } else {
                        $task.QueueTask.Status = "失败"
                        Show-Async-MsgBox -Message "解压过程中出现错误，请检查控制台日志。`n退出码: ${exitCode}`n`n报告问题与寻求帮助请前往: `nhttps://github.com/licyk/sd-webui-all-in-one/issues" -Title "解压失败" -Icon "Error"
                    }
                }
                $State.CurrentExtractionTask = $null
                & $script:UpdateQueueUI -UI $UI -State $State
            }
        }
    })
    $timer.Start()

    $UI.PathInput.Text = if ($PSScriptRoot) {
        $PSScriptRoot
    } elseif ($script:ScriptRootPath) {
        $script:ScriptRootPath
    } elseif ($env:SCRIPT_ROOT_PATH) {
        $env:SCRIPT_ROOT_PATH
    } else {
        (Get-Location).Path
    }
    $window.Add_Loaded({
        # 获取窗口句柄
        $handle = (New-Object System.Windows.Interop.WindowInteropHelper($window)).Handle

        # 开启毛玻璃效果
        [BlurHelper]::EnableBlur($handle)

        # 应用系统圆角偏好 (解决毛玻璃穿透圆角问题)
        [BlurHelper]::SetRounding($handle, $true)

        # 设置 DWM 沉浸式深色模式
        [BlurHelper]::SetDarkMode($handle, $isDarkMode)

        & $script:UpdateDiskInfo -UI $UI
        Invoke-Refresh -UI $UI -State $State
        Invoke-Update-Async -IsDarkMode $isDarkMode
    })
    $window.ShowDialog() | Out-Null
    $timer.Stop()
    Write-Host "[APP] 退出应用" -ForegroundColor Yellow
}

Start-App
