import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listRuns, previewUrl } from '../api/client'
import { useTranslation } from '../i18n/LanguageContext'

const VIEWABLE_STATUSES = new Set(['WAITING_FINAL_APPROVAL', 'COMPLETED'])

export default function ResumeViewerPage() {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const [token, setToken] = useState(searchParams.get('token') ?? 'master')
  const [previewLang, setPreviewLang] = useState<'zh' | 'en'>('zh')

  const { data } = useQuery({
    queryKey: ['runs-for-viewer'],
    queryFn: () => listRuns(1, 100),
  })
  const viewableRuns = (data?.items ?? []).filter((run) => VIEWABLE_STATUSES.has(run.status))

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{t('resumeViewer.title')}</h1>
          <p>{t('resumeViewer.subtitle')}</p>
        </div>
      </div>
      <div className="card" style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16 }}>
        <label style={{ flex: 1, marginTop: 0 }}>
          {t('resumeViewer.version')}
          <select value={token} onChange={(event) => setToken(event.target.value)}>
            <option value="master">{t('resumeViewer.masterResumeOption')}</option>
            {viewableRuns.map((run) => (
              <option key={run.run_id} value={run.run_id}>
                {run.jd_label}
                {run.company ? ` · ${run.company}` : ''}
                {run.status === 'COMPLETED' ? '' : t('resumeViewer.pendingApproval')}
              </option>
            ))}
          </select>
        </label>
        <div className="lang-toggle" style={{ display: 'flex', gap: 4 }}>
          <button className={previewLang === 'zh' ? 'active' : ''} onClick={() => setPreviewLang('zh')}>
            中文
          </button>
          <button className={previewLang === 'en' ? 'active' : ''} onClick={() => setPreviewLang('en')}>
            English
          </button>
        </div>
      </div>
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <iframe className="preview-frame" style={{ border: 0, borderRadius: 0 }} title="Resume preview" src={previewUrl(token, previewLang)} />
      </div>
    </div>
  )
}
