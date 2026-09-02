import { ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTranslation } from '../i18n/LanguageContext'
import type { RunMetadata } from '../api/types'
import StatusBadge from './StatusBadge'

export default function RunHeader({ run }: { run: RunMetadata }) {
  const { t } = useTranslation()
  return (
    <div>
      <div className="breadcrumb">
        <Link to="/">{t('runDetail.breadcrumbRuns')}</Link> / {run.jd_label}
      </div>
      <div className="page-header">
        <div className="row-lead">
          <div className="avatar-square" style={{ width: 40, height: 40, fontSize: 13 }}>
            JD
          </div>
          <div>
            <h1 style={{ margin: 0 }}>{run.jd_label}</h1>
            <p className="muted">
              {run.company ?? t('runDetail.uncategorized')} · {run.run_id}
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {run.langsmith_trace_url && (
            <a
              className="button secondary"
              href={run.langsmith_trace_url}
              target="_blank"
              rel="noreferrer"
            >
              {t('runDetail.langsmith')}
              <ExternalLink size={14} />
            </a>
          )}
          <StatusBadge status={run.status} />
        </div>
      </div>
    </div>
  )
}
