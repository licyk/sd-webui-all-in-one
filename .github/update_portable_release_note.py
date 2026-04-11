"""生成便携包发布说明的脚本

该脚本用于从便携包列表 JSON 数据生成 Markdown 格式的发布说明，
支持 ModelScope 和 HuggingFace 两个下载源的链接展示。
"""

import subprocess
from tempfile import TemporaryDirectory
from pathlib import Path
from typing import Any

import requests


def fetch_portable_list(
    url: str,
) -> dict[str, Any]:
    """获取便携包列表 JSON 数据

    Args:
        url (str):
            便携包列表 JSON 文件的 URL

    Returns:
        (dict[str, Any]):
            解析后的 JSON 数据字典
    """
    response = requests.get(
        url=url,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_download_link(
    data: dict[str, Any],
    source: str,
    version_type: str,
    project: str,
) -> str:
    """获取下载链接

    从便携包列表数据中提取指定项目在下载源和版本类型下的下载链接

    Args:
        data (dict[str, Any]):
            便携包列表数据
        source (str):
            下载源，可选值："modelscope" 或 "huggingface"
        version_type (str):
            版本类型，可选值："stable" 或 "nightly"
        project (str):
            项目名称

    Returns:
        str: Markdown 格式的下载链接，格式为 "[文件名](URL)"；如果不存在则返回"暂无"

    Example:
        >>> get_download_link(data, "modelscope", "stable", "ComfyUI")
        '[comfyui-licyk-v2.2.7z](https://modelscope.cn/...)'
    """
    try:
        project_data = data.get(source, {}).get(version_type, {}).get(project, [])
        if project_data and len(project_data) > 0:
            filename = project_data[0][0]
            url = project_data[0][1]
            return f"[{filename}]({url})"
        return "暂无"
    except (KeyError, IndexError, TypeError):
        return "暂无"


def generate_markdown_table(
    data: dict[str, Any],
    version_type: str,
    title: str,
) -> list[str]:
    """生成 Markdown 表格

    根据便携包列表数据生成包含 ModelScope 和 HuggingFace 下载链接的表格

    Args:
        data (dict[str, Any]):
            便携包列表数据
        version_type (str):
            版本类型 ("stable" 或 "nightly")
        title (str):
            表格标题（如 "Stable 版整合包"）

    Returns:
        list[str]:
            Markdown 表格行列表，每行代表表格的一行

    Example:
        >>> table_lines = generate_markdown_table(data, "stable", "Stable 版整合包")
        >>> for line in table_lines:
        ...     print(line)
    """
    lines: list[str] = []

    # 获取所有项目名称（从 modelscope 获取，然后排序）
    projects: list[str] = sorted(data.get("modelscope", {}).get(version_type, {}).keys())

    if not projects:
        return lines

    # 表格标题
    lines.append(f"|{title}|最新版本 (ModelScope)|最新版本 (HuggingFace)|")
    lines.append("|---|---|---|")

    # 遍历所有项目
    for project in projects:
        ms_link = get_download_link(data, "modelscope", version_type, project)
        hf_link = get_download_link(data, "huggingface", version_type, project)
        lines.append(f"|{project}|{ms_link}|{hf_link}|")

    return lines


def main() -> None:
    """主函数

    执行以下操作：
    1. 从远程 URL 下载便携包列表 JSON 数据
    2. 提取更新时间信息
    3. 生成 Stable 和 Nightly 版本的下载链接表格
    4. 将完整的 Markdown 内容写入到发布说明文件
    """
    portable_list_url: str = "https://github.com/licyk/resources/raw/gh-pages/portable_list.json"

    # 获取便携包列表数据
    print("正在下载便携包列表...")
    data: dict[str, Any] = fetch_portable_list(portable_list_url)

    # 获取更新时间
    update_time: str = data.get("update_time", "未知")
    print(f"更新时间：{update_time}")

    # 构建 Markdown 内容
    markdown_lines: list[str] = [
        "详细说明与使用请阅读：[AI 绘画 / 训练整合包 · licyk/sd-webui-all-in-one · Discussion #1](https://github.com/licyk/sd-webui-all-in-one/discussions/1)",
        "---",
        f"- 更新时间：`{update_time}`",
        "- 所有历史版本下载：[AI 绘画 / 训练整合包下载列表](https://licyk.github.io/t/#/sd_portable)",
        "- 建议使用 [7-Zip](https://7-zip.org/) / [Bandizip](https://www.bandisoft.com/bandizip/) 解压整合包",
        "- Nightly 整合包相比 Stable 整合包，版本较新，推荐使用",
        "---",
    ]

    # 生成 Stable 版本表格
    print("正在生成 Stable 版本表格...")
    stable_table: list[str] = generate_markdown_table(data, "stable", "Stable 版整合包")
    markdown_lines.extend(stable_table)
    markdown_lines.append("")

    # 生成 Nightly 版本表格
    print("正在生成 Nightly 版本表格...")
    nightly_table: list[str] = generate_markdown_table(data, "nightly", "Nightly 版整合包")
    markdown_lines.extend(nightly_table)

    with TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)
        release_note_file: Path = tmp_dir / "portable_release_note.md"

        # 写入文件
        with open(release_note_file, "w", encoding="utf-8") as f:
            f.write("\n".join(markdown_lines))

        subprocess.run(
            [
                "gh",
                "release",
                "edit",
                "portable",
                "--notes-file",
                release_note_file.as_posix(),
                "--repo",
                "licyk/sd-webui-all-in-one",
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        print("说明发布完成")


if __name__ == "__main__":
    main()
