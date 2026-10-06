import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Activity, BarChart3, ClipboardList, FilePlus2, LayoutDashboard, Shield, X } from 'lucide-react'

const baseItems = [
  { label: 'Dashboard', to: '/', icon: LayoutDashboard },
  { label: 'New Report', to: '/report/new', icon: FilePlus2 },
  { label: 'My Reports', to: '/my-reports', icon: ClipboardList },
]

export default function Sidebar({ user, open, collapsed, onClose, onCollapse }) {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])
  useEffect(() => {
    const closeOnEscape = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  const items = [...baseItems]
  if (user?.role === 'authority' || user?.role === 'admin') items.push({ label: 'Authority Board', to: '/authority', icon: Shield })
  if (user?.role === 'admin') items.push({ label: 'Analytics', to: '/admin', icon: BarChart3 })

  return <>
    {open && <button type="button" aria-label="Close navigation menu" onClick={onClose} className="fixed inset-0 z-40 bg-slate-950/40 lg:hidden" />}
    <aside className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-slate-200 bg-sidebar shadow-lg transition-all duration-200 lg:sticky lg:top-0 lg:z-20 lg:h-screen lg:translate-x-0 lg:shadow-none ${collapsed ? 'lg:w-[76px]' : 'lg:w-60'} ${open ? 'translate-x-0' : '-translate-x-full'}`} aria-label="Main navigation">
      <div className="flex h-16 items-center justify-between border-b border-slate-200 px-4">
        <div className={`flex items-center gap-3 overflow-hidden ${collapsed ? 'lg:justify-center' : ''}`}>
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-primary text-white"><Activity size={20} /></div>
          <div className={collapsed ? 'lg:hidden' : ''}><p className="font-extrabold tracking-wide text-primary">S.O.S.</p><p className="whitespace-nowrap text-[10px] font-semibold text-slate-500">Campus Safety Portal</p></div>
        </div>
        <button type="button" aria-label="Close navigation menu" onClick={onClose} className="rounded p-2 text-slate-500 hover:bg-white lg:hidden"><X size={18} /></button>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-5">
        {items.map(({ label, to, icon: Icon }) => <NavLink key={to} to={to} end={to === '/'} onClick={onClose} title={collapsed ? label : undefined} className={({ isActive }) => `flex min-h-11 items-center gap-3 rounded-md px-3 text-sm transition-colors focus-visible:ring-primary ${isActive ? 'bg-white font-bold text-primary shadow-sm' : 'font-medium text-slate-700 hover:bg-white/80 hover:text-primary'} ${collapsed ? 'lg:justify-center lg:px-2' : ''}`}>
          <Icon size={19} className="shrink-0" /><span className={collapsed ? 'lg:hidden' : ''}>{label}</span>
        </NavLink>)}
      </nav>
      <div className={`border-t border-slate-200 px-4 py-4 ${collapsed ? 'lg:px-2' : ''}`}>
        <div className={`mb-3 flex items-center gap-3 ${collapsed ? 'lg:justify-center' : ''}`}>
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-primary/10 text-sm font-bold text-primary">{user?.name?.slice(0, 1)?.toUpperCase() || 'U'}</div>
          <div className={`min-w-0 ${collapsed ? 'lg:hidden' : ''}`}><p className="truncate text-sm font-bold text-slate-800">{user?.name}</p><p className="capitalize text-xs text-slate-500">{user?.role}</p></div>
        </div>
        <div className={`text-xs leading-5 text-slate-600 ${collapsed ? 'lg:hidden' : ''}`}><p>{now.toLocaleDateString(undefined, { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })}</p><p className="font-semibold tabular-nums">{now.toLocaleTimeString()}</p></div>
        <button type="button" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} onClick={onCollapse} className="mt-3 hidden w-full rounded px-2 py-1 text-left text-xs font-semibold text-slate-500 hover:bg-white hover:text-primary lg:block">{collapsed ? '›' : '‹  Collapse menu'}</button>
      </div>
    </aside>
  </>
}
