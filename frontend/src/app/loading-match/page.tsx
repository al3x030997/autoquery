'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'

const MESSAGES = [
  'Analysiere dein Manuskript...',
  'Durchsuche Agenten-Profile...',
  'Berechne die besten Matches...',
  'Finde die passendsten Agenten...',
]

function LoadingContent() {
  const router = useRouter()
  const params = useSearchParams()
  const id = params.get('id')
  const [msgIdx, setMsgIdx] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setMsgIdx(i => (i + 1) % MESSAGES.length)
    }, 1500)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (!id) { router.push('/flow'); return }
    const timer = setTimeout(() => {
      router.push(`/results/${id}`)
    }, 2500)
    return () => clearTimeout(timer)
  }, [id, router])

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-8rem)] px-4">
      <div className="flex gap-2 mb-8">
        {[0, 1, 2].map(i => (
          <motion.div
            key={i}
            className="w-3 h-3 rounded-full bg-accent"
            animate={{ scale: [1, 1.4, 1], opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
          />
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.p
          key={msgIdx}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.3 }}
          className="text-muted text-sm"
        >
          {MESSAGES[msgIdx]}
        </motion.p>
      </AnimatePresence>
    </div>
  )
}

export default function LoadingMatchPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[calc(100vh-8rem)]">
        <p className="text-muted animate-pulse">Laden...</p>
      </div>
    }>
      <LoadingContent />
    </Suspense>
  )
}
