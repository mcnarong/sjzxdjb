from __future__ import annotations

from ._bytecode_loader import exec_recovered_module as _exec_recovered_module

_exec_recovered_module(globals(), 'adb_automation\\failure_guidance.pyc')

del _exec_recovered_module

from .adb import RUNTIME_ROOT as _ADB_RUNTIME_ROOT


PROJECT_ROOT = _ADB_RUNTIME_ROOT
