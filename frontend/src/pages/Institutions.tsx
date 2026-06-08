import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, Download } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { institutionsApi, exportApi, Institution } from '../services/api'
import { useApi } from '../hooks/useApi'

const fmt = (n: number) => {
  if (n >= 1e9) return `RD$${(n/1e9).toFixed(2)}B`
  if (n >= 1e6) return `RD$${(n/1e6).toFixed(0)}M`
  return `RD$${n?.toLocaleString()}`
}

export default function Institutions() {
  const [search, setSearch] = useState('')
  const { data, loading } = useApi<Institution[]>(() => institutionsApi.list({ search }), [search])

  const filtered = (data || []).filter(i =>
    !search || i.nombre.toLowerCase().includes(search.toLowerCase()) || (i.siglas || '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title="Instituciones Públicas"
        subtitle={`${filtered.length} instituciones`}
      />

      <div className="card flex gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input className="input pl-8" placeholder="Buscar institución..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <div className="col-span-3 text-center text-gray-500 py-8">Cargando...</div>
        ) : filtered.map(inst => {
          const pct = inst.presupuesto_anual > 0
            ? Math.min(100, (inst.total_monto_contratos / inst.presupuesto_anual) * 100)
            : 0
          return (
            <Link key={inst.id} to={`/institutions/${inst.id}`} className="card hover:border-gov-700 transition-colors block">
              <div className="flex items-start justify-between mb-2">
                <div className="w-10 h-10 bg-gov-700/30 rounded-lg flex items-center justify-center text-gov-400 font-bold text-sm">
                  {inst.siglas?.slice(0, 3) || inst.nombre.slice(0, 3)}
                </div>
                <span className="badge-blue text-xs">{inst.tipo?.replace(/_/g, ' ')}</span>
              </div>
              <h3 className="text-white font-medium text-sm mt-2 line-clamp-2">{inst.nombre}</h3>
              <p className="text-xs text-gray-500 mt-0.5">{inst.siglas}</p>
              <div className="mt-3 space-y-1">
                <div className="flex justify-between text-xs text-gray-400">
                  <span>Contratado</span>
                  <span className="text-white font-mono">{fmt(inst.total_monto_contratos)}</span>
                </div>
                <div className="flex justify-between text-xs text-gray-400">
                  <span>Contratos</span>
                  <span className="text-white">{inst.total_contratos.toLocaleString()}</span>
                </div>
              </div>
              {pct > 0 && (
                <div className="mt-2">
                  <div className="bg-gray-800 rounded-full h-1.5">
                    <div className="bg-gov-600 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                  <p className="text-xs text-gray-600 mt-0.5">{pct.toFixed(0)}% del presupuesto</p>
                </div>
              )}
            </Link>
          )
        })}
      </div>
    </div>
  )
}
