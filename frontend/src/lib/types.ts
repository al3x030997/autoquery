// Auth
export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface User {
  id: number
  email: string
  plan: string
}

// Matching
export interface ManuscriptInput {
  genre: string
  audience: string
  tone: string
  themes: string[]
  comps: string[]
  query_letter: string
  synopsis: string
  additional_notes: string
}

export interface MatchResponse {
  manuscript_id: number
  results: ScoredAgent[]
  total_found: number
}

export interface ScoredAgent {
  agent: AgentPublic
  composite_score: number
  mmr_rank: number | null
  match_tags: MatchTag[]
  snippet: string
  scores: ScoreBreakdown
}

export interface MatchTag {
  dimension: string
  indicator: string  // "match" | "partial" | "mismatch"
  label: string
}

export interface ScoreBreakdown {
  genre_score: number
  fts_score: number
  semantic_score: number
  audience_score: number
}

export interface AgentPublic {
  id: number
  name: string
  agency: string | null
  profile_url: string
  genres: string[] | null
  keywords: string[] | null
  audience: string[] | null
  hard_nos_keywords: string[] | null
  submission_req: Record<string, unknown> | null
  is_open: boolean | null
  review_status: string
  opted_out: boolean
}

// Upload
export interface UploadResponse {
  text: string
  word_count: number
  category: string
  filename: string
}

// Events
export interface EventInput {
  event_type: string
  manuscript_id?: number | null
  agent_id?: number | null
  payload?: Record<string, unknown> | null
}

// Opt-out
export interface OptOutInput {
  agent_name: string
  contact_email: string
  reason?: string
}

// Flow state
export interface FlowAnswers {
  genre: string[]
  audience: string
  tone: string
  themes: string[]
  comps: string
  queryLetterText: string
  additionalNotes: string
}

export interface UploadedFile {
  category: string
  filename: string
  text: string
  wordCount: number
}
