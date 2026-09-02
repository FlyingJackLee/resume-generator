import { useQuery } from '@tanstack/react-query'
import { Ban, CheckCircle2, Clock, PlayCircle, Plus, XCircle } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { listRuns } from '../api/client'
import type { RunStatus } from '../api/types'
import StatusBadge from '../components/StatusBadge'
import { useTranslation } from '../i18n/LanguageContext'
import { formatDate } from '../lib/format'

const PAGE_SIZE_OPTIONS = [5, 10, 20, 50]

const STATUS_DOT: Record<string, { icon: typeof CheckCircle2; color: string }> = {
  COMPLETED: { icon: CheckCircle2, color: 'var(--status-success-fg)' },
  FAILED: { icon: XCircle, color: 'var(--status-danger-fg)' },
  INTERRUPTED: { icon: XCircle, color: 'var(--status-danger-fg)' },
  REJECTED: { icon: Ban, color: 'var(--status-purple-fg)' },
  WAITING_STRATEGY_APPROVAL: { icon: Clock, color: 'var(--status-warning-fg)' },
  WAITING_FINAL_APPROVAL: { icon: Clock, color: 'var(--status-warning-fg)' },
}

function StatusDot({ status }: { status: RunStatus | string }) {
  const entry = STATUS_DOT[status] ?? { icon: PlayCircle, color: 'var(--status-info-fg)' }
  const Icon = entry.icon
  return (
    <div className="status-dot" style={{ background: entry.color }}>
      <Icon size={16} />
    </div>
  )
}

export default function RunsListPage() {
  const { t, uiLang } = useTranslation()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const { data, isLoading, error } = useQuery({
    queryKey: ['runs', page, pageSize],
    queryFn: () => listRuns(page, pageSize),
  })

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{t('runsList.title')}</h1>
          <p>{t('runsList.subtitle')}</p>
        </div>
        <Link className="button" to="/runs/new">
          <Plus size={16} />
          {t('runsList.newRun')}
        </Link>
      </div>

      {isLoading && <p className="muted">{t('runsList.loading')}</p>}
      {error && <p className="error-text">{(error as Error).message}</p>}

      {data && data.items.length === 0 && (
        <div className="card">
          <p className="muted">{t('runsList.empty')}</p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <div className="card" style={{ padding: 0 }}>
          <table className="table">
            <thead>
              <tr>
                <th style={{ paddingLeft: 20 }}>{t('runsList.colJdCompany')}</th>
                <th>{t('runsList.colStatus')}</th>
                <th>{t('runsList.colScore')}</th>
                <th>{t('runsList.colCreated')}</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((run) => (
                <tr key={run.run_id}>
                  <td style={{ paddingLeft: 20 }}>
                    <div className="row-lead">
                      <StatusDot status={run.status} />
                      <div className="avatar-square">JD</div>
                      <div>
                        <Link to={`/runs/${run.run_id}`} style={{ fontWeight: 600, color: 'inherit', textDecoration: 'none' }}>
                          {run.jd_label}
                        </Link>
                        <div className="row-company">{run.company ?? t('runsList.uncategorized')}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <StatusBadge status={run.status} />
                    {run.stage && <div className="muted" style={{ marginTop: 4 }}>{run.stage}</div>}
                  </td>
                  <td>
                    {run.hiring_score != null ? (
                      <div className="score-cell">
                        <span className="score-value">
                          {run.hiring_score}
                          <span className="of100"> /100</span>
                        </span>
                        <div className="mini-progress">
                          <div className="mini-progress-fill" style={{ width: `${run.hiring_score}%` }} />
                        </div>
                      </div>
                    ) : (
                      <span className="muted">-</span>
                    )}
                  </td>
                  <td className="muted">{formatDate(run.created_at, uiLang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data && data.total > 0 && (
        <div className="pagination">
          <span className="muted">
            {t('runsList.showing', {
              from: (page - 1) * data.page_size + 1,
              to: Math.min(page * data.page_size, data.total),
              total: data.total,
            })}
          </span>
          <div className="pagination-pages">
            <button className="page-button secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              ‹
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .slice(0, 5)
              .map((p) => (
                <button
                  key={p}
                  className={`page-button ${p === page ? 'active' : 'secondary'}`}
                  onClick={() => setPage(p)}
                >
                  {p}
                </button>
              ))}
            <button
              className="page-button secondary"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              ›
            </button>
            <select
              className="page-size"
              value={pageSize}
              onChange={(event) => {
                setPageSize(Number(event.target.value))
                setPage(1)
              }}
            >
              {PAGE_SIZE_OPTIONS.map((size) => (
                <option key={size} value={size}>
                  {t('runsList.pageSize', { size })}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  )
}
