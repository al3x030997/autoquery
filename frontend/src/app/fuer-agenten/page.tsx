import Link from 'next/link'

export default function FuerAgentenPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-16">
      <h1 className="font-[family-name:var(--font-heading)] text-3xl font-bold mb-6">Für Agenten</h1>

      <div className="space-y-6 text-sm text-muted leading-relaxed">
        <p>
          AutoQuery hilft Autoren, passende Literaturagenten zu finden. Dafür analysieren wir öffentlich zugängliche Informationen
          von Agentur-Websites und Branchenverzeichnissen.
        </p>

        <h2 className="font-[family-name:var(--font-heading)] text-xl font-semibold text-text">Was wir speichern</h2>
        <ul className="list-disc list-inside space-y-1">
          <li>Name und Agentur</li>
          <li>Genre-Präferenzen und Keywords aus öffentlichen Profilen</li>
          <li>Submission-Anforderungen (Format, Umfang)</li>
          <li>Link zur Originalquelle</li>
        </ul>
        <p>
          Wir zeigen <strong className="text-text">keine Originalzitate</strong> aus Profilen. Alle angezeigten Informationen
          sind maschinell generierte Zusammenfassungen in Stichwortform.
        </p>

        <h2 className="font-[family-name:var(--font-heading)] text-xl font-semibold text-text">Opt-Out</h2>
        <p>
          Du möchtest nicht in AutoQuery erscheinen? Kein Problem — wir respektieren das.
          Nutze unser{' '}
          <Link href="/opt-out" className="text-accent hover:underline">Opt-Out-Formular</Link>{' '}
          und wir entfernen dein Profil schnellstmöglich.
        </p>

        <h2 className="font-[family-name:var(--font-heading)] text-xl font-semibold text-text">Kontakt</h2>
        <p>
          Fragen oder Anmerkungen? Schreib uns an{' '}
          <span className="text-text">kontakt@autoquery.de</span>
        </p>
      </div>
    </div>
  )
}
