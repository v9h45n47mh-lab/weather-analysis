# Temperaturanalyse

Home-Assistant-Integration mit Dashboard-Karte für vorhandene **Thermometer, einen separaten Windsensor und einen Helligkeitssensor**. Version **1.1.0**, HA UI Kit **1.7.1** lokal eingebunden.

## Funktionen

- Oben nur **Temperatur**, **Wind** und **Helligkeit**, mit jeweils eigenem Sensor aus den Karteneinstellungen.
- Mehrere Thermometer in derselben Karte; Wechsel zwischen ausgewählten Sensoren im Dropdown.
- Eine Integration für alle Sensoren. Auswahl ausschließlich in den Einstellungen der Karte, keine einzelne Integration je Thermometer.
- Aktueller Messwert, zeitlich gewichteter Durchschnitt, Minimum, Maximum und Spanne.
- Verlauf mit Durchschnittslinie und Min-/Max-Band, Trends und Vortagesvergleich.
- Weitere Kennzahlen, Vergleiche, Rekorde, Monatsübersicht und Tageswerte sind aufklappbar.
- Temperatur: Froststunden, Stunden ab 25/30 °C sowie nachgewiesene Frost-/Warm-/Heißtage.
- Wind: aktueller Wert und Kennzahlen in km/h. Sensoren in m/s, km/h, mph, Knoten und ft/s werden umgerechnet. Ein Sensor-Höchstwert ist keine separat gemessene Böe.
- **Tag** mit Links-/Rechtspfeilen, Kalenderwoche, Monat, Jahr und freier Zeitraum bis 366 Kalendertage. Kein eigener Gestern-Button. Der nächste Tag ist am heutigen Datum gesperrt.
- **Helligkeit:** separater Lux-Sensor, aktueller Wert, Verlauf, Mittelwert, Extremwerte und Vergleiche.
- **Historie übernehmen** in den Einstellungen zum erneuten Import; bereits archivierte Detailwerte bleiben erhalten.
- Vorhandene Detailhistorie wird bei der ersten Sensorwahl importiert und sofort ausgewertet; ältere HA-Langzeitstatistik ergänzt verfügbare Zeiträume.
- Ausgewählte Sensoren werden auch bei geschlossener Karte weiter aufgezeichnet.
- Keine Heizgradtage, Raumtemperatur oder Heizgrenze.
- Mehrere unabhängige Karten, helle/dunkle Themes, Mobilansicht und lokale Brand-Icons.

## Installation und Update

1. HACS → Benutzerdefinierte Repositories → `https://github.com/v9h45n47mh-lab/weather-analysis`, Typ **Integration**.
2. **Temperaturanalyse** installieren/aktualisieren, Home Assistant neu starten und Browser/App vollständig neu laden.
3. Nur bei Erstinstallation: Einstellungen → Geräte & Dienste → Integration hinzufügen → **Temperaturanalyse**. Es wird noch kein Sensor ausgewählt.
4. Dashboard bearbeiten → Karte hinzufügen → **Temperaturanalyse**.
5. Über das Zahnrad mehrere Thermometer sowie je einen Wind- und Helligkeitssensor wählen und speichern. In der Temperaturansicht wechselst du nur zwischen den dort ausgewählten Thermometern.

Bestehende Integrationen und ihre Archive funktionieren nach dem Update weiter. Alte Einzeleinträge müssen nicht gelöscht werden; zusätzliche Einträge je Sensor entfallen. Der Repositoryname, die Integrationsdomain und der technische Kartentyp bleiben zur Kompatibilität erhalten.

```yaml
type: custom:weather-analysis-card
card_id: temperatur-garten
title: Temperaturanalyse
period: day
grid_options:
  columns: 12
  rows: auto
```

