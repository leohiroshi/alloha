import React from "react"
import type { Metadata, Viewport } from 'next'
import { Inter, Playfair_Display } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import './globals.css'

const inter = Inter({ 
  subsets: ["latin"],
  variable: '--font-inter'
});

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: '--font-playfair',
  style: ['normal', 'italic'],
});

export const metadata: Metadata = {
  title: 'Alloha | Real Estate AI Assistant MVP',
  description: 'Private technical MVP exploring real estate lead qualification, property search, and broker handoff with Next.js, FastAPI, Supabase/PostgreSQL, Redis, and WhatsApp-oriented workflows.',
  keywords: ['real estate AI', 'technical MVP', 'lead qualification', 'property search', 'FastAPI', 'Next.js', 'Supabase', 'pgvector'],
  icons: {
    icon: [
      {
        url: '/favicon.ico',
      },
      {
        url: '/logo.png',
        type: 'image/png',
      },
    ],
    apple: '/logo.png',
  },
}

export const viewport: Viewport = {
  themeColor: '#000000',
  colorScheme: 'dark',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} ${playfair.variable} font-sans antialiased bg-black text-white overflow-x-hidden`}>
        {children}
        <Analytics />
      </body>
    </html>
  )
}
