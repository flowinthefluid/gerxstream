<p align="center">
  <img src="resources/clearlogo.png" alt="GerXStream" width="420">
</p>

<h1 align="center">GerXStream für Kodi</h1>
<p align="center"><b>Eine Suche. Alle Quellen. Ein Klick.</b></p>

<p align="center">
  <img src="https://img.shields.io/badge/Kodi-22%20Piers-5ad?style=flat-square" alt="Kodi 22">
  <img src="https://img.shields.io/badge/Kodi%2021-Omega%20unterstützt-3a7?style=flat-square" alt="Kodi 21">
  <img src="https://img.shields.io/badge/Python-3-blue?style=flat-square" alt="Python 3">
  <img src="https://img.shields.io/badge/Quellen-36-7c3aed?style=flat-square" alt="36 Quellen">
  <img src="https://img.shields.io/badge/Lizenz-GPL--3.0--only-green?style=flat-square" alt="GPL-3.0-only">
</p>

***

## Ein Suchfeld. Und du bist fertig.

Du weißt, wie es sonst läuft: Eine Seite hat die Serie, aber nur Staffel 1.
Die nächste hat Staffel 2, dafür kein Deutsch. Die dritte will erst ein Captcha,
dann einen Account. Zwanzig Minuten später schaust du immer noch nichts.

**GerXStream dreht das um.** Du tippst einmal, GerXStream fragt alle
angebundenen Quellen **gleichzeitig** und legt dir das Ergebnis als fertige
Kodi-Liste hin — mit Cover, Beschreibung, Bewertung, Cast und Serienstatus.
Du wählst aus. Mehr ist es nicht.

***

## Was drin steckt

| | |
|---|---|
| 🔎 **Globale Parallelsuche** | Alle Quellen auf einmal, sauber gedrosselt und jederzeit abbrechbar — Kodi bleibt bedienbar, auch wenn eine Seite hängt |
| 🎬 **Echte Metadaten** | Cover, Fanart, Plot, Bewertung, Laufzeit, Genres, Cast, Erstausstrahlung und Serienstatus über TMDB |
| 🧩 **36 Quellen, modular** | Jede Webseite ist ein eigenes, austauschbares Site-Plugin — kaputte Quelle raus, neue rein, ohne den Rest anzufassen |
| 🗂️ **Kategorien statt nur "Neu"** | Genres, Sammlungen (MCU, Star Wars, …), Charts, Jahrzehnte und angesagte Schauspieler — TMDB-gespeist, wirkt über alle Quellen gleichzeitig |
| 🎯 **Gezielt statt global** | Nur eine bestimmte Seite durchstöbern? Jede Quelle hat ihr eigenes Menü mit Genres, Jahren und A–Z |
| 📺 **Mediatheken & Dokus** | Nicht nur Filme und Serien: Doku-Quellen und Kinderinhalte sind eigene Bereiche |
| ⬇️ **Download & Weiterleitung** | Direkter Download oder Übergabe an JDownloader, JDownloader 2, MyJDownloader oder pyLoad |
| 🛡️ **Sicherheit ohne Sternchen** | Striktes URL-Routing, TLS-Prüfung aktiv, kein `eval()` auf Fremddaten — Details unten |
| 🇩🇪 **Deutsch zuerst** | Oberfläche, Dialoge und Fehlermeldungen auf Deutsch, Englisch als Fallback |
| ⚡ **Kodi 22 „Piers"** | Auf die aktuelle Kodi-Generation gebaut — und auf Kodi 21 „Omega" vollständig nutzbar |

***

## GerXStream ist **nicht** xStream

Das ist der wichtigste Satz in dieser Datei. GerXStream ist kein Reskin und kein
Fork, der ein Logo tauscht. Der Code wurde Befund für Befund auseinandergenommen,
geprüft und neu aufgebaut — **68 dokumentierte Befunde, jeder einzelne
geschlossen und im [Befundkatalog](docs/BEFUNDE.md) mit dem zugehörigen Commit
belegt.**

**Was vorher kaputt war und es jetzt nicht mehr ist:**

- 🔴 **Fremdcode-Ausführung über die URL.** Ein `eval()` auf einem
  URL-Parameter ließ jedes andere Addon, jeden Favoriteneintrag und jeden
  Webinterface-Aufruf beliebigen Python-Code ausführen. Dazu ein ungefiltertes
  `__import__` auf den `site`-Parameter: **52 Module** waren von außen
  erreichbar, darunter ein Killswitch, der das Addon löschte. Heute: feste
  Whitelist für Module *und* Einstiegsfunktionen, sauberer Abbruch mit
  Logeintrag statt stillem Fallback.
- 🔴 **TLS-Prüfung war komplett aus.** `CERT_NONE` für *allen* Verkehr —
  Scraper, TMDB, Captcha. Zusammen mit `eval()` auf den Antwortdaten war das
  Codeausführung per Man-in-the-Middle. Heute: Prüfung an, Ausnahme nur pro
  Quelle, ausdrücklich einzuschalten und mit Warnung im Log.
- 🔴 **Zip-Slip im Update-Pfad.** Ein Update-Archiv aus einem frei
  konfigurierbaren Repo durfte über `..`-Einträge überall ins Dateisystem
  schreiben. Heute: Zielpfade normalisiert und gegen das Wurzelverzeichnis
  geprüft.
