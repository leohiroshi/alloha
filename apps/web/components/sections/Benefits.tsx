"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Check, Star } from "lucide-react";
import { useLanguage } from "@/lib/i18n/LanguageContext";

export function Benefits() {
  const { t } = useLanguage();
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  const benefitsList = [
    { title: t("benefits.item1.title"), desc: t("benefits.item1.desc") },
    { title: t("benefits.item2.title"), desc: t("benefits.item2.desc") },
    { title: t("benefits.item3.title"), desc: t("benefits.item3.desc") },
  ];

  return (
    <section ref={ref} className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left - Text */}
          <div>
            <motion.p
              initial={{ opacity: 0 }}
              animate={isInView ? { opacity: 1 } : {}}
              className="text-[#FF5500] text-sm font-medium mb-4"
            >
              {t("benefits.label")}
            </motion.p>
            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.1 }}
              className="text-4xl md:text-5xl font-bold text-white mb-6"
            >
              {t("benefits.title")}{" "}
              <span className="font-serif italic text-transparent bg-clip-text bg-gradient-to-r from-[#FF5500] to-[#FF8800]">
                {t("benefits.titleHighlight")}
              </span>
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.2 }}
              className="text-white/50 text-lg mb-8"
            >
              {t("benefits.subtitle")}
            </motion.p>

            {/* Benefits list */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.3 }}
              className="space-y-4"
            >
              {benefitsList.map((benefit, i) => (
                <div key={i} className="flex gap-4">
                  <div className="w-6 h-6 rounded-full bg-[#FF5500]/20 flex items-center justify-center shrink-0 mt-1">
                    <Check className="w-3 h-3 text-[#FF5500]" />
                  </div>
                  <div>
                    <h4 className="text-white font-medium mb-1">{benefit.title}</h4>
                    <p className="text-white/40 text-sm">{benefit.desc}</p>
                  </div>
                </div>
              ))}
            </motion.div>
          </div>

          {/* Right - Testimonial */}
          <motion.div
            initial={{ opacity: 0, x: 40 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ delay: 0.4, duration: 0.8 }}
            className="relative"
          >
            <div className="p-8 rounded-3xl bg-gradient-to-b from-white/[0.08] to-white/[0.02] border border-white/10">
              <div className="flex gap-1 mb-4">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="w-4 h-4 fill-[#FF5500] text-[#FF5500]" />
                ))}
              </div>
              <p className="text-white/80 text-lg leading-relaxed mb-6">
                {t("benefits.testimonial")}
              </p>
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#FF5500] to-[#FF8800]" />
                <div>
                  <p className="text-white font-medium">{t("benefits.testimonial.author")}</p>
                  <p className="text-white/40 text-sm">{t("benefits.testimonial.role")}</p>
                </div>
              </div>
            </div>

            {/* Decorative glow */}
            <div className="absolute -inset-4 bg-[#FF5500]/10 rounded-3xl blur-3xl -z-10" />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
