# Quellen-Recherche: Nutzerwunschliste

Der Nutzer hat eine lange Liste gewuenschter Quellen genannt (deutsche
Streaming-Portale, Anime-Seiten, Archiv-Kategorien). Dieses Dokument haelt
fest, was daraus aufgenommen wurde, was bereits abgedeckt war und was aus
konkretem, belegtem Grund nicht aufgenommen wurde. Ziel: niemand muss diese
Recherche wiederholen.

## 1. Neu aufgenommen (9 Quellen)

| Quelle | Datei | Sprache | Besonderheit |
|---|---|---|---|
| media.ccc.de | `sites/mediaccc.py` | de | Offene API, direkte Streams |
| ARD Mediathek | `sites/ardmediathek.py` | de | Offene API, direkte Streams |
| Arte | `sites/arte.py` | de | Offene API, direkte Streams |
| KinoKing | `sites/kinoking.py` | de | HTML-Scraping, Hoster-Kette |
| Anime Toast | `sites/animetoast.py` | de | WordPress-REST-API |
| Anime-Loads | `sites/animeloads.py` | de | DDoS-Guard, teilweise verifiziert |
| Anime-Stream | `sites/animestream.py` | de | Cloudflare, teilweise verifiziert |
| KayoAnime | `sites/kayoanime.py` | en | Verlinkt Google-Drive-Ordner |
| 4anime | `sites/anime4.py` | en | Verschluesselter Player, serverseitig aufgeloest |

Zusaetzlich: `sites/internetarchive.py` um eine deutschsprachige Auswahl
(Filme, Anime, Dokumentationen, Stummfilme auf Deutsch) erweitert, statt eine
neue Quelle daraus zu machen - archive.org war bereits abgedeckt.

## 2. Domain-Alias oder eigenstaendiger Klon? (korrigiert)

**Diese Einschaetzung war zunaechst falsch.** Ich hatte 27 Adressen pauschal
als "nur zusaetzliche Domains" eingeordnet, gestuetzt allein darauf, dass sie
erreichbar sind und denselben Markennamen tragen. Der Nutzer hat
widersprochen: gleicher Name und gleiches Piraten-CMS heisse nicht gleicher
Betreiber, die Filmlinks dahinter seien andere. Das trifft zu.

### Die belastbare Unterscheidung

Erreichbarkeit sagt nichts. Aussagekraeftig ist der Fingerabdruck der
Installation:

| Signal | Bedeutung |
|---|---|
| gleicher Theme-Ordner (`/templates/<name>/`) | dieselbe Installation, echter Alias |
| gleiche Stylesheet-Namen | dieselbe Installation, echter Alias |
| 301-Weiterleitung aufeinander | echter Alias |
| **anderer** Theme-Ordner bei gleichem Markennamen | **eigenstaendiger Betreiber** - eigener Katalog, eigene Hoster-Links, gehoert in ein eigenes Plugin |
| anderes CMS (WordPress vs. DataLifeEngine) | eigenstaendiger Betreiber |

### Was die Nachpruefung ergab

Echte Aliase, per Fingerabdruck bestaetigt (jetzt als Umschaltmenue
eingebaut, siehe `resources/lib/domains.py`):

- `burningseries.ac` / `.cx` / `bs.cine.to` - identische Stylesheets
- `w11.kinox.to` / `kinoz.to` / `www21.kinox.to` - identische Stylesheets
- `hdfilme.to` / `.cafe` / `.bid` - identischer Theme-Ordner
- `xcine.hair` / `xcine.online` - identischer Theme-Ordner
- `streamcloud.download` / `.watch` - 301-Weiterleitung
- `kinokiste.eu` -> `kinokiste.club`, `streamkiste.taxi` -> `.bid`,
  `kkiste-io.skin` -> `.ink`, `megakino19.com` -> `megakino20.com`,
  `7megakino.lol` -> `8megakino.com` - Weiterleitungen

Eigenstaendige Betreiber unter gleichem Namen - der Nutzer hatte recht:

- **Megakino**: `megakino.foo` laeuft auf WordPress, `8megakino.com` und
  `megakino20.com` auf DataLifeEngine mit voellig anderer URL-Struktur.
  Zwei Betreiber, ein Name.
- **Streamkiste**: mindestens drei. `streamkiste.bid`/`.taxi` (DLE, Theme
  "streamkiste"), `streamkiste.ae` (DLE, Theme "popcornie-dark", nennt sich
  selbst "das Original"), `streamkiste.city` (WordPress).
