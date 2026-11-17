# Weather Analysis · Wetteranalyse

Home-Assistant-Integration mit eigener Dashboard-Karte für die Analyse eines **vorhandenen Temperatursensors**. Version **1.0.0**, deutsche Kartenoberfläche, HA UI Kit **1.7.0** lokal eingebunden.

## Funktionen

- Aktuelle Temperatur und Messzeit, Verlauf mit Durchschnittslinie und Min-/Max-Band.
- Minimum, Maximum, zeitlich gewichteter Durchschnitt und Temperaturspanne.
- Trends über eine und drei Stunden sowie Vergleich mit gestern zur gleichen Ortszeit, sobald die ergänzende Aufzeichnung diese Zeit abdeckt.
- Heute, gestern, laufende Kalenderwoche, laufender Monat, laufendes Jahr und freier Zeitraum bis 366 Kalendertage.
- Froststunden unter 0 °C, warme Stunden ab 25 °C, heiße Stunden ab 30 °C und entsprechende nachgewiesene Tage.
- Heizgradtage für vollständige Tage; Raumtemperatur und Heizgrenze einstellbar, Standard 20/15 °C.
- Vergleich der Mittelwerte mit dem vorherigen gleich langen Zeitraum und dem Vorjahreszeitraum.
- Temperaturrekorde, Tageswerttabelle und Monatsübersicht im ausgewählten Zeitraum.
- Mehrere Thermometer und mehrere Karten mit eigenen Einstellungen; helles/dunkles HA-Theme und Mobilansicht.
- Keine Wetter-Cloud, kein API-Schlüssel und keine externe Bibliothek zur Laufzeit.

## Installation über HACS

Dieses Repository ist als **benutzerdefiniertes Repository** verfügbar, nicht Bestandteil des HACS-Standardkatalogs.

1. In HACS → Menü → Benutzerdefinierte Repositories die URL `https://github.com/v9h45n47mh-lab/weather-analysis` mit Typ **Integration** hinzufügen.
2. **Weather Analysis** herunterladen und Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → Integration hinzufügen → **Weather Analysis**. Dein vorhandenes Thermometer auswählen.
4. Dashboard bearbeiten → Karte hinzufügen → **Wetteranalyse**. Falls die Auswahl noch fehlt, Browser/App vollständig neu laden.
5. In der Karte über das Zahnrad Thermometer und Anzeigename wählen und speichern.

Die Kartenressource wird durch die Integration automatisch eingebunden. Es ist normalerweise kein manueller Ressourceneintrag nötig.

```yaml
type: custom:weather-analysis-card
card_id: wetter-garten
title: Wetteranalyse
period: today
grid_options:
  columns: 12
  rows: auto
```

Neue Karten aus der Kartenauswahl erhalten eine eigene ID. Beim Kopieren einer Karte die `card_id` im visuellen Karteneditor ändern, wenn unabhängige Einstellungen gewünscht sind. Gleiche IDs teilen sich absichtlich die gespeicherten Einstellungen. Ohne ID gilt die YAML-Entität beziehungsweise `default`. Über das Zahnrad gespeicherte Einstellungen haben Vorrang vor den YAML-Startwerten. Kartenkonfigurationen werden auf dem HA-Server gespeichert.

Für weitere Thermometer die Integration jeweils erneut mit dem anderen Sensor hinzufügen. Bestehende Sensoren werden nicht verändert. Unterstützt sind Temperatur-Sensoren mit `device_class: temperature` und Einheit °C, °F oder K. Die Karte zeigt und berechnet alle Temperaturen in °C.

## Manuelle Installation

`weather-analysis-1.0.0-manual.zip` aus dem Release herunterladen und dessen Ordner `custom_components/weather_analysis` nach `/config/custom_components/weather_analysis` kopieren. Home Assistant neu starten und ab Schritt 3 oben fortfahren.

Das kleinere `weather-analysis.zip` ist für HACS vorgesehen: Es enthält den Inhalt des Integrationsordners, nicht dessen übergeordnete Ordner.

## Daten und Genauigkeit

Die Temperatur stammt unmittelbar vom ausgewählten HA-Sensor. Für ältere Zeiträume liest die Integration **vorhandene HA-Langzeitstatistiken**. Ohne Langzeitstatistik sind ältere Werte in dieser Version nicht rückwirkend verfügbar; normale Recorder-Rohhistorie wird nicht importiert.

