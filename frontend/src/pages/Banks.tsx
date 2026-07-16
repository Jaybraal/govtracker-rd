import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Landmark, Shield, TrendingUp } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import { useApi } from '../hooks/useApi'
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// `null`/`undefined` ("sin dato") y `0` ("de verdad cero") no son lo mismo —
// antes esta función los confundía y mostraba "RD$0" en columnas como
// Depósitos donde en realidad SIB nunca publicó el dato para ningún banco,
// haciendo que la tabla entera se viera rota.
const fmt = (n: number | null | undefined) => {
  if (n == null) return 'sin dato'
  if (n === 0) return 'RD$0'
  if (n >= 1e12) return `RD$${(n / 1e12).toFixed(2)}T`
  if (n >= 1e9) return `RD$${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6) return `RD$${(n / 1e6).toFixed(1)}M`
  return `RD$${n.toLocaleString()}`
}

const TIPO_LABEL: Record<string, string> = {
  banco_multiple:       '🏦 Banco Múltiple',
  banco_ahorro_credito: '💳 Banco A&C',
  banco_credito:        '📋 Banco Crédito',
  asociacion_ahorro:    '🏠 Asoc. A&P',
  banco_estatal:        '🏛 Banco Estatal',
  banco_extranjero:     '🌐 Banco Extranjero',
}

const MORA_COLOR = (p: number) => p < 2 ? '#10b981' : p < 4 ? '#f59e0b' : '#ef4444'

export default function Banks() {
  const [selectedBank, setSelectedBank] = useState<any>(null)

  const { data: banks, loading } = useApi(() => api.get('/banks/').then(r => r.data), [])
  const { data: stats }          = useApi(() => api.get('/banks/stats').then(r => r.data), [])

  return (
    <div className="p-6 space-y-5">
      <PageHeader
        title="Sistema Bancario Dominicano"
        subtitle="Bancos autorizados por la Superintendencia de Bancos"
      />

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <StatCard label="Total Bancos" value={stats.total_bancos.toString()} icon={<Landmark size={16} />} color="blue" />
          <StatCard label="Activos del Sistema" value={fmt(stats.total_activos_sistema)} icon={<TrendingUp size={16} />} color="purple" />
          <StatCard label="Bancos Estatales" value={(stats.por_tipo?.find((t: any) => t.tipo === 'banco_estatal')?.cantidad ?? 0).toString()} icon={<Shield size={16} />} color="yellow" />
        </div>
      )}

      {/* Gráfico activos */}
      {banks && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-4">Activos Totales por Banco (RD$)</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={banks.slice(0, 10)} layout="vertical" margin={{ left: 10, right: 30 }}>
              <XAxis type="number" tickFormatter={v => `${(v / 1e9).toFixed(0)}B`} tick={{ fill: '#6b7280', fontSize: 10 }} />
              <YAxis type="category" dataKey="nombre_corto" tick={{ fill: '#9ca3af', fontSize: 10 }} width={100} />
              <Tooltip formatter={(v: number) => fmt(v)} contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }} />
              <Bar dataKey="activos_totales" radius={[0, 4, 4, 0]}>
                {(banks || []).slice(0, 10).map((b: any, i: number) => (
                  <Cell key={i} fill={b.es_estatal ? '#f59e0b' : '#6366f1'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-2 text-xs text-gray-500">
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-yellow-500" /> Estatal</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-gov-500" /> Privado</span>
          </div>
        </div>
      )}

      {/* Tabla completa */}
      <div className="card p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-left">
              <th className="px-4 py-3 text-gray-400 font-medium">#</th>
              <th className="px-4 py-3 text-gray-400 font-medium">Banco</th>
              <th className="px-4 py-3 text-gray-400 font-medium">Tipo</th>
              <th className="px-4 py-3 text-gray-400 font-medium text-right">Activos</th>
              <th className="px-4 py-3 text-gray-400 font-medium text-right">Cartera</th>
              <th className="px-4 py-3 text-gray-400 font-medium text-center">Empleados</th>
              <th className="px-4 py-3 text-gray-400 font-medium text-center">Sucursales</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">Cargando...</td></tr>
            ) : (banks || []).map((b: any, i: number) => (
              <tr key={b.id} className={`table-row cursor-pointer ${b.es_estatal ? 'bg-yellow-950/5' : ''}`}
                  onClick={() => setSelectedBank(b)}>
                <td className="px-4 py-2.5 text-xs text-gray-600 font-mono">{i + 1}</td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    {b.es_estatal && <Shield size={12} className="text-yellow-400 flex-shrink-0" />}
                    <div>
                      <p className="text-white font-medium text-sm">{b.nombre_corto || b.nombre}</p>
                      <p className="text-xs text-gray-500">{b.pais_origen} · f. {b.ano_fundacion}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-2.5 text-xs text-gray-500">{TIPO_LABEL[b.tipo] || b.tipo}</td>
                <td className="px-4 py-2.5 text-right font-mono text-white">{fmt(b.activos_totales)}</td>
                <td className="px-4 py-2.5 text-right font-mono text-gray-400">{fmt(b.cartera_creditos)}</td>
                <td className="px-4 py-2.5 text-center text-xs text-gray-400">
                  {b.num_empleados != null ? b.num_empleados.toLocaleString() : 'sin dato'}
                </td>
                <td className="px-4 py-2.5 text-center text-xs text-gray-400">
                  {b.num_sucursales != null ? b.num_sucursales.toLocaleString() : 'sin dato'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Detalle banco seleccionado */}
      {selectedBank && (
        <div className="card border-gov-700">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="font-bold text-white text-lg">{selectedBank.nombre}</h3>
              <p className="text-xs text-gray-500">{selectedBank.codigo_sib} · {TIPO_LABEL[selectedBank.tipo]}</p>
            </div>
            <button onClick={() => setSelectedBank(null)} className="text-gray-500 hover:text-white text-xs">cerrar ✕</button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
            {[
              ['Activos', fmt(selectedBank.activos_totales)],
              ['Cartera Créditos', fmt(selectedBank.cartera_creditos)],
              ['Patrimonio', fmt(selectedBank.patrimonio)],
              ['Utilidad Neta', fmt(selectedBank.utilidad_neta)],
              ['Solvencia', selectedBank.indice_solvencia != null ? `${selectedBank.indice_solvencia.toFixed(1)}%` : 'sin dato'],
              ['Mora', selectedBank.mora_porcentaje != null ? `${selectedBank.mora_porcentaje.toFixed(1)}%` : 'sin dato'],
              ['Empleados', selectedBank.num_empleados != null ? selectedBank.num_empleados.toLocaleString() : 'sin dato'],
              ['Sucursales', selectedBank.num_sucursales != null ? selectedBank.num_sucursales.toLocaleString() : 'sin dato'],
            ].map(([k, v]) => (
              <div key={k as string} className="bg-gray-800 rounded-lg p-3">
                <p className="text-xs text-gray-500">{k as string}</p>
                <p className="text-white font-semibold">{v as string}</p>
              </div>
            ))}
          </div>
          {selectedBank.mora_porcentaje != null && (
            <p className="text-xs mt-3" style={{ color: MORA_COLOR(selectedBank.mora_porcentaje) }}>
              Mora: {selectedBank.mora_porcentaje.toFixed(1)}%
            </p>
          )}
          <p className="text-xs text-gray-600 mt-3">{selectedBank.fuente}</p>
        </div>
      )}
    </div>
  )
}
