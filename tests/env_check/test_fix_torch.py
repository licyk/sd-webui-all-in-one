"""PyTorch 运行库修复测试"""

import importlib
import types

fix_torch = importlib.import_module("sd_webui_all_in_one.env_check.fix_torch.fixer")


def test_fix_torch_libomp_copies_missing_runtime(monkeypatch, tmp_path):
    torch_root = tmp_path / "torch"
    lib = torch_root / "lib"
    lib.mkdir(parents=True)
    fbgemm = lib / "fbgemm.dll"
    fbgemm.write_bytes(b"needs libomp140.x86_64.dll")
    (lib / "libiomp5md.dll").write_bytes(b"runtime")

    spec = types.SimpleNamespace(submodule_search_locations=[torch_root.as_posix()])
    monkeypatch.setattr(fix_torch.importlib.util, "find_spec", lambda name: spec if name == "torch" else None)
    monkeypatch.setattr(fix_torch.ctypes.cdll, "LoadLibrary", lambda _path: (_ for _ in ()).throw(FileNotFoundError("missing dll")))

    fix_torch.fix_torch_libomp()

    assert (lib / "libomp140.x86_64.dll").read_bytes() == b"runtime"

    (lib / "libomp140.x86_64.dll").write_bytes(b"existing")
    fix_torch.fix_torch_libomp()
    assert (lib / "libomp140.x86_64.dll").read_bytes() == b"existing"
