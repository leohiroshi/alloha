"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X } from "lucide-react";
import Image from "next/image";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { MagneticButton } from "../ui/MagneticButton";
import { LanguageSwitcher } from "../LanguageSwitcher";

export function Navigation() {
  const { t } = useLanguage();
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navItems = [
    { key: "nav.about", href: "#about" },
    { key: "nav.blog", href: "#blog" },
    { key: "nav.features", href: "#features" },
    { key: "nav.pricing", href: "#pricing" },
    { key: "nav.faq", href: "#faq" },
  ];

  React.useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 50);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <motion.nav
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="fixed top-0 left-0 right-0 z-50 px-4 md:px-6 py-4"
    >
      <div className={`mx-auto max-w-6xl rounded-full px-5 py-2.5 transition-all duration-500 ${
        isScrolled ? "bg-black/80 backdrop-blur-xl border border-white/10" : "bg-transparent"
      }`}>
        <div className="flex items-center justify-between">
          <motion.div className="flex items-center gap-2" whileHover={{ scale: 1.02 }}>
            <Image src="/logo.png" alt="Alloha" width={24} height={24} />
            <span className="text-lg font-bold text-white">Alloha</span>
          </motion.div>

          <div className="hidden md:flex items-center gap-6 text-sm">
            {navItems.map((item) => (
              <a key={item.key} href={item.href} className="text-white/60 hover:text-white transition-colors">
                {t(item.key)}
              </a>
            ))}
          </div>

          <div className="hidden md:flex items-center gap-3">
            <LanguageSwitcher />
            <MagneticButton className="bg-[#FF5500] text-black font-semibold px-5 py-2 rounded-full text-sm">
              {t("nav.bookCall")}
            </MagneticButton>
          </div>

          <button className="md:hidden text-white" onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}>
            {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="md:hidden mt-4 mx-4 rounded-2xl bg-black/95 backdrop-blur-xl border border-white/10 p-6"
          >
            <div className="flex flex-col gap-4">
              {navItems.map((item) => (
                <a key={item.key} href={item.href} className="text-white/70 hover:text-white py-2" onClick={() => setIsMobileMenuOpen(false)}>
                  {t(item.key)}
                </a>
              ))}
              <div className="pt-2">
                <LanguageSwitcher />
              </div>
              <MagneticButton className="bg-[#FF5500] text-black font-semibold px-5 py-3 rounded-full text-sm mt-2">
                {t("nav.bookCall")}
              </MagneticButton>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  );
}
