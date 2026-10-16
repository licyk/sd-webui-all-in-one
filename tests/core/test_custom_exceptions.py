"""自定义异常测试"""

from sd_webui_all_in_one.custom_exceptions import AggregateError


def test_aggregate_error_formats_child_traceback():
    try:
        raise ValueError("inner")
    except ValueError as exc:
        aggregate = AggregateError("many failed", [exc])

    text = str(aggregate)
    assert "many failed" in text
    assert "ValueError" in text
    assert "inner" in text
    assert "test_aggregate_error_formats_child_traceback" in text
