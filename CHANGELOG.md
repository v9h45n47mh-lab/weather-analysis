## 1.17.1

- Durchgehende Radarzeitleiste ohne Auswahlbuttons für 1 oder 12 Stunden. Erste Stunde in 5-Minuten-Schritten; danach automatisch 30-Minuten-Schritte bis zwölf Stunden.
- Der Übergang erfolgt lückenlos am Ende der ersten Stunde. Quellenkennzeichnung, mittiger Standort und Zwei-Finger-Zoom bleiben erhalten.
- HA UI Kit 1.16.1 mit passender Zeitachsenbeschriftung und Vorschauhinweis.

## 1.17.0

- Radarvorschau umschaltbar: eine Stunde in 5-Minuten-Schritten oder zwölf Stunden in 30-Minuten-Schritten. Zwei Stunden Messhistorie bleiben erhalten.
- Erste Stunde aus dem DWD-Radar-Nowcast, längere Vorschau aus DWD ICON-D2-RUC. Modellvorhersagen werden ausdrücklich gekennzeichnet und auf dem nativen Modellgitter geografisch zugeordnet.
- Standort bei allen Zoomstufen in der Kartenmitte. Zwei-Finger-Geste zum Zoomen; Ein-Finger-Scrollen und Zoom-Buttons bleiben verfügbar.
- HA UI Kit 1.16.0 mit gemeinsamer Vorschauauswahl, korrekter Zeitachse und Zwei-Finger-Zoom. Weißer Kartenhintergrund und blaue Niederschlagsskala bleiben erhalten.
- Neue Decoder-Abhängigkeiten: SciPy 1.16.3 und der vorhandene HDF5-CCSDS-Decoder.

## 1.16.1

- Regenradar startet eine Zoomstufe weiter heraus und bleibt auf den aktuellen Standort zentriert. Weiteres Vergrößern und Verkleinern ist möglich.
- Weiße Karte, auch im dunklen Theme. Regen ausschließlich in Blautönen: je stärker der Niederschlag, desto dunkler das Blau.
- HA UI Kit 1.15.0 mit identischer Niederschlagsskala für Legende und lokal erzeugte Radar-Bilder.

## 1.16.0

- Radar startet maximal auf den aktuellen Standort gezoomt. Im Heim-WLAN wird ein plausibler konfigurierter HA-Heimstandort zur Markierung verwendet.
- Sehr reduzierte, lokal gezeichnete Karte: nur Flüsse, Ländergrenzen und höchstens vier Städtenamen. Keine Straßen, Gebäude, Geländedarstellung und keine externen Hintergrundkartenabrufe.
- DWD-RV-Rohdaten werden direkt geladen und lokal georeferenziert. Ein gemeinsamer Vorhersagelauf liefert alle Zukunftsbilder; die langsame WMS-Kartenerzeugung pro Bild entfällt.
- Karte und Standortmarker erscheinen während des Datenladens. Der Ortsname wird unabhängig nachgeladen; HA-Standort- und Heim-WLAN-Regeln benötigen weiterhin keine zusätzliche Browserfreigabe.
- Öffentliche Radardaten werden beim HA-Start vorbereitet und begrenzt im Speicher sowie auf Festplatte zwischengespeichert. Nutzerstandorte werden dabei nicht gespeichert. Historie wird im Hintergrund vorbereitet.
- Unverändert zwei Stunden Messhistorie und eine Stunde DWD-Vorhersage, getrennte Kennzeichnung und exakte Bildzeiten. Fehlende Daten bleiben erkennbar; Schraffur zeigt fehlende Abdeckung. Die Auflösung der DWD-Rohdaten beträgt 1 km.
- Abspielen beginnt am ausgewählten Zeitpunkt. Neues HA UI Kit 1.14.0 mit lokalen Radar-Vektorgrafiken und gemeinsamer Niederschlagsskala.
- Neue Decoder-Bibliotheken werden über die Home-Assistant-Integration installiert: h5py 3.15.1 und pyproj 3.7.2.

