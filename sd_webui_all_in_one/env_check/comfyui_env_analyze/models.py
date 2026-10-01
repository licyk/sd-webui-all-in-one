"""ComfyUI 环境检查数据类型"""

from pathlib import Path
from typing import TypedDict, Literal, TypeAlias


ComponentType: TypeAlias = Literal["core", "extension"]
"""组件类型
- core: 内核
- extension: 扩展
"""


class ComponentEnvironmentDetails(TypedDict):
    """ComfyUI 组件的环境信息结构

    Attributes:
        requirement_path (Path | None):
            依赖文件路径
        component_type (ComponentType | None):
            组件类型
        is_disabled (bool):
            组件是否禁用
        requires (list[str]):
            需要的依赖列表
        has_missing_requires (bool):
            是否存在缺失依赖
        missing_requires (list[str]):
            具体缺失的依赖项
        has_conflict_requires (bool):
            是否存在冲突依赖
        conflict_requires (list[str]):
            具体冲突的依赖项
    """

    requirement_path: Path | None
    """依赖文件路径"""

    component_type: ComponentType | None
    """组件类型"""

    is_disabled: bool
    """组件是否禁用"""

    requires: list[str]
    """需要的依赖列表"""

    has_missing_requires: bool
    """是否存在缺失依赖"""

    missing_requires: list[str]
    """具体缺失的依赖项"""

    has_conflict_requires: bool
    """是否存在冲突依赖"""

    conflict_requires: list[str]
    """具体冲突的依赖项"""


ComfyUIEnvironmentComponent = dict[str, ComponentEnvironmentDetails]
"""ComfyUI 环境组件表字典"""


class ComfyUIConflictItem(TypedDict):
    """单个冲突组件与其版本要求。"""

    component: str
    component_type: ComponentType | None
    requirement: str


class ComfyUIConflictGroup(TypedDict):
    """单个软件包的冲突组。"""

    package: str
    components: list[ComfyUIConflictItem]


ComfyUIDisableReason: TypeAlias = Literal["self_conflict", "conflicts_with_protected", "optimal_selection"]
"""组件被建议禁用的原因
- self_conflict: 组件自身的依赖声明互相冲突
- conflicts_with_protected: 与受保护组件 (如 ComfyUI 内核) 冲突
- optimal_selection: 为保留最多组件而在冲突组件中选择禁用
"""


class ComfyUIConflictEdge(TypedDict):
    """两个组件之间 (或组件自身) 的一条依赖冲突关系。"""

    package: str
    """冲突的软件包名称"""

    component: str
    """组件名称"""

    requirement: str
    """组件的版本声明"""

    other_component: str
    """与之冲突的组件名称"""

    other_requirement: str
    """与之冲突的组件的版本声明"""


class ComfyUIDisableCandidate(TypedDict):
    """建议禁用的组件及原因。"""

    component: str
    """组件名称"""

    reason: ComfyUIDisableReason
    """建议禁用的原因"""

    conflicts_with: list[str]
    """与之冲突的保留组件"""

    packages: list[str]
    """产生冲突的软件包"""


class ComfyUIConflictResolution(TypedDict):
    """冲突组件禁用方案。

    Attributes:
        keep_components (list[str]):
            保留的冲突相关组件。
        disable_components (list[str]):
            可禁用的组件列表, 禁用后剩余组件之间不再存在可解决的冲突。
        disable_details (list[ComfyUIDisableCandidate]):
            每个可禁用组件的禁用原因。
        unresolvable_conflicts (list[ComfyUIConflictEdge]):
            无法通过禁用扩展解决的冲突 (如 ComfyUI 内核依赖自身冲突)。
        is_optimal (bool):
            方案是否已被证明为保留组件最多的方案。
        is_conflict_free (bool):
            执行方案后是否不再存在冲突。
    """

    keep_components: list[str]
    """保留的冲突相关组件。"""

    disable_components: list[str]
    """可禁用的组件列表。"""

    disable_details: list[ComfyUIDisableCandidate]
    """每个可禁用组件的禁用原因。"""

    unresolvable_conflicts: list[ComfyUIConflictEdge]
    """无法通过禁用扩展解决的冲突。"""

    is_optimal: bool
    """方案是否已被证明为保留组件最多的方案。"""

    is_conflict_free: bool
    """执行方案后是否不再存在冲突。"""


ComfyUIConflictAction: TypeAlias = Literal["install", "disable", "skip"]
"""检测到冲突依赖时的处理方式
- install: 按顺序安装冲突组件依赖
- disable: 禁用冲突组件并继续安装依赖
- skip: 忽略冲突
"""


class ComfyUIConflictAnalysisResult(TypedDict):
    """ComfyUI 组件依赖检查结果。

    Attributes:
        components (ComfyUIEnvironmentComponent):
            ComfyUI 组件环境信息。
        requirement_paths (list[Path]):
            需要安装或修复的依赖文件路径。
        conflicts (list[ComfyUIConflictGroup]):
            结构化的冲突依赖信息。
        conflict_info (str):
            冲突依赖文本说明。
        has_missing_requires (bool):
            是否存在缺失依赖。
        has_conflict_requires (bool):
            是否存在冲突依赖。
        conflict_resolution (ComfyUIConflictResolution):
            冲突组件禁用方案, 记录可禁用的组件列表。
    """

    components: ComfyUIEnvironmentComponent
    """ComfyUI 组件环境信息。"""

    requirement_paths: list[Path]
    """需要安装或修复的依赖文件路径。"""

    conflicts: list[ComfyUIConflictGroup]
    """结构化的冲突依赖信息。"""

    conflict_info: str
    """冲突依赖文本说明。"""

    has_missing_requires: bool
    """是否存在缺失依赖。"""

    has_conflict_requires: bool
    """是否存在冲突依赖。"""

    conflict_resolution: ComfyUIConflictResolution
    """冲突组件禁用方案。"""
