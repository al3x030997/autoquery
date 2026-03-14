'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { AnimatePresence } from 'framer-motion'
import { fetchResults } from '@/lib/api'
import { fireEvent } from '@/lib/events'
import { useAuth } from '@/hooks/useAuth'
import { useEventTracker } from '@/hooks/useEventTracker'
import { loadFlowState } from '@/lib/session-storage'
import AgentCard from '@/components/results/AgentCard'
import AgentCardExpanded from '@/components/results/AgentCardExpanded'
import InlineRegister from '@/components/results/InlineRegister'
import FeedbackBanner from '@/components/results/FeedbackBanner'
import type { MatchResponse, UploadedFile } from '@/lib/types'

export default function ResultsPage() {
  const params = useParams()
  const manuscriptId = Number(params.id)
  const { user } = useAuth()
  const track = useEventTracker(manuscriptId)

  const [data, setData] = useState<MatchResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [uploads, setUploads] = useState<UploadedFile[]>([])

  // Load uploads from session (for checklist)
  useEffect(() => {
    const saved = loadFlowState<{ uploads?: UploadedFile[] }>()
    if (saved?.uploads) setUploads(saved.uploads)
  }, [])

  // Fetch results
  useEffect(() => {
    let cancelled = false
    setError(null)
    fetchResults(manuscriptId)
      .then(res => {
        if (!cancelled) setData(res)
      })
      .catch(err => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Fehler beim Laden.')
      })
    return () => { cancelled = true }
  }, [manuscriptId, user]) // re-fetch when user changes (after registration)

  // Log result_shown events
  useEffect(() => {
    if (!data) return
    data.results.forEach(r => {
      fireEvent('result_shown', manuscriptId, r.agent.id)
    })
    if (!user && data.total_found > data.results.length) {
      fireEvent('signup_cta_shown', manuscriptId)
    }
  }, [data, manuscriptId, user])

  const handleCardClick = (agentId: number) => {
    if (!user) return // no expanding for guests
    track('card_clicked', agentId)
    setExpandedId(expandedId === agentId ? null : agentId)
  }

  const handleRegistered = () => {
    // Re-fetch with auth will happen via the user dependency in useEffect
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <p className="text-red-400 mb-4">{error}</p>
        <button onClick={() => window.location.reload()} className="text-accent hover:underline text-sm">
          Nochmal versuchen
        </button>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <p className="text-muted animate-pulse">Ergebnisse werden geladen...</p>
      </div>
    )
  }

  const results = data.results
  const totalFound = data.total_found
  const remaining = totalFound - results.length
  const isGuest = !user

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="font-[family-name:var(--font-heading)] text-2xl font-bold mb-1">
        {totalFound} passende Agenten gefunden
      </h1>
      <p className="text-sm text-muted mb-6">
        {isGuest ? `Du siehst ${results.length} von ${totalFound} Ergebnissen.` : 'Klicke auf eine Karte für Details.'}
      </p>

      <div className="space-y-4">
        <AnimatePresence mode="sync">
          {results.map((r, i) => {
            const isExpanded = expandedId === r.agent.id
            if (isExpanded) {
              return (
                <AgentCardExpanded
                  key={r.agent.id}
                  result={r}
                  rank={r.mmr_rank ?? i + 1}
                  manuscriptId={manuscriptId}
                  uploads={uploads}
                  onCollapse={() => setExpandedId(null)}
                />
              )
            }
            return (
              <AgentCard
                key={r.agent.id}
                result={r}
                rank={r.mmr_rank ?? i + 1}
                onClick={() => handleCardClick(r.agent.id)}
                expandable={!!user}
              />
            )
          })}
        </AnimatePresence>
      </div>

      {/* CTA for guests */}
      {isGuest && remaining > 0 && (
        <div className="mt-8">
          <InlineRegister
            remainingCount={remaining}
            manuscriptId={manuscriptId}
            onRegistered={handleRegistered}
          />
        </div>
      )}

      {/* Feedback banner */}
      {user && <FeedbackBanner manuscriptId={manuscriptId} />}
    </div>
  )
}
