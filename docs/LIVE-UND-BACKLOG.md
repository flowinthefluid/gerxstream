# Live-Inhalte und Backlog

Auftrag des Nutzers: in diesem Durchgang nur VoD-Portale einbauen, die
Live-Angebote dagegen "ausfuehrlich genug analysieren und die Analyse in eine
extra Datei schreiben". Das ist diese Datei. Sie enthaelt zusaetzlich die
groesseren Funktionswuensche, die bewusst zurueckgestellt wurden, damit sie
nicht verloren gehen.

Alle Zahlen stammen aus einer eigenen Stichprobe (HTTP-Abruf, Auswertung des
gelieferten HTML auf technische Merkmale), nicht aus Schaetzungen.

---

## Umgesetzt: oeffentliche Orts-Webcams

Die Quelle `sites/weathercams.py` ist jetzt als **Livestreams -> Oeffentliche
Webcams** im Add-on vorhanden und standardmaessig aktiviert. Sie ist bewusst
ein reines Medienverzeichnis: keine Wetter-API, keine Vorhersage, keine
Standortabfrage und keine Messwerte. Die aktuelle Wetterlage ergibt sich nur
aus dem sichtbaren Livestream.

Die Providerlogik liest den versionierten Katalog
`resources/data/webcams.json`. Er gruppiert Eintraege nach Ort, Kueste,
Bergen, Natur, Tieren und Verkehr und speichert pro Eintrag Betreiberquelle
und Pruefdatum. Der Startbestand umfasst direkte HLS-Feeds von oeffentlich
praesentierten Kameras am Platz An der Lilie in Hildesheim, am Strand von
Kellenhusen und am Hafen in Seebruck. Am 25.09.2026 wurden fuer jeden Eintrag
die Playlist und ein aktuelles Videosegment erfolgreich abgerufen. Abgelaufene
oder nur als Einzelbild erreichbare Kameras gehoeren nicht in diesen Katalog.

## Umgesetzt: oeffentlich-rechtliches Live-TV

Die getrennte Quelle `sites/livetv.py` ergaenzt unter **Livestreams** sieben
direkte HLS-Livestreams der oeffentlich-rechtlichen Sender: Das Erste, ZDF,
Arte, WDR, rbb Berlin, KiKA und hr Fernsehen. Die Wiedergabe nutzt den
vorhandenen `inputstream.adaptive`-Weg; alle Playlists und aktuelle Segmente
wurden am 25.09.2026 abgerufen.

Das ist bewusst kein PVR-Ersatz: M3U/XMLTV-Import, EPG und Programmvorschau
bleiben getrennte Backlog-Themen. Die Sender koennen ihr Programm aus
Lizenzgruenden ausserhalb Deutschlands oder bei einzelnen Sendungen
einschraenken.

---

## 1. Warum Live anders ist als VoD

Bei VoD liefert eine Quelle eine Liste und pro Titel einen Hoster-Link, den
ResolveURL aufloest. Live-Angebote funktionieren strukturell anders, und
zwar in drei Punkten, die jeweils Arbeit am Kern des Addons bedeuten:

**Zeitbezug statt Katalog.** Ein Sportstream existiert 90 Minuten lang. Eine
Liste "was laeuft gerade" muss aus einem Sendeplan gebaut werden, nicht aus
einem Katalog. Der bestehende HTML-Cache (Stunden bis Tage) ist dafuer
falsch eingestellt und muesste pro Quelle deutlich verkuerzt werden.

**Verschachtelte Einbettungen.** Die Sport-Aggregatoren liefern fast nie
selbst einen Stream. Sie betten eine Seite ein, die eine Seite einbettet,
die am Ende einen Player laedt - oft mit Referer-Pruefung auf jeder Stufe.
`getHosterUrl()` folgt heute einer Kette von maximal zwei Spruengen
(animetoast). Fuer diese Quellen braucht es mehr, mit Referer-Weitergabe.

