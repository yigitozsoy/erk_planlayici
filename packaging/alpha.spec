# -*- mode: python ; coding: utf-8 -*-
# PyInstaller tanımı. packaging\build.ps1 üzerinden çalıştırın.
# Çıktı: build\dist\alpha\alpha.exe — Görev Yöneticisi'nde ve görev çubuğunda "alpha" adı ve logosu görünür
# (pythonw.exe ile çalışınca her yerde "Python" yazıyordu).
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [(os.path.join(ROOT, "alphaapp", "assets"), os.path.join("alphaapp", "assets"))]
hiddenimports = ["PyQt6.QtSvg", "PyQt6.QtNetwork", "winsound", "wave"]

EXCLUDES = [
    "tkinter", "unittest", "pydoc", "test", "lib2to3", "matplotlib", "scipy", "pandas", "numpy", "IPython",
    "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets", "PyQt6.QtWebChannel", "PyQt6.QtQml",
    "PyQt6.QtQuick", "PyQt6.QtQuickWidgets", "PyQt6.Qt3DCore", "PyQt6.QtBluetooth", "PyQt6.QtSql",
    "PyQt6.QtTest", "PyQt6.QtDesigner", "PyQt6.QtHelp", "PyQt6.QtPdf", "PyQt6.QtPdfWidgets",
    "PyQt6.QtMultimedia", "PyQt6.QtMultimediaWidgets", "PyQt6.QtPositioning", "PyQt6.QtSensors",
    "PyQt6.QtSerialPort", "PyQt6.QtCharts", "PyQt6.QtOpenGL", "PyQt6.QtOpenGLWidgets",
]

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="alpha",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    version=os.path.join(SPECPATH, "version_info.txt"),
    icon=[os.path.join(ROOT, "alphaapp", "assets", "logo.ico")],
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="alpha")
