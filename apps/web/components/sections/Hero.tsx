"use client";

import { motion } from "framer-motion";
import { ArrowRight, Play } from "lucide-react";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { MagneticButton } from "../ui/MagneticButton";
import { FloatingPhone } from "../hero/FloatingPhone";
import { WaveChatBubble } from "../hero/WaveChatBubble";
import { StatsBubble } from "../hero/StatsBubble";

export function Hero() {
  const { t } = useLanguage();
  
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center pt-32 pb-20 px-6">
      {/* Urgency badge */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="mb-8"
      >
        <div className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-sm">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-white/70">{t("hero.urgency")} <span className="text-white font-medium">{t("hero.spotsLeft")}</span></span>
        </div>
      </motion.div>

      {/* Main headline */}
      <motion.h1
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.1 }}
        className="text-center text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tight mb-6 max-w-5xl"
      >
        <span className="text-white">{t("hero.title1")}</span>
        <span className="font-serif italic text-transparent bg-clip-text bg-gradient-to-r from-[#FF5500] to-[#FF8800]">
          {t("hero.titleHighlight")}
        </span>
        <br />
        <span className="text-white">{t("hero.title2")}</span>
      </motion.h1>

      {/* Subtitle */}
      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.2 }}
        className="text-center text-lg md:text-xl text-white/50 mb-10 max-w-2xl"
      >
        {t("hero.subtitle1")}{" "}
        <span className="font-serif italic text-transparent bg-clip-text bg-gradient-to-r from-[#FF5500] to-[#FF8800]">
          {t("hero.subtitleHighlight")}
        </span>
        {t("hero.subtitle2")}
      </motion.p>

      {/* CTA Buttons */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.3 }}
        className="flex flex-col sm:flex-row gap-4 mb-16"
      >
        <MagneticButton className="group bg-[#FF5500] hover:bg-[#FF6600] text-black font-bold px-8 py-4 rounded-full text-base transition-colors">
          <span className="flex items-center gap-2">
            {t("hero.ctaPrimary")}
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </span>
        </MagneticButton>
        <MagneticButton className="flex items-center gap-2 text-white/80 hover:text-white font-medium px-8 py-4 rounded-full border border-white/20 hover:border-white/40 transition-colors" variant="secondary">
          <Play className="w-4 h-4" />
          {t("hero.ctaSecondary")}
        </MagneticButton>
      </motion.div>

      {/* Hero Visual - 3D Phone with Chat Bubble */}
      <motion.div
        initial={{ opacity: 0, y: 60 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1, delay: 0.4 }}
        className="relative w-full max-w-5xl flex items-center justify-center"
      >
        {/* Floating chat bubble - Left side */}
        <div className="absolute left-0 top-10 hidden lg:block z-20">
          <WaveChatBubble />
        </div>

        {/* 3D Phone - Center */}
        <div className="relative z-10">
          <FloatingPhone />
        </div>

        {/* Stats bubble - Right side */}
        <motion.div
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 1, delay: 1 }}
          className="absolute right-0 bottom-20 hidden lg:block z-20"
        >
          <StatsBubble />
        </motion.div>

        {/* Decorative glow behind phone */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-[500px] h-[500px] bg-[#FF5500]/15 rounded-full blur-[100px]" />
        </div>
      </motion.div>

      {/* Social proof logos */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1, delay: 0.8 }}
        className="mt-20"
      >
        <p className="text-center text-sm text-white/30 mb-6">{t("hero.socialProof")}</p>
        <div className="flex flex-wrap items-center justify-center gap-8 md:gap-12 opacity-40">
          {["Logoteam", "LOGO", "Logoipsum", "IPSUM", "Logoipsum", "Logoteam"].map((logo, i) => (
            <span key={i} className="text-white font-medium text-sm md:text-base">{logo}</span>
          ))}
        </div>
      </motion.div>
    </section>
  );
}
