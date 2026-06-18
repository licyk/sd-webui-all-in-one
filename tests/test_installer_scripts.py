import re
from pathlib import Path


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
