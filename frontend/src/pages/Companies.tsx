import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, TrendingUp } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { companiesApi, Company, PagedResponse } from '../services/api'
import { useApi } from '../hooks/useApi'

const fmt = (n: number) => {
  if (n >= 1_000_000_000) return `RD$${(n / 1_000_000_000).toFixed(2)}B`
  if (n >= 1_000_000) return `RD$${(n / 1_000_000).toFixed(1)}M`
  return `RD$${n.toLocaleString()}`
}

export default function Companies() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [minContratos, setMinContratos] = useState('')

  const params = {
    page, size: 50,
    ...(search && { search }),
    ...(minContratos && { min_contratos: minContratos }),
    order_by: 'total_monto_recibido',
  }

  const { data, loading } = useApi<PagedResponse<Company>>(
    () => companiesApi.list(params),
    [page, search, minContratos],
  )

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title="Empresas Contratistas"
        subtitle={data ? `${data.total.toLocaleString()} empresas en la base de datos` : 'Cargando...'}
      />

      <div className="card flex gap-3 items-center">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            className="input pl-8"
            placeholder="Buscar por nombre o RNC..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
          />
        </div>
        <input
          type="number"
          className="input w-40"
          placeholder="Mín. contratos"
          value={minContratos}
          onChange={e => { setMinContratos(e.target.value); setPage(1) }}
        />
      </div>

      <div className="card p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-left">
              <th className="px-4 py-3 text-gray-400 font-medium">#</th>
              <th className="px-4 py-3 text-gray-400 font-medium">Empresa</th>
              <th className="px-4 py-3 text-gray-400 font-medium">RNC</th>
              <th className="px-4 py-3 text-gray-400 font-medium">Sector</th>
              <th className="px-4 py-3 text-gray-400 font-medium text-right">Monto Total</th>
              <th className="px-4 py-3 text-gray-400 font-medium text-center">Contratos</th>
              <th className="px-4 py-3 text-gray-400 font-medium text-center">Instituciones</th>
              <th className="px-4 py-3 text-gray-400 font-medium text-center">Concentración</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-500">Cargando...</td></tr>
            ) : data?.items.map((c, i) => (
              <tr key={c.id} className="table-row">
                <td className="px-4 py-3 text-gray-600 text-xs font-mono">
                  {(page - 1) * 50 + i + 1}
                </td>
                <td className="px-4 py-3">
                  <Link to={`/companies/${c.id}`} className="text-white hover:text-gov-300 font-medium">
                    {c.nombre}
                  </Link>
                  {c.nombre_comercial && c.nombre_comercial !== c.nombre && (
                    <p className="text-xs text-gray-500">{c.nombre_comercial}</p>
                  )}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-gray-400">{c.rnc || '—'}</td>
                <td className="px-4 py-3 text-xs text-gray-500">{c.sector || '—'}</td>
                <td className="px-4 py-3 text-right font-mono font-semibold text-white">
                  {fmt(c.total_monto_recibido)}
                </td>
                <td className="px-4 py-3 text-center">
                  <span className="badge-blue">{c.total_contratos}</span>
                </td>
                <td className="px-4 py-3 text-center text-gray-400 text-xs">{c.total_instituciones}</td>
                <td className="px-4 py-3 text-center">
                  {c.indice_concentracion == null ? (
                    <span className="text-gray-600 text-xs">—</span>
                  ) : c.indice_concentracion > 80 ? (
                    <span className="badge-red">{c.indice_concentracion.toFixed(0)}%</span>
                  ) : c.indice_concentracion > 50 ? (
                    <span className="badge-yellow">{c.indice_concentracion.toFixed(0)}%</span>
                  ) : (
                    <span className="text-gray-600 text-xs">{c.indice_concentracion.toFixed(0)}%</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && data.pages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-400">
          <span>Página {page} de {data.pages}</span>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn-ghost disabled:opacity-40">← Anterior</button>
            <button onClick={() => setPage(p => Math.min(data.pages, p + 1))} disabled={page === data.pages} className="btn-ghost disabled:opacity-40">Siguiente →</button>
          </div>
        </div>
      )}
    </div>
  )
}
