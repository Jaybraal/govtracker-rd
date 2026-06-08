import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Download, Network } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { institutionsApi, exportApi } from '../services/api'
import { useApi } from '../hooks/useApi'

const fmt = (n: number) => n >= 1e9 ? `RD$${(n/1e9).toFixed(2)}B` : n >= 1e6 ? `RD$${(n/1e6).toFixed(0)}M` : `RD$${n?.toLocaleString()}`

export default function InstitutionDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: inst, loading } = useApi(() => institutionsApi.get(Number(id)), [id])

  if (loading) return <div className="p-6 text-gray-500">Cargando...</div>
  if (!inst) return <div className="p-6 text-gray-500">Institución no encontrada</div>

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title={(inst as any).nombre}
        subtitle={(inst as any).siglas}
        actions={
          <div className="flex gap-2">
            <Link to="/institutions" className="btn-ghost flex items-center gap-1.5"><ArrowLeft size={14} /> Volver</Link>
            <button onClick={() => exportApi.institutionReport(Number(id))} className="btn-ghost flex items-center gap-1.5">
              <Download size={14} /> PDF
            </button>
            <Link to={`/graph?entity_type=institution&entity_id=${id}`} className="btn-primary flex items-center gap-1.5">
              <Network size={14} /> Red
            </Link>
          </div>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div className="card text-center"><p className="text-xs text-gray-500">Total Contratado</p><p className="text-2xl font-bold text-white">{fmt((inst as any).total_monto_contratos)}</p></div>
        <div className="card text-center"><p className="text-xs text-gray-500">Contratos</p><p className="text-2xl font-bold text-white">{(inst as any).total_contratos?.toLocaleString()}</p></div>
        <div className="card text-center"><p className="text-xs text-gray-500">Tipo</p><p className="text-sm font-medium text-white mt-1">{(inst as any).tipo?.replace(/_/g, ' ')}</p></div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-3">Detalles</h3>
          <dl className="space-y-2 text-sm">
            {[
              ['Código', (inst as any).codigo], ['Presupuesto Anual', (inst as any).presupuesto_anual ? fmt((inst as any).presupuesto_anual) : null],
              ['Sitio Web', (inst as any).sitio_web], ['Activo', (inst as any).activo ? 'Sí' : 'No'],
            ].filter(([_, v]) => v).map(([k, v]) => (
              <div key={k as string} className="flex justify-between">
                <dt className="text-gray-500">{k as string}</dt>
                <dd className="text-white">{v as string}</dd>
              </div>
            ))}
          </dl>
        </div>

        {(inst as any).top_empresas?.length > 0 && (
          <div className="card">
            <h3 className="text-sm font-semibold text-white mb-3">Top Empresas Contratistas</h3>
            <div className="space-y-2">
              {(inst as any).top_empresas.map((e: any, i: number) => (
                <div key={e.company_id} className="flex items-center gap-3">
                  <span className="text-xs text-gray-600 w-5 text-right">{i + 1}</span>
                  <Link to={`/companies/${e.company_id}`} className="flex-1 text-xs text-gov-400 hover:text-gov-300 truncate">
                    Empresa #{e.company_id}
                  </Link>
                  <span className="text-xs font-mono text-white">{fmt(e.monto)}</span>
                  <span className="text-xs text-gray-500">{e.num_contratos}c</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <Link to={`/contracts?institution_id=${id}`} className="btn-primary">
          Ver todos los contratos →
        </Link>
      </div>
    </div>
  )
}
