import { useQuery } from '@tanstack/react-query'
import { Download, Pencil } from 'lucide-react'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { listRuns, previewDownloadUrl, previewUrl, previewYamlDownloadUrl } from '../api/client'
import { useTranslation } from '../i18n/LanguageContext'

// Only COMPLETED runs are listed here: WAITING_FINAL_APPROVAL previews live on
// the run's own Gate② page now, and only a COMPLETED run's own output file is
// safe to open in the free-form editor (see ResumeEditorPage).
const VIEWABLE_STATUSES = new Set(['COMPLETED'])

export default function ResumeViewerPage() {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const [token, setToken] = useState(searchParams.get('token') ?? 'master')
  const [previewLang, setPreviewLang] = useState<'zh' | 'en'>('zh')

  const { data } = useQuery({
    queryKey: ['runs-for-viewer'],
    queryFn: () => listRuns(1, 100),
  })
  // target_file also filters out the singleton editor draft: it's internally
  // stored with status COMPLETED too (so generic "is this run done" checks
  // treat it consistently), but it never has an exported target_file and
  // isn't a real job-specific version — it already has its own dedicated
  // "修改基线版本" entry point and would be a confusing duplicate here.
  const viewableRuns = (data?.items ?? []).filter((run) => VIEWABLE_STATUSES.has(run.status) && run.target_file)

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
        <div style={{ display: 'flex', gap: 8 }}>
          <Link className="button secondary" to={token === 'master' ? '/editor' : `/editor/${token}`}>
            <Pencil size={16} />
            {t('resumeViewer.edit')}
          </Link>
          <a className="button secondary" href={previewYamlDownloadUrl(token)}>
            <Download size={16} />
            {t('resumeViewer.download.yaml')}
          </a>
          <a className="button secondary" href={previewDownloadUrl(token, 'html', previewLang)}>
            <Download size={16} />
            {t('resumeViewer.download.html')}
          </a>
          <a className="button secondary" href={previewDownloadUrl(token, 'pdf', previewLang)}>
            <Download size={16} />
            {t('resumeViewer.download.pdf')}
          </a>
        </div>
      </div>
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <iframe className="preview-frame" style={{ border: 0, borderRadius: 0 }} title="Resume preview" src={previewUrl(token, previewLang)} />
      </div>
    </div>
  )
}
