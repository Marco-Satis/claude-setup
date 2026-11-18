# Rekursive Scans unter Windows: Container-Layer auslassen (Global Rule)

> System Diagnose 17.11.2026 (Bericht `projects-sync/System_Diagnose/WINDOWS_LEAK_BERICHT_2026-11-17.md`,
> wz `pc-system/windows-handle-spruenge-im-system-prozess-ursache-c661`). Gilt am PC für alle Sessions.

## Kernregel

Wer unter Windows rekursiv über `C:\` oder `C:\ProgramData` läuft (Python `os.walk`/`os.scandir`/`pathlib.rglob`,
PowerShell `Get-ChildItem -Recurse`, `dir /s`, `du`, `find`, Speicher- und Bestandsscans), schließt diesen Ordner aus:

```
C:\ProgramData\Microsoft\Windows\Containers
```

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
