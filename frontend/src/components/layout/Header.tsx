'use client'

import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'

export default function Header() {
  const { user, logout } = useAuth()

  return (
    <header className="border-b border-border">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/" className="font-[family-name:var(--font-heading)] text-xl font-semibold text-accent">
          AutoQuery
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link href="/fuer-agenten" className="text-muted hover:text-text transition-colors">
            Für Agenten
          </Link>
          {user ? (
            <button onClick={logout} className="text-muted hover:text-text transition-colors">
              Abmelden
            </button>
          ) : (
            <Link href="/login" className="text-muted hover:text-text transition-colors">
              Einloggen
            </Link>
          )}
        </nav>
      </div>
    </header>
  )
}
