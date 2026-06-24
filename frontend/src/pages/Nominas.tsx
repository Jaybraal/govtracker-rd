import { useState } from 'react'
import { Search, Users, TrendingUp, Building2, AlertTriangle, ChevronLeft, ChevronRight, X } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { useApi } from '../hooks/useApi'
import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 60000 })

const fmtRD = (n: number) => {
  if (n >= 1_000_000) return `RD$${(n / 1_000_000).toFixed(1)}M`
  return `RD$${Math.round(n).toLocaleString('es-DO')}`
}

const CONFIDENCE_COLORS: Record<string, string> = {
  ALTA:  'bg-red-900/40 text-red-300 border border-red-700/40',
  MEDIA: 'bg-yellow-900/40 text-yellow-300 border border-yellow-700/40',
  BAJA:  'bg-gray-800 text-gray-400 border border-gray-700/40',
}

type Tab = 'doble' | 'salarios' | 'instituciones' | 'buscar'

// ── Hooks de datos ───────────────────────────────────────────
function useNominasStats() {
  return useApi(() => api.get('/nominas/stats').then(r => r.data), [])
}

function useDoble(anio: number | '', confianza: string, page: number) {
  return useApi(() => api.get('/nominas/doble-cobro', {
    params: { ...(anio && { anio }), ...(confianza && { confianza }), page, size: 50 },
  }).then(r => r.data), [anio, confianza, page])
}

function useTopSalarios(anio: number | '', page: number) {
  return useApi(() => api.get('/nominas/top-salarios', {
    params: { ...(anio && { anio }), page, size: 50 },
  }).then(r => r.data), [anio, page])
}

function useInstituciones(anio: number | '') {
  return useApi(() => api.get('/nominas/instituciones', {
    params: { ...(anio && { anio }) },
  }).then(r => r.data), [anio])
}

function useDobleCobroDetalle(nombre: string | null) {
  return useApi(
    () => nombre
      ? api.get('/nominas/doble-cobro/detalle', { params: { nombre } }).then(r => r.data)
      : Promise.resolve(null),
    [nombre],
  )
}

// ── Paginador ────────────────────────────────────────────────
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

const MESES = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