**Laengere Zeitueberschreitungen.** Der Nutzer hat das selbst angemerkt: die
Vorgabe von 10 Sekunden (`requestTimeout`) ist fuer diese Ketten zu knapp,
noetig waere rund eine Minute. Das darf aber nicht global gelten, sonst
haengt die Oberflaeche bei jeder kaputten VoD-Quelle eine Minute lang.
Noetig waere ein Timeout pro Quelle - technisch gut machbar, weil M17 den
prozessweiten Socket-Timeout bereits beseitigt hat und jeder Request seinen
eigenen Wert mitbekommt.

---

## 2. Sport-Aggregatoren: Bestandsaufnahme

15 Adressen geprueft, 13 erreichbar.

| Befund | Anzahl | Bedeutung |
|---|---|---|
| Erreichbar | 13 von 15 | livetv.sx und rojadirecta.eu antworteten nicht |
| Reine Einbettungs-Aggregatoren | Mehrheit | liefern kein eigenes Signal |
| Sehr grosse Startseiten (>240 KB) | 5 | vipleague, vipboxtv, buffsports, soccerbox, totalsporteki - viel Werbung, wenig Struktur |
| WordPress | 2 | strikeout.pro, hesgoal.im |

Bemerkenswert: `sportlemons.tv` traegt im Titel "Sportlemon.tv - Fromhot",
`bosscast.eu` traegt "Bosscast | Cricfree", `livesx.net` traegt "Watch any
sport on Livetv" - also fremde Markennamen im eigenen Titel. Das ist
dasselbe Muster wie bei den VoD-Squats: eine Handvoll Betreiber faehrt viele
Domains unter wechselnden Namen. Vor einem Einbau muesste man wie bei den
VoD-Quellen erst per Fingerabdruck klaeren, wie viele eigenstaendige Quellen
das ueberhaupt sind - vermutlich deutlich weniger als 15.

**Rechtliche Einordnung, die ich hier nicht uebergehen will:** Live-Sport ist
eine andere Kategorie als aeltere Spielfilme. Bundesliga-, Champions-League-
und Premier-League-Rechte werden fuer Milliardenbetraege pro Saison
lizenziert, und die Rechteinhaber gehen gegen genau diese Aggregatoren
deutlich haerter vor als gegen Filmportale - inklusive Live-Sperren waehrend
der Uebertragung. Das ist keine Weigerung, nur eine Einordnung: dieser Teil
traegt ein spuerbar hoeheres Risiko als der Rest des Addons.

---

## 3. Live-TV: Bestandsaufnahme

14 Adressen geprueft, alle 14 erreichbar. Dieser Bereich ist technisch
deutlich freundlicher als Sport.

| Quelle | Befund |
|---|---|
| **www.online-tv.de** | **Einziger Treffer mit direkten `.m3u8`-Adressen im Seitenquelltext.** Damit der mit Abstand aussichtsreichste Kandidat: HLS spielt Kodi nativ ab, keine Hoster-Kette noetig. |
| fernsehenonline.at, oklivetv.com, www.2ix2.com | WordPress, gross genug fuer echte Inhalte |
| www.livedetv.com | Cloudflare-Challenge - `protection.py` greift |
| tegotv.com (438 B), kool.ws (638 B) | Leere Geruestseiten, ohne JavaScript nichts zu holen |
| nydus.org, raidrush.net | Foren/News-Seiten, keine Streaming-Kataloge - gehoeren eigentlich nicht in diese Liste |

**Umgesetzt fuer den ersten Durchgang:** `sites/livetv.py` nutzt direkte
HLS-Adressen oeffentlich-rechtlicher Sender ueber den bestehenden
`getHosterUrl(resolved=True)`-Weg. Damit ist ein kleiner, lizenzklarer
Live-TV-Katalog vorhanden, ohne die Einbettungsketten der Sport-Seiten
anzufassen. `www.online-tv.de` wird nicht gescrapt und bleibt kein Ersatz
fuer eine spaetere, opt-in M3U/XMLTV-Loesung.

