#!/usr/bin/env python3
"""Tests fuer hooks/session_snapshot.py und die Snapshot-/Tageslisten-Teile von scripts/zentrale_eingang.py (15.11.2026).

Laufen isoliert: ZENTRALE_DIR/ERR/MARCO_BLOCK/VOLLTEXT_FLAG/MAIL zeigen in ein Temp-Verzeichnis, rc-mail.sh wird durch
ein Fake-Skript ersetzt, das Argumente und RC_MAIL_*-Variablen protokolliert.
Aufruf: python3 -m unittest ~/.claude/hooks/tests/test_session_snapshot.py  (oder direkt ausfuehren)
"""
import datetime
import importlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HOOK = Path.home() / ".claude" / "hooks" / "session_snapshot.py"
SCRIPTS = Path.home() / ".claude" / "scripts"


def lade_hook():
    spec = importlib.util.spec_from_file_location("session_snapshot", HOOK)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.log = t / "mail.log"
        fake = t / "rc-mail.sh"
        fake.write_text("#!/bin/bash\nprintf '%s\\n' \"ARGS:$1|$3\" \"$2\" \"CLICK:${RC_MAIL_CLICK:-}\" "
                        f"\"ACTIONS:${{RC_MAIL_ACTIONS:-}}\" >> '{self.log}'\nexit 0\n")
        fake.chmod(0o755)
        self.mb = t / "MARCO_BLOCK.md"
        self.flag = t / "ntfy_eigen.on"
        self.env = {"ZENTRALE_DIR": str(t / "z"), "ZENTRALE_ERR": str(t / "err.log"), "ZENTRALE_MAIL": str(fake),
                    "ZENTRALE_MARCO_BLOCK": str(self.mb), "ZENTRALE_VOLLTEXT_FLAG": str(self.flag),
                    "ZENTRALE_BUENDEL_SYNC": "1", "ZENTRALE_KEIN_SYSTEMCTL": "1",
                    "ZENTRALE_JETZT": "2026-11-15T12:00:00"}
        self._alt = {k: os.environ.get(k) for k in self.env}
        os.environ.update(self.env)
        sys.path.insert(0, str(SCRIPTS))
        import zentrale_eingang
        self.Z = importlib.reload(zentrale_eingang)

    def tearDown(self):
        for k, v in self._alt.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def snap(self, **kw):
        d = {"name": "Cell Survivor", "ts": datetime.datetime(2026, 11, 15, 12).timestamp(), "host": "netcup",
             "cwd": "$HOME/projects/CellSurvivor", "projekt": "CellSurvivor", "status": "fertig", "art": "",
             "text": "Stand: alles gut.", "session_id": "abc", "link": "", "marco_vor_s": 3600}
        d.update(kw)
        return d


class StatusErkennung(unittest.TestCase):
    def setUp(self):
        self.h = lade_hook()

    def test_faelle(self):
        f = [
            ("Plan v2 ist fertig.\n\nSoll ich die Fragen als Entwurf formulieren?", "braucht-marco"),
            ("Tabelle oben.\n\nAntworte mit a oder b.", "braucht-marco"),
            ("Danach „durch“ schreiben. Dann prüfe ich A und B.", "braucht-marco"),
            ("Neu im der Nutzer-Block ist MB172. Wenn du ihn freigibst, protokolliert Windows Fehler.", "braucht-marco"),
            ("Die drei Punkte liegen im der Nutzer-Block für Sonntag, ich frage dich also nicht direkt.", "fertig"),
            ("Ich habe dir zwei Dinge gesammelt. Bis Sonntag habe ich keine weiteren Fragen an dich.", "fertig"),
            ("Der Krisentest rechnet noch. Wenn er fertig ist, prüfe ich das Ergebnis.", "arbeitet"),
            ("Diese Session wartet ohnehin, bis Nutzerin A und Nutzer B antworten.", "wartet-auf-ereignis"),
            ("Commit 1234 ist drin, Tests grün.", "fertig"),
            ("**Nächste Aktion: keine von dir nötig.** Frag einfach, wenn du etwas brauchst.", "fertig"),
        ]
        for text, soll in f:
            self.assertEqual(self.h.status_erkennen(text)[0], soll, text)

    def test_hintergrund_und_cron(self):
        self.assertEqual(self.h.status_erkennen("Stand gesichert.", background_tasks=[{"id": 1}])[0], "arbeitet")
        self.assertEqual(self.h.status_erkennen("Stand gesichert.", session_crons=[{"id": 1}])[0],
                         "wartet-auf-ereignis")

    def test_art(self):
        self.assertEqual(self.h.status_erkennen("Mit einem Ja ziehe ich das nach, ein Commit.")[1], "Freigabe")
        self.assertEqual(self.h.status_erkennen("Welche Variante nimmst du?\n\nSoll ich A nehmen?")[1], "Frage")

    def test_umgebung_link_nur_mit_cse(self):
        h = self.h
        h._vorfahren = lambda max_n=8: [["claude", "--print", "--sdk-url", "x", "--session-id", "cse_017hXmcJyMYqi6nW"],
                                        ["claude", "remote-control", "--name", "Setup Server", "--continue"]]
        u = h.umgebung("$HOME/projects/Skills_&_Co")
        self.assertEqual(u["name"], "Setup Server")
        self.assertEqual(u["link"], "https://claude.ai/code/session_017hXmcJyMYqi6nW")
        self.assertFalse(u["headless"])
        h._vorfahren = lambda max_n=8: [["claude", "-p", "--no-session-persistence", "Auftrag"]]
        self.assertTrue(h.umgebung("/tmp")["headless"])


