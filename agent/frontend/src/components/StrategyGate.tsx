import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { approveStrategy, reviseStrategy } from '../api/client'
import { useTranslation } from '../i18n/LanguageContext'
import type { Facts, RewriteAction, RewriteStrategy } from '../api/types'

interface EditableAction extends RewriteAction {
  keep: boolean
}

function buildPayload(
  positioning: string,
  safeKeywords: string[],
  forbiddenKeywords: string[],
  actions: EditableAction[],
): RewriteStrategy {
  return {
    positioning,
    safe_keywords: safeKeywords,
    forbidden_keywords: forbiddenKeywords,
    actions: actions
      .filter((action) => action.keep)
      .map(({ keep: _keep, ...rest }) => rest),
  }
}

function ChipInput({
  label,
  tone,
  values,
  onChange,
}: {
  label: string
  tone?: 'danger'
  values: string[]
  onChange: (next: string[]) => void
}) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState('')
  return (
    <label>
      {label}
      <div>
        {values.map((word) => (
          <span key={word} className={`chip ${tone ? `chip-${tone}` : ''}`}>
            {word}{' '}
            <a
              href="#remove"
              onClick={(event) => {
                event.preventDefault()
                onChange(values.filter((item) => item !== word))
              }}
            >
              ×
            </a>
          </span>
        ))}
      </div>
      <input
        value={draft}
        placeholder={t('strategyGate.addHint')}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key !== 'Enter') return
          event.preventDefault()
          const word = draft.trim()
          if (word && !values.includes(word)) onChange([...values, word])
          setDraft('')
        }}
      />
    </label>
  )
}

export default function StrategyGate({
  runId,
  strategy,
  pathLabels,
  facts,
}: {
  runId: string
  strategy: RewriteStrategy
  pathLabels: Record<string, string>
  facts: Facts
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [positioning, setPositioning] = useState(strategy.positioning)
  const [safeKeywords, setSafeKeywords] = useState(strategy.safe_keywords)
  const [forbiddenKeywords, setForbiddenKeywords] = useState(strategy.forbidden_keywords)
  const [actions, setActions] = useState<EditableAction[]>(
    strategy.actions.map((action) => ({ ...action, keep: true })),
  )

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['run', runId] })
    queryClient.invalidateQueries({ queryKey: ['run-artifacts', runId] })
  }

  const saveMutation = useMutation({
    mutationFn: () =>
      reviseStrategy(runId, buildPayload(positioning, safeKeywords, forbiddenKeywords, actions)),
    onSuccess: invalidate,
  })
  const approveMutation = useMutation({
    mutationFn: () =>
      approveStrategy(runId, buildPayload(positioning, safeKeywords, forbiddenKeywords, actions)),
    onSuccess: invalidate,
  })

  function updateAction(index: number, changes: Partial<EditableAction>) {
    setActions((current) =>
      current.map((action, i) => (i === index ? { ...action, ...changes } : action)),
    )
  }

  const mutationError = saveMutation.error ?? approveMutation.error

  return (
    <div className="card">
      <h2>{t('strategyGate.title')}</h2>

      <label>
        {t('strategyGate.positioning')}
        <textarea
          rows={3}
          value={positioning}
          onChange={(event) => setPositioning(event.target.value)}
        />
      </label>

      <ChipInput label={t('strategyGate.allowedKeywords')} values={safeKeywords} onChange={setSafeKeywords} />
      <ChipInput
        label={t('strategyGate.forbiddenKeywords')}
        tone="danger"
        values={forbiddenKeywords}
        onChange={setForbiddenKeywords}
      />

      <h3>{t('strategyGate.pendingActionsTitle')}</h3>
      <p className="muted">{t('strategyGate.pendingActionsHint')}</p>
      <ul className="issue-list">
        {actions.map((action, index) => (
          <li key={index}>
            <label style={{ fontWeight: 400 }}>
              <input
                type="checkbox"
                checked={action.keep}
                onChange={(event) => updateAction(index, { keep: event.target.checked })}
              />{' '}
              <span className="badge badge-neutral">{action.action}</span>{' '}
              {pathLabels[action.target_path] ?? action.target_path}
            </label>
            <label>
              {t('strategyGate.priority')}
              <input
                type="number"
                min={1}
                max={5}
                value={action.priority}
                onChange={(event) =>
                  updateAction(index, { priority: Number(event.target.value) })
                }
              />
            </label>
            <label>
              {t('strategyGate.instruction')}
              <input
                type="text"
                value={action.instruction}
                onChange={(event) => updateAction(index, { instruction: event.target.value })}
              />
            </label>
            {action.supported_by
              .map((factId) => facts[factId])
              .filter(Boolean)
              .map((fact) => (
                <div className="muted" key={fact.id}>
                  {t('strategyGate.evidence')}{fact.statement.zh || fact.statement.en}
                </div>
              ))}
          </li>
        ))}
      </ul>

      <button disabled={saveMutation.isPending} onClick={() => saveMutation.mutate()}>
        {saveMutation.isPending ? t('strategyGate.saving') : t('strategyGate.save')}
      </button>{' '}
      <button disabled={approveMutation.isPending} onClick={() => approveMutation.mutate()}>
        {approveMutation.isPending ? t('strategyGate.approving') : t('strategyGate.approve')}
      </button>
      {mutationError && <p className="error-text">{(mutationError as Error).message}</p>}
    </div>
  )
}
