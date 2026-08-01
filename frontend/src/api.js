const API_BASE = '/api'

async function parseJsonOrThrow(response) {
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail ?? response.statusText
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return response.json()
}

export async function analyzeKd({ drawing, stepModel }) {
  const form = new FormData()
  if (drawing) form.append('drawing', drawing)
  if (stepModel) form.append('step_model', stepModel)
  const response = await fetch(`${API_BASE}/kd/analyze`, { method: 'POST', body: form })
  return parseJsonOrThrow(response)
}

export async function reviewKd({ drawing }) {
  const form = new FormData()
  form.append('drawing', drawing)
  const response = await fetch(`${API_BASE}/kd/review`, { method: 'POST', body: form })
  return parseJsonOrThrow(response)
}

export async function downloadKdReviewPdf({ drawing }) {
  const form = new FormData()
  form.append('drawing', drawing)
  const response = await fetch(`${API_BASE}/kd/review/pdf`, { method: 'POST', body: form })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? response.statusText)
  }
  return response.blob()
}

export async function generateRouteCard({ drawing }) {
  const form = new FormData()
  form.append('drawing', drawing)
  const response = await fetch(`${API_BASE}/kd/route-card`, { method: 'POST', body: form })
  return parseJsonOrThrow(response)
}

export async function generatePrintRouteCard({ stepModel, amTechnologyCode, materialGroupCode }) {
  const form = new FormData()
  form.append('step_model', stepModel)
  const params = new URLSearchParams({
    am_technology_code: amTechnologyCode,
    material_group_code: materialGroupCode,
  })
  const response = await fetch(`${API_BASE}/print/route-card?${params}`, {
    method: 'POST',
    body: form,
  })
  return parseJsonOrThrow(response)
}

export async function decideApproval({ decision, comment }) {
  const params = new URLSearchParams({ decision })
  if (comment) params.append('comment', comment)
  const response = await fetch(`${API_BASE}/manufacturing/approval?${params}`, {
    method: 'POST',
  })
  return parseJsonOrThrow(response)
}

export async function simulateMetalManufacturing({ drawing }) {
  const form = new FormData()
  form.append('drawing', drawing)
  const response = await fetch(`${API_BASE}/manufacturing/simulate/metal`, {
    method: 'POST',
    body: form,
  })
  return parseJsonOrThrow(response)
}

export async function simulatePrintManufacturing({ stepModel, amTechnologyCode, materialGroupCode }) {
  const form = new FormData()
  form.append('step_model', stepModel)
  const params = new URLSearchParams({
    am_technology_code: amTechnologyCode,
    material_group_code: materialGroupCode,
  })
  const response = await fetch(`${API_BASE}/manufacturing/simulate/print?${params}`, {
    method: 'POST',
    body: form,
  })
  return parseJsonOrThrow(response)
}

export async function assessQualityMetal({ drawing, referencePhoto, actualPhoto }) {
  const form = new FormData()
  form.append('drawing', drawing)
  form.append('reference_photo', referencePhoto)
  form.append('actual_photo', actualPhoto)
  const response = await fetch(`${API_BASE}/quality/assess/metal`, { method: 'POST', body: form })
  return parseJsonOrThrow(response)
}

export async function assessQualityPrint({
  stepModel,
  referencePhoto,
  actualPhoto,
  amTechnologyCode,
  materialGroupCode,
}) {
  const form = new FormData()
  form.append('step_model', stepModel)
  form.append('reference_photo', referencePhoto)
  form.append('actual_photo', actualPhoto)
  const params = new URLSearchParams({
    am_technology_code: amTechnologyCode,
    material_group_code: materialGroupCode,
  })
  const response = await fetch(`${API_BASE}/quality/assess/print?${params}`, {
    method: 'POST',
    body: form,
  })
  return parseJsonOrThrow(response)
}
