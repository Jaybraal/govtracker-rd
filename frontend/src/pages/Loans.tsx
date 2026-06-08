import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Banknote } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import { loansApi, Loan, PagedResponse } from '../services/api'
import { useApi } from '../hooks/useApi'

const fmt = (n: number, currency = 'USD') => {
  if (!n) return '—'
  const s = n >= 1e9 ? `${(n/1e9).toFixed(2)}B` : n >= 1e6 ? `${(n/1e6).toFixed(0)}M` : n.toLocaleString()
  return `${currency} $${s}`
}

export default function Loans() {
  const [page, setPage] = useState(1)
  const [acreedor, setAcreedor] = useState('')

  const { data, loading } = useApi<PagedResponse<Loan>>(
    () => loansApi.list({ page, size: 50, ...(acreedor && { acreedor }) }),
    [page, acreedor],
  )
  const { data: stats } = useApi(() => loansApi.stats(), [])

  const STATUS_BADGE: Record<string, string> = {
    activo: 'badge-green',
    en_desembolso: 'badge-blue',
    completado: 'badge-purple',
    cancelado: 'badge-red',
  }

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title="Préstamos Internacionales"
        subtitle="Deuda pública externa de República Dominicana"
      />

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <StatCard label="Total Aprobado" value={fmt(stats.total_aprobado_usd)} icon={<Banknote size={16} />} color="purple" />
          <StatCard label="Total Desembolsado" value={fmt(stats.total_desembolsado_usd)} color="blue" />
          <StatCard label="% Desembolsado" value={`${(stats.porcentaje_desembolsado || 0).toFixed(1)}%`} color="green" />
        </div>
      )}

      {/* Ranking por acreedor */}
      {stats?.por_acreedor && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-3">Deuda por Acreedor</h3>
          <div className="space-y-2">
            {stats.por_acreedor.map((r: any) => {
              const pct = stats.total_aprobado_usd > 0 ? (r.monto / stats.total_aprobado_usd) * 100 : 0
              return (
                <div key={r.acreedor} className="flex items-center gap-3">
                  <span className="text-xs text-gray-400 w-60 truncate">{r.acreedor}</span>
                  <div className="flex-1 bg-gray-800 rounded-full h-2">
                    <div className="bg-gov-600 h-2 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-xs text-white font-mono w-24 text-right">{fmt(r.monto)}</span>
                  <span className="text-xs text-gray-500 w-10 text-right">{r.cantidad}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Filtro */}
      <div className="card flex gap-3">
        <input className="input flex-1" placeholder="Filtrar por acreedor..." value={acreedor} onChange={e => { setAcreedor(e.target.value); setPage(1) }} />
      </div>

      {/* Tabla */}
      <div className="card p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-left">
              <th className="px-4 py-3 text-gray-400 font-medium">Acreedor</th>
              <th className="px-4 py-3 text-gray-400 font-medium">Descripción</th>
              <th className="px-4 py-3 text-gray-400 font-medium text-right">Monto Aprobado</th>
              <th className="px-4 py-3 text-gray-400 font-medium text-right">Desembolsado</th>
              <th className="px-4 py-3 text-gray-400 font-medium">Estado</th>
              <th className="px-4 py-3 text-gray-400 font-medium">Vencimiento</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">Cargando...</td></tr>
            ) : data?.items.map(l => (
              <tr key={l.id} className="table-row">
                <td className="px-4 py-3">
                  <p className="text-white font-medium text-xs">{l.acreedor}</p>
                  <p className="text-xs text-gray-500">{l.tipo_acreedor}</p>
                </td>
                <td className="px-4 py-3 text-xs text-gray-400 max-w-64 truncate">{l.descripcion}</td>
                <td className="px-4 py-3 text-right font-mono text-white">{fmt(l.monto_aprobado, l.moneda)}</td>
                <td className="px-4 py-3 text-right font-mono text-gray-400">
                  {fmt(l.monto_desembolsado, l.moneda)}
                  {l.monto_aprobado > 0 && (
                    <span className="text-xs text-gray-600 ml-1">
                      ({((l.monto_desembolsado / l.monto_aprobado) * 100).toFixed(0)}%)
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className={STATUS_BADGE[l.estado] || 'badge-blue'}>{l.estado}</span>
                </td>
                <td className="px-4 py-3 text-xs text-gray-500">
                  {l.fecha_vencimiento ? new Date(l.fecha_vencimiento).toLocaleDateString('es-DO') : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
