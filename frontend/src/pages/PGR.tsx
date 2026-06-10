import { useState } from 'react'
import { Search, Shield, AlertTriangle, FileText, ChevronLeft, ChevronRight, ExternalLink, Play } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { useApi } from '../hooks/useApi'
import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 60000 })

type Tab = 'comunicados' | 'operaciones' | 'buscar'

const TIPO_COLORS: Record<string, string> = {
  operacion:      'bg-red-900/40 text-red-300 border border-red-700/40',
  condena:        'bg-green-900/40 text-green-300 border border-green-700/40',
  acusacion:      'bg-orange-900/40 text-orange-300 border border-orange-700/40',
  aprehension:    'bg-yellow-900/40 text-yellow-300 border border-yellow-700/40',
  requerimiento:  'bg-purple-900/40 text-purple-300 border border-purple-700/40',
  comunicado:     'bg-blue-900/40 text-blue-300 border border-blue-700/40',
  general:        'bg-gray-800 text-gray-400 border border-gray-700/40',
}

function useStats() {
  return useApi(() => api.get('/pgr/stats').then(r => r.data).catch(() => null), [])
}
function useComunicados(tipo: string, operacion: string, page: number) {
  return useApi(() => api.get('/pgr/comunicados', {
    params: {
      ...(tipo && { tipo }),
      ...(operacion && { operacion }),
      page,
      size: 50,
    },
  }).then(r => r.data), [tipo, operacion, page])
}
function useOperaciones() {
  return useApi(() => api.get('/pgr/operaciones').then(r => r.data), [])
}
function useBuscar(q: string, page: number) {
  return useApi(
    () => q.length >= 3
      ? api.get('/pgr/buscar', { params: { q, page, size: 50 } }).then(r => r.data)
      : Promise.resolve(null),
    [q, page],
  )
}

function Pager({ page, total, size, onChange }: { page: number; total: number; size: number; onChange: (p: number) => void }) {
  const pages = Math.ceil(total / size)
  if (pages <= 1) return null
  return (
    <div className="flex items-center justify-between text-sm text-gray-500 pt-3">
      <span>{total.toLocaleString()} resultados</span>
      <div className="flex items-center gap-2">
        <button disabled={page <= 1} onClick={() => onChange(page - 1)}
          className="p-1 rounded hover:bg-gray-800 disabled:opacity-30">
          <ChevronLeft size={16} />
        </button>
        <span className="text-gray-400">{page} / {pages}</span>
        <button disabled={page >= pages} onClick={() => onChange(page + 1)}
          className="p-1 rounded hover:bg-gray-800 disabled:opacity-30">
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )
}

