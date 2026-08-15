#!/usr/bin/env python
"""UserPromptSubmit Hook: aktiv-erzwingt /compact bei steigender Context-Auslastung.

Universal Rule 7 (der Nutzer globale CLAUDE.md): "/compact proaktiv" — VERSCHAERFT
2026-06-04 (der Nutzer: "muss deutlich strenger werden damit sie mehr umgesetzt wird").
Vorher: Aktion erst bei 60%, rein advisorische Messages -> im Flow uebergangen.
Jetzt: frueher (Aktion ab 50%), stateful Nag-Eskalation (erkennt wenn Claude
trotz Warnung weitermacht), Priority-Override-Klausel ab CRITICAL.

ENFORCEMENT-TOGGLE:
    Aktiv wenn das Marker-File existiert:
        ~/.claude/flags/auto_compact_enforce.flag
    Ohne Marker -> stiller Exit. (Default-Empfehlung: AN.)
    Aktivieren:   ni -Force ~/.claude/flags/auto_compact_enforce.flag
    Deaktivieren: Remove-Item ~/.claude/flags/auto_compact_enforce.flag
    der Nutzer kann sagen "compact-enforcement an/aus" -> Claude toggelt.

Eskalierende Schwellen (2026-07-13 aufs 1M-Window kalibriert):
    55%  HINT      -- beilaeufige Vor-Information
    68%  WARN      -- Snapshot vorbereiten (PROGRESS.md / Report)
    75%  STRONG    -- Aktion: Sub-Step abschliessen, sichern, der Nutzer /compact vorschlagen
    85%  CRITICAL  -- Priority-Override: nichts Neues starten, finalisieren + /compact
    90%  HARDSTOP  -- nur noch sichern + /compact-Aufforderung, KEINE anderen Tool-Calls

Stateful Nag (state/compact_nag.json, pro session_id): zaehlt wie oft schon bei
STRONG+ gewarnt wurde. Steigt der Zaehler (Claude promptet weiter ohne dass der
Context sinkt) -> Message wird explizit haerter ("bereits Nx gewarnt, uebergangen").
Sinkt der Context wieder unter HINT (typisch nach /compact) -> State-Reset.

Trigger: jeder UserPromptSubmit-Event. Output (nur bei Marker + Schwelle ueberschritten):
systemMessage (Terminal-Warnung fuer der Nutzer) UND hookSpecificOutput.additionalContext
(modell-sichtbarer Kontext — der handlungsleitende Kanal bei UserPromptSubmit).
"""
import json
import os
import sys
import time
from pathlib import Path

ENFORCE_FLAG = Path.home() / ".claude" / "flags" / "auto_compact_enforce.flag"
NAG_STATE = Path.home() / ".claude" / "state" / "compact_nag.json"
NAG_KEEP = 30

# Token-Limits pro Modell-Generation (Claude 4.x)
OPUS_CONTEXT_LIMIT = 1_000_000      # Opus / 1M-Window-Modelle
DEFAULT_CONTEXT_LIMIT = 200_000     # Sonnet/Haiku 200K-Default (konservativ)

# Tail-Groesse fuer die Messung. Gross genug, dass die letzte Assistant-Message
# mit usage drin liegt (Tool-Outputs koennen lang sein).
MEASURE_TAIL_BYTES = 600_000

