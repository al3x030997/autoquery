# Feature 00 — MVP-Definition

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Abschnitt 1.4

## Zweck

Der MVP ist ein Hypothesentest, kein Feature-Showcase. Drei Hypothesen werden validiert bevor weitere Entwicklung gerechtfertigt ist.

---

## Drei Hypothesen

**1. Konversion:** Autoren erkennen in Sekunden dass AutoQuery ihr Problem löst → sie registrieren sich.

**2. Engagement:** Autoren bleiben aktiv bei den Ergebnissen — klicken, lesen, planen nächste Schritte.

**3. Emotionale Resonanz:** Die Ergebnisse fühlen sich persönlich an, nicht generisch. "Endlich versteht mich etwas."

---

## Erfolgsmetriken

| Metrik | Ziel | Messung | Fail |
|---|---|---|---|
| Visit-to-Signup | ≥ 10% | Unique Visitors vs. Registrierungen | < 5% nach 4 Wochen |
| Engagement Erstnutzung | ≥ 60s aktiv | Erster Input bis letzte Ergebnis-Interaktion | < 30s Median |
| Emotionale Resonanz | Freude + Neugier | Qualitative Interviews (10–15 Nutzer) + One-Click-Feedback | Überwiegend negativ/gleichgültig |

---

## MVP User Journey — Screen für Screen

### Screen 1: Landing Page

**Was der Nutzer sieht:** Eine klare Headline, ein Subtext, ein einzelner CTA-Button.

Beispiel-Tonalität:
- Headline: "Finde den Agenten, der genau dein Buch sucht."
- Subtext: "Beschreib dein Manuskript. Wir matchen es gegen hunderte echte Agenten-Profile — in Sekunden."
- CTA: "Matching starten" (kein Login nötig)

**Was der Nutzer tun kann:** CTA klicken → direkt zum Conversational Flow. Kein Login, kein Onboarding, kein Cookie-Banner (Session-Cookie ist funktional notwendig).

**Sekundäre Elemente:** Kurzer Dreischritt-Explainer ("1. Beschreib dein Buch → 2. Wir finden passende Agenten → 3. Du entscheidest, wen du anschreibst"), Link zu "Für Agenten" (Opt-Out + Transparenz), Footer mit Impressum + Datenschutz.

**Akzeptanzkriterien:**
- Seite lädt in < 2 Sekunden
- CTA ist above the fold auf Desktop und Mobile
- Hallway-Test: 4 von 5 Testpersonen verstehen in < 10s was AutoQuery tut
- Kein Login-Gate vor dem Matching
- Event geloggt: `page_view` (Analytics)

**Zahlt ein auf:** Konversion

---

### Screen 2: Conversational Input — Fragenkatalog

**Was der Nutzer sieht:** Eine Chat-ähnliche Oberfläche die eine Frage nach der anderen stellt. Keine Formularwand, kein Stepper — ein Gespräch.

**Interaktionsmodell:** Jede Frage erscheint einzeln. Der Autor beantwortet sie, die Antwort wird visuell bestätigt (ähnlich einer Chat-Bubble), dann erscheint die nächste Frage. Der Autor sieht seinen bisherigen Verlauf nach oben scrollbar.

**Fragensequenz:**

| # | Frage | Eingabetyp | Pflicht? |
|---|---|---|---|
| 1 | "Welches Genre hat dein Buch?" | Dropdown (min. 20 Genres aus `genre_aliases.yaml`), max. 3 auswählbar | Ja |
| 2 | "Wer ist deine Zielgruppe?" | Single-Select: Adult / YA / Middle Grade / Children's | Ja |
| 3 | "Beschreib den Ton deines Buchs in ein paar Worten." | Freitext, max. 200 Zeichen. Placeholder: "z.B. melancholisch, humorvoll, spannend, lyrisch" | Ja |
| 4 | "Welche Themen stehen im Zentrum?" | Tag-Input, min. 2, max. 8. Placeholder: "z.B. Found Family, Identität, Klimawandel" | Ja |
| 5 | "Mit welchen Büchern würdest du deins vergleichen?" | Freitext, 2–3 Comp Titles. Hinweis: "Comp Titles sind das stärkste Signal — sie helfen uns am meisten." | Ja |
| 6 | "Hast du Dokumente die du hochladen möchtest?" | Upload-Zone (siehe Screen 3) | Nein |
| 7 | "Gibt es sonst noch etwas das uns bei der Suche helfen kann?" | Freitext, max. 300 Zeichen. Placeholder: "z.B. Agent mit Erfahrung in Übersetzungsrechten, UK-basiert" | Nein |

