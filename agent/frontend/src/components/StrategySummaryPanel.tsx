import { useTranslation } from '../i18n/LanguageContext'
import type { RewriteStrategy } from '../api/types'

export default function StrategySummaryPanel({ strategy }: { strategy: RewriteStrategy }) {
  const { t } = useTranslation()
  const high = strategy.actions.filter((a) => a.priority <= 2).length
  const medium = strategy.actions.filter((a) => a.priority === 3).length
  const low = strategy.actions.filter((a) => a.priority >= 4).length

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>{t('runDetail.strategySummary.title')}</h3>
      <dl className="run-info-list">
        <dt>{t('runDetail.strategySummary.total')}</dt>
        <dd>{strategy.actions.length}</dd>
        <dt>{t('runDetail.strategySummary.high')}</dt>
        <dd>{high}</dd>
        <dt>{t('runDetail.strategySummary.medium')}</dt>
        <dd>{medium}</dd>
        <dt>{t('runDetail.strategySummary.low')}</dt>
        <dd>{low}</dd>
      </dl>
    </div>
  )
}
