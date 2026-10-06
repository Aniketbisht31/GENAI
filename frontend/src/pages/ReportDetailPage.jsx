import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { reportsAPI } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { SeverityBadge, StatusBadge, CategoryBadge, Spinner, CriticalBanner } from '../components/UI'
import toast from 'react-hot-toast'
import { MapPin, Clock, Flame, CheckCircle, XCircle, RotateCcw, BarChart3 } from 'lucide-react'
import PageCard from '../components/PageCard'
import Tabs from '../components/Tabs'

const STATUS_STEPS = ['reported', 'assigned', 'in_progress', 'pending_confirmation', 'resolved']

export default function ReportDetailPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [hyped, setHyped] = useState(false)
  const [hypeCount, setHypeCount] = useState(0)
  const [hypeLoading, setHypeLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('details')
  const [confirmLoading, setConfirmLoading] = useState(false)

  const fetchReport = () => {
    setLoading(true)
    reportsAPI.get(id)
      .then(r => {
        setReport(r.data)
        setHyped(r.data.current_user_hyped)
        setHypeCount(r.data.hype_count)
      })
      .catch(() => toast.error('Report not found'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchReport() }, [id])

  const toggleHype = async () => {
    if (hypeLoading) return
    setHypeLoading(true)
    try {
      const r = hyped ? await reportsAPI.unhype(id) : await reportsAPI.hype(id)
      setHypeCount(r.data.hype_count)
      setHyped(r.data.current_user_hyped)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error')
    } finally {
      setHypeLoading(false)
    }
  }

  const handleConfirm = async (confirmed) => {
    setConfirmLoading(true)
    try {
      await reportsAPI.confirm(id, confirmed)
      toast.success(confirmed ? 'Resolution confirmed!' : 'Dispute submitted. Issue reopened.')
      fetchReport()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error')
    } finally {
      setConfirmLoading(false)
    }
  }

  const timeAgo = (dt) => {
    if (!dt) return ''
    const diff = (Date.now() - new Date(dt + 'Z')) / 1000
    if (diff < 60) return 'just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return `${Math.floor(diff / 86400)}d ago`
  }

  if (loading) return (
    <div className="flex justify-center py-16"><Spinner size="lg" /></div>
  )
  if (!report) return <div className="text-center py-16 text-gray-500">Report not found</div>

  const stepIndex = STATUS_STEPS.indexOf(report.status)

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      {/* Back */}
      <button onClick={() => navigate(-1)} className="rounded text-sm font-semibold text-slate-600 hover:text-primary">← Back</button>

      {/* Critical banner */}
      {report.is_safety_critical && <CriticalBanner />}

      {/* Header */}
      <PageCard title={report.title}>
        <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
          <MapPin size={12} />
          <span>{report.building}{report.zone ? ` · ${report.zone}` : ''}</span>
          <span>·</span>
          <Clock size={12} />
          <span>{timeAgo(report.created_at)}</span>
          <span>·</span>
          <span>by {report.is_anonymous ? 'Anonymous' : report.reporter_name}</span>
        </div>

        <div className="flex flex-wrap gap-2 mt-3">
          {report.intent === 'service_request'
            ? <span className="badge bg-blue-100 text-blue-800">Service request</span>
            : <SeverityBadge severity={report.severity} />}
          <StatusBadge status={report.status} />
          <CategoryBadge category={report.category} />
          {report.service_group && <span className="badge bg-violet-100 text-violet-800">{report.service_group}</span>}
          {report.service_subcategory && <span className="badge bg-indigo-100 text-indigo-800">{report.service_subcategory}</span>}
          {report.prompt_version && <span className="badge bg-gray-100 text-gray-600">Prompt {report.prompt_version}</span>}
          {report.recurrence_count > 0 && (
            <span className="badge bg-purple-100 text-purple-800">
              <RotateCcw size={10} className="mr-1" />×{report.recurrence_count} recurring
            </span>
          )}
        </div>

        {/* Hype button */}
        <div className="flex items-center gap-4 mt-4 pt-3 border-t">
          <button
            onClick={toggleHype}
            type="button"
            aria-label={`${hyped ? 'Remove hype from' : 'Hype'} this report`}
            aria-pressed={Boolean(hyped)}
            disabled={hypeLoading || report.reporter_id === user?.id}
            className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold transition-all disabled:opacity-50 ${
              hyped ? 'bg-primary-light text-primary-dark hover:bg-blue-100' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Flame size={16} className={hyped ? 'fill-primary text-primary' : ''} />
            Hype · {hypeCount}
          </button>
          <span className="text-xs text-gray-400">
            Priority score: <strong className="text-gray-700">{Math.round(report.priority_score)}</strong>
          </span>
        </div>
      </PageCard>

      {/* Tabs */}
      <Tabs items={[
          { key: 'details', label: 'Details' },
          { key: 'timeline', label: 'Timeline' },
          { key: 'ai', label: 'AI Analysis' },
          { key: 'priority', label: 'Priority' },
        ]} value={activeTab} onChange={setActiveTab} />

      {/* Tab content */}
      {activeTab === 'details' && (
        <PageCard title="Report Details"><div className="space-y-4">
          {report.image_path && (
            <img
              src={`http://localhost:8000/${report.image_path}`}
              alt="hazard"
              className="w-full rounded-lg max-h-64 object-cover"
            />
          )}
          {report.description && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-1">Description</p>
              <p className="text-sm text-gray-600">{report.description}</p>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-gray-400">Department:</span> <span className="font-medium">{report.assigned_department || '—'}</span></div>
            <div><span className="text-gray-400">Hazard type:</span> <span className="font-medium">{report.hazard_type?.replace(/_/g, ' ') || '—'}</span></div>
            {report.sla_hours && <div><span className="text-gray-400">Response SLA:</span> <span className="font-medium">{report.sla_hours}h</span></div>}
          </div>

          {/* Before/after photos */}
          {report.verification && (
            <div>
              <p className="text-sm font-semibold text-gray-700 mb-2">Before / After Comparison</p>
              <div className="grid grid-cols-2 gap-2">
                {report.image_path && (
                  <div>
                    <p className="text-xs text-gray-400 mb-1">Before</p>
                    <img src={`http://localhost:8000/${report.image_path}`} alt="before" className="rounded-lg w-full h-28 object-cover" />
                  </div>
                )}
                <div>
                  <p className="text-xs text-gray-400 mb-1">After</p>
                  <img src={`http://localhost:8000/${report.verification.after_image_path}`} alt="after" className="rounded-lg w-full h-28 object-cover" />
                </div>
              </div>
              {report.verification.flagged_for_review && (
                <p className="text-xs text-amber-600 mt-1">⚠️ Flagged for admin review (low AI match confidence)</p>
              )}
            </div>
          )}

          {/* Reporter confirm/dispute buttons */}
          {report.status === 'pending_confirmation' && report.reporter_id === user?.id && (
            <div className="pt-2 border-t">
              <p className="text-sm font-medium text-gray-700 mb-3">Has the issue been fixed?</p>
              <div className="flex gap-3">
                <button
                  onClick={() => handleConfirm(true)}
                  disabled={confirmLoading}
                  className="flex-1 flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white py-2 rounded-lg text-sm font-semibold transition-colors"
                >
                  <CheckCircle size={16} /> Yes, it's fixed
                </button>
                <button
                  onClick={() => handleConfirm(false)}
                  disabled={confirmLoading}
                  className="flex-1 flex items-center justify-center gap-2 bg-red-100 hover:bg-red-200 text-red-700 py-2 rounded-lg text-sm font-semibold transition-colors"
                >
                  <XCircle size={16} /> No, still open
                </button>
              </div>
            </div>
          )}
        </div></PageCard>
      )}

      {activeTab === 'timeline' && (
        <PageCard title="Status Timeline"><div>
          {/* Status progress bar */}
          <div className="flex items-center mb-6">
            {STATUS_STEPS.map((s, i) => (
              <div key={s} className="flex items-center flex-1">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                  i <= stepIndex ? 'bg-primary text-white' : 'bg-gray-200 text-gray-600'
                }`}>
                  {i < stepIndex ? '✓' : i + 1}
                </div>
                {i < STATUS_STEPS.length - 1 && (
                  <div className={`flex-1 h-0.5 mx-1 ${i < stepIndex ? 'bg-primary' : 'bg-gray-200'}`} />
                )}
              </div>
            ))}
          </div>
          <div className="flex justify-between text-xs text-gray-400 mb-4">
            {STATUS_STEPS.map(s => <span key={s} className="text-center">{s.replace(/_/g, ' ')}</span>)}
          </div>

          {/* Status log */}
          <div className="space-y-3">
            {report.status_history?.map((log, i) => (
              <div key={log.id} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className="w-2 h-2 bg-primary rounded-full mt-1 flex-shrink-0" />
                  {i < report.status_history.length - 1 && <div className="w-0.5 flex-1 bg-gray-200 mt-1" />}
                </div>
                <div className="pb-4">
                  <p className="text-xs font-semibold text-gray-800">
                    {log.old_status ? `${log.old_status} → ` : ''}{log.new_status}
                  </p>
                  {log.note && <p className="text-xs text-gray-500 mt-0.5">{log.note}</p>}
                  <p className="text-xs text-gray-400 mt-0.5">{timeAgo(log.created_at)} {log.changer_name ? `· ${log.changer_name}` : ''}</p>
                </div>
              </div>
            ))}
          </div>
        </div></PageCard>
      )}

      {activeTab === 'ai' && (
        <PageCard title="AI Analysis"><div className="space-y-3">
          <h3 className="font-semibold text-sm text-gray-800">AI Transparency</h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-400">Hazard Type</p>
              <p className="font-semibold mt-0.5">{report.hazard_type?.replace(/_/g, ' ') || '—'}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-400">Confidence</p>
              <p className="font-semibold mt-0.5">{report.ai_confidence ? `${Math.round(report.ai_confidence * 100)}%` : '—'}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-400">Intent confidence</p>
              <p className="font-semibold mt-0.5">{report.intent_confidence != null ? `${Math.round(report.intent_confidence * 100)}%` : '—'}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-400">Group confidence</p>
              <p className="font-semibold mt-0.5">{report.group_confidence != null ? `${Math.round(report.group_confidence * 100)}%` : '—'}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-400">Subcategory confidence</p>
              <p className="font-semibold mt-0.5">{report.subcategory_confidence != null ? `${Math.round(report.subcategory_confidence * 100)}%` : '—'}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-400">Category</p>
              <p className="font-semibold mt-0.5">{report.category || '—'}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-400">Safety Critical</p>
              <p className="font-semibold mt-0.5">{report.is_safety_critical ? '🚨 Yes' : '✅ No'}</p>
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-400 mb-1">AI Reasoning</p>
            <p className="text-sm text-gray-700">{report.ai_reasoning || 'No AI reasoning available'}</p>
          </div>
        </div></PageCard>
      )}

      {activeTab === 'priority' && report.priority_breakdown && (
        <PageCard title="Priority Score Breakdown"><div className="space-y-3">
          <div className="flex items-center gap-2">
            <BarChart3 size={18} className="text-primary" />
            <h3 className="font-semibold text-sm text-gray-800">Priority Score Breakdown</h3>
            <span className="ml-auto text-2xl font-bold text-primary">{Math.round(report.priority_breakdown.final_score)}</span>
          </div>

          {[
            { label: 'Severity (40%)', value: report.priority_breakdown.severity_norm, weight: 0.40 },
            { label: 'Hype (25%)', value: report.priority_breakdown.hype_norm, weight: 0.25 },
            { label: 'Recurrence (20%)', value: report.priority_breakdown.recurrence_norm, weight: 0.20 },
            { label: 'Location Risk (15%)', value: report.priority_breakdown.location_criticality_norm, weight: 0.15 },
          ].map(({ label, value, weight }) => (
            <div key={label}>
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>{label}</span>
                <span>{Math.round(value * weight * 100)} pts</span>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div className="h-full bg-primary rounded-full" style={{ width: `${value * 100}%` }} />
              </div>
            </div>
          ))}

          {report.priority_breakdown.age_bonus > 0 && (
            <p className="text-xs text-gray-500">⏳ Age bonus: +{report.priority_breakdown.age_bonus.toFixed(1)} pts</p>
          )}
          {report.priority_breakdown.safety_critical_override && (
            <p className="text-xs text-red-600 font-semibold">🚨 Safety-critical override applied (score forced to ≥90)</p>
          )}
        </div></PageCard>
      )}
    </div>
  )
}