// ── Modal: Detalle de Doble Cobro ─────────────────────────────
function DobleCobroModal({ nombre, nombreOriginal, onClose }: { nombre: string; nombreOriginal: string; onClose: () => void }) {
  const { data, loading } = useDobleCobroDetalle(nombre)

  const grupos: Record<string, { anio: number; mes: number; items: any[] }> = {}
  for (const r of data?.registros ?? []) {
    const mes = Number(r.mes)
    const key = `${r.anio}-${mes}`
    if (!grupos[key]) grupos[key] = { anio: r.anio, mes, items: [] }
    grupos[key].items.push(r)
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="card max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-white">{nombreOriginal}</h3>
            <p className="text-xs text-gray-500 mt-0.5">Desglose mes a mes por institución</p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white"><X size={18} /></button>
        </div>
        {loading ? (
          <div className="p-8 text-center text-gray-500">Cargando...</div>
        ) : !data?.registros?.length ? (
          <div className="p-8 text-center text-gray-500">Sin detalle disponible</div>
        ) : (
          <div className="space-y-3">
            {Object.values(grupos).map(g => (
              <div key={`${g.anio}-${g.mes}`} className="bg-gray-800/50 rounded-lg p-3">
                <p className="text-xs text-gray-400 font-medium mb-2">{MESES[g.mes] ?? g.mes} {g.anio}</p>
                <div className="space-y-1.5">
                  {g.items.map((it: any, i: number) => (
                    <div key={i} className="flex items-center justify-between gap-3 text-sm">
                      <div className="min-w-0">
                        <p className="text-white truncate">{it.institucion}</p>
                        {it.funcion && <p className="text-xs text-gray-500 truncate">{it.funcion}</p>}
                      </div>
                      <span className="font-mono text-green-400 shrink-0">{fmtRD(it.salario)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Tab: Doble Cobro ─────────────────────────────────────────
function TabDoble({ anios }: { anios: number[] }) {
  const [anio, setAnio] = useState<number | ''>(anios[0] ?? '')
  const [confianza, setConfianza] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<{ nombre: string; nombreOriginal: string } | null>(null)
  const { data, loading } = useDoble(anio, confianza, page)

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap gap-3 items-center">
        <select className="input w-32" value={anio} onChange={e => { setAnio(e.target.value ? +e.target.value : ''); setPage(1) }}>
          <option value="">Todos los años</option>
          {anios.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        <select className="input w-40" value={confianza} onChange={e => { setConfianza(e.target.value); setPage(1) }}>
          <option value="">Toda confianza</option>
          <option value="ALTA">Alta confianza</option>
          <option value="MEDIA">Media confianza</option>
          <option value="BAJA">Baja confianza</option>
        </select>
        {data && <span className="text-sm text-gray-500">{data.total} casos detectados</span>}
      </div>

      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-3 bg-red-950/30 border-b border-red-900/30 flex items-center gap-2">
          <AlertTriangle size={16} className="text-red-400" />
          <span className="text-sm text-red-300 font-medium">
            Personas detectadas en 2 o más instituciones el mismo mes/año
          </span>
        </div>
        {loading ? (
          <div className="p-8 text-center text-gray-500">Cargando...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase">
                  <th className="px-4 py-3 text-left">Confianza</th>
                  <th className="px-4 py-3 text-left">Nombre</th>
                  <th className="px-4 py-3 text-center">Meses</th>
                  <th className="px-4 py-3 text-left">Período</th>
                  <th className="px-4 py-3 text-center"># Inst.</th>
                  <th className="px-4 py-3 text-right">Total cobrado</th>
                  <th className="px-4 py-3 text-left">Instituciones</th>
                </tr>
              </thead>
              <tbody>
                {data?.results?.map((r: any, i: number) => (
                  <tr key={i} onClick={() => setSelected({ nombre: r.nombre, nombreOriginal: r.nombre_original })}
                    className="border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer">
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${CONFIDENCE_COLORS[r.confianza] ?? ''}`}>
                        {r.confianza}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-medium text-white max-w-[180px] truncate" title={r.nombre_original}>
                      {r.nombre_original}
                    </td>
                    <td className="px-4 py-3 text-center text-gray-300">{r.meses_afectados}</td>
                    <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">
                      {r.primer_periodo} → {r.ultimo_periodo}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="bg-orange-900/40 text-orange-300 text-xs px-2 py-0.5 rounded font-bold">
                        {r.max_instituciones}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-green-400">
                      {fmtRD(r.total_cobrado ?? 0)}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs max-w-[200px] truncate" title={r.instituciones}>
                      {r.instituciones}
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
        <DobleCobroModal
          nombre={selected.nombre}
          nombreOriginal={selected.nombreOriginal}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  )
}

// ── Tab: Top Salarios ────────────────────────────────────────
function TabSalarios({ anios }: { anios: number[] }) {
  const [anio, setAnio] = useState<number | ''>(anios[0] ?? '')
  const [page, setPage] = useState(1)
  const { data, loading } = useTopSalarios(anio, page)

  return (
    <div className="space-y-4">
      <div className="card flex items-center gap-3">
        <select className="input w-32" value={anio} onChange={e => { setAnio(e.target.value ? +e.target.value : ''); setPage(1) }}>
          <option value="">Todos los años</option>
          {anios.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        {data && <span className="text-sm text-gray-500">Máximo RD$1,500,000/mes · Sin anomalías</span>}
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
                  <th className="px-4 py-3 text-left">Nombre</th>
                  <th className="px-4 py-3 text-left">Institución</th>
                  <th className="px-4 py-3 text-left">Cargo</th>
                  <th className="px-4 py-3 text-right">Salario mensual</th>
                  <th className="px-4 py-3 text-center">Año</th>
                </tr>
              </thead>
              <tbody>
                {data?.results?.map((r: any, i: number) => (
                  <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="px-4 py-3 text-gray-600">{(page - 1) * 50 + i + 1}</td>
                    <td className="px-4 py-3 font-medium text-white max-w-[180px] truncate" title={r.nombre}>
                      {r.nombre}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs max-w-[160px] truncate" title={r.institucion}>
                      {r.institucion}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs max-w-[160px] truncate" title={r.funcion}>
                      {r.funcion}
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-bold text-emerald-400">
                      {fmtRD(r.salario_max)}
                    </td>
                    <td className="px-4 py-3 text-center text-gray-400">{r.anio}</td>
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
    </div>
  )
}

// ── Tab: Por Institución ──────────────────────────────────────
function TabInstituciones({ anios }: { anios: number[] }) {
  const [anio, setAnio] = useState<number | ''>(anios[0] ?? '')
  const { data, loading } = useInstituciones(anio)

  return (
    <div className="space-y-4">
      <div className="card flex items-center gap-3">
        <select className="input w-32" value={anio} onChange={e => setAnio(e.target.value ? +e.target.value : '')}>
          <option value="">Todos los años</option>
          {anios.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        <span className="text-sm text-gray-500">Masa salarial por institución (top 50)</span>
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
                  <th className="px-4 py-3 text-right">Empleados únicos</th>
                  <th className="px-4 py-3 text-right">Salario promedio</th>
                  <th className="px-4 py-3 text-right">Salario máximo</th>
                  <th className="px-4 py-3 text-right">Masa salarial total</th>
                </tr>
              </thead>
              <tbody>
                {data?.results?.map((r: any, i: number) => (
                  <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="px-4 py-3 text-gray-600">{i + 1}</td>
                    <td className="px-4 py-3 font-medium text-white max-w-[240px] truncate" title={r.institucion}>
                      {r.institucion}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-300">
                      {r.empleados_unicos?.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-blue-400">
                      {fmtRD(r.salario_promedio)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-orange-400">
                      {fmtRD(r.salario_max)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-bold text-emerald-400">
                      {fmtRD(r.masa_salarial_total)}
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
function TabBuscar({ anios }: { anios: number[] }) {
  const [query, setQuery] = useState('')
  const [anio, setAnio] = useState<number | ''>('')
  const [page, setPage] = useState(1)
  const [searchTerm, setSearchTerm] = useState('')

  const { data, loading } = useApi(
    () => searchTerm.length >= 3
      ? api.get('/nominas/buscar', { params: { q: searchTerm, ...(anio && { anio }), page, size: 50 } }).then(r => r.data)
      : Promise.resolve(null),
    [searchTerm, anio, page],
  )

  const handleSearch = () => {
    setPage(1)
    setSearchTerm(query)
  }

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-64">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            className="input pl-8 w-full"
            placeholder="Buscar empleado por nombre..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
          />
        </div>
        <select className="input w-32" value={anio} onChange={e => setAnio(e.target.value ? +e.target.value : '')}>
          <option value="">Todos los años</option>
          {anios.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        <button className="btn-primary px-4 py-2 text-sm" onClick={handleSearch}>Buscar</button>
        {data && <span className="text-sm text-gray-500">{data.total} registros encontrados</span>}
      </div>

      {searchTerm.length >= 3 && (
        <div className="card p-0 overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-gray-500">Buscando...</div>
          ) : !data?.results?.length ? (
            <div className="p-8 text-center text-gray-500">Sin resultados para "{searchTerm}"</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase">
                    <th className="px-4 py-3 text-left">Nombre</th>
                    <th className="px-4 py-3 text-left">Institución</th>
                    <th className="px-4 py-3 text-left">Cargo</th>
                    <th className="px-4 py-3 text-right">Salario</th>
                    <th className="px-4 py-3 text-center">Mes/Año</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((r: any, i: number) => (
                    <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                      <td className="px-4 py-3 font-medium text-white max-w-[180px] truncate" title={r.nombre_raw}>
                        {r.nombre_raw}
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs max-w-[160px] truncate" title={r.institucion}>
                        {r.institucion}
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs max-w-[160px] truncate" title={r.funcion}>
                        {r.funcion}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-emerald-400">
                        {fmtRD(r.salario)}
                      </td>
                      <td className="px-4 py-3 text-center text-gray-400 text-xs">
                        {r.mes}/{r.anio}
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
      )}
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────
const TABS: { id: Tab; label: string; icon: typeof Users }[] = [
  { id: 'doble',         label: 'Doble Cobro',    icon: AlertTriangle },
  { id: 'salarios',      label: 'Top Salarios',   icon: TrendingUp },
  { id: 'instituciones', label: 'Por Institución', icon: Building2 },
  { id: 'buscar',        label: 'Buscar Empleado', icon: Search },
]

export default function Nominas() {
  const [tab, setTab] = useState<Tab>('doble')
  const { data: stats } = useNominasStats()
  const anios: number[] = stats?.anios_disponibles ?? []

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title="Nóminas del Gobierno"
        subtitle={stats
          ? `${stats.total_registros.toLocaleString()} registros · ${stats.total_instituciones} instituciones`
          : 'Cargando estadísticas...'}
      />

      {/* Stats rápidos */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <div className="card">
            <p className="text-xs text-gray-500">Total registros</p>
            <p className="text-2xl font-bold text-white mt-1">{(stats.total_registros / 1_000_000).toFixed(1)}M</p>
          </div>
          <div className="card">
            <p className="text-xs text-gray-500">Instituciones</p>
            <p className="text-2xl font-bold text-white mt-1">{stats.total_instituciones}</p>
          </div>
          <div className="card">
            <p className="text-xs text-gray-500">Años disponibles</p>
            <p className="text-2xl font-bold text-white mt-1">{anios.length > 0 ? `${anios[anios.length - 1]}–${anios[0]}` : '–'}</p>
          </div>
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

      {/* Contenido del tab */}
      {tab === 'doble'         && <TabDoble anios={anios} />}
      {tab === 'salarios'      && <TabSalarios anios={anios} />}
      {tab === 'instituciones' && <TabInstituciones anios={anios} />}
      {tab === 'buscar'        && <TabBuscar anios={anios} />}
    </div>
  )
}
