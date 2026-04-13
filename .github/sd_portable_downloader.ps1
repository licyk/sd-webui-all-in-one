Add-Type -AssemblyName PresentationFramework, System.Windows.Forms

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

function Get-Portable-Metadata {
    param([string]$Uri = "https://licyk.github.io/resources/portable_list.json")

    try {
        Write-Host "[数据管理] 下载整合包数据中" -ForegroundColor Yellow
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 10 -ErrorAction Stop
        return $response.Content | ConvertFrom-Json
    }
    catch {
        Write-Error "[数据管理] 下载整合包数据失败: $($_.Exception.Message)"
        return $null
    }
}

function Get-Aria2-Executable {
    $binUrl = "https://www.modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/aria2/windows/amd64/aria2c.exe"
    $binPath = Join-Path ([IO.Path]::GetTempPath()) "aria2c.exe"
    $localBinPath = Get-Command aria2c -ErrorAction SilentlyContinue

    if ($null -eq $localBinPath) { return $localBinPath.Source }
    if (Test-Path $binPath) {
        try { 
            & "$binPath" --version > $null
            if ($?) { return $binPath } 
        } catch { }
    }

    Write-Host "[环境初始化] 正在下发 Aria2 核心组件..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $binUrl -OutFile $binPath
    return $binPath
}

function Get-7za-Executable {
    $binUrl = "https://modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/7za/windows/amd64/7za.exe"
    $binPath = Join-Path ([IO.Path]::GetTempPath()) "7za.exe"
    $localBinPath = Get-Command 7za -ErrorAction SilentlyContinue
    $localBinPath7z = Get-Command 7z -ErrorAction SilentlyContinue

    if ($null -eq $localBinPath) { return $localBinPath.Source }
    if ($null -eq $localBinPath7z) { return $localBinPath7z.Source }
    if (Test-Path $binPath) {
        try { 
            & "$binPath" > $null
            if ($?) { return $binPath } 
        } catch { }
    }

    Write-Host "[环境初始化] 正在下发 7-Zip 解压组件..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $binUrl -OutFile $binPath
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
        Show-Async-MsgBox -Message "检测到并发冲突：已有任务正在运行。" -Title "警告" -Icon "Warning"
        return $null 
    }

    $bin = Get-Aria2-Executable
    $launch_args = "-c -x 16 -s 64 -k 1M --file-allocation=none --summary-interval=0 --console-log-level=error -d `"$OutDir`" `"$Url`" -o `"$SaveName`""

    try {
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
        return $taskInfo.Id
    }
    catch {
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

function Sync-DataGrid-View {
    param($UI, $State)
    if ($null -eq $State.Metadata) { return }

    $versionType = if ($UI.StableRadio.IsChecked) { "stable" } else { "nightly" }
    $sourceName  = if ($UI.HFRadio.IsChecked) { "huggingface" } else { "modelscope" }

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
                        Type     = $comp.Name
                        Versions = $versions 
                    }
                }
            }
        }
    }
    $UI.MainGrid.ItemsSource = $null
    $UI.MainGrid.ItemsSource = $gridSource
}

function Invoke-Refresh {
    param($UI, $State)
    $data = Get-Portable-Metadata
    if ($null -ne $data) {
        $State.Metadata = $data
        $UI.UpdateTimeText.Text = "更新时间: $($data.update_time)"
        Sync-DataGrid-View -UI $UI -State $State
    }
}

function Invoke-DownloadAction {
    param($UI, $State, $Button)
    $savePath = $UI.PathInput.Text
    if (-not (Test-Path $savePath -PathType Container)) {
        Show-Async-MsgBox -Message "下载路径无效。" -Title "错误" -Icon "Error"
        return
    }

    $rowData = $Button.DataContext
    $rowIndex = $UI.MainGrid.Items.IndexOf($rowData)
    $rowContainer = $UI.MainGrid.ItemContainerGenerator.ContainerFromIndex($rowIndex)
    $combo = Find-Visual-Element -Parent $rowContainer -Name "VersionSelector"

    $selected = if ($null -ne $combo -and $null -ne $combo.SelectedItem) { $combo.SelectedItem } else { $rowData.Versions[0] }
    
    # 路径可视化增强
    $fullDest = Join-Path $savePath $selected.Name
    Show-Async-MsgBox -Message "任务已开始后台下载：`n$($selected.Name)`n`n保存路径：`n$fullDest" -Title "任务下发"

    $taskId = Invoke-DownloadTask -Url $selected.Url -OutDir $savePath -SaveName $selected.Name -State $State
    if ($null -ne $taskId) { $UI.StopBtn.IsEnabled = $true }
}

