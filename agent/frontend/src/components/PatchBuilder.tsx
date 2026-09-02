import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { getRunFacts, getRunStructure, manualEdit } from '../api/client'
import { useTranslation } from '../i18n/LanguageContext'
import type { Facts, PatchOperation, StructureItem } from '../api/types'

type OpType = PatchOperation['op']
type Kind = 'text' | 'text_hideable' | 'hideable' | 'collection' | 'removed'

const OPS_BY_KIND: Record<string, OpType[]> = {
  text: ['replace', 'restore'],
  text_hideable: ['replace', 'hide', 'restore'],
  hideable: ['hide', 'restore'],
  collection: ['reorder'],
}

const KIND_ORDER: Kind[] = ['text', 'text_hideable', 'hideable', 'collection', 'removed']

function directChildren(structure: StructureItem[], collectionPath: string): StructureItem[] {
  const prefix = `${collectionPath}/`
  const depth = collectionPath.split('/').length + 1
  return structure.filter(
    (item) => item.path.startsWith(prefix) && item.path.split('/').length === depth,
  )
}

function ReorderList({
  path,
  structure,
  order,
  onChange,
}: {
  path: string
  structure: StructureItem[]
  order: string[]
  onChange: (next: string[]) => void
}) {
  const { t } = useTranslation()
  const labelFor = (id: string) =>
    structure.find((item) => item.path === `${path}/${id}`)?.label ?? id

  function move(index: number, delta: number) {
    const target = index + delta
    if (target < 0 || target >= order.length) return
    const next = [...order]
    ;[next[index], next[target]] = [next[target], next[index]]
    onChange(next)
  }

  if (order.length === 0) {
    return <p className="muted">{t('patchBuilder.reorderUnsupported')}</p>
  }

  return (
    <ul className="issue-list">
      {order.map((id, index) => (
        <li key={id}>
          {labelFor(id)}{' '}
          <button type="button" disabled={index === 0} onClick={() => move(index, -1)}>
            ↑
          </button>{' '}
          <button type="button" disabled={index === order.length - 1} onClick={() => move(index, 1)}>
            ↓
          </button>
        </li>
      ))}
    </ul>
  )
}

