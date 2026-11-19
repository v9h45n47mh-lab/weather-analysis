# Weather Analysis

Home-Assistant-Integration mit Dashboard-Karte für vorhandene **mehrere Temperatur-, Wind- und Helligkeitssensoren**. Version **1.13.1**, HA UI Kit **1.12.0** lokal eingebunden.

## Funktionen

- **Wetter** mit anschaulichen 3-Stunden-Wetterzeilen untereinander: große lokale Wettersymbole, Temperaturen, Min/Max und kompakte Symbolzeilen. Gemessene Sensorwerte erscheinen blau, Vorhersagen schwarz auf weißer Lesefläche. Regenrisiko/-menge, Windrichtung, Wind/Böen, gefühlte Temperatur, Luftfeuchte und Luftdruck ergänzen die Vorhersage. **Heute** zeigt die Reihenfolge **Ist → Aktuell → Vorhersage**. Ist ist initial zugeklappt; Aktuell ist geöffnet und zeigt Temperatur, Wind und Temperatur-Min/Max heute. Wind steht bei Messwerten, Aktuell und Vorhersage in derselben Spalte. Helligkeit entfällt in der Wetterübersicht. Beide Faltzustände bleiben beim Nachladen und bei Reiterwechseln erhalten. Im Kopfbereich steht der Aufenthaltsort; Messpunkte erscheinen nur in 67459. **Wetter ist der Startreiter**; die Liste scrollt gemeinsam mit der Seite. Daneben **Temperatur**, **Wind** und **Helligkeit**, mit jeweils eigener Sensorauswahl aus den Karteneinstellungen.
- Relevante Sensoren aller drei Messarten im einklappbaren Bereich „Sensorauswahl“ vorauswählen, je Karte eigene Namen vergeben und per Ziehen sortieren. Die Reihenfolge gilt auch für die Dropdowns. Die ursprünglichen HA-Entitätsnamen bleiben erhalten.
- Schmale, links ausgerichtete Sensordropdowns und ein Aktualisieren-Symbol in der Kopfleiste aller Reiter. Kein Kartentitel und kein Feld Anzeigename.
- Zwei Kacheln über dem Chart: Aktuell mit Veränderung in 1 Std. sowie Minimum/Maximum.
- Durchschnittslinie mit Wert direkt im Chart; keine Durchschnitts- oder Spannenkachel.
- Helligkeit ohne Nachkommastellen in allen Messwerten, Trends und Chartdetails; Berechnungen bleiben unverändert präzise.
- Mit **+** einen zweiten vorausgewählten Sensor vergleichen: zwei durchgezogene farbige Kurven mit gemeinsamer Messwertskala, Namenslegende und Vergleichstabelle. **×** beendet den Vergleich. Beide Verläufe verwenden durchgezogene Linien in unterschiedlichen Farben.
- Geöffnete und geschlossene Bereiche bleiben bei Tag-/Wochen-/Monatswechsel, Sensorwechsel und Nachladen erhalten; jede Karte und Ansicht merkt ihre eigenen Zustände.
- Eine Integration für alle Sensoren. Auswahl ausschließlich in den Einstellungen der Karte, keine einzelne Integration je Thermometer.
- Aktueller Messwert, zeitlich gewichteter Durchschnitt sowie Minimum und Maximum.
- Verlauf mit Durchschnittslinie und Min-/Max-Band, Trends und Vortagesvergleich. Auflösung: **Tag 15 Minuten**, **Woche 1 Stunde**, **Monat 6 Stunden**, für alle drei Messarten und beide Vergleichssensoren.
- Maus oder Finger über den Chart bewegen: Zeit und Intervallmittel für beide Sensoren oberhalb des Charts; Minimum und Maximum stehen unterhalb. Messlücken bleiben als fehlende Werte erkennbar; Tab unterstützt die Tastaturbedienung.
- Weitere Kennzahlen, Vergleiche und Rekorde sind aufklappbar. Doppelte Monats- und Tageswerttabellen entfallen.
- Temperatur: Froststunden, Stunden ab 25/30 °C sowie nachgewiesene Frost-/Warm-/Heißtage.
- Wind: aktueller Wert und Kennzahlen in km/h. Sensoren in m/s, km/h, mph, Knoten und ft/s werden umgerechnet. Ein Sensor-Höchstwert ist keine separat gemessene Böe. Alternative Einheitenschreibweisen und leere Geräteklassen werden unterstützt.
- **Tag:** Aktuell zeigt **heute**, immer mit vollständiger Zeitachse **00:00–23:59 Uhr**. Zurück/vorwärts wechselt volle Kalendertage; Aktuell kehrt zu heute zurück. Messwerte reichen ausschließlich bis jetzt.
- **Woche:** Aktuell zeigt heute plus die letzten sieben Kalendertage. Zurück wechselt zur vollständigen vorherigen Kalenderwoche Montag–Sonntag. Vorwärts zeigt die aktuelle Kalenderwoche vollständig; Aktuell kehrt zur rollierenden Sicht zurück.
- **Monat:** voller Kalendermonat. In Kalenderansichten bleibt die vollständige Zeitachse sichtbar; Messwerte reichen höchstens bis jetzt. Zukünftige Zeiträume sind gesperrt. Links-/Rechtspfeile der Tastatur funktionieren bei fokussierter Karte, unabhängig von Eingabefeldern. Freier Zeitraum bis 366 Kalendertage.
- **Helligkeit:** separate Lux-Sensoren, aktueller Wert, Verlauf, Mittelwert, Extremwerte und Vergleiche.
- **Historie übernehmen** in den Einstellungen zum erneuten Import; bereits archivierte Detailwerte bleiben erhalten.
- Vorhandene Detailhistorie wird bei der ersten Sensorwahl importiert und sofort ausgewertet; ältere HA-Langzeitstatistik ergänzt verfügbare Zeiträume.
- Ausgewählte Sensoren werden auch bei geschlossener Karte weiter aufgezeichnet.
- Keine Heizgradtage, Raumtemperatur oder Heizgrenze.
- Mehrere unabhängige Karten, helle/dunkle Themes, Mobilansicht und lokale Brand-Icons.

