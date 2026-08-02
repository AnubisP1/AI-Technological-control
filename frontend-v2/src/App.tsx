import { BrowserRouter, Routes, Route } from 'react-router'
import { Network } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { LandingPage } from '@/routes/LandingPage'
import { ModulePlaceholder } from '@/routes/ModulePlaceholder'
import { AnalysisPage } from '@/routes/AnalysisPage'
import { ProductionPage } from '@/routes/ProductionPage'
import { QualityPage } from '@/routes/QualityPage'
import { WorkflowProvider } from '@/lib/workflow'

function App() {
  return (
    <WorkflowProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route
            path="/app/analysis"
            element={
              <AppShell>
                <AnalysisPage />
              </AppShell>
            }
          />
          <Route
            path="/app/production"
            element={
              <AppShell>
                <ProductionPage />
              </AppShell>
            }
          />
          <Route
            path="/app/quality"
            element={
              <AppShell>
                <QualityPage />
              </AppShell>
            }
          />
          <Route
            path="/app/digital-twin"
            element={
              <AppShell>
                <ModulePlaceholder icon={Network} title="Цифровой двойник" phase="Фазе 14" />
              </AppShell>
            }
          />
        </Routes>
      </BrowserRouter>
    </WorkflowProvider>
  )
}

export default App
