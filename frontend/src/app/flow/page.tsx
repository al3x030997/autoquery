'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { FlowProvider, useFlow } from '@/context/FlowContext'
import ChatBubble from '@/components/flow/ChatBubble'
import QuestionRenderer from '@/components/flow/QuestionRenderer'
import FlowProgress from '@/components/flow/FlowProgress'
import { submitMatch } from '@/lib/api'
import type { ManuscriptInput } from '@/lib/types'
import { clearFlowState } from '@/lib/session-storage'

const QUESTIONS = [
  'Welches Genre hat dein Buch?',
  'Wer ist deine Zielgruppe?',
  'Beschreib den Ton deines Buchs in ein paar Worten.',
  'Welche Themen stehen im Zentrum?',
  'Mit welchen Büchern würdest du deins vergleichen?',
  'Hast du Dokumente die du hochladen möchtest?',
  'query_letter_fallback', // conditional — handled by renderer
  'Gibt es sonst noch etwas das uns bei der Suche helfen kann?',
]

function formatAnswer(step: number, state: ReturnType<typeof useFlow>['state']): string | null {
  const { answers, uploads } = state
  switch (step) {
    case 0: return answers.genre.map(g => g.split('_').map(w => w[0].toUpperCase() + w.slice(1)).join(' ')).join(', ')
    case 1: return answers.audience
    case 2: return answers.tone
    case 3: return answers.themes.join(', ')
    case 4: return answers.comps
    case 5: return uploads.length > 0 ? uploads.map(u => `${u.filename} (${u.category})`).join(', ') : 'Übersprungen'
    case 6: return !state.hasQueryLetter ? (answers.queryLetterText ? `${answers.queryLetterText.substring(0, 80)}...` : null) : null
    case 7: return answers.additionalNotes || 'Übersprungen'
    default: return null
  }
}

function FlowContent() {
  const router = useRouter()
  const { state, nextStep, goToStep } = useFlow()
  const { currentStep, answers, uploads, hasQueryLetter } = state
  const scrollRef = useRef<HTMLDivElement>(null)
  const [editing, setEditing] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Compute the total number of steps (skipping query_letter_fallback if QL uploaded)
  const totalSteps = hasQueryLetter ? 7 : 8

  // Determine which step is the "last" step (additional notes)
  const lastInputStep = hasQueryLetter ? 6 : 7

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [currentStep])

  const handleAnswer = () => {
    // If we just answered the last step, submit
    if (currentStep === lastInputStep) {
      doSubmit()
      return
    }
    // If hasQueryLetter and we're at step 5 (upload), skip the fallback (step 6)
    if (currentStep === 5 && hasQueryLetter) {
      // Jump to step 6 which maps to additional notes
      nextStep()
      return
    }
    nextStep()
  }

  const handleEditClick = (step: number) => {
    setEditing(step)
    goToStep(step)
  }

  const doSubmit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const input: ManuscriptInput = {
        genre: answers.genre[0] || '',
        audience: answers.audience,
        tone: answers.tone,
        themes: answers.themes,
        comps: answers.comps.split(',').map(s => s.trim()).filter(Boolean),
        query_letter: uploads.find(u => u.category === 'query_letter')?.text || answers.queryLetterText || '',
        synopsis: uploads.find(u => u.category === 'synopsis')?.text || '',
        additional_notes: answers.additionalNotes,
      }
      const result = await submitMatch(input)
      clearFlowState()
      router.push(`/loading-match?id=${result.manuscript_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Etwas ist schiefgelaufen.')
      setSubmitting(false)
    }
  }

  // Build conversation history
  const history: { step: number; question: string; answer: string }[] = []
  for (let i = 0; i < currentStep; i++) {
    // Skip the query_letter_fallback step if QL was uploaded
    if (i === 6 && hasQueryLetter) continue
    const q = QUESTIONS[i]
    if (q === 'query_letter_fallback') {
      if (!hasQueryLetter) {
        const ans = formatAnswer(i, state)
        if (ans) history.push({ step: i, question: 'Dann beschreib dein Buch bitte kurz in eigenen Worten — wie würdest du es einem Agenten pitchen?', answer: ans })
      }
      continue
    }
    const ans = formatAnswer(i, state)
    if (ans) history.push({ step: i, question: q, answer: ans })
  }

  // Get current question text
  let currentQuestion = QUESTIONS[currentStep]
  if (currentStep === 6 && !hasQueryLetter) {
    currentQuestion = 'Dann beschreib dein Buch bitte kurz in eigenen Worten — wie würdest du es einem Agenten pitchen?'
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <FlowProgress total={totalSteps} current={currentStep} />

      <div className="space-y-4 mt-6">
        {history.map(h => (
          <div key={h.step} className="space-y-2">
            <ChatBubble variant="question">{h.question}</ChatBubble>
            <ChatBubble variant="answer" onClick={() => handleEditClick(h.step)}>
              {h.answer}
            </ChatBubble>
          </div>
        ))}

        {!submitting && currentQuestion && currentQuestion !== 'query_letter_fallback' && (
          <div className="space-y-3">
            <ChatBubble variant="question">{currentQuestion}</ChatBubble>
            <div className="ml-4">
              <QuestionRenderer step={currentStep} onAnswer={handleAnswer} />
            </div>
          </div>
        )}

        {submitting && (
          <ChatBubble variant="question">
            <span className="animate-pulse">Matching wird gestartet...</span>
          </ChatBubble>
        )}

        {error && (
          <div className="bg-red-900/20 border border-red-800 rounded-lg p-3 text-sm text-red-300">
            {error}
            <button onClick={doSubmit} className="ml-2 underline hover:no-underline">Nochmal versuchen</button>
          </div>
        )}

        <div ref={scrollRef} />
      </div>
    </div>
  )
}

export default function FlowPage() {
  return (
    <FlowProvider>
      <FlowContent />
    </FlowProvider>
  )
}
