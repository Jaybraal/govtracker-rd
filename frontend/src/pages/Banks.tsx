import { useState } from 'react'
import { Link } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Landmark, Shield, TrendingUp, AlertTriangle, ExternalLink } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import StatCard from '../components/StatCard'
import { cooperativesApi } from '../services/api'
import { useApi } from '../hooks/useApi'
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

const fmt = (n: number) => {
  if (!n) return 'RD$0'
  if (n >= 1e12) return `RD$${(n/1e12).toFixed(2)}T`
  if (n >= 1e9)  return `RD$${(n/1e9).toFixed(2)}B`
  if (n >= 1e6)  return `RD$${(n/1e6).toFixed(1)}M`
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
  const [tab, setTab] = useState<'ranking' | 'fondos' | 'empresas'>('ranking')
  const [selectedBank, setSelectedBank] = useState<any>(null)

  const { data: banks, loading }  = useApi(() => api.get('/banks/').then(r => r.data), [])
  const { data: stats }           = useApi(() => api.get('/banks/stats').then(r => r.data), [])
  const { data: fondos }          = useApi(() => api.get('/banks/fondos-estado').then(r => r.data), [])

  return (
    <div className="p-6 space-y-5">
      <PageHeader
        title="Sistema Bancario Dominicano"
        subtitle="Bancos autorizados por la Superintendencia de Bancos — dónde están los fondos del Estado"
      />

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Bancos"      value={stats.total_bancos.toString()} icon={<Landmark size={16}/>} color="blue" />
          <StatCard label="Activos del Sistema" value={fmt(stats.total_activos_sistema)} icon={<TrendingUp size={16}/>} color="purple" />
          <StatCard label="Fondos Estado"     value={fmt(stats.total_fondos_estado_custodiados)} icon={<Shield size={16}/>} color="yellow" />
          <StatCard label="Bancos Pagadores"  value={stats.bancos_con_fondos_estado?.toString()} icon={<Landmark size={16}/>} color="green" />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-xl p-1">
        {[
          { id: 'ranking', label: '🏦 Ranking Bancos' },
          { id: 'fondos',  label: '🏛 Fondos del Estado' },
          { id: 'empresas', label: '🏢 Empresas por Banco' },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id as any)}
            className={`flex-1 py-2 px-3 rounded-lg text-sm transition-all ${tab === t.id ? 'bg-gov-700 text-white font-medium' : 'text-gray-400 hover:text-white'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ─── RANKING BANCOS ─── */}
      {tab === 'ranking' && (
        <div className="space-y-4">
          {/* Gráfico activos */}
          {banks && (
            <div className="card">
              <h3 className="text-sm font-semibold text-white mb-4">Activos Totales por Banco (RD$)</h3>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={banks.slice(0,10)} layout="vertical" margin={{ left: 10, right: 30 }}>
                  <XAxis type="number" tickFormatter={v => `${(v/1e9).toFixed(0)}B`} tick={{ fill:'#6b7280', fontSize:10 }} />
                  <YAxis type="category" dataKey="nombre_corto" tick={{ fill:'#9ca3af', fontSize:10 }} width={100} />
                  <Tooltip formatter={(v: number) => fmt(v)} contentStyle={{ background:'#111827', border:'1px solid #374151', borderRadius:8 }} />
                  <Bar dataKey="activos_totales" radius={[0,4,4,0]}>
                    {(banks || []).slice(0,10).map((b: any, i: number) => (
                      <Cell key={i} fill={b.es_estatal ? '#f59e0b' : '#6366f1'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="flex gap-4 mt-2 text-xs text-gray-500">
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-yellow-500"/> Estatal</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-gov-500"/> Privado</span>
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
                  <th className="px-4 py-3 text-gray-400 font-medium text-right">Depósitos</th>
                  <th className="px-4 py-3 text-gray-400 font-medium text-right">Cartera</th>
                  <th className="px-4 py-3 text-gray-400 font-medium text-center">Solvencia</th>
                  <th className="px-4 py-3 text-gray-400 font-medium text-center">Mora</th>
                  <th className="px-4 py-3 text-gray-400 font-medium text-right">Fondos Estado</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-500">Cargando...</td></tr>
                ) : (banks || []).map((b: any, i: number) => (
                  <tr key={b.id} className={`table-row cursor-pointer ${b.es_estatal ? 'bg-yellow-950/5' : ''}`}
                      onClick={() => setSelectedBank(b)}>
                    <td className="px-4 py-2.5 text-xs text-gray-600 font-mono">{i+1}</td>
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
                    <td className="px-4 py-2.5 text-right font-mono text-gray-400">{fmt(b.depositos_totales)}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-gray-400">{fmt(b.cartera_creditos)}</td>
                    <td className="px-4 py-2.5 text-center">
                      <span className={`text-xs font-mono ${b.indice_solvencia >= 14 ? 'text-green-400' : b.indice_solvencia >= 12 ? 'text-yellow-400' : 'text-red-400'}`}>
                        {b.indice_solvencia?.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <span className="text-xs font-mono" style={{ color: MORA_COLOR(b.mora_porcentaje) }}>
                        {b.mora_porcentaje?.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      {b.monto_fondos_estado > 0
                        ? <span className="text-yellow-400 font-mono font-semibold text-xs">{fmt(b.monto_fondos_estado)}</span>
                        : <span className="text-gray-700 text-xs">—</span>}
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
                  ['Depósitos', fmt(selectedBank.depositos_totales)],
                  ['Cartera Créditos', fmt(selectedBank.cartera_creditos)],
                  ['Patrimonio', fmt(selectedBank.patrimonio)],
                  ['Utilidad Neta', fmt(selectedBank.utilidad_neta)],
                  ['Solvencia', `${selectedBank.indice_solvencia?.toFixed(1)}%`],
                  ['Mora', `${selectedBank.mora_porcentaje?.toFixed(1)}%`],
                  ['Sucursales', selectedBank.num_sucursales?.toLocaleString()],
                ].map(([k, v]) => (
                  <div key={k as string} className="bg-gray-800 rounded-lg p-3">
                    <p className="text-xs text-gray-500">{k as string}</p>
                    <p className="text-white font-semibold">{v as string}</p>
                  </div>
                ))}
              </div>
              {selectedBank.custodia_fondos_estado && (
                <div className="mt-3 p-3 bg-yellow-950/30 border border-yellow-900/50 rounded-lg text-sm text-yellow-300">
                  <Shield size={14} className="inline mr-1" />
                  Custodia <strong>{fmt(selectedBank.monto_fondos_estado)}</strong> en fondos del Estado dominicano
                  · {selectedBank.num_cuentas_instituciones} cuentas institucionales
                  {selectedBank.es_banco_pagador && ' · Banco pagador de nómina estatal'}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ─── FONDOS DEL ESTADO ─── */}
      {tab === 'fondos' && (
        <div className="space-y-3">
          <div className="card bg-yellow-950/20 border-yellow-900/40 text-sm text-yellow-200 p-4">
            <AlertTriangle size={14} className="inline mr-1" />
            Esta información muestra en qué banco tiene depósitos cada institución del Estado.
            Los montos son aproximados según informes de Tesorería Nacional y Hacienda.
            <strong className="block mt-1 text-yellow-300">Los números de cuenta específicos son confidenciales por ley bancaria.</strong>
          </div>
          <div className="card p-0 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left">
                  <th className="px-4 py-3 text-gray-400 font-medium">Institución</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Banco</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Tipo banco</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Descripción</th>
                  <th className="px-4 py-3 text-gray-400 font-medium text-right">Monto aprox.</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Fuente</th>
                </tr>
              </thead>
              <tbody>
                {(fondos || []).map((f: any, i: number) => (
                  <tr key={i} className={`table-row ${f.banco_estatal ? 'bg-yellow-950/5' : ''}`}>
                    <td className="px-4 py-2.5">
                      <p className="text-white font-medium">{f.institucion_siglas}</p>
                      <p className="text-xs text-gray-500 max-w-48 truncate">{f.institucion}</p>
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-1.5">
                        {f.banco_estatal && <Shield size={10} className="text-yellow-400" />}
                        <span className="text-white text-sm">{f.banco}</span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-gray-500">{TIPO_LABEL[f.banco_tipo] || '—'}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-400 max-w-48 truncate">{f.descripcion}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-yellow-400 font-semibold">{fmt(f.monto_depositado)}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-600">{f.fuente}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ─── EMPRESAS POR BANCO ─── */}
      {tab === 'empresas' && (
        <div className="space-y-4">
          <p className="text-xs text-gray-500 px-1">
            Empresas contratistas del Estado vinculadas a cada banco. Datos inferidos por sector/RNC — no son cuentas verificadas individualmente.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(banks || []).filter((b: any) => b.es_banco_pagador || b.monto_fondos_estado > 0).map((b: any) => (
              <div key={b.id} className="card hover:border-gov-700 transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  {b.es_estatal && <Shield size={12} className="text-yellow-400" />}
                  <p className="font-semibold text-white">{b.nombre_corto}</p>
                </div>
                <div className="text-xs text-gray-400 space-y-1">
                  <div className="flex justify-between">
                    <span>Fondos Estado</span>
                    <span className="text-yellow-400 font-mono">{fmt(b.monto_fondos_estado)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Cuentas inst.</span>
                    <span className="text-white">{b.num_cuentas_instituciones}</span>
                  </div>
                  {b.es_banco_pagador && (
                    <p className="text-green-400 text-xs">✓ Paga nómina estatal</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
