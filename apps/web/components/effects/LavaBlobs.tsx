"use client";

import { motion } from "framer-motion";

export function LavaBlobs() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none">
      <motion.div
        className="absolute w-[900px] h-[900px] rounded-full"
        style={{
          background:
            "radial-gradient(circle, rgba(255,85,0,0.25) 0%, rgba(255,85,0,0.08) 40%, transparent 70%)",
          top: "-10%",
          right: "-15%",
          filter: "blur(80px)",
        }}
        animate={{
          x: [0, 50, -30, 0],
          y: [0, -40, 20, 0],
          scale: [1, 1.1, 0.95, 1],
        }}
        transition={{ duration: 25, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute w-[600px] h-[600px] rounded-full"
        style={{
          background:
            "radial-gradient(circle, rgba(138,43,226,0.2) 0%, rgba(138,43,226,0.05) 40%, transparent 70%)",
          top: "30%",
          left: "-5%",
          filter: "blur(100px)",
        }}
        animate={{
          x: [0, -40, 30, 0],
          y: [0, 30, -40, 0],
          scale: [1, 0.9, 1.1, 1],
        }}
        transition={{ duration: 30, repeat: Infinity, ease: "easeInOut", delay: 5 }}
      />
      <motion.div
        className="absolute w-[500px] h-[500px] rounded-full"
        style={{
          background:
            "radial-gradient(circle, rgba(255,85,0,0.2) 0%, transparent 60%)",
          bottom: "5%",
          right: "10%",
          filter: "blur(70px)",
        }}
        animate={{
          scale: [1, 1.2, 0.9, 1],
          opacity: [0.3, 0.5, 0.3],
        }}
        transition={{ duration: 20, repeat: Infinity, ease: "easeInOut", delay: 10 }}
      />
    </div>
  );
}
