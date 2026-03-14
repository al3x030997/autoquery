import type { MatchTag as MatchTagType } from '@/lib/types'

const indicators: Record<string, { icon: string; color: string }> = {
  match: { icon: '✓', color: 'text-green-400' },
  partial: { icon: '~', color: 'text-amber-400' },
  mismatch: { icon: '✗', color: 'text-red-400' },
}

export default function MatchTag({ tag }: { tag: MatchTagType }) {
  const ind = indicators[tag.indicator] || indicators.partial
  return (
    <span className={`inline-flex items-center gap-1 text-xs ${ind.color}`}>
      <span>{ind.icon}</span>
      <span>{tag.label}</span>
    </span>
  )
}
