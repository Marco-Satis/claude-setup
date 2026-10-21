#!/usr/bin/env python3
"""Nachrichtenkanal Claude <-> Codex (2026-09-29).

Richtung Claude -> Codex (echtes Push):
    agent_msg.py to-codex "Nachricht" [--thread claude-partner] [--cwd DIR] [--timeout 900]
    Startet einen eigenen `codex app-server` (stdio, JSON-RPC), setzt den benannten
    Thread fort (oder legt ihn an) und schickt die Nachricht als neuen Turn. Codex
    arbeitet sofort; die Antwort geht auf stdout. Der Thread behaelt seinen Verlauf.

Richtung Codex -> Claude (Zustellung beim naechsten Hook-Ereignis):
    agent_msg.py to-claude "Nachricht" --to <projekt-slug|all> [--from codex]
    Legt eine mcp-Memory mit Tags `agent-msg,to-claude,to:<slug>,from:<absender>` an.
    Codex selbst nutzt dafuer das MCP-Tool memory_store mit denselben Tags (siehe
    ~/.codex/AGENTS.md); dieses Kommando ist fuer Shell/Tests.
    Zustellung: Hook ~/.claude/hooks/agent_inbox.py.

Sonstiges:
    agent_msg.py inbox [--to <slug>] [--limit 10]   letzte Nachrichten an Claude
    agent_msg.py threads                             Codex-Threads auflisten
    agent_msg.py notify-pending                      Discord-Ping fuer unzugestellte
                                                     Nachrichten > 10 min (Cron)

Grenze: Ist derselbe Codex-Thread parallel in der Desktop-App offen (eigener
app-server), sieht die App die neue Nachricht erst nach Neuladen.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import select
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude" / "scripts"))
try:
    from memory_auth import auth_headers as _auth, base_url as _base
except Exception:  # pragma: no cover
    def _auth() -> dict:
        return {}

    def _base() -> str:
        return "http://127.0.0.1:8000"

STATE_DIR = Path.home() / ".claude" / "state"
THREADS = STATE_DIR / "agent_msg_threads.json"      # name -> threadId
DELIVERED = STATE_DIR / "agent_inbox_delivered.json"  # hash -> iso (von agent_inbox.py)
NOTIFIED = STATE_DIR / "agent_msg_notified.json"
CODEX = str(Path.home() / ".local" / "bin" / "codex")
DEFAULT_CWD = str(Path.home() / "projects" / "Skills_&_Co")

PARTNER_INSTRUCTIONS = (
    "Du bist Codex und arbeitest mit Claude (Claude Code) auf des Nutzers netcup-Server zusammen. "
    "Nachrichten in diesem Thread kommen von Claude, nicht von der Nutzer. Antworte knapp, "
    "sachlich, auf Deutsch; Code und Fachbegriffe englisch. Widersprich, wenn Claude falsch "
    "liegt. Willst du Claude spaeter von dir aus etwas mitteilen, nutze memory_store mit den "
    "Tags agent-msg,to-claude,to:<projekt-slug>,from:codex (Details: ~/.codex/AGENTS.md)."
)


def slug(name: str) -> str:
    """Projekt-Slug: Verzeichnisname, klein, nur [a-z0-9]."""
    return re.sub(r"[^a-z0-9]", "", name.lower()) or "all"


# ---------------------------------------------------------------- Codex-Seite
# Die RC-Units laden mcp.env per EnvironmentFile; ohne Filter erbt Codex MCP_API_KEY &
# Co. und schreibt sie im Klartext in ~/.codex/shell_snapshots (Befund 2026-10-01: 16
# Dateien). Codex selbst braucht keine davon: Login in ~/.codex/auth.json, der
# Memory-Adapter liest mcp.env selbst.
_SECRET_ENV = re.compile(r"KEY|TOKEN|SECRET|PASSW|WEBHOOK|CREDENTIAL", re.I)
_KEEP_ENV = {"OPENAI_API_KEY", "CODEX_API_KEY"}


def codex_env() -> dict:
    return {k: v for k, v in os.environ.items() if k in _KEEP_ENV or not _SECRET_ENV.search(k)}


class AppServer:
    def __init__(self) -> None:
        exe = CODEX if os.path.exists(CODEX) else "codex"
        self.p = subprocess.Popen([exe, "app-server"], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  env=codex_env())
        self.buf = b""
        self.nid = 0
        self.events: list[dict] = []

    def _send(self, obj: dict) -> None:
        self.p.stdin.write((json.dumps(obj) + "\n").encode())
        self.p.stdin.flush()

    def _read(self, timeout: float) -> dict | None:
        end = time.time() + timeout
        while time.time() < end:
            if b"\n" in self.buf:
                line, self.buf = self.buf.split(b"\n", 1)
                if line.strip():
                    return json.loads(line)
                continue
            r, _, _ = select.select([self.p.stdout], [], [], 0.5)
            if r:
                chunk = os.read(self.p.stdout.fileno(), 1 << 20)
                if not chunk:
                    raise RuntimeError("codex app-server beendet")
                self.buf += chunk
        return None

    def call(self, method: str, params: dict, timeout: float = 30) -> dict:
        self.nid += 1
        rid = self.nid
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        end = time.time() + timeout
        while time.time() < end:
            m = self._read(end - time.time())
            if m is None:
                break
            if m.get("id") == rid and "method" not in m:
                if "error" in m:
                    raise RuntimeError(f"{method}: {m['error']}")
                return m.get("result") or {}
            if "method" in m:
                if "id" in m:  # Server-Request (z. B. Approval) -> ablehnen, headless
                    self._send({"jsonrpc": "2.0", "id": m["id"], "result": {"decision": "decline"}})
                else:
                    self.events.append(m)
        raise TimeoutError(method)

    def notify(self, method: str) -> None:
        self._send({"jsonrpc": "2.0", "method": method})

    def wait_turn(self, thread_id: str, timeout: float) -> tuple[str, str]:
        """Sammelt agentMessage-Items bis turn/completed. -> (text, status)"""
        texts: list[str] = []
        end = time.time() + timeout
        pending = self.events
        self.events = []
        while time.time() < end:
            m = pending.pop(0) if pending else self._read(end - time.time())
            if m is None:
                break
            if "id" in m and "method" in m:
                self._send({"jsonrpc": "2.0", "id": m["id"], "result": {"decision": "decline"}})
                continue
            meth = m.get("method", "")
            prm = m.get("params") or {}
            if prm.get("threadId") not in (None, thread_id):
                continue
            if meth == "item/completed":
                item = prm.get("item") or {}
                if item.get("type") == "agentMessage" and item.get("text"):
                    texts.append(item["text"])
            elif meth == "turn/completed":
                turn = prm.get("turn") or {}
                return "\n\n".join(texts), str(turn.get("status", "completed"))
        return "\n\n".join(texts), "timeout"

    def close(self) -> None:
        try:
            self.p.kill()
        except Exception:
            pass


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def to_codex(msg: str, thread: str, cwd: str, timeout: float, sandbox: str = "read-only") -> int:
    srv = AppServer()
    try:
        srv.call("initialize", {"clientInfo": {"name": "claude_agent_msg", "title": None,
                                               "version": "1.0"}})
        srv.notify("initialized")
        threads = _load(THREADS)
        tid = threads.get(thread)
        # workspace-write erlaubt Schreiben NUR im cwd (Staging), nie in ~/.claude
        common = {"cwd": cwd, "approvalPolicy": "never", "sandbox": sandbox,
                  "developerInstructions": PARTNER_INSTRUCTIONS}
        if tid:
            try:
                srv.call("thread/resume", {"threadId": tid, "excludeTurns": True, **common})
            except Exception as e:
                print(f"[agent_msg] Thread {thread} nicht fortsetzbar ({e}) - lege neu an",
                      file=sys.stderr)
                tid = None
        if not tid:
            res = srv.call("thread/start", common)
            tid = (res.get("thread") or {}).get("id") or res.get("threadId")
            if not tid:
                raise RuntimeError(f"thread/start ohne id: {res}")
            try:
                srv.call("thread/name/set", {"threadId": tid, "name": thread})
            except Exception:
                pass
            threads[thread] = tid
            _save(THREADS, threads)
        srv.call("turn/start", {"threadId": tid,
                                "input": [{"type": "text", "text": f"[Nachricht von Claude]\n{msg}"}]})
        text, status = srv.wait_turn(tid, timeout)
        print(text or "(keine Antwort)")
        print(f"\n[agent_msg] thread={thread} id={tid} status={status}", file=sys.stderr)
        return 0 if status == "completed" and text else 1
    finally:
        srv.close()


def list_threads() -> int:
    srv = AppServer()
    try:
        srv.call("initialize", {"clientInfo": {"name": "claude_agent_msg", "title": None,
                                               "version": "1.0"}})
        srv.notify("initialized")
        res = srv.call("thread/list", {"limit": 20})
        named = {v: k for k, v in _load(THREADS).items()}
        for t in res.get("data", []):
            print(t.get("id"), named.get(t.get("id"), t.get("name") or ""), t.get("cwd", ""))
        if not res.get("data"):
            print("(keine Threads)")
        return 0
    finally:
        srv.close()


# ---------------------------------------------------------------- Claude-Seite
def _post(path: str, payload: dict, timeouts: tuple[float, ...] = (10, 25)) -> dict:
    # Unter Speicherdruck antwortet mcp-memory vereinzelt > 10 s (2x am 29./30.09.);
    # ein zweiter Versuch mit laengerem Timeout faengt das ab, Dauerausfall bleibt sichtbar.
    for i, t in enumerate(timeouts):
        req = urllib.request.Request(f"{_base()}{path}", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json", **_auth()},
                                     method="POST")
        try:
            with urllib.request.urlopen(req, timeout=t) as r:
                return json.loads(r.read().decode("utf-8", errors="replace"))
        except (TimeoutError, urllib.error.URLError, ConnectionError) as e:
            if i == len(timeouts) - 1:
                raise SystemExit(f"mcp-memory nicht erreichbar ({path}, {len(timeouts)} Versuche): "
                                 f"{type(e).__name__}: {e}")
            time.sleep(5)
    raise AssertionError("unreachable")


def fetch_inbox() -> list[dict]:
    d = _post("/api/search/by-tag", {"tags": ["to-claude"]})
    mems = d.get("memories")
    if mems is None:
        mems = [it.get("memory") or it for it in d.get("results", [])]
    return [m for m in mems if isinstance(m, dict)]


def targets(m: dict) -> set[str]:
    return {t[3:] for t in (m.get("tags") or []) if isinstance(t, str) and t.startswith("to:")}


def to_claude(msg: str, to: str, sender: str) -> int:
    tags = ["agent-msg", "to-claude", f"to:{slug(to)}", f"from:{sender}"]
    res = _post("/api/memories", {"content": f"[Nachricht von {sender} an Claude/{to}]\n{msg}",
                                  "tags": tags, "memory_type": "communication"})
    print(json.dumps({"stored": bool(res.get("success", True)), "tags": tags}))
    return 0


def inbox(to: str | None, limit: int) -> int:
    ms = fetch_inbox()
    if to:
        ms = [m for m in ms if targets(m) & {slug(to), "all"}]
    ms.sort(key=lambda m: m.get("created_at") or 0, reverse=True)
    for m in ms[:limit]:
        print(f"--- {m.get('created_at_iso', '')} {sorted(targets(m))}")
        print((m.get("content") or "").strip()[:1500])
    if not ms:
        print("(keine Nachrichten)")
    return 0


def notify_pending() -> int:
    """Discord-Ping fuer Nachrichten, die > 10 min von keiner Session abgeholt wurden."""
    delivered = _load(DELIVERED)
    notified = _load(NOTIFIED)
    now = time.time()
    fresh = []
    for m in fetch_inbox():
        h = m.get("content_hash") or m.get("hash") or ""
        ts = float(m.get("created_at") or 0)
        if not h or h in delivered or h in notified or not (600 < now - ts < 86400):
            continue
        fresh.append(m)
        notified[h] = now
    if fresh:
        first = (fresh[0].get("content") or "").strip().splitlines()
        body = f"{len(fresh)} Nachricht(en) von Codex warten auf eine Claude-Session. " \
               f"Ziel: {', '.join(sorted(set().union(*(targets(m) for m in fresh))))}. " \
               f"Erste: {' '.join(first[1:2])[:200]}"
        subprocess.run([str(Path.home() / ".claude" / "rc-notify.sh"), "Codex -> Claude", body],
                       check=False)
        print(body)
        _save(NOTIFIED, {k: v for k, v in notified.items() if now - v < 7 * 86400})
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Nachrichtenkanal Claude <-> Codex")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("to-codex")
    a.add_argument("message")
    a.add_argument("--thread", default="claude-partner")
    a.add_argument("--cwd", default=DEFAULT_CWD)
    a.add_argument("--timeout", type=float, default=900)
    a.add_argument("--sandbox", choices=["read-only", "workspace-write"], default="read-only",
                   help="workspace-write: Codex darf im --cwd schreiben (z. B. Staging)")
    b = sub.add_parser("to-claude")
    b.add_argument("message")
    b.add_argument("--to", default="all")
    b.add_argument("--from", dest="sender", default="codex")
    c = sub.add_parser("inbox")
    c.add_argument("--to")
    c.add_argument("--limit", type=int, default=10)
    sub.add_parser("threads")
    sub.add_parser("notify-pending")
    args = ap.parse_args()
    if args.cmd == "to-codex":
        cwd = os.path.realpath(os.path.expanduser(args.cwd))
        if args.sandbox != "read-only":
            # S11 (E1 2026-10-21): Sperrliste lebt in codex_call.py. Scheitert der Import,
            # bleibt schreibend gesperrt (fail-closed).
            try:
                from codex_call import s11_write_block
                why = s11_write_block(args.cwd)
            except Exception as e:
                why = (f"ABGELEHNT (2) S11: Sperrlisten-Pruefung nicht ladbar ({type(e).__name__}), "
                       f"deshalb kein workspace-write.\nWeiter: --sandbox read-only, oder "
                       f"~/.claude/scripts/codex_call.py reparieren lassen (Skills-Session).")
            if why:
                print(why, file=sys.stderr)
                return 2
        return to_codex(args.message, args.thread, cwd, args.timeout, args.sandbox)
    if args.cmd == "to-claude":
        return to_claude(args.message, args.to, args.sender)
    if args.cmd == "inbox":
        return inbox(args.to, args.limit)
    if args.cmd == "threads":
        return list_threads()
    return notify_pending()


if __name__ == "__main__":
    sys.exit(main())
