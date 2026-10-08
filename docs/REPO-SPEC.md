# Spezifikation: Kodi-Repository GerXStream

Stand: 2026-10-09. Quelle: `https://gitlab.com/gerxstream/gerxstream`, Branch `main`.

## Aktueller Release-Stand

- GerXStream: **1.0.30**. Repository-Addon: **1.0.7**.
- `.gitlab-ci.yml` fuehrt zuerst die Tests und dann den Pages-Build aus.
- `tools/build-gitlab-pages.sh` verwendet `tools/build_repo.py` und die von
  GitLab gelieferte `CI_PAGES_URL`. Versionsnummern werden aus den Manifesten
  gelesen, ResolveURL aus dem neuesten versionierten `release-inputs/`-Archiv.
- Die Pages-Ausgabe `public/` wird in CI gebaut, nicht in Git committet.
  Lokale Pakete unter `repo/` und `dist/` sind ebenfalls generierte Ausgaben.
- Aktuelle Kodi-Quelle: `https://gerxstream-db50a2.gitlab.io/`.
- Installation: `repository.gerxstream-1.0.7.zip` im Pages-Wurzelverzeichnis.
- Katalog: `catalog/addons.xml` und `catalog/addons.xml.md5`.
- ZIPs: `zips/<addon-id>/<addon-id>-<version>.zip`.
- Der Katalog enthaelt GerXStream, das Repository-Addon selbst und
  `script.module.resolveurl`. Die verpflichtende ResolveURL-Untergrenze ist
  **5.1.209**, diese Version wird mitgeliefert.
- Updates erfolgen ueber Kodis Add-on-Verwaltung, nicht durch eigenes
  Entpacken nach `special://home/addons/`.
- Die optionalen GitHub-Workflows bleiben als Mirror-Build erhalten; das
  primaere Push- und Veroeffentlichungsziel ist GitLab.

Lokaler Build:

```sh
python tools/build_repo.py --out dist --force --pages-url https://gerxstream-db50a2.gitlab.io
```

## Historischer Entwurf

Die folgenden Abschnitte dokumentieren den Entwurf vom 2026-09-21. Alte
Versionsnummern, GitHub-URLs, optionale ResolveURL-Abhaengigkeiten und geplante
Selbst-Updates sind **nicht** der aktuelle Implementierungsstand. Fuer
Installation und Release-Build gilt ausschliesslich der Abschnitt oben.

---

## 1. Dateibaum

```
gerxstream/repo/                     (Branch: main)
├── addons.xml                       Katalog aller ausgelieferten Addons
├── addons.xml.md5                   MD5 von addons.xml, roh, ohne Dateiname
├── repository.gerxstream/
│   ├── addon.xml                    Das Repo-Zeiger-Addon (Quelle)
│   ├── icon.png                     512x512
│   └── fanart.jpg                   1280x720 oder 1920x1080
├── repository.gerxstream-<version>.zip  Installierbares Zip des Repo-Addons
└── zips/
    ├── plugin.video.gerxstream/
    │   ├── addon.xml                Kopie der addon.xml der neuesten Version
    │   ├── icon.png
    │   ├── fanart.jpg
    │   ├── changelog.txt            Changelog der neuesten Version
    │   ├── changelog-1.0.0.txt      Changelog je Version (optional)
    │   └── plugin.video.gerxstream-1.0.0.zip
    └── repository.resolveurl/
        └── repository.resolveurl-1.0.0.zip     (spaeter, siehe Abschnitt 5)
```

Wichtig: Im Zip liegt das Addon in einem Ordner, der **exakt** der Addon-ID
entspricht — also `plugin.video.gerxstream/…` als oberste Ebene im Archiv.

---

## 2. `repository.gerxstream/addon.xml`

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="repository.gerxstream"
       name="GeerXStream Repository"
       version="1.0.0"
       provider-name="flowinthefluid">
  <extension point="xbmc.addon.repository" name="GeerXStream Repository">
    <dir>
      <info compressed="false">https://flowinthefluid.github.io/gerxstream/repo/catalog/addons.xml</info>
      <checksum>https://flowinthefluid.github.io/gerxstream/repo/catalog/addons.xml.md5</checksum>
      <datadir zip="true">https://flowinthefluid.github.io/gerxstream/repo/zips/</datadir>
    </dir>
  </extension>
  <extension point="xbmc.addon.metadata">
    <summary lang="de_de">GeerXStream Repository</summary>
    <description lang="de_de">Bezugsquelle fuer GeerXStream und dessen Abhaengigkeiten.</description>
    <platform>all</platform>
    <license>GPL-3.0-only</license>
  </extension>
</addon>
```

`<datadir zip="true">` zeigt auf `zips/`. Kodi haengt daran selbst
`<addon-id>/<addon-id>-<version>.zip` an. Deshalb muss unter `zips/` je Addon
ein Ordner mit dem Addon-Namen liegen.

`<dir>` statt der flachen Variante ist die Form, die Kodi 19+ erwartet; sie
erlaubt spaeter mehrere `<dir>`-Bloecke, falls du je Kodi-Version getrennte
Zweige ausliefern willst (`<dir minversion="21.0.0" maxversion="21.9.9">`).

---

## 3. `addons.xml`

Enthaelt die vollstaendige `<addon>`-Deklaration jedes ausgelieferten Addons,
eingeschlossen in `<addons>`. Die `<addon>`-Bloecke sind woertliche Kopien der
jeweiligen `addon.xml` **ohne** deren XML-Deklaration.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addons>
  <addon id="repository.gerxstream" name="GeerXStream Repository" version="1.0.0" provider-name="flowinthefluid">
    ...
  </addon>
  <addon id="plugin.video.gerxstream" name="GeerXStream" version="1.0.0" provider-name="flowinthefluid">
    ...
  </addon>
</addons>
```

