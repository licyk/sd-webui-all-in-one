"""package_analyzer 环境标记规范测试

参考:
    - https://packaging.python.org/en/latest/specifications/dependency-specifiers/
"""

import pytest

from sd_webui_all_in_one.package_analyzer.errors import (
    InvalidMarker,
    UndefinedEnvironmentName,
)
from sd_webui_all_in_one.package_analyzer.markers import (
    Marker,
    default_environment,
)

LINUX_ENV = {
    "implementation_name": "cpython",
    "implementation_version": "3.11.9",
    "os_name": "posix",
    "platform_machine": "x86_64",
    "platform_python_implementation": "CPython",
    "platform_release": "6.8.0-111-generic",
    "platform_system": "Linux",
    "platform_version": "#111-Ubuntu SMP PREEMPT_DYNAMIC",
    "python_full_version": "3.11.9",
    "python_version": "3.11",
    "sys_platform": "linux",
}


# ============================================================================
# 环境标记
# ============================================================================
class TestMarker:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            # String 字段: 区分大小写
            ('sys_platform == "linux"', True),
            ('platform_system == "Linux"', True),
            ('platform_system == "linux"', False),
            ('os_name != "nt"', True),
            ('platform_machine in "x86_64 AMD64"', True),
            ('"SMP" in platform_version', True),
            ('"win" not in sys_platform', True),
            # String 字段的有序比较: >= / <= 等同于 ==, > / < 恒为 False
            ('sys_platform >= "linux"', True),
            ('sys_platform <= "linux"', True),
            ('sys_platform >= "aaa"', False),
            ('sys_platform > "aaa"', False),
            ('sys_platform < "zzz"', False),
            # Version 字段: 按版本比较而不是字符串比较
            ('python_version >= "3.9"', True),
            ('python_version >= "3.10"', True),
            ('python_version < "3.9"', False),
            ('python_version == "3.*"', True),
            ('python_full_version ~= "3.11.0"', True),
            ('python_version in "3.10 3.11"', True),
            ('python_version not in "3.8 3.9"', True),
            ('implementation_version >= "3"', True),
            # Version | String 字段: 无法按版本比较时回退到字符串规则
            ('platform_release >= "5.0"', False),
            ('platform_release == "6.8.0-111-generic"', True),
            # 逻辑运算与优先级
            ('os_name == "nt" or os_name == "posix" and python_version >= "3"', True),
            ('(os_name == "nt" or os_name == "posix") and python_version < "3"', False),
            ('os_name == "nt" and python_version >= "3" or sys_platform == "linux"', True),
            # 旧字段名
            ("os.name == 'posix'", True),
            ("python_implementation == 'CPython'", True),
            # 常量可以位于左侧
            ('"3.9" <= python_version', True),
        ],
    )
    def test_evaluation(self, text, expected):
        assert Marker.parse(text).evaluate(LINUX_ENV) is expected

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "python_version",
            "python_version >=",
            "sys_platform == win32",
            'unknown_field == "x"',
            'python_version >= "3" and',
            'python_version >= "3" extra',
            '(python_version >= "3"',
            "python_version >= '3",
            'python_version notin "3"',
            '"3.4" < python_version < "3.9"',
        ],
    )
    def test_invalid_markers(self, text):
        with pytest.raises(InvalidMarker):
            Marker.parse(text)

    def test_extra_is_normalized_and_must_be_defined(self):
        marker = Marker.parse('extra == "Foo_Bar"')
        assert marker.evaluate({"extra": "foo-bar"}) is True
        assert marker.evaluate({"extra": "FOO.BAR"}) is True
        assert marker.evaluate({"extra": ""}) is False
        with pytest.raises(UndefinedEnvironmentName):
            marker.evaluate()
        assert marker.extra_names() == {"foo-bar"}

    def test_set_fields_only_support_containment(self):
        marker = Marker.parse('"gui" in extras and "dev" not in dependency_groups')
        assert marker.evaluate({"extras": {"GUI"}, "dependency_groups": set()}) is True
        assert marker.evaluate({"extras": set(), "dependency_groups": set()}) is False
        assert Marker.parse('extras == "gui"').evaluate({"extras": {"gui"}}) is False

    def test_marker_keeps_field_names_and_round_trips(self):
        marker = Marker.parse("python_version>='3.8' and (os_name=='nt' or os_name=='posix')")
        assert marker.fields() == {"python_version", "os_name"}
        assert str(marker) == 'python_version >= "3.8" and (os_name == "nt" or os_name == "posix")'
        assert Marker.parse(str(marker)) == marker

    def test_same_marker_evaluates_differently_per_environment(self):
        marker = Marker.parse('sys_platform == "win32"')
        assert marker.evaluate({"sys_platform": "win32"}) is True
        assert marker.evaluate({"sys_platform": "linux"}) is False

    def test_local_python_build_version(self):
        assert Marker.parse('python_full_version >= "3.13"').evaluate({"python_full_version": "3.13.0+"}) is True

    def test_default_environment_has_all_standard_fields(self):
        environment = default_environment()
        assert {"os_name", "sys_platform", "python_version", "python_full_version", "platform_machine"} <= set(environment)
        assert "extra" not in environment
