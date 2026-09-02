import type { RunEvent, RunMetadata } from '../api/types'

export type StepStatus = 'done' | 'active' | 'pending'

export interface WorkflowStep {
  key: string
  status: StepStatus
}

const COMPILE_NODES = ['edit_resume', 'apply_patch', 'validate_facts', 'hiring_manager']

const ACTIVE_ANALYSIS: Record<string, string> = {
  ANALYZING: 'analyze_jd',
  MATCHING: 'match_resume',
  HR_REVIEWING: 'hr_review',
  STRATEGIZING: 'build_strategy',
}

const ACTIVE_COMPILE: Record<string, string> = {
  EDITING: 'edit_resume',
  APPLYING_PATCH: 'apply_patch',
  VALIDATING: 'validate_facts',
  REVIEWING: 'hiring_manager',
  REVISING: 'edit_resume',
  HIRING_REVIEWED: 'hiring_manager',
  FINALIZING: 'hiring_manager',
}

const TERMINAL_DONE_WITH_RUN = new Set(['COMPLETED', 'REJECTED'])

/**
 * The 11 fine-grained nodes shown in the left Workflow rail. Derived purely
 * from `run.status` + the `last_completed_node` values already recorded in
 * events.jsonl (Milestone 1) — no new backend data needed. This is a
 * best-effort approximation (no per-step duration yet), not an exact replay
 * of the LangGraph execution.
 */
export function deriveWorkflowSteps(run: RunMetadata, events: RunEvent[]): WorkflowStep[] {
  const completed = new Set(
    events.map((event) => event.last_completed_node).filter((v): v is string => typeof v === 'string'),
  )
  const status = run.status

  function nodeStatus(node: string, activeMap: Record<string, string>): StepStatus {
    if (completed.has(node)) return 'done'
    if (activeMap[status] === node) return 'active'
    return 'pending'
  }

  const gate1Status: StepStatus = (() => {
    if (status === 'WAITING_STRATEGY_APPROVAL') return 'active'
    if (completed.has('build_strategy') && !(status in ACTIVE_ANALYSIS)) return 'done'
    return 'pending'
  })()

  const gate2Status: StepStatus = (() => {
    if (status === 'WAITING_FINAL_APPROVAL') return 'active'
    if (TERMINAL_DONE_WITH_RUN.has(status)) return 'done'
    return 'pending'
  })()

  const finalStatus: StepStatus = TERMINAL_DONE_WITH_RUN.has(status) ? 'done' : 'pending'

  return [
    { key: 'analyze_jd', status: nodeStatus('analyze_jd', ACTIVE_ANALYSIS) },
    { key: 'match_resume', status: nodeStatus('match_resume', ACTIVE_ANALYSIS) },
    { key: 'hr_review', status: nodeStatus('hr_review', ACTIVE_ANALYSIS) },
    { key: 'build_strategy', status: nodeStatus('build_strategy', ACTIVE_ANALYSIS) },
    { key: 'gate1', status: gate1Status },
    { key: 'edit_resume', status: nodeStatus('edit_resume', ACTIVE_COMPILE) },
    { key: 'apply_patch', status: nodeStatus('apply_patch', ACTIVE_COMPILE) },
    { key: 'validate_facts', status: nodeStatus('validate_facts', ACTIVE_COMPILE) },
    { key: 'hiring_manager', status: nodeStatus('hiring_manager', ACTIVE_COMPILE) },
    { key: 'gate2', status: gate2Status },
    { key: 'final', status: finalStatus },
  ]
}

/** Groups the 11 fine-grained steps into the 7 macro steps shown in the top strip. */
export function deriveMacroSteps(steps: WorkflowStep[]): StepStatus[] {
  const byKey = Object.fromEntries(steps.map((s) => [s.key, s.status]))
  const groupStatus = (keys: string[]): StepStatus => {
    const statuses = keys.map((k) => byKey[k])
    if (statuses.every((s) => s === 'done')) return 'done'
    if (statuses.some((s) => s === 'active' || s === 'done')) return 'active'
    return 'pending'
  }
  return [
    byKey.analyze_jd,
    byKey.match_resume,
    byKey.hr_review,
    byKey.build_strategy,
    byKey.gate1,
    groupStatus(COMPILE_NODES),
    groupStatus(['gate2', 'final']),
  ]
}
