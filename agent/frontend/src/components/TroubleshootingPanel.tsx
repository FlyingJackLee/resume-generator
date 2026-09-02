import { useTranslation } from '../i18n/LanguageContext'
import type { ValidationIssue } from '../api/types'

const SEVERITY_TONE: Record<ValidationIssue['severity'], string> = {
  critical: 'danger',
  high: 'warning',
  low: 'neutral',
}

export default function TroubleshootingPanel({ issues }: { issues: ValidationIssue[] }) {
  const { t } = useTranslation()
  const counts: Record<ValidationIssue['severity'], number> = { critical: 0, high: 0, low: 0 }
  for (const issue of issues) counts[issue.severity] += 1

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>{t('runDetail.troubleshooting.title')}</h3>
      <p className="muted">{t('runDetail.troubleshooting.total', { n: issues.length })}</p>
      <ul className="issue-list">
        {(Object.keys(counts) as ValidationIssue['severity'][])
          .filter((severity) => counts[severity] > 0)
          .map((severity) => (
            <li key={severity} style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className={`badge badge-${SEVERITY_TONE[severity]}`}>{severity}</span>
              <span>{counts[severity]}</span>
            </li>
          ))}
      </ul>
    </div>
  )
}
