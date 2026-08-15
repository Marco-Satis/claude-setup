---
name: db-explore
version: 1.0.1
last-reviewed: 2026-05-28
description: SQLite-Datenbank-Inspect ohne Modifikationen — Schema, Indices, Row-Counts, NULL-Rates, Outliers, Top-Werte, Query-Plan-Stichproben. Optimiert für Memory-Service-DB, Discord-Bot-DBs (audit_log, stats_history, events), FootstepPro-Configs.
when_to_use: db explore, db inspect, sqlite analysieren, datenbank stichprobe, schema check, db statistik, table profile, query plan, sqlite analyze, db hygiene check
argument-hint: Required DB-Pfad ("/path/to/file.sqlite") + Optional Mode ("schema" | "stats" | "queries" | "full" — Default "full")
allowed-tools: Read Bash Glob
userInvocable: true
---

# db-explore — SQLite-Inspect-Skill

Zweck: Schnelle Übersicht einer SQLite-DB ohne Daten zu verändern. Pflicht Read-only (keine `INSERT`/`UPDATE`/`DELETE`/`DROP`).

## Vor dem Start

1. DB-Pfad aus Argument oder bei fehlend: der Nutzer fragen welche DB
2. Existenz prüfen + Read-Permission
3. **WICHTIG:** Wenn ein Service auf der DB schreibt (z.B. Bot läuft), nur `SELECT`-Queries ausführen. Niemals `VACUUM`/`REINDEX`/`ANALYZE` während Service läuft.

```bash
# Prüfung ob Service läuft (Linux):
ssh -p 4422 marco@159.195.72.217 "sudo systemctl is-active monitor-bot gameserver-bot admin-bot web-dashboard"
```

## Phase 1 — Schema-Inventar

```sql
.tables                            -- alle Tabellen + Views
.schema                            -- vollständige CREATE-Statements
SELECT name, sql FROM sqlite_master WHERE type='table';
SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index';
SELECT name, tbl_name FROM sqlite_master WHERE type='trigger';
```

Output-Tabelle:
| Table | Spalten | Indices | FKs | Trigger | Row-Count (geschätzt) |

## Phase 2 — Row-Counts + Größen-Inventar

```sql
-- Pro Table die Zeilenanzahl
SELECT 'audit_log' AS table_name, COUNT(*) AS rows FROM audit_log
UNION ALL SELECT 'stats_history', COUNT(*) FROM stats_history
UNION ALL SELECT 'events', COUNT(*) FROM events
-- ... für alle Tables
ORDER BY rows DESC;

-- Page-Count + Größe
PRAGMA page_count;
PRAGMA page_size;
-- DB-Größe MB = page_count * page_size / 1024 / 1024
```

**Pflicht-Output:**
- Top-5 größte Tables (Row-Count)
- DB-Größe gesamt (MB)
- Free-Pages (`PRAGMA freelist_count` — VACUUM-Empfehlung wenn > 10% der page_count)

## Phase 3 — Spalten-Profil (NULL-Rates, Distribution)

Pro Table (max die Top-5 größten):

```sql
-- NULL-Rate pro Spalte
SELECT
  COUNT(*) AS total,
  COUNT(column_a) AS not_null_a,
  COUNT(*) - COUNT(column_a) AS null_a,
  ROUND(100.0 * (COUNT(*) - COUNT(column_a)) / COUNT(*), 2) AS null_pct_a
FROM <table>;

-- Top-Werte einer kategorialen Spalte
SELECT category, COUNT(*) AS cnt
FROM <table>
GROUP BY category
ORDER BY cnt DESC
LIMIT 10;

-- Datums-Range
SELECT
  MIN(timestamp) AS oldest,
  MAX(timestamp) AS newest,
  ROUND(julianday(MAX(timestamp)) - julianday(MIN(timestamp))) AS days_span
FROM <table>;
```

**Findings-Pattern:**
- Spalte mit > 50% NULLs auf großen Tables → DESIGN-SMELL (sollte vielleicht in separate Table)
- Datums-Range > 2 Jahre und keine Archivierung → BACKLOG (Disk-Wachstum)
- Skewed-Categories (Top-Wert > 80% der Rows) → INFO (möglicherweise enum-besser)

## Phase 4 — Index-Effektivität

```sql
-- Indices auflisten
SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index';

-- Pro Index: prüfen ob er in häufigen Queries genutzt wird
-- (Heuristik: für jedes WHERE-Pattern aus den Queries des Codes)
EXPLAIN QUERY PLAN SELECT * FROM <table> WHERE <column> = ?;
-- Erwartet: "SEARCH ... USING INDEX <name>" NICHT "SCAN TABLE"
```

