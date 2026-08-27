from pathlib import Path

root = Path(SPECPATH)
app_root = root / "assets" / "app"

a = Analysis(
    [str(root / "desktop_launcher.py")],
    pathex=[str(app_root)],
    binaries=[],
    datas=[
        (str(app_root / "app" / "static"), "app/static"),
        (str(app_root / "data"), "data"),
    ],
    hiddenimports=["uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["webview", "clr", "pythonnet"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="镭钍钾定量分析-Win10兼容版",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=[str(root / "assets" / "project-icon.ico")],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="镭钍钾定量分析-Win10兼容版",
)
