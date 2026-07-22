# TalkTrace AI base

[![PyPI](https://img.shields.io/pypi/v/talktrace-ai-base?label=PyPI)](https://pypi.org/project/talktrace-ai-base/)
[![Python](https://img.shields.io/pypi/pyversions/talktrace-ai-base)](https://pypi.org/project/talktrace-ai-base/)
[![License](https://img.shields.io/pypi/l/talktrace-ai-base)](LICENSE)

📖 [English](README.md) · **Deutsch**

<p align="left">
    <picture>
        <source media="(prefers-color-scheme: light)" srcset="images/light.png">
        <source media="(prefers-color-scheme: dark)" srcset="images/light.png">
        <img src="images/light.png" alt="TalkTrace AI base" width="1280">
    </picture>
</p>

LLM-gestützte Analyse von Transkripten aus Unterricht und Kleingruppen. Quantitative Metriken, qualitatives Codieren, strukturierte Berichte — als Desktop-App verpackt, lizenziert unter AGPL-3.0.

> **base** ist die öffentliche Distribution, die aus dem ursprünglichen [TalkTrace-AI](https://github.com/talktrace-ai/talktrace-ai) von Jami Schorling und Dennis Hauk (Universität Leipzig) hervorgegangen ist. base konzentriert sich auf den stabilen, gut getesteten Kern; experimentelle Funktionen und die aktive Forschungs-Roadmap liegen in einer privaten internen Forschungsversion.

**Highlights** — Integrierte **T-SEDA-Codebuch-Vorlage** (ein Klick: Codebuch geladen, lehrkraftfokussiertes Multi-Coding mit Konfidenz je Code und einem zweiten Prüfdurchlauf — einfach ein Transkript hochladen) · Fünf LLM-Backends mit dem EU-gehosteten [LocalMind](https://www.localmind.ai/)-Gateway als DSGVO-freundlicher Voreinstellung (plus OpenAI, Anthropic, Mistral, DeepSeek) · Eigene OpenAI-kompatible Endpunkte (eigene Base-URL + Key) mit Modell-Aktualisierung per Klick · Lokale Audio-Transkription mit In-App-Waveform-Zuschnitt (optionale noScribe-Engine, 100 % auf dem Gerät) · Forschungsbasiertes formatives Lehrkraft-Feedback (editierbar, DOCX/PDF) · DSGVO-Art.-13-Einwilligungserklärungs-Generator (DOCX/PDF) · Streaming-Codieransicht · Human-in-the-Loop-Codebearbeitung · Code-Übergangs-Heatmap und Verlaufsansichten · Automatisch erzeugter Methoden-Absatz + Reproduzierbarkeits-Fingerprint · DOCX-/PDF-/XLSX-/HTML-/CSV-Exporte · Helle/dunkle Themes · EN/DE-Oberfläche

**Vollständige Funktionsliste** — [FEATURES.md](FEATURES.md)

---

## Über das Projekt

Eine FLOSS-, plattformunabhängige Web-App zur Analyse verbaler Interaktion in Unterrichts- und Kleingruppensettings. Aufbauend auf [Shiny for Python](https://shiny.posit.co/py/) nutzt sie LLMs, um sowohl **quantitative** Metriken (Beteiligung, Gesprächsanteile) als auch **qualitatives** Codieren (Sprechakte) zu erzeugen, und exportiert diese als strukturierte Berichte.

**Backends:** [LocalMind](https://www.localmind.ai/) (EU-gehostetes Gateway, Voreinstellung) · [OpenAI](https://platform.openai.com/) · [Anthropic](https://www.anthropic.com/api) · [Mistral](https://mistral.ai/) · [DeepSeek](https://platform.deepseek.com/) · eigener OpenAI-kompatibler Endpunkt (eigene Base-URL + Key)

---

## Download (Windows, kein Python nötig)

Lade die aktuelle **TalkTraceAI-base-v1.2.0-win64.zip** von den [GitHub Releases](https://github.com/MoominVibeCoder/talktrace-ai-base/releases), entpacke sie und doppelklicke `TalkTraceAI.exe`. Keine Python-Installation erforderlich.

> Für macOS / Linux oder wenn du lieber aus dem Quellcode startest, siehe den Quickstart unten.

---

## Quickstart (aus dem Quellcode)

**Python ≥ 3.12 erforderlich** (Entwicklungsziel: 3.13). Auf Python 3.14 ist das eingebettete Desktop-Fenster nicht verfügbar — `pywebview` wird übersprungen und die App öffnet stattdessen im Standardbrowser. Wähle dann dein Betriebssystem:

<details>
<summary><strong>Windows</strong></summary>

Doppelklicke `start.bat`, oder aus einem Terminal:

```bat
start.bat
```

Python-Installation: Lade sie von [python.org](https://www.python.org/downloads/windows/) herunter und stelle sicher, dass *„Add python.exe to PATH"* aktiviert ist — sonst kann `start.bat` den Interpreter nicht finden.

</details>

<details>
<summary><strong>macOS</strong></summary>

```bash
chmod +x start.sh
./start.sh
```

Python-Installation: Das mit macOS ausgelieferte Python ist in der Regel veraltet. Installiere eine aktuelle Version von [python.org](https://www.python.org/downloads/macos/) oder über Homebrew (`brew install python@3.13`).

</details>

<details>
<summary><strong>Linux</strong></summary>

```bash
chmod +x start.sh
./start.sh
```

`start.sh` erkennt fehlende `python3-venv` / `python3-pip` und bietet an, sie über `apt` / `dnf` / `pacman` zu installieren.

Für ein natives Desktop-Fenster (sonst öffnet die App im Standardbrowser):

```bash
sudo apt install gir1.2-webkit2-4.1 python3-gi    # Debian/Ubuntu
```

**Einschränkungen:**
- PDF-Export unter Linux nicht verfügbar (setzt Microsoft Word voraus) — nutze stattdessen DOCX.
- Ohne System-Keyring bleiben API-Keys nur für die laufende Sitzung erhalten. Starte entweder einen Keyring-Daemon oder verlasse dich auf den mitgelieferten `keyrings.alt`-Datei-Fallback.

</details>

<details>
<summary><strong>Launcher-Flags & Entwicklungsmodus</strong></summary>

| Flag (Unix) | Flag (Windows) | Wirkung |
|---|---|---|
| `--reinstall` | `/reinstall` | Die virtuelle Umgebung von Grund auf neu anlegen |
| `--nowindow` | `/nowindow` | Headless starten — öffnen unter <http://localhost:8000> |
| `--setup-only` | — | Venv + Abhängigkeiten bereitstellen, dann beenden |

Für die aktive Entwicklung nutze `dev.bat` (Windows) oder `./dev.sh` (Linux/macOS) — startet die App unter `shiny run --reload` und startet bei `.py`-Speichervorgängen automatisch neu.

</details>

---

## Oberfläche

Ein **Start**-Tab ist die Startseite (Workflow-Überblick, Einstiegs-Kacheln, Zeile zur aktuellen Konfiguration, Datenschutz-Bestätigung, Quickstart-Checkliste). Der Workflow läuft dann von links nach rechts — **Transkription · Analyse · Ergebnisse · Feedback** — mit **Optionen** daneben sowie **Einwilligung** + **Info** rechts. Die LLM-Konfiguration (Provider, Modell, Schalter, Live-Kostenschätzung, *Analysieren*) liegt im **Analyse**-Tab; die Sidebar dient nur der Organisation — EN/DE-Umschaltung und Sitzung speichern/wiederherstellen/zurücksetzen. Der Dark-Mode-Umschalter sitzt in der Titelleiste.

<details>
<summary><strong>Start-Tab</strong> (Startseite)</summary>

Der erste Bildschirm beim Start. Ein Workflow-Streifen (Audio → Transkript → Analyse → Feedback → Export) zeigt, wie weit du bist; Einstiegs-Kacheln springen zu einer **T-SEDA-Analyse** (lädt das integrierte Codebuch mit seinen Voreinstellungen — einfach ein Transkript ergänzen), zur Transkription, zur Analyse, zum Sitzungsverlauf oder zu einer Demo ohne Key. Eine Konfigurationszeile nennt den aktiven Provider bzw. das aktive Modell, und eine einmalige **Datenschutz-Bestätigung** (Auswahl von *ausdrückliche Einwilligung*, *fiktive Testdaten* oder *nur meine eigenen Äußerungen*) gibt LLM-Aufrufe erst nach Bestätigung frei.

</details>

<details>
<summary><strong>Analyse-Tab</strong></summary>

Panel „Dokument-Eingabe":
- **Transkript** *(erforderlich)* — muss dem [noScribe](https://github.com/kaixxx/noScribe)-Format folgen. Der interaktive mehrstufige Konverter verarbeitet Transkripte aus anderen Werkzeugen (z. B. [aTrain](https://github.com/JuergenFleiss/aTrain)) — Erkennung von Sprecher-Labels, Entfernen von Zeitstempeln, Prüfung von Klammer-Annotationen, Zuordnung je Sprecher, Vorschau nebeneinander.
- **Codebuch** *(erforderlich für die qualitative Analyse)* — siehe das [Beispiel-Codebuch](images/Example%20Codebook.docx). Codes gelten für **alle Sprecher** (Lehrkraft und Schüler). Alternativ lade die integrierte **T-SEDA-Vorlage** mit einem Klick (offizielle [T-SEDA](https://camtree.learnworlds.com/t-seda)-Codes für dialogisches Unterrichtsgespräch, DE/EN; T-SEDA Collective 2023, University of Cambridge, CC BY) — sie voreinstellt außerdem das Codieren von Lehrkraft- **und** Schülerbeiträgen (kontextsensitiv) sowie Multi-Coding mit Konfidenz.
- **Name der Lehrkraft** *(optional)* — falls im Transkript vorhanden, ermöglicht lehrkraftspezifische Metriken.
- **Gruppenkennung und Metadaten** — für die Beschriftung der Berichte.

Konfiguriere das LLM und klicke im Karte **LLM-Konfiguration** des Tabs auf *Analysieren*; die App wechselt nach Abschluss zu den Ergebnissen.

> **Kostenschätzung.** Der Wert in der LLM-Konfigurationskarte ist eine *Untergrenze* — Länge von Transkript + Codebuch × Eingabepreis × ~4 für die Ausgabe. Ein kumulativer Kosten-Tracker (in *Optionen*) summiert die Ausgaben über alle deine Analysen hinweg.

</details>

<details>
<summary><strong>Transkriptions-Tab</strong> (optional, lokal)</summary>

Verwandle eine Audioaufnahme **vollständig auf deinem Rechner** in ein Transkript — das Audio verlässt deinen Computer nie. Angetrieben von der eigenständigen Open-Source-Engine [noScribe](https://github.com/kaixxx/noScribe) (Whisper + pyannote), GPL-3.0, nur als separater Subprozess aufgerufen und bei Bedarf installiert (~3 GB, einmalig, Windows).

Bietet den vollen Satz an noScribe-Optionen: Audio-Eingabe, Ausgabedateiname, Start-/Stopp-Bereich, Sprache, **Modell (schnell / präzise)**, Sprecheranzahl (vorbelegt aus der Gruppengröße), Pausen-Markierung, überlappende Sprache, Sprechunflüssigkeiten, Zeitstempel. Ein **In-App-Waveform-Editor** lässt dich Anfasser für Start und Ende des Segments ziehen — kein externes Werkzeug nötig. Eine Live-Fortschrittsanzeige (Schritt, Prozentsatz, verstrichene Zeit) zeigt, was gerade passiert, und ein **editierbares Transkript-Feld** lässt dich Sprecher-Labels oder Rechtschreibung korrigieren, bevor das Ergebnis direkt in den Analyse-Tab übergeben oder als `.txt`-Datei gespeichert wird.

Am besten geeignet für **10–15-minütige Kleingruppenaufnahmen** (CPU-Transkription ≈ 1,5-fache Echtzeit mit dem *schnellen* Modell). Siehe den In-App-Tab Info / Lizenz und [NOTICE](NOTICE) für die Details zu Lizenzierung und Datenschutz.

</details>

<details>
<summary><strong>Feedback-Tab</strong> (optional, LLM)</summary>

Erzeuge **forschungsbasiertes, formatives Feedback für die Lehrkraft**, nachdem eine Analyse gelaufen ist. Der Feedback-Tab nimmt die codierten Beiträge, die Codebuch-Definitionen und die quantitativen Metriken aus derselben Sitzung und erzeugt einen strukturierten Fließtext-Bericht entlang dreier Achsen — **Stärken** · **Entwicklungsfelder** · **Konkrete Umsetzungshinweise** — mit einer kurzen Literaturliste, die in der Forschung zum dialogischen Unterricht verankert ist (T-SEDA, IRE/IRF, accountable talk, productive disciplinary engagement).

Der erzeugte Text ist **vollständig direkt editierbar** — du kannst ihn straffen, umformulieren oder Abschnitte entfernen, bevor du nach **Word (.docx)** oder **PDF** exportierst. Eine Live-Kostenschätzung und der kumulative Kosten-Tracker (in *Optionen*) gelten auch hier.

Du kannst außerdem einen **korrigierten Bericht hochladen** (DOCX / XLSX / CSV / HTML), sodass das Feedback auf den Codierungen beruht, die du in Word oder Excel geprüft hast, statt auf der Rohausgabe des Modells — er dient zugleich als **eigenständiger Einstiegspunkt** in einer frischen Sitzung (Codes *und* Metriken stammen aus dem Dokument, und das Codebuch wird aus der Berichtslegende rekonstruiert, sofern vorhanden).

Es ist eine **Hilfe, kein Urteil** — klar gerahmt als formatives Gerüst zur Selbstreflexion, nicht als summative Bewertung.

</details>

<details>
<summary><strong>Einwilligungs-Tab</strong> (optional)</summary>

Erzeuge eine druckfertige **DSGVO-Art.-13**-Einwilligungserklärung für den Fortbildungskontext — in dem ein Trainerteam *mit* Lehrkräften arbeitet und jede Lehrkraft in die Verarbeitung ihrer **eigenen** Aufnahme einwilligt. Ein vorausgefülltes Formular (links) erzeugt eine Live-Dokumentvorschau (rechts), die du nach **Word (.docx)** oder **PDF** exportierst.

Die Erklärung bildet den realen Datenfluss ab: lokale Transkription (Audio bleibt auf dem Gerät) gegenüber dem konfigurierten LLM als Empfänger. Ein Cloud-/Lokal-Umschalter steuert den Absatz zur **Drittlandübermittlung** und ein separates Einwilligungs-Kästchen; fehlende Pflichtfelder erscheinen als rote `!!! … !!!`-Marker. Die Formulierung ist aus dem **CC0**-lizenzierten [Consent-Gen-RDMO](https://github.com/berndzey/Consent-Gen-RDMO) (TU Dortmund) übernommen.

Es ist eine **Hilfe, keine Rechtsberatung** — der Hinweis wird im Formular und in der Dokument-Fußzeile angezeigt; lass sie vor der Verwendung von deiner bzw. deinem Datenschutzbeauftragten prüfen. Siehe [NOTICE](NOTICE).

</details>

<details>
<summary><strong>Ergebnisse-Tab</strong></summary>

Aufgeteilt in einen quantitativen und einen qualitativen Abschnitt.

**Quantitativ** (deterministisch): Beteiligungsmetriken, Gesprächsanteile (absolut + relativ), Beitragsstatistiken je Sprecher (Anzahl / Mittelwert / Median), Verlaufsansicht über drei Segmente.

**Qualitativ** (LLM-codiert): Codierung je Sprecher (jeder Beitrag trägt ein `Sprecher`-Label), Verteilungsplot der Codes **gestapelt nach Sprechergruppe** (Lehrkraft vs. Schüler, mit der passenden Tabelle Code × Sprechergruppe im Bericht), Tabelle codierter Impulse, Code-Verteilung im Zeitverlauf, **Markov-artige Code-Übergangs-Heatmap** und ein **automatisch erzeugter Methoden-Absatz** für Paper-Manuskripte (Kopieren per Klick, EN/DE). **Jede Codierung trägt die Konfidenz des Modells** (z. B. `EN (92 %)`) — im Single-Coding auf dem einen Code, und mit aktiviertem **Multi-Coding** über die **beiden Top-Kandidaten-Codes in eigenen Spalten** (entsprechend der T-SEDA-Regel von 0–2 Codes pro Beitrag), nach Konfidenz sortiert; unsichere Kandidaten bleiben sichtbar, der Mensch entscheidet. Der DOCX-/HTML-Bericht **schattiert die Sicherheitsränder** jeder Code-Zelle (≥ 90 % und < 50 %) anhand derselben Ankerpunkte, gegen die der Prompt kalibriert. Ein **zweiter Prüfdurchlauf** reicht nicht codierte Beiträge automatisch erneut an das LLM zur sorgfältigen Nachprüfung, und jede Zelle bleibt von Hand editierbar. Alle Beiträge des Gesprächs erscheinen in der Tabelle und den Berichten, codiert oder nicht.

</details>

<details>
<summary><strong>Optionen-Tab</strong></summary>

- **API-Konfiguration** — Keys für LocalMind, OpenAI, Anthropic, Mistral, DeepSeek sowie **beliebig viele eigene OpenAI-kompatible Endpunkte** (in den Optionen hinzufügen/umbenennen/löschen — jeweils mit Name, Base-URL und eigenem Key, z. B. ein selbst gehosteter vLLM-Server und ein institutionelles Gateway nebeneinander). Keys liegen im OS-Keyring (Keychain / Credential Manager / SecretService); Namen und Base-URLs bleiben in deiner lokalen Konfiguration erhalten.
- **Modelle für die LLM-Auswahl** — bearbeite die Registry (Modelle hinzufügen/entfernen, Preise pro Million Token festlegen); Änderungen werden in Echtzeit an die Modellauswahl im Analyse-Tab weitergegeben. Ein Knopf **Modelle vom Provider laden** aktualisiert die Liste des ausgewählten Providers direkt aus dessen Live-Katalog (benötigt einen gespeicherten Key); Embedding-/Audio-/Bildmodelle werden herausgefiltert und bereits gesetzte Preise bleiben erhalten.
- **Eigene Prompts** — passe die System- + User-Prompts für das qualitative Codieren an; Voreinstellungen jederzeit wiederherstellbar.
- **Kosten-Tracker** — kumulative Ausgaben über alle Analysen hinweg, je Provider.
- **App testen** (Goldstandard-Selbsttest) — führt eine bekannte Vorlage aus und zeigt Erwartet vs. Tatsächlich, um Vertrauen aufzubauen, bevor du echte Daten analysierst.
- **Weitere Optionen** — Voreinstellungen für Name der Lehrkraft, Gruppen-ID, Klassengröße, erweiterte Schalter wie Streaming.

</details>

---

## Datenschutz

TalkTrace AI speichert Transkripte oder Analyseergebnisse **nicht** auf einem von den Betreuenden kontrollierten externen Server. Alle für eine Analyse benötigten Daten liegen im Browser- bzw. lokalen Speicher, während du mit dem Werkzeug arbeitest.

Da LLM-Modelle nicht von der App gehostet werden, kommuniziert das Backend während des qualitativen Codierschritts mit externen LLM-Providern. Die betreffenden Transkript- und Codebuch-Auszüge werden über die API des Providers übertragen — jegliche serverseitige Speicherung oder Protokollierung hängt dann von den Richtlinien dieses Providers und deinen Konto-Einstellungen ab. Der Standard-Provider ist das **EU-gehostete LocalMind-Gateway**, das Transkripte innerhalb der EU hält; in den USA oder China gehostete Provider bleiben eine ausdrückliche Wahl.

**Die Audio-Transkription ist vollständig lokal.** Der optionale Transkriptions-Tab führt die noScribe-Engine auf deinem eigenen Rechner aus — die Audiodatei wird nie auf einen von den Betreuenden kontrollierten oder einen Drittanbieter-Server hochgeladen. Das macht sie zu einer datenschutzfreundlichen Alternative zu Cloud-Transkriptionsdiensten. Siehe [NOTICE](NOTICE) für die Details zu Drittanbieter-Engine/-Modellen und der Lizenzgrenze.

Sitzungen können lokal als `.pkl`-Dateien gespeichert/wiederhergestellt werden; Berichte können heruntergeladen werden. **API-Keys** liegen im verschlüsselten Zugangsdaten-Tresor des Betriebssystems — Keychain (macOS), Credential Manager (Windows), SecretService (GNOME Keyring, KWallet) unter Linux.

---

## Mitwirkende

TalkTrace AI base wird von [Simon Filler](https://orcid.org/0009-0008-8736-8831) an der [Technischen Universität Dortmund](https://idif.sowi.tu-dortmund.de/institut/) betreut.

Das ursprüngliche TalkTrace AI wurde von [Jami Schorling](https://orcid.org/0009-0005-9007-2896) und [Dennis Hauk](https://orcid.org/0000-0002-5779-2876) am [Lehrstuhl für Lehr-Lern-Forschung in der politischen Bildung](https://www.sozphil.uni-leipzig.de/institut-fuer-politikwissenschaft/arbeitsbereiche/professur-fuer-fachdidaktik-gemeinschaftskunde/team/prof-dr-dennis-hauk) der Universität Leipzig entwickelt.

Siehe [NOTICE](NOTICE) für die vollständige Nennung.

## Mitwirken

Beiträge sind willkommen — bitte lies [CONTRIBUTING.md](CONTRIBUTING.md) und [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), bevor du einen Pull Request eröffnest. Sicherheitsprobleme: siehe [SECURITY.md](SECURITY.md).

## Lizenz

GNU Affero General Public License v3.0 — siehe [LICENSE](LICENSE) und [NOTICE](NOTICE).

Das vorgelagerte [TalkTrace-AI](https://github.com/talktrace-ai/talktrace-ai)-Repository trägt einen CC-BY-NC-4.0-Hinweis. Die base-Distribution wird mit der ausdrücklichen Zustimmung der ursprünglichen Autoren (Schorling, Hauk) unter AGPL-3.0 veröffentlicht; siehe [NOTICE](NOTICE) für die Relizenzierungs-Historie.
