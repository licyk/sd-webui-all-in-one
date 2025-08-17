import os
import argparse
from pathlib import Path
from typing import Union



def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    normalized_filepath = lambda filepath: str(Path(filepath).absolute().as_posix())

    parser.add_argument('docs_path', type=normalized_filepath, default=os.environ.get("docs_path", os.getcwd()), help="文档保存路径")

    return parser.parse_args()


def write_content_to_file(content: Union[list, str], path: Union[str, Path]) -> None:
    if len(content) == 0:
        return
    
    if isinstance(content, str):
        content = content.strip().split("\n")

    with open(path, 'w', encoding = 'utf8') as f:
        for item in content:
            f.write(item + '\n')



if __name__ == "__main__":
    args = get_args()
    help_content = """
首次使用该需要双击运行 configure_env.bat 配置环境
运行后即可正常运行 PowerShell 脚本 (ps1 后缀的文件), PowerShell 脚本需要右键后选择 "使用 PowerShell 运行" 才可以运行

使用该整合包启动前请打开 help.txt 文件阅读说明
更多说明请阅读: https://github.com/licyk/sd-webui-all-in-one/discussions/1

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

    write_content_to_file(help_content, os.path.join(args.docs_path, "说明.txt"))
    write_content_to_file(sign_content, os.path.join(args.docs_path, "bilibili@licyk_.txt"))
    write_content_to_file(user_agreement_content, os.path.join(args.docs_path, "用户协议.txt"))
