'use client'

import { useEffect } from 'react'
import { motion } from 'framer-motion'
import Card from '@/components/ui/Card'
import ScoreBar from '@/components/ui/ScoreBar'
import MatchTagComp from '@/components/ui/MatchTag'
import SubmissionChecklist from './SubmissionChecklist'
import type { ScoredAgent, UploadedFile } from '@/lib/types'
import { fireEvent } from '@/lib/events'

interface Props {
  result: ScoredAgent
  rank: number
  manuscriptId: number
  uploads: UploadedFile[]
  onCollapse: () => void
}

export default function AgentCardExpanded({ result, rank, manuscriptId, uploads, onCollapse }: Props) {
  const { agent, composite_score, match_tags } = result

  useEffect(() => {
    fireEvent('profile_expanded', manuscriptId, agent.id)
  }, [manuscriptId, agent.id])

  const handleSourceClick = () => {
    fireEvent('source_link_clicked', manuscriptId, agent.id)
  }

  const updatedAt = agent.profile_url ? new Date().toLocaleDateString('de-DE') : null

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Card className="border-accent/30">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs text-accent font-semibold">#{rank}</span>
              <h3 className="font-[family-name:var(--font-heading)] text-lg font-semibold">{agent.name}</h3>
            </div>
            {agent.agency && <p className="text-sm text-muted mt-0.5">{agent.agency}</p>}
          </div>
          <button onClick={onCollapse} className="text-muted hover:text-text text-sm p-1">✕</button>
        </div>

        <div className="mt-3">
          <ScoreBar score={composite_score} />
        </div>

        {/* All genres + keywords */}
        <div className="flex flex-wrap gap-1.5 mt-4">
          {agent.genres?.map(g => (
            <span key={g} className="text-xs bg-accent/10 text-accent px-2 py-0.5 rounded-full">{g}</span>
          ))}
          {agent.keywords?.map(k => (
            <span key={k} className="text-xs bg-surface border border-border px-2 py-0.5 rounded-full text-muted">{k}</span>
          ))}
        </div>

        {/* Audience */}
        {agent.audience && agent.audience.length > 0 && (
          <div className="mt-3">
            <span className="text-xs text-muted">Zielgruppe: </span>
            <span className="text-xs text-text">{agent.audience.join(', ')}</span>
          </div>
        )}

        {/* Match tags */}
        {match_tags.length > 0 && (
          <div className="flex flex-wrap gap-3 mt-3">
            {match_tags.map((t, i) => (
              <MatchTagComp key={i} tag={t} />
            ))}
          </div>
        )}

        {/* Submission requirements */}
        {agent.submission_req && Object.keys(agent.submission_req).length > 0 && (
          <div className="mt-4 pt-4 border-t border-border">
            <SubmissionChecklist
              agentName={agent.name}
              agency={agent.agency}
              submissionReq={agent.submission_req}
              uploads={uploads}
              manuscriptId={manuscriptId}
              agentId={agent.id}
            />
          </div>
        )}

        {/* Source + timestamp */}
        <div className="mt-4 pt-4 border-t border-border space-y-2">
          {updatedAt && (
            <p className="text-xs text-muted">Zuletzt aktualisiert: {updatedAt}</p>
          )}
          <a
            href={agent.profile_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleSourceClick}
            className="inline-flex items-center gap-1 text-sm text-accent hover:text-accent-hover transition-colors"
          >
            Zum Originalprofil →
          </a>
          <p className="text-xs text-muted/80 italic">
            Bitte prüfe alle Details direkt beim Agenten vor dem Einreichen.
          </p>
        </div>
      </Card>
    </motion.div>
  )
}
