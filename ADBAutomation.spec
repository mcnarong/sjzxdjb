# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['adb_automation.adb', 'adb_automation.adb_keepalive', 'adb_automation.calibration', 'adb_automation.cli', 'adb_automation.desktop_app', 'adb_automation.diagnostics', 'adb_automation.delta_force_calibrator', 'adb_automation.failure_guidance', 'adb_automation.gui', 'adb_automation.license_gate', 'adb_automation.maintenance', 'adb_automation.run_log', 'adb_automation.scheduler', 'adb_automation.script_runner', 'adb_automation.webapp', 'adb_automation.wireless_adb', 'adb_automation.workflows', 'PIL', 'PIL.Image', 'PIL.ImageChops', 'PIL.ImageTk', 'tkinter', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.simpledialog', 'tkinter.ttk']
hiddenimports += collect_submodules('tkinter')
hiddenimports += collect_submodules('PIL')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('recovered_bytecode', 'recovered_bytecode'), ('device_profiles', 'device_profiles'), ('examples', 'examples'), ('platform-tools', 'platform-tools'), ('assets', 'assets')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ADBAutomation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\app_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ADBAutomation',
)
