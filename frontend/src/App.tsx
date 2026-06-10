import { Routes, Route, useLocation } from 'react-router-dom'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import Dashboard from './pages/Dashboard'
import Contracts from './pages/Contracts'
import ContractDetail from './pages/ContractDetail'
import Companies from './pages/Companies'
import CompanyDetail from './pages/CompanyDetail'
import Institutions from './pages/Institutions'
import InstitutionDetail from './pages/InstitutionDetail'
import Loans from './pages/Loans'
import GraphView from './pages/GraphView'
import AlertsPage from './pages/AlertsPage'
import AIChat from './pages/AIChat'
import ETLPanel from './pages/ETLPanel'
import Intelligence from './pages/Intelligence'
import Cooperatives from './pages/Cooperatives'
import Banks from './pages/Banks'
import PoliticalParties from './pages/PoliticalParties'
import Legislators from './pages/Legislators'
import Inhabilitados from './pages/Inhabilitados'
import Nominas from './pages/Nominas'
import Seguros from './pages/Seguros'
import PGR from './pages/PGR'

export default function App() {
  const location = useLocation()
  return (
    <Layout>
      <ErrorBoundary key={location.pathname}>
      <Routes>
        <Route path="/"                          element={<Dashboard />} />
        <Route path="/contracts"                 element={<Contracts />} />
        <Route path="/contracts/:id"             element={<ContractDetail />} />
        <Route path="/companies"                 element={<Companies />} />
        <Route path="/companies/:id"             element={<CompanyDetail />} />
        <Route path="/institutions"              element={<Institutions />} />
        <Route path="/institutions/:id"          element={<InstitutionDetail />} />
        <Route path="/loans"                     element={<Loans />} />
        <Route path="/graph"                     element={<GraphView />} />
        <Route path="/alerts"                    element={<AlertsPage />} />
        <Route path="/inhabilitados"              element={<Inhabilitados />} />
        <Route path="/ai"                        element={<AIChat />} />
        <Route path="/etl"                       element={<ETLPanel />} />
        <Route path="/intelligence"              element={<Intelligence />} />
        <Route path="/cooperatives"              element={<Cooperatives />} />
        <Route path="/banks"                     element={<Banks />} />
        <Route path="/parties"                   element={<PoliticalParties />} />
        <Route path="/legislators"               element={<Legislators />} />
        <Route path="/nominas"                   element={<Nominas />} />
        <Route path="/seguros"                   element={<Seguros />} />
        <Route path="/pgr"                       element={<PGR />} />
      </Routes>
      </ErrorBoundary>
    </Layout>
  )
}
