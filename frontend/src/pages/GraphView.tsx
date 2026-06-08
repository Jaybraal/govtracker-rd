import { useState, useEffect, useRef, useCallback } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import {
  Network, RefreshCw, Search, X, ZoomIn, ZoomOut,
  Building2, Landmark, Banknote, User, ExternalLink,
} from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { graphApi } from '../services/api'

// ─── Colores por tipo de nodo ────────────────────────────────────────────────
const GROUP_COLORS: Record<string, string> = {
  institution:      '#6366f1',
  company:          '#10b981',
  company_related:  '#34d399',
  representative:   '#f59e0b',
  persona_interes:  '#ef4444',
  persona_relacionada: '#8b5cf6',
  loan:             '#ef4444',
  project:          '#8b5cf6',
}

const GROUP_LABELS: Record<string, string> = {
  institution:     'Institución',
  company:         'Empresa',
  company_related: 'Empresa relacionada',
  representative:  'Representante legal',
  loan:            'Préstamo',
  project:         'Proyecto',
}

const fmt = (n: number) => {
  if (!n) return ''
  if (n >= 1e9) return `RD$${(n / 1e9).toFixed(1)}B`
  if (n >= 1e6) return `RD$${(n / 1e6).toFixed(0)}M`
  return `RD$${n.toLocaleString()}`
}

interface GraphNode {
  id: string
  label: string
  title?: string
  group: string
  value?: number
  // injected by force-graph
  x?: number; y?: number; fx?: number; fy?: number
}

interface GraphEdge {
  from: string; to: string
  value?: number; title?: string; label?: string; dashes?: boolean
}

