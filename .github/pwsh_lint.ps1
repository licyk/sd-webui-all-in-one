param(
    [Parameter(Mandatory = $true)]
    [string]$Workspace,
    [string]$TempRoot = "",
    [switch]$KeepTemp
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Convert-ToDisplayPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return $Path.Replace([System.IO.Path]::DirectorySeparatorChar, "/")
}

function Get-RelativePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BasePath,
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return [System.IO.Path]::GetRelativePath($BasePath, $Path)
}

function Test-InGitDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $normalizedPath = Convert-ToDisplayPath -Path $RelativePath
    return $normalizedPath -eq ".git" -or $normalizedPath.StartsWith(".git/")
}

function Get-PowerShellScriptFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $extensions = @(".ps1", ".psm1", ".psd1")
    return @(
        Get-ChildItem -LiteralPath $Root -File -Recurse -Force |
            Where-Object { $_.Extension -in $extensions } |
            Sort-Object FullName
    )
}

function Initialize-TempRoot {
    param(
        [string]$RequestedPath
    )

    if ([string]::IsNullOrWhiteSpace($RequestedPath)) {
        $RequestedPath = Join-Path ([System.IO.Path]::GetTempPath()) ("sd-webui-all-in-one-pwsh-lint-" + [System.Guid]::NewGuid().ToString("N"))
    }

    $fullPath = [System.IO.Path]::GetFullPath($RequestedPath)
    if (Test-Path -LiteralPath $fullPath) {
        $children = @(Get-ChildItem -LiteralPath $fullPath -Force)
        if ($children.Count -gt 0) {
            throw "TempRoot exists and is not empty: $fullPath"
        }
    } else {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
    }

    return $fullPath
}

function Copy-RepositoryPowerShellScripts {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceRoot,
        [Parameter(Mandatory = $true)]
        [string]$DestinationRoot
    )

    $copiedCount = 0
    $scriptFiles = Get-PowerShellScriptFiles -Root $SourceRoot

    foreach ($scriptFile in $scriptFiles) {
        $relativePath = Get-RelativePath -BasePath $SourceRoot -Path $scriptFile.FullName
        if (Test-InGitDirectory -RelativePath $relativePath) {
            continue
        }

        $targetPath = Join-Path $DestinationRoot $relativePath
        $targetDirectory = Split-Path -Parent $targetPath
        if (-not [string]::IsNullOrWhiteSpace($targetDirectory)) {
            New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null
        }

        Copy-Item -LiteralPath $scriptFile.FullName -Destination $targetPath -Force
        $copiedCount += 1
    }

    Write-Host "Copied $copiedCount repository PowerShell script file(s) to $DestinationRoot"
}

function New-InstallerManagedScripts {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LintRoot
    )

    $installers = @(
        @{ File = "fooocus_installer.ps1"; Path = "fooocus" },
        @{ File = "comfyui_installer.ps1"; Path = "comfyui" },
        @{ File = "invokeai_installer.ps1"; Path = "invokeai" },
        @{ File = "sd_trainer_installer.ps1"; Path = "sd_trainer" },
        @{ File = "sd_trainer_script_installer.ps1"; Path = "sd_trainer_script" },
        @{ File = "stable_diffusion_webui_installer.ps1"; Path = "sd_webui" },
        @{ File = "qwen_tts_webui_installer.ps1"; Path = "qwen_tts_webui" }
    )

    $generationFailures = @()
    foreach ($item in $installers) {
        $installerPath = Join-Path (Join-Path $LintRoot "installer") $item.File
        $installPath = Join-Path $LintRoot $item.Path
        try {
            & pwsh -NoLogo -NoProfile -File $installerPath -InstallPath $installPath -UseUpdateMode
            if ($LASTEXITCODE -ne 0) {
                $generationFailures += [PSCustomObject]@{
                    File = $item.File
                    InstallPath = $installPath
                    Reason = "Exited with code $LASTEXITCODE"
                }
            }
        } catch {
            $generationFailures += [PSCustomObject]@{
                File = $item.File
                InstallPath = $installPath
                Reason = $_.Exception.Message
            }
        }
    }

    if ($generationFailures.Count -eq 0) {
        return
    }

    $summaryLines = @("Installer managed script generation failed for $($generationFailures.Count) installer(s):")
    foreach ($failure in $generationFailures) {
        $summaryLines += "  $($failure.File) -> $($failure.InstallPath): $($failure.Reason)"
    }

    $summary = $summaryLines -join [Environment]::NewLine
    Write-Host $summary
    throw $summary
}

