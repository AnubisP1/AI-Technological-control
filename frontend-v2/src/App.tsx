import { BrowserRouter, Routes, Route } from 'react-router'
import { AppShell } from '@/components/layout/AppShell'
import { LandingPage } from '@/routes/LandingPage'
import { AnalysisPage } from '@/routes/AnalysisPage'
import { ProductionPage } from '@/routes/ProductionPage'
import { QualityPage } from '@/routes/QualityPage'
import { DigitalTwinPage } from '@/routes/DigitalTwinPage'
import { NsiExpertisePage } from '@/routes/NsiExpertisePage'
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
                <DigitalTwinPage />
              </AppShell>
            }
          />
          <Route
            path="/app/nsi-expertise"
            element={
              <AppShell>
                <NsiExpertisePage />
              </AppShell>
            }
          />
        </Routes>
      </BrowserRouter>
    </WorkflowProvider>
  )
}

export default App