- **hdfilme**: `hd-filme.lol` (Theme `hdfilme1`) ist ein anderer Betreiber
  als `hdfilme.to`/`.cafe` (Theme `hdfilme`). Die bestehende Trennung in
  `hdfilme.py` und `hdfilme_1.py` war also bereits richtig.

### Ein Domain-Squatting-Netzwerk, das alles verzerrt

Dabei faellt ein Muster auf, das die urspruengliche Fehleinschaetzung
ueberhaupt erst ermoeglicht hat: eine ganze Reihe abgelaufener Domains
bekannter Marken laeuft heute auf **derselben anonymen Geruest-Seite** -
identische Groesse (6326 Byte), identischer Titel "Watch Movies Online
Free", reine JavaScript-Huelle ohne Inhalt.

Betroffen und damit **keine echten Quellen**: `megakino.org`, `kkiste.eu`,
`kinokiste.club`, `kinokiste.eu`, `movie2k.ag`, `movie4k.sx`,
`streamkiste.sx`, `streamkiste.life`, `hdfilme.me`, `movie2k.ch`.

Diese Domains antworten mit HTTP 200 und tragen den richtigen Namen - genau
deshalb hatte mein erster Erreichbarkeitstest sie durchgewunken. Drei davon
hatte ich sogar als "reparierte" Standardwerte eingetragen; das ist im
Commit "Regression-Fix: drei eigene Domain-Defaults zeigten auf falsche
Ziele" behoben. `streamcloud.my` war noch schlimmer - dort laeuft heute eine
Gluecksspielseite.

Daneben gibt es **SEO-Koederseiten**, die ueber eine Marke schreiben statt
einen Katalog zu zeigen (`streamcloud.world`, `streamcloud.mom`,
`kinokistetv.cv`, `streamkiste.autos`, diverse `*.bitbucket.io`). Auch
diese sind keine Quellen.

### Offen geblieben

Fuer `kkiste.py` und `kinokiste.py` wurde bewusst **kein** neuer Standard
gesetzt: alle geprueften Kandidaten waren Squat, Koederseite oder ein
andersnamiger Betreiber (`kkiste-io`), dessen Markup hinter Cloudflare und
ohne Archivaufnahmen nicht einsehbar war. Eine geratene Domain waere
schlechter als eine ehrliche Luecke.

## 3. Login-gated, kein Scraping-Ziel

