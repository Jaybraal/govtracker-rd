import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { legislatorsApi } from '../services/api'
import { useApi } from '../hooks/useApi'

const fmt = (n: number) => {
  if (!n) return 'RD$0'
  if (n >= 1e9) return `RD$${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6) return `RD$${(n / 1e6).toFixed(0)}M`
  return `RD$${n.toLocaleString()}`
}

const CAMARA_LABEL: Record<string, string> = {
  diputados: 'Diputados',
  senado:    'Senado',
}

export default function LegislatorDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: l, loading } = useApi(() => legislatorsApi.get(Number(id)), [id])

  if (loading) return <div className="p-6 text-gray-500">Cargando...</div>
  if (!l) return <div className="p-6 text-gray-500">Legislador no encontrado</div>

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title={l.nombre_completo}
        subtitle={`${l.funcion ? l.funcion + ' · ' : ''}${CAMARA_LABEL[l.camara] || l.camara || ''}`}
        actions={
          <Link to="/legislators" className="btn-ghost flex items-center gap-1.5"><ArrowLeft size={14} /> Volver</Link>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          ['Cámara', CAMARA_LABEL[l.camara] || l.camara || '—'],
          ['Partido', l.partido_siglas || '—'],
          ['Provincia', l.provincia || '—'],
          ['Contratos Relacionados', `${l.total_contratos_relacionados || 0} (${fmt(l.total_monto_relacionado)})`],
        ].map(([label, value]) => (
          <div key={label} className="card text-center">
            <p className="text-xs text-gray-500 mb-1">{label}</p>
            <p className="text-xl font-bold text-white">{value}</p>
          </div>
        ))}
      </div>

      <div className="card">
        <h3 className="text-sm font-semibold text-white mb-3">Información</h3>
        <dl className="space-y-2 text-sm">
          {[
            ['Función', l.funcion],
            ['Cámara', CAMARA_LABEL[l.camara] || l.camara],
            ['Partido', l.partido_nombre],
            ['Provincia', l.provincia],
            ['Circunscripción', l.circunscripcion],
            ['ID SIL', l.legislador_id_sil],
            ['Fuente', l.fuente],
          ].filter(([_, v]) => v).map(([k, v]) => (
            <div key={k as string} className="flex justify-between gap-3">
              <dt className="text-gray-500 shrink-0">{k as string}</dt>
              <dd className="text-white text-right">{v as string}</dd>
            </div>
          ))}
          {l.url_fuente && (
            <div className="flex justify-between">
              <dt className="text-gray-500">Enlace</dt>
              <dd><a href={l.url_fuente} target="_blank" rel="noopener noreferrer" className="text-gov-400 hover:text-gov-300 text-xs">Ver fuente original (SIL) →</a></dd>
            </div>
          )}
        </dl>
      </div>

      {l.comisiones?.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-3">Comisiones del Congreso ({l.comisiones.length})</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left">
                  <th className="py-2 px-3 text-gray-400 font-medium">Comisión</th>
                  <th className="py-2 px-3 text-gray-400 font-medium">Tipo</th>
                  <th className="py-2 px-3 text-gray-400 font-medium">Cargo</th>
                </tr>
              </thead>
              <tbody>
                {l.comisiones.map((com: any) => (
                  <tr key={com.comision_id} className="table-row">
                    <td className="py-2 px-3">
                      <Link to={`/comisiones/${com.comision_id}`} className="text-gov-400 hover:text-gov-300 text-sm">
                        {com.nombre}
                      </Link>
                    </td>
                    <td className="py-2 px-3 text-xs text-gray-400">{com.tipo}</td>
                    <td className="py-2 px-3 text-xs text-gray-400">{com.cargo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {l.contratos_relacionados?.length > 0 && (
        <div className="card border-yellow-900/40">
          <h3 className="text-sm font-semibold text-white mb-3">Contratos Relacionados ({l.contratos_relacionados.length})</h3>
          <p className="text-xs text-gray-500 mb-3">
            Contratos del Estado de empresas con un representante legal cuyo nombre coincide con «{l.nombre_completo}».
            Es una coincidencia por nombre — el SIL no publica cédula del legislador — y requiere verificación manual
            de identidad antes de concluir que se trata de la misma persona.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left">
                  <th className="py-2 px-3 text-gray-400 font-medium">Número</th>
                  <th className="py-2 px-3 text-gray-400 font-medium">Descripción</th>
                  <th className="py-2 px-3 text-gray-400 font-medium">Institución</th>
                  <th className="py-2 px-3 text-gray-400 font-medium text-right">Monto</th>
                </tr>
              </thead>
              <tbody>
                {l.contratos_relacionados.map((ct: any) => (
                  <tr key={ct.id} className="table-row">
                    <td className="py-2 px-3">
                      <Link to={`/contracts/${ct.id}`} className="text-gov-400 hover:text-gov-300 font-mono text-xs">
                        {ct.numero || `#${ct.id}`}
                      </Link>
                    </td>
                    <td className="py-2 px-3 text-xs text-gray-400 max-w-96 truncate">{ct.descripcion}</td>
                    <td className="py-2 px-3">
                      {ct.institucion_id ? (
                        <Link to={`/institutions/${ct.institucion_id}`} className="text-gov-400 hover:text-gov-300 text-xs">
                          Ver institución →
                        </Link>
                      ) : '—'}
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-yellow-400 font-semibold">{fmt(ct.monto)}</td>
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
