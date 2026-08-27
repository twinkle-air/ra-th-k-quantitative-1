"""Windows desktop entry point for the offline Ra-Th-K workbench."""

from __future__ import annotations

import ctypes
import os
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from app.main import app
from app.services.exporters import export_pdf, export_png, export_xlsx


class DesktopApi:
    """Native file-system bridge exposed only inside the packaged desktop app."""

    def __init__(self) -> None:
        desktop = Path.home() / "Desktop"
        self.export_directory = desktop if desktop.is_dir() else Path.home()
        self.window: Any | None = None

    def get_export_directory(self) -> str:
        return str(self.export_directory)

    def choose_export_directory(self) -> str:
        if self.window is None:
            return str(self.export_directory)
        import webview

        selected = self.window.create_file_dialog(
            webview.FOLDER_DIALOG,
            directory=str(self.export_directory),
        )
        if selected:
            candidate = Path(selected[0] if isinstance(selected, (tuple, list)) else selected)
            if candidate.is_dir():
                self.export_directory = candidate
        return str(self.export_directory)

    def save_export(self, format_name: str, language: str, analysis: dict[str, Any]) -> dict[str, str]:
        exporters = {"png": export_png, "pdf": export_pdf, "xlsx": export_xlsx}
        if format_name not in exporters:
            raise ValueError("不支持的导出格式。")
        if language not in {"zh", "zht", "en", "fr"}:
            raise ValueError("不支持的导出语言。")
        self.export_directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = self.export_directory / f"镭钍钾定量分析结果_{timestamp}.{format_name}"
        destination.write_bytes(exporters[format_name](analysis, language))
        return {"path": str(destination), "directory": str(self.export_directory)}


def _free_local_port(preferred: int = 8000) -> int:
    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("无法找到可用的本地端口。")


def _wait_until_ready(url: str, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("本地分析服务启动超时。")


def _open_workbench(url: str) -> None:
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/Application/msedge.exe",
    ]
    edge = next((path for path in candidates if path.is_file()), None)
    if edge:
        subprocess.Popen(
            [str(edge), f"--app={url}", "--no-first-run", "--disable-background-networking"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        webbrowser.open(url, new=1)


def main() -> int:
    port = _free_local_port()
    url = f"http://127.0.0.1:{port}"
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_config=None,
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="rtk-local-server", daemon=True)
    thread.start()
    try:
        _wait_until_ready(url)
        _open_workbench(url)
        ctypes.windll.user32.MessageBoxW(
            None,
            "分析工作台已在独立浏览器窗口中打开。\n\n使用结束后，请点击“确定”关闭本地服务。",
            "镭钍钾定量分析 - 运行中",
            0x40,
        )
    finally:
        server.should_exit = True
        thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException:
        error = traceback.format_exc()
        log_path = Path(os.environ.get("TEMP", str(Path.home()))) / "镭钍钾定量分析-启动错误.log"
        try:
            log_path.write_text(error, encoding="utf-8")
        except OSError:
            pass
        ctypes.windll.user32.MessageBoxW(
            None,
            f"程序启动失败，诊断日志已保存到：\n{log_path}\n\n{error[-800:]}",
            "镭钍钾定量分析 - 启动错误",
            0x10,
        )
        sys.exit(1)
