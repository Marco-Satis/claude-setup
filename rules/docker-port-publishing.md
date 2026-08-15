# Docker-Port-Publishing (Global Rule)

Auto-applied bei Edits an `docker-compose.yml`, `Dockerfile`, `docker run`-Befehlen und bei
Firewall-Arbeit auf dem netcup-Server.

## Kernregel

Jeder veröffentlichte Container-Port wird an **`127.0.0.1`** gebunden, außer der Dienst soll
nachweislich aus dem Internet erreichbar sein:

```yaml
ports:
  - "127.0.0.1:5678:5678"   # richtig — nur lokal, Reverse-Proxy davor
  - "5678:5678"             # falsch — 0.0.0.0, an UFW vorbei erreichbar
```

## Warum das kein Stil-Thema ist

Docker schreibt seine Regeln **direkt in die DOCKER-iptables-Chain**, die vor den UFW-Ketten
ausgewertet wird. Ein `-p 8080:80` ist damit aus dem Internet erreichbar, **auch wenn `ufw status`
den Port als geschlossen ausweist**. Die Firewall lügt einen dabei nicht an — sie wird schlicht
nicht gefragt. Das betrifft jedes `-p`-Flag und jeden `ports:`-Eintrag ohne Interface-Prefix.

Stand 2026-08-12 auf netcup geprüft: nur `n8n` publisht, und zwar korrekt auf `127.0.0.1:5678`.
Die Regel hält den Zustand, sie repariert ihn nicht.

## Gegenprobe (30 Sekunden)

```bash
docker ps --format '{{.Names}}\t{{.Ports}}'   # alles ohne 127.0.0.1: ist offen
sudo ufw status verbose                        # und weiß nichts davon
```

Beides gehört zusammen gelesen. Die Prüfung läuft zusätzlich als mechanischer Vorlauf in
`/cso` Phase 5 ("Host hardening baseline").

## Wenn ein Dienst wirklich nach außen soll

Nicht den Publish öffnen, sondern nginx als Reverse-Proxy davor und den Container weiter lokal
binden — dann greifen TLS, Auth und die UFW-Regeln für 80/443 wie erwartet. Für Zugriff nur von
der Nutzer Geräten reicht Tailscale (`tailscale serve`), siehe Memory `tailscale-serve-portmap`.
