"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { ArrowRight } from "lucide-react";
import Image from "next/image";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { MagneticButton } from "../ui/MagneticButton";

export function CTA() {
  const { t } = useLanguage();
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section ref={ref} className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 40, scale: 0.98 }}
          animate={isInView ? { opacity: 1, y: 0, scale: 1 } : {}}
          transition={{ duration: 0.8 }}
          className="relative rounded-[40px] p-12 md:p-20 text-center overflow-hidden bg-gradient-to-b from-white/[0.08] to-transparent border border-white/10"
        >
          {/* Background glow */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-[#FF5500]/20 rounded-full blur-[100px] -z-10" />

          <Image src="/logo.png" alt="Alloha" width={64} height={64} className="mx-auto mb-8" />

          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
            {t("cta.title")}{" "}
            <span className="font-serif italic text-transparent bg-clip-text bg-gradient-to-r from-[#FF5500] to-[#FF8800]">
              {t("cta.titleHighlight")}
            </span>
          </h2>

          <p className="text-white/50 text-lg mb-10 max-w-xl mx-auto">
            {t("cta.subtitle")}
          </p>

          <MagneticButton className="bg-[#FF5500] hover:bg-[#FF6600] text-black font-bold px-10 py-4 rounded-full text-lg transition-colors">
            <span className="flex items-center gap-2">
              {t("cta.button")}
              <ArrowRight className="w-5 h-5" />
            </span>
          </MagneticButton>

          <p className="mt-6 text-sm text-white/30">
            {t("cta.note")}
          </p>
        </motion.div>
      </div>
    </section>
  );
}
