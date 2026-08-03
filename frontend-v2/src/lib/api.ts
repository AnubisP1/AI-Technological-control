const API_BASE = '/api'

async function parseJsonOrThrow<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail ?? response.statusText
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return response.json()
}

// ---------- Модуль 1.1: анализ КД ----------

export interface TitleBlockFields {
  designation: string | null
  part_name: string | null
  material: string | null
  blank_designation: string | null
  scale: string | null
  sheet_format: string | null
  mass: string | null
}

export interface DrawingAnalysis {
  has_text_layer: boolean
  title_block: TitleBlockFields
  technical_requirements: { number: number; text: string }[]
}

export interface ViewDetection {
  method: string
  view_count: number
  regions: { x0: number; y0: number; x1: number; y1: number; element_count: number }[]
}

export interface BoundingBox {
  length_x: number
  length_y: number
  length_z: number
}

export interface StepModelAnalysis {
  face_count: number
  bounding_box: BoundingBox | null
  has_colour_annotations: boolean
  colour_count: number
}

export interface KdAnalysisResult {
  is_complete: boolean
  drawing: DrawingAnalysis | null
  view_detection: ViewDetection | null
  step_model: StepModelAnalysis | null
}

export async function analyzeKd(params: {
  drawing?: File | null
  stepModel?: File | null
}): Promise<KdAnalysisResult> {
  const form = new FormData()
  if (params.drawing) form.append('drawing', params.drawing)
  if (params.stepModel) form.append('step_model', params.stepModel)
  const response = await fetch(`${API_BASE}/kd/analyze`, { method: 'POST', body: form })
  return parseJsonOrThrow(response)
}

/**
 * Реальная тесселяция STEP -> STL (Фаза 17, часть 5) — возвращает null,
 * если backend не смог её построить (pythonocc-core не настроен, файл
 * не читается OCC и т.д., см. step_mesh_exporter.py) — это ожидаемый
 * fallback-путь, не ошибка: PartViewer в этом случае показывает
 * параметрический прокси-бокс, как и раньше.
 */
export async function fetchStepMesh(stepModel: File): Promise<ArrayBuffer | null> {
  const form = new FormData()
  form.append('step_model', stepModel)
  const response = await fetch(`${API_BASE}/kd/step-mesh`, { method: 'POST', body: form })
  if (!response.ok) return null
  return response.arrayBuffer()
}

// ---------- Модуль 1.2: оценка КД ----------

export type MatchStatus = 'matched' | 'partial_match' | 'not_found'

export interface MaterialCheck {
  material_from_drawing: string | null
  status: MatchStatus
  matched_grade: string | null
  matched_gost: string | null
  note: string | null
}

export interface BlankCheck {
  blank_from_drawing: string | null
  status: MatchStatus
  matched_designation: string | null
  note: string | null
}

export interface TechnicalRequirementCheck {
  number: number
  text: string
  is_recognized: boolean
  category: string | null
}

export interface Finding {
  severity: 'blocking' | 'warning' | 'info'
  message: string
}

export interface KdReviewReport {
  material_check: MaterialCheck | null
  blank_check: BlankCheck | null
  technical_requirement_checks: TechnicalRequirementCheck[]
  findings: Finding[]
  has_blocking_findings: boolean
  summary: { text: string; generated_by: 'llm' | 'template' } | null
}

export async function reviewKd(params: { drawing: File }): Promise<KdReviewReport> {
  const form = new FormData()
  form.append('drawing', params.drawing)
  const response = await fetch(`${API_BASE}/kd/review`, { method: 'POST', body: form })
  return parseJsonOrThrow(response)
}

export async function downloadKdReviewPdf(params: { drawing: File }): Promise<Blob> {
  const form = new FormData()
  form.append('drawing', params.drawing)
  const response = await fetch(`${API_BASE}/kd/review/pdf`, { method: 'POST', body: form })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? response.statusText)
  }
  return response.blob()
}

// ---------- Модуль 1.3: маршрутная/печатная карта ----------

export interface RouteCard {
  part_name: string | null
  material_grade: string | null
  gost_form: string | null
  columns: string[]
  rows: string[][]
  technical_requirements: string[]
  warnings: string[]
}

export async function generateRouteCard(params: { drawing: File }): Promise<RouteCard> {
  const form = new FormData()
  form.append('drawing', params.drawing)
  const response = await fetch(`${API_BASE}/kd/route-card`, { method: 'POST', body: form })
  return parseJsonOrThrow(response)
}

export interface QualityStandard {
  tolerance_mm: string
  min_wall_thickness_mm: string
  roughness_ra_raw_um: string
  roughness_ra_finished_um: string | null
  min_thread_pitch_mm: string | null
  assembly_clearance_mm: string | null
  source_note: string
}

