"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { useLanguage } from "@/lib/i18n/LanguageContext";

export function Solutions() {
  const { t } = useLanguage();
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  const solutions = [
    t("solutions.logos"), t("solutions.landingPages"), t("solutions.websites"), t("solutions.digitalProducts"),
    t("solutions.pitchDecks"), t("solutions.mobileApps"), t("solutions.emailDesign"), t("solutions.productDesign")
  ];

  return (
    <section ref={ref} className="py-24 px-6">
      <div className="max-w-4xl mx-auto text-center">
        <motion.p
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          className="text-[#FF5500] text-sm font-medium mb-4"
        >
          {t("solutions.label")}
        </motion.p>
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.1 }}
          className="text-4xl md:text-5xl font-bold text-white mb-6"
        >
          {t("solutions.title")}{" "}
          <span className="font-serif italic text-transparent bg-clip-text bg-gradient-to-r from-[#FF5500] to-[#FF8800]">
            {t("solutions.titleHighlight")}
          </span>
          {" "}{t("solutions.title2")}
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.2 }}
          className="text-white/50 text-lg mb-12 max-w-xl mx-auto"
        >
          {t("solutions.subtitle")}
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.3 }}
          className="flex flex-wrap justify-center gap-3"
        >
          {solutions.map((solution, i) => (
            <span
              key={i}
              className="px-5 py-2.5 rounded-full bg-white/5 border border-white/10 text-white/70 text-sm hover:border-[#FF5500]/30 hover:text-white transition-colors cursor-default"
            >
              {solution}
            </span>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
