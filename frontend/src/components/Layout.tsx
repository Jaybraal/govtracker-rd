import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, FileText, Building2, Landmark, Banknote,
  Network, Bell, Bot, Database, Menu, X, Shield, Eye, Flag, Gavel, ShieldAlert, Receipt, HeartPulse, Scale, Wallet,
} from 'lucide-react'
import clsx from 'clsx'

const NAV = [
  { to: '/',             icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/contracts',    icon: FileText,        label: 'Contratos' },
  { to: '/companies',    icon: Building2,       label: 'Empresas' },
  { to: '/institutions', icon: Landmark,        label: 'Instituciones' },
  { to: '/loans',        icon: Banknote,        label: 'Préstamos' },
  { to: '/gasto-ejecutado', icon: Wallet,        label: 'Gasto Ejecutado' },
  { to: '/graph',        icon: Network,         label: 'Red de Relaciones' },
  { to: '/banks',        icon: Landmark,         label: 'Bancos' },
  { to: '/parties',      icon: Flag,             label: 'Partidos Políticos' },
  { to: '/legislators',  icon: Gavel,            label: 'Congreso Nacional' },
  { to: '/nominas',      icon: Receipt,          label: 'Nóminas del Estado' },
  { to: '/seguros',      icon: HeartPulse,       label: 'Seguros del Estado' },
  { to: '/pgr',          icon: Scale,            label: 'Procuraduría (PGR)' },
  { to: '/intelligence', icon: Eye,             label: 'Inteligencia', highlight: true },
  { to: '/alerts',       icon: Bell,            label: 'Alertas' },
  { to: '/inhabilitados', icon: ShieldAlert,    label: 'Proveedores Inhabilitados' },
  { to: '/ai',           icon: Bot,             label: 'IA Analista' },
  { to: '/etl',          icon: Database,        label: 'Datos / ETL' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      {/* Sidebar */}
      <aside className={clsx(
        'flex flex-col border-r border-gray-800 bg-gray-900 transition-all duration-300 flex-shrink-0',
        sidebarOpen ? 'w-60' : 'w-16',
      )}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-gray-800">
          <div className="w-8 h-8 bg-gov-600 rounded-lg flex items-center justify-center flex-shrink-0">
            <Shield size={16} className="text-white" />
          </div>
          {sidebarOpen && (
            <div>
              <p className="text-sm font-bold text-white leading-tight">GovTracker</p>
              <p className="text-xs text-gov-400 leading-tight">República Dominicana</p>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(v => !v)}
            className="ml-auto text-gray-500 hover:text-white transition-colors"
          >
            {sidebarOpen ? <X size={16} /> : <Menu size={16} />}
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 overflow-y-auto">
          {NAV.map(({ to, icon: Icon, label, highlight }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => clsx(
                'flex items-center gap-3 px-4 py-2.5 mx-2 rounded-lg text-sm transition-all',
                isActive
                  ? 'bg-gov-700/40 text-gov-300 font-medium'
                  : highlight
                    ? 'text-red-400 hover:text-red-300 hover:bg-red-900/20'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800',
              )}
            >
              <Icon size={18} className="flex-shrink-0" />
              {sidebarOpen && (
                <span className="flex items-center gap-2">
                  {label}
                  {highlight && (
                    <span className="text-xs bg-red-900/60 text-red-300 px-1.5 py-0.5 rounded font-medium">
                      NUEVO
                    </span>
                  )}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        {sidebarOpen && (
          <div className="px-4 py-3 border-t border-gray-800">
            <p className="text-xs text-gray-600">
              Datos: DGCP · Hacienda · Crédito Público
            </p>
          </div>
        )}
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}