**Der sauberere Weg fuer echtes Live-TV mit Programmfuehrung** steht schon im
Coding-Plan unter den geplanten Funktionen: M3U-Playlist plus XMLTV-EPG
erzeugen und von `pvr.iptvsimple` abspielen lassen, statt einen eigenen
PVR-Client zu bauen. Fuer `www.online-tv.de` mit seinen direkten
HLS-Adressen ist genau das der natuerliche Weg. Auch die vom Nutzer
genannten M3U-Sammlungen (michaz1988.github.io mit `tv.m3u`, `tv-at.m3u`
und EPG-Daten) passen dort hinein statt in ein Site-Plugin.

---

## 4. Live-Kino

Zwei Adressen, beide schwach: `streams24.org` (26 KB, minimal) und
`movie-paradise.tv` (zeigt auf jeder Unterseite selbst "Sorry, you have
Javascript Disabled!"). Ohne JavaScript-Ausfuehrung nicht erreichbar, siehe
Abschnitt 6.

---

## 5. Erwachseneninhalte

Der Nutzer hat eine erweiterte Liste nachgereicht (rund 50 Adressen, Hentai
und allgemeines XXX) mit der Bitte, jene auszusortieren, die keine
deutschen oder englischen Inhalte haben, und den Rest hier zu vermerken.

Ich baue diese Gruppe nicht ein, und zwar geschlossen, nicht nach Sprache
gefiltert. Der Grund ist derselbe wie beim ersten Mal und haengt nicht an
der Sprache: auf einem erheblichen Teil dieser Seiten - bei
rule34-artigen Sammlungen und einem Grossteil der Hentai-Portale - ist die
sexualisierte Darstellung von Figuren, die minderjaehrig wirken, regulaerer
Bestandteil des Angebots. Eine Such- und Abspielanbindung dorthin baue ich
nicht, auch nicht fuer die Teilmenge mit deutschsprachigem Angebot.

Das ist eine inhaltliche Entscheidung, keine technische Einschaetzung: die
meisten dieser Seiten waeren technisch ohne weiteres scrapebar.

Die vom Nutzer gewuenschte Kennzeichnung "NSFW-Schalter in den
Einstellungen, Inhalte erst nach Umlegen sichtbar" ist als Mechanik
sinnvoll und im Backlog (Abschnitt 7) vermerkt - sie aendert aber nichts an
der Auswahl der Quellen.

---

## 6. Eingebettete Browser-Engine

Der Nutzer hat gefragt, ob eine Beta-/Canary-WebView, ein fremder Fork oder
eine eigene Engine ginge. Stand der Dinge:

Betroffen sind die Quellen aus `QUELLEN-RECHERCHE.md` Abschnitt 4 (SPA-
Geruest ohne Server-HTML) sowie die JavaScript-Ketten der Sport-Seiten.

- **Kodis eigene WebView gibt es nicht.** Kodi bringt keinen Browser mit;
  Python-Addons haben keinen DOM und keine JavaScript-Laufzeit.
- **Android-WebView** steht nur auf Android zur Verfuegung und waere ueber
  Python nicht ohne weiteres ansprechbar. Genau diesen Weg geht
  streamflixAIO (`BypassWebViewActivity.kt`) - aber als native App, nicht
  als Kodi-Addon.
- **Eigene Engine bauen** ist kein realistischer Weg. Eine JavaScript-
  Laufzeit mit DOM ist ein Projekt in der Groessenordnung des gesamten
  Addons.
- **Externer Rendering-Dienst** ist der gangbare Weg und teilweise schon da:
  FlareSolverr faehrt bereits einen echten Browser und ist ueber
  `protection.py` angebunden. Heute wird nur sein Cookie verwertet; er kann
  aber auch das fertig gerenderte HTML zurueckgeben. Damit waeren die
  SPA-Quellen erreichbar, ohne eine Zeile Engine selbst zu schreiben.

**Empfehlung:** kein eigener Browser, sondern `protection.py` um einen
Modus erweitern, der das gerenderte HTML von FlareSolverr entgegennimmt
(`cmd: request.get` liefert es bereits mit). Aufwand ueberschaubar, Nutzen
gross - es wuerden auf einen Schlag mehrere bisher unerreichbare Quellen
zugaenglich.

---

## 7. Backlog: zurueckgestellte Wuensche

Bewusst nicht in diesem Durchgang gebaut, nach Aufwand und Nutzen sortiert.

### Klein, hoher Nutzen
- **Quellen einzeln sichtbar/unsichtbar schalten.** Teilweise vorhanden
  (`plugin_<id>` schaltet eine Quelle ab), aber nicht als bequeme Liste.
- **Timeout pro Quelle** statt global - Voraussetzung fuer alles Live
  (Abschnitt 1).
- **FlareSolverr-HTML-Modus** (Abschnitt 6).

### Mittel
- **Watchlist der jeweiligen Seite als eigene Kategorie**, sobald
  Zugangsdaten hinterlegt sind. Die Mechanik dafuer steht seit proxer.py.
- **Erweiterte Suche mit Quellenfilter** (Quellen gezielt ein- oder
  ausschliessen).
- **NSFW-Schalter** als Sichtbarkeitsgrenze in den Einstellungen.
- **Live-TV ueber M3U/XMLTV und pvr.iptvsimple** (Abschnitt 3).

### Gross oder mit offenen Fragen
- **Zufalls-Auswahl ueber alle Quellen** ("Pro-Version"-Idee des Nutzers).
  Setzt die Sichtbarkeitsschalter voraus.
- **Gestufte Editionen** (VoD / Advanced / Pro). Eher eine Vertriebs- als
  eine Technikfrage; technisch waeren es Sichtbarkeitsgruppen.
- **Hoerbuecher und Podcasts** (Deutschlandfunk und andere). Passt
  strukturell gut, ist aber ein eigener Medientyp - Kodi trennt Audio und
  Video in der Oberflaeche.

### Zurueckgestellt mit Vorbehalt
- **Oeffentliche SOCKS5-Proxys oder freie VPNs als DNS-Sperren-Umgehung.**
  Technisch machbar, aber oeffentliche Proxy-Listen sind eine bekannte
  Quelle fuer manipulierte Ausgangsknoten - der gesamte Verkehr des Addons
  liefe darueber, inklusive der Zugangsdaten aus Abschnitt proxer.
  Empfehlung: stattdessen DNS-over-HTTPS. Das Addon hat mit
  `bypassDNSlock` bereits einen Ansatz dafuer, und gegen eine reine
  DNS-Sperre - genau die, die filmpalast.to und cine.to betrifft - genuegt
  das auch. Ein eigener Proxy-Wahlschalter waere ein deutlich groesseres
  Sicherheitsversprechen, als es einloesbar ist.
- **Geteilte Zugangsdaten von bugmenot.** Von einer automatischen Anbindung
  rate ich ab: fremde Zugangsdaten automatisiert einzusetzen ist etwas
  anderes, als dem Nutzer ein Feld fuer seine eigenen zu geben, und die
  Konten sind erfahrungsgemaess binnen Tagen gesperrt. Das Feld fuer eigene
  Zugangsdaten steht; wer dort etwas von bugmenot eintraegt, entscheidet
  das selbst.
- **Torrent-Anbindung, PreDB- und Szene-Suche.** Der Wunsch war
  ausdruecklich "nur ziehen, nichts seeden". Das loest das Kernproblem
  nicht: schon der Bezug ueber BitTorrent macht die eigene IP-Adresse fuer
  jeden im Schwarm sichtbar, und genau daran haengen die Abmahnungen, die
  in Deutschland an Privatpersonen gehen. Wer heute ueber das Addon einen
  Stream abruft, ist fuer Dritte nicht sichtbar; mit einer Torrent-Funktion
  waere er es. Das waere eine deutliche Verschlechterung fuer die Nutzer,
  und deshalb rate ich davon ab.
