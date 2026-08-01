import { useState } from 'react'
import './App.css'

const NAV_ITEMS = [
  { id: 'module1', label: 'Анализ КД' },
  { id: 'module2', label: 'Контроль и исполнение' },
  { id: 'module3', label: 'Оценка качества' },
  { id: 'module4', label: 'Серийное производство' },
]

function App() {
  const [activeModule, setActiveModule] = useState(NAV_ITEMS[0].id)

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
          <span className="status-badge status-badge-pending">В разработке</span>
        </header>
        <section className="card">
          <p>Экран модуля будет реализован на соответствующей фазе (см. dev/PLAN.md).</p>
        </section>
      </main>
    </div>
  )
}

export default App
