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
  title: 'Alloha | AI Real Estate Chatbot - Never Sleep on Leads',
  description: 'Alloha is an AI-powered real estate chatbot that works 24/7. While the city sleeps, the ocean keeps moving. Never miss another lead.',
  generator: 'v0.app',
  keywords: ['real estate', 'AI chatbot', 'lead generation', '24/7 support', 'property'],
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
