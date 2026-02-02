"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Check } from "lucide-react";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { MagneticButton } from "../ui/MagneticButton";

export function Pricing() {
  const { t } = useLanguage();
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  const plans = [
    {
      name: t("pricing.starter.name"),
      price: t("pricing.starter.price"),
      period: t("pricing.starter.period"),
      desc: t("pricing.starter.desc"),
      features: [
        t("pricing.starter.feature1"),
        t("pricing.starter.feature2"),
        t("pricing.starter.feature3"),
        t("pricing.starter.feature4"),
        t("pricing.starter.feature5"),
      ],
      cta: t("pricing.starter.cta"),
      popular: false,
    },
    {
      name: t("pricing.pro.name"),
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
      popular: true,
    },
    {
      name: t("pricing.enterprise.name"),
      price: t("pricing.enterprise.price"),
      period: t("pricing.enterprise.period"),
      desc: t("pricing.enterprise.desc"),
      features: [
        t("pricing.enterprise.feature1"),
        t("pricing.enterprise.feature2"),
        t("pricing.enterprise.feature3"),
        t("pricing.enterprise.feature4"),
        t("pricing.enterprise.feature5"),
        t("pricing.enterprise.feature6"),
      ],
      cta: t("pricing.enterprise.cta"),
      popular: false,
    },
  ];

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

        <div className="grid md:grid-cols-3 gap-6">
          {plans.map((plan, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 40 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.3 + i * 0.1, duration: 0.8 }}
              className={`relative rounded-3xl p-8 text-left ${
                plan.popular
                  ? "bg-gradient-to-b from-[#FF5500]/20 to-transparent border-2 border-[#FF5500]/50"
                  : "bg-gradient-to-b from-white/[0.06] to-transparent border border-white/10"
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-[#FF5500] rounded-full text-black text-xs font-bold">
                  {t("pricing.mostPopular")}
                </div>
              )}

              <h3 className="text-white font-semibold text-xl mb-2">{plan.name}</h3>
              <p className="text-white/40 text-sm mb-4">{plan.desc}</p>

              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-4xl font-bold text-white">{plan.price}</span>
                <span className="text-white/40">{plan.period}</span>
              </div>

              <ul className="space-y-3 mb-8">
                {plan.features.map((feature, j) => (
                  <li key={j} className="flex items-center gap-3 text-white/70 text-sm">
                    <Check className="w-4 h-4 text-[#FF5500] shrink-0" />
                    {feature}
                  </li>
                ))}
              </ul>

              <MagneticButton
                className={`w-full py-3 rounded-full font-semibold ${
                  plan.popular
                    ? "bg-[#FF5500] text-black"
                    : "bg-white/10 text-white hover:bg-white/20"
                } transition-colors`}
              >
                {plan.cta}
              </MagneticButton>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