## Installation und Update

1. HACS → Benutzerdefinierte Repositories → `https://github.com/v9h45n47mh-lab/weather-analysis`, Typ **Integration**.
2. **Weather Analysis** installieren/aktualisieren, Home Assistant neu starten und Browser/App vollständig neu laden.
3. Nur bei Erstinstallation: Einstellungen → Geräte & Dienste → Integration hinzufügen → **Weather Analysis**. Es wird noch kein Sensor ausgewählt.
4. Dashboard bearbeiten → Karte hinzufügen → **Weather Analysis**.
5. Über das Zahnrad den Bereich „Sensorauswahl“ der jeweiligen Messart aufklappen, mehrere Temperatur-, Wind- und Helligkeitssensoren wählen und speichern. Darunter im Bereich „Temperatur“, „Wind“ beziehungsweise „Helligkeit“ eigene Sensornamen vergeben und mit dem Ziehgriff sortieren. Die Reihenfolge wird erst mit Speichern übernommen; Pfeil hoch/runter am Griff unterstützt die Tastatur. In jeder Messansicht wechselst du oben links zwischen den vorausgewählten Sensoren; über **+** kommt ein zweiter Sensor zum Vergleich hinzu.

Bestehende Integrationen und ihre Archive funktionieren nach dem Update weiter. Bisherige einzelne Wind- und Helligkeitssensoren werden automatisch in die neue Mehrfachauswahl übernommen. Alte Einzeleinträge müssen nicht gelöscht werden; zusätzliche Einträge je Sensor entfallen. Der Repositoryname, die Integrationsdomain und der technische Kartentyp bleiben zur Kompatibilität erhalten.

```yaml
type: custom:weather-analysis-card
card_id: temperatur-garten
period: day
grid_options:
  columns: 12
  rows: auto
```

Die Kartenressource wird automatisch eingebunden. Bei kopierten Karten eine andere `card_id` verwenden, wenn die Einstellungen unabhängig sein sollen. Gleiche IDs teilen sich Einstellungen. Gespeicherte Einstellungen haben Vorrang vor YAML-Startwerten. Gespeicherte Sensoren werden serverseitig aufgezeichnet. Der Wechsel zwischen konfigurierten Sensoren und die Vergleichsauswahl verändern nur die aktuell betrachtete Karte. Die Klappzustände bleiben während der Verwendung der Karte erhalten. Weitere Kennzahlen unterhalb des Sensorvergleichs beziehen sich auf den ersten gewählten Sensor.

Manuell: `weather-analysis-1.13.1-manual.zip` herunterladen, den enthaltenen Ordner `custom_components/weather_analysis` nach `/config/custom_components/weather_analysis` kopieren und HA neu starten. `weather-analysis.zip` enthält den Integrationsinhalt für HACS.

## Wetter und 3-Stunden-Sicht

