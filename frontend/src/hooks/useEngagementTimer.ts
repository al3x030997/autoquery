'use client'

import { useEffect, useRef, useState } from 'react'

export function useEngagementTimer(thresholdMs: number = 60000): boolean {
  const [reached, setReached] = useState(false)
  const elapsed = useRef(0)
  const interval = useRef<ReturnType<typeof setInterval>>()

  useEffect(() => {
    if (reached) return

    const start = () => {
      if (interval.current) return
      interval.current = setInterval(() => {
        elapsed.current += 1000
        if (elapsed.current >= thresholdMs) {
          setReached(true)
          if (interval.current) clearInterval(interval.current)
        }
      }, 1000)
    }

    const stop = () => {
      if (interval.current) {
        clearInterval(interval.current)
        interval.current = undefined
      }
    }

    // Only count time when tab is visible
    const handleVisibility = () => {
      if (document.hidden) stop()
      else start()
    }

    start()
    document.addEventListener('visibilitychange', handleVisibility)

    return () => {
      stop()
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [reached, thresholdMs])

  return reached
}