function Test-Utf8Bom {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $stream = [System.IO.File]::OpenRead($Path)
    try {
        if ($stream.Length -lt 3) {
            return $false
        }

        $buffer = [byte[]]::new(3)
        $null = $stream.Read($buffer, 0, 3)
        return $buffer[0] -eq 0xEF -and $buffer[1] -eq 0xBB -and $buffer[2] -eq 0xBF
    } finally {
        $stream.Dispose()
    }
}

function Test-PowerShellScriptEncoding {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LintRoot
    )

    $scriptFiles = Get-PowerShellScriptFiles -Root $LintRoot
    $invalidFiles = @()
    foreach ($scriptFile in $scriptFiles) {
        if (-not (Test-Utf8Bom -Path $scriptFile.FullName)) {
            $invalidFiles += $scriptFile
        }
    }

    if ($invalidFiles.Count -eq 0) {
        Write-Host "UTF-8 BOM check passed for $($scriptFiles.Count) PowerShell script file(s)."
        return
    }

    Write-Host "UTF-8 BOM check failed for $($invalidFiles.Count) PowerShell script(s):"
    foreach ($scriptFile in $invalidFiles) {
        $relativePath = Convert-ToDisplayPath -Path (Get-RelativePath -BasePath $LintRoot -Path $scriptFile.FullName)
        Write-Host "  $relativePath"
    }
    throw "PowerShell script encoding check failed."
}

function Get-PythonExecutable {
    if (-not [string]::IsNullOrWhiteSpace($env:PYTHON)) {
        return $env:PYTHON
    }

    foreach ($commandName in @("python", "python3")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            return $command.Source
        }
    }

    throw "Unable to find python or python3 for installer parameter forwarding check."
}

function Test-InstallerParameterForwarding {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Workspace,
        [Parameter(Mandatory = $true)]
        [string]$LintRoot
    )

    $checkerPath = Join-Path $Workspace ".github/check_installer_param_config.py"
    $python = Get-PythonExecutable
    & $python $checkerPath --workspace $LintRoot
}

function Invoke-PowerShellScriptAnalyzer {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LintRoot
    )

    Import-Module PSScriptAnalyzer -ErrorAction Stop

    $scriptFiles = Get-PowerShellScriptFiles -Root $LintRoot
    $allIssues = @()
    foreach ($scriptFile in $scriptFiles) {
        $issues = @(Invoke-ScriptAnalyzer -Path $scriptFile.FullName -Severity @("Error", "ParseError"))
        $blockingIssues = @($issues | Where-Object { $_.Severity -in @("Error", "ParseError") })
        if ($blockingIssues.Count -eq 0) {
            continue
        }

        $relativePath = Convert-ToDisplayPath -Path (Get-RelativePath -BasePath $LintRoot -Path $scriptFile.FullName)
        Write-Host "$relativePath has $($blockingIssues.Count) blocking analyzer issue(s)."
        foreach ($issue in $blockingIssues) {
            $line = if ($issue.Line) { $issue.Line } else { 0 }
            $column = if ($issue.Column) { $issue.Column } else { 0 }
            Write-Host "  ${relativePath}:${line}:${column} [$($issue.Severity)] $($issue.RuleName): $($issue.Message)"
        }
        $allIssues += $blockingIssues
    }

    if ($allIssues.Count -gt 0) {
        throw "PSScriptAnalyzer found $($allIssues.Count) blocking issue(s)."
    }

    Write-Host "PSScriptAnalyzer check passed for $($scriptFiles.Count) PowerShell script file(s)."
}

$workspaceRoot = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $Workspace).Path)
$lintRoot = Initialize-TempRoot -RequestedPath $TempRoot
$failed = $false

try {
    Write-Host "PowerShell lint workspace: $workspaceRoot"
    Write-Host "PowerShell lint temp root: $lintRoot"

    Copy-RepositoryPowerShellScripts -SourceRoot $workspaceRoot -DestinationRoot $lintRoot
    New-InstallerManagedScripts -LintRoot $lintRoot
    Test-PowerShellScriptEncoding -LintRoot $lintRoot
    Test-InstallerParameterForwarding -Workspace $workspaceRoot -LintRoot $lintRoot
    Invoke-PowerShellScriptAnalyzer -LintRoot $lintRoot
} catch {
    $failed = $true
    throw
} finally {
    if ($KeepTemp -or $failed) {
        Write-Host "PowerShell lint temp root preserved: $lintRoot"
    } elseif (Test-Path -LiteralPath $lintRoot) {
        Remove-Item -LiteralPath $lintRoot -Recurse -Force
        Write-Host "PowerShell lint temp root removed: $lintRoot"
    }
}