function Start-App {
    [xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" 
        Title="AI 整合包下载器" Height="700" Width="750" WindowStartupLocation="CenterScreen">
    <Grid Margin="15">
        <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>

        <Grid Grid.Row="0" Margin="0,0,0,10">
            <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
            <StackPanel Grid.Column="0">
                <TextBlock Name="UpdateTime" Text="状态: 等待同步..." FontSize="12" Foreground="Gray"/>
                <StackPanel Orientation="Horizontal" Margin="0,10">
                    <TextBlock Text="版本:" VerticalAlignment="Center" Margin="0,0,10,0"/><RadioButton Name="Stable" Content="Stable" GroupName="V"/><RadioButton Name="Nightly" Content="Nightly" IsChecked="True" GroupName="V" Margin="10,0"/>
                    <TextBlock Text="下载源:" VerticalAlignment="Center" Margin="20,0,10,0"/><RadioButton Name="HF" Content="HuggingFace" GroupName="S"/><RadioButton Name="MS" Content="ModelScope" IsChecked="True" GroupName="S" Margin="10,0"/>
                </StackPanel>
            </StackPanel>
            <StackPanel Grid.Column="1" Orientation="Horizontal" VerticalAlignment="Top">
                <Button Name="ProjBtn" Content="项目主页" Padding="8,3" Margin="0,0,5,0" Cursor="Hand" Background="Transparent" Foreground="Blue" BorderThickness="0"/>
                <Button Name="DocBtn" Content="整合包使用说明" Padding="8,3" Cursor="Hand" Background="Transparent" Foreground="Blue" BorderThickness="0"/>
            </StackPanel>
        </Grid>

        <DataGrid Name="MainGrid" Grid.Row="1" AutoGenerateColumns="False" IsReadOnly="True" GridLinesVisibility="Horizontal">
            <DataGrid.Columns>
                <DataGridTextColumn Header="资源类型" Binding="{Binding Type}" Width="150"/>
                <DataGridTemplateColumn Header="版本选择" Width="*"><DataGridTemplateColumn.CellTemplate><DataTemplate><ComboBox Name="VersionSelector" ItemsSource="{Binding Versions}" DisplayMemberPath="Name" SelectedIndex="0" Margin="5,2"/></DataTemplate></DataGridTemplateColumn.CellTemplate></DataGridTemplateColumn>
                <DataGridTemplateColumn Header="操作" Width="80"><DataGridTemplateColumn.CellTemplate><DataTemplate><Button Name="RowDL" Content="下载" Padding="5,2"/></DataTemplate></DataGridTemplateColumn.CellTemplate></DataGridTemplateColumn>
            </DataGrid.Columns>
        </DataGrid>

        <StackPanel Grid.Row="2" Margin="0,15,0,0">
            <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                <TextBox Name="PathInput" Grid.Column="0" VerticalContentAlignment="Center" Margin="0,0,10,0"/><Button Name="BrowseBtn" Grid.Column="1" Content="选择下载路径" Padding="10,5"/>
            </Grid>
            <CheckBox Name="AutoExtract" Content="下载完成后自动解压" IsChecked="True" Margin="0,10,0,5"/>
            <UniformGrid Columns="2" Margin="0,5,0,0">
                <Button Name="RefreshBtn" Content="同步云端数据" Margin="0,0,5,0" Height="35"/><Button Name="StopBtn" Content="终止当前任务" IsEnabled="False" Margin="5,0,0,0" Height="35"/>
            </UniformGrid>
        </StackPanel>
    </Grid>
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
    }

    $State = [PSCustomObject]@{ Metadata = $null; IsDownloading = $false; CurrentTask = $null; IsCancelled = $false }

    $UI.RefreshBtn.Add_Click({ Invoke-Refresh -UI $UI -State $State })
    $onStateChanged = { Sync-DataGrid-View -UI $UI -State $State }
    $UI.StableRadio.Add_Checked($onStateChanged); $UI.NightlyRadio.Add_Checked($onStateChanged); $UI.HFRadio.Add_Checked($onStateChanged); $UI.MSRadio.Add_Checked($onStateChanged)
    $UI.BrowseBtn.Add_Click({ $dialog = New-Object System.Windows.Forms.FolderBrowserDialog; if ($dialog.ShowDialog() -eq "OK") { $UI.PathInput.Text = $dialog.SelectedPath } })
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

    $timer = New-Object System.Windows.Threading.DispatcherTimer
    $timer.Interval = [TimeSpan]::FromMilliseconds(100)
    $timer.Add_Tick({
        if ($State.IsDownloading -and $null -ne $State.CurrentTask) {
            $task = $State.CurrentTask
            if ($task.Process.HasExited) {
                $State.IsDownloading = $false
                $UI.StopBtn.IsEnabled = $false
                if ($State.IsCancelled) {
                    $State.IsCancelled = $false
                } else {
                    $exitCode = $task.Process.ExitCode
                    if ($exitCode -eq 0) {
                        $fullPath = Join-Path $task.OutDir $task.SaveName
                        if ($UI.AutoExtract.IsChecked) {
                            Show-Async-MsgBox -Message "下载已完成，正在后台启动解压程序...`n`n保存文件：$($task.SaveName)`n保存目录：$($task.OutDir)" -Title "下载成功"
                            Invoke-Extraction -FilePath $fullPath -ExtractDir $task.OutDir
                        } else {
                            Show-Async-MsgBox -Message "下载已完成。`n`n保存文件：$($task.SaveName)`n保存路径：$($task.OutDir)" -Title "下载成功"
                        }
                    } else {
                        Show-Async-MsgBox -Message "下载失败。退出码: $exitCode" -Title "下载失败" -Icon "Error"
                    }
                }
                $State.CurrentTask = $null
            }
        }
    })
    $timer.Start()

    $UI.PathInput.Text = $PSScriptRoot
    $window.Add_Loaded({ Invoke-Refresh -UI $UI -State $State })
    $window.ShowDialog() | Out-Null
    $timer.Stop()
}

Start-App
