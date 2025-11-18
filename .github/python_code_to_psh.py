import os
import argparse
from pathlib import Path


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    def _normalized_filepath(filepath):
        return Path(filepath).absolute().as_posix()

    parser.add_argument(
        "input_path",
        type=_normalized_filepath,
        default=None,
        help="原始 Python 文件路径",
    )
    parser.add_argument("output_path", type=_normalized_filepath, default=None, help="转换后的 Python 文件路径")
    parser.add_argument("--depth", type=int, default=1, help="Python 代码嵌套在 PpowerShell 脚本中的深度")

    return parser.parse_args()


def read_content_from_file(path: str | Path) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"读取文件出现错误: {e}")
        return None


def write_content_to_file(
    content: list[str],
    path: str | Path,
) -> None:
    """将内容列表写入到文件中

    Args:
        content (list[str]): 内容列表
        path (str | Path): 保存内容的路径
    """
    if len(content) == 0:
        return

    dir_path = os.path.dirname(path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

    try:
        print(
            f"写入文件到 {path}",
        )
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(content, list):
                for item in content:
                    f.write(item + "\n")
            else:
                f.write(content)
    except Exception as e:
        print(f"写入文件到 {path} 时出现了错误: {e}")


def make_python_code_to_psh(
    input_path: str | Path,
    output_path: str | Path,
    depth: int | None = 1,
) -> None:
    print(f"{input_path} -> {output_path}, 嵌套深度: {depth}")
    content = read_content_from_file(input_path)
    for _ in range(depth):
        content = content.replace("`", "``").replace('"', '`"')

    write_content_to_file(content, output_path)


def main() -> None:
    args = get_args()
    make_python_code_to_psh(args.input_path, args.output_path, args.depth)


if __name__ == "__main__":
    main()
