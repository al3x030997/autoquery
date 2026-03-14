export default function DatenschutzPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-16">
      <h1 className="font-[family-name:var(--font-heading)] text-3xl font-bold mb-6">Datenschutzerklärung</h1>
      <div className="text-sm text-muted space-y-4 leading-relaxed">
        <h2 className="text-lg font-semibold text-text">1. Verantwortlicher</h2>
        <p>[Wird vor Launch ergänzt]</p>

        <h2 className="text-lg font-semibold text-text">2. Erhobene Daten</h2>
        <p>
          Wir verarbeiten folgende Daten: E-Mail-Adresse und Passwort (bei Registrierung),
          Manuskript-Beschreibungen (Genre, Themen, Ton etc.), hochgeladene Dokumente (temporär zur Textextraktion),
          Interaktionsdaten (Klicks, Verweildauer — pseudonymisiert).
        </p>

        <h2 className="text-lg font-semibold text-text">3. Zweck der Verarbeitung</h2>
        <p>
          Bereitstellung des Matching-Services, Verbesserung der Ergebnisqualität,
          Validierung der Produkt-Hypothesen (anonymisierte Metriken).
        </p>

        <h2 className="text-lg font-semibold text-text">4. Speicherdauer</h2>
        <p>
          Manuskript-Daten werden gespeichert solange das Nutzerkonto existiert.
          Interaktionsdaten werden nach 12 Monaten anonymisiert.
          Hochgeladene Dateien werden nach der Textextraktion nicht dauerhaft gespeichert.
        </p>

        <h2 className="text-lg font-semibold text-text">5. Cookies</h2>
        <p>
          Wir verwenden einen funktionalen Session-Cookie zur Identifikation anonymer Nutzer.
          Dieser Cookie enthält keine personenbezogenen Daten.
          Es werden keine Tracking- oder Werbe-Cookies eingesetzt.
        </p>

        <h2 className="text-lg font-semibold text-text">6. Deine Rechte</h2>
        <p>
          Du hast das Recht auf Auskunft, Berichtigung, Löschung und Datenübertragbarkeit.
          Kontaktiere uns unter kontakt@autoquery.de.
        </p>

        <h2 className="text-lg font-semibold text-text">7. Agenten-Daten</h2>
        <p>
          Wir verarbeiten öffentlich zugängliche Informationen über Literaturagenten.
          Agenten können jederzeit die Entfernung ihres Profils über unser Opt-Out-Formular beantragen.
        </p>
      </div>
    </div>
  )
}
