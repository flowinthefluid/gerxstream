# D4 — Bewertung von Parser- und HTTP-Stack

Arbeitspunkt D4 aus [BEFUNDE.md](BEFUNDE.md). Die Frage lautete, ob die beiden
tragenden Schichten des Addons — das Parsen der Seiteninhalte und der
HTTP-Zugriff — so bleiben können oder ersetzt werden müssen.

**Ergebnis vorweg: beide bleiben.** Ein Austausch wäre ein Framework-Wechsel und
damit gegen die geltenden Arbeitsregeln; er wäre zudem nicht durch einen
messbaren Gewinn gedeckt. Dafür fallen im Bestand sechs konkrete Mängel an, die
unabhängig vom Framework behoben werden sollten. Vier davon ändern sichtbares
Verhalten und sind deshalb hier zur Entscheidung gestellt statt umgesetzt.

---

## 1. Parser-Stack

### Ist-Zustand

Das Parsen läuft vollständig über `cParser` in
[resources/lib/tools.py](../resources/lib/tools.py) und damit über reguläre
Ausdrücke. Ein HTML-Parser (BeautifulSoup, lxml, `html.parser`) wird nirgends
verwendet und ist auch nicht als Abhängigkeit deklariert.

| Kennzahl | Wert |
|---|---|
| Aufrufe von `cParser.parse()` | 173 |
| Aufrufe von `cParser.parseSingleResult()` | 155 |
| Regex-Muster in `sites/` | ~134 |
| Site-Plugins, die darauf aufbauen | 27 |

### Bewertung

Ein Wechsel auf einen echten HTML-Parser müsste **328 Aufrufstellen und rund
134 Muster** anfassen. Das ist kein Refactoring, sondern eine Neuschreibung
aller Scraper — ausdrücklich ausgeschlossen durch die Arbeitsregel „Kein
Framework-Wechsel".

Unabhängig von der Regel spricht die Sache selbst dagegen. Scraper greifen
gezielt einzelne Fragmente aus Seiten, die sich ohne Vorwarnung ändern und
häufig kein wohlgeformtes HTML liefern. Ein Baum-Parser hilft dort, wo man
strukturiert navigiert; hier wird gegen Marker im Rohtext gearbeitet, und der
Bruch tritt in beiden Ansätzen zum selben Zeitpunkt ein — wenn die Seite ihr
Markup ändert. Der Gewinn wäre Lesbarkeit, der Preis die Neuvalidierung von 27
Quellen ohne Testabdeckung.

**Empfehlung: Regex beibehalten.** Die folgenden Mängel liegen ohnehin nicht am
Ansatz, sondern an der Umsetzung.

### P1 — `_get_compiled_pattern` war kein Cache *(behoben)*

Die Funktion trug den Namen eines Caches, rief aber bei jedem Aufruf
`re.compile()`. Pythons interner Musterspeicher federte das ab, wird bei
vielen verschiedenen Mustern aber verdrängt.

Behoben: `@lru_cache(maxsize=512)`. Kompilierte Muster sind unveränderlich und
beim Matchen thread-sicher, lassen sich also gefahrlos halten. Unter Python
3.14.4 gegengeprüft: gleiches Muster plus gleiche Flags liefert dasselbe
Objekt, abweichende Flags ein eigenes.

### P2 — `parse()` und `parseSingleResult()` arbeiten mit verschiedenen Flags

```
parseSingleResult()  ->  re.S | re.M
parse()              ->  re.DOTALL            (= re.S, ohne re.M)
```

Dasselbe Muster verhält sich damit je nach aufgerufener Funktion
unterschiedlich: `^` und `$` greifen in `parseSingleResult()` pro Zeile, in
`parse()` nur am Anfang und Ende des gesamten Dokuments. Wer ein Muster von
einer Funktion auf die andere umhängt, bekommt stillschweigend ein anderes
Ergebnis — kein Fehler, kein Logeintrag, nur weniger oder mehr Treffer.

**Verhaltensändernd.** Eine Angleichung würde bestehende Muster beeinflussen und
müsste quellenweise nachgeprüft werden. Vorschlag: zunächst nur dokumentieren
und `re.M` bei neuen Mustern meiden; eine Angleichung wäre ein eigener
Durchgang mit Sichtprüfung je Quelle.

### P3 — Zeichenersetzung ist eine handgepflegte Tabelle mit Fehlern

`_replaceSpecialCharacters()` ersetzt 54 fest verdrahtete Paare. Geprüft per
`ast`-Auswertung der Tabelle gegen `html.unescape()`:

| Eintrag | Tabelle | Korrekt | Bewertung |
|---|---|---|---|
| `&#xDC;` | `³` | `Ü` | **Fehler.** Der Schlüssel ist doppelt belegt (vorher schon `Ü`), die zweite Zeile greift nie. Gemeint war ersichtlich `&#xB3;` → `³`. Folge: `³` als HTML-Entity wird nirgends aufgelöst. |
| ` ` | `h` | schmales geschütztes Leerzeichen | **Fehler.** Aus „20:30 Uhr" wird „20:30hUhr". Offenbar ein Schnellschuss für eine einzelne Quelle. |
| `&#8211;`, `–` | `-` | `–` | Absichtliche ASCII-Faltung, in Ordnung. |
| `…` | `...` | `…` | Absichtliche ASCII-Faltung, in Ordnung. |
| `&#8727;` | `*` | `∗` | Absichtliche ASCII-Faltung, in Ordnung. |
| `\\/` | `/` | — | Doppelt aufgeführt, wirkungslos, harmlos. |

