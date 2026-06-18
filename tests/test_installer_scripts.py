import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]

LAUNCH_INSTALLER_SCRIPTS = [
    "installer/stable_diffusion_webui_installer.ps1",
    "installer/comfyui_installer.ps1",
    "installer/fooocus_installer.ps1",
    "installer/invokeai_installer.ps1",
    "installer/qwen_tts_webui_installer.ps1",
    "installer/sd_trainer_installer.ps1",
]

INIT_INSTALLER_SCRIPTS = [
    "installer/sd_trainer_script_installer.ps1",
]

LONG_PATH_INSTALLER_SCRIPTS = LAUNCH_INSTALLER_SCRIPTS + INIT_INSTALLER_SCRIPTS

SNAPSHOT_REBUILD_INSTALLERS = {
    "installer/stable_diffusion_webui_installer.ps1": {
        "cli": "sd-webui",
        "type": "sd_webui",
        "path_arg": "--sd-webui-path",
        "git_kernel": True,
    },
    "installer/comfyui_installer.ps1": {
        "cli": "comfyui",
        "type": "comfyui",
        "path_arg": "--comfyui-path",
        "git_kernel": True,
    },
    "installer/fooocus_installer.ps1": {
        "cli": "fooocus",
        "type": "fooocus",
        "path_arg": "--fooocus-path",
        "git_kernel": True,
    },
    "installer/invokeai_installer.ps1": {
        "cli": "invokeai",
        "type": "invokeai",
        "path_arg": "--invokeai-path",
        "git_kernel": False,
    },
    "installer/qwen_tts_webui_installer.ps1": {
        "cli": "qwen-tts-webui",
        "type": "qwen_tts_webui",
        "path_arg": "--qwen-tts-webui-path",
        "git_kernel": True,
    },
    "installer/sd_trainer_installer.ps1": {
        "cli": "sd-trainer",
        "type": "sd_trainer",
        "path_arg": "--sd-trainer-path",
        "git_kernel": True,
    },
    "installer/sd_trainer_script_installer.ps1": {
        "cli": "sd-scripts",
        "type": "sd_scripts",
        "path_arg": "--sd-scripts-path",
        "git_kernel": True,
    },
}

MSVCPP_RUNTIME_CORE_DLLS = [
    "concrt140.dll",
    "msvcp140.dll",
    "msvcp140_1.dll",
    "msvcp140_2.dll",
    "msvcp140_atomic_wait.dll",
    "msvcp140_codecvt_ids.dll",
    "vcamp140.dll",
    "vccorlib140.dll",
    "vcomp140.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "vcruntime140_threads.dll",
]


