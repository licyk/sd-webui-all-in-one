import argparse
import configparser
import sys
from pathlib import Path


CONFIG_SECTION = "default"
TARGET_VALUES = {
    "network_mode": "personal_cloud",
    "security_level": "weak",
}


def configure_comfyui_manager(config_path: Path) -> None:
    if not config_path.is_file():
        raise FileNotFoundError(f"ComfyUI Manager config not found: {config_path}")

    config = configparser.ConfigParser(allow_no_value=True, interpolation=None)
    config.read(config_path, encoding="utf-8")

    if not config.has_section(CONFIG_SECTION):
        config.add_section(CONFIG_SECTION)

    for key, value in TARGET_VALUES.items():
        config.set(CONFIG_SECTION, key, value)

    with config_path.open("w", encoding="utf-8") as file:
        config.write(file)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Configure ComfyUI Manager settings for portable builds."
    )
    parser.add_argument(
        "--config-path",
        type=Path,
        required=True,
        help="Path to ComfyUI Manager config.ini.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        configure_comfyui_manager(args.config_path)
    except Exception as e:
        print(e, file=sys.stderr)
        return 1

    print(f"Configured ComfyUI Manager config: {args.config_path}")
    for key, value in TARGET_VALUES.items():
        print(f"{key} = {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
