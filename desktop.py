#!/usr/bin/env python3
"""
desktop.py — run Peloton as a native desktop app.

    python desktop.py [Career.cdb]

Starts the local server on a background thread and opens it in a native window
(via pywebview). If no career file is given, a native file picker opens first.
Falls back to the default browser if pywebview isn't installed.

    pip install pywebview        # for the native window (optional)
"""
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server import app as server

PORT = 8765
URL = f"http://127.0.0.1:{PORT}/"


def _pick_file():
    """Native file dialog (tkinter, stdlib) -> path or None."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw()
        path = filedialog.askopenfilename(
            title="Open PCM career (.cdb)",
            filetypes=[("PCM database", "*.cdb"), ("All files", "*.*")])
        root.destroy()
        return path or None
    except Exception:
        return None


class Api:
    """Exposed to the page as window.pywebview.api for runtime file opening."""
    def pick(self):
        import webview
        res = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG, file_types=("PCM database (*.cdb)", "All files (*.*)"))
        if res:
            server.open_career(res[0])
            return {"ok": True, "path": res[0]}
        return {"ok": False}


def _start_server():
    srv = server.build_server(PORT)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path and os.path.isfile(path):
        server.open_career(path)
    elif path is None:
        picked = _pick_file()
        if picked:
            server.open_career(picked)

    _start_server()

    try:
        import webview
        webview.create_window("Peloton — Season Planner", URL, width=1440, height=900,
                              min_size=(1100, 720), js_api=Api())
        webview.start()
    except ImportError:
        import webbrowser
        print(f"pywebview niet gevonden — open in browser: {URL}")
        print("(installeer met: pip install pywebview voor een native venster)")
        webbrowser.open(URL)
        import time
        while True:
            time.sleep(3600)


if __name__ == "__main__":
    main()
