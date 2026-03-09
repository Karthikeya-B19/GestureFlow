# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for GestureFlow HCI."""

import sys
import os

block_cipher = None

a = Analysis(
    ['apps/hci/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets/icons/*.ico', 'assets/icons'),
    ],
    hiddenimports=[
        'pycaw',
        'pycaw.pycaw',
        'comtypes',
        'comtypes.stream',
        'pynput',
        'pynput.keyboard',
        'pynput.keyboard._win32',
        'pynput.mouse',
        'pynput.mouse._win32',
        'screen_brightness_control',
        'mediapipe',
        'mediapipe.python',
        'mediapipe.python.solutions',
        'cv2',
        'numpy',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'pyautogui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'pandas',
        'PIL',
        'tkinter',
        'unittest',
        'test',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GestureFlowHCI',
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
    icon='assets/icons/app_icon.ico',
)
