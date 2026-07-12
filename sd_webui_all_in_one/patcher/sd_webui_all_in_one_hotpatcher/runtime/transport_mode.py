"""Centralized Hotpatch runtime transport selection."""

from __future__ import annotations

import os
from enum import Enum
from typing import Mapping

TRANSPORT_MODE_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TRANSPORT_MODE"


class TransportMode(str, Enum):
    """Supported runtime transport implementations."""

    LEGACY = "legacy"
    DESKTOP_BROKER = "desktop_broker"


def resolve_transport_mode(environ: Mapping[str, str] | None = None) -> TransportMode:
    """Resolve the configured transport without accepting aliases.

    Missing and exactly empty values retain the legacy TCP JSONL default.
    Values are case-sensitive and are not whitespace-normalized so deployment
    mistakes cannot silently select a different transport.
    """

    source = os.environ if environ is None else environ
    value = source.get(TRANSPORT_MODE_ENV)
    if value is None or value == "":
        return TransportMode.LEGACY
    try:
        return TransportMode(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {TRANSPORT_MODE_ENV} value {value!r}; supported values: legacy, desktop_broker") from exc


__all__ = ["TRANSPORT_MODE_ENV", "TransportMode", "resolve_transport_mode"]
