import os
from pathlib import Path

def has_utf8_bom(file_path: Path) -> bool:
    """检查文件是否以 UTF-8 BOM 开头。"""
    try:
        with open(file_path, "rb") as f:
            return f.read(3) == b"\xef\xbb\xbf"
    except Exception as e:
        print(f"读取文件时出错 {file_path}: {e}")
        return False

def main():
    # 从项目根目录开始搜索（.github/ 文件夹的上一级）
    root_dir = Path(__file__).parent.parent
    ps1_files = sorted(list(root_dir.rglob("*.ps1")))
    
    if not ps1_files:
        print("未找到任何 .ps1 文件。")
        return

    invalid_files = []
    print(f"正在检查 {len(ps1_files)} 个 PowerShell 脚本的 UTF-8 BOM 编码：\n")
    
    for ps1_file in ps1_files:
        # 获取相对于项目根目录的路径，使输出更整洁
        relative_path = ps1_file.relative_to(root_dir)
        if has_utf8_bom(ps1_file):
            print(f"[通过] {relative_path}")
        else:
            invalid_files.append(relative_path)
            print(f"[失败] {relative_path} (缺失 UTF-8 BOM)")

    print("\n" + "-" * 40)
    if not invalid_files:
        print("成功：所有 PowerShell 脚本均已使用 UTF-8 BOM 编码。")
    else:
        print(f"失败：发现 {len(invalid_files)} 个文件的编码不正确。")
        exit(1) # 退出并返回错误代码以触发 CI 失败

if __name__ == "__main__":
    main()
