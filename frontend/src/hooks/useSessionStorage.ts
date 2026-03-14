'use client'

import { useEffect } from 'react'
import { saveFlowState, loadFlowState } from '@/lib/session-storage'

export function useSessionPersist<T>(state: T) {
  useEffect(() => {
    saveFlowState(state)
  }, [state])
}

export function loadPersistedState<T>(): T | null {
  return loadFlowState<T>()
}