**UX-Details:**
- Jede Frage hat einen kurzen Hilfetext darunter (dezent, nicht aufdringlich)
- Antworten sind nach Bestätigung noch editierbar (Klick auf die eigene Antwort → Inline-Bearbeitung)
- Optionale Fragen haben einen "Überspringen"-Link
- Nach der letzten Frage: CTA "Matching starten"
- Fortschrittsindikator als dezente Punkte oder Linie (nicht als "Schritt 3 von 7")

**Akzeptanzkriterien:**
- Jede Frage erscheint mit einer kurzen Animation (Einblenden, kein harter Cut)
- Antwort-Bestätigung ist sofort visuell sichtbar
- Zurückgehen und Editieren möglich ohne Datenverlust
- Auf Mobile: vollständig nutzbar, Tastatur-Handling korrekt
- Gesamtdauer: 2–4 Minuten für einen Autor der sein Buch kennt
- Alle Eingaben werden im Browser zwischengespeichert (Session, kein Verlust bei versehentlichem Reload)

**Zahlt ein auf:** Engagement (Conversational Flow fühlt sich leichter an als ein Formular), Emotionale Resonanz (Autor hat das Gefühl gehört zu werden)

---

### Screen 3: Upload-Zone (innerhalb des Conversational Flow)

**Kontext:** Erscheint als Antwort auf Frage 6 ("Hast du Dokumente?"). Der Autor kann Dateien hochladen oder überspringen.

**Akzeptierte Uploads:**

| Dokumenttyp | Dateiformate | Max. Größe | Zweck |
|---|---|---|---|
| Query Letter | .docx, .txt, .pdf | 10 MB | Kerntext für Matching — alternativ zum Freitext in einer späteren Frage |
| Synopsis | .docx, .txt, .pdf | 10 MB | Zusätzliches Signal für thematische Tiefe |
| Manuskript-Ausschnitt | .docx, .txt, .pdf | 10 MB | Kapitel oder Passage, wird auf 2000 Wörter gekürzt (serverseitig) |
| Pitch Deck / One-Pager | .pdf, .docx | 10 MB | Für Autoren die bereits pitching-ready sind |

**Verhalten:**
- Multi-Upload möglich: Drag & Drop oder Datei-Dialog, mehrere Dateien gleichzeitig
- Der Autor wählt per Dropdown pro Datei den Typ: "Query Letter" / "Synopsis" / "Manuskript-Ausschnitt" / "Pitch Deck"
- Upload-Fortschrittsanzeige pro Datei
- Nach Upload: Dateiname + Typ + Häkchen sichtbar in der Chat-Bubble
- Serverseitig: MIME-Type-Validierung (nicht nur Extension), Text-Extraktion, Kürzung auf max. 2000 Wörter pro Dokument

**Wenn ein Query Letter hochgeladen wird:**
- Das System erkennt das und überspringt die separate Query-Letter-Frage (falls es eine gäbe) — der Upload ersetzt sie
- Wenn der Autor *keinen* Query Letter hochlädt, erscheint nach der Upload-Zone eine Zusatzfrage: "Dann beschreib dein Buch bitte kurz in eigenen Worten — wie würdest du es einem Agenten pitchen?" (Freitext, min. 100, max. 1000 Wörter, Pflicht)

