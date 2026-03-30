from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any


class UsageDB:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._lock = Lock()

    def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS visitor_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    event_type TEXT NOT NULL,
                    ip_address TEXT,
                    path TEXT,
                    method TEXT,
                    status_code INTEGER,
                    user_agent TEXT,
                    os_name TEXT,
                    system_name TEXT,
                    browser_name TEXT,
                    accept_language TEXT,
                    page TEXT
                )
                """
            )
            conn.commit()

    def log_event(self, event: dict[str, Any]) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO visitor_events (
                        event_type,
                        ip_address,
                        path,
                        method,
                        status_code,
                        user_agent,
                        os_name,
                        system_name,
                        browser_name,
                        accept_language,
                        page
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.get("event_type", "unknown"),
                        event.get("ip_address"),
                        event.get("path"),
                        event.get("method"),
                        event.get("status_code"),
                        event.get("user_agent"),
                        event.get("os_name"),
                        event.get("system_name"),
                        event.get("browser_name"),
                        event.get("accept_language"),
                        event.get("page"),
                    ),
                )
                conn.commit()

    def recent_events(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, event_type, ip_address, path, method, status_code,
                       user_agent, os_name, system_name, browser_name, accept_language, page
                FROM visitor_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        keys = [
            "id",
            "created_at",
            "event_type",
            "ip_address",
            "path",
            "method",
            "status_code",
            "user_agent",
            "os_name",
            "system_name",
            "browser_name",
            "accept_language",
            "page",
        ]
        return [dict(zip(keys, row)) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)


def parse_os_from_user_agent(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if "windows" in ua:
        return "Windows"
    if "android" in ua:
        return "Android"
    if "iphone" in ua or "ipad" in ua or "ios" in ua:
        return "iOS"
    if "mac os" in ua or "macintosh" in ua:
        return "macOS"
    if "linux" in ua:
        return "Linux"
    return "Unknown"


def parse_browser_from_user_agent(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if "edg/" in ua:
        return "Edge"
    if "chrome/" in ua and "edg/" not in ua:
        return "Chrome"
    if "firefox/" in ua:
        return "Firefox"
    if "safari/" in ua and "chrome/" not in ua:
        return "Safari"
    return "Unknown"
