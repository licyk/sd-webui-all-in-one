"""SD Trainer Next 浏览器打开顺序热补丁。"""

from .config import (
    apply_from_config,
)
from .patches import (
    TARGET_FUNCTION,
    TARGET_MODULE,
    is_sd_trainer_browser_order_patch_registered,
    is_sd_trainer_next_application,
    patch_sd_trainer_browser_order,
)
from .recording import (
    BrowserRequest,
)
from .replay import (
    DEFAULT_MAIN_WAIT_TIMEOUT,
    DEFAULT_MONITOR_DELAY,
    order_browser_requests,
    replay_browser_requests,
)

__all__ = [
    "DEFAULT_MAIN_WAIT_TIMEOUT",
    "DEFAULT_MONITOR_DELAY",
    "TARGET_FUNCTION",
    "TARGET_MODULE",
    "BrowserRequest",
    "apply_from_config",
    "is_sd_trainer_browser_order_patch_registered",
    "is_sd_trainer_next_application",
    "order_browser_requests",
    "patch_sd_trainer_browser_order",
    "replay_browser_requests",
]
