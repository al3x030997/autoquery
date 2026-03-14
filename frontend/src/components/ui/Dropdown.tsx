'use client'

import { useState, useRef, useEffect } from 'react'

interface DropdownProps {
  options: string[]
  selected: string[]
  onChange: (selected: string[]) => void
  max?: number
  placeholder?: string
  formatLabel?: (value: string) => string
}

export default function Dropdown({ options, selected, onChange, max = 1, placeholder = 'Auswählen...', formatLabel }: DropdownProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const label = (v: string) => formatLabel ? formatLabel(v) : v

  const toggle = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter(s => s !== value))
    } else if (selected.length < max) {
      onChange([...selected, value])
    }
  }

  return (
    <div ref={ref} className="relative w-full">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-sm text-left flex items-center justify-between focus:outline-none focus:border-accent transition-colors"
      >
        <span className={selected.length ? 'text-text' : 'text-muted/60'}>
          {selected.length ? selected.map(label).join(', ') : placeholder}
        </span>
        <svg className={`w-4 h-4 text-muted transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="absolute z-50 mt-1 w-full max-h-60 overflow-y-auto bg-surface border border-border rounded-lg shadow-lg">
          {options.map(opt => (
            <button
              key={opt}
              type="button"
              onClick={() => toggle(opt)}
              className={`w-full text-left px-4 py-2 text-sm hover:bg-border/50 transition-colors flex items-center gap-2 ${
                selected.includes(opt) ? 'text-accent' : 'text-text'
              }`}
            >
              <span className={`w-4 h-4 rounded border flex-shrink-0 flex items-center justify-center text-xs ${
                selected.includes(opt) ? 'bg-accent border-accent text-stone-900' : 'border-muted'
              }`}>
                {selected.includes(opt) && '✓'}
              </span>
              {label(opt)}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
