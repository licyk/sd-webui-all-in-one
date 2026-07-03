"""Headless desktop bridge for sd webui all in one."""

BRIDGE_PROTOCOL = 1
CAPABILITIES = (
    "bridge.info",
    "version.get_state",
)

__all__ = [
    "BRIDGE_PROTOCOL",
    "CAPABILITIES",
]
