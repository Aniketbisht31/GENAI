import { useState, useEffect } from 'react'
import { reportsAPI } from '../api/client'
import ReportCard from '../components/ReportCard'
import { ReportCardSkeleton, EmptyState } from '../components/UI'
import { Link } from 'react-router-dom'
import PageCard from '../components/PageCard'

export default function MyReportsPage() {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    reportsAPI.mine()
      .then(r => setReports(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="mx-auto max-w-4xl">
      <PageCard title="My Reports" actions={<Link to="/report/new" className="inline-flex items-center rounded-md border border-white/70 px-3 py-1.5 text-xs font-bold text-white transition-colors hover:bg-white hover:text-primary">+ New Report</Link>}>
      <div className="space-y-3">
        {loading
          ? Array.from({ length: 3 }).map((_, i) => <ReportCardSkeleton key={i} />)
          : reports.length === 0
            ? <EmptyState icon="📋" title="No reports yet" description="Report a campus hazard to get started." />
            : reports.map(r => <ReportCard key={r.id} report={r} />)
        }
      </div>
      </PageCard>
    </div>
  )
}
