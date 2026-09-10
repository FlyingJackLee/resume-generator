import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { approveFinal, previewUrl, rejectFinal, restoreOriginal } from '../api/client'
import { useTranslation } from '../i18n/LanguageContext'
import PatchBuilder from './PatchBuilder'

export default function FinalGate({ runId }: { runId: string }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [previewLang, setPreviewLang] = useState<'zh' | 'en'>('zh')

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
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 4, padding: 8 }}>
          <button className={previewLang === 'zh' ? 'active' : ''} onClick={() => setPreviewLang('zh')}>
            中文
          </button>
          <button className={previewLang === 'en' ? 'active' : ''} onClick={() => setPreviewLang('en')}>
            English
          </button>
        </div>
        <iframe
          className="preview-frame"
          style={{ border: 0, borderRadius: 0, height: '70vh' }}
          title={t('finalGate.previewTitle')}
          src={previewUrl(runId, previewLang)}
        />
      </div>
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
