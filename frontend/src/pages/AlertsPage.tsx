import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Bell, CheckCircle, XCircle, RefreshCw, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'
import PageHeader from '../components/PageHeader'
import { alertsApi, Alert, PagedResponse } from '../services/api'
import { useApi } from '../hooks/useApi'
import toast from 'react-hot-toast'

const SEVERITY_BADGE: Record<string, string> = {
  critica: 'badge-red',
  alta:    'badge-red',
  media:   'badge-yellow',
  baja:    'badge-blue',
}

const fmt = (n: number) => n >= 1e6 ? `RD$${(n/1e6).toFixed(1)}M` : `RD$${n?.toLocaleString()}`

export default function AlertsPage() {
  const [searchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [severidad, setSeveridad] = useState(searchParams.get('severidad') ?? '')
  const [tipo, setTipo] = useState(searchParams.get('tipo') ?? '')
  const [soloNoRevisadas, setSoloNoRevisadas] = useState(searchParams.get('revisada') === 'false')

  const params = { page, size: 50, ...(severidad && { severidad }), ...(tipo && { tipo }), ...(soloNoRevisadas && { revisada: false }) }
  const { data, loading, reload } = useApi<PagedResponse<Alert>>(() => alertsApi.list(params), [page, severidad, tipo, soloNoRevisadas])
  const { data: stats } = useApi(() => alertsApi.stats(), [])

  const handleScan = async () => {
    const t = toast.loading('Escaneando alertas...')
    try {
      const r = await alertsApi.scan()
      toast.success(`${r.count} alertas generadas`, { id: t })
      reload()
    } catch { toast.error('Error en el scan', { id: t }) }
  }

  const handleReview = async (id: number) => {
    await alertsApi.review(id)
    toast.success('Alerta marcada como revisada')
    reload()
  }

  const handleDiscard = async (id: number) => {
    await alertsApi.discard(id)
    toast.success('Alerta descartada')
    reload()
  }

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title="Alertas de Riesgo"
        subtitle="Patrones detectados automáticamente en contratos y empresas"
        actions={
          <button onClick={handleScan} className="btn-primary flex items-center gap-2">
            <RefreshCw size={14} /> Escanear Ahora
          </button>
        }
      />

      {/* Stats chips */}
      {stats && (
        <div className="flex flex-wrap gap-3">
          <div className="card py-2 px-4 flex items-center gap-2">
            <Bell size={14} className="text-gov-400" />
            <span className="text-sm text-white font-semibold">{stats.total}</span>
            <span className="text-xs text-gray-500">total</span>
          </div>
          <div className="card py-2 px-4 flex items-center gap-2">
            <AlertTriangle size={14} className="text-red-400" />
            <span className="text-sm text-white font-semibold">{stats.criticas}</span>
            <span className="text-xs text-gray-500">críticas</span>
          </div>
          <div className="card py-2 px-4 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-yellow-400" />
            <span className="text-sm text-white font-semibold">{stats.no_revisadas}</span>
            <span className="text-xs text-gray-500">sin revisar</span>
          </div>
          {stats.por_tipo?.map((t: any) => (
            <button
              key={t.tipo}
              onClick={() => { setTipo(v => v === t.tipo ? '' : t.tipo); setPage(1) }}
              className={clsx(
                'card py-2 px-4 text-xs transition-colors cursor-pointer',
                tipo === t.tipo ? 'border-gov-600 text-gov-300 bg-gov-900/20' : 'text-gray-400 hover:text-white hover:bg-gray-800',
              )}
            >
              {t.tipo.replace(/_/g, ' ')}: <span className="text-white">{t.cantidad}</span>
            </button>
          ))}
        </div>
      )}

      {/* Filtros */}
      <div className="card flex gap-3 items-center">
        <select className="input w-auto" value={severidad} onChange={e => setSeveridad(e.target.value)}>
          <option value="">Todas las severidades</option>
          <option value="critica">Crítica</option>
          <option value="alta">Alta</option>
          <option value="media">Media</option>
          <option value="baja">Baja</option>
        </select>
        <label className="flex items-center gap-1.5 text-sm text-gray-400 cursor-pointer">
          <input type="checkbox" checked={soloNoRevisadas} onChange={e => setSoloNoRevisadas(e.target.checked)} className="accent-gov-500" />
          Solo sin revisar
        </label>
      </div>

      {/* Lista */}
      <div className="space-y-3">
        {loading ? (
          <div className="card text-center text-gray-500 py-8">Cargando alertas...</div>
        ) : data?.items.length === 0 ? (
          <div className="card text-center text-gray-500 py-12">
            <CheckCircle size={32} className="mx-auto mb-2 text-green-500 opacity-50" />
            No hay alertas activas
          </div>
        ) : data?.items.map(a => (
          <div key={a.id} className={`card flex items-start gap-4 ${a.revisada ? 'opacity-60' : ''}`}>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className={SEVERITY_BADGE[a.severidad] || 'badge-blue'}>{a.severidad}</span>
                <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">
                  {a.tipo.replace(/_/g, ' ')}
                </span>
                {a.revisada && <span className="badge-green">revisada</span>}
              </div>
              <p className="text-white font-medium">{a.titulo}</p>
              <p className="text-sm text-gray-400 mt-0.5">{a.descripcion}</p>
              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                {a.monto_involucrado > 0 && (
                  <span className="text-yellow-400 font-mono">{fmt(a.monto_involucrado)}</span>
                )}
                <span>{a.entidad_tipo} #{a.entidad_id}</span>
                <span>{new Date(a.created_at).toLocaleDateString('es-DO')}</span>
              </div>
            </div>
            {!a.revisada && (
              <div className="flex gap-2 flex-shrink-0">
                <button
                  onClick={() => handleReview(a.id)}
                  className="btn-ghost text-green-400 hover:text-green-300 flex items-center gap-1 text-xs"
                >
                  <CheckCircle size={14} /> Revisar
                </button>
                <button
                  onClick={() => handleDiscard(a.id)}
                  className="btn-ghost text-gray-500 hover:text-gray-400 flex items-center gap-1 text-xs"
                >
                  <XCircle size={14} /> Descartar
                </button>
              </div>
            )}
          </div>
        ))}
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
