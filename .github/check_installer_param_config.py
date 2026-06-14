import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


INSTALLER_PATTERN = "*_installer.ps1"
SKIPPED_TEMPLATE_FUNCTIONS = {"Write-LaunchInstallerScript"}
MODULE_TEMPLATE_FUNCTION = "Write-ModulesScript"


@dataclass(frozen=True)
class Template:
    file_path: Path
    function_name: str
    line_number: int
    content: str


@dataclass(frozen=True)
class Issue:
    file_path: Path
    function_name: str
    line_number: int
    missing_config_keys: tuple[str, ...]
    unsupported_config_keys: tuple[str, ...]
    missing_module_assignments: tuple[str, ...]
    unknown_cfg_references: tuple[str, ...]


def get_line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def remove_escaped_here_strings(text: str) -> str:
    return re.sub(r'@`".*?`"@', '@`""@', text, flags=re.DOTALL)


def get_templates(installer_path: Path, require_config: bool = True) -> list[Template]:
    text = installer_path.read_text(encoding="utf-8-sig")
    pattern = re.compile(
        r"^function\s+(?P<function>Write-[A-Za-z0-9_-]*Script)\s*\{"
        r".*?^\s*\$content\s*=\s*\"\s*\n"
        r"(?P<content>.*?)"
        r"^\"\.Trim\(\)",
        flags=re.DOTALL | re.MULTILINE,
    )
    templates = []
    for match in pattern.finditer(text):
        function_name = match.group("function")
        if function_name in SKIPPED_TEMPLATE_FUNCTIONS:
            continue

        content = match.group("content")
        if require_config and not re.search(r"`?\$config\s*=\s*@\{", content):
            continue
        if require_config and ".Invoke({" not in content:
            continue

        templates.append(
            Template(
                file_path=installer_path,
                function_name=function_name,
                line_number=get_line_number(text, match.start("content")),
                content=content,
            )
        )
    return templates


def get_param_block(content: str) -> str:
    content = remove_escaped_here_strings(content)
    match = re.search(r"^\s*param\s*\(", content, flags=re.MULTILINE)
    if not match:
        return ""

    start = content.find("(", match.start())
    depth = 0
    for index in range(start, len(content)):
        char = content[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return content[start + 1 : index]

    return ""


def get_template_parameters(content: str) -> list[str]:
    block = get_param_block(content)
    if not block:
        return []

    params = []
    for variable_match in re.finditer(r"`?\$([A-Za-z_][A-Za-z0-9_]*)", block):
        name = variable_match.group(1)
        if name.lower() in {"false", "null", "true"}:
            continue
        if name not in params:
            params.append(name)
    return params


def get_config_keys(content: str) -> list[str]:
    match = re.search(
        r"`?\$config\s*=\s*@\{(?P<body>.*?)(?:^\s*\}\s*\n\s*\(Import-Module)",
        content,
        flags=re.DOTALL | re.MULTILINE,
    )
    if not match:
        return []

    keys = []
    for line in match.group("body").splitlines():
        key_match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if key_match:
            keys.append(key_match.group(1))
    return keys


def get_cfg_assignment_sources(content: str) -> list[str]:
    pattern = re.compile(
        r"`?\$script:[A-Za-z_][A-Za-z0-9_]*\s*=\s*`?\$cfg\.([A-Za-z_][A-Za-z0-9_]*)"
    )
    return [match.group(1) for match in pattern.finditer(content)]


def check_template(template: Template, module_param_keys: set[str]) -> Issue | None:
    params = get_template_parameters(template.content)
    config_keys = get_config_keys(template.content)
    cfg_assignment_sources = get_cfg_assignment_sources(template.content)

    forwardable_params = [param for param in params if param in module_param_keys]
    config_key_set = set(config_keys)
    cfg_assignment_source_set = set(cfg_assignment_sources)

    # Only parameters declared by Write-ModulesScript are expected to be forwarded.
    missing_config_keys = tuple(param for param in forwardable_params if param not in config_key_set)
    unsupported_config_keys = tuple(key for key in config_keys if key not in module_param_keys)
    missing_module_assignments = tuple(
        key for key in config_keys if key not in cfg_assignment_source_set
    )
    unknown_cfg_references = tuple(
        source for source in cfg_assignment_sources if source not in config_key_set
    )

    if not (
        missing_config_keys
        or unsupported_config_keys
        or missing_module_assignments
        or unknown_cfg_references
    ):
        return None

    return Issue(
        file_path=template.file_path,
        function_name=template.function_name,
        line_number=template.line_number,
        missing_config_keys=missing_config_keys,
        unsupported_config_keys=unsupported_config_keys,
        missing_module_assignments=missing_module_assignments,
        unknown_cfg_references=unknown_cfg_references,
    )


def get_module_param_keys(installer_path: Path) -> set[str]:
    templates = get_templates(installer_path, require_config=False)
    module_templates = [
        template for template in templates if template.function_name == MODULE_TEMPLATE_FUNCTION
    ]
    if len(module_templates) != 1:
        raise RuntimeError(
            f"Expected exactly one {MODULE_TEMPLATE_FUNCTION} in {installer_path}, "
            f"found {len(module_templates)}."
        )
    return set(get_template_parameters(module_templates[0].content))


def get_issues(workspace: Path) -> tuple[list[Issue], int]:
    installer_dir = workspace / "installer"
    installer_files = sorted(installer_dir.glob(INSTALLER_PATTERN))
    checked_count = 0
    issues = []

    for installer_file in installer_files:
        module_param_keys = get_module_param_keys(installer_file)
        for template in get_templates(installer_file):
            checked_count += 1
            issue = check_template(template, module_param_keys)
            if issue:
                issues.append(issue)

    return issues, checked_count


def format_keys(keys: tuple[str, ...]) -> str:
    return ", ".join(keys)


def print_issues(workspace: Path, issues: list[Issue], checked_count: int) -> None:
    print(f"Checked {checked_count} installer management script templates.")
    if not issues:
        print("Installer parameter/config forwarding check passed.")
        return

    print(f"Installer parameter/config forwarding check failed with {len(issues)} issue(s).")
    for issue in issues:
        relative_path = issue.file_path.relative_to(workspace)
        print(f"\n{relative_path}:{issue.line_number} {issue.function_name}")
        if issue.missing_config_keys:
            print(f"  Missing config keys: {format_keys(issue.missing_config_keys)}")
        if issue.unsupported_config_keys:
            print(
                "  Config keys not declared by Write-ModulesScript: "
                f"{format_keys(issue.unsupported_config_keys)}"
            )
        if issue.missing_module_assignments:
            print(
                "  Config keys not assigned from $cfg into module scope: "
                f"{format_keys(issue.missing_module_assignments)}"
            )
        if issue.unknown_cfg_references:
            print(f"  $cfg references without config key: {format_keys(issue.unknown_cfg_references)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check installer template param/config/module forwarding consistency."
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root. Defaults to the parent directory of .github.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = args.workspace.resolve()
    issues, checked_count = get_issues(workspace)
    print_issues(workspace, issues, checked_count)
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
