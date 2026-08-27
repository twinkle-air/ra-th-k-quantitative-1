from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH)
app_root = root / "assets" / "app"
webview_datas, webview_binaries, webview_hidden = collect_all("webview")

a = Analysis(
    [str(root / "desktop_launcher.py")],
    pathex=[str(app_root)],
    binaries=webview_binaries,
    datas=[
        (str(app_root / "app" / "static"), "app/static"),
        (str(app_root / "data"), "data"),
    ] + webview_datas,
    hiddenimports=["uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on"] + webview_hidden,
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
    name="镭钍钾定量分析",
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
    icon=[str(root / "assets" / "project-icon.ico")],
)
