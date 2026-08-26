"""Implementation grouped from the former ``extensions.py`` module."""

from __future__ import annotations

from typing import TypedDict


class ComfyUiCustomNodeInfo(TypedDict):
    """ComfyUI 扩展信息."""

    name: str
    url: str
    save_dir: str


ComfyUiCustomNodeInfoList = list[ComfyUiCustomNodeInfo]

COMFYUI_CUSTOM_NODES_INFO_DICT: ComfyUiCustomNodeInfoList = [
    {
        "name": "ComfyUI-Manager",
        "url": "https://github.com/Comfy-Org/ComfyUI-Manager",
        "save_dir": "custom_nodes/ComfyUI-Manager",
    },
    {
        "name": "comfyui_controlnet_aux",
        "url": "https://github.com/licyk/comfyui_controlnet_aux",
        "save_dir": "custom_nodes/comfyui_controlnet_aux",
    },
    {
        "name": "ComfyUI-Advanced-ControlNet",
        "url": "https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet",
        "save_dir": "custom_nodes/ComfyUI-Advanced-ControlNet",
    },
    {
        "name": "ComfyUI_IPAdapter_plus",
        "url": "https://github.com/cubiq/ComfyUI_IPAdapter_plus",
        "save_dir": "custom_nodes/ComfyUI_IPAdapter_plus",
    },
    {
        "name": "ComfyUI-Marigold",
        "url": "https://github.com/kijai/ComfyUI-Marigold",
        "save_dir": "custom_nodes/ComfyUI-Marigold",
    },
    {
        "name": "ComfyUI-WD14-Tagger",
        "url": "https://github.com/pythongosssss/ComfyUI-WD14-Tagger",
        "save_dir": "custom_nodes/ComfyUI-WD14-Tagger",
    },
    {
        "name": "ComfyUI-Custom-Scripts",
        "url": "https://github.com/pythongosssss/ComfyUI-Custom-Scripts",
        "save_dir": "custom_nodes/ComfyUI-Custom-Scripts",
    },
    {
        "name": "ComfyUI_UltimateSDUpscale",
        "url": "https://github.com/ssitu/ComfyUI_UltimateSDUpscale",
        "save_dir": "custom_nodes/ComfyUI_UltimateSDUpscale",
    },
    {
        "name": "ComfyUI_Custom_Nodes_AlekPet",
        "url": "https://github.com/AlekPet/ComfyUI_Custom_Nodes_AlekPet",
        "save_dir": "custom_nodes/ComfyUI_Custom_Nodes_AlekPet",
    },
    {
        "name": "comfyui-browser",
        "url": "https://github.com/talesofai/comfyui-browser",
        "save_dir": "custom_nodes/comfyui-browser",
    },
    {
        "name": "ComfyUI-Inspire-Pack",
        "url": "https://github.com/ltdrdata/ComfyUI-Inspire-Pack",
        "save_dir": "custom_nodes/ComfyUI-Inspire-Pack",
    },
    {
        "name": "ComfyUI_Comfyroll_CustomNodes",
        "url": "https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes",
        "save_dir": "custom_nodes/ComfyUI_Comfyroll_CustomNodes",
    },
    {
        "name": "ComfyUI-Crystools",
        "url": "https://github.com/crystian/ComfyUI-Crystools",
        "save_dir": "custom_nodes/ComfyUI-Crystools",
    },
    {
        "name": "ComfyUI-TiledDiffusion",
        "url": "https://github.com/shiimizu/ComfyUI-TiledDiffusion",
        "save_dir": "custom_nodes/ComfyUI-TiledDiffusion",
    },
    {
        "name": "ComfyUI-Restart-Sampler",
        "url": "https://github.com/licyk/ComfyUI-Restart-Sampler",
        "save_dir": "custom_nodes/ComfyUI-Restart-Sampler",
    },
    {
        "name": "WeiLin-Comfyui-Tools",
        "url": "https://github.com/weilin9999/WeiLin-Comfyui-Tools",
        "save_dir": "custom_nodes/WeiLin-Comfyui-Tools",
    },
    {
        "name": "ComfyUI-HakuImg",
        "url": "https://github.com/licyk/ComfyUI-HakuImg",
        "save_dir": "custom_nodes/ComfyUI-HakuImg",
    },
    {
        "name": "ComfyUI-Easy-Use",
        "url": "https://github.com/yolain/ComfyUI-Easy-Use",
        "save_dir": "custom_nodes/ComfyUI-Easy-Use",
    },
    {
        "name": "rgthree-comfy",
        "url": "https://github.com/rgthree/rgthree-comfy",
        "save_dir": "custom_nodes/rgthree-comfy",
    },
]

COMFYUI_CUSTOM_NODE_LIST_PATH = "Comfy-Org/ComfyUI-Manager/refs/heads/main/custom-node-list.json"

COMFYUI_CUSTOM_NODE_INDEX_URL = f"https://raw.githubusercontent.com/{COMFYUI_CUSTOM_NODE_LIST_PATH}"
