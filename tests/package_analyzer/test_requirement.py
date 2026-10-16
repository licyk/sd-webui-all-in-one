"""package_analyzer 依赖声明规范测试

参考:
    - https://packaging.python.org/en/latest/specifications/dependency-specifiers/
"""

import pytest

from sd_webui_all_in_one.package_analyzer.errors import (
    InvalidRequirement,
)
from sd_webui_all_in_one.package_analyzer.requirement import Requirement


# ============================================================================
# 依赖声明
# ============================================================================
class TestRequirement:
    def test_full_requirement(self):
        requirement = Requirement.parse('requests [security,tests] >= 2.8.1, == 2.8.* ; python_version < "2.7"')
        assert requirement.name == "requests"
        assert requirement.extras == ("security", "tests")
        assert str(requirement.specifier) == ">=2.8.1,==2.8.*"
        assert requirement.url is None
        assert str(requirement.marker) == 'python_version < "2.7"'
        assert str(requirement) == 'requests[security,tests]>=2.8.1,==2.8.*; python_version < "2.7"'

    def test_url_requirement(self):
        requirement = Requirement.parse("pip @ https://github.com/pypa/pip/archive/1.3.1.zip#sha1=da9234 ; os_name == 'posix'")
        assert requirement.name == "pip"
        assert requirement.url == "https://github.com/pypa/pip/archive/1.3.1.zip#sha1=da9234"
        assert not requirement.specifier
        assert str(requirement.marker) == 'os_name == "posix"'

    def test_url_swallows_semicolon_without_whitespace(self):
        requirement = Requirement.parse("a @ https://e.com/a.whl;python_version<'3'")
        assert requirement.url == "https://e.com/a.whl;python_version<'3'"
        assert requirement.marker is None

    @pytest.mark.parametrize(
        "text",
        [
            "A",
            "A.B-C_D",
            "name<=1.0",
            "name>=3,<2",
            "name@http://foo.com",
            "name [fred,bar] @ http://foo.com ; python_version=='2.7'",
            "name[quux, strange];python_version<'2.7' and platform_version=='2'",
            "name; os_name=='a' or os_name=='b'",
            "name; os_name=='a' and os_name=='b' or os_name=='c'",
            "name; os_name=='a' and (os_name=='b' or os_name=='c')",
            "name (>=1.0,<2)",
            "name[]",
            " name   >=  1.0  ,  < 2  ",
            "name===1.0+foo",
            "torch==2.3.0+cu118",
        ],
    )
    def test_valid_requirements_round_trip(self, text):
        requirement = Requirement.parse(text)
        assert Requirement.parse(str(requirement)) == requirement

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "requests>=1.0 garbage here",
            "pâckage>=1.0",
            "-a",
            "a-",
            "a..b==",
            "a~=1",
            "a>=1.*",
            "a>=",
            "a==1.0a1.*",
            "a>=1.0+local",
            "a(>=1.0",
            "a[x,]",
            "a[,x]",
            "a[x y]",
            "a @",
            "a;",
            "a; sys_platform == win32",
            "a; unknown == 'x'",
            "a >= 1.0 # comment",
            "a==1.0 --hash=sha256:abc",
            "a==not_canonical",
        ],
    )
    def test_invalid_requirements(self, text):
        with pytest.raises(InvalidRequirement):
            Requirement.parse(text)

    def test_error_reports_position(self):
        with pytest.raises(InvalidRequirement) as error:
            Requirement.parse("requests>=1.0 garbage")
        assert error.value.position == 14
        assert error.value.text == "requests>=1.0 garbage"
        assert "^" in str(error.value)
        assert isinstance(error.value, ValueError)

    def test_normalized_accessors(self):
        requirement = Requirement.parse("Foo_Bar[Dev_Tools]")
        assert requirement.normalized_name == "foo-bar"
        assert requirement.normalized_extras == {"dev-tools"}

    def test_applies_to_treats_missing_extra_as_not_requested(self):
        assert Requirement.parse("a; extra == 'gpu'").applies_to() is False
        assert Requirement.parse("a; extra == 'gpu'").applies_to({"extra": "gpu"}) is True
        assert Requirement.parse("a").applies_to() is True
