import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, AlertTriangle, FileText, ExternalLink, Copy, Check } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { contractsApi, aiApi } from '../services/api'
import { useApi } from '../hooks/useApi'
import { useState } from 'react'

const fmt = (n: number) => n >= 1e6 ? `RD$${(n/1e6).toFixed(2)}M` : `RD$${n?.toLocaleString()}`

export default function ContractDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: c, loading } = useApi(() => contractsApi.get(Number(id)), [id])
  const [analysis, setAnalysis] = useState<any>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [copied, setCopied] = useState(false)

  const copyCode = () => {
    if (c?.numero_contrato) {
      navigator.clipboard.writeText(c.numero_contrato)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // Genera URLs de consulta según la fuente del contrato
  const buildSourceLinks = (contrato: typeof c) => {
    if (!contrato) return []
    const links: { label: string; url: string; primary?: boolean }[] = []
    const isBulkDGCP = contrato.fuente?.includes('DGCP') || contrato.fuente?.includes('Adjudicaciones SECP')
    const hasSpecificUrl = contrato.url_fuente &&
      !contrato.url_fuente.includes('adjudicaciones-secp.csv') &&
      !contrato.url_fuente.includes('new_dg')

    if (hasSpecificUrl) {
      links.push({ label: contrato.fuente || 'Ver fuente original', url: contrato.url_fuente!, primary: true })
    }
    if (isBulkDGCP && contrato.numero_contrato) {
      links.push({
        label: 'Buscar en Portal DGCP',
        url: `https://www.dgcp.gob.do/index.php/proceso?buscar=${encodeURIComponent(contrato.numero_contrato)}`,
        primary: !hasSpecificUrl,
      })
      links.push({
        label: 'Ver dataset en Datos Abiertos',
        url: 'https://datos.gob.do/dataset/adjudicaciones-secp',
      })
    }
    if (!isBulkDGCP && !hasSpecificUrl) {
      links.push({ label: contrato.fuente || 'Fuente no disponible', url: '#' })
    }
    return links
  }

  const runAnalysis = async () => {
    setAnalyzing(true)
    try { setAnalysis(await aiApi.analyzeContract(Number(id))) }
    finally { setAnalyzing(false) }
  }

  if (loading) return <div className="p-6 text-gray-500">Cargando...</div>
  if (!c) return <div className="p-6 text-gray-500">Contrato no encontrado</div>

  const riskColors: Record<string, string> = { BAJO: 'text-green-400', MEDIO: 'text-yellow-400', ALTO: 'text-red-400' }

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title={c.numero_contrato || `Contrato #${c.id}`}
        subtitle={c.institucion_nombre}
        actions={
          <div className="flex gap-2">
            <Link to="/contracts" className="btn-ghost flex items-center gap-1.5"><ArrowLeft size={14} /> Volver</Link>
            <button onClick={runAnalysis} disabled={analyzing} className="btn-primary flex items-center gap-1.5">
              <FileText size={14} /> {analyzing ? 'Analizando...' : 'Analizar IA'}
            </button>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Info principal */}
        <div className="lg:col-span-2 space-y-4">
          <div className="card">
            <h3 className="text-sm font-semibold text-white mb-3">Información General</h3>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              {[
                ['Número', c.numero_contrato],
                ['Proceso', c.numero_proceso],
                ['Institución', c.institucion_nombre],
                ['Empresa', c.empresa_nombre],
                ['RNC', c.empresa_rnc],
                ['Modalidad', c.modalidad?.replace(/_/g, ' ')],
                ['Estado', c.estado],
                ['Moneda', c.moneda],
                ['Funcionario Firmante', c.oficial_firmante],
                ['Fecha Firma', c.fecha_firma ? new Date(c.fecha_firma).toLocaleDateString('es-DO') : '—'],
                ['Fecha Inicio', c.fecha_inicio ? new Date(c.fecha_inicio).toLocaleDateString('es-DO') : '—'],
                ['Fecha Fin Planificada', c.fecha_fin_planificada ? new Date(c.fecha_fin_planificada).toLocaleDateString('es-DO') : '—'],
              ].map(([k, v]) => v ? (
                <div key={k}>
                  <dt className="text-xs text-gray-500">{k}</dt>
                  <dd className="text-white font-medium truncate">{v}</dd>
                </div>
              ) : null)}
            </dl>
            {c.descripcion && (
              <div className="mt-4 pt-4 border-t border-gray-800">
                <p className="text-xs text-gray-500 mb-1">Descripción / Objeto</p>
                <p className="text-sm text-gray-300">{c.descripcion || c.objeto}</p>
              </div>
            )}
          </div>

          {/* Montos */}
          <div className="card">
            <h3 className="text-sm font-semibold text-white mb-3">Montos</h3>
            <div className="grid grid-cols-3 gap-4">
              {[
                ['Original', c.monto_original, 'text-white'],
                ['Actual', c.monto_actual, c.monto_actual > c.monto_original ? 'text-yellow-400' : 'text-white'],
                ['Pagado', c.monto_pagado, 'text-green-400'],
              ].map(([label, val, cls]) => (
                <div key={label as string} className="text-center">
                  <p className="text-xs text-gray-500">{label as string}</p>
                  <p className={`text-lg font-bold font-mono ${cls as string}`}>{fmt(val as number)}</p>
                </div>
              ))}
            </div>
            {c.incremento_porcentual > 0 && (
              <div className="mt-3 flex items-center gap-2 text-yellow-400 text-sm">
                <AlertTriangle size={14} />
                Incremento del {c.incremento_porcentual.toFixed(1)}% respecto al monto original
              </div>
            )}
          </div>

          {/* Adendas */}
          {(c as any).adendas?.length > 0 && (
            <div className="card">
              <h3 className="text-sm font-semibold text-white mb-3">Adendas ({(c as any).adendas.length})</h3>
              <div className="space-y-2">
                {(c as any).adendas.map((a: any) => (
                  <div key={a.id} className="flex items-start gap-3 p-3 bg-gray-800 rounded-lg text-sm">
                    <span className="badge-yellow w-6 h-6 flex items-center justify-center text-xs">{a.numero}</span>
                    <div className="flex-1">
                      <p className="text-gray-300">{a.descripcion || 'Sin descripción'}</p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {a.monto_adicional > 0 && `+${fmt(a.monto_adicional)} `}
                        {a.dias_adicionales > 0 && `+${a.dias_adicionales} días`}
                        {a.fecha && ` · ${new Date(a.fecha).toLocaleDateString('es-DO')}`}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Flags */}
          <div className="card">
            <h3 className="text-sm font-semibold text-white mb-3">Indicadores de Riesgo</h3>
            <div className="space-y-2">
              {[
                [c.es_mayor_100m, 'Contrato >RD$100M', 'badge-red'],
                [c.financiado_prestamo, 'Financiado con préstamo', 'badge-blue'],
                [c.tiene_adendas, `${c.num_adendas ?? 0} adenda(s)`, 'badge-yellow'],
                [c.incremento_porcentual != null && c.incremento_porcentual >= 25, `Incremento ${(c.incremento_porcentual ?? 0).toFixed(0)}%`, 'badge-yellow'],
                [c.retraso_dias > 0, `Retraso ${c.retraso_dias ?? 0} días`, 'badge-red'],
                [c.modalidad === 'contratacion_directa', 'Contratación directa', 'badge-yellow'],
              ].filter(([cond]) => cond).map(([_, label, cls]) => (
                <span key={label as string} className={`block ${cls as string}`}>{label as string}</span>
              ))}
              {!c.es_mayor_100m && !c.tiene_adendas && !c.financiado_prestamo && (
                <p className="text-xs text-gray-500">Sin indicadores de riesgo</p>
              )}
            </div>
          </div>

          {/* Links */}
          <div className="card space-y-2">
            <Link to={`/companies/${c.company_id}`} className="btn-ghost w-full text-center block">
              Ver empresa →
            </Link>
            <Link to={`/institutions/${c.institution_id}`} className="btn-ghost w-full text-center block">
              Ver institución →
            </Link>

            {/* Fuente / código de contrato */}
            {c.numero_contrato && (
              <div className="pt-2 border-t border-gray-800">
                <p className="text-xs text-gray-500 mb-2">Código de contrato</p>
                <div className="flex items-center gap-2 bg-gray-800 rounded px-3 py-2">
                  <code className="text-xs text-gray-300 flex-1 truncate">{c.numero_contrato}</code>
                  <button onClick={copyCode} className="shrink-0 text-gray-500 hover:text-gray-200 transition-colors">
                    {copied ? <Check size={13} className="text-green-400" /> : <Copy size={13} />}
                  </button>
                </div>
              </div>
            )}

            {c.fuente && (
              <div className="pt-2 border-t border-gray-800 space-y-1.5">
                <p className="text-xs text-gray-500">Fuente de datos</p>
                <p className="text-xs text-gray-400 leading-relaxed">{c.fuente}</p>
                {buildSourceLinks(c).map((link, i) => (
                  link.url === '#'
                    ? <span key={i} className="text-xs text-gray-600 block">Sin enlace directo disponible</span>
                    : <a key={i} href={link.url} target="_blank" rel="noopener noreferrer"
                        className={`flex items-center gap-1.5 text-xs w-full px-3 py-2 rounded transition-colors ${
                          link.primary
                            ? 'bg-gov-900/40 text-gov-300 hover:bg-gov-900/60 border border-gov-800/40'
                            : 'bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700'
                        }`}>
                        <ExternalLink size={11} className="shrink-0" />
                        {link.label}
                      </a>
                ))}
              </div>
            )}
          </div>

          {/* Análisis IA */}
          {analysis && (
            <div className="card">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-white">Análisis IA</h3>
                <span className={`font-bold text-sm ${riskColors[analysis.risk_level]}`}>
                  {analysis.risk_level}
                </span>
              </div>
              <div className="text-xs text-gray-400 mb-2">Score: {analysis.risk_score}/100</div>
              <div className="w-full bg-gray-800 rounded-full h-2 mb-3">
                <div
                  className={`h-2 rounded-full ${analysis.risk_score >= 60 ? 'bg-red-500' : analysis.risk_score >= 30 ? 'bg-yellow-500' : 'bg-green-500'}`}
                  style={{ width: `${analysis.risk_score}%` }}
                />
              </div>
              {analysis.flags.length > 0 && (
                <ul className="space-y-1">
                  {analysis.flags.map((f: string, i: number) => (
                    <li key={i} className="flex items-center gap-1.5 text-xs text-yellow-300">
                      <AlertTriangle size={10} /> {f}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