function TipoBadge({ tipo }: { tipo: string }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-medium ${TIPO_COLORS[tipo] ?? TIPO_COLORS.general}`}>
      {tipo}
    </span>
  )
}

// ── Tab: Comunicados ──────────────────────────────────────────
function TabComunicados({ tiposDisponibles }: { tiposDisponibles: string[] }) {
  const [tipo, setTipo] = useState('')
  const [operacion, setOperacion] = useState('')
  const [page, setPage] = useState(1)
  const { data, loading } = useComunicados(tipo, operacion, page)

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap gap-3 items-center">
        <select className="input w-36" value={tipo} onChange={e => { setTipo(e.target.value); setPage(1) }}>
          <option value="">Todos los tipos</option>
          {tiposDisponibles.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <input
          className="input flex-1 min-w-48"
          placeholder="Filtrar por operación (ej: Cobra)"
          value={operacion}
          onChange={e => { setOperacion(e.target.value); setPage(1) }}
        />
        {data && <span className="text-sm text-gray-500">{data.total.toLocaleString()} comunicados</span>}
      </div>

      <div className="card p-0 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Cargando...</div>
        ) : !data?.results?.length ? (
          <div className="p-8 text-center text-gray-500">
            Sin resultados. Ejecuta el scraper primero desde el panel ETL.
          </div>
        ) : (
          <div className="divide-y divide-gray-800/60">
            {data.results.map((r: any) => (
              <div key={r.id} className="px-4 py-3 hover:bg-gray-800/30 transition-colors">
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <TipoBadge tipo={r.tipo} />
                      {r.operacion && (
                        <span className="text-xs bg-indigo-900/40 text-indigo-300 border border-indigo-700/40 px-2 py-0.5 rounded">
                          {r.operacion}
                        </span>
                      )}
                      {r.fecha && (
                        <span className="text-xs text-gray-500">{r.fecha}</span>
                      )}
                    </div>
                    <a href={r.url} target="_blank" rel="noopener noreferrer"
                      className="text-white font-medium text-sm hover:text-gov-400 transition-colors line-clamp-2">
                      {r.titulo}
                    </a>
                    {r.resumen && (
                      <p className="text-gray-400 text-xs mt-1 line-clamp-2">{r.resumen}</p>
                    )}
                    <div className="flex flex-wrap gap-3 mt-1">
                      {r.montos && (
                        <span className="text-xs text-emerald-400 font-mono">{r.montos.split(';')[0]}</span>
                      )}
                      {r.imputados && (
                        <span className="text-xs text-gray-500 truncate max-w-xs" title={r.imputados}>
                          👤 {r.imputados.split(';').slice(0, 2).join(', ')}
                        </span>
                      )}
                    </div>
                  </div>
                  <a href={r.url} target="_blank" rel="noopener noreferrer"
                    className="shrink-0 text-gray-600 hover:text-gray-300 mt-1">
                    <ExternalLink size={14} />
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="px-4 pb-3">
          <Pager page={page} total={data?.total ?? 0} size={50} onChange={setPage} />
        </div>
      </div>
    </div>
  )
}

// ── Tab: Operaciones ──────────────────────────────────────────
function TabOperaciones() {
  const { data, loading } = useOperaciones()
  return (
    <div className="space-y-4">
      <div className="card p-0 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Cargando...</div>
        ) : !data?.results?.length ? (
          <div className="p-8 text-center text-gray-500">
            Sin operaciones detectadas. Ejecuta el scraper desde el panel ETL.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase">
                  <th className="px-4 py-3 text-left">Operación / Caso</th>
                  <th className="px-4 py-3 text-right">Comunicados</th>
                  <th className="px-4 py-3 text-center">Período</th>
                  <th className="px-4 py-3 text-left">Tipos</th>
                  <th className="px-4 py-3 text-left">Montos mencionados</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((r: any, i: number) => (
                  <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="px-4 py-3 font-medium text-white">
                      <span className="bg-red-900/30 text-red-300 border border-red-800/40 px-2 py-0.5 rounded text-xs">
                        {r.operacion}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-white font-bold">{r.total_comunicados}</span>
                    </td>
                    <td className="px-4 py-3 text-center text-gray-400 text-xs whitespace-nowrap">
                      {r.primera_fecha && r.ultima_fecha
                        ? r.primera_fecha === r.ultima_fecha
                          ? r.primera_fecha
                          : `${r.primera_fecha} → ${r.ultima_fecha}`
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">
                      {r.tipos?.split(',').map((t: string) => (
                        <TipoBadge key={t} tipo={t.trim()} />
                      ))}
                    </td>
                    <td className="px-4 py-3 text-emerald-400 text-xs font-mono max-w-xs truncate" title={r.montos_mencionados}>
                      {r.montos_mencionados?.split(';')[0] ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Tab: Buscar ───────────────────────────────────────────────
function TabBuscar() {
  const [input, setInput] = useState('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const { data, loading } = useBuscar(q, page)

  return (
    <div className="space-y-4">
      <div className="card flex gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            className="input pl-8 w-full"
            placeholder="Buscar en comunicados PGR (nombre, operación, monto…)"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { setQ(input); setPage(1) } }}
          />
        </div>
        <button className="btn-primary px-4 py-2 text-sm"
          onClick={() => { setQ(input); setPage(1) }}>
          Buscar
        </button>
        {data && <span className="text-sm text-gray-500 self-center">{data.total} resultados</span>}
      </div>

      {q.length >= 3 && (
        <div className="card p-0 overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-gray-500">Buscando...</div>
          ) : !data?.results?.length ? (
            <div className="p-8 text-center text-gray-500">Sin resultados para "{q}"</div>
          ) : (
            <div className="divide-y divide-gray-800/60">
              {data.results.map((r: any) => (
                <div key={r.id} className="px-4 py-3 hover:bg-gray-800/30">
                  <div className="flex items-start gap-2 mb-1 flex-wrap">
                    <TipoBadge tipo={r.tipo} />
                    {r.operacion && (
                      <span className="text-xs bg-indigo-900/40 text-indigo-300 border border-indigo-700/40 px-2 py-0.5 rounded">
                        {r.operacion}
                      </span>
                    )}
                    {r.fecha && <span className="text-xs text-gray-500">{r.fecha}</span>}
                  </div>
                  <a href={r.url} target="_blank" rel="noopener noreferrer"
                    className="text-white font-medium text-sm hover:text-gov-400">
                    {r.titulo}
                  </a>
                  {r.resumen && (
                    <p className="text-gray-400 text-xs mt-1 line-clamp-3">{r.resumen}</p>
                  )}
                  {r.montos && (
                    <p className="text-emerald-400 text-xs mt-1 font-mono">{r.montos}</p>
                  )}
                </div>
              ))}
            </div>
          )}
          <div className="px-4 pb-3">
            <Pager page={page} total={data?.total ?? 0} size={50} onChange={setPage} />
          </div>
        </div>
      )}
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────
const TABS: { id: Tab; label: string; icon: typeof Shield }[] = [
  { id: 'comunicados',  label: 'Comunicados',  icon: FileText },
  { id: 'operaciones',  label: 'Operaciones / Casos', icon: AlertTriangle },
  { id: 'buscar',       label: 'Buscar',       icon: Search },
]

export default function PGR() {
  const [tab, setTab] = useState<Tab>('comunicados')
  const { data: stats } = useStats()
  const tiposDisponibles = stats?.por_tipo ? Object.keys(stats.por_tipo) : []
  const dbVacia = stats === null || stats?.total_comunicados === 0

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title="Procuraduría General de la República"
        subtitle={stats?.total_comunicados
          ? `${stats.total_comunicados.toLocaleString()} comunicados indexados · ${stats.operaciones_detectadas?.length ?? 0} operaciones detectadas`
          : 'Comunicados oficiales — pgr.gob.do'}
      />

      {/* Alerta si BD está vacía */}
      {dbVacia && (
        <div className="card border border-yellow-800/50 bg-yellow-950/20 flex items-start gap-3">
          <Play size={16} className="text-yellow-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-yellow-300 font-medium text-sm">Base de datos vacía — ejecuta el scraper</p>
            <p className="text-gray-400 text-xs mt-1">
              Ve al panel <strong>Datos / ETL</strong> y ejecuta{' '}
              <code className="bg-gray-800 px-1 rounded">POST /api/etl/scrape/pgr</code>.
              Con <code className="bg-gray-800 px-1 rounded">max_pages=50</code> (~450 artículos, ~5 min).
              Con <code className="bg-gray-800 px-1 rounded">max_pages=991</code> indexa el archivo completo (~8,900 artículos, ~30 min).
            </p>
          </div>
        </div>
      )}

      {/* Stats rápidos */}
      {stats && stats.total_comunicados > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="card">
            <p className="text-xs text-gray-500">Total comunicados</p>
            <p className="text-2xl font-bold text-white mt-1">{stats.total_comunicados.toLocaleString()}</p>
          </div>
          <div className="card">
            <p className="text-xs text-gray-500">Con fecha extraída</p>
            <p className="text-2xl font-bold text-white mt-1">{stats.con_fecha_extraida?.toLocaleString()}</p>
          </div>
          <div className="card">
            <p className="text-xs text-gray-500">Operaciones/casos</p>
            <p className="text-2xl font-bold text-white mt-1">{stats.operaciones_detectadas?.length ?? 0}</p>
          </div>
          <div className="card">
            <p className="text-xs text-gray-500">Tipo más frecuente</p>
            <p className="text-xl font-bold text-white mt-1 capitalize">
              {tiposDisponibles[0] ?? '—'}
            </p>
          </div>
        </div>
      )}

      {/* Operaciones destacadas (mini-chips) */}
      {stats?.operaciones_detectadas?.length > 0 && (
        <div className="card flex flex-wrap gap-2 items-center">
          <span className="text-xs text-gray-500 mr-1">Operaciones:</span>
          {stats.operaciones_detectadas.slice(0, 10).map((op: any) => (
            <button
              key={op.operacion}
              onClick={() => { setTab('operaciones') }}
              className="text-xs bg-red-900/30 text-red-300 border border-red-800/40 px-2 py-0.5 rounded hover:bg-red-900/50 transition-colors"
            >
              {op.operacion} <span className="text-red-500">({op.cantidad})</span>
            </button>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-800">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === id
                ? 'border-gov-500 text-gov-400'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      {tab === 'comunicados'  && <TabComunicados tiposDisponibles={tiposDisponibles} />}
      {tab === 'operaciones'  && <TabOperaciones />}
      {tab === 'buscar'       && <TabBuscar />}
    </div>
  )
}
