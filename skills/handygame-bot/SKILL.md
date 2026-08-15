---
name: handygame-bot
description: 'Scaffoldt ein neues Mobile-Game-Automation-Projekt (Android-Emulator/ADB, OpenCV-Screen-Detection, FSM-Bot) nach der Nutzer-Pattern — robuste Module für Device-Connect, Screen-Capture, Template-Match+OCR, Tap/Swipe mit Human-Jitter, State-Machine, Watchdog/Safe-Stop. Vorverdrahtet mit uiautomator2+adbutils+opencv. Use when "Handygame-Bot bauen", "Mobile-Game automatisieren", "Farming-Bot", "Idle-Game-Bot", "Auto-Battle", "Android-Bot scaffold", "Spiel automatisieren", "/handygame-bot". Voice "handygame bot", "game bot bauen", "mobile bot".'
version: 1.0.0
---

# Handygame-Bot — Scaffold-Skill

> v1.0.0 | 2026-06-13 | Erzeugt ein lauffähiges, robustes Skelett für einen Mobile-Game-Automation-Bot.
> Backt die Best-Practices ein, die `game-automation-reviewer` prüft (Threshold-Gate,
> wait-for-stable, Jitter, Connection-Reuse, Watchdog, FSM, atomic State).

## Wann
User will einen Bot der ein **Android-Handygame selbst spielt** (Farming/Idle/Auto-Battle) — neu aufsetzen oder ein bestehendes Skript auf saubere Struktur heben.

## Research-First
Vor dem Schreiben von Library-Code gegen `uiautomator2`, `adbutils`, `opencv-python`, `pytesseract`, `python-statemachine` → **context7 queryen** (resolve-library-id → query-docs). Versionen driften, nicht aus Training raten.

## Phase 0 — Inputs erfragen (kurz)
Frage nur was nötig ist (1 Runde):
1. **Spiel + Package-Name** (`adb shell pm list packages | grep <name>`), z.B. `com.example.idle`.
2. **Device:** Emulator (BlueStacks/LDPlayer/Nox/Memu/AVD) oder Real-Device? ADB-Adresse (`127.0.0.1:5555` o.ä.) oder Serial.
3. **Referenz-Auflösung** (z.B. 1280×720) — Templates werden darauf normalisiert.
4. **Ziel-Tasks** (welche Loops: Daily-Claim, Farm-Stage, Upgrade, Box-Open …) → bestimmen die FSM-States.
5. **Projekt-Pfad** (default: `~/projects/<spielname>_bot` — auf netcup `~/projects`, PC-seitig der entsprechende Syncthing-`projekte`-Ordner; Bot-RUNTIME mit Emulator/ADB ist Windows-lokal).

## Phase 1 — Projektstruktur anlegen
```
<spiel>_bot/
├─ bot/
│  ├─ __init__.py
│  ├─ device.py        # ADB-Connect (einmal, wiederverwendet) + Reconnect-Recovery
│  ├─ capture.py       # Screencap + wait-for-stable-screen
│  ├─ vision.py        # Template-Match (Threshold-Gate, Multi-Scale, Cache) + OCR
│  ├─ input.py         # Tap/Swipe mit Human-Jitter (Offset + Delay)
│  ├─ states.py        # FSM (python-statemachine): States + Transitions + Guards
│  ├─ watchdog.py      # Heartbeat, Kill-Switch-Flag, max-runtime
│  └─ config.py        # ENV-Load, Pfade, Thresholds (atomic state-write)
├─ anchors/            # Template-PNGs, benannt nach Screen+Element (dokumentiert)
│  └─ README.md        # welcher Crop = welcher Screen @ welcher Auflösung
├─ data/               # Screenshots-Dumps (Recovery/Debug), progress.json (atomic)
├─ logs/
├─ main.py             # Entry: connect → FSM-Loop unter Watchdog
├─ requirements.txt
├─ .env.example        # nie echte Creds; ENV + KeePass
├─ .gitignore          # .env, data/, logs/, __pycache__
└─ README.md
```

## Phase 2 — Kern-Module (robuste Templates)

Schreibe die Module mit diesen Patterns. Identifier Englisch, Doku/Kommentar Deutsch, `logging` statt print, `pathlib.Path`, UTF-8.

### bot/device.py — Connection einmal, mit Recovery
```python
"""ADB-Device-Anbindung: einmal verbinden, wiederverwenden, bei Disconnect reconnecten."""
from __future__ import annotations
import logging, time
import uiautomator2 as u2

logger = logging.getLogger(__name__)

class Device:
    def __init__(self, addr: str):
        self._addr = addr
        self._d: u2.Device | None = None

    @property
    def d(self) -> u2.Device:
        if self._d is None:
            self.connect()
        return self._d  # type: ignore[return-value]

    def connect(self) -> None:
        logger.info("Connecting to %s", self._addr)
        self._d = u2.connect(self._addr)  # einmalig; NICHT pro Loop
        logger.info("Connected: %s", self._d.info.get("productName", "?"))

    def ensure_alive(self) -> None:
        """Bei Disconnect (Emulator-Hänger) reconnecten statt crashen."""
        try:
            _ = self.d.info  # billiger Ping
        except Exception as e:  # noqa: BLE001
            logger.warning("Device tot (%s) — reconnect", e)
            self._d = None
            for attempt in range(5):
                try:
                    self.connect(); return
                except Exception as ex:  # noqa: BLE001
                    logger.warning("reconnect %d/5 fehlgeschlagen: %s", attempt + 1, ex)
                    time.sleep(min(2 ** attempt, 30))
            raise RuntimeError("Device nicht wiederherstellbar")
```