export default function GraphView() {
  const fgRef = useRef<any>(null)
  const [entityType, setEntityType]   = useState('company')
  const [entityId, setEntityId]       = useState('')
  const [minMonto, setMinMonto]       = useState('0')
  const [loading, setLoading]         = useState(false)
  const [nodes, setNodes]             = useState<GraphNode[]>([])
  const [links, setLinks]             = useState<any[]>([])
  const [selected, setSelected]       = useState<GraphNode | null>(null)
  const [searchTerm, setSearchTerm]   = useState('')
  const [highlightNodes, setHighlight] = useState<Set<string>>(new Set())
  const [dimensions, setDimensions]   = useState({ w: 900, h: 520 })
  const containerRef = useRef<HTMLDivElement>(null)

  // Dimensiones responsivas
  useEffect(() => {
    const update = () => {
      if (containerRef.current) {
        setDimensions({ w: containerRef.current.clientWidth, h: 520 })
      }
    }
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])

  const loadGraph = useCallback(async () => {
    setLoading(true)
    setSelected(null)
    try {
      const data = await graphApi.network({
        entity_type: entityType,
        ...(entityId && { entity_id: parseInt(entityId) }),
        min_monto: parseFloat(minMonto) || 0,
      })

      // Convertir al formato que espera react-force-graph-2d
      setNodes(data.nodes as GraphNode[])
      setLinks(data.edges.map((e: GraphEdge) => ({
        source: e.from,
        target: e.to,
        value:  e.value  || 1,
        label:  e.label  || '',
        title:  e.title  || '',
        dashes: e.dashes || false,
      })))
    } catch (e) {
      console.error('Graph error:', e)
    } finally {
      setLoading(false)
    }
  }, [entityType, entityId, minMonto])

  // Carga automática al montar
  useEffect(() => { loadGraph() }, [])

  // Búsqueda de nodo
  useEffect(() => {
    if (!searchTerm) { setHighlight(new Set()); return }
    const s = searchTerm.toLowerCase()
    const matched = new Set(
      nodes
        .filter(n => (n.label || '').toLowerCase().includes(s) || (n.title || '').toLowerCase().includes(s))
        .map(n => n.id)
    )
    setHighlight(matched)
    // Centrar en el primer match
    if (matched.size > 0 && fgRef.current) {
      const first = nodes.find(n => matched.has(n.id))
      if (first?.x && first?.y) {
        fgRef.current.centerAt(first.x, first.y, 600)
        fgRef.current.zoom(3, 600)
      }
    }
  }, [searchTerm, nodes])

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelected(node)
    if (fgRef.current && node.x && node.y) {
      fgRef.current.centerAt(node.x, node.y, 500)
      fgRef.current.zoom(2.5, 500)
    }
  }, [])

  const handleBgClick = useCallback(() => {
    setSelected(null)
  }, [])

  // Calcular conexiones del nodo seleccionado
  const selectedLinks = selected
    ? links.filter(l => {
        const src = typeof l.source === 'object' ? l.source.id : l.source
        const tgt = typeof l.target === 'object' ? l.target.id : l.target
        return src === selected.id || tgt === selected.id
      })
    : []

  const connectedIds = new Set(
    selectedLinks.flatMap(l => {
      const src = typeof l.source === 'object' ? l.source.id : l.source
      const tgt = typeof l.target === 'object' ? l.target.id : l.target
      return [src, tgt]
    })
  )

  // Stats por grupo
  const groupStats = nodes.reduce((acc: Record<string, number>, n) => {
    acc[n.group] = (acc[n.group] || 0) + 1
    return acc
  }, {})

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title="Red de Relaciones"
        subtitle="Haz clic en cualquier nodo para explorar sus conexiones"
      />

      {/* ─── Controles ─── */}
      <div className="card flex flex-wrap gap-3 items-center">
        <select
          className="input w-44"
          value={entityType}
          onChange={e => setEntityType(e.target.value)}
        >
          <option value="company">Por empresa</option>
          <option value="institution">Por institución</option>
          <option value="loan">Por préstamo</option>
        </select>

        <input
          className="input w-36"
          placeholder="ID (opcional)"
          value={entityId}
          onChange={e => setEntityId(e.target.value)}
        />

        <select
          className="input w-48"
          value={minMonto}
          onChange={e => setMinMonto(e.target.value)}
        >
          <option value="0">Todos los montos</option>
          <option value="10000000">Desde RD$10M</option>
          <option value="50000000">Desde RD$50M</option>
          <option value="100000000">Desde RD$100M</option>
          <option value="500000000">Desde RD$500M</option>
        </select>

        <button
          onClick={loadGraph}
          disabled={loading}
          className="btn-primary flex items-center gap-2"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          {loading ? 'Cargando...' : 'Actualizar red'}
        </button>

        {/* Búsqueda */}
        <div className="relative ml-auto">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            className="input pl-8 w-48"
            placeholder="Buscar nodo..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
          />
          {searchTerm && (
            <button onClick={() => setSearchTerm('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white">
              <X size={13} />
            </button>
          )}
        </div>
      </div>

      {/* ─── Leyenda + stats ─── */}
      <div className="flex flex-wrap gap-3 items-center">
        {Object.entries(groupStats).map(([group, cnt]) => (
          <div key={group} className="flex items-center gap-1.5 text-xs text-gray-400">
            <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: GROUP_COLORS[group] || '#6b7280' }} />
            <span>{GROUP_LABELS[group] || group}: <span className="text-white font-medium">{cnt}</span></span>
          </div>
        ))}
        <span className="text-xs text-gray-600 ml-2">
          {links.length} conexiones · El tamaño del nodo = monto involucrado
        </span>
      </div>

      {/* ─── Grafo principal ─── */}
      <div className="flex gap-4">
        {/* Canvas */}
        <div
          ref={containerRef}
          className="flex-1 bg-gray-950 rounded-xl overflow-hidden border border-gray-800 relative"
          style={{ height: 520 }}
        >
          {nodes.length === 0 && !loading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-600">
              <Network size={48} className="mb-3 opacity-30" />
              <p className="text-sm">No hay datos para mostrar</p>
              <p className="text-xs mt-1">Prueba cambiando los filtros</p>
            </div>
          )}

          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-950/80 z-10">
              <RefreshCw size={28} className="animate-spin text-gov-400" />
            </div>
          )}

          {nodes.length > 0 && (
            <ForceGraph2D
              ref={fgRef}
              width={dimensions.w}
              height={dimensions.h}
              graphData={{ nodes, links }}
              backgroundColor="#030712"

              // Nodos
              nodeId="id"
              nodeLabel={node => {
                const n = node as GraphNode
                return `${n.title || n.label}${n.value ? '\n' + fmt(n.value) : ''}`
              }}
              nodeColor={node => {
                const n = node as GraphNode
                if (highlightNodes.size > 0 && !highlightNodes.has(n.id)) return '#374151'
                if (selected && n.id === selected.id) return '#ffffff'
                if (selected && connectedIds.has(n.id)) return GROUP_COLORS[n.group] || '#6b7280'
                if (selected && !connectedIds.has(n.id)) return '#1f2937'
                return GROUP_COLORS[n.group] || '#6b7280'
              }}
              nodeVal={node => {
                const n = node as GraphNode
                const base = Math.max(3, Math.log((n.value || 1) / 1e7) * 2)
                return Math.min(base, 20)
              }}
              nodeCanvasObject={(node, ctx, globalScale) => {
                const n = node as GraphNode
                const x = n.x || 0, y = n.y || 0

                // Color del nodo
                const isSelected = selected?.id === n.id
                const isConnected = selected ? connectedIds.has(n.id) : true
                const isHighlighted = highlightNodes.size === 0 || highlightNodes.has(n.id)
                const color = GROUP_COLORS[n.group] || '#6b7280'
                const r = Math.max(4, Math.min(22, Math.log((n.value || 1e6) / 1e7 + 1) * 5))

                // Anillo exterior si está seleccionado
                if (isSelected) {
                  ctx.beginPath()
                  ctx.arc(x, y, r + 4, 0, 2 * Math.PI)
                  ctx.strokeStyle = '#ffffff'
                  ctx.lineWidth = 2
                  ctx.stroke()
                }

                // Círculo principal
                ctx.beginPath()
                ctx.arc(x, y, r, 0, 2 * Math.PI)
                ctx.fillStyle = !isConnected ? '#111827' : !isHighlighted ? '#374151' : color
                ctx.fill()

                // Borde
                ctx.strokeStyle = isSelected ? '#ffffff' : color
                ctx.lineWidth = 1.5
                ctx.stroke()

                // Etiqueta (solo si zoom suficiente o si está seleccionado)
                const label = n.label || ''
                const truncated = label.length > 18 ? label.slice(0, 16) + '…' : label
                const fontSize = Math.max(9, Math.min(13, 10 / globalScale * 2))
                if (globalScale > 0.6 || isSelected) {
                  ctx.font = `${isSelected ? 'bold ' : ''}${fontSize}px Inter, sans-serif`
                  ctx.textAlign = 'center'
                  ctx.textBaseline = 'middle'

                  // Sombra del texto
                  ctx.shadowColor = '#000000'
                  ctx.shadowBlur = 4
                  ctx.fillStyle = isSelected ? '#ffffff' : (isConnected && isHighlighted) ? '#e5e7eb' : '#4b5563'
                  ctx.fillText(truncated, x, y + r + fontSize * 0.8)
                  ctx.shadowBlur = 0
                }
              }}
              nodeCanvasObjectMode={() => 'replace'}

              // Aristas
              linkColor={link => {
                if (selected) {
                  const src = typeof link.source === 'object' ? (link.source as any).id : link.source
                  const tgt = typeof link.target === 'object' ? (link.target as any).id : link.target
                  return (src === selected.id || tgt === selected.id) ? '#6366f1' : '#1f2937'
                }
                return '#374151'
              }}
              linkWidth={link => {
                const v = (link as any).value || 1
                return Math.max(0.5, Math.min(4, Math.log(v / 1e8 + 1) * 1.5))
              }}
              linkDirectionalArrowLength={4}
              linkDirectionalArrowRelPos={1}
              linkDirectionalParticles={link => {
                if (!selected) return 0
                const src = typeof link.source === 'object' ? (link.source as any).id : link.source
                const tgt = typeof link.target === 'object' ? (link.target as any).id : link.target
                return (src === selected?.id || tgt === selected?.id) ? 3 : 0
              }}
              linkDirectionalParticleSpeed={0.003}
              linkDirectionalParticleColor={() => '#6366f1'}

              // Interacción
              onNodeClick={handleNodeClick as any}
              onBackgroundClick={handleBgClick}

              // Física
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
              cooldownTicks={200}
              onEngineStop={() => fgRef.current?.zoomToFit(400, 60)}
            />
          )}

          {/* Controles de zoom */}
          <div className="absolute bottom-3 right-3 flex flex-col gap-1 z-10">
            <button
              onClick={() => fgRef.current?.zoom(fgRef.current.zoom() * 1.3, 200)}
              className="w-7 h-7 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg flex items-center justify-center text-gray-400 hover:text-white transition-colors"
            >
              <ZoomIn size={13} />
            </button>
            <button
              onClick={() => fgRef.current?.zoom(fgRef.current.zoom() * 0.7, 200)}
              className="w-7 h-7 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg flex items-center justify-center text-gray-400 hover:text-white transition-colors"
            >
              <ZoomOut size={13} />
            </button>
            <button
              onClick={() => fgRef.current?.zoomToFit(400, 60)}
              className="w-7 h-7 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg flex items-center justify-center text-gray-400 hover:text-white transition-colors text-xs font-bold"
              title="Ver todo"
            >
              ⊡
            </button>
          </div>

          {/* Instrucciones */}
          <div className="absolute bottom-3 left-3 text-xs text-gray-600">
            Clic = explorar · Scroll = zoom · Arrastrar = mover nodo
          </div>
        </div>

        {/* ─── Panel lateral — detalle del nodo seleccionado ─── */}
        <div className="w-72 flex-shrink-0 space-y-3">
          {selected ? (
            <>
              <div className="card" style={{ borderLeftColor: GROUP_COLORS[selected.group], borderLeftWidth: 3 }}>
                <div className="flex items-start justify-between mb-2">
                  <span className="text-xs px-2 py-0.5 rounded-full text-white" style={{ background: GROUP_COLORS[selected.group] }}>
                    {GROUP_LABELS[selected.group] || selected.group}
                  </span>
                  <button onClick={() => setSelected(null)} className="text-gray-600 hover:text-white">
                    <X size={13} />
                  </button>
                </div>
                <h3 className="font-bold text-white text-sm mt-1">{selected.title || selected.label}</h3>
                {selected.value && (
                  <p className="text-yellow-400 font-mono font-semibold mt-1">{fmt(selected.value)}</p>
                )}
                <p className="text-xs text-gray-500 mt-0.5">ID: {selected.id}</p>
              </div>

              {/* Conexiones */}
              <div className="card">
                <p className="text-xs font-semibold text-white mb-2">
                  {selectedLinks.length} conexion{selectedLinks.length !== 1 ? 'es' : ''}
                </p>
                <div className="space-y-1.5 max-h-72 overflow-y-auto">
                  {selectedLinks.map((l, i) => {
                    const srcId = typeof l.source === 'object' ? l.source.id : l.source
                    const tgtId = typeof l.target === 'object' ? l.target.id : l.target
                    const otherId = srcId === selected.id ? tgtId : srcId
                    const other = nodes.find(n => n.id === otherId)
                    return (
                      <div
                        key={i}
                        className="flex items-center gap-2 p-2 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700 transition-colors"
                        onClick={() => other && handleNodeClick(other)}
                      >
                        <span
                          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                          style={{ background: GROUP_COLORS[other?.group || ''] || '#6b7280' }}
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-white truncate">{other?.title || other?.label}</p>
                          {l.value > 0 && (
                            <p className="text-xs text-gray-500 font-mono">{fmt(l.value)}</p>
                          )}
                          {l.title && (
                            <p className="text-xs text-gray-600 truncate">{l.title}</p>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Link a ver detalle completo */}
              {selected.id.startsWith('comp_') && (
                <a
                  href={`/companies/${selected.id.replace('comp_', '')}`}
                  className="btn-primary w-full flex items-center justify-center gap-2 text-sm"
                >
                  <ExternalLink size={14} /> Ver empresa completa
                </a>
              )}
              {selected.id.startsWith('inst_') && (
                <a
                  href={`/institutions/${selected.id.replace('inst_', '')}`}
                  className="btn-primary w-full flex items-center justify-center gap-2 text-sm"
                >
                  <ExternalLink size={14} /> Ver institución completa
                </a>
              )}
            </>
          ) : (
            <div className="card text-center py-8 text-gray-600">
              <Network size={32} className="mx-auto mb-2 opacity-30" />
              <p className="text-sm">Haz clic en un nodo</p>
              <p className="text-xs mt-1">para ver sus conexiones</p>
            </div>
          )}

          {/* Guía rápida */}
          <div className="card text-xs text-gray-500 space-y-1.5">
            <p className="text-gray-400 font-medium mb-1">Cómo usar:</p>
            <p>🔵 <span className="text-gov-400">Azul</span> = Institución pública</p>
            <p>🟢 <span className="text-emerald-400">Verde</span> = Empresa contratista</p>
            <p>🟡 <span className="text-yellow-400">Amarillo</span> = Representante legal</p>
            <p>🔴 <span className="text-red-400">Rojo</span> = Préstamo / Persona de interés</p>
            <p className="pt-1 text-gray-600">El grosor de la línea = monto del contrato. Las partículas animadas indican la dirección del flujo de dinero.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
