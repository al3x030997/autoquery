'use client'

import { useCallback, useRef, useState, type DragEvent } from 'react'

const ACCEPTED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
]

const ACCEPTED_EXT = '.pdf,.docx,.txt'
const MAX_SIZE = 10 * 1024 * 1024 // 10 MB

interface FileUploadProps {
  onFiles: (files: File[]) => void
  disabled?: boolean
}

export default function FileUpload({ onFiles, disabled }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const validate = useCallback((files: File[]): File[] => {
    const valid: File[] = []
    for (const f of files) {
      if (!ACCEPTED_TYPES.includes(f.type) && !f.name.match(/\.(pdf|docx|txt)$/i)) {
        setError(`${f.name}: Nur .pdf, .docx und .txt erlaubt`)
        return []
      }
      if (f.size > MAX_SIZE) {
        setError(`${f.name}: Max. 10 MB`)
        return []
      }
      valid.push(f)
    }
    setError(null)
    return valid
  }, [])

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    if (disabled) return
    const files = validate(Array.from(e.dataTransfer.files))
    if (files.length) onFiles(files)
  }

  const handleChange = () => {
    const el = inputRef.current
    if (!el?.files) return
    const files = validate(Array.from(el.files))
    if (files.length) onFiles(files)
    el.value = ''
  }

  return (
    <div>
      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          dragOver ? 'border-accent bg-accent/5' : 'border-border hover:border-muted'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <p className="text-sm text-muted">
          Dateien hierher ziehen oder <span className="text-accent">durchsuchen</span>
        </p>
        <p className="text-xs text-muted/60 mt-1">.pdf, .docx, .txt — max. 10 MB</p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXT}
          multiple
          onChange={handleChange}
          className="hidden"
        />
      </div>
      {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
    </div>
  )
}
