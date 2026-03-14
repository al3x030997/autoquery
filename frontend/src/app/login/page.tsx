'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { TextInput } from '@/components/ui/Input'
import Button from '@/components/ui/Button'
import { useAuth } from '@/hooks/useAuth'
import Link from 'next/link'

export default function LoginPage() {
  const router = useRouter()
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await login(email, password)
      router.push('/flow')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login fehlgeschlagen')
      setLoading(false)
    }
  }

  return (
    <div className="max-w-sm mx-auto px-4 py-16">
      <h1 className="font-[family-name:var(--font-heading)] text-2xl font-bold mb-6 text-center">Einloggen</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
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
          placeholder="Passwort"
          required
        />
        {error && <p className="text-xs text-red-400">{error}</p>}
        <Button type="submit" fullWidth disabled={loading}>
          {loading ? 'Wird eingeloggt...' : 'Einloggen'}
        </Button>
      </form>
      <p className="text-xs text-muted text-center mt-4">
        Noch kein Konto? <Link href="/flow" className="text-accent hover:underline">Starte ein Matching</Link> und registriere dich bei den Ergebnissen.
      </p>
    </div>
  )
}