### bot/capture.py — Screencap + wait-for-stable
```python
"""Screenshot + Warten bis der Screen still steht (keine Animation mehr)."""
from __future__ import annotations
import time
import numpy as np

def grab(device) -> np.ndarray:
    """BGR-Frame (OpenCV-Konvention). u2.screenshot(format='opencv') liefert BGR."""
    return device.d.screenshot(format="opencv")

def wait_stable(device, *, settle: float = 0.4, timeout: float = 8.0,
                diff_thresh: float = 2.0, poll: float = 0.2) -> np.ndarray:
    """Pollt bis zwei aufeinanderfolgende Frames ~identisch sind (mean abs diff < thresh)."""
    last = grab(device); stable_since = None; deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(poll); cur = grab(device)
        if cur.shape == last.shape and float(np.mean(np.abs(cur.astype("int16") - last.astype("int16")))) < diff_thresh:
            stable_since = stable_since or time.time()
            if time.time() - stable_since >= settle:
                return cur
        else:
            stable_since = None
        last = cur
    return last  # Timeout: letzten Frame zurück (Caller entscheidet)
```

### bot/vision.py — Match mit Threshold-Gate + Cache + OCR
```python
"""Template-Matching mit Pflicht-Threshold, Multi-Scale, Template-Cache; OCR mit Preprocessing."""
from __future__ import annotations
import logging
from functools import lru_cache
from pathlib import Path
import cv2, numpy as np

logger = logging.getLogger(__name__)
ANCHORS = Path(__file__).resolve().parent.parent / "anchors"

@lru_cache(maxsize=128)
def _template(name: str) -> np.ndarray:
    p = ANCHORS / name
    img = cv2.imread(str(p), cv2.IMREAD_COLOR)  # BGR; einmal gecacht, nicht pro Loop
    if img is None:
        raise FileNotFoundError(f"Anchor fehlt: {p}")
    return img

def find(frame: np.ndarray, anchor: str, *, threshold: float = 0.85,
         scales: tuple[float, ...] = (1.0, 0.9, 1.1)) -> tuple[int, int] | None:
    """Center-(x,y) des besten Matches ODER None wenn unter Threshold (Pflicht-Gate)."""
    tpl = _template(anchor); best = (-1.0, None)
    for s in scales:
        t = tpl if s == 1.0 else cv2.resize(tpl, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        if t.shape[0] > frame.shape[0] or t.shape[1] > frame.shape[1]:
            continue
        res = cv2.matchTemplate(frame, t, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val > best[0]:
            best = (max_val, (max_loc[0] + t.shape[1] // 2, max_loc[1] + t.shape[0] // 2))
    if best[0] < threshold:   # <-- ohne dieses Gate tappt der Bot auf Phantome
        return None
    logger.debug("match %s conf=%.3f", anchor, best[0])
    return best[1]

def visible(frame, anchor, **kw) -> bool:
    return find(frame, anchor, **kw) is not None

def read_number(frame, box: tuple[int, int, int, int]) -> int | None:
    """OCR einer Zahl in box=(x,y,w,h) mit Preprocessing + Sanity. Braucht pytesseract+Tesseract."""
    import pytesseract, re
    x, y, w, h = box
    roi = frame[y:y + h, x:x + w]
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    g = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, g = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    raw = pytesseract.image_to_string(g, config="--psm 7 -c tessedit_char_whitelist=0123456789")
    digits = re.sub(r"\D", "", raw)
    return int(digits) if digits else None  # Caller macht Range-Check
```

### bot/input.py — Human-Jitter
```python
"""Taps/Swipes mit zufälligem Offset + Delay — robust gegen Pixel-genaue UI-Drift."""
from __future__ import annotations
import logging, random, time

logger = logging.getLogger(__name__)

def tap(device, x: int, y: int, *, radius: int = 6,
        delay: tuple[float, float] = (0.15, 0.45)) -> None:
    jx = x + random.randint(-radius, radius); jy = y + random.randint(-radius, radius)
    device.d.click(jx, jy)
    logger.debug("tap (%d,%d)", jx, jy)
    time.sleep(random.uniform(*delay))

def swipe(device, x1, y1, x2, y2, *, dur: tuple[float, float] = (0.2, 0.5)) -> None:
    device.d.swipe(x1, y1, x2, y2, duration=random.uniform(*dur))
    time.sleep(random.uniform(0.2, 0.5))
```

