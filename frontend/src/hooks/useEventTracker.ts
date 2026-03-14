'use client'

import { useCallback } from 'react'
import { fireEvent } from '@/lib/events'

export function useEventTracker(manuscriptId: number | null) {
  const track = useCallback(
    (eventType: string, agentId?: number, payload?: Record<string, unknown>) => {
      if (!manuscriptId) return
      fireEvent(eventType, manuscriptId, agentId ?? null, payload)
    },
    [manuscriptId]
  )

  return track
}
