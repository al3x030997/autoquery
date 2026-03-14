'use client'

import { useState, useEffect } from 'react'
import Dropdown from '@/components/ui/Dropdown'
import { TextInput, TextArea } from '@/components/ui/Input'
import TagInput from '@/components/ui/TagInput'
import Button from '@/components/ui/Button'
import UploadStep from './UploadStep'
import QueryLetterFallback from './QueryLetterFallback'
import { useFlow } from '@/context/FlowContext'
import { fetchGenres } from '@/lib/api'

const AUDIENCES = ['Adult', 'YA', 'Middle Grade', "Children's"]

function formatGenre(key: string): string {
  return key
    .split('_')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

interface QuestionRendererProps {
  step: number
  onAnswer: () => void
}

export default function QuestionRenderer({ step, onAnswer }: QuestionRendererProps) {
  const { state, setAnswer } = useFlow()
  const { answers, hasQueryLetter } = state
  const [genres, setGenres] = useState<string[]>([])

  useEffect(() => {
    fetchGenres().then(r => setGenres(r.genres)).catch(() => {})
  }, [])

  // Step 0: Genre
  if (step === 0) {
    return (
      <div className="space-y-3">
        <p className="text-xs text-muted">Wähle bis zu 3 Genres</p>
        <Dropdown
          options={genres}
          selected={answers.genre}
          onChange={val => setAnswer('genre', val)}
          max={3}
          placeholder="Genre auswählen..."
          formatLabel={formatGenre}
        />
        <Button onClick={onAnswer} disabled={answers.genre.length === 0}>Weiter</Button>
      </div>
    )
  }

  // Step 1: Audience
  if (step === 1) {
    return (
      <div className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {AUDIENCES.map(a => (
            <button
              key={a}
              type="button"
              onClick={() => setAnswer('audience', a)}
              className={`px-4 py-2 rounded-lg text-sm border transition-colors ${
                answers.audience === a
                  ? 'bg-accent/15 border-accent text-accent'
                  : 'bg-surface border-border text-text hover:border-muted'
              }`}
            >
              {a}
            </button>
          ))}
        </div>
        <Button onClick={onAnswer} disabled={!answers.audience}>Weiter</Button>
      </div>
    )
  }

  // Step 2: Tone
  if (step === 2) {
    return (
      <div className="space-y-3">
        <TextInput
          value={answers.tone}
          onChange={e => setAnswer('tone', e.target.value)}
          maxLength={200}
          placeholder="z.B. melancholisch, humorvoll, spannend, lyrisch"
        />
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted">{answers.tone.length}/200</span>
          <Button onClick={onAnswer} disabled={!answers.tone.trim()}>Weiter</Button>
        </div>
      </div>
    )
  }

  // Step 3: Themes
  if (step === 3) {
    return (
      <div className="space-y-3">
        <TagInput
          tags={answers.themes}
          onChange={val => setAnswer('themes', val)}
          min={2}
          max={8}
          placeholder="z.B. Found Family, Identität, Klimawandel"
        />
        <Button onClick={onAnswer} disabled={answers.themes.length < 2}>Weiter</Button>
      </div>
    )
  }

  // Step 4: Comps
  if (step === 4) {
    return (
      <div className="space-y-3">
        <p className="text-xs text-muted">Comp Titles sind das stärkste Signal — sie helfen uns am meisten.</p>
        <TextInput
          value={answers.comps}
          onChange={e => setAnswer('comps', e.target.value)}
          placeholder="z.B. Legends & Lattes meets The House in the Cerulean Sea"
        />
        <Button onClick={onAnswer} disabled={!answers.comps.trim()}>Weiter</Button>
      </div>
    )
  }

  // Step 5: Upload
  if (step === 5) {
    return <UploadStep onDone={onAnswer} onSkip={onAnswer} />
  }

  // Step 5b: Query letter fallback (only if no QL uploaded)
  if (step === 6 && !hasQueryLetter) {
    return (
      <QueryLetterFallback
        value={answers.queryLetterText}
        onChange={val => setAnswer('queryLetterText', val)}
        onSubmit={onAnswer}
      />
    )
  }

  // Step 6 (or 5b+1): Additional notes
  if (step === 6 && hasQueryLetter || step === 7) {
    return (
      <div className="space-y-3">
        <TextArea
          value={answers.additionalNotes}
          onChange={e => setAnswer('additionalNotes', e.target.value)}
          maxLength={300}
          rows={3}
          placeholder="z.B. Agent mit Erfahrung in Übersetzungsrechten, UK-basiert"
        />
        <div className="flex items-center gap-3">
          <Button onClick={onAnswer}>Matching starten</Button>
          <Button variant="ghost" onClick={onAnswer}>Überspringen</Button>
        </div>
      </div>
    )
  }

  return null
}
