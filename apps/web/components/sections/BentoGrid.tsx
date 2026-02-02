"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { BarChart3, Building2, Users, Sparkles, Globe } from "lucide-react";
import { useLanguage } from "@/lib/i18n/LanguageContext";

export function BentoGrid() {
  const { t } = useLanguage();
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  const cards = [
    { title: t("bento.visualize.title"), desc: t("bento.visualize.desc"), span: "md:col-span-1", icon: BarChart3 },
    { title: t("bento.brand.title"), desc: t("bento.brand.desc"), span: "md:col-span-1", icon: Building2 },
    { title: t("bento.multiplatform.title"), desc: t("bento.multiplatform.desc"), span: "md:col-span-1", icon: Users },
    { title: t("bento.mockups.title"), desc: t("bento.mockups.desc"), span: "md:col-span-2", icon: Sparkles },
    { title: t("bento.internet.title"), desc: t("bento.internet.desc"), span: "md:col-span-1", icon: Globe },
  ];

  return (
    <section ref={ref} className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="grid md:grid-cols-3 gap-4">
          {cards.map((card, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 40 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: i * 0.1, duration: 0.8 }}
              className={`group relative rounded-3xl p-6 bg-gradient-to-b from-white/[0.06] to-transparent border border-white/10 overflow-hidden hover:border-[#FF5500]/30 transition-colors ${card.span}`}
            >
              <div className="relative z-10">
                <card.icon className="w-8 h-8 text-[#FF5500] mb-4" />
                <h3 className="text-white font-semibold text-lg mb-2">{card.title}</h3>
                <p className="text-white/50 text-sm">{card.desc}</p>
              </div>
              
              {/* Hover glow */}
              <div className="absolute inset-0 bg-gradient-to-t from-[#FF5500]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
