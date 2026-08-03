import { Outlet } from 'react-router-dom'
import { TopBar } from '@/components/layout/top-bar'
import { DockNav } from '@/components/layout/dock-nav'

export function AppShell() {
  return (
    <div className="grid h-screen w-full grid-cols-[56px_minmax(0,1fr)] grid-rows-[46px_1fr] overflow-hidden bg-bg text-fg">
      <div className="col-span-2">
        <TopBar />
      </div>
      <DockNav />
      <main className="min-w-0 overflow-y-auto overflow-x-hidden px-8 py-7">
        <div className="mx-auto min-w-0 max-w-[1320px]">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
