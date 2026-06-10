import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Network } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { companiesApi } from '../services/api'
import { useApi } from '../hooks/useApi'

const fmt = (n: number) => n >= 1e9 ? `RD$${(n/1e9).toFixed(2)}B` : n >= 1e6 ? `RD$${(n/1e6).toFixed(1)}M` : `RD$${n?.toLocaleString()}`

export default function CompanyDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: c, loading } = useApi(() => companiesApi.get(Number(id)), [id])

  if (loading) return <div className="p-6 text-gray-500">Cargando...</div>
  if (!c) return <div className="p-6 text-gray-500">Empresa no encontrada</div>

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title={c.nombre}
        subtitle={c.rnc ? `RNC: ${c.rnc}` : c.sector || ''}
        actions={
          <div className="flex gap-2">
            <Link to="/companies" className="btn-ghost flex items-center gap-1.5"><ArrowLeft size={14} /> Volver</Link>
            <Link to={`/graph?entity_type=company&entity_id=${id}`} className="btn-primary flex items-center gap-1.5">
              <Network size={14} /> Ver en grafo
            </Link>
          </div>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          ['Monto Total', fmt(c.total_monto_recibido), 'text-white'],
          ['Contratos', c.total_contratos.toLocaleString(), 'text-white'],
          ['Instituciones', c.total_instituciones.toString(), 'text-white'],
          ['Concentración', c.indice_concentracion != null ? `${c.indice_concentracion.toFixed(0)}%` : '—', c.indice_concentracion > 80 ? 'text-red-400' : 'text-white'],
        ].map(([label, value, cls]) => (
          <div key={label as string} className="card text-center">
            <p className="text-xs text-gray-500 mb-1">{label as string}</p>
            <p className={`text-2xl font-bold ${cls as string}`}>{value as string}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-3">Información</h3>
          <dl className="space-y-2 text-sm">
            {[
              ['RNC', c.rnc], ['Tipo', c.tipo_empresa], ['Sector', c.sector],
              ['Provincia', c.provincia], ['Email', c.email], ['Teléfono', c.telefono],
            ].filter(([_, v]) => v).map(([k, v]) => (
              <div key={k as string} className="flex justify-between">
                <dt className="text-gray-500">{k as string}</dt>
                <dd className="text-white">{v as string}</dd>
              </div>
            ))}
            {c.primer_contrato && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Período activo</dt>
                <dd className="text-white text-xs">
                  {new Date(c.primer_contrato).getFullYear()} – {c.ultimo_contrato ? new Date(c.ultimo_contrato).getFullYear() : 'presente'}
                </dd>
              </div>
            )}
          </dl>
        </div>

        {(c as any).representantes?.length > 0 && (
          <div className="card">
            <h3 className="text-sm font-semibold text-white mb-3">Representantes / Contactos</h3>
            <div className="space-y-2">
              {(c as any).representantes.map((r: any, i: number) => (
                <div key={r.id ?? i} className="flex items-center gap-3 p-2 bg-gray-800 rounded-lg">
                  <div className="w-8 h-8 bg-gov-700/40 rounded-full flex items-center justify-center text-xs text-gov-300 font-bold">
                    {r.nombre.split(' ').filter(Boolean).map((n: string) => n[0]).slice(0, 2).join('')}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm text-white">{r.nombre}</p>
                    <p className="text-xs text-gray-500">{r.cargo || 'Representante'} {r.cedula ? `· ${r.cedula}` : ''}</p>
                    {(r.telefono || r.email) && (
                      <p className="text-xs text-gray-600 mt-0.5">
                        {[r.telefono, r.email].filter(Boolean).join(' · ')}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {(c as any).contratos_recientes?.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white">Contratos Recientes (Top 20 por monto)</h3>
            <Link to={`/contracts?company_id=${id}`} className="text-xs text-gov-400 hover:text-gov-300">
              Ver todos los contratos ({c.total_contratos.toLocaleString()}) →
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left">
                  <th className="py-2 px-3 text-gray-400 font-medium">Número</th>
                  <th className="py-2 px-3 text-gray-400 font-medium">Descripción</th>
                  <th className="py-2 px-3 text-gray-400 font-medium text-right">Monto</th>
                  <th className="py-2 px-3 text-gray-400 font-medium">Institución</th>
                </tr>
              </thead>
              <tbody>
                {(c as any).contratos_recientes.map((ct: any) => (
                  <tr key={ct.id} className="table-row">
                    <td className="py-2 px-3">
                      <Link to={`/contracts/${ct.id}`} className="text-gov-400 hover:text-gov-300 font-mono text-xs">
                        {ct.numero || `#${ct.id}`}
                      </Link>
                    </td>
                    <td className="py-2 px-3 text-xs text-gray-400 max-w-64 truncate">{ct.descripcion || '—'}</td>
                    <td className="py-2 px-3 text-right font-mono text-white">{fmt(ct.monto)}</td>
                    <td className="py-2 px-3">
                      <Link to={`/institutions/${ct.institucion_id}`} className="text-xs text-gray-400 hover:text-white">
                        #{ct.institucion_id}
                      </Link>
                    </td>
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