export default function PatchBuilder({ runId }: { runId: string }) {
  const { t, dict } = useTranslation()
  const queryClient = useQueryClient()

  const candidateQuery = useQuery({
    queryKey: ['run-structure-candidate', runId],
    queryFn: () => getRunStructure(runId, 'candidate'),
  })
  const inputQuery = useQuery({
    queryKey: ['run-structure-input', runId],
    queryFn: () => getRunStructure(runId, 'input'),
  })
  const factsQuery = useQuery({
    queryKey: ['run-facts', runId],
    queryFn: () => getRunFacts(runId),
  })
  const candidateItems = candidateQuery.data ?? []
  const facts: Facts = factsQuery.data ?? {}

  // Anything hidden earlier (by the AI editor or a previous manual patch) drops
  // out of the candidate structure entirely, so it can never be re-selected for
  // "restore" from the candidate list alone. Surface those paths (present in the
  // original input structure but missing from the candidate one) as a separate,
  // restore-only group.
  const candidatePaths = new Set(candidateItems.map((item) => item.path))
  const removedItems = (inputQuery.data ?? [])
    .filter((item) => !candidatePaths.has(item.path))
    .map((item) => ({ ...item, kind: 'removed' }))
  const structure = [...candidateItems, ...removedItems]

  const [pendingOps, setPendingOps] = useState<PatchOperation[]>([])
  const [selectedPath, setSelectedPath] = useState('')
  const [selectedOp, setSelectedOp] = useState<OpType | ''>('')
  const [zh, setZh] = useState('')
  const [en, setEn] = useState('')
  const [reason, setReason] = useState('')
  const [selectedFacts, setSelectedFacts] = useState<string[]>([])
  const [reorderIds, setReorderIds] = useState<string[]>([])
  const [formError, setFormError] = useState<string | null>(null)

  const selectedKind = structure.find((item) => item.path === selectedPath)?.kind
  const availableOps = selectedKind === 'removed' ? ['restore'] : (OPS_BY_KIND[selectedKind ?? ''] ?? [])

  function resetForm() {
    setSelectedPath('')
    setSelectedOp('')
    setZh('')
    setEn('')
    setReason('')
    setSelectedFacts([])
    setReorderIds([])
    setFormError(null)
  }

  function handlePathChange(path: string) {
    setSelectedPath(path)
    setSelectedOp('')
    setReorderIds([])
  }

  function handleOpChange(op: OpType) {
    setSelectedOp(op)
    if (op === 'reorder') {
      setReorderIds(directChildren(candidateItems, selectedPath).map((item) => item.path.split('/').pop()!))
    }
  }

  function addOperation() {
    if (!selectedPath || !selectedOp) return
    if (selectedOp === 'replace') {
      if (!zh.trim() || !en.trim() || !reason.trim() || selectedFacts.length === 0) {
        setFormError(t('patchBuilder.validationError'))
        return
      }
      setPendingOps((prev) => [
        ...prev,
        { op: 'replace', path: selectedPath, supported_by: selectedFacts, reason, value: { zh, en } },
      ])
    } else if (selectedOp === 'reorder') {
      if (reorderIds.length === 0) {
        setFormError(t('patchBuilder.reorderUnsupported'))
        return
      }
      setPendingOps((prev) => [
        ...prev,
        { op: 'reorder', path: selectedPath, supported_by: [], reason: '', value: reorderIds },
      ])
    } else {
      setPendingOps((prev) => [
        ...prev,
        { op: selectedOp, path: selectedPath, supported_by: [], reason: '', value: null },
      ])
    }
    resetForm()
  }

  const submitMutation = useMutation({
    mutationFn: () => manualEdit(runId, pendingOps),
    onSuccess: () => {
      setPendingOps([])
      queryClient.invalidateQueries({ queryKey: ['run', runId] })
      queryClient.invalidateQueries({ queryKey: ['run-artifacts', runId] })
      queryClient.invalidateQueries({ queryKey: ['run-structure-candidate', runId] })
    },
  })

  return (
    <div className="card">
      <h3>{t('patchBuilder.advancedTitle')}</h3>
      <p className="muted">{t('patchBuilder.hint')}</p>

      <label>
        {t('patchBuilder.targetField')}
        <select value={selectedPath} onChange={(event) => handlePathChange(event.target.value)}>
          <option value="">{t('patchBuilder.choose')}</option>
          {KIND_ORDER.map((kind) => {
            const options = structure.filter((item) => item.kind === kind)
            if (options.length === 0) return null
            return (
              <optgroup key={kind} label={dict.patchBuilder.kindLabels[kind]}>
                {options.map((item) => (
                  <option key={item.path} value={item.path}>
                    {item.label}
                  </option>
                ))}
              </optgroup>
            )
          })}
        </select>
      </label>

      {selectedPath && (
        <label>
          {t('patchBuilder.operationType')}
          <select value={selectedOp} onChange={(event) => handleOpChange(event.target.value as OpType)}>
            <option value="">{t('patchBuilder.choose')}</option>
            {availableOps.map((op) => (
              <option key={op} value={op}>
                {op}
              </option>
            ))}
          </select>
        </label>
      )}

      {selectedOp === 'replace' && (
        <>
          <label>
            {t('patchBuilder.replaceZh')}
            <textarea rows={3} value={zh} onChange={(event) => setZh(event.target.value)} />
          </label>
          <label>
            {t('patchBuilder.replaceEn')}
            <textarea rows={3} value={en} onChange={(event) => setEn(event.target.value)} />
          </label>
          <label>
            {t('patchBuilder.reason')}
            <input type="text" value={reason} onChange={(event) => setReason(event.target.value)} />
          </label>
          <label>
            {t('patchBuilder.evidence')}
            <div style={{ maxHeight: 160, overflowY: 'auto', border: '1px solid #ddd', borderRadius: 6, padding: 8 }}>
              {Object.values(facts).map((fact) => (
                <label key={fact.id} style={{ fontWeight: 400, marginTop: 4 }}>
                  <input
                    type="checkbox"
                    checked={selectedFacts.includes(fact.id)}
                    onChange={(event) =>
                      setSelectedFacts((prev) =>
                        event.target.checked ? [...prev, fact.id] : prev.filter((id) => id !== fact.id),
                      )
                    }
                  />{' '}
                  {fact.statement.zh || fact.statement.en}
                </label>
              ))}
            </div>
          </label>
        </>
      )}

      {selectedOp === 'reorder' && (
        <ReorderList path={selectedPath} structure={structure} order={reorderIds} onChange={setReorderIds} />
      )}

      {selectedOp && (
        <button type="button" onClick={addOperation}>
          {t('patchBuilder.addOperation')}
        </button>
      )}
      {formError && <p className="error-text">{formError}</p>}

      {pendingOps.length > 0 && (
        <>
          <h3>{t('patchBuilder.pendingTitle')}</h3>
          <ul className="issue-list">
            {pendingOps.map((operation, index) => (
              <li key={index}>
                <span className="badge badge-neutral">{operation.op}</span>{' '}
                {structure.find((item) => item.path === operation.path)?.label ?? operation.path}
                <button type="button" onClick={() => setPendingOps((prev) => prev.filter((_, i) => i !== index))}>
                  {t('patchBuilder.remove')}
                </button>
              </li>
            ))}
          </ul>
          <button disabled={submitMutation.isPending} onClick={() => submitMutation.mutate()}>
            {submitMutation.isPending ? t('patchBuilder.submitting') : t('patchBuilder.submit')}
          </button>
          {submitMutation.error && (
            <p className="error-text">{(submitMutation.error as Error).message}</p>
          )}
        </>
      )}
    </div>
  )
}
