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

## 8. Nachtrag (2026-09-19): Nachpruefung einer zweiten Nutzerliste

Der Nutzer hat widersprochen, dass 27 seiner Adressen nur zusaetzliche
Domains gewesen seien, und eine deutlich laengere Liste nachgereicht, mit der
Bitte, sie mit der gleichen Fingerabdruck-Methode wie oben (Abschnitt 2)
gegenzupruefen statt sie nach Erreichbarkeit allein einzuordnen. Das ist hier
geschehen, live gegen die aktuellen Seiten (nicht gegen den Stand von
Abschnitt 2 - Domains koennen sich zwischen zwei Pruefungen aendern, siehe
`movie2k.cx` unten als Beispiel dafuer).

**Bereits eingebaut, nur unter anderem Namen bekannt:**
- `anime-loads.org`-artige Quellen: `sites/animeloads.py` existiert bereits
  (Abschnitt 1). Nichts fehlt hier.
- `internetarchive.py` hat bereits 19 vorkonfigurierte Kategorien (Sprache,
  Genre, Regisseur, Epoche) statt einer einzigen Suche - siehe
  `URL_GERMAN_LIST` in der Datei.
- `proxer.me` hat bereits ein Zugangsdaten-Feld nach demselben Muster wie
  `aniworld.py`/`serienstream.py` (`proxer.user`/`proxer.pass` in den
  Einstellungen) - der Nutzer muss dort seine eigenen Zugangsdaten
  eintragen, das Addon bringt keine mit. Kein weiterer Auftrag hier.
- `mediathekviewweb.de`: `sites/mediathekviewweb.py` existiert bereits.

**Neu gefunden, eigenstaendige Quelle - Kandidaten fuer neue Plugins:**

| Domain | Befund |
|---|---|
| `movie2k.cx` | Eigener Katalog mit eigener ID-Struktur (`/stream/<titel>-<jahr>-<hash>`), eigenem Forum, eigener "Wunsch Box" (Nutzer koennen Titel nachfragen) und TMDB-Anbindung fuer Metadaten. Deutlich lebendiger und anders aufgebaut als das Squat-Netzwerk um `movie2k.ag`/`movie2k.ch` aus Abschnitt 2 - das ist eine andere, eigenstaendige Installation. Der Nutzer hatte recht. |
| `streamkinos.lat` | DataLifeEngine-Installation mit durchlaufender eigener ID (`/25615-...html`), eigenen Kurzbeschreibungen und Besetzungsangaben, 25 Genre-Kategorien inkl. eigener Zaehlung. Eigenstaendiger Katalog. |
| `kellerkino.com` | Eigenes, ausgereiftes Wordpress-Layout, eigene Genre-Slugs (`/drama/`, `/horror/` usw.), Foren-Link, taeglich aktualisierte Neuerscheinungsliste. Eigenstaendige Quelle. |
| `videogold.de` | Deutsche Mediathek-Sammelseite (keine Kinofilme, sondern TV-Formate/Doku/Interview/Podcast-Clips), bindet u.a. ARTE- und CCC-Inhalte ein. Eher ein Kandidat fuer die Dokus-Kategorie als fuer VoD-Spielfilme. |

**Ein Betreiber, zwei Domains (echter Alias, kein Doppel-Plugin):**
- `streamworld.to` und `streamworld.co` liefern beim Abruf identische
  Trend-Listen mit identischen internen IDs (`/movie/1101383-...`) - eine
  Installation, zwei Domains. Gehoert als Domain-Umschaltmenue zu einem
  einzigen Plugin, nicht zu zweien.

**Falsche Faehrte - keine Streaming-Quelle:**
- `watchhub.work/watchserieshd/` leitet beim Abruf auf eine
  Werbe-/Schadseite um ("Opera One installieren"), keine Filmseite
  dahinter. Nicht einbauen.
- `flixnet.to` leitet auf ein Werbenetzwerk-Tracking-Skript um
  (`coosync.com`). Ebenfalls keine echte Quelle mehr, unabhaengig davon, ob
  die Domain das einmal war.
