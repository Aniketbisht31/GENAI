import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Activity, Bell, LogOut, Menu } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { notificationsAPI } from '../api/client'

export default function Topbar({ onMenuClick }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [notifs, setNotifs] = useState([])
  const [showNotifs, setShowNotifs] = useState(false)
  const notifRef = useRef(null)

  useEffect(() => {
    if (!user) return undefined
    const load = () => notificationsAPI.list().then(r => setNotifs(r.data)).catch(() => {})
    load()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [user])

  useEffect(() => {
    const closeOutside = e => { if (!notifRef.current?.contains(e.target)) setShowNotifs(false) }
    document.addEventListener('mousedown', closeOutside)
    return () => document.removeEventListener('mousedown', closeOutside)
  }, [])

  const unread = notifs.filter(n => !n.read).length
  const markAllRead = () => notificationsAPI.markAllRead().then(() => setNotifs(prev => prev.map(n => ({ ...n, read: true })))).catch(() => {})
  const handleLogout = () => { logout(); navigate('/login') }
  const campus = 'Faculty of Engineering and Technology, Kattankulathur'

  return <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-slate-200 bg-white px-3 shadow-sm sm:px-5 lg:px-7">
    <div className="flex min-w-0 items-center gap-3">
      <button type="button" aria-label="Toggle navigation menu" onClick={onMenuClick} className="rounded-md p-2 text-slate-600 hover:bg-slate-100 hover:text-primary"><Menu size={21} /></button>
      <div className="hidden items-center gap-2 sm:flex"><Activity size={20} className="text-primary" /><div className="leading-tight"><p className="text-[10px] font-semibold text-slate-500">Campus Safety Portal</p><p className="text-sm font-bold text-primary">S.O.S.</p></div></div>
      <p className="min-w-0 max-w-[46vw] truncate text-[11px] font-bold text-primary sm:ml-2 sm:max-w-none sm:border-l sm:border-slate-200 sm:pl-4 sm:text-sm">{campus}</p>
    </div>
    <div className="flex shrink-0 items-center gap-1 sm:gap-3">
      <div className="relative" ref={notifRef}>
        <button type="button" aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`} aria-expanded={showNotifs} onClick={() => setShowNotifs(v => !v)} className="relative rounded-md p-2 text-slate-600 hover:bg-blue-50 hover:text-primary">
          <Bell size={19} />{unread > 0 && <span className="absolute right-0.5 top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-primary px-1 text-[9px] font-bold text-white">{unread > 9 ? '9+' : unread}</span>}
        </button>
        {showNotifs && <div className="absolute right-0 top-12 z-50 w-[min(21rem,calc(100vw-1.5rem))] overflow-hidden rounded-md border border-slate-200 bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3"><span className="text-sm font-bold">Notifications</span>{unread > 0 && <button type="button" onClick={markAllRead} className="text-xs font-semibold text-primary hover:underline">Mark all read</button>}</div>
          <div className="max-h-80 divide-y divide-slate-100 overflow-y-auto">{notifs.length === 0 ? <p className="px-4 py-8 text-center text-sm text-slate-500">No notifications</p> : notifs.slice(0, 15).map(n => <button type="button" key={n.id} onClick={() => { if (n.report_id) navigate(`/reports/${n.report_id}`); setShowNotifs(false) }} className={`block w-full px-4 py-3 text-left text-xs hover:bg-blue-50 ${!n.read ? 'bg-primary-light' : ''}`}><span className={`block ${!n.read ? 'font-semibold text-slate-900' : 'text-slate-700'}`}>{n.message}</span><span className="mt-1 block text-slate-500">{new Date(n.sent_at).toLocaleString()}</span></button>)}</div>
        </div>}
      </div>
      <button type="button" onClick={handleLogout} className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 px-2.5 py-2 text-xs font-semibold text-slate-700 hover:border-primary hover:bg-blue-50 hover:text-primary sm:px-3 sm:text-sm"><LogOut size={16} /><span>Logout</span></button>
    </div>
  </header>
}
