import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import {
  getRun,
  getRunArtifacts,
  getRunEvents,
  getRunFacts,
  getRunStructure,
  runStreamUrl,
} from '../api/client'
import { TERMINAL_STATUSES } from '../api/types'
import type {
  DiffItem,
  Facts,
  HiringEvaluation,
  HRReview,
  JobProfile,
  MatchReport,
  RewriteStrategy,
  RunEvent,
  ValidationIssue,
  ValidationResult,
} from '../api/types'
import FinalGate from '../components/FinalGate'
import RunHeader from '../components/RunHeader'
import RunInfoPanel from '../components/RunInfoPanel'
import RunTabs from '../components/RunTabs'
import StepStrip from '../components/StepStrip'
import StrategyGate from '../components/StrategyGate'
import StrategySummaryPanel from '../components/StrategySummaryPanel'
import TroubleshootingPanel from '../components/TroubleshootingPanel'
import WorkflowRail from '../components/WorkflowRail'
import { useTranslation } from '../i18n/LanguageContext'
import { localize } from '../lib/format'
import { deriveMacroSteps, deriveWorkflowSteps } from '../lib/workflowSteps'

export default function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>()
  const queryClient = useQueryClient()
  const { t } = useTranslation()

  const runQuery = useQuery({
    queryKey: ['run', runId],
    queryFn: () => getRun(runId!),
    enabled: Boolean(runId),
  })
  const artifactsQuery = useQuery({
    queryKey: ['run-artifacts', runId],
    queryFn: () => getRunArtifacts(runId!),
    enabled: Boolean(runId),
  })
  const eventsQuery = useQuery({
    queryKey: ['run-events', runId],
    queryFn: () => getRunEvents(runId!),
    enabled: Boolean(runId),
  })
  const factsQuery = useQuery({
    queryKey: ['run-facts', runId],
    queryFn: () => getRunFacts(runId!),
    enabled: Boolean(runId),
  })
  const structureQuery = useQuery({
    queryKey: ['run-structure', runId],
    queryFn: () => getRunStructure(runId!),
    enabled: Boolean(runId),
  })

  useEffect(() => {
    if (!runId) return
    const source = new EventSource(runStreamUrl(runId))
    source.onmessage = (message) => {
      queryClient.invalidateQueries({ queryKey: ['run', runId] })
      queryClient.invalidateQueries({ queryKey: ['run-artifacts', runId] })
      queryClient.invalidateQueries({ queryKey: ['run-events', runId] })
      try {
        const payload = JSON.parse(message.data) as RunEvent
        if (payload.status && TERMINAL_STATUSES.includes(payload.status)) {
          source.close()
        }
      } catch {
        // malformed SSE payload; ignore and keep listening
      }
    }
    return () => source.close()
  }, [runId, queryClient])

  if (!runId) return null
  if (runQuery.isLoading) return <p>{t('runDetail.loading')}</p>
  if (runQuery.error) return <p className="error-text">{(runQuery.error as Error).message}</p>
  const run = runQuery.data
  if (!run) return null

  const artifacts = artifactsQuery.data
  const events = eventsQuery.data ?? []
  const facts: Facts = factsQuery.data ?? {}
  const pathLabels: Record<string, string> = {}
  for (const item of structureQuery.data ?? []) {
    pathLabels[item.path] = item.label
  }
  const isStrategyGate = run.status === 'WAITING_STRATEGY_APPROVAL'
  const isFinalGate = run.status === 'WAITING_FINAL_APPROVAL'
  const workflowSteps = deriveWorkflowSteps(run, events)
  const macroSteps = deriveMacroSteps(workflowSteps)

  return (
    <div>
      <RunHeader run={run} />
      <StepStrip steps={macroSteps} />

      <div className="run-detail-grid">
        <WorkflowRail steps={workflowSteps} />

        <div className="run-detail-main">
          {run.status === 'COMPLETED' && run.target_file && (
            <div className="card callout">
              <p>{t('runDetail.generated', { file: run.target_file })}</p>
            </div>
          )}

          {run.status === 'FAILED' && artifacts?.error && (
            <div className="card callout-danger">
              <h2>{t('runDetail.runFailed')}</h2>
              <p>
                <strong>{artifacts.error.type}</strong>
              </p>
              <p>{artifacts.error.message}</p>
              {artifacts.error.issues && artifacts.error.issues.length > 0 && (
                <ValidationIssuesList issues={artifacts.error.issues} />
              )}
            </div>
          )}

          {artifacts?.job_profile && <JobProfileCard profile={artifacts.job_profile} />}
          {artifacts?.match_report && <MatchReportCard report={artifacts.match_report} />}
          {artifacts?.hr_review && <HrReviewCard review={artifacts.hr_review} />}

          {isStrategyGate && artifacts?.rewrite_strategy && (
            <StrategyGate
              runId={run.run_id}
              strategy={artifacts.rewrite_strategy}
              pathLabels={pathLabels}
              facts={facts}
            />
          )}
          {!isStrategyGate && artifacts?.rewrite_strategy && (
            <StrategyCard strategy={artifacts.rewrite_strategy} pathLabels={pathLabels} facts={facts} />
          )}

          {artifacts?.final_diff && artifacts.final_diff.length > 0 && (
            <FinalDiffCard diff={artifacts.final_diff} facts={facts} />
          )}

          {isFinalGate && <FinalGate runId={run.run_id} />}

          <RunTabs run={run} events={events} />
        </div>

        <div className="run-detail-side">
          <RunInfoPanel run={run} />
          {isStrategyGate && artifacts?.rewrite_strategy && (
            <StrategySummaryPanel strategy={artifacts.rewrite_strategy} />
          )}
          {run.status === 'FAILED' && artifacts?.error?.issues && artifacts.error.issues.length > 0 && (
            <TroubleshootingPanel issues={artifacts.error.issues} />
          )}
          {artifacts?.validation && <ValidationCard validation={artifacts.validation} />}
          {artifacts?.hiring_review && <HiringReviewCard evaluation={artifacts.hiring_review} />}
        </div>
      </div>
    </div>
  )
}

