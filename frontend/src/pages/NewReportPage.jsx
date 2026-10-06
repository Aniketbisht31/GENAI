import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { reportsAPI, locationsAPI } from '../api/client'
import { Spinner, SeverityBadge } from '../components/UI'
import toast from 'react-hot-toast'
import { Camera, MapPin, Eye, CheckCircle, AlertTriangle, Flame } from 'lucide-react'
import PageCard from '../components/PageCard'

const STEPS = ['Photo & Description', 'Location', 'Review & Submit']

export default function NewReportPage() {
  const navigate = useNavigate()
  const fileRef = useRef(null)
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [locations, setLocations] = useState([])
  const [form, setForm] = useState({
    title: '', description: '', image: null, imagePreview: null,
    building: '', zone: '', lat: '', lng: '', is_anonymous: false,
  })
  const [aiResult, setAiResult] = useState(null)
  const [dupCheck, setDupCheck] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [confirmingCandidate, setConfirmingCandidate] = useState(null)

  useEffect(() => {
    locationsAPI.list().then(r => setLocations(r.data)).catch(() => {})
  }, [])

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  const handleImage = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setForm(f => ({ ...f, image: file, imagePreview: URL.createObjectURL(file) }))
  }

  const handleGPS = () => {
    navigator.geolocation?.getCurrentPosition(
      pos => setForm(f => ({ ...f, lat: pos.coords.latitude.toFixed(6), lng: pos.coords.longitude.toFixed(6) })),
      () => toast.error('GPS unavailable')
    )
  }

  const buildings = [...new Set(locations.map(l => l.building))]
  const zonesForBuilding = locations.filter(l => l.building === form.building).map(l => l.zone).filter(Boolean)

  const nextStep = () => {
    if (step === 0 && !form.description && !form.image) {
      toast.error('Please add a photo or description')
      return
    }
    if (step === 1 && !form.building) {
      toast.error('Please select a building')
      return
    }
    if (step === 1) {
      // Pre-analyze before review step
      analyzePreview()
    }
    setStep(s => s + 1)
  }

  const analyzePreview = async () => {
    setAnalyzing(true)
    try {
      const fd = new FormData()
      fd.append('title', form.title || form.description?.slice(0, 50) || 'Hazard report')
      fd.append('description', form.description || '')
      fd.append('building', form.building)
      if (form.zone) fd.append('zone', form.zone)
      if (form.lat) fd.append('lat', form.lat)
      if (form.lng) fd.append('lng', form.lng)
      fd.append('is_anonymous', form.is_anonymous)
      if (form.image) fd.append('image', form.image)

      const r = await reportsAPI.create(fd)
      setAiResult(r.data.ai_result)
      setDupCheck(r.data.duplicate_check)
      // Store the created report id for navigation
      setForm(f => ({ ...f, _createdId: r.data.report.id }))
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Analysis failed')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (aiResult?.candidates?.length) {
      toast.error('Please confirm the right subcategory first')
      return
    }
    if (form._createdId) {
      toast.success('Report submitted successfully!')
      navigate(`/reports/${form._createdId}`)
    }
  }

  const chooseCandidate = async (candidate) => {
    setConfirmingCandidate(candidate.id)
    try {
      await reportsAPI.confirmClassification(form._createdId, candidate.id)
      setAiResult(result => ({
        ...result,
        catalog_id: candidate.id,
        service_group: candidate.group,
        service_subcategory: candidate.subcategory,
        intent: candidate.intent,
        candidates: [],
      }))
      toast.success('Classification confirmed')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not confirm classification')
    } finally {
      setConfirmingCandidate(null)
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageCard title="Report a Campus Issue">

      {/* Stepper */}
      <div className="flex items-center mb-8">
        {STEPS.map((s, i) => (
          <div key={i} className="flex items-center">
            <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold transition-all ${
              i < step ? 'bg-green-600 text-white' : i === step ? 'bg-primary text-white' : 'bg-gray-200 text-gray-600'
            }`}>
              {i < step ? <CheckCircle size={16} /> : i + 1}
            </div>
            <span className={`ml-2 text-xs font-medium hidden sm:block ${i === step ? 'text-primary' : 'text-gray-500'}`}>
              {s}
            </span>
            {i < STEPS.length - 1 && <div className={`flex-1 h-px mx-3 ${i < step ? 'bg-green-500' : 'bg-gray-200'}`} style={{ minWidth: 20 }} />}
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit}>
        {/* Step 1: Photo & Description */}
        {step === 0 && (
          <div className="space-y-4">
            {/* Image upload */}
            <div
              role="button"
              tabIndex={0}
              aria-label={form.imagePreview ? 'Change report photo' : 'Add report photo'}
              onClick={() => fileRef.current?.click()}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileRef.current?.click() } }}
              className={`relative border-2 border-dashed rounded-xl cursor-pointer transition-all h-40 flex items-center justify-center ${
                form.imagePreview ? 'border-primary' : 'border-gray-300 hover:border-primary'
              }`}
            >
              {form.imagePreview ? (
                <img src={form.imagePreview} alt="preview" className="w-full h-full object-cover rounded-xl" />
              ) : (
                <div className="text-center text-gray-400">
                  <Camera size={32} className="mx-auto mb-2" />
                  <p className="text-sm font-medium">Tap to upload or take photo</p>
                  <p className="text-xs mt-0.5">JPEG, PNG, WebP</p>
                </div>
              )}
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={handleImage}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description *</label>
              <textarea
                className="input resize-none"
                rows={4}
                value={form.description}
                onChange={set('description')}
                placeholder="Describe the hazard clearly — what you saw, where exactly, how dangerous it looks..."
              />
            </div>

            <div className="flex items-center gap-2">
              <input type="checkbox" id="anon" checked={form.is_anonymous} onChange={set('is_anonymous')} className="rounded" />
              <label htmlFor="anon" className="text-sm text-gray-600">Report anonymously</label>
            </div>
          </div>
        )}

        {/* Step 2: Location */}
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Building *</label>
              <select className="input" value={form.building} onChange={set('building')} required>
                <option value="">Select building</option>
                {buildings.map(b => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>

            {zonesForBuilding.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Zone / Area</label>
                <select className="input" value={form.zone} onChange={set('zone')}>
                  <option value="">Select zone (optional)</option>
                  {zonesForBuilding.map(z => <option key={z} value={z}>{z}</option>)}
                </select>
              </div>
            )}

            <div>
              <button type="button" onClick={handleGPS} className="btn-secondary text-sm flex items-center gap-2">
                <MapPin size={14} />
                Use my GPS location
              </button>
              {form.lat && (
                <p className="text-xs text-green-600 mt-1">📍 GPS: {form.lat}, {form.lng}</p>
              )}
            </div>
          </div>
        )}

        {/* Step 3: Review */}
        {step === 2 && (
          <div className="space-y-4">
            {analyzing ? (
              <div className="text-center py-8">
                <Spinner size="lg" />
                <p className="text-sm text-gray-500 mt-3">AI is analyzing your report...</p>
              </div>
            ) : aiResult ? (
              <>
                {/* AI Result panel */}
                {aiResult.is_campus_related !== false ? (
                  <div className="card border border-primary/20 bg-primary-light">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle size={16} className="text-primary" />
                      <span className="font-semibold text-sm text-primary-dark">AI Analysis</span>
                      <span className="ml-auto text-xs text-gray-500">{Math.round((aiResult.confidence || 0) * 100)}% confident</span>
                    </div>
                    <div className="flex flex-wrap gap-2 mb-2">
                      {aiResult.intent === 'service_request'
                        ? <span className="badge bg-blue-100 text-blue-800">Service request</span>
                        : <SeverityBadge severity={aiResult.severity} />}
                      <span className="badge bg-yellow-100 text-yellow-800">{aiResult.hazard_type?.replace(/_/g, ' ')}</span>
                      {aiResult.is_safety_critical && (
                        <span className="badge bg-red-600 text-white animate-pulse">🚨 CRITICAL</span>
                      )}
                    </div>
                    {aiResult.service_group && (
                      <p className="text-sm font-medium text-gray-800 mb-1">
                        {aiResult.service_group} <span className="text-gray-400">›</span> {aiResult.service_subcategory}
                      </p>
                    )}
                    <div className="flex flex-wrap gap-x-3 text-[11px] text-gray-500 mb-2">
                      <span>Intent {Math.round((aiResult.intent_confidence || 0) * 100)}%</span>
                      <span>Group {Math.round((aiResult.group_confidence || 0) * 100)}%</span>
                      <span>Subcategory {Math.round((aiResult.subcategory_confidence || 0) * 100)}%</span>
                      {aiResult.prompt_version && <span>Prompt {aiResult.prompt_version}</span>}
                    </div>
                    <p className="text-xs text-gray-700">{aiResult.reasoning}</p>
                  </div>
                ) : (
                  <div className="card border border-amber-200 bg-amber-50">
                    <p className="text-amber-800 text-sm font-medium">⚠️ This doesn't appear to be a campus hazard. Please upload a relevant photo or add more details.</p>
                  </div>
                )}

                {aiResult.candidates?.length > 0 && (
                  <div className="card border border-blue-200 bg-blue-50">
                    <p className="text-sm font-semibold text-blue-900 mb-2">Confirm the right subcategory</p>
                    <div className="space-y-2">
                      {aiResult.candidates.map(candidate => (
                        <button
                          key={candidate.id}
                          type="button"
                          onClick={() => chooseCandidate(candidate)}
                          disabled={Boolean(confirmingCandidate)}
                          className="w-full text-left rounded-lg border border-blue-100 bg-white p-2.5 hover:border-blue-400 disabled:opacity-60"
                        >
                          <span className="block text-sm font-medium text-gray-800">{candidate.group} › {candidate.subcategory}</span>
                          <span className="text-xs text-gray-500">Routed to {candidate.owner_department}</span>
                          {confirmingCandidate === candidate.id && <span className="ml-2 text-xs text-blue-600">Saving…</span>}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Duplicate suggestions */}
                {dupCheck?.status === 'POSSIBLE_DUPLICATE' && dupCheck.suggestions?.length > 0 && (
                  <div className="card border border-amber-200 bg-amber-50">
                    <p className="text-amber-800 text-sm font-semibold mb-2">Similar issues already reported:</p>
                    {dupCheck.suggestions.map(s => (
                      <div key={s.id} className="flex items-center justify-between py-1.5 border-t border-amber-100">
                        <span className="text-xs text-gray-700">{s.title} — {s.building}</span>
                        <button
                          type="button"
                          onClick={() => navigate(`/reports/${s.id}`)}
                          className="flex items-center gap-1 text-xs text-amber-700 font-semibold hover:underline"
                        >
                          <Flame size={11} />
                          Hype instead
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {dupCheck?.status === 'DUPLICATE' && (
                  <div className="card border border-green-200 bg-green-50">
                    <p className="text-green-800 text-sm">✅ {dupCheck.message}</p>
                  </div>
                )}

                {dupCheck?.status === 'RECURRING' && (
                  <div className="card border border-purple-200 bg-purple-50">
                    <p className="text-purple-800 text-sm">🔁 {dupCheck.message}</p>
                  </div>
                )}

                <div className="pt-2">
                  <p className="text-sm text-gray-600">
                    Reporting at <strong>{form.building}</strong>{form.zone ? ` · ${form.zone}` : ''}
                    {form.is_anonymous ? ' (anonymously)' : ''}
                  </p>
                </div>
              </>
            ) : null}
          </div>
        )}

        {/* Navigation buttons */}
        <div className="flex gap-3 mt-6">
          {step > 0 && (
            <button
              type="button"
              onClick={() => setStep(s => s - 1)}
              className="btn-secondary flex-1"
              disabled={analyzing}
            >
              Back
            </button>
          )}
          {step < 2 ? (
            <button
              type="button"
              onClick={nextStep}
              className="btn-primary flex-1"
            >
              {step === 1 ? 'Analyze & Review' : 'Next'}
            </button>
          ) : (
            <button
              type="submit"
              className="btn-primary flex-1"
              disabled={analyzing || !form._createdId}
            >
              {analyzing ? <Spinner size="sm" /> : form._createdId ? 'View Report →' : 'Submitting...'}
            </button>
          )}
        </div>
      </form>
      </PageCard>
    </div>
  )
}