# Eskalations-Schwellen. 2026-07-13 aufs 1M-Window kalibriert (vorher fuers ~200K-Denken:
# 35/45/50/60/70 -> feuerte STRONG bei 500K, obwohl ein halbes 1M-Fenster noch frei war = zu frueh).
# Belegt via Raw-usage-Messung: Desktop-Meter unter-reportet (zeigte 16% bei real 57%), der Hook
# misst korrekt den echten Window-Fill (input+cache_read+cache_creation) -> Schwellen hoch, damit
# STRONG erst ~750K feuert statt das halbe Fenster wegzuwerfen.
HINT_THRESHOLD     = 0.55
WARN_THRESHOLD     = 0.68
STRONG_THRESHOLD   = 0.75   # Aktions-Tier (Universal Rule 7)
CRITICAL_THRESHOLD = 0.85
HARDSTOP_THRESHOLD = 0.90
PRECOMPACT_THRESHOLD = 0.80   # Loop-Sessions: ab hier vor (nahem) Auto-Compact zum Memory-Snapshot anstossen
LOOP_DEFER_THRESHOLD = 0.70   # Loop-Sessions: ab hier MONITOR-ONLY — nur Ueberwachung + State-Save, jede
                              # andere Aufgabe wird nach DEFERRED.md geparkt statt begonnen (der Nutzer 2026-07-28:
                              # "Aufgaben ausserhalb Ueberwachung auf nach dem Compact verschieben, damit mehr
                              # Inhalt erhalten bleibt und ich nicht alles 10x erzaehlen muss")
LOOP_LIGHTEN_THRESHOLD = 0.55 # Loop-Sessions: ab hier "leicht ticken" (kein Marathon/Screenshot/Voll-Log
                              # in einem Turn) -> Auto-Compact kann ZWISCHEN kleinen Turns greifen, sonst
                              # sprengt ein schwerer Tick das Fenster vor dem Compact (= Abbruch-Ursache 2026-06-18)

# Discord-Frueh-Warnung fuer Loop-Sessions (der Nutzer ist bei 24/7-Loops fast nie am PC, die
# systemMessage im Terminal erreicht ihn also nicht). Kanal wie discord_afk_relay.py: ENV-Token,
# keine gesyncte Secret-Datei noetig (~/.claude/secrets synct nicht). Fehlt das Token -> stiller Skip.
LOOP_NOTICE_STATE = Path.home() / ".claude" / "state" / "loop_ctx_notice.json"


