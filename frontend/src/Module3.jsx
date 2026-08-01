import { useState } from 'react'
import { assessQualityMetal, assessQualityPrint } from './api'

const VERDICT_LABEL = {
  ok: { text: 'норма', cls: 'status-badge-ok' },
  defective: { text: 'брак', cls: 'status-badge-error' },
  inconclusive: { text: 'неопределённо', cls: 'status-badge-pending' },
}

function VerdictBadge({ verdict }) {
  const info = VERDICT_LABEL[verdict] ?? { text: verdict, cls: 'status-badge-pending' }
  return <span className={`status-badge ${info.cls}`}>{info.text}</span>
}

export default function Module3({ pendingInput }) {
  const [referencePhoto, setReferencePhoto] = useState(null)
  const [actualPhoto, setActualPhoto] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [report, setReport] = useState(null)

  if (!pendingInput) {
    return (
      <div className="module3">
        <section className="card">
          <p className="muted">
            Сначала пройдите Модуль 1 (генерация ТД) и Модуль 2 (согласование и симуляция).
          </p>
        </section>
      </div>
    )
  }

  async function handleAssess() {
    setBusy(true)
    setError(null)
    setReport(null)
    try {
      const result =
        pendingInput.kind === 'metal'
          ? await assessQualityMetal({
              drawing: pendingInput.drawing,
              referencePhoto,
              actualPhoto,
            })
          : await assessQualityPrint({
              stepModel: pendingInput.stepModel,
              referencePhoto,
              actualPhoto,
              amTechnologyCode: pendingInput.amTechnologyCode,
              materialGroupCode: pendingInput.materialGroupCode,
            })
      setReport(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="module3">
      <section className="card">
        <h2>3.1. Сравнение фото изделия с эталоном</h2>
        <p className="muted">
          Эталон — фото качественного изделия (не рендер 3D-модели: детальная геометрия
          STEP в системе не строится, см. docs/ARCHITECTURE.md). Сравнение по силуэту на
          фото демонстрационное, не точное геометрическое — по ТЗ.
        </p>
        <div className="field-row">
          <label className="file-field">
            Эталонное фото (качественное изделие)
            <input type="file" accept="image/*" onChange={(e) => setReferencePhoto(e.target.files[0] ?? null)} />
          </label>
          <label className="file-field">
            Фото изготовленного изделия
            <input type="file" accept="image/*" onChange={(e) => setActualPhoto(e.target.files[0] ?? null)} />
          </label>
        </div>
        <button type="button" disabled={!referencePhoto || !actualPhoto || busy} onClick={handleAssess}>
          {busy ? 'Сравнение…' : 'Выполнить анализ качества'}
        </button>
        {error && <p className="error-text">{error}</p>}
      </section>

      {report && (
        <>
          <section className="card">
            <h2>Отчёт об оценке качества</h2>
            <p>
              Вердикт: <VerdictBadge verdict={report.verdict} /> · схожесть силуэта с эталоном:{' '}
              {Math.round(report.similarity_score * 100)}%
            </p>
            {report.notes.length > 0 && (
              <ul className="findings-list">
                {report.notes.map((note, i) => (
                  <li key={i} className={report.verdict === 'defective' ? 'finding-blocking' : 'finding-info'}>
                    {note}
                  </li>
                ))}
              </ul>
            )}
          </section>

          {report.verdict === 'ok' && report.serial_production_plan && (
            <section className="card">
              <h2>3.2. Документы для запуска в серию</h2>
              <p className="muted">
                Демонстрационная оценочная модель (не производственный расчёт) — простые
                формулы от числа операций и предупреждений автоподбора.
              </p>
              <dl className="kv-list">
                <dt>Число операций</dt>
                <dd>{report.serial_production_plan.operation_count}</dd>
                <dt>Расчётное время цикла</dt>
                <dd>{report.serial_production_plan.estimated_cycle_time_minutes} мин</dd>
                <dt>Партия 100 шт. (оценка)</dt>
                <dd>{report.serial_production_plan.estimated_batch_100_duration_days} дн.</dd>
                <dt>Себестоимость единицы (оценка)</dt>
                <dd>{report.serial_production_plan.estimated_unit_cost_rub} ₽</dd>
                <dt>Уровень риска</dt>
                <dd>{report.serial_production_plan.risk_level}</dd>
                <dt>Оценка процента брака</dt>
                <dd>{report.serial_production_plan.estimated_defect_rate_percent}%</dd>
              </dl>
              {report.serial_production_plan.workshop_load_notes.length > 0 && (
                <ul className="findings-list">
                  {report.serial_production_plan.workshop_load_notes.map((n, i) => (
                    <li key={i} className="finding-info">
                      {n}
                    </li>
                  ))}
                </ul>
              )}

              <h3>Рекомендации по оптимизации техпроцесса</h3>
              <ul className="findings-list">
                {report.optimization_suggestions.map((s, i) => (
                  <li key={i} className="finding-info">
                    {s}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {report.verdict === 'defective' && (
            <section className="card">
              <h2>Рекомендации по устранению причин брака</h2>
              <ul className="findings-list">
                {report.remediation_recommendations.map((r, i) => (
                  <li key={i} className="finding-warning">
                    {r}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  )
}
