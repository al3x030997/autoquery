'use client'

import { createContext, useCallback, useContext, useEffect, useReducer, type ReactNode } from 'react'
import type { FlowAnswers, UploadedFile } from '@/lib/types'
import { saveFlowState, loadFlowState } from '@/lib/session-storage'

interface FlowState {
  currentStep: number
  answers: FlowAnswers
  uploads: UploadedFile[]
  hasQueryLetter: boolean
}

const initialAnswers: FlowAnswers = {
  genre: [],
  audience: '',
  tone: '',
  themes: [],
  comps: '',
  queryLetterText: '',
  additionalNotes: '',
}

const initialState: FlowState = {
  currentStep: 0,
  answers: initialAnswers,
  uploads: [],
  hasQueryLetter: false,
}

type Action =
  | { type: 'SET_ANSWER'; field: keyof FlowAnswers; value: FlowAnswers[keyof FlowAnswers] }
  | { type: 'NEXT_STEP' }
  | { type: 'GO_TO_STEP'; step: number }
  | { type: 'ADD_UPLOAD'; file: UploadedFile }
  | { type: 'REMOVE_UPLOAD'; index: number }
  | { type: 'RESTORE'; state: FlowState }
  | { type: 'RESET' }

function reducer(state: FlowState, action: Action): FlowState {
  switch (action.type) {
    case 'SET_ANSWER': {
      const answers = { ...state.answers, [action.field]: action.value }
      return { ...state, answers }
    }
    case 'NEXT_STEP':
      return { ...state, currentStep: state.currentStep + 1 }
    case 'GO_TO_STEP':
      return { ...state, currentStep: action.step }
    case 'ADD_UPLOAD': {
      const uploads = [...state.uploads, action.file]
      const hasQueryLetter = uploads.some(u => u.category === 'query_letter')
      return { ...state, uploads, hasQueryLetter }
    }
    case 'REMOVE_UPLOAD': {
      const uploads = state.uploads.filter((_, i) => i !== action.index)
      const hasQueryLetter = uploads.some(u => u.category === 'query_letter')
      return { ...state, uploads, hasQueryLetter }
    }
    case 'RESTORE':
      return action.state
    case 'RESET':
      return initialState
    default:
      return state
  }
}

interface FlowContextValue {
  state: FlowState
  setAnswer: (field: keyof FlowAnswers, value: FlowAnswers[keyof FlowAnswers]) => void
  nextStep: () => void
  goToStep: (step: number) => void
  addUpload: (file: UploadedFile) => void
  removeUpload: (index: number) => void
  reset: () => void
}

const FlowCtx = createContext<FlowContextValue | null>(null)

export function FlowProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState)

  // Restore from session storage on mount
  useEffect(() => {
    const saved = loadFlowState<FlowState>()
    if (saved && saved.currentStep > 0) {
      dispatch({ type: 'RESTORE', state: saved })
    }
  }, [])

  // Persist to session storage on change
  useEffect(() => {
    if (state.currentStep > 0) {
      saveFlowState(state)
    }
  }, [state])

  const setAnswer = useCallback((field: keyof FlowAnswers, value: FlowAnswers[keyof FlowAnswers]) => {
    dispatch({ type: 'SET_ANSWER', field, value })
  }, [])

  const nextStep = useCallback(() => dispatch({ type: 'NEXT_STEP' }), [])
  const goToStep = useCallback((step: number) => dispatch({ type: 'GO_TO_STEP', step }), [])
  const addUpload = useCallback((file: UploadedFile) => dispatch({ type: 'ADD_UPLOAD', file }), [])
  const removeUpload = useCallback((index: number) => dispatch({ type: 'REMOVE_UPLOAD', index }), [])
  const reset = useCallback(() => dispatch({ type: 'RESET' }), [])

  return (
    <FlowCtx.Provider value={{ state, setAnswer, nextStep, goToStep, addUpload, removeUpload, reset }}>
      {children}
    </FlowCtx.Provider>
  )
}

export function useFlow() {
  const ctx = useContext(FlowCtx)
  if (!ctx) throw new Error('useFlow must be used within FlowProvider')
  return ctx
}