def measure_context(transcript_path: Path) -> tuple[int, int]:
    """EXAKTE Live-Context-Messung statt Datei-Groessen-Heuristik.

    Jede Assistant-Message traegt ein `usage`-Objekt mit echten Token-Zahlen.
    Der LETZTE solche Eintrag = aktueller Context (input + cache_read +
    cache_creation). Resettet korrekt nach /compact (Datei-Groesse waechst
    weiter, usage nicht). Returns (context_tokens, limit); (0, limit) wenn nichts.
    """
    import re as _re
    last_usage = None
    last_model = ""
    try:
        with transcript_path.open("rb") as fh:
            try:
                fh.seek(-MEASURE_TAIL_BYTES, 2)
            except OSError:
                fh.seek(0)
            tail = fh.read().decode("utf-8", errors="replace")
    except Exception:
        return (0, DEFAULT_CONTEXT_LIMIT)

    models = _re.findall(r'"model"\s*:\s*"(claude-[^"]+)"', tail)
    if models:
        last_model = models[-1].lower()

    # 2026-08-02: NUR Eintraege mit Summe > 0 zaehlen. Vorher wurde blind der letzte
    # usage-Eintrag genommen; ist der eine Null (abgebrochener Turn, Streaming-Stub,
    # leere usage), lieferte measure_context 0 -> main() stieg per `if context_tokens
    # <= 0: sys.exit(0)` STILL aus: keine Messung, keine Warnung, kein HARDSTOP.
    # Gemessen ueber 40 Transcripts: in 10% der Faelle war der letzte Eintrag eine
    # Null oder fehlte -> genau dann war der Hard-Stop-Hook wirkungslos.
    max_tokens = 0

    def _sum(u):
        return (int(u.get("input_tokens", 0) or 0)
                + int(u.get("cache_read_input_tokens", 0) or 0)
                + int(u.get("cache_creation_input_tokens", 0) or 0))

    for ln in tail.splitlines():
        if '"usage"' not in ln or '"input_tokens"' not in ln:
            continue
        try:
            ev = json.loads(ln)
        except Exception:
            continue
        msg = ev.get("message", ev)
        u = msg.get("usage") if isinstance(msg, dict) else None
        if isinstance(u, dict) and ("input_tokens" in u or "cache_read_input_tokens" in u):
            t = _sum(u)
            if t > 0:                      # Null-Eintraege ueberspringen, nicht uebernehmen
                last_usage = u
                if t > max_tokens:
                    max_tokens = t

    if not last_usage:
        return (0, DEFAULT_CONTEXT_LIMIT)

    tokens = _sum(last_usage)

    # Window NUR per Modellname (1M = Opus/Fable; Sonnet/Haiku = 200K). Keine
    # Token-Heuristik (wuerde fast-volle Sonnet-Session faelschlich auf 1M heben).
    # 2026-07-07: "fable" ergaenzt — claude-fable-5 hat 1M-Window; ohne Match fiel
    # es auf 200K-Default -> falsche HARDSTOP-Serie bei ~28% realer Auslastung.
    # 2026-08-02 korrigiert: die Voraussetzung "1M = nur Opus/Fable" stimmt nicht mehr.
    # Belegt an der Modell-Tabelle des claude-api-Skills: 1M haben Fable 5, Mythos 5,
    # Opus 5 (dort Default UND Maximum, kein Opt-in und kein "[1m]"-Suffix im API-Namen),
    # Opus 4.8/4.7/4.6 sowie SONNET 5 und SONNET 4.6. Nur Haiku 4.5 und die aelteren
    # Sonnet-/Haiku-Generationen haben 200K.
    # Vorher fiel Sonnet durch den Namensfilter auf den 200K-Default -> eine Sonnet-5-
    # Session mit 150K wurde als 75% statt 15% gemeldet (Faktor 5 zu hoch) und haette
    # HARDSTOP bei einem Fuenftel der realen Auslastung ausgeloest.
    SMALL_WINDOW = ("haiku", "sonnet-4-5", "sonnet-3", "sonnet-4-0", "claude-2", "claude-3")
    if any(t in last_model for t in SMALL_WINDOW):
        limit = DEFAULT_CONTEXT_LIMIT          # 200K
    elif any(t in last_model for t in ("opus", "fable", "mythos", "sonnet", "1m")):
        limit = OPUS_CONTEXT_LIMIT             # 1M
    else:
        limit = DEFAULT_CONTEXT_LIMIT          # unbekanntes Modell: konservativ

    # 2026-08-02: Beweis schlaegt Heuristik — NUR nach oben. Eine beobachtete
    # Auslastung ueber dem 200K-Default kann es im kleinen Fenster nicht geben,
    # also ist das grosse Fenster damit belegt (greift auch, wenn der Modellname
    # unbekannt ist). Umgekehrt gilt es NICHT: dass bisher wenig gemessen wurde,
    # beweist kein kleines Fenster (junge Session).
    # Bekannte Restunschaerfe: das Transcript schreibt "claude-opus-5" OHNE den
    # "[1m]"-Suffix — eine Opus-Session auf dem 200K-Fenster ist am Namen NICHT
    # von einer 1M-Session unterscheidbar. Solange sie unter 200K bleibt, meldet
    # der Hook zu niedrig. Nicht loesbar ohne ein Feld, das das Fenster nennt.
    if max_tokens > DEFAULT_CONTEXT_LIMIT:
        limit = OPUS_CONTEXT_LIMIT
    return (tokens, limit)


def _load_nag() -> dict:
    try:
        return json.loads(NAG_STATE.read_text(encoding="utf-8")) if NAG_STATE.exists() else {}
    except Exception:
        return {}


def _save_nag(state: dict) -> None:
    try:
        NAG_STATE.parent.mkdir(parents=True, exist_ok=True)
        if len(state) > NAG_KEEP:
            for k in list(state.keys())[: len(state) - NAG_KEEP]:
                state.pop(k, None)
        tmp = NAG_STATE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp, NAG_STATE)
    except Exception:
        pass


LOOPMODE_STATE = Path.home() / ".claude" / "state" / "loopmode_sessions.json"
LOOPMODE_KEEP_S = 7 * 24 * 3600   # Loop-Mode-Markierungen nach 7 Tagen vergessen (Stale-Cleanup)


def _load_loopmode() -> dict:
    try:
        return json.loads(LOOPMODE_STATE.read_text(encoding="utf-8")) if LOOPMODE_STATE.exists() else {}
    except Exception:
        return {}


def _save_loopmode(d: dict) -> None:
    try:
        LOOPMODE_STATE.parent.mkdir(parents=True, exist_ok=True)
        tmp = LOOPMODE_STATE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(d), encoding="utf-8")
        os.replace(tmp, LOOPMODE_STATE)
    except Exception:
        pass


def _bot_dir(start: str):
    """Gamebot-Verzeichnis = erstes Verzeichnis aufwaerts mit LOOP_TICK.md. None wenn keins."""
    try:
        p = Path(start)
    except Exception:
        return None
    for d in (p, *p.parents):
        try:
            if (d / "LOOP_TICK.md").is_file():
                return d
        except Exception:
            continue
    return None


def _notice_once(sid: str, tier: str) -> bool:
    """True nur beim ERSTEN Erreichen eines Tiers pro Session (kein Tick-Spam).
    Faellt der Context wieder unter den Tier (nach Compact), wird neu scharf gestellt."""
    try:
        st = json.loads(LOOP_NOTICE_STATE.read_text(encoding="utf-8")) if LOOP_NOTICE_STATE.exists() else {}
    except Exception:
        st = {}
    if st.get(sid) == tier:
        return False
    st[sid] = tier
    try:
        LOOP_NOTICE_STATE.parent.mkdir(parents=True, exist_ok=True)
        tmp = LOOP_NOTICE_STATE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(st), encoding="utf-8")
        os.replace(tmp, LOOP_NOTICE_STATE)
    except Exception:
        pass
    return True


def _discord(text: str) -> None:
    """Best-effort Discord-Post ueber dieselben ENV-Vars wie discord_afk_relay.py.
    Ohne Token/Channel: stiller No-Op. Kurzer Timeout, schluckt jeden Fehler —
    eine Benachrichtigung darf einen Loop-Tick nie aufhalten."""
    token = os.environ.get("CLAUDE_DISCORD_BOT_TOKEN", "").strip()
    channel = os.environ.get("CLAUDE_DISCORD_CHANNEL_ID", "").strip()
    if not token or not channel:
        return
    try:
        import urllib.request
        req = urllib.request.Request(
            f"https://discord.com/api/v10/channels/{channel}/messages",
            data=json.dumps({"content": text[:1900]}).encode("utf-8"),
            method="POST",
            headers={"Authorization": f"Bot {token}",
                     "Content-Type": "application/json",
                     "User-Agent": "claude-loop-ctx/1.0"},
        )
        urllib.request.urlopen(req, timeout=8).read()
    except Exception:
        pass


