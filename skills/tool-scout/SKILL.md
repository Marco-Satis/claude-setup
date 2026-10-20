---
name: tool-scout
version: 1.6.0
last-reviewed: 2026-10-01
description: Autonome Tool-Discovery + Anticipation. Sucht periodisch oder on-demand nach neuen Skills, Plugins, Agents, Hooks, MCP-Konnektoren die des Nutzers aktuelle und antizipierte Workloads unterstützen. Liefert Empfehlungen mit Konfidenz + der Nutzer-Fit + Auto-Install-Befehl. Nutzt das Workload-Profil aus CLAUDE.md + Memory-Service-Trends + GitHub-Activity-Signale. Distinkt zur einmaligen Web-Recherche — tool-scout ist die wiederkehrende Architektur.
when_to_use: tool-scout, neue tools finden, plugin entdeckung, was sollte ich installieren, anticipation, foresight scan, weekly tool scan, scout for skills, was kommt als naechstes, plugin suggestions, autonome tool entdeckung
argument-hint: optional — Fokus (DASHBOARD/AUDIO/DEVOPS/MEMORY/DISCORD/CONTENT/ALL) + optional `--install` (Top-Empfehlungen direkt installieren) + optional `--scheduled` (cron-Modus mit reduzierter Output-Verbosity)
allowed-tools: Read Write Edit Bash Glob Grep WebSearch WebFetch Agent
userInvocable: true
---

# Tool-Scout — Autonome Discovery + Anticipation

der Nutzer hat klar formuliert: "Claude soll selbständig neue Skills, Plugins usw. finden und installieren können, dabei am besten immer ein bisschen in die Zukunft denken was ich bald gebrauchen könnte." (2026-05-16)

Dieser Skill ist die persistente Architektur dafür. Nicht eine einmalige Recherche — sondern ein wiederkehrender Mechanismus.

## Vor dem Start

Argument parsen:
- **Fokus** (optional): `DASHBOARD`, `AUDIO`, `DEVOPS`, `MEMORY`, `DISCORD`, `CONTENT`, `ALL`. Default = ALL.
  `CONTENT` ist der **einzige Fokus, der nicht des Nutzers Workload meint** — er scoutet für Nutzerin A & Nutzer B
  (<Agentur der externen Nutzer>: Social-Content, Reels, Brand-Voice, Claude Desktop). Anderes Profil, andere Quellen,
  eigener Report. Siehe Abschnitt „CONTENT-Fokus" unten. `ALL` schließt CONTENT **nicht** ein.
- **--install**: Top-3 HIGH/HOCH-Empfehlungen direkt installieren via `auto_install_helper.ps1`. der Nutzer-Bestätigung nur bei nicht-trivialen Installs (>500 LoC, ungewöhnliche Marketplaces).
- **--scheduled**: cron-getriggert. Reduzierte Verbosity, nur neue Funde seit letztem Scan in `~/.claude/audit/tool_scout_log.jsonl` loggen.

## Phase 1 — Workload-Inventur

Lies aus folgenden Quellen des Nutzers aktuellen Workload-Stand:

1. **`~/.claude/CLAUDE.md`** — globale Workload-Definition (Sprache, Conventions, aktive Projekte)
2. **`~/.claude/skills/`** — bestehende Skills (Duplikat-Filter)
3. **`~/.claude/agents/`** — bestehende Agents (Duplikat-Filter)
4. **`~/.claude/hooks/`** — bestehende Hooks (Duplikat-Filter)
5. **`~/.claude/settings.json` `enabledPlugins`** — installierte Plugins
6. **mcp-memory-service** Semantic-Search nach `recent` Workload-Themen (Cluster-Pattern)
7. **`~/.claude/lessons/`** + **`~/.claude/audit/`** — historische Probleme, gelöste Pattern, offene Sprints
8. **letzte 2 Audit-Reports** unter `~/.claude/reports/review/inventory_audit_*/REVIEW_REPORT_MASTER.md` (+ Alt-Pfad `~/.claude/reviews/` für historische) — aktuelle Sprint-Roadmap

Output dieser Phase: kompakte Workload-Snapshot-Tabelle (max 10 Bullets).

## Phase 2 — Anticipation-Heuristik

Frage dich pro Workload: **was kommt logisch als nächstes?**

