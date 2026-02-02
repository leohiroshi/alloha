"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { MessageSquare, Zap, Shield, TrendingUp, Clock, Globe } from "lucide-react";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { MagneticButton } from "../ui/MagneticButton";

export function Features() {
  const { t } = useLanguage();
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  const features = [
    { icon: MessageSquare, title: t("features.designBoard.title"), desc: t("features.designBoard.desc") },
    { icon: Zap, title: t("features.delivery.title"), desc: t("features.delivery.desc") },
    { icon: Shield, title: t("features.rate.title"), desc: t("features.rate.desc") },
    { icon: TrendingUp, title: t("features.designs.title"), desc: t("features.designs.desc") },
    { icon: Clock, title: t("features.revisions.title"), desc: t("features.revisions.desc") },
    { icon: Globe, title: t("features.unique.title"), desc: t("features.unique.desc") },
  ];

  return (
    <section ref={ref} id="features" className="py-24 px-6">
      <div className="max-w-6xl mx-auto text-center">
        <motion.p
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          className="text-[#FF5500] text-sm font-medium mb-4"
        >
          {t("features.label")}
        </motion.p>
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.1 }}
          className="text-4xl md:text-5xl font-bold text-white mb-4"
        >
          {t("features.title")}{" "}
          <span className="font-serif italic text-transparent bg-clip-text bg-gradient-to-r from-[#FF5500] to-[#FF8800]">
            {t("features.titleHighlight")}
          </span>
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.2 }}
          className="text-white/50 text-lg mb-16 max-w-xl mx-auto"
        >
          {t("features.subtitle")}
        </motion.p>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-8 mb-12">
          {features.map((feature, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 30 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.3 + i * 0.1 }}
              className="text-center"
            >
              <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-4">
                <feature.icon className="w-6 h-6 text-[#FF5500]" />
              </div>
              <h3 className="text-white font-semibold mb-2">{feature.title}</h3>
              <p className="text-white/40 text-sm">{feature.desc}</p>
            </motion.div>
          ))}
        </div>

        <MagneticButton className="bg-[#FF5500] text-black font-semibold px-8 py-3 rounded-full">
          {t("features.cta")}
        </MagneticButton>
      </div>
    </section>
  );
}
