import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { comisionesApi } from '../services/api'
import { useApi } from '../hooks/useApi'

const CARGOS_DIRECTIVOS = ['Presidente/a', 'Vice-Presidente/a', 'Secretario/a']

const CARGO_BADGE: Record<string, string> = {
  'Presidente/a':       'badge-yellow',
  'Vice-Presidente/a':  'badge-blue',
  'Secretario/a':       'badge-purple',
}

export default function CommissionDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: c, loading } = useApi(() => comisionesApi.get(Number(id)), [id])

  if (loading) return <div className="p-6 text-gray-500">Cargando...</div>
  if (!c) return <div className="p-6 text-gray-500">Comisión no encontrada</div>

  const miembrosRegulares = (c.miembros || []).filter((m: any) => !CARGOS_DIRECTIVOS.includes(m.cargo))

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title={c.nombre}
        subtitle={`${c.tipo || ''}${c.estado ? ' · ' + c.estado : ''} · ${c.total_miembros} miembro${c.total_miembros === 1 ? '' : 's'}`}
        actions={
          <Link to="/legislators" className="btn-ghost flex items-center gap-1.5"><ArrowLeft size={14} /> Volver al Congreso</Link>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          ['Tipo', c.tipo || '—'],
          ['Estado', c.estado || '—'],
          ['Total Miembros', c.total_miembros?.toString() || '0'],
          ['Designación', c.fecha_designacion ? new Date(c.fecha_designacion).toLocaleDateString('es-DO') : '—'],
        ].map(([label, value]) => (
          <div key={label} className="card text-center">
            <p className="text-xs text-gray-500 mb-1">{label}</p>
            <p className="text-xl font-bold text-white">{value}</p>
          </div>
        ))}
      </div>

      {c.descripcion && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-2">Descripción</h3>
          <p className="text-sm text-gray-400">{c.descripcion}</p>
        </div>
      )}

      {c.directiva?.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-3">Directiva</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {c.directiva.map((m: any) => (
              <div
                key={m.id}
                onClick={() => m.legislator_id && navigate(`/legislators/${m.legislator_id}`)}
                className={`rounded-lg border border-gray-800 p-3 ${m.legislator_id ? 'cursor-pointer hover:border-gov-700' : ''}`}
              >
                <span className={CARGO_BADGE[m.cargo] || 'badge-blue'}>{m.cargo}</span>
                <p className="text-white font-medium text-sm mt-2">{m.nombre_completo}</p>
                <p className="text-gray-500 text-xs">{m.partido_siglas || '—'}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {miembrosRegulares.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-3">Miembros ({miembrosRegulares.length})</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left">
                  <th className="py-2 px-3 text-gray-400 font-medium">Legislador</th>
                  <th className="py-2 px-3 text-gray-400 font-medium">Partido</th>
                  <th className="py-2 px-3 text-gray-400 font-medium">Cargo</th>
                  <th className="py-2 px-3 text-gray-400 font-medium">Estado</th>
                </tr>
              </thead>
              <tbody>
                {miembrosRegulares.map((m: any) => (
                  <tr
                    key={m.id}
                    onClick={() => m.legislator_id && navigate(`/legislators/${m.legislator_id}`)}
                    className={`table-row ${m.legislator_id ? 'cursor-pointer' : ''}`}
                  >
                    <td className="py-2 px-3 text-white">{m.nombre_completo}</td>
                    <td className="py-2 px-3 text-xs text-gray-400">{m.partido_siglas || '—'}</td>
                    <td className="py-2 px-3 text-xs text-gray-400">{m.cargo}</td>
                    <td className="py-2 px-3 text-xs text-gray-500">{m.estado || '—'}</td>
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