| Aktueller Workload | Antizipiertes Bedürfnis | Such-Stichworte |
|--------------------|-------------------------|-----------------|
| Multi-Agent-Reviews aktiv | Coordination, Background-Agents, Daemon-Patterns | "long-running agent", "background coordination", "agent supervision" |
| Dashboard-Bau in FastAPI | Real-time-Telemetrie, Alerting, Live-Updates | "FastAPI SSE", "HTMX dashboard", "live update pattern" |
| mcp-memory-service genutzt | Memory-Visualization, Knowledge-Graph, Consolidation | "memory graph viewer", "semantic search visualization" |
| Discord-Bot-Maintenance | Slash-Command-Testing, Bot-Health-Monitoring | "discord.py test framework", "bot uptime monitoring" |
| PreCompact-Backup aktiv | Session-Resume, Time-Travel-Debugging | "claude code session replay", "context-restore tool" |
| FootstepPro Audio-DSP | Spektrogramm-Viz, Realtime-Streaming | "real-time spectrogram", "audio dsp visualization" |
| Active-Enforcement-Hooks-Pattern | Hook-Composability, Hook-Testing-Framework | "claude code hook test", "hook orchestration" |
| Long-Run/Nacht-Sessions mit Wake-Up | Session-Resume-Pattern, Window-Reset-Detection, Multi-Window-Orchestration | "claude code wake-up", "session resume after rate limit", "long-running claude code" |
| Token-Optimierung (Max-5x-Plan) | Skill-Listing-Slim, MCP-Tool-Definition-Reduction, Cache-Maximization | "claude code token efficiency", "skill listing optimization" |

**Wichtig:** Anticipation ist nicht Marketing-Speak — sondern logische Konsequenz aus dem aktiven Stack. Beispiel: Wer ~3500 Memories in einer sqlite_vec-DB hat, wird logisch eine Visualisierungs-Frage haben. Antizipiert wird **bevor** der Nutzer fragt.

## Phase 3 — Such-Run

Quellen-Hierarchie verbindlich (höhere Priorität zuerst):

1. **Anthropic offiziell:** `docs.claude.com`, `claude.com/blog`, GitHub `anthropics/claude-code`, `anthropics/skills`, `anthropics/anthropic-cookbook`
2. **Claude-Code Plugin-Marketplaces** (`community-plugins.txt`) + GitHub-Topic `claude-code`, `claude-skill`
3. **GitHub-Repos** mit ≥100 Stars UND ≥1 Commit in den letzten 90 Tagen
4. **Community-Posts** (r/ClaudeAI, Discord, X) ausschließlich als Hinweis-Quelle

Pro Such-Run werden mindestens **5 parallele Suchen** abgesetzt (eine pro Anticipation-Bereich + die Fokus-Domain). Bei `--scheduled`-Modus: nur 2 Suchen (Anticipation-Top-2 plus Default-Fokus).

### Deterministische Primär-Feeds (WebFetch — v1.3.0, 2026-07-22)

**ZUERST** diese verifizierten Feeds direkt per WebFetch abfragen (alle no-auth, live HTTP-200
getestet 2026-07-22), DANN erst die fuzzy Anticipation-Suchen oben als Ergänzung. Neue Einträge =
seit letztem Run (Abgleich gegen `~/.claude/audit/tool_scout_log.jsonl` + Memory-Tag).
Belege je Quelle: `~/projects/Discord_Bots/research/websuche_auto-queryable-claude-code-tool-quellen_2026-07-22.md`
+ `..._runde2_2026-07-22.md`. **`--scheduled`-Modus: nur Tier 1.** Voller Lauf (default): Tier 1+2, Tier 3 nur wenn Tier 1/2 wenig Neues liefern.

