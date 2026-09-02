import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { updateNotes } from '../api/client'
import { useTranslation } from '../i18n/LanguageContext'
import type { RunEvent, RunMetadata } from '../api/types'
import { formatDate } from '../lib/format'

function ActivityLogTab({ events, uiLang }: { events: RunEvent[]; uiLang: 'zh' | 'en' }) {
  const ordered = [...events].reverse()
  return (
    <ul className="issue-list">
      {ordered.map((event, index) => (
        <li key={index}>
          <span className="muted">{formatDate(event.timestamp, uiLang)}</span>{' '}
          {event.status && <span className="badge badge-neutral">{event.status}</span>}{' '}
          {event.stage as string | undefined}
        </li>
      ))}
    </ul>
  )
}

function NotesTab({ run }: { run: RunMetadata }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [notes, setNotes] = useState(run.notes)

  useEffect(() => {
    setNotes(run.notes)
  }, [run.run_id])

  const saveMutation = useMutation({
    mutationFn: () => updateNotes(run.run_id, notes),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['run', run.run_id] }),
  })

  return (
    <div>
      <textarea
        rows={6}
        value={notes}
        placeholder={t('runDetail.notes.placeholder')}
        onChange={(event) => setNotes(event.target.value)}
      />
      <button disabled={saveMutation.isPending} onClick={() => saveMutation.mutate()} style={{ marginTop: 8 }}>
        {saveMutation.isPending ? t('runDetail.notes.saving') : t('runDetail.notes.save')}
      </button>
      {saveMutation.isSuccess && <span className="muted" style={{ marginLeft: 8 }}>{t('runDetail.notes.saved')}</span>}
    </div>
  )
}

export default function RunTabs({ run, events }: { run: RunMetadata; events: RunEvent[] }) {
  const { t, uiLang } = useTranslation()
  const [tab, setTab] = useState<'activity' | 'notes'>('activity')

  return (
    <div className="card">
      <div className="tab-buttons">
        <button
          className={tab === 'activity' ? 'tab-button active' : 'tab-button'}
          onClick={() => setTab('activity')}
        >
          {t('runDetail.tabs.activityLog')}
        </button>
        <button
          className={tab === 'notes' ? 'tab-button active' : 'tab-button'}
          onClick={() => setTab('notes')}
        >
          {t('runDetail.tabs.notes')}
        </button>
      </div>
      {tab === 'activity' ? <ActivityLogTab events={events} uiLang={uiLang} /> : <NotesTab run={run} />}
    </div>
  )
}
