"""Sync the core version required by the installers and bump installer versions."""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


INSTALLER_PATTERN = "*_installer.ps1"
CORE_VERSION_FILE = Path("sd_webui_all_in_one") / "version.py"
CORE_BUMP_PARTS = ("major", "minor", "patch")

# Only the real assignments start a line with ``$script:``; the copies inside the
# generated-script templates are escaped with a backtick and must stay untouched.
CORE_VERSION_PATTERN = re.compile(r'^(\s*VERSION\s*=\s*")([^"]+)(")', re.MULTILINE)
INSTALLER_VERSION_PATTERN = re.compile(r"^(\s*\$script:(\w+_INSTALLER_VERSION)\s*=\s*)(\d+)", re.MULTILINE)
CORE_MINIMUM_VERSION_PATTERN = re.compile(r'^(\s*\$script:CORE_MINIMUM_VER\s*=\s*")([^"]+)(")', re.MULTILINE)
CORE_VERSION_FORMAT = re.compile(r"\d+\.\d+\.\d+")


class VersionSyncError(Exception):
    """Raised when a version cannot be read or the requested change is invalid."""


@dataclass(frozen=True)
class InstallerUpdate:
    path: Path
    flag: str
    old_version: int
    new_version: int
    old_core_version: str
    new_core_version: str
    content: str

    @property
    def changed(self) -> bool:
        return self.old_version != self.new_version or self.old_core_version != self.new_core_version


def read_text(path: Path) -> str:
    """Read a file without translating line endings, keeping any BOM in the text."""
    with open(path, encoding="utf-8", newline="") as file:
        return file.read()


def write_text(path: Path, content: str) -> None:
    """Write a file back exactly as given, so the BOM and line endings are preserved."""
    with open(path, "w", encoding="utf-8", newline="") as file:
        file.write(content)


def find_single_match(pattern: re.Pattern[str], text: str, description: str, path: Path) -> re.Match[str]:
    """Find the only match of a pattern, failing on zero or several matches."""
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise VersionSyncError(f"{path}: expected exactly one {description}, found {len(matches)}")
    return matches[0]


def format_installer_version(version: int) -> str:
    """Format an installer version code the way the installers display it (532 -> v5.3.2)."""
    digits = str(version).rjust(3, "0")
    return f"v{digits[:-2]}.{digits[-2]}.{digits[-1]}"