**Findings:**
- Index existiert aber wird nicht von typischen Queries genutzt → INFO (Index-Bloat)
- Häufige WHERE-Spalte ohne Index → MEDIUM (Performance-Problem bei Wachstum)
- Foreign-Key-Spalte ohne Index → MEDIUM (SQLite indiziert FKs NICHT automatisch)

## Phase 5 — Integrity-Check (Read-only)

```sql
PRAGMA integrity_check;     -- gibt "ok" oder Liste von Problemen
PRAGMA foreign_key_check;   -- prüft FK-Violations
PRAGMA quick_check;         -- schnellere Variante von integrity_check
```

**Pflicht-Output:** „integrity_check: ok" oder Liste der Probleme als CRITICAL-Finding.

## Phase 6 — Wartungs-Empfehlungen

Basierend auf Phase 1–5:

| Befund | Empfehlung | Wann ausführen |
|---|---|---|
| Free-Pages > 10% der page_count | `VACUUM` | nur nach `systemctl stop <service>` |
| `ANALYZE` älter als 30 Tage / nie | `ANALYZE` | Service kann laufen, kurze Lock-Zeit |
| Indices fehlen auf häufigen WHERE-Spalten | `CREATE INDEX IF NOT EXISTS ...` | Service kann laufen, aber Schreiblast prüfen |
| Datums-Range > 2 Jahre ohne Archivierung | Migration: alte Daten in separate Archive-DB | mit Stop + Migration-Skript |
| Integrity-Check schlägt fehl | `.recover` + Backup | sofort (CRITICAL) |
| WAL-File > 100 MB | `PRAGMA wal_checkpoint(TRUNCATE);` | kann während Service laufen |

## Phase 7 — Output

**Output-Datei:** `~/.claude/reports/db-explore/<datum>_<HHMM>/<db-name>.md`

**Master-Sektionen:**
1. Executive Summary (max 100 Worte: DB-Name, Größe, Top-3 Empfehlungen)
2. Schema-Inventar (Tables, Indices, FKs, Trigger)
3. Row-Counts + Größen
4. Spalten-Profile (Top-5 größte Tables)
5. Index-Effektivität
6. Integrity-Status
7. Wartungs-Empfehlungen (priorisiert)

**Chat-Output (max 20 Zeilen):**
- DB-Größe + Top-3 Tables
- Integrity-Status
- 3 wichtigste Wartungs-Empfehlungen

## der Nutzer häufige DBs

| DB-Pfad | Service | Hinweise |
|---|---|---|
| `C:\Users\der Nutzer\AppData\Local\mcp-memory\sqlite_vec.db` (Windows, real) bzw. `~/.local/share/mcp-memory/sqlite_vec.db` (Linux) | mcp-memory-service | Port 8000 — Health-Check vor Inspect. WAL-Mode: `wal_checkpoint` vor Backup. Backup-Script: `~/.claude/scripts/backup_memory_db.py` |
| `/home/botuser/Discord_Bots/data/bot.db` | monitor-bot, gameserver-bot, admin-bot | shared DB — Inspect lieber bei niedriger Last |
| `$HOME/n8n_stack/state/pipeline_state.sqlite` (geplant) | n8n-Workflow | erst nach Phase-2-Setup der Pipeline |
| `$HOME/n8n_data/database.sqlite` (geplant) | n8n selbst | Workflow-Storage |

## Constraints

- **Read-only.** Niemals INSERT/UPDATE/DELETE/DROP/VACUUM/REINDEX während Service läuft
- **Backup-Empfehlung** vor jeder Wartungs-Aktion: `cp -a <db> <db>.bak.$(date +%s)`
- **Permission-Check:** wenn DB von Service geschrieben wird → Output dass Wartungs-Aktionen einen `systemctl stop` brauchen
- **WAL-Mode-Awareness:** bei `journal_mode=WAL` muss `wal_checkpoint` vor Backup laufen damit `.wal`/`.shm` konsistent sind
- **Severity** kompatibel mit `/review`

## Beispiel-Triggers

- `/db-explore /home/botuser/Discord_Bots/data/bot.db`
- `/db-explore ~/.local/share/mcp_memory/memory.db schema` (nur Schema-Phase)
- `/db-explore ~/.local/share/mcp_memory/memory.db stats` (nur Row-Counts + Profiles)

## Changelog

- **v1.0.1** (2026-05-28): Lyra-Audit-Fix — Memory-DB-Pfad korrigiert auf realen `C:\Users\der Nutzer\AppData\Local\mcp-memory\sqlite_vec.db` (Windows-lokal; alter Pfad `managed_agent_venv/.../memory.db` existierte nicht); Backup-Script-Referenz ergänzt.
- **v1.0.0** (2026-05-17): Erste Version.
