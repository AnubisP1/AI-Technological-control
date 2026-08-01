import { useState } from 'react'
import {
  analyzeKd,
  generatePrintRouteCard,
  generateRouteCard,
  reviewKd,
} from './api'

const AM_TECHNOLOGIES = [
  { code: 'FDM', label: 'FDM' },
  { code: 'SLA', label: 'SLA' },
  { code: 'MSLA', label: 'MSLA' },
  { code: 'SLS', label: 'SLS' },
]

function StatusBadge({ status }) {
  const map = {
    matched: { text: 'совпадение', cls: 'status-badge-ok' },
    partial_match: { text: 'частичное совпадение', cls: 'status-badge-pending' },
    not_found: { text: 'не найдено', cls: 'status-badge-error' },
  }
  const info = map[status] ?? { text: status, cls: 'status-badge-pending' }
  return <span className={`status-badge ${info.cls}`}>{info.text}</span>
}

function CardTable({ columns, rows }) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((value, j) => (
                <td key={j}>{value || '—'}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Module1({ onRouteCardReady, onProceedToApproval }) {
  const [materialKind, setMaterialKind] = useState('metal')
  const [drawing, setDrawing] = useState(null)
  const [stepModel, setStepModel] = useState(null)
  const [amTechnology, setAmTechnology] = useState('FDM')
  const [materialGroupCode, setMaterialGroupCode] = useState('')

  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [review, setReview] = useState(null)
  const [routeCard, setRouteCard] = useState(null)
  const [printCards, setPrintCards] = useState(null)

  const canAnalyze =
    materialKind === 'metal' ? Boolean(drawing) : Boolean(stepModel) && Boolean(materialGroupCode)

  async function handleAnalyze() {
    setBusy(true)
    setError(null)
    setAnalysis(null)
    setReview(null)
    setRouteCard(null)
    setPrintCards(null)
    try {
      if (materialKind === 'metal') {
        const analysisResult = await analyzeKd({ drawing, stepModel })
        setAnalysis(analysisResult)
        const reviewResult = await reviewKd({ drawing })
        setReview(reviewResult)
        const card = await generateRouteCard({ drawing })
        setRouteCard(card)
        onRouteCardReady({ kind: 'metal', drawing })
      } else {
        const card = await generatePrintRouteCard({
          stepModel,
          amTechnologyCode: amTechnology,
          materialGroupCode,
        })
        setPrintCards(card)
        onRouteCardReady({
          kind: 'plastic',
          stepModel,
          amTechnologyCode: amTechnology,
          materialGroupCode,
        })
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="module1">
      <section className="card">
        <h2>1. Загрузка КД и выбор материала</h2>
        <div className="field-row">
          <label>
            <input
              type="radio"
              name="material-kind"
              checked={materialKind === 'metal'}
              onChange={() => setMaterialKind('metal')}
            />
            Металл
          </label>
          <label>
            <input
              type="radio"
              name="material-kind"
              checked={materialKind === 'plastic'}
              onChange={() => setMaterialKind('plastic')}
            />
            Пластик
          </label>
        </div>

        {materialKind === 'metal' ? (
          <div className="field-row">
            <label className="file-field">
              Чертёж (PDF)
              <input
                type="file"
                accept="application/pdf"
                onChange={(e) => setDrawing(e.target.files[0] ?? null)}
              />
            </label>
            <label className="file-field">
              STEP-модель (опционально)
              <input type="file" onChange={(e) => setStepModel(e.target.files[0] ?? null)} />
            </label>
          </div>
        ) : (
          <div className="field-row">
            <label className="file-field">
              STEP-модель
              <input type="file" onChange={(e) => setStepModel(e.target.files[0] ?? null)} />
            </label>
            <label className="file-field">
              Технология печати
              <select value={amTechnology} onChange={(e) => setAmTechnology(e.target.value)}>
                {AM_TECHNOLOGIES.map((t) => (
                  <option key={t.code} value={t.code}>
                    {t.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="file-field">
              Код материала (напр. PETG, RESIN_STD)
              <input
                type="text"
                value={materialGroupCode}
                onChange={(e) => setMaterialGroupCode(e.target.value.toUpperCase())}
                placeholder="PETG"
              />
            </label>
          </div>
        )}

        <button type="button" disabled={!canAnalyze || busy} onClick={handleAnalyze}>
          {busy ? 'Обработка…' : 'Проанализировать и сгенерировать документацию'}
        </button>

        {error && <p className="error-text">{error}</p>}
      </section>

      {analysis && (
        <section className="card">
          <h2>Результат распознавания КД</h2>
          <dl className="kv-list">
            <dt>Обозначение</dt>
            <dd>{analysis.drawing?.title_block?.designation || '—'}</dd>
            <dt>Наименование детали</dt>
            <dd>{analysis.drawing?.title_block?.part_name || '—'}</dd>
            <dt>Материал</dt>
            <dd>{analysis.drawing?.title_block?.material || '—'}</dd>
            <dt>Число видов на чертеже</dt>
            <dd>{analysis.view_detection?.view_count ?? '—'}</dd>
            <dt>Геометрия (STEP)</dt>
            <dd>
              {analysis.step_model
                ? `${analysis.step_model.face_count ?? '—'} граней`
                : 'модель не загружена'}
            </dd>
          </dl>
        </section>
      )}

      {review && (
        <section className="card">
          <h2>Отчёт об оценке КД</h2>
          {review.material_check && (
            <p>
              Материал «{review.material_check.material_from_drawing}»:{' '}
              <StatusBadge status={review.material_check.status} />
              {review.material_check.note ? ` — ${review.material_check.note}` : ''}
            </p>
          )}
          {review.blank_check && (
            <p>
              Заготовка «{review.blank_check.blank_from_drawing}»:{' '}
              <StatusBadge status={review.blank_check.status} />
              {review.blank_check.note ? ` — ${review.blank_check.note}` : ''}
            </p>
          )}
          {review.findings.length > 0 && (
            <ul className="findings-list">
              {review.findings.map((f, i) => (
                <li key={i} className={`finding-${f.severity}`}>
                  {f.message}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {routeCard && (
        <section className="card">
          <h2>Маршрутная карта — {routeCard.part_name || 'деталь'}</h2>
          <p className="muted">{routeCard.gost_form}</p>
          <CardTable columns={routeCard.columns} rows={routeCard.rows} />
          {routeCard.warnings.length > 0 && (
            <ul className="findings-list">
              {routeCard.warnings.map((w, i) => (
                <li key={i} className="finding-warning">
                  {w}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {printCards && (
        <section className="card">
          <h2>Карта техпроцесса печати — {printCards.process_card.part_name || 'деталь'}</h2>
          <CardTable
            columns={printCards.process_card.columns}
            rows={[printCards.process_card.row]}
          />
          <h3>Постобработка</h3>
          <CardTable
            columns={printCards.postprocessing_card.columns}
            rows={printCards.postprocessing_card.rows}
          />
          {printCards.warnings.length > 0 && (
            <ul className="findings-list">
              {printCards.warnings.map((w, i) => (
                <li key={i} className="finding-warning">
                  {w}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {(routeCard || printCards) && (
        <section className="card">
          <p className="muted">
            Комплект технологической документации сформирован. Передайте его на
            согласование главному технологу.
          </p>
          <button type="button" onClick={onProceedToApproval}>
            Перейти к согласованию
          </button>
        </section>
      )}
    </div>
  )
}
