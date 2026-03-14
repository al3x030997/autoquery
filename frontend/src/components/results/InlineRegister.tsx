'use client'

import { useState } from 'react'
import { TextInput } from '@/components/ui/Input'
import Button from '@/components/ui/Button'
import { useAuth } from '@/hooks/useAuth'
import { fireEvent } from '@/lib/events'
import Link from 'next/link'

interface Props {
  remainingCount: number
  manuscriptId: number
  onRegistered: () => void
}

export default function InlineRegister({ remainingCount, manuscriptId, onRegistered }: Props) {
  const { register } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [privacy, setPrivacy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!privacy) { setError('Bitte akzeptiere die Datenschutzerklärung.'); return }
    if (password.length < 8) { setError('Mindestens 8 Zeichen.'); return }
    setLoading(true)
    setError(null)
    try {
      await register(email, password)
      fireEvent('signup_completed', manuscriptId)
      onRegistered()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Registrierung fehlgeschlagen'
      if (msg.includes('already') || msg.includes('existiert')) {
        setError('Diese E-Mail ist bereits registriert.')
      } else {
        setError(msg)
      }
      setLoading(false)
    }
  }

  return (
    <div className="bg-surface border border-accent/30 rounded-xl p-6 text-center">
      <p className="font-[family-name:var(--font-heading)] text-xl font-semibold mb-1">
        {remainingCount} weitere Agenten gefunden.
      </p>
      <p className="text-sm text-muted mb-5">
        Erstelle ein kostenloses Konto um alle zu sehen.
      </p>

      <form onSubmit={handleSubmit} className="max-w-sm mx-auto space-y-3">
        <TextInput
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="E-Mail"
          required
        />
        <TextInput
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          placeholder="Passwort (min. 8 Zeichen)"
          minLength={8}
          required
        />
        <label className="flex items-start gap-2 text-xs text-muted text-left">
          <input
            type="checkbox"
            checked={privacy}
            onChange={e => setPrivacy(e.target.checked)}
            className="mt-0.5 accent-accent"
          />
          <span>
            Ich akzeptiere die{' '}
            <Link href="/datenschutz" className="text-accent hover:underline" target="_blank">
              Datenschutzerklärung
            </Link>
          </span>
        </label>
        {error && (
          <p className="text-xs text-red-400">
            {error}{' '}
            {error.includes('registriert') && (
              <Link href="/login" className="text-accent hover:underline">Einloggen?</Link>
            )}
          </p>
        )}
        <Button type="submit" fullWidth disabled={loading}>
          {loading ? 'Wird erstellt...' : 'Kostenlos registrieren'}
        </Button>
      </form>
    </div>
  )
}
