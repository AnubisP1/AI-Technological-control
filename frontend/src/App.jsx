import { useState } from 'react'
import './App.css'
import Module1 from './Module1.jsx'
import Module2 from './Module2.jsx'
import Module3 from './Module3.jsx'

const NAV_ITEMS = [
  { id: 'module1', label: 'Анализ КД' },
  { id: 'module2', label: 'Контроль и исполнение' },
  { id: 'module3', label: 'Оценка качества' },
  { id: 'module4', label: 'Серийное производство' },
]

const READY_MODULES = new Set(['module1', 'module2', 'module3'])

function App() {
  const [activeModule, setActiveModule] = useState(NAV_ITEMS[0].id)
  const [pendingInput, setPendingInput] = useState(null)

  function handleRouteCardReady(input) {
    setPendingInput(input)
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-title">Цифровое производство</div>
        <nav>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-item ${activeModule === item.id ? 'nav-item-active' : ''}`}
              onClick={() => setActiveModule(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="content">
        <header className="content-header">
          <h1>{NAV_ITEMS.find((item) => item.id === activeModule)?.label}</h1>
          {!READY_MODULES.has(activeModule) && (
            <span className="status-badge status-badge-pending">В разработке</span>
          )}
        </header>

        {activeModule === 'module1' && (
          <Module1
            onRouteCardReady={handleRouteCardReady}
            onProceedToApproval={() => setActiveModule('module2')}
          />
        )}
        {activeModule === 'module2' && (
          <Module2
            pendingInput={pendingInput}
            onQualityCheck={() => setActiveModule('module3')}
          />
        )}
        {activeModule === 'module3' && <Module3 pendingInput={pendingInput} />}
        {!READY_MODULES.has(activeModule) && (
          <section className="card">
            <p>Экран модуля будет реализован на соответствующей фазе (см. dev/PLAN.md).</p>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
