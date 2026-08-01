import { useState } from 'react'
import {
  analyzeKd,
  downloadKdReviewPdf,
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

function TreeNode({ label, status, note, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  const statusCls = status
    ? { matched: 'tree-node-ok', partial_match: 'tree-node-warn', not_found: 'tree-node-error' }[status]
    : ''
  const hasChildren = Boolean(children)

  return (
    <div className="tree-node">
      <div
        className={`tree-node-row ${statusCls} ${hasChildren ? 'tree-node-toggle' : ''}`}
        onClick={hasChildren ? () => setOpen((o) => !o) : undefined}
      >
        {hasChildren && <span className="tree-caret">{open ? '▾' : '▸'}</span>}
        <span className="tree-node-label">{label}</span>
        {status && <StatusBadge status={status} />}
      </div>
      {note && <div className="tree-node-note">{note}</div>}
      {hasChildren && open && <div className="tree-node-children">{children}</div>}
    </div>
  )
}

function ReviewTree({ review }) {
  return (
    <div className="review-tree">
      {review.material_check && (
        <TreeNode
          label={`Материал: ${review.material_check.material_from_drawing || '—'}`}
          status={review.material_check.status}
          note={review.material_check.note}
        />
      )}
      {review.blank_check && (
        <TreeNode
          label={`Заготовка: ${review.blank_check.blank_from_drawing || '—'}`}
          status={review.blank_check.status}
          note={review.blank_check.note}
        />
      )}
      {review.technical_requirement_checks.length > 0 && (
        <TreeNode label="Технические требования" defaultOpen={false}>
          {review.technical_requirement_checks.map((tt) => (
            <TreeNode
              key={tt.number}
              label={`п.${tt.number}: ${tt.text}`}
              status={tt.is_recognized ? 'matched' : 'partial_match'}
              note={`категория: ${tt.category || 'не распознана'}`}
            />
          ))}
        </TreeNode>
      )}
    </div>
  )
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
  const [pdfBusy, setPdfBusy] = useState(false)
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

  async function handleDownloadPdf() {
    setPdfBusy(true)
    setError(null)
    try {
      const blob = await downloadKdReviewPdf({ drawing })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'kd_review_report.pdf'
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err.message)
    } finally {
      setPdfBusy(false)
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
          <div className="content-header" style={{ marginBottom: 12 }}>
            <h2 style={{ margin: 0 }}>Отчёт об оценке КД</h2>
            <button type="button" className="btn-secondary" disabled={pdfBusy} onClick={handleDownloadPdf}>
              {pdfBusy ? 'Формирование PDF…' : 'Скачать PDF'}
            </button>
          </div>

          <ReviewTree review={review} />

          {review.findings.length > 0 && (
            <>
              <h3>Находки</h3>
              <ul className="findings-list">
                {review.findings.map((f, i) => (
                  <li key={i} className={`finding-${f.severity}`}>
                    {f.message}
                  </li>
                ))}
              </ul>
            </>
          )}

          {review.summary && (
            <>
              <h3>
                Резюме{' '}
                <span className="muted">
                  ({review.summary.generated_by === 'llm' ? 'сгенерировано LLM' : 'шаблонный текст'})
                </span>
              </h3>
              <p>{review.summary.text}</p>
            </>
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
