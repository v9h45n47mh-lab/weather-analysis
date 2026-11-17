# Changelog

## 1.4.0

- Jahr aus der Zeitraumwahl entfernt; alte Jahres-Startansichten wechseln auf Monat.
- Sensorauswahl links ausgerichtet.
- Mehrere Wind- und Helligkeitssensoren mit derselben Vorauswahl, eigenen Kartennamen, Dropdowns und Zwei-Sensoren-Vergleich wie Temperatur. Vergleichsauswahl bleibt je Messansicht erhalten.
- Bestehende einzelne Wind- und Helligkeitssensoren werden automatisch übernommen. Alle ausgewählten Sensoren werden auch ohne offene Karte aufgezeichnet und beim Historienimport berücksichtigt.
- Doppelte Monatsübersicht und Tageswerttabelle unterhalb der Auswertung entfernt.
- Maus- und Touchcursor im Verlauf zeigt Zeit sowie Mittel-, Minimal- und Maximalwerte beider Sensoren; Messlücken werden nicht überbrückt. Tastaturbedienung bleibt erhalten.
- Tagesintervalle berücksichtigen die Sommer-/Winterzeit für korrekte Chartdetails. HA UI Kit 1.8.0 bleibt unverändert eingebunden.

## 1.3.0

- Helligkeitswerte überall ohne Nachkommastellen, einschließlich Trends, Rekorden, Tabellen und Chartdetails. Berechnungen bleiben ungerundet.
- Aktualisieren als gemeinsames Symbol in der Kopfleiste aller Reiter; schmalere Temperatur-Dropdowns.
- Kartentitel und Feld Anzeigename entfernt. Eigene Sensornamen bleiben in den Dropdowns erhalten.
- Zwei kombinierte Kacheln oberhalb des Charts: Aktuell mit Änderung in 1 Std. sowie Minimum/Maximum.
- Durchschnitt als beschriftete horizontale Linie im Verlauf; eigene Durchschnitts- und Spannenkacheln entfallen.
- HA UI Kit 1.8.0 mit optionalen Kopfaktionen und kombinierten Messkacheln eingebunden.

## 1.2.0

- Anzeigename wieder Weather Analysis. Bestehende YAMLs, Karteneinstellungen und Archive bleiben kompatibel; eigene Kartentitel bleiben erhalten.
- Relevante Thermometer in den Einstellungen vorauswählen und pro Karte umbenennen.
- Sensordropdown oben rechts anstelle von Aktualisieren, auch bei nur einem vorausgewählten Thermometer.
- Pluszeichen zum Vergleich mit einem zweiten vorausgewählten Sensor: zwei Farben, zusätzliche Strichelung, gemeinsame Temperaturskala, beschriftete Legende und Kennzahlenvergleich. Vergleich über × entfernen.
- Auf-/Zuklappzustände aller Bereiche bleiben beim Wechsel des Zeitraums und beim Nachladen erhalten, unabhängig je Karte und Ansicht.
- Sensoraliase werden mit den Karteneinstellungen gespeichert und nach nativen HA-Leserechten gefiltert.
- Gemeinsames HA UI Kit 1.7.1 bleibt unverändert eingebunden.

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