Der Reiter **Wetter** verwendet automatisch den GPS-Standort der mit dem angemeldeten Home-Assistant-Benutzer verknüpften **Person**. Dafür in HA die Person dem Benutzer zuordnen und ihren GPS-Tracker aus der Companion-App hinterlegen. Unter den eigenen lesbaren GPS-Trackern wird die zuletzt aktualisierte gültige Position verwendet; eine verfügbare Personenposition dient als Rückfall. Es wird niemals die Person eines anderen Benutzers ausgewählt. Tracker-Updates aktualisieren die Wetteransicht automatisch. Die zuletzt gemeldete Position gilt, solange HA sie bereitstellt; deaktiviertes Standorttracking kann daher einen alten Aufenthaltsort liefern.

**Heim-WLAN wird zuerst geprüft:** Vor einer Geräte-GPS-Abfrage und vor der Browser-Freigabe prüft die Karte serverseitig das gemeinsame Heim-WLAN, ohne GPS auszulesen oder einen Ortsdienst aufzurufen. Bei erkanntem Heim-WLAN werden weder `navigator.permissions.query` noch `navigator.geolocation.watchPosition` aufgerufen. Auch eine gespeicherte Geräte-Standortwahl bleibt zuhause pausiert. Beim Verbinden mit dem Heim-WLAN wird eine laufende Geräte-Abfrage beendet; abgelaufene Freigaben werden dort nicht angezeigt oder angefordert. Nach Verlassen wird eine gemerkte Geräteauswahl nur bei bereits gültiger Freigabe wieder aufgenommen. Kann die WLAN-Prüfung nicht abgeschlossen werden, startet Geräte-GPS nicht automatisch.

**Heim-WLAN hat Vorrang:** Meldet ein mit der eigenen HA-Person verknüpfter, lesbarer `device_tracker` mit `source_type: router` den Zustand `home`, gilt Böhl-Iggelheim inklusive Ist-Daten. Dafür ist keine Browser-GPS-Freigabe nötig. Router-Tracker müssen als Heim-Anwesenheit eingerichtet und mit der eigenen Person verknüpft sein.

Alternativ in **Einstellungen → Standort → Heim-WLAN** die Heim-SSID auswählen oder als WLAN-Namen hinzufügen und mit **Heim-WLAN speichern** übernehmen. Diese Einstellung gilt zentral für **alle Anwender und Karten** und darf nur von HA-Administratoren geändert werden. Aktiviere dafür in der HA-Companion-App den Sensor **SSID** (iOS) beziehungsweise **Wi-Fi-Verbindung** (Android). Die automatische Gerätezuordnung erfolgt über die HA-Geräteregistrierung und die mit der eigenen Person verknüpften Tracker. Es werden nur eigene, lesbare Mobile-App-Sensoren angeboten. Die Heim-SSIDs werden einmal zentral in HA gespeichert und gesichert; Änderungen gelten ohne Einrichtung pro Anwender für alle Karten. Die Zuordnung zum jeweils eigenen Gerät erfolgt automatisch. Reguläres Speichern einer Karte verändert die zentrale WLAN-Einstellung nicht. Netzwerke können in der zentralen Auswahl auch wieder abgewählt und mit Heim-WLAN speichern entfernt werden. Nur die explizit gewählten SSIDs gelten als zuhause, keine beliebigen fremden WLANs. Für einen Wechsel verwendet die Karte die von HA zuletzt gemeldeten Zustände; verzögerte Router-/SSID-Updates können daher auch die Erkennung verzögern. Die SSID wird weder an den Orts- noch an den Wetterdienst übertragen.

Im deutschen Postleitzahlgebiet **67459** zeigt Wetter **Ist → Aktuell → Vorhersage**. Die Messpunkte stammen aus der gespeicherten Sensorauswahl der Karte. Aktuell enthält Temperatur, Wind und Temperatur-Minimum/-Maximum heute. Helligkeit/lx wird hier nicht angezeigt. Ist startet zugeklappt, Aktuell geöffnet. Vergangene Abschnitte sind gemessene, zeitlich gewichtete Sensorwerte in Blau, anschließende Vorhersagen schwarz. Fehlende Messwerte werden nicht durch Vorhersagen ersetzt. Ist und Forecast verwenden denselben Abfragezeitpunkt. Außerhalb von 67459 werden ausschließlich die örtlichen Vorhersagen angezeigt; heimische Messwerte werden dafür nicht abgefragt. Die separaten Sensoranalysen bleiben zugänglich.

