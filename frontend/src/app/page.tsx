'use client'

import Link from 'next/link'
import Button from '@/components/ui/Button'

export default function LandingPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-8rem)] px-4 text-center">
      <h1 className="font-[family-name:var(--font-heading)] text-4xl sm:text-5xl md:text-6xl font-bold leading-tight max-w-3xl">
        Finde den Agenten, der genau dein Buch sucht.
      </h1>
      <p className="mt-6 text-lg text-muted max-w-xl">
        Beschreib dein Manuskript. Wir matchen es gegen hunderte echte Agenten-Profile — in Sekunden.
      </p>
      <Link href="/flow" className="mt-10">
        <Button className="text-base px-8 py-3.5">Matching starten</Button>
      </Link>

      <div className="mt-20 grid grid-cols-1 sm:grid-cols-3 gap-8 max-w-3xl w-full text-left">
        <Step num="1" title="Beschreib dein Buch" text="Genre, Themen, Ton — in einem kurzen Gespräch." />
        <Step num="2" title="Wir finden Agenten" text="Hunderte Profile, analysiert und gematcht in Sekunden." />
        <Step num="3" title="Du entscheidest" text="Prüfe die Ergebnisse und schreib gezielt die passenden Agenten an." />
      </div>
    </div>
  )
}

function Step({ num, title, text }: { num: string; title: string; text: string }) {
  return (
    <div>
      <span className="text-accent font-semibold text-sm">{num}</span>
      <h3 className="font-[family-name:var(--font-heading)] text-lg font-semibold mt-1">{title}</h3>
      <p className="text-sm text-muted mt-1">{text}</p>
    </div>
  )
}
