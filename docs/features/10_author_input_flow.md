# Feature 10 — Autor-Input-Flow (Conversational)

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Modul H (12.1, 12.1a), MVP (1.4.7, 1.4.8)
> Für die vollständige Screen-by-Screen-Beschreibung inkl. Akzeptanzkriterien → `00_mvp_definition.md` (Screen 2+3, F1+F2)

## Scope

Technische Implementierungsdetails für den Conversational Input-Flow, Datei-Uploads, Backend-Verarbeitung. Die UX-Spezifikation liegt in `00_mvp_definition.md`.

## Dateien

```
api/routes/
└── matching.py     # Manuscript-Submission-Endpoint
frontend/
└── ...             # Conversational Input-UI
```

---

## Conversational Flow

Chat-ähnliche Oberfläche: eine Frage erscheint, der Autor antwortet, die Antwort wird als Bubble bestätigt, die nächste Frage erscheint. Kein Formular-Grid, kein Stepper.

### Fragensequenz

| # | Frage | Eingabetyp | Pflicht |
|---|---|---|---|
| 1 | "Welches Genre hat dein Buch?" | Dropdown (min. 20 Genres aus `genre_aliases.yaml`), max. 3 auswählbar | Ja |
| 2 | "Wer ist deine Zielgruppe?" | Single-Select: Adult / YA / Middle Grade / Children's | Ja |
| 3 | "Beschreib den Ton deines Buchs in ein paar Worten." | Freitext, max. 200 Zeichen | Ja |
| 4 | "Welche Themen stehen im Zentrum?" | Tag-Input, min. 2, max. 8 | Ja |
| 5 | "Mit welchen Büchern würdest du deins vergleichen?" | Freitext, 2–3 Comp Titles | Ja |
| 6 | "Hast du Dokumente die du hochladen möchtest?" | Upload-Zone (siehe unten) | Nein |
| 7 | "Gibt es sonst noch etwas das uns bei der Suche helfen kann?" | Freitext, max. 300 Zeichen | Nein |

**Konditionale Frage:** Wenn bei Frage 6 kein Query Letter hochgeladen wird, erscheint eine Zusatzfrage: "Dann beschreib dein Buch bitte kurz in eigenen Worten — wie würdest du es einem Agenten pitchen?" (Freitext, min. 100, max. 1000 Wörter, Pflicht).

### UX-Details

- Jede Frage mit kurzer Animation (Einblenden)
- Antworten editierbar nach Bestätigung (Klick auf eigene Bubble)
- Optionale Fragen haben sichtbaren "Überspringen"-Link
- Fortschrittsindikator als dezente Punkte (nicht "Schritt 3 von 7")
- Nach letzter Frage: CTA "Matching starten"
- Alle Eingaben im Browser zwischengespeichert (Session, kein Verlust bei Reload)
- Funktioniert komplett ohne Login

---

## Datei-Uploads

Erscheinen als Upload-Zone innerhalb des Conversational Flow (Frage 6).

### Akzeptierte Dokumenttypen

| Typ | Formate | Max. Größe | Zweck |
|---|---|---|---|
| Query Letter | .docx, .txt, .pdf | 10 MB | Kerntext für Matching |
| Synopsis | .docx, .txt, .pdf | 10 MB | Thematische Tiefe |
| Manuskript-Ausschnitt | .docx, .txt, .pdf | 10 MB | Stimme und Stil |
| Pitch Deck / One-Pager | .pdf, .docx | 10 MB | Für pitching-ready Autoren |

### Upload-Verhalten

- Multi-Upload: Drag & Drop oder Datei-Dialog, mehrere Dateien gleichzeitig
- Typ-Zuordnung: Dropdown pro Datei (nicht automatisch geraten)
- Upload-Fortschrittsanzeige pro Datei
- Nach Upload: Dateiname + Typ + Häkchen in Chat-Bubble
- Serverseitig: MIME-Type-Validierung, Text-Extraktion, Kürzung auf max. 2000 Wörter pro Dokument
- Dateiname sanitizen

### Query-Letter-Logik

Mindestens ein Query Letter muss vorhanden sein:
- Option A: Query Letter als Datei hochgeladen → keine Freitext-Frage
- Option B: Kein Upload → Freitext-Frage (min. 100 Wörter, Pflicht)

---

## Manuskript-Bearbeitung & Versionierung (Post-MVP / Sprint 2)

- Bei Bearbeitung: neuer `manuscripts`-Eintrag (kein In-Place-Update)
- Alter Eintrag bleibt mit bisherigen `matching_results` verknüpft
- Alte Ergebnisse: Markierung "Basiert auf früherer Version"
- CASCADE-Löschung möglich