Der **Ortsname** steht im Kopfbereich. Ohne GPS und ohne erkannte Heim-WLAN-Verbindung erscheint ein Hinweis; zunächst wird nur der Forecast für Böhl-Iggelheim angezeigt. Mit **Standort dieses Geräts verwenden** lässt sich optional die Browser-/Gerätefreigabe anfordern, auch in Einstellungen → Standort. Diese Auswahl wird dauerhaft **auf dem verwendeten Gerät je HA-Benutzer und Karten-ID** gespeichert. Es werden nur die Auswahl und keine GPS-Koordinaten gespeichert. Beim erneuten Öffnen prüft die Karte zuerst die Browserfreigabe: Nur außerhalb des erkannten Heim-WLANs und bei `granted` wird GPS automatisch gestartet. Bei `prompt`, `denied` oder fehlender Permissions-API verwendet sie vorläufig den HA-Standort und fordert die Freigabe ausschließlich nach einem Knopfdruck erneut an. Die Gültigkeitsdauer der Freigabe wird vom Browser beziehungsweise Betriebssystem bestimmt und kann von einer Karte nicht erzwungen werden. Die Browserfunktion benötigt einen sicheren Kontext (HTTPS oder localhost) und die entsprechende Gerätefreigabe. **HA-Person verwenden** beendet die Standortabfrage, entfernt die gespeicherte Geräteauswahl und kehrt zum automatischen HA-Standort zurück. Die Betriebssystem-Berechtigung wird dabei nicht widerrufen. Ein fehlender Ortsname verhindert den GPS-Forecast nicht, schaltet aber keine Ist-Daten frei.

