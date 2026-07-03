"""Headless desktop bridge for sd webui all in one."""

BRIDGE_PROTOCOL = 1
CAPABILITIES = (
    "bridge.info",
    "version.get_state",
    "version.list_branches",
    "instance.prepare_launch",
)

__all__ = [
    "BRIDGE_PROTOCOL",
    "CAPABILITIES",
]
