export type RunStatus =
  | 'INIT'
  | 'ANALYZING'
  | 'MATCHING'
  | 'HR_REVIEWING'
  | 'STRATEGIZING'
  | 'WAITING_STRATEGY_APPROVAL'
  | 'EDITING'
  | 'APPLYING_PATCH'
  | 'VALIDATING'
  | 'REVIEWING'
  | 'REVISING'
  | 'HIRING_REVIEWED'
  | 'FINALIZING'
  | 'WAITING_FINAL_APPROVAL'
  | 'COMPLETED'
  | 'FAILED'
  | 'INTERRUPTED'
  | 'REJECTED'

export const TERMINAL_STATUSES: RunStatus[] = ['COMPLETED', 'FAILED', 'INTERRUPTED', 'REJECTED']

export const ACTIVE_STATUSES: RunStatus[] = [
  'ANALYZING', 'MATCHING', 'HR_REVIEWING', 'STRATEGIZING',
  'EDITING', 'APPLYING_PATCH', 'VALIDATING', 'REVIEWING', 'REVISING',
  'HIRING_REVIEWED', 'FINALIZING',
]

export interface RunMetadata {
  run_id: string
  jd_label: string
  company: string | null
  notes: string
  output_name: string
  status: RunStatus
  stage?: string
  created_at: string
  updated_at?: string
  progress_current?: number
  progress_total?: number
  iteration?: number
  hiring_score?: number | null
  target_file?: string
  last_completed_node?: string
  error?: string | null
  langsmith_trace_url?: string | null
}

export interface PaginatedRuns {
  items: RunMetadata[]
  total: number
  page: number
  page_size: number
}

// One line of events.jsonl: the fixed fields below, plus whatever else was
// passed to update_metadata() for that transition (loosely typed).
export interface RunEvent {
  timestamp: string
  run_id: string
  status?: RunStatus
  stage?: string
  [key: string]: unknown
}

export interface StructureItem {
  path: string
  kind: string
  label: string
}

export interface JobRequirement {
  id: string
  category: 'must_have' | 'preferred' | 'responsibility'
  statement: string
  weight: number
}

export interface JobProfile {
  target_company: string
  target_role: string
  seniority: string
  requirements: JobRequirement[]
  keywords: string[]
}

export interface RequirementMatch {
  requirement_id: string
  status: 'full' | 'partial' | 'missing'
  fact_ids: string[]
  confidence: number
  rationale: string
}

export interface MatchReport {
  matches: RequirementMatch[]
  overall_summary: string
}

export interface HRReview {
  strengths: string[]
  weaknesses: string[]
  missing_keywords: string[]
  rewrite_priorities: string[]
}

export interface RewriteAction {
  action: 'promote' | 'rewrite' | 'reorder' | 'deprioritize' | 'preserve'
  target_path: string
  priority: number
  instruction: string
  supported_by: string[]
}

export interface RewriteStrategy {
  positioning: string
  safe_keywords: string[]
  forbidden_keywords: string[]
  actions: RewriteAction[]
}

export interface ValidationIssue {
  code: string
  severity: 'critical' | 'high' | 'low'
  path: string
  message: string
}

export interface ValidationResult {
  passed: boolean
  issues: ValidationIssue[]
}

export interface HiringScores {
  jd_core_match: number
  relevant_experience: number
  technical_depth: number
  business_impact: number
  ats_keywords: number
  clarity: number
  credibility: number
}

export interface HiringEvaluation {
  scores: HiringScores
  decision: 'PASS' | 'REVISE'
  strengths: string[]
  concerns: string[]
  feedback: string[]
  total_score: number
}

export type BilingualText = { zh: string; en: string; id?: string; supported_by?: string[] } | null

export interface DiffItem {
  op: 'replace' | 'reorder' | 'hide' | 'restore'
  path: string
  original: BilingualText | string[] | null
  revised: BilingualText | string[] | null
  reason: string
  supported_by: string[]
}

export interface RunError {
  type: string
  message: string
  issues?: ValidationIssue[]
  traceback?: string
}

export interface RunArtifacts {
  job_profile: JobProfile | null
  match_report: MatchReport | null
  hr_review: HRReview | null
  rewrite_strategy: RewriteStrategy | null
  validation: ValidationResult | null
  hiring_review: HiringEvaluation | null
  final_diff: DiffItem[] | null
  error: RunError | null
}

export interface Fact {
  id: string
  type: string
  statement: { zh: string; en: string }
}

export type Facts = Record<string, Fact>

export interface PatchOperation {
  op: 'replace' | 'reorder' | 'hide' | 'restore'
  path: string
  supported_by: string[]
  reason: string
  value: { zh: string; en: string } | string[] | null
}