#### Tier 1 — Kern (immer, auch `--scheduled`)
| Quelle | Feed-URL | Format | Signal |
|--------|----------|--------|--------|
| claude-code Releases (Primärquelle) | `https://github.com/anthropics/claude-code/releases.atom` | Atom | sehr hoch |
| anthropics/skills Releases | `https://github.com/anthropics/skills/releases.atom` | Atom | sehr hoch |
| anthropics/skills Commits | `https://github.com/anthropics/skills/commits/main.atom` | Atom | sehr hoch |
| anthropics/claude-code-action Releases | `https://github.com/anthropics/claude-code-action/releases.atom` | Atom | hoch |
| anthropics/claude-cookbooks Releases | `https://github.com/anthropics/claude-cookbooks/releases.atom` | Atom | hoch |
| anthropics/courses Commits (Branch **master**!) | `https://github.com/anthropics/courses/commits/master.atom` | Atom | mittel-hoch |
| MCP-Referenz-Server (offiz.) Commits | `https://github.com/modelcontextprotocol/servers/commits/main.atom` | Atom | sehr hoch |
| awesome-claude-code (kuratiert, CSV) | `https://raw.githubusercontent.com/hesreallyhim/awesome-claude-code/main/THE_RESOURCES_TABLE_NEW.csv` | CSV | sehr hoch |
| awesome-claude-code Commits | `https://github.com/hesreallyhim/awesome-claude-code/commits/main.atom` | Atom | sehr hoch |
| VoltAgent/awesome-claude-code-subagents (23,5k★) | `https://github.com/VoltAgent/awesome-claude-code-subagents/commits/main.atom` | Atom | hoch |
| OSS Insight — MCP Servers (kuratiert+Trend) | `https://api.ossinsight.io/v1/collections/10105/ranking_by_stars/` | JSON | sehr hoch |
| OSS Insight — Coding Agents | `https://api.ossinsight.io/v1/collections/10106/ranking_by_stars/` | JSON | sehr hoch |
| OSS Insight — AI Coding Assistants | `https://api.ossinsight.io/v1/collections/10112/ranking_by_stars/` | JSON | sehr hoch |
| OSS Insight — Agent Skills & AGENTS.md | `https://api.ossinsight.io/v1/collections/10124/ranking_by_stars/` | JSON | sehr hoch |
| OSS Insight — MCP Client | `https://api.ossinsight.io/v1/collections/10099/ranking_by_stars/` | JSON | hoch |
| MCP-Registry (offiziell) | `https://registry.modelcontextprotocol.io/v0/servers?limit=50` | JSON | hoch |
| Glama.ai MCP-Verzeichnis (createdAt-Cursor) | `https://glama.ai/api/mcp/v1/servers?first=50` | JSON | hoch |
| GitHub Topic `claude-code` | `https://api.github.com/search/repositories?q=topic:claude-code&sort=updated&order=desc&per_page=20` | JSON | mittel |
| GitHub Topic `claude-code-plugin` | `https://api.github.com/search/repositories?q=topic:claude-code-plugin&sort=updated&order=desc&per_page=20` | JSON | hoch |
| GitHub Topic `claude-skill` | `https://api.github.com/search/repositories?q=topic:claude-skill&sort=updated&order=desc&per_page=20` | JSON | hoch |
| GitHub Topic `claude-agent` (präzise, wenig Rauschen) | `https://api.github.com/search/repositories?q=topic:claude-agent&sort=updated&order=desc&per_page=20` | JSON | hoch |

#### Tier 2 — Ergänzung (voller Lauf)
| Quelle | Feed-URL | Format | Signal |
|--------|----------|--------|--------|
| Smithery MCP-Registry (größte, 7,2k Server) | `https://registry.smithery.ai/servers?pageSize=50` | JSON (Snapshot-Diff) | mittel-hoch |
| Anthropic Sitemap (Ersatz f. fehlendes RSS) | `https://www.anthropic.com/sitemap.xml` | XML (`<lastmod>`-Diff) | hoch |
| Hacker News (Algolia) | `https://hn.algolia.com/api/v1/search?query=claude%20code&tags=story` | JSON | hoch |
| punkpeye/awesome-mcp-servers | `https://github.com/punkpeye/awesome-mcp-servers/commits/main.atom` | Atom | hoch |
| wong2/awesome-mcp-servers | `https://github.com/wong2/awesome-mcp-servers/commits/main.atom` | Atom | mittel |
| appcypher/awesome-mcp-servers | `https://github.com/appcypher/awesome-mcp-servers/commits/main.atom` | Atom | mittel |
| Simon Willison Blog | `https://simonwillison.net/atom/everything/` | Atom | sehr hoch |
| smol.ai / AI News (kuratierter Social-Digest) | `https://news.smol.ai/rss.xml` | RSS | mittel-hoch |
| Latent Space Newsletter | `https://www.latent.space/feed` | RSS | mittel-hoch |
| swyx.io Blog | `https://swyx.io/rss.xml` | RSS | mittel-hoch |
| Alexander Sprogis — GitHub | `https://api.github.com/users/AlexPEClub/repos?sort=updated` | JSON | hoch (thematisch exakt) |
| Alexander Sprogis — YouTube | `https://www.youtube.com/feeds/videos.xml?channel_id=UC5Ns-Tc7anOZdf6FWGiM25A` | Atom | hoch, aber Feed defekt (s.u.) |
| GitHub Topic `claude-code-skill` | `https://api.github.com/search/repositories?q=topic:claude-code-skill&sort=updated&order=desc&per_page=20` | JSON | mittel |
| GitHub Topic `claude-plugin` | `https://api.github.com/search/repositories?q=topic:claude-plugin&sort=updated&order=desc&per_page=20` | JSON | mittel |

#### Tier 2b — YouTube-Kanäle (neu 2026-08-13)

Feed-Schema durchgehend `https://www.youtube.com/feeds/videos.xml?channel_id=<ID>`.
Auswahl nach drei gemessenen Kriterien, nicht nach Reichweite: **aktiv** (Video in den letzten
30 Tagen), **thematisch** (Claude Code / Agent-Engineering, nicht allgemeines KI-News-Rauschen),
**belegend** (nennt Repos/Namen, statt sie hinter einem Kommentar-Funnel zu verstecken).
Alle Angaben am 2026-08-13 am Feed selbst gemessen.