### bot/watchdog.py — Kill-Switch + Heartbeat + Max-Runtime
```python
"""Sicheres Stoppen: Flag-File-Kill-Switch, Max-Laufzeit, Heartbeat-File."""
from __future__ import annotations
import json, os, time, logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Watchdog:
    def __init__(self, stop_flag: Path, heartbeat: Path, max_runtime_s: float = 8 * 3600):
        self.stop_flag = stop_flag; self.heartbeat = heartbeat
        self.deadline = time.time() + max_runtime_s; self.iters = 0

    def should_continue(self) -> bool:
        if self.stop_flag.exists():
            logger.info("Kill-Switch (%s) — stop", self.stop_flag); return False
        if time.time() > self.deadline:
            logger.info("Max-Runtime erreicht — stop"); return False
        return True

    def beat(self, state: str) -> None:
        self.iters += 1
        tmp = self.heartbeat.with_suffix(".tmp")
        tmp.write_text(json.dumps({"ts": time.time(), "state": state, "iters": self.iters}), encoding="utf-8")
        os.replace(tmp, self.heartbeat)  # atomic
```

### bot/states.py — FSM (python-statemachine)
```python
"""Bot-FSM: explizite States inkl. UNKNOWN-Recovery. Transitions sind Guards, keine if/elif-Wüste.

Skeleton — States/Transitions an Phase-0-Tasks anpassen. Jeder State: (1) wait_stable,
(2) Screen erkennen via vision.find, (3) Aktion, (4) Transition. Unerwarteter Screen → UNKNOWN.
"""
from statemachine import StateMachine, State

class GameBot(StateMachine):
    boot = State(initial=True)
    home = State()
    farming = State()
    unknown = State()           # Recovery-State — NIE blind weitertappen
    done = State(final=True)

    orient = boot.to(home) | unknown.to(home) | home.to(home)
    start_farm = home.to(farming)
    farm_tick = farming.to(farming)
    finish = farming.to(home) | home.to(done)
    lost = home.to(unknown) | farming.to(unknown)
```

### bot/config.py & main.py
- `config.py`: `load_dotenv`, Pfade (`ROOT/data`, `logs`, `anchors`), `STOP_FLAG = ROOT/"data"/"stop.flag"`, Thresholds. Credentials NUR aus ENV.
- `main.py`: Logging-Setup (Console+RotatingFileHandler), `Device.connect()`, `Watchdog`, dann Loop:
```python
while wd.should_continue():
    device.ensure_alive()
    frame = wait_stable(device)
    # Screen erkennen -> FSM-Event feuern; bei keinem bekannten Anker -> bot.lost() + recovery_dump(frame)
    wd.beat(bot.current_state.id)
    time.sleep(random.uniform(0.3, 0.8))
```
Recovery: bei `unknown` Screenshot nach `data/recovery_<ts>.png` dumpen, Back-Taste / Home-Anchor suchen, `orient()`.

## Phase 3 — requirements.txt (verifiziert 2026-06-13)
```
uiautomator2>=3.0      # ADB+UI, minicap/minitouch (openatx, 8k★, aktiv)
adbutils>=2.0          # pure-python ADB (Komplement)
opencv-python>=4.9     # Template-Match
numpy>=1.26
pytesseract>=0.3.10    # OCR — braucht Tesseract-Binary auf PATH
python-statemachine>=2.3
python-dotenv>=1.0
```
Versionen vor Pin via context7/PyPI gegenchecken (Drift). Tesseract separat installieren (UB-Mannheim-Build für Windows).

## Phase 4 — Dev-Loop & Anchors
- **UI-Anker finden (Claude-im-Loop):** optional MCP `mobile-next/mobile-mcp` (`npx -y @mobilenext/mobile-mcp@latest`) ODER `JuanCF/scrcpy-mcp` einrichten → Claude sieht den Live-Screen, hilft Crops für `anchors/` zu ziehen + Flows zu prototypen. **Nicht** der Runtime — der Bot läuft ohne MCP.
- **anchors/README.md** pflegen: Dateiname → Screen + Element + Referenz-Auflösung.
- **.gitignore**: `.env`, `data/`, `logs/`, `__pycache__/`, `anchors/*.png`? (Anchors meist behalten, aber keine Screenshots mit Account-Daten).

## Phase 5 — Abschluss
- README mit Start (`python main.py`) + Stop (`type nul > data\stop.flag` / `touch data/stop.flag`).
- Hinweis: **ToS/Account-Risiko liegt bei der Nutzer** — der Skill baut nur die Technik.
- Danach **`game-automation-reviewer`** über den Code laufen lassen (prüft genau die hier eingebauten Achsen).

## Constraints
- Credentials/Token NIE in Code/Chat → ENV + KeePass (secret-handling-Rule).
- `logging` statt print, `pathlib.Path`, UTF-8, atomic-write (.tmp+os.replace) für progress/heartbeat.
- Kein `while True` ohne Watchdog. Kein Template-Match ohne Threshold-Gate. Kein Tap ohne wait-stable davor.
- Library-Code gegen uiautomator2/opencv/etc.: Research-First via context7.
- Cross-Ref: Review mit Agent `game-automation-reviewer`.
