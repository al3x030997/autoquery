const FLOW_STATE_KEY = 'aq_flow_state'

export function saveFlowState<T>(state: T) {
  if (typeof window === 'undefined') return
  try {
    sessionStorage.setItem(FLOW_STATE_KEY, JSON.stringify(state))
  } catch {}
}

export function loadFlowState<T>(): T | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = sessionStorage.getItem(FLOW_STATE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function clearFlowState() {
  if (typeof window === 'undefined') return
  sessionStorage.removeItem(FLOW_STATE_KEY)
}
