import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Lock, Search, Sparkles, User } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createRun } from '../api/client'
import { useTranslation } from '../i18n/LanguageContext'

const STEP_ICONS = [Search, Sparkles, User, CheckCircle2]

export default function NewRunPage() {
  const { t, dict } = useTranslation()
  const [jdLabel, setJdLabel] = useState('')
  const [company, setCompany] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: () =>
      createRun({
        jd_label: jdLabel,
        company: company.trim() ? company.trim() : undefined,
        job_description: jobDescription,
      }),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      navigate(`/runs/${run.run_id}`)
    },
  })

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{t('newRun.title')}</h1>
          <p>{t('newRun.subtitle')}</p>
        </div>
      </div>
      <div className="two-col">
        <div className="card">
          <form
            onSubmit={(event) => {
              event.preventDefault()
              mutation.mutate()
            }}
          >
            <label>
              {t('newRun.jdLabel')}
              <input
                required
                maxLength={120}
                value={jdLabel}
                onChange={(event) => setJdLabel(event.target.value)}
                placeholder={t('newRun.jdLabelPlaceholder')}
              />
            </label>
            <label>
              {t('newRun.company')}
              <input
                maxLength={120}
                value={company}
                onChange={(event) => setCompany(event.target.value)}
                placeholder={t('newRun.companyPlaceholder')}
              />
            </label>
            <label>
              {t('newRun.jd')}
              <textarea
                required
                minLength={20}
                rows={12}
                value={jobDescription}
                onChange={(event) => setJobDescription(event.target.value)}
                placeholder={t('newRun.jdPlaceholder')}
              />
            </label>
            <button type="submit" disabled={mutation.isPending} style={{ marginTop: 16 }}>
              {mutation.isPending ? t('newRun.submitting') : t('newRun.submit')}
            </button>
            {mutation.isError && <p className="error-text">{(mutation.error as Error).message}</p>}
          </form>
        </div>

        <div className="card">
          <h2>{t('newRun.howItWorks')}</h2>
          {dict.newRun.steps.map((step, index) => {
            const Icon = STEP_ICONS[index]
            return (
              <div className="side-card-step" key={step.title}>
                <div className="side-card-step-icon">
                  <Icon size={14} />
                </div>
                <div>
                  <div className="side-card-step-title">{step.title}</div>
                  <div className="side-card-step-desc">{step.desc}</div>
                </div>
              </div>
            )
          })}
          <div className="privacy-note">
            <Lock size={16} />
            <span>{t('newRun.privacyNote')}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
