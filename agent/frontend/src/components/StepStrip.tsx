import { Check } from 'lucide-react'
import { useTranslation } from '../i18n/LanguageContext'
import type { StepStatus } from '../lib/workflowSteps'

const MACRO_KEYS = ['analyze_jd', 'match_resume', 'hr_review', 'build_strategy', 'gate1', 'compile', 'final'] as const

export default function StepStrip({ steps }: { steps: StepStatus[] }) {
  const { dict } = useTranslation()
  return (
    <div className="step-strip">
      {steps.map((status, index) => (
        <div className={`step-strip-item step-strip-${status}`} key={MACRO_KEYS[index]}>
          <div className="step-strip-circle">
            {status === 'done' ? <Check size={14} /> : index + 1}
          </div>
          <span className="step-strip-label">{dict.workflow.macro[MACRO_KEYS[index]]}</span>
        </div>
      ))}
    </div>
  )
}
