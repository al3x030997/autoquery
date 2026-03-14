import { trackEvent } from './api'

export function fireEvent(
  eventType: string,
  manuscriptId?: number | null,
  agentId?: number | null,
  payload?: Record<string, unknown>
) {
  trackEvent({
    event_type: eventType,
    manuscript_id: manuscriptId ?? null,
    agent_id: agentId ?? null,
    payload: payload ?? null,
  })
}
