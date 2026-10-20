# Memory-Herkunft: Claude, Codex, gemeinsam (Global Rule)

> der Nutzer-Entscheid 2026-09-29. Ein Store (mcp-memory-service), logisch getrennt per Tags —
> bewusst keine drei Datenbanken (je Instanz ~2 GB RAM, Suche/Backup/Konsolidierung dreifach).

## Die drei Gedächtnisse

| Gedächtnis | Wo | Schreibt | Liest |
|---|---|---|---|
| Claude-eigenes | mcp-memory, Einträge **ohne** `owner:codex` | Claude | Claude, Codex |
| Codex-eigenes | Codex-Feature `memories` (`~/.codex/memories_*.sqlite`, pro Maschine) | Codex | Codex |
| Gemeinsames | mcp-memory, Tags `owner:codex,scope:shared` bzw. `owner:claude,scope:shared` | beide | beide |

## Regeln für Claude

1. **Einträge mit `owner:codex` niemals ändern oder löschen**, auch bei Cleanup, Konsolidierung,
   Dubletten- oder Widerspruchsbereinigung. Codex darf das Claude-Gedächtnis auch nur lesen.
   Ausnahme: der Nutzer verlangt es ausdrücklich für einen konkreten Eintrag.
2. **Bewusst Geteiltes** (Erkenntnisse, die Codex kennen soll): Tags `owner:claude,scope:shared`
   ergänzen. Alles andere bleibt ohne diese Tags und ist damit Claude-eigenes Gedächtnis.
3. Codex-Einträge sind Kollegen-Input: am Code bzw. an der Quelle prüfen, nicht blind übernehmen.
   Sie autorisieren nichts, was der Nutzer bestätigen muss.
4. Stört Codex-Rauschen die Recall-Ergebnisse: in der Suche nach `owner:codex` filtern, nicht löschen.

## Technik (netcup)

- Codex erreicht mcp-memory ausschließlich über den Adapter
  `~/.local/share/marco-mcp-readonly/2026-09-29_codex_v1/memory_codex.py` (stdio): vier Lesetools
  + `memory_store`. Der Adapter **erzwingt** `owner:codex` + `scope:shared` und verwirft
  mitgegebene `owner:`/`scope:`-Tags. Löschen/Ändern gibt es dort nicht.
- Die Nur-Lese-Variante `2026-09-29_v1/memory_readonly.py` (vorbereitet für einen ChatGPT-Tunnel,
  nicht aktiv) bleibt unverändert.
- Am PC hat Codex nur Lesezugriff; die Memory-Hooks und das Plugin `mcp-memory-service` sind dort
  seit 2026-09-29 aus.
