from __future__ import annotations

from ._bytecode_loader import exec_recovered_module as _exec_recovered_module

_exec_recovered_module(globals(), 'adb_automation\\gui.pyc')

del _exec_recovered_module

from .adb import RUNTIME_ROOT as _ADB_RUNTIME_ROOT


PROJECT_ROOT = _ADB_RUNTIME_ROOT


class _HiddenSubprocessProxy:
    def __init__(self, module):
        self._module = module

    def __getattr__(self, name):
        return getattr(self._module, name)

    def Popen(self, *args, **kwargs):
        if _os.name == "nt":
            startupinfo = kwargs.get("startupinfo")
            if startupinfo is None:
                startupinfo = self._module.STARTUPINFO()
                startupinfo.dwFlags |= self._module.STARTF_USESHOWWINDOW
                kwargs["startupinfo"] = startupinfo
            kwargs["creationflags"] = kwargs.get("creationflags", 0) | self._module.CREATE_NO_WINDOW
        return self._module.Popen(*args, **kwargs)

    def run(self, *args, **kwargs):
        if _os.name == "nt":
            startupinfo = kwargs.get("startupinfo")
            if startupinfo is None:
                startupinfo = self._module.STARTUPINFO()
                startupinfo.dwFlags |= self._module.STARTF_USESHOWWINDOW
                kwargs["startupinfo"] = startupinfo
            kwargs["creationflags"] = kwargs.get("creationflags", 0) | self._module.CREATE_NO_WINDOW
        return self._module.run(*args, **kwargs)


import os as _os

subprocess = _HiddenSubprocessProxy(subprocess)


_gui_launch = launch


def launch(*args, **kwargs):
    from .license_gate import ensure_license_tk

    if not ensure_license_tk():
        return None
    return _gui_launch(*args, **kwargs)
