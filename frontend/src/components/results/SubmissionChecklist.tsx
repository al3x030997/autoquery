'use client'

import { useEffect } from 'react'
import type { UploadedFile } from '@/lib/types'
import { fireEvent } from '@/lib/events'

interface Props {
  agentName: string
  agency: string | null
  submissionReq: Record<string, unknown>
  uploads: UploadedFile[]
  manuscriptId: number
  agentId: number
}

// Map common submission requirement keys to upload categories
const REQ_MAP: Record<string, { category: string; label: string }> = {
  query_letter: { category: 'query_letter', label: 'Query Letter' },
  query: { category: 'query_letter', label: 'Query Letter' },
  synopsis: { category: 'synopsis', label: 'Synopsis' },
  pages: { category: 'manuscript_excerpt', label: 'Manuskript-Ausschnitt' },
  sample_pages: { category: 'manuscript_excerpt', label: 'Manuskript-Ausschnitt' },
  first_pages: { category: 'manuscript_excerpt', label: 'Manuskript-Ausschnitt' },
  chapters: { category: 'manuscript_excerpt', label: 'Kapitel' },
  pitch: { category: 'pitch_deck', label: 'Pitch Deck' },
}

type Status = 'present' | 'missing' | 'check' | 'optional'

const ICONS: Record<Status, string> = {
  present: '✅',
  missing: '❌',
  check: '⚠️',
  optional: '○',
}

export default function SubmissionChecklist({ agentName, agency, submissionReq, uploads, manuscriptId, agentId }: Props) {
  useEffect(() => {
    fireEvent('submission_checklist', manuscriptId, agentId)
  }, [manuscriptId, agentId])

  const uploadCategories = uploads.map(u => u.category)

  const items: { status: Status; label: string; note?: string }[] = []

  for (const [key, value] of Object.entries(submissionReq)) {
    const mapped = REQ_MAP[key.toLowerCase()]
    if (!mapped) {
      // Unknown requirement — show as optional
      items.push({ status: 'optional', label: String(key), note: String(value || '') })
      continue
    }

    const isOptional = typeof value === 'string' && value.toLowerCase().includes('optional')
    const hasUpload = uploadCategories.includes(mapped.category)

    if (isOptional) {
      items.push({ status: 'optional', label: `${mapped.label} (optional)` })
    } else if (hasUpload) {
      items.push({ status: 'present', label: `${mapped.label} (vorhanden)` })
    } else if (mapped.category === 'manuscript_excerpt' && uploadCategories.includes('manuscript_excerpt')) {
      items.push({ status: 'check', label: `${mapped.label} (hochgeladen — prüfe Seitenzahl)` })
    } else {
      items.push({ status: 'missing', label: `${mapped.label} (nicht vorhanden)` })
    }
  }

  if (items.length === 0) return null

  return (
    <div>
      <p className="text-sm font-medium mb-2">
        Für {agentName}{agency ? ` bei ${agency}` : ''} brauchst du:
      </p>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-sm">
            <span>{ICONS[item.status]}</span>
            <span className="text-text">{item.label}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
