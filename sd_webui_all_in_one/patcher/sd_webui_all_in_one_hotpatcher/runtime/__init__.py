"""运行时宿主通信工具"""

from .browser import BrowserMode, ManagedBrowser, patch_webbrowser
from .client import RuntimeClient
from .desktop_broker import (
    DesktopBrokerClient,
    DesktopBrokerCommandError,
    DesktopBrokerConfigurationError,
    DesktopBrokerProtocolError,
    DesktopBrokerSettings,
    DesktopTransportStatus,
)
from .interfaces import RuntimeCommandHandler, RuntimeEventSink, RuntimeTransportLifecycle
from .config import load_config
from .errors import (
    CaughtExceptionTracer,
    ErrorCapture,
    configure_error_capture_from_env,
    install_error_capture,
    install_exception_reporter,
    is_error_capture_installed,
    uninstall_error_capture,
    uninstall_exception_reporter,
)
from .fileops import FileOperation, UserCanceledException
from .logs import (
    LogCapture,
    RuntimeLogHandler,
    configure_log_capture_from_env,
    install_log_capture,
    uninstall_log_capture,
)
from .progress import Progress, ProgressManager
from .protocol import RuntimeProtocolError, RuntimeRequestError, RuntimeTransportError
from .transport_mode import TRANSPORT_MODE_ENV, TransportMode, resolve_transport_mode

__all__ = [
    "FileOperation",
    "CaughtExceptionTracer",
    "ErrorCapture",
    "LogCapture",
    "ManagedBrowser",
    "BrowserMode",
    "Progress",
    "ProgressManager",
    "RuntimeLogHandler",
    "RuntimeClient",
    "DesktopBrokerClient",
    "DesktopBrokerCommandError",
    "DesktopBrokerConfigurationError",
    "DesktopBrokerProtocolError",
    "DesktopBrokerSettings",
    "DesktopTransportStatus",
    "RuntimeCommandHandler",
    "RuntimeEventSink",
    "RuntimeTransportLifecycle",
    "RuntimeProtocolError",
    "RuntimeRequestError",
    "RuntimeTransportError",
    "TRANSPORT_MODE_ENV",
    "TransportMode",
    "UserCanceledException",
    "configure_error_capture_from_env",
    "configure_log_capture_from_env",
    "install_error_capture",
    "install_exception_reporter",
    "is_error_capture_installed",
    "install_log_capture",
    "load_config",
    "patch_webbrowser",
    "resolve_transport_mode",
    "uninstall_error_capture",
    "uninstall_exception_reporter",
    "uninstall_log_capture",
]