Ab Einrichtung integriert die Ergänzungsaufzeichnung den zuletzt bekannten gültigen Zustand über die Zeit und archiviert stündlich gewichtete Werte, Min-/Max-Uhrzeiten sowie Grenzwertdauern. Sie läuft serverseitig auch ohne geöffnetes Dashboard. `unknown`, `unavailable` und Ausfallzeiten der Integration zählen als Messlücken. Ein Sensor, der einen alten gültigen Wert weiterhin meldet, wird als gültig behandelt; die Karte zeigt dessen letzte Aktualisierung an. Ein konstanter Wert muss nicht regelmäßig neu gemeldet werden.

Stündliche Aggregate bleiben dauerhaft im HA-Speicher erhalten; Zustandswechsel für Trendvergleiche werden drei Tage vorgehalten. Der Datenbestand wächst je Thermometer um höchstens 8.784 Stundenaggregate pro Jahr. Es entstehen keine neuen Temperatursensoren und keine Schaltaktionen. Die Daten liegen unter `.storage/weather_analysis.<entry_id>` und `.storage/weather_analysis.cards` und werden mit normalen HA-Konfigurationsbackups gesichert.

- **≈:** Ein Mittelwert verwendet ältere HA-Statistiken. Deren Stundenmittel werden nach Intervalllänge gewichtet; die tatsächliche Messabdeckung innerhalb dieser Stunden ist nicht bekannt. „Datenintervalle“ ist deshalb keine Garantie lückenloser Messungen.
- **Grenzwertdauern:** Ausschließlich aus der Ergänzungsaufzeichnung. Die Karte nennt den erfassten Anteil des Zeitraums. Alte Min-/Max-Werte erlauben keine Rekonstruktion von Froststunden.
- **Extrem-Uhrzeiten:** Bei neuen Messungen wird das erste Auftreten des Wertes innerhalb des jeweiligen aufgezeichneten Intervalls gespeichert. Die zeitliche Auflösung bleibt die des Quellsensors. Ältere HA-Statistiken enthalten keine genaue Uhrzeit; Jahresstatistiken enthalten auch kein genaues Rekorddatum. Die Karte erfindet diese Angaben nicht.
- **Heizgradtage:** Nur abgeschlossene lokale Tage mit mindestens 95 % abgedeckten Intervallen. An Tagen mit Tagesmittel unter der Heizgrenze wird `Raumtemperatur − Tagesmittel` addiert. Werte aus HA-Statistiken bleiben Näherungen. Das ist ein Temperaturindikator, keine berechnete Heizenergie.
- **Vergleiche:** Unvollständige Daten und unterschiedliche Sensorstandorte begrenzen ihre Aussagekraft. Verglichen wird bei laufenden Zeiträumen dieselbe verstrichene Zeitspanne. Der 29. Februar wird im Vorjahr dem 28. Februar zugeordnet.
- **Zeitzone:** Kalendergrenzen, Sommer-/Winterzeit und Anzeige folgen der HA-Zeitzone. Exakte archivierte Grenzwertdauern werden nur für vollständig enthaltene Stundenaggregate verwendet; angeschnittene Randstunden etwa in Zeitzonen mit halbstündigem Versatz werden ausgelassen und in der Abdeckung sichtbar.

Ein geschützter, gut belüfteter Standort im Schatten ist für Außentemperaturvergleiche wesentlich. Das System analysiert Temperatur; Regen, Luftfeuchte und Wind sind nicht Bestandteil dieser Version.

## Berechtigungen

Die WebSocket-Endpunkte prüfen das native HA-Leserecht für den gewählten Sensor. Nur zugängliche konfigurierte Sensoren werden angeboten. Karteneinstellungen dürfen echte HA-Administratoren speichern; lesende Benutzer können Zeiträume wechseln und auswerten. Die Integration gewährt keine zusätzlichen Geräteberechtigungen.

## Entwicklung und Prüfung

```sh
npm install
npx playwright install chromium
npm run build
npm run check
npm test
npm run test:browser
npm run package
```

Die automatisierten Browserprüfungen nutzen ausdrücklich synthetische Messwerte. Sie prüfen Bedienung, Fehlerfälle, unabhängige Karten, Mobil/Desktop und helle/dunkle Themes. Pythonprüfungen decken unter anderem Gewichtung, Umrechnung, Neustartlücken und 23-/25-Stunden-Tage ab. Ein Test auf einer echten HA-Installation des Anwenders steht vor der ersten Installation nicht zur Verfügung.

MIT-Lizenz. Der gemeinsam verwendete UI-Baukasten liegt unverändert und mit eigener Lizenz im Frontend-Verzeichnis.
