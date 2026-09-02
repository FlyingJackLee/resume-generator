import { useMutation, useQueryClient } from '@tanstack/react-query'
import { approveFinal, rejectFinal, restoreOriginal } from '../api/client'
import { useTranslation } from '../i18n/LanguageContext'
import PatchBuilder from './PatchBuilder'

export default function FinalGate({ runId }: { runId: string }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const invalidateRun = () => queryClient.invalidateQueries({ queryKey: ['run', runId] })
  const invalidateAll = () => {
    invalidateRun()
    queryClient.invalidateQueries({ queryKey: ['run-artifacts', runId] })
  }

  const approveMutation = useMutation({ mutationFn: () => approveFinal(runId), onSuccess: invalidateRun })
  const rejectMutation = useMutation({ mutationFn: () => rejectFinal(runId), onSuccess: invalidateRun })
  const restoreMutation = useMutation({ mutationFn: () => restoreOriginal(runId), onSuccess: invalidateAll })

  const error = approveMutation.error ?? rejectMutation.error ?? restoreMutation.error
  const pending = approveMutation.isPending || rejectMutation.isPending || restoreMutation.isPending

  return (
    <>
      <div className="card">
        <button disabled={pending} onClick={() => approveMutation.mutate()}>
          {t('finalGate.approve')}
        </button>{' '}
        <button disabled={pending} onClick={() => restoreMutation.mutate()}>
          {t('finalGate.restore')}
        </button>{' '}
        <button disabled={pending} onClick={() => rejectMutation.mutate()}>
          {t('finalGate.reject')}
        </button>
        {error && <p className="error-text">{(error as Error).message}</p>}
      </div>
      <details>
        <summary>{t('finalGate.advanced')}</summary>
        <PatchBuilder runId={runId} />
      </details>
    </>
  )
}
