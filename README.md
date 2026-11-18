# Weather Analysis

Home-Assistant-Integration mit Dashboard-Karte für vorhandene **mehrere Temperatur-, Wind- und Helligkeitssensoren**. Version **1.6.0**, HA UI Kit **1.8.0** lokal eingebunden.

## Funktionen

- Oben nur **Temperatur**, **Wind** und **Helligkeit**, mit jeweils eigener Sensorauswahl aus den Karteneinstellungen.
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
- **Tag:** Aktuell zeigt die letzten 24 Stunden minutengenau. Um 06:40 reicht die Sicht von gestern 06:41 bis heute 06:40. Zurück zeigt den vollständigen Vortag; vorwärts zurück auf heute den vollständigen Tag 00:00–23:59. Erst **Aktuell** kehrt zur rollierenden Sicht zurück.
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

Manuell: `weather-analysis-1.6.0-manual.zip` herunterladen, den enthaltenen Ordner `custom_components/weather_analysis` nach `/config/custom_components/weather_analysis` kopieren und HA neu starten. `weather-analysis.zip` enthält den Integrationsinhalt für HACS.

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

Die WebSocket-Endpunkte prüfen das native HA-Leserecht für jeden Sensor. Nur zugängliche Sensoren werden angeboten. Karteneinstellungen dürfen HA-Administratoren speichern. Sensorauswahl, Mehrfachauswahl, Navigation, Buttons, Listen und Klappbereiche verwenden das unveränderte gemeinsame **HA UI Kit 1.8.0**. Die Datumsnavigation unterstützt ab 1.7.1 einzeln deaktivierbare Pfeile; Darstellung und bisherige Aufrufe bleiben unverändert.

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
