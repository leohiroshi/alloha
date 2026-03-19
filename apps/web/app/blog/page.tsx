"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { BlogShell } from "@/components/blog/BlogShell";
import { blogPosts, type BlogCategory, blogCategoryLabels } from "@/lib/blog";

type FilterKey = "all" | BlogCategory;

const categoryOrder: BlogCategory[] = ["tutorials", "tips", "news"];

export default function BlogPage() {
  const [activeFilter, setActiveFilter] = useState<FilterKey>("all");

  const filteredPosts =
    activeFilter === "all" ? blogPosts : blogPosts.filter((post) => post.category === activeFilter);

  const [featuredPost, ...gridPosts] = filteredPosts;

  const filters = [
    { key: "all" as const, label: "Todos", count: blogPosts.length },
    ...categoryOrder.map((category) => ({
      key: category,
      label: blogCategoryLabels[category],
      count: blogPosts.filter((post) => post.category === category).length,
    })),
  ];

  return (
    <BlogShell>
      <section className="mx-auto max-w-7xl px-4 pb-24 pt-14 sm:px-6 lg:px-8 lg:pt-20">
        <div className="mx-auto max-w-3xl text-center">
          <div className="glass-chip justify-center border-[#ff8e50]/18 bg-[#ff5500]/8 text-[#ffc7a5]">
            Conteúdo Alloha
          </div>
          <h1 className="mt-8 text-5xl font-semibold tracking-[-0.05em] text-white sm:text-6xl">Blog</h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-white/62">
            Guias curtos, novidades e decisões de produto para vender melhor, operar com menos fricção e evoluir o MVP com clareza.
          </p>
        </div>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
          {filters.map((filter) => {
            const isActive = activeFilter === filter.key;
            return (
              <button
                key={filter.key}
                type="button"
                onClick={() => setActiveFilter(filter.key)}
                className={`inline-flex min-h-11 items-center rounded-full border px-4 py-2 text-sm transition ${
                  isActive
                    ? "border-[#ff8e4a]/32 bg-[linear-gradient(135deg,rgba(255,85,0,0.24),rgba(255,141,58,0.12))] text-white shadow-[0_0_0_1px_rgba(255,85,0,0.08)_inset]"
                    : "border-white/8 bg-white/[0.02] text-white/62 hover:border-[#ff8b4a]/20 hover:text-white"
                }`}
              >
                {filter.label} ({filter.count})
              </button>
            );
          })}
        </div>

        {featuredPost ? (
          <Link
            href={`/blog/${featuredPost.slug}`}
            className="group liquid-card mt-16 block rounded-[30px] p-5 transition duration-300 hover:-translate-y-1 hover:border-[#ff8f4d]/28"
          >
            <div className="grid gap-5 md:grid-cols-[280px_minmax(0,1fr)] lg:grid-cols-[320px_minmax(0,1fr)]">
              <div className="relative min-h-[220px] overflow-hidden rounded-[22px] border border-white/10 bg-[#090909] shadow-[0_18px_48px_rgba(0,0,0,0.34)]">
                <Image
                  src={featuredPost.thumbnail}
                  alt={featuredPost.thumbnailAlt}
                  fill
                  priority
                  className="object-cover transition duration-500 group-hover:scale-[1.02]"
                  sizes="(max-width: 768px) 100vw, 320px"
                />
                <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(0,0,0,0)_35%,rgba(0,0,0,0.12)_100%)]" />
              </div>
              <div className="flex flex-col justify-center px-2 py-1 md:px-3">
                <div className="flex flex-wrap items-center gap-3 text-sm text-white/58">
                  <span className="rounded-full border border-[#ff8d48]/20 bg-[#ff5500]/12 px-3 py-1 text-xs font-medium text-[#ffc7a4]">
                    {featuredPost.categoryLabel}
                  </span>
                  <span>{featuredPost.readTime}</span>
                </div>
                <h2 className="mt-5 max-w-2xl text-3xl font-semibold tracking-[-0.04em] text-white sm:text-[2.35rem]">
                  {featuredPost.title}
                </h2>
                <p className="mt-4 max-w-2xl text-base leading-8 text-white/62">{featuredPost.excerpt}</p>
                <div className="mt-7 flex flex-wrap items-center gap-3 text-sm text-white/58">
                  <span>{featuredPost.author}</span>
                  <span className="h-1 w-1 rounded-full bg-white/28" />
                  <span>{featuredPost.date}</span>
                </div>
              </div>
            </div>
          </Link>
        ) : null}

        <div className="mt-16 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {gridPosts.map((post) => (
            <Link
              key={post.slug}
              href={`/blog/${post.slug}`}
              className="group rounded-[26px] border border-white/8 bg-[linear-gradient(180deg,rgba(13,13,13,0.96),rgba(8,8,8,0.99))] p-4 shadow-[0_16px_40px_rgba(0,0,0,0.24)] transition duration-300 hover:-translate-y-1 hover:border-[#ff8e4b]/22 hover:bg-[linear-gradient(180deg,rgba(18,18,18,0.98),rgba(8,8,8,1))]"
            >
              <div className="relative h-[190px] overflow-hidden rounded-[18px] border border-white/8 bg-[#090909]">
                <Image
                  src={post.thumbnail}
                  alt={post.thumbnailAlt}
                  fill
                  className="object-cover transition duration-500 group-hover:scale-[1.03]"
                  sizes="(max-width: 768px) 100vw, (max-width: 1280px) 50vw, 33vw"
                />
                <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(0,0,0,0)_38%,rgba(0,0,0,0.18)_100%)]" />
              </div>

              <div className="mt-4 flex items-center gap-3 text-xs text-white/48">
                <span className="rounded-full border border-[#ff8d48]/18 bg-[#ff5500]/10 px-2.5 py-1 font-medium text-[#ffc6a1]">
                  {post.categoryLabel}
                </span>
                <span>{post.readTime}</span>
              </div>

              <h3 className="mt-4 text-2xl font-semibold tracking-[-0.035em] text-white">{post.title}</h3>
              <p className="mt-3 line-clamp-3 text-sm leading-7 text-white/58">{post.excerpt}</p>

              <div className="mt-6 flex items-center gap-3 text-sm text-white/50">
                <span>{post.author}</span>
                <span className="h-1 w-1 rounded-full bg-white/24" />
                <span>{post.date}</span>
              </div>
            </Link>
          ))}
        </div>

        <div className="mt-16 flex justify-center">
          <Link
            href={featuredPost ? `/blog/${featuredPost.slug}` : "/contact"}
            className="aw-btn-secondary rounded-2xl border-[#ff8f4d]/18 bg-white/[0.04] px-6 py-3 text-sm text-white hover:border-[#ff9a5f]/28"
          >
            {featuredPost ? "Ler destaque" : "Falar com a Alloha"}
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </BlogShell>
  );
}
