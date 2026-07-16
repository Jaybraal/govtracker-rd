import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend,
} from 'recharts'
import { Wallet, TrendingDown, AlertTriangle, Building2 } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import { useApi } from '../hooks/useApi'
import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 60000 })

const fmtRD = (n: number) => {
  if (n == null) return 'sin dato'
  if (Math.abs(n) >= 1_000_000_000) return `RD$${(n / 1_000_000_000).toFixed(2)}B`
  if (Math.abs(n) >= 1_000_000) return `RD$${(n / 1_000_000).toFixed(1)}M`
  return `RD$${Math.round(n).toLocaleString('es-DO')}`
}

const FINALIDAD_COLOR: Record<string, string> = {
  'SERVICIOS SOCIALES': '#10b981',
  'SERVICIOS ECONÓMICOS': '#6366f1',
  'INTERESES DE LA DEUDA PÚBLICA': '#ef4444',
  'SERVICIOS  GENERALES': '#f59e0b',
  'PROTECCIÓN DEL MEDIO AMBIENTE': '#06b6d4',
}

type Tab = 'resumen' | 'instituciones' | 'funcion' | 'baja-ejecucion'

function useStats() {
  return useApi(() => api.get('/gasto-ejecutado/stats').then(r => r.data), [])
}
function useSerieHistorica() {
  return useApi(() => api.get('/gasto-ejecutado/serie-historica').then(r => r.data), [])
}
function usePorInstitucion(anio: number | '', page: number) {
  return useApi(() => api.get('/gasto-ejecutado/por-institucion', {
    params: { ...(anio && { anio }), page, size: 50 },
  }).then(r => r.data), [anio, page])
}
function usePorFuncion(anio: number | '') {
  return useApi(() => api.get('/gasto-ejecutado/por-funcion', {
    params: { ...(anio && { anio }) },
  }).then(r => r.data), [anio])
}
function useBajaEjecucion(anio: number | '') {
  return useApi(() => api.get('/gasto-ejecutado/baja-ejecucion', {
    params: { ...(anio && { anio }), umbral: 0.5 },
  }).then(r => r.data), [anio])
}
function useDetalle(institucionNorm: string | null, anio: number | '') {
  return useApi(
    () => institucionNorm
      ? api.get('/gasto-ejecutado/detalle', { params: { institucion_norm: institucionNorm, ...(anio && { anio }) } }).then(r => r.data)
      : Promise.resolve(null),
    [institucionNorm, anio],
  )
}

const MESES = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

function DetalleGastoModal({ institucionNorm, anioInicial, onClose }: { institucionNorm: string; anioInicial: number | ''; onClose: () => void }) {
  const [anio, setAnio] = useState<number | ''>(anioInicial)
  const { data, loading } = useDetalle(institucionNorm, anio)

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="card max-w-3xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <h3 className="text-sm font-semibold text-white">{data?.institucion ?? '...'}</h3>
            <p className="text-xs text-gray-500 mt-0.5">Detalle de gasto devengado por programa/actividad y mes</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <select className="input w-28 text-xs" value={anio} onChange={e => setAnio(e.target.value ? +e.target.value : '')}>
              <option value="">Todos los años</option>
              {[2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017].map(a => <option key={a} value={a}>{a}</option>)}
            </select>
            <button onClick={onClose} className="text-gray-500 hover:text-white text-sm">✕</button>
          </div>
        </div>
        {loading ? (
          <div className="p-8 text-center text-gray-500">Cargando...</div>
        ) : (
          <div className="space-y-1.5">
            {data?.results?.map((r: any, i: number) => (
              <div key={i} className="flex items-center justify-between gap-3 bg-gray-800/50 rounded-lg px-3 py-2">
                <div className="min-w-0">
                  <p className="text-white text-sm truncate" title={r.actividad}>{r.actividad || r.programa}</p>
                  <p className="text-gray-500 text-xs truncate" title={r.programa}>{r.programa}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-emerald-400 font-mono text-sm">{fmtRD(r.devengado)}</p>
                  <p className="text-gray-500 text-xs">{MESES[r.mes]} {r.anio}</p>
                </div>
              </div>
            ))}
            {(!data?.results || data.results.length === 0) && (
              <p className="text-center text-gray-500 py-8 text-sm">Sin movimientos para este filtro</p>
            )}
          </div>
        )}
        <p className="text-xs text-gray-600 mt-3">{data?.caveat}</p>
      </div>
    </div>
  )
}