## 1.15.1

- Im Heim-WLAN lösen GPS-Schwankungen kein erneutes Laden des festen Heimstandorts mehr aus.

- Ruhige, deutlich reduzierte Radar-Hintergrundkarte in hellen Grautönen. Standortmarker, Niederschlag, Zeitregler und Zoom bleiben erhalten.
- DWD-Metadaten nur für die benötigte Radarebene statt für den gesamten Dienst abrufen. Die vereinfachte BKG-Karte wird als kompaktes PNG geladen.
- Bereits geladene Messbilder, Hintergrund und Legende bleiben bei Aktualisierungen und Reiterwechseln im Speicher. Neue Vorhersageläufe werden weiterhin neu geladen.
- Aktuelle beziehungsweise ausgewählte Bilder erhalten reservierte Abrufkapazität. Nachbarbilder werden zuerst im Hintergrund geladen.
- Automatische Radaraktualisierung passend zum Fünf-Minuten-Raster; laufende Animationen werden dabei nicht unterbrochen. Zwei Stunden Rückblick und eine Stunde Vorhersage bleiben erhalten.

## 1.15.0

- Durchschnittliche Ist-Werte in der Wetterübersicht ohne ≈-Zeichen.

- Neues standortabhängiges Regenradar als eigener Reiter und separate Lovelace-Karte `custom:weather-radar-card`.
- DWD RV: letzte zwei Stunden Messhistorie und nächste Stunde Vorhersage in Fünf-Minuten-Schritten. Abspielen/Pause, Einzelbildnavigation, Zeitregler, Zoom und Standortmarker auf BKG-Karte.
- Messung und Vorhersage bleiben ausdrücklich getrennt; exakte lokale Bildzeit, letzter Messstand, Original-DWD-Farbskala und Quellenangaben. Fehlende oder veraltete Bilder werden nicht als trockene Wetterlage dargestellt.
- Standort folgt derselben HA-Person-/Heim-WLAN-Logik wie Wetter; keine zusätzliche automatische Standortfreigabe.
- Alle Hauptreiter verwenden passende gemeinsame Symbole mit Tooltips und zugänglichen Beschriftungen. Wetter bleibt Startreiter.
- HA UI Kit auf die neue veröffentlichte Version 1.13.0 mit gemeinsamem Radarbaustein und Wetter-, Warnungs-, Radar- und Windsymbolen aktualisiert.

## 1.14.0

- Neuer Reiter Warnungen: amtliche DWD-Wetterwarnungen anhand des ermittelten Standorts mit Warnstufe, Gültigkeit, Warngebiet und Hinweisen. Räumliche Filterung über den offiziellen DWD-Gemeindewarnungsdienst, Quelle und Abrufstand in der Karte.
- Aktuelle, angekündigte und vorläufige Warnungen werden unterschieden. Für Standorte außerhalb Deutschlands erscheint ein Hinweis. Abruffehler werden ausdrücklich angezeigt und nicht als Entwarnung behandelt.
- Aufklappen der Zeitabschnitte hält den gewählten Faltpfeil, Scrollposition und Fokus stabil. Auch automatische und teilweise Datenaktualisierungen erhalten diese Position; HA-Scrollcontainer und Shadow DOM werden berücksichtigt.
- Ein vorhandener HA-Personenstandort verhindert automatische Browser-GPS-Abfragen, auch bei einer alten gespeicherten Gerätewahl. HA-Person verwenden beendet Geräte-GPS in allen geöffneten Wetterkarten desselben Benutzers auf diesem Gerät und verhindert weitere automatische Starts. Andere Benutzer bleiben unabhängig.
- Bestehende lokale Komponenten aus HA UI Kit 1.12.0 für Navigation, Warnhinweise, Statuskennzeichen und aufklappbare Warnmeldungen verwendet.

## 1.13.1

