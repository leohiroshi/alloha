import Image from "next/image";
import Link from "next/link";

type LegalSection = {
  id: string;
  title: string;
  paragraphs: string[];
};

type LegalDocLink = {
  href: string;
  label: string;
  active?: boolean;
};

type LegalDocumentLayoutProps = {
  label: string;
  title: string;
  version: string;
  intro: string[];
  sections: LegalSection[];
  documentLinks: LegalDocLink[];
};

const topLinks = [
  { href: "/", label: "Home" },
  { href: "/blog", label: "Blog" },
  { href: "/contact", label: "Contact" },
  { href: "/login", label: "Login" },
];

export function LegalDocumentLayout({
  label,
  title,
  version,
  intro,
  sections,
  documentLinks,
}: LegalDocumentLayoutProps) {
  return (
    <main className="min-h-screen bg-black text-white">
      <header className="sticky top-0 z-40 border-b border-white/8 bg-black/88 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-4 py-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex min-h-11 items-center gap-3 text-white">
            <Image src="/logo.png" alt="Alloha" width={18} height={18} />
            <span className="text-xs font-semibold uppercase tracking-[0.24em] text-white/78">Alloha</span>
          </Link>

          <nav className="hidden items-center gap-6 md:flex">
            {topLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-[11px] uppercase tracking-[0.2em] text-white/42 transition-colors hover:text-white/78"
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <Link
            href="/contact"
            className="min-h-11 rounded-full border border-white/10 px-4 py-2 text-[11px] uppercase tracking-[0.2em] text-white/72 transition hover:border-[#ff7d2f]/30 hover:text-white"
          >
            Contact us
          </Link>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 pb-20 pt-10 sm:px-6 lg:px-8 lg:pb-28 lg:pt-14">
        <div className="grid gap-12 lg:grid-cols-[220px_minmax(0,1fr)] lg:gap-16">
          <aside className="lg:sticky lg:top-28 lg:self-start">
            <div className="space-y-8">
              <div>
                <p className="text-[10px] uppercase tracking-[0.28em] text-[#ff8b47]">{label}</p>
                <div className="mt-4 space-y-2">
                  {documentLinks.map((link) => (
                    <Link
                      key={link.href}
                      href={link.href}
                      className={`block text-sm transition-colors ${
                        link.active ? "text-white" : "text-white/46 hover:text-white/78"
                      }`}
                    >
                      {link.label}
                    </Link>
                  ))}
                </div>
              </div>

              <div className="hidden lg:block">
                <p className="text-[10px] uppercase tracking-[0.28em] text-white/28">On this page</p>
                <nav className="mt-4 space-y-2">
                  {sections.map((section, index) => (
                    <a
                      key={section.id}
                      href={`#${section.id}`}
                      className="block text-sm text-white/42 transition-colors hover:text-white/80"
                    >
                      {index + 1}. {section.title}
                    </a>
                  ))}
                </nav>
              </div>
            </div>
          </aside>

          <article className="max-w-3xl">
            <div className="border-b border-white/8 pb-10">
              <p className="text-[11px] uppercase tracking-[0.28em] text-white/34">{label}</p>
              <h1 className="mt-5 text-4xl font-semibold tracking-[-0.04em] text-white sm:text-5xl">
                {title}
              </h1>
              <p className="mt-4 text-sm text-white/42">{version}</p>

              <div className="mt-8 space-y-5 text-[15px] leading-8 text-white/66">
                {intro.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </div>
            </div>

            <div className="mt-8 space-y-12">
              {sections.map((section, index) => (
                <section key={section.id} id={section.id} className="scroll-mt-28">
                  <h2 className="text-2xl font-semibold tracking-[-0.03em] text-white">
                    {index + 1}. {section.title}
                  </h2>
                  <div className="mt-5 space-y-4 text-[15px] leading-8 text-white/66">
                    {section.paragraphs.map((paragraph) => (
                      <p key={paragraph}>{paragraph}</p>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </article>
        </div>
      </div>
    </main>
  );
}
