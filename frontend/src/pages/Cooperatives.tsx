import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Search, Users, TrendingUp, Building2, MapPin } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'
import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import { cooperativesApi } from '../services/api'
import { useApi } from '../hooks/useApi'

const fmt = (n: number) => {
  if (!n) return 'RD$0'
  if (n >= 1e9) return `RD$${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6) return `RD$${(n / 1e6).toFixed(0)}M`
  return `RD$${n.toLocaleString()}`
}

const TIPO_LABEL: Record<string, string> = {
  ahorro_credito:       '💰 Ahorro y Crédito',
  agropecuaria:         '🌾 Agropecuaria',
  consumo:              '🛒 Consumo',
  vivienda:             '🏠 Vivienda',
  servicios_multiples:  '🔧 Servicios Múltiples',
  escolar:              '📚 Escolar/Universitaria',
  transporte:           '🚌 Transporte',
  salud:                '🏥 Salud',
  produccion:           '🏭 Producción',
  otro:                 '📦 Otro',
}

const PIE_COLORS = ['#6366f1','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#f97316','#84cc16','#ec4899','#6b7280']

const TIPOS = Object.keys(TIPO_LABEL)

export default function Cooperatives() {
  const navigate = useNavigate()
  const [page, setPage]       = useState(1)
  const [search, setSearch]   = useState('')
  const [tipo, setTipo]       = useState('')
  const [provincia, setProv]  = useState('')
  const [conContrato, setConContrato] = useState<'' | 'si' | 'no'>('')
  const [viewMode, setViewMode] = useState<'tabla' | 'tarjetas' | 'mapa'>('tabla')

  const params = {
    page, size: 100,
    ...(search    && { search }),
    ...(tipo      && { tipo }),
    ...(provincia && { provincia }),
    ...(conContrato === 'si'  && { con_contratos: true }),
    ...(conContrato === 'no'  && { con_contratos: false }),
  }

  const { data, loading }  = useApi(() => cooperativesApi.list(params),  [page, search, tipo, provincia, conContrato])
  const { data: stats }    = useApi(() => cooperativesApi.stats(),        [])
  const { data: conContr } = useApi(() => cooperativesApi.conContratosEstado(20), [])

  return (
    <div className="p-6 space-y-5">
      <PageHeader
        title="Cooperativas de República Dominicana"
        subtitle={`Registro completo IDECOOP — ${stats?.total_cooperativas || 0} cooperativas`}
      />

      {/* KPIs */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Cooperativas" value={stats.total_cooperativas.toLocaleString()} icon={<Building2 size={16}/>} color="blue" />
          <StatCard label="Socios Totales"     value={Number(stats.total_socios).toLocaleString()} icon={<Users size={16}/>} color="green" />
          <StatCard label="Activos Totales"    value={fmt(stats.total_activos_dop)} icon={<TrendingUp size={16}/>} color="purple" />
          <StatCard label="Con Contratos Estado" value={stats.con_contratos_estado.toString()} icon={<Building2 size={16}/>} color="yellow" />
        </div>
      )}

      {/* Gráficos */}
      {stats && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Por tipo */}
          <div className="card">
            <h3 className="text-sm font-semibold text-white mb-4">Cooperativas por Tipo</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={stats.por_tipo} layout="vertical" margin={{ left: 10, right: 20 }}>
                <XAxis type="number" tick={{ fill:'#6b7280', fontSize:10 }} tickFormatter={v => v.toString()} />
                <YAxis type="category" dataKey="tipo"
                  tickFormatter={v => (TIPO_LABEL[v] || v).replace(/[^\w\s]/g,'').trim().slice(0,18)}
                  tick={{ fill:'#9ca3af', fontSize:10 }} width={120} />
                <Tooltip
                  formatter={(v: number, name: string) => [v, name === 'cnt' ? 'Cantidad' : 'Activos']}
                  contentStyle={{ background:'#111827', border:'1px solid #374151', borderRadius:8 }}
                />
                <Bar dataKey="cnt" fill="#6366f1" radius={[0,4,4,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Por provincia */}
          <div className="card">
            <h3 className="text-sm font-semibold text-white mb-4">Distribución por Provincia</h3>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={stats.por_provincia?.slice(0, 8)}
                  dataKey="cantidad"
                  nameKey="provincia"
                  cx="50%" cy="50%"
                  outerRadius={80}
                  label={({ provincia: p, percent }: any) => `${p?.slice(0,10)} ${(percent*100).toFixed(0)}%`}
                  labelLine={{ stroke:'#4b5563' }}
                >
                  {stats.por_provincia?.slice(0,8).map((_: any, i: number) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background:'#111827', border:'1px solid #374151', borderRadius:8 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Cooperativas con contratos del Estado */}
      {conContr && conContr.length > 0 && (
        <div className="card border-yellow-900/40">
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <TrendingUp size={14} className="text-yellow-400" />
            Cooperativas con Contratos del Estado (Top 20)
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="py-2 px-3 text-gray-400 text-left">Cooperativa</th>
                  <th className="py-2 px-3 text-gray-400 text-center">Tipo</th>
                  <th className="py-2 px-3 text-gray-400 text-center">Contratos</th>
                  <th className="py-2 px-3 text-gray-400 text-right">Monto Estado</th>
                  <th className="py-2 px-3 text-gray-400 text-right">Activos Propios</th>
                </tr>
              </thead>
              <tbody>
                {conContr.map((c: any) => (
                  <tr key={c.id} onClick={() => navigate(`/cooperatives/${c.id}`)} className="table-row cursor-pointer">
                    <td className="py-2 px-3">
                      <p className="text-white font-medium">{c.siglas || c.nombre.slice(0, 30)}</p>
                      <p className="text-gray-500 text-xs truncate max-w-48">{c.provincia}</p>
                    </td>
                    <td className="py-2 px-3 text-center text-gray-500">
                      {TIPO_LABEL[c.tipo]?.split(' ')[0] || '—'}
                    </td>
                    <td className="py-2 px-3 text-center">
                      <span className="badge-yellow">{c.total_contratos_estado}</span>
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-yellow-400 font-semibold">
                      {fmt(c.total_monto_contratos)}
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-gray-400">
                      {fmt(c.activos_totales)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Filtros */}
      <div className="card flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input className="input pl-8" placeholder="Buscar cooperativa..." value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} />
        </div>
        <select className="input w-48" value={tipo} onChange={e => { setTipo(e.target.value); setPage(1) }}>
          <option value="">Todos los tipos</option>
          {TIPOS.map(t => <option key={t} value={t}>{TIPO_LABEL[t]}</option>)}
        </select>
        <input className="input w-40" placeholder="Provincia..." value={provincia} onChange={e => { setProv(e.target.value); setPage(1) }} />
        <select className="input w-44" value={conContrato} onChange={e => { setConContrato(e.target.value as any); setPage(1) }}>
          <option value="">Todas</option>
          <option value="si">Con contratos Estado</option>
          <option value="no">Sin contratos Estado</option>
        </select>
        {/* Toggle vista */}
        <div className="flex gap-1 bg-gray-800 rounded-lg p-1 ml-auto">
          {(['tabla', 'tarjetas'] as const).map(v => (
            <button key={v} onClick={() => setViewMode(v)}
              className={`px-3 py-1 rounded-md text-xs transition-all ${viewMode === v ? 'bg-gov-700 text-white' : 'text-gray-400 hover:text-white'}`}>
              {v === 'tabla' ? 'Lista' : 'Tarjetas'}
            </button>
          ))}
        </div>
      </div>

      {/* ─── VISTA TABLA ─── */}
      {viewMode === 'tabla' && (
        <div className="card p-0 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-left">
                <th className="px-4 py-3 text-gray-400 font-medium">Cooperativa</th>
                <th className="px-4 py-3 text-gray-400 font-medium">Tipo</th>
                <th className="px-4 py-3 text-gray-400 font-medium">Provincia</th>
                <th className="px-4 py-3 text-gray-400 font-medium text-center">Socios</th>
                <th className="px-4 py-3 text-gray-400 font-medium text-right">Activos</th>
                <th className="px-4 py-3 text-gray-400 font-medium text-right">Contratos Estado</th>
                <th className="px-4 py-3 text-gray-400 font-medium text-right">Monto Estado</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">Cargando...</td></tr>
              ) : data?.items.map((c: any) => (
                <tr key={c.id} onClick={() => navigate(`/cooperatives/${c.id}`)} className={`table-row cursor-pointer ${c.total_contratos_estado > 0 ? 'bg-yellow-950/5' : ''}`}>
                  <td className="px-4 py-3">
                    <p className="text-white font-medium text-sm">{c.siglas || ''}</p>
                    <p className="text-xs text-gray-500 max-w-64 truncate">{c.nombre}</p>
                    {c.rnc && <p className="text-xs text-gray-600 font-mono">RNC: {c.rnc}</p>}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">{TIPO_LABEL[c.tipo] || c.tipo}</td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <MapPin size={10} />
                      {c.provincia || '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-gray-300">{c.num_socios?.toLocaleString() || '—'}</td>
                  <td className="px-4 py-3 text-right font-mono text-white">{fmt(c.activos_totales)}</td>
                  <td className="px-4 py-3 text-center">
                    {c.total_contratos_estado > 0
                      ? <span className="badge-yellow">{c.total_contratos_estado}</span>
                      : <span className="text-gray-700 text-xs">—</span>}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    {c.total_monto_contratos > 0
                      ? <span className="text-yellow-400 font-semibold">{fmt(c.total_monto_contratos)}</span>
                      : <span className="text-gray-700">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ─── VISTA TARJETAS ─── */}
      {viewMode === 'tarjetas' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {loading ? (
            <div className="col-span-3 text-center text-gray-500 py-8">Cargando...</div>
          ) : data?.items.map((c: any) => (
            <div key={c.id} onClick={() => navigate(`/cooperatives/${c.id}`)} className={`card hover:border-gov-700 transition-colors cursor-pointer ${c.total_contratos_estado > 0 ? 'border-yellow-900/50' : ''}`}>
              <div className="flex items-start justify-between mb-2">
                <div className="w-10 h-10 bg-gov-700/20 rounded-lg flex items-center justify-center text-gov-400 font-bold text-xs text-center leading-tight p-1">
                  {(c.siglas || c.nombre.slice(0,4)).slice(0,6)}
                </div>
                <span className="text-xs text-gray-500">{TIPO_LABEL[c.tipo]?.split(' ')[0]}</span>
              </div>
              <h3 className="text-sm font-semibold text-white mt-2 line-clamp-2">{c.nombre}</h3>
              <p className="text-xs text-gray-500 flex items-center gap-1 mt-1">
                <MapPin size={10} /> {c.provincia || '—'}
              </p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div>
                  <p className="text-gray-500">Socios</p>
                  <p className="text-white font-medium">{c.num_socios?.toLocaleString() || '—'}</p>
                </div>
                <div>
                  <p className="text-gray-500">Activos</p>
                  <p className="text-white font-medium">{fmt(c.activos_totales)}</p>
                </div>
              </div>
              {c.total_contratos_estado > 0 && (
                <div className="mt-3 pt-2 border-t border-gray-800">
                  <p className="text-xs text-yellow-400 font-medium">
                    💼 {c.total_contratos_estado} contrato{c.total_contratos_estado > 1 ? 's' : ''} · {fmt(c.total_monto_contratos)}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Paginación */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-400">
          <span>{data.total.toLocaleString()} cooperativas · Página {page} de {data.pages}</span>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn-ghost disabled:opacity-40">← Anterior</button>
            <button onClick={() => setPage(p => Math.min(data.pages, p + 1))} disabled={page === data.pages} className="btn-ghost disabled:opacity-40">Siguiente →</button>
          </div>
        </div>
      )}
    </div>
  )
}
