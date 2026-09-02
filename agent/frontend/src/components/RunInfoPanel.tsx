import { useTranslation } from '../i18n/LanguageContext'
import type { RunMetadata } from '../api/types'
import { formatDate } from '../lib/format'
import StatusBadge from './StatusBadge'

function formatElapsed(createdAt: string, uiLang: 'zh' | 'en'): string {
  const ms = Date.now() - new Date(createdAt).getTime()
  const minutes = Math.floor(ms / 60000)
  if (minutes < 1) return uiLang === 'zh' ? '不到 1 分钟' : '< 1 min'
  if (minutes < 60) return uiLang === 'zh' ? `${minutes} 分钟` : `${minutes} min`
  const hours = Math.floor(minutes / 60)
  return uiLang === 'zh' ? `${hours} 小时 ${minutes % 60} 分钟` : `${hours}h ${minutes % 60}m`
}

export default function RunInfoPanel({ run }: { run: RunMetadata }) {
  const { t, uiLang } = useTranslation()
  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>{t('runDetail.runInfo.title')}</h3>
      <dl className="run-info-list">
        <dt>{t('runDetail.runInfo.status')}</dt>
        <dd>
          <StatusBadge status={run.status} />
        </dd>
        <dt>{t('runDetail.runInfo.stage')}</dt>
        <dd>{run.stage ?? '-'}</dd>
        <dt>{t('runDetail.runInfo.created')}</dt>
        <dd>{formatDate(run.created_at, uiLang)}</dd>
        <dt>{t('runDetail.runInfo.elapsed')}</dt>
        <dd>{formatElapsed(run.created_at, uiLang)}</dd>
      </dl>
    </div>
  )
}
