"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Database, GitBranch, Wrench } from "lucide-react";
import { useLanguage } from "@/lib/i18n/LanguageContext";

const proofIcons = [Database, GitBranch, Wrench];

export function Testimonials() {
  const { t } = useLanguage();
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  const proofCards = [
    { title: t("proof.card1.title"), desc: t("proof.card1.desc") },
    { title: t("proof.card2.title"), desc: t("proof.card2.desc") },
    { title: t("proof.card3.title"), desc: t("proof.card3.desc") },
  ];

  return (
    <section ref={ref} className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-12 max-w-3xl">
          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            className="text-[#FF5500] text-sm font-medium mb-4"
          >
            {t("proof.label")}
          </motion.p>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.1 }}
            className="text-4xl md:text-5xl font-bold text-white mb-5"
          >
            {t("proof.title")}{" "}
            <span className="font-serif italic text-transparent bg-clip-text bg-gradient-to-r from-[#FF5500] to-[#FF8800]">
              {t("proof.titleHighlight")}
            </span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.2 }}
            className="text-white/50 text-lg leading-relaxed"
          >
            {t("proof.subtitle")}
          </motion.p>
        </div>

        <div className="grid md:grid-cols-3 gap-4">
          {proofCards.map((card, index) => {
            const Icon = proofIcons[index] ?? Database;
            return (
              <motion.div
                key={card.title}
                initial={{ opacity: 0, y: 30 }}
                animate={isInView ? { opacity: 1, y: 0 } : {}}
                transition={{ delay: 0.25 + index * 0.1, duration: 0.7 }}
                className="rounded-3xl bg-[#0a0a0a] border border-white/10 p-7"
              >
                <div className="w-12 h-12 rounded-2xl bg-[#FF5500]/15 border border-[#FF5500]/20 flex items-center justify-center mb-5">
                  <Icon className="w-5 h-5 text-[#FF5500]" />
                </div>
                <h3 className="text-white text-xl font-semibold mb-3">{card.title}</h3>
                <p className="text-white/50 text-sm leading-relaxed">{card.desc}</p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