function ValidationIssuesList({ issues }: { issues: ValidationIssue[] }) {
  return (
    <ul className="issue-list">
      {issues.map((issue, index) => (
        <li key={index}>
          <span className={`badge badge-${issue.severity === 'critical' ? 'danger' : issue.severity === 'high' ? 'warning' : 'neutral'}`}>
            {issue.severity}
          </span>{' '}
          <strong>{issue.code}</strong> · {issue.message}
          <div className="muted">{issue.path}</div>
        </li>
      ))}
    </ul>
  )
}

function JobProfileCard({ profile }: { profile: JobProfile }) {
  const { t } = useTranslation()
  return (
    <div className="card">
      <h2>{t('runDetail.jobProfile.title')}</h2>
      <p>
        {profile.target_company} · {profile.target_role} · {profile.seniority}
      </p>
      <ul className="issue-list">
        {profile.requirements.map((req) => (
          <li key={req.id}>
            <span className="badge badge-neutral">{req.category}</span> {req.statement}
            <span className="muted"> {t('runDetail.jobProfile.weight', { n: req.weight })}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function MatchReportCard({ report }: { report: MatchReport }) {
  const { t } = useTranslation()
  return (
    <div className="card">
      <h2>{t('runDetail.matchReport.title')}</h2>
      <p className="muted">{report.overall_summary}</p>
      <ul className="issue-list">
        {report.matches.map((match) => (
          <li key={match.requirement_id}>
            <span className="badge badge-neutral">{match.status}</span> {match.requirement_id}
            <span className="muted"> {t('runDetail.matchReport.confidence', { n: Math.round(match.confidence * 100) })}</span>
            <div className="muted">{match.rationale}</div>
          </li>
        ))}
      </ul>
    </div>
  )
}

function HrReviewCard({ review }: { review: HRReview }) {
  const { t } = useTranslation()
  return (
    <div className="card">
      <h2>{t('runDetail.hrReview.title')}</h2>
      <p>
        <strong>{t('runDetail.hrReview.strengths')}</strong>
        {review.strengths.join('；') || '-'}
      </p>
      <p>
        <strong>{t('runDetail.hrReview.weaknesses')}</strong>
        {review.weaknesses.join('；') || '-'}
      </p>
      <p>
        <strong>{t('runDetail.hrReview.missingKeywords')}</strong>
        {review.missing_keywords.join('、') || '-'}
      </p>
      <p>
        <strong>{t('runDetail.hrReview.priorities')}</strong>
        {review.rewrite_priorities.join('；') || '-'}
      </p>
    </div>
  )
}

function StrategyCard({
  strategy,
  pathLabels,
  facts,
}: {
  strategy: RewriteStrategy
  pathLabels: Record<string, string>
  facts: Facts
}) {
  const { t } = useTranslation()
  return (
    <div className="card">
      <h2>{t('runDetail.strategyCard.title')}</h2>
      <p>{strategy.positioning}</p>
      <p>
        {strategy.safe_keywords.map((word) => (
          <span key={word} className="chip">
            {word}
          </span>
        ))}
        {strategy.forbidden_keywords.map((word) => (
          <span key={word} className="chip chip-danger">
            {word}
          </span>
        ))}
      </p>
      <ul className="issue-list">
        {strategy.actions.map((action, index) => (
          <li key={index}>
            <span className="badge badge-neutral">{action.action}</span> {t('runDetail.strategyCard.priority')} {action.priority}
            <div className="muted">{pathLabels[action.target_path] ?? action.target_path}</div>
            <div>{action.instruction}</div>
            {action.supported_by
              .map((factId) => facts[factId])
              .filter(Boolean)
              .map((fact) => (
                <div className="muted" key={fact.id}>
                  {t('runDetail.strategyCard.evidence')}{fact.statement.zh || fact.statement.en}
                </div>
              ))}
          </li>
        ))}
      </ul>
    </div>
  )
}

function ValidationCard({ validation }: { validation: ValidationResult }) {
  const { t } = useTranslation()
  return (
    <div className="card">
      <h2>{t('runDetail.validation.title')}</h2>
      <p>
        <span className={`badge badge-${validation.passed ? 'success' : 'danger'}`}>
          {validation.passed ? t('runDetail.validation.passed') : t('runDetail.validation.failed')}
        </span>
      </p>
      {validation.issues.length > 0 && <ValidationIssuesList issues={validation.issues} />}
    </div>
  )
}

function HiringReviewCard({ evaluation }: { evaluation: HiringEvaluation }) {
  const { t, dict } = useTranslation()
  return (
    <div className="card">
      <h2>{t('runDetail.hiringReview.title')}</h2>
      <p className="score-line">
        <span className="score-value">{evaluation.total_score} / 100</span>
        <span className={`badge badge-${evaluation.decision === 'PASS' ? 'success' : 'warning'}`}>
          {evaluation.decision}
        </span>
      </p>
      <p>
        {Object.entries(evaluation.scores).map(([key, value]) => (
          <span key={key} className="chip">
            {dict.runDetail.hiringReview.scoreLabels[key as keyof typeof dict.runDetail.hiringReview.scoreLabels] ?? key} {value}
          </span>
        ))}
      </p>
      {evaluation.concerns.length > 0 && (
        <>
          <strong>{t('runDetail.hiringReview.concerns')}</strong>
          <ul className="issue-list">
            {evaluation.concerns.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </>
      )}
      {evaluation.feedback.length > 0 && (
        <>
          <strong>{t('runDetail.hiringReview.suggestions')}</strong>
          <ul className="issue-list">
            {evaluation.feedback.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}

function FinalDiffCard({ diff, facts }: { diff: DiffItem[]; facts: Facts }) {
  const { t } = useTranslation()
  return (
    <div className="card">
      <h2>{t('runDetail.finalDiff.title')}</h2>
      {diff.map((item, index) => (
        <div className="diff-item" key={index}>
          <div className="muted">
            {item.path} · {item.op}
          </div>
          <div className="diff-grid">
            <div className="diff-before">{localize(item.original) || t('runDetail.finalDiff.none')}</div>
            <div className="diff-after">{localize(item.revised) || t('runDetail.finalDiff.hidden')}</div>
          </div>
          <p className="muted">{item.reason}</p>
          {item.supported_by
            .map((factId) => facts[factId])
            .filter(Boolean)
            .map((fact) => (
              <div className="muted" key={fact.id}>
                {t('runDetail.finalDiff.evidence')}{fact.statement.zh || fact.statement.en}
              </div>
            ))}
        </div>
      ))}
    </div>
  )
}
