import type { ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";

type BlogShellProps = {
  children: ReactNode;
};

const headerLinks = [
  { href: "/login?mode=signup", label: "Começar" },
  { href: "/blog", label: "Recursos" },
  { href: "/contact", label: "Suporte" },
];

const footerColumns = [
  {
    title: "Produto",
    links: [
      { href: "/login?mode=signup", label: "Primeiro acesso" },
      { href: "/dashboard", label: "Dashboard" },
      { href: "/signup", label: "Cadastrar" },
      { href: "/login", label: "Entrar" },
    ],
  },
  {
    title: "Conteúdo",
    links: [
      { href: "/blog", label: "Blog" },
      { href: "/blog/primeiro-mvp-sem-cron", label: "MVP sem cron" },
      { href: "/blog/como-validar-a-busca-de-imoveis", label: "Busca de imóveis" },
      { href: "/blog/novo-fluxo-de-onboarding-do-mvp", label: "Onboarding" },
    ],
  },
  {
    title: "Legal",
    links: [
      { href: "/privacy", label: "Política de Privacidade" },
      { href: "/terms", label: "Termos de Uso" },
      { href: "/contact", label: "Contato" },
    ],
  },
];

const quickLinks = [
  { href: "/", label: "Landing" },
  { href: "/login?mode=signup", label: "Começar" },
  { href: "/login", label: "Entrar" },
  { href: "/contact", label: "Contato" },
];

export function BlogShell({ children }: BlogShellProps) {
  return (
    <main className="relative min-h-screen overflow-hidden bg-[#050505] text-white">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_-10%,rgba(255,120,40,0.24),transparent_28%),radial-gradient(circle_at_14%_22%,rgba(255,85,0,0.12),transparent_26%),radial-gradient(circle_at_84%_18%,rgba(255,162,84,0.12),transparent_18%),linear-gradient(180deg,#090909_0%,#050505_45%,#020202_100%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.026)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.026)_1px,transparent_1px)] bg-[size:56px_56px] opacity-20" />
        <div className="absolute left-0 right-0 top-[76px] h-px bg-gradient-to-r from-transparent via-[#ff7b2f]/30 to-transparent" />
        <div className="absolute left-1/2 top-24 h-64 w-64 -translate-x-1/2 rounded-full bg-[#ff6b1b]/10 blur-3xl" />
        <div className="absolute bottom-0 left-0 right-0 h-48 bg-[linear-gradient(180deg,transparent,rgba(255,85,0,0.06))]" />
      </div>

      <div className="relative z-10">
        <header className="sticky top-0 z-30 border-b border-white/8 bg-black/68 backdrop-blur-2xl">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
            <Link href="/" className="flex min-h-11 items-center gap-3">
              <Image src="/logo.png" alt="Alloha" width={28} height={28} />
              <div className="leading-none">
                <p className="text-lg font-semibold tracking-[0.08em] text-white">ALLOHA</p>
                <p className="mt-1 text-[10px] uppercase tracking-[0.32em] text-white/42">real estate ai</p>
              </div>
            </Link>

            <nav className="liquid-nav hidden items-center rounded-full px-3 py-2 md:flex">
              {headerLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="min-h-10 rounded-full px-4 py-2 text-sm text-white/68 transition hover:bg-white/[0.04] hover:text-white"
                >
                  {link.label}
                </Link>
              ))}
            </nav>

            <div className="flex items-center gap-3">
              <span className="hidden text-[11px] font-semibold uppercase tracking-[0.28em] text-white/46 sm:block">
                BR PT
              </span>
              <Link href="/login" className="min-h-11 px-4 py-3 text-sm text-white/80 transition hover:text-white">
                Entrar
              </Link>
              <Link href="/login?mode=signup" className="aw-btn-primary min-h-11 rounded-2xl px-5 py-3 text-sm">
                Começar
              </Link>
            </div>
          </div>
        </header>

        {children}

        <footer className="mt-24 border-t border-white/8 bg-black/72">
          <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
            <div className="grid gap-12 lg:grid-cols-[1.4fr_2fr]">
              <div>
                <div className="flex items-center gap-3">
                  <Image src="/logo.png" alt="Alloha" width={30} height={30} />
                  <div>
                    <p className="text-2xl font-semibold tracking-[0.06em] text-white">ALLOHA</p>
                    <p className="text-xs uppercase tracking-[0.3em] text-white/42">real estate ai</p>
                  </div>
                </div>
                <p className="mt-6 max-w-sm text-sm leading-7 text-white/56">
                  Conteúdo para simplificar a operação imobiliária com IA, do primeiro setup à publicação.
                </p>
                <div className="mt-6 flex flex-wrap gap-3">
                  {quickLinks.map((link) => (
                    <Link
                      key={link.href + link.label}
                      href={link.href}
                      className="inline-flex min-h-11 items-center rounded-full border border-white/8 bg-white/[0.03] px-4 py-2 text-sm text-white/64 transition hover:border-[#ff8b4a]/28 hover:bg-white/[0.05] hover:text-white"
                    >
                      {link.label}
                    </Link>
                  ))}
                </div>
              </div>

              <div className="grid gap-8 sm:grid-cols-3">
                {footerColumns.map((column) => (
                  <div key={column.title}>
                    <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#ffb177]">{column.title}</p>
                    <div className="mt-5 space-y-3">
                      {column.links.map((link) => (
                        <Link key={link.href + link.label} href={link.href} className="block text-sm text-white/52 transition hover:text-white">
                          {link.label}
                        </Link>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-14 border-t border-white/8 pt-10 text-center">
              <p className="text-sm uppercase tracking-[0.42em] text-white/64">100% brasileira</p>
              <p className="mt-6 text-sm text-white/44">Alloha 2026. Produto, conteúdo e operação na mesma direção.</p>
            </div>
          </div>
        </footer>
      </div>
    </main>
  );
}