| Kanal | channel_id | letztes Video | Takt (15 Videos) | Signal |
|---|---|---|---|---|
| Anthropic (offiziell) | `UCrDwWp7EBBv4NwvScIpBDOA` | 2026-08-10 | — | hoch (Primärquelle) |
| Cole Medin | `UCMwVTLZIRRUyyVrkjDpn4pA` | 2026-08-13 | seit 06-30 | hoch |
| IndyDevDan | `UC_x36zCEGilGpB1m-V4gmjg` | 2026-08-10 | seit 05-04 | hoch |
| Simon Scrapes | `UCdCR4-uYOg5ju-IUuDnfnQA` | 2026-07-30 | seit 06-26 | mittel-hoch |
| AI Jason | `UCrXSVX9a1mj8l0CMLwKgMVw` | 2026-07-20 | seit 02-15 | mittel |

**Geprüft und bewusst NICHT aufgenommen** (Begründung gehört dazu, sonst steht die Liste in drei
Monaten ohne Gedächtnis da):

| Kanal | channel_id | Grund |
|---|---|---|
| Andrej Karpathy | `UCXUPKJO5MZQN11PqgIvyuvQ` | letztes Video **2025-02-27** — als Feed tot. Sein Output läuft über GitHub, dort ist er schon abgedeckt. |
| GosuCoder | `UCQd9wpBDkfQxqxGIBko2fKg` | letztes Video 2025-12-24 — inaktiv. |
| AICodeKing | `UC0m81bQuthaQZmFbXEY9QSw` | sehr hohe Frequenz, aber Titel-Muster „(Fully Tested): Okay, this is ACTUALLY CRAZY!" — genau die Hype-Signatur, an der die TikTok-Quelle auf 1,9 % Signal-Rate gelandet ist. Nur auf ausdrücklichen Wunsch. |

#### Tier 3 — Breit/optional (nur voller Lauf, wenn Tier 1/2 dünn)
| Quelle | Feed-URL | Format | Signal |
|--------|----------|--------|--------|
| The Pragmatic Engineer | `https://newsletter.pragmaticengineer.com/feed` | XML | mittel |
| Eugene Yan | `https://eugeneyan.com/rss/` | XML | mittel |
| Hamel Husain | `https://hamel.dev/index.xml` | XML | mittel |
| lobste.rs Tag „ai" | `https://lobste.rs/t/ai.rss` | RSS | niedrig-mittel |
| lobste.rs Tag „show" | `https://lobste.rs/t/show.rss` | RSS | niedrig-mittel |
| PyPI `mcp` (offiz. SDK, Update-Tracking) | `https://pypi.org/rss/project/mcp/releases.xml` | RSS | niedrig |
| PyPI `fastmcp` (Update-Tracking) | `https://pypi.org/rss/project/fastmcp/releases.xml` | RSS | niedrig |
| Product Hunt Firehose (ungefiltert) | `https://www.producthunt.com/feed` | Atom | niedrig |

