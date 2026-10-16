"""依赖文件解析与 pip 解析器的对照测试 (pip 不可用时跳过)

参考:
    - https://pip.pypa.io/en/stable/reference/requirements-file-format/
"""

import pytest

from sd_webui_all_in_one.package_analyzer.reqfile import (
    EntryKind,
    parse_requirements_file,
)


# ============================================================================
# 与 pip 对照
# ============================================================================
class TestPipOracle:
    """以 pip 自身的依赖文件解析器作为对照, pip 内部接口不可用时跳过"""

    def test_lines_match_pip(self, tmp_path, monkeypatch):
        req_file = pytest.importorskip("pip._internal.req.req_file")
        session_module = pytest.importorskip("pip._internal.network.session")
        monkeypatch.setenv("REQ_HOST", "h.example")
        monkeypatch.delenv("REQ_UNDEFINED", raising=False)

        (tmp_path / "sub").mkdir()
        (tmp_path / "main.txt").write_text(
            "\n".join(
                [
                    "# comment",
                    'torch==2.3.* ; sys_platform != "nope"   # trailing comment',
                    "requests[security] >= 2.8.1, \\",
                    "    < 3 --hash=sha256:abc --hash sha256:def",
                    "-e ./proj[dev]",
                    "--editable=other",
                    "./demo-1.0-py3-none-any.whl",
                    "git+https://github.com/user/Repo.git@main#egg=RealName&subdirectory=src",
                    "https://example.com/pkgs/demo_pkg-1.2.3-py3-none-any.whl#sha256=deadbeef",
                    "pkg @ https://${REQ_HOST}/${REQ_UNDEFINED}/pkg-1.0-py3-none-any.whl",
                    "-r sub/more.txt",
                    "-c cons.txt",
                    "--index-url https://a/simple --extra-index-url=https://b/simple",
                    "-f https://links --pre --no-binary :all:",
                    "last  ",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (tmp_path / "sub" / "more.txt").write_text("nested>=1\n-r deeper.txt\n", encoding="utf-8")
        (tmp_path / "sub" / "deeper.txt").write_text("deepest # note\n", encoding="utf-8")
        (tmp_path / "cons.txt").write_text("numpy<2\n-r from-constraint.txt\n", encoding="utf-8")
        (tmp_path / "from-constraint.txt").write_text("extra-req\n", encoding="utf-8")

        def pip_hashes(item):
            hashes = (item.options or {}).get("hashes") or {}
            return sorted(f"{algorithm}:{digest}" for algorithm, digests in hashes.items() for digest in digests)

        expected = sorted(
            (item.requirement, item.is_editable, item.constraint, pip_hashes(item)) for item in req_file.parse_requirements(str(tmp_path / "main.txt"), session=session_module.PipSession())
        )

        parsed = parse_requirements_file(tmp_path / "main.txt")
        actual = sorted((entry.raw, entry.editable, entry.constraint, sorted(entry.hashes) if entry.kind == EntryKind.NAMED else []) for entry in [*parsed.entries, *parsed.constraints])

        assert actual == expected
        assert parsed.errors == []