`addons.xml.md5` enthaelt **ausschliesslich** den MD5-Hex-String von
`addons.xml`, ohne Dateinamen, ohne Zeilenumbruch am Ende:

```sh
md5sum addons.xml | cut -d' ' -f1 | tr -d '\n' > addons.xml.md5
```

Stimmt der Hash nicht, aktualisiert Kodi den Katalog stillschweigend nicht —
eine haeufige und schwer zu findende Fehlerquelle.

---

## 4. Was `checkVersion()` spaeter liest

Der Update-Pfad wird in einem eigenen Auftrag verdrahtet. Damit der Code dann
nicht erneut umgebaut werden muss, hier die Festlegung:

| Zweck | URL |
|---|---|
| Versionsabfrage | `https://flowinthefluid.github.io/gerxstream/repo/zips/plugin.video.gerxstream/addon.xml` |
| Zip-Download | `https://flowinthefluid.github.io/gerxstream/repo/zips/plugin.video.gerxstream/plugin.video.gerxstream-<version>.zip` |

Gelesene Felder:

- Aus der entfernten `addon.xml`: das Attribut `version` des `<addon>`-Elements
  mit `id="plugin.video.gerxstream"`. **Nicht** ueber `re.findall(...)[1]` wie
  bisher in `service.py:112` — dieser Index war ein Zufallstreffer der
  bisherigen Dateireihenfolge.
- Vergleich gegen `cConfig().getAddonInfo('version')`.
- Vergleich als Versionstupel (`tuple(int(x) for x in v.split('.'))`), nicht als
  String. Mit semver dreistellig (Beschluss j) ist das eindeutig.

Anforderungen an die Implementierung, wenn sie kommt:

- `requests.get(..., timeout=…)` — nie ohne Timeout (M16).
- Kein `except: pass` auf diesem Pfad (Beschluss 2.1).
- Ergebnis in jedem Fall auf `LOGINFO`: geprueft / aktuell / Update gefunden /
  fehlgeschlagen samt Grund.
- Entpacken ausschliesslich ueber die in S4 abgesicherte Routine
  (Zielpfad normalisieren, gegen das Zielverzeichnis pruefen).

---

## 5. ResolveURL

Umgesetzt: `repository.resolveurl` (Zeiger auf `Gujal00/smrzips`, **nicht**
`script.module.resolveurl` selbst) wird unter `zips/repository.resolveurl/`
mitgehostet. Nutzer installieren damit ueber unsere eigene Quelle sowohl
GerXStream als auch die ResolveURL-Repository-Quelle, ohne das ResolveURL-Repo
von Hand suchen zu muessen. Begruendung fuer den reinen Zeiger (statt eines
gespiegelten `script.module.resolveurl`) siehe D1-Bericht: ein gespiegeltes
ResolveURL veraltet und reisst die Hoster-Aufloesung mit.

Zusaetzlich wurde die Versionsangabe in `addon.xml` von `5.1.173` auf `5.1.0`
gesenkt (weiterhin `optional="true"`): Kodi deaktiviert ein Addon auch bei
*optionalen* Abhaengigkeiten hart, wenn eine bereits installierte Version die
verlangte Untergrenze unterschreitet — das war die Ursache dafuer, dass
GerXStream bei manchen Nutzern mit vorhandenem, aber aelterem ResolveURL gar
nicht erst startete. Die inhaltliche Mindestempfehlung (`5.1.208`, Hoster-
Aktualitaet) bleibt als reiner Laufzeit-`LOGWARNING` in `service.py` bestehen.

### Offener Punkt: `resolverUpdate()` faellt weg

`updateManager.resolverUpdate()` laedt ResolveURL als GitHub-Zipball
(`Gujal00/ResolveURL` bzw. `fetchdevteam/snipsolver`) und entpackt es selbst
nach `special://home/addons/script.module.resolveurl` — an Kodis
Addon-Verwaltung vorbei. Aufrufer: `service.py:166` beim Start, sowie
`devUpdates()` (`updateManager.py:304`) hinter dem Menueeintrag
"Manuelles Update" (`xstream.py:288-292`).

Sobald `repository.resolveurl` in diesem Repo als regulaerer Versorgungsweg
steht, faellt die Selbstinstallation **ersatzlos** weg: `resolverUpdate()`,
`UpdateResolve()`, der Aufruf beim Start, der Resolver-Teil von `devUpdates()`
und die zugehoerigen Einstellungen (`resolver.branch`, `githubUpdateResolver`,
`enforceUpdate`) werden entfernt. Updates kommen dann ueber die
Addon-Verwaltung.

Bis dahin bleibt die Funktion bestehen — mit dem in S4 abgesicherten Entpacken
und einem `LOGINFO`, wenn sie anlaeuft. Kein stilles Entpacken in fremde
Verzeichnisse.

---

## 6. Veroeffentlichungs-Checkliste je Version

1. `addon.xml` im Plugin: `<version>` erhoehen, `<news>` fuellen.
2. `changelog.txt` ergaenzen.
3. Zip bauen: oberste Ebene im Archiv = Ordner `plugin.video.gerxstream`.
4. Zip nach `zips/plugin.video.gerxstream/` legen.
5. `addon.xml`, `icon.png`, `fanart.jpg`, `changelog.txt` daneben aktualisieren.
6. `<addon>`-Block in `addons.xml` auf die neue Version heben.
7. `addons.xml.md5` neu erzeugen (siehe Abschnitt 3).
8. Commit und Push auf `main`.