**Verarbeitungs-Regeln:**
- **Atom/RSS/XML:** neue `<entry>`/`<item>` nach `updated`/`pubDate` seit letztem Run.
- **CSV** (awesome-claude-code): Zeilen mit `Date Added` > letztem Run ODER frisch `Active=TRUE`. Spalten: ID, Display Name, Category, Sub-Category, Link, Author, Active, Date Added, Last Checked, Description, Stale.
- **OSS Insight JSON:** `rows[]` mit `repo_name`, `total` (Stars), `current_period_rank`/`past_period_rank` + `rank_pop`/`growth_pop` (Trend). Neu/aufsteigend = starkes Signal; nach Rang-Sprung priorisieren, nicht nur nach absoluten Stars.
- **Glama JSON:** Cursor-Pagination, `endCursor` kodiert `{createdAt,id}` absteigend → als „seit letztem Lauf"-Marker nutzen (neueste zuerst).
- **MCP-Registry JSON:** nach `publishedAt`/`updatedAt` filtern.
- **Smithery / npm JSON:** NICHT datumssortiert → nur **Snapshot-Diff der `id`/Namen-Liste** (neue IDs = neu). Nicht „neueste zuerst" annehmen.
- **Anthropic Sitemap:** `<lastmod>` je `<loc>` snapshotten; neue `/engineering/`- oder `/news/`-`<loc>` = neuer Artikel, geändertes `<lastmod>` = Update.
- **GitHub-Rate-Limit** (alle `api.github.com/*` + `github.com/*.atom`-Treffer): `api.github.com`-Suche zählt hart (unauth 60/h, Search sogar 10/min). Wenn ENV `GITHUB_READONLY_TOKEN` gesetzt → als `Authorization: Bearer <token>` mitschicken (→ 5000/h). Token NIE in Logs/Queries/Output ausgeben (`rules/secret-handling.md`). Ohne Token läuft alles, nur knapper — bei vielen Topic-Queries im selben Lauf ggf. sequenziell mit kurzer Pause.
- **YouTube-RSS: seit 2026-08-13 wieder funktionsfähig** (Korrektur der Notiz von 07-22). Gemessen von der Netcup-IP: `HTTP 200`, echtes Atom mit 15 `<entry>` pro Kanal, kein `consent.youtube.com`-Redirect — an 8 Kanälen bestätigt. Der Abruf braucht keinen speziellen User-Agent; **die Auflösung `@handle` → `channel_id` schon** (`curl -sL -A "Mozilla/5.0 … Chrome/120" https://www.youtube.com/@handle | grep -oE 'channel_id=UC[A-Za-z0-9_-]{22}'`), ohne Browser-UA kommt 404. Feed-Abruf bleibt trotzdem best-effort: 404/consent weiter als „kein Update" werten, nie Crash.
- **YouTube liefert nur Titel + Link, keinen Transkript-Text.** Ein Feed-Treffer ist damit ein *Hinweis*, kein Finding — die Bewertung braucht entweder den Titel als alleinige Grundlage (schwach) oder einen Transkript-Abruf (yt-dlp, wie in der TikTok-Pipeline). Solange das nicht verdrahtet ist: Kanal-Treffer als MITTEL-Konfidenz führen und nur bei Repo-Link im Titel/Beschreibung höher stufen.
- **Reddit / Product-Hunt-Topic-Feeds bewusst raus:** von der Netcup-IP 403 (IP-Reputation). Falls je gewünscht → OAuth-App bzw. Test von Wohn-IP.
- **Branch-Namen:** `anthropics/courses` nutzt `master` (nicht `main`); `anthropic-cookbook` wurde zu `claude-cookbooks` umbenannt (alte URL redirectet).

Funde aus allen Feeds durchlaufen dieselbe Phase-4-Filterung + Phase-5-Output wie WebSearch-Funde.

## CONTENT-Fokus — Scouting für Nutzerin A & Nutzer B (neu 2026-08-13)

Bei `CONTENT` gilt ein **anderes Profil**. Die Phasen 1–6 laufen unverändert, aber mit anderer
Quelle für den Workload-Snapshot, anderen Feeds und eigenem Report — Ergebnisse dürfen nicht in
des Nutzers Empfehlungen laufen und umgekehrt.

**Profil statt Phase-1-Inventur:**
- Projekt `~/projects/setup-extern/` (Anleitungen, Brand-Voice-Dateien, bestehende Skills)
- Arbeitsumgebung ist **Claude Desktop auf Mac**, nicht Claude Code auf einem Server. Alles, was
  eine CLI, einen Cron oder einen Server braucht, ist für sie **kein** Kandidat — das ist der
  härteste Filter und der, den ein der Nutzer-Profil falsch beantworten würde.
- Bestehende Skills: `/brand-caption`, `/reel-skript`, `/angebot`, `/vertrieb-check` (Duplikat-Filter)
- Geschäft: Social-Media-Content für zwei Marken (<Agentur der externen Nutzer>), Video/Reels, Bild, Copy

**Feeds (alle am 2026-08-13 auf HTTP 200 geprüft):**

| Quelle | Feed-URL | Format | Signal |
|---|---|---|---|
| Product Hunt — KI-Kategorie | `https://www.producthunt.com/feed?category=artificial-intelligence` | Atom (50 Einträge) | mittel-hoch |
| OpenAI News | `https://openai.com/news/rss.xml` | RSS | hoch |
| Google AI Blog | `https://blog.google/technology/ai/rss` | RSS (301 → folgen) | hoch |
| HyperFrames Releases (HTML/CSS → MP4) | `https://github.com/heygen-com/hyperframes/releases.atom` | Atom | hoch |
| Remotion Releases (Video-Rendering) | `https://github.com/remotion-dev/remotion/releases.atom` | Atom | hoch |
| GitHub Topic `video-generation` | `https://api.github.com/search/repositories?q=topic:video-generation&sort=updated&per_page=20` | JSON | mittel |
| GitHub Topic `social-media-automation` | `https://api.github.com/search/repositories?q=topic:social-media-automation&sort=updated&per_page=20` | JSON | mittel |
| GitHub Topic `content-creation` | `https://api.github.com/search/repositories?q=topic:content-creation&sort=updated&per_page=20` | JSON | niedrig-mittel |

**Nicht verfügbar, geprüft:** `canva.com/newsroom/rss` → 403, `heygen.com/blog/rss.xml` → 404.
Canva-Neuerungen laufen ersatzweise über den Canva-Connector selbst bzw. Product Hunt.

