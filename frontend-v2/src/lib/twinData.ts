/**
 * Данные цифрового двойника (Модуль 4, Фаза 14) — иллюстративная схема,
 * не привязанная к загруженным данным конкретной детали (см. ТЗ:
 * "здесь мы просто отображаем возможную архитектуру"). Состав зон и
 * телеметрия — перенос содержания из UI UX reference/factory digital
 * twin.html и visual factory.html (уже одобренные пользователем
 * референсы), симуляция значений — целиком на фронте, не запрос к
 * backend (согласовано в плане Фазы 9, см. dev/PLAN.md).
 */

export type ZoneStatus = 'online' | 'warning' | 'alert' | 'offline'

export interface TwinZone {
  id: string
  name: string
  type: string
  x: number
  y: number
  w: number
  d: number
  height: number
  color: string
  status: ZoneStatus
  load: number
  cycle: string
  output: number
  description: string
  sensors: string[]
  protocols: string[]
}

export interface TwinFactory {
  title: string
  basePower: number
  zones: TwinZone[]
  flows: [string, string][]
}

export const TWIN_FACTORIES: Record<'metal' | 'plastic', TwinFactory> = {
  metal: {
    title: 'Цех металлических деталей',
    basePower: 684,
    zones: [
      {
        id: 'warehouse', name: 'Склад металла', type: 'Склад сырья',
        x: 1, y: 1, w: 3, d: 2, height: 30, color: '#48566a',
        status: 'online', load: 73, cycle: '—', output: 124,
        description: 'Адресное хранение листового металла, профиля, прутка, порошков и технологической оснастки.',
        sensors: ['RFID', 'Весовые датчики', 'Камеры', 'Влажность'],
        protocols: ['RFID', 'OPC UA', 'WMS API'],
      },
      {
        id: 'cutting', name: 'Лазерный раскрой', type: 'Раскрой и резка',
        x: 5, y: 1, w: 3, d: 2, height: 42, color: '#536274',
        status: 'online', load: 86, cycle: '04:28', output: 238,
        description: 'Автоматизированный участок лазерной и плазменной резки листовых металлических заготовок.',
        sensors: ['Мощность лазера', 'Давление газа', 'Высота сопла', 'Камера'],
        protocols: ['PROFINET', 'OPC UA', 'EtherCAT'],
      },
      {
        id: 'forming', name: 'Гибка и штамповка', type: 'Формирование заготовок',
        x: 9, y: 1, w: 3, d: 2, height: 38, color: '#566678',
        status: 'online', load: 81, cycle: '02:15', output: 196,
        description: 'Листогибочные прессы и штамповочные комплексы с автоматическим контролем усилия.',
        sensors: ['Усилие пресса', 'Энкодеры', 'Световые завесы', 'Вибрация'],
        protocols: ['PROFINET', 'IO-Link', 'Safety PLC'],
      },
      {
        id: 'cnc', name: 'Обработка ЧПУ', type: 'Механическая обработка',
        x: 1, y: 4, w: 4, d: 3, height: 48, color: '#4c5c70',
        status: 'online', load: 91, cycle: '08:42', output: 154,
        description: 'Токарные и фрезерные обрабатывающие центры с автоматической сменой инструмента.',
        sensors: ['Вибрация шпинделя', 'Температура', 'Ток двигателя', 'Износ инструмента'],
        protocols: ['MTConnect', 'OPC UA', 'PROFINET'],
      },
      {
        id: 'metal3d', name: 'SLM / DMLS', type: 'Аддитивное производство',
        x: 6, y: 4, w: 3, d: 3, height: 52, color: '#596a7d',
        status: 'warning', load: 62, cycle: '06:21:14', output: 18,
        description: 'Печать металлических деталей методом селективного лазерного плавления порошка.',
        sensors: ['Кислород', 'Камера слоя', 'Температура', 'Мощность лазера'],
        protocols: ['OPC UA', 'MQTT', 'EtherCAT'],
      },
      {
        id: 'heat', name: 'Термообработка', type: 'Печи и охлаждение',
        x: 10, y: 4, w: 3, d: 3, height: 58, color: '#5e5960',
        status: 'online', load: 78, cycle: '01:35:00', output: 92,
        description: 'Закалка, отпуск, отжиг и контролируемое охлаждение металлических деталей.',
        sensors: ['Термопары', 'Газоанализатор', 'Давление', 'Контроль атмосферы'],
        protocols: ['Modbus TCP', 'OPC UA', 'PROFINET'],
      },
      {
        id: 'surface', name: 'Обработка поверхности', type: 'Финишная обработка',
        x: 2, y: 8, w: 3, d: 2, height: 35, color: '#4d6070',
        status: 'online', load: 68, cycle: '05:36', output: 171,
        description: 'Шлифование, дробеструйная обработка, нанесение защитных и декоративных покрытий.',
        sensors: ['Толщина покрытия', 'Давление', 'Расход', 'Машинное зрение'],
        protocols: ['PROFINET', 'IO-Link', 'Modbus'],
      },
      {
        id: 'quality', name: 'Контроль качества', type: 'Измерительная лаборатория',
        x: 6, y: 8, w: 3, d: 2, height: 32, color: '#46616d',
        status: 'online', load: 74, cycle: '03:12', output: 202,
        description: 'КИМ, 3D-сканирование, рентген и системы машинного зрения для неразрушающего контроля.',
        sensors: ['КИМ', '3D-сканер', 'Рентген', 'Камеры'],
        protocols: ['OPC UA', 'GigE Vision', 'REST API'],
      },
      {
        id: 'assembly', name: 'Сборка', type: 'Роботизированная линия',
        x: 10, y: 8, w: 3, d: 2, height: 38, color: '#516274',
        status: 'online', load: 84, cycle: '01:48', output: 184,
        description: 'Сборочные роботы, сервопрессы, сварочные посты и автоматическая маркировка.',
        sensors: ['Контроль момента', 'Камеры', 'Датчики усилия', 'Сканеры кодов'],
        protocols: ['PROFINET', 'EtherCAT', 'IO-Link'],
      },
      {
        id: 'finished', name: 'Готовая продукция', type: 'Склад и отгрузка',
        x: 14, y: 8, w: 3, d: 2, height: 27, color: '#48586b',
        status: 'online', load: 65, cycle: '—', output: 176,
        description: 'Упаковка, адресное хранение, комплектация партий и подготовка продукции к отгрузке.',
        sensors: ['RFID', 'Весы', 'Штрихкоды', 'Камеры'],
        protocols: ['RFID', 'WMS API', 'MQTT'],
      },
    ],
    flows: [
      ['warehouse', 'cutting'], ['cutting', 'forming'], ['forming', 'cnc'],
      ['forming', 'metal3d'], ['cnc', 'heat'], ['metal3d', 'heat'],
      ['heat', 'surface'], ['surface', 'quality'], ['quality', 'assembly'],
      ['assembly', 'finished'],
    ],
  },
  plastic: {
    title: 'Цех пластиковых деталей',
    basePower: 492,
    zones: [
      {
        id: 'warehouse', name: 'Склад полимеров', type: 'Склад сырья',
        x: 1, y: 1, w: 3, d: 2, height: 30, color: '#48566a',
        status: 'online', load: 69, cycle: '—', output: 148,
        description: 'Гранулят, филамент, полимерные порошки, красители и комплектующие.',
        sensors: ['RFID', 'Вес', 'Влажность', 'Температура'],
        protocols: ['RFID', 'OPC UA', 'WMS API'],
      },
      {
        id: 'prepare', name: 'Сушка и смешивание', type: 'Подготовка материала',
        x: 5, y: 1, w: 3, d: 2, height: 42, color: '#536274',
        status: 'online', load: 82, cycle: '45:00', output: 216,
        description: 'Сушка гранулята, автоматическое дозирование и смешивание полимерного сырья.',
        sensors: ['Влажность', 'Температура', 'Расход', 'Уровень бункера'],
        protocols: ['Modbus TCP', 'IO-Link', 'OPC UA'],
      },
      {
        id: 'injection', name: 'Термопластавтоматы', type: 'Литье под давлением',
        x: 9, y: 1, w: 3, d: 2, height: 44, color: '#566678',
        status: 'online', load: 89, cycle: '00:42', output: 426,
        description: 'Серийное производство пластиковых деталей методом литья под давлением.',
        sensors: ['Давление впрыска', 'Температура', 'Положение шнека', 'Смыкание'],
        protocols: ['EUROMAP 77', 'OPC UA', 'PROFINET'],
      },
      {
        id: 'cr30', name: 'FDM CR-30', type: 'Конвейерная 3D-печать',
        x: 1, y: 4, w: 4, d: 3, height: 45, color: '#4c5c70',
        status: 'online', load: 76, cycle: '02:48:12', output: 64,
        description: 'Ферма конвейерных FDM-принтеров для непрерывного производства длинных деталей.',
        sensors: ['Температура сопла', 'Температура стола', 'Филамент', 'Камера'],
        protocols: ['OctoPrint API', 'MQTT', 'Wi-Fi'],
      },
      {
        id: 'bambu', name: 'FDM Bambu Lab', type: 'Ферма FDM-принтеров',
        x: 6, y: 4, w: 3, d: 3, height: 50, color: '#596a7d',
        status: 'online', load: 88, cycle: '01:26:33', output: 83,
        description: 'Высокоскоростные FDM-принтеры для прототипирования и серийного производства.',
        sensors: ['Камеры', 'Лидар', 'Температура', 'Датчики филамента'],
        protocols: ['MQTT', 'LAN API', 'Wi-Fi'],
      },
      {
        id: 'sls', name: 'SLS-печать', type: 'Порошковая 3D-печать',
        x: 10, y: 4, w: 3, d: 3, height: 58, color: '#5e5960',
        status: 'warning', load: 71, cycle: '08:42:00', output: 24,
        description: 'Селективное лазерное спекание полиамидных и композитных порошков.',
        sensors: ['Температура камеры', 'Камера слоя', 'Лазер', 'Кислород'],
        protocols: ['OPC UA', 'MQTT', 'EtherCAT'],
      },
      {
        id: 'powder', name: 'Обработка порошка', type: 'Просеивание и регенерация',
        x: 2, y: 8, w: 3, d: 2, height: 34, color: '#4d6070',
        status: 'online', load: 66, cycle: '18:30', output: 48,
        description: 'Распаковка SLS-камер, очистка, просеивание и повторное смешивание порошка.',
        sensors: ['Запыленность', 'Размер частиц', 'Вес', 'Влажность'],
        protocols: ['Modbus', 'OPC UA', 'IO-Link'],
      },
      {
        id: 'quality', name: 'Контроль качества', type: '3D-сканирование и рентген',
        x: 6, y: 8, w: 3, d: 2, height: 32, color: '#46616d',
        status: 'online', load: 73, cycle: '02:42', output: 224,
        description: 'Геометрический и неразрушающий контроль пластиковых деталей.',
        sensors: ['3D-сканер', 'Рентген', 'Камеры', 'Спектрометр'],
        protocols: ['GigE Vision', 'OPC UA', 'REST API'],
      },
      {
        id: 'finish', name: 'Постобработка', type: 'Очистка и финишная обработка',
        x: 10, y: 8, w: 3, d: 2, height: 38, color: '#516274',
        status: 'online', load: 79, cycle: '04:15', output: 195,
        description: 'Удаление поддержек, шлифовка, окраска и химическое сглаживание.',
        sensors: ['Шероховатость', 'Камеры', 'Температура', 'Концентрация паров'],
        protocols: ['PROFINET', 'IO-Link', 'Modbus'],
      },
      {
        id: 'finished', name: 'Склад продукции', type: 'Упаковка и отгрузка',
        x: 14, y: 8, w: 3, d: 2, height: 27, color: '#48586b',
        status: 'online', load: 63, cycle: '—', output: 182,
        description: 'Сборка, упаковка, адресное хранение и подготовка пластиковых деталей к отгрузке.',
        sensors: ['RFID', 'Весы', 'Камеры', 'Штрихкоды'],
        protocols: ['RFID', 'WMS API', 'MQTT'],
      },
    ],
    flows: [
      ['warehouse', 'prepare'], ['prepare', 'injection'], ['prepare', 'cr30'],
      ['prepare', 'bambu'], ['prepare', 'sls'], ['sls', 'powder'],
      ['injection', 'quality'], ['cr30', 'quality'], ['bambu', 'quality'],
      ['powder', 'quality'], ['quality', 'finish'], ['finish', 'finished'],
    ],
  },
}

export const STATUS_COLOR: Record<ZoneStatus, string> = {
  online: '#37df91',
  warning: '#ffc857',
  alert: '#ff5364',
  offline: '#667487',
}

export const STATUS_LABEL: Record<ZoneStatus, string> = {
  online: 'Работает',
  warning: 'Ожидание',
  alert: 'Авария',
  offline: 'Отключено',
}
