import type { ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";

type NavLink = {
  href: string;
  label: string;
};

type ExperienceStat = {
  value: string;
  label: string;
};

type ExperienceShellProps = {
  children: ReactNode;
  navLinks?: NavLink[];
};

type ExperienceHeroProps = {
  eyebrow: string;
  title: ReactNode;
  description: ReactNode;
  actions?: ReactNode;
  stats?: ExperienceStat[];
  aside?: ReactNode;
};

type LiquidCardProps = {
  children: ReactNode;
  className?: string;
};

const defaultNavLinks: NavLink[] = [
  { href: "/blog", label: "Blog" },
  { href: "/privacy", label: "Privacidade" },
  { href: "/contact", label: "Contato" },
];

export function ExperienceShell({ children, navLinks = defaultNavLinks }: ExperienceShellProps) {
  return (
    <main className="experience-page text-white">
      <div className="relative z-10 mx-auto max-w-7xl px-4 pb-16 pt-5 sm:px-6 lg:px-8">
        <header className="liquid-nav rounded-full px-4 py-3 sm:px-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <Link href="/" className="flex min-h-11 items-center gap-3">
              <Image src="/logo.png" alt="Alloha" width={28} height={28} />
              <div>
                <p className="text-sm font-semibold tracking-[0.18em] uppercase text-white/92">Alloha</p>
                <p className="text-[11px] uppercase tracking-[0.22em] text-white/42">Real Estate AI</p>
              </div>
            </Link>

            <div className="flex flex-wrap items-center gap-2 sm:justify-end">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="glass-chip min-h-11 justify-center px-4 text-[11px] text-white/76 hover:text-white"
                >
                  {link.label}
                </Link>
              ))}
              <Link href="/" className="aw-btn-primary px-5 text-sm">
                Voltar para landing
              </Link>
            </div>
          </div>
        </header>

        {children}
      </div>
    </main>
  );
}

export function ExperienceHero({
  eyebrow,
  title,
  description,
  actions,
  stats = [],
  aside,
}: ExperienceHeroProps) {
  return (
    <section className="grid gap-6 pb-10 pt-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)] lg:items-end lg:gap-8 lg:pt-14">
      <div className="space-y-6">
        <div className="editorial-kicker">
          <span className="h-2 w-2 rounded-full bg-[#ff7b2c]" />
          {eyebrow}
        </div>

        <div className="space-y-5">
          <h1 className="editorial-title max-w-5xl">{title}</h1>
          <div className="editorial-subtitle">{description}</div>
        </div>

        {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}

        {stats.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-3">
            {stats.map((stat) => (
              <div key={`${stat.value}-${stat.label}`} className="metric-pill">
                <span className="metric-value">{stat.value}</span>
                <span className="metric-label">{stat.label}</span>
              </div>
            ))}
          </div>
        ) : null}
      </div>

      {aside ? <LiquidCard className="p-6 sm:p-7">{aside}</LiquidCard> : null}
    </section>
  );
}

export function LiquidCard({ children, className = "" }: LiquidCardProps) {
  return <section className={`liquid-card ${className}`.trim()}>{children}</section>;
}
