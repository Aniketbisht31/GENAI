import { Link } from 'react-router-dom'
import { MapPin, Clock, Flame, RotateCcw } from 'lucide-react'
import { SeverityBadge, StatusBadge, CategoryBadge, PriorityBar, CriticalBanner } from './UI'
import { reportsAPI } from '../api/client'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'

export default function ReportCard({ report, onHypeChange }) {
  const { user } = useAuth()
  const [hypeCount, setHypeCount] = useState(report.hype_count)
  const [hyped, setHyped] = useState(report.current_user_hyped)
  const [loading, setLoading] = useState(false)

  const toggleHype = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (loading) return
    if (report.reporter_id === user?.id) {
      toast.error("You can't hype your own report")
      return
    }
    setLoading(true)
    try {
      if (hyped) {
        const r = await reportsAPI.unhype(report.id)
        setHypeCount(r.data.hype_count)
        setHyped(false)
      } else {
        const r = await reportsAPI.hype(report.id)
        setHypeCount(r.data.hype_count)
        setHyped(true)
      }
      onHypeChange?.()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to hype')
    } finally {
      setLoading(false)
    }
  }

  const timeAgo = (dt) => {
    const diff = (Date.now() - new Date(dt + 'Z')) / 1000
    if (diff < 60) return 'just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return `${Math.floor(diff / 86400)}d ago`
  }

  return (
    <Link to={`/reports/${report.id}`} className="block">
      <div className="card cursor-pointer transition-all hover:border-primary/40 hover:shadow-md">
        {/* Safety critical banner */}
        {report.is_safety_critical && (
          <div className="mb-2">
            <CriticalBanner />
          </div>
        )}

        {/* Header row */}
        <div className="flex items-start gap-3">
          {/* Thumbnail */}
          {report.image_path && (
            <img
              src={`http://localhost:8000/${report.image_path}`}
              alt="hazard"
              className="w-16 h-16 rounded-lg object-cover flex-shrink-0 border border-gray-100"
            />
          )}

          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-gray-900 truncate">{report.title}</h3>
            <div className="flex items-center gap-1 text-xs text-gray-500 mt-0.5">
              <MapPin size={11} />
              <span>{report.building}{report.zone ? ` · ${report.zone}` : ''}</span>
              <span className="mx-1">·</span>
              <Clock size={11} />
              <span>{timeAgo(report.created_at)}</span>
            </div>
          </div>
        </div>

        {/* Badges row */}
        <div className="flex flex-wrap gap-1.5 mt-2.5">
          {report.intent === 'service_request'
            ? <span className="badge bg-blue-100 text-blue-800">Service request</span>
            : <SeverityBadge severity={report.severity} />}
          <StatusBadge status={report.status} />
          <CategoryBadge category={report.category} />
          {report.service_group && <span className="badge bg-violet-100 text-violet-800">{report.service_group}</span>}
          {report.service_subcategory && <span className="badge bg-indigo-100 text-indigo-800">{report.service_subcategory}</span>}
          {report.recurrence_count > 0 && (
            <span className="badge bg-purple-100 text-purple-800">
              <RotateCcw size={10} className="mr-1" />
              ×{report.recurrence_count} recurring
            </span>
          )}
        </div>

        {report.prompt_version && <p className="text-[10px] text-gray-400 mt-1">Classifier {report.prompt_version}</p>}

        {/* Priority bar */}
        <div className="mt-2.5">
          <PriorityBar score={report.priority_score} />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-50">
          <span className="text-xs text-gray-400">
            {report.is_anonymous ? 'Anonymous' : report.reporter_name}
          </span>

          {/* Hype button */}
          <button
            onClick={toggleHype}
            type="button"
            aria-label={`${hyped ? 'Remove hype from' : 'Hype'} ${report.title}`}
            aria-pressed={Boolean(hyped)}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold transition-all
              ${hyped
                ? 'bg-primary-light text-primary-dark hover:bg-blue-100'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
          >
            <Flame size={13} className={hyped ? 'fill-primary text-primary' : ''} />
            {hypeCount}
          </button>
        </div>
      </div>
    </Link>
  )
}
