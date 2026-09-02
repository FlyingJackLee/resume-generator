import type { BilingualText } from '../api/types'

export function localize(value: BilingualText | string[] | null | undefined): string {
  if (value == null) return ''
  if (Array.isArray(value)) return value.join(' / ')
  return value.zh || value.en || ''
}

export function formatDate(iso: string | undefined, uiLang: 'zh' | 'en' = 'zh'): string {
  if (!iso) return '-'
  const locale = uiLang === 'zh' ? 'zh-CN' : 'en-US'
  return new Date(iso).toLocaleString(locale)
}
