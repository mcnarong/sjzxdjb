from __future__ import annotations

import importlib.util
import marshal
import sys
from pathlib import Path


def _bundle_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root)
    return Path(__file__).resolve().parents[1]


def exec_recovered_module(module_globals: dict[str, object], relative_pyc_path: str) -> None:
    path = _bundle_root() / "recovered_bytecode" / relative_pyc_path
    data = path.read_bytes()
    magic = data[:4]
    if magic != importlib.util.MAGIC_NUMBER:
        raise RuntimeError(
            f"Recovered bytecode {path} was built for a different Python version: "
            f"file magic={magic!r}, runtime magic={importlib.util.MAGIC_NUMBER!r}. "
            "Use Python 3.13 to run this recovered project."
        )
    code = marshal.loads(data[16:])
    exec(code, module_globals)
