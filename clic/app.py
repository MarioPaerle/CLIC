"""
CLIC — Cooler Lite IDE for Commandline

Multi-tab terminal with real PTY sessions.
Architecture: xterm.js + WebSocket + pywinpty, served to Edge in app mode.
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from fnmatch import fnmatch
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import urllib.request

import websockets

from clic.config import Config, BASE_DIR
from clic.sounds import SoundManager

# ── Nerd font icons ──────────────────────────────────────
_ICONS = {
    "dir": "", "up": "󰁞",
    ".py": "", ".js": "", ".ts": "", ".jsx": "", ".tsx": "",
    ".rs": "", ".go": "", ".java": "", ".c": "", ".cpp": "",
    ".json": "", ".yaml": "", ".yml": "", ".toml": "",
    ".md": "", ".txt": "", ".sh": "", ".bash": "",
    ".html": "", ".css": "",
    ".png": "", ".jpg": "", ".gif": "",
    ".zip": "", ".tar": "", ".gz": "",
    ".lock": "", ".log": "",
}
_DEFAULT_ICON = ""


def _list_dir(path_str: str) -> list[dict]:
    path = Path(path_str)
    excludes = Config.get("file_browser", "exclude", default=[])
    entries = []

    parent = path.parent
    if parent != path:
        entries.append({"name": "..", "path": str(parent), "is_dir": True, "icon": _ICONS["up"]})

    try:
        items = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return entries

    for item in items:
        name = item.name
        if any(fnmatch(name, pat) for pat in excludes):
            continue
        is_dir = item.is_dir()
        ext = Path(name).suffix.lower()
        icon = _ICONS["dir"] if is_dir else _ICONS.get(ext, _DEFAULT_ICON)
        entries.append({"name": name, "path": str(item), "is_dir": is_dir, "icon": icon})

    return entries


def _get_client_config() -> dict:
    """Build config dict to send to the frontend."""
    return {
        "font": {
            "family": Config.get("font", "family", default="JetBrainsMono Nerd Font"),
            "size": Config.get("font", "size", default=14),
            "line_height": Config.get("font", "line_height", default=1.2),
        },
        "background_image": Config.get("background_image", default=""),
        "background_opacity": Config.get("background_opacity", default=0.05),
        "shortcuts": Config.get("shortcuts", default=[]),
    }


class TerminalServer:
    """Manages multiple PTY sessions and the WebSocket bridge."""

    def __init__(self, sound: SoundManager):
        self.sound = sound
        self.sessions: dict[str, object] = {}
        self.current_dir = os.getcwd()

    def _spawn_pty(self) -> object:
        from winpty import PtyProcess
        shell = Config.get("shell", default="cmd")
        opts = Config.get("shell_options", shell, default={})
        exe = opts.get("executable", "cmd.exe")
        args_list = opts.get("args", [])
        cmd = exe + (" " + " ".join(args_list) if args_list else "")
        return PtyProcess.spawn(cmd)

    async def handle_ws(self, websocket):
        readers: dict[str, asyncio.Task] = {}

        async def read_pty(session_id: str, pty):
            loop = asyncio.get_event_loop()
            while True:
                try:
                    data = await loop.run_in_executor(None, lambda: self._pty_read(pty))
                    if data:
                        await websocket.send(json.dumps({
                            "type": "output", "session": session_id, "data": data,
                        }))
                    else:
                        await asyncio.sleep(0.01)
                except asyncio.CancelledError:
                    break
                except Exception:
                    await asyncio.sleep(0.05)

        self.sound.play_effect("startup")

        try:
            async for message in websocket:
                msg = json.loads(message)
                t = msg.get("type")

                if t == "get_config":
                    await websocket.send(json.dumps({
                        "type": "config", "data": _get_client_config(),
                    }))

                elif t == "new_session":
                    sid = msg["session"]
                    pty = self._spawn_pty()
                    self.sessions[sid] = pty
                    readers[sid] = asyncio.create_task(read_pty(sid, pty))

                elif t == "input":
                    pty = self.sessions.get(msg["session"])
                    if pty:
                        pty.write(msg["data"])
                        data = msg["data"]
                        if len(data) == 1 and (data.isprintable() or data in ('\r', ' ')):
                            self.sound.play_typing()

                elif t == "resize":
                    pty = self.sessions.get(msg["session"])
                    if pty:
                        try:
                            pty.setwinsize(msg["rows"], msg["cols"])
                        except Exception:
                            pass

                elif t == "close_session":
                    sid = msg["session"]
                    if sid in readers:
                        readers[sid].cancel()
                        del readers[sid]
                    pty = self.sessions.pop(sid, None)
                    if pty:
                        try:
                            pty.terminate(force=True)
                        except Exception:
                            pass

                elif t == "file_click":
                    await self._handle_file_click(websocket, msg)

                elif t == "run_shortcut":
                    pty = self.sessions.get(msg.get("session"))
                    if pty and msg.get("command"):
                        pty.write(msg["command"] + "\r")
                        self.sound.play_effect("command_run")

                elif t == "refresh_files":
                    await self._send_files(websocket)

                elif t == "open_folder_dialog":
                    import tkinter as tk
                    from tkinter import filedialog
                    def _pick():
                        root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
                        folder = filedialog.askdirectory(initialdir=self.current_dir)
                        root.destroy()
                        return folder
                    loop = asyncio.get_event_loop()
                    folder = await loop.run_in_executor(None, _pick)
                    if folder:
                        self.current_dir = folder
                        await self._send_files(websocket)
                        session = msg.get("session")
                        if session:
                            pty = self.sessions.get(session)
                            if pty:
                                escaped = folder.replace('"', '""')
                                pty.write(f'cd /d "{escaped}"\r')
                            self.sound.play_effect("cd")

                elif t == "open_settings":
                    theme_path = str(Path(__file__).parent / "web" / "theme.json")
                    config_path = str(BASE_DIR / "config.yaml")
                    try:
                        os.startfile(theme_path)
                        os.startfile(config_path)
                    except Exception:
                        pass

                elif t == "set_volume":
                    self.sound.set_volumes(
                        master=msg.get("master"),
                        typing=msg.get("typing"),
                        effects=msg.get("effects"),
                    )

                elif t == "toggle_ambient":
                    self.sound.toggle_ambient()

                elif t == "open_url":
                    url = msg.get("url", "")
                    if url.startswith(("http://", "https://")):
                        try:
                            os.startfile(url)
                        except Exception:
                            pass

                elif t == "save_md":
                    md_path = msg.get("path", "")
                    md_content = msg.get("content", "")
                    if md_path:
                        try:
                            Path(md_path).write_text(md_content, encoding="utf-8")
                        except Exception:
                            pass

                elif t == "save_colors":
                    theme_path = Path(__file__).parent / "web" / "theme.json"
                    try:
                        with open(theme_path, "r", encoding="utf-8") as f:
                            theme_data = json.load(f)
                        theme_data.setdefault("colors", {})
                        theme_data["colors"]["background"] = msg.get("background", "#000000")
                        theme_data["colors"]["foreground"] = msg.get("foreground", "#d4d4d4")
                        theme_data["colors"]["cursor"] = msg.get("accent", "#7aa2f7")
                        with open(theme_path, "w", encoding="utf-8") as f:
                            json.dump(theme_data, f, indent=2, ensure_ascii=False)
                    except Exception:
                        pass

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            for task in readers.values():
                task.cancel()
            for pty in self.sessions.values():
                try:
                    pty.terminate(force=True)
                except Exception:
                    pass
            self.sessions.clear()

    def _pty_read(self, pty):
        try:
            if not pty.isalive():
                return None
            return pty.read(8192)
        except (EOFError, RuntimeError):
            return None

    async def _handle_file_click(self, websocket, msg):
        path = msg["path"]
        is_dir = msg["is_dir"]
        name = msg["name"]
        session = msg.get("session")
        do_cd = msg.get("do_cd", False)

        if is_dir:
            # Always navigate the sidebar
            self.current_dir = path
            await self._send_files(websocket)

            # Only cd in terminal if ctrl+click (do_cd=True)
            if do_cd:
                pty = self.sessions.get(session)
                if pty:
                    escaped = path.replace('"', '""')
                    pty.write(f'cd "{escaped}"\r')
                self.sound.play_effect("cd")
        else:
            run = msg.get("run", False)
            ext = Path(name).suffix.lower()
            if run and ext == ".py":
                pty = self.sessions.get(session)
                if pty:
                    escaped = path.replace('"', '""')
                    pty.write(f'python "{escaped}"\r')
                self.sound.play_effect("command_run")
            elif ext == ".md":
                # Render markdown in a built-in viewer tab
                try:
                    content = Path(path).read_text(encoding="utf-8", errors="replace")
                    await websocket.send(json.dumps({
                        "type": "md_content", "filename": name, "content": content, "path": path,
                    }))
                except Exception:
                    pass
                self.sound.play_effect("file_open")
            else:
                try:
                    os.startfile(path)
                except Exception:
                    pass
                self.sound.play_effect("file_open")

    async def _send_files(self, websocket):
        display = self.current_dir.replace(str(Path.home()), "~")
        entries = _list_dir(self.current_dir)
        await websocket.send(json.dumps({
            "type": "files", "path": display, "entries": entries,
        }))


# ── Browser detection ────────────────────────────────────

def _find_edge() -> str | None:
    for p in [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]:
        if os.path.exists(p):
            return p
    return shutil.which("msedge") or shutil.which("msedge.exe")


def _find_chrome() -> str | None:
    for p in [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]:
        if os.path.exists(p):
            return p
    return shutil.which("chrome") or shutil.which("google-chrome")


# ── HTTP handler ─────────────────────────────────────────

class CLICHandler(SimpleHTTPRequestHandler):
    """Serves the web UI and background image."""

    def __init__(self, *args, **kwargs):
        self._web_dir = str(Path(__file__).parent / "web")
        super().__init__(*args, directory=self._web_dir, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        # Serve background image from config path
        if self.path == '/bg-image':
            bg_path = Config.get("background_image", default="")
            if bg_path:
                full_path = Path(bg_path)
                if not full_path.is_absolute():
                    full_path = BASE_DIR / bg_path
                if full_path.exists():
                    self.send_response(200)
                    ext = full_path.suffix.lower()
                    ct = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                          "gif": "image/gif", "webp": "image/webp", "svg": "image/svg+xml"
                    }.get(ext.lstrip("."), "application/octet-stream")
                    self.send_header("Content-Type", ct)
                    data = full_path.read_bytes()
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
            self.send_error(404)
            return
        return super().do_GET()

    def log_message(self, format, *args):
        pass


# ── Main ─────────────────────────────────────────────────

def run():
    Config.load()

    sound = SoundManager()
    sound.init()

    server = TerminalServer(sound)

    http_port = 17760
    httpd = HTTPServer(("127.0.0.1", http_port), CLICHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    ws_port = 17761

    async def ws_main():
        async with websockets.serve(server.handle_ws, "127.0.0.1", ws_port, max_size=2**20):
            await asyncio.Future()

    threading.Thread(target=lambda: asyncio.run(ws_main()), daemon=True).start()

    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{http_port}/index.html", timeout=1)
            break
        except Exception:
            time.sleep(0.1)

    browser = _find_edge() or _find_chrome()
    url = f"http://127.0.0.1:{http_port}/index.html?v={int(time.time())}"

    if not browser:
        print(f"Open {url} in your browser")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        user_data = os.path.join(tempfile.gettempdir(), "clic-browser")
        # Clear cached pages so the browser always loads fresh content
        cache_dir = os.path.join(user_data, "Default", "Cache")
        if os.path.isdir(cache_dir):
            shutil.rmtree(cache_dir, ignore_errors=True)
        proc = subprocess.Popen([
            browser,
            f"--app={url}",
            f"--user-data-dir={user_data}",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1100,700",
        ])
        proc.wait()

    httpd.shutdown()
    sound.shutdown()
