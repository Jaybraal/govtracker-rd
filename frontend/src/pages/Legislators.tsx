import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Search, Users, Landmark, MapPin, AlertTriangle, Gavel, Crown } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'
import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import { legislatorsApi, comisionesApi } from '../services/api'
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

const PIE_COLORS = ['#6366f1','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#f97316','#84cc16','#ec4899','#6b7280']

const CARGO_BADGE: Record<string, string> = {
  'Presidente/a':       'badge-yellow',
  'Vice-Presidente/a':  'badge-blue',
  'Secretario/a':       'badge-purple',
}

export default function Legislators() {
  const navigate = useNavigate()
  const [view, setView]       = useState<'legisladores' | 'comisiones'>('legisladores')
  const [page, setPage]       = useState(1)
  const [search, setSearch]   = useState('')
  const [camara, setCamara]   = useState('')
  const [partido, setPartido] = useState('')
  const [provincia, setProv]  = useState('')
  const [tipoComision, setTipoComision] = useState('')
  const [searchComision, setSearchComision] = useState('')

  const params = {
    page, size: 100,
    ...(search    && { search }),
    ...(camara    && { camara }),
    ...(partido   && { partido_siglas: partido }),
    ...(provincia && { provincia }),
  }

  const { data, loading } = useApi(() => legislatorsApi.list(params), [page, search, camara, partido, provincia])
  const { data: stats }   = useApi(() => legislatorsApi.stats(), [])
  const { data: conContr } = useApi(() => legislatorsApi.conContratosRelacionados(20), [])

  const comisionesParams = {
    ...(tipoComision   && { tipo: tipoComision }),
    ...(searchComision && { search: searchComision }),
  }
  const { data: comisiones, loading: loadingComisiones } = useApi(() => comisionesApi.list(comisionesParams), [tipoComision, searchComision])
  const { data: comisionesStats } = useApi(() => comisionesApi.stats(), [])
  const { data: directiva } = useApi(() => comisionesApi.directiva(), [])

  const partidosDiputados = (stats?.por_partido || [])
    .filter((p: any) => p.camara === 'diputados')
    .sort((a: any, b: any) => b.cantidad - a.cantidad)

  return (
    <div className="p-6 space-y-5">
      <PageHeader
        title="Congreso Nacional"
        subtitle={`Cámara de Diputados / Senado — Sistema de Información Legislativa (SIL), consulta en vivo · ${stats?.total_legisladores || 0} legisladores`}
      />

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-800">
        <button
          onClick={() => setView('legisladores')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${view === 'legisladores' ? 'border-gov-500 text-white' : 'border-transparent text-gray-500 hover:text-gray-300'}`}
        >
          Legisladores
        </button>
        <button
          onClick={() => setView('comisiones')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-1.5 ${view === 'comisiones' ? 'border-gov-500 text-white' : 'border-transparent text-gray-500 hover:text-gray-300'}`}
        >
          <Gavel size={14} /> Comisiones del Congreso
        </button>
      </div>

      {/* KPIs */}
      {view === 'legisladores' && stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total legisladores" value={stats.total_legisladores.toString()} icon={<Landmark size={16}/>} color="blue" />
          {stats.por_camara?.map((c: any) => (
            <StatCard key={c.camara} label={CAMARA_LABEL[c.camara] || c.camara} value={c.cantidad.toString()} icon={<Users size={16}/>} color="purple" />
          ))}
          <StatCard label="Con contratos relacionados" value={stats.con_contratos_relacionados.toString()} icon={<AlertTriangle size={16}/>} color="yellow" />
        </div>
      )}

      {/* Gráficos */}
      {view === 'legisladores' && stats && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div className="card">
            <h3 className="text-sm font-semibold text-white mb-4">Diputados por Partido</h3>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={partidosDiputados} layout="vertical" margin={{ left: 10, right: 20 }}>
                <XAxis type="number" tick={{ fill:'#6b7280', fontSize:10 }} />
                <YAxis type="category" dataKey="partido_siglas" tick={{ fill:'#9ca3af', fontSize:11 }} width={70} />
                <Tooltip
                  formatter={(v: number) => [v, 'Diputados']}
                  contentStyle={{ background:'#111827', border:'1px solid #374151', borderRadius:8 }}
                />
                <Bar dataKey="cantidad" fill="#6366f1" radius={[0,4,4,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
            <h3 className="text-sm font-semibold text-white mb-4">Distribución por Provincia</h3>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={stats.por_provincia?.slice(0, 8)}
                  dataKey="cantidad"
                  nameKey="provincia"
                  cx="50%" cy="50%"
                  outerRadius={85}
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

      {/* Legisladores con contratos relacionados (conflicto de interés) */}
      {view === 'legisladores' && conContr && conContr.length > 0 && (
        <div className="card border-yellow-900/40">
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <AlertTriangle size={14} className="text-yellow-400" />
            Legisladores con posibles vínculos a contratos del Estado
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="py-2 px-3 text-gray-400 text-left">Legislador</th>
                  <th className="py-2 px-3 text-gray-400 text-center">Cámara</th>
                  <th className="py-2 px-3 text-gray-400 text-center">Contratos</th>
                  <th className="py-2 px-3 text-gray-400 text-right">Monto relacionado</th>
                </tr>
              </thead>
              <tbody>
                {conContr.map((l: any) => (
                  <tr key={l.id} onClick={() => navigate(`/legislators/${l.id}`)} className="table-row cursor-pointer">
                    <td className="py-2 px-3">
                      <p className="text-white font-medium">{l.nombre_completo}</p>
                      <p className="text-gray-500 text-xs">{l.partido_siglas} · {l.provincia}</p>
                    </td>
                    <td className="py-2 px-3 text-center text-gray-400">{CAMARA_LABEL[l.camara]}</td>
                    <td className="py-2 px-3 text-center">
                      <span className="badge-yellow">{l.total_contratos_relacionados}</span>
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-yellow-400 font-semibold">
                      {fmt(l.total_monto_relacionado)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {view === 'legisladores' && (
        <>
          {/* Filtros */}
          <div className="card flex flex-wrap gap-3 items-center">
            <div className="relative flex-1 min-w-48">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input className="input pl-8" placeholder="Buscar legislador..." value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} />
            </div>
            <select className="input w-44" value={camara} onChange={e => { setCamara(e.target.value); setPage(1) }}>
              <option value="">Ambas cámaras</option>
              <option value="diputados">Diputados</option>
              <option value="senado">Senado</option>
            </select>
            <input className="input w-32" placeholder="Partido (siglas)..." value={partido} onChange={e => { setPartido(e.target.value.toUpperCase()); setPage(1) }} />
            <input className="input w-40" placeholder="Provincia..." value={provincia} onChange={e => { setProv(e.target.value); setPage(1) }} />
          </div>

          {/* Tabla */}
          <div className="card p-0 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left">
                  <th className="px-4 py-3 text-gray-400 font-medium">Legislador</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Cámara</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Partido</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Provincia</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Circunscripción</th>
                  <th className="px-4 py-3 text-gray-400 font-medium text-right">Vínculo contratos</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">Cargando...</td></tr>
                ) : data?.items.map((l: any) => (
                  <tr key={l.id} onClick={() => navigate(`/legislators/${l.id}`)} className={`table-row cursor-pointer ${l.total_contratos_relacionados > 0 ? 'bg-yellow-950/5' : ''}`}>
                    <td className="px-4 py-3">
                      <p className="text-white font-medium text-sm">{l.nombre_completo}</p>
                      <p className="text-xs text-gray-500">{l.funcion}</p>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-400">{CAMARA_LABEL[l.camara] || l.camara}</td>
                    <td className="px-4 py-3 text-xs text-gray-400">{l.partido_siglas || '—'}</td>
                    <td className="px-4 py-3 text-xs text-gray-400">
                      <span className="flex items-center gap-1">
                        <MapPin size={10} />
                        {l.provincia || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">{l.circunscripcion || '—'}</td>
                    <td className="px-4 py-3 text-right">
                      {l.total_contratos_relacionados > 0
                        ? <span className="text-yellow-400 font-semibold font-mono">{fmt(l.total_monto_relacionado)}</span>
                        : <span className="text-gray-700 text-xs">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Paginación */}
          {data && data.pages > 1 && (
            <div className="flex items-center justify-between text-sm text-gray-400">
              <span>{data.total.toLocaleString()} legisladores · Página {page} de {data.pages}</span>
              <div className="flex gap-2">
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn-ghost disabled:opacity-40">← Anterior</button>
                <button onClick={() => setPage(p => Math.min(data.pages, p + 1))} disabled={page === data.pages} className="btn-ghost disabled:opacity-40">Siguiente →</button>
              </div>
            </div>
          )}
        </>
      )}

      {view === 'comisiones' && (
        <>
          {/* Mesa Directiva */}
          {directiva && (
            <div className="card border-gov-900/40">
              <h3 className="text-sm font-semibold text-white mb-1 flex items-center gap-2">
                <Crown size={14} className="text-yellow-400" />
                Mesa Directiva — {directiva.nombre}
              </h3>
              <p className="text-xs text-gray-500 mb-3">
                {directiva.fecha_designacion ? `Designada ${new Date(directiva.fecha_designacion).toLocaleDateString('es-DO')} · ` : ''}
                {directiva.total_miembros} miembros
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {directiva.directiva?.map((m: any) => (
                  <div
                    key={m.id}
                    onClick={() => m.legislator_id && navigate(`/legislators/${m.legislator_id}`)}
                    className={`rounded-lg border border-gray-800 p-3 ${m.legislator_id ? 'cursor-pointer hover:border-gov-700' : ''}`}
                  >
                    <span className={CARGO_BADGE[m.cargo] || 'badge-blue'}>{m.cargo}</span>
                    <p className="text-white font-medium text-sm mt-2">{m.nombre_completo}</p>
                    <p className="text-gray-500 text-xs">{m.partido_siglas || '—'}</p>
                  </div>
                ))}
              </div>
              <div className="mt-3">
                <Link to={`/comisiones/${directiva.id}`} className="text-gov-400 hover:text-gov-300 text-xs">Ver todos los miembros →</Link>
              </div>
            </div>
          )}

          {/* KPIs */}
          {comisionesStats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Total comisiones" value={comisionesStats.total_comisiones.toString()} icon={<Gavel size={16}/>} color="blue" />
              <StatCard label="Total membresías" value={comisionesStats.total_membresias.toString()} icon={<Users size={16}/>} color="purple" />
              {comisionesStats.por_tipo?.slice(0, 2).map((t: any) => (
                <StatCard key={t.tipo} label={t.tipo} value={t.cantidad.toString()} icon={<Landmark size={16}/>} color="green" />
              ))}
            </div>
          )}

          {/* Filtros */}
          <div className="card flex flex-wrap gap-3 items-center">
            <div className="relative flex-1 min-w-48">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input className="input pl-8" placeholder="Buscar comisión..." value={searchComision} onChange={e => setSearchComision(e.target.value)} />
            </div>
            <select className="input w-56" value={tipoComision} onChange={e => setTipoComision(e.target.value)}>
              <option value="">Todos los tipos</option>
              {comisionesStats?.por_tipo?.map((t: any) => (
                <option key={t.tipo} value={t.tipo}>{t.tipo} ({t.cantidad})</option>
              ))}
            </select>
          </div>

          {/* Tabla */}
          <div className="card p-0 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left">
                  <th className="px-4 py-3 text-gray-400 font-medium">Comisión</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Tipo</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Presidente/a</th>
                  <th className="px-4 py-3 text-gray-400 font-medium text-right">Miembros</th>
                </tr>
              </thead>
              <tbody>
                {loadingComisiones ? (
                  <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-500">Cargando...</td></tr>
                ) : comisiones?.map((c: any) => {
                  const presidente = c.directiva?.find((m: any) => m.cargo === 'Presidente/a')
                  return (
                    <tr key={c.id} onClick={() => navigate(`/comisiones/${c.id}`)} className="table-row cursor-pointer">
                      <td className="px-4 py-3">
                        <p className="text-white font-medium text-sm">{c.nombre}</p>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-400">{c.tipo}</td>
                      <td className="px-4 py-3 text-xs text-gray-400">{presidente?.nombre_completo || '—'}</td>
                      <td className="px-4 py-3 text-right text-xs text-gray-400">{c.total_miembros}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
