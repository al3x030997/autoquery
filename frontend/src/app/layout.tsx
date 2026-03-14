'use client'

import { Crimson_Pro, DM_Sans } from 'next/font/google'
import { AuthProvider } from '@/context/AuthContext'
import Header from '@/components/layout/Header'
import Footer from '@/components/layout/Footer'
import './globals.css'

const crimsonPro = Crimson_Pro({
  subsets: ['latin'],
  variable: '--font-heading',
  display: 'swap',
})

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-body',
  display: 'swap',
})

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de" className={`${crimsonPro.variable} ${dmSans.variable}`}>
      <head>
        <title>AutoQuery — Finde den Agenten, der genau dein Buch sucht</title>
        <meta name="description" content="Beschreib dein Manuskript. Wir matchen es gegen hunderte echte Agenten-Profile — in Sekunden." />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className="font-[family-name:var(--font-body)] min-h-screen flex flex-col">
        <AuthProvider>
          <Header />
          <main className="flex-1">{children}</main>
          <Footer />
        </AuthProvider>
      </body>
    </html>
  )
}
