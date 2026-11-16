---
name: instructions-drift-check
description: Prüft wöchentlich den Spiegel von des Nutzers claude.ai-Anweisungen (SETUP_SPIEGEL/claude_app_anweisungen.md) auf Drift gegen das Setup (Connector-Werkzeugnamen, eingeschlichene harte Fakten, Widersprüche zu den Rules) und schreibt nur einen Bericht. Ändert weder den Spiegel noch den App-Text; der Nutzer trägt Änderungen selbst in die App ein. Use when "instructions drift", "anweisungen prüfen", "claude.ai-anweisungen check", "custom-instructions check", "/instructions-drift-check", oder wöchentlich per Routine.
version: 2.0.0
model: inherit
---

# instructions-drift-check: Drift im Spiegel der claude.ai-Anweisungen

**Quelle seit 16.11.2026** (der Nutzer, MB170 „neuer Spiegel“): `SETUP_SPIEGEL/claude_app_anweisungen.md`
- PC: `C:\Users\<user>\projects-sync\Skills_&_Co\SETUP_SPIEGEL\claude_app_anweisungen.md`
- netcup: `~/projects/Skills_&_Co/SETUP_SPIEGEL/claude_app_anweisungen.md`

Der Spiegel gibt wieder, was der Nutzer in die claude.ai-App eingetragen hat (erste Zeile „Stand: …“). Er hat
keine AUTO-FACTS-Regionen und enthält absichtlich keine Ports, Pfade, Versionen oder Modellnamen; die stehen
im Wissensspeicher. `~/.claude/CUSTOM_INSTRUCTIONS.md` (nur PC) ist Altbestand: nicht mehr prüfen, nicht
patchen, nicht löschen. Bis v1.3.0 hat dieser Skill dort AUTO-FACTS gepatcht (Backups `*.bak.pre-mb170.*`).

## Harte Grenzen
- **Nur lesen und berichten.** Spiegel, Vorschlagsdateien und Altbestand bleiben unverändert. Ein Vorschlag
  für neuen App-Text steht im Bericht; eintragen tut der Nutzer.
- Datei-Inhalte nur via Read-Tool (nie cat/Get-Content/head/tail via Shell), sonst Security-Flag.
- Keine SSH-, curl- oder sudo-Aufrufe. Der Lauf braucht keine Live-Proben am Server.
- Unsicher → im Bericht „unklar“, nicht raten.

## Ablauf
1. **Spiegel lesen** (Read). Fehlt er: Bericht „Spiegel fehlt“ und Ende.
2. **Stand:** Datum der ersten Zeile notieren. Liegt im selben Ordner eine `claude_app_anweisungen_VORSCHLAG_*.md`,
   die neuer ist als dieser Stand → Bericht „Vorschlag liegt bereit, nicht eingetragen“.
3. **Connector-Werkzeuge:** Jeder im Spiegel genannte Werkzeugname (z. B. `wissen_suchen`, `wissen_lesen`,
   `wissen_merken`) muss in DIESER Session als Connector-Werkzeug vorkommen (eigenes Tool-Listing inklusive
   deferred; der Name endet auf `__<werkzeug>`). Fehlt einer → drift.
4. **Harte Fakten:** Stehen Ports, IP-Adressen, Pfade, Versionsnummern, Modell-IDs oder URLs im Spiegel → drift
   („gehört in den Wissensspeicher“).
5. **Regel-Abgleich:** Kernaussagen des Spiegels gegen `~/.claude/rules/` (vor allem `mitdenken.md`,
   `session-disziplin.md` „Sofort erledigen statt vertagen“, `secret-handling.md`) und die globale `CLAUDE.md`
   halten. Nur echte Widersprüche melden (beide Stellen mit Zeile), keine Stilfragen.
6. **Kontext-Abschnitt:** nur bei klarem Widerspruch zu des Nutzers Projekten melden.
7. **Bericht** nach `C:\Users\<user>\OneDrive\Dokumente\Projekte\Skills_&_Co\INSTRUCTIONS_DRIFT\DRIFT_<YYYY-MM-DD>.md`
   (netcup: `~/projects/Skills_&_Co/INSTRUCTIONS_DRIFT/`): Tabelle `Prüfpunkt | Spiegel | Ist | Urteil (ok/drift/unklar)`,
   bei Drift darunter ein Textvorschlag für die App. Bei 0 Drift eine Zeile „all green“. Hat der Bericht Drift,
   lautet seine letzte Zeile `BRAUCHT: der Nutzer – App-Text anpassen (<Punkt>)`.

## Output (an der Nutzer, knapp)
X Punkte geprüft, Y Drift, Z unklar; Berichtspfad.
