"""Small project-owned boundaries shared by runtime transports."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RuntimeEventSink(Protocol):
    """A non-critical runtime event destination."""

    def emit_event(self, event_type: str, payload: dict[str, Any] | None = None) -> bool | None:
        """Accept an event without imposing transport I/O on the caller."""


@runtime_checkable
class RuntimeTransportLifecycle(Protocol):
    """Lifecycle operations implemented by selected runtime transports."""

    def start(self) -> Any:
        """Start transport-owned background work."""

    def close(self) -> None:
        """Release transport resources."""

    def status(self) -> dict[str, Any]:
        """Return a transport-owned status snapshot."""


@runtime_checkable
class RuntimeCommandHandler(Protocol):
    """Handle one broker command outside the HTTP protocol implementation."""

    def __call__(self, command_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Return a JSON-compatible command result."""


def emit_runtime_event(
    sink: RuntimeEventSink | Any,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> bool | None:
    """Emit through the narrow boundary while preserving legacy duck types."""

    emitter = getattr(sink, "emit_event", None)
    if emitter is not None:
        return emitter(event_type, payload)
    # RuntimeClient.event() predates the boundary and remains a public API.
    legacy_emitter = getattr(sink, "event", None)
    if legacy_emitter is not None:
        return legacy_emitter(event_type, payload)
    # Some established capture tests and embedders expose only the public
    # JsonlTcpTransport-shaped member on a light client facade.
    return sink.transport.event(event_type, payload)


__all__ = [
    "RuntimeCommandHandler",
    "RuntimeEventSink",
    "RuntimeTransportLifecycle",
    "emit_runtime_event",
]
