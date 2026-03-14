'use client'

import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

interface ChatBubbleProps {
  children: ReactNode
  variant: 'question' | 'answer'
  onClick?: () => void
}

export default function ChatBubble({ children, variant, onClick }: ChatBubbleProps) {
  const isAnswer = variant === 'answer'
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={`max-w-[85%] ${isAnswer ? 'ml-auto' : 'mr-auto'}`}
    >
      <div
        onClick={onClick}
        className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isAnswer
            ? 'bg-accent/15 text-text cursor-pointer hover:bg-accent/20 transition-colors rounded-br-md'
            : 'bg-surface text-text rounded-bl-md'
        }`}
      >
        {children}
      </div>
    </motion.div>
  )
}
