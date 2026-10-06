export default function PageCard({ title, actions, children, className = '' }) {
  return (
    <section className={`overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm ${className}`}>
      <header className="flex min-h-12 flex-wrap items-center justify-between gap-3 bg-primary px-4 py-3 text-white">
        <h2 className="text-sm font-bold sm:text-base">{title}</h2>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </header>
      <div className="p-4 sm:p-5">{children}</div>
    </section>
  )
}