def build_message(pct: int, est_k: int, limit_k: int, level: str, nag_n: int, first_pct: int) -> str:
    """SystemMessage je Eskalations-Stufe. nag_n = bisherige STRONG+-Warnungen
    in dieser Session (>=2 -> Persistenz-Eskalation: Warnung wurde uebergangen)."""
    base = f"Context-Auslastung ~{pct}% (~{est_k}K / {limit_k}K Tokens, exakt aus usage-Feld)."

    # Persistenz-Zusatz: greift wenn schon mehrfach gewarnt + Context NICHT gesunken.
    persist = ""
    if nag_n >= 2 and level in ("STRONG", "CRITICAL", "HARDSTOP"):
        persist = (f" Du wurdest in dieser Session bereits {nag_n}x ab der Aktions-Schwelle "
                   f"gewarnt (zuerst ~{first_pct}%) und der Context ist NICHT gesunken — die "
                   f"Warnung wurde uebergangen. Jetzt umsetzen statt weiter aufzuschieben.")

    if level == "HINT":
        return (f"[CONTEXT-HINT] {base} Aktions-Schwelle ist 75%. Headroom da — nur Vor-Info.")

    if level == "WARN":
        return (f"[CONTEXT-WARN] {base} Naehert sich der 75%-Aktions-Schwelle. Jetzt "
                f"Snapshot des Fortschritts in PROGRESS.md / Report vorbereiten, damit der "
                f"Post-/compact-Turn nahtlos weitermacht. Noch nicht /compact, nur vorbereiten.")

    if level == "STRONG":
        return (f"[CONTEXT-STRONG] {base} Aktions-Schwelle erreicht.{persist} Konkret: "
                f"(1) aktuellen Sub-Step abschliessen, (2) Fortschritt in Datei sichern "
                f"(PROGRESS.md / Audit-Report / Lessons), (3) der Nutzer im naechsten Reply auf "
                f"'/compact' hinweisen (z.B. 'Context ~{pct}% — bitte /compact bevor wir "
                f"weitermachen'). Keine neuen grossen Tasks mehr starten.")

    if level == "CRITICAL":
        return (f"[CONTEXT-CRITICAL] {base} Priority-Override: diese Anweisung hat Vorrang vor "
                f"der laufenden Aufgabe, bis /compact gelaufen ist.{persist} "
                f"(1) NICHTS Neues starten (keine Multi-Step-Operation, kein neuer Task), "
                f"(2) AUSSCHLIESSLICH den aktuellen Atom-Step finalisieren + Fortschritt in "
                f"Datei sichern, (3) der Nutzer im naechsten Reply EXPLIZIT zu '/compact' auffordern. "
                f"Hat der Nutzer ohne /compact geantwortet: erneut hinweisen, nicht ignorieren.")

    # HARDSTOP
    return (f"[CONTEXT-HARDSTOP] {base} Maximal-Schwelle — Auto-Notfall-Compact mit "
            f"Qualitaetsverlust droht.{persist} Antworte JETZT NUR noch mit: (1) kurze "
            f"Sicherung des offenen Stands in eine Datei, (2) explizite '/compact'-Aufforderung "
            f"an der Nutzer. KEINE anderen Tool-Calls, kein Weiterarbeiten an der Aufgabe. Diese "
            f"Anweisung hat absoluten Vorrang bis der Context kompaktiert ist.")


