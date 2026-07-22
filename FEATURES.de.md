# TalkTrace AI base — Funktionen

📖 [English](FEATURES.md) · **Deutsch**

> Was die App kann, von oben bis unten.

---

## Eingaben

- **Transkript-Upload** — `.txt`, `.docx`, `.pdf`
- **Codebuch-Upload** — `.txt`, `.docx`, `.pdf`, mit Live-Vorschau
- **Integrierte T-SEDA-Codebuch-Vorlage** — ein Klick (Kachel auf der Start-Seite oder neben dem Codebuch-Upload) lädt das offizielle [T-SEDA](https://camtree.learnworlds.com/t-seda)-Schema für dialogisches Unterrichtsgespräch (T-SEDA Collective 2023, University of Cambridge, CC BY; die deutschen Pack-Abkürzungen in der DE-Oberfläche, die englischen Originale in der EN-Oberfläche; Definitionen und Schlüsselwörter folgen dem offiziellen detaillierten Kodierrahmen, bewusst knapp gehalten) und stellt die Pipeline voreingestellt bereit: LLM-Kodierung an, **Lehrer- und Schülerbeiträge** (Gesprächsqualität wird ko-konstruiert), **kontextsensitive Kodierung** (jeder Beitrag wird im Licht des umgebenden Gesprächs kodiert), **Multi-Kodierung mit Konfidenz**. Einfach ein Transkript hochladen.
- **Mehrstufiger Format-Konverter** — Sprecher-Zuordnung, Entfernen von Klammern/Zeitstempeln, Seite-an-Seite-Vorschau vor dem Download
- **Gruppen-Metadaten** — Klassen-ID, Klassengröße, Name der Lehrkraft (alles optional)

## Lokale Audio-Transkription (optional)

Eigener **Transkription**-Tab — verwandelt eine Audio-Aufnahme in ein Transkript, das direkt in die Analyse fließt, **zu 100 % lokal auf dem Gerät** (das Audio verlässt die Maschine nie). Angetrieben von der eigenständigen Open-Source-Engine [noScribe](https://github.com/kaixxx/noScribe) (Whisper + pyannote, GPL-3.0), die ausschließlich als separater Subprozess aufgerufen wird.

- **Installation bei Bedarf** — ein Knopf lädt eine isolierte Engine herunter (uv-verwaltetes Python + torch/pyannote + Whisper-Modell, ~3 GB, einmalig); die Umgebung der Haupt-App bleibt unberührt. Erkennt eine bestehende Desktop-Installation von noScribe und nutzt diese stattdessen.
- **Wellenform-Zuschnitt in der App** — die Start-/End-Anfasser direkt auf der Wellenform ziehen, um den zu transkribierenden Abschnitt auszuwählen; der gewählte Bereich wird automatisch in die noScribe-Start-/Stopp-Felder geschrieben (kein externer Audio-Editor nötig). Der Vorschnitt erfolgt auf Armlänge über den eigenen Audio-Stack der Engine, sodass die Originaldatei nie verändert wird
- **Vollständige noScribe-Optionsparität** — Audio-Eingabe, Ausgabe-Dateiname, Start-/Stopp-Bereich, Sprache, **Modellauswahl (schnell / präzise)**, Sprecheranzahl (aus der Gruppengröße vorbelegt), Pausen-Markierung, überlappende Sprache, Sprech-Disfluenzen, Zeitstempel
- **Whisper-Modellauswahl** — *schnell* (int8, ~0,8 GB) oder *präzise* (fp16, ~1,6 GB); ein noch nicht installiertes Modell wird vor dem Lauf bei Bedarf heruntergeladen
- **Live-Fortschritt** — Phase, Schritt (X von N), Prozentwert und eine Uhr für die verstrichene Zeit; abbrechbar (beendet den gesamten Prozessbaum)
- **Editierbares Transkript-Feld** — Sprecher-Bezeichnungen oder Rechtschreibung vor der Analyse korrigieren (Human-in-the-Loop); Änderungen wirken auf das geteilte Transkript, das die Pipeline speist
- **Transkript speichern (.txt)** — das fertige Transkript als reine Textdatei herunterladen, unabhängig von der Analyse-Pipeline
- **Berücksichtigt Sitzung zurücksetzen** — *Sitzung zurücksetzen* leert das Audio, das Wellenform-Widget, den Zuschnittbereich und das Transkript; dieselbe Datei lässt sich nach erneutem Upload jederzeit wieder zuschneiden
- **Automatische Übergabe** — Sprecher-Bezeichnungen auf die TalkTrace-Konvention `S01+` umnummeriert, Metadaten-Kopf entfernt, Format validiert, in den Analyse-Tab geladen
- **Engine-Verwaltung** — Version angezeigt, Ein-Klick-Deinstallation, um den Speicherplatz zurückzugewinnen

## Formatives Lehrkräfte-Feedback (optional, LLM)

Eigener **Feedback**-Tab — erzeugt **forschungsgestütztes, formatives Feedback für die Lehrkraft** aus der bereits auf dem Bildschirm vorliegenden Analyse. Der Bericht versteht sich als Gerüst für die Selbstreflexion, nicht als summative Bewertung.

- **Drei strukturierte Achsen** — *Stärken*, *Entwicklungsfelder*, *Konkrete Umsetzungshinweise*
- **In der Analyse verankert** — nutzt das codebezogene Profil der Lehrkraft, die Codebuch-Definitionen und die quantitativen Kennzahlen der aktuellen Sitzung; kein externer Kontext erforderlich
- **Einen korrigierten Bericht hochladen** — den Bericht exportieren, die Kodierungen in Word oder Excel prüfen und korrigieren und ihn hier wieder einlesen, sodass das Feedback auf der **geprüften** Fassung statt auf der Rohausgabe des Modells beruht. Akzeptiert DOCX, XLSX, CSV/ZIP und HTML (nicht PDF — die Tabellenstruktur lässt sich daraus nicht zuverlässig rekonstruieren). Der Import trägt sich selbst: Codes *und* Kennzahlen stammen aus dem Dokument, sodass er auch als **eigenständiger Einstiegspunkt** in einer frischen Sitzung ohne durchgeführte Analyse funktioniert. Tabellen werden über ihre Spaltenüberschriften in beiden Sprachen gefunden, nie über die Position, und die Bezeichnung der Lehrkraft wird dem Bericht entnommen — andernfalls würde eine Abweichung zwischen der Bezeichnung im Bericht und der App-Einstellung stillschweigend jeden Lehrkraft-Beitrag aus den Kennzahlen fallen lassen. Enthält der Bericht seinen **Legenden**-Abschnitt, wird das Codebuch daraus rekonstruiert, sodass das Modell weiß, was die Code-Buchstaben bedeuten, ohne weiteres Einrichten; ein im Analyse-Tab geladenes Codebuch hat weiterhin Vorrang, da es auch die vollständigen Beschreibungen mitführt.
- **Kurze Literaturliste** — verankert in der Literatur zum dialogischen Unterrichten (T-SEDA, IRE/IRF, accountable talk, productive disciplinary engagement)
- **Zweisprachig** — deutscher oder englischer Prompt-Satz, folgt der aktiven UI-Sprache
- **Direkt editierbar** — vor dem Export verfeinern, straffen oder umformulieren; Bearbeitungen bleiben über erneute Renderings hinweg erhalten
- **Export nach Word (.docx) oder PDF** — natives Dokument; PDF über das installierte Word (docx2pdf), unter Linux nicht verfügbar
- **Sichtbarer Haftungsausschluss** — formative Hilfe, kein Urteil; kein Ersatz für kollegiale oder aufsichtsführende Durchsicht
- **Kosten erfasst** — zählt wie jeder andere LLM-Aufruf in den kumulativen Kosten-Tracker

## Einwilligungserklärung (optional)

Eigener **Einwilligung**-Tab — erzeugt eine druckfertige **DSGVO-Art.-13**-Einwilligungserklärung für den Fortbildungskontext, in dem ein Trainerteam *mit* Lehrkräften arbeitet und jede Lehrkraft in die Verarbeitung ihrer **eigenen** Aufnahme einwilligt. Wortlaut adaptiert von dem **CC0**-lizenzierten [Consent-Gen-RDMO](https://github.com/berndzey/Consent-Gen-RDMO) (TU Dortmund).

- **Vorausgefülltes Formular + Live-Vorschau** — sinnvolle Voreinstellungen für den Fortbildungskontext; das Dokument rendert beim Bearbeiten neu
- **Bildet den realen Datenfluss ab** — lokale Transkription (Audio bleibt auf dem Gerät) vs. das konfigurierte LLM als Empfänger; ein Cloud/Lokal-Schalter steuert den Absatz zur **Drittstaaten-Übermittlung** und eine separate Einwilligungs-Checkbox, wobei der Anbieter aus dem aktiven Backend vorbelegt wird
- **Export nach Word (.docx) oder PDF** — editierbares natives Dokument; PDF über das installierte Word (docx2pdf)
- **Pflichtfeld-Absicherung** — fehlende Pflichtfelder erscheinen als rote `!!! … !!!`-Markierungen auf dem Dokument
- **Sichtbarer Haftungsausschluss** — eine Hilfe, keine Rechtsberatung; im Formular und in der Fußzeile des Dokuments angezeigt (Prüfung durch Ihre*n Datenschutzbeauftragte*n erforderlich)

## LLM-Backends

- **Fünf Anbieter + eigene benutzerdefinierte Endpunkte** — [LocalMind](https://www.localmind.ai/) (EU-gehostetes Gateway, der DSGVO-freundliche Standard), OpenAI, Anthropic, Mistral, DeepSeek, plus **beliebig viele eigene OpenAI-kompatible Endpunkte** — im Optionen-Tab hinzufügen, umbenennen und löschen (jeweils mit Name, Basis-URL und eigenem Schlüssel im OS-Keyring), z. B. ein selbst gehosteter vLLM-/llama.cpp-Server und ein institutionelles Gateway nebeneinander. Jeder benutzerdefinierte Anbieter führt seine eigene Modellliste.
- **Live-Modell-Aktualisierung** — ein Klick pro Anbieter holt die aktuelle Modellliste direkt aus dessen Katalog (OpenAI-kompatibles `/v1/models` oder Anthropics Modellliste; erfordert einen gespeicherten Schlüssel); Embedding-/Audio-/Bild-Modelle werden herausgefiltert, und Preise bereits in der Registry vorhandener Modelle überstehen die Aktualisierung
- **Editierbare Modell-Registry** — Modelle hinzufügen oder entfernen, Preise pro Million Token festlegen
- **Benutzerdefinierte Prompts** — System- und User-Prompts bearbeiten, jederzeit auf Standard zurücksetzen
- **Strukturierte Ausgaben mit Codebuch-Enums** — Shortcode + Sprecher werden decoderseitig auf die Codebuch-Einträge / Transkript-Sprecher beschränkt (OpenAI strict json_schema, Anthropic tool_use input_schema, Mistral / DeepSeek / LocalMind / custom json_schema). Beseitigt halluzinierte Codes; fällt auf ein unbeschränktes Schema zurück, falls ein Modell die strict-Variante ablehnt.
- **Live-Kostenvorhersage** — untere Schätzgrenze, aktualisiert sich beim Tippen
- **Kumulativer Kosten-Tracker** — Gesamtausgaben über alle Analysen, pro Anbieter, sitzungsübergreifend persistiert
- **API-Schlüssel im OS-Keyring** — Keychain, Credential Manager, SecretService

## Quantitative Ergebnisse

- **Beteiligungs-Kennzahlen** — Klassengröße, aktive Teilnehmende, Beteiligungsquote
- **Redeanteil-Diagramm** — von Lehrkraft vs. Schüler*innen gesprochene Wörter
- **Sprecherbezogene Beitragsstatistik** — Anzahl, durchschnittliche Länge, Median-Länge
- **Zeitverlaufs-Ansicht** — Aufschlüsselung in drei Segmente über die Stunde

## Qualitative Ergebnisse

- **Sprecherbezogene Kodierung** — jeder kodierte Beitrag trägt eine Sprecher-Bezeichnung
- **Kontextsensitive Kodierung** — das LLM wird ausdrücklich angewiesen, jeden Beitrag im Licht des umgebenden Gesprächs zu kodieren (eine kurze Antwort nach einer Warum-Frage ist eine Begründung, ein „nein, aber…" nach einem Vorschlag ist ein Einwand), nicht isoliert; Codes werden weiterhin pro Beitrag vergeben
- **Nicht-Züge bleiben unkodiert** — ein code-unabhängiger Schutzmechanismus hält bloße Nominierungen („S2?"), minimales Feedback ohne eigenen Inhalt („Ja.", „Genau.") und unverständliche Fetzen („(unverständlich)") aus der Kodierung heraus — es sei denn, der Kontext macht einen kurzen Beitrag klar zu einem substanziellen Zug (ein entschiedenes „Nein." als Widerspruch, eine kurze Sachantwort); Konfidenzwerte sind über die gesamte Skala verankert (90+ nur bei eindeutiger Textevidenz), statt sich bei einem Standardwert zu häufen
- **Konfidenz bei jeder Kodierung** — bei Single- wie Multi-Kodierung gleichermaßen: jeder Code trägt die **0–100-Konfidenz** des Modells, inline als `CODE (NN %)` angezeigt. Das Schema fordert sie in **beiden Modi** an und lässt einen Code nicht mehr ohne sie zurückkommen, sodass selbst kleinere Modelle (z. B. GPT-3.5) kalibrierte Werte statt Leerstellen liefern.
- **Multi-Kodierung mit Konfidenz** — optional zuschaltbar; das Modell vergibt bis zu **2 Kandidaten-Codes pro Äußerung, jeweils mit einer 0–100-Konfidenz** (passend zu T-SEDAs Regel von 0–2 Codes pro Beitrag), angezeigt in **eigenen Spalten** (`Code 1`, `Code 2`, z. B. `EN (92 %)`), nach Konfidenz gereiht. Unsichere Kandidaten bleiben sichtbar — der Konfidenzwert macht die Unsicherheit transparent, der Mensch entscheidet. Ein Sicherheitsnetz in der Nachverarbeitung erzwingt die Obergrenze, selbst wenn das Modell überliefert; das Häufigkeitsdiagramm, der Chip für den häufigsten Code, die Zeitverlaufs-Verteilung und die Übergangsmatrix zählen den **Primär-Code** (`Code 1`) pro Beitrag, sodass Sekundär-Kandidaten die Verteilung nie verzerren.
- **Zweiter Prüfdurchgang** — nach jeder Analyse werden Beiträge, die unkodiert geblieben sind (innerhalb der gewählten Sprechergruppe), automatisch erneut an das LLM übermittelt, mit einer ausdrücklichen Sorgfalts-Anweisung: nur dann einen Code vergeben, wenn er klar gestützt ist, unkodiert zu bleiben ist legitim. Neue Kodierungen werden in die Tabelle eingefügt; eine Benachrichtigung meldet, wie viele Beiträge erneut geprüft und wie viele Codes ergänzt wurden.
- **Codebuch-Prioritätshierarchie** — Prioritätszeile, explizite Spalte oder Codebuch-Reihenfolge
- **Code-Verteilungsdiagramm** — Häufigkeit jedes Codes über das Gespräch, **nach Sprechergruppe gestapelt**: ein Balken pro Code, aufgeteilt in den Anteil der Lehrkraft und den der Schüler*innen. Die Gesamthöhe bleibt die Gesamthäufigkeit, sodass das „wie oft" lesbar bleibt und das „von wem" obenauf kommt — das Interaktionsmuster, das ein einfarbiger Balken verbirgt (z. B. Einladungen von der Lehrkraft, Einwände von den Schüler*innen). Fällt auf eine einzelne Farbe zurück, wenn nur eine Gruppe kodiert ist. Der DOCX-/HTML-Bericht ergänzt die exakten Zahlen als **Code-×-Sprechergruppen-Tabelle** (Zeilensummen pro Code und eine Summenzeile), sodass die Aufteilung zitierbar und nicht nur sichtbar ist.
- **Konfidenz-Hervorhebung im Bericht** — Code-Zellen im DOCX-/HTML-Bericht werden nur an den **beiden Rändern** eingefärbt: sicher (≥ 90 %) und hochgradig unsicher (< 50 %). Die Schwellen sind **dieselben Anker, gegen die der Prompt kalibriert**, sodass der Bericht nie als sicher markiert, was das Modell nicht als sicher zu behandeln angewiesen war. Das mittlere Band ist der Normalfall (rund drei Viertel eines realen Laufs) und bleibt neutral — es ebenfalls einzufärben würde den Bericht durchgehend einfärben und der Hervorhebung ihre Wirkung nehmen. Der Prozentwert bleibt in der Zelle und trägt das Detail: präziser als jedes Band und im Schwarz-Weiß-Druck lesbar. Handkorrigierte Zellen tragen keinen Konfidenzwert und bleiben bewusst uneingefärbt — eine menschliche Entscheidung darf nicht wie eine spekulative Modellvermutung aussehen.
- **Tabelle der kodierten Impulse** — jeder Beitrag des Gesprächs (kodiert oder nicht) mit Sprecher, Beitragsindex, Code-Spalte(n) und Äußerungstext; **editierbar** — jede Code-Zelle doppelklicken, um die LLM-Zuweisung zu korrigieren (gegen das Codebuch validiert, Änderungen wirken sofort auf alle Diagramme und Berichte; eine manuelle Korrektur überschreibt bewusst die Konfidenz des Modells)
- **Zeitverlauf der Code-Verteilung** — welche Codes wann in der Stunde auftauchen (Primär-Code pro Beitrag, konsistent mit dem Häufigkeitsdiagramm)
- **Code-Übergangs-Heatmap** — Markov-artige Matrix, welcher Code auf welchen folgt (unkodierte Beiträge übersprungen, bei Multi-Kodierung gilt der prioritätsaufgelöste Code). Legt Gesprächsdynamiken wie IRE-Muster offen, die Häufigkeitsdiagramme verbergen. Optionaler Berichtsabschnitt in DOCX/HTML/XLSX/CSV.
- **Zusammenfassung des häufigsten Codes** + Redeanteil der Lehrkraft mit Aufschlüsselung pro Schüler*in
- **Live-Kodier-Ansicht (Streaming)** — Kodierungen erscheinen fortschreitend, optional zuschaltbar

## Berichte

- **Vier Export-Formate** — DOCX, PDF (Win/macOS), XLSX, HTML
- **Long-Format-CSV- / R-Datapack-Export** — statistikfreundliches Bündel neben DOCX/XLSX/PDF/HTML
- **Konfigurierbare Abschnitte** — quantitativ, qualitativ, Zeitverlauf, Code-Legende, alle zuschaltbar
- **Eingebettete Diagramme und Tabellen** — teilfertig, keine Nachbearbeitung
- **Reproduzierbarkeits-Fingerabdruck** — kurzer Hash aus Codebuch + Prompts + Modell + Transkript, in jeden Bericht eingebettet
- **Automatisch erzeugter Methoden-Absatz** — per Zwischenablage kopierbarer Text für den Methodenteil von Papern (Werkzeug, Modell, Codebuch-Umfang, Stichprobenumfang, Fingerabdruck, Datum), zweisprachig, auch in die Berichtslegende eingebettet

## Sitzungen

- **Automatisches Speichern in den Verlauf** nach jeder erfolgreichen Analyse
- **Manueller Verlaufs-Browser** — laden, löschen, jetzt speichern
- **Sitzungs-Import/-Export** als `.pkl`
- **Verlauf-Neuladen ist kostenlos** — keine neuen LLM-Aufrufe beim Wiederherstellen einer gespeicherten Sitzung

## Oberfläche

- **Start-Tab (Landing-Page)** — Workflow-Statusleiste, fünf Einstiegskacheln (T-SEDA-Analyse · Audio · Transkript · Fortsetzen · Demo), Zeile mit der aktuellen Konfiguration, „Was ist neu" und die Datenschutz-Bestätigung; der Standard-Tab beim Start
- **Workflow-geordnete Tabs** — Start → Transkription → Analyse → Ergebnisse → Feedback, mit Optionen daneben und Einwilligung + Info rechts; die LLM-Konfiguration liegt im Analyse-Tab, die Sidebar dient nur der Organisation (Sprache, Sitzung speichern/wiederherstellen/zurücksetzen)
- **Helles & dunkles Theme** — Soft Nordic (hell) und Deep Forest (dunkel), Umschalter in der Titelleiste
- **Zweisprachige Oberfläche** — Englisch & Deutsch, jederzeit umschaltbar
- **Onboarding-Tooltips** — Hover-Hilfe an jedem wichtigen Bedienelement
- **Datenschutz-Bestätigungsschranke** — eine Auswahl im Start-Tab (Daten mit ausdrücklicher Einwilligung · fiktive Testdaten · nur meine eigenen Äußerungen), die bestätigt sein muss, bevor irgendein LLM-Aufruf hinausgeht
- **Schnellstart-Checkliste** — Live-✓/✗-Panel (auf dem Start-Tab), das zeigt, was bereit ist
- **Demo-Knopf** — eine Beispiel-Analyse ohne API-Schlüssel laden (T-SEDA-kodierte Sozialkundestunde zur Senkung des Wahlalters auf 16)
- **Goldstandard-Selbsttest** — ein Klick auf *Die App testen* führt eine bekannte Fixture aus und zeigt Erwartet vs. Tatsächlich; ein Vertrauensanker, bevor Nutzende ihre eigenen Daten analysieren
- **Tab-Benachrichtigungs-Badges** — Status auf einen Blick, wo Handlung nötig ist
- **Automatischer Tab-Wechsel** — springt zu Ergebnisse, wenn die Analyse abgeschlossen ist
- **Sprecher-Filter** — nur die Lehrkraft, nur die Schüler*innen oder beide kodieren
- **Analyse ohne Lehrkraft** — reine Schüler-Gruppendiskussionen werden vollständig unterstützt
- **Abbrechbare Analysen** — roter Abbrechen-Knopf neben Start, während ein Streaming-Lauf in Arbeit ist; Teilkodierungen bleiben mit einem roten Banner erhalten.
- **Info-/Lizenz-Tab** — Betreuer-Infos, GitHub-/ORCID-Links, AGPL-3.0-Hinweis

## Einrichtung & Launcher

- **Ein-Klick-Launcher** für Windows (`start.bat`), macOS, Linux (`start.sh`)
- **Automatische venv- + Abhängigkeits-Installation** beim ersten Start
- **Natives Desktop-Fenster** (Cocoa / WebKit / GTK) oder Headless-Browser-Modus
- **Hot-Reload-Entwicklungsmodus** (`dev.bat` / `dev.sh`)
- **Distributionsbewusste Einrichtung** — bietet an, fehlende Pakete unter Debian/Fedora/Arch zu installieren

---

## Roadmap

base v1 deckt den stabilen Kern ab. Die aktive Entwicklung neuer Funktionen findet in einer privaten internen Forschungsversion statt; geprüfte, umfangsangemessene Ergänzungen werden mit der Zeit in base übernommen. Externe Beiträge sind willkommen — siehe [CONTRIBUTING.md](CONTRIBUTING.md).