Die Vorhersage kommt von [Open-Meteo](https://open-meteo.com/) ohne API-Schlüssel. HA lädt sie serverseitig mit den auf vier Nachkommastellen gerundeten GPS-Koordinaten; pro Standort gilt ein 30-Minuten-Cache. Für Ortsnamen, Land und Postleitzahl verwendet HA [Photon](https://github.com/komoot/photon) mit [OpenStreetMap-Ortsdaten](https://www.openstreetmap.org/copyright); Ortsauflösungen werden zwölf Stunden im Arbeitsspeicher zwischengespeichert, fehlgeschlagene Abrufe zwei Minuten. Die beiden Dienste erhalten Koordinaten und benötigte Abfrageparameter, keine HA-Benutzernamen oder lokalen Sensorwerte. GPS-Koordinaten werden weder in Karteneinstellungen noch in Messarchiven gespeichert oder protokolliert. Die Standort-Caches sind begrenzt und werden bei HA-Neustart verworfen.

Der Forecast umfasst heute nur den verbleibenden Resttag und morgen den vollen Tag in der örtlichen Zeitzone des Aufenthaltsorts. Jeder 3-Stunden-Abschnitt lässt sich in seine echten Stundenwerte aufklappen. Die örtlichen Zeitfenster beginnen bei 00, 03, 06, 09, 12, 15, 18 und 21 Uhr. Der erste noch laufende Abschnitt beginnt jetzt. Die Temperatur bezieht sich auf den Beginn des Abschnitts; Wetterzustand und Wind berücksichtigen die im Abschnitt enthaltenen Stunden. Regenrisiko zeigt das höchste stündliche Risiko; Niederschlag die aufsummierte Menge. Angebrochene Stunden werden für Niederschlag anteilig geschätzt. Fehlende Werte werden als fehlend angezeigt.

Quelle und Abrufzeit stehen direkt an der Vorhersage. Bei einer Störung kann ein bis zu sechs Stunden alter Stand mit deutlicher Kennzeichnung weiter angezeigt werden; danach erscheint eine Fehlermeldung. Dafür benötigt HA Internetzugang. Die Wetterdaten sind Vorhersagen; Ist und Aktuell stammen ausschließlich von den eigenen Sensoren.

## Historie und Genauigkeit

Die erste Auswertung verwendet die vorhandenen Daten des gewählten Sensors:

1. **Detailhistorie:** Zeitlich gewichtete Werte, Grenzwertdauern und Extremzeiten werden aus aufgezeichneten Zustandswechseln berechnet und als 15-Minuten- sowie Stundenwerte gesichert. Einheiten werden je historischem Zustand umgerechnet. Bekannte Recorder-Ausfallzeiten sowie `unknown`/`unavailable` bleiben Lücken.
2. **Langzeitstatistik:** Für ältere Zeiträume werden verfügbare stündliche Durchschnitts-, Minimal- und Maximalwerte genutzt. Ohne `state_class: measurement` kann die Detailhistorie trotzdem ausgewertet werden; ältere Langzeitwerte sind dann gegebenenfalls nicht vorhanden.
3. **Fortlaufende Aufzeichnung:** Ab Auswahl ergänzen wir die Historie dauerhaft. Beim Update wird noch verfügbare Detailhistorie automatisch für 15-Minuten-Werte nachimportiert; bestehende Stundenarchive bleiben erhalten. Alte Abschnitte ohne Detailhistorie bleiben ausdrücklich als Stundenwerte erkennbar und werden nicht künstlich in Viertelstunden zerlegt. Vorhandene Archive werden erhalten und nicht doppelt gezählt.

Die rückwirkende Genauigkeit hängt von den noch gespeicherten HA-Daten ab. Gelöschte Detailhistorie lässt sich nicht rekonstruieren. Aus verdichteten Stundenwerten werden keine exakten Grenzwertdauern oder Extrem-Uhrzeiten erfunden. **≈** markiert Mittelwerte mit HA-Statistikanteil; die Karte zeigt Datenintervalle und Detailabdeckung.

Die Rekorde beziehen sich auf verfügbare Historie, eigene Archive und vorhandene Jahresstatistiken. Letztere enthalten keinen genauen Zeitpunkt. Windwerte verwenden die Messauflösung und Bedeutung des gewählten Sensors; die Karte erzeugt keine eigenständige Böenmessung.

Kalendergrenzen und Anzeige folgen der HA-Zeitzone einschließlich Sommer-/Winterzeit. Bei laufenden Zeiträumen werden nur bereits vergangene Zeiten verglichen. Ein unveränderter gültiger Sensorzustand wird bis zum nächsten Zustandswechsel verwendet. Die Aktualisierungszeit wird angezeigt.

Karteneinstellungen sowie 15-Minuten- und Stundenarchive liegen im HA-Konfigurationsspeicher und werden mit normalen Backups gesichert. Es entstehen keine neuen Sensoren und keine Schaltaktionen.

## Berechtigungen und UI

Die WebSocket-Endpunkte prüfen das native HA-Leserecht für jeden Sensor. Nur zugängliche Sensoren werden angeboten. Karteneinstellungen dürfen HA-Administratoren speichern. Sensorauswahl, Mehrfachauswahl, Navigation, Buttons, Listen und Klappbereiche verwenden das unveränderte gemeinsame **HA UI Kit 1.12.0**. Die Datumsnavigation unterstützt ab 1.7.1 einzeln deaktivierbare Pfeile; Darstellung und bisherige Aufrufe bleiben unverändert.

Brand-Icons werden lokal in `brand/` mitgeliefert. Die Anzeige im HACS-Marktplatz hängt von der lokalen Brand-Unterstützung der installierten HACS-Version ab.

## Entwicklung

```sh
npm install
npx playwright install chromium
npm run build
npm run check
npm test
npm run test:browser
npm run package
```

Automatisierte Browserprüfungen nutzen synthetische Daten und prüfen alle drei Ansichten, unabhängige Karten, Vorauswahl und eigene Sensornamen, Vergleich zweier Sensoren aller drei Messarten, Maus-/Touchdetails und Messlücken, Kalenderpfeile, rollierende und vollständige Zeitfenster einschließlich 06:40-Beispiel, Auflösungen sowie Ziehsortierung und einklappbare Auswahl, erhaltene Klappzustände, Rechte, schmale Bildschirme und beide Themes. Der HA-Test läuft im offiziellen Container und prüft insbesondere die native Recorder-Historie vor der ersten Sensorwahl.

MIT-Lizenz. Der gemeinsame UI-Baukasten wird unverändert mit eigener Lizenz ausgeliefert.


Die Wettergrafiken und die komplette Darstellung stammen unverändert aus **HA UI Kit 1.12.0**. Keine Grafik wird zur Laufzeit nachgeladen. Messungen erhalten ein Thermometer-Symbol; Bewölkung/Regen werden ausschließlich aus der Vorhersage übernommen. Temperatur und Detailwerte beschreiben den Beginn eines Vorhersagezeitraums; Min/Max beziehen sich auf den ganzen Abschnitt. Wind zeigt die höchste stündliche Geschwindigkeit, Böen das Maximum der überlappenden Stunden. Luftdruck ist auf Meereshöhe bezogen. Fehlende Werte bleiben als „—“ sichtbar.


Jeden 3-Stunden-Zeitraum in Wetter am Faltpfeil in seine **Stundenwerte** aufklappen. Die Daten stammen aus den nativen gemessenen Stundenwerten beziehungsweise aus den stündlichen Open-Meteo-Daten. Der laufende Abschnitt ist bis zum gemeinsamen Abfragezeitpunkt auf Ist und Forecast aufgeteilt. Stundenwerte bleiben zunächst eingeklappt und merken sich ihren Zustand bei Reiterwechsel und Aktualisierung. Fehlende Stunden werden nicht aus einem 3-Stunden-Mittel erfunden; Sommer-/Winterzeit folgt den tatsächlichen Stunden.