export interface PrintProcessCard {
  part_name: string | null
  columns: string[]
  row: string[]
  quality_standard: QualityStandard | null
}

export interface PostprocessingCard {
  columns: string[]
  rows: string[][]
}

export interface PrintRouteCardResponse {
  process_card: PrintProcessCard
  postprocessing_card: PostprocessingCard
  warnings: string[]
}

export async function generatePrintRouteCard(params: {
  stepModel: File
  amTechnologyCode: string
  materialGroupCode: string
}): Promise<PrintRouteCardResponse> {
  const form = new FormData()
  form.append('step_model', params.stepModel)
  const query = new URLSearchParams({
    am_technology_code: params.amTechnologyCode,
    material_group_code: params.materialGroupCode,
  })
  const response = await fetch(`${API_BASE}/print/route-card?${query}`, {
    method: 'POST',
    body: form,
  })
  return parseJsonOrThrow(response)
}

async function _downloadPdfOrThrow(response: Response): Promise<Blob> {
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? response.statusText)
  }
  return response.blob()
}

export async function downloadRouteCardPdf(params: { drawing: File }): Promise<Blob> {
  const form = new FormData()
  form.append('drawing', params.drawing)
  const response = await fetch(`${API_BASE}/kd/route-card/pdf`, { method: 'POST', body: form })
  return _downloadPdfOrThrow(response)
}

export async function downloadOperationCardPdf(params: { drawing: File }): Promise<Blob> {
  const form = new FormData()
  form.append('drawing', params.drawing)
  const response = await fetch(`${API_BASE}/kd/operation-card/pdf`, { method: 'POST', body: form })
  return _downloadPdfOrThrow(response)
}

export async function downloadPrintRouteCardPdf(params: {
  stepModel: File
  amTechnologyCode: string
  materialGroupCode: string
}): Promise<Blob> {
  const form = new FormData()
  form.append('step_model', params.stepModel)
  const query = new URLSearchParams({
    am_technology_code: params.amTechnologyCode,
    material_group_code: params.materialGroupCode,
  })
  const response = await fetch(`${API_BASE}/print/route-card/pdf?${query}`, {
    method: 'POST',
    body: form,
  })
  return _downloadPdfOrThrow(response)
}

// ---------- Фаза 10: автоподбор материала для пластика ----------

export interface PartApplicationClass {
  code: string
  name: string
  description: string | null
}

export async function fetchPartApplicationClasses(): Promise<PartApplicationClass[]> {
  const response = await fetch(`${API_BASE}/print/part-application-classes`)
  return parseJsonOrThrow(response)
}

export interface OperatingCondition {
  code: string
  name: string
  condition_type: string
  range_min: number | null
  range_max: number | null
  unit: string | null
}

export async function fetchOperatingConditions(
  partApplicationClassCode?: string
): Promise<OperatingCondition[]> {
  const query = partApplicationClassCode
    ? `?${new URLSearchParams({ part_application_class_code: partApplicationClassCode })}`
    : ''
  const response = await fetch(`${API_BASE}/print/operating-conditions${query}`)
  return parseJsonOrThrow(response)
}

export interface MaterialRecommendationOption {
  priority: number
  am_technology_code: string
  am_technology_name: string
  material_group_code: string
  material_group_name: string
  rationale: string
  source_type: string
  source_title: string
  source_reliability: 'low' | 'medium' | 'high'
  min_infill_percent: number | null
  recommended_wall_count: number | null
  orientation_note: string | null
}

export interface MaterialRecommendationResult {
  part_application_class_code: string
  matched_operating_conditions: string[]
  options: MaterialRecommendationOption[]
  warnings: string[]
}

export async function fetchMaterialRecommendations(params: {
  partApplicationClassCode: string
  operatingConditionCodes: string[]
}): Promise<MaterialRecommendationResult> {
  const query = new URLSearchParams({
    part_application_class_code: params.partApplicationClassCode,
  })
  for (const code of params.operatingConditionCodes) {
    query.append('operating_condition_codes', code)
  }
  const response = await fetch(`${API_BASE}/print/material-recommendations?${query}`, {
    method: 'POST',
  })
  return parseJsonOrThrow(response)
}

// ---------- Модуль 2: согласование и симуляция изготовления ----------

export interface ApprovalResult {
  decision: 'approved' | 'rejected'
  comment: string | null
  can_start_simulation: boolean
}

