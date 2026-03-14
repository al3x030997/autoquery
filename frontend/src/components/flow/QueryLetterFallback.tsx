'use client'

import { useState } from 'react'
import { TextArea } from '@/components/ui/Input'
import Button from '@/components/ui/Button'

interface Props {
  value: string
  onChange: (val: string) => void
  onSubmit: () => void
}

function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length
}

export default function QueryLetterFallback({ value, onChange, onSubmit }: Props) {
  const [touched, setTouched] = useState(false)
  const wc = wordCount(value)
  const valid = wc >= 100 && wc <= 1000

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted">
        Da du keinen Query Letter hochgeladen hast, beschreib dein Buch bitte kurz — wie würdest du es einem Agenten pitchen?
      </p>
      <TextArea
        value={value}
        onChange={e => { onChange(e.target.value); setTouched(true) }}
        rows={8}
        placeholder="Beschreib dein Buch in eigenen Worten..."
      />
      <div className="flex items-center justify-between">
        <span className={`text-xs ${wc < 100 ? 'text-muted' : wc > 1000 ? 'text-red-400' : 'text-green-400'}`}>
          {wc} / 100–1000 Wörter
        </span>
        <Button onClick={onSubmit} disabled={!valid}>Weiter</Button>
      </div>
      {touched && wc < 100 && (
        <p className="text-xs text-red-400">Mindestens 100 Wörter erforderlich.</p>
      )}
    </div>
  )
}
