interface FlowProgressProps {
  total: number
  current: number
}

export default function FlowProgress({ total, current }: FlowProgressProps) {
  return (
    <div className="flex items-center gap-1.5 justify-center py-3">
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          className={`h-1.5 rounded-full transition-all duration-300 ${
            i <= current ? 'w-6 bg-accent' : 'w-1.5 bg-border'
          }`}
        />
      ))}
    </div>
  )
}
