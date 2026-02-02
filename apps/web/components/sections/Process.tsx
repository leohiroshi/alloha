"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Bot, Zap, Check } from "lucide-react";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { MagneticButton } from "../ui/MagneticButton";

export function Process() {
  const { t } = useLanguage();
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  const steps = [
    { icon: Bot, title: t("process.step1.title"), desc: t("process.step1.desc") },
    { icon: Zap, title: t("process.step2.title"), desc: t("process.step2.desc") },
    { icon: Check, title: t("process.step3.title"), desc: t("process.step3.desc") },
  ];

  return (
    <section ref={ref} className="py-24 px-6">
      <div className="max-w-6xl mx-auto text-center">
        <motion.p
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          className="text-[#FF5500] text-sm font-medium mb-4"
        >
          {t("process.label")}
        </motion.p>
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.1 }}
          className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-4"
        >
          {t("process.title")}{" "}
          <span className="font-serif italic text-transparent bg-clip-text bg-gradient-to-r from-[#FF5500] to-[#FF8800]">
            {t("process.titleHighlight")}
          </span>
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.2 }}
          className="text-white/50 text-lg mb-16 max-w-xl mx-auto"
        >
          {t("process.subtitle")}
        </motion.p>

        <div className="grid md:grid-cols-3 gap-8 mb-12">
          {steps.map((step, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 30 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.3 + i * 0.1 }}
              className="text-center"
            >
              <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-4">
                <step.icon className="w-7 h-7 text-[#FF5500]" />
              </div>
              <h3 className="text-white font-semibold text-lg mb-2">{step.title}</h3>
              <p className="text-white/50 text-sm">{step.desc}</p>
            </motion.div>
          ))}
        </div>

        <MagneticButton className="bg-[#FF5500] text-black font-semibold px-8 py-3 rounded-full">
          {t("process.cta")}
        </MagneticButton>
      </div>
    </section>
  );
}
