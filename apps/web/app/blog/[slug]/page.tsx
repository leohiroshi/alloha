import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { BlogShell } from "@/components/blog/BlogShell";
import { blogPosts, getBlogPostBySlug } from "@/lib/blog";

export default async function BlogPostPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = getBlogPostBySlug(slug);

  if (!post) {
    notFound();
  }

  const relatedPosts = blogPosts.filter((item) => item.slug !== post.slug).slice(0, 3);

  return (
    <BlogShell>
      <article className="mx-auto max-w-7xl px-4 pb-24 pt-14 sm:px-6 lg:px-8 lg:pt-18">
        <div className="mx-auto max-w-5xl">
          <Link href="/blog" className="inline-flex min-h-11 items-center gap-2 text-sm text-white/62 transition hover:text-white">
            <ArrowLeft className="h-4 w-4" />
            Voltar para o blog
          </Link>

          <div className="liquid-card mt-8 rounded-[32px] p-6 sm:p-8 lg:p-10">
            <div className="flex flex-wrap items-center gap-3 text-sm text-white/54">
              <span className="rounded-full border border-[#ff8c47]/18 bg-[#ff5500]/10 px-3 py-1 text-xs font-medium text-[#ffc6a2]">
                {post.categoryLabel}
              </span>
              <span>{post.readTime}</span>
              <span className="h-1 w-1 rounded-full bg-white/24" />
              <span>{post.author}</span>
              <span className="h-1 w-1 rounded-full bg-white/24" />
              <span>{post.date}</span>
            </div>

            <h1 className="mt-6 max-w-4xl text-4xl font-semibold tracking-[-0.05em] text-white sm:text-5xl lg:text-6xl">
              {post.title}
            </h1>
            <p className="mt-5 max-w-3xl text-base leading-8 text-white/62">{post.summary}</p>

            <div className="relative mt-8 h-[250px] overflow-hidden rounded-[24px] border border-white/10 bg-[#090909] sm:h-[320px]">
              <Image
                src={post.thumbnail}
                alt={post.thumbnailAlt}
                fill
                priority
                className="object-cover"
                sizes="(max-width: 1024px) 100vw, 960px"
              />
            </div>
          </div>
        </div>

        <div className="mx-auto mt-12 grid max-w-5xl gap-10 lg:grid-cols-[220px_minmax(0,1fr)]">
          <aside className="lg:sticky lg:top-28 lg:self-start">
            <div className="rounded-[22px] border border-white/8 bg-white/[0.03] p-5 backdrop-blur-xl">
              <p className="text-[11px] uppercase tracking-[0.24em] text-white/42">Neste artigo</p>
              <div className="mt-4 space-y-3">
                {post.sections.map((section, index) => (
                  <a
                    key={section.heading}
                    href={`#section-${index + 1}`}
                    className="block text-sm text-white/56 transition hover:text-[#ffc59f]"
                  >
                    {index + 1}. {section.heading}
                  </a>
                ))}
              </div>
            </div>
          </aside>

          <div className="space-y-10">
            {post.sections.map((section, index) => (
              <section key={section.heading} id={`section-${index + 1}`} className="scroll-mt-28">
                <div className="mb-4 h-px w-16 bg-[linear-gradient(90deg,#ff5500,transparent)]" />
                <h2 className="text-3xl font-semibold tracking-[-0.04em] text-white">
                  {index + 1}. {section.heading}
                </h2>
                <div className="mt-5 space-y-5 text-[15px] leading-8 text-white/68">
                  {section.paragraphs.map((paragraph) => (
                    <p key={paragraph}>{paragraph}</p>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </div>

        <div className="mx-auto mt-20 max-w-5xl">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-[11px] uppercase tracking-[0.24em] text-white/42">Leituras relacionadas</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-white">Continue explorando</h2>
            </div>
          </div>

          <div className="mt-8 grid gap-5 md:grid-cols-3">
            {relatedPosts.map((relatedPost) => (
              <Link
                key={relatedPost.slug}
                href={`/blog/${relatedPost.slug}`}
                className="group rounded-[24px] border border-white/8 bg-[linear-gradient(180deg,rgba(13,13,13,0.96),rgba(8,8,8,0.99))] p-4 transition duration-300 hover:-translate-y-1 hover:border-[#ff8f4d]/22"
              >
                <div className="relative h-[160px] overflow-hidden rounded-[16px] border border-white/8 bg-[#090909]">
                  <Image
                    src={relatedPost.thumbnail}
                    alt={relatedPost.thumbnailAlt}
                    fill
                    className="object-cover transition duration-500 group-hover:scale-[1.03]"
                    sizes="(max-width: 768px) 100vw, 33vw"
                  />
                </div>
                <div className="mt-4 flex items-center gap-3 text-xs text-white/48">
                  <span className="rounded-full border border-[#ff8d48]/18 bg-[#ff5500]/10 px-2.5 py-1 font-medium text-[#ffc6a1]">
                    {relatedPost.categoryLabel}
                  </span>
                  <span>{relatedPost.readTime}</span>
                </div>
                <h3 className="mt-4 text-2xl font-semibold tracking-[-0.035em] text-white">{relatedPost.title}</h3>
                <p className="mt-3 text-sm leading-7 text-white/58">{relatedPost.excerpt}</p>
              </Link>
            ))}
          </div>
        </div>
      </article>
    </BlogShell>
  );
}