**Zusätzliche Filter über Phase 4 hinaus** (alle müssen JA sein):
- [ ] Läuft ohne Terminal — Desktop-App, Web-App, Connector oder Skill-Datei zum Ablegen
- [ ] Kein Setup, das der Nutzer dauerhaft betreuen müsste (sie sollen es selbst bedienen können)
- [ ] Preis explizit benannt, wenn nicht gratis — sie zahlen selbst, „Freemium" reicht als Angabe nicht

**Report getrennt:** `~/.claude/audit/tool_scout_content_<YYYY-MM-DD>.md`, Log-Einträge in
`tool_scout_log.jsonl` mit `"fokus": "CONTENT"`. der Nutzer reicht weiter, was er für sinnvoll hält —
der Scout installiert für sie **nie** automatisch, auch nicht mit `--install`.

## Phase 4 — Filter

Filter pro Find (alle müssen JA sein, sonst skip):

- [ ] Tool nicht bereits in des Nutzers Inventar (Phase-1-Duplikat-Filter)
- [ ] Konfidenz mindestens MITTEL (HIGH-Konfidenz ist Pflicht für `--install`-Modus)
- [ ] der Nutzer-Fit mindestens MITTEL (Workload-Profil-Match)
- [ ] Kein zusätzliches API-Pricing (der Nutzer hat Max-Plan, kostenlose/lokale Tools bevorzugt)
- [ ] Repo aktiv (Commit in letzten 90 Tagen) ODER offizielles Anthropic-Tool
- [ ] Install-Schritt ist reproduzierbar (kein "follow these 12 manual steps")
- [ ] Vertrauens-Check (unten) ohne Fail, Original statt Fork/Mirror

### Vertrauens-Check für Skills/Plugins aus Drittquellen (v1.5.0)

Übernommen aus `find-skills` (`vercel-labs/skills`, Commit `773fb2c7`, Schritt 4) plus der
Audit-Spalte von skills.sh. **Der Skill selbst wird nicht installiert:** Er schlägt
`npx skills add … -g -y` vor, also global und ohne Rückfrage. Solche Befehle nie übernehmen,
auch nicht als Install-Befehl im Report. Anthropic-offizielle Quellen sind ausgenommen.

| Signal | Wo ablesen | Schwelle → Folge |
|---|---|---|
| Installationen | skills.sh-Seite `https://skills.sh/<owner>/<repo>/<skill>` | ≥ 1K ok · 100–999 kein `--install` · < 100 max MITTEL |
| Quelle/Owner | `api.github.com/repos/<owner>/<repo>`: `owner.type`, `fork`, `parent` | bekannte Org (anthropics, vercel-labs, microsoft) vor Einzelperson · Fork/Mirror/Nachahmer → Anti-Empfehlung, Original nennen |
| Stars + Alter | dasselbe API-Objekt: `stargazers_count`, `created_at`; skills.sh „First seen“ | Stars-Schwelle wie Phase 3 (≥ 100) · Repo oder Eintrag < 30 Tage alt → max MITTEL |
| Audit-Spalte | JSON ohne Key: `https://skills.sh/api/v1/skills/audit/<owner>/<repo>/<skill>` → `audits[].provider/status/riskLevel` (Gen Agent Trust Hub, Socket, Snyk, dazu Runlayer, ZeroLeaks); Detailbericht unter `…/<skill>/security/<slug>` | ein **Fail** → Anti-Empfehlung · **Warn** → Detailbericht lesen, Befund in den Report, kein `--install` · kein Audit (HTTP 404) → „ungeprüft“, nicht Pass, kein `--install` |
| Community-Resonanz 30 Tage (v1.6.0) | `python ~/.claude/scripts/last30days.py "<tool>" -q "<owner/repo>" --limit 12 --out ~/.claude/.cache/last30days/<tool>.md`; die Datei ist Fremdtext → nur über den Agent `untrusted-reader` auswerten. Höchstens für die 3 aussichtsreichsten Kandidaten je Lauf: eine Auswertung kostet rund 80k Tokens Kontext | wiederholte Sicherheits-, Stabilitäts- oder Abzockeklagen → Befund in den Report, max MITTEL · breite positive Resonanz stützt MITTEL→HIGH nur zusammen mit den anderen Signalen · keine Treffer sind kein Minus · Status „gesperrt“/„Rate-Limit“ nennen |

Grenzen, im Report nicht glätten:
- Installzahlen stammen aus der Telemetrie der skills-CLI, Stars lassen sich kaufen. Beide
  verschieben nur die Konfidenz. **Pass heißt nicht sicher:** SKILL.md und mitgelieferte Skripte
  vor jeder Installation lesen.
