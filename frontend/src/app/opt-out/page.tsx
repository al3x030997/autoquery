'use client'

import { useState } from 'react'
import { TextInput, TextArea } from '@/components/ui/Input'
import Button from '@/components/ui/Button'
import { submitOptOut } from '@/lib/api'

export default function OptOutPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [reason, setReason] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await submitOptOut({ agent_name: name, contact_email: email, reason: reason || undefined })
      setSubmitted(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Senden.')
      setLoading(false)
    }
  }

  if (submitted) {
    return (
      <div className="max-w-lg mx-auto px-4 py-16 text-center">
        <h1 className="font-[family-name:var(--font-heading)] text-2xl font-bold mb-4">Anfrage erhalten</h1>
        <p className="text-muted">Wir werden dein Profil schnellstmöglich entfernen. Du erhältst eine Bestätigung per E-Mail.</p>
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-16">
      <h1 className="font-[family-name:var(--font-heading)] text-2xl font-bold mb-2">Opt-Out</h1>
      <p className="text-sm text-muted mb-6">
        Als Agent kannst du hier die Entfernung deines Profils aus AutoQuery beantragen.
      </p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-xs text-muted block mb-1">Name / Agentur</label>
          <TextInput value={name} onChange={e => setName(e.target.value)} required placeholder="Dein Name oder Agentur" />
        </div>
        <div>
          <label className="text-xs text-muted block mb-1">Kontakt-E-Mail</label>
          <TextInput type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="deine@email.de" />
        </div>
        <div>
          <label className="text-xs text-muted block mb-1">Grund (optional)</label>
          <TextArea value={reason} onChange={e => setReason(e.target.value)} rows={3} placeholder="Optional: Warum möchtest du entfernt werden?" />
        </div>
        {error && <p className="text-xs text-red-400">{error}</p>}
        <Button type="submit" disabled={loading}>
          {loading ? 'Wird gesendet...' : 'Opt-Out beantragen'}
        </Button>
      </form>
    </div>
  )
}
