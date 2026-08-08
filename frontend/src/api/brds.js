import { api, apiDownload } from './client'

export function listBrds(params = {}) {
  const query = new URLSearchParams()
  if (params.page) query.set('page', String(params.page))
  if (params.page_size) query.set('page_size', String(params.page_size))
  if (params.status) query.set('status', params.status)
  if (params.search) query.set('search', params.search)
  if (params.file_extension) query.set('file_extension', params.file_extension)
  if (params.has_images === true) query.set('has_images', 'true')
  if (params.has_images === false) query.set('has_images', 'false')
  if (params.sort_by) query.set('sort_by', params.sort_by)
  if (params.sort_order) query.set('sort_order', params.sort_order)
  if (params.trashed) query.set('trashed', 'true')
  const qs = query.toString()
  return api.get(`/brds${qs ? `?${qs}` : ''}`)
}

export function getBrd(id, includeText = false) {
  return api.get(`/brds/${id}?include_text=${includeText}`)
}

export function getPipelineSummary(brdId) {
  return api.get(`/brds/${brdId}/pipeline-summary`)
}

/** Full features → sub-features → stories → test-cases tree in one request. */
export function getPipeline(brdId) {
  return api.get(`/brds/${brdId}/pipeline`)
}

export function getLlmUsage(brdId) {
  return api.get(`/brds/${brdId}/llm-usage`)
}

export function uploadBrd(name, file, pipelineSettings = null) {
  const form = new FormData()
  form.append('name', name)
  form.append('file', file)
  if (pipelineSettings) {
    form.append('pipeline_settings', JSON.stringify(pipelineSettings))
  }
  return api.post('/brds/upload', form)
}

export function updatePipelineSettings(brdId, pipelineSettings) {
  return api.patch(`/brds/${brdId}/pipeline-settings`, {
    pipeline_settings: pipelineSettings,
  })
}

export function extractFeatures(brdId) {
  return api.post(`/brds/${brdId}/features/extract`)
}

export function listFeatures(brdId, status) {
  const qs = status ? `?status=${status}` : ''
  return api.get(`/brds/${brdId}/features${qs}`)
}

export function generateAllSubFeatures(brdId) {
  return api.post(`/brds/${brdId}/sub-features/generate-all`)
}

export function generateAllStories(brdId) {
  return api.post(`/brds/${brdId}/stories/generate-all`)
}

export function estimateAllPoints(brdId) {
  return api.post(`/brds/${brdId}/points/estimate-all`)
}

export function generateAllTestCases(brdId) {
  return api.post(`/brds/${brdId}/test-cases/generate-all`)
}

export function reparseBrd(id) {
  return api.post(`/brds/${id}/reparse`)
}

export function deleteBrd(id) {
  return api.delete(`/brds/${id}`)
}

export function restoreBrd(id) {
  return api.post(`/brds/${id}/restore`)
}

export function purgeBrd(id) {
  return api.delete(`/brds/${id}/permanent`)
}

async function downloadExport(brdId, format) {
  const { blob, filename } = await apiDownload(`/brds/${brdId}/export?format=${format}`, {
    method: 'POST',
  })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
  return { filename }
}

/** Download approved stories + test cases as CSV. Triggers a browser file save. */
export function exportBrdCsv(brdId) {
  return downloadExport(brdId, 'csv')
}

/** Download Jira CSV importer file for approved stories. */
export function exportBrdJira(brdId) {
  return downloadExport(brdId, 'jira')
}

/** Download stakeholder Markdown pack of approved stories + tests. */
export function exportBrdMarkdown(brdId) {
  return downloadExport(brdId, 'markdown')
}
