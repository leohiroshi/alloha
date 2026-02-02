"use client";

import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import { LavaBlobs } from "@/components/effects/LavaBlobs";
import { Navigation } from "@/components/layout/Navigation";
import { Footer } from "@/components/layout/Footer";
import { Hero } from "@/components/sections/Hero";
import { Testimonials } from "@/components/sections/Testimonials";
import { Process } from "@/components/sections/Process";
import { BentoGrid } from "@/components/sections/BentoGrid";
import { Benefits } from "@/components/sections/Benefits";
import { Features } from "@/components/sections/Features";
import { Solutions } from "@/components/sections/Solutions";
import { Pricing } from "@/components/sections/Pricing";
import { FAQ } from "@/components/sections/FAQ";
import { CTA } from "@/components/sections/CTA";

function AllohaLandingContent() {
  return (
    <main className="relative bg-black min-h-screen overflow-x-hidden">
      <LavaBlobs />
      <Navigation />
      <Hero />
      <Testimonials />
      <Process />
      <BentoGrid />
      <Benefits />
      <Features />
      <Solutions />
      <Pricing />
      <FAQ />
      <CTA />
      <Footer />
    </main>
  );
}

export default function AllohaLanding() {
  return (
    <LanguageProvider>
      <AllohaLandingContent />
    </LanguageProvider>
  );
}
