import pytest
from sd_webui_all_in_one_hotpatcher.runtime.transport_mode import (
    TRANSPORT_MODE_ENV,
    TransportMode,
    resolve_transport_mode,
)


def test_transport_mode_defaults_to_legacy_when_missing_or_empty():
    assert resolve_transport_mode({}) is TransportMode.LEGACY
    assert resolve_transport_mode({TRANSPORT_MODE_ENV: ""}) is TransportMode.LEGACY


def test_transport_mode_accepts_only_explicit_documented_values():
    assert resolve_transport_mode({TRANSPORT_MODE_ENV: "legacy"}) is TransportMode.LEGACY
    assert resolve_transport_mode({TRANSPORT_MODE_ENV: "desktop_broker"}) is TransportMode.DESKTOP_BROKER


@pytest.mark.parametrize("value", ["LEGACY", "desktop-broker", " desktop_broker", "unknown"])
def test_transport_mode_rejects_aliases_with_exact_diagnostic(value):
    with pytest.raises(ValueError) as error:
        resolve_transport_mode({TRANSPORT_MODE_ENV: value})

    assert str(error.value) == (f"Invalid {TRANSPORT_MODE_ENV} value {value!r}; supported values: legacy, desktop_broker")
