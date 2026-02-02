"use client";

import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import Image from "next/image";
import { useLanguage } from "@/lib/i18n/LanguageContext";

export function WaveChatBubble() {
  const { t } = useLanguage();
  
  return (
    <motion.div
      className="relative"
      initial={{ opacity: 0, scale: 0.8, x: -50 }}
      animate={{ opacity: 1, scale: 1, x: 0 }}
      transition={{ duration: 1, delay: 0.8, ease: [0.16, 1, 0.3, 1] }}
    >
      <motion.div
        animate={{ y: [-8, 8, -8], rotate: [-1, 1, -1] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
      >
        <div className="relative w-72 min-h-[160px]">
          {/* Main glass container */}
          <div 
            className="absolute inset-0 rounded-[28px] rounded-bl-lg overflow-hidden"
            style={{
              background: "linear-gradient(135deg, rgba(10,10,10,0.9) 0%, rgba(20,20,20,0.8) 100%)",
              backdropFilter: "blur(30px)",
              border: "1px solid rgba(255,85,0,0.2)",
              boxShadow: `
                0 0 60px rgba(255,85,0,0.15),
                0 25px 50px rgba(0,0,0,0.5),
                inset 0 1px 0 rgba(255,255,255,0.05)
              `,
            }}
          />

          {/* Logo decoration at top */}
          <div className="absolute -top-3 -left-3 z-10">
            <motion.div
              animate={{ rotate: [0, 10, 0], scale: [1, 1.1, 1] }}
              transition={{ duration: 4, repeat: Infinity }}
            >
              <Image src="/logo.png" alt="Alloha" width={32} height={32} className="drop-shadow-[0_0_10px_rgba(255,85,0,0.5)]" />
            </motion.div>
          </div>

          {/* Content */}
          <div className="relative z-10 p-5">
            <div className="flex items-start gap-3 mb-3">
              <motion.div 
                className="w-9 h-9 rounded-full bg-gradient-to-br from-[#FF5500] to-[#FF8800] flex items-center justify-center shrink-0 shadow-lg shadow-[#FF5500]/30"
                animate={{ boxShadow: ["0 0 20px rgba(255,85,0,0.3)", "0 0 35px rgba(255,85,0,0.5)", "0 0 20px rgba(255,85,0,0.3)"] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <Sparkles className="w-4 h-4 text-black" />
              </motion.div>
              <div className="flex-1">
                <div className="text-[10px] text-[#FF5500] mb-1 font-medium">{t("bubble.online")}</div>
                <motion.div 
                  className="text-xs text-white/90 leading-relaxed"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 1.2 }}
                >
                  {t("bubble.message")}
                </motion.div>
              </div>
            </div>

            {/* Typing indicator */}
            <div className="flex gap-1.5 mt-3">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="w-1.5 h-1.5 rounded-full bg-[#FF5500]"
                  animate={{ 
                    opacity: [0.3, 1, 0.3], 
                    scale: [0.8, 1.2, 0.8],
                    y: [0, -2, 0]
                  }}
                  transition={{
                    duration: 1.2,
                    repeat: Infinity,
                    delay: i * 0.15,
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
