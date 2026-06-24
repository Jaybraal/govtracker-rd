import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export interface Contract {
  id: number
  numero_contrato: string
  numero_proceso: string | null
  descripcion: string
  objeto: string
  modalidad: string
  estado: string
  monto_original: number
  monto_actual: number
  monto_pagado: number
  moneda: string
  fecha_firma: string | null
  fecha_inicio: string | null
  fecha_fin_planificada: string | null
  oficial_firmante: string | null
  tiene_adendas: boolean
  num_adendas: number
  incremento_porcentual: number
  retraso_dias: number
  financiado_prestamo: boolean
  es_mayor_100m: boolean
  empresa_nombre: string
  empresa_rnc: string
  institucion_nombre: string
  institucion_siglas: string
  institution_id: number
  company_id: number
  fuente: string
  url_fuente: string | null
}

export interface Company {
  id: number
  rnc: string
  nombre: string
  nombre_comercial: string
  tipo_empresa: string
  sector: string
  telefono: string | null
  email: string | null
  direccion: string | null
  provincia: string | null
  total_contratos: number
  total_monto_recibido: number
  total_instituciones: number
  indice_concentracion: number
  primer_contrato: string | null
  ultimo_contrato: string | null
}

export interface Institution {
  id: number
  codigo: string
  nombre: string
  siglas: string
  tipo: string
  total_contratos: number
  total_monto_contratos: number
  presupuesto_anual: number
}

export interface Loan {
  id: number
  codigo: string
  acreedor: string
  tipo_acreedor: string
  descripcion: string
  objeto: string
  estado: string
  monto_aprobado: number
  monto_desembolsado: number
  moneda: string
  tasa_interes: number
  plazo_anos: number
  fecha_aprobacion: string | null
  fecha_vencimiento: string | null
}

export interface Alert {
  id: number
  tipo: string
  severidad: string
  titulo: string
  descripcion: string
  entidad_tipo: string
  entidad_id: number
  entidad_nombre: string
  monto_involucrado: number
  revisada: boolean
  descartada: boolean
  created_at: string
}

export interface GlobalStats {
  total_contratos: number
  total_monto_contratos: number
  total_empresas: number
  total_instituciones: number
  total_prestamos: number
  total_monto_prestamos: number
  alertas_activas: number
}

export interface PagedResponse<T> {
  total: number
  page: number
  size: number
  pages: number
  items: T[]
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface GraphNode {
  id: string
  label: string
  title?: string
  group: string
  value?: number
}

export interface GraphEdge {
  from: string
  to: string
  value?: number
  title?: string
  label?: string
  dashes?: boolean
}

// ─── Endpoints ────────────────────────────────────────────────────────────────

export const statsApi = {
  global: () => api.get<GlobalStats>('/stats').then(r => r.data),
}

export const contractsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<PagedResponse<Contract>>('/contracts', { params }).then(r => r.data),
  get: (id: number) => api.get<Contract>(`/contracts/${id}`).then(r => r.data),
  stats: () => api.get('/contracts/stats').then(r => r.data),
  top100: (institution_id?: number) =>
    api.get<Contract[]>('/contracts/top-100', { params: { institution_id } }).then(r => r.data),
}

export const companiesApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<PagedResponse<Company>>('/companies', { params }).then(r => r.data),
  get: (id: number) => api.get<Company>(`/companies/${id}`).then(r => r.data),
  ranking: (limit = 50, institution_id?: number) =>
    api.get<Company[]>('/companies/ranking', { params: { limit, institution_id } }).then(r => r.data),
  sharedReps: () => api.get('/companies/shared-representatives').then(r => r.data),
  inhabilitados: (limit = 100) => api.get('/companies/inhabilitados', { params: { limit } }).then(r => r.data),
}

export const institutionsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<Institution[]>('/institutions', { params }).then(r => r.data),
  get: (id: number) => api.get<Institution>(`/institutions/${id}`).then(r => r.data),
  ranking: (limit = 30) =>
    api.get('/institutions/ranking', { params: { limit } }).then(r => r.data),
}