class SnapshotWeiterleitung(Basis):
    def eingang(self):
        return [e for e in self.Z.lesen() if e.get("unterart") == "snapshot"]

    def test_wechsel_meldet_einmal(self):
        Z = self.Z
        self.assertEqual(Z.snapshot_aufnehmen(self.snap()), "gespeichert")
        r = Z.snapshot_aufnehmen(self.snap(status="braucht-marco", art="Frage", text="Soll ich neu starten?"))
        self.assertTrue(r.startswith("gemeldet E"), r)
        self.assertEqual(Z.snapshot_aufnehmen(self.snap(status="braucht-marco", art="Frage")), "gleich")
        self.assertEqual(len(self.eingang()), 1)
        e = self.eingang()[0]
        self.assertEqual((e["klasse"], e["titel"], e["projekt"]),
                         ("ENTSCHEIDUNG", "Session wartet auf der Nutzer — CellSurvivor", "CellSurvivor"))
        log = self.log.read_text()
        self.assertIn("Cell Survivor braucht dich (Frage)", log)
        self.assertNotIn("neu starten", log)          # Vorlagentext: kein Freitext im oeffentlichen Topic

    def test_marco_aktiv_unterdrueckt(self):
        r = self.Z.snapshot_aufnehmen(self.snap(status="braucht-marco", marco_vor_s=120))
        self.assertEqual(r, "unterdrueckt")
        self.assertEqual(self.eingang(), [])

    def test_neue_runde_nach_marco_antwort(self):
        Z = self.Z
        t0 = self.snap()["ts"]
        Z.snapshot_aufnehmen(self.snap(status="braucht-marco"))
        # der Nutzer hat danach geschrieben (vor 20 min, also nach der Meldung), Session fragt wieder
        r = Z.snapshot_aufnehmen(self.snap(status="braucht-marco", ts=t0 + 3600, marco_vor_s=1200))
        self.assertTrue(r.startswith("gemeldet"), r)

    def test_verlassen_erledigt_eintrag(self):
        Z = self.Z
        Z.snapshot_aufnehmen(self.snap(status="braucht-marco"))
        Z.snapshot_aufnehmen(self.snap(status="fertig"))
        self.assertEqual(self.eingang()[0]["status"], "erledigt")

    def test_denylist_bleibt_vertraulich(self):
        self.flag.write_text("")
        self.Z.snapshot_aufnehmen(self.snap(name="UYM-Setup-Server", projekt="uym-setup", cwd="/x/uym-setup",
                                            status="braucht-marco", text="Kundendaten XY"))
        log = self.log.read_text()
        self.assertNotIn("Kundendaten", log)
        self.assertNotIn("UYM", log)
        self.assertIn("vertraulich", log)

    def test_volltext_und_link(self):
        self.flag.write_text("")
        link = "https://claude.ai/code/session_017hXmcJyMYqi6nWDbbPo2pR"
        self.Z.snapshot_aufnehmen(self.snap(status="braucht-marco", text="Darf ich den Bot neu starten? token=geheim123",
                                            link=link))
        log = self.log.read_text()
        self.assertIn("Cell Survivor braucht dich (Frage): Darf ich den Bot neu starten?", log)
        self.assertNotIn("geheim123", log)
        self.assertIn("CLICK:" + link, log)
        self.assertIn('"action": "view"', log)

    def test_link_nur_claude_ai(self):
        self.Z.snapshot_aufnehmen(self.snap(status="braucht-marco", link="https://evil.example/x"))
        self.assertIn("CLICK:\n", self.log.read_text())

    def test_sessions_tabelle(self):
        self.Z.snapshot_aufnehmen(self.snap(status="arbeitet", text="**Stand:** Import läuft noch."))
        self.Z.snapshot_aufnehmen(self.snap(name="Trading", projekt="Trading", status="braucht-marco",
                                            marco_vor_s=10))
        t = self.Z.sessions_tabelle()
        zeilen = t.splitlines()
        self.assertTrue(zeilen[1].startswith("Trading"))   # braucht-marco zuerst
        self.assertIn("Stand: Import läuft noch.", t)


