'use client'
import { useState, useEffect } from 'react'
import { TopNav } from '@/components/layout/TopNav'
import { Footer } from '@/components/layout/Footer'
import { getLegalNews, NewsArticle } from '@/services/newsService'

export default function NewsPage() {
  const [articles, setArticles] = useState<NewsArticle[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getLegalNews().then((r) => {
      setArticles(r.articles || [])
      setLoading(false)
    })
  }, [])

  return (
    <div className="flex min-h-screen flex-col bg-[#08090C] text-slate-100 font-sans antialiased">
      <TopNav />
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-12 md:py-16">
        {/* Header section */}
        <div className="flex flex-col md:flex-row md:items-end justify-between border-b border-white/[0.08] pb-8 gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse-dot" />
              <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400">
                Live Law Wire
              </span>
            </div>
            <h1 className="font-[var(--font-serif)] text-3xl font-medium tracking-tight text-white md:text-4xl">
              Legal & Constitutional News
            </h1>
            <p className="mt-2 text-xs text-slate-400 max-w-lg">
              Verified legal updates, Supreme Court rulings, and statutory amendments from the last 24 hours.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs text-white/40">
            <span>Aggregated from verified Indian legal portals</span>
          </div>
        </div>

        {/* Loading state skeleton */}
        {loading && (
          <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((idx) => (
              <div
                key={idx}
                className="animate-pulse rounded-xl border border-white/[0.06] bg-[#12151E] p-4 h-72 flex flex-col justify-between"
              >
                <div className="h-36 w-full rounded-lg bg-white/[0.04]" />
                <div className="space-y-2 mt-4">
                  <div className="h-4 w-3/4 rounded bg-white/[0.06]" />
                  <div className="h-3 w-full rounded bg-white/[0.03]" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && articles.length === 0 && (
          <div className="my-16 flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 p-12 text-center">
            <span className="text-3xl mb-2">📰</span>
            <p className="text-sm font-medium text-slate-300">
              No recent legal articles indexed within the 24-hour window.
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Check back shortly as new court rulings and gazette notifications are published.
            </p>
          </div>
        )}

        {/* News Cards Grid */}
        {!loading && articles.length > 0 && (
          <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {articles.map((a, i) => (
              <a
                key={i}
                href={a.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex flex-col overflow-hidden rounded-xl border border-white/[0.08] bg-gradient-to-b from-[#141722] to-[#0E1017] transition-all hover:-translate-y-1 hover:border-blue-500/30 hover:shadow-xl no-underline"
              >
                {a.image && (
                  <div className="relative h-44 w-full overflow-hidden bg-white/[0.02]">
                    <img
                      src={a.image}
                      alt={a.title}
                      className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                      loading="lazy"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#0E1017] via-transparent to-transparent opacity-60" />
                  </div>
                )}
                <div className="flex flex-1 flex-col justify-between p-5">
                  <div>
                    <div className="mb-2 flex items-center justify-between text-[10px] text-white/40">
                      <span className="font-semibold uppercase tracking-wider text-blue-400">
                        {a.source || "Legal Dispatch"}
                      </span>
                      {a.date && <span>{new Date(a.date).toLocaleDateString()}</span>}
                    </div>
                    <h2 className="text-sm font-semibold leading-snug text-slate-100 group-hover:text-blue-300 transition-colors">
                      {a.title}
                    </h2>
                    <p className="mt-2 text-xs leading-relaxed text-slate-400 line-clamp-3">
                      {a.summary}
                    </p>
                  </div>
                  <div className="mt-4 flex items-center gap-1 text-[11px] font-medium text-blue-400">
                    <span>Read full article</span>
                    <span className="transition-transform group-hover:translate-x-0.5">→</span>
                  </div>
                </div>
              </a>
            ))}
          </div>
        )}
      </main>
      <Footer />
    </div>
  )
}