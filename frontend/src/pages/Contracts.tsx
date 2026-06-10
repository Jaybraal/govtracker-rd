import { useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { Search, Download, AlertTriangle, X } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { contractsApi, exportApi, Contract, PagedResponse } from '../services/api'
import { useApi } from '../hooks/useApi'

const fmt = (n: number) => {
  if (n >= 1_000_000_000) return `RD$${(n / 1_000_000_000).toFixed(2)}B`
  if (n >= 1_000_000) return `RD$${(n / 1_000_000).toFixed(1)}M`
  return `RD$${n.toLocaleString()}`
}

const MODALIDADES = [
  '', 'licitacion_publica', 'licitacion_restringida', 'comparacion_precios',
  'contratacion_directa', 'subasta_inversa', 'sorteo', 'acuerdo_marco',
]

export default function Contracts() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [modalidad, setModalidad] = useState(searchParams.get('modalidad') ?? '')
  const [montoMin, setMontoMin] = useState('')
  const [soloAdendas, setSoloAdendas] = useState(searchParams.get('tiene_adendas') === 'true')
  const [soloMayores, setSoloMayores] = useState(searchParams.get('es_mayor_100m') === 'true')
  const [soloFinanciados, setSoloFinanciados] = useState(searchParams.get('financiado_prestamo') === 'true')
  const companyId = searchParams.get('company_id')
  const institutionId = searchParams.get('institution_id')

  const params = {
    page, size: 50,
    ...(search && { search }),
    ...(modalidad && { modalidad }),
    ...(montoMin && { monto_min: montoMin }),
    ...(soloAdendas && { tiene_adendas: true }),
    ...(soloMayores && { es_mayor_100m: true }),
    ...(soloFinanciados && { financiado_prestamo: true }),
    ...(companyId && { company_id: companyId }),
    ...(institutionId && { institution_id: institutionId }),
  }

  const { data, loading } = useApi<PagedResponse<Contract>>(
    () => contractsApi.list(params),
    [page, search, modalidad, montoMin, soloAdendas, soloMayores, soloFinanciados, companyId, institutionId],
  )

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title="Contratos Públicos"
        subtitle={data ? `${data.total.toLocaleString()} contratos encontrados` : 'Cargando...'}
        actions={
          <div className="flex gap-2">
            <button onClick={() => exportApi.contractsCsv(params)} className="btn-ghost flex items-center gap-1.5">
              <Download size={14} /> CSV
            </button>
            <button onClick={() => exportApi.contractsExcel(params)} className="btn-ghost flex items-center gap-1.5">
              <Download size={14} /> Excel
            </button>
          </div>
        }
      />

      {(companyId || institutionId) && (
        <div className="flex items-center gap-2 text-sm text-gov-300 bg-gov-900/30 border border-gov-800/40 rounded-lg px-3 py-2">
          <span>
            Mostrando solo contratos de {companyId ? `la empresa #${companyId}` : `la institución #${institutionId}`}
          </span>
          <button
            onClick={() => navigate('/contracts')}
            className="ml-auto flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
          >
            <X size={12} /> Quitar filtro
          </button>
        </div>
      )}

      {/* Filtros */}
      <div className="card flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            className="input pl-8"
            placeholder="Buscar por número, descripción, objeto..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
          />
        </div>
        <select
          className="input w-auto"
          value={modalidad}
          onChange={e => { setModalidad(e.target.value); setPage(1) }}
        >
          {MODALIDADES.map(m => (
            <option key={m} value={m}>{m || 'Todas las modalidades'}</option>
          ))}
        </select>
        <input
          type="number"
          className="input w-40"
          placeholder="Monto mínimo"
          value={montoMin}
          onChange={e => { setMontoMin(e.target.value); setPage(1) }}
        />
        <label className="flex items-center gap-1.5 text-sm text-gray-400 cursor-pointer">
          <input type="checkbox" checked={soloAdendas} onChange={e => setSoloAdendas(e.target.checked)} className="accent-gov-500" />
          Con adendas
        </label>
        <label className="flex items-center gap-1.5 text-sm text-gray-400 cursor-pointer">
          <input type="checkbox" checked={soloMayores} onChange={e => setSoloMayores(e.target.checked)} className="accent-gov-500" />
          &gt;RD$100M
        </label>
        <label className="flex items-center gap-1.5 text-sm text-gray-400 cursor-pointer">
          <input type="checkbox" checked={soloFinanciados} onChange={e => setSoloFinanciados(e.target.checked)} className="accent-gov-500" />
          Financiados préstamo
        </label>
      </div>

      {/* Tabla */}
      <div className="card p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-left">
              <th className="px-4 py-3 text-gray-400 font-medium">Número</th>
              <th className="px-4 py-3 text-gray-400 font-medium">Institución</th>
              <th className="px-4 py-3 text-gray-400 font-medium">Empresa</th>
              <th className="px-4 py-3 text-gray-400 font-medium">Modalidad</th>
              <th className="px-4 py-3 text-gray-400 font-medium text-right">Monto Original</th>
              <th className="px-4 py-3 text-gray-400 font-medium text-center">Adendas</th>
              <th className="px-4 py-3 text-gray-400 font-medium text-center">Flags</th>
              <th className="px-4 py-3 text-gray-400 font-medium">Fecha</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-500">Cargando...</td></tr>
            ) : data?.items.map(c => (
              <tr key={c.id} className="table-row">
                <td className="px-4 py-3">
                  <Link to={`/contracts/${c.id}`} className="text-gov-400 hover:text-gov-300 font-mono text-xs">
                    {c.numero_contrato || `#${c.id}`}
                  </Link>
                </td>
                <td className="px-4 py-3 text-gray-300 max-w-32 truncate">
                  <Link to={`/institutions/${c.institution_id}`} className="hover:text-white">
                    {c.institucion_siglas || c.institucion_nombre}
                  </Link>
                </td>
                <td className="px-4 py-3 text-gray-300 max-w-40 truncate">
                  <Link to={`/companies/${c.company_id}`} className="hover:text-white">
                    {c.empresa_nombre}
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs text-gray-500">
                    {c.modalidad?.replace(/_/g, ' ') || '—'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-mono font-medium text-white">
                  {fmt(c.monto_original)}
                </td>
                <td className="px-4 py-3 text-center">
                  {c.num_adendas > 0 ? (
                    <span className="badge-yellow">{c.num_adendas}</span>
                  ) : <span className="text-gray-600">—</span>}
                </td>
                <td className="px-4 py-3 text-center">
                  <div className="flex items-center justify-center gap-1">
                    {c.es_mayor_100m && <span title=">RD$100M" className="badge-red">$</span>}
                    {c.financiado_prestamo && <span title="Financiado préstamo" className="badge-blue">P</span>}
                    {c.incremento_porcentual >= 25 && (
                      <span title={`+${c.incremento_porcentual}%`}>
                        <AlertTriangle size={12} className="text-yellow-400" />
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-xs text-gray-500">
                  {c.fecha_firma ? new Date(c.fecha_firma).toLocaleDateString('es-DO') : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Paginación */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-400">
          <span>Página {page} de {data.pages} ({data.total.toLocaleString()} registros)</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="btn-ghost disabled:opacity-40"
            >← Anterior</button>
            <button
              onClick={() => setPage(p => Math.min(data.pages, p + 1))}
              disabled={page === data.pages}
              className="btn-ghost disabled:opacity-40"
            >Siguiente →</button>
          </div>
        </div>
      )}
    </div>
  )
}
