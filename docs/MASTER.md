# AutoQuery — Technischer Anforderungskatalog
**Version:** 5.7  
**Status:** Bereit zur Implementierung  
**Änderungen gegenüber v5.5:** MVP-Kapitel hinzugefügt (1.4) — drei Erfolgsmetriken (Visit-to-Signup ≥ 10%, Engagement ≥ 60s, emotionale Resonanz), Feature-Scope abgeleitet aus Metriken, explizite Nicht-MVP-Liste, Launch-Voraussetzungen (min. 200 Profile, Precision@10 > 0.5), Soft-Launch-Strategie mit 4-Wochen-Validierungszyklus.

---

## Inhaltsverzeichnis
1. [Projektübersicht](#1-projektübersicht)
   - 1.4 [MVP-Definition: Ziele, Metriken und Scope](#14-mvp-definition-ziele-metriken-und-scope)
2. [Matching-Architektur: Philosophie & Phasen](#2-matching-architektur-philosophie--phasen)
3. [Systemarchitektur & Projektstruktur](#3-systemarchitektur--projektstruktur)
4. [Technologie-Stack](#4-technologie-stack)
5. [Modul A: Crawling & Klassifikation](#5-modul-a-crawling--klassifikation)
6. [Modul B: LLM-Extraktion & Review](#6-modul-b-llm-extraktion--review)
7. [Modul C: Datenbank & Datenmodell](#7-modul-c-datenbank--datenmodell)
8. [Modul D: Embedding-Pipeline](#8-modul-d-embedding-pipeline)
9. [Modul E: Matching-Algorithmus (Phase 1)](#9-modul-e-matching-algorithmus-phase-1)
10. [Modul F: Interaction Logging & Feedback](#10-modul-f-interaction-logging--feedback)
11. [Modul G: Matching-Qualitätskriterien](#11-modul-g-matching-qualitätskriterien)
12. [Modul H: Autor-Input & Interface](#12-modul-h-autor-input--interface)
13. [Modul I: Nutzer & Authentifizierung](#13-modul-i-nutzer--authentifizierung)
14. [Modul J: Datenpflege & Aktualisierung](#14-modul-j-datenpflege--aktualisierung)
15. [Modul K: Datenschutz & DSGVO](#15-modul-k-datenschutz--dsgvo)
16. [Modul L: Rechtliche Compliance](#16-modul-l-rechtliche-compliance)
17. [Nicht-funktionale Anforderungen](#17-nicht-funktionale-anforderungen)
18. [Roadmap: Phase 2 & 3](#18-roadmap-phase-2--3)
19. [Offene Entscheidungen für den Entwickler](#19-offene-entscheidungen-für-den-entwickler)

---

## 1. Projektübersicht

### 1.1 Ziel
AutoQuery ist eine öffentliche Web-Plattform die Buchautoren dabei hilft, passende Literaturagenten zu finden. Das System crawlt Agenturen-Webseiten direkt, extrahiert strukturierte Profile, und matcht diese gegen das Manuskript-Profil eines Autors — mit einem Algorithmus der mit wachsenden Nutzerdaten kontinuierlich besser wird.

### 1.2 Zwei Kernstufen

**Stufe 1 — Agenten-Datenbank:** Agentur-Websites werden direkt gecrawlt (Direct-to-Source, nie Aggregatoren). Fakten, maschinell extrahierte Keywords, und Originaltexte (Wishlist, Bio, Hard-Nos) werden persistent gespeichert. Originaltexte werden intern für Embedding-Qualität und Review genutzt, aber im Frontend **nie angezeigt** (Store More, Show Less). Profile werden manuell geprüft und monatlich aktualisiert.

**Stufe 2 — Manuskript-Matching:** Ein Autor durchläuft ein geführtes Formular und erhält ein geranktes, erklärbares Matching. Der Algorithmus startet als regelbasiertes Content-based Filtering und entwickelt sich mit wachsenden Interaktionsdaten zu einem trainierten ML-Modell.

### 1.3 Abgrenzung MVP
Kein automatisches Erstellen von Query Letters oder Synopsen, keine Community-Features, keine direkte Kontaktaufnahme über die Plattform, nur englischsprachige Agenturen, keine Aggregatoren (MSWL, QueryTracker, PublishersMarketplace — nie).

### 1.4 MVP-Definition: Ziele, Metriken und Scope

#### 1.4.1 Was der MVP beweisen soll

Der MVP ist kein Feature-Showcase — er ist ein Hypothesentest. Drei Hypothesen müssen validiert werden bevor weitere Entwicklung gerechtfertigt ist:

**Hypothese 1 — Konversion:** Buchautoren die AutoQuery besuchen erkennen innerhalb von Sekunden dass die Plattform ein echtes Problem für sie löst. Sie registrieren sich um die vollen Ergebnisse zu sehen.

**Hypothese 2 — Engagement:** Ein Autor der das Matching durchläuft bleibt aktiv dabei — er liest die Ergebnisse, klickt Profile auf, prüft Submission-Anforderungen. Die Ergebnisse sind relevant genug um echte Interaktion auszulösen.

**Hypothese 3 — Emotionale Resonanz:** Die Erfahrung erzeugt Freude und Neugier — das Gefühl "endlich versteht mich etwas", nicht "das hätte ich auch selbst googeln können". Die Ergebnisse fühlen sich persönlich an, nicht generisch.

#### 1.4.2 Erfolgsmetriken

| Metrik | Ziel | Messung | Fail-Kriterium |
|---|---|---|---|
| Visit-to-Signup Rate | ≥ 10% | Unique Visitors vs. abgeschlossene Registrierungen (Analytics + DB) | < 5% nach 4 Wochen |
| Aktives Engagement bei Erstnutzung | ≥ 60 Sekunden | Zeit zwischen erstem Formular-Input und letzter Interaktion mit Ergebnissen (Interaction Events) | < 30 Sekunden Median |
| Emotional Response | Freude + Neugier | Qualitative Interviews (10–15 Nutzer) + optionaler One-Click-Feedback nach Ergebnissen ("Hat dich das überrascht?" Ja/Nein) | Überwiegend negatives oder gleichgültiges Feedback |

Die quantitativen Metriken (Konversion, Engagement) werden automatisch gemessen. Die emotionale Resonanz wird in der MVP-Phase qualitativ über Nutzerinterviews erhoben — ein quantitativer Proxy wird erst nach ausreichend Daten definiert.

#### 1.4.3 Was im MVP enthalten sein muss

Die Minimalanforderung ergibt sich direkt aus den drei Hypothesen — jedes Feature muss auf mindestens eine Metrik einzahlen.

**Für Konversion (Visit → Signup):**

Die Landing Page muss in unter 5 Sekunden kommunizieren: "Du beschreibst dein Manuskript, wir finden die Agenten die genau das suchen." Kein Feature-Dump, keine lange Erklärung. Der Nutzer muss sofort den Conversational Flow starten können — ohne Registrierung. Die 3 Teaser-Ergebnisse (ohne Account) müssen überzeugend genug sein, dass der Nutzer die restlichen 17 sehen will.

Enthält: Landing Page, Conversational Input-Flow (ohne Login), Ergebnis-Anzeige (3 Karten ohne Account), Registrierung (E-Mail + Passwort), Ergebnis-Anzeige (20 Karten mit Account).

**Für Engagement (≥ 60s aktive Nutzung):**

Der Conversational Flow selbst ist ein Engagement-Treiber — Autoren investieren gerne 2–3 Minuten um ihr Manuskript zu beschreiben, wenn die Fragen sich wie ein Gespräch anfühlen. Die Ergebnis-Seite muss zum Aufklappen und Weiterlesen einladen: Match-Tags (✓/~/✗) erzeugen Neugier, Submission-Checklisten machen die nächsten Schritte greifbar, der Score-Balken lädt zum Vergleichen ein.

Enthält: Conversational Flow (7 Fragen), Datei-Uploads (Query Letter, Synopsis, Ausschnitt, Pitch Deck), aufklappbare Agenten-Profile, Match-Tags, Submission-Checkliste, Interaction Logging (ab Tag 1).

**Für Freude und Neugier:**

Freude entsteht wenn die Ergebnisse sich anfühlen wie eine Empfehlung von jemandem der das Buch gelesen hat — nicht wie ein Keyword-Filter. Das erfordert: Matching-Qualität die über Genre-Match hinausgeht (semantische Ähnlichkeit, Comp-Title-Matching, Query Expansion), Erklärbarkeit die spezifisch ist ("Sucht: Cozy Fantasy · Found Family · Queer Protagonists" statt "Fantasy-Match"), und das Gefühl der Entdeckung — mindestens 1–2 Agenten in den Ergebnissen die der Autor noch nicht kannte.

Enthält: Alle 4 Scoring-Signale (Genre, Audience, FTS, Semantic), Query Expansion, Match-Tags mit spezifischen Keywords, MMR-Diversifizierung (verhindert generische Ergebnislisten).

#### 1.4.4 Was im MVP explizit nicht enthalten ist

Nicht im MVP enthalten — aber die Architektur muss es ermöglichen:

| Feature | Warum nicht im MVP | Wann |
|---|---|---|
| LLM-Erklärung per Klick ("Warum dieser Agent?") | Erhöht Latenz + Ollama-Abhängigkeit, Wert erst mit validierten Matchings klar | Post-MVP, wenn Matching-Qualität bestätigt |
| Originaltext-Anzeige im Frontend | Rechtliche Klärung ausstehend (Store More, Show Less) | Nach medienrechtlicher Beratung |
| Agenten organisieren (Kontaktiert/Abgelehnt/Notiz) | Braucht Wiederkehrer, Engagement erstmal ohne validieren | Sprint 2 |
| Explizites Feedback (1–5 Sterne) | Braucht Mindestmenge aktiver Nutzer um statistisch relevant zu sein | Ab ~200 aktive Nutzer |
| Passwort-Reset via E-Mail | Nice-to-have, nicht konversionsrelevant | Sprint 2 |
| Manuskript-Bearbeitung / Versionierung | Erst relevant wenn Nutzer wiederkommen | Sprint 2 |
| Fehler-melden-Button | Erst relevant bei aktiver Nutzerbasis | Sprint 2 |
| Priority Re-Crawling | Erst relevant bei Fehlerberichten | Sprint 2 |
| Monatlicher automatischer Re-Crawl | Agenten-Profile ändern sich selten — manueller Re-Crawl reicht für MVP | Post-MVP |
| Vollmanuskript-Upload | Overkill für MVP, Ausschnitte reichen | Sprint 2 |

#### 1.4.5 MVP-Voraussetzungen (vor Launch)

Bevor der MVP live geht, müssen folgende Bedingungen erfüllt sein:

**Daten:** Mindestens 200 genehmigte Agenten-Profile in der Datenbank, verteilt über mindestens 5 Genres und 3 Audience-Kategorien. Ohne ausreichende Datenbasis produziert selbst ein perfekter Algorithmus schlechte Ergebnisse — und ein Autor der bei seiner ersten Nutzung nur 2 irrelevante Ergebnisse bekommt, kommt nicht wieder.

**Qualität:** Matching wurde gegen mindestens 20 bekannte Agent-Autor-Beziehungen getestet (Rückwärtstest aus Danksagungen). Precision@10 muss > 0.5 sein (weicher als das langfristige Ziel von 0.7, aber ausreichend für MVP-Validierung). Hard-Nos Violation Rate = 0%.

**Infrastruktur:** Opt-Out-Seite und "Für Agenten"-Seite live, Impressum und Datenschutzerklärung live, Analytics-Tracking für die drei Metriken konfiguriert, Interaction Logging aktiv.

**Landing Page:** Getestet mit 5 Autoren (Hallway-Test): Versteht der Nutzer in unter 10 Sekunden was AutoQuery tut und warum es für ihn relevant ist?

#### 1.4.6 MVP-Zeitleiste und Validierungszyklus

**Launch:** Soft Launch mit Einladung an 100–200 Autoren aus Writing-Communities (z.B. r/PubTips, AbsoluteWrite, Writing Twitter/BlueSky). Kein öffentlicher Launch bevor die Metriken validiert sind.

**Validierungszeitraum:** 4 Wochen nach Soft Launch.

**Entscheidungspunkte nach 4 Wochen:**

| Ergebnis | Aktion |
|---|---|
| Alle 3 Metriken erreicht | Öffentlicher Launch, Sprint 2 starten |
| Konversion < 10% aber Engagement + Emotion gut | Landing Page und CTA optimieren, 2 weitere Wochen testen |
| Engagement < 60s | Matching-Qualität oder Ergebnis-Darstellung überarbeiten |
| Emotion negativ | Grundsätzliche Matching-Qualität hinterfragen — möglicherweise Datenbasis zu dünn |
| Alle 3 Metriken verfehlt | Pivot oder grundlegende Neuausrichtung evaluieren |

#### 1.4.7 MVP User Journey — Screen für Screen

Die MVP-Funktionen für den Nutzer sind als lineare Journey definiert. Jeder Screen hat Akzeptanzkriterien und zahlt auf mindestens eine der drei Metriken ein.

**Screen 1 — Landing Page:** Headline ("Finde den Agenten, der genau dein Buch sucht"), Subtext, CTA "Matching starten". Kein Login nötig. Dreischritt-Explainer. Links zu "Für Agenten", Impressum, Datenschutz. Seite lädt in < 2s. CTA above the fold. → Zahlt auf Konversion ein.

**Screen 2 — Conversational Input (Fragenkatalog):** Chat-ähnliche Oberfläche, eine Frage nach der anderen. 7 Fragen: (1) Genre — Dropdown, max. 3, Pflicht. (2) Audience — Single-Select (Adult/YA/MG/Children's), Pflicht. (3) Ton — Freitext max. 200 Zeichen, Pflicht. (4) Themen — Tags min. 2 max. 8, Pflicht. (5) Comp Titles — Freitext 2–3 Titel, Pflicht. (6) Datei-Uploads — optional, siehe Screen 3. (7) Sonstige Wünsche — Freitext max. 300 Zeichen, optional. Antworten editierbar nach Bestätigung. Optionale Fragen überspringbar. Gesamtdauer: 2–4 Minuten. → Zahlt auf Engagement + Emotionale Resonanz ein.

**Screen 3 — Upload-Zone (innerhalb Conversational Flow):** Multi-Upload per Drag & Drop. Akzeptierte Typen: Query Letter, Synopsis, Manuskript-Ausschnitt, Pitch Deck (.docx/.txt/.pdf, max. 10 MB). Typ-Zuordnung per Dropdown pro Datei. MIME-Type serverseitig validiert. Text auf 2000 Wörter/Dokument gekürzt. Wenn kein Query Letter hochgeladen: Freitext-Frage (min. 100 Wörter, Pflicht). Mindestens ein Query Letter muss vorhanden sein (Upload oder Freitext). → Zahlt auf Matching-Qualität ein.

**Screen 4 — Loading:** Animierter Fortschrittsindikator. Textfeedback ("Analysiere dein Manuskript...", "Durchsuche 247 Agenten-Profile..."). Ziel: < 3 Sekunden. Bei Fehler: Meldung + "Nochmal versuchen". → Zahlt auf Emotionale Resonanz ein.

**Screen 5 — Ergebnisse ohne Account (3 Teaser):** 3 Karten: Name, Agentur, Genre-Tags, Audience, Match-Tags (2–3 spezifische Keywords), Score-Balken. Kein Aufklappen. CTA: "17 weitere Agenten gefunden. Erstelle ein kostenloses Konto um alle zu sehen." Exakte Anzahl. → Zahlt auf Konversion ein (kritischer Moment).

**Screen 6 — Registrierung (inline):** E-Mail + Passwort + Datenschutz-Checkbox. Inline auf Ergebnis-Seite. Nach Registrierung: sofort eingeloggt, 3 → 20 Karten. Kein Seitenwechsel. E-Mail-Verifizierung im Hintergrund. → Zahlt auf Konversion ein.

**Screen 7 — Ergebnisse mit Account (20 Karten):** Karten aufklappbar. Aufgeklappt: Keywords als Tags, Submission-Anforderungen, personalisierte Submission-Checkliste, "Zuletzt aktualisiert" + Link zur Originalseite + Pflicht-Hinweis. Alle Snippets maschinell aus Keywords. Events für jede Interaktion. → Zahlt auf Engagement + Emotionale Resonanz ein.

**Screen 8 — One-Click-Feedback:** Banner nach 60s: "Wie fühlen sich die Ergebnisse an?" — "🎯 Überraschend gut" / "😐 Nicht was ich erwartet habe". 1× pro Session, verschwindet nach 15s. → Zahlt auf Messung der Emotionalen Resonanz ein.

#### 1.4.8 MVP-Features aus Autorensicht

7 Features definieren was der Autor mit AutoQuery tun kann — jeweils mit Nutzerversprechen und Akzeptanzkriterien. Vollständige Dokumentation in Feature 00.

**F1 — Manuskript beschreiben (Conversational):** Geführtes Gespräch statt Formular. Genre + Audience als Dropdown, Rest als Freitext. Fühlt sich an wie eine Unterhaltung, nicht wie Bürokratie.

**F2 — Dateien hochladen und kategorisieren:** Query Letter, Synopsis, Kapitel-Ausschnitt, Pitch Deck. Multi-Upload mit Typ-Zuordnung. Wenn kein Query Letter als Datei: Freitext-Pflicht.

**F3 — Personalisierte Agenten-Empfehlungen:** Bis 20 gerankte Treffer mit spezifischen Match-Tags. Diversifiziert, keine Hard-Nos-Verletzungen, max. 3 pro Agentur in Top-10.

**F4 — Agenten-Profil verstehen:** Aufklappbar, Keywords als Tags, Match-Indikatoren (✓/~/✗), Timestamp, Direktlink zur Originalseite.

**F5 — Submission-Checkliste pro Agent:** Dynamisch abgeglichen gegen Agenten-Anforderungen und Autoren-Uploads. ✅/❌/⚠️/○ mit Link zur Submission-Seite.

**F6 — Ohne Account testen:** Vollständiger Flow bis 3 Teaser-Ergebnisse. Inline-Registrierung mit sofortiger Expansion auf 20 Karten.

**F7 — Daten-Transparenz:** Timestamp, Quellenlink, Verifikations-Hinweis auf jedem Profil.

**Gesamtzeit geschätzt:** Landing (10s) → Conversational Input (2–4 min) → Loading (3s) → Teaser (30s) → Registrierung (30s) → Ergebnisse (2–5 min) = 5–10 Minuten aktive Nutzung.

**Kritischer Moment:** Der Übergang von den 3 Teaser-Karten zur Registrierung. Matching-Qualität und Match-Tags-Darstellung entscheiden über die Konversion.

---

## 2. Matching-Architektur: Philosophie & Phasen

### 2.1 Das eigentliche Problem

Literaturagenten-Matching ist kein klassisches Retrieval-Problem. Es ist ein Kompatibilitäts-Problem mit binärem Ground Truth: Entweder würde ein Agent ein Manuskript vertreten wollen — oder nicht. Die objektiv beste Lösung für dieses Problem ist ein trainiertes Modell auf echten Interaktionsdaten — konkret ein Fine-Tuned Late-Interaction-Modell (ColBERTv2) oder ein auf domänenspezifischen Daten nachtrainierter Bi-Encoder (Augmented SBERT). Dieses Modell lernt aus echten Matches welche Features tatsächlich predictiv sind — nicht was wir theoretisch für wichtig halten.

### 2.2 Warum wir damit nicht starten können: Cold Start

Zum Launch existieren keine Trainingsdaten. Es gibt keine Daten über tatsächliche Matches oder Ablehnungen, keine Interaktionshistorie, und Submission-Ergebnisse sind private Informationen die wir nie systematisch sammeln können. Ohne Trainingsdaten ist ein supervised Modell nicht möglich.

### 2.3 Die dreiphasige Strategie

Die etablierte Lösung für Cold Start in Recommender Systems ist eine schrittweise Architektur. Entscheidend ist dass die gesamte Pipeline über alle Phasen identisch bleibt — nur die Scoring-Funktion wird ausgetauscht. Die Dateninfrastruktur für Phase 2 und 3 muss deshalb von Anfang an mitgebaut werden.

**Phase 1 — Cold Start (Launch bis ~500 Interaktionen):** Content-based Filtering auf strukturierten Features (Genre, Audience, Keywords) mit Embedding-Similarity als Feinabstimmung. Parallel werden alle Nutzerinteraktionen geloggt.

**Phase 2 — Supervised Learning (~500–10.000 Interaktionen):** LightGBM oder XGBoost trainiert auf den geloggten Interaktionsdaten. Das Modell lernt welche der Phase-1-Features tatsächlich predictiv sind.

**Phase 3 — Fine-Tuned Late Interaction / Augmented SBERT (ab ~10.000 Interaktionen):** ColBERTv2 für token-granulares asymmetrisches Matching oder Augmented SBERT für domänenspezifisches Fine-Tuning des Bi-Encoders. State of the Art für textbasiertes Matching bei kleinem Korpus.

---

## 3. Systemarchitektur & Projektstruktur

### 3.1 Komponenten

Das System besteht aus fünf Hauptbereichen: Admin-Bereich (Crawling, Extraktion, Review), Datenbank (PostgreSQL + pgvector), Backend API (FastAPI), Frontend (Next.js), und Interaction Logger. Die Datenbank enthält Fakten, Keywords, Embedding-Vektoren und intern gespeicherte Originaltexte (Wishlist, Bio, Hard-Nos). Originaltexte werden im Frontend **nie angezeigt** — nur Keywords und Fakten sind öffentlich sichtbar.

### 3.2 Verzeichnisstruktur

```
autoquery/
├── crawler/
│   ├── seed_list.yaml
│   ├── blacklist.yaml
│   ├── page_classifier.py
│   ├── crawler_engine.py
│   └── content_extractor.py
├── extractor/
│   ├── profile_extractor.py
│   ├── embedding_builder.py
│   └── prompts.py
├── matching/
│   ├── phase1/
│   │   ├── query_expander.py
│   │   ├── filter.py
│   │   ├── scorer.py
│   │   └── reranker.py
│   ├── phase2/
│   │   └── README.md
│   └── phase3/
│       └── README.md
├── logging/
│   └── interaction_logger.py
├── database/
│   ├── models.py
│   ├── migrations/
│   └── db.py
├── embeddings/
│   ├── model.py
│   └── pipeline.py
├── review/
│   └── app.py
├── api/
│   ├── main.py
│   ├── routes/
│   └── schemas.py
├── tasks/
│   └── crawler_tasks.py
├── frontend/
└── docker-compose.yml
```

Die `phase2/` und `phase3/` Verzeichnisse werden jetzt angelegt aber bleiben zunächst leer. Ihre README-Dateien dokumentieren wann und wie die jeweilige Phase aktiviert wird.

---

## 4. Technologie-Stack

| Komponente | Technologie | Begründung |
|---|---|---|
| Sprache | Python 3.11+ | — |
| API | FastAPI | — |
| Datenbank | PostgreSQL 15+ mit pgvector | Vektorsuche nativ integriert |
| LLM (lokal) | Ollama, Modell: llama3 | Kein externer API-Aufruf, konfigurierbar |
| Embedding | BAAI/bge-large-en-v1.5 | Stärkstes open-source Modell auf MTEB STS, asymmetrisches Matching via Instruction Prefix, 1024d, lokal betreibbar |
| Crawler | Playwright + BeautifulSoup4 | JavaScript-Rendering für dynamische Seiten |
| Review | Streamlit | Schnelle Admin-UI ohne separates Frontend |
| Task Queue | Celery + Redis | Monatliche Crawls + Priority-Queue |
| Auth | JWT | — |
| Frontend | Next.js | SSR für SEO, empfohlen |
| Container | Docker + Docker Compose | Vollständig lokal betreibbar |
| Phase 2 (vorbereitet) | LightGBM / XGBoost | — |
| Phase 3 (vorbereitet) | ColBERTv2 / PyTorch | Late Interaction für asymmetrisches Matching |

### 4.1 Ollama Health-Check & Graceful Degradation

Ollama ist eine zentrale Abhängigkeit für vier Komponenten: Page Classifier (5.14), Profil-Extraktion (6.3), Query Expansion (8.4), und LLM-Erklärungen (9.5). Ein Docker Health-Check pingt den Ollama-Endpunkt alle 5 Minuten. Bei Ausfall:

| Komponente | Auswirkung bei Ollama-Ausfall | Verhalten |
|---|---|---|
| Matching (Schicht 1–3) | Keine — läuft ohne LLM | Normal |
| Query Expansion | Gecachte Expansion wird verwendet falls vorhanden, sonst wird nur das Volltext-Embedding genutzt (100% Gewicht statt 70/30) | Degraded, funktional |
| LLM-Erklärungen | Button wird ausgeblendet | Degraded, funktional |
| Crawling & Extraktion | Blockiert — kein neuer Crawl möglich | Blockiert, Alert an Admin |
| Page Classifier | Blockiert — keine Klassifikation möglich | Blockiert, Alert an Admin |

Bei Ausfall wird der Admin sofort per Alert benachrichtigt (siehe 17.1). Das Matching und die Ergebnis-Anzeige funktionieren uneingeschränkt weiter — nur die Daten-Pipeline ist betroffen.

---

## 5. Modul A: Crawling & Klassifikation

### 5.1 Direct-to-Source Prinzip

AutoQuery crawlt ausschließlich individuelle Agentur-Websites direkt. Aggregatoren (MSWL, QueryTracker, PublishersMarketplace u.a.) werden nie gecrawlt — sie sind in `blacklist.yaml` eingetragen und müssen vor jedem Crawl-Request technisch geprüft werden. Ein Verstoß wirft eine Exception und wird geloggt. Manuelles Nachschlagen von Agentur-Domains über Aggregatoren durch den Admin ist erlaubt.

### 5.2 Admin-Input: Wie Domains in die Datenbank kommen

Der Admin ist die einzige Person die neue Agentur-Domains einträgt. Es gibt zwei gleichwertige Input-Formate — beide sind im Streamlit Admin-Interface verfügbar.

**Format 1 — Direkte URL-Eingabe:** Der Admin gibt eine einzelne Domain oder URL ein (z.B. `janklow.com` oder `https://janklow.com/agents`) zusammen mit Name und Land der Agentur. Das System normalisiert auf die Root-Domain, prüft gegen Blacklist und bestehende Einträge, und legt den Eintrag an.

**Format 2 — CSV-Upload:** Für Bulk-Imports. Das CSV-Format hat die Pflichtfelder `domain`, `name`, `country` und das optionale Feld `notes`. Das System validiert jede Zeile einzeln, zeigt eine Vorschau mit Validierungsergebnis pro Zeile (gültig / bereits vorhanden / in Blacklist / ungültiges Format), und importiert nach Admin-Bestätigung. Fehlerhafte Zeilen werden übersprungen und im Log ausgewiesen — der Import bricht nicht ab.

Beispiel CSV-Format:
```
domain,name,country,notes
janklow.com,Janklow & Nesbit,US,
inkwellmanagement.com,InkWell Management,US,speculative fiction focus
```

Beide Formate schreiben in dieselbe `seed_list.yaml`. Hinzufügedatum und Admin-Name werden automatisch eingetragen. Die `blacklist.yaml` enthält gesperrte Domains mit Begründung — Aggregatoren sowie Domains aus Opt-Out-Requests. Beide Dateien liegen im Repository und sind versioniert.

**Post-MVP — Nutzer-Vorschläge:** Autoren sollen später über das Frontend Agenturen vorschlagen können. Die Dateninfrastruktur dafür wird jetzt als Stub angelegt aber nicht aktiviert.

**Schema `suggested_domains` (Stub — nicht im MVP-Frontend exponiert):**

Felder: id, domain (TEXT NOT NULL), suggested\_by (FK → users, SET NULL), agency\_name (TEXT), country (TEXT), notes (TEXT), status (pending\_review / accepted / rejected, DEFAULT 'pending\_review'), reviewed\_by (TEXT), reviewed\_at (TIMESTAMP), created\_at (TIMESTAMP DEFAULT NOW()).

Bei Aktivierung im Post-MVP: Frontend-Formular für eingeloggte Nutzer, Admin-Ansicht im Streamlit-Interface, bei Acceptance wird die Domain automatisch in `seed_list.yaml` eingetragen und der Browser-Agent ausgelöst.

### 5.3 Erstcrawl-Strategie: Schlanker Browser-Agent via Claude API

Der Erstcrawl einer neuen Domain — wenn die Struktur der Website noch unbekannt ist — wird nicht mit blindem BFS-Crawling durchgeführt, sondern mit einem schlanken Browser-Agenten der direkt auf der Claude API aufbaut. Dieser Agent wird einmalig pro Domain ausgeführt und identifiziert gezielt welche URLs die relevanten Agenten-Profile enthalten. Danach übernimmt der Standard-Crawl-Prozess (Abschnitt 5.4 ff.) für alle zukünftigen Re-Crawls.

**Warum kein fertiges Tool (OpenClaw etc.):** Fertige Agent-Frameworks sind für 24/7-Automation designed, nicht für strukturierte Einmal-Batch-Jobs. Wir würden ein Tool zweckentfremden und hätten keine Kontrolle über Prompts, Fehlerbehandlung, und Quality Gate Integration. Der Eigenaufwand für einen schlanken Agenten ist überschaubar und das Ergebnis ist direkt in die bestehende Pipeline integrierbar.

**Architektur des Browser-Agenten:**

Der Agent besteht aus drei Komponenten: Playwright übernimmt die Browser-Steuerung (Seiten laden, JavaScript rendern, Screenshots erstellen). Claude Haiku 4.5 über die Anthropic API trifft Navigations-Entscheidungen und extrahiert Profil-URLs. Ein einfacher Zustandsautomat koordiniert die Schleife aus "Screenshot aufnehmen → Claude entscheiden → Aktion ausführen".

Der Agent arbeitet in zwei Phasen:

**Phase 1 — Exploration (Claude entscheidet):** Der Agent startet auf der Agentur-Homepage, macht einen Screenshot, und fragt Claude: "Wo auf dieser Seite finde ich eine Liste von Agenten oder deren individuelle Profile? Nenne die relevante URL oder beschreibe wo ich klicken soll." Claude antwortet mit einer konkreten Aktion (URL navigieren, Element klicken, scrollen). Das wiederholt sich bis die Agenten-Übersichtsseite und mindestens ein Einzel-Profil gefunden sind. Maximale Tiefe: 5 Navigationsschritte pro Domain.

**Phase 2 — Profil-URL-Extraktion:** Sobald eine Agenten-Übersichtsseite identifiziert ist, extrahiert Claude alle Links zu Einzel-Profilen. Diese URLs werden als "bekannte Profil-URLs" für diese Domain gespeichert — sie sind der Input für alle zukünftigen Standard-Crawls.

Das Ergebnis des Erstcrawls ist keine extrahierte Datenbank, sondern eine verifizierte URL-Liste pro Domain. Die eigentliche Profil-Extraktion übernimmt danach der LLM-Extraktor aus Modul B — wie bei allen anderen Crawls auch.

**Abgrenzung Erstcrawl vs. Re-Crawl:** Der Browser-Agent läuft ausschließlich bei der Erstaufnahme einer neuen Domain — er ist kein Teil des monatlichen Crawl-Zyklus. Monatliche Re-Crawls lesen ausschließlich aus `known_profile_urls` und fetchen nur die dort hinterlegten URLs direkt. Sitemap-Discovery und BFS kommen beim Re-Crawl nicht zum Einsatz. Einzige Ausnahme: Wenn ein Admin eine bestehende Domain explizit zum erneuten Erstcrawl freigibt (z.B. nach einem kompletten Website-Relaunch), wird der Browser-Agent erneut ausgeführt und `known_profile_urls` für diese Domain vollständig ersetzt.

**Modell-Wahl: Claude Haiku 4.5**

Für Navigations-Entscheidungen reicht Haiku vollständig aus — die Aufgaben sind klar definiert ("Wo ist die Agenten-Liste?", "Welche Links führen zu Profilen?") und erfordern keine komplexe Reasoning-Kapazität. Haiku ist dabei 3× günstiger als Sonnet.

**Kostenschätzung Erstcrawl (Stand März 2026, Haiku 4.5: $1/MTok Input, $5/MTok Output):**

Pro Agent realistisch 5 Navigationsschritte + 1 Extraktions-Call, je ~1.500 Token Input + 400 Token Output:

| | Berechnung | Kosten |
|---|---|---|
| 500 Agenten × 6 Calls × 1.500 Token Input | 4,5 MTok | $4.50 |
| 500 Agenten × 6 Calls × 400 Token Output | 1,2 MTok | $6.00 |
| **Gesamt Erstcrawl 500 Agenten** | | **~$10–15** |

Puffer für schwierige Seiten (mehr Navigationsschritte, Retries): +50% → **realistisches Budget: $15–20 einmalig**.

Falls für einzelne besonders komplexe Domains auf Sonnet 4.6 ($3/$15 per MTok) eskaliert werden muss: +$5–10 für die schwierigsten ~20 Domains.

**Abbruch-Kriterien:** Der Agent bricht ab wenn nach 5 Navigationsschritten keine Agenten-Seite gefunden wurde (→ Domain als `needs_manual_review` markieren), wenn eine Login-Wall erkannt wird, oder wenn ein Captcha auftaucht. In all diesen Fällen wird der Admin notifiziert.

**Integration in bestehende Pipeline:**

Der Browser-Agent ist ein separates Script (`crawler/browser_agent.py`) das vom Admin manuell für neue Domains ausgelöst wird — nicht Teil des monatlichen Celery-Crawl-Zyklus. Ergebnis wird in einer neuen Tabelle `known_profile_urls` gespeichert: domain, url, discovered_at, discovery_method ('browser_agent'). Der monatliche Re-Crawl liest aus dieser Tabelle statt BFS zu nutzen.

### 5.4 Crawl-Reihenfolge pro Domain (nur Erstcrawl-Fallback)

Für Domains bei denen der Browser-Agent (5.3) nicht eingesetzt wird oder fehlschlägt, gilt als Fallback folgende Reihenfolge: robots.txt abrufen und für den Run cachen, dann Sitemap-Discovery als primäre URL-Quelle, bei fehlender Sitemap BFS-Crawling als Fallback. Jede einzelne Seite durchläuft vor dem Fetch: Blacklist-Check, robots.txt-Check, URL-Normalisierung, Deduplication. Dieser Prozess ist nur beim Erstcrawl relevant — monatliche Re-Crawls lesen ausschließlich aus `known_profile_urls` (siehe 5.3).

### 5.5 Sitemap-Nutzung

Wenn eine Domain eine Sitemap anbietet, ist das die bevorzugte URL-Quelle — sie ist effizienter und belastet den Server weniger als blindes BFS-Crawling. Die Sitemap wird zuerst in `robots.txt` gesucht, dann unter Standard-Pfaden (`/sitemap.xml`, `/sitemap_index.xml`). Verschachtelte Sitemap-Indizes werden rekursiv aufgelöst. Das `<lastmod>`-Feld wird für Incremental Crawling ausgewertet.

### 5.6 BFS-Crawling (Fallback)

Wenn keine Sitemap vorhanden ist, wird Breadth-First Search verwendet: maximal 4 Ebenen tief, maximal 200 Seiten pro Domain, nur interne Links. Index Pages werden vorne in die Queue eingereiht da sie schneller zu neuen Content Pages führen.

### 5.7 URL-Normalisierung & Deduplication

Dieselbe Seite kann unter verschiedenen URLs erreichbar sein — mit und ohne Trailing Slash, mit und ohne `www.`, mit verschiedenen Tracking-Parametern. Vor jedem Fetch muss die URL normalisiert werden: Schema auf HTTPS vereinheitlichen, Trailing Slash entfernen, Tracking-Parameter entfernen (`utm_*`, `fbclid`, `gclid` etc.), Fragment-Anker entfernen, Canonical URL aus `<link rel="canonical">` bevorzugen. Die normalisierte URL ist der Deduplication-Key für den aktuellen Run.

### 5.8 Playwright-Konfiguration

Playwright läuft im Headless-Modus mit einem eigenen User-Agent-String der AutoQuery identifiziert und eine Kontakt-URL enthält — das ist Best Practice und signalisiert Transparenz gegenüber Website-Betreibern. Nach dem Seitenload wird auf `networkidle` gewartet statt auf ein blindes Timeout, mit maximal 8 Sekunden als Obergrenze. Wenn nach 8 Sekunden noch nicht idle, wird mit dem vorhandenen Inhalt weitergemacht.

Infinite Scroll muss simuliert werden: nach dem initialen Load schrittweise zum Ende der Seite scrollen, jeweils warten bis neue Inhalte geladen sind, maximal 5 Scroll-Iterationen. Stoppen wenn sich die Seitenhöhe nicht mehr verändert.

### 5.8a Rate Limiting

Rate Limiting ist pro Domain implementiert, nicht global — mehrere Domains können parallel gecrawlt werden, aber Requests an dieselbe Domain werden serialisiert mit konfigurierbarem Delay.

**Standard-Delay:** 2 Sekunden zwischen Requests an dieselbe Domain (konfigurierbar pro Domain in `seed_list.yaml` für Domains die empfindlicher sind). **Nach HTTP 429:** Mindestens 30 Sekunden Pause, danach Exponential Backoff. **Parallele Domains:** Maximal 5 Domains gleichzeitig im Erstcrawl, 10 im monatlichen Re-Crawl (Re-Crawl-Requests sind leichter wegen Conditional Requests).

Die Rate-Limiter-Implementierung nutzt einen Domain-scoped Semaphore mit Timestamp-Tracking — kein globaler Lock der alle Domains blockiert. Der Delay wird nach jedem Request aktualisiert, nicht vor dem Request gewartet — das verhindert Drift bei langsamen Responses.

### 5.9 Pagination

Pagination-Seiten (numerisch via `?page=2` oder `/page/2`, "Next"-Links, Load-More-Buttons) werden als Index Pages behandelt und vorne in die Queue eingereiht. Pagination-URLs müssen normalisiert und dedupliziert werden um Endlosschleifen zu vermeiden.

### 5.10 Fehlerbehandlung & Retry

HTTP-Fehler werden in permanent und temporär klassifiziert. Permanente Fehler (404, 410) führen dazu dass der Agent als `unreachable` markiert wird — kein weiterer Retry, kein monatlicher Re-Crawl bis ein Admin die Domain manuell freigibt. Temporäre Fehler (429, 500, 503, Timeout) werden mit Exponential Backoff bis zu 3 Mal wiederholt. Bei 429 (Too Many Requests) gilt eine zusätzliche Wartezeit von mindestens 30 Sekunden vor dem ersten Retry. Nach 3 fehlgeschlagenen Versuchen wird der Fehler geloggt und die Seite übersprungen.

Redirects (301, 302) werden verfolgt und die finale URL normalisiert und gespeichert.

### 5.11 Anti-Crawling & Captcha-Erkennung

Wenn der geholte Inhalt Captcha-Indikatoren enthält (z.B. Cloudflare-Challenge, "Are you human"-Seiten), wird die Domain für die aktuelle Session gesperrt und der Admin notifiziert. Kein automatischer Bypass-Versuch — das wäre ein AGB-Verstoß. Ebenso werden leere Responses bei HTTP 200 (Bot-Detection ohne Weiterleitung) erkannt und geloggt.

### 5.12 Login-Wall-Erkennung

Wenn eine Seite auf eine Login-URL weiterleitet oder "Members only"/"Login to view"-Inhalte enthält, wird sie übersprungen und geloggt. Kein Versuch diese Seiten zu umgehen.

### 5.13 Incremental Crawling

Beim monatlichen Re-Crawl werden Conditional Requests verwendet: `If-Modified-Since` mit dem Datum des letzten erfolgreichen Crawls sowie `If-None-Match` mit dem gespeicherten ETag. Eine HTTP-304-Antwort bedeutet dass sich die Seite nicht verändert hat — `last_checked_at` wird aktualisiert, aber keine Neu-Extraktion. Der ETag wird pro Agent-Profil in der Datenbank gespeichert. Das reduziert den Traffic erheblich und schont die Ziel-Server.

### 5.14 Page Classifier

Der Classifier entscheidet für jede Content-Seite ob es sich um eine Index Page (Liste von Agenten-Links) oder eine Content Page (einzelnes Agenten-Profil) handelt. Input ist Seiten-Titel plus die ersten 500 Wörter des bereinigten Body-Texts — mehr Input liefert keine bessere Klassifikation aber erhöht die LLM-Latenz. Ausgabe ist exakt `INDEX` oder `CONTENT`. Bei uneindeutigem Output gilt `CONTENT` als Fallback — besser eine Seite doppelt zu prüfen als einen Agenten zu verpassen. Vor Produktionseinsatz ist eine Kalibrierung an mindestens 30 manuell gelabelten Beispielseiten verpflichtend.

### 5.15 Content Extractor

Der Content Extractor erzeugt sauberen Fließtext aus dem HTML. Dieser Text wird nach der Extraktion und Embedding-Berechnung persistent in der Datenbank gespeichert (Felder `wishlist_raw`, `bio_raw`, `hard_nos_raw` in der `agents`-Tabelle). Der gespeicherte Originaltext dient drei Zwecken: (1) höhere Embedding-Qualität bei Re-Crawls, (2) Verifikation im Review-Interface, (3) Option zur späteren Frontend-Anzeige. **Im Frontend wird Originaltext im MVP nicht angezeigt** — diese Entscheidung kann später ohne Architektur-Änderung revidiert werden.

Zu entfernen sind strukturelle Elemente (`<script>`, `<style>`, `<nav>`, `<footer>`, `<header>`, `<aside>`, `<form>`) sowie Elemente mit Navigation-CSS-Klassen (nav, menu, sidebar, footer, cookie, banner, advertisement, related, social, newsletter, popup, modal, breadcrumb). Bevorzugt werden `<main>`, `<article>`, semantische `<section>`-Elemente. Die Canonical URL aus `<link rel="canonical">` wird extrahiert und für URL-Normalisierung genutzt.

### 5.16 Quality Gate — Crawl Output Bewertung

**Zweck:** Bevor ein extrahierter Text ans LLM übergeben wird, muss bewertet werden ob er für eine hochwertige Extraktion geeignet ist. Schlechte Inputs produzieren schlechte Extraktionen und vergiften die Datenbank. Das Quality Gate ist die letzte Qualitätskontrolle vor dem LLM.

**Die sieben Bewertungsdimensionen** werden zu einem Gesamtscore von 0–1 kombiniert. Signal-Rausch-Verhältnis und strukturelle Vollständigkeit sind am stärksten gewichtet (je 25%), da sie am direktesten die LLM-Extraktionsqualität bestimmen.

**Dimension 1 — Mindestlänge (Gewicht: 20%):** Unter 150 Wörtern sofortiger Discard ohne weitere Prüfung. Zwischen 150 und 300 Wörtern reduzierter Score. Über 5000 Wörtern reduzierter Score mit Kürzungs-Flag — Text wird auf 4000 Wörter gekürzt, nicht verworfen.

**Dimension 2 — Signal-Rausch-Verhältnis (Gewicht: 25%):** Verhältnis agenten-relevanter Begriffe (represent, looking for, seeking, wishlist, submit, query, manuscript, fiction, fantasy, thriller, literary, genre, audience, YA, middle grade) zur Gesamtwortanzahl. Unter 1% stark reduzierter Score. Über 3% voller Score. Begründung: Ein Text mit wenig Agent-Vokabular ist entweder eine falsch klassifizierte Seite oder stark mit Navigation-Inhalten verunreinigt — beides führt zu schlechten LLM-Extraktionen.

**Dimension 3 — Strukturelle Vollständigkeit (Gewicht: 25%):** Prüft ob der Text die erwarteten Sektionen eines Agenten-Profils enthält. Wunschlisten-Sektion (Begriffe wie wishlist, looking for, seeking, represent, interests) ist mit 50% des Struktur-Scores gewichtet — sie ist das wichtigste Inhaltselement. Bio/Name-Sektion (about, bio, profile) mit 30%, Submission-Sektion (submit, query, guidelines) mit 20%. Fehlt die Wunschlisten-Sektion komplett wird das als kritisches Issue gewertet.

**Dimension 4 — Rausch-Indikatoren (Gewicht: 15%):** Zählt Vorkommen von Texten die eindeutig nicht zum Agenten-Profil gehören: Cookie-Hinweise, Privacy-Policy-Verweise, Copyright-Footer, Social-Media-Aufforderungen, 404-Texte. Drei oder mehr solcher Indikatoren deuten darauf hin dass der Content Extractor unzureichend gereinigt hat — Score wird proportional reduziert.

**Dimension 5 — Encoding & Lesbarkeit (Gewicht: 10%):** Verhältnis lesbarer Zeichen (Buchstaben + Leerzeichen) zur Gesamtzeichenzahl. Unter 60% Encoding-Fehler oder Garbled Text — sofortiger Discard, weil das LLM Encoding-Fehler nicht korrigieren kann und inkonsistente Extraktionen produzieren würde.

**Dimension 6 — Spracherkennung (Gewicht: 5%):** Einfache Heuristik über häufige englische Funktionswörter in den ersten 200 Wörtern. Weniger als 3 Treffer deutet auf nicht-englischen Text hin — Discard, da außerhalb des Scopes.

**Dimension 7 — Duplikat-Erkennung (hartes Kriterium, kein Score):** MD5-Hash des bereinigten Texts wird mit allen Hashes des aktuellen Runs verglichen. Duplikat → Discard ohne weitere Prüfung.

**Quality Gate Aktionen:**

| Score | Kritische Issues | Aktion |
|---|---|---|
| ≥ 0.65 | Keine | `extract` — normal ans LLM übergeben |
| 0.40–0.65 | Keine kritischen | `extract_with_warning` — LLM extrahiert, Review-Interface zeigt gelbes Flag |
| < 0.40 | — | `discard` — nicht extrahieren |
| Beliebig | Encoding-Fehler | `discard` — LLM kann das nicht reparieren |
| Beliebig | Nicht-Englisch | `discard` — außerhalb Scope |
| Beliebig | Duplikat | `discard` — ohne weitere Prüfung |
| < 150 Wörter | — | `discard` — sofort, ohne weiteren Check |

`extract_with_warning`-Profile erhalten im Streamlit-Review-Interface ein gelbes Flag mit den konkreten Issues. Der Reviewer entscheidet dann manuell ob das Profil trotzdem genehmigt wird.

Das Quality Gate Ergebnis (Score, Issues, Aktion) wird immer geloggt — unabhängig davon ob der Text extrahiert wird oder nicht. Diese Daten sind wichtig für die kontinuierliche Verbesserung des Content Extractors.

### 5.17 Crawl-Run-Logging

Jeder Crawl-Run wird in einer `crawl_runs`-Tabelle protokolliert. Gespeichert werden: Domain, Run-Typ (initial/monthly/priority), Start- und Endzeit, Status, Anzahl gecrawlter/klassifizierter/übersprungener/fehlerhafter Seiten, Quality Gate Ergebnisse (extracted/warned/discarded, Durchschnittsscore, häufigste Issues als JSON), und Extraktionsergebnisse (neue/aktualisierte/unveränderte Profile).

Nach jedem Run prüft ein automatischer Task ob die Discard-Rate über 40% liegt oder die Gesamt-Erfolgsrate unter 50% fällt — in beiden Fällen wird der Admin notifiziert. Eine hohe Discard-Rate signalisiert dass sich eine Website strukturell verändert hat und der Crawler oder Content Extractor nachgearbeitet werden muss.

---

## 6. Modul B: LLM-Extraktion & Review

### 6.1 Rechtliche Grundlage

Was gespeichert werden darf und was nicht ergibt sich direkt aus dem Urheberrecht:

| Datentyp | Speichern? | Anzeigen? | Begründung |
|---|---|---|---|
| Genres, Audience, Submission-Anforderungen | ✅ | ✅ | Fakten, nicht urheberrechtlich schützbar |
| Maschinell extrahierte Keywords | ✅ | ✅ | Eigene maschinelle Schöpfung, kein Zitat |
| Embedding-Vektor | ✅ | — | §44b UrhG — Text and Data Mining |
| Wunschliste als Fließtext | ✅ | ❌ (MVP) | Intern gespeichert für Embedding-Qualität + Review. Nicht im Frontend angezeigt — reduziert Veröffentlichungsrisiko nach §2 UrhG. Anzeige kann später aktiviert werden. |
| Bio als Fließtext | ✅ | ❌ (MVP) | Wie Wunschliste |
| Hard-Nos als Fließtext | ✅ | ❌ (MVP) | Wie Wunschliste |

**Strategie: Store More, Show Less.** Originaltexte werden intern gespeichert, aber im MVP nicht veröffentlicht. Das gibt uns die bestmögliche Embedding-Qualität und hält die Option offen, Originaltexte später im Frontend anzuzeigen — ohne erneutes Crawling aller Profile. Die Entscheidung zur Veröffentlichung kann jederzeit per Frontend-Änderung getroffen werden, idealerweise nach Rechtsberatung.

### 6.2 Verarbeitungsreihenfolge

Die Reihenfolge: zuerst alle strukturierten Felder aus dem Text extrahieren (Fakten, Keywords), dann das Embedding aus dem Volltext berechnen, dann die Originaltexte (Wishlist, Bio, Hard-Nos) als separate Felder in der Datenbank speichern. Die Trennung zwischen strukturierten Feldern und Rohtext bleibt erhalten — Keywords sind die maschinell extrahierte, kompakte Repräsentation, Rohtext ist das Original für Embedding-Qualität und spätere Optionalität.

### 6.3 Zu extrahierende Felder

Das LLM extrahiert aus dem Rohtext folgende Felder die persistent gespeichert werden: Name, Agentur, E-Mail (intern, nie öffentlich angezeigt), Land, Genres (Liste), Audience (Liste), Keywords aus der Wunschliste (maschinell extrahierte Liste), Hard-Nos Keywords (Liste), Submission-Anforderungen (Query Letter ja/nein, Synopsis ja/nein, Seiten als Zahl, Vollmanuskript ja/nein, Bio ja/nein, kurze faktische Zusatznotiz), Submissions-Status (offen/geschlossen), Antwortzeit als faktische Angabe.

Zusätzlich werden die Originaltext-Segmente als separate Felder gespeichert: `wishlist_raw`, `bio_raw`, `hard_nos_raw`. Diese Felder werden im Frontend nicht angezeigt (MVP), aber intern für Embedding-Berechnung und im Review-Interface genutzt.

**Qualitätsprüfung nach Extraktion:** Name muss vorhanden sein, Genres muss mindestens einen Eintrag enthalten, Keywords sollte mindestens 3 Einträge enthalten. Schlägt die Prüfung fehl → Status `extraction_failed`, geloggt, nicht ins Review.

### 6.4 LLM-Prompt-Anforderungen

Alle Prompts werden zentral in `prompts.py` verwaltet. Prompts müssen mit `format: "json"` im Ollama-Aufruf erzwingen dass die Ausgabe valides JSON ist. Jeder Prompt ist versioniert — Änderungen an Prompts erfordern eine neue Versionsnummer damit Extraktionen später nachvollziehbar sind.

Für die Keywords-Extraktion muss der Prompt explizit anweisen **keine** vollständigen Sätze oder Fließtext-Zitate zurückzugeben — nur prägnante Begriffe und kurze Phrasen. Keywords dienen als kompakte, durchsuchbare Repräsentation für FTS und Frontend-Anzeige — der Originaltext wird separat gespeichert.

### 6.5 Review-Interface (Streamlit)

Das Review-Interface zeigt die extrahierten Fakten und Keywords sowie die gespeicherten Originaltexte (Wishlist, Bio, Hard-Nos) für Verifikation. Zusätzlich einen prominenten Link zur Originalseite, das Crawl-Datum, den Quality Gate Score und eventuelle Issues.

Alle extrahierten Felder sind vor der Genehmigung editierbar. Der Reviewer öffnet die Originalseite im Browser, vergleicht manuell, und korrigiert falls nötig. Aktionen: Genehmigen, Ablehnen (mit Pflichtbegründung), Überspringen. Profile mit Quality Gate Flag `extract_with_warning` werden mit gelbem Indikator hervorgehoben.

**Embedding-Trigger:** Das Agenten-Embedding wird automatisch neu berechnet wenn ein Profil den Status `approved` erhält — sowohl bei Erstaufnahme als auch nach Re-Crawl-Review. Wenn ein Reviewer Keywords oder Genres editiert bevor er genehmigt, fließen die editierten Werte in das Embedding ein. Für Profile die bereits `approved` sind und nachträglich vom Admin editiert werden (z.B. Korrektur eines falschen Genres), muss das Embedding ebenfalls automatisch neu berechnet werden — der Save-Button im Review-Interface triggert die Neuberechnung.

---

## 7. Modul C: Datenbank & Datenmodell

### 7.1 Erforderliche PostgreSQL Extensions

`pgvector` für Vektorsuche, `pg_trgm` für trigram-basierte Ähnlichkeitssuche als optionale Ergänzung.

### 7.2 Tabelle `agents`

Enthält alle persistenten Agenten-Daten. Originaltexte (Wishlist, Bio, Hard-Nos) werden intern gespeichert aber im Frontend nicht angezeigt (MVP). Die API-Endpunkte für das Frontend dürfen die `*_raw`-Felder **nicht** ausliefern — das wird serverseitig über separate Pydantic-Schemas erzwungen (ein internes Schema mit Rohtext für Admin/Review, ein öffentliches Schema ohne).

Felder: id, name (NOT NULL), agency, email, country, source_url (UNIQUE NOT NULL), genres (TEXT[]), audience (TEXT[]), keywords (TEXT[]), hard\_nos\_keywords (TEXT[]), wishlist\_raw (TEXT), bio\_raw (TEXT), hard\_nos\_raw (TEXT), submission\_req (JSONB), response\_time, is\_open (BOOLEAN), embedding (vector(1024)), embedding\_model, embedding\_updated\_at, fts\_vector (TSVECTOR), review\_status (pending/approved/rejected/extraction\_failed/unreachable), rejection\_reason, reviewed\_by, reviewed\_at, crawled\_at, last\_checked\_at, etag (für Incremental Crawling), recrawl\_requested, opted\_out, opted\_out\_at, created\_at, updated\_at.

Indizes: IVFFlat auf `embedding` für Cosine Similarity (`lists = 50` als Startwert, anpassen wenn Datenmenge wächst), GIN auf `fts_vector`, kombinierter Index auf `review_status + is_open + opted_out` für die häufigste Filter-Kombination im Matching.

### 7.3 Tabelle `manuscripts`

Enthält Autoren-Inputs und beide Embedding-Varianten. Die Manuskript-Texte gehören dem Autor und dürfen für wiederholtes Matching gespeichert werden — müssen aber bei Account-Löschung via CASCADE gelöscht werden.

Felder: id, user\_id (FK → users, CASCADE DELETE), genre, audience, tone, themes, comp\_titles, query\_letter (alle NOT NULL), first\_chapter, chosen\_excerpt, additional\_wishes (alle optional), embedding\_fulltext (vector(1024)), embedding\_query\_expanded (vector(1024)), embedding\_weight\_fulltext (FLOAT DEFAULT 0.7), embedding\_weight\_expanded (FLOAT DEFAULT 0.3), embedding\_model, created\_at.

Beide Gewichtungsparameter werden pro Manuskript gespeichert um späteres A/B-Testing und Recomputing mit anderen Gewichtungen zu ermöglichen.

### 7.4 Tabelle `users`

Felder: id, email (UNIQUE NOT NULL), password\_hash, created\_at, last\_login, is\_active, plan (DEFAULT 'free' — Freemium-Vorbereitung).

### 7.5 Tabelle `matching_results`

Speichert alle Matching-Ergebnisse mit den vier Einzel-Scores aus Phase 1. Diese Scores sind für Phase 2 essenziell — sie werden als Features ins trainierte Modell eingehen. `algorithm_version` ermöglicht A/B-Testing zwischen verschiedenen Algorithmus-Varianten.

Felder: id, user\_id (CASCADE), manuscript\_id (CASCADE), agent\_id (CASCADE), final\_score, semantic\_score, fts\_score, genre\_score, audience\_score, mmr\_rank, algorithm\_version, status (saved/contacted/full\_ms\_requested/rejected\_by\_agent/offer\_received/withdrawn), status\_updated\_at, notes, user\_rating (1–5, optional), user\_rating\_at, created\_at.

Die Status-Abstufungen `contacted → full_ms_requested → offer_received` sind als Funnel konzipiert — je weiter ein Nutzer darin vorschreitet, desto stärker das positive Trainings-Signal für Phase 2.

### 7.6 Tabelle `interaction_events`

Das ist die wichtigste Investition in Phase 2. Alle Nutzer-Interaktionen mit Matching-Ergebnissen werden als Events gespeichert. Ohne diese Daten ist ein Upgrade auf supervised Learning nicht möglich. Das Logging muss von Tag 1 an aktiv sein.

Felder: id (BIGSERIAL), user\_id (SET NULL bei Löschung), session\_id (für nicht eingeloggte Nutzer), manuscript\_id (SET NULL), agent\_id (SET NULL), event\_type, result\_rank, session\_score, algorithm\_version, created\_at.

**Session-ID-Generierung:** Für nicht eingeloggte Nutzer wird eine UUID v4 als Session-ID generiert und in einem HttpOnly-Cookie mit 24h Lebensdauer gespeichert. Die Session-ID enthält keine personenbezogenen Daten und dient ausschließlich der Zuordnung von Events innerhalb einer Sitzung. Da das Cookie funktional notwendig ist (kein Tracking, kein Profiling), fällt es unter die ePrivacy-Ausnahme für technisch notwendige Cookies — kein Cookie-Banner erforderlich. Die Session-ID wird nach 90 Tagen aus der Datenbank gelöscht (siehe 15.4). Sobald ein Nutzer sich registriert oder einloggt, werden offene Session-Events nachträglich mit der `user_id` verknüpft und die Session-ID wird nicht weiter verwendet.

Indizes auf `(manuscript_id, agent_id)`, `event_type`, und `created_at`.

**Event-Typen und ihre Bedeutung als Feedback-Signal:**

| Event | Signal |
|---|---|
| `result_shown` | Neutral — Baseline |
| `card_clicked` | Schwach positiv |
| `profile_expanded` | Mittel positiv |
| `submission_checklist` | Mittel positiv |
| `source_link_clicked` | Stark positiv |
| `marked_contacted` | Sehr stark positiv |
| `full_ms_requested` | Stärkstes positives Signal |
| `offer_received` | Stärkstes positives Signal |
| `marked_rejected` | Negatives Signal |
| `result_ignored` | Schwach negativ (Timer: 30s keine Interaktion) |

### 7.7 Tabellen `opt_out_requests`, `recrawl_queue`, `crawl_runs`

`opt_out_requests`: id, agent\_name, agent\_url, contact\_email, request\_text, status (pending/processed), received\_at, processed\_at.

`recrawl_queue`: id, agent\_id (CASCADE), reason, reported\_by (FK users), status (pending/processing/done), created\_at, processed\_at.

`known_profile_urls`: id, domain (TEXT), url (TEXT UNIQUE), discovered\_at, discovery\_method ('browser\_agent' / 'sitemap' / 'manual'), status (active / unreachable / removed), last\_checked\_at, consecutive\_failures (INTEGER DEFAULT 0).

**Lifecycle-Regeln für `known_profile_urls`:**

- Bei HTTP 404/410 im Re-Crawl: `consecutive_failures` inkrementieren. Nach 3 aufeinanderfolgenden Fehlern: `status → unreachable`, URL wird nicht mehr im monatlichen Re-Crawl berücksichtigt, Admin wird notifiziert.
- Bei erfolgreicher Antwort: `consecutive_failures` auf 0 zurücksetzen, `last_checked_at` aktualisieren.
- Admin kann URLs manuell hinzufügen (`discovery_method = 'manual'`), entfernen (`status → removed`), oder als `active` reaktivieren — alles über das Streamlit Admin-Interface.
- Wenn eine Agentur ihre Seitenstruktur komplett ändert (viele `unreachable`-URLs derselben Domain), kann der Admin den Browser-Agenten erneut für diese Domain auslösen. Dabei werden alle bestehenden URLs der Domain auf `status → removed` gesetzt und durch die neu entdeckten URLs ersetzt.

`crawl_runs`: id, domain, run\_type (initial/monthly/priority), started\_at, finished\_at, status, pages\_fetched, pages\_index, pages\_content, pages\_skipped, pages\_error, quality\_extracted, quality\_warned, quality\_discarded, avg\_quality\_score, top\_issues (JSONB), profiles\_new, profiles\_updated, profiles\_unchanged, error\_message.

---

## 8. Modul D: Embedding-Pipeline

### 8.1 Modell: BAAI/bge-large-en-v1.5

Dieses Modell ist die Empfehlung weil es aktuell das stärkste open-source Modell auf MTEB für Semantic Textual Similarity ist, explizit für asymmetrisches Matching trainiert wurde (Instruction Prefix signalisiert dem Modell die Rolle des Textes), 1024 Dimensionen produziert, lokal betreibbar und kommerziell nutzbar ist. Fallback ist `intfloat/e5-large-v2` mit analogem Instruction-Prefix-System.

**Wichtig:** Das Modell muss über eine abstrakte Schnittstelle eingebunden werden die einen Modellwechsel ohne Änderungen an der übrigen Pipeline ermöglicht. Der Modellname wird in `.env` konfiguriert. Bei Modellwechsel muss ein `recompute_all_embeddings`-Skript alle Embeddings in `agents` und `manuscripts` neu berechnen, inklusive Datenbankmigration der Vektordimension.

**Similarity-Metrik:** Cosine Similarity — passend zum Trainings-Loss des Modells. In pgvector der `<=>` Operator (Cosine Distance = 1 − Cosine Similarity).

### 8.2 Das Asymmetrie-Problem und seine Lösung

Agenten-Embeddings und Manuskript-Embeddings entstehen aus strukturell verschiedenen Texten: Agenten-Profile sind ~100–300 Wörter Originaltext (Wishlist + Bio), Manuskript-Profile sind ~800–3000 Wörter Fließtext. Zusätzlich besteht ein Perspektiven-Problem: Autoren beschreiben ihr Buch aus ihrer Perspektive, Agenten formulieren Wunschlisten aus ihrer Perspektive. Diese sprachliche Lücke kann nicht allein durch das Embedding-Modell geschlossen werden.

Die Lösung sind drei Maßnahmen gemeinsam: BGE Instruction Prefix (adressiert Längen-Asymmetrie), zweistufiges Manuskript-Embedding (adressiert Perspektiven-Problem), normalisierte Kombination beider Vektoren.

### 8.3 Agenten-Embedding

**Beim Erstcrawl** steht der Originaltext zur Verfügung — das Embedding wird direkt daraus berechnet, was die bestmögliche Qualität liefert. Der Agenten-Instruction-Prefix lautet: `"Represent this literary agent profile for retrieval: This agent is looking for: "`.

**Bei Re-Crawls:** Da der Originaltext jetzt persistent gespeichert ist, wird das Embedding bei jedem Re-Crawl aus dem aktuellen Originaltext neu berechnet — dieselbe Qualität wie beim Erstcrawl. Wenn sich der Text geändert hat, fließen die Änderungen direkt ins Embedding ein. Falls der Originaltext aus technischen Gründen fehlt (z.B. Legacy-Profile vor der Umstellung), wird als Fallback aus gespeicherten Keywords rekonstruiert. Keywords werden dabei doppelt eingefügt um ihr Gewicht im Embedding-Raum zu erhöhen. Gleicher Instruction-Prefix.

### 8.4 Manuskript-Embedding — Zweistufige Strategie

**Embedding 1 — Volltext (beim Upload, einmalig gespeichert):** Alle Autoren-Inputs werden zu einem strukturierten Text zusammengesetzt (Genre, Audience, Ton, Themen, Comp Titles, Query Letter, Kapitel-Ausschnitte) und mit dem Manuskript-Instruction-Prefix eingebettet: `"Represent this manuscript to find matching literary agents: "`. Dieses Embedding enthält alle Informationen ohne Verlust. Comp Titles sind hier besonders wertvoll — ein spezifischer Titel wie "A Psalm for the Wild-Built" transportiert Ton, Tempo, Stil und Verlagskontext in einem Begriff.

**Embedding 2 — Query Expansion (beim ersten Matching, dann gecacht):** Ein LLM-Call (Ollama lokal) generiert aus dem Query Letter 12 Keywords in Agenten-Sprache — Begriffe die ein Agent der dieses Buch lieben würde in seiner eigenen Wunschliste verwenden würde. Dieses Embedding wird mit dem **Agenten**-Instruction-Prefix formuliert, nicht dem Manuskript-Prefix. Dadurch liegt es im selben Vektor-Raum wie die Agenten-Embeddings — das ist die eigentliche Brücke über die Perspektiven-Lücke. Das Ergebnis wird gecacht.

**Finales Manuskript-Embedding:** Gewichtete Kombination aus Volltext-Embedding (Standard: 70%) und Query-Expansion-Embedding (Standard: 30%), danach L2-Normalisierung für korrekte Cosine Similarity. Die Gewichtung 70/30 ist ein empirisch zu validierender Startwert — nach den ersten 100 Matchings und Nutzer-Feedback sollte sie getuned werden. Beide Gewichte werden als konfigurierbare Parameter in `.env` geführt und pro Manuskript in der Datenbank gespeichert.

---

## 9. Modul E: Matching-Algorithmus (Phase 1)

### 9.1 Architektur-Anforderung

Die Scoring-Funktion muss hinter einer abstrakten Schnittstelle (`score_candidates(manuscript, candidates) → list[ScoredAgent]`) implementiert werden. Diese Schnittstelle bleibt in Phase 2 und 3 identisch — nur die Implementierung dahinter wird ausgetauscht. Das ermöglicht einen Phasenwechsel ohne Pipeline-Änderungen.

### 9.2 Schicht 1 — Harte Constraints (Filter)

Vor jeder Score-Berechnung werden Kandidaten ausgeschlossen wenn: `is_open = FALSE`, `opted_out = TRUE`, `review_status != 'approved'`, oder Hard-Nos-Match über Schwellenwert. Für den Hard-Nos-Check wird das Manuskript-Embedding gegen ein Embedding der Hard-Nos-Keywords verglichen. Der Schwellenwert von 0.75 ist ein Startwert der nach den ersten Review-Ergebnissen empirisch validiert werden muss — zu niedrig führt zu False Positives (harmlose Überschneidungen), zu hoch übersieht echte Hard-Nos.

### 9.3 Schicht 2 — Hybrid Scoring via Gewichteter Konvexkombination

Vier Signale scoren die verbliebenen Kandidaten unabhängig voneinander. Die Scores werden per Distribution-Based Score Normalization (DBSF) auf [0,1] normalisiert und dann als gewichtete Konvexkombination zusammengeführt:

```
final_score = w₁·norm(genre_match) + w₂·norm(audience_score) + w₃·norm(fts_score) + w₄·norm(cosine_sim)
```

**Warum Konvexkombination statt RRF:** RRF (Cormack et al. 2009) konvertiert Scores in Ränge und verwirft dabei Score-Magnituden. Wenn ein Agent eine Cosine Similarity von 0.98 hat und der nächste 0.52, macht RRF daraus Rang 1 und 2 — der dramatische Qualitätsunterschied geht verloren. Bei unserem Szenario (500–5.000 Agenten, alle Scores für alle Kandidaten vollständig berechenbar) entfällt RRFs Hauptvorteil — die Vermeidung von Score-Normalisierung über verschiedene Ergebnismengen. Convex Combination übertrifft RRF sowohl In-Domain als auch Out-of-Domain bei vollständig berechenbaren Scores (Bruch et al. 2023, ACM TOIS). Bereits ~20 gelabelte Matches reichen für nahezu optimale Gewichte (Sun et al. 2025).

**Initiale Gewichte (vor empirischem Tuning):** w₁=0.35 (Genre), w₂=0.15 (Audience), w₃=0.25 (FTS), w₄=0.25 (Semantic). Genre ist am stärksten gewichtet weil es im Publishing das dominante Filterkritierum ist — ein Agent der kein Fantasy vertritt wird nie einen Fantasy-Roman annehmen, egal wie gut der semantische Match ist. Alle Gewichte sind in `.env` konfigurierbar und müssen sich zu 1.0 summieren.

**Tuning-Strategie:** Vor Launch werden die Gewichte manuell auf Basis von Expert Reviews gesetzt. Nach ~50 gelabelten Matches (aus Interaction Events, siehe 10.5) werden die Gewichte per Grid Search auf den gelabelten Daten optimiert. Die optimierten Gewichte werden in `algorithm_version` versioniert.

**Normalisierung (DBSF):** Jedes Signal wird anhand seiner empirischen Verteilung normalisiert: `norm(x) = (x - μ) / σ`, dann auf [0,1] geclippt. μ und σ werden beim Server-Start aus den aktuellen Agenten-Scores berechnet und gecacht. Bei signifikanter Änderung der Agenten-Datenbank (>10% neue Profile) werden μ und σ neu berechnet.

**Fallback:** Solange keine gelabelten Daten für Gewichts-Optimierung vorliegen, werden die initialen Gewichte verwendet. Falls ein Signal nicht berechenbar ist (z.B. kein FTS-Treffer), wird sein Gewicht proportional auf die verbleibenden Signale verteilt.

**Konzeptionelle Hierarchie:** Genre und strukturierter Keyword-Match sind dominante Signale. Embedding ist Feinabstimmung für Kandidaten die strukturell passen aber keine exakten Keyword-Treffer haben. Diese Hierarchie spiegelt sich direkt in den Gewichten wider — Genre (w₁) ist am stärksten gewichtet.

**Signal A — Genre-Match-Score:** Vergleicht Manuskript-Genres gegen Agenten-Genres. Exakter Match = 1.0, Alias-Match (z.B. "YA" = "Young Adult", "Spec Fic" = "Speculative Fiction") = 0.85, semantischer Match via Embedding = bis 0.7 skaliert.

**Genre-Alias-Tabelle:** Eine YAML-Datei (`matching/genre_aliases.yaml`) definiert kanonische Genre-Namen und ihre Aliasse. Die Datei wird beim Server-Start einmalig geladen und im Speicher gehalten. Der Admin pflegt die Datei manuell — Änderungen erfordern einen Neustart des API-Servers (akzeptabel im MVP, Post-MVP in DB-Tabelle mit Admin-UI migrieren).

Beispielstruktur:
```yaml
- canonical: "Cozy Fantasy"
  aliases: ["cozy fant", "cosy fantasy", "comfort fantasy"]
- canonical: "Young Adult"
  aliases: ["YA", "young-adult", "teen fiction"]
- canonical: "Speculative Fiction"
  aliases: ["spec fic", "specfic", "speculative"]
- canonical: "Literary Fiction"
  aliases: ["lit fic", "literary", "upmarket fiction"]
```

Beim Genre-Score-Vergleich werden beide Seiten (Manuskript-Genre und Agenten-Genre) zuerst auf ihre kanonische Form normalisiert. Erst wenn kein Alias-Match gefunden wird, greift der semantische Embedding-Fallback. Die Alias-Tabelle muss vor Launch mindestens 30 Genre-Einträge mit gängigen Publishing-Varianten enthalten.

**Signal B — Audience-Proximity-Score:** Hierarchische Ähnlichkeit entlang der Reihenfolge Children's → Middle Grade → YA → Adult. Exakter Match = 1.0, eine Stufe Abstand = 0.6, zwei Stufen = 0.3, drei Stufen = 0.1.

**Signal C — Full-Text-Search via ts\_rank\_cd:** PostgreSQL FTS auf `fts_vector` mit Query aus Manuskript-Genre, Themen, Comp Titles, und Query-Expansion-Keywords. `ts_rank_cd` (Cover Density) statt `ts_rank` weil es die Nähe der Suchbegriffe berücksichtigt — besser für kurze Keyword-Listen. Comp Titles sind hier besonders wertvolle Signale da spezifische Titel exakt matchen können.

**Signal D — Semantische Cosine Similarity:** Cosine Similarity zwischen finalem Manuskript-Embedding und Agenten-Embedding. Erfasst semantische Nähe die in den strukturierten Signalen nicht sichtbar ist — z.B. Agenten die thematisch sehr ähnliche Bücher vertreten ohne dieselben Begriffe zu verwenden.

### 9.4 Schicht 3 — MMR Re-Ranking

Maximal Marginal Relevance diversifiziert die Top-50-Kandidaten nach Scoring zu einer finalen Liste. Parameter λ=0.7 (konfigurierbar in `.env`) — balanciert Relevanz und Diversität. λ=1.0 wäre reines Relevanz-Ranking, λ=0.0 reines Diversity-Ranking. Input: Top-50 nach Konvexkombination. Output: Top-20 für eingeloggte Nutzer, Top-3 für nicht eingeloggte.

Zusätzliches hartes Strukturlimit unabhängig von MMR: Maximal 3 Agenten derselben Agentur in den Top-10. Das verhindert dass ein Nutzer alle Empfehlungen nur an eine einzige Agentur richtet.

**Post-MVP Upgrade — DPP + Calibration:** Wenn ausreichend Interaktionsdaten vorliegen (Phase 2), sollte MMR durch Determinantal Point Processes (DPP) ersetzt werden. DPP bewertet die Diversität der gesamten ausgewählten Menge simultan über eine Kernel-Matrix statt wie MMR nur paarweise Distanzen zu betrachten — bei 50 Kandidaten ist die 50×50-Kernel-Matrix trivial berechenbar (Chen et al. 2018, NeurIPS). Ergänzend dazu kann Calibration (Steck 2018, RecSys) als orthogonale Schicht sicherstellen, dass die Ergebnisliste die Genre-Verteilung des Manuskripts proportional abbildet. Beide Methoden sind Cold-Start-tauglich da sie nur Item-Features benötigen, aber ihr Mehrwert gegenüber MMR lässt sich erst mit echten Nutzerdaten messen.

### 9.5 Schicht 4 — Erklärbarkeit

Für jeden Agenten in den Ergebnissen werden Match-Tags berechnet: Genre (✓ exakt / ~ partiell / ✗ kein Match), Themen (Keyword-Overlap), Audience (Proximity). Diese Tags müssen serverseitig berechnet werden, nicht clientseitig.

Das angezeigte Snippet ist kein Originalzitat sondern eine maschinell generierte Darstellung aus den extrahierten Keywords: z.B. "Sucht: Cozy Fantasy · Character-driven · Queer Protagonists". Der Originaltext ist intern gespeichert, wird aber im MVP-Frontend nicht angezeigt. Die LLM-Erklärung (optional, auf Klick, gecacht pro manuscript/agent-Paar) wird aus Agenten-Keywords, Genres, und Manuskript-Profil generiert — im MVP nicht aus gespeichertem Originaltext, um das Veröffentlichungsrisiko zu minimieren.

---

## 10. Modul F: Interaction Logging & Feedback

### 10.1 Zweck und Priorität

Interaction Logging ist die Investition in Phase 2 und muss von Tag 1 aktiv sein. Ohne ausreichende Interaktionsdaten ist ein Wechsel zu supervised Learning nicht möglich. Das Logging darf die Matching-Latenz nicht beeinflussen — alle Events müssen asynchron geschrieben werden.

### 10.2 Event-Logging

Alle zehn Event-Typen (siehe Tabelle in Modul C 7.6) werden in `interaction_events` geschrieben. `result_shown` wird serverseitig bei jedem Matching geloggt. Alle anderen Events kommen vom Frontend per API-Aufruf. `result_ignored` wird ausgelöst wenn ein Agenten-Ergebnis nach 30 Sekunden ohne jede Interaktion in der sichtbaren Liste war.

### 10.3 Explizites Feedback

1–5 Sterne Bewertung pro Matching-Ergebnis, optional. Wird einmalig nach der ersten Submission-Markierung eingeblendet — nie aufdringlich, nie als Pflicht. Freitext-Kommentar optional. Gespeichert in `matching_results.user_rating`.

### 10.4 Datenschutz

Events enthalten nur IDs und Metadaten — keinen Manuskript-Inhalt. Nutzer können in den Account-Einstellungen das Tracking deaktivieren. Bei Deaktivierung: `result_shown`-Events weiterhin anonym geloggt (für Algorithmus-Baseline), alle anderen Events nicht. In der Datenschutzerklärung muss das Interaction Logging dokumentiert werden.

### 10.5 Phase-2-Trigger

Ein wöchentlicher Celery-Task prüft ob die Mindestmenge für Phase 2 erreicht wurde: mindestens 500 unique (manuscript\_id, agent\_id)-Paare mit non-neutralem Event, davon mindestens 50 positive (contacted, full\_ms\_requested, offer\_received) und 50 negative (marked\_rejected, result\_ignored). Bei Erreichen wird der Admin notifiziert. Die Schwellenwerte sind konfigurierbar.

---

## 11. Modul G: Matching-Qualitätskriterien

### 11.1 User Story

Sarah, 34 Jahre, Erstautorin. Drei Jahre an einem Cozy Fantasy-Roman gearbeitet — character-driven, queere Protagonisten, Found Family, melancholischer Ton. Comp Titles: "A Psalm for the Wild-Built", "The House in the Cerulean Sea." Sarah kennt die Agentur-Landschaft kaum. Jede falsche Submission kostet sie 6–8 Wochen Wartezeit und eine Absage — mit echten emotionalen Kosten.

**Misserfolg:** 20 Empfehlungen die alle generell "Fantasy" vertreten, aber keiner ist je an Cozy Fantasy interessiert gewesen. Sarah bekommt 20 Absagen und denkt ihr Buch taugt nichts. Das System hat versagt, nicht das Buch.

### 11.2 Die fünf Qualitätskriterien

| Kriterium | Messgröße | Ziel | Typ |
|---|---|---|---|
| Precision | Precision@10 | > 0.7 | Soft |
| Hard-Nos | Violation Rate | **0%** | **Hard** |
| Semantische Tiefe | Score mit vs. ohne Query Expansion | +15% | Soft |
| Diversität Score | Intra-List Diversity | > 0.4 | Soft |
| Diversität Struktur | Max. Agenten pro Agentur in Top-10 | **≤ 3** | **Hard** |
| Erklärbarkeit | Expert Review Score | ≥ 4/5 | Soft |

Die zwei harten Kriterien (Hard-Nos Violation Rate = 0%, max. 3 pro Agentur) werden algorithmisch erzwungen. Die vier weichen Kriterien sind Optimierungsziele.

### 11.3 Messung ohne Trainingsdaten

Vor Launch: Bekannte Agent-Autor-Beziehungen (aus Danksagungen veröffentlichter Bücher) rückwärts testen. Expert Review: 1–2 Branchenkenner bewerten 20–30 Matchings auf Skala 1–5. Nach Launch: Interaction Events als implizite Qualitätsmessung.

---

## 12. Modul H: Autor-Input & Interface

### 12.1 Input-Flow

**Schritt 1 — Strukturiertes Formular (Pflicht):** Genre (Dropdown + Freitext, max. 3), Audience (Single-Select: Adult/YA/Middle Grade/Children's), Ton (Freitext, max. 200 Zeichen), Themen (Tags, min. 2, max. 8), Comp Titles (Freitext, 2–3 aktuelle Vergleichstitel, Pflichtfeld). Comp Titles sind besonders wichtig — sie werden im FTS-Signal stark gewichtet und ermöglichen präzise Matches.

**Schritt 2 — Query Letter (Pflicht):** Freitext, min. 100, max. 1000 Wörter, Live-Wortzähler.

**Schritt 3 — Manuskript-Ausschnitte (Optional):** DOCX oder TXT, max. 10 MB, max. 2000 Wörter nach Extraktion pro Datei.

**Schritt 4 — Sonstige Wünsche (Optional):** Freitext, max. 300 Zeichen, fließt als weiches Signal in Query Expansion ein.

### 12.1a Manuskript-Bearbeitung & Versionierung

Ein Autor kann sein Manuskript-Profil jederzeit bearbeiten. Bei Bearbeitung wird ein neuer `manuscripts`-Eintrag erstellt (kein In-Place-Update) — der alte Eintrag bleibt erhalten und mit den bisherigen `matching_results` verknüpft. Beide Embeddings (Volltext + Query Expansion) werden für den neuen Eintrag neu berechnet. Der Autor kann ein neues Matching mit dem aktualisierten Profil starten.

Alte Matching-Ergebnisse bleiben einsehbar (mit Markierung "Basiert auf früherer Version deines Profils") aber werden nicht nachträglich neu berechnet. Der Autor kann alte Manuskript-Versionen einzeln oder komplett löschen — CASCADE auf zugehörige `matching_results` und `interaction_events`.

### 12.2 Ergebnis-Anzeige — Search Engine Modus

**Ohne Konto:** 3 Agenten-Karten (Name, Agentur, Genre-Tags, Audience), kein Aufklappen, CTA zur Registrierung.

**Mit Konto:** Bis zu 20 Karten. Aufklappen zeigt: Genres und Keywords als Tags, Audience, Match-Tags (✓/~/✗), Score-Balken, Submission-Anforderungen. Originaltext (Wishlist, Bio) wird im MVP **nicht** angezeigt — nur Keywords und Fakten. Immer sichtbar: "Zuletzt aktualisiert: [Datum]" und prominenter Link zur Originalseite. Pflicht-Hinweis: "Bitte prüfe alle Details direkt beim Agenten vor dem Einreichen." Aktionen: Kontaktiert / Vollmanuskript angefragt / Angebot erhalten / Abgelehnt / Notiz / Fehler melden / Bewertung (1–5).

### 12.3 Submission-Checkliste

Pro Agent eine personalisierte Checkliste basierend auf den gespeicherten Submission-Anforderungen, abgeglichen gegen was der Nutzer hochgeladen hat. Zeigt was vorhanden ist, was fehlt, was optional ist. Immer mit Link zur Originalseite für Verifikation.

---

## 13. Modul I: Nutzer & Authentifizierung

### 13.1 Zugangsmodell

| Feature | Ohne Konto | Mit Konto |
|---|---|---|
| Matching | ✅ | ✅ |
| Anzahl Ergebnisse | Max. 3 | Bis 20 |
| Profil aufklappen | ❌ | ✅ |
| Speichern / Tracking | ❌ | ✅ |
| Submission-Checkliste | ❌ | ✅ |
| LLM-Erklärungen | ❌ | ✅ |
| Feedback geben | ❌ | ✅ |
| Tracking deaktivieren | ❌ | ✅ |

### 13.2 Authentifizierung
E-Mail + Passwort (bcrypt), E-Mail-Verifizierung bei Registrierung, Passwort-Reset via E-Mail, JWT mit Access Token und Refresh Token. Kein Social Login im MVP.

### 13.2a Frontend-Sicherheit

**Rate Limiting:** Login- und Registrierungs-Endpoints: max. 5 Versuche pro IP pro 15 Minuten. Matching-Endpoint: max. 10 Anfragen pro Nutzer pro Stunde (verhindert Scraping der Agenten-Datenbank). Passwort-Reset: max. 3 Anfragen pro E-Mail pro Stunde.

**Input-Sanitization:** Alle Freitext-Felder (Query Letter, Themen, Notizen, Fehler-Meldungen) werden serverseitig sanitized — HTML-Tags werden gestripped, nicht escaped. Keine User-Inputs werden als HTML gerendert. Pydantic-Validierung auf allen API-Schemas mit Längen-Limits.

**CSRF-Schutz:** JWT in HttpOnly-Cookies mit SameSite=Strict. Alternativ: Bearer Token im Authorization-Header (dann kein CSRF-Risiko). Entscheidung dem Entwickler überlassen, aber eine der beiden Varianten muss implementiert sein.

**File-Upload-Validierung (Schritt 3):** MIME-Type-Check serverseitig (nicht nur Dateiendung) — nur `application/vnd.openxmlformats-officedocument.wordprocessingml.document` und `text/plain` akzeptieren. Dateigröße serverseitig prüfen (max. 10 MB). Dateiname sanitizen (keine Pfad-Traversal-Zeichen). Extrahierter Text wird vor Weiterverarbeitung auf max. 2000 Wörter gekürzt.

### 13.3 Freemium-Vorbereitung
`plan`-Feld in `users` mit Default `'free'`. Alle Feature-Checks laufen über eine zentrale Feature-Flag-Funktion — nie hardcoded. Ermöglicht späteren Freemium-Rollout ohne Architektur-Änderung.

---

## 14. Modul J: Datenpflege & Aktualisierung

### 14.1 Monatlicher Crawl-Zyklus

Celery Beat triggert monatlich einen Re-Crawl aller approved, nicht-opted-out Profile. Bei jedem Re-Crawl: Incremental Request mit `If-Modified-Since` und `ETag`. Unveränderte Seiten: nur `last_checked_at` aktualisieren. Geänderte Seiten: Fakten, Keywords und Originaltexte neu extrahieren, Embedding aus dem neuen Originaltext neu berechnen, bei Änderungen Status → `pending` und Review-Queue. Neue Domains aus `seed_list.yaml` durchlaufen den vollständigen Erstaufnahme-Prozess. Nicht erreichbare Domains (nach 3 Retries) werden als `unreachable` markiert und der Admin notifiziert.

### 14.2 Prioritäts-Re-Crawling

Eingeloggte Nutzer können über einen "Fehler melden"-Button mit Freitext einen Re-Crawl anfordern. Eintrag in `recrawl_queue`, Bearbeitung binnen 48h durch Celery-Task.

---

## 15. Modul K: Datenschutz & DSGVO

### 15.1 Opt-Out für Agenten

Öffentliche Opt-Out-Seite ohne Login-Pflicht. Formular: Name, Agentur-URL, Kontakt-E-Mail, optionaler Freitext. Bearbeitung binnen 72 Stunden: Agent → `opted_out = TRUE`, Domain → `blacklist.yaml`. Bestätigung per E-Mail.

### 15.2 Informationspflicht Art. 14 DSGVO

Öffentliche "Für Agenten"-Seite erklärt: was AutoQuery ist, welche Daten gespeichert werden (Fakten, Keywords, Embeddings, und Originaltexte der Profilseite — intern, nicht öffentlich angezeigt), wie Opt-Out funktioniert, Kontaktmöglichkeit. Diese Seite erfüllt die Transparenzpflicht ohne jeden Agenten einzeln anschreiben zu müssen.

### 15.3 Rechtsgrundlagen
Agenten-Daten: Art. 6 Abs. 1 lit. f DSGVO — Berechtigtes Interesse (AutoQuery führt Agenten aktiv Traffic zu). Nutzerdaten: Art. 6 Abs. 1 lit. b — Vertragserfüllung.

### 15.4 Interaction Logging & DSGVO
In der Datenschutzerklärung dokumentieren. Opt-Out in Account-Einstellungen. Events enthalten keine Manuskript-Inhalte. Anonyme Session-IDs nach 90 Tagen löschen.

---

## 16. Modul L: Rechtliche Compliance

### 16.1 Die vier Risiko-Säulen

**AGB-Verstoß:** Direct-to-Source Prinzip — Aggregatoren technisch via `blacklist.yaml` gesperrt. Manuelles Recherchieren durch Admin erlaubt, automatisiertes Crawlen nie.

**Datenbankschutz §§ 87a ff. UrhG:** Eigenständige Datenbank aus Primärquellen — keine Übernahme kuratierter Sammlungen.

**Urheberrecht §2 UrhG:** Store More, Show Less — Originaltexte (Wishlist, Bio, Hard-Nos) werden intern gespeichert (§44b UrhG — Text and Data Mining erlaubt maschinelle Verarbeitung), aber im MVP-Frontend nicht veröffentlicht. Dadurch entfällt das Veröffentlichungsrisiko nach §2 UrhG. Die Anzeige von Originaltexten im Frontend kann später aktiviert werden — idealerweise nach medienrechtlicher Beratung. Keywords und Fakten werden angezeigt (nicht urheberrechtlich schützbar).

**DSGVO:** Opt-Out + "Für Agenten"-Informationsseite + Berechtigtes Interesse als Rechtsgrundlage.

### 16.2 Technische Compliance-Checkliste (vor Launch)

- [ ] `blacklist.yaml` technisch erzwungen — Exception bei Crawl-Versuch einer gesperrten Domain
- [ ] `robots.txt`-Parser aktiv vor jedem Domain-Crawl
- [ ] Rate Limiter: min. 2 Sekunden zwischen Requests pro Domain
- [ ] `*_raw`-Felder (wishlist\_raw, bio\_raw, hard\_nos\_raw) werden von öffentlichen API-Endpunkten **nicht** ausgeliefert — separate Pydantic-Schemas für intern vs. öffentlich
- [ ] Frontend zeigt keine Originaltexte — nur Keywords und Fakten
- [ ] Opt-Out-Seite live und öffentlich zugänglich
- [ ] "Für Agenten"-Informationsseite live (inkl. Hinweis auf intern gespeicherte Originaltexte)
- [ ] `opted_out = TRUE` serverseitig geprüft — nie nur clientseitig
- [ ] Bei Opt-Out: `*_raw`-Felder werden gelöscht (nicht nur ausgeblendet)
- [ ] Timestamp "Zuletzt aktualisiert" auf jedem Profil sichtbar
- [ ] Link zur Originalquelle auf jedem Profil sichtbar
- [ ] Pflicht-Hinweis zur Verifikation auf jedem Profil
- [ ] Account-Löschung löscht alle Nutzerdaten via CASCADE
- [ ] Interaction Logging in Datenschutzerklärung dokumentiert
- [ ] Tracking Opt-Out in Account-Einstellungen implementiert

---

## 17. Nicht-funktionale Anforderungen

| Operation | Ziel-Latenz |
|---|---|
| Matching gesamt (ohne LLM-Erklärung) | < 3 Sekunden |
| davon Query Expansion (gecacht nach erstem Run) | < 1 Sekunde |
| LLM-Erklärung (on demand) | < 10 Sekunden |
| Frontend Seiten-Load | < 2 Sekunden |
| Event Logging | Non-blocking (async) |

**Skalierung:** 500–5000 Agenten, bis 10.000 Nutzer, min. 20 concurrent Matchings ohne Performance-Degradation.

### 17.2 Backup & Disaster Recovery

**Backup-Strategie:** Tägliches `pg_dump` der gesamten PostgreSQL-Datenbank (inkl. pgvector-Daten). Backups werden komprimiert und auf ein separates Volume/Storage-System geschrieben (nicht dasselbe Filesystem wie die Datenbank). Retention: 7 tägliche Backups, 4 wöchentliche, 3 monatliche.

**Restore-Prozedur:** Muss vor Launch einmal vollständig getestet werden — `pg_restore` auf eine leere Datenbank, danach Verifikation dass pgvector-Indizes korrekt funktionieren (IVFFlat-Indizes werden mit-gebackupt und müssen nicht rebuilt werden, aber ein `REINDEX` nach Restore ist empfohlen). Die Restore-Prozedur muss dokumentiert und im Repository hinterlegt sein.

**Kritische Daten-Priorität:** Bei partiellem Datenverlust ist die Wiederherstellungs-Priorität: (1) `agents`-Tabelle inkl. Embeddings (Monate an Crawl- und Review-Arbeit), (2) `known_profile_urls` (verifizierte URL-Struktur), (3) `interaction_events` (Phase-2-Investition), (4) `users` und `manuscripts`.

**Docker-Volumes:** Alle persistenten Daten (PostgreSQL, Redis, Ollama-Modelle) liegen auf benannten Docker-Volumes die im `docker-compose.yml` explizit definiert sind — keine anonymen Volumes.

**Pflicht-Logging:** Crawl-Runs (Modul A), Extraktionen, Review-Entscheidungen, Matching-Metadaten (nur IDs und Scores, kein Inhalt), Interaction Events, Opt-Out-Requests, Fehler-Reports, Blacklist-Verstöße. Explizit ausgeschlossen: Originaltext von Agenten-Seiten, Manuskript-Inhalte.

### 17.1 Monitoring & Alerting

Es gibt zwei Kategorien von Benachrichtigungen: **Logs** (passiv, werden nur bei Bedarf eingesehen) und **Alerts** (aktive Benachrichtigung an den Admin). Alerts werden im MVP per E-Mail verschickt — ein Webhook-basiertes System (Slack, Discord) ist als Post-MVP-Erweiterung vorgesehen.

**Kritische Alerts (sofortige E-Mail an Admin):**

| Trigger | Quelle |
|---|---|
| Monatlicher Crawl-Job nicht gestartet (Celery Beat Watchdog) | Celery |
| Ollama-Container nicht erreichbar (Health-Check alle 5 Min.) | Docker |
| Datenbank-Speicher über 80% (täglicher Check) | PostgreSQL |
| Discard-Rate eines Crawl-Runs über 40% | Modul A (5.17) |
| Mehr als 10 `unreachable`-URLs derselben Domain in einem Run | Modul J |
| Embedding-Pipeline-Fehler (Modell nicht ladbar, Dimension Mismatch) | Modul D |
| Opt-Out-Request eingegangen (72h-Frist) | Modul K |

**Informations-Alerts (tägliche Zusammenfassung):**

| Trigger | Quelle |
|---|---|
| Neue Profile im Review-Queue | Modul B |
| Offene Recrawl-Requests | Modul J |
| Celery-Worker Restart aufgetreten | Celery |
| Fehlgeschlagene Login-Versuche über Schwellenwert | Modul I |

**Nur Logging (kein Alert):**

Einzelne Seiten-Fehler beim Crawl, reguläre Review-Entscheidungen, Matching-Requests, Interaction Events, erfolgreiche Crawl-Runs.

---

## 18. Roadmap: Phase 2 & 3

### Phase 2 — LightGBM (ab ~500 Interaktionen)

LightGBM oder XGBoost wird auf den geloggten Interaktionsdaten trainiert. Features sind die vier Phase-1-Einzel-Scores (genre\_score, audience\_score, fts\_score, semantic\_score) plus historische Agenten-Features aus den Events (wie oft wird dieser Agent kontaktiert, durchschnittliche Bewertung). Label: 1 für positive Interaktionen (contacted, full\_ms\_requested, offer\_received), 0 für negative (marked\_rejected, result\_ignored). Output: P(positives Outcome) ∈ [0,1].

LightGBM ist für Phase 2 die richtige Wahl weil es mit kleinen Datensätzen gut funktioniert, interpretierbar ist (Feature Importance zeigt welche Signale tatsächlich predictiv sind), und schnell zu trainieren ist.

Migration: Nur `scorer.py` in `matching/phase2/` wird ausgetauscht. `algorithm_version` in `matching_results` auf `"phase2_v1"` setzen.

**Phase-2-Zusatz — Diversity Upgrade:** Parallel zum LightGBM-Scoring wird MMR in Schicht 3 durch DPP (Determinantal Point Processes) ersetzt und Calibration als zusätzliche Schicht für proportionale Genre-Abdeckung ergänzt. Die Kernel-Matrix für DPP wird aus den Agenten-Embeddings gebaut. Ob DPP MMR tatsächlich übertrifft, wird per A/B-Test gemessen.

### Phase 3 — Fine-Tuned Retrieval mit Late Interaction (ab ~10.000 Interaktionen)

Die ursprüngliche Planung sah ein Two-Tower Neural Network nach Yi et al. (2019) vor. Aktuellere Forschung zeigt dass dieser Ansatz für unser Szenario suboptimal ist: Two-Tower wurde für YouTube-Scale (Milliarden Items, Milliarden Interaktionen) designt und trainiert Embeddings von Grund auf mit ID-basierten Features. Bei unserem kleinen Korpus (≤5.000 Items) entfällt das Effizienzargument vollständig — Cross-Encoder und Late-Interaction-Modelle sind in Echtzeit machbar.

**Primärer Ansatz — ColBERTv2 (Late Interaction):** ColBERT kodiert Queries und Dokumente unabhängig mit BERT, behält aber Token-Level-Repräsentationen bei statt in einen einzelnen Vektor zu poolen. Ein MaxSim-Operator berechnet fein-granulare Relevanz. Das ist ideal für asymmetrisches Text-Matching: der Operator identifiziert welche spezifischen Tokens in einer Manuskriptbeschreibung mit den Präferenzen eines Agentenprofils alignieren (Santhanam et al. 2022, NAACL). Bei ≤5.000 Items ist Full-Corpus-Scoring ohne Approximate Nearest Neighbor machbar.

**Alternativer Ansatz — Augmented SBERT Fine-Tuning:** Falls die Interaktionsdaten nicht für ColBERT-Training ausreichen: Ein Cross-Encoder generiert Silver-Labels auf rekombinierten Manuskript-Agenten-Paaren, dann wird der bestehende Bi-Encoder (BGE) auf dem augmentierten Datensatz fine-getuned. Designt für 1k–3k gelabelte Paare (Thakur et al. 2021, NAACL).

**Architektur-Guidance:** Für asymmetrisches Matching (langer Manuskript-Text vs. kurzes Agenten-Profil) eine Siamese-Architektur mit Shared Projection Layer verwenden, nicht vollständig getrennte Encoder. Moderne Embedding-Modelle wie BGE implementieren dies bereits über asymmetrische Instruction-Prefixe (Dong et al. 2022, EMNLP).

Migration: Embedding-Pipeline und Scorer werden ersetzt. Der pgvector-Index bleibt, alle Embeddings werden einmalig recomputed.

---

## 19. Offene Entscheidungen für den Entwickler

| # | Entscheidung | Empfehlung | Priorität |
|---|---|---|---|
| 1 | Embedding-Modell final | BGE-large als Start — vor Implementierung auf 50 realen Profilen benchmarken | **Hoch** |
| 2 | Embedding-Gewichtung (70/30) | Startwert — nach ersten 100 Matchings empirisch tunen | Mittel |
| 3 | Hard-Nos Threshold (0.75) | Startwert — nach ersten Review-Ergebnissen validieren | Mittel |
| 4 | Phase-2-Trigger (500/50/50) | Startwert — konfigurierbar halten | Mittel |
| 5 | Ollama-Modell | llama3 als Start | Mittel |
| 6 | Frontend-Framework | Next.js (SSR + SEO) | Mittel |
| 7 | Deployment-Umgebung | Außerhalb dieses Katalogs | Niedrig |
| 8 | E-Mail-Provider | SendGrid oder Resend | Niedrig |

---

*Dokument erstellt auf Basis von:*
- *Sasazawa & Sogawa (2025) "Web Page Classification using LLMs for Crawling Support"*
- *Carbonell & Goldstein (1998) "The Use of MMR, Diversity-Based Reranking"*
- *Chen, Zhang & Zhou (2018, NeurIPS) "Fast Greedy MAP Inference for Determinantal Point Process to Improve Recommendation Diversity"*
- *Steck (2018, RecSys) "Calibrated Recommendations" + Survey ACM TORS 2025*
- *Bruch, Gai & Ingber (2023, ACM TOIS) "An Analysis of Fusion Functions for Hybrid Retrieval" — Convex Combination statt RRF*
- *Sun, Wu, Nugent & Moore (2025, KAIS) "Cost-Effective Data Fusion in Information Retrieval" — minimale Trainingsdaten für Fusion-Gewichte*
- *Cormack, Clarke & Buettcher (2009) "Reciprocal Rank Fusion" — historische Referenz, in Phase 1 durch CC ersetzt*
- *Santhanam, Khattab et al. (2022, NAACL) "ColBERTv2" — Late Interaction Retrieval für Phase 3*
- *Thakur, Reimers et al. (2021, NAACL) "Augmented SBERT" — Small-Data Fine-Tuning für Phase 3*
- *Dong et al. (2022, EMNLP) "Exploring Dual Encoder Architectures" — Siamese vs. Asymmetric Design-Guidance*
- *BAAI/bge-large-en-v1.5 Model Card — Instruction Prefix für asymmetrisches Matching*
- *§44b UrhG, §§ 87a ff. UrhG, §2 UrhG, Art. 6 + 14 DSGVO*
