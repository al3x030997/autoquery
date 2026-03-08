# Feature 11 — Ergebnis-Anzeige

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Modul H (12.2, 12.3), MVP (1.4.7 Screen 5–7, 1.4.8 F3–F5)

## Scope

Ergebniskarten, Aufklapp-Ansicht, Submission-Checkliste, Match-Tags, Unterschied eingeloggt/nicht-eingeloggt. **MVP-Scope — keine Sprint-2-Features.**

---

## Ohne Konto (3 Teaser)

- 3 Agenten-Karten: Name, Agentur, Genre-Tags, Audience, Match-Tags, Score-Balken
- Kein Aufklappen, keine Checkliste
- CTA: "[N] weitere Agenten gefunden. Erstelle ein kostenloses Konto um alle zu sehen."

## Mit Konto (bis 20 Ergebnisse)

**Karten-Ansicht (zugeklappt):** Name, Agentur, Genre-Tags, Audience, Match-Tags (✓/~/✗), Score-Balken, MMR-Rang

**Aufklappen zeigt:**
- Genres und Keywords als Tags
- Audience
- Submission-Anforderungen (strukturierte Liste)
- Submission-Checkliste (siehe unten)
- **Kein Original-Fließtext**
- "Zuletzt aktualisiert: [Datum]" + Link zur Originalseite
- Pflicht-Hinweis: "Bitte prüfe alle Details direkt beim Agenten vor dem Einreichen."

---

## Match-Tags (serverseitig berechnet)

Pro Ergebnis: 2–3 spezifische Keywords mit Indikator. Beispiel: "✓ Cozy Fantasy · ✓ Character-driven · ~ Queer Protagonists". Nie generisch ("Fantasy-Match"), immer manuskriptspezifisch.

---

## Submission-Checkliste

Pro aufgeklapptem Agent: personalisierte Checkliste basierend auf `submission_req` abgeglichen gegen Autoren-Uploads.

```
Für [Agent Name] bei [Agentur] brauchst du:
✅ Query Letter (vorhanden)
❌ Synopsis (nicht vorhanden)
⚠️ Erste 50 Seiten (Kapitel hochgeladen — prüfe die Seitenzahl)
○ Autor-Bio (optional laut Profil)
→ Direkt zur Submission-Seite des Agenten [Link]
```

---

## Wichtig

- Alle Snippets sind maschinell generiert aus Keywords — nie Originalzitate
- Timestamps + Links zur Originalquelle auf jedem Profil
- Verifikations-Hinweis nicht ausblendbar
