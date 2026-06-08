import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Search, Sparkles } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import { aiApi } from '../services/api'

interface Message { role: 'user' | 'assistant'; content: string; ts: string }

const SUGGESTIONS = [
  '¿Cuáles son los 10 contratos más grandes de INAPA?',
  '¿Qué empresa ha recibido más dinero del Estado?',
  '¿Qué préstamos tiene el BID con República Dominicana?',
  '¿Qué contratos tienen más de 3 adendas?',
  '¿Qué empresas trabajan para múltiples ministerios?',
  '¿Qué proyectos financiados por el Banco Mundial están activos?',
]

export default function AIChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: '¡Hola! Soy el Analista IA de GovTracker RD. Puedo responder preguntas sobre contratos, préstamos, empresas e instituciones públicas dominicanas. ¿En qué te puedo ayudar?',
      ts: new Date().toISOString(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text = input) => {
    if (!text.trim() || loading) return
    const userMsg: Message = { role: 'user', content: text, ts: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)
    try {
      const r = await aiApi.chat(text)
      setMessages(prev => [...prev, { role: 'assistant', content: r.answer, ts: new Date().toISOString() }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error al conectar con el servidor.', ts: new Date().toISOString() }])
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    const r = await aiApi.search(searchQuery)
    setSearchResults(r.results || [])
  }

  return (
    <div className="p-6 h-full flex flex-col gap-4" style={{ maxHeight: 'calc(100vh - 0px)' }}>
      <PageHeader
        title="IA Analista"
        subtitle="Consultas en lenguaje natural sobre el gasto público"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1 min-h-0">
        {/* Chat */}
        <div className="lg:col-span-2 card flex flex-col min-h-0" style={{ height: 580 }}>
          {/* Mensajes */}
          <div className="flex-1 overflow-y-auto space-y-4 pb-2">
            {messages.map((msg, i) => (
              <div key={i} className={`flex items-start gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  msg.role === 'assistant' ? 'bg-gov-700' : 'bg-gray-700'
                }`}>
                  {msg.role === 'assistant' ? <Bot size={16} /> : <User size={16} />}
                </div>
                <div className={`max-w-lg rounded-xl px-4 py-3 text-sm whitespace-pre-wrap ${
                  msg.role === 'assistant'
                    ? 'bg-gray-800 text-gray-100'
                    : 'bg-gov-700 text-white ml-auto'
                }`}>
                  {msg.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gov-700 flex items-center justify-center">
                  <Bot size={16} />
                </div>
                <div className="bg-gray-800 rounded-xl px-4 py-3 text-sm text-gray-400 flex items-center gap-2">
                  <span className="animate-pulse">Analizando datos...</span>
                  <Sparkles size={12} className="animate-spin" />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="border-t border-gray-800 pt-3 mt-2">
            <div className="flex gap-2">
              <input
                className="input flex-1"
                placeholder="Pregunta sobre contratos, empresas, préstamos..."
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                disabled={loading}
              />
              <button
                onClick={() => sendMessage()}
                disabled={loading || !input.trim()}
                className="btn-primary px-3 disabled:opacity-50"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>

        {/* Panel lateral */}
        <div className="space-y-4">
          {/* Sugerencias */}
          <div className="card">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Preguntas sugeridas</p>
            <div className="space-y-2">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(s)}
                  className="w-full text-left text-xs text-gray-400 hover:text-white hover:bg-gray-800 px-3 py-2 rounded-lg transition-colors border border-gray-800 hover:border-gray-700"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Búsqueda semántica */}
          <div className="card">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Búsqueda Global</p>
            <div className="flex gap-2 mb-3">
              <input
                className="input flex-1 text-xs"
                placeholder="Buscar..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
              />
              <button onClick={handleSearch} className="btn-primary px-2">
                <Search size={14} />
              </button>
            </div>
            {searchResults.length > 0 && (
              <div className="space-y-2">
                {searchResults.map((r, i) => (
                  <a
                    key={i}
                    href={r.url}
                    className="block hover:bg-gray-800 p-2 rounded-lg border border-gray-800 hover:border-gray-700 transition-colors"
                  >
                    <p className="text-xs text-white truncate">{r.title}</p>
                    <p className="text-xs text-gray-500">{r.type} · {r.subtitle}</p>
                  </a>
                ))}
              </div>
            )}
          </div>

          {/* Info modelo */}
          <div className="card border-gov-900/50">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Modelo IA</p>
            <p className="text-xs text-gray-400">
              Usa <strong className="text-gov-300">Ollama (llama3)</strong> si está disponible localmente en puerto 11434.
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Sin Ollama: análisis basado en reglas + consultas SQL directas.
            </p>
            <a
              href="https://ollama.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-gov-400 hover:text-gov-300 mt-2 block"
            >
              Instalar Ollama →
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
