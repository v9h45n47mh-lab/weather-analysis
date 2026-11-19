## 1.11.0

- Jeder 3-Stunden-Zeitraum in Wetter lässt sich in seine Stundenwerte aufklappen, sowohl Ist als auch Vorhersage.
- Stundenwerte verwenden echte stündliche Sensorintegrale beziehungsweise stündliche Vorhersagedaten mit eigenen Temperaturen, Wind- und Wetterwerten.
- Angebrochene Stunden, Messlücken und Zeitumstellung werden berücksichtigt. Niederschlag wird für jeden Abschnitt getrennt berechnet.
- Stundenwerte sind initial zugeklappt und behalten ihren Faltzustand beim Aktualisieren und Reiterwechsel. Forecast-IDs bleiben auch beim laufenden ersten Abschnitt stabil.
- Gemeinsame aufklappbare Wetterzeilen aus HA UI Kit 1.12.0 lokal eingebunden; die Messspalten bleiben ausgerichtet.

## 1.10.1

- Heute zeigt die Reihenfolge Ist → Aktuell → Vorhersage; aktuelle Messwerte stehen zwischen den gemessenen Zeiträumen und der Vorhersage.
- Ist ist anfangs zugeklappt und Aktuell geöffnet. Beide Bereiche behalten ihre gewählten Faltzustände beim Aktualisieren und Reiterwechsel.
- Helligkeit/lx entfällt in der Wetterübersicht und wird dort nicht mehr abgefragt.
- Windwerte stehen bei Ist, Aktuell und Vorhersage in derselben Spalte, auch auf Mobilgeräten.
- Zusätzliche Tages- und Ortsüberschriften entfernt; Messpunkte sowie Heute und Morgen bleiben sichtbar.
- Gemeinsame Wetterliste aus HA UI Kit 1.11.0 verwendet.

## 1.10.0

- Wetter ist der Startreiter der Karte.
- Die Wetterzeiträume stehen als kompakte, anschauliche Zeilen untereinander; keine horizontale Wetterliste mehr.
- Aktuelle Temperatur, Wind, Helligkeit und Temperatur-Min/Max heute stehen direkt als erste Ist-Zeile in der Übersicht.
- Ist lässt sich zuklappen. Der Zustand bleibt beim Aktualisieren und beim Wechsel der Reiter erhalten; die Vorhersage bleibt sichtbar.
- Gemeinsame responsive Wetterliste aus HA UI Kit 1.11.0 lokal eingebunden.

## 1.9.0

- Wetter zeigt anschauliche 3-Stunden-Spalten mit großen Wettersymbolen, Temperaturen, Min/Max und verständlichen Symbolzeilen statt technischer Datenlisten.
- Regenrisiko/-menge, Windrichtung und Böen, gefühlte Temperatur, Luftfeuchtigkeit und Luftdruck ergänzen die Vorhersage für 67459 Böhl-Iggelheim.
- Messwerte bleiben blau, Vorhersagen schwarz. Vergangene Zeiträume verwenden ausschließlich Sensordaten; keine erfundenen Wetterlagen.
- Wetterspalten per Maus, Tastatur und Touch durchblättern. Scrollpositionen und geöffnete Bereiche bleiben beim Wechseln und Nachladen erhalten.
- Neue originale SVG-Wettergrafiken und gemeinsame Wetterbausteine aus HA UI Kit 1.10.0 lokal eingebunden, einschließlich Prüfsummen und Lizenz.

# Changelog

## 1.8.0

- Reiter Dashboard heißt jetzt Wetter. Die vier Messkacheln entfallen in dieser Übersicht.
- Gemeinsame 3-Stunden-Zeitliste für heute: tatsächliche Sensordaten in Blau, anschließender Forecast in Schwarz; morgen ausschließlich Forecast.
- Ist-Werte stammen aus der HA-Historie: zeitgewichtete Temperatur-, Wind- und Helligkeitsmittel sowie Temperatur-Minimum/-Maximum je Abschnitt. Fehlende Ist-Daten werden nicht aus dem Wettermodell aufgefüllt.
- Der laufende 3-Stunden-Abschnitt wird an einem gemeinsamen Abfragezeitpunkt geteilt. Messwerte enden dort, Vorhersage beginnt dort.
- Kompakte blaue Jetzt-Zeile mit aktuellen Werten und Temperatur-Minimum/-Maximum heute.
- Helle Zeitzeilen für gute Lesbarkeit der ausdrücklich schwarzen Prognose auch im dunklen Theme. Gemeinsame Zeilen und Klappbereiche des HA UI Kits bleiben erhalten.

## 1.7.0

