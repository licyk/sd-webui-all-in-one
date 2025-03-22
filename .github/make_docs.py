import os
import argparse
from pathlib import Path
from typing import Union



def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    normalized_filepath = lambda filepath: str(Path(filepath).absolute().as_posix())

    parser.add_argument('docs-path', type=normalized_filepath, default=os.environ.get("docs_path", os.getcwd()), help="文档保存路径")

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
首次使用需要双击运行 configure_env.bat 配置环境
运行后即可正常运行 PowerShell 脚本, PowerShell 脚本需要右键后选择 "使用 PowerShell 运行" 才可以运行
简单使用说明可打开 help.txt 进行阅读
更多说明请阅读: https://github.com/licyk/sd-webui-all-in-one/discussions/1
    """

    sign_content = """
https://space.bilibili.com/46497516
"""

    write_content_to_file(help_content, os.path.join(args.docs_path, "说明.txt"))
    write_content_to_file(sign_content, os.path.join(args.docs_path, "bilibili@licyk_.txt"))
