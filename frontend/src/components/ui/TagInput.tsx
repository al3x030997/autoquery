'use client'

import { useState, KeyboardEvent } from 'react'

interface TagInputProps {
  tags: string[]
  onChange: (tags: string[]) => void
  min?: number
  max?: number
  placeholder?: string
}

export default function TagInput({ tags, onChange, min = 0, max = 8, placeholder = 'Tag eingeben + Enter' }: TagInputProps) {
  const [input, setInput] = useState('')

  const addTag = (value: string) => {
    const trimmed = value.trim()
    if (!trimmed || tags.includes(trimmed) || tags.length >= max) return
    onChange([...tags, trimmed])
    setInput('')
  }

  const removeTag = (index: number) => {
    onChange(tags.filter((_, i) => i !== index))
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addTag(input)
    } else if (e.key === 'Backspace' && !input && tags.length > 0) {
      removeTag(tags.length - 1)
    }
  }

  return (
    <div className="w-full">
      <div className="flex flex-wrap gap-1.5 mb-2">
        {tags.map((tag, i) => (
          <span key={i} className="inline-flex items-center gap-1 bg-accent/20 text-accent text-xs px-2.5 py-1 rounded-full">
            {tag}
            <button type="button" onClick={() => removeTag(i)} className="hover:text-text transition-colors">&times;</button>
          </span>
        ))}
      </div>
      <input
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => { if (input.trim()) addTag(input) }}
        placeholder={tags.length >= max ? `Max. ${max} erreicht` : placeholder}
        disabled={tags.length >= max}
        className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-sm text-text placeholder:text-muted/60 focus:outline-none focus:border-accent transition-colors disabled:opacity-50"
      />
      {min > 0 && tags.length < min && (
        <p className="text-xs text-muted mt-1">Mindestens {min} Tags</p>
      )}
    </div>
  )
}
