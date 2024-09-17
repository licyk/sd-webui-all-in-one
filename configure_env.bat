@echo off

>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
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

title Configuration environment
echo :: Set PowerShell execution policies
echo :: Executing command: "Set-ExecutionPolicy Unrestricted -Scope CurrentUser"
powershell "Set-ExecutionPolicy Unrestricted -Scope CurrentUser"
echo :: Enable long paths supported
echo :: Executing command: "New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force"
powershell "New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force"
echo :: Configuration completed
echo :: Exit environment configuration script 

pause