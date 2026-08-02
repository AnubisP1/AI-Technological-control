import { BrowserRouter, Routes, Route } from 'react-router'
import { Factory, ShieldCheck, Network } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { LandingPage } from '@/routes/LandingPage'
import { ModulePlaceholder } from '@/routes/ModulePlaceholder'
import { AnalysisPage } from '@/routes/AnalysisPage'

function App() {
  return (
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
              <ModulePlaceholder icon={Factory} title="Производство" phase="Фазе 13" />
            </AppShell>
          }
        />
        <Route
          path="/app/quality"
          element={
            <AppShell>
              <ModulePlaceholder icon={ShieldCheck} title="Контроль качества" phase="Фазе 13" />
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
  )
}

export default App