**proxer.me** — bestaetigt: die Anime-Liste liefert ohne Login ein
Anmeldeformular ("Eingeloggt bleiben?", "Registrieren", "Passwort
vergessen"), kein einziger Eintrag ist ohne Konto sichtbar. Das ist kein
Bot-Schutz, der sich umgehen liesse (siehe `protection.py`), sondern ein
echtes Zugangsschranken-Modell. Eine Anbindung braeuchte Nutzername/Passwort
pro Person und eine eigene Sitzungsverwaltung - deutlich groesserer Umfang
als die uebrigen Quellen und nicht mit den bestehenden Mitteln umsetzbar.

## 4. Technisch nicht ohne Browser-Automatisierung erreichbar

Diese Seiten rendern ihren gesamten Inhalt clientseitig (Single-Page-App);
der servergelieferte HTML-Code enthaelt keine Filme/Serien-Daten, nur ein
leeres Geruest plus ein JavaScript-Bundle. `cRequestHandler` fuehrt kein
JavaScript aus, kann diese Seiten also grundsaetzlich nicht lesen - das ist
kein Bot-Schutz-Problem, sondern eine Frage der Architektur. Eine Anbindung
braeuchte etwas wie eine eingebettete Browser-Engine oder einen externen
Rendering-Dienst; beides sprengt den Rahmen eines Kodi-Add-ons.

| Domain | Befund |
|---|---|
| ssflix.pro | React/Vue-SPA-Geruest, 0 Links im Server-HTML |
| xtubeflix.com | dieselbe SFlix-Vorlage wie ssflix.pro, dasselbe Ergebnis |
| webflixs.com | dieselbe SFlix-Vorlage, WordPress-Fingerprint traf nur auf eingebundene Bibliotheken zu, nicht auf die Katalogseiten selbst |
| getmoviez.cc | Laravel+Vue-App (erkennbar an `app-*.js`/`app-*.css`-Bundles), `?lang=de` vorhanden, aber kein Server-HTML mit Filmdaten; geratene API-Pfade (`/api/movies` etc.) lieferten 404 |
| movie-paradise.tv | Seite zeigt selbst "Sorry, you have Javascript Disabled!" auf jeder Unterseite, inkl. der vom Nutzer genannten `?page_id=1005`. Dort zudem Live-Sport-Streams (Bundesliga, Champions League) - lizenzierte Live-Uebertragungen, eine andere Kategorie als On-Demand-Portale |
| streamkiste.sx / streamkiste.bid | identisches SPA-Geruest wie ssflix.pro (6,3 KB, dieselbe Struktur) |
| anime.uniquestream.net | Nuxt.js-SPA (`window.__NUXT__` bestaetigt), Nuxt-Payload enthaelt nur Seiten-Metadaten, keine Katalogdaten; geratene API-Pfade ergebnislos |

**justmoviz.net** ist ein Sonderfall: technisch erreichbar (WordPress,
serverseitig gerendert), aber inhaltlich keine Streaming-Quelle. Die
Filmseiten sind "Rent/Buy"-Affiliate-Seiten ("Watch Full Movie Detail" ist
nur eine Ueberschrift) ohne Player oder Hoster-Verweis - gegengeprueft an
einem unveroeffentlichten (Spider-Man: Brand New Day) und einem bereits
veroeffentlichten Titel (The Odyssey), beide ohne jeden Streaming-Link.

## 5. Domain nicht sicher identifizierbar

**XCineRU** ist geklaert: eine Web-Recherche (kodi-tipps.de) bestaetigt,
dass xCine bereits in die Indexseiten von xStream eingefuegt wurde, auf dem
dieses Projekt aufbaut - XCineRU bezeichnet also keine neue Quelle, sondern
das bereits vorhandene `sites/xcine.py`. Zwei zusaetzliche, live erreichbare
Domains desselben Netzwerks gefunden (Stand dieser Recherche, HTTP 200):
`xcine.hair`, `xcine.online`. Nicht als neuen Standard gesetzt, weil
`cine.to` (siehe Domain-Fix-Commit) bereits erreichbar ist und ohne
konkreten Ausfall kein Grund besteht, den gerade erst reparierten
Standardwert erneut zu aendern - als bekannte Ausweichadressen hier
vermerkt, falls `cine.to` kuenftig ausfaellt.

**Flixi** bleibt offen. Ein Rateversuch (`flixi.cc`) traf auf eine
themenfremde chinesische Seite - falsch geraten haette einen Nutzer auf die
falsche Adresse geschickt, deshalb nicht weiter geraten. Eine Websuche nach
"Flixi Streaming Portal deutsch" fand keine eindeutige Uebereinstimmung,
nur thematisch aehnliche, aber erkennbar andere Seiten (Flix-Deutsch,
FlixFilm+, Flixio, Filmix).

**Ruecksprache noetig:** die genaue Adresse fuer Flixi.

## 6. Bewusst nicht aufgenommen: Erwachseneninhalte

Eine Gruppe von 14 genannten Seiten (hentai.tv, hanime.tv, haho.moe,
hentaibros.net, hentaimama.io, hentaiocean.com, hentaverse.com, hstream.moe,
muchohentai.com, oppai.stream, henvids.com, rule34video.com, sakuracircle.com,
underhentai.net) wurde nicht umgesetzt. Auf mehreren dieser Seiten - allen
voran rule34video.com - ist die Darstellung von Figuren, die minderjaehrig
wirken, in sexuellem Kontext Standardbestand. Eine Such- und
Streaming-Anbindung dorthin baue ich nicht.

## 7. Bot-Schutz: wie er jetzt gehandhabt wird

Zwei der neuen Quellen (Anime-Loads, Anime-Stream) stehen hinter DDoS-Guard
bzw. Cloudflare. Dafuer wurde `resources/lib/handler/protection.py`
geschaffen: eine im Browser bestaetigte Sitzung (Cookie + User-Agent) laesst
sich pro Quelle hinterlegen und wird automatisch wiederverwendet und bei
Bedarf ueber einen optionalen FlareSolverr-Dienst erneuert. Details und
Testergebnisse in den zugehoerigen Commits.

Siehe auch: [LIVE-UND-BACKLOG.md](LIVE-UND-BACKLOG.md) fuer die Analyse der
Live-Angebote (Sport, Live-TV, Live-Kino) und die zurueckgestellten
Funktionswuensche.
