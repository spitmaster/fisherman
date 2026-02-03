# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

project_root = 'D:\\workspace\\wow\\fisherman'
src_dir = 'D:\\workspace\\wow\\fisherman\\src'

datas = [
    (src_dir, '.'),
    (project_root + '\\requirements.txt', '.')
]
binaries = []
hiddenimports = ['ultralytics', 'ultralytics.yolo', 'ultralytics.yolo.v8', 'torch', 'torchvision', 'cv2', 'PIL', 'PIL._imaging', 'pygetwindow', 'pyautogui', 'mss', 'sqlite3', 'tkinter']
tmp_ret = collect_all('ultralytics')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('torch')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('torchvision')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['D:\\workspace\\wow\\fisherman\\src\\main.py'],
    pathex=[project_root, src_dir],
    binaries=binaries,
    datas=datas,
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
    a.binaries,
    a.datas,
    [],
    name='Fisherman',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)