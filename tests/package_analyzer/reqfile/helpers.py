"""依赖文件解析测试辅助工具"""

from sd_webui_all_in_one.package_analyzer.reqfile import (
    parse_requirements_text,
)


def parse_lines(text, tmp_path, **kwargs):
    """在空目录下解析依赖文件文本"""
    kwargs.setdefault("base_dir", tmp_path)
    kwargs.setdefault("environ", {})
    return parse_requirements_text(text, **kwargs)


def make_project(path, name="Local_Proj"):
    path.mkdir(parents=True, exist_ok=True)
    (path / "pyproject.toml").write_text(f'[project]\nname = "{name}"\nversion = "1.0"\n', encoding="utf-8")
    return path
