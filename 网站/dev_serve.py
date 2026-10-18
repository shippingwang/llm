#!/usr/bin/env python3
"""Watch manuscripts and keep the MkDocs preview in sync.

Canonical source is ../书稿. On Markdown changes, this script regenerates
网站/docs; mkdocs serve already hot-reloads from docs/.
"""

from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import sync_content


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WATCH_DIRS = [
    ROOT / "书稿",
    HERE / "stylesheets",
    HERE / "javascripts",
]


class DebouncedSync(FileSystemEventHandler):
    def __init__(self, delay: float = 0.8, quiet_until: float = 0.0) -> None:
        super().__init__()
        self.delay = delay
        self.quiet_until = quiet_until
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._busy = False
        self._pending = False
        self._last_trigger = ""

    def on_any_event(self, event) -> None:
        if event.is_directory:
            return
        if time.time() < self.quiet_until:
            return

        path = Path(getattr(event, "src_path", "") or "")
        name = path.name
        if (
            name.startswith(".")
            or name.endswith("~")
            or name.endswith(".tmp")
            or name.endswith(".swp")
        ):
            return

        try:
            resolved = path.resolve()
        except OSError:
            return

        # Generated output must never retrigger sync.
        if sync_content.DOCS in resolved.parents or resolved == sync_content.DOCS:
            return
        if (HERE / "site") in resolved.parents or resolved == HERE / "site":
            return

        if path.suffix.lower() not in {".md", ".css", ".js"}:
            return

        under_watch_dir = any(
            d.exists() and (d in resolved.parents or resolved == d)
            for d in WATCH_DIRS
        )
        if not under_watch_dir:
            return

        self._last_trigger = str(resolved.relative_to(ROOT)) if ROOT in resolved.parents else str(resolved)
        self._schedule()

    def _schedule(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.delay, self._run)
            self._timer.daemon = True
            self._timer.start()

    def _run(self) -> None:
        with self._lock:
            if self._busy:
                self._pending = True
                return
            self._busy = True
            self._pending = False
            trigger = self._last_trigger
        try:
            print(
                f"[sync] {time.strftime('%H:%M:%S')} trigger={trigger or '?'} …",
                flush=True,
            )
            changed = sync_content.main()
            # Give mkdocs time to finish one rebuild before accepting more events.
            self.quiet_until = time.time() + 1.2
            if changed:
                print(f"[sync] {time.strftime('%H:%M:%S')} docs updated", flush=True)
            else:
                print(f"[sync] {time.strftime('%H:%M:%S')} no content change", flush=True)
        except Exception as exc:  # noqa: BLE001 — preview should keep running
            print(f"[sync] failed: {exc}", file=sys.stderr, flush=True)
        finally:
            with self._lock:
                self._busy = False
                again = self._pending
                self._pending = False
            if again:
                self._schedule()


def start_mkdocs(host: str, port: int) -> subprocess.Popen:
    mkdocs = Path.home() / ".local" / "bin" / "mkdocs"
    cmd = [
        str(mkdocs) if mkdocs.exists() else "mkdocs",
        "serve",
        "-a",
        f"{host}:{port}",
    ]
    return subprocess.Popen(cmd, cwd=HERE)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--delay", type=float, default=0.8, help="debounce seconds")
    args = parser.parse_args()

    print("[sync] initial build …", flush=True)
    sync_content.main()

    handler = DebouncedSync(delay=args.delay, quiet_until=time.time() + 2.0)
    observer = Observer()
    for directory in WATCH_DIRS:
        if directory.exists():
            observer.schedule(handler, str(directory), recursive=True)
    observer.start()

    proc = start_mkdocs(args.host, args.port)
    print(
        f"[preview] watching 书稿 → docs → mkdocs  |  http://127.0.0.1:{args.port}/",
        flush=True,
    )

    stop = threading.Event()

    def shutdown(*_args) -> None:
        stop.set()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while not stop.is_set():
            code = proc.poll()
            if code is not None:
                print(f"[preview] mkdocs exited with {code}", flush=True)
                return code
            stop.wait(0.5)
    finally:
        observer.stop()
        observer.join(timeout=2)
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
