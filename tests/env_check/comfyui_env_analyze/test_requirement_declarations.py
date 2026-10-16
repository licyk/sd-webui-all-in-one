"""ComfyUI 组件依赖声明读取测试"""

import pytest

from sd_webui_all_in_one.env_check.comfyui_env_analyze.environment import read_requirement_declarations
from tests.package_analyzer.reqfile.helpers import make_project


# ============================================================================
# ComfyUI 环境分析使用的软件包声明列表
# ============================================================================
class TestRequirementDeclarations:
    def test_declarations_cover_file_syntax(self, tmp_path):
        requirement = tmp_path / "requirements.txt"
        requirement.write_text(
            "\n".join(
                [
                    "Torch==2.3.*",
                    "diffusers[torch]==0.33.1",
                    "protobuf>=4.25.3, \\",
                    "    <5",
                    "triton-windows<3.4 # skip_verify",
                    "never; python_version < '0'",
                    "git+https://github.com/user/repo.git@main#egg=RealName",
                    "git+https://gitlab.example/group/subgroup/Fancy-Package.git@main",
                    "git+ssh://git@github.com:user/sshrepo.git@main",
                    "https://example.test/packages/demo_pkg-1.2.3-py3-none-any.whl",
                    "direct @ https://example.com/direct-1.0.tar.gz",
                    "https://example.com/foo-1.0.tar.gz",
                    "invalid !!!",
                    "--pre",
                    "--extra-index-url=https://x/simple",
                    "numpy",
                    "",
                ]
            ),
            encoding="utf-8-sig",
        )

        assert read_requirement_declarations(requirement) == [
            "torch==2.3.*",
            "diffusers==0.33.1",
            "protobuf>=4.25.3,<5",
            "realname",
            "fancy-package",
            "sshrepo",
            "demo_pkg==1.2.3",
            "direct",
            "numpy",
        ]

    def test_declarations_follow_nested_files_and_editables(self, tmp_path):
        make_project(tmp_path / "proj")
        (tmp_path / "main.txt").write_text("torch==2.3.0\n-r more.txt\n-c cons.txt\n-e ./proj\n-e .\n", encoding="utf-8")
        (tmp_path / "more.txt").write_text("numpy<2\n", encoding="utf-8")
        (tmp_path / "cons.txt").write_text("scipy<2\n", encoding="utf-8")
        # 约束条目不是依赖; 无法确定软件包名的 "-e ." 只产生警告
        assert read_requirement_declarations(tmp_path / "main.txt") == ["torch==2.3.0", "numpy<2", "local_proj"]

    def test_declarations_raise_for_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_requirement_declarations(tmp_path / "missing.txt")
