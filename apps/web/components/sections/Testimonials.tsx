"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Star } from "lucide-react";
import Image from "next/image";
import { useLanguage } from "@/lib/i18n/LanguageContext";

interface TestimonialCardProps {
  quote: string;
  author: string;
  role: string;
  image: string;
  rating?: number;
  delay?: number;
}

function TestimonialCard({
  quote,
  author,
  role,
  image,
  rating = 5,
  delay = 0,
}: TestimonialCardProps) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.8, delay, ease: [0.16, 1, 0.3, 1] }}
      className="relative rounded-3xl bg-[#0a0a0a] border border-white/10 overflow-hidden"
    >
      <div className="flex flex-row h-[320px]">
        {/* Content */}
        <div className="flex-1 p-8 md:p-10 flex flex-col justify-center z-10 relative">
          {/* Stars */}
          <div className="flex gap-1 mb-4">
            {[...Array(rating)].map((_, i) => (
              <Star key={i} className="w-4 h-4 fill-[#FF5500] text-[#FF5500]" />
            ))}
          </div>

          <p className="text-white/90 text-base md:text-lg leading-relaxed mb-6 font-serif italic max-w-md">{quote}</p>

          <div>
            <p className="text-white font-semibold text-base">{author}</p>
            <p className="text-white/40 text-sm">{role}</p>
          </div>
        </div>

        {/* Image positioned to the right with heavy gradient overlay */}
        <div className="absolute right-0 top-0 bottom-0 w-[55%] md:w-[50%]">
          <Image
            src={image}
            alt={author}
            fill
            className="object-cover object-top"
          />
          {/* Multiple gradient layers for smooth dark transition */}
          <div className="absolute inset-0 bg-gradient-to-r from-[#0a0a0a] via-[#0a0a0a]/95 via-30% to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#0a0a0a] via-[#0a0a0a]/70 via-40% to-[#0a0a0a]/20" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0a]/50 to-transparent" />
        </div>
      </div>
    </motion.div>
  );
}

export function Testimonials() {
  const { t } = useLanguage();
  
  const testimonials = [
    {
      quote: t("testimonial1.quote"),
      author: t("testimonial1.author"),
      role: t("testimonial1.role"),
      image: "/customers/customer1.jpg",
    },
    {
      quote: t("testimonial2.quote"),
      author: t("testimonial2.author"),
      role: t("testimonial2.role"),
      image: "/customers/customer2.jpg",
    },
    {
      quote: t("testimonial3.quote"),
      author: t("testimonial3.author"),
      role: t("testimonial3.role"),
      image: "/customers/customer3.jpg",
    },
  ];

  return (
    <section className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col gap-6">
          {testimonials.map((testimonial, i) => (
            <TestimonialCard key={i} {...testimonial} delay={i * 0.1} />
          ))}
        </div>
      </div>
    </section>
  );
}