function Pager({ page, total, size, onChange }: { page: number; total: number; size: number; onChange: (p: number) => void }) {
  const pages = Math.ceil(total / size)
  if (pages <= 1) return null
  return (
    <div className="flex items-center justify-between text-sm text-gray-500 pt-3">
      <span>{total.toLocaleString()} resultados</span>
      <div className="flex items-center gap-2">
        <button disabled={page <= 1} onClick={() => onChange(page - 1)} className="px-2 py-1 rounded hover:bg-gray-800 disabled:opacity-30">←</button>
        <span className="text-gray-400">{page} / {pages}</span>
        <button disabled={page >= pages} onClick={() => onChange(page + 1)} className="px-2 py-1 rounded hover:bg-gray-800 disabled:opacity-30">→</button>
      </div>
    </div>
  )
}

function CaveatBanner({ text }: { text?: string }) {
  return (
    <div className="px-4 py-3 bg-blue-950/30 border border-blue-900/30 rounded-lg flex items-start gap-2">
      <AlertTriangle size={16} className="text-blue-400 shrink-0 mt-0.5" />
      <span className="text-sm text-blue-300">
        {text ?? "Fuente: Ministerio de Hacienda y Economía — Estadísticas de Ejecución de los Gastos. 'Devengado' es lo realmente ejecutado, no lo presupuestado."}
      </span>
    </div>
  )
}

