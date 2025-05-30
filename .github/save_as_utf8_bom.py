import os
import argparse
from pathlib import Path
from typing import Union

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    normalized_filepath = lambda filepath: str(Path(filepath).absolute().as_posix())

    parser.add_argument('root_path', type=normalized_filepath, default=os.environ.get("root_path", os.getcwd()), help="根目录")

    return parser.parse_args()


def has_utf8_bom(file_path: Union[str, Path]) -> bool:
    with open(file_path, "rb") as file:
        bom = file.read(3)
        return bom == b"\xef\xbb\xbf"


def save_as_utf8_with_bom(input_file: Union[str, Path]) -> None:
    if has_utf8_bom(input_file):
        read_encode = "utf-8-sig"
    else:
        read_encode = "utf-8"

    with open(input_file, "r", encoding=read_encode) as file:
        content = file.read()

    content = content.replace("\r\n", "\n")

    with open(input_file, "w", encoding="utf-8-sig", newline="\n") as file:
        file.write(content)


if __name__ == "__main__":
    args = get_args()

    file_list = [
        os.path.abspath(os.path.join(args.root_path, file)) 
        for file in os.listdir(args.root_path) 
        if os.path.isfile(os.path.join(args.root_path, file)) and os.path.splitext(file)[1] == '.ps1'
    ]

    for file in file_list:
        print("transfer {} to UTF-8 BOM encode".format(file))
        save_as_utf8_with_bom(file)
