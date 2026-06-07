@echo off

echo =================================================================
echo :: More information: https://github.com/licyk/sd-webui-all-in-one
echo =================================================================
>nul 2>&1 "%SYSTEMROOT%\system32\icacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo :: Requesting administrative privileges
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo :: Write vbs script to request administrative privileges
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo :: Executing vbs script
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    echo :: Launch CMD with administrative privileges
    if exist "%temp%\getadmin.vbs" ( del "%temp%\getadmin.vbs" )
    pushd "%CD%"
    CD /D "%~dp0"
    goto configureEnv

:configureEnv
    title Configure environment
    echo :: Set PowerShell execution policies
    echo :: Executing command: "Set-ExecutionPolicy Unrestricted -Scope CurrentUser"
    powershell -NoLogo -NoProfile -Command "Set-ExecutionPolicy Unrestricted -Scope CurrentUser"
    echo :: Enable long paths supported
    echo :: Executing command: "New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force"
    powershell -NoLogo -NoProfile -Command "New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force"
    echo :: Set .ps1 default open method to PowerShell
    echo :: Download set_ps1_default_powershell.ps1 from mirrors and execute it
    powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "& { $ErrorActionPreference = 'Stop'; $scriptPath = $null; $tempPath = $null; try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12; $urls = @('https://github.com/licyk/sd-webui-all-in-one/raw/main/.github/set_ps1_default_powershell.ps1', 'https://gitee.com/licyk/sd-webui-all-in-one/raw/main/.github/set_ps1_default_powershell.ps1', 'https://gitlab.com/licyk/sd-webui-all-in-one/-/raw/main/.github/set_ps1_default_powershell.ps1'); $localAppData = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData); $cacheDir = Join-Path $localAppData 'Temp'; New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null; $scriptPath = Join-Path $cacheDir 'set_ps1_default_powershell.ps1'; $downloaded = $false; foreach ($url in $urls) { Write-Host (':: Trying to download: ' + $url); try { $tempPath = $scriptPath + '.download'; if (Test-Path -LiteralPath $tempPath) { Remove-Item -LiteralPath $tempPath -Force }; $downloadParams = @{ Uri = $url; OutFile = $tempPath; UseBasicParsing = $true; TimeoutSec = 15; ErrorAction = 'Stop' }; Invoke-WebRequest @downloadParams; if ((Test-Path -LiteralPath $tempPath) -and ((Get-Item -LiteralPath $tempPath).Length -gt 0)) { Move-Item -LiteralPath $tempPath -Destination $scriptPath -Force; $downloaded = $true; Write-Host (':: Downloaded to: ' + $scriptPath); break } } catch { Write-Warning ('Download failed: ' + $url + ' - ' + $_.Exception.Message) } }; if (-not $downloaded) { throw 'Failed to download set_ps1_default_powershell.ps1 from all mirrors.' }; & $scriptPath -Force } finally { foreach ($path in @($tempPath, $scriptPath)) { if ($path -and (Test-Path -LiteralPath $path)) { try { Remove-Item -LiteralPath $path -Force -ErrorAction Stop; Write-Host (':: Removed temporary file: ' + $path) } catch { Write-Warning ('Failed to remove temporary file: ' + $path + ' - ' + $_.Exception.Message) } } } } }"
    if "%errorlevel%" NEQ "0" (
        echo :: Failed to set .ps1 default open method, please check network or run set_ps1_default_powershell.ps1 manually
    )
    echo :: Configure completed
    echo :: Exit environment configuration script
    pause
