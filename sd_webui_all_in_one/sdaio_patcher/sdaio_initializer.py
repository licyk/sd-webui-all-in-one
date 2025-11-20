"""SD WebUI All In One 补丁模块初始化"""

from sdaio_patches.uv_patch import patch_uv_to_subprocess

patch_uv_to_subprocess()
