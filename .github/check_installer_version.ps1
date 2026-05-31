param (
    [string]$Workspace = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"

function Get-ValueFromFile {
    param (
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Pattern,
        [Parameter(Mandatory = $true)][string]$Description
    )

    try {
        $match = Select-String -Path $Path -Pattern $Pattern | Select-Object -First 1
        if (!$match) {
            throw "Pattern not found: $Pattern"
        }
        return $match.Matches[0].Groups[1].Value
    }
    catch {
        Write-Host "Failed to read ${Description} from ${Path}: $_"
        return $null
    }
}

function Get-Installer-Version-Format {
    param ([Parameter(Mandatory = $true)][int]$Version)

    $ver = ([string]$Version).PadLeft(3, "0").ToCharArray()
    $major = -join $ver[0..($ver.Length - 3)]
    $minor = $ver[-2]
    $micro = $ver[-1]
    return "v${major}.${minor}.${micro}"
}

$installerPath = Join-Path $Workspace "installer"
$coreVersionPath = Join-Path $Workspace "sd_webui_all_in_one/version.py"
$coreVersion = Get-ValueFromFile `
    -Path $coreVersionPath `
    -Pattern '^\s*VERSION\s*=\s*"([^"]+)"' `
    -Description "Python package version"

$installerList = @(
    @{ Path = Join-Path $installerPath "comfyui_installer.ps1"; Flag = "COMFYUI_INSTALLER_VERSION" },
    @{ Path = Join-Path $installerPath "fooocus_installer.ps1"; Flag = "FOOOCUS_INSTALLER_VERSION" },
    @{ Path = Join-Path $installerPath "invokeai_installer.ps1"; Flag = "INVOKEAI_INSTALLER_VERSION" },
    @{ Path = Join-Path $installerPath "sd_trainer_installer.ps1"; Flag = "SD_TRAINER_INSTALLER_VERSION" },
    @{ Path = Join-Path $installerPath "sd_trainer_script_installer.ps1"; Flag = "SD_TRAINER_SCRIPT_INSTALLER_VERSION" },
    @{ Path = Join-Path $installerPath "stable_diffusion_webui_installer.ps1"; Flag = "SD_WEBUI_INSTALLER_VERSION" },
    @{ Path = Join-Path $installerPath "qwen_tts_webui_installer.ps1"; Flag = "QWEN_TTS_WEBUI_INSTALLER_VERSION" }
)

$hasError = $false
$data = @()

if (!$coreVersion) {
    $hasError = $true
}

foreach ($installer in $installerList) {
    $versionValue = Get-ValueFromFile `
        -Path $installer.Path `
        -Pattern "^\s*\`$script:$($installer.Flag)\s*=\s*(\d+)" `
        -Description $installer.Flag
    $coreMinimumVersion = Get-ValueFromFile `
        -Path $installer.Path `
        -Pattern '^\s*\$script:CORE_MINIMUM_VER\s*=\s*"([^"]+)"' `
        -Description "CORE_MINIMUM_VER"

    $version = $null
    $versionFormat = $null
    if ($versionValue) {
        $version = [int]$versionValue
        $versionFormat = Get-Installer-Version-Format $version
    } else {
        $hasError = $true
    }

    $isCoreVersionMatched = $coreVersion -and $coreMinimumVersion -and ($coreMinimumVersion -eq $coreVersion)
    if (!$coreMinimumVersion -or !$isCoreVersionMatched) {
        $hasError = $true
    }

    $data += @(
        [PSCustomObject]@{
            Installer = [System.IO.Path]::GetFileName($installer.Path)
            Ver = $versionFormat
            Code = $version
            Core = $coreMinimumVersion
            Package = $coreVersion
            Match = $isCoreVersionMatched
        }
    )
}

$data | Format-Table -AutoSize -Property Installer, Ver, Code, Core, Package, Match

if ($hasError) {
    Write-Error "Installer version check failed" -ErrorAction Stop
}

Write-Host "Installer version check passed"
