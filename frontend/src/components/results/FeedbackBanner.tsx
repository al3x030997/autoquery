'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { fireEvent } from '@/lib/events'

interface Props {
  manuscriptId: number
}

const SESSION_KEY = 'aq_feedback_shown'

export default function FeedbackBanner({ manuscriptId }: Props) {
  const [visible, setVisible] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    // Only show once per session
    if (sessionStorage.getItem(SESSION_KEY)) return

    const timer = setTimeout(() => {
      setVisible(true)
      sessionStorage.setItem(SESSION_KEY, '1')
    }, 60000) // 60 seconds

    return () => clearTimeout(timer)
  }, [])

  // Auto-dismiss after 15 seconds
  useEffect(() => {
    if (!visible) return
    const timer = setTimeout(() => setDismissed(true), 15000)
    return () => clearTimeout(timer)
  }, [visible])

  const handleFeedback = (type: 'feedback_positive' | 'feedback_neutral') => {
    fireEvent(type, manuscriptId)
    setDismissed(true)
  }

  return (
    <AnimatePresence>
      {visible && !dismissed && (
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          className="fixed bottom-4 left-4 right-4 sm:left-auto sm:right-4 sm:w-96 z-50"
        >
          <div className="bg-surface border border-border rounded-xl p-4 shadow-xl">
            <div className="flex items-start justify-between gap-2 mb-3">
              <p className="text-sm font-medium">Wie fühlen sich die Ergebnisse an?</p>
              <button onClick={() => setDismissed(true)} className="text-muted hover:text-text text-xs">✕</button>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleFeedback('feedback_positive')}
                className="flex-1 py-2 text-sm bg-green-900/30 border border-green-800/50 rounded-lg hover:bg-green-900/50 transition-colors"
              >
                Überraschend gut
              </button>
              <button
                onClick={() => handleFeedback('feedback_neutral')}
                className="flex-1 py-2 text-sm bg-surface border border-border rounded-lg hover:bg-border/50 transition-colors"
              >
                Nicht was ich erwartet habe
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