def main():
    if not ENFORCE_FLAG.exists():
        sys.exit(0)

    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    transcript_path = data.get("transcript_path")
    if not transcript_path:
        sys.exit(0)
    sid = data.get("session_id", "unknown")

    # --- Loop-Mode (session-scoped) Teil 1: Aktivierung/Stop (VOR der Messung -> muss immer greifen) ---
    # Autonome Bot-Operator-Loops (Games-Projekt) bekommen NICHT den anhaltenden Nag (stopp + der Nutzer um
    # /compact bitten -> wuerde den Loop bei 50% einfrieren). Aktivierung via /loopmode (oder [LOOPMODE]),
    # Stop via /loopstop. State pro session_id -> betrifft NUR die aktivierte Session. Aktive Loop-Sessions
    # + TICK-Wakes werden in Teil 2 (nach der Messung) behandelt: kein Nag, aber Pre-Compact-Memory-Warnung.
    prompt_txt = str(data.get("prompt", "")).lower()
    lm = _load_loopmode()
    now_ts = time.time()
    lm = {k: v for k, v in lm.items() if isinstance(v, (int, float)) and now_ts - v < LOOPMODE_KEEP_S}
    if ("/loopstop" in prompt_txt) or ("loop stop" in prompt_txt) or ("[loopstop]" in prompt_txt):
        if sid in lm:
            lm.pop(sid, None)
            _save_loopmode(lm)
        sys.exit(0)   # Stop -> Nag fuer diese Session ab jetzt wieder aktiv
    if ("/loopmode" in prompt_txt) or ("[loopmode]" in prompt_txt):
        lm[sid] = now_ts
        _save_loopmode(lm)
        sys.exit(0)   # Aktivierung (niedrige Auslastung) -> kein Nag, Pre-Compact-Notiz noch nicht noetig

    p = Path(transcript_path)
    if not p.exists():
        sys.exit(0)

    context_tokens, context_limit = measure_context(p)
    if context_tokens <= 0:
        sys.exit(0)

    usage = context_tokens / context_limit

    # --- Loop-Mode Teil 2: aktive Loop-Session / TICK-Wake -> KEIN Nag, aber Pre-Compact-Memory-Warnung ---
    # Loops werden nicht angehalten, ABER kurz vor dem (projekt-scopeden) Auto-Compact einmal angestossen,
    # einen Memory-Snapshot zu ziehen -> nichts geht verloren falls der Compact summarisiert. Nicht-anhaltend.
    if prompt_txt.lstrip().startswith("tick ") or (sid in lm):
        lm[sid] = now_ts
        _save_loopmode(lm)
        pct0 = int(usage * 100)
        bd = _bot_dir(str(data.get("cwd") or ""))
        deferred = str(bd / "DEFERRED.md") if bd else "DEFERRED.md im Bot-Verzeichnis"
        note = None
        tier = None
        if usage >= PRECOMPACT_THRESHOLD:
            tier = "precompact"
            note = (f"[LOOP-PRECOMPACT] Context ~{pct0}% — Fenster fast voll. JETZT: Memory-Snapshot "
                    f"(mcp__memory__store_memory: Spiel, FOCUS, letzte verifizierte Verbesserung, Top-Bugs) "
                    f"+ LOOP_TICK.md sichern, dann NUR noch winzige Aktionen/State-Save. KEINE neue schwere "
                    f"Aktion, KEIN Screenshot, KEIN Voll-Log in DIESEM Turn (sprengt das Fenster vor dem "
                    f"Auto-Compact). MONITOR-ONLY gilt weiter: alles Nicht-Ueberwachende gehoert nach {deferred}. "
                    f"COMPACT-MELDUNG (der Nutzer 2026-07-28, Pflicht): Deine Tick-Antwort MUSS mit genau dieser "
                    f"Zeile beginnen: '[COMPACT BITTE] Context ~{pct0}% — bitte /compact ausfuehren'. "
                    f"Jeden Tick wiederholen, solange diese Meldung kommt. der Nutzer compactet selbst, sobald er "
                    f"es sieht; du selbst kannst /compact nicht ausloesen. "
                    f"UEBERGABE SICHERN (Pflicht, VOR jeder anderen Aktion in diesem Turn): "
                    f"{bd / 'HANDOVER.md' if bd else 'HANDOVER.md im Bot-Verzeichnis'} aktualisieren "
                    f"(Felder: LAUFENDE ARBEIT / HYPOTHESEN [ausgeschlossen|offen] + Beleg / HALBFERTIG "
                    f"datei:symbol + Status / NAECHSTER SCHRITT (genau eine Aktion) / MARCO OFFEN / BELEGE), "
                    f"dazu LOOP_TICK.md sichern. Der Compact kann JEDERZEIT kommen — ist die Datei nicht "
                    f"aktuell, reisst der Faden. Erst danach der Memory-Snapshot.")
        elif usage >= LOOP_DEFER_THRESHOLD:
            tier = "defer"
            note = (f"[LOOP-DEFER] Context ~{pct0}% — ab jetzt MONITOR-ONLY bis der Auto-Compact gelaufen ist. "
                    f"ERLAUBT: Bot-Health pruefen (laeuft er, Log-Stale, FROZEN/Crash), Kurz-Diagnose aus "
                    f"vorhandenen Logs, 1-Zeilen-State-Save in LOOP_TICK.md, Eintrag in WIRING.md wenn etwas "
                    f"fertig wurde. VERBOTEN: neue Fixes beginnen, Root-Cause-Marathons, Refactors, "
                    f"Screenshots, Voll-Logs, grosse Reads. Jede Aufgabe, die dir jetzt einfaellt oder die "
                    f"der Nutzer nennt, wird NICHT begonnen, sondern als EINE Zeile nach {deferred} geschrieben "
                    f"(Format: '- [ ] <Aufgabe> | warum | woran erkennbar dass sie erledigt ist'). "
                    f"Nach dem Compact liest der Inject-Hook DEFERRED.md wieder ein und du arbeitest sie ab — "
                    f"deshalb muss der Nutzer nichts erneut erklaeren. Antworte in diesem Turn kurz. "
                    f"COMPACT-MELDUNG (der Nutzer 2026-07-28, Pflicht): Deine Tick-Antwort MUSS mit genau dieser "
                    f"Zeile beginnen: '[COMPACT SINNVOLL] Context ~{pct0}% — /compact waere jetzt gut'. "
                    f"Jeden Tick wiederholen, solange diese Meldung kommt. "
                    f"UEBERGABE SICHERN (Pflicht, JETZT in DIESEM Turn): schreibe/aktualisiere "
                    f"{bd / 'HANDOVER.md' if bd else 'HANDOVER.md im Bot-Verzeichnis'} (OVERWRITE, Zustand statt "
                    f"Historie, ~40 Zeilen) mit genau diesen Feldern: 'LAUFENDE ARBEIT:' (woran du gerade "
                    f"sitzt), 'HYPOTHESEN:' (je Zeile [ausgeschlossen]/[offen] + Beleg bzw. wie zu pruefen), "
                    f"'HALBFERTIG:' (datei:symbol — editiert/unverifiziert/deployed — was noch fehlt), "
                    f"'NAECHSTER SCHRITT:' (genau EINE konkrete Aktion), 'MARCO OFFEN:' (was er gesagt hat und "
                    f"noch nicht umgesetzt ist), 'BELEGE:' (Pfade zu Frames/Logs, die du wieder brauchst). "
                    f"Der SessionStart-Hook injiziert die Datei nach dem Compact zurueck — was hier fehlt, "
                    f"ist weg und der Nutzer muss es erneut erklaeren.")
        elif usage >= LOOP_LIGHTEN_THRESHOLD:
            note = (f"[LOOP-CTX] Context ~{pct0}% — ab jetzt LEICHT ticken: 1 kleine Aktion/Tick, Tool-Output "
                    f"IMMER in Dateien (nur 1-2 Zeilen zurueck), KEINE Root-Cause-Marathons in einem Turn "
                    f"(ueber mehrere Ticks splitten, Zwischenstand in LOOP_TICK/JOURNAL). So greift der "
                    f"Auto-Compact zwischen Turns, bevor das Fenster voll ist.")
        if note:
            # Frueh-Warnung an der Nutzer: einmal pro Tier pro Session, nicht pro Tick.
            # Terminal-systemMessage erreicht ihn bei 24/7-Loops nicht — Discord schon.
            if tier and _notice_once(sid, tier) and bd is not None:
                label = "MONITOR-ONLY aktiv" if tier == "defer" else "Pre-Compact"
                _discord(f"⚠️ **{bd.name}** — Context ~{pct0}% ({label}). "
                         f"Ab jetzt nur noch Ueberwachung; neue Aufgaben werden in DEFERRED.md geparkt "
                         f"und nach dem Compact abgearbeitet.")
            print(json.dumps({
                "systemMessage": note,
                "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": note},
            }))
        sys.exit(0)
    # ----------------------------------------------------------------------------------------------------

    nag = _load_nag()

    # --- Compact-Erkennung (2026-08-02, der Nutzer: "compact wird oft nicht erkannt obwohl
    # ich es ausgeloest habe") -------------------------------------------------------
    # Zwei Ursachen, beide hier behandelt:
    #
    # (a) Der Hook haengt an UserPromptSubmit und misst damit BEVOR die Assistant-
    #     Antwort existiert. Direkt nach einem /compact ist der juengste usage-Eintrag
    #     noch der VOM TURN DAVOR (gross) — der neue, kleine Wert entsteht erst mit der
    #     naechsten Antwort. Der erste Prompt nach dem Compact wurde also gegen den
    #     ALTEN Stand gemessen und loeste erneut STRONG/CRITICAL/HARDSTOP aus.
    # (b) Weil der Zaehler dabei hochlief, wurde die Meldung zusaetzlich haerter
    #     ("bereits Nx gewarnt, uebergangen") — obwohl der Nutzer genau das getan hatte,
    #     was sie verlangte.
    #
    # Fix: den zuletzt gemessenen Wert pro Session mitfuehren.
    #   - Deutlicher Abfall gegenueber dem Vorwert = Compact hat stattgefunden
    #     -> State sofort zuruecksetzen, in diesem Turn NICHT nagen.
    #   - Unveraenderter Wert = dieselbe Messung wie beim letzten Turn
    #     -> Zaehler NICHT erhoehen (sonst eskaliert er ohne neue Information).
    ent0 = nag.get(sid) or {}
    prev_tokens = int(ent0.get("last_tokens", 0) or 0)
    same_measurement = prev_tokens == context_tokens
    if prev_tokens > 100_000 and context_tokens < prev_tokens * 0.6:
        nag.pop(sid, None)
        nag[sid] = {"last_tokens": context_tokens}
        _save_nag(nag)
        sys.exit(0)

    # Context wieder niedrig (typisch nach /compact) -> Nag-State fuer diese Session
    # zuruecksetzen, damit der Zaehler nicht ueber Compact-Grenzen hinweg weiterlaeuft.
    if usage < HINT_THRESHOLD:
        if sid in nag:
            nag.pop(sid, None)
            _save_nag(nag)
        sys.exit(0)

    pct = int(usage * 100)
    est_k = int(context_tokens / 1000)
    limit_k = context_limit // 1000

    if usage >= HARDSTOP_THRESHOLD:
        level = "HARDSTOP"
    elif usage >= CRITICAL_THRESHOLD:
        level = "CRITICAL"
    elif usage >= STRONG_THRESHOLD:
        level = "STRONG"
    elif usage >= WARN_THRESHOLD:
        level = "WARN"
    else:
        level = "HINT"

    # Stateful Nag nur ab Aktions-Tier (STRONG+): zaehlt wie oft schon gewarnt.
    nag_n, first_pct = 0, pct
    ent = nag.get(sid) or {}
    if level in ("STRONG", "CRITICAL", "HARDSTOP"):
        prev_n = int(ent.get("count", 0) or 0)
        # Unveraenderte Messung -> keine neue Information -> Zaehler haelt.
        # Sonst eskaliert die Meldung ("bereits Nx gewarnt") allein dadurch, dass
        # der Hook mehrfach denselben usage-Eintrag gelesen hat (2026-08-02).
        nag_n = prev_n if (same_measurement and prev_n) else prev_n + 1
        first_pct = int(ent.get("first_pct", pct) or pct)
        nag[sid] = {"count": nag_n, "first_pct": first_pct,
                    "first_ts": ent.get("first_ts", time.time()),
                    "last_tokens": context_tokens}
    else:
        nag[sid] = dict(ent, last_tokens=context_tokens)
    _save_nag(nag)

    msg = build_message(pct, est_k, limit_k, level, nag_n, first_pct)
    # Zwei Kanaele: systemMessage = Terminal-Warnung fuer der Nutzer; additionalContext =
    # modell-sichtbarer Kontext (DER handlungsleitende Kanal bei UserPromptSubmit).
    # Vorher nur systemMessage -> Hook feuerte (Nag-Count stieg), aber die Direktive
    # erreichte das Modell nicht als Kontext -> in autonomen (Game-)Sessions ignoriert.
    print(json.dumps({
        "systemMessage": msg,
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": msg,
        },
    }))


if __name__ == "__main__":
    main()