class Tagesliste(Basis):
    MB = """| | ID | Projekt | Was | Dauer | Warum | gemeldet |
|---|---|---|---|---|---|---|
| [ ] | MB1 | Setup | sudo-Runde T1 | 25 min | Sicherheit (Root-Weg) | 13.11. |
| [x] | MB2 | Setup | erledigt | 2 min | x | 13.11. |
| [ ] | MB9 | trading | „D ja“ für Rollout nach Auswertung (G177, 16.11.) | 2 min | sonst bleibt D liegen | 13.11. |
| [ ] | MB14 | Games/Apex | Ability binden: A oder B | 2 min | unbenutzbar | 13.11. |
| [ ] | MB44 | uym | Hetzner-Konsole 2FA ablesen | 5 min | offener root-Login | 13.11. |
| [ ] | MB50 | n8n-stack | Findings abhaken | 20 min | Few-Shot | 13.11. |
| [D] | MB8 | trading | entschieden | 1 min | x | 13.11. |
"""

    def test_liste(self):
        self.mb.write_text(self.MB, encoding="utf-8")
        z = self.Z.tagesliste()
        txt = "\n".join(z)
        self.assertIn("der Nutzer-Block offen: 5 (Sicherheit 2)", txt)
        self.assertEqual(z[1], "- MB1 Setup Server · Sicherheit · 25 min")   # Sicherheit zuerst
        self.assertIn("- MB9 Trading · Freigabe · 2 min", txt)
        self.assertIn("- MB14 anderes · Entscheidung · 2 min", txt)
        self.assertIn("- 1 vertraulich", txt)                                 # uym nur als Zahl
        self.assertNotIn("Hetzner", txt)
        self.assertIn("- 16.11. MB9 Trading", txt)
        self.assertNotIn("sudo", txt)                                         # Vorlagentext ohne Flag

    def test_volltext(self):
        self.mb.write_text(self.MB, encoding="utf-8")
        self.flag.write_text("")
        txt = "\n".join(self.Z.tagesliste())
        self.assertIn("MB1 Setup Server · Sicherheit · 25 min: sudo-Runde T1", txt)
        self.assertNotIn("Hetzner", txt)

    def test_digest_enthaelt_liste_und_sessions(self):
        self.mb.write_text(self.MB, encoding="utf-8")
        self.Z.snapshot_aufnehmen(self.snap(status="braucht-marco", art="Freigabe"))
        titel, text = self.Z.digest_text({"aufgaben": 2, "stillstand": []})
        self.assertIn("Sessions brauchen dich: 1", text)
        self.assertIn("- Cell Survivor (Freigabe, seit 0 min)", text)
        self.assertIn("MB1 Setup Server", text)
        self.assertLess(len(text), 3500)


class HookEndeZuEnde(Basis):
    def test_laufzeit_und_datei(self):
        data = {"session_id": "test-snap-1", "cwd": "$HOME/projects/CellSurvivor", "hook_event_name": "Stop",
                "stop_hook_active": False, "last_assistant_message": "Fertig. Soll ich den Bot neu starten?"}
        env = dict(os.environ, CLAUDE_SESSION_NAME="Testsession Snapshot", HOME=str(Path.home()))
        dauer = []
        for _ in range(5):
            t = time.perf_counter()
            r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(data), capture_output=True, text=True,
                               env=env, timeout=10)
            dauer.append(time.perf_counter() - t)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, "")
        p = Path(self.env["ZENTRALE_DIR"]) / "sessions" / "Testsession_Snapshot.json"
        d = json.loads(p.read_text())
        self.assertEqual((d["status"], d["art"]), ("braucht-marco", "Freigabe"))
        self.assertEqual(oct(p.stat().st_mode & 0o777), "0o600")
        med = sorted(dauer)[2]
        print(f"\n  Hook-Laufzeit Median {med * 1000:.0f} ms (5 Laeufe, max {max(dauer) * 1000:.0f} ms)")
        self.assertLess(med, 0.2)

    def test_kaputte_eingabe(self):
        r = subprocess.run([sys.executable, str(HOOK)], input="kein json", capture_output=True, text=True, timeout=10)
        self.assertEqual((r.returncode, r.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
