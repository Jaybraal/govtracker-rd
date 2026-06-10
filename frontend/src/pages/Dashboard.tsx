import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import { FileText, Building2, Landmark, Banknote, Bell, AlertTriangle, Eye, HeartPulse } from 'lucide-react'
import StatCard from '../components/StatCard'
import PageHeader from '../components/PageHeader'
import { statsApi, contractsApi, institutionsApi, alertsApi, intelligenceApi, segurosApi, GlobalStats } from '../services/api'

const PIE_COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe']

const fmt = (n: number) => {
  if (n >= 1_000_000_000) return `RD$${(n / 1_000_000_000).toFixed(1)}B`
  if (n >= 1_000_000) return `RD$${(n / 1_000_000).toFixed(0)}M`
  return `RD$${n.toLocaleString()}`
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<GlobalStats | null>(null)
  const [contractStats, setContractStats] = useState<any>(null)
  const [topInstitutions, setTopInstitutions] = useState<any[]>([])
  const [alertStats, setAlertStats] = useState<any>(null)
  const [intelResumen, setIntelResumen] = useState<any>(null)
  const [segurosStats, setSegurosStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      statsApi.global(),
      contractsApi.stats(),
      institutionsApi.ranking(10),
      alertsApi.stats(),
      intelligenceApi.resumen().catch(() => null),
      segurosApi.stats().catch(() => null),
    ]).then(([s, cs, ti, as_, ir, ss]) => {
      setStats(s)
      setContractStats(cs)
      setTopInstitutions(ti)
      setAlertStats(as_)
      setIntelResumen(ir)
      setSegurosStats(ss)
    }).finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-full text-gray-500">
      Cargando datos...
    </div>
  )

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Dashboard — GovTracker RD"
        subtitle="Monitoreo en tiempo real del gasto público dominicano"
      />

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Contratos"
          value={stats?.total_contratos?.toLocaleString() ?? '0'}
          icon={<FileText size={16} />}
          color="blue"
          to="/contracts"
        />
        <StatCard
          label="Monto Contratado"
          value={fmt(stats?.total_monto_contratos ?? 0)}
          icon={<Landmark size={16} />}
          color="purple"
          to="/contracts"
        />
        <StatCard
          label="Empresas"
          value={stats?.total_empresas?.toLocaleString() ?? '0'}
          icon={<Building2 size={16} />}
          color="green"
          to="/companies"
        />
        <StatCard
          label="Alertas Activas"
          value={stats?.alertas_activas?.toString() ?? '0'}
          icon={<Bell size={16} />}
          color="red"
          to="/alerts"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          label="Préstamos Internacionales"
          value={stats?.total_prestamos?.toString() ?? '0'}
          sub={`USD ${fmt(stats?.total_monto_prestamos ?? 0)}`}
          icon={<Banknote size={16} />}
          color="yellow"
          to="/loans"
        />
        <StatCard
          label="Contratos >RD$100M"
          value={contractStats?.contratos_mayores_100m?.toString() ?? '0'}
          sub="Alto valor"
          color="red"
          to="/contracts?es_mayor_100m=true"
        />
        <StatCard
          label="Con Adendas"
          value={contractStats?.contratos_con_adendas?.toString() ?? '0'}
          sub="Modificados"
          color="yellow"
          to="/contracts?tiene_adendas=true"
        />
        <StatCard
          label="Financiados con Préstamos"
          value={contractStats?.contratos_financiados_prestamo?.toString() ?? '0'}
          sub="Deuda externa"
          color="purple"
          to="/contracts?financiado_prestamo=true"
        />
      </div>

      {/* Seguros KPI */}
      {segurosStats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard
            label="Contratos de Seguros"
            value={segurosStats.total_contratos?.toLocaleString() ?? '0'}
            sub={`${segurosStats.empresas_unicas} aseguradoras`}
            icon={<HeartPulse size={16} />}
            color="blue"
            to="/seguros"
          />
          <StatCard
            label="Monto en Seguros (DGCP)"
            value={fmt(segurosStats.monto_total ?? 0)}
            sub="Total adjudicado"
            icon={<HeartPulse size={16} />}
            color="purple"
            to="/seguros"
          />
          <div className="card border border-red-800/50 bg-red-950/20 flex flex-col justify-between cursor-pointer hover:bg-red-950/30 transition-colors"
            onClick={() => navigate('/seguros?tab=caso')}>
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle size={14} className="text-red-400" />
              <p className="text-xs text-red-400 font-medium">Caso SENASA — Operación Cobra</p>
            </div>
            <p className="text-xl font-bold text-red-300">{segurosStats.caso_cobra_monto_defraudado}</p>
            <p className="text-xs text-gray-500 mt-1">
              {segurosStats.caso_cobra_imputados} imputados · Fuente: PGR oficial
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Instituciones */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white">Top Instituciones por Monto</h2>
            <Link to="/institutions" className="text-xs text-gov-400 hover:text-gov-300">Ver todas →</Link>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={topInstitutions.slice(0, 8)} layout="vertical" margin={{ left: 10, right: 30 }}>
              <XAxis type="number" tickFormatter={v => `${(v/1e9).toFixed(1)}B`} tick={{ fill: '#6b7280', fontSize: 11 }} />
              <YAxis type="category" dataKey="siglas" tick={{ fill: '#9ca3af', fontSize: 11 }} width={70} />
              <Tooltip
                formatter={(v: number) => fmt(v)}
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                labelStyle={{ color: '#f9fafb' }}
              />
              <Bar
                dataKey="monto_total"
                fill="#6366f1"
                radius={[0, 4, 4, 0]}
                cursor="pointer"
                onClick={(d: any) => d?.id && navigate(`/institutions/${d.id}`)}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Modalidades */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white">Contratos por Modalidad</h2>
          </div>
          {contractStats?.por_modalidad && (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={contractStats.por_modalidad.filter((m: any) => m.modalidad)}
                  dataKey="cantidad"
                  nameKey="modalidad"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ modalidad, percent }: any) =>
                    `${(modalidad || '?').split('_').join(' ')} ${(percent * 100).toFixed(0)}%`
                  }
                  labelLine={{ stroke: '#4b5563' }}
                  cursor="pointer"
                  onClick={(d: any) => d?.modalidad && navigate(`/contracts?modalidad=${d.modalidad}`)}
                >
                  {contractStats.por_modalidad.map((_: any, i: number) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(v: number) => [v, 'Contratos']}
                  contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Inteligencia — personas de interés */}
      {intelResumen && intelResumen.stats?.personas_detectadas > 0 && (
        <div className="card border-red-900/40">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Eye size={16} className="text-red-400" />
              <h2 className="font-semibold text-white">Personas de Interés Detectadas</h2>
              {intelResumen.stats.personas_doble_rol > 0 && (
                <span className="badge-red text-xs">
                  {intelResumen.stats.personas_doble_rol} doble rol
                </span>
              )}
            </div>
            <Link to="/intelligence" className="btn-primary text-xs bg-red-800 hover:bg-red-700">
              Ver análisis completo →
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
            {intelResumen.top_personas?.slice(0, 3).map((p: any, i: number) => (
              <Link key={i} to="/intelligence" className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 ${i === 0 ? 'bg-red-900/60 text-red-300' : 'bg-gray-700 text-gray-400'}`}>
                  {i + 1}
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-white truncate font-medium">{p.nombre}</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    {p.roles?.includes('firmante') && <span className="text-xs text-blue-400">firmante</span>}
                    {p.roles?.includes('firmante') && p.roles?.includes('representante_legal') && <span className="text-xs text-gray-600">·</span>}
                    {p.roles?.includes('representante_legal') && <span className="text-xs text-purple-400">rep. legal</span>}
                    {p.total_monto > 0 && (
                      <span className="text-xs text-yellow-400 font-mono ml-auto">{fmt(p.total_monto)}</span>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
          {intelResumen.stats.patrones_criticos > 0 && (
            <p className="text-xs text-red-400">
              ⚠ {intelResumen.stats.patrones_criticos} patrón{intelResumen.stats.patrones_criticos > 1 ? 'es' : ''} crítico{intelResumen.stats.patrones_criticos > 1 ? 's' : ''} detectado{intelResumen.stats.patrones_criticos > 1 ? 's' : ''} · {intelResumen.stats.total_patrones} patrones totales
            </p>
          )}
        </div>
      )}

      {/* Alertas recientes */}
      {alertStats && alertStats.total > 0 && (
        <div className="card border-yellow-900/50">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <AlertTriangle size={16} className="text-yellow-400" />
              <h2 className="font-semibold text-white">Alertas por Tipo</h2>
            </div>
            <Link to="/alerts" className="btn-primary text-xs">Ver alertas</Link>
          </div>
          <div className="flex flex-wrap gap-2">
            {alertStats.por_tipo?.map((t: any) => (
              <Link key={t.tipo} to={`/alerts?tipo=${t.tipo}`} className="badge-yellow hover:brightness-110 transition-all">
                {t.tipo.replace(/_/g, ' ')}: {t.cantidad}
              </Link>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-3">
            <Link to="/alerts?revisada=false" className="hover:text-gray-300 transition-colors">{alertStats.no_revisadas} alertas sin revisar</Link>
            {' · '}
            <Link to="/alerts?severidad=critica" className="hover:text-red-400 transition-colors">{alertStats.criticas} críticas</Link>
          </p>
        </div>
      )}
    </div>
  )
}