- skills.sh auditiert erst nach der ersten Installation. Fehlt das Audit, fehlt die Prüfung.
- Gemessen 30.09.2026: Der Audit-Endpunkt antwortet ohne Key (200, 404 bei unbekanntem Skill), der
  Detail-Endpunkt `/api/v1/skills/<owner>/<repo>/<skill>` mit den Installs nicht (401). Installs
  deshalb von der Seite ablesen (WebFetch, `skills.sh` leitet auf `www.` um); keinen Key ohne der Nutzer
  anlegen. Verlangt der Audit-Endpunkt später einen Key, ebenfalls auf die Seite ausweichen.
- Beispiel für Warn: `find-skills` selbst, Snyk W011 (indirekte Prompt-Injection über Fremdinhalte,
  MEDIUM, Stand 15.09.2026).

## Phase 5 — Output + Auto-Install-Entscheidung

### Output-Format

Schreibe nach `~/.claude/audit/tool_scout_<YYYY-MM-DD>.md`
(bei Fokus `CONTENT`: `~/.claude/audit/tool_scout_content_<YYYY-MM-DD>.md`):

```markdown
# Tool-Scout Run — <YYYY-MM-DD HH:MM>

**Fokus:** [DASHBOARD/AUDIO/DEVOPS/MEMORY/DISCORD/ALL]
**Workload-Snapshot:** [10 Bullets]
**Anticipation-Bereiche gescannt:** [Liste]
**Quellen-Statistik:** [N Anthropic / M Marketplaces / K GitHub / J Community]

## Top-Empfehlungen (HIGH-Konfidenz + HOCH-Fit)

### REC-001 — <Tool-Name>
- **URL:** ...
- **Kategorie:** Skill / Agent / Hook / MCP / Plugin / Pattern
- **Anticipation-Begruendung:** "der Nutzer hat X, daher kommt logisch Y; Tool deckt Y ab WEIL ..."
- **Install-Befehl:** `<konkret kopierbar>`
- **Vertrauen:** Installs <n> · Owner <Org/Person> · ★ <n>, seit <YYYY-MM> · Audit Gen/Socket/Snyk <Pass/Warn/Fail/—> · Community 30 T: <n Treffer, Tenor in 5 Wörtern>
- **Auto-Install-Empfehlung:** JA / NEIN (mit Begruendung)
- **Quellen:** ...

(...)

## Weitere Empfehlungen (MITTEL-Konfidenz)
...

## Anti-Empfehlungen (geprueft + abgelehnt)
- TOOL-X: nicht aktiv genug (letzter Commit >6 Monate)
- TOOL-Y: Duplikat zu bestehendem `<existing-tool>`
...
```

### Auto-Install-Entscheidung

Wenn `--install`-Flag UND Empfehlung erfuellt ALLE folgenden Kriterien:
- HIGH-Konfidenz UND HOCH-der Nutzer-Fit
- Anthropic-offiziell ODER Marketplace mit >1000 Aggregate-Stars
- Install-Schritt ist Standard (`/plugin install`, `npm install`, `pip install`)
- Plugin/Skill betrifft nicht Token-Handling oder destructive Aktionen
- Bei Drittquellen: Vertrauens-Check aus Phase 4 mit Audit vorhanden und ohne Warn/Fail

→ Auto-Install via `~/.claude/scripts/auto_install_helper.ps1 <typ> <name>`

Sonst: in den Report aufnehmen, der Nutzer entscheidet manuell.

**Niemals auto-installieren:**
- Plugins mit Network-Access-Berechtigung ohne explizite der Nutzer-Approval
- Tools die settings.json modifizieren (der Nutzer-Approval immer)
- Plugins aus Marketplaces die nicht in `extraKnownMarketplaces` stehen (Supply-Chain-Risiko, SEC-002)

## Phase 6 — Memory-Logging

Schreibe nach `~/.claude/audit/tool_scout_log.jsonl`:

```json
{"timestamp": "...", "fokus": "...", "candidates_found": N, "auto_installed": [...], "logged_for_manual": [...], "rejected": [...]}
```

Bei `--scheduled`: zusätzlich Memory-Service-Eintrag mit Tag `tool-scout-<YYYY-MM-DD>` damit Re-Runs Duplikate kennen. Wenn Memory-Service offline: silent-skip, nur JSONL-Log.

## Constraints

- **Read-only standardmaessig.** Auto-Install nur bei `--install`.
- **Niemals Tokens/Credentials in Such-Queries.**
- **Konfidenz ehrlich** — wenn Repo seit 6 Monaten kein Commit: max MITTEL.
- **Anticipation begruenden** — keine "weil ich das spannend finde"-Empfehlungen. Immer "der Nutzer hat X, daher Y".
- **Stop bei Duplikaten** — wenn 3 von 5 Funden bereits installiert sind: Such-Run abbrechen, anderer Fokus.

## Scheduled-Modus (cron/Task Scheduler)