- Heim-WLAN wird vor der Browser-Standortfreigabe geprüft, auch beim Neustart, Wiederöffnen und bei einer gespeicherten Geräte-Standortwahl.
- Im erkannten Heim-WLAN wird weder die Browser-Berechtigung abgefragt noch ein GPS-Watcher gestartet. Böhl-Iggelheim inklusive Ist bleibt ohne Geräte-Standortfreigabe verfügbar.
- Beim Verbinden mit dem Heim-WLAN wird eine laufende Geräte-Standortabfrage beendet. Verspätete Netzwerk-, Berechtigungs- und GPS-Antworten können sie nicht wieder starten.
- Der Geräte-Standortbutton ist zuhause deaktiviert; Freigabehinweise entfallen dort. Nach Verlassen gilt wieder die gespeicherte Standortwahl mit Prüfung einer bereits gültigen Freigabe.
- Die WLAN-Prüfung ist unabhängig von GPS und Ortsauflösung und verwendet die zentrale Konfiguration für alle Anwender und Karten.
- HA UI Kit 1.12.0 unverändert lokal eingebunden.

## 1.13.0

- Heim-WLAN hat Vorrang vor GPS: Ein lesbarer Router-Tracker der eigenen HA-Person mit Zustand zuhause aktiviert Böhl-Iggelheim inklusive Ist und Aktuell, auch ohne GPS.
- Heim-WLAN unter Einstellungen → Standort → Heim-WLAN einmal zentral für alle Anwender und Karten hinterlegen. HA-Administratoren können eine gemeldete SSID auswählen oder den WLAN-Namen eintragen und mit Heim-WLAN speichern übernehmen. Erkannt werden die eigenen verknüpften Mobilgeräte; fremde WLANs gelten nicht als zuhause. Reguläres Speichern einer Karte verändert die zentrale WLAN-Einstellung nicht.
- Die Auswahl „Standort dieses Geräts verwenden“ wird je HA-Benutzer und Karte auf dem verwendeten Gerät gespeichert. GPS-Koordinaten werden dabei nicht dauerhaft gespeichert.
- Beim erneuten Öffnen wird eine bereits gültige Standortfreigabe wiederverwendet. Bei abgelaufener, fehlender oder abgelehnter Freigabe nutzt die Karte den HA-Standort und öffnet keinen automatischen Freigabedialog. Neue Freigaben werden nur auf Knopfdruck angefordert.
- „HA-Person verwenden“ entfernt die gespeicherte Geräteauswahl. Watcher und verspätete Standortantworten werden beim Verlassen und Benutzerwechsel sauber beendet.
- Unveränderte Auswahl-, Hinweis- und Einstellungsbausteine aus HA UI Kit 1.12.0 lokal eingebunden.

## 1.12.0

- Wetter folgt automatisch dem GPS-Standort der mit dem angemeldeten HA-Benutzer verknüpften Person. Alternativ lässt sich der Standort des angezeigten Geräts freigeben.
- Im deutschen Postleitzahlgebiet 67459 stehen Ist, Aktuell und Vorhersage bereit. An anderen Orten wird ausschließlich die örtliche Vorhersage angezeigt; heimische Sensorwerte werden dort nicht abgefragt.
- Der Ortsname steht im Kopfbereich. Heute, Morgen und die aufklappbaren Stundenwerte folgen der Zeitzone am Aufenthaltsort.
- Ohne GPS erscheint ein Hinweis mit optionaler Gerätefreigabe und zunächst nur die Vorhersage für Böhl-Iggelheim. Eine fehlgeschlagene Ortsauflösung schaltet keine heimischen Messwerte frei.
- Getrennte, begrenzte Standort- und Vorhersage-Caches; nur eigene, lesbare Person-/GPS-Entitäten werden für die automatische Position verwendet. Verspätete Antworten nach Ortswechsel werden verworfen.
- Bestehende Kopfbereich-, Hinweis-, Button- und Wetterkomponenten aus HA UI Kit 1.12.0 wiederverwendet.

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
