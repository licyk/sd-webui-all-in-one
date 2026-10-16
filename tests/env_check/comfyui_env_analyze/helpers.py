"""ComfyUI 环境分析测试辅助工具"""

from pathlib import Path


def make_comfyui(root: Path, core_requirements: str, nodes: dict[str, str]) -> Path:
    comfyui = root / "ComfyUI"
    (comfyui / "custom_nodes").mkdir(parents=True)
    (comfyui / "requirements.txt").write_text(core_requirements, encoding="utf-8")
    for name, requirements in nodes.items():
        node = comfyui / "custom_nodes" / name
        node.mkdir()
        (node / "requirements.txt").write_text(requirements, encoding="utf-8")
    return comfyui
