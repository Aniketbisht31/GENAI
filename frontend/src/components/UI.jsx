// Shared UI components

// ── Severity Badge ────────────────────────────────────────────────────────────
export function SeverityBadge({ severity }) {
  const labels = { 1: 'Low', 2: 'Minor', 3: 'Moderate', 4: 'High', 5: 'Critical' }
  return (
    <span className={`badge severity-${severity}`}>
      S{severity} · {labels[severity] || 'Unknown'}
    </span>
  )
}

// ── Status Badge ──────────────────────────────────────────────────────────────
export function StatusBadge({ status }) {
  const label = status?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  return <span className={`badge status-${status}`}>{label}</span>
}

// ── Category Badge ────────────────────────────────────────────────────────────
export function CategoryBadge({ category }) {
  const colors = {
    electrical: 'bg-yellow-100 text-yellow-800',
    civil: 'bg-blue-100 text-blue-800',
    security: 'bg-slate-100 text-slate-800',
    other: 'bg-gray-100 text-gray-800',
  }
  return (
    <span className={`badge ${colors[category] || colors.other}`}>
      {category}
    </span>
  )
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
export function Skeleton({ className = 'h-4 w-full' }) {
  return <div className={`skeleton ${className}`} />
}

export function ReportCardSkeleton() {
  return (
    <div className="card space-y-3">
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
      <div className="flex gap-2">
        <Skeleton className="h-6 w-16 rounded-full" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
    </div>
  )
}

// ── Priority Bar ──────────────────────────────────────────────────────────────
export function PriorityBar({ score }) {
  const color = score >= 80 ? 'bg-table-purple' : score >= 50 ? 'bg-primary' : score >= 30 ? 'bg-sky-500' : 'bg-green-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-bold text-gray-600">{Math.round(score)}</span>
    </div>
  )
}

// ── Empty State ───────────────────────────────────────────────────────────────
export function EmptyState({ icon = '📭', title = 'Nothing here yet', description = '' }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-5xl mb-3">{icon}</div>
      <h3 className="font-semibold text-gray-800 text-lg">{title}</h3>
      {description && <p className="text-gray-500 text-sm mt-1">{description}</p>}
    </div>
  )
}

// ── Loading Spinner ───────────────────────────────────────────────────────────
export function Spinner({ size = 'md' }) {
  const sz = size === 'sm' ? 'h-4 w-4' : size === 'lg' ? 'h-8 w-8' : 'h-6 w-6'
  return (
    <div role="status" aria-label="Loading" className={`${sz} border-2 border-primary border-t-transparent rounded-full animate-spin`} />
  )
}

// ── Safe Critical Banner ──────────────────────────────────────────────────────
export function CriticalBanner() {
  return (
    <div className="flex items-center gap-2 bg-red-600 text-white text-xs font-bold px-3 py-1 rounded-full animate-pulse">
      🚨 SAFETY CRITICAL
    </div>
  )
}
