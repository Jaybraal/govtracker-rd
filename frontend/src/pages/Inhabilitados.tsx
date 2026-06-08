import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ShieldAlert, ExternalLink, ChevronDown, ChevronUp, FileWarning } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { companiesApi } from '../services/api'
import { useApi } from '../hooks/useApi'

const fmt = (n: number) => n >= 1e9 ? `RD$${(n/1e9).toFixed(2)}B` : n >= 1e6 ? `RD$${(n/1e6).toFixed(1)}M` : `RD$${n?.toLocaleString()}`

const ESTADO_BADGE: Record<string, string> = {
  activo: 'badge-green',
  completado: 'badge-blue',
  cancelado: 'badge-red',
  suspendido: 'badge-yellow',
}

export default function Inhabilitados() {
  const { data, loading } = useApi(() => companiesApi.inhabilitados(100), [])
  const [expanded, setExpanded] = useState<number | null>(null)

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title="Proveedores Inhabilitados con Contratos Posteriores"
        subtitle="Empresas que el propio órgano regulador (DGCP/SECP) ya sancionó oficialmente — y que aun así firmaron contratos con el Estado en o después de esa fecha"
      />

      <div className="card bg-red-950/20 border-red-900/40 flex gap-3 items-start">
        <FileWarning size={18} className="text-red-400 mt-0.5 flex-shrink-0" />
        <p className="text-sm text-gray-300">
          Esta sección cruza, por <span className="text-white font-mono">RPE</span> (Registro de Proveedores del Estado),
          el listado oficial de <span className="text-white">Proveedores del Estado Inhabilitados</span> que publica la
          Dirección General de Contrataciones Públicas (DGCP) contra los contratos adjudicados que también publica DGCP.
          Cada caso está documentado con el número de resolución/oficio oficial, el motivo exacto de la sanción
          (incumplimiento contractual, presentar documentos falsos o adulterados, etc.), la fecha en que DGCP la inhabilitó,
          y los contratos firmados <span className="text-white">en o después</span> de esa fecha — con su monto y estado actual.
          Nada de esto es interpretación: son los mismos documentos oficiales que DGCP publica sobre sí misma.
        </p>
      </div>

      {loading ? (
        <div className="card text-center text-gray-500 py-8">Cargando...</div>
      ) : !data?.items?.length ? (
        <div className="card text-center text-gray-500 py-12">No hay casos documentados</div>
      ) : (
        <>
          <div className="flex flex-wrap gap-3">
            <div className="card py-2 px-4 flex items-center gap-2">
              <ShieldAlert size={14} className="text-red-400" />
              <span className="text-sm text-white font-semibold">{data.resumen.empresas}</span>
              <span className="text-xs text-gray-500">empresas inhabilitadas con contratos posteriores</span>
            </div>
            <div className="card py-2 px-4 flex items-center gap-2">
              <span className="text-sm text-white font-semibold">{data.resumen.contratos_posteriores_a_inhabilitacion.toLocaleString()}</span>
              <span className="text-xs text-gray-500">contratos firmados tras la sanción</span>
            </div>
            <div className="card py-2 px-4 flex items-center gap-2">
              <span className="text-sm text-yellow-400 font-mono font-semibold">{fmt(data.resumen.monto_total_contratos_posteriores)}</span>
              <span className="text-xs text-gray-500">monto total involucrado</span>
            </div>
          </div>

          <div className="space-y-3">
            {data.items.map((item: any) => {
              const isOpen = expanded === item.company_id
              return (
                <div key={item.company_id} className="card">
                  <button
                    onClick={() => setExpanded(isOpen ? null : item.company_id)}
                    className="w-full flex items-start justify-between gap-4 text-left"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Link to={`/companies/${item.company_id}`} className="text-white font-medium hover:text-gov-300 transition-colors" onClick={e => e.stopPropagation()}>
                          {item.nombre}
                        </Link>
                        <span className="text-xs text-gray-500 font-mono">RPE {item.rpe}</span>
                        {item.casos.some((c: any) => c.permanente) && (
                          <span className="badge-red">inhabilitación permanente</span>
                        )}
                      </div>
                      <p className="text-sm text-gray-400">
                        <span className="text-yellow-400 font-mono">{fmt(item.monto_contratos_posteriores)}</span>
                        {' '}en <span className="text-white">{item.num_contratos_posteriores}</span> contratos firmados
                        {' '}<span className="text-red-400">después</span> de su inhabilitación
                        {' '}· {item.casos.length} {item.casos.length === 1 ? 'evento de sanción' : 'eventos de sanción'} documentado{item.casos.length === 1 ? '' : 's'}
                        {' '}· histórico total: {fmt(item.total_monto_recibido)} en {item.total_contratos} contratos
                      </p>
                    </div>
                    {isOpen ? <ChevronUp size={18} className="text-gray-500 flex-shrink-0 mt-1" /> : <ChevronDown size={18} className="text-gray-500 flex-shrink-0 mt-1" />}
                  </button>

                  {isOpen && (
                    <div className="mt-4 pt-4 border-t border-gray-800 space-y-4">
                      {item.casos.map((caso: any, i: number) => (
                        <div key={i} className="bg-gray-800/40 rounded-lg p-3">
                          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                            <span className={caso.permanente ? 'badge-red' : 'badge-yellow'}>
                              inhabilitada desde {new Date(caso.fecha_inhabilitacion).toLocaleDateString('es-DO')}
                            </span>
                            {caso.oficio && <span className="text-xs text-gray-500 font-mono">{caso.oficio}</span>}
                            {caso.fecha_habilitacion && (
                              <span className="text-xs text-gray-500">rehabilitada: {new Date(caso.fecha_habilitacion).toLocaleDateString('es-DO')}</span>
                            )}
                            {caso.url_certificacion && (
                              <a href={caso.url_certificacion} target="_blank" rel="noopener noreferrer" className="text-xs text-gov-400 hover:text-gov-300 flex items-center gap-1">
                                <ExternalLink size={11} /> certificación RPE
                              </a>
                            )}
                          </div>
                          <p className="text-sm text-gray-300 mb-3">{caso.motivo}</p>

                          <p className="text-xs text-gray-500 mb-1.5">Contratos firmados en o después de esta sanción:</p>
                          <div className="space-y-1.5">
                            {caso.contratos.map((ct: any) => (
                              <Link
                                key={ct.id}
                                to={`/contracts/${ct.id}`}
                                className="flex items-center justify-between gap-3 text-xs bg-gray-900/60 hover:bg-gray-900 transition-colors rounded px-3 py-2"
                              >
                                <div className="flex items-center gap-2 min-w-0">
                                  <span className="text-white font-mono flex-shrink-0">{ct.numero}</span>
                                  <span className="text-gray-500 truncate">{ct.objeto}</span>
                                </div>
                                <div className="flex items-center gap-3 flex-shrink-0">
                                  <span className="text-gray-500">{new Date(ct.fecha_firma).toLocaleDateString('es-DO')}</span>
                                  <span className="text-yellow-400 font-mono">{fmt(ct.monto)}</span>
                                  {ct.estado && <span className={ESTADO_BADGE[ct.estado] || 'badge-blue'}>{ct.estado}</span>}
                                </div>
                              </Link>
                            ))}
                          </div>
                        </div>
                      ))}
                      <p className="text-xs text-gray-600">Fuente: {item.fuente}</p>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
