import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle, RotateCcw } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Error de renderizado capturado por ErrorBoundary:', error, info.componentStack)
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children

    return (
      <div className="flex h-screen items-center justify-center bg-gray-950 p-6">
        <div className="card max-w-lg text-center space-y-3">
          <AlertTriangle size={28} className="text-red-400 mx-auto" />
          <h2 className="text-white font-semibold">Ocurrió un error al mostrar esta página</h2>
          <p className="text-sm text-gray-400">
            Esto suele pasar cuando un dato esperado viene incompleto. El resto de la aplicación sigue funcionando —
            volvé al inicio o intentá de nuevo.
          </p>
          <p className="text-xs text-gray-600 font-mono break-all">{error.message}</p>
          <div className="flex gap-2 justify-center pt-1">
            <button onClick={() => { this.setState({ error: null }); window.location.assign('/') }} className="btn-primary flex items-center gap-1.5">
              <RotateCcw size={14} /> Volver al inicio
            </button>
            <button onClick={() => this.setState({ error: null })} className="btn-ghost">
              Reintentar
            </button>
          </div>
        </div>
      </div>
    )
  }
}