**Akzeptanzkriterien:**
- Dateiformat-Validierung vor Upload
- Dateigröße-Check vor Upload
- MIME-Type serverseitig geprüft (nicht nur Extension)
- Mindestens ein Query Letter muss vorhanden sein — entweder als Upload oder als Freitext
- "Überspringen" ist gleichwertig sichtbar
- Text-Extraktion aus .docx und .pdf funktioniert sauber (kein Formatting-Müll)

**Zahlt ein auf:** Matching-Qualität (mehr Kontext = bessere Embeddings), Engagement (Autoren die bereits Material haben investieren gerne)

---

### Screen 4: Loading / Matching in Progress

**Was der Nutzer sieht:** Eine kurze Übergangsanimation während das Matching läuft.

**Verhalten:**
- Ladezeit-Ziel: < 3 Sekunden
- Zeigt einen animierten Fortschrittsindikator (kein Spinner, etwas mit Persönlichkeit)
- Optional: kurzer Text der zeigt was passiert ("Analysiere dein Manuskript...", "Durchsuche 247 Agenten-Profile...", "Finde die besten Matches...")

**Akzeptanzkriterien:**
- Kein weißer Screen — sofort visuelles Feedback nach Klick
- Bei > 3 Sekunden: Fortschrittstext aktualisiert sich (nicht eingefroren)
- Bei Fehler: klare Fehlermeldung mit "Nochmal versuchen"-Button

**Zahlt ein auf:** Emotionale Resonanz (Spannung aufbauen), Engagement (verhindert Abbruch)

---

### Screen 5: Ergebnisse — Ohne Account (3 Teaser)

**Was der Nutzer sieht:** 3 Agenten-Karten mit genug Information um Relevanz zu erkennen, aber nicht genug um zu handeln.

**Pro Karte:**
- Name + Agentur
- Genre-Tags (z.B. "Cozy Fantasy", "Literary Fiction")
- Audience-Label (z.B. "Adult")
- Match-Indikator (Score-Balken oder Prozent — visuell, nicht nur Zahl)
- Match-Tags: 2–3 spezifische Keywords warum dieser Agent passt (z.B. "✓ Cozy Fantasy · ✓ Character-driven · ~ Queer Protagonists")

**Nicht sichtbar ohne Account:** Kein Aufklappen, keine Submission-Anforderungen, keine Aktionen.

**CTA unter den 3 Karten:** "17 weitere Agenten gefunden. Erstelle ein kostenloses Konto um alle zu sehen." — E-Mail + Passwort Registrierung inline (kein Seitenwechsel).

**Akzeptanzkriterien:**
- Die 3 gezeigten Agenten sind die Top-3 nach Scoring (nicht zufällig)
- Match-Tags sind spezifisch für *dieses* Manuskript (nicht generisch)
- CTA nennt die exakte Anzahl der weiteren Ergebnisse ("17 weitere", nicht "mehr")
- Registrierungsformular erscheint inline beim Klick auf CTA (kein Redirect)
- Event geloggt: `result_shown` (3×), `signup_cta_shown`

**Zahlt ein auf:** Konversion

---

### Screen 6: Registrierung (Inline)

**Was der Nutzer sieht:** Registrierungsformular direkt auf der Ergebnis-Seite.

**Felder:**
- E-Mail (Pflicht)
- Passwort (Pflicht, min. 8 Zeichen)
- Checkbox: Datenschutzerklärung akzeptieren (Pflicht, mit Link)

**Verhalten nach Registrierung:**
- Account erstellt, Nutzer sofort eingeloggt
- Ergebnis-Seite aktualisiert inline: 3 Karten → 20 Karten, Aufklappen wird verfügbar
- Kein Seitenwechsel, kein Neuberechnen — Ergebnisse sind bereits da
- E-Mail-Verifizierung im Hintergrund (blockiert nicht)

**Akzeptanzkriterien:**
- Registrierung → volle Ergebnisse in < 2 Sekunden
- Fehler bei bereits existierender E-Mail: "Diese E-Mail ist bereits registriert. Einloggen?" mit Login-Link
- Events geloggt: `signup_completed`, `result_shown` (20×)

