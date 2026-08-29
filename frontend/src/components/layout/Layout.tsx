import { Outlet } from 'react-router-dom'
import { SiteHeader } from './SiteHeader'

export function Layout() {
  return (
    <div className="min-h-screen bg-background font-sans text-foreground">
      <SiteHeader />
      <Outlet />
    </div>
  )
}
