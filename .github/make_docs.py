import argparse
import shutil
from pathlib import Path


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    def _normalized_filepath(filepath) -> Path:
        return Path(filepath).absolute()

    parser.add_argument("docs_path", type=_normalized_filepath, help="文档保存路径")

    return parser.parse_args()


def write_content_to_file(
    content: str | list[str],
    save_path: Path,
    encoding: str = "utf-8",
    use_crlf: bool = False,
) -> None:
    if use_crlf:
        newline = "\r\n"
    else:
        newline = "\n"

    if isinstance(content, list):
        content = f"{newline}".join(content)

    print(f"[INFO] 写入文本到: {save_path}")
    with open(save_path, "w", encoding=encoding, newline=newline) as file:
        file.write(content)


def generate_launch_bat(psh_script: str) -> str:
    content = r"""
@echo off
@setlocal DisableDelayedExpansion
set "__WorkPath__=%~dp0"
if "%__WorkPath__:~-1%"=="\" set "__WorkPath__=%__WorkPath__:~0,-1%"
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%__WorkPath__%\{{PSH_SCRIPT}}" %*
exit %errorlevel%
""".strip()
    return content.replace(r"{{PSH_SCRIPT}}", psh_script)


def generate_launch_hanamizuki_bat(base_path: Path) -> None:
    content = r"""
@echo off
@setlocal DisableDelayedExpansion
set "__WorkPath__=%~dp0"
if "%__WorkPath__:~-1%"=="\" set "__WorkPath__=%__WorkPath__:~0,-1%"
cmd /c "%__WorkPath__%\hanamizuki.bat" %*
exit %errorlevel%
"""
    if not (base_path / "hanamizuki.bat").is_file():
        return
    print("[INFO] 生成绘世启动器启动脚本")
    write_content_to_file(
        content=content,
        save_path=base_path / "启动绘世启动器.bat",
        use_crlf=True,
    )


def generate_open_docs_bat(base_path: Path) -> None:
    content = r"""
@echo off
@setlocal DisableDelayedExpansion
set "__WorkPath__=%~dp0"
if "%__WorkPath__:~-1%"=="\" set "__WorkPath__=%__WorkPath__:~0,-1%"
powershell -NoLogo -NoProfile -Command "Invoke-Item (Join-Path '%__WorkPath__%' 'help.txt')" %*
exit %errorlevel%
"""
    print("[INFO] 生成文档查询脚本")
    write_content_to_file(
        content=content,
        save_path=base_path / "打开文档.bat",
        use_crlf=True,
    )


def make_launch_scripts(base_path: Path, scripts: list[tuple[str, str]]) -> None:
    for psh, name in scripts:
        if not (base_path / psh).is_file():
            continue
        code = generate_launch_bat(psh)
        print(f"[INFO] 生成快捷启动脚本: {name} -> {psh}")
        write_content_to_file(
            content=code,
            save_path=base_path / name,
            use_crlf=True,
        )


def install_hanamizuki_bg(
    docs_path: Path,
) -> None:
    bg_path = Path(__file__).parent / "head_image.jpg"
    if not bg_path.exists():
        print(f"[WARNING] 未在 {bg_path} 找到绘世启动器头图")
        return

    save_path = docs_path / "core" / ".launcher" / "head_image.jpg"
    hanamizuki_exe = docs_path / "core" / "hanamizuki.exe"
    if not hanamizuki_exe.exists():
        return

    if not (docs_path / "core").exists():
        print("[WARNING] 未找到内核路径")

    print(f"[INFO] 复制绘世启动器头图到 {save_path}")
    save_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(bg_path, save_path)


def main() -> None:
    args = get_args()
    docs_path: Path = args.docs_path
    help_content = """
首次使用该需要双击运行 configure_env.bat 配置环境
运行后即可正常运行 PowerShell 脚本 (ps1 后缀的文件), PowerShell 脚本需要右键后选择 "使用 PowerShell 运行" 才可以运行

使用该整合包启动前请打开 help.txt 文件阅读说明
更多说明请阅读: https://licyk.github.io/sd-webui-all-in-one/portable/portable
整合包支持使用启动器运行，启动器的使用方法请阅读：https://licyk.github.io/sd-webui-all-in-one/tools/launcher-gui

！！！不会启动该整合包的请重新阅读 help.txt 文件中的说明！！！

！！！本整合包免费提供，如您通过其他渠道付费获得本整合包，请立即退款并投诉相应商家！！！
""".strip()

    sign_content = """
https://space.bilibili.com/46497516
""".strip()

    user_agreement_content = """
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
    实施任何违背“七条底线”的行为。
    含有法律、行政法规禁止的其他内容的。
因您的数据的产生、收集、处理、使用等任何相关事项存在违反法律法规等情况而造成的全部结果及责任均由您自行承担。
""".strip()

    write_content_to_file(
        content=help_content,
        save_path=docs_path / "说明.txt",
    )
    write_content_to_file(
        content=sign_content,
        save_path=docs_path / "bilibili@licyk_.txt",
    )
    write_content_to_file(
        content=user_agreement_content,
        save_path=docs_path / "用户协议.txt",
    )
    make_launch_scripts(
        base_path=docs_path,
        scripts=[
            ("launch.ps1", "启动.bat"),
            ("update.ps1", "更新内核.bat"),
            ("update_extension.ps1", "更新扩展.bat"),
            ("update_node.ps1", "更新扩展.bat"),
            ("download_models.ps1", "下载模型.bat"),
            ("switch_branch.ps1", "切换分支.bat"),
            ("reinstall_pytorch.ps1", "重装 PyTorch.bat"),
            ("version_manager.ps1", "版本管理.bat"),
            ("settings.ps1", "打开 Installer 设置.bat"),
            ("terminal.ps1", "打开终端.bat"),
            ("train.ps1", "启动训练.bat"),
            ("launch_comfyui_installer.ps1", "重新运行安装 ComfyUI.bat"),
            ("launch_fooocus_installer.ps1", "重新运行安装 Fooocus.bat"),
            ("launch_invokeai_installer.ps1", "重新运行安装 InvokeAI.bat"),
            ("launch_qwen_tts_webui_installer.ps1", "重新运行安装 Qwen TTS WebUI.bat"),
            ("launch_sd_trainer_installer.ps1", "重新运行安装 SD Trainer.bat"),
            ("launch_sd_trainer_script_installer.ps1", "重新运行安装 SD Trainer Script.bat"),
            ("launch_stable_diffusion_webui_installer.ps1", "重新运行安装 SD WebUI.bat"),
        ],
    )
    generate_launch_hanamizuki_bat(docs_path)
    generate_open_docs_bat(docs_path)
    install_hanamizuki_bg(docs_path)


if __name__ == "__main__":
    main()
