# Alloha - AI Real Estate Chatbot Landing Page

A modern, responsive landing page for Alloha, an AI-powered real estate chatbot.

## Tech Stack

- **Next.js 16** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Animations and transitions
- **Lucide React** - Icon library

## Project Structure

```
alloha-frontend/
├── app/                          # Next.js App Router
│   ├── globals.css              # Global styles
│   ├── layout.tsx               # Root layout
│   └── page.tsx                 # Landing page
├── components/
│   ├── effects/                 # Visual effects
│   │   └── LavaBlobs.tsx       # Animated background blobs
│   ├── hero/                    # Hero section components
│   │   ├── FloatingPhone.tsx   # 3D phone mockup
│   │   ├── StatsBubble.tsx     # Stats floating bubble
│   │   └── WaveChatBubble.tsx  # Chat bubble animation
│   ├── layout/                  # Layout components
│   │   ├── Footer.tsx          # Page footer
│   │   └── Navigation.tsx      # Navigation bar
│   ├── sections/                # Page sections
│   │   ├── Benefits.tsx        # Benefits section
│   │   ├── BentoGrid.tsx       # Bento grid features
│   │   ├── CTA.tsx             # Call to action
│   │   ├── FAQ.tsx             # FAQ accordion
│   │   ├── Features.tsx        # Features grid
│   │   ├── Hero.tsx            # Hero section
│   │   ├── Pricing.tsx         # Pricing plans
│   │   ├── Process.tsx         # Process steps
│   │   ├── Solutions.tsx       # Solutions tags
│   │   └── Testimonials.tsx    # Customer testimonials
│   ├── ui/                      # UI primitives
│   │   └── MagneticButton.tsx  # Magnetic hover button
│   └── LanguageSwitcher.tsx    # i18n language toggle
├── lib/
│   └── i18n/
│       └── LanguageContext.tsx # i18n context & translations
├── public/
│   ├── logo.png                # Alloha logo
│   └── customers/              # Customer photos
└── ...config files
```

## Getting Started

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Internationalization (i18n)

The app supports English (en) and Portuguese (pt-BR). Language preference is:
1. Saved to localStorage
2. Auto-detected from browser on first visit

To add new translations, edit `lib/i18n/LanguageContext.tsx`.

## Architecture Decisions

- **Component Colocation**: Components are organized by feature/purpose rather than by type
- **Direct Imports**: Using explicit imports instead of barrel exports to avoid circular dependencies
- **Client Components**: All interactive components use `"use client"` directive
- **Responsive Design**: Mobile-first approach with Tailwind breakpoints

## License

Private - All rights reserved