Die Kartenressource wird automatisch eingebunden. Bei kopierten Karten eine andere `card_id` verwenden, wenn die Einstellungen unabhängig sein sollen. Gleiche IDs teilen sich Einstellungen. Gespeicherte Einstellungen haben Vorrang vor YAML-Startwerten. Gespeicherte Sensoren werden serverseitig aufgezeichnet. Der Wechsel zwischen konfigurierten Thermometern verändert nur die aktuell betrachtete Karte.

Manuell: `weather-analysis-1.1.0-manual.zip` herunterladen, den enthaltenen Ordner `custom_components/weather_analysis` nach `/config/custom_components/weather_analysis` kopieren und HA neu starten. `weather-analysis.zip` enthält den Integrationsinhalt für HACS.

## Historie und Genauigkeit

Die erste Auswertung verwendet die vorhandenen Daten des gewählten Sensors:

1. **Detailhistorie:** Zeitlich gewichtete Werte, Grenzwertdauern und Extremzeiten werden aus aufgezeichneten Zustandswechseln berechnet und als Stundenwerte gesichert. Einheiten werden je historischem Zustand umgerechnet. Bekannte Recorder-Ausfallzeiten sowie `unknown`/`unavailable` bleiben Lücken.
2. **Langzeitstatistik:** Für ältere Zeiträume werden verfügbare stündliche Durchschnitts-, Minimal- und Maximalwerte genutzt. Ohne `state_class: measurement` kann die Detailhistorie trotzdem ausgewertet werden; ältere Langzeitwerte sind dann gegebenenfalls nicht vorhanden.
3. **Fortlaufende Aufzeichnung:** Ab Auswahl ergänzen wir die Historie dauerhaft. Vorhandene Archive werden erhalten und nicht doppelt gezählt.

Die rückwirkende Genauigkeit hängt von den noch gespeicherten HA-Daten ab. Gelöschte Detailhistorie lässt sich nicht rekonstruieren. Aus verdichteten Stundenwerten werden keine exakten Grenzwertdauern oder Extrem-Uhrzeiten erfunden. **≈** markiert Mittelwerte mit HA-Statistikanteil; die Karte zeigt Datenintervalle und Detailabdeckung.

Die Rekorde beziehen sich auf verfügbare Historie, eigene Archive und vorhandene Jahresstatistiken. Letztere enthalten keinen genauen Zeitpunkt. Windwerte verwenden die Messauflösung und Bedeutung des gewählten Sensors; die Karte erzeugt keine eigenständige Böenmessung.

Kalendergrenzen und Anzeige folgen der HA-Zeitzone einschließlich Sommer-/Winterzeit. Bei laufenden Zeiträumen werden nur bereits vergangene Zeiten verglichen. Ein unveränderter gültiger Sensorzustand wird bis zum nächsten Zustandswechsel verwendet. Die Aktualisierungszeit wird angezeigt.

Karteneinstellungen und Stundenarchive liegen im HA-Konfigurationsspeicher und werden mit normalen Backups gesichert. Es entstehen keine neuen Sensoren und keine Schaltaktionen.

## Berechtigungen und UI

Die WebSocket-Endpunkte prüfen das native HA-Leserecht für jeden Sensor. Nur zugängliche Sensoren werden angeboten. Karteneinstellungen dürfen HA-Administratoren speichern. Sensorauswahl, Mehrfachauswahl, Navigation, Buttons, Listen und Klappbereiche verwenden das unveränderte gemeinsame **HA UI Kit 1.7.1**. Die Datumsnavigation unterstützt ab 1.7.1 einzeln deaktivierbare Pfeile; Darstellung und bisherige Aufrufe bleiben unverändert.

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

Automatisierte Browserprüfungen nutzen synthetische Daten und prüfen alle drei Ansichten, unabhängige Karten, Auswahl mehrerer Sensoren, Rechte, schmale Bildschirme und beide Themes. Der HA-Test läuft im offiziellen Container und prüft insbesondere die native Recorder-Historie vor der ersten Sensorwahl.

MIT-Lizenz. Der gemeinsame UI-Baukasten wird unverändert mit eigener Lizenz ausgeliefert.
