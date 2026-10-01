"""ComfyUI 环境检查工具"""

from sd_webui_all_in_one.env_check.shared import logger
from sd_webui_all_in_one.env_check.comfyui_env_analyze.models import (
    ComponentType,
    ComponentEnvironmentDetails,
    ComfyUIEnvironmentComponent,
    ComfyUIConflictItem,
    ComfyUIConflictGroup,
    ComfyUIDisableReason,
    ComfyUIConflictEdge,
    ComfyUIDisableCandidate,
    ComfyUIConflictResolution,
    ComfyUIConflictAction,
    ComfyUIConflictAnalysisResult,
)
from sd_webui_all_in_one.env_check.comfyui_env_analyze.environment import (
    create_comfyui_environment_dict,
    update_comfyui_environment_dict,
    update_comfyui_component_requires_list,
    update_comfyui_component_missing_requires_list,
    update_comfyui_component_conflict_requires_list,
    get_comfyui_component_requires_list,
    statistical_need_install_require_component,
    collect_conflict_components,
    fitter_has_version_package,
)
from sd_webui_all_in_one.env_check.comfyui_env_analyze.reporting import (
    format_conflict_info,
    format_conflict_resolution_info,
    display_comfyui_environment_dict,
    display_check_result,
)
from sd_webui_all_in_one.env_check.comfyui_env_analyze.conflict_detection import (
    detect_conflict_package,
    detect_conflict_package_from_list,
)
from sd_webui_all_in_one.env_check.comfyui_env_analyze.resolution import (
    build_component_conflict_graph,
    resolve_conflict_components,
)
from sd_webui_all_in_one.env_check.comfyui_env_analyze.checks import (
    process_comfyui_env_analysis,
    check_comfyui_component_dependencies,
    comfyui_conflict_analyzer,
    check_comfyui_manager_dependence,
)

__all__ = [
    "logger",
    "ComponentType",
    "ComponentEnvironmentDetails",
    "ComfyUIEnvironmentComponent",
    "ComfyUIConflictItem",
    "ComfyUIConflictGroup",
    "ComfyUIDisableReason",
    "ComfyUIConflictEdge",
    "ComfyUIDisableCandidate",
    "ComfyUIConflictResolution",
    "ComfyUIConflictAction",
    "ComfyUIConflictAnalysisResult",
    "create_comfyui_environment_dict",
    "update_comfyui_environment_dict",
    "update_comfyui_component_requires_list",
    "update_comfyui_component_missing_requires_list",
    "update_comfyui_component_conflict_requires_list",
    "get_comfyui_component_requires_list",
    "statistical_need_install_require_component",
    "collect_conflict_components",
    "fitter_has_version_package",
    "format_conflict_info",
    "format_conflict_resolution_info",
    "display_comfyui_environment_dict",
    "display_check_result",
    "detect_conflict_package",
    "detect_conflict_package_from_list",
    "build_component_conflict_graph",
    "resolve_conflict_components",
    "process_comfyui_env_analysis",
    "check_comfyui_component_dependencies",
    "comfyui_conflict_analyzer",
    "check_comfyui_manager_dependence",
]