def _read_installer(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8-sig")


def _extract_launch_template(text: str) -> str:
    start = text.index("# 启动脚本\nfunction Write-LaunchScript")
    end = text.index("# 更新脚本", start)
    return text[start:end]


def _extract_init_template(text: str) -> str:
    start = text.index("# 启动脚本\nfunction Write-InitScript")
    end = text.index("# 更新脚本", start)
    return text[start:end]


def _extract_modules_template(text: str) -> str:
    start = text.index("# 通用模块脚本\nfunction Write-ModulesScript")
    end = text.index("# 启动脚本", start)
    return text[start:end]


def _extract_launch_installer_template(text: str) -> str:
    start = text.index("# 获取安装脚本\nfunction Write-LaunchInstallerScript")
    end = text.index("# 重装 PyTorch 脚本", start)
    return text[start:end]


def _extract_restore_args_function(text: str) -> str:
    start = text.index("function Get-RestoreCoreArgs")
    end = text.index("function Update-SDWebUiAllInOne", start)
    return text[start:end]


def test_installer_templates_include_windows_long_path_helpers():
    helper_names = [
        "Test-WindowsLongPathsEnabled",
        "Get-CurrentPowerShellExecutable",
        "Quote-ProcessArgument",
        "Join-ProcessArguments",
        "Enable-WindowsLongPathsElevated",
        "Invoke-WindowsLongPathsStartupCheck",
    ]

    for script_path in LONG_PATH_INSTALLER_SCRIPTS:
        installer = _read_installer(script_path)
        for helper_name in helper_names:
            assert f"function {helper_name}" in installer, script_path

        assert "是否现在以管理员权限启用 Windows 长路径支持" in installer
        assert "依赖、扩展、模型缓存目录可能很深" in installer
        assert (
            "New-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\FileSystem' "
            "-Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force"
        ) in installer
        assert "configure_env.bat" in installer


def test_installer_scripts_parse_as_powershell():
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        pytest.skip("PowerShell is not available")

    quoted_paths = ", ".join(f"'{path}'" for path in LONG_PATH_INSTALLER_SCRIPTS)
    command = f"""
$failed = $false
foreach ($path in @({quoted_paths})) {{
    $tokens = $null
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path $path), [ref]$tokens, [ref]$errors) > $null
    if ($errors) {{
        $failed = $true
        Write-Output "== $path =="
        foreach ($errorRecord in $errors) {{
            Write-Output "$($errorRecord.Extent.StartLineNumber):$($errorRecord.Extent.StartColumnNumber) $($errorRecord.Message)"
        }}
    }}
}}
if ($failed) {{ exit 1 }}
"""
    result = subprocess.run(
        [pwsh, "-NoProfile", "-Command", command],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_launch_templates_import_and_call_windows_long_path_check():
    main_call_pattern = re.compile(
        r"function Main \{\s+"
        r"Get-HelpMessage\s+"
        r"Get-Version\s+"
        r"Set-CorePrefix\s+"
        r"Initialize-EnvPath\s+"
        r"if \(!\(`\$script:BuildMode\)\) \{\s+"
        r"Invoke-WindowsLongPathsStartupCheck\s+"
        r"\}\s+"
        r"Test-PythonAndGit",
        re.MULTILINE,
    )

    for script_path in LAUNCH_INSTALLER_SCRIPTS:
        launch_template = _extract_launch_template(_read_installer(script_path))
        import_lines = [
            line
            for line in launch_template.splitlines()
            if "Import-Module" in line and "modules.psm1" in line
        ]

        assert import_lines, script_path
        assert '`"Invoke-WindowsLongPathsStartupCheck`"' in import_lines[0]
        assert main_call_pattern.search(launch_template), script_path


def test_init_template_imports_and_calls_windows_long_path_check():
    main_call_pattern = re.compile(
        r"function Main \{\s+"
        r"Get-HelpMessage\s+"
        r"Get-Version\s+"
        r"Set-CorePrefix\s+"
        r"Initialize-EnvPath\s+"
        r"if \(!\(`\$script:BuildMode\)\) \{\s+"
        r"Invoke-WindowsLongPathsStartupCheck\s+"
        r"\}\s+"
        r"Test-PythonAndGit",
        re.MULTILINE,
    )

    for script_path in INIT_INSTALLER_SCRIPTS:
        init_template = _extract_init_template(_read_installer(script_path))
        import_lines = [
            line
            for line in init_template.splitlines()
            if "Import-Module" in line and "modules.psm1" in line
        ]

        assert import_lines, script_path
        assert '`"Invoke-WindowsLongPathsStartupCheck`"' in import_lines[0]
        assert main_call_pattern.search(init_template), script_path


def test_launch_runtime_helpers_are_moved_to_modules_template():
    helper_names = [
        "Get-WebUILaunchArgs",
        "Add-Shortcut",
        "Test-MSVCPPRedistributable",
        "Test-WebUIEnv",
        "Set-Hotpatcher",
    ]

    for script_path in LAUNCH_INSTALLER_SCRIPTS:
        installer = _read_installer(script_path)
        modules_template = _extract_modules_template(installer)
        launch_template = _extract_launch_template(installer)
        import_lines = [
            line
            for line in launch_template.splitlines()
            if "Import-Module" in line and "modules.psm1" in line
        ]

        assert import_lines, script_path
        for helper_name in helper_names:
            assert f"function {helper_name}" in modules_template, script_path
            assert f"function {helper_name}" not in launch_template, script_path
            assert f"    {helper_name}, ``" in modules_template, script_path
            assert f'`"{helper_name}`"' in import_lines[0], script_path


def test_init_runtime_helpers_are_moved_to_modules_template():
    helper_names = [
        "Test-MSVCPPRedistributable",
        "Set-PyTorch-CUDA-Memory-Alloc",
        "Clear-Hotpatcher-Env",
        "Test-HotpatcherPort",
        "Get-HotpatcherPort",
        "Set-Hotpatcher-Env",
    ]
    imported_helper_names = [
        "Test-MSVCPPRedistributable",
        "Set-PyTorch-CUDA-Memory-Alloc",
        "Set-Hotpatcher-Env",
    ]

    for script_path in INIT_INSTALLER_SCRIPTS:
        installer = _read_installer(script_path)
        modules_template = _extract_modules_template(installer)
        init_template = _extract_init_template(installer)
        import_lines = [
            line
            for line in init_template.splitlines()
            if "Import-Module" in line and "modules.psm1" in line
        ]

        assert import_lines, script_path
        for helper_name in helper_names:
            assert f"function {helper_name}" in modules_template, script_path
            assert f"function {helper_name}" not in init_template, script_path
            assert f"    {helper_name}, ``" in modules_template, script_path

        for helper_name in imported_helper_names:
            assert f'`"{helper_name}`"' in import_lines[0], script_path


def test_installer_hotpatcher_config_path_is_not_parameterized():
    forbidden_tokens = [
        "HotpatcherConfig",
        "--hotpatcher-config",
        "self-manager patcher export-config --output",
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE",
        "Resolve-HotpatcherConfigPath",
    ]

    for script_path in LAUNCH_INSTALLER_SCRIPTS + INIT_INSTALLER_SCRIPTS:
        installer = _read_installer(script_path)
        modules_template = _extract_modules_template(installer)

        for token in forbidden_tokens:
            assert token not in installer, script_path

        assert 'Join-NormalizedPath `$PSScriptRoot `"patcher_config.json`"' in modules_template, script_path
        assert '$hotpatcher_config_source = Join-NormalizedPath $PSScriptRoot "patcher_config.json"' in installer, script_path

    init_modules_template = _extract_modules_template(_read_installer(INIT_INSTALLER_SCRIPTS[0]))
    assert '`$Env:SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE = `"env`"' in init_modules_template
    assert "`$Env:SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON = Get-Content -Raw -Encoding UTF8 -Path `$config_path" in init_modules_template


def test_installer_snapshot_rebuild_mode_is_wired():
    helper_names = [
        "Stop-SnapshotRestore",
        "Normalize-SnapshotPlatform",
        "Normalize-SnapshotArchitecture",
        "Get-PythonMajorMinor",
        "Remove-ManagedPythonIfVersionMismatch",
        "Test-InstallerGitKernelSnapshot",
        "Resolve-SnapshotRebuildConfig",
        "Initialize-SnapshotRestoreTarget",
    ]

    for script_path, config in SNAPSHOT_REBUILD_INSTALLERS.items():
        installer = _read_installer(script_path)
        for helper_name in helper_names:
            assert f"function {helper_name}" in installer, script_path

        assert "[switch]$RestoreFromSnapshot" in installer, script_path
        assert "[string]$SnapshotPath" in installer, script_path
        assert f'$script:SnapshotExpectedWebUIType = "{config["type"]}"' in installer, script_path
        assert f'$script:SnapshotRestoreCliName = "{config["cli"]}"' in installer, script_path
        assert f'$script:SnapshotRestorePathArgument = "{config["path_arg"]}"' in installer, script_path
        git_kernel_value = "$true" if config["git_kernel"] else "$false"
        assert f"$script:SnapshotRequiresGitKernel = {git_kernel_value}" in installer, script_path
        assert "Normalize-SnapshotPlatform $snapshot.system.system" in installer, script_path
        assert "Normalize-SnapshotArchitecture $snapshot.system.architecture" in installer, script_path
        assert "ConvertFrom-Json -ErrorAction Stop" in installer, script_path
        assert "Remove-ManagedPythonIfVersionMismatch -ExpectedVersion $py_ver" in installer, script_path
        assert "Resolve-SnapshotRebuildConfig" in installer, script_path
        assert "Initialize-SnapshotRestoreTarget" in installer, script_path
        assert "$script:RestoreFromSnapshot -and $script:UseUpdateMode" in installer, script_path
        assert (
            "& python -m sd_webui_all_in_one $script:SnapshotRestoreCliName restore "
            "$snapshot_path $script:SnapshotRestorePathArgument $core_path $launch_params"
        ) in installer, script_path
        assert f'& python -m sd_webui_all_in_one {config["cli"]} install $launch_params' in installer, script_path


def test_installer_snapshot_restore_args_are_not_install_args():
    forbidden_tokens = [
        "Set-ModelMirror",
        "--no-pre-download-model",
        "--no-pre-download-extension",
        "--pytorch-mirror-type",
        "--custom-pytorch-package",
        "--custom-xformers-package",
        "--install-branch",
    ]

    for script_path in SNAPSHOT_REBUILD_INSTALLERS:
        restore_args = _extract_restore_args_function(_read_installer(script_path))
        assert "Set-uv $restore_params" in restore_args, script_path
        assert "Set-PyPIMirror $restore_params" in restore_args, script_path
        assert "Set-Proxy" in restore_args, script_path
        assert "Set-GithubMirror $restore_params" in restore_args, script_path
        assert '$restore_params.Add("--prune-packages")' in restore_args, script_path
        assert '$restore_params.Add("--prune-extensions")' in restore_args, script_path
        for token in forbidden_tokens:
            assert token not in restore_args, script_path


def test_launch_installer_templates_forward_snapshot_rebuild_args():
    for script_path in SNAPSHOT_REBUILD_INSTALLERS:
        launch_installer_template = _extract_launch_installer_template(_read_installer(script_path))
        assert "[switch]`$RestoreFromSnapshot" in launch_installer_template, script_path
        assert "[string]`$SnapshotPath" in launch_installer_template, script_path
        assert '`$arg.Add(`"-RestoreFromSnapshot`", `$true)' in launch_installer_template, script_path
        assert '`$arg.Add(`"-SnapshotPath`", `$script:SnapshotPath)' in launch_installer_template, script_path


def test_msvc_check_is_skipped_in_build_mode():
    msvc_guard_pattern = re.compile(
        r"if \(!\(`\$script:BuildMode\)\) \{\s+"
        r"Test-MSVCPPRedistributable\s+"
        r"\}",
        re.MULTILINE,
    )

    for script_path in LAUNCH_INSTALLER_SCRIPTS:
        launch_template = _extract_launch_template(_read_installer(script_path))
        assert msvc_guard_pattern.search(launch_template), script_path

    for script_path in INIT_INSTALLER_SCRIPTS:
        init_template = _extract_init_template(_read_installer(script_path))
        assert msvc_guard_pattern.search(init_template), script_path


def test_msvc_check_uses_core_runtime_dlls():
    for script_path in LAUNCH_INSTALLER_SCRIPTS + INIT_INSTALLER_SCRIPTS:
        modules_template = _extract_modules_template(_read_installer(script_path))
        for dll_name in MSVCPP_RUNTIME_CORE_DLLS:
            assert f'`"{dll_name}`"' in modules_template, script_path

        assert '`"Sysnative`"' in modules_template, script_path
        assert "Test-Path -LiteralPath `$vc_runtime_dll_path -PathType Leaf" in modules_template, script_path
        assert "`$missing_vc_runtime_dll_names.Count -eq 0" in modules_template, script_path


def test_installer_scripts_use_refactored_self_manager_paths():
    for script_path in LAUNCH_INSTALLER_SCRIPTS + INIT_INSTALLER_SCRIPTS:
        installer = _read_installer(script_path)
        assert "self-manager get proxy" in installer, script_path
        assert "self-manager get-proxy" not in installer, script_path

    init_installer = _read_installer(INIT_INSTALLER_SCRIPTS[0])
    assert "self-manager get cuda-malloc" in init_installer
    assert "self-manager get-cuda-malloc" not in init_installer


def test_installer_templates_include_snapshot_manager_script():
    expected_commands = {
        "installer/stable_diffusion_webui_installer.ps1": "sd-webui gui snapshot-manager",
        "installer/comfyui_installer.ps1": "comfyui gui snapshot-manager",
        "installer/fooocus_installer.ps1": "fooocus gui snapshot-manager",
        "installer/invokeai_installer.ps1": "invokeai gui snapshot-manager",
        "installer/qwen_tts_webui_installer.ps1": "qwen-tts-webui gui snapshot-manager",
        "installer/sd_trainer_installer.ps1": "sd-trainer gui snapshot-manager",
        "installer/sd_trainer_script_installer.ps1": "sd-scripts gui snapshot-manager",
    }

    for script_path, command in expected_commands.items():
        installer = _read_installer(script_path)
        snapshot_start = installer.index("function Write-SnapshotManagerScript")
        snapshot_end = installer.index("function Write-SettingsScript", snapshot_start)
        snapshot_template = installer[snapshot_start:snapshot_end]
        assert "function Write-SnapshotManagerScript" in installer, script_path
        assert "Write-SnapshotManagerScript" in installer[installer.index("function Write-ManagerScripts") :], script_path
        assert "snapshot_manager.ps1" in installer, script_path
        assert command in installer, script_path
        assert '`"Set-PyPIMirror`"' in snapshot_template, script_path
        assert '`"Set-uv`"' in snapshot_template, script_path
        assert "    Set-uv `$launch_params\n    Set-PyPIMirror `$launch_params\n    Set-GithubMirror `$launch_params" in snapshot_template, script_path
        assert "- snapshot_manager.ps1：创建和恢复当前环境快照。" in installer, script_path
