import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { loansApi } from '../services/api'
import { useApi } from '../hooks/useApi'

const fmt = (n: number, currency = 'USD') => {
  if (!n) return '—'
  const s = n >= 1e9 ? `${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n.toLocaleString()
  return `${currency} $${s}`
}

const STATUS_BADGE: Record<string, string> = {
  activo: 'badge-green',
  en_desembolso: 'badge-blue',
  completado: 'badge-purple',
  cancelado: 'badge-red',
}

export default function LoanDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: l, loading } = useApi(() => loansApi.get(Number(id)), [id])

  if (loading) return <div className="p-6 text-gray-500">Cargando...</div>
  if (!l) return <div className="p-6 text-gray-500">Préstamo no encontrado</div>

  const pct = l.monto_aprobado > 0 ? (l.monto_desembolsado / l.monto_aprobado) * 100 : 0

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title={l.codigo || `Préstamo #${l.id}`}
        subtitle={l.acreedor}
        actions={
          <Link to="/loans" className="btn-ghost flex items-center gap-1.5"><ArrowLeft size={14} /> Volver</Link>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          ['Monto Aprobado', fmt(l.monto_aprobado, l.moneda)],
          ['Desembolsado', `${fmt(l.monto_desembolsado, l.moneda)} (${pct.toFixed(0)}%)`],
          ['Tasa de Interés', l.tasa_interes != null ? `${l.tasa_interes}%` : '—'],
          ['Plazo', l.plazo_anos != null ? `${l.plazo_anos} años` : '—'],
        ].map(([label, value]) => (
          <div key={label} className="card text-center">
            <p className="text-xs text-gray-500 mb-1">{label}</p>
            <p className="text-xl font-bold text-white">{value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-3">Información</h3>
          <dl className="space-y-2 text-sm">
            {[
              ['Tipo de Acreedor', l.tipo_acreedor],
              ['Objeto', l.objeto],
              ['Descripción', l.descripcion],
              ['Resolución del Congreso', (l as any).resolucion_congreso],
              ['Fuente', (l as any).fuente],
            ].filter(([_, v]) => v).map(([k, v]) => (
              <div key={k as string} className="flex justify-between gap-3">
                <dt className="text-gray-500 shrink-0">{k as string}</dt>
                <dd className="text-white text-right">{v as string}</dd>
              </div>
            ))}
            <div className="flex justify-between">
              <dt className="text-gray-500">Estado</dt>
              <dd><span className={STATUS_BADGE[l.estado] || 'badge-blue'}>{l.estado}</span></dd>
            </div>
            {l.fecha_aprobacion && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Aprobación</dt>
                <dd className="text-white">{new Date(l.fecha_aprobacion).toLocaleDateString('es-DO')}</dd>
              </div>
            )}
            {l.fecha_vencimiento && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Vencimiento</dt>
                <dd className="text-white">{new Date(l.fecha_vencimiento).toLocaleDateString('es-DO')}</dd>
              </div>
            )}
            {(l as any).url_fuente && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Enlace</dt>
                <dd><a href={(l as any).url_fuente} target="_blank" rel="noopener noreferrer" className="text-gov-400 hover:text-gov-300 text-xs">Ver fuente original →</a></dd>
              </div>
            )}
          </dl>
        </div>

        {(l as any).instituciones?.length > 0 && (
          <div className="card">
            <h3 className="text-sm font-semibold text-white mb-3">Instituciones Ejecutoras</h3>
            <div className="space-y-2">
              {(l as any).instituciones.map((i: any) => (
                <Link key={i.id} to={`/institutions/${i.id}`}
                  className="flex items-center p-2 bg-gray-800 rounded-lg hover:bg-gray-700/60 transition-colors">
                  <p className="text-sm text-white">{i.nombre}</p>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>

      {(l as any).proyectos?.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-3">Proyectos Financiados</h3>
          <div className="space-y-2">
            {(l as any).proyectos.map((p: any) => (
              <div key={p.id} className="flex items-center justify-between p-2 bg-gray-800 rounded-lg">
                <p className="text-sm text-white">{p.nombre}</p>
                {p.estado && <span className="text-xs text-gray-500">{p.estado}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {(l as any).contratos?.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-3">Contratos Asociados ({(l as any).contratos.length})</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left">
                  <th className="py-2 px-3 text-gray-400 font-medium">Número</th>
                  <th className="py-2 px-3 text-gray-400 font-medium text-right">Monto</th>
                </tr>
              </thead>
              <tbody>
                {(l as any).contratos.map((c: any) => (
                  <tr key={c.id} className="table-row">
                    <td className="py-2 px-3">
                      <Link to={`/contracts/${c.id}`} className="text-gov-400 hover:text-gov-300 font-mono text-xs">
                        {c.numero || `#${c.id}`}
                      </Link>
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-white">{fmt(c.monto, 'RD$')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
