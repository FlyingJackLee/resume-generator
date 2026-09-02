import { useTranslation } from '../i18n/LanguageContext'
import type { RunStatus } from '../api/types'

const TONE: Record<string, string> = {
  INIT: 'neutral',
  ANALYZING: 'active', MATCHING: 'active', HR_REVIEWING: 'active', STRATEGIZING: 'active',
  EDITING: 'active', APPLYING_PATCH: 'active', VALIDATING: 'active', REVIEWING: 'active',
  REVISING: 'active', HIRING_REVIEWED: 'active', FINALIZING: 'active',
  WAITING_STRATEGY_APPROVAL: 'waiting', WAITING_FINAL_APPROVAL: 'waiting',
  COMPLETED: 'success',
  FAILED: 'danger', INTERRUPTED: 'danger', REJECTED: 'purple',
}

export default function StatusBadge({ status }: { status: RunStatus | string }) {
  const { t } = useTranslation()
  const tone = TONE[status] ?? 'neutral'
  return <span className={`badge badge-${tone}`}>{t(`statusBadge.${tone}`)}</span>
}
