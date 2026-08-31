"""Validate the PyTorch accelerator bundled in a portable package."""

import argparse
import sys
from dataclasses import dataclass
from types import ModuleType


SUPPORTED_PYTORCH_TYPES = ("cuda", "rocm", "xpu", "mps")


@dataclass(frozen=True)
class PyTorchTypeInfo:
    version: str
    detected_type: str
    cuda_version: str | None
    hip_version: str | None
    mps_built: bool


def get_expected_pytorch_type(software_name: str) -> str:
    """Get the expected PyTorch type from a portable software name."""
    normalized_name = software_name.strip().casefold()
    for pytorch_type in SUPPORTED_PYTORCH_TYPES:
        if normalized_name.endswith(f"_{pytorch_type}"):
            return pytorch_type
    supported_suffixes = ", ".join(f"_{item}" for item in SUPPORTED_PYTORCH_TYPES)
    raise ValueError(f"software name must end with one of: {supported_suffixes}")


def _get_mps_built(torch_module: ModuleType) -> bool:
    backends = getattr(torch_module, "backends", None)
    mps = getattr(backends, "mps", None)
    is_built = getattr(mps, "is_built", None)
    return bool(is_built()) if callable(is_built) else False


def detect_pytorch_type(torch_module: ModuleType, platform: str = sys.platform) -> PyTorchTypeInfo:
    """Detect the accelerator type exposed by an imported torch module."""
    torch_version = getattr(torch_module, "version", None)
    version = str(getattr(torch_module, "__version__", getattr(torch_version, "__version__", "unknown")))
    cuda_version = getattr(torch_version, "cuda", None)
    hip_version = getattr(torch_version, "hip", None)
    normalized_version = version.casefold()
    mps_built = _get_mps_built(torch_module)

    if hip_version or "+rocm" in normalized_version:
        detected_type = "rocm"
    elif "+xpu" in normalized_version:
        detected_type = "xpu"
    elif cuda_version or "+cu" in normalized_version:
        detected_type = "cuda"
    elif platform.casefold().startswith("darwin") and mps_built:
        detected_type = "mps"
    elif "+cpu" in normalized_version:
        detected_type = "cpu"
    else:
        detected_type = "unknown"

    return PyTorchTypeInfo(
        version=version,
        detected_type=detected_type,
        cuda_version=str(cuda_version) if cuda_version else None,
        hip_version=str(hip_version) if hip_version else None,
        mps_built=mps_built,
    )


def validate_pytorch_type(software_name: str, torch_module: ModuleType, platform: str = sys.platform) -> PyTorchTypeInfo:
    """Validate that torch matches the accelerator encoded in software_name."""
    expected_type = get_expected_pytorch_type(software_name)
    info = detect_pytorch_type(torch_module, platform=platform)
    if info.detected_type != expected_type:
        raise RuntimeError(
            f"PyTorch type mismatch: expected {expected_type}, detected {info.detected_type} "
            f"(torch={info.version}, cuda={info.cuda_version}, hip={info.hip_version}, mps_built={info.mps_built})"
        )
    return info


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--software-name", required=True, help="Portable software name ending in _cuda, _rocm, _xpu, or _mps.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        import torch

        info = validate_pytorch_type(args.software_name, torch)
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        print(f"PyTorch accelerator check failed: {error}", file=sys.stderr)
        return 1

    print(
        f"PyTorch accelerator check passed: type={info.detected_type}, torch={info.version}, "
        f"cuda={info.cuda_version}, hip={info.hip_version}, mps_built={info.mps_built}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
