import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie,
} from 'recharts'
import { Flag, DollarSign, AlertTriangle, TrendingDown, Users } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import { useApi } from '../hooks/useApi'
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

const fmt = (n: number) => {
  if (!n) return 'RD$0'
  if (n >= 1e9) return `RD$${(n/1e9).toFixed(2)}B`
  if (n >= 1e6) return `RD$${(n/1e6).toFixed(0)}M`
  return `RD$${n.toLocaleString()}`
}

const IDEOLOGIA_LABEL: Record<string, string> = {
  centro_derecha:   'Centro Derecha',
  centro:           'Centro',
  centro_izquierda: 'Centro Izquierda',
  derecha:          'Derecha',
  izquierda:        'Izquierda',
  populista:        'Populista',
  otro:             'Otro',
}

type Tab = 'resumen' | 'financiamiento' | 'gastos' | 'proveedores' | 'detalle'

export default function PoliticalParties() {
  const navigate = useNavigate()
  const [tab, setTab]               = useState<Tab>('resumen')
  const [selectedParty, setSelected] = useState<any>(null)
  const [filterAnio, setFilterAnio]  = useState('')

  const { data: parties, loading } = useApi(() => api.get('/parties/').then(r => r.data), [])
  const { data: stats }            = useApi(() => api.get('/parties/stats').then(r => r.data), [])
  const { data: financ }           = useApi(
    () => api.get('/parties/financiamiento', { params: { ...(filterAnio && { anio: filterAnio }) } }).then(r => r.data),
    [filterAnio],
  )
  const { data: gastos }           = useApi(() => api.get('/parties/gastos').then(r => r.data), [])
  const { data: proveedores }      = useApi(() => api.get('/parties/proveedores').then(r => r.data), [])
  const { data: partyDetail }      = useApi(
    () => selectedParty ? api.get(`/parties/${selectedParty.id}`).then(r => r.data) : Promise.resolve(null),
    [selectedParty?.id],
  )

  const TABS = [
    { id: 'resumen',       label: '📊 Resumen' },
    { id: 'financiamiento', label: '💰 Financiamiento' },
    { id: 'gastos',        label: '📋 Gastos declarados' },
    { id: 'proveedores',   label: '🏢 Proveedores' },
    { id: 'detalle',       label: '🔍 Detalle partido' },
  ] as const

  const totalNoDeclarado = (stats?.total_financiamiento_publico || 0) - (stats?.total_gastos_declarados || 0)

  return (
    <div className="p-6 space-y-5">
      <PageHeader
        title="Partidos Políticos"
        subtitle="Financiamiento público JCE — Ley 33-18 — rendición de cuentas"
      />

      {/* KPIs */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Partidos activos"      value={stats.total_partidos.toString()}                   icon={<Flag size={16}/>}        color="blue" />
          <StatCard label="Total financiado JCE"  value={fmt(stats.total_financiamiento_publico)}           icon={<DollarSign size={16}/>}  color="purple" />
          <StatCard label="Gastos declarados"     value={fmt(stats.total_gastos_declarados)}                icon={<TrendingDown size={16}/>} color="green" />
          <StatCard label="Sin rendir cuentas"    value={fmt(totalNoDeclarado)}                             icon={<AlertTriangle size={16}/>} color="red" />
        </div>
      )}

      {/* Representación política */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            ['Senadores', stats.total_senadores],
            ['Diputados', stats.total_diputados],
          ].map(([k, v]) => (
            <div key={k as string} className="card flex items-center gap-3">
              <Users size={18} className="text-gov-400" />
              <div>
                <p className="text-xl font-bold text-white">{v}</p>
                <p className="text-xs text-gray-500">{k as string} total</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-xl p-1 flex-wrap">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex-1 min-w-24 py-2 px-2 rounded-lg text-xs transition-all ${tab === t.id ? 'bg-gov-700 text-white font-medium' : 'text-gray-400 hover:text-white'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ─── RESUMEN ─── */}
      {tab === 'resumen' && stats && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Ranking financiamiento */}
            <div className="card">
              <h3 className="text-sm font-semibold text-white mb-4">Financiamiento por Partido</h3>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={stats.ranking_financiamiento} layout="vertical" margin={{ left:10, right:30 }}>
                  <XAxis type="number" tickFormatter={v => `${(v/1e6).toFixed(0)}M`} tick={{ fill:'#6b7280', fontSize:10 }} />
                  <YAxis type="category" dataKey="siglas" tick={{ fill:'#9ca3af', fontSize:11 }} width={70} />
                  <Tooltip
                    formatter={(v: number, name: string) => [fmt(v), name === 'financiamiento' ? 'Financiado' : 'Gastos declarados']}
                    contentStyle={{ background:'#111827', border:'1px solid #374151', borderRadius:8 }}
                  />
                  <Bar dataKey="financiamiento" name="financiamiento" radius={[0,4,4,0]}>
                    {stats.ranking_financiamiento.map((r: any, i: number) => (
                      <Cell key={i} fill={r.color || '#6366f1'} opacity={0.85} />
                    ))}
                  </Bar>
                  <Bar dataKey="gastos" name="gastos" fill="#10b981" opacity={0.6} radius={[0,4,4,0]} />
                </BarChart>
              </ResponsiveContainer>
              <div className="flex gap-4 mt-2 text-xs text-gray-500">
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-gov-500"/> Financiado</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-500"/> Declarado</span>
              </div>
            </div>

            {/* Votos */}
            <div className="card">
              <h3 className="text-sm font-semibold text-white mb-4">Votos Últimas Elecciones 2024</h3>
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={(parties || []).filter((p: any) => p.votos_ultimas_elecciones > 0)}
                    dataKey="votos_ultimas_elecciones"
                    nameKey="siglas"
                    cx="50%" cy="50%"
                    outerRadius={95}
                    label={({ siglas, votos_ultimas_elecciones }: any) =>
                      `${siglas} ${votos_ultimas_elecciones?.toFixed(1)}%`
                    }
                    labelLine={{ stroke:'#4b5563' }}
                  >
                    {(parties || []).map((p: any, i: number) => (
                      <Cell key={i} fill={p.color || '#6b7280'} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => [`${v}%`, 'Votos']} contentStyle={{ background:'#111827', border:'1px solid #374151', borderRadius:8 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Financiamiento por año */}
          {stats.financiamiento_por_anio?.length > 0 && (
            <div className="card">
              <h3 className="text-sm font-semibold text-white mb-4">Evolución del Financiamiento Público</h3>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={stats.financiamiento_por_anio}>
                  <XAxis dataKey="anio" tick={{ fill:'#9ca3af', fontSize:11 }} />
                  <YAxis tickFormatter={v => `${(v/1e9).toFixed(1)}B`} tick={{ fill:'#6b7280', fontSize:10 }} />
                  <Tooltip formatter={(v: number) => fmt(v)} contentStyle={{ background:'#111827', border:'1px solid #374151', borderRadius:8 }} />
                  <Bar dataKey="total" fill="#8b5cf6" radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Tarjetas partidos */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(parties || []).map((p: any) => {
              const f_total = p.total_financiamiento_jce || 0
              return (
                <div
                  key={p.id}
                  onClick={() => { setSelected(p); setTab('detalle') }}
                  className="card cursor-pointer hover:border-gov-700 transition-colors"
                  style={{ borderLeftColor: p.color, borderLeftWidth: 3 }}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center font-bold text-sm text-white"
                         style={{ background: p.color || '#4b5563' }}>
                      {p.siglas?.slice(0,3)}
                    </div>
                    <div>
                      <p className="font-semibold text-white text-sm">{p.siglas}</p>
                      <p className="text-xs text-gray-500 line-clamp-1">{p.nombre}</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs mt-2">
                    <div>
                      <p className="text-gray-500">Financiamiento JCE</p>
                      <p className="text-white font-mono">{fmt(f_total)}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Votos 2024</p>
                      <p className="text-white">{p.votos_ultimas_elecciones?.toFixed(1)}%</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Senadores / Diputados</p>
                      <p className="text-white">{p.senadores} / {p.diputados}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Ideología</p>
                      <p className="text-gray-400">{IDEOLOGIA_LABEL[p.ideologia]}</p>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ─── FINANCIAMIENTO ─── */}
      {tab === 'financiamiento' && (
        <div className="space-y-4">
          <div className="card flex gap-3 items-center">
            <label className="text-xs text-gray-400">Año:</label>
            <select className="input w-32" value={filterAnio} onChange={e => setFilterAnio(e.target.value)}>
              <option value="">Todos</option>
              {[2024, 2023, 2022, 2021, 2020].map(y => <option key={y} value={y}>{y}</option>)}
            </select>
            <p className="text-xs text-gray-500 ml-auto">
              Fuente: JCE — Dirección de Financiamiento Político · Ley 33-18
            </p>
          </div>
          <div className="card p-0 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left">
                  <th className="px-4 py-3 text-gray-400 font-medium">Partido</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Año</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Concepto</th>
                  <th className="px-4 py-3 text-gray-400 font-medium text-right">Monto</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Fuente de pago</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Banco</th>
                </tr>
              </thead>
              <tbody>
                {(financ || []).map((f: any, i: number) => (
                  <tr key={i} className="table-row cursor-pointer" onClick={() => {
                    if (f.partido_id) { setSelected({ id: f.partido_id }); setTab('detalle') }
                  }}>
                    <td className="px-4 py-2.5">
                      <span className="inline-flex items-center gap-1.5">
                        <span className="w-3 h-3 rounded-full" style={{ background: f.partido_color || '#6b7280' }} />
                        <span className="text-white font-medium">{f.partido}</span>
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-gray-400">{f.anio}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-400 max-w-48 truncate">{f.concepto}</td>
                    <td className="px-4 py-2.5 text-right font-mono font-semibold text-white">{fmt(f.monto)}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-500">{f.fuente_pago}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-500">{f.banco_pago}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ─── GASTOS DECLARADOS ─── */}
      {tab === 'gastos' && (
        <div className="space-y-4">
          <div className="card bg-blue-950/20 border-blue-900/40 text-xs text-blue-300 p-3">
            Los partidos están obligados por la Ley 33-18 a declarar sus gastos ante la JCE dentro de los 60 días
            posteriores a cada año fiscal. El monto "sin rendir cuentas" es la diferencia entre lo recibido y lo declarado.
          </div>
          <div className="card p-0 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left">
                  <th className="px-4 py-3 text-gray-400">Partido</th>
                  <th className="px-4 py-3 text-gray-400">Año</th>
                  <th className="px-4 py-3 text-gray-400">Categoría</th>
                  <th className="px-4 py-3 text-gray-400 text-right">Monto</th>
                  <th className="px-4 py-3 text-gray-400">Proveedor</th>
                </tr>
              </thead>
              <tbody>
                {(gastos || []).map((g: any, i: number) => (
                  <tr key={i} className="table-row cursor-pointer" onClick={() => {
                    if (g.partido_id) { setSelected({ id: g.partido_id }); setTab('detalle') }
                  }}>
                    <td className="px-4 py-2.5">
                      <span className="inline-flex items-center gap-1.5">
                        <span className="w-3 h-3 rounded-full" style={{ background: g.partido_color || '#6b7280' }} />
                        <span className="text-white font-medium">{g.partido}</span>
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-gray-400">{g.anio}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-300">{g.categoria}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-white">{fmt(g.monto)}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-500">{g.proveedor || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ─── PROVEEDORES ─── */}
      {tab === 'proveedores' && (
        <div className="space-y-3">
          <p className="text-xs text-gray-500 px-1">
            Empresas que figuran en las rendiciones de cuentas de los partidos.
            Los marcados con ⚠ también tienen contratos con el Estado dominicano.
          </p>
          <div className="card p-0 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left">
                  <th className="px-4 py-3 text-gray-400">Proveedor</th>
                  <th className="px-4 py-3 text-gray-400">RNC</th>
                  <th className="px-4 py-3 text-gray-400 text-center">Facturas</th>
                  <th className="px-4 py-3 text-gray-400 text-right">Monto total</th>
                  <th className="px-4 py-3 text-gray-400 text-center">Partidos</th>
                  <th className="px-4 py-3 text-gray-400">Alerta</th>
                </tr>
              </thead>
              <tbody>
                {(proveedores || []).map((p: any, i: number) => (
                  <tr key={i}
                    onClick={() => p.empresa_id && navigate(`/companies/${p.empresa_id}`)}
                    className={`table-row ${p.empresa_id ? 'cursor-pointer' : ''} ${p.tambien_contratista_estado ? 'bg-yellow-950/10' : ''}`}>
                    <td className="px-4 py-2.5 text-white font-medium">{p.proveedor}</td>
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-500">{p.rnc || '—'}</td>
                    <td className="px-4 py-2.5 text-center text-gray-400">{p.num_facturas}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-white">{fmt(p.monto_total)}</td>
                    <td className="px-4 py-2.5 text-center">
                      <span className="badge-blue">{p.num_partidos}</span>
                    </td>
                    <td className="px-4 py-2.5">
                      {p.tambien_contratista_estado && (
                        <span className="text-xs text-yellow-400 flex items-center gap-1">
                          <AlertTriangle size={10} />
                          También contratista Estado · {fmt(p.monto_contratos_estado)}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
                {(!proveedores || proveedores.length === 0) && (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">Sin proveedores con RNC registrado aún</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ─── DETALLE PARTIDO ─── */}
      {tab === 'detalle' && (
        <div className="space-y-4">
          {/* Selector */}
          <div className="card flex flex-wrap gap-2">
            {(parties || []).map((p: any) => (
              <button
                key={p.id}
                onClick={() => setSelected(p)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${selectedParty?.id === p.id ? 'text-white' : 'text-gray-400 hover:text-white bg-gray-800'}`}
                style={{ background: selectedParty?.id === p.id ? p.color : undefined }}
              >
                {p.siglas}
              </button>
            ))}
          </div>

          {partyDetail && (
            <div className="space-y-4">
              {/* Header */}
              <div className="card" style={{ borderLeftColor: partyDetail.color, borderLeftWidth: 4 }}>
                <div className="flex items-start gap-4">
                  <div className="w-14 h-14 rounded-xl flex items-center justify-center font-bold text-lg text-white flex-shrink-0"
                       style={{ background: partyDetail.color }}>
                    {partyDetail.siglas?.slice(0,3)}
                  </div>
                  <div className="flex-1">
                    <h2 className="text-xl font-bold text-white">{partyDetail.nombre}</h2>
                    <p className="text-gray-500 text-sm">{IDEOLOGIA_LABEL[partyDetail.ideologia]} · Fundado {partyDetail.fecha_fundacion?.slice(0,4)} por {partyDetail.fundador}</p>
                    <p className="text-gray-400 text-sm mt-1">Presidente: {partyDetail.presidente_partido} · Sede: {partyDetail.sede_principal}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-2xl font-bold text-white">{partyDetail.votos_ultimas_elecciones?.toFixed(1)}%</p>
                    <p className="text-xs text-gray-500">votos {partyDetail.ano_ultimas_elecciones}</p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  ['Financiamiento total JCE', fmt(partyDetail.total_financiamiento_jce)],
                  ['Senadores', partyDetail.senadores],
                  ['Diputados', partyDetail.diputados],
                  ['Síndicos', partyDetail.sindicos],
                ].map(([k, v]) => (
                  <div key={k as string} className="card text-center py-3">
                    <p className="text-xs text-gray-500">{k as string}</p>
                    <p className="text-xl font-bold text-white mt-1">{v as string}</p>
                  </div>
                ))}
              </div>

              {/* Índice de transparencia */}
              <div className="card">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm text-white font-medium">Índice de Transparencia</p>
                  <p className={`text-lg font-bold ${partyDetail.indice_transparencia >= 70 ? 'text-green-400' : partyDetail.indice_transparencia >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {partyDetail.indice_transparencia}%
                  </p>
                </div>
                <div className="bg-gray-800 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all ${partyDetail.indice_transparencia >= 70 ? 'bg-green-500' : partyDetail.indice_transparencia >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${partyDetail.indice_transparencia}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  % del financiamiento público que tiene gastos declarados ante la JCE
                </p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Financiamientos */}
                <div className="card">
                  <h3 className="text-sm font-semibold text-white mb-3">Aportes del Estado</h3>
                  <div className="space-y-2">
                    {partyDetail.financiamientos?.map((f: any, i: number) => (
                      <div key={i} className="flex items-center justify-between p-2 bg-gray-800 rounded-lg text-xs">
                        <div>
                          <p className="text-gray-400">{f.anio} — {f.concepto?.slice(0,40)}</p>
                          <p className="text-gray-600">{f.banco} · JCE</p>
                        </div>
                        <p className="text-white font-mono font-medium">{fmt(f.monto)}</p>
                      </div>
                    ))}
                  </div>
                </div>
                {/* Gastos */}
                <div className="card">
                  <h3 className="text-sm font-semibold text-white mb-3">Gastos Declarados</h3>
                  {partyDetail.gastos?.length > 0 ? (
                    <div className="space-y-2">
                      {partyDetail.gastos?.map((g: any, i: number) => (
                        <div key={i} className="flex items-center justify-between p-2 bg-gray-800 rounded-lg text-xs">
                          <div>
                            <p className="text-gray-300">{g.categoria}</p>
                            <p className="text-gray-600">{g.anio} · {g.proveedor || 'sin proveedor'}</p>
                          </div>
                          <p className="text-white font-mono">{fmt(g.monto)}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-6 text-red-400 text-xs">
                      <AlertTriangle size={24} className="mx-auto mb-2 opacity-50" />
                      Sin gastos declarados ante la JCE
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {!selectedParty && (
            <div className="card text-center py-12 text-gray-500">
              <Flag size={40} className="mx-auto mb-3 opacity-30" />
              Selecciona un partido arriba para ver su detalle
            </div>
          )}
        </div>
      )}
    </div>
  )
}
