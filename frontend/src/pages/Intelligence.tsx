import { useState } from 'react'
import { Search, Eye, Network, AlertTriangle, User, TrendingUp, Shield } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { intelligenceApi } from '../services/api'
import { useApi } from '../hooks/useApi'

const fmt = (n: number) => {
  if (!n) return 'RD$0'
  if (n >= 1e9) return `RD$${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6) return `RD$${(n / 1e6).toFixed(1)}M`
  return `RD$${n.toLocaleString()}`
}

const SEV_STYLE: Record<string, string> = {
  critica: 'border-l-4 border-red-500 bg-red-950/20',
  alta:    'border-l-4 border-orange-500 bg-orange-950/20',
  media:   'border-l-4 border-yellow-500 bg-yellow-950/20',
  baja:    'border-l-4 border-blue-500 bg-blue-950/20',
}

const SEV_BADGE: Record<string, string> = {
  critica: 'badge-red',
  alta:    'badge-red',
  media:   'badge-yellow',
  baja:    'badge-blue',
}

type Tab = 'personas' | 'patrones' | 'nombres' | 'red'

export default function Intelligence() {
  const [tab, setTab] = useState<Tab>('personas')
  const [searchNombre, setSearchNombre] = useState('')
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null)

  const { data: resumen } = useApi(() => intelligenceApi.resumen(), [])
  const { data: personas, loading: loadingPersonas } = useApi(() => intelligenceApi.personasInteres(100), [])
  const { data: patrones, loading: loadingPatrones } = useApi(() => intelligenceApi.patrones(), [])
  const { data: nombres, loading: loadingNombres } = useApi(
    () => intelligenceApi.nombresFrecuentes(2, searchNombre || undefined),
    [searchNombre],
  )
  const { data: redPersona, loading: loadingRed } = useApi(
    () => selectedPersona ? intelligenceApi.redPersona(selectedPersona) : Promise.resolve(null),
    [selectedPersona],
  )

  const TABS = [
    { id: 'personas', label: 'Personas de Interés', icon: User },
    { id: 'patrones', label: 'Patrones Sospechosos', icon: AlertTriangle },
    { id: 'nombres',  label: 'Nombres Frecuentes',  icon: TrendingUp },
    { id: 'red',      label: 'Red de Conexiones',   icon: Network },
  ] as const

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title="Inteligencia de Patrones"
        subtitle="Detección automática de personas de interés, redes ocultas y anomalías"
        actions={
          <div className="flex items-center gap-2 text-xs text-gov-400 bg-gov-900/30 border border-gov-800 px-3 py-1.5 rounded-lg">
            <Shield size={12} /> Motor de análisis activo
          </div>
        }
      />

      {/* KPIs del resumen */}
      {resumen && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            { label: 'Personas detectadas', value: resumen.stats.personas_detectadas >= 200 ? '200+' : resumen.stats.personas_detectadas, color: 'text-white' },
            { label: 'Doble rol (firmante + rep.)', value: resumen.stats.personas_doble_rol, color: 'text-red-400' },
            { label: 'Patrones críticos', value: resumen.stats.patrones_criticos, color: 'text-red-400' },
            { label: 'Patrones altos', value: resumen.stats.patrones_altos, color: 'text-orange-400' },
            { label: 'Total patrones', value: resumen.stats.total_patrones, color: 'text-white' },
          ].map(k => (
            <div key={k.label} className="card text-center py-3">
              <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
              <p className="text-xs text-gray-500 mt-0.5">{k.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-xl p-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id as Tab)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-all flex-1 justify-center ${
              tab === id
                ? 'bg-gov-700 text-white font-medium'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Icon size={14} />
            <span className="hidden md:inline">{label}</span>
          </button>
        ))}
      </div>

      {/* ── TAB: PERSONAS DE INTERÉS ── */}
      {tab === 'personas' && (
        <div className="space-y-3">
          <p className="text-xs text-gray-500 px-1">
            Personas rankeadas por monto involucrado, doble rol (firmante de contratos + representante legal de empresas ganadoras) y concentración de poder.
          </p>
          {loadingPersonas ? (
            <div className="card text-center text-gray-500 py-8">Analizando patrones...</div>
          ) : (
            <div className="space-y-2">
              {(personas || []).map((p: any, i: number) => (
                <div key={i} className={`card ${p.tiene_doble_rol || p.flags?.some((f: string) => f.includes('DOBLE ROL')) ? 'border-red-900/60' : ''}`}>
                  <div className="flex items-start gap-4">
                    {/* Ranking */}
                    <div className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm"
                         style={{ background: i < 3 ? '#7f1d1d' : '#1f2937', color: i < 3 ? '#fca5a5' : '#9ca3af' }}>
                      {i + 1}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="font-semibold text-white">{p.nombre}</p>
                        {p.cedula && <span className="text-xs text-gray-500 font-mono">CED: {p.cedula}</span>}
                        {p.roles?.includes('firmante') && (
                          <span className="badge-blue text-xs">✍ firmante</span>
                        )}
                        {p.roles?.includes('representante_legal') && (
                          <span className="badge-purple text-xs">⚖ rep. legal</span>
                        )}
                        {p.cargos?.map((cargo: string) => (
                          <span key={cargo} className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">{cargo}</span>
                        ))}
                        {p.roles?.includes('firmante') && p.roles?.includes('representante_legal') && (
                          <span className="badge-red text-xs font-bold">⚠ DOBLE ROL</span>
                        )}
                      </div>

                      {/* Métricas */}
                      <div className="flex flex-wrap gap-4 mt-2 text-xs text-gray-400">
                        {p.total_monto > 0 && (
                          <span className="text-yellow-400 font-mono font-medium">{fmt(p.total_monto)}</span>
                        )}
                        {p.total_contratos > 0 && (
                          <span>{p.total_contratos} contratos</span>
                        )}
                        {p.num_instituciones_firmante > 0 && (
                          <span>{p.num_instituciones_firmante} institución{p.num_instituciones_firmante > 1 ? 'es' : ''}</span>
                        )}
                        {p.num_empresas_repr > 0 && (
                          <span>Representa {p.num_empresas_repr} empresa{p.num_empresas_repr > 1 ? 's' : ''}</span>
                        )}
                      </div>

                      {/* Flags */}
                      {p.flags?.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {p.flags.map((f: string, fi: number) => (
                            <span key={fi} className="text-xs text-yellow-300 bg-yellow-950/30 border border-yellow-900/50 px-2 py-0.5 rounded-md">
                              {f}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Empresas que representa */}
                      {p.empresas_representa?.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs text-gray-600">Empresas que representa:</p>
                          <p className="text-xs text-gray-400">{p.empresas_representa.slice(0, 4).join(' · ')}</p>
                        </div>
                      )}
                    </div>

                    {/* Score */}
                    <div className="flex-shrink-0 text-right">
                      <div className={`text-lg font-bold ${p.score_riesgo >= 50 ? 'text-red-400' : p.score_riesgo >= 25 ? 'text-yellow-400' : 'text-gray-500'}`}>
                        {p.score_riesgo}
                      </div>
                      <p className="text-xs text-gray-600">score</p>
                      <button
                        onClick={() => { setSelectedPersona(p.nombre); setTab('red') }}
                        className="btn-ghost text-xs mt-1 flex items-center gap-1 justify-end"
                      >
                        <Network size={10} /> Red
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── TAB: PATRONES SOSPECHOSOS ── */}
      {tab === 'patrones' && (
        <div className="space-y-3">
          <p className="text-xs text-gray-500 px-1">
            Anomalías estadísticas detectadas automáticamente: fraccionamiento, monopolio sectorial, dependencia única, contratación directa irregular.
          </p>
          {loadingPatrones ? (
            <div className="card text-center text-gray-500 py-8">Analizando patrones...</div>
          ) : (patrones || []).length === 0 ? (
            <div className="card text-center text-gray-500 py-8">No se detectaron patrones con los datos actuales</div>
          ) : (
            <div className="space-y-2">
              {(patrones || []).map((p: any, i: number) => (
                <div key={i} className={`card ${SEV_STYLE[p.severidad] || ''}`}>
                  <div className="flex items-start gap-3">
                    <AlertTriangle size={16} className={p.severidad === 'critica' || p.severidad === 'alta' ? 'text-red-400 mt-0.5' : 'text-yellow-400 mt-0.5'} />
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={SEV_BADGE[p.severidad] || 'badge-blue'}>{p.severidad}</span>
                        <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">
                          {p.tipo.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <p className="text-white font-medium">{p.titulo}</p>
                      <p className="text-sm text-gray-400 mt-0.5">{p.descripcion}</p>
                      <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-500">
                        {p.monto > 0 && <span className="text-yellow-400 font-mono">{fmt(p.monto)}</span>}
                        {p.entidad_empresa && <span>🏢 {p.entidad_empresa}</span>}
                        {p.entidad_institucion && <span>🏛 {p.entidad_institucion}</span>}
                        {p.porcentaje && <span>📊 {p.porcentaje.toFixed(1)}% concentración</span>}
                        {p.cantidad && <span>📋 {p.cantidad} contratos</span>}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── TAB: NOMBRES FRECUENTES ── */}
      {tab === 'nombres' && (
        <div className="space-y-4">
          <div className="card flex gap-3">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                className="input pl-8"
                placeholder="Buscar persona por nombre..."
                value={searchNombre}
                onChange={e => setSearchNombre(e.target.value)}
              />
            </div>
          </div>

          {loadingNombres ? (
            <div className="card text-center text-gray-500 py-8">Buscando...</div>
          ) : (
            <div className="card p-0 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-left">
                    <th className="px-4 py-3 text-gray-400 font-medium">#</th>
                    <th className="px-4 py-3 text-gray-400 font-medium">Nombre</th>
                    <th className="px-4 py-3 text-gray-400 font-medium text-center">Como firmante</th>
                    <th className="px-4 py-3 text-gray-400 font-medium text-center">Como rep. legal</th>
                    <th className="px-4 py-3 text-gray-400 font-medium text-right">Monto firmado</th>
                    <th className="px-4 py-3 text-gray-400 font-medium text-right">Monto empresas</th>
                    <th className="px-4 py-3 text-gray-400 font-medium text-center">Inst.</th>
                    <th className="px-4 py-3 text-gray-400 font-medium text-center">Doble rol</th>
                    <th className="px-4 py-3 text-gray-400 font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {(nombres || []).map((n: any, i: number) => (
                    <tr key={i} className={`table-row ${n.tiene_doble_rol ? 'bg-red-950/10' : ''}`}>
                      <td className="px-4 py-2.5 text-xs text-gray-600 font-mono">{i + 1}</td>
                      <td className="px-4 py-2.5">
                        <p className="text-white font-medium">{n.nombre}</p>
                        {n.cedula && <p className="text-xs text-gray-600 font-mono">{n.cedula}</p>}
                        {n.cargos?.length > 0 && (
                          <p className="text-xs text-gray-600">{n.cargos.join(' · ')}</p>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        {n.apariciones_firmante > 0
                          ? <span className="badge-blue">{n.apariciones_firmante}</span>
                          : <span className="text-gray-700">—</span>}
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        {n.apariciones_repr > 0
                          ? <span className="badge-purple">{n.apariciones_repr}</span>
                          : <span className="text-gray-700">—</span>}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-xs text-gray-300">
                        {n.monto_contratos_firmados > 0 ? fmt(n.monto_contratos_firmados) : '—'}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-xs text-gray-300">
                        {n.monto_contratos_empresa > 0 ? fmt(n.monto_contratos_empresa) : '—'}
                      </td>
                      <td className="px-4 py-2.5 text-center text-xs text-gray-500">{n.num_instituciones}</td>
                      <td className="px-4 py-2.5 text-center">
                        {n.tiene_doble_rol
                          ? <span className="badge-red text-xs">⚠ DOBLE</span>
                          : <span className="text-gray-700 text-xs">—</span>}
                      </td>
                      <td className="px-4 py-2.5">
                        <button
                          onClick={() => { setSelectedPersona(n.nombre); setTab('red') }}
                          className="btn-ghost text-xs flex items-center gap-1"
                        >
                          <Eye size={12} /> Ver red
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── TAB: RED DE CONEXIONES ── */}
      {tab === 'red' && (
        <div className="space-y-4">
          <div className="card flex gap-3">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                className="input pl-8"
                placeholder="Nombre de la persona a investigar..."
                value={selectedPersona || ''}
                onChange={e => setSelectedPersona(e.target.value || null)}
              />
            </div>
            <p className="text-xs text-gray-500 self-center w-64">
              Escribe un nombre para ver su red de contratos, empresas e instituciones
            </p>
          </div>

          {loadingRed && (
            <div className="card text-center text-gray-500 py-8">Construyendo red...</div>
          )}

          {redPersona && !loadingRed && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="card text-center"><p className="text-xl font-bold text-white">{redPersona.contratos_encontrados}</p><p className="text-xs text-gray-500">Contratos firmados</p></div>
                <div className="card text-center"><p className="text-xl font-bold text-white">{redPersona.empresas_representa}</p><p className="text-xs text-gray-500">Empresas representa</p></div>
                <div className="card text-center"><p className="text-xl font-bold text-white">{redPersona.nodes?.length || 0}</p><p className="text-xs text-gray-500">Nodos en la red</p></div>
              </div>

              {/* SVG de la red */}
              <div className="card p-0 overflow-hidden">
                <div className="bg-gray-950 rounded-xl" style={{ height: 500 }}>
                  <svg width="100%" height="100%" viewBox="0 0 900 500">
                    {(redPersona.edges || []).map((edge: any, i: number) => {
                      const fromNode = redPersona.nodes?.find((n: any) => n.id === edge.from)
                      const toNode   = redPersona.nodes?.find((n: any) => n.id === edge.to)
                      if (!fromNode || !toNode) return null
                      const ni = redPersona.nodes.indexOf(fromNode)
                      const nj = redPersona.nodes.indexOf(toNode)
                      const total = redPersona.nodes.length
                      const cx = 450, cy = 250
                      const fromX = ni === 0 ? cx : cx + 200 * Math.cos((ni / (total - 1)) * 2 * Math.PI)
                      const fromY = ni === 0 ? cy : cy + 180 * Math.sin((ni / (total - 1)) * 2 * Math.PI)
                      const toX = nj === 0 ? cx : cx + 200 * Math.cos((nj / (total - 1)) * 2 * Math.PI)
                      const toY = nj === 0 ? cy : cy + 180 * Math.sin((nj / (total - 1)) * 2 * Math.PI)
                      return (
                        <line key={i} x1={fromX} y1={fromY} x2={toX} y2={toY}
                              stroke={edge.dashes ? '#374151' : '#4b5563'}
                              strokeWidth={1.5} strokeDasharray={edge.dashes ? '4 4' : undefined} opacity={0.7} />
                      )
                    })}
                    {(redPersona.nodes || []).map((node: any, i: number) => {
                      const total = redPersona.nodes.length
                      const cx = 450, cy = 250
                      const x = i === 0 ? cx : cx + 200 * Math.cos((i / (total - 1)) * 2 * Math.PI)
                      const y = i === 0 ? cy : cy + 180 * Math.sin((i / (total - 1)) * 2 * Math.PI)
                      const colors: Record<string, string> = {
                        persona_interes: '#ef4444',
                        institution: '#6366f1',
                        company: '#10b981',
                        company_repr: '#f59e0b',
                        persona_relacionada: '#8b5cf6',
                      }
                      const r = i === 0 ? 24 : 14
                      return (
                        <g key={node.id} transform={`translate(${x},${y})`}>
                          <circle r={r} fill={colors[node.group] || '#6b7280'} opacity={0.9} />
                          <text textAnchor="middle" dy="0.35em" fill="white"
                                fontSize={i === 0 ? 9 : 7} fontWeight={i === 0 ? '700' : '400'}>
                            {(node.label || '').slice(0, 12)}
                          </text>
                          {i !== 0 && (
                            <text textAnchor="middle" dy={r + 10} fill="#9ca3af" fontSize={7}>
                              {(node.label || '').slice(0, 14)}
                            </text>
                          )}
                        </g>
                      )
                    })}
                  </svg>
                </div>
                <div className="p-3 flex gap-4 text-xs text-gray-500">
                  {[
                    { color: '#ef4444', label: 'Persona investigada' },
                    { color: '#6366f1', label: 'Institución' },
                    { color: '#10b981', label: 'Empresa (contrato firmado)' },
                    { color: '#f59e0b', label: 'Empresa (rep. legal)' },
                    { color: '#8b5cf6', label: 'Persona relacionada' },
                  ].map(l => (
                    <div key={l.label} className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-full" style={{ background: l.color }} />
                      {l.label}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {!selectedPersona && !loadingRed && (
            <div className="card flex flex-col items-center justify-center py-16 text-gray-600">
              <Network size={48} className="mb-4 opacity-30" />
              <p className="text-sm">Escribe un nombre para investigar sus conexiones</p>
              <p className="text-xs mt-1">O selecciona una persona desde la pestaña "Personas de Interés"</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
