import { InputHTMLAttributes, TextareaHTMLAttributes } from 'react'

const base = 'w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-sm text-text placeholder:text-muted/60 focus:outline-none focus:border-accent transition-colors'

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${base} ${props.className || ''}`} />
}

export function TextArea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`${base} resize-none ${props.className || ''}`} />
}
