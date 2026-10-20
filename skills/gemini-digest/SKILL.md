---
name: gemini-digest
version: 1.0.0
description: |
  Offload großer Reads + Zusammenfassungen an Gemini (gemini-flash-latest, günstig,
  Riesen-Kontext) via gemini-bridge — statt teure Opus-Tokens auf große Dateien/Ordner/
  Logs zu verbrennen. Gemini liest + verdichtet, der Main-Loop bekommt nur den
  zielgerichteten Digest. Use when: "fass diese große Datei/Log/Ordner zusammen",
  "digest", "was steht in den X-tausend Zeilen", "offload read", "gemini-digest".
---

# gemini-digest — Große Reads an Gemini auslagern (Token-Spar)

Token-Spar-Hebel: große Datei-/Ordner-/Log-Reads sind der größte Opus-Token-Sink.
Statt sie selbst zu lesen, lagerst du sie an `gemini-bridge` (gemini-flash-latest,
Riesen-Kontext, ~Cent-Bruchteile) aus und arbeitest nur mit dem Digest weiter.

## Vorgehen
1. **Ziel schärfen:** WAS soll aus dem Material raus? Konkrete Frage/Extraktion, nicht
   „lies alles". Ohne klares Ziel wird der Digest unbrauchbar und du liest am Ende doch selbst.
2. **Dispatch** `gemini-bridge` (1 Call) mit: Datei-Pfade/Ordner/Glob · die konkrete
   Frage/Extraktions-Aufgabe · gewünschtes Output-Format (Bullet-Digest, Tabelle, Antwort).
   Datei-Reads im Subagent NUR via Read-Tool (kein cat/Get-Content — Security-Flag).
3. **Digest nutzen, aber kritische Fakten verifizieren:** Der Digest ist eine
   Zusammenfassung, keine Ground-Truth. Bevor du auf einer kritischen Aussage handelst
   (Code-Änderung, Löschung, Config-Edit) → die eine relevante Stelle gezielt selbst per
   Read gegenchecken. Zeilennummern/Namen aus dem Digest nie blind übernehmen.

## Wann NICHT
- Nur 1–2 kleine Dateien nötig → direkt selbst per Read (Bridge-Overhead lohnt nicht).
- Exakte Zeilen für einen Edit nötig → selbst lesen (Digest ist unscharf).
- Secret-/DSGVO-sensibles Material → NICHT an externe Modelle geben.

## Kosten (wichtig)
Gemini läuft über die API (API-Key, Prepay-Guthaben; seit 30.09. wieder alleiniger Weg, `agy` nie aus Claude). `flash` = Bruchteile eines
Cents pro Digest, Usage in `~/.claude/state/gemini_usage.jsonl` (Übersicht: `ai_usage.py`).
Tagesdeckel `GEMINI_TEXT_DAILY_USD_CAP` (Default 1 USD je Maschine, Exit 4 = Deckel/Rate-Limit, Exit 3 = Schlüssel fehlt); Ampel: `gemini_usage.py`.

## Abgrenzung
- `gemini-bridge` (Agent) = der Consult selbst; `gemini-digest` (dieser Skill) = die
  Orchestrierung fürs Read-/Kontext-Offload.
- `codex-review` lagert Code-Review an Codex aus (code-spezialisiert); `gemini-digest` =
  Bulk-Read/Kontext-Masse (günstig, riesiges Fenster).
- `websuche`/`web-researcher` = Web; `gemini-digest` = lokale Dateien/Logs/Code.

## Beispiel-Triggers
`/gemini-digest logs/marshal.log — welche Fehler seit gestern?` · „fass analyzer.py (2000 Zeilen)
zusammen, was macht Klasse X" · „digest web/routes/: welche Endpoints existieren + Auth"

## Changelog
- v1.0.0 (2026-07-14): Initial — Offload-Skill-Suite (Token-Spar via Gemini/Codex).
