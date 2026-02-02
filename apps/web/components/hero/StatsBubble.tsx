"use client";

import { motion } from "framer-motion";
import { TrendingUp } from "lucide-react";
import { useLanguage } from "@/lib/i18n/LanguageContext";

export function StatsBubble() {
  const { t } = useLanguage();
  
  return (
    <motion.div
      animate={{ y: [-5, 5, -5], rotate: [1, -1, 1] }}
      transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
    >
      <div 
        className="w-64 p-5 rounded-[24px] rounded-br-lg"
        style={{
          background: "linear-gradient(135deg, rgba(10,10,10,0.9) 0%, rgba(20,20,20,0.8) 100%)",
          backdropFilter: "blur(30px)",
          border: "1px solid rgba(255,85,0,0.2)",
          boxShadow: "0 0 40px rgba(255,85,0,0.1), 0 20px 40px rgba(0,0,0,0.4)",
        }}
      >
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-full bg-[#FF5500]/20 flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-[#FF5500]" />
          </div>
          <span className="text-xs text-white/60 font-medium">{t("stats.thisWeek")}</span>
        </div>
        <div className="text-2xl font-bold text-white mb-1">{t("stats.leads")}</div>
        <div className="flex items-center gap-1 text-xs">
          <span className="text-green-400">↑ 23%</span>
          <span className="text-white/40">{t("stats.vsLastWeek")}</span>
        </div>
      </div>
    </motion.div>
  );
}