def bump_core_version(version: str, part: str) -> str:
    """Increment one part of an ``X.Y.Z`` core version and reset the lower parts."""
    validate_core_version(version)
    major, minor, patch = (int(item) for item in version.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise VersionSyncError(f"unknown core version part: {part}")


def validate_core_version(version: str) -> None:
    """Ensure a core version is in ``X.Y.Z`` format."""
    if not CORE_VERSION_FORMAT.fullmatch(version):
        raise VersionSyncError(f"core version must be in X.Y.Z format: {version!r}")


def get_installer_paths(workspace: Path, names: list[str] | None = None) -> list[Path]:
    """Get the installer scripts to update, optionally limited to the given names."""
    installer_paths = sorted((workspace / "installer").glob(INSTALLER_PATTERN))
    if not installer_paths:
        raise VersionSyncError(f"no installer found in {workspace / 'installer'}")
    if not names:
        return installer_paths

    available = {path.name: path for path in installer_paths}
    selected = []
    for name in names:
        file_name = name if name.endswith(".ps1") else f"{name}.ps1"
        if file_name not in available:
            file_name = f"{name}_installer.ps1"
        if file_name not in available:
            raise VersionSyncError(f"unknown installer: {name} (available: {', '.join(available)})")
        if available[file_name] not in selected:
            selected.append(available[file_name])
    return selected


def plan_core_update(workspace: Path, bump_part: str | None, core_version: str | None) -> tuple[str, str, str]:
    """Work out the core version change.

    Returns:
        The old version, the new version and the new content of the version file.
    """
    path = workspace / CORE_VERSION_FILE
    content = read_text(path)
    match = find_single_match(CORE_VERSION_PATTERN, content, "VERSION assignment", path)
    old_version = match.group(2)

    if core_version is not None:
        new_version = core_version
    elif bump_part is not None:
        new_version = bump_core_version(old_version, bump_part)
    else:
        new_version = old_version
    validate_core_version(new_version)

    new_content = content[: match.start(2)] + new_version + content[match.end(2) :]
    return old_version, new_version, new_content


def plan_installer_update(path: Path, core_version: str, bump_installer: bool) -> InstallerUpdate:
    """Work out the version changes for one installer script."""
    content = read_text(path)
    version_match = find_single_match(INSTALLER_VERSION_PATTERN, content, "installer version assignment", path)
    old_version = int(version_match.group(3))
    new_version = old_version + 1 if bump_installer else old_version
    content = content[: version_match.start(3)] + str(new_version) + content[version_match.end(3) :]

    core_match = find_single_match(CORE_MINIMUM_VERSION_PATTERN, content, "CORE_MINIMUM_VER assignment", path)
    old_core_version = core_match.group(2)
    content = content[: core_match.start(2)] + core_version + content[core_match.end(2) :]

    return InstallerUpdate(
        path=path,
        flag=version_match.group(2),
        old_version=old_version,
        new_version=new_version,
        old_core_version=old_core_version,
        new_core_version=core_version,
        content=content,
    )


def format_change(old: str, new: str) -> str:
    return old if old == new else f"{old} -> {new}"


def print_report(old_core_version: str, new_core_version: str, updates: list[InstallerUpdate]) -> None:
    """Print the core version change and a table of the installer changes."""
    print(f"Core version: {format_change(old_core_version, new_core_version)}")
    rows = [("Installer", "Ver", "Code", "Core")]
    for update in updates:
        rows.append(
            (
                update.path.name,
                format_change(format_installer_version(update.old_version), format_installer_version(update.new_version)),
                format_change(str(update.old_version), str(update.new_version)),
                format_change(update.old_core_version, update.new_core_version),
            )
        )
    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    for row in rows:
        print("  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip())


def sync_versions(
    workspace: Path,
    *,
    bump_installer: bool = False,
    bump_core: str | None = None,
    core_version: str | None = None,
    installers: list[str] | None = None,
    dry_run: bool = False,
) -> int:
    """Sync installer core versions and apply the requested bumps.

    Every file is parsed before anything is written, so a failure never leaves
    the installers half updated.

    Returns:
        The number of files that were changed (or would be, for a dry run).
    """
    old_core_version, new_core_version, core_content = plan_core_update(workspace, bump_core, core_version)
    updates = [plan_installer_update(path, new_core_version, bump_installer) for path in get_installer_paths(workspace, installers)]

    print_report(old_core_version, new_core_version, updates)

    changed_count = 0
    if old_core_version != new_core_version:
        changed_count += 1
        if not dry_run:
            write_text(workspace / CORE_VERSION_FILE, core_content)
    for update in updates:
        if not update.changed:
            continue
        changed_count += 1
        if not dry_run:
            write_text(update.path, update.content)
    return changed_count


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync CORE_MINIMUM_VER in the installers with the core package version, optionally bumping the installer and core versions.",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to the parent directory of this script.",
    )
    parser.add_argument(
        "--bump-installer",
        action="store_true",
        help="Increment the version of each installer by 1.",
    )
    core_group = parser.add_mutually_exclusive_group()
    core_group.add_argument(
        "--bump-core",
        nargs="?",
        const="patch",
        choices=CORE_BUMP_PARTS,
        help="Increment the core package version before syncing. Defaults to patch.",
    )
    core_group.add_argument(
        "--core-version",
        help="Set the core package version to this X.Y.Z value before syncing.",
    )
    parser.add_argument(
        "--installer",
        nargs="+",
        metavar="NAME",
        help="Only update these installers, e.g. comfyui or comfyui_installer.ps1. Defaults to all installers.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the changes without writing any file.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        changed_count = sync_versions(
            args.workspace.resolve(),
            bump_installer=args.bump_installer,
            bump_core=args.bump_core,
            core_version=args.core_version,
            installers=args.installer,
            dry_run=args.dry_run,
        )
    except (VersionSyncError, OSError) as e:
        print(f"Installer version sync failed: {e}", file=sys.stderr)
        return 1

    if changed_count == 0:
        print("Installer versions are already in sync.")
    elif args.dry_run:
        print(f"Dry run: {changed_count} file(s) would be updated.")
    else:
        print(f"Updated {changed_count} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
