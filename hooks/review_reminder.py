#!/usr/bin/env python
"""PostToolUse Hook (Edit/Write): Review-Reminder bei sicherheits-/integritäts-
kritischem Code (Harmonist-Idee abgespeckt, 2026-05-24).

Harmonist gated Code-Changes hart (stop-hook REFUSED Turn ohne Review). Das wäre
für der Nutzer Autonomous-Mode zu invasiv (bricht den Flow). Diese abgespeckte Variante:
SOFT-Reminder NACH dem Edit (PostToolUse), kein hartes Gate. Bei Edit an
security/auth/db/RCON/payment-Code wird eine SystemMessage injiziert die an /review
oder /security-audit VOR Deploy erinnert.

Nicht blockierend — der Nutzer/Claude kann ignorieren. Zweck: verhindern dass
sicherheits-relevante Edits stillschweigend deployed werden ohne Review-Gedanken.
"""
from __future__ import annotations

import json
import re
import sys

# File-Patterns die einen Review-Reminder verdienen (case-insensitive).
# Fokus: Auth, Security, DB, Server-Control, Payment, Secrets-Handling.
SENSITIVE_PATTERNS = [
    # Auth / Security
    (r"(^|[/_])auth([/_.]|$)", "Auth-Code"),
    (r"login|session|token|jwt|oauth|password|credential", "Auth/Credential-Code"),
    (r"web/middleware/csrf", "CSRF-Middleware"),
    (r"security|permission|sanitiz|escape", "Security-Code"),
    # DB / Persistence
    (r"modules/database/|db_manager|migrations?/", "DB-Code (SQL-Injection/Migration-Risiko)"),
    # Server-Control / RCON
    (r"rcon|systemd|nginx|sudoers", "Server-Control-Code"),
    # FastAPI Routes (auth-relevant)
    (r"web/routes/.*\.py$|web/app\.py$", "FastAPI-Route (Auth/Validation prüfen)"),
    # Payment / Finance
    (r"payment|invoice|abrechnung|finanz", "Payment/Finanz-Code"),
    # Secret-Handling
    (r"secret|\.env|vault|keepass", "Secret-Handling-Code"),
]


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name not in ("Edit", "Write", "NotebookEdit"):
        sys.exit(0)

    tool_input = data.get("tool_input", {}) or {}
    fp = (tool_input.get("file_path", "") or "").replace("\\", "/")
    if not fp:
        sys.exit(0)

    for pat, label in SENSITIVE_PATTERNS:
        if re.search(pat, fp, re.IGNORECASE):
            msg = (
                f"[REVIEW-REMINDER] Edit an {label}: {fp}\n"
                f"Sicherheits-/integritäts-relevant — vor Deploy /quick-review (Spot) "
                f"oder /security-audit (tief) erwägen. review prüft auch "
                f"Functional-Correctness + Data-Flow-Coverage + Error&Rescue-Map. "
                f"Soft-Reminder, kein Gate — bei Trivial-Edit ignorieren."
            )
            print(json.dumps({"systemMessage": msg}))
            break


if __name__ == "__main__":
    main()
