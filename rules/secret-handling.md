# Secret-Handling Coding-Standards (Global)

Auto-applied bei Edits an `.env`-Pattern, Token-Variablen, Credentials.

## .env-Files
- **NIEMALS in git tracken**
- `.gitignore` Pattern: `config/.env*` (alle Varianten)
- Read-Permission 600
- Pre-Commit-Check via detect-secrets

## Token-Reads
```python
# ✅ GOOD
from utils.config import get_env
token = get_env("DISCORD_TOKEN")

# ❌ BAD - hardcoded
token = "MTI3..."
```

## Token-Logs
- **NIEMALS Token-Werte in Logs ausgeben**
- ✅ `logger.info(f"Token loaded (length: {len(token)})")`
- ❌ `logger.info(f"Token: {token}")`

## Token-Rotation-Workflow
1. Bot offline (`systemctl stop discord-bot-*`)
2. Token in Discord Developer Portal regenerieren
3. Neu in `.env`
4. Bot starten
5. Discord-Audit-Logs für Exposure-Window prüfen

## Git-History-Cleanup nach Leak
```bash
git filter-repo --path config/.env.new --invert-paths
git push --force-with-lease  # nur nach Token-Rotation!
```

## Detect-Secrets Pre-Commit
```bash
detect-secrets scan --baseline .secrets.baseline
git diff --staged | detect-secrets-hook
```

## Hash für Player-Privacy in Logs
```python
import hashlib
def hash_player(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()[:8]

logger.info(f"Blacklist: {hash_player(player_name)} ({player_name[:3]}***) banned")
```

## Anti-Patterns
- ❌ Token in Code-Kommentar
- ❌ Token in URL-Parameter
- ❌ `.env` per Email/Slack/Discord teilen
- ❌ `git push` mit kontaminierter History (vor Token-Rotation)
- ❌ Token im Claude-Chat posten → siehe Section [Token-Posting im Chat (Lesson 2026-05-16)](#token-posting-im-chat-lesson-2026-05-16) unten

## Token-Posting im Chat (Lesson 2026-05-16)

Lesson: der Nutzer postete am 2026-05-16 versehentlich seinen Anthropic-API-Key im Claude-Chat. Resultat: Key in
mindestens 4 Persistenz-Schichten geleakt (Transcript-JSONL, PreCompact-Backup, Anthropic-Server-Logs, ggf. Hook-Logs).
Lehre: Active-Enforcement statt passive Doku-Hoffnung.

**Sicherer Setup-Workflow fuer ENV-Variable (Windows / PowerShell):**

```powershell
# Interaktiv — Wert wird angezeigt aber nicht in PowerShell-History gespeichert
$k = Read-Host "API-Key einfuegen"
[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $k, "User")
$k = $null

# Verifikation (gibt nur True/False, kein Wert)
[bool][Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY', 'User')
```

**Active-Enforcement:**
- `~/.claude/hooks/secret_leak_detector.py` (UserPromptSubmit, seit 2026-05-16)
- Patterns: Anthropic (`sk-ant-api\d+-`), OpenAI (`sk-`/`sk-proj-`), GitHub (`ghp_`/`github_pat_`/`gho_`/`ghs_`), Discord-Bot-Token, AWS (`AKIA`), Slack (`xox?-`), Google (`AIza`)
- Log nach `~/.claude/lessons/leaks.jsonl` (Pattern-Name + Hash, niemals der Wert)
- Nicht-blockierend (der Nutzer kann Prompts senden), aber Claude wird angewiesen den Wert nicht weiterzuverwenden

**Wenn Leak passiert:**
1. SOFORT in der jeweiligen Console (Anthropic / GitHub / Discord) den Key revoken
2. Neuen Key generieren mit anderem Namen
3. Via Read-Host-Workflow als ENV-Variable setzen
4. Optional: Transcript-File (`~/.claude/projects/<project>/<session>.jsonl`) auf `[REDACTED]` patchen oder loeschen
5. Optional: PreCompact-Backups (`~/.claude/backups/`) ebenso pruefen

## Audit-Log-DB
- Plain-Text in DB-File mit 600-Permissions OK (DSGVO-Audit-Trail)
- Logs (journald, *.log) immer Hash + Truncation

## Multi-AI-Keys & Creds (2026-06-04)
Mit dem Multi-AI-Ausbau (Gemini, Codex, Nano Banana) kamen neue Credentials dazu.
Alle gehören in **KeePass** (`Vault.kdbx`), nie in git/Chat/Repo.

| Provider | Credential | Ort | Typ |
|---|---|---|---|
| Gemini-CLI | OAuth Code-Assist | `~/.gemini/oauth_creds.json` + `google_accounts.json` | OAuth (Free-Tier, kein Key) |
| Gemini-API / Nano Banana | `GEMINI_API_KEY` | User-ENV (Registry HKCU\Environment) | API-Key `AIza...` (Prepay=echtes Geld) |
| Codex-CLI | ChatGPT-Plus-OAuth | `~/.codex/auth.json` | OAuth (nutzt Plus-Sub) |

**Regeln:**
- `GEMINI_API_KEY` NUR als User-ENV (via `Read-Host`-Workflow gesetzt, Wert nie im Chat) + **KeePass-Backup**. Bei Leak: in [AI Studio](https://aistudio.google.com) revoken + neu. `secret_leak_detector` kennt das `AIza`-Pattern.
- OAuth-Creds (`~/.gemini/`, `~/.codex/`) nicht committen, nicht syncen (lokale User-Dirs). Bei Kompromittierung: `gemini`/`codex login` neu.
- Usage/Spend via `ai_usage.py`. Nano verbrennt echtes Prepay-Geld → Spend-Guard `NANO_DAILY_USD_CAP` in `nano_banana.py`.
