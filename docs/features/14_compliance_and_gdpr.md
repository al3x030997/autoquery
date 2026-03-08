# Feature 14 — Compliance & DSGVO

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Modul K (15.1–15.4), Modul L (16.1–16.2)

## Scope

Alles Rechtliche an einem Ort: Opt-Out, Informationspflicht, Rechtsgrundlagen, Urheberrecht, AGB-Compliance, technische Checkliste.

---

## Die vier Risiko-Säulen

**1. AGB-Verstoß:** Direct-to-Source — Aggregatoren technisch via `blacklist.yaml` gesperrt.

**2. Datenbankschutz §§ 87a ff. UrhG:** Eigenständige DB aus Primärquellen — keine Übernahme kuratierter Sammlungen.

**3. Urheberrecht §2 UrhG:** Store More, Show Less. Originaltexte (Wishlist, Bio, Hard-Nos) werden intern gespeichert (§44b UrhG — TDM erlaubt maschinelle Verarbeitung), aber im MVP-Frontend **nicht veröffentlicht**. Dadurch entfällt das Veröffentlichungsrisiko. Anzeige kann später aktiviert werden — idealerweise nach medienrechtlicher Beratung. Keywords und Fakten werden angezeigt (nicht schützbar).

**4. DSGVO:** Opt-Out + Informationsseite + Berechtigtes Interesse als Rechtsgrundlage.

---

## Opt-Out für Agenten

- Öffentliche Opt-Out-Seite ohne Login
- Formular: Name, Agentur-URL, Kontakt-E-Mail, optionaler Freitext
- Bearbeitung binnen **72 Stunden**
- Agent → `opted_out = TRUE`, Domain → `blacklist.yaml`
- **`*_raw`-Felder werden gelöscht** (nicht nur ausgeblendet)
- Bestätigung per E-Mail

## Informationspflicht Art. 14 DSGVO

Öffentliche "Für Agenten"-Seite erklärt: was AutoQuery ist, welche Daten gespeichert werden (Fakten, Keywords, Embeddings, und Originaltexte der Profilseite — intern, nicht öffentlich angezeigt), Opt-Out-Anleitung, Kontakt.

## Rechtsgrundlagen

- Agenten-Daten: Art. 6 Abs. 1 lit. f DSGVO — Berechtigtes Interesse (Traffic-Zuführung)
- Nutzerdaten: Art. 6 Abs. 1 lit. b — Vertragserfüllung

## Interaction Logging & DSGVO

- In Datenschutzerklärung dokumentieren
- Opt-Out in Account-Einstellungen
- Events enthalten keine Manuskript-Inhalte
- Anonyme Session-IDs nach 90 Tagen löschen

---

## Technische Compliance-Checkliste (vor Launch)

- [ ] `blacklist.yaml` technisch erzwungen — Exception bei gesperrter Domain
- [ ] `robots.txt`-Parser aktiv vor jedem Domain-Crawl
- [ ] Rate Limiter: min. 2s zwischen Requests pro Domain
- [ ] `*_raw`-Felder werden von öffentlichen API-Endpunkten **nicht** ausgeliefert — separate Pydantic-Schemas
- [ ] Frontend zeigt keine Originaltexte — nur Keywords und Fakten
- [ ] Opt-Out-Seite live und öffentlich
- [ ] "Für Agenten"-Informationsseite live (inkl. Hinweis auf intern gespeicherte Originaltexte)
- [ ] `opted_out = TRUE` serverseitig geprüft
- [ ] Bei Opt-Out: `*_raw`-Felder werden gelöscht
- [ ] Timestamp "Zuletzt aktualisiert" auf jedem Profil
- [ ] Link zur Originalquelle auf jedem Profil
- [ ] Pflicht-Hinweis zur Verifikation auf jedem Profil
- [ ] Account-Löschung löscht alle Nutzerdaten via CASCADE
- [ ] Interaction Logging in Datenschutzerklärung
- [ ] Tracking Opt-Out in Account-Einstellungen
