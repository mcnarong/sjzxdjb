# ADBAutomation Recovered Source Package

This project was recovered from `ADBAutomation.exe` / `PYZ.pyz`.

The original readable `.py` sources were not present in the portable package. The files under `adb_automation/*.py` are runtime loaders; they execute the original Python 3.13 bytecode stored under `recovered_bytecode/`.

## Run From Source

```powershell
python -m pip install -r requirements.txt
python main.py --help
python main.py
```

Use Python 3.13. The recovered bytecode will not load under Python 3.14+ unless the original source is rewritten.

## Build Portable Exe

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_portable.ps1
```

The portable result is written to `dist\ADBAutomation`.

## Important Files

- `adb_automation/*.py`: loader modules for recovered bytecode.
- `recovered_bytecode/`: original `.pyc` modules extracted from the exe.
- `recovery_artifacts/disassembly/`: recursive bytecode disassembly for future manual source reconstruction.
- `recovery_artifacts/pycdc_partial/`: incomplete `pycdc` output for reference only.

If the original `.py` files are recovered later, prefer replacing the loader modules with real source files.
