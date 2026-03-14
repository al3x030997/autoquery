import { getAccessToken } from './auth'
import type {
  TokenResponse,
  ManuscriptInput,
  MatchResponse,
  UploadResponse,
  EventInput,
  OptOutInput,
} from './types'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAccessToken()
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  // Only set Content-Type for non-FormData bodies
  if (init?.body && !(init.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, body.detail || res.statusText)
  }

  return res.json()
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

// Auth
export function register(email: string, password: string) {
  return request<TokenResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function login(email: string, password: string) {
  return request<TokenResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function refreshToken(refresh_token: string) {
  return request<TokenResponse>('/api/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token }),
  })
}

// Genres
export function fetchGenres() {
  return request<{ genres: string[] }>('/api/genres')
}

// Upload
export function uploadFile(file: File, category: string) {
  const form = new FormData()
  form.append('file', file)
  form.append('category', category)
  return request<UploadResponse>('/api/upload', {
    method: 'POST',
    body: form,
  })
}

// Match
export function submitMatch(input: ManuscriptInput) {
  return request<MatchResponse>('/api/match', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function fetchResults(manuscriptId: number) {
  return request<MatchResponse>(`/api/results/${manuscriptId}`)
}

// Events
export function trackEvent(event: EventInput) {
  // Fire-and-forget
  request('/api/events', {
    method: 'POST',
    body: JSON.stringify(event),
  }).catch(() => {})
}

// Opt-out
export function submitOptOut(input: OptOutInput) {
  return request<{ id: number; status: string }>('/api/opt-out', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}
