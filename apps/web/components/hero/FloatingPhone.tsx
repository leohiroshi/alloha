"use client";

import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import Image from "next/image";
import { useLanguage } from "@/lib/i18n/LanguageContext";

export function FloatingPhone() {
  const { t } = useLanguage();
  
  return (
    <motion.div
      className="relative"
      initial={{ opacity: 0, y: 80, rotateY: -15 }}
      animate={{ opacity: 1, y: 0, rotateY: 0 }}
      transition={{ duration: 1.2, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
      style={{ perspective: "1200px" }}
    >
      <motion.div
        className="relative"
        animate={{ 
          y: [-10, 10, -10],
          rotateY: [-2, 2, -2],
          rotateX: [1, -1, 1],
        }}
        transition={{ 
          duration: 8, 
          repeat: Infinity, 
          ease: "easeInOut" 
        }}
        style={{ transformStyle: "preserve-3d" }}
      >
        {/* Phone shadow/reflection */}
        <motion.div
          className="absolute -bottom-16 left-1/2 -translate-x-1/2 w-56 h-32"
          style={{
            background: "radial-gradient(ellipse, rgba(255,85,0,0.35) 0%, transparent 60%)",
            filter: "blur(30px)",
          }}
          animate={{
            scale: [1, 1.1, 1],
            opacity: [0.4, 0.6, 0.4],
          }}
          transition={{ duration: 4, repeat: Infinity }}
        />

        {/* Phone frame */}
        <div 
          className="relative w-64 h-[520px] rounded-[45px] p-2.5"
          style={{
            background: "linear-gradient(145deg, #1a1a1a 0%, #0a0a0a 50%, #1a1a1a 100%)",
            boxShadow: `
              0 50px 100px rgba(0,0,0,0.7),
              0 0 0 1px rgba(255,85,0,0.2),
              inset 0 1px 1px rgba(255,255,255,0.1),
              inset 0 -1px 1px rgba(0,0,0,0.5)
            `,
          }}
        >
          {/* Screen bezel glow */}
          <motion.div
            className="absolute inset-2 rounded-[38px] opacity-50"
            style={{
              boxShadow: "inset 0 0 30px rgba(255,85,0,0.1)",
            }}
            animate={{
              boxShadow: [
                "inset 0 0 30px rgba(255,85,0,0.1)",
                "inset 0 0 40px rgba(255,85,0,0.2)",
                "inset 0 0 30px rgba(255,85,0,0.1)",
              ],
            }}
            transition={{ duration: 3, repeat: Infinity }}
          />

          {/* Screen */}
          <div className="relative w-full h-full bg-black rounded-[38px] overflow-hidden">
            {/* Dynamic Island */}
            <div className="absolute top-2.5 left-1/2 -translate-x-1/2 w-24 h-7 bg-black rounded-full z-20 flex items-center justify-center">
              <motion.div 
                className="w-2 h-2 rounded-full bg-[#1a1a1a]"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </div>

            {/* Status bar */}
            <div className="flex justify-between items-center px-6 pt-3 text-[10px] text-white/60 relative z-10">
              <span className="font-medium">9:41</span>
              <div className="flex items-center gap-1">
                <div className="flex gap-0.5">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="w-0.5 rounded-full bg-white/60" style={{ height: `${i * 2 + 2}px` }} />
                  ))}
                </div>
                <div className="w-5 h-2.5 rounded-sm border border-white/60 relative ml-1">
                  <div className="absolute inset-0.5 bg-[#FF5500] rounded-xs" style={{ width: "70%" }} />
                </div>
              </div>
            </div>

            {/* Chat header */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-white/5 mt-1">
              <motion.div 
                className="w-10 h-10 rounded-full bg-gradient-to-br from-[#000] to-[#010] flex items-center justify-center overflow-hidden"
                style={{
                  boxShadow: "0 0 20px rgba(81, 81, 81, 0.4)",
                }}
              >
                <Image src="/logo.png" alt="Alloha" width={28} height={28} className="object-contain" />
              </motion.div>
              <div className="flex-1">
                <div className="text-white font-semibold text-sm">Alloha</div>
                <div className="text-[#FF5500] text-[10px] flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#FF5500] animate-pulse" />
                  {t("phone.online")}
                </div>
              </div>
            </div>

            {/* Chat messages */}
            <div className="p-4 space-y-3">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 1, duration: 0.6 }}
                className="bg-[#1a1a1a] rounded-2xl rounded-tl-md px-3 py-2 max-w-[85%] text-white/90 text-xs"
              >
                {t("phone.chat1")}
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 1.5, duration: 0.6 }}
                className="ml-auto max-w-[85%]"
              >
                <div 
                  className="bg-gradient-to-r from-[#FF5500] to-[#FF7700] rounded-2xl rounded-tr-md px-3 py-2 text-black text-xs font-medium"
                  style={{
                    boxShadow: "0 4px 15px rgba(255,85,0,0.3)",
                  }}
                >
                  {t("phone.chat2")}
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 2, duration: 0.6 }}
                className="ml-auto max-w-[85%]"
              >
                <div 
                  className="bg-gradient-to-r from-[#FF5500] to-[#FF7700] rounded-2xl rounded-tr-md px-3 py-2 text-black text-xs font-medium"
                  style={{
                    boxShadow: "0 4px 15px rgba(255,85,0,0.3)",
                  }}
                >
                  {t("phone.chat3")}
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 2.5, duration: 0.6 }}
                className="bg-[#1a1a1a] rounded-2xl rounded-tl-md px-3 py-2 max-w-[85%] text-white/90 text-xs"
              >
                {t("phone.chat4")}
              </motion.div>
            </div>

            {/* Input area */}
            <div className="absolute bottom-4 left-3 right-3">
              <div 
                className="flex items-center gap-2 rounded-full px-4 py-2.5"
                style={{
                  background: "rgba(26,26,26,0.9)",
                  border: "1px solid rgba(255,85,0,0.2)",
                }}
              >
                <input
                  type="text"
                  placeholder={t("phone.placeholder")}
                  className="bg-transparent text-white text-xs flex-1 outline-none placeholder:text-white/30"
                  readOnly
                />
                <motion.div 
                  className="w-7 h-7 rounded-full bg-gradient-to-r from-[#FF5500] to-[#FF7700] flex items-center justify-center"
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                  style={{
                    boxShadow: "0 0 15px rgba(255,85,0,0.4)",
                  }}
                >
                  <ArrowRight className="w-3 h-3 text-black" />
                </motion.div>
              </div>
            </div>

            {/* Screen reflection */}
            <div 
              className="absolute inset-0 pointer-events-none"
              style={{
                background: "linear-gradient(135deg, rgba(255,255,255,0.03) 0%, transparent 50%)",
              }}
            />
          </div>
        </div>

        {/* Phone edge highlight */}
        <div 
          className="absolute inset-0 rounded-[45px] pointer-events-none"
          style={{
            background: "linear-gradient(135deg, rgba(255,255,255,0.1) 0%, transparent 30%, transparent 70%, rgba(255,255,255,0.05) 100%)",
          }}
        />
      </motion.div>
    </motion.div>
  );
}
