# Changelog

## 1.1.0

- Neuer Anzeigename: Temperaturanalyse. Bestehender Kartentyp und YAML bleiben gültig.
- Eine Integration für alle Sensoren; Auswahl ausschließlich in den Karteneinstellungen. Mehrere Thermometer pro Karte.
- Eigene Windansicht mit separatem Windsensor und einheitlicher Anzeige in km/h.
- Nur Temperatur, Wind und Helligkeit in der Navigation; weitere Kennzahlen, Vergleiche, Rekorde sowie Tages- und Monatswerte sind aufklappbar.
- Initiale Auswertung aus vorhandener Recorder-Detailhistorie und Langzeitstatistik. Vorhandene Live-Archive bleiben erhalten; keine doppelte Zählung.
- Separate Helligkeitsansicht mit eigenem Lux-Sensor.
- Tagesansicht heißt Tag und erhält Links-/Rechtspfeile; Gestern entfällt.
- Historie übernehmen für erneuten Import in den Einstellungen.
- Heizgradtage, Raumtemperatur und Heizgrenze entfernt.
- Lokales Thermometer-Icon für HA/HACS und Kartenauswahl.
- Gemeinsames HA UI Kit 1.7.1 mit einzeln deaktivierbaren Datumspfeilen eingebunden.

# Änderungen

## 1.0.0 · 2026-11-17

Erste Veröffentlichung: Thermometerwahl, Temperaturverlauf, gewichtete Kennzahlen, Zeiträume und Vergleiche, langfristige Stundenaufzeichnung für Grenzwertdauern und Extrem-Uhrzeiten, Heizgradtage, native HA-Leserechte und gemeinsame Oberfläche mit HA UI Kit 1.7.0.