- 🔴 **Rund 100 hartcodierte Zugangsdaten** in einer vierfach
  base64-verschachtelten `exec()`-Datei. Ersatzlos gelöscht, bevor das Repo
  überhaupt angelegt wurde.
- 🔴 **Nicht installierbar.** Eine nicht-optionale Abhängigkeit zeigte auf ein
  Repository, das es nicht mehr gibt (404) — Kodi bricht die Installation in so
  einem Fall vollständig ab. Entfernt.

**Und was einfach nicht mehr abstürzt:** Wiedergabe-Callbacks auf
Python-3.14-Basis, Fortschrittsdialoge, die sich auch im Fehlerfall schließen,
Downloads ohne `Content-Length`, hängende Threads beim Beenden von Kodi, tote
Python-2-Reste im heißen Pfad, Genres, die nie gesetzt wurden, Info-Dialoge, die
leer blieben — alles einzeln gefunden, einzeln behoben, einzeln committet.

**Neues Coding-Konzept.** Jede Quelle spricht ausschließlich über eine
gemeinsame GUI- und HTTP-Abstraktion — kein Site-Plugin fasst Kodis API oder das
Netzwerk direkt an. Das klingt nach Kleinkram, ist aber der Grund, warum eine
kaputte Quelle heute nur sich selbst zerlegt und nicht den Rest des Addons.
Timeouts, TLS und Caching liegen an genau einer Stelle. Die Regeln dafür stehen
verbindlich im [Coding-Plan](docs/CODING-PLAN.md) — samt der Sicherheitsregeln,
die für neuen Code nicht verhandelbar sind.

***

## Umstieg von xStream: du musst nichts tun

Beim ersten Start übernimmt GerXStream deine bisherigen Daten automatisch —
Einstellungen, Quellen-Datenbank, Cookies und Cache:

- Läuft **einmal**, beim ersten Start, ohne Nachfrage und ohne Zutun.
- Vorhandene Dateien im Ziel werden **nie** überschrieben.
- Deine alte Installation wird **nicht** angefasst — du kannst beides parallel
  behalten, bis du sicher bist.
- Der Lauf wird per Markerdatei dokumentiert, damit er sich nicht wiederholt.

Voraussetzung ist nur, dass die Daten der früheren xStream-Installation noch
vorhanden sind. Ist zusätzlich das alte Addon noch installiert, weist dich
GerXStream einmalig darauf hin. Details in [INSTALL.md](INSTALL.md).

***

## Los geht's

1. **ResolveURL installieren** — GerXStream benötigt `script.module.resolveurl`
   (Mindeststand `5.1.208`). Solange kein eigenes Repo verdrahtet ist, muss das
   ResolveURL-Repo vorher in Kodi hinzugefügt werden.
2. **GerXStream installieren** — als ZIP über *Addons → Aus ZIP-Datei installieren*.
3. **Starten.** Die Datenübernahme läuft von selbst.

Die ausführliche Fassung mit allen Voraussetzungen steht in [INSTALL.md](INSTALL.md).

***

## Kommt als Nächstes

Ehrlich gekennzeichnet: Das hier ist geplant, aber **noch nicht eingebaut**.

- ⭐ **Favoriten-Engine mit echten Ordnern** — Ordner *und* Unterordner, frei
  benennbar, zum Sortieren deiner Favoriten wie in einem Dateimanager. Statt
  einer flachen Liste, die ab dem fünfzigsten Eintrag unbrauchbar wird.
- 📡 **IPTV** mit direkten Adressen.
- 🌦️ **Webcams für Live-Wetter** (MJPEG, HLS, Standbilder).
- 🔴 **Livestreams** über `inputstream.adaptive`; für echtes Live-TV mit EPG per
  M3U und XMLTV, konsumiert von `pvr.iptvsimple`.

Die Architektur ist dafür bereits offen gehalten — das ist der Grund, warum
manche Dinge im Code allgemeiner gelöst sind, als sie heute sein müssten.

***

## Mitentwickeln

Neue Quelle anbinden oder an der Oberfläche mitbauen? Der technische Überblick,
die Konventionen für Site-Plugins und die verbindlichen Sicherheitsregeln stehen
in **[docs/CODING-PLAN.md](docs/CODING-PLAN.md)**. Der vollständige
Befundkatalog mit Status und Commit je Punkt liegt in
**[docs/BEFUNDE.md](docs/BEFUNDE.md)**.

Vor jedem Commit müssen diese beiden Kommandos sauber durchlaufen:

```powershell
python -W error::SyntaxWarning -m compileall -q -f -x "\.tmp|design|__pycache__" .
python -m pyflakes .
```

***

## Rechtliches

GerXStream ist eine **Suchmaschine** und hostet keine Inhalte. Die Site-Plugins
stellen ausschließlich die Verknüpfung zur jeweiligen Webseite her. Der dort
bereitgestellte Inhalt steht in keinerlei Bezug zu GerXStream oder den
Entwickler:innen. Was damit abgerufen wird, liegt in der Verantwortung der
Nutzerin oder des Nutzers.

Lizenz: **GPL-3.0-only**, siehe [license.txt](license.txt).
