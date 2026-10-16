"""SD WebUI Forge Neo 提示修复测试"""

import importlib
import json
import sys

fix_forge_neo_alert = importlib.import_module("sd_webui_all_in_one.env_check.fix_forge_neo_alert")


fix_forge_neo_alert_worker = importlib.import_module("sd_webui_all_in_one.env_check.fix_forge_neo_alert.worker")


fix_forge_neo_alert_fixer = importlib.import_module("sd_webui_all_in_one.env_check.fix_forge_neo_alert.fixer")


def test_fix_forge_neo_alert_worker_updates_moves_or_ignores(monkeypatch, tmp_path):
    webui = tmp_path / "webui"
    modules = webui / "modules"
    modules.mkdir(parents=True)
    (modules / "__init__.py").write_text("", encoding="utf-8")
    (modules / "launch_utils.py").write_text("VERSION_UID = 'new-version'\n", encoding="utf-8")
    config = webui / "config.json"
    config.write_text(json.dumps({"VERSION_UID": "old"}), encoding="utf-8")

    try:
        fix_forge_neo_alert.fix_alert_worker(webui)
    finally:
        sys.path = [p for p in sys.path if p != webui.as_posix()]
        sys.modules.pop("modules.launch_utils", None)
        sys.modules.pop("modules", None)

    assert json.loads(config.read_text(encoding="utf-8"))["VERSION_UID"] == "new-version"

    moved = []
    config.write_text("{", encoding="utf-8")
    monkeypatch.setattr(fix_forge_neo_alert_worker, "move_files", lambda src, dst: moved.append((src, dst)))
    try:
        fix_forge_neo_alert.fix_alert_worker(webui)
    finally:
        sys.path = [p for p in sys.path if p != webui.as_posix()]
        sys.modules.pop("modules.launch_utils", None)
        sys.modules.pop("modules", None)
    assert moved == [(config, webui / "tmp" / "config.json")]

    missing = tmp_path / "missing-webui"
    missing.mkdir()
    fix_forge_neo_alert.fix_alert_worker(missing)


def test_fix_forge_neo_alert_process_cleanup(monkeypatch, tmp_path):
    events = []

    class FakeProcess:
        def __init__(self, target, args, name):
            events.append(("process", target.__name__, args, name))
            self.alive = True

        def start(self):
            events.append("start")

        def join(self):
            events.append("join")

        def is_alive(self):
            return self.alive

        def terminate(self):
            events.append("terminate")
            self.alive = False

        def close(self):
            events.append("close")

    class FakeContext:
        Process = FakeProcess

    monkeypatch.setattr(fix_forge_neo_alert_fixer.multiprocessing, "get_context", lambda mode: events.append(("ctx", mode)) or FakeContext())

    fix_forge_neo_alert.fix_forge_neo_alert(tmp_path)

    assert events == [
        ("ctx", "spawn"),
        ("process", "fix_alert_worker", (tmp_path,), "ForgeNeoAlertFix"),
        "start",
        "join",
        "terminate",
        "join",
        "close",
    ]
