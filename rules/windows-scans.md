# Rekursive Scans unter Windows: Container-Layer auslassen (Global Rule)

> System Diagnose 17.11.2026 (Bericht `projects-sync/System_Diagnose/WINDOWS_LEAK_BERICHT_2026-11-17.md`,
> wz `pc-system/windows-handle-spruenge-im-system-prozess-ursache-c661`). Gilt am PC für alle Sessions.

## Kernregel

Wer unter Windows rekursiv über `C:\` oder `C:\ProgramData` läuft (Python `os.walk`/`os.scandir`/`pathlib.rglob`,
PowerShell `Get-ChildItem -Recurse`, `dir /s`, `du`, `find`, Speicher- und Bestandsscans), schließt diesen Ordner aus:

```
C:\ProgramData\Microsoft\Windows\Containers
```

Das gilt auch für Suchwerkzeuge, nicht nur für Skripte: das Grep- und Glob-Werkzeug von Claude Code mit einem Pfad
unter `C:\ProgramData` oder `C:\`, `grep -r`, `rg` (ripgrep) und Codex-Suchen. Belegt 15.11.2026 07:10: Ein Grep-Aufruf
mit Pfad `C:\ProgramData` erzeugte einen Handle-Sprung. Am PC sperrt zusätzlich eine Leseregel in der `settings.json`
(`permissions.deny` für den Containers-Ordner, genaue Schreibweise siehe PC-`settings.json`; Windows-Pfade werden für die
Regel in POSIX-Form gebracht) den Ordner; das Grep-Werkzeug gibt
Leseverbote als `--iglob` an ripgrep weiter (Claude Code 2.1.325). Suche gezielt im Unterordner, nie ab `C:\ProgramData`.

Seit 18.11.2026 22:24 meldet ein Wächter im SystemLogger am PC hohe Handle-Stände (ab 150.000 ENTSCHEIDUNG, ab 400.000
ALARM, Sprung +50.000 in 15 min) an die Zentrale (wz `pc-system/handle-waechter-im-systemlogger-meldet-hohe-system-f1ad`).
Die Windows-Sandbox bleibt installiert (der Nutzer 18.11.2026).

## Warum

Jede Erstöffnung eines Ordners im Container-Basis-Layer (`…\Containers\Layers\<guid>\Files`) legt im System-Prozess
einen File-Handle an, der bis zum Neustart bleibt (Treiber vermutlich `wcifs.sys`). Ein Durchlauf erzeugt Hunderttausende
Handles und mehrere GB Kernel-Pool (belegt 12.–16.11.2026: bis 1,15 Mio. Handles, ~6 GB). Das echte `C:\Windows\WinSxS`
ist nicht betroffen. Nach Windows-Updates baut Windows den Layer neu; ein zeitnaher Neustart räumt die Handles ab.

## Beispiele

```python
for root, dirs, files in os.walk("C:\\"):
    dirs[:] = [d for d in dirs if os.path.join(root, d).lower() != r"c:\programdata\microsoft\windows\containers"]
```

PowerShell: `Get-ChildItem -Recurse` steigt auch mit `-Exclude` oder nachgeschaltetem `Where-Object` in den Ordner
hinab, der Handle entsteht also trotzdem. Deshalb eigene Rekursion, die den Ordner vor dem Öffnen überspringt:

```powershell
function Walk($p) {
  if ($p -like 'C:\ProgramData\Microsoft\Windows\Containers*') { return }
  Get-ChildItem -LiteralPath $p -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $_; if ($_.PSIsContainer) { Walk $_.FullName } }
}
```