**Zahlt ein auf:** Konversion (Reibung minimieren)

---

### Screen 7: Ergebnisse — Mit Account (20 Karten)

**Was der Nutzer sieht:** Die vollständige Ergebnisliste. Jede Karte ist aufklappbar.

**Karten-Ansicht (zugeklappt):**
- Name + Agentur
- Genre-Tags + Audience
- Match-Tags (✓/~/✗) mit spezifischen Keywords
- Score-Balken (visuell)
- MMR-Rang (#1, #2, ...)

**Aufgeklappte Ansicht:**
- Alle Genres und Keywords als Tags
- Audience
- Submission-Anforderungen (strukturierte Liste)
- Submission-Checkliste (siehe F4)
- "Zuletzt aktualisiert: [Datum]"
- Link zur Originalseite des Agenten (prominent)
- Pflicht-Hinweis: "Bitte prüfe alle Details direkt beim Agenten vor dem Einreichen."

**Akzeptanzkriterien:**
- Aufklappen ist smooth animiert (kein Layout-Jump)
- Link zur Originalseite öffnet in neuem Tab
- Alle Snippets maschinell aus Keywords — nie Originalzitate
- Events geloggt: `card_clicked`, `profile_expanded`, `submission_checklist`, `source_link_clicked`

**Zahlt ein auf:** Engagement, Emotionale Resonanz

---

### Screen 8: One-Click-Feedback (Post-Ergebnis)

**Was der Nutzer sieht:** Nach 60 Sekunden Interaktion mit den Ergebnissen erscheint ein dezentes, nicht-blockierendes Banner am unteren Bildschirmrand.

**Inhalt:**
- "Wie fühlen sich die Ergebnisse an?"
- Zwei Buttons: "🎯 Überraschend gut" / "😐 Nicht was ich erwartet habe"
- Dismiss-Button (X)

**Verhalten:**
- Erscheint nur einmal pro Session
- Verschwindet nach 15 Sekunden automatisch wenn nicht interagiert
- Kein Popup, kein Modal — ein Banner das den Content nicht verdeckt

**Akzeptanzkriterien:**
- Nicht vor 60 Sekunden aktiver Ergebnis-Interaktion
- Maximal 1× pro Session
- Funktioniert auf Mobile und Desktop
- Event: `feedback_positive` oder `feedback_neutral`

**Zahlt ein auf:** Emotionale Resonanz (Messung)

---

## MVP User Journey — Zusammenfassung

```
Landing Page ──→ Conversational Flow (Fragen + Upload) ──→ Loading ──→ 3 Teaser
                                                                          │
                                                               Registrierung (inline)
                                                                          │
                                                              20 Ergebnisse (aufklappbar)
                                                                          │
                                                              One-Click-Feedback (nach 60s)
```

**Gesamtzeit geschätzt:** Landing (10s) → Conversational Input (2–4 min) → Loading (3s) → Teaser (30s) → Registrierung (30s) → Ergebnisse (2–5 min) = **5–10 Minuten** aktive Nutzung.

**Kritischer Moment:** Der Übergang von den 3 Teaser-Karten zur Registrierung. Wenn die 3 Karten spezifisch und relevant wirken, registriert sich der Nutzer. Wenn sie generisch wirken, nicht. Matching-Qualität und Match-Tags-Darstellung entscheiden über die Konversion.

---

## MVP-Features aus Autorensicht

Was ein Autor mit AutoQuery im MVP konkret tun kann — definiert als abgeschlossene Funktionen mit jeweils einem klaren Nutzerversprechen.

---

### F1 — Manuskript beschreiben (Conversational)

**Nutzerversprechen:** "Ich beschreibe mein Buch in einem geführten Gespräch — nicht in einem Formular. Es fühlt sich an wie eine Unterhaltung, nicht wie Bürokratie."

**Was der Autor tut:** Er beantwortet Fragen eine nach der anderen in einer Chat-ähnlichen Oberfläche. Genre und Audience wählt er aus vordefinierten Listen (Dropdowns/Checkboxen). Ton, Themen, Comp Titles tippt er in eigenen Worten. Dann kann er Dateien hochladen (Query Letter, Synopsis, Kapitel-Ausschnitt, Pitch Deck) oder eine kurze Beschreibung tippen. Am Ende optional: spezifische Wünsche.

**Warum es für den Autor wichtig ist:** Ein klassisches Formular mit 7 Feldern auf einem Screen wirkt einschüchternd. Eine Frage nach der anderen fühlt sich machbar an — der Autor konzentriert sich auf genau eine Sache. Gleichzeitig zwingen die Fragen zur Klarheit, was an sich schon wertvoll ist. Comp Titles sind für Autoren die intuitivste Art zu kommunizieren ("Mein Buch ist X meets Y") und das stärkste Signal für das Matching.

**Akzeptanzkriterien:**
- Conversational UI: eine Frage erscheint, Antwort wird bestätigt, nächste Frage erscheint
- Genre + Audience als Dropdown/Checkboxen (keine Freitexteingabe für diese Felder)
- Antworten editierbar nach Bestätigung (Klick auf eigene Antwort)
- Optionale Fragen haben sichtbaren "Überspringen"-Link
- Mindestens ein Query Letter muss vorhanden sein (Upload ODER Freitext)
- Gesamtdauer: 2–4 Minuten
- Funktioniert ohne Login

---

### F2 — Dateien hochladen und kategorisieren

**Nutzerversprechen:** "Ich lade meine fertigen Dokumente hoch und AutoQuery versteht was es damit anfangen soll."

**Was der Autor tut:** Innerhalb des Conversational Flow kann er Dateien hochladen — per Drag & Drop oder Datei-Dialog, auch mehrere gleichzeitig. Pro Datei wählt er den Typ: Query Letter, Synopsis, Manuskript-Ausschnitt, oder Pitch Deck.

**Akzeptierte Formate:** .docx, .txt, .pdf (max. 10 MB pro Datei). MIME-Type serverseitig validiert.

**Warum es für den Autor wichtig ist:** Die meisten Autoren haben ihren Query Letter, ihre Synopsis und Kapitel-Ausschnitte als Dateien vorliegen. Sie wollen nicht alles nochmal abtippen. Der Upload mit Typ-Zuordnung ermöglicht das — und gibt AutoQuery besseres Material für die Embeddings als ein eingeklebter Text in einem Freitextfeld.

**Akzeptanzkriterien:**
- Multi-File-Upload in einem Schritt möglich
- Typ-Zuordnung per Dropdown pro Datei (nicht geraten, nicht automatisch)
- Upload-Fortschrittsanzeige
- Dateiformat + Dateigröße vor Upload geprüft
- Wenn Query Letter hochgeladen: keine separate Freitext-Frage
- Wenn kein Query Letter hochgeladen: Freitext-Frage erscheint (min. 100 Wörter, Pflicht)
- Text-Extraktion serverseitig, Kürzung auf 2000 Wörter pro Dokument

---

### F3 — Personalisierte Agenten-Empfehlungen erhalten

**Nutzerversprechen:** "Ich bekomme eine Liste von Agenten die *genau das* suchen was ich geschrieben habe — nicht einfach alle die 'Fantasy' vertreten."

**Was der Autor bekommt:** Bis zu 20 gerankte Agenten-Empfehlungen. Jeder Treffer wird mit spezifischen Match-Tags erklärt ("✓ Cozy Fantasy · ✓ Found Family · ~ Queer Protagonists"). Ein Score-Balken zeigt die relative Matching-Stärke. Die Ergebnisliste ist diversifiziert — nicht 20× dieselbe Agentur oder dasselbe Profil.

**Warum es für den Autor wichtig ist:** Die Alternative ist manuelles Durchsuchen von QueryTracker, Publishers Marketplace, und Dutzenden Agentur-Websites — ein Prozess der Wochen dauert und trotzdem Lücken hat. AutoQuery komprimiert das auf Sekunden und findet Agenten die der Autor alleine nie gefunden hätte.

**Akzeptanzkriterien:**
- Ergebnisse in < 3 Sekunden nach Absenden
- Match-Tags sind spezifisch für *dieses* Manuskript (nicht generisch)
- Mindestens 1–2 Agenten die der Autor noch nicht kannte (Entdeckungseffekt)
- Keine Hard-Nos-Verletzungen
- Max. 3 Agenten derselben Agentur in den Top-10

---

### F4 — Agenten-Profil verstehen

**Nutzerversprechen:** "Ich sehe auf einen Blick wer dieser Agent ist, was er sucht, und ob es sich lohnt ihn anzuschreiben."

**Was der Autor sieht (aufgeklappte Karte):**
- Name und Agentur
- Genres und Keywords als Tags — die Sprache des Agenten
- Audience (Adult / YA / Middle Grade / Children's)
- Match-Tags die zeigen *warum* dieser Agent passt (✓ exakt / ~ partiell / ✗ kein Match)
- Datum der letzten Aktualisierung
- Direktlink zur Originalseite des Agenten

**Warum es für den Autor wichtig ist:** Autoren haben Angst vor falschen Submissions — jede Absage kostet 6–8 Wochen Wartezeit und emotionale Energie. Die Tags und Match-Indikatoren ermöglichen die Evaluation in Sekunden statt Minuten.

**Akzeptanzkriterien:**
- Aufklappen zeigt alle relevanten Informationen ohne Scrollen (Desktop)
- "Zuletzt aktualisiert"-Datum sichtbar
- Link zur Originalseite prominent, öffnet in neuem Tab
- Pflicht-Hinweis: "Prüfe alle Details direkt beim Agenten vor dem Einreichen"
- Kein Originaltext des Agenten sichtbar — nur Keywords und Fakten

---

### F5 — Submission-Checkliste pro Agent

**Nutzerversprechen:** "Ich weiß sofort was ich für diesen spezifischen Agenten vorbereiten muss — und was mir noch fehlt."

**Was der Autor sieht:**
```
Für Sarah Chen bei Janklow & Nesbit brauchst du:
✅ Query Letter (vorhanden)
❌ Synopsis (nicht vorhanden)
⚠️ Erste 50 Seiten (Kapitel hochgeladen — prüfe Seitenzahl)
○ Autor-Bio (optional)
→ Zur Submission-Seite [Link]
```

**Warum es für den Autor wichtig ist:** Submission-Anforderungen variieren stark zwischen Agenten. Der häufigste Fehler ist falsches oder unvollständiges Submission-Material. Die Checkliste verhindert das und gibt Handlungssicherheit.

**Akzeptanzkriterien:**
- Dynamisch: abgeglichen gegen `submission_req` des Agenten und Uploads des Autors
- ✅ vorhanden, ❌ fehlend, ⚠️ prüfenswert, ○ optional
- Direktlink zur Submission-Seite des Agenten
- Berücksichtigt alle hochgeladenen Dokumenttypen (Query Letter, Synopsis, Ausschnitt)

---

### F6 — Ohne Account testen

**Nutzerversprechen:** "Ich kann AutoQuery ausprobieren ohne meine E-Mail herzugeben — und entscheide selbst ob es sich lohnt."

**Was der Autor bekommt:** Den vollständigen Conversational Flow und die ersten 3 Ergebnisse. Genug um Relevanz zu sehen, nicht genug um darauf zu handeln.

**Warum es für den Autor wichtig ist:** Autoren sind skeptisch gegenüber neuen Tools. Die Möglichkeit zu testen senkt die Schwelle und baut Vertrauen auf. Die Ergebnisse selbst sind der beste Beweis.

**Akzeptanzkriterien:**
- Conversational Flow komplett nutzbar ohne Login
- Uploads funktionieren ohne Account
- 3 Ergebnisse mit Match-Tags sichtbar
- Kein Aufklappen, keine Checkliste ohne Account
- CTA nennt exakte Anzahl der weiteren Ergebnisse
- Registrierung inline, Ergebnisse expandieren sofort

---

### F7 — Daten-Transparenz und Vertrauen

**Nutzerversprechen:** "Ich weiß woher die Daten kommen, wie aktuell sie sind, und dass ich sie selbst verifizieren kann."

**Was der Autor sieht:**
- Auf jedem Profil: "Zuletzt aktualisiert: [Datum]" + Link zur Originalseite
- Pflicht-Hinweis: "Bitte prüfe alle Details direkt beim Agenten vor dem Einreichen."
- Submission-Checkliste verlinkt direkt auf die Submission-Seite

**Warum es für den Autor wichtig ist:** Ein Tool das veraltete Daten zeigt ist schlimmer als kein Tool. Die Transparenz-Elemente signalisieren: "Wir sind eine Startrampe, nicht die letzte Wahrheit."

**Akzeptanzkriterien:**
- Timestamp auf jedem Profil sichtbar
- Link zur Originalseite funktioniert und öffnet in neuem Tab
- Verifikations-Hinweis ist nicht ausblendbar

---

## Explizit NICHT im MVP

| Feature | Warum nicht | Wann |
|---|---|---|
| LLM-Erklärung ("Warum dieser Agent?") | Latenz + Ollama-Last, Wert erst nach Validierung klar | Post-MVP |
| Originaltext-Anzeige im Frontend | Rechtliche Klärung ausstehend | Nach Rechtsberatung |
| Agenten organisieren (Kontaktiert/Abgelehnt/Notiz) | Braucht Wiederkehrer, Engagement erstmal ohne validieren | Sprint 2 |
| Explizites Feedback (1–5 Sterne) | Braucht Mindestmenge Nutzer | Ab ~200 aktive Nutzer |
| Passwort-Reset | Nice-to-have | Sprint 2 |
| Manuskript-Bearbeitung / Versionierung | Erst bei Wiederkehrern relevant | Sprint 2 |
| Fehler-melden-Button | Erst bei aktiver Nutzerbasis | Sprint 2 |
| Priority Re-Crawling | Erst bei Fehlerberichten | Sprint 2 |
| Automatischer monatlicher Re-Crawl | Profile ändern sich selten | Post-MVP |
| Vollmanuskript-Upload | Overkill für MVP, Ausschnitte reichen | Sprint 2 |

---

## Voraussetzungen vor Launch

**Daten:** ≥ 200 genehmigte Agenten-Profile, verteilt über ≥ 5 Genres und ≥ 3 Audience-Kategorien.

**Qualität:** Rückwärtstest gegen ≥ 20 bekannte Agent-Autor-Beziehungen. Precision@10 > 0.5 (weicher als Ziel 0.7, aber MVP-tauglich). Hard-Nos Violation Rate = 0%.

**Infrastruktur:** Opt-Out-Seite live, "Für Agenten"-Seite live, Impressum + Datenschutz live, Analytics konfiguriert, Interaction Logging aktiv.

**Landing Page:** Hallway-Test mit 5 Autoren — versteht der Nutzer in < 10s was AutoQuery tut?

---

## Launch-Strategie

**Soft Launch:** Einladung an 100–200 Autoren aus Writing-Communities (r/PubTips, AbsoluteWrite, Writing Twitter/BlueSky). Kein öffentlicher Launch vor Metrik-Validierung.

**Validierung:** 4 Wochen nach Soft Launch.

**Entscheidungspunkte:**

| Ergebnis | Aktion |
|---|---|
| Alle 3 Metriken erreicht | Öffentlicher Launch + Sprint 2 |
| Konversion schwach, Rest gut | Landing Page + CTA optimieren, 2 Wochen nachtesten |
| Engagement schwach | Matching-Qualität oder Ergebnis-Darstellung überarbeiten |
| Emotion negativ | Grundlegende Matching-Qualität oder Datenbasis hinterfragen |
| Alles verfehlt | Pivot evaluieren |