export async function decideApproval(params: {
  decision: 'approved' | 'rejected'
  comment?: string
}): Promise<ApprovalResult> {
  const query = new URLSearchParams({ decision: params.decision })
  if (params.comment) query.append('comment', params.comment)
  const response = await fetch(`${API_BASE}/manufacturing/approval?${query}`, { method: 'POST' })
  return parseJsonOrThrow(response)
}

export interface SimulatedOperation {
  sequence_no: number
  name: string
  machine_icon: string
  machine_label: string
  program_lines: string[]
  duration_share: number
}

export interface SimulationPlan {
  part_name: string | null
  material_kind: string
  total_seconds: number
  operations: SimulatedOperation[]
}

export async function simulateMetalManufacturing(params: {
  drawing: File
}): Promise<{ plan: SimulationPlan; warnings: string[] }> {
  const form = new FormData()
  form.append('drawing', params.drawing)
  const response = await fetch(`${API_BASE}/manufacturing/simulate/metal`, {
    method: 'POST',
    body: form,
  })
  return parseJsonOrThrow(response)
}

export async function simulatePrintManufacturing(params: {
  stepModel: File
  amTechnologyCode: string
  materialGroupCode: string
}): Promise<{ plan: SimulationPlan; warnings: string[] }> {
  const form = new FormData()
  form.append('step_model', params.stepModel)
  const query = new URLSearchParams({
    am_technology_code: params.amTechnologyCode,
    material_group_code: params.materialGroupCode,
  })
  const response = await fetch(`${API_BASE}/manufacturing/simulate/print?${query}`, {
    method: 'POST',
    body: form,
  })
  return parseJsonOrThrow(response)
}

// ---------- Модуль 3: оценка качества по фото ----------

export type QualityVerdict = 'ok' | 'defective' | 'inconclusive'

export interface SerialProductionPlan {
  operation_count: number
  estimated_cycle_time_minutes: number
  estimated_batch_100_duration_days: number
  estimated_unit_cost_rub: number
  risk_level: string
  estimated_defect_rate_percent: number
  workshop_load_notes: string[]
  is_demonstration_estimate: boolean
}

export interface QualityReport {
  verdict: QualityVerdict
  similarity_score: number
  notes: string[]
  serial_production_plan: SerialProductionPlan | null
  optimization_suggestions: string[]
  remediation_recommendations: string[]
}

export async function assessQualityMetal(params: {
  drawing: File
  referencePhoto: File
  actualPhoto: File
}): Promise<QualityReport> {
  const form = new FormData()
  form.append('drawing', params.drawing)
  form.append('reference_photo', params.referencePhoto)
  form.append('actual_photo', params.actualPhoto)
  const response = await fetch(`${API_BASE}/quality/assess/metal`, { method: 'POST', body: form })
  return parseJsonOrThrow(response)
}

export async function assessQualityPrint(params: {
  stepModel: File
  referencePhoto: File
  actualPhoto: File
  amTechnologyCode: string
  materialGroupCode: string
}): Promise<QualityReport> {
  const form = new FormData()
  form.append('step_model', params.stepModel)
  form.append('reference_photo', params.referencePhoto)
  form.append('actual_photo', params.actualPhoto)
  const query = new URLSearchParams({
    am_technology_code: params.amTechnologyCode,
    material_group_code: params.materialGroupCode,
  })
  const response = await fetch(`${API_BASE}/quality/assess/print?${query}`, {
    method: 'POST',
    body: form,
  })
  return parseJsonOrThrow(response)
}

// ---------- Фаза 17, часть 5: просмотрщик БД НСИ целиком ----------

export type NsiDatabaseName = 'metal' | 'additive'

export interface NsiTableSummary {
  name: string
  row_count: number
}

export async function fetchNsiTables(database: NsiDatabaseName): Promise<NsiTableSummary[]> {
  const response = await fetch(`${API_BASE}/nsi/${database}/tables`)
  return parseJsonOrThrow(response)
}

export interface NsiTableContent {
  name: string
  columns: string[]
  rows: string[][]
  total_row_count: number
  truncated: boolean
}

export async function fetchNsiTableContent(
  database: NsiDatabaseName,
  tableName: string
): Promise<NsiTableContent> {
  const response = await fetch(`${API_BASE}/nsi/${database}/tables/${encodeURIComponent(tableName)}`)
  return parseJsonOrThrow(response)
}

// ---------- Фаза 17, часть 5: AI-ассистент по НСИ (страница "Обзор") ----------

export interface ChatReply {
  text: string
  generated_by: 'llm' | 'template'
}

export async function askAssistant(question: string): Promise<ChatReply> {
  const response = await fetch(`${API_BASE}/assistant/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  return parseJsonOrThrow(response)
}
