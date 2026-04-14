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

    public static void EnableBlur(IntPtr hwnd) {
        var accent = new AccentPolicy();
        accent.AccentState = 3; // ACCENT_ENABLE_BLURBEHIND

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
}
"@ -PassThru | Out-Null

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

function Open-Url {
    param([string]$Url)
    try { Start-Process $Url } catch { Write-Warning "无法打开链接: $Url" }
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
    Invoke-WebRequest -UseBasicParsing -Uri $binUrl -OutFile $binPath
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
    Invoke-WebRequest -UseBasicParsing -Uri $binUrl -OutFile $binPath
    return $binPath
}

function Invoke-DownloadTask {
    param(
        [Parameter(Mandatory)] [string]$Url,
        [Parameter(Mandatory)] [string]$OutDir,
        [Parameter(Mandatory)] [string]$SaveName,
        [Parameter(Mandatory)] [Object]$State
    )

    if ($State.IsDownloading) { 
        Write-Host "[任务] 拒绝启动：已有正在运行的任务" -ForegroundColor Red
        Show-Async-MsgBox -Message "检测到并发冲突：已有任务正在运行。" -Title "警告" -Icon "Warning"
        return $null 
    }

    $bin = Get-Aria2-Executable
    $launch_args = "-c -x 16 -s 64 -k 1M --file-allocation=none --summary-interval=0 --console-log-level=error -d `"$OutDir`" `"$Url`" -o `"$SaveName`""

    try {
        Write-Host "[任务] 正在启动 Aria2 下载引擎..." -ForegroundColor Blue
        Write-Host "[任务] 目标: $SaveName" -ForegroundColor Gray
        Write-Host "[任务] 目录: $OutDir" -ForegroundColor Gray

        $process = Start-Process -FilePath $bin -ArgumentList $launch_args -PassThru -NoNewWindow
        $process.EnableRaisingEvents = $true

        $taskInfo = [PSCustomObject]@{ 
            Id       = "Task-" + [guid]::NewGuid().Guid.Substring(0, 8)
            Process  = $process; 
            SaveName = $SaveName; 
            OutDir   = $OutDir 
        }

        $State.CurrentTask = $taskInfo
        $State.IsDownloading = $true
        $State.IsCancelled = $false
        Write-Host "[任务] 引擎启动成功 [PID: $($process.Id)]" -ForegroundColor Green
        return $taskInfo.Id
    }
    catch {
        Write-Host "[任务] 启动下载任务失败: $($_.Exception.Message)" -ForegroundColor Red
        Write-Error "启动下载任务失败: $_"
        return $null
    }
}

function Invoke-Extraction {
    param([string]$FilePath, [string]$ExtractDir)

    $bin = Get-7za-Executable
    Write-Host "[后处理] 正在解压文件: $FilePath ..." -ForegroundColor Cyan

    $rs = [runspacefactory]::CreateRunspace()
    $rs.Open()
    $ps = [powershell]::Create().AddScript({
        param($bin, $file, $dir)
        $proc = Start-Process -FilePath $bin -ArgumentList "x `"$file`" -o`"$dir`" -y" -Wait -PassThru -NoNewWindow
        $proc.EnableRaisingEvents = $true

        # 解压完成后的异步弹窗逻辑
        Add-Type -AssemblyName PresentationFramework
        if ($proc.ExitCode -eq 0) {
            [System.Windows.MessageBox]::Show("解压已成功完成！`n`n源文件：$file`n解压至：$dir", "解压成功", "OK", "Information")
        } else {
            [System.Windows.MessageBox]::Show("解压过程中出现错误。`n退出码: $($proc.ExitCode)", "解压失败", "OK", "Error")
        }
        return $proc.ExitCode
    }).AddArgument($bin).AddArgument($FilePath).AddArgument($ExtractDir)

    $ps.Runspace = $rs
    $ps.BeginInvoke() | Out-Null
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
        $Global:DownloadRunspacePool = [runspacefactory]::CreateRunspacePool(1, 1)
        $Global:DownloadRunspacePool.Open()
    }

    $ps = [powershell]::Create().AddScript({
        param([string]$Uri)
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 15 -ErrorAction Stop
            return $response.Content | ConvertFrom-Json
        } catch {
            return "ERROR: " + $_.Exception.Message
        }
    }).AddArgument("https://licyk.github.io/resources/portable_list.json")

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
    Write-Host "[UI] 用户点击下载: $($selected.Name)" -ForegroundColor Cyan
    
    # 路径可视化增强
    $fullDest = Join-Path $savePath $selected.Name
    Show-Async-MsgBox -Message "任务已开始后台下载：`n$($selected.Name)`n`n保存路径：`n$fullDest" -Title "任务下发"

    $taskId = Invoke-DownloadTask -Url $selected.Url -OutDir $savePath -SaveName $selected.Name -State $State
    if ($null -ne $taskId) { $UI.StopBtn.IsEnabled = $true }
}

