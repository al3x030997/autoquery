import Link from 'next/link'

export default function Footer() {
  return (
    <footer className="border-t border-border py-6 mt-auto">
      <div className="max-w-5xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted">
        <span>&copy; {new Date().getFullYear()} AutoQuery</span>
        <nav className="flex gap-4">
          <Link href="/fuer-agenten" className="hover:text-text transition-colors">Für Agenten</Link>
          <Link href="/opt-out" className="hover:text-text transition-colors">Opt-Out</Link>
          <Link href="/impressum" className="hover:text-text transition-colors">Impressum</Link>
          <Link href="/datenschutz" className="hover:text-text transition-colors">Datenschutz</Link>
        </nav>
      </div>
    </footer>
  )
}
