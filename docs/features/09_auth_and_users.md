# Feature 09 — Auth & Nutzer

> Lies zuerst: `PROJECT_CONTEXT.md` | Master-Referenz: Modul I (13.1–13.3)

## Scope

JWT-Auth, Registrierung, Login, Zugangsmodell, Freemium-Vorbereitung, Frontend-Sicherheit. **Kein Passwort-Reset im MVP** (Sprint 2).

## Dateien

```
api/routes/
└── auth.py    # Login, Register, Token-Refresh
```

---

## Zugangsmodell

| Feature | Ohne Konto | Mit Konto |
|---|---|---|
| Conversational Flow + Upload | ✅ | ✅ |
| Matching auslösen | ✅ | ✅ |
| Anzahl Ergebnisse | Max. 3 | Bis 20 |
| Profil aufklappen | ❌ | ✅ |
| Submission-Checkliste | ❌ | ✅ |

---

## Authentifizierung

- E-Mail + Passwort (bcrypt Hashing)
- E-Mail-Verifizierung bei Registrierung (non-blocking — Nutzer kann sofort weiterarbeiten)
- JWT: Access Token + Refresh Token
- Kein Social Login im MVP
- Kein Passwort-Reset im MVP

## Freemium-Vorbereitung

`plan`-Feld in `users` mit Default `'free'`. Alle Feature-Checks über zentrale Feature-Flag-Funktion — nie hardcoded.

---

## Frontend-Sicherheit

**Rate Limiting:**
- Login/Register: max. 5 Versuche pro IP / 15 Min
- Matching-Endpoint: max. 10 pro Nutzer / Stunde

**Input-Sanitization:** Alle Freitext-Felder serverseitig sanitized — HTML-Tags strippen. Keine User-Inputs als HTML rendern. Pydantic-Validierung mit Längen-Limits.

**CSRF:** JWT in HttpOnly-Cookies mit SameSite=Strict ODER Bearer Token im Authorization-Header.

**File-Upload-Validierung:** MIME-Type serverseitig prüfen (nicht nur Extension). Akzeptiert: .docx, .txt, .pdf. Max. 10 MB. Dateiname sanitizen.
