"use client";

import Image from "next/image";
import { useLanguage } from "@/lib/i18n/LanguageContext";

export function Footer() {
  const { t } = useLanguage();
  
  const footerLinks = [
    { key: "footer.privacy", href: "#" },
    { key: "footer.terms", href: "#" },
    { key: "footer.contact", href: "#" },
  ];
  
  return (
    <footer className="py-12 px-6 border-t border-white/10">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <Image src="/logo.png" alt="Alloha" width={24} height={24} />
            <span className="text-lg font-bold text-white">Alloha</span>
          </div>

          <div className="flex items-center gap-8 text-sm text-white/40">
            {footerLinks.map((item) => (
              <a key={item.key} href={item.href} className="hover:text-white transition-colors">
                {t(item.key)}
              </a>
            ))}
          </div>

          <p className="text-sm text-white/30">{t("footer.rights")}</p>
        </div>
      </div>
    </footer>
  );
}
