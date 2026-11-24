"""私有安装目录依赖检查的命令行契约。"""

import pytest

from sd_webui_all_in_one.cli_manager.utils import register_manager
from tests.cli_manager.helpers import single_command_parser


def test_requirements_in_target(tmp_path):
    parser = single_command_parser(register_manager)
    requirements = tmp_path / "requirements.txt"
    target = tmp_path / "packages"
    args = parser.parse_args(["self-manager", "check", "requirements", str(requirements), "--target", str(target)])
    requirements.write_text("-r nested.txt\n")
    with pytest.raises(SystemExit) as error:
        args.func(args)
    assert error.value.code == 1

    # pytest is installed in the invoking interpreter, but not in the target.
    (tmp_path / "nested.txt").write_text("pytest>=8\nunused; python_version < '2'\n")
    with pytest.raises(SystemExit) as error:
        args.func(args)
    assert error.value.code == 3
    metadata = target / "pytest-8.dist-info" / "METADATA"
    metadata.parent.mkdir(parents=True)
    metadata.write_text("Metadata-Version: 2.1\nName: pytest\nVersion: 8\n")
    args.func(args)
    metadata.write_text("Metadata-Version: 2.1\nName: pytest\nVersion: 7\n")
    with pytest.raises(SystemExit) as error:
        args.func(args)
    assert error.value.code == 3
