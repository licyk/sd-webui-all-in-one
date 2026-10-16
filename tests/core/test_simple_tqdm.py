"""SimpleTqdm 进度条测试"""

import io

from sd_webui_all_in_one.simple_tqdm import SimpleTqdm


def _reset_simple_tqdm_state():
    SimpleTqdm._active_instances = 0
    SimpleTqdm._max_pos = -1
    SimpleTqdm._instances.clear()


def test_simple_tqdm_disabled_iter_context_and_formatting(capsys):
    bar = SimpleTqdm([1, 2, 3], desc="items", disable=True)

    assert list(bar) == [1, 2, 3]
    assert bar.n == 3

    with SimpleTqdm(total=3, disable=True) as disabled_bar:
        disabled_bar.update(0)
        disabled_bar.update(2)
        assert disabled_bar.n == 2
        assert disabled_bar._format_time(65) == "01:05"

    with SimpleTqdm(total=2048, unit="B", unit_scale=True, disable=True) as bytes_bar:
        bytes_bar.update(1024)
        assert bytes_bar._format_amount(bytes_bar.n) == "1KB"

    assert capsys.readouterr().out == ""


def test_simple_tqdm_renders_known_total_and_clears(monkeypatch, capsys):
    _reset_simple_tqdm_state()
    times = iter([100.0, 100.0, 100.5, 101.0, 101.0])
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.time.time", lambda: next(times, 101.0))
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.shutil.get_terminal_size", lambda fallback: (50, 20))

    try:
        with SimpleTqdm(desc="demo", total=2, leave=False, bar_length=5) as bar:
            bar.update(1)
            bar.update(1)
            assert bar.n == 2
    finally:
        _reset_simple_tqdm_state()

    output = capsys.readouterr().out
    assert "demo" in output
    assert "100%" in output
    assert "\033[K" in output


def test_simple_tqdm_initial_unit_divisor_file_and_idempotent_close(monkeypatch):
    _reset_simple_tqdm_state()
    output = io.StringIO()
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.shutil.get_terminal_size", lambda fallback: (60, 20))

    bar = SimpleTqdm(total=2048, initial=512, unit="B", unit_scale=True, unit_divisor=1024, file=output, mininterval=0)

    assert bar.n == 512
    assert bar._format_amount(1536) == "1.5KB"
    assert bar._format_time(3661) == "1:01:01"

    bar.update(512)
    bar.update(0)
    bar.set_description("download")
    bar.set_postfix({"status": "ok"}, speed="fast")
    bar.set_postfix_str("done")
    bar.close()
    bar.close()

    rendered = output.getvalue()
    assert "download" in rendered
    assert "done" in rendered
    assert SimpleTqdm._active_instances == 0


def test_simple_tqdm_reset_clear_write_and_falsey_iterable(monkeypatch):
    class FalseyIterable:
        def __bool__(self):
            return False

        def __iter__(self):
            return iter([1, 2])

    _reset_simple_tqdm_state()
    output = io.StringIO()
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.shutil.get_terminal_size", lambda fallback: (40, 20))

    bar = SimpleTqdm(FalseyIterable(), total=2, file=output, ncols=40)

    assert list(bar) == [1, 2]
    assert bar.n == 2
    assert SimpleTqdm._active_instances == 0

    with SimpleTqdm(total=3, file=output, leave=False) as manual_bar:
        manual_bar.update(2)
        manual_bar.reset(total=5)
        assert manual_bar.n == 0
        assert manual_bar.total == 5
        manual_bar.clear()

    SimpleTqdm.write("message", file=output)
    rendered = output.getvalue()
    assert "\033[K" in rendered
    assert "message\n" in rendered


def test_simple_tqdm_colour_is_applied_only_to_known_bar_colours(monkeypatch):
    _reset_simple_tqdm_state()
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.shutil.get_terminal_size", lambda fallback: (80, 20))

    output = io.StringIO()
    with SimpleTqdm(total=2, colour="red", bar_length=4, file=output, mininterval=0) as bar:
        bar.update(1)

    rendered = output.getvalue()
    assert "\033[31m" in rendered
    assert "\033[0m" in rendered
    assert ": 50%|" in rendered

    output = io.StringIO()
    with SimpleTqdm(total=2, colour="unknown", bar_length=4, file=output, mininterval=0) as bar:
        bar.update(1)

    assert "\033[31m" not in output.getvalue()


def test_simple_tqdm_smoothing_controls_display_rate(monkeypatch):
    _reset_simple_tqdm_state()
    clock = {"now": 0.0}
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.time.time", lambda: clock["now"])
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.shutil.get_terminal_size", lambda fallback: (100, 20))

    output = io.StringIO()
    bar = SimpleTqdm(total=20, file=output, mininterval=0, smoothing=0.25)
    clock["now"] = 1.0
    bar.update(1)
    clock["now"] = 2.0
    bar.update(9)

    assert "3it/s" in output.getvalue()

    bar.reset(total=4)
    assert bar._ema_rate is None
    bar.close()

    output = io.StringIO()
    clock["now"] = 0.0
    bar = SimpleTqdm(total=20, file=output, mininterval=0, smoothing=0)
    clock["now"] = 1.0
    bar.update(1)
    clock["now"] = 2.0
    bar.update(9)
    bar.close()

    assert "5it/s" in output.getvalue()


def test_simple_tqdm_bar_format_subset_preserves_unknown_fields(monkeypatch):
    _reset_simple_tqdm_state()
    clock = {"now": 0.0}
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.time.time", lambda: clock["now"])
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.shutil.get_terminal_size", lambda fallback: (100, 20))

    output = io.StringIO()
    bar = SimpleTqdm(
        desc="fmt",
        total=4,
        file=output,
        mininterval=0,
        bar_length=4,
        bar_format="{desc}|{bar}|{n_fmt}/{total_fmt}|{postfix}|{elapsed}|{rate_fmt}|{unknown}",
    )
    bar.set_postfix_str("phase=1", refresh=False)
    clock["now"] = 2.0
    bar.update(2)
    bar.close()

    rendered = output.getvalue()
    assert "fmt|██--|2it/4it|phase=1|00:02|1it/s|{unknown}" in rendered


def test_simple_tqdm_truncates_ansi_and_wide_text_by_visible_width():
    bar = SimpleTqdm(total=1, disable=True, ncols=8)
    rendered = bar._truncate_visible("\033[36m下载任务进度\033[0m", 8)

    assert bar._visible_len(rendered) <= 8
    assert rendered.endswith("\033[0m")
    assert "..." in rendered


def test_simple_tqdm_write_clears_and_refreshes_active_bars(monkeypatch):
    _reset_simple_tqdm_state()
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.shutil.get_terminal_size", lambda fallback: (80, 20))

    output = io.StringIO()
    bar_one = SimpleTqdm(desc="one", total=2, file=output, position=0, mininterval=0)
    bar_two = SimpleTqdm(desc="two", total=2, file=output, position=1, mininterval=0)

    SimpleTqdm.write("log message", file=output)
    bar_two.close()
    bar_one.close()

    rendered = output.getvalue()
    assert "log message\n" in rendered
    assert rendered.count("\033[K") >= 4
    assert rendered.count("one") >= 2
    assert rendered.count("two") >= 2
