import type { RunEvent, RunMetadata } from '../api/types'

export type StepStatus = 'done' | 'active' | 'pending' | 'error'

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
 * Every fixed `stage=` string literal the backend writes (see
 * `workflow_service.py`), mapped to the workflow node it describes. `stage`
 * always names the node that is currently running/about to run — never the
 * one that just finished — so this table doubles as "what was in flight when
 * a FAILED status was reached" (see deriveFailedNode below).
 */
const STAGE_TO_NODE: Record<string, string> = {
  'JD Analyzer': 'analyze_jd',
  'Resume Matcher': 'match_resume',
  'Resume Matcher（断点续跑）': 'match_resume',
  'HR Reviewer': 'hr_review',
  'HR Reviewer（断点续跑）': 'hr_review',
  'Rewrite Strategy': 'build_strategy',
  'Rewrite Strategy（断点续跑）': 'build_strategy',
  'Human Gate ①': 'gate1',
  'Human Gate ①：等待策略确认': 'gate1',
  'Resume Editor': 'edit_resume',
  'Resume Editor（重试编译）': 'edit_resume',
  'Resume Editor 返工': 'edit_resume',
  'Patch Engine': 'apply_patch',
  'Fact Validator': 'validate_facts',
  'Fact Validator（从候选版本继续）': 'validate_facts',
  '事实校验失败': 'validate_facts',
  'Hiring Manager': 'hiring_manager',
  'Human Gate ②': 'gate2',
  'Human Gate ②：等待最终确认': 'gate2',
  '已批准导出': 'final',
  '已拒绝': 'final',
}

/**
 * Best-effort "which node was in flight when this run died" — scans events
 * newest-first for the last one whose `stage` resolves to a node. The
 * terminal FAILED event itself has stage="运行失败" (not in the table), so
 * this naturally falls through to the node that was actually running.
 */
export function deriveFailedNode(run: RunMetadata, events: RunEvent[]): string | null {
  if (run.status !== 'FAILED') return null
  for (let i = events.length - 1; i >= 0; i--) {
    const stage = events[i].stage
    if (typeof stage === 'string' && STAGE_TO_NODE[stage]) {
      return STAGE_TO_NODE[stage]
    }
  }
  return null
}

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
  const failedNode = deriveFailedNode(run, events)

  function nodeStatus(node: string, activeMap: Record<string, string>): StepStatus {
    if (node === failedNode) return 'error'
    if (completed.has(node)) return 'done'
    if (activeMap[status] === node) return 'active'
    return 'pending'
  }

  const gate1Status: StepStatus = (() => {
    if (failedNode === 'gate1') return 'error'
    if (status === 'WAITING_STRATEGY_APPROVAL') return 'active'
    if (completed.has('build_strategy') && !(status in ACTIVE_ANALYSIS)) return 'done'
    return 'pending'
  })()

  const gate2Status: StepStatus = (() => {
    if (failedNode === 'gate2') return 'error'
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
    if (statuses.some((s) => s === 'error')) return 'error'
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

/**
 * Which node's content the main panel should show by default: the node that
 * failed, else whichever node is currently active, else the relevant gate,
 * else `final` for a terminal run, else the first node as an ultimate
 * fallback (e.g. a brand-new run that hasn't started yet).
 */
export function deriveDefaultSelectedStep(run: RunMetadata, events: RunEvent[]): string {
  const failedNode = deriveFailedNode(run, events)
  if (failedNode) return failedNode
  const status = run.status
  if (ACTIVE_ANALYSIS[status]) return ACTIVE_ANALYSIS[status]
  if (ACTIVE_COMPILE[status]) return ACTIVE_COMPILE[status]
  if (status === 'WAITING_STRATEGY_APPROVAL') return 'gate1'
  if (status === 'WAITING_FINAL_APPROVAL') return 'gate2'
  if (TERMINAL_DONE_WITH_RUN.has(status) || status === 'FAILED' || status === 'INTERRUPTED') return 'final'
  return 'analyze_jd'
}
