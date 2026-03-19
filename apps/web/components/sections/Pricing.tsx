"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { MagneticButton } from "../ui/MagneticButton";

export function Pricing() {
  const { t } = useLanguage();
  const router = useRouter();
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  const plan = {
    price: t("pricing.pro.price"),
    period: t("pricing.pro.period"),
    desc: t("pricing.pro.desc"),
    features: [
      t("pricing.pro.feature1"),
      t("pricing.pro.feature2"),
      t("pricing.pro.feature3"),
      t("pricing.pro.feature4"),
      t("pricing.pro.feature5"),
      t("pricing.pro.feature6"),
      t("pricing.pro.feature7"),
    ],
    cta: t("pricing.pro.cta"),
  };

  return (
    <section ref={ref} id="pricing" className="py-24 px-6">
      <div className="max-w-6xl mx-auto text-center">
        <motion.p
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          className="text-[#FF5500] text-sm font-medium mb-4"
        >
          {t("pricing.label")}
        </motion.p>
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.1 }}
          className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-4"
        >
          {t("pricing.title")}{" "}
          <span className="font-serif italic text-transparent bg-clip-text bg-gradient-to-r from-[#FF5500] to-[#FF8800]">
            {t("pricing.titleHighlight")}
          </span>
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.2 }}
          className="text-white/50 text-lg mb-16 max-w-xl mx-auto"
        >
          {t("pricing.subtitle")}
        </motion.p>

        {/* Single centered card */}
        <div className="flex justify-center">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.3, duration: 0.8 }}
            className="relative w-full max-w-md rounded-3xl p-8 text-left bg-gradient-to-br from-[#0a0a0a] to-[#111] border border-white/10 overflow-hidden"
          >
            {/* Spots left badge */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={isInView ? { opacity: 1, scale: 1 } : {}}
              transition={{ delay: 0.5 }}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 mb-6"
            >
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-white/70 text-sm">3 vagas restantes</span>
            </motion.div>

            {/* Price */}
            <div className="flex items-baseline gap-1 mb-2">
              <span className="text-5xl md:text-6xl font-bold text-white">{plan.price}</span>
              <span className="text-white/40 text-lg">{plan.period}</span>
            </div>

            <p className="text-white/50 text-sm mb-8">{plan.desc}</p>

            {/* CTA Buttons */}
            <div className="flex gap-3 mb-8">
              <MagneticButton
                onClick={() => router.push("/signup")}
                className="flex-1 py-3.5 rounded-full font-semibold bg-[#FF5500] text-black transition-all hover:bg-[#FF6600]"
              >
                {plan.cta}
              </MagneticButton>
              <MagneticButton
                onClick={() => router.push("/login?mode=signup")}
                className="flex-1 py-3.5 rounded-full font-semibold bg-transparent text-white border border-white/20 hover:bg-white/5 transition-all"
              >
                {t("pricing.trial")}
              </MagneticButton>
            </div>

            {/* Features list */}
            <ul className="space-y-3 relative z-10">
              {plan.features.map((feature, j) => (
                <motion.li
                  key={j}
                  initial={{ opacity: 0, x: -20 }}
                  animate={isInView ? { opacity: 1, x: 0 } : {}}
                  transition={{ delay: 0.5 + j * 0.05 }}
                  className="flex items-center gap-3 text-white/70 text-sm"
                >
                  <Sparkles className="w-4 h-4 text-[#FF5500] shrink-0" />
                  {feature}
                </motion.li>
              ))}
            </ul>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
