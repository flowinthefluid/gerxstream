Befundkatalog — GerXstream for Kodi (plugin.video.gerxstream)
Rekonstruiert aus dem Audit-Report der Phase A sowie allen seither getroffenen Entscheidungen. Dies ist die verbindliche Quelle für alle Befund-Kennungen. Ablage: docs/BEFUNDE.md im Repo, damit sie nicht an einer Sitzung hängt.

Zeilennummern beziehen sich auf den Ausgangsstand (Commit „Etappe 0: Ausgangsstand ohne jsnprotect.py"). Nach den Etappen 1 ff. können sie abweichen — die Kennung gilt, nicht die Zeile.

Ziel: Kodi 22 „Piers" (Python 3.14.x) primär, Kodi 21 „Omega" als weicher Fallback. Kodi 19/20 sind kein Ziel.
Schweregrade
Grad	Bedeutung
Blocker	Addon startet oder läuft unter Kodi 22 nicht
Blocker-Sec	release-blockierend aus Sicherheitsgründen
Blocker-Dist	Addon ist nicht installierbar / nicht verteilbar
Hoch	Funktion bricht in bestimmten Fällen
Mittel	Deprecation, bricht in einer künftigen Version
Niedrig	Stil, Wartbarkeit
Status-Werte
offen · erledigt · freigegeben (entschieden, noch nicht umgesetzt) · verschoben (eigener Auftrag) · entfällt


Blocker — Kodi-22-Lauffähigkeit
ID	Datei:Zeile	Befund	Fix	Status
B1	resources/lib/tmdbinfo.py:44	xbmcgui.WindowXMLDialog.__init__(self) — unbound Base-Call auf SWIG-Klasse. Unter Py3.14 TypeError. Zusätzlich gehen die vier Konstruktorargumente verloren.	super().__init__(*args, **kwargs)	erledigt (Etappe 1)
B2	resources/lib/player.py:11	xbmc.Player.__init__(self, *args, **kwargs) — dasselbe Muster. Bricht jede Wiedergabe.	super().__init__(*args, **kwargs)	erledigt (Etappe 1)
Sicherheit
ID	Datei:Zeile	Befund	Fix	Status
S1	sites/aniworld.py:403, sites/serienstream.py:411, sites/burningseries.py:364	if type(hUrl) == str: hUrl = eval(hUrl) — hUrl stammt aus dem url-Parameter der plugin://-URL. Beliebige Codeausführung durch jedes andere Addon, jeden Favoriteneintrag, jeden Webinterface-Aufruf.	ast.literal_eval() + try/except (ValueError, SyntaxError)	freigegeben — Etappe 2, erster Commit, zusammen mit S8
S2	resources/lib/tmdb.py:313, resources/lib/tmdbinfo.py:58,60	eval() auf TMDB-Antwortdaten. Zusammen mit S3 ⇒ RCE über MITM. _meta['credits'] wird absichtlich als Python-Literal-String serialisiert und später wieder ge-evalt.	Datenstruktur als dict durchreichen statt als String; falls Kompatibilität nötig ast.literal_eval. Serialisierungspfad beidseitig anpassen (setItemValues).	freigegeben — Etappe 2
S3	resources/lib/handler/requestHandler.py:93,172-175	ssl_verify=False ist Default, kein Aufrufer setzt ihn. check_hostname=False, verify_mode=CERT_NONE für allen Scraper-, TMDB- und Captcha-Traffic. Der certifi-Pfad (CustomSecureHTTPSHandler) ist toter Code.	Default auf True. Plus freigegebenes Setting plugin_<id>_allowInsecureTLS (Default aus) zur Abschaltung pro Seite; bei Nutzung LOGWARNING mit Domainnamen. certifi-Pfad reaktivieren oder durch ssl.create_default_context() ersetzen — Wahl begründen.	freigegeben — Etappe 2, einzeln melden vor dem Commit
S4	resources/lib/updateManager.py:177-188	Zip-Slip: dest = os.path.join(LocalDir, "/".join(n.split("/")[1:])) ohne Pfadprüfung. Das Zip kommt von einem in den Settings frei konfigurierbaren GitHub-Repo. ..-Einträge schreiben beliebig ins Dateisystem.	Ziel normalisieren, gegen LocalDir prüfen (os.path.commonpath), Einträge außerhalb überspringen.	freigegeben — Etappe 2
S5	resources/lib/updateManager.py:109,123,198-210	Update() bekommt plugin_id aus einem Setting und schreibt nach special://home/addons/<plugin_id>. removeFilesNotInRepo() löscht rekursiv nach Dateinamen ohne Pfadbezug.	plugin_id gegen Whitelist/Regex prüfen; Löschlogik pfadbasiert statt basename-basiert.	freigegeben — Etappe 2
S6	resources/lib/jsnprotect.py:4	Vierfach verschachteltes exec(base64). Deobfuskiert: ~100 hartcodierte E-Mail;Passwort-Paare, per random.choice gewählt. Nirgends importiert.	Datei löschen, vor git init, damit sie nie in die Historie gerät.	erledigt (Etappe 0)
S7	resources/lib/tools.py:414-424	cCache.get() macht eval() auf eine Property von xbmcgui.Window(10000). Fenster 10000 ist Kodi-global, jedes Addon kann dort schreiben. Cache-Inhalt = HTML ganzer Seiten (nur wenn volatileHtmlCache an). Kein TTL, keine Größen- oder Anzahlgrenze; gelöscht wird nur beim Lesen nach Ablauf.	json.dumps/json.loads statt repr/eval. Plus Mengenbegrenzung: Schlüsselregister als eigene Property, Anzahlgrenze 200, älteste verwerfen; abgelaufene Einträge zusätzlich beim Service-Start räumen. Keine Bytegrenze — über Stringlängen nur scheinbar messbar.	freigegeben — Etappe 2
S8	xstream.py:172-175	__import__(sSiteName) + getattr(plugin, sFunction) — beide Namen ungefiltert aus der URL. Nachgewiesen erreichbar: 52 Module über ?site= (10 in resources/lib, 4 in gui, 8 in handler, 27 in sites, 3 im Wurzelverzeichnis, darunter service und default). plugin://…/?site=utils&function=kill führt den Killswitch aus.	sSiteName nur gegen die von pluginHandler gefundenen Scraper-Module zulassen. sFunction gegen explizite Whitelist erlaubter Einstiegsfunktionen. Bei Verstoß LOGERROR + sauberer Abbruch, kein stiller Fallback. Die 52-Module-Zahl gehört in den Commit-Body.	freigegeben — Etappe 2, erster Commit, zusammen mit S1
Hoch
ID	Datei:Zeile	Befund	Fix	Status
H1	resources/lib/handler/pluginHandler.py:654 vs. resources/settings.xml	Gelesen wird plugin_<id>_checkdomain (klein-d), definiert ist plugin_<id>_checkDomain (groß-D, 19×). Setting-IDs sind case-sensitiv ⇒ die automatische Domain-Prüfung läuft nie. Zeile 650 schreibt ebenfalls auf die falsche ID.	Schreibweise auf _checkDomain angleichen. Zusammen mit dem Umbau: Prüfung aus service.py herausnehmen, an einen Menüpunkt „Scraper prüfen" hängen; optionaler Hintergrundlauf mit ThreadPoolExecutor max. 4–6 parallel, 5 s Timeout, daemon=True, Abbruch über xbmc.Monitor.	freigegeben — Etappe 5
H2	resources/lib/config.py:46-49	setSetting() prüft if id and value: — Setzen auf '' ist ein No-op. Alle „lösche Settings-Eintrag"-Aufrufe (6 Stellen) wirken nicht.	if id is not None:	freigegeben — Etappe 5
H3	resources/lib/handler/requestHandler.py:422-435	content wird nur im try zugewiesen; schlägt open() fehl ⇒ UnboundLocalError, bricht die komplette Listenerstellung ab.	content = None vor dem try, return None im Fehlerfall.	freigegeben — Etappe 4
H4	resources/lib/gui/hoster.py:82	if not 'filemoon' in siteResult['streamUrl'] — siteResult hat Default False (⇒ TypeError), im streamID-Pfad fehlt streamUrl (⇒ KeyError).	(siteResult or {}).get('streamUrl', '')	freigegeben — Etappe 4
H5	resources/lib/gui/hoster.py:101	list_item.setArt(data['thumb']) — String statt dict. Im Auto-Modus schluckt except: in __autoEnqueue den Fehler ⇒ stille Wiedergabefehler.	setArt({'thumb': …, 'poster': …})	freigegeben — Etappe 4
H6	resources/lib/handler/pyLoadHandler.py:9,38,45,48-49	from string import maketrans (Py2, entfernt) ⇒ ImportError beim Import. Zusätzlich str().decode(), Request(url, str) statt bytes, bytes.close(). Der pyLoad-Versand ist seit der Py3-Migration tot.	Modul auf Py3 portieren (str.maketrans, .encode(), Response korrekt schließen). Ohne pyLoad-Instanz nicht testbar.	freigegeben — Etappe 4
H7	sites/kinox.py:630	from urllib2 import build_opener, HTTPError im try — greift nie, except ImportError fängt es ab. Toter Py2-Rest im heißen Pfad.	Py2-Zweig entfernen.	freigegeben — Etappe 4
H8	resources/lib/tmdbinfo.py:104-112	isinstance(meta[prop], unicode) ⇒ NameError ⇒ except-Zweig ⇒ setProperty(prop, meta[prop].encode('utf-8')) übergibt bytes an eine str-API ⇒ TypeError. Der Info-Dialog bleibt weitgehend leer.	Beide Zweige auf str(...) reduzieren.	freigegeben — Etappe 4
H9	resources/lib/captcha/captcha_solver.py:169-178	Einrückungsfehler: die while-Schleife steht außerhalb von if 'captchaid' in data:. Fehlt captchaid, sind captcha_id und tries ungebunden ⇒ NameError.	while-Block in das if einrücken, sonst früh zurückgeben.	freigegeben — Etappe 4
H10	xstream.py:327,353,478	dialog.update(… // numPlugins) bzw. … // total ohne Nullprüfung ⇒ ZeroDivisionError, wenn kein Scraper aktiv ist bzw. die Suche nichts findet.	max(1, n) bzw. vorher abbrechen.	freigegeben — Etappe 4
H11	resources/lib/download.py:111	Fehlt Content-Length, ist iTotalSize = -1 ⇒ negativer Prozentwert an DialogProgress.update(). Zusätzlich 'content-length' in headers vs. Zugriff headers['Content-Length'].	Auf iTotalSize <= 0 prüfen, unbestimmten Fortschritt anzeigen.	freigegeben — Etappe 4
H12	resources/lib/download.py:62-67	Wirft __createProcessDialog(), ist self.__oDialog ungebunden ⇒ AttributeError in Zeile 67. Kein finally. __download() schließt f im except, obwohl f ungebunden sein kann.	try/finally, Dialog vorab auf None.	freigegeben — Etappe 4
H13	resources/lib/gui/hoster.py:291-377	stream() gibt an vier Stellen zurück ohne self.dialog.close(); der zweite DialogProgress (Z. 361) wird nur im Erfolgsfall geschlossen. Hängende Fortschrittsdialoge.	try/finally um den Dialog-Lebenszyklus.	freigegeben — Etappe 4
H14	resources/lib/handler/pluginHandler.py:628-665	Ein Thread pro Scraper (~19–27), alle mit Netzwerk-I/O, ohne Monitor.abortRequested(), ohne daemon=True, mit unbegrenztem t.join(). Blockiert Kodis Shutdown. Alle Threads schreiben parallel setSetting. Gleiches Muster in den vier Suchfunktionen xstream.py:343/415/469.	ThreadPoolExecutor mit Limit, daemon=True, Abbruch über xbmc.Monitor.	freigegeben — Etappe 7 (Domain-Check-Teil zusammen mit H1 in Etappe 5)
H15	service.py:86-142	checkVersion('xstream') greift, weil getAddonInfo('id') == 'plugin.video.xstream'. Der Dienst lädt die Upstream-Version, löscht special://home/addons/plugin.video.xstream und entpackt Upstream dorthin. Zusätzlich checkDependence('plugin.video.xstream') (Z. 179) fest verdrahtet.	Variante (ii): deaktivieren statt umbiegen, aber nicht still — einmalig LOGINFO beim Start („Selbst-Update deaktiviert, kein Repo hinterlegt") und eine Zeile im Dialog „Plugin Informationen". Kein except: pass auf diesem Pfad. Verdrahtung gegen github.com/flowinthefluid/gerxstream4kodi als eigener Auftrag, sobald das Repo steht.	freigegeben — Etappe 3
H16	addon.xml:2 vs. Ordnername	ID ist plugin.video.xstream, der Ordner heißt plugin.video.gerxstream. Jeder Code, der Pfade aus der ID baut, greift ins Leere: tools.changelog() (T:53), tools.devWarning() (T:69), tmdbinfo.py:219. InstallAddon(plugin.video.xstream) installiert eine zweite Kopie.	ID auf plugin.video.gerxstream. Die 45 hartcodierten ID-Vorkommen (kids_tube.py allein 27×) nicht durch die neue ID ersetzen, sondern durch getAddonInfo('path')/getAddonInfo('id'). Migration: beim ersten Start addon_data/plugin.video.xstream/ erkennen, Settings/pluginDB/Cookies/Cache kopieren, Marker-Datei. Alte Installation erkennen ⇒ einmaliger Hinweisdialog.	freigegeben — Etappe 3
H17	resources/lib/player.py:52-58	streamFinished wird nur in onPlayBackStopped() gesetzt. onPlayBackError ist nicht implementiert. Scheitert die Wiedergabe, ohne je zu starten (toter Hoster-Link, 403, abgelaufene Stream-URL), feuert kein Callback — die Schleife läuft bis zum Kodi-Ende und pollt alle 10 s. Jeder Fehlversuch hinterlässt Thread, Player-Callback-Instanz und Monitor.	onPlayBackError implementieren (streamSuccess = False, streamFinished = True). Harte Obergrenze für die Schleife (Abbruch, wenn nach 60 s nichts spielt und nie etwas gespielt hat). waitForAbort(10) → waitForAbort(1). & → and. Commit-Body aus der Funktion heraus begründen, nicht aus dem Absturzverdacht.	freigegeben — Etappe 4
Mittel
ID	Datei:Zeile	Befund	Fix	Status
M1	resources/lib/config.py:5	import resolveurl auf Modulebene. Fehlt ResolveURL, stirbt das Addon mit ImportError statt mit dem vorgesehenen Dialog.	Import in isBlockedHoster() verschieben.	erledigt (Etappe 1)
M2	24 Dateien (Liste unten)	Ungültige Escape-Sequenzen ⇒ SyntaxWarning unter 3.12–3.14, künftig SyntaxError. Füllt das Log bei jedem Import. Kein Blocker unter 3.14.	Betroffene Literale auf Raw-Strings.	freigegeben — Etappe 6
M3	resources/lib/gui/gui.py:109, resources/lib/gui/hoster.py:110	ListItem.setInfo() — seit Kodi 20 deprecated. gui.py ruft es immer auf und danach zusätzlich setInfoTagVideo(); Werte werden doppelt gesetzt.	Auf getVideoInfoTag() umstellen, setInfo() entfernen. Prüfen, ob script.module.infotagger im Piers-Repo verfügbar ist. Liste der umgezogenen Felder in den Bericht, für die Sichtprüfung.	freigegeben — Etappe 8, sofort auflösen (kein Doppelaufruf belassen)
M4	resources/lib/gui/gui.py:184-187	if 'genre' in itemValues: → vtag.setGenres(itemValues['genres']…). Schlüssel-Verwechslung; tmdb._format() setzt genre. except: pass verbirgt es ⇒ Genres werden nie gesetzt.	Auf itemValues['genre'] korrigieren.	freigegeben — Etappe 4
M5	resources/lib/gui/guiElement.py:19	DEFAULT_FANART = path.join(getAddonInfo('path'), 'fanart.jpg') — im Addon-Root liegt keine Bilddatei. Der Pfad ist heute schon tot; jedes ListItem bekommt ein nicht existierendes Fanart. Deklariert ist resources/fanart.jpg.	getAddonInfo('fanart') verwenden (löst den deklarierten Wert auf). Präzedenz: gui.py:394-418 nutzt bereits getAddonInfo('icon').	freigegeben — Etappe 4
M6	xstream.py:341,412,466	t.getName() — seit Python 3.10 deprecated.	t.name	freigegeben — Etappe 6
M7	resources/lib/download.py:66, resources/lib/updateManager.py:221,312	log(e) übergibt ein Exception-Objekt an xbmc.log(msg: str) ⇒ TypeError innerhalb des Fehlerbehandlers.	log(str(e), LOGERROR)	freigegeben — Etappe 4
M8	addon.xml:4	<import addon="xbmc.python" version="3.0.0"/>	Auf 3.0.1 anheben. Begründung über die ABI: xbmc.python in xbmc/master ist 3.0.2 mit <backwards-compatibility abi="3.0.0"/>, Kodi 21 liefert 3.0.1. 3.0.2 zu fordern würde Kodi 21 ausschließen.	erledigt (Etappe 1)
M9	addon.xml:7	script.module.six gefordert, nirgends importiert.	<import> entfernen. Hinweis: ResolveURL zieht six und kodi-six transitiv nach — das bleibt so, ist aber nicht unser Problem.	freigegeben — Etappe 8
M10	resources/lib/handler/requestHandler.py:12	import certifi, aber script.module.certifi nicht in <requires>. Funktioniert heute nur transitiv über script.module.requests.	Deklarieren oder (mit S3) auf ssl.create_default_context() ohne cafile umstellen.	freigegeben — Etappe 8
M11	addon.xml:8	<import addon="repository.xstream" version="1.2.4"/> — nicht-optional. Das Backend streamxstream/xStreamRepo ist bestätigt 404; AddonInstaller.cpp:567-593: fehlt eine nicht-optionale Abhängigkeit in allen aktivierten Repos, bricht die Installation des gesamten Addons ab. Das Addon ist damit auf einem sauberen Gerät heute nicht installierbar.	Zeile entfernen, nicht wiederbeleben.	hochgestuft auf Blocker-Dist — freigegeben, letzter Commit der Etappe 2
M12	addon.xml	Kein <news>; lang="de" statt lang="de_de"; <license> als Fließtext statt SPDX; Version 4.3.0.5 vierteilig.	Ergänzen/normalisieren. SPDX GPL-3.0-only. Version → 1.0.0 (Neustart, da die ID wechselt; für Kodi kein Downgrade).	freigegeben — Etappe 8 (Version in Etappe 3)
M13	resources/lib/tools.py:108, resources/lib/gui/gui.py:378,405,413	Default-Argumente rufen beim Import cConfig().getAddonInfo()/getLocalizedString() auf — Kodi-API-Zugriff zur Importzeit, Werte danach eingefroren.	Default None, Auflösung im Funktionsrumpf.	freigegeben — Etappe 8
M14	resources/lib/utils.py:11	progressDialog = xbmcgui.DialogProgress() auf Modulebene — ein globaler, geteilter Dialog.	In download_url() instanziieren.	freigegeben — Etappe 7
M15	sites/dokus.py:22, sites/kids_tube.py:27	cConfig().setSetting(...) auf Modulebene. pluginHandler importiert jedes Site-Plugin ⇒ Settings-Schreibvorgang bei jedem Discovery-Lauf.	In load() verschieben.	freigegeben — Etappe 8
M16	sites/kids_tube.py:356, service.py:110, updateManager.py:170,215, myjdapi.py:404,419	requests.get(...) ohne timeout ⇒ die GUI kann unbegrenzt hängen.	Überall timeout= setzen.	freigegeben — Etappe 7
M17	resources/lib/handler/requestHandler.py:126	socket.setdefaulttimeout() setzt einen prozessweiten Default — betrifft auch andere Addons im selben Interpreter.	Timeout pro Request übergeben. Vorrang innerhalb Etappe 7. Darf spätere rohe http://ip:port-Streams nicht ausschließen.	freigegeben — Etappe 7
M18	resources/lib/captcha/captcha_solver.py:135,174-176	Polling mit time.sleep(2) / xbmc.sleep(1000) bis zu 120 s, ohne Monitor.waitForAbort(), ohne Abbruchmöglichkeit.	Auf xbmc.Monitor().waitForAbort() umstellen.	freigegeben — Etappe 7
M19	xstream.py:172-173	Bis zu 60 s time.sleep(5) im Main-Thread beim Aufbau des Hauptmenüs, während auf das Service-Fertigsignal gewartet wird.	Monitor().waitForAbort(1) in der Schleife.	freigegeben — Etappe 7
M20	resources/lib/tools.py:87-104	textBox() öffnet Fenster 10147 per executebuiltin und pollt while getCondVisibility(...): xbmc.sleep(500).	Dialog().textviewer() (wird in pluginInfo() bereits genutzt).	freigegeben — Etappe 7
M21	default.py:36, requestHandler.py:278	traceback.format_exc().splitlines()[-3] ⇒ IndexError, wenn der Traceback kürzer ist. Der Fehlerbehandler kann selbst abstürzen.	Defensiv indizieren.	freigegeben — Etappe 4
M22	resources/lib/handler/myjdownloaderHandler.py:4	import myjdapi als Top-Level-Modul — funktioniert nur, weil default.py resources/lib/handler in sys.path schiebt. Aus dem Service-Kontext würde es fehlschlagen.	from resources.lib.handler import myjdapi	freigegeben — Etappe 8
M23	resources/lib/handler/myjdapi.py:14	class MYJDException(BaseException) — umgeht except Exception.	Von Exception ableiten.	freigegeben — Etappe 6
M24	resources/lib/tmdb.py:18, sites/kids_tube.py:348, resources/lib/youtube_fix.py:22-24	TMDB-API-Key, zwei YouTube-Data-API-Keys und ein Google-OAuth-Client-Secret im Klartext im Repo. Die YouTube-Keys gehen mit youtube_fix.py (Punkt e).	TMDB-Key: keine triviale Lösung — dokumentieren, ggf. rotieren.	freigegeben — Etappe 2 (teilweise, mit e) / Rest offen
M25	resources/lib/updateManager.py:162-165	Im except Exception: steht os.remove(offlineFile) — existiert die Datei nicht, wirft der Handler selbst.	os.path.exists() prüfen.	freigegeben — Etappe 4
M26	xstream.py:18-22	Nach dem „ResolveURL fehlt"-Dialog fehlt der Abbruch ⇒ parseUrl() läuft weiter und knallt mit NameError. Erst durch M1 erreichbar geworden.	endOfDirectory(handle, succeeded=False) vor sys.exit(), Handle-Ermittlung gegen fehlendes sys.argv[1] absichern.	erledigt (Etappe 1, Commit e8b4858)
Niedrig
ID	Fundstelle	Befund	Fix	Status
N1	resources/settings.xml	<settings version="1"> ist korrekt (v2-Format). Aber kein einziger getSettingBool/Int/Number/String-Aufruf, kein onSettingsChanged. Alles String-Vergleich (== 'true').	Schrittweise auf typisierte Getter. 189 Settings, breite Streuung.	verschoben — Etappe 10, eigener Durchgang
N2	resources/settings.xml	plugin_testplugin_checkDomain für ein nicht existierendes Site-Plugin.	Entfernen.	freigegeben — Etappe 5
N3	resources/language/.../de_de/strings.po	String 30249 („Send Pyload") fehlt im deutschen .po ⇒ leeres Label. 30283 existiert nur in en_gb. 32 leere msgstr.	Ergänzen/aufräumen.	freigegeben — Etappe 9
N4	sites/kids_tube.py:363,372	Hartcodierte UI-Texte 'Kids_Tube', 'Not found'.	Über strings.po.	freigegeben — Etappe 9
N5	resources/lib/gui/gui.py:112, resources/lib/gui/hoster.py:109	Versionsvergleich per String-Slice: kodi_version[:2] > '19'. Bricht ab Kodi 100 und bei ungewöhnlichen Buildstrings.	Numerisch parsen, eine gemeinsame Helper-Funktion. Kodi-19/20-Zweige entfallen (nur 22 + 21).	freigegeben — Etappe 8
N6	16 Dateien	85 nackte except: ohne Logging (gui.py 24×, hoster.py 12×, youtube_fix.py/utils.py je 6×). Verbirgt u.a. M4, H5, H9.	Auf except Exception + Logging, wo sinnvoll.	freigegeben — Etappe 9
N7	resources/lib/handler/pluginHandler.py:114-207	__updateSettings() (~95 Zeilen) plus vier _add_*_plugin-Helfer, deaktiviert (Z. 69 auskommentiert). Schreibt zur Laufzeit in die settings.xml im Installationsverzeichnis — auf Android/LibreELEC teils nicht schreibbar, bei jedem Update weg, mit dem v2-Format unvereinbar. Ursache der 189 Settings und von N2.	Löschen (~200 Zeilen).	freigegeben — Etappe 5
N8	resources/lib/tmdb.py:203	if 'episode_number': — konstant wahr.	Korrigieren oder entfernen.	freigegeben — Etappe 9
N9	resources/lib/gui/guiElement.py:335	if 'cover_url' in meta != '' — Verkettung ergibt ('cover_url' in meta) and (meta != ''). Zufällig funktional.	Klammern/klarstellen.	freigegeben — Etappe 9
N10	resources/lib/gui/hoster.py:226-261	for resolver in hmf.get_resolvers() überschreibt das Modul resolver; danach del(resolver) und Re-Import pro Schleifendurchlauf. Macht jede künftige ResolveURL-API-Prüfung schwerer, weil ein Name zwei Dinge bedeutet.	Schleifenvariable umbenennen, Import nach oben.	vorgezogen nach Etappe 4
N11	resources/lib/utils.py:147	def help(): return 'OK' — Platzhalter, überschattet das Builtin.	Entfernen.	freigegeben — Etappe 9
N12	resources/lib/tmdbinfo.py:22	print("TMDB - error") statt xbmc.log. Danach if 'tmdb_id' not in meta ⇒ NameError, falls der try scheiterte.	Logging + meta = {} initialisieren.	freigegeben — Etappe 9
N13	Paketinhalt	8 __pycache__-Ordner, .github/, ScraperInfo.txt im Release.	.gitignore (erledigt) + Build-Schritt für das Zip.	teilweise erledigt (Etappe 0)
N14	xstream.py, 4 Suchfunktionen	searchGlobal, searchAlter, searchTMDB zu ~80 % identisch (je ~50 Zeilen Thread-Fan-out + Dialog).	Gemeinsame Hilfsfunktion.	freigegeben — Etappe 9
N15	Logging, projektweit	Drei parallele Stile: cConfig().getLocalizedString(30166) + ' -> [modul]: ', logger.info('-> [modul]: '), '[xStream] -> [...]'. Ein lokalisierter String als Log-Präfix ist ungewöhnlich.	Auf logger vereinheitlichen. Berührt D3.2 (Präfix trägt den alten Namen).	freigegeben — Etappe 9
M2 — betroffene Dateien (24)
xstream.py, resources/lib/tools.py, resources/lib/tmdb.py, resources/lib/jsunpacker.py, resources/lib/gui/guiElement.py, resources/lib/handler/requestHandler.py, sowie sites/{aniworld,api_all,dokus,filmpalast,hdfilme,hdfilme_1,kinoger,kinokiste,kinox,kkiste,megakino,movie2k,movie4k,netzkino,serienstream,streamcloud,topstreamfilm,xcine}.py


Entscheidungen a)–l) aus der Phase-B-Freigabe
Punkt	Entscheidung	Status
a)	Addon-ID → plugin.video.gerxstream. Migration aus addon_data/plugin.video.xstream/ bauen (kopieren, Marker-Datei). Hartcodierte IDs durch getAddonInfo() ersetzen. Alte Parallelinstallation erkennen ⇒ Hinweisdialog.	freigegeben — Etappe 3 (siehe H16)
b)	Zwangsupdate auf eigenes Repo: github.com/flowinthefluid/gerxstream4kodi, User flowinthefluid. Repo ist derzeit leer ⇒ Variante (ii): deaktivieren, Spezifikation in docs/REPO-SPEC.md, Verdrahtung als eigener Auftrag.	freigegeben — Etappe 3 (siehe H15)
c)	resources/lib/jsnprotect.py löschen, vor git init.	erledigt (Etappe 0, siehe S6)
d)	utils.kill() / countdown() ersatzlos entfernen. Beweissicherung erfolgt (siehe S8).	freigegeben — Etappe 2
e)	resources/lib/youtube_fix.py entfernen. Vorher prüfen, ob ein Scraper darauf verweist; wenn ja, durch plugin://plugin.video.youtube/play/?video_id=<id> ersetzen. Die zwei YouTube-API-Keys und das OAuth-Client-Secret gehen mit (Teil von M24).	freigegeben — Etappe 2
f)	TLS-Default True plus freigegebenes Setting plugin_<id>_allowInsecureTLS pro Scraper (Default aus), Nutzung loggt LOGWARNING. Einzige Ausnahme von „keine neuen Features".	freigegeben — Etappe 2 (siehe S3)
g)	Domain-Check nicht löschen, umbauen: IDs fixen (H1/H2), aus service.py heraus, Menüpunkt „Scraper prüfen", gedrosselter Hintergrundlauf.	freigegeben — Etappe 5
h)	M3 sofort umstellen, Doppelaufruf auflösen, Feldliste liefern.	freigegeben — Etappe 8
i)	pyaes behalten. Der Tausch gegen pycryptodome bringt bei den paar Captcha-Strings nichts Messbares.	entschieden
j)	Version 1.0.0, dreistellig semver, pluginweit, keine Alpha-/Beta-Suffixe.	freigegeben — Etappe 3
k)	Keine Kodi-19/20-Fallbacks. gui.py:112, hoster.py:86,94,109 entfernen.	freigegeben — Etappe 8 (siehe N5)
l)	__updateSettings + Helfer löschen.	freigegeben — Etappe 5 (siehe N7)
Arbeitspunkte D
ID	Inhalt	Status
D1	ResolveURL: Bezugsquelle und Version. Untergrenze 5.1.208 (Begründung Hoster-Aktualität, nicht Kompatibilität — die API-Inventur zeigt keine brechende Änderung seit 5.1.173). repository.resolveurl bleibt vorerst optional="true", script.module.resolveurl bleibt nicht-optional. INSTALL.md anlegen: bis auf Weiteres muss das ResolveURL-Repo vorher installiert sein. Laufzeit-Check: installierte Version bedingungslos bei jedem Start auf LOGINFO, zusätzlich LOGWARNING bei Unterschreitung. Abschaffung von resolverUpdate() → Repo-Auftrag; S4-Fix jetzt; bis dahin LOGINFO, wenn die Funktion anläuft.	teilweise erledigt (REPO-SPEC), Rest Etappe 3
D2	Absturzuntersuchung — zurückgestuft, kein eigener Track. Ergebnisse in S8 und H17 überführt.	abgeschlossen
D3	Eigenständigkeit / Entflechtung. Siehe eigener Abschnitt in der laufenden Freigabe.	laufend
D4	Parser- und HTTP-Stack-Bewertung (neu).	offen
Etappenplan
Etappe	Inhalt
0	Git-Init, .gitignore, jsnprotect.py vorher löschen — erledigt
1	B1, B2, M8, M1, M26 — erledigt
2	S1+S8 (zusammen, erster Commit) · S4 · S7 · S2 · S5 · S3+f) · c)/d)/e) · M11 als letzter Commit
3	H16+a) · H15+b) · 45 ID-Vorkommen · M11-Nachlauf · j) Version 1.0.0 · D1-Laufzeitcheck
3b	D3.2/D3.3 — Inventur, Namensbestätigung, Rewrite
4	H3, H4, H5, H8, H9, H10, H11, H12, H13, H17 · M4, M5, M7, M21, M25 · H6, H7 · N10 (vorgezogen)
5	H1, H2 + g) · N2 · N7/l)
6	M2 · M6 · M23
7	H14 · M16, M17 (Vorrang), M18, M19, M20, M14
8	M3+h) · N5+k) · M9, M10, M12, M13, M15, M22
9	N3, N4, N6, N8, N9, N11, N12, N13, N14, N15
10	N1 (typisierte Settings-Getter) — eigener Durchgang
nach 9	Modul-/Dateinamen-Umbenennung (D3.5)
Geltende Arbeitsregeln
    • Ein Commit pro Befund-ID, Message <ID>: <kurz>, Begründung im Body.
    • Zwischenstand nach jeder Etappe, nicht alles am Stück.
    • Keine Features außer dem TLS-Opt-out aus f) und dem Laufzeit-Check aus D1.
    • Jede Verhaltensänderung vorher melden.
    • Kein Framework-Wechsel; xstream.py-Routing bleibt, abgesehen von S8.
    • script.module.inputstreamhelper bleibt in addon.xml (für die geplanten Livestream-Features).
    • Belegpflicht: jede Versionsangabe und jede „verifiziert"-Aussage mit exakter Datei-URL oder Commit-Hash. Ohne Beleg heißt es „angenommen".
    • Wenn ein Fix einen bisher unerreichbaren kaputten Pfad erstmals erreichbar macht, gehört der Folgefix in dieselbe Etappe.
Geplante Features — jetzt nicht bauen, nicht verbauen
    1. Favoritenverwaltung mit echten, verschachtelten Ordnern (SQLite in addon_data). ListItem-Erzeugung zentral in gui.py/guiElement.py halten.
    2. IPTV mit direkten ip:port-Adressen. TLS- und Timeout-Änderungen dürfen nicht global/socketweit wirken (siehe M17).
    3. Webcams für Live-Wetter (MJPEG/HLS/Standbilder). player.py erweiterbar halten, keine Annahme „jeder Stream kommt aus einem Hoster-Resolver".
    4. Livestreams: inputstream.adaptive + inputstreamhelper. Für echtes Live-TV mit EPG: M3U + XMLTV erzeugen und von pvr.iptvsimple konsumieren lassen, kein eigener PVR-Client.

