import { useState } from 'react'
import { Database, Play, Upload, CheckCircle, XCircle, Clock } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { etlApi } from '../services/api'
import { useApi } from '../hooks/useApi'
import toast from 'react-hot-toast'

const SOURCES = [
  { id: 'hacienda',        label: 'Ministerio de Hacienda',     desc: 'Instituciones y presupuesto anual' },
  { id: 'credito_publico', label: 'Crédito Público',            desc: 'Préstamos internacionales y bonos' },
  { id: 'idecoop',         label: 'IDECOOP — Cooperativas',     desc: 'Registro nacional de cooperativas + cruce con DGCP' },
  { id: 'sib',             label: 'SIB — Bancos',               desc: 'Superintendencia de Bancos + fondos del Estado' },
  { id: 'jce',             label: 'JCE — Partidos Políticos',   desc: 'Financiamiento público + gastos declarados Ley 33-18' },
  { id: 'dgcp',            label: 'DGCP — Contrataciones',      desc: 'Contratos y procesos de compra' },
]

export default function ETLPanel() {
  const [selected, setSelected] = useState<string[]>(['hacienda', 'credito_publico', 'dgcp'])
  const [running, setRunning] = useState(false)
  const { data: status, reload } = useApi(() => etlApi.status(), [])

  const toggleSource = (id: string) =>
    setSelected(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id])

  const handleRun = async () => {
    if (!selected.length) { toast.error('Selecciona al menos una fuente'); return }
    setRunning(true)
    const t = toast.loading('Iniciando pipeline ETL...')
    try {
      const r = await etlApi.run(selected)
      toast.success(r.message || 'Pipeline iniciado', { id: t })
      setTimeout(reload, 2000)
    } catch { toast.error('Error iniciando pipeline', { id: t }) }
    finally { setRunning(false) }
  }

  const lastResult = status?.last_result

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title="Panel de Datos / ETL"
        subtitle="Importar y actualizar datos desde fuentes gubernamentales"
      />

      {/* Estado del pipeline */}
      <div className={`card flex items-center gap-3 ${status?.running ? 'border-yellow-700' : 'border-gray-800'}`}>
        {status?.running ? (
          <><Clock size={16} className="text-yellow-400 animate-pulse" /><span className="text-yellow-400 font-medium">Pipeline en ejecución...</span></>
        ) : (
          <><CheckCircle size={16} className="text-green-400" /><span className="text-gray-400">Pipeline inactivo</span></>
        )}
        {status?.last_run && (
          <span className="text-xs text-gray-600 ml-auto">
            Última ejecución: {new Date(status.last_run).toLocaleString('es-DO')}
          </span>
        )}
      </div>

      {/* Selección de fuentes */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white mb-4">Fuentes de Datos</h3>
        <div className="space-y-3">
          {SOURCES.map(src => (
            <label key={src.id} className={`flex items-center gap-4 p-3 rounded-xl border cursor-pointer transition-colors ${
              selected.includes(src.id)
                ? 'border-gov-600 bg-gov-900/20'
                : 'border-gray-800 hover:border-gray-700'
            }`}>
              <input
                type="checkbox"
                checked={selected.includes(src.id)}
                onChange={() => toggleSource(src.id)}
                className="accent-gov-500 w-4 h-4"
              />
              <div className="flex-1">
                <p className="text-sm font-medium text-white">{src.label}</p>
                <p className="text-xs text-gray-500">{src.desc}</p>
              </div>
              {selected.includes(src.id) && <CheckCircle size={16} className="text-gov-400" />}
            </label>
          ))}
        </div>

        <button
          onClick={handleRun}
          disabled={running || status?.running || !selected.length}
          className="btn-primary w-full mt-4 flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <Play size={16} /> {running ? 'Iniciando...' : 'Ejecutar Pipeline ETL'}
        </button>
      </div>

      {/* Resultado previo */}
      {lastResult && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-3">Último Resultado</h3>
          <div className="space-y-2">
            {Object.entries(lastResult).map(([source, result]: [string, any]) => (
              <div key={source} className="flex items-center gap-3 p-2 bg-gray-800 rounded-lg">
                {result.status === 'ok'
                  ? <CheckCircle size={14} className="text-green-400" />
                  : <XCircle size={14} className="text-red-400" />}
                <span className="text-sm text-white">{source}</span>
                {result.status === 'ok'
                  ? <span className="text-xs text-green-400 ml-auto">{result.records} registros</span>
                  : <span className="text-xs text-red-400 ml-auto truncate max-w-48">{result.error}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Carga manual */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white mb-3">Importar Archivo Manual</h3>
        <p className="text-xs text-gray-500 mb-4">
          Sube un archivo Excel (.xlsx) o CSV con contratos para importarlos directamente.
          Formatos soportados: DGCP estándar, Hacienda, formato libre.
        </p>
        <label className="flex flex-col items-center justify-center gap-3 border-2 border-dashed border-gray-700 rounded-xl p-8 cursor-pointer hover:border-gov-600 transition-colors">
          <Upload size={24} className="text-gray-500" />
          <span className="text-sm text-gray-400">Arrastra un archivo o haz clic para seleccionar</span>
          <span className="text-xs text-gray-600">Excel (.xlsx), CSV, PDF de contrato</span>
          <input
            type="file"
            className="hidden"
            accept=".xlsx,.xls,.csv,.pdf"
            onChange={async (e) => {
              const file = e.target.files?.[0]
              if (!file) return
              const form = new FormData()
              form.append('file', file)
              const endpoint = file.name.endsWith('.pdf') ? '/api/etl/upload/pdf' : '/api/etl/upload/contracts'
              const t = toast.loading(`Procesando ${file.name}...`)
              try {
                const resp = await fetch(endpoint, { method: 'POST', body: form })
                const data = await resp.json()
                if (data.error) { toast.error(data.error, { id: t }); return }
                toast.success(
                  file.name.endsWith('.pdf')
                    ? `PDF procesado: ${data.text_length} caracteres extraídos`
                    : `${data.records_parsed} registros procesados`,
                  { id: t }
                )
              } catch { toast.error('Error al procesar archivo', { id: t }) }
            }}
          />
        </label>
      </div>

      {/* Fuentes adicionales info */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white mb-3">Fuentes Adicionales (Descarga Manual)</h3>
        <div className="space-y-2 text-sm">
          {[
            { label: 'DGCP Portal Transaccional', url: 'https://www.dgcp.gob.do', desc: 'Contratos y procesos en tiempo real' },
            { label: 'Datos Abiertos Hacienda', url: 'https://datos.hacienda.gob.do', desc: 'Ejecución presupuestaria, pagos' },
            { label: 'Crédito Público', url: 'https://www.creditopublico.gob.do', desc: 'Préstamos y bonos soberanos' },
            { label: 'Cámara de Cuentas', url: 'https://www.camaradecuentas.gob.do', desc: 'Informes de auditoría' },
            { label: 'Portal Transparencia MOPC', url: 'https://www.mopc.gob.do', desc: 'Contratos de obras públicas' },
            { label: 'INAPA Transparencia', url: 'https://www.inapa.gob.do', desc: 'Contratos y proyectos INAPA' },
          ].map(src => (
            <div key={src.url} className="flex items-center gap-3 p-2 hover:bg-gray-800 rounded-lg">
              <div className="flex-1">
                <span className="text-white text-xs font-medium">{src.label}</span>
                <p className="text-xs text-gray-500">{src.desc}</p>
              </div>
              <a href={src.url} target="_blank" rel="noopener noreferrer"
                 className="text-xs text-gov-400 hover:text-gov-300 whitespace-nowrap">
                Visitar →
              </a>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
