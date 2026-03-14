export default function ImpressumPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-16">
      <h1 className="font-[family-name:var(--font-heading)] text-3xl font-bold mb-6">Impressum</h1>
      <div className="text-sm text-muted space-y-4 leading-relaxed">
        <p>Angaben gemäß § 5 TMG</p>
        <p>
          AutoQuery<br />
          [Adresse wird vor Launch ergänzt]<br />
          [Ort]
        </p>
        <p>
          <strong className="text-text">Kontakt:</strong><br />
          E-Mail: kontakt@autoquery.de
        </p>
        <p>
          <strong className="text-text">Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV:</strong><br />
          [Name wird vor Launch ergänzt]
        </p>
      </div>
    </div>
  )
}
