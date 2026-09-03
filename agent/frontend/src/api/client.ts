import type {
  Facts,
  PaginatedRuns,
  PatchOperation,
  RewriteStrategy,
  RunArtifacts,
  RunEvent,
  RunMetadata,
  StructureItem,
} from './types'

const BASE = '/api/v1/resume/runs'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    ...init,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `请求失败：${response.status}`)
  }
  return response.json() as Promise<T>
}

export function listRuns(page: number, pageSize: number): Promise<PaginatedRuns> {
  return request(`${BASE}?page=${page}&page_size=${pageSize}`)
}

export function getRun(runId: string): Promise<RunMetadata> {
  return request(`${BASE}/${runId}`)
}

export function getRunArtifacts(runId: string): Promise<RunArtifacts> {
  return request(`${BASE}/${runId}/artifacts`)
}

export function getRunEvents(runId: string): Promise<RunEvent[]> {
  return request(`${BASE}/${runId}/events`)
}

export function getRunStructure(
  runId: string,
  source: 'input' | 'candidate' = 'input',
): Promise<StructureItem[]> {
  return request(`${BASE}/${runId}/structure?source=${source}`)
}

export function getRunFacts(runId: string): Promise<Facts> {
  return request(`${BASE}/${runId}/facts`)
}

export function reviseStrategy(runId: string, strategy: RewriteStrategy): Promise<RunMetadata> {
  return request(`${BASE}/${runId}/revise-strategy`, {
    method: 'POST',
    body: JSON.stringify(strategy),
  })
}

export function approveStrategy(runId: string, strategy: RewriteStrategy): Promise<RunMetadata> {
  return request(`${BASE}/${runId}/approve-strategy`, {
    method: 'POST',
    body: JSON.stringify({ strategy }),
  })
}

export function retryRun(runId: string): Promise<RunMetadata> {
  return request(`${BASE}/${runId}/retry`, { method: 'POST' })
}

export function approveFinal(runId: string): Promise<RunMetadata> {
  return request(`${BASE}/${runId}/approve-final`, { method: 'POST' })
}

export function rejectFinal(runId: string): Promise<RunMetadata> {
  return request(`${BASE}/${runId}/reject-final`, { method: 'POST' })
}

export function restoreOriginal(runId: string): Promise<RunMetadata> {
  return request(`${BASE}/${runId}/restore-original`, { method: 'POST' })
}

export function manualEdit(runId: string, operations: PatchOperation[]): Promise<RunMetadata> {
  return request(`${BASE}/${runId}/manual-edit`, {
    method: 'POST',
    body: JSON.stringify({ patch: { operations } }),
  })
}

export function createRun(payload: {
  jd_label: string
  company?: string
  job_description: string
}): Promise<RunMetadata> {
  return request(BASE, { method: 'POST', body: JSON.stringify(payload) })
}

export function createEditorDraft(label = '在线编辑草稿'): Promise<RunMetadata> {
  return request('/api/v1/resume/editor-drafts', {
    method: 'POST',
    body: JSON.stringify({ label }),
  })
}

export function getEditorDraft(runId: string): Promise<Record<string, unknown>> {
  return request(`/api/v1/resume/editor-drafts/${runId}`)
}

export function updateEditorDraft(runId: string, resume: Record<string, unknown>): Promise<RunMetadata> {
  return request(`/api/v1/resume/editor-drafts/${runId}`, {
    method: 'PUT',
    body: JSON.stringify({ resume }),
  })
}

export interface EditorVersion { id: string; filename: string; message: string; created_at: string }
export function getEditorVersions(runId: string): Promise<EditorVersion[]> { return request(`/api/v1/resume/editor-drafts/${runId}/versions`) }
export function getEditorExternalChange(runId: string): Promise<{ changed: boolean }> { return request(`/api/v1/resume/editor-drafts/${runId}/external-change`) }
export function resolveEditorExternalChange(runId: string, action: 'reload' | 'keep'): Promise<RunMetadata> { return request(`/api/v1/resume/editor-drafts/${runId}/external-change`, { method: 'POST', body: JSON.stringify({ action }) }) }
export function publishEditorDraft(runId: string, message: string): Promise<RunMetadata> { return request(`/api/v1/resume/editor-drafts/${runId}/publish`, { method: 'POST', body: JSON.stringify({ message }) }) }
export function rollbackEditorVersion(runId: string, versionId: string): Promise<RunMetadata> { return request(`/api/v1/resume/editor-drafts/${runId}/rollback/${versionId}`, { method: 'POST' }) }
export function editorDownloadUrl(runId: string, format: 'html' | 'pdf', lang: 'zh' | 'en'): string { return `/api/v1/resume/editor-drafts/${runId}/download/${format}/${lang}` }
export function originalYamlDownloadUrl(runId: string): string { return `/api/v1/resume/editor-drafts/${runId}/download/original-yaml` }

export interface ResumeTemplate { id: string; name: string; description: string; builtin: boolean; active: boolean; unsupported: string[] }
export function listTemplates(): Promise<ResumeTemplate[]> { return request('/api/v1/resume/templates') }
export function setActiveTemplate(templateId: string): Promise<ResumeTemplate> { return request('/api/v1/resume/templates/active', { method: 'POST', body: JSON.stringify({ template_id: templateId }) }) }
export function deleteTemplate(templateId: string): Promise<void> { return fetch(`/api/v1/resume/templates/${templateId}`, { method: 'DELETE' }).then((r) => { if (!r.ok) throw new Error('删除模板失败') }) }
export function renameTemplate(templateId: string, name: string): Promise<ResumeTemplate> { return request(`/api/v1/resume/templates/${templateId}`, { method: 'PATCH', body: JSON.stringify({ name }) }) }
export function copyTemplate(sourceId: string, templateId: string, name: string): Promise<ResumeTemplate> { return request('/api/v1/resume/templates/copy', { method: 'POST', body: JSON.stringify({ source_id: sourceId, template_id: templateId, name }) }) }
export async function importTemplate(file: File): Promise<ResumeTemplate> { const form = new FormData(); form.append('file', file); const response = await fetch('/api/v1/resume/templates/import', { method: 'POST', body: form }); if (!response.ok) { const body = await response.json().catch(() => null); throw new Error(body?.detail ?? '导入模板失败') } return response.json() as Promise<ResumeTemplate> }

export function updateNotes(runId: string, notes: string): Promise<RunMetadata> {
  return request(`${BASE}/${runId}/notes`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  })
}

export function runStreamUrl(runId: string): string {
  return `${BASE}/${runId}/stream`
}

export function previewUrl(token: string, lang: 'zh' | 'en'): string {
  return `/preview/${token}?lang=${lang}`
}
