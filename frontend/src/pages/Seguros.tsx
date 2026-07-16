import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, HeartPulse, Building2, TrendingUp, AlertTriangle, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { useApi } from '../hooks/useApi'
import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 60000 })

const fmtRD = (n: number) => {
  if (n >= 1_000_000_000) return `RD$${(n / 1_000_000_000).toFixed(2)}B`
  if (n >= 1_000_000) return `RD$${(n / 1_000_000).toFixed(1)}M`
  return `RD$${Math.round(n).toLocaleString('es-DO')}`
}

type Tab = 'contratos' | 'aseguradoras' | 'instituciones' | 'caso'

function useStats() {
  return useApi(() => api.get('/seguros/stats').then(r => r.data), [])
}
function useContratos(anio: number | '', page: number) {
  return useApi(() => api.get('/seguros/contratos', {
    params: { ...(anio && { anio }), page, size: 50 },
  }).then(r => r.data), [anio, page])
}
function useAseguradoras(anio: number | '') {
  return useApi(() => api.get('/seguros/top-aseguradoras', {
    params: { ...(anio && { anio }) },
  }).then(r => r.data), [anio])
}
function useInstituciones(anio: number | '') {
  return useApi(() => api.get('/seguros/por-institucion', {
    params: { ...(anio && { anio }) },
  }).then(r => r.data), [anio])
}
function usoCaso() {
  return useApi(() => api.get('/seguros/caso-senasa').then(r => r.data), [])
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

// ── Tab: Contratos ────────────────────────────────────────────
function TabContratos({ anios }: { anios: number[] }) {
  const navigate = useNavigate()
  const [anio, setAnio] = useState<number | ''>(anios[0] ?? '')
  const [page, setPage] = useState(1)
  const { data, loading } = useContratos(anio, page)

  return (
    <div className="space-y-4">
      <div className="card flex items-center gap-3">
        <select className="input w-32" value={anio} onChange={e => { setAnio(e.target.value ? +e.target.value : ''); setPage(1) }}>
          <option value="">Todos los años</option>
          {anios.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        {data && <span className="text-sm text-gray-500">{data.total.toLocaleString()} contratos</span>}
      </div>
      <div className="card p-0 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Cargando...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase">
                  <th className="px-4 py-3 text-left">Código</th>
                  <th className="px-4 py-3 text-left">Empresa</th>
                  <th className="px-4 py-3 text-left">Institución (RPE)</th>
                  <th className="px-4 py-3 text-left">Tipo</th>
                  <th className="px-4 py-3 text-right">Valor</th>
                  <th className="px-4 py-3 text-center">Año</th>
                  <th className="px-4 py-3 text-center">Estado</th>
                </tr>
              </thead>
              <tbody>
                {data?.results?.map((r: any, i: number) => (
                  <tr key={i}
                    onClick={() => r.company_id && navigate(`/companies/${r.company_id}`)}
                    className={`border-b border-gray-800/50 hover:bg-gray-800/30 ${r.company_id ? 'cursor-pointer' : ''}`}>
                    <td className="px-4 py-3 text-xs font-mono">
                      {r.codigo_contrato ? (
                        <a href={`https://www.dgcp.gob.do/index.php/proceso?buscar=${encodeURIComponent(r.codigo_contrato)}`}
                          target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}
                          className="text-gov-400 hover:text-gov-200 flex items-center gap-1 transition-colors" title="Buscar en portal DGCP">
                          {r.codigo_contrato}
                          <ExternalLink size={10} className="opacity-60 shrink-0" />
                        </a>
                      ) : <span className="text-gray-600">—</span>}
                    </td>
                    <td className="px-4 py-3 font-medium text-white max-w-[180px] truncate" title={r.empresa}>
                      {r.empresa}
                      {!r.company_id && <span className="text-gray-600 text-[10px] ml-1">(sin ficha)</span>}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{r.rpe}</td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{r.objeto}</td>
                    <td className="px-4 py-3 text-right font-mono font-bold text-emerald-400">
                      {fmtRD(r.valor_contratado)}
                    </td>
                    <td className="px-4 py-3 text-center text-gray-400">{r.anio}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        r.estado === 'Activo'
                          ? 'bg-green-900/40 text-green-300 border border-green-700/40'
                          : 'bg-gray-800 text-gray-400 border border-gray-700/40'
                      }`}>{r.estado}</span>
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
    </div>
  )
}

// ── Tab: Top Aseguradoras ─────────────────────────────────────
function TabAseguradoras({ anios }: { anios: number[] }) {
  const navigate = useNavigate()
  const [anio, setAnio] = useState<number | ''>('')
  const { data, loading } = useAseguradoras(anio)

  return (
    <div className="space-y-4">
      <div className="card flex items-center gap-3">
        <select className="input w-32" value={anio} onChange={e => setAnio(e.target.value ? +e.target.value : '')}>
          <option value="">Todos los años</option>
          {anios.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        <span className="text-sm text-gray-500">Empresas con más contratos con el gobierno (top 50)</span>
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
                  <th className="px-4 py-3 text-left">Empresa</th>
                  <th className="px-4 py-3 text-right">Contratos</th>
                  <th className="px-4 py-3 text-right">Monto total</th>
                  <th className="px-4 py-3 text-right">Promedio</th>
                  <th className="px-4 py-3 text-right">Mayor contrato</th>
                  <th className="px-4 py-3 text-center">Período</th>
                </tr>
              </thead>
              <tbody>
                {data?.results?.map((r: any, i: number) => (
                  <tr key={i}
                    onClick={() => r.company_id && navigate(`/companies/${r.company_id}`)}
                    className={`border-b border-gray-800/50 hover:bg-gray-800/30 ${r.company_id ? 'cursor-pointer' : ''}`}>
                    <td className="px-4 py-3 text-gray-600">{i + 1}</td>
                    <td className="px-4 py-3 font-medium text-white max-w-[220px] truncate" title={r.empresa}>
                      {r.empresa}
                      {!r.company_id && <span className="text-gray-600 text-[10px] ml-1">(sin ficha)</span>}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-300">{r.num_contratos}</td>
                    <td className="px-4 py-3 text-right font-mono font-bold text-emerald-400">
                      {fmtRD(r.monto_total)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-blue-400">
                      {fmtRD(r.monto_promedio)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-orange-400">
                      {fmtRD(r.contrato_max)}
                    </td>
                    <td className="px-4 py-3 text-center text-gray-400 text-xs">
                      {r.primer_anio === r.ultimo_anio ? r.primer_anio : `${r.primer_anio}–${r.ultimo_anio}`}
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

// ── Tab: Empresas por RPE ──────────────────────────────────────
// Esta tabla NO tiene dimensión de institución compradora — contratos_seguros solo
// registra el RPE del vendedor. Agrupa por RPE (en vez de por nombre, como "Top
// Aseguradoras") para detectar variantes de nombre registradas bajo el mismo RPE.
function TabInstituciones({ anios }: { anios: number[] }) {
  const navigate = useNavigate()
  const [anio, setAnio] = useState<number | ''>('')
  const { data, loading } = useInstituciones(anio)

  return (
    <div className="space-y-4">
      <div className="card flex items-center gap-3">
        <select className="input w-32" value={anio} onChange={e => setAnio(e.target.value ? +e.target.value : '')}>
          <option value="">Todos los años</option>
          {anios.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        <span className="text-sm text-gray-500">Agrupado por RPE — detecta variantes de nombre de la misma empresa (top 50)</span>
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
                  <th className="px-4 py-3 text-left">Empresa (RPE)</th>
                  <th className="px-4 py-3 text-right">Contratos</th>
                  <th className="px-4 py-3 text-right">Gasto total</th>
                  <th className="px-4 py-3 text-right">Variantes de nombre</th>
                  <th className="px-4 py-3 text-right">Mayor contrato</th>
                </tr>
              </thead>
              <tbody>
                {data?.results?.map((r: any, i: number) => (
                  <tr key={i}
                    onClick={() => r.company_id && navigate(`/companies/${r.company_id}`)}
                    className={`border-b border-gray-800/50 hover:bg-gray-800/30 ${r.company_id ? 'cursor-pointer' : ''}`}>
                    <td className="px-4 py-3 text-gray-600">{i + 1}</td>
                    <td className="px-4 py-3 font-medium text-white">
                      {r.empresa}
                      <span className="text-gray-600 text-xs ml-1">RPE {r.institucion_rpe}</span>
                      {!r.company_id && <span className="text-gray-600 text-[10px] ml-1">(sin ficha)</span>}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-300">{r.num_contratos}</td>
                    <td className="px-4 py-3 text-right font-mono font-bold text-emerald-400">
                      {fmtRD(r.monto_total)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`text-xs px-2 py-0.5 rounded ${r.empresas_distintas > 1 ? 'bg-yellow-900/40 text-yellow-300' : 'bg-blue-900/40 text-blue-300'}`}>
                        {r.empresas_distintas}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-orange-400">
                      {fmtRD(r.contrato_max)}
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

// ── Tab: Caso SENASA ──────────────────────────────────────────
function TabCaso() {
  const { data, loading } = usoCaso()
  if (loading) return <div className="p-8 text-center text-gray-500">Cargando...</div>
  const caso = data?.caso
  const instituciones: any[] = data?.instituciones_sector ?? []
  if (!caso) return null

  return (
    <div className="space-y-4">
      {/* Banner principal */}
      <div className="card border border-red-800/50 bg-red-950/20">
        <div className="flex items-start gap-3">
          <AlertTriangle size={20} className="text-red-400 mt-0.5 shrink-0" />
          <div>
            <h3 className="text-red-300 font-semibold text-base">{caso.titulo}</h3>
            <p className="text-gray-300 text-sm mt-1 leading-relaxed">{caso.descripcion}</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-4">
              <div>
                <p className="text-xs text-gray-500">Monto defraudado</p>
                <p className="text-lg font-bold text-red-400">{caso.monto_defraudado}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Sobornos cobrados</p>
                <p className="text-lg font-bold text-orange-400">{caso.monto_sobornos}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Afiliados afectados</p>
                <p className="text-lg font-bold text-yellow-400">{caso.afiliados_afectados}</p>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-3">Fecha: {caso.fecha} · Fiscal: {caso.fiscal}</p>
          </div>
        </div>
      </div>

      {/* Cargos imputados */}
      <div className="card">
        <h4 className="text-sm font-semibold text-gray-300 mb-3">Cargos imputados</h4>
        <div className="flex flex-wrap gap-2">
          {caso.cargos_imputados?.map((c: string, i: number) => (
            <span key={i} className="bg-gray-800 text-gray-300 text-xs px-3 py-1 rounded-full border border-gray-700/50">
              {c}
            </span>
          ))}
        </div>
      </div>

      {/* Imputados */}
      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800">
          <h4 className="text-sm font-semibold text-gray-300">Imputados ({caso.imputados?.length})</h4>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase">
              <th className="px-4 py-3 text-left">Nombre</th>
              <th className="px-4 py-3 text-left">Cargo / Rol</th>
            </tr>
          </thead>
          <tbody>
            {caso.imputados?.map((imp: any, i: number) => (
              <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="px-4 py-3 font-medium text-white">{imp.nombre}</td>
                <td className="px-4 py-3 text-gray-400 text-xs">{imp.cargo}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Instituciones del sector */}
      <div className="card">
        <h4 className="text-sm font-semibold text-gray-300 mb-3">Instituciones del sector salud / seguros</h4>
        <div className="space-y-2">
          {instituciones.map((inst: any, i: number) => (
            <div key={i} className="flex items-start gap-3 py-2 border-b border-gray-800/50 last:border-0">
              <span className="bg-blue-900/40 text-blue-300 text-xs px-2 py-0.5 rounded font-mono font-bold shrink-0">
                {inst.siglas}
              </span>
              <div>
                <p className="text-white text-sm font-medium">{inst.nombre}</p>
                <p className="text-gray-400 text-xs">{inst.rol}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Fuentes oficiales */}
      <div className="card">
        <h4 className="text-sm font-semibold text-gray-300 mb-3">Fuentes oficiales (Procuraduría General de la República)</h4>
        <div className="space-y-1">
          {caso.fuentes?.map((url: string, i: number) => (
            <a key={i} href={url} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300 break-all">
              <ExternalLink size={12} className="shrink-0" />
              {url.replace('https://pgr.gob.do/', 'pgr.gob.do/...')}
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────
const TABS: { id: Tab; label: string; icon: typeof HeartPulse }[] = [
  { id: 'contratos',     label: 'Contratos del Estado', icon: HeartPulse },
  { id: 'aseguradoras',  label: 'Top Aseguradoras',     icon: TrendingUp },
  { id: 'instituciones', label: 'Empresas por RPE',      icon: Building2 },
  { id: 'caso',          label: 'Caso SENASA',          icon: AlertTriangle },
]

export default function Seguros() {
  const [tab, setTab] = useState<Tab>('contratos')
  const { data: stats } = useStats()
  const anios: number[] = stats?.anios_disponibles ?? []

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title="Seguros del Estado"
        subtitle={stats
          ? `${stats.total_contratos.toLocaleString()} contratos · ${stats.empresas_unicas} empresas · ${fmtRD(stats.monto_total)} adjudicados`
          : 'Cargando estadísticas...'}
      />

      {/* Stats rápidos */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="card">
            <p className="text-xs text-gray-500">Total contratos</p>
            <p className="text-2xl font-bold text-white mt-1">{stats.total_contratos.toLocaleString()}</p>
          </div>
          <div className="card">
            <p className="text-xs text-gray-500">Monto adjudicado</p>
            <p className="text-2xl font-bold text-white mt-1">{fmtRD(stats.monto_total)}</p>
          </div>
          <div className="card">
            <p className="text-xs text-gray-500">Empresas distintas</p>
            <p className="text-2xl font-bold text-white mt-1">{stats.empresas_unicas}</p>
          </div>
          <div className="card border border-red-800/50 bg-red-950/20">
            <p className="text-xs text-red-400">Caso SENASA (Operación Cobra)</p>
            <p className="text-lg font-bold text-red-300 mt-1">{stats.caso_cobra_monto_defraudado}</p>
            <p className="text-xs text-gray-500">{stats.caso_cobra_imputados} imputados</p>
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
              id === 'caso'
                ? tab === id
                  ? 'border-red-500 text-red-400'
                  : 'border-transparent text-red-500/70 hover:text-red-400'
                : tab === id
                  ? 'border-gov-500 text-gov-400'
                  : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      {tab === 'contratos'     && <TabContratos anios={anios} />}
      {tab === 'aseguradoras'  && <TabAseguradoras anios={anios} />}
      {tab === 'instituciones' && <TabInstituciones anios={anios} />}
      {tab === 'caso'          && <TabCaso />}
    </div>
  )
}