export const loansApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<PagedResponse<Loan>>('/loans', { params }).then(r => r.data),
  get: (id: number) => api.get<Loan>(`/loans/${id}`).then(r => r.data),
  stats: () => api.get('/loans/stats').then(r => r.data),
}

export const graphApi = {
  network: (params: {
    entity_type?: string
    entity_id?: number
    depth?: number
    min_monto?: number
  }) => api.get<GraphData>('/graph/network', { params }).then(r => r.data),
}

export const alertsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<PagedResponse<Alert>>('/alerts', { params }).then(r => r.data),
  stats: () => api.get('/alerts/stats').then(r => r.data),
  scan: () => api.post('/alerts/scan').then(r => r.data),
  review: (id: number, notas = '') =>
    api.patch(`/alerts/${id}/review`, { notas }).then(r => r.data),
  discard: (id: number) => api.patch(`/alerts/${id}/discard`).then(r => r.data),
}

export const aiApi = {
  chat: (message: string, context?: string) =>
    api.post('/ai/chat', { message, context }).then(r => r.data),
  analyzeContract: (id: number) =>
    api.post(`/ai/analyze-contract/${id}`).then(r => r.data),
  search: (q: string) =>
    api.get('/ai/search', { params: { q } }).then(r => r.data),
}

export const cooperativesApi = {
  list: (params?: Record<string, unknown>) =>
    api.get('/cooperatives', { params }).then(r => r.data),
  get: (id: number) => api.get(`/cooperatives/${id}`).then(r => r.data),
  stats: () => api.get('/cooperatives/stats').then(r => r.data),
  conContratosEstado: (limit = 50) =>
    api.get('/cooperatives/con-contratos-estado', { params: { limit } }).then(r => r.data),
}

export const legislatorsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get('/legislators', { params }).then(r => r.data),
  get: (id: number) => api.get(`/legislators/${id}`).then(r => r.data),
  stats: () => api.get('/legislators/stats').then(r => r.data),
  conContratosRelacionados: (limit = 50) =>
    api.get('/legislators/con-contratos-relacionados', { params: { limit } }).then(r => r.data),
}

export const comisionesApi = {
  list: (params?: Record<string, unknown>) =>
    api.get('/congreso/comisiones', { params }).then(r => r.data),
  get: (id: number) => api.get(`/congreso/comisiones/${id}`).then(r => r.data),
  stats: () => api.get('/congreso/comisiones/stats').then(r => r.data),
  directiva: () => api.get('/congreso/directiva').then(r => r.data),
}

export const intelligenceApi = {
  resumen: () => api.get('/intelligence/resumen').then(r => r.data),
  personasInteres: (limit = 50) =>
    api.get('/intelligence/personas-interes', { params: { limit } }).then(r => r.data),
  nombresFrecuentes: (min_apariciones = 2, search?: string) =>
    api.get('/intelligence/nombres-frecuentes', { params: { min_apariciones, search } }).then(r => r.data),
  patrones: () => api.get('/intelligence/patrones').then(r => r.data),
  redPersona: (nombre: string) =>
    api.get('/intelligence/red-persona', { params: { nombre } }).then(r => r.data),
}

export const segurosApi = {
  stats: () => api.get('/seguros/stats').then(r => r.data),
  topAseguradoras: (anio?: number) =>
    api.get('/seguros/top-aseguradoras', { params: anio ? { anio } : {} }).then(r => r.data),
}

export const etlApi = {
  run: (sources?: string[]) =>
    api.post('/etl/run', null, { params: sources ? { sources } : {} }).then(r => r.data),
  status: () => api.get('/etl/status').then(r => r.data),
}

export const exportApi = {
  contractsCsv: (params?: Record<string, unknown>) => {
    const url = new URLSearchParams(params as Record<string, string>).toString()
    window.open(`/api/export/contracts/csv?${url}`)
  },
  contractsExcel: (params?: Record<string, unknown>) => {
    const url = new URLSearchParams(params as Record<string, string>).toString()
    window.open(`/api/export/contracts/excel?${url}`)
  },
  institutionReport: (id: number) => {
    window.open(`/api/export/report/institution/${id}`)
  },
}

export default api
