import { useState, useEffect, useCallback } from 'react'
import { reportsAPI, locationsAPI } from '../api/client'
import ReportCard from '../components/ReportCard'
import { ReportCardSkeleton, EmptyState } from '../components/UI'
import { Search, SlidersHorizontal, ChevronLeft, ChevronRight } from 'lucide-react'
import PageCard from '../components/PageCard'
import Tabs from '../components/Tabs'

const STATUSES = ['reported', 'assigned', 'in_progress', 'pending_confirmation', 'resolved', 'reopened']
const CATEGORIES = ['electrical', 'civil', 'security', 'other']
const SORTS = [
  { value: 'priority', label: '🔥 Priority' },
  { value: 'newest', label: '🕐 Newest' },
  { value: 'hype', label: '📣 Hype' },
]

export default function HomePage() {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(1)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({ status: '', category: '', building: '', sort: 'priority' })
  const [locations, setLocations] = useState([])
  const [showFilters, setShowFilters] = useState(false)

  useEffect(() => {
    locationsAPI.list().then(r => setLocations(r.data)).catch(() => {})
  }, [])

  const fetchReports = useCallback(() => {
    setLoading(true)
    const params = { page, page_size: 15, sort: filters.sort }
    if (filters.status) params.status = filters.status
    if (filters.category) params.category = filters.category
    if (filters.building) params.building = filters.building

    reportsAPI.list(params)
      .then(r => {
        setReports(r.data.items)
        setTotal(r.data.total)
        setPages(r.data.pages)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [page, filters])

  useEffect(() => { fetchReports() }, [fetchReports])

  const setFilter = (k) => (v) => {
    setFilters(f => ({ ...f, [k]: v }))
    setPage(1)
  }

  const buildings = [...new Set(locations.map(l => l.building))]

  return (
    <div className="mx-auto max-w-4xl">
      <PageCard title="Campus Hazard Feed" actions={<><span className="hidden text-xs text-blue-50 sm:inline">{total} report{total !== 1 ? 's' : ''} found</span><button
          onClick={() => setShowFilters(!showFilters)}
          aria-expanded={showFilters}
          className={`flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-semibold transition-colors ${
            showFilters ? 'border-white bg-white text-primary' : 'border-white/50 text-white hover:bg-white/10'
          }`}
        >
          <SlidersHorizontal size={14} />
          Filters
        </button></>}>
      <p className="mb-3 text-xs text-slate-500 sm:hidden">{total} report{total !== 1 ? 's' : ''} found</p>

      {/* Sort pills */}
      <Tabs className="mb-4" value={filters.sort} onChange={value => setFilter('sort')(value)} items={SORTS.map(s => ({ key: s.value, label: s.label }))} />

      {/* Filter panel */}
      {showFilters && (
        <div className="card mb-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
            <select className="input text-xs" value={filters.status} onChange={e => setFilter('status')(e.target.value)}>
              <option value="">All statuses</option>
              {STATUSES.map(s => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Category</label>
            <select className="input text-xs" value={filters.category} onChange={e => setFilter('category')(e.target.value)}>
              <option value="">All categories</option>
              {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Building</label>
            <select className="input text-xs" value={filters.building} onChange={e => setFilter('building')(e.target.value)}>
              <option value="">All buildings</option>
              {buildings.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
          <div className="col-span-2 sm:col-span-3">
            <button className="text-xs font-semibold text-primary hover:underline" onClick={() => {
              setFilters({ status: '', category: '', building: '', sort: 'priority' }); setPage(1)
            }}>
              Clear all filters
            </button>
          </div>
        </div>
      )}

      {/* Report list */}
      <div className="space-y-3">
        {loading
          ? Array.from({ length: 5 }).map((_, i) => <ReportCardSkeleton key={i} />)
          : reports.length === 0
            ? <EmptyState icon="🏫" title="No reports found" description="Try changing your filters or be the first to report a hazard." />
            : reports.map(r => <ReportCard key={r.id} report={r} onHypeChange={fetchReports} />)
        }
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-center gap-3 mt-6">
          <button
            disabled={page === 1}
            onClick={() => setPage(p => p - 1)}
            className="p-2 rounded-lg border disabled:opacity-40 hover:bg-gray-50"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="text-sm text-gray-600">Page {page} of {pages}</span>
          <button
            disabled={page === pages}
            onClick={() => setPage(p => p + 1)}
            className="p-2 rounded-lg border disabled:opacity-40 hover:bg-gray-50"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      )}
      </PageCard>
    </div>
  )
}
