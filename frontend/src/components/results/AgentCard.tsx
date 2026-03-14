'use client'

import Card from '@/components/ui/Card'
import ScoreBar from '@/components/ui/ScoreBar'
import MatchTagComp from '@/components/ui/MatchTag'
import type { ScoredAgent } from '@/lib/types'

interface AgentCardProps {
  result: ScoredAgent
  rank: number
  onClick?: () => void
  expandable?: boolean
}

export default function AgentCard({ result, rank, onClick, expandable = false }: AgentCardProps) {
  const { agent, composite_score, match_tags } = result

  return (
    <Card className={`${expandable ? 'cursor-pointer hover:border-accent/40' : ''} transition-colors`}>
      <div onClick={onClick}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs text-accent font-semibold">#{rank}</span>
              <h3 className="font-[family-name:var(--font-heading)] text-lg font-semibold truncate">{agent.name}</h3>
            </div>
            {agent.agency && <p className="text-sm text-muted mt-0.5">{agent.agency}</p>}
          </div>
        </div>

        <div className="mt-3">
          <ScoreBar score={composite_score} />
        </div>

        {/* Genre + Audience tags */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {agent.genres?.slice(0, 4).map(g => (
            <span key={g} className="text-xs bg-accent/10 text-accent px-2 py-0.5 rounded-full">{g}</span>
          ))}
          {agent.audience?.map(a => (
            <span key={a} className="text-xs bg-surface border border-border px-2 py-0.5 rounded-full text-muted">{a}</span>
          ))}
        </div>

        {/* Match tags */}
        {match_tags.length > 0 && (
          <div className="flex flex-wrap gap-3 mt-3">
            {match_tags.map((t, i) => (
              <MatchTagComp key={i} tag={t} />
            ))}
          </div>
        )}
      </div>
    </Card>
  )
}
