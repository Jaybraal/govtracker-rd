import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { cooperativesApi } from '../services/api'
import { useApi } from '../hooks/useApi'

const fmt = (n: number) => {
  if (!n) return 'RD$0'
  if (n >= 1e9) return `RD$${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6) return `RD$${(n / 1e6).toFixed(0)}M`
  return `RD$${n.toLocaleString()}`
}

const TIPO_LABEL: Record<string, string> = {
  ahorro_credito:       '💰 Ahorro y Crédito',
  agropecuaria:         '🌾 Agropecuaria',
  consumo:              '🛒 Consumo',
  vivienda:             '🏠 Vivienda',
  servicios_multiples:  '🔧 Servicios Múltiples',
  escolar:              '📚 Escolar/Universitaria',
  transporte:           '🚌 Transporte',
  salud:                '🏥 Salud',
  produccion:           '🏭 Producción',
  otro:                 '📦 Otro',
}

export default function CooperativeDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: c, loading } = useApi(() => cooperativesApi.get(Number(id)), [id])

  if (loading) return <div className="p-6 text-gray-500">Cargando...</div>
  if (!c) return <div className="p-6 text-gray-500">Cooperativa no encontrada</div>

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title={c.nombre}
        subtitle={`${TIPO_LABEL[c.tipo] || c.tipo || ''}${c.provincia ? ' · ' + c.provincia : ''}`}
        actions={
          <Link to="/cooperatives" className="btn-ghost flex items-center gap-1.5"><ArrowLeft size={14} /> Volver</Link>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          ['Socios', c.num_socios?.toLocaleString() || '—'],
          ['Activos Totales', fmt(c.activos_totales)],
          ['Patrimonio', fmt(c.patrimonio)],
          ['Contratos del Estado', `${c.total_contratos_estado || 0} (${fmt(c.total_monto_contratos)})`],
        ].map(([label, value]) => (
          <div key={label} className="card text-center">
            <p className="text-xs text-gray-500 mb-1">{label}</p>
            <p className="text-xl font-bold text-white">{value}</p>
          </div>
        ))}
      </div>

      <div className="card">
        <h3 className="text-sm font-semibold text-white mb-3">Información</h3>
        <dl className="space-y-2 text-sm">
          {[
            ['Siglas', c.siglas],
            ['RNC', c.rnc],
            ['Número de Registro', c.numero_registro],
            ['Estado', c.estado],
            ['Municipio', c.municipio],
            ['Teléfono', c.telefono],
            ['Email', c.email],
            ['Gerente General', c.gerente_general],
            ['Presidente del Consejo', c.presidente_consejo],
            ['Capital Social', c.capital_social ? fmt(c.capital_social) : null],
            ['Cartera de Créditos', c.cartera_creditos ? fmt(c.cartera_creditos) : null],
            ['Depósitos', c.depositos ? fmt(c.depositos) : null],
            ['Ingresos', c.ingresos ? fmt(c.ingresos) : null],
            ['Excedentes', c.excedentes ? fmt(c.excedentes) : null],
            ['Año del Balance', c.anio_balance],
            ['Recibe Subsidio del Estado', c.recibe_subsidio_estado ? 'Sí' : null],
            ['Fuente', c.fuente],
          ].filter(([_, v]) => v).map(([k, v]) => (
            <div key={k as string} className="flex justify-between gap-3">
              <dt className="text-gray-500 shrink-0">{k as string}</dt>
              <dd className="text-white text-right">{v as string}</dd>
            </div>
          ))}
          {c.fecha_constitucion && (
            <div className="flex justify-between">
              <dt className="text-gray-500">Fecha de Constitución</dt>
              <dd className="text-white">{new Date(c.fecha_constitucion).toLocaleDateString('es-DO')}</dd>
            </div>
          )}
          {c.url_fuente && (
            <div className="flex justify-between">
              <dt className="text-gray-500">Enlace</dt>
              <dd><a href={c.url_fuente} target="_blank" rel="noopener noreferrer" className="text-gov-400 hover:text-gov-300 text-xs">Ver fuente original →</a></dd>
            </div>
          )}
        </dl>
      </div>

      {c.contratos_estado?.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-3">Contratos del Estado ({c.contratos_estado.length})</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left">
                  <th className="py-2 px-3 text-gray-400 font-medium">Número</th>
                  <th className="py-2 px-3 text-gray-400 font-medium">Descripción</th>
                  <th className="py-2 px-3 text-gray-400 font-medium text-right">Monto</th>
                </tr>
              </thead>
              <tbody>
                {c.contratos_estado.map((ct: any) => (
                  <tr key={ct.id} className="table-row">
                    <td className="py-2 px-3">
                      <Link to={`/contracts/${ct.id}`} className="text-gov-400 hover:text-gov-300 font-mono text-xs">
                        {ct.numero || `#${ct.id}`}
                      </Link>
                    </td>
                    <td className="py-2 px-3 text-xs text-gray-400 max-w-96 truncate">{ct.descripcion}</td>
                    <td className="py-2 px-3 text-right font-mono text-white">{fmt(ct.monto)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