// ── Tab: Resumen ────────────────────────────────────────────
function TabResumen() {
  const { data: stats } = useStats()
  const { data: serie } = useSerieHistorica()

  return (
    <div className="space-y-4">
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Gasto ejecutado total (2017-2025)" value={fmtRD(stats.total_devengado)} icon={<Wallet size={16} />} color="green" />
          <StatCard label="Presupuesto vigente total" value={fmtRD(stats.total_presupuesto_vigente)} icon={<Building2 size={16} />} color="blue" />
          <StatCard label="% ejecución global" value={`${(100 * stats.total_devengado / stats.total_presupuesto_vigente).toFixed(1)}%`} icon={<TrendingDown size={16} />} color="purple" />
          <StatCard label="Instituciones reportantes" value={stats.num_instituciones.toString()} icon={<Building2 size={16} />} color="yellow" />
        </div>
      )}
      {stats && <CaveatBanner text={stats.caveat} />}
      {serie && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-4">Gasto Ejecutado vs. Presupuesto Vigente por Año</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={serie.results}>
              <XAxis dataKey="anio" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis tickFormatter={v => `${(v / 1e9).toFixed(0)}B`} tick={{ fill: '#6b7280', fontSize: 10 }} />
              <Tooltip formatter={(v: number) => fmtRD(v)} contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }} />
              <Bar dataKey="presupuesto_vigente" name="Presupuesto vigente" fill="#374151" radius={[4, 4, 0, 0]} />
              <Bar dataKey="devengado" name="Devengado (ejecutado)" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-2 text-xs text-gray-500">
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-gray-700" /> Presupuesto vigente</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-emerald-500" /> Devengado (ejecutado)</span>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Tab: Por Institución ──────────────────────────────────────
function TabInstituciones({ anios }: { anios: number[] }) {
  const [anio, setAnio] = useState<number | ''>('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<string | null>(null)
  const { data, loading } = usePorInstitucion(anio, page)

  return (
    <div className="space-y-4">
      <div className="card flex items-center gap-3">
        <select className="input w-32" value={anio} onChange={e => { setAnio(e.target.value ? +e.target.value : ''); setPage(1) }}>
          <option value="">Todos los años (2017-2025)</option>
          {anios.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        {data && <span className="text-sm text-gray-500">{data.total} instituciones</span>}
      </div>
      <div className="card p-0 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Cargando...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase">
                  <th className="px-4 py-3 text-left w-8">#</th>
                  <th className="px-4 py-3 text-left">Institución</th>
                  <th className="px-4 py-3 text-right">Presupuesto vigente</th>
                  <th className="px-4 py-3 text-right">Devengado (ejecutado)</th>
                  <th className="px-4 py-3 text-right">% ejecución</th>
                </tr>
              </thead>
              <tbody>
                {data?.results?.map((r: any, i: number) => (
                  <tr key={i}
                    onClick={() => setSelected(r.institucion_norm)}
                    className="border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer">
                    <td className="px-4 py-3 text-gray-600">{(page - 1) * 50 + i + 1}</td>
                    <td className="px-4 py-3 font-medium text-white max-w-[300px] truncate" title={r.institucion}>
                      {r.institucion}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gray-400">{fmtRD(r.presupuesto_vigente)}</td>
                    <td className="px-4 py-3 text-right font-mono font-bold text-emerald-400">{fmtRD(r.devengado)}</td>
                    <td className="px-4 py-3 text-right">
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        r.pct_ejecucion == null ? 'bg-gray-800 text-gray-500'
                        : r.pct_ejecucion < 50 ? 'bg-red-900/40 text-red-300'
                        : r.pct_ejecucion < 80 ? 'bg-yellow-900/40 text-yellow-300'
                        : 'bg-green-900/40 text-green-300'
                      }`}>
                        {r.pct_ejecucion != null ? `${r.pct_ejecucion}%` : '—'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="px-4 pb-3">
          <Pager page={page} total={data?.total ?? 0} size={50} onChange={setPage} />
        </div>
      </div>

      {selected && (
        <DetalleGastoModal institucionNorm={selected} anioInicial={anio} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}

// ── Tab: Por Función ──────────────────────────────────────────
function TabFuncion({ anios }: { anios: number[] }) {
  const [anio, setAnio] = useState<number | ''>('')
  const { data, loading } = usePorFuncion(anio)

  return (
    <div className="space-y-4">
      <div className="card flex items-center gap-3">
        <select className="input w-32" value={anio} onChange={e => setAnio(e.target.value ? +e.target.value : '')}>
          <option value="">Todos los años</option>
          {anios.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        <span className="text-sm text-gray-500">Clasificación funcional del gasto (6 categorías oficiales)</span>
      </div>
      {loading ? (
        <div className="card p-8 text-center text-gray-500">Cargando...</div>
      ) : data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="card">
            <h3 className="text-sm font-semibold text-white mb-4">Devengado por Categoría</h3>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={data.results} dataKey="devengado" nameKey="finalidad" cx="50%" cy="50%" outerRadius={95}
                  label={({ finalidad, percent }: any) => `${(percent * 100).toFixed(0)}%`}>
                  {data.results.map((r: any, i: number) => (
                    <Cell key={i} fill={FINALIDAD_COLOR[r.finalidad] || '#6b7280'} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => fmtRD(v)} contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="card p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase">
                  <th className="px-4 py-3 text-left">Categoría</th>
                  <th className="px-4 py-3 text-right">Devengado</th>
                  <th className="px-4 py-3 text-right">% del total</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((r: any, i: number) => {
                  const totalDev = data.results.reduce((s: number, x: any) => s + x.devengado, 0)
                  return (
                    <tr key={i} className="border-b border-gray-800/50">
                      <td className="px-4 py-3 font-medium text-white">
                        <span className="inline-block w-2.5 h-2.5 rounded-full mr-2" style={{ background: FINALIDAD_COLOR[r.finalidad] || '#6b7280' }} />
                        {r.finalidad}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-emerald-400">{fmtRD(r.devengado)}</td>
                      <td className="px-4 py-3 text-right text-gray-400">{((100 * r.devengado) / totalDev).toFixed(1)}%</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Tab: Baja Ejecución ────────────────────────────────────────
function TabBajaEjecucion({ anios }: { anios: number[] }) {
  const [anio, setAnio] = useState<number | ''>(anios[anios.length - 1] ?? '')
  const [selected, setSelected] = useState<string | null>(null)
  const { data, loading } = useBajaEjecucion(anio)

  return (
    <div className="space-y-4">
      <div className="card flex items-center gap-3">
        <select className="input w-32" value={anio} onChange={e => setAnio(e.target.value ? +e.target.value : '')}>
          <option value="">Todos los años</option>
          {anios.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        <span className="text-sm text-gray-500">Instituciones que ejecutaron menos del 50% de su presupuesto vigente</span>
      </div>
      <CaveatBanner text="En este dataset el gasto Devengado nunca supera el Presupuesto Vigente (el vigente ya incorpora las modificaciones del año) — por eso no existe 'sobre-ejecución' aquí. La señal real es la baja ejecución: dinero aprobado que la institución no llegó a gastar." />
      <div className="card p-0 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Cargando...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase">
                  <th className="px-4 py-3 text-left">Institución</th>
                  <th className="px-4 py-3 text-center">Año</th>
                  <th className="px-4 py-3 text-right">Presupuesto vigente</th>
                  <th className="px-4 py-3 text-right">Devengado</th>
                  <th className="px-4 py-3 text-right">Sin ejecutar</th>
                  <th className="px-4 py-3 text-right">% ejecución</th>
                </tr>
              </thead>
              <tbody>
                {data?.results?.map((r: any, i: number) => (
                  <tr key={i}
                    onClick={() => setSelected(r.institucion_norm)}
                    className="border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer">
                    <td className="px-4 py-3 font-medium text-white max-w-[260px] truncate" title={r.institucion}>
                      {r.institucion}
                    </td>
                    <td className="px-4 py-3 text-center text-gray-400">{r.anio}</td>
                    <td className="px-4 py-3 text-right font-mono text-gray-400">{fmtRD(r.presupuesto_vigente)}</td>
                    <td className="px-4 py-3 text-right font-mono text-white">{fmtRD(r.devengado)}</td>
                    <td className="px-4 py-3 text-right font-mono text-red-400">{fmtRD(r.sin_ejecutar)}</td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-xs px-2 py-0.5 rounded bg-red-900/40 text-red-300">{r.pct_ejecucion}%</span>
                    </td>
                  </tr>
                ))}
                {(!data?.results || data.results.length === 0) && (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">Sin resultados para este filtro</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selected && (
        <DetalleGastoModal institucionNorm={selected} anioInicial={anio} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────
const TABS: { id: Tab; label: string; icon: typeof Wallet }[] = [
  { id: 'resumen',         label: 'Resumen',          icon: Wallet },
  { id: 'instituciones',   label: 'Por Institución',  icon: Building2 },
  { id: 'funcion',         label: 'Por Categoría',    icon: TrendingDown },
  { id: 'baja-ejecucion',  label: 'Baja Ejecución',   icon: AlertTriangle },
]

export default function GastoEjecutado() {
  const [tab, setTab] = useState<Tab>('resumen')
  const { data: stats } = useStats()
  const anios: number[] = stats?.anios_disponibles ?? []

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title="Gasto Ejecutado del Estado"
        subtitle="Lo que el gobierno reporta a Hacienda como realmente gastado (Devengado) — Ministerio de Hacienda y Economía, 2017-2025"
      />

      <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-xl p-1 flex-wrap">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setTab(id)}
            className={`flex items-center gap-2 flex-1 min-w-32 justify-center py-2 px-2 rounded-lg text-xs transition-all ${tab === id ? 'bg-gov-700 text-white font-medium' : 'text-gray-400 hover:text-white'}`}>
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {tab === 'resumen'        && <TabResumen />}
      {tab === 'instituciones'  && <TabInstituciones anios={anios} />}
      {tab === 'funcion'        && <TabFuncion anios={anios} />}
      {tab === 'baja-ejecucion' && <TabBajaEjecucion anios={anios} />}
    </div>
  )
}
