import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'
import { Activity, LockKeyhole, Mail, UserRound } from 'lucide-react'

export default function LoginPage() {
  const [mode, setMode] = useState('login')
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'student', department: '' })
  const { login, register } = useAuth()
  const navigate = useNavigate()
  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      let user
      if (mode === 'login') user = await login(form.email, form.password)
      else user = await register(form)
      toast.success(`Welcome, ${user.name}!`)
      if (user.role === 'admin') navigate('/admin')
      else if (user.role === 'authority') navigate('/authority')
      else navigate('/')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Something went wrong')
    } finally { setLoading(false) }
  }

  const field = (label, icon, input) => <label className="block text-sm font-semibold text-slate-700">
    <span className="mb-1.5 block">{label}</span>
    <span className="relative block">{icon}<span className="sr-only">{label}</span>{input}</span>
  </label>

  return <main className="flex min-h-screen items-center justify-center bg-page px-4 py-8 sm:px-6">
    <div className="w-full max-w-5xl overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl">
      <header className="flex items-center gap-3 border-b border-slate-100 px-5 py-4 sm:px-8">
        <div className="grid h-11 w-11 place-items-center rounded-md bg-primary text-white"><Activity size={22} /></div>
        <div><p className="text-lg font-extrabold tracking-wide text-primary">S.O.S.</p><p className="text-xs font-medium text-slate-500">Spark On-Site Solutions · Campus Safety Portal</p></div>
        <span className="ml-auto hidden rounded border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-500 sm:block">College logo area</span>
      </header>

      <div className="grid md:grid-cols-2">
        <section className="flex flex-col justify-center bg-gradient-to-br from-blue-50 to-white px-6 py-8 sm:px-10 sm:py-12">
          <span className="mb-3 inline-flex w-fit items-center gap-2 rounded-full bg-primary-light px-3 py-1 text-xs font-bold text-primary"><Activity size={14} /> CAMPUS COMMUNITY</span>
          <h1 className="text-2xl font-extrabold leading-tight text-slate-900 sm:text-3xl">A safer campus starts with you.</h1>
          <p className="mt-4 max-w-md text-sm leading-6 text-slate-600">Report hazards and request on-site services in one place.</p>
          <p className="mt-2 max-w-md text-sm leading-6 text-slate-600">Track progress, support your community, and help campus teams respond sooner.</p>
          <p className="mt-2 max-w-md text-sm leading-6 text-slate-600">Sign in to see updates and manage your reports.</p>
        </section>

        <section className="p-5 sm:p-8">
          <div className="overflow-hidden rounded-md border border-slate-200 shadow-sm">
            <div className="bg-primary px-5 py-4 text-white"><h2 className="text-lg font-bold">{mode === 'login' ? 'Sign in' : 'Create your account'}</h2><p className="mt-1 text-xs text-blue-50">Access your campus safety portal</p></div>
            <div className="p-5 sm:p-6">
              <div className="mb-5 flex gap-5 border-b border-slate-200" role="tablist" aria-label="Account access">
                {['login', 'register'].map(m => <button key={m} type="button" role="tab" aria-selected={mode === m} onClick={() => setMode(m)} className={`-mb-px border-b-2 px-1 py-2 text-sm font-semibold capitalize transition-colors ${mode === m ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-800'}`}>{m === 'login' ? 'Sign in' : 'Register'}</button>)}
              </div>
              <form onSubmit={handleSubmit} className="space-y-4">
                {mode === 'register' && field('Full Name', <UserRound size={16} aria-hidden="true" className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />, <input className="input pl-10" value={form.name} onChange={set('name')} required placeholder="Your name" />)}
                {field('Email', <Mail size={16} aria-hidden="true" className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />, <input className="input pl-10" type="email" value={form.email} onChange={set('email')} required placeholder="you@university.edu" autoComplete="email" />)}
                {field('Password', <LockKeyhole size={16} aria-hidden="true" className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />, <input className="input pl-10" type="password" value={form.password} onChange={set('password')} required placeholder="Enter your password" minLength={6} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />)}
                {mode === 'register' && <>
                  <label className="block text-sm font-semibold text-slate-700">Role<select className="input mt-1.5" value={form.role} onChange={set('role')}><option value="student">Student / Staff</option><option value="authority">Authority</option><option value="admin">Admin</option></select></label>
                  {form.role === 'authority' && <label className="block text-sm font-semibold text-slate-700">Department<select className="input mt-1.5" value={form.department} onChange={set('department')}><option value="">Select department</option><option value="Electrical">Electrical</option><option value="Civil">Civil / Maintenance</option><option value="Security">Security</option><option value="Admin">Admin</option></select></label>}
                </>}
                <button type="submit" className="btn-primary w-full py-2.5" disabled={loading}>{loading ? 'Please wait...' : mode === 'login' ? 'Login' : 'Create Account'}</button>
              </form>
              <div className="mt-5 border-t border-slate-100 pt-4">
                <p className="mb-2 text-xs font-semibold text-slate-600">Quick demo login</p>
                <div className="flex flex-wrap gap-2">{[
                  { label: 'Student', email: 'arjun@student.edu', password: 'student123' },
                  { label: 'Authority', email: 'raj.elec@university.edu', password: 'auth123' },
                  { label: 'Admin', email: 'admin@university.edu', password: 'admin123' },
                ].map(d => <button type="button" key={d.label} className="rounded-full border border-primary/50 bg-white px-3 py-1.5 text-xs font-semibold text-primary transition-colors hover:bg-primary-light" onClick={() => { setForm(f => ({ ...f, email: d.email, password: d.password })); setMode('login') }}>{d.label}</button>)}</div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  </main>
}