function Start-App {
    Write-Host "[APP] 初始化中..." -ForegroundColor Yellow
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
        Title="AI 整合包下载器" Height="700" Width="780"
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
    <Border CornerRadius="12" BorderThickness="1" BorderBrush="{DynamicResource BorderBrush}" ClipToBounds="True">
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

                <!-- 数据表格：禁用选中效果 -->
                <Border Grid.Row="1" Background="{DynamicResource PanelBGBrush}" CornerRadius="8" BorderThickness="1" BorderBrush="{DynamicResource BorderBrush}">
                    <DataGrid Name="MainGrid" AutoGenerateColumns="False" IsReadOnly="True"
                              HeadersVisibility="Column" GridLinesVisibility="None" Background="Transparent"
                              BorderThickness="0" RowHeight="42" Visibility="Collapsed"
                              SelectionMode="Single" SelectionUnit="FullRow">
                        <DataGrid.Resources>
                            <!-- 移除单元格选中样式并设置居中 -->
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
                            <DataGridTextColumn Header="资源类型" Binding="{Binding Type}" Width="160"/>
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
                </Border>

                <!-- 加载遮罩 -->
                <StackPanel Name="LoadingOverlay" Grid.Row="1" VerticalAlignment="Center" HorizontalAlignment="Center">
                    <ProgressBar IsIndeterminate="True" Width="220" Height="4" Background="{DynamicResource BorderBrush}" Foreground="#0078D4" BorderThickness="0"/>
                    <TextBlock Text="正在同步云端元数据..." Margin="0,15,0,0" HorizontalAlignment="Center" Foreground="{DynamicResource TextSecBrush}" FontSize="13"/>
                </StackPanel>

                <!-- 底部控制 -->
                <StackPanel Grid.Row="2" Margin="0,20,0,0">
                    <Grid Margin="0,0,0,8">
                        <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                        <TextBox Name="PathInput" Grid.Column="0" Margin="0,0,10,0"/>
                        <Button Name="BrowseBtn" Grid.Column="1" Content="更改保存路径" Background="{DynamicResource BtnNormalBrush}"/>
                    </Grid>

                    <!-- 磁盘空间显示 -->
                    <StackPanel Margin="0,0,0,15">
                        <Grid Margin="2,0">
                            <TextBlock Name="DiskLabel" Text="磁盘空间: 计算中..." FontSize="11" Foreground="{DynamicResource TextSecBrush}"/>
                            <TextBlock Name="DiskPercent" Text="0%" HorizontalAlignment="Right" FontSize="11" Foreground="{DynamicResource TextSecBrush}"/>
                        </Grid>
                        <ProgressBar Name="DiskBar" Height="4" Margin="0,5,0,0" Background="{DynamicResource BorderBrush}" Foreground="#0078D4" BorderThickness="0"/>
                    </StackPanel>

                    <DockPanel>
                        <CheckBox Name="AutoExtract" Content="下载完成后自动解压到当前目录" IsChecked="True" Style="{StaticResource ToggleSwitchStyle}" DockPanel.Dock="Left"/>
                        <StackPanel Orientation="Horizontal" HorizontalAlignment="Right">
                            <Button Name="RefreshBtn" Content="刷新同步" Style="{StaticResource PrimaryButton}" Width="100" Height="34" Margin="0,0,10,0"/>
                            <Button Name="StopBtn" Content="终止任务" Width="100" Height="34" IsEnabled="False" Background="#FFF1F0" Foreground="#E81123" BorderBrush="#FFCCC7"/>
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
        Window = $window; MainGrid = $window.FindName("MainGrid"); UpdateTimeText = $window.FindName("UpdateTime"); PathInput = $window.FindName("PathInput")
        StableRadio = $window.FindName("Stable"); NightlyRadio = $window.FindName("Nightly"); HFRadio = $window.FindName("HF"); MSRadio = $window.FindName("MS")
        RefreshBtn = $window.FindName("RefreshBtn"); StopBtn = $window.FindName("StopBtn"); BrowseBtn = $window.FindName("BrowseBtn")
        AutoExtract = $window.FindName("AutoExtract")
        ProjBtn = $window.FindName("ProjBtn"); DocBtn = $window.FindName("DocBtn")
        LoadingOverlay = $window.FindName("LoadingOverlay")
        TitleBar = $window.FindName("TitleBar"); CloseBtn = $window.FindName("CloseBtn")
        MinBtn = $window.FindName("MinBtn"); MaxBtn = $window.FindName("MaxBtn")
        DiskLabel = $window.FindName("DiskLabel"); DiskBar = $window.FindName("DiskBar"); DiskPercent = $window.FindName("DiskPercent")
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
                $UI.PathInput.BorderBrush = [System.Windows.Media.Brushes]::Red
                $UI.PathInput.Background = [System.Windows.Media.SolidColorBrush]::new([System.Windows.Media.Color]::FromArgb(30, 255, 0, 0)) # 浅红背景
                $UI.DiskLabel.Text = "磁盘空间: 路径无效"
                $UI.DiskBar.Value = 0
                $UI.DiskPercent.Text = "ERR"
                $UI.DiskBar.Foreground = [System.Windows.Media.Brushes]::Gray
            }
        } catch {}
    }

    # 处理无边框窗口逻辑
    $UI.TitleBar.Add_MouseLeftButtonDown({ $window.DragMove() })
    $UI.TitleBar.Add_MouseLeftButtonDown({ if ($_.ClickCount -eq 2) { $UI.MaxBtn.RaiseEvent((New-Object System.Windows.RoutedEventArgs([System.Windows.Controls.Button]::ClickEvent))) } })

    $UI.MinBtn.Add_Click({ $window.WindowState = "Minimized" })
    $UI.MaxBtn.Add_Click({
        if ($window.WindowState -eq "Maximized") {
            $window.WindowState = "Normal"
            $UI.MaxBtn.Content = "⬜"
        } else {
            $window.WindowState = "Maximized"
            $UI.MaxBtn.Content = "❐"
        }
    })
    $UI.CloseBtn.Add_Click({ $window.Close() })

    $State = [PSCustomObject]@{ Metadata = $null; IsDownloading = $false; CurrentTask = $null; IsCancelled = $false }

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

    $UI.StopBtn.Add_Click({ 
        if ($State.IsDownloading -and $null -ne $State.CurrentTask) { 
            $State.IsCancelled = $true
            Stop-Process -Id $State.CurrentTask.Process.Id -Force
            $UI.StopBtn.IsEnabled = $false 
            Show-Async-MsgBox -Message "任务已由用户手动终止。" -Title "任务终止" -Icon "Warning"
        } 
    })

    # 定时器增强：增加磁盘空间每秒刷新
    $tickCounter = 0
    $timer = New-Object System.Windows.Threading.DispatcherTimer
    $timer.Interval = [TimeSpan]::FromMilliseconds(100)
    $timer.Add_Tick({
        # 磁盘空间每 1 秒 (10 * 100ms) 自动刷新一次
        $script:tickCounter++
        if ($script:tickCounter -ge 10) {
            $script:tickCounter = 0
            & $script:UpdateDiskInfo -UI $UI
        }

        if ($State.IsDownloading -and $null -ne $State.CurrentTask) {
            $task = $State.CurrentTask
            if ($task.Process.HasExited) {
                Write-Host "[任务] 引擎进程已退出 [ExitCode: $($task.Process.ExitCode)]" -ForegroundColor Blue
                $State.IsDownloading = $false
                $UI.StopBtn.IsEnabled = $false
                if ($State.IsCancelled) {
                    Write-Host "[状态] 任务由用户取消" -ForegroundColor Yellow
                    $State.IsCancelled = $false
                } else {
                    $exitCode = $task.Process.ExitCode
                    if ($exitCode -eq 0) {
                        Write-Host "[状态] 下载已成功完成: $($task.SaveName)" -ForegroundColor Green
                        $fullPath = Join-Path $task.OutDir $task.SaveName
                        if ($UI.AutoExtract.IsChecked) {
                            Show-Async-MsgBox -Message "下载已完成，正在后台启动解压程序...`n`n保存文件：$($task.SaveName)`n保存目录：$($task.OutDir)" -Title "下载成功"
                            Invoke-Extraction -FilePath $fullPath -ExtractDir $task.OutDir
                        } else {
                            Show-Async-MsgBox -Message "下载已完成。`n`n保存文件：$($task.SaveName)`n保存路径：$($task.OutDir)" -Title "下载成功"
                        }
                    } else {
                        Write-Host "[状态] 下载过程中出现错误 [代码: $exitCode]" -ForegroundColor Red
                        Show-Async-MsgBox -Message "下载失败。退出码: $exitCode" -Title "下载失败" -Icon "Error"
                    }
                }
                $State.CurrentTask = $null
            }
        }
    })
    $timer.Start()

    $UI.PathInput.Text = $PSScriptRoot
    $window.Add_Loaded({
        # 获取窗口句柄并开启毛玻璃
        $handle = (New-Object System.Windows.Interop.WindowInteropHelper($window)).Handle
        [BlurHelper]::EnableBlur($handle)

        & $script:UpdateDiskInfo -UI $UI
        Invoke-Refresh -UI $UI -State $State
    })
    $window.ShowDialog() | Out-Null
    $timer.Stop()
    Write-Host "[APP] 退出应用" -ForegroundColor Yellow
}

Start-App