- Aktuell bedeutet bei Tag wieder heute. Die Zeitachse zeigt immer 00:00–23:59 Uhr; Messwerte reichen bis jetzt. Pfeile wechseln volle Kalendertage, Aktuell kehrt zu heute zurück.
- Neuer Reiter Dashboard: aktuelle Temperatur, Temperatur-Minimum/-Maximum von heute, Wind und Helligkeit. Die jeweils aktiven Sensoren der Messreiter und ihre Kartennamen werden verwendet.
- Wettervorhersage für 67459 Böhl-Iggelheim: heute Resttag und morgen in örtlichen 3-Stunden-Abschnitten mit Wetterzustand, Temperatur, Regenrisiko/-menge und Wind.
- Open-Meteo serverseitig ohne API-Schlüssel, gemeinsamer 30-Minuten-Cache, Quellenangabe und Abrufzeit. Letzter verfügbarer Stand bei Störungen klar gekennzeichnet; lokale Messwerte und Vorhersage laden unabhängig voneinander.
- Fehlende Wetterwerte bleiben fehlend. Vorhersagefenster berücksichtigen Sommer-/Winterzeit und werden auf den verbleibenden Resttag zugeschnitten.
- HA UI Kit 1.8.0 mit gemeinsamen Messkacheln, Navigation, Zeilen und Klappbereichen unverändert verwendet.

## 1.6.0

- Durchgezogene Verlaufslinien für beide Sensoren, ohne dauerhaft sichtbare Messpunktkreise. Zwei Farben bleiben erhalten; bekannte Messlücken werden weiterhin erkennbar dargestellt.
- Tag startet mit der rollierenden 24-Stunden-Sicht. Um 06:40: gestern 06:41 bis heute 06:40.
- Zurück zeigt den vollständigen Vortag. Vorwärts zurück auf heute zeigt 00:00–23:59; Aktuell kehrt ausdrücklich zur rollierenden Sicht zurück.
- Woche startet mit heute plus den letzten sieben Tagen. Pfeile navigieren vollständige Kalenderwochen Montag–Sonntag; Aktuell stellt die rollierende Sicht wieder her.
- Monat bleibt der vollständige Kalendermonat. Vollständige Kalenderachsen werden bis zum Periodenende gezeigt, Messwerte ausschließlich bis jetzt.
- Zeitgewichtete Kennzahlen und 15-Minuten-Werte werden an rollierenden Fenstergrenzen aus tatsächlichen Zustandswechseln zugeschnitten. Alte Stundenmittel werden nicht künstlich auf Teilintervalle verteilt.
- Beide Vergleichssensoren erhalten denselben Zeitpunkt für die rollierende Abfrage. UI Kit 1.8.0 bleibt unverändert eingebunden.

## 1.5.0

- Chartauflösung für alle Messarten und beide Vergleichssensoren: Tag 15 Minuten, Woche 1 Stunde und Monat 6 Stunden. Mittelwerte bleiben zeitlich gewichtet.
- Viertelstunden werden aus vorhandener Detailhistorie importiert und fortlaufend gespeichert. Bestehende Archive bleiben erhalten; alte Stundenwerte ohne feinere Historie werden als solche gekennzeichnet.
- Links-/Rechtspfeile auch für Kalenderwochen und Monate, einschließlich Rückkehr zum aktuellen Zeitraum. Vergangene Zeiträume werden vollständig gezeigt, zukünftige gesperrt. Tastaturpfeile werden außerhalb von Eingabefeldern unterstützt.
- Eigenen Navigationsstand je Zeitraum merken; Klappzustände bleiben erhalten. Kalendergrenzen und 6-Stunden-Intervalle berücksichtigen Sommer-/Winterzeit.
- Ausgewählte Sensoren in den Einstellungen per gemeinsamem Ziehgriff sortieren, mit Maus, Touch oder Tastatur. Reihenfolge und Namen werden je Karte gespeichert und in den Dropdowns verwendet.
- Sensorauswahl für Temperatur, Wind und Helligkeit jeweils separat einklappbar und zunächst geschlossen.
- HA UI Kit 1.8.0 mit vorhandenen Navigations-, Klapp- und Sortierkomponenten unverändert verwendet.

## 1.4.1

- Maus-/Touchwerte erhalten einen festen Bereich oberhalb des Charts; die Kurven werden nicht verdeckt und verschieben sich beim Ablesen nicht. Farbige Messpunktmarkierungen und Detailwerte bleiben erhalten.
- Sensornamen in den Einstellungen stehen unter Temperatur, Wind beziehungsweise Helligkeit.
- Sensorsuche berücksichtigt die Messart zusätzlich zu Name und Entitäts-ID; auch englisch benannte Sensoren werden mit Wind oder Helligkeit gefunden.
- Alternative Lux- und Geschwindigkeitseinheiten sowie leere beziehungsweise ältere Geräteklassen werden bei Auswahl und Detailhistorie erkannt.
- HA UI Kit 1.8.0 bleibt unverändert eingebunden.

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
