import { useState } from 'react'

// Иллюстративные схемы цеха (Модуль 4, ТЗ: "здесь мы просто отображаем
// возможную архитектуру цеха... универсальную архитектуру/схему для
// цеха по изготовлению деталей из металла и... из пластика"). Состав
// зон для пластика — прямая формулировка ТЗ; для металла — по аналогии,
// основанной на типах оборудования, уже описанных в БД НСИ металла
// (см. equipment_type в БД НСИ/02_equipment.sql): токарные, фрезерные,
// сверлильные, шлифовальные станки.
const SCHEMES = {
  metal: {
    label: 'Цех по изготовлению деталей из металла',
    zones: [
      { id: 'turning', label: 'Токарный участок', hint: 'токарные, токарно-винторезные станки, станки с ЧПУ' },
      { id: 'milling', label: 'Фрезерный участок', hint: 'фрезерные станки, обрабатывающие центры с ЧПУ' },
      { id: 'drilling', label: 'Сверлильный участок', hint: 'вертикально-сверлильные станки' },
      { id: 'grinding', label: 'Шлифовальный участок', hint: 'круглошлифовальные станки' },
      { id: 'qc', label: 'Контроль качества', hint: 'КИМ, микрометрия, машинное зрение' },
      { id: 'assembly', label: 'Сборка' },
      { id: 'energy', label: 'Энергетический блок' },
      { id: 'material-warehouse', label: 'Склад материалов и заготовок' },
      { id: 'office', label: 'Офис и управление' },
      { id: 'goods-warehouse', label: 'Склад готовой продукции' },
    ],
  },
  plastic: {
    label: 'Цех по изготовлению деталей из пластика',
    zones: [
      { id: 'injection', label: 'Термопластавтомат' },
      { id: 'fdm-conveyor', label: 'FDM-конвейерные принтеры', hint: 'напр. Creality CR-30' },
      { id: 'fdm-desktop', label: 'FDM настольные принтеры', hint: 'напр. Bambu Lab' },
      { id: 'sls', label: 'SLS-печать' },
      { id: 'cleaning', label: 'Очистка' },
      { id: 'powder-handling', label: 'Обработка порошка' },
      { id: 'part-finishing', label: 'Обработка деталей' },
      { id: 'qc', label: 'Контроль качества', hint: 'сканеры, рентген, машинное зрение, лидары' },
      { id: 'assembly', label: 'Сборка' },
      { id: 'energy', label: 'Энергетический блок' },
      { id: 'material-warehouse', label: 'Склад материалов и комплектующих' },
      { id: 'office', label: 'Офис и управление' },
      { id: 'goods-warehouse', label: 'Склад готовой продукции' },
    ],
  },
}

const IIOT_LAYERS = [
  {
    id: 'actuators',
    label: 'Исполнительные механизмы',
    hint: 'приводы станков/принтеров, роботы-манипуляторы, конвейеры',
  },
  {
    id: 'sensors',
    label: 'Датчики контроля',
    hint: 'температура, вибрация, ток привода, положение осей, качество печати/обработки',
  },
  {
    id: 'telemetry',
    label: 'Передача информации (телеметрия)',
    hint: 'шина/шлюз сбора данных оборудования → MES/SCADA',
  },
]

function ZoneCard({ zone, isHighlighted, onHover }) {
  return (
    <div
      className={`shop-zone ${isHighlighted ? 'shop-zone-highlighted' : ''}`}
      onMouseEnter={() => onHover(zone.id)}
      onMouseLeave={() => onHover(null)}
    >
      <div className="shop-zone-label">{zone.label}</div>
      {zone.hint && <div className="shop-zone-hint">{zone.hint}</div>}
    </div>
  )
}

export default function Module4() {
  const [materialKind, setMaterialKind] = useState('metal')
  const [hoveredZone, setHoveredZone] = useState(null)
  const scheme = SCHEMES[materialKind]

  return (
    <div className="module4">
      <section className="card">
        <h2>Архитектура цеха / IIoT (иллюстративная схема)</h2>
        <p className="muted">
          Статическая референсная схема — не привязана к загруженным данным и не
          отражает конкретный реальный цех. Демонстрирует состав оборудования и слой
          Индустриального интернета вещей (исполнительные механизмы, датчики контроля,
          передача телеметрии), как того требует Модуль 4 ТЗ.
        </p>
        <div className="field-row">
          <label>
            <input
              type="radio"
              name="module4-material-kind"
              checked={materialKind === 'metal'}
              onChange={() => setMaterialKind('metal')}
            />
            Металл
          </label>
          <label>
            <input
              type="radio"
              name="module4-material-kind"
              checked={materialKind === 'plastic'}
              onChange={() => setMaterialKind('plastic')}
            />
            Пластик
          </label>
        </div>
      </section>

      <section className="card">
        <h2>{scheme.label}</h2>
        <div className="shop-zone-grid">
          {scheme.zones.map((zone) => (
            <ZoneCard key={zone.id} zone={zone} isHighlighted={hoveredZone === zone.id} onHover={setHoveredZone} />
          ))}
        </div>
      </section>

      <section className="card">
        <h2>Слой IIoT</h2>
        <div className="iiot-layer">
          {IIOT_LAYERS.map((layer) => (
            <div key={layer.id} className="iiot-block">
              <div className="iiot-block-label">{layer.label}</div>
              <div className="shop-zone-hint">{layer.hint}</div>
            </div>
          ))}
        </div>
        <p className="muted" style={{ marginTop: 12 }}>
          Каждая зона цеха выше условно подключена к этому слою: оборудование передаёт
          телеметрию через датчики контроля на шину сбора данных. Это иллюстративная
          архитектура (см. ТЗ, Модуль 4) — не живая интеграция с реальным оборудованием.
        </p>
      </section>
    </div>
  )
}