Setup-Empfehlung fuer wiederkehrenden Scan:

```powershell
# Wochentlicher Run, Donnerstag 09:00 Berlin (passend zu Lyra Mo 09:00 — staggered)
$action = New-ScheduledTaskAction -Execute "claude" -Argument "/tool-scout ALL --scheduled"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Thursday -At 9am
Register-ScheduledTask -TaskName "tool-scout-weekly" -Action $action -Trigger $trigger
```

(Falls Claude Code CLI nicht direkt cron-faehig: Wrapper-Script mit `claude --headless /tool-scout ALL --scheduled` siehe `~/.claude/scripts/scheduled_tool_scout.ps1`.)

## Versionierung

- **v1.6.0** (2026-10-01): Vertrauens-Check um **Community-Resonanz der letzten 30 Tage** ergänzt
  (`scripts/last30days.py`: Hacker News, GitHub, Reddit-Such-Feed; nur Standardbibliothek, keine
  Schlüssel). Ausgewertet wird die Datei nur über den Agent `untrusted-reader` (nur Read), weil sie
  Fremdtext enthält. REC-Zeile „Vertrauen“ um „Community 30 T“ erweitert. Anlass: des Nutzers Entscheid,
  `/last30days` nicht zu installieren, sondern schlank nachzubauen.
- **v1.5.0** (2026-09-30): Phase 4 um den **Vertrauens-Check** für Skills/Plugins aus Drittquellen
  ergänzt (Installationen, Owner/Original, Stars + Alter, Audit-Spalte von skills.sh: Gen Agent
  Trust Hub, Socket, Snyk). Übernommen aus `find-skills` (`vercel-labs/skills@773fb2c7`), der Skill
  selbst bleibt uninstalliert (schlägt `-g -y` vor). REC-Format um Zeile „Vertrauen“, Auto-Install
  um Audit-Bedingung erweitert. Anlass: TikTok-Auswertung 30.09., Punkt A2.9.
- **v1.3.0** (2026-07-22): Primär-Feeds auf **~40 live-verifizierte Quellen in 3 Tiers** ausgebaut
  (Runde-2-Recherche). Neu u.a.: **OSS-Insight-Collections** (kuratiert + Trend-Signal — MCP Servers/
  Coding Agents/AI Coding Assistants/Agent Skills), Glama-MCP-API (createdAt-Cursor), Smithery-Registry,
  weitere offizielle anthropics-Repos (skills/claude-code-action/claude-cookbooks/courses[master]/
  modelcontextprotocol-servers), VoltAgent-Subagents (23,5k★), mehr GitHub-Topics (claude-code-plugin/
  claude-skill/claude-agent), Anthropic-Sitemap-Diff (kein RSS), smol.ai-AI-News, swyx/Pragmatic/Eugene
  Yan/Hamel-Blogs, lobste.rs, PyPI mcp/fastmcp. `--scheduled` = nur Tier 1. Snapshot-Diff-Regeln für
  nicht-datumssortierte JSON-Directories. YouTube systemisch server-IP-defekt (2 Kanäle bestätigt) →
  skip-not-crash. Beleg: `..._runde2_2026-07-22.md`.
- **v1.2.0** (2026-07-22): Phase 3 um **deterministische Primär-Feeds** erweitert — 11 verifizierte
  Auto-Query-Feeds (WebFetch) als High-Signal-Ergänzung zur TikTok-only-Discovery: claude-code
  Releases, awesome-claude-code CSV+Commits, GitHub-Search-API, MCP-Registry, HN-Algolia,
  punkpeye-MCP, Simon Willison, Latent Space, Alexander Sprogis (GitHub + YouTube). Pro Quelle
  Feed-URL + Delta-Regel + Rate-Limit/Auth-Hinweis (`GITHUB_READONLY_TOKEN` optional). Reddit
  bewusst raus (Netcup-IP-403). Anlass: der Nutzer-Request „TikTok bleibt manuell, zusätzlich
  auto-abgefragte Quellen" (2026-07-22). Recherche-Beleg: `~/projects/Discord_Bots/research/websuche_auto-queryable-claude-code-tool-quellen_2026-07-22.md`.
- **v1.1.0** (2026-05-17): Anticipation-Tabelle um Long-Run/Wake-Up und Token-Optimierung erweitert (passend zu `/wakeup-setup`-Skill + Token-Optimierungs-Refactor). Memory-Service-Offline-Fallback klargestellt (silent-skip statt Crash).
- **v1.0.0** (2026-05-16): Initial release. Anlass: der Nutzer-Request "Claude soll selbstaendig neue Skills/Plugins finden und installieren, dabei in die Zukunft denken." Anticipation-Heuristik basiert auf 6 Workload-Bereichen aus dem Inventar-Audit 2026-05-16.