Darüber hinaus deckt die Tabelle nur diese 54 Fälle ab. Jede andere Entity —
und davon gibt es über 2000 benannte plus den gesamten numerischen Raum —
erreicht die Oberfläche unaufgelöst.

**Vorschlag (verhaltensändernd):** zuerst `html.unescape()` laufen lassen, das
sämtliche Entities korrekt und vollständig auflöst, und danach eine kurze,
ausdrücklich als solche benannte Liste gewollter ASCII-Faltungen (`–` → `-`,
`…` → `...`, `∗` → `*`). Das ersetzt 54 Zeilen durch etwa fünf, behebt die
beiden Fehler und deckt alle übrigen Entities mit ab. Da sich sichtbare Titel
ändern können, nicht ohne Freigabe.

Anmerkung: `html.entities.name2codepoint` ist in
[tools.py](../resources/lib/tools.py) bereits importiert — der Umstieg war
offenbar schon einmal angedacht.

---

## 2. HTTP-Stack

### Ist-Zustand

Zwei Wege stehen nebeneinander:

| Weg | Verwendung | Umfang |
|---|---|---|
| `cRequestHandler` (`urllib`, eigener Aufbau) | **sämtlicher** Scraper- und TMDB-Verkehr | 34 Dateien |
| `requests` direkt | nur Infrastruktur | 4 Aufrufe |

Die vier direkten Aufrufe liegen in
[myjdapi.py](../resources/lib/handler/myjdapi.py) (Zeilen 404, 419 — die
MyJDownloader-Fernsteuerung, eine fremde JSON-API ohne Bezug zum Scraping) und
in [updateManager.py](../resources/lib/updateManager.py) (Zeilen 204, 267 — der
Selbst-Update-Pfad, der laut H15 abgeschaltet ist). Alle vier haben seit M16
ein `timeout`.

### Bewertung

Die Aufteilung ist keine gewachsene Unordnung, sondern sinnvoll: `cRequestHandler`
bündelt das, was Scraping braucht und was zentral bleiben muss — Caching,
Cookie-Haltung, TLS-Richtlinie samt Opt-out pro Quelle, Timeout pro Anfrage
(M17), Kompression, Redirect-Filter, Umgehung der DNS-Sperre. Eine fremde
JSON-API und ein abgeschalteter Update-Pfad brauchen davon nichts.

`cRequestHandler` durch `requests` zu ersetzen hieße, all das auf eine Bibliothek
zu portieren, die es nicht mitbringt, und dabei 34 Dateien anzufassen. Kein
Gewinn, hohes Risiko.

**Empfehlung: beibehalten.** Zwei Anmerkungen:

### H-A — `updateManager` umgeht die zentrale TLS-Richtlinie

Die beiden `requests.get()` dort laufen an `cRequestHandler` vorbei und damit
an der TLS-Richtlinie und deren Protokollierung. Beide Zeilen tragen noch den
auskommentierten Rest `# verify=False,` aus der Zeit vor S3. Praktisch
folgenlos, weil der Pfad seit H15 nicht mehr angelaufen wird — aber wenn das
eigene Repo verdrahtet wird (Auftrag b), muss dieser Code auf `cRequestHandler`
umgestellt werden, sonst entsteht S3 dort neu. **Gehört in den Repo-Auftrag,
nicht hierher.**

### H-B — TLS-Umsetzung geprüft, kein Befund

Die Signatur `cRequestHandler(..., ssl_verify=True, allow_insecure_tls=True)`
liest sich beim ersten Hinsehen so, als sei unsichere TLS der Standard. Sie ist
es nicht: `allow_insecure_tls` erlaubt lediglich, dass das **pro Quelle
abschaltbare** Opt-out überhaupt berücksichtigt wird. Das Opt-out selbst
(`plugin_<id>_allowInsecureTLS`) steht auf `False`, der Site-Bezeichner wird
gegen `[a-z0-9_-]+` geprüft, und greift es doch, erscheint eine `LOGWARNING`
mit Domainnamen. TMDB-Verkehr übergibt ausdrücklich `allow_insecure_tls=False`
und kann damit nie herabgestuft werden. Entspricht S3 und Entscheidung f).

---

## 3. Zusammenfassung

| Nr. | Punkt | Status |
|---|---|---|
| P1 | `_get_compiled_pattern` ohne Cache | behoben |
| P2 | Uneinheitliche Regex-Flags zwischen `parse()` und `parseSingleResult()` | dokumentiert, Angleichung als eigener Durchgang vorgeschlagen |
| P3 | Zeichentabelle: `&#xDC;`→`³` falsch, ` `→`h` falsch, 54 Fälle statt aller Entities | Vorschlag `html.unescape()`, **Freigabe nötig** |
| H-A | `updateManager` umgeht die TLS-Richtlinie | in den Repo-Auftrag b) verschoben |
| H-B | TLS-Standardwerte | geprüft, kein Befund |
| — | Parser-Framework wechseln | abgelehnt, begründet |
| — | HTTP-Framework wechseln | abgelehnt, begründet |
