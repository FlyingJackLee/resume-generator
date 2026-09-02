import { Check, Circle, Loader2 } from 'lucide-react'
import { useTranslation } from '../i18n/LanguageContext'
import type { WorkflowStep } from '../lib/workflowSteps'

function StepIcon({ status }: { status: WorkflowStep['status'] }) {
  if (status === 'done') return <Check size={14} />
  if (status === 'active') return <Loader2 size={14} className="spin" />
  return <Circle size={10} />
}

export default function WorkflowRail({ steps }: { steps: WorkflowStep[] }) {
  const { dict } = useTranslation()
  return (
    <div className="card workflow-rail">
      <h3 style={{ marginTop: 0 }}>{dict.workflow.title}</h3>
      <ul className="workflow-rail-list">
        {steps.map((step) => (
          <li key={step.key} className={`workflow-rail-item workflow-rail-${step.status}`}>
            <span className="workflow-rail-icon">
              <StepIcon status={step.status} />
            </span>
            <span>{dict.workflow.steps[step.key as keyof typeof dict.workflow.steps]}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