- `filmpalast-to.net` ist **nicht** `filmpalast.to`. Die Seite verlinkt
  selbst auf `mobzax.info`, `megakino-co.com` und `vider.to`, hat
  erkennbar generierte Autoren-Biografien (z. B. eine "Kinderbuchautorin"
  als Autorin von SEO-Text ueber eine Streaming-Seite) und wirbt im
  Fliesstext für eine dritte Seite. Das ist eine SEO-Koederseite, die den
  bekannten Markennamen fuer Suchmaschinen-Traffic verwendet, keine
  eigenstaendige Quelle. Nicht einbauen.

**Durch Bot-Schutz nicht pruefbar (kein Urteil moeglich):**
`hd-area.tv`, `serienfans.org` und `moviefans.to` haben den automatisierten
Abruf mit HTTP 403 abgelehnt. Das ist kein Beleg gegen die Seiten - nur ein
Hinweis, dass sie ueber `protection.py`/FlareSolverr geprueft werden
muessten, nicht ueber einen einfachen Abruf. Offen fuer einen naechsten
Durchgang.

**Geringe Prioritaet - templatiertes Netzwerk, nicht deutschsprachig:**
`streamkiste.al` und `stream-kiste.tv` (mit Bindestrich, nicht zu
verwechseln mit den deutschen `streamkiste.*`-Quellen aus Abschnitt 2) laufen
beide auf englischsprachigen Oberflaechen; `stream-kiste.tv` traegt zudem
wortgleich denselben generischen Disclaimer-Text ("is a social video sharing
platform..."), der auf hunderten baugleichen Seiten auftaucht - ein
Hinweis auf eine gekaufte Vorlage statt auf einen erkennbar eigenen
Betreiber. Ohne deutschsprachiges Angebot fuer dieses Projekt nachrangig.

**Noch offen:** die Dokus-, Hoerbuch-, Gaming- und Sender-Mediathek-Listen
(ARD/ZDF/ORF/Joyn/RBB/WDR usw.) aus der zweiten Nutzerliste sind noch nicht
einzeln nachgeprueft - das ist ein eigener, aehnlich grosser Durchgang und
wird nicht in einem Rutsch mit dieser Nachpruefung erledigt.

### Ausdruecklich nicht Teil dieses Projekts

Zwei Wuensche aus der zweiten Liste werden nicht umgesetzt, unabhaengig von
technischer Machbarkeit:

- **bugmenot.com als Quelle geteilter Zugangsdaten.** Das war bereits in
  Abschnitt 7 des Backlogs abgelehnt (siehe LIVE-UND-BACKLOG.md) und bleibt
  dabei: automatisiert fremde, geteilte Zugangsdaten einzusetzen ist etwas
  anderes als dem Nutzer ein Feld fuer seine eigenen zu geben. Das Feld
  steht (siehe proxer.py); was jemand dort eintraegt, ist seine eigene
  Entscheidung.
- **Hentai- und allgemeine Erwachsenenseiten als neue Quellen**, auch die in
  dieser zweiten Liste erneut genannten rund 90 Adressen. Die Begruendung
  ist dieselbe wie in Abschnitt 5 dieser Datei bzw. Abschnitt 5 des
  Backlogs: auf einem erheblichen Teil dieser Seiten ist die sexualisierte
  Darstellung von Figuren, die minderjaehrig wirken, regulaerer Bestandteil
  des Angebots. Das baue ich nicht, auch nicht gefiltert nach Sprache und
  auch nicht in eine "noch nicht moeglich"-Warteliste - das waere am Ende
  dieselbe Aufgabe mit einem anderen Dateinamen.

## 9. Nachtrag (2026-09-19, Teil 2): Dokus- und Sender-Mediathek-Liste

Fortsetzung des in Abschnitt 8 offen gelassenen Punktes ("Noch offen: die
Dokus-, Hoerbuch-, Gaming- und Sender-Mediathek-Listen"). Gegengeprueft:
die Dokus- und Sender-Mediathek-Adressen sowie der VOD-Rest. Hoerbuch- und
Gaming-Liste sind weiterhin offen, siehe letzter Punkt.

**Wichtigste Erkenntnis vorab:** ein grosser Teil der genannten
Sender-Mediatheken ist bereits abgedeckt, nur nicht unter dem eigenen
Domainnamen sichtbar:

- `sites/mediathekviewweb.py` fragt die gebuendelte Suche von
  MediathekViewWeb ab und deckt damit ARD, ZDF, 3sat, arte, phoenix, ORF,
  SRF, alle Dritten (BR, HR, MDR, NDR, RBB, SR, WDR), KiKA, funk und
  Deutsche Welle in einem einzigen Plugin ab (siehe `CHANNELS` in der
  Datei). `zdf.de`, `3sat.de`, `phoenix.de`, `wdr.de`, `rbb-online.de`
  (leitet auf `rbb24.de` weiter) und `tv.orf.at` aus der Nutzerliste sind
  damit bereits erreichbar - kein neues Plugin noetig.
- `sites/dokus.py` hat inzwischen fuenf Quellen eingebaut: Dokus4.me,
  **Dokustreams.de**, Dokuh.de, **Doku-Streams.com** (neu, Unterquelle `_4`)
  und Videogold.de (Sammelseite fuer Mediatheken-Clips inkl. ARTE/CCC).
  Wichtig zum Nichtverwechseln: `dokustreams.de` und `doku-streams.com` sind
  zwei verschiedene, unabhaengige Seiten mit fast identischem Namen - beide
  sind mittlerweile als getrennte Unterquellen eingebaut.
- `sites/animestream.py` verwendet bereits exakt die URL-Struktur
  (`/alle-serien`, `/alle-filme`, `/suche?s=`), die auf `anime-stream.to`
  zu sehen ist. Keine neue Quelle, nur eine Bestaetigung, dass der
  bestehende Standardwert noch stimmt.

**Neu gefunden, eigenstaendige Quelle - Kandidaten fuer neue Plugins
(Dokus):**

| Domain | Befund |
|---|---|
| `doku-streams.com` | ✅ **Implementiert** als Unterquelle `_4` in `sites/dokus.py` (`showEntries_4`/`showGenre_4`/`showSearch_4`). Privat betriebene Doku-Sammlung mit 599 eingetragenen, 525 direkt abspielbaren Dokumentationen nach Themen (Sucht, Kultur, Persoenlichkeiten, Wissenschaft, Politik, Wirtschaft, Erotik & Sex - letztere Kategorie wird beim Scraping bewusst ausgeblendet). Eigenstaendiger Betreiber, nicht zu verwechseln mit dem bereits eingebauten `dokustreams.de` (siehe oben). |
| `dailyme.de` | Kostenloses, werbefinanziertes Portal mit eigenen Kategorien fuer Filme, Serien, **Dokus** (u.a. "Faszinierende Dokumentationen", "Historische Kriegs-Dokus") und Live-TV. Deutlich groesserer, aktiver Katalog als die bisherigen Dokus-Quellen. Noch nicht implementiert. |

**Korrektur nach vertiefter Pruefung (Nachpruefung per curl, volle Detailseiten-Analyse):**
Die erste Fassung dieses Abschnitts stufte `doksite.de` und `tierwelt-live.de` faelschlich als ergiebige neue Dokus-Quellen ein. Eine echte Detailseiten-Pruefung (nicht nur Kategorie-/Startseite) ergab das Gegenteil - beide werden **nicht** implementiert:

- `doksite.de` ist entgegen der ersten Einschaetzung **kein Streaming-Portal**, sondern ein reines Metadaten-/Datenbank-"Filmportal" (Eigenbezeichnung im Titel: "DOKsite Filmportal"), vergleichbar mit `filmportal.de`/`moviepilot.de`/IMDb. Die Detailseite (`/de/video/<id>-movie`) enthaelt ausschliesslich: Verweise auf IMDb/TMDB/Letterboxd/Wikidata, Kinostart- und TV-Sendetermine, YouTube-**Trailer**-Einbettungen (keine Vollfilme) und einen "Verfuegbarkeit"-Tab, der nur zu "Wer streamt es?"/JustWatch/Bibliothekskatalogen weiterverlinkt. Es gibt nirgends einen abspielbaren Vollfilm.
- `tierwelt-live.de` ist entgegen der ersten Einschaetzung **kein Dokumentationen-Aggregator**, sondern eine kommerzielle Live-Tierwebcam-Plattform (Zoo-/Wildtier-Kameras) mit privater REST-API, echten HLS/MP4-Stream-URLs hinter UUID-Platzhaltern und einem vollstaendigen VAST-Werbe-System (Pre-/Mid-Roll-Anzeigen ueber `smartclip.net`). Das erfordert das Reverse-Engineering einer werbefinanzierten, kommerziellen privaten API - ausserhalb des Rahmens eines regelbasierten Kodi-Scrapers und mit ungeklaerten ToS-/Rechtsfragen. Empfehlung: nicht implementieren.

**Neu gefunden, eigenstaendige Quelle - Kandidat VOD (kein Dokus-Fokus):**

| Domain | Befund |
|---|---|
| `flixitv-stream.eu` | ✅ **Implementiert** in `sites/flixitvstream.py`. Deutschsprachiges Film-/Serien-Streamportal mit eigener ID-Struktur (`/serie?v=<id>`), ein einziger, unpaginierter Gesamtkatalog (512 Eintraege, Filme und Serien gemischt) unter `/serie`. Jeder Eintrag - auch Einzelfilme - haengt formal an einer Staffelauswahl (`?v=<id>&s=<n>`) mit Episodentabelle; bei nur einer Staffel wird das Zwischenmenue automatisch uebersprungen. Hoster: `hubu.cloud`-Embed, neben einem Werbe-Iframe, der gezielt ausgefiltert wird. |
| `flash-moviez.ucoz.org` | ✅ **Implementiert** in `sites/flashmoviez.py`. **Korrektur nach Nachpruefung, siehe Kasten unten:** aktive, deutschsprachige ucoz-Seite ("Flash-Moviez.Tv - Deine StreamSource # 1") mit klarer Genre-Navigation - 25 Genres, u.a. eine eigene Kategorie `/publ/alle_moviez/dokus/11`, dazu Action, Abenteuer, Bollywood, Krieg/Western, Zeichentrick, 720p usw. Verlinkt auch auf `toplist.raidrush.ws` (Szene-Linkliste), passt also ins selbe Umfeld wie andere bereits eingebaute Szene-Quellen. Detailseiten verlinken echte Hoster (streamcloud.eu, divxstage, movshare) neben einem YouTube-Trailer, der beim Scraping uebersprungen wird. Die Startseite laedt zusaetzlich obfuskierte Werbe-Scripts (`slimtrade.com`-Banner, `yadro.ru`-Zaehler) - fuer das Scraping per `cRequestHandler`/`cParser` (kein JS, kein Rendering) ist das irrelevant, nur beim Betrachten im echten Browser stoerend. |

**Niedrige Prioritaet / nur mit Einschraenkung brauchbar:**

- `k-tv.org` - echter, aktiver katholischer Fernsehsender mit eigener
  Mediathek und Livestream. Legitime Quelle, aber ein sehr enges,
  religioeses Nischenthema; nur bei ausdruecklichem Interesse sinnvoll.
- `x-oo.com` - in erster Linie ein Flash-/Browserspiele-Portal (passt eher
  zur offenen Gaming-Liste als zu Dokus); der kleine Filme/Serien-Bereich
  bindet nur als "ZDF"/"YouTube" deklarierte Fremdinhalte ein, kein
  eigener Katalog. Kaum Mehrwert als Streaming-Quelle.
- `filmo.to` - umfangreicher, gepflegter Katalog mit Sammlungen/Charts,
  aber durchgehend englischsprachige Oberflaeche ("Watch Now", "Free
  movies. Nothing in the way.") ohne erkennbaren Deutschland-Fokus - passt
  thematisch schlechter zu diesem Projekt als die deutschen Quellen.
- `medici.tv` - echtes Angebot, aber ueberwiegend kostenpflichtiges
  Klassik-/Opern-/Ballett-Streaming, kein allgemeines Dokus-Portal.
- `andererseits.org` - Abo-finanziertes Behinderungs-Journalismus-Magazin
  mit gelegentlichen kurzen Dokus; ueberwiegend Text, kein Streaming-Katalog.

**Zugangsschranke, gleiche Kategorie wie proxer.me (Abschnitt 3):**

- `filmfriend.ch` - Arthouse-/Dokumentarfilm-Streaming fuer Bibliotheken;
  jede Sitzung braucht die Bibliotheksausweisnummer der jeweiligen
  Gemeinde/Bibliothek als Login. Kein pauschaler Zugang moeglich, nur
  ueber ein Zugangsdatenfeld pro Nutzer denkbar - wie bei proxer.me ein
  groesserer Sonderfall als die uebrigen Quellen.

**Keine Streaming-Quelle - andere Zweckbestimmung:**

- `filmportal.de` - Filmdatenbank des DFF (Deutsches Filminstitut), listet
  Filme/Personen/Kinostarts auf, aber keine Videos zum Abspielen.
- `moviepilot.de` - Film-/Serien-Nachrichtenseite mit "Wo laeuft das?"
  -Verweisen auf Netflix/Amazon/Disney+ usw., kein eigener Player.
- `heftfilme.com` - Filmkritik-Magazin; "Stream"-Links fuehren zu
  Amazon-Affiliate-Seiten, kein eigener Katalog.
- `welt.de`, `n-tv.de`, `bpb.de` - Nachrichten- bzw. politische
  Bildungsseiten mit gelegentlichen Videobeitraegen, keine
  Dokumentarfilm-Kataloge.
- `alexanderstreet.com` - leitet auf die ProQuest-Unternehmensseite um;
  Alexander Street ist ein Bibliotheks-/Institutionen-Lizenzdienst ohne
  oeffentlichen Zugang.
- `rumble.com`, `odysee.com` - generische Videoplattformen (wie YouTube-
  Alternativen) ohne kuratierten Dokus-Fokus; die Startseiten zeigen
  ueberwiegend Gaming-, Politik- und teils verschwoerungsnahe Inhalte.
  Fuer eine dedizierte Dokus-Quelle ungeeignet.
- `joyn.de` - kommerzieller DRM-Streadingdienst (ProSiebenSat1), kein
  Scraping-Ziel, vergleichbar mit Netflix/Amazon.
- `alliance4creativity.com` - das ist die Anti-Piraterie-Koalition ACE
  (Alliance for Creativity and Entertainment), keine Streaming-Seite.

**Korrektur nach Nutzerhinweis (wichtig fuer kuenftige Pruefungen):** die
erste Fassung dieses Abschnitts hatte `vumoo.live`, `schoener-fernsehen.com`,
`ww2.fmovies.cab`, `couchtuner.fashion` und `flash-moviez.ucoz.org` faelschlich
als tot/auf Werbung umgeleitet eingestuft. Grund war, dass das genutzte
Fetch-Werkzeug die Seite wie ein Browser rendert und dabei einem
JS-/Popunder-Redirect folgt, den ein reiner HTTP-Client nie ausloest. Ein
Gegencheck mit `curl` (reiner GET-Request, kein JS, genau wie
`resources/lib/handler/requestHandler.py` es in diesem Addon macht) zeigt: alle
fuenf Domains antworten mit HTTP 200 und liefern echtes, inhaltsreiches HTML.
Fuer das Scraping selbst sind clientseitige Werbe-Redirects ohnehin
irrelevant, weil der Parser (`cParser`) nur das rohe HTML durchsucht und nie
JavaScript ausfuehrt - Cloudflare-Challenges (siehe `filmfans.org` unten)
sind die einzige Kategorie, die einen echten Scraping-Blocker darstellt.
Lehre: reine Fetch-Ergebnisse ohne Redirect-Ziel-Pruefung reichen nicht, um
eine Seite als tot einzustufen - immer mit einem rohen HTTP-Request
gegenpruefen.

Richtiggestellte Befunde:

- `vumoo.live` ist eine echte, aktive englischsprachige Film/Serien-Seite
  ("Watch Free Movies & TV Shows Online - Vumoo 2026") - gleiche Marke wie
  `vumoo.gd` weiter unten, also derselbe Vorbehalt (kurzlebig, ohne
  Deutschland-Fokus).
- `ww2.fmovies.cab` und `couchtuner.fashion` sind ebenfalls echt und aktiv
  (baugleiche Fmovies-Vorlage, "Watch Free Full HD Movies & TV Shows"),
  aber weiterhin durchgehend englischsprachig und ohne Deutschland-Bezug -
  bleiben deshalb niedrige Prioritaet, nicht weil sie tot waeren.
- `schoener-fernsehen.com` ist eine echte, aktive deutsche Live-TV-Seite:
  Startseite zeigt explizit ein "Live-TV"-Menue sowie Status-Hinweise zu
  einzelnen Sendern ("Aktuell sind die Sender HR, BR, RBB nicht
  erreichbar"), Meta-Beschreibung nennt ausdruecklich "ARD als Live Stream
  online schauen". Das ist ein Fund fuer die Live-TV-Liste, nicht fuer die
  Dokus-Liste - siehe `docs/LIVE-UND-BACKLOG.md` fuer den passenden Kontext.
- `flash-moviez.ucoz.org` ist keine verlassene Forenseite, sondern aktiv
  (siehe Eintrag oben in der VOD-Kandidatentabelle).

**Durch Bot-Schutz nicht pruefbar bzw. technisch inkonklusiv (per curl
bestaetigt, kein Fetch-Tool-Artefakt):**

- `filmfans.org` antwortet mit HTTP 403 und `Cf-Mitigated: challenge`
  (interaktive Cloudflare-Challenge, CSP referenziert
  `challenges.cloudflare.com`) - wie `hd-area.tv`/`serienfans.org` in
  Abschnitt 8 ein echter Bot-Schutz, kein Urteil ohne
  FlareSolverr/`protection.py` moeglich.
- `filmfrei24.com` antwortet auch per curl nicht (`Operation timed out`) -
  das ist ein echter Verbindungsfehler, keine Fetch-Tool-Eigenart. Aktuell
  nicht erreichbar.
- `dokus4.me` liefert einen TLS-Zertifikatsfehler (SNI/Certificate
  Mismatch, `SEC_E_WRONG_PRINCIPAL`) und selbst mit ignoriertem
  Zertifikat nur eine generische 1,2-KB-"System Status"-Seite statt
  echtem Inhalt - die Domain zeigt also auf eine falsche/kaputte
  Infrastruktur, nicht auf die eigentliche Seite. Aktuell nicht nutzbar.
- `mediathekdirekt.de` ist dagegen ein echtes, funktionierendes
  Open-Source-Projekt (AGPL, Markus Koschany): eine schlanke, per
  DataTables/AJAX befuellte Suchmaske fuer oeffentlich-rechtliche
  Mediatheken. Die Startseite selbst ist bewusst klein (4,5 KB), weil der
  eigentliche Datensatz aus einer separaten `good.json` (Sender, Titel,
  Thema, Datum, Dauer, direkte URL, HD-URL) nachgeladen wird - das waere
  sogar einfacher zu scrapen als MediathekViewWebs API. Inhaltlich aber
  dieselben oeffentlich-rechtlichen Sender, die `mediathekviewweb.py`
  bereits abdeckt - kein neues Plugin noetig, nur eine falsche
  "inkonklusiv"-Einstufung von vorher richtiggestellt.
- `vumoo.gd` ist zwar inhaltlich ein echter, englischsprachiger
  Film/Serien-Katalog, beschreibt sich in seinem eigenen FAQ aber selbst
  als kurzlebige, jederzeit wechselnde Marke ("The site may close
  tomorrow"/Telegram-Kanal fuer die naechste Adresse) - kein stabiler
  Standardwert, zudem ohne Deutschland-Fokus.

**Noch offen:** die Hoerbuch- und Gaming-Listen aus der zweiten
Nutzerliste sind weiterhin nicht einzeln nachgeprueft - dafuer fehlen noch
die konkreten Adressen.
