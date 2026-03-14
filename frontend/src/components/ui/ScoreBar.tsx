interface ScoreBarProps {
  score: number // 0-1
}

export default function ScoreBar({ score }: ScoreBarProps) {
  const pct = Math.round(score * 100)
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
        <div
          className="h-full bg-accent rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-muted w-8 text-right">{pct}%</span>
    </div>
  )
}
