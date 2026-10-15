from __future__ import annotations

from ._bytecode_loader import exec_recovered_module as _exec_recovered_module

_exec_recovered_module(globals(), 'adb_automation\\cli.pyc')

del _exec_recovered_module


_cli_main = main


def main(argv=None):
    import sys as _sys

    args = list(_sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"-h", "--help", "help"}:
        return _cli_main(argv)

    from .license_gate import ensure_license_tk

    if not ensure_license_tk():
        return 1
    return _cli_main(argv)
