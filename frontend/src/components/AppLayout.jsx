import { useCallback, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

export default function AppLayout({ children }) {
  const { user } = useAuth()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const closeDrawer = useCallback(() => setDrawerOpen(false), [])

  return <div className="flex min-h-screen bg-page">
    <Sidebar user={user} open={drawerOpen} collapsed={collapsed} onClose={closeDrawer} onCollapse={() => setCollapsed(v => !v)} />
    <div className="min-w-0 flex-1">
      <Topbar onMenuClick={() => {
        if (window.matchMedia('(min-width: 1024px)').matches) setCollapsed(v => !v)
        else setDrawerOpen(true)
      }} />
      <main className="mx-auto w-full max-w-[1600px] px-3 py-5 sm:px-5 sm:py-6 lg:px-8">{children}</main>
    </div>
  </div>
}
