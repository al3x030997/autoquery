'use client'

import { useState } from 'react'
import FileUpload from '@/components/ui/FileUpload'
import { uploadFile } from '@/lib/api'
import { useFlow } from '@/context/FlowContext'
import Button from '@/components/ui/Button'

const CATEGORIES = [
  { value: 'query_letter', label: 'Query Letter' },
  { value: 'synopsis', label: 'Synopsis' },
  { value: 'manuscript_excerpt', label: 'Manuskript-Ausschnitt' },
  { value: 'pitch_deck', label: 'Pitch Deck / One-Pager' },
]

interface PendingFile {
  file: File
  category: string
  uploading: boolean
  done: boolean
  error?: string
}

interface UploadStepProps {
  onDone: () => void
  onSkip: () => void
}

export default function UploadStep({ onDone, onSkip }: UploadStepProps) {
  const { addUpload } = useFlow()
  const [pending, setPending] = useState<PendingFile[]>([])

  const handleFiles = (files: File[]) => {
    const newPending = files.map(file => ({
      file,
      category: 'query_letter',
      uploading: false,
      done: false,
    }))
    setPending(prev => [...prev, ...newPending])
  }

  const setCategory = (index: number, category: string) => {
    setPending(prev => prev.map((p, i) => i === index ? { ...p, category } : p))
  }

  const uploadAll = async () => {
    const toUpload = pending.filter(p => !p.done)
    if (!toUpload.length) { onDone(); return }

    for (let i = 0; i < pending.length; i++) {
      if (pending[i].done) continue
      setPending(prev => prev.map((p, j) => j === i ? { ...p, uploading: true } : p))
      try {
        const res = await uploadFile(pending[i].file, pending[i].category)
        addUpload({
          category: res.category,
          filename: res.filename,
          text: res.text,
          wordCount: res.word_count,
        })
        setPending(prev => prev.map((p, j) => j === i ? { ...p, uploading: false, done: true } : p))
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Upload fehlgeschlagen'
        setPending(prev => prev.map((p, j) => j === i ? { ...p, uploading: false, error: msg } : p))
      }
    }
    onDone()
  }

  const removePending = (index: number) => {
    setPending(prev => prev.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-4">
      <FileUpload onFiles={handleFiles} />

      {pending.length > 0 && (
        <div className="space-y-2">
          {pending.map((p, i) => (
            <div key={i} className="flex items-center gap-2 bg-surface border border-border rounded-lg px-3 py-2 text-sm">
              {p.done ? (
                <span className="text-green-400">✓</span>
              ) : p.uploading ? (
                <span className="text-accent animate-pulse">↑</span>
              ) : p.error ? (
                <span className="text-red-400">!</span>
              ) : (
                <span className="text-muted">○</span>
              )}
              <span className="flex-1 truncate">{p.file.name}</span>
              {!p.done && !p.uploading && (
                <>
                  <select
                    value={p.category}
                    onChange={e => setCategory(i, e.target.value)}
                    className="bg-bg border border-border rounded px-2 py-1 text-xs"
                  >
                    {CATEGORIES.map(c => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                  <button onClick={() => removePending(i)} className="text-muted hover:text-red-400 text-xs">&times;</button>
                </>
              )}
              {p.error && <span className="text-xs text-red-400">{p.error}</span>}
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-3">
        {pending.length > 0 && (
          <Button onClick={uploadAll} disabled={pending.some(p => p.uploading)}>
            {pending.some(p => p.uploading) ? 'Wird hochgeladen...' : 'Hochladen'}
          </Button>
        )}
        <Button variant="ghost" onClick={onSkip}>
          {pending.length > 0 ? 'Ohne weitere Dateien fortfahren' : 'Überspringen'}
        </Button>
      </div>
    </div>
  )
}
