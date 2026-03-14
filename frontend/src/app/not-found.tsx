import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-8rem)] px-4 text-center">
      <h1 className="font-[family-name:var(--font-heading)] text-5xl font-bold text-accent mb-4">404</h1>
      <p className="text-muted mb-6">Diese Seite existiert nicht.</p>
      <Link href="/" className="text-accent hover:underline text-sm">Zurück zur Startseite</Link>
    </div>
  )
}
