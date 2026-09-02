import { createContext, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { translations } from './translations'
import type { Translations, UiLang } from './translations'

const STORAGE_KEY = 'resume-agent-ui-lang'

function readStoredLang(): UiLang {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === 'en' ? 'en' : 'zh'
  } catch {
    return 'zh'
  }
}

function resolvePath(dict: unknown, path: string): unknown {
  return path.split('.').reduce<unknown>((node, key) => {
    if (node && typeof node === 'object' && key in node) {
      return (node as Record<string, unknown>)[key]
    }
    return undefined
  }, dict)
}

function interpolate(template: string, params?: Record<string, string | number>): string {
  if (!params) return template
  return template.replace(/\{(\w+)\}/g, (match, key) =>
    key in params ? String(params[key]) : match,
  )
}

interface LanguageContextValue {
  uiLang: UiLang
  setUiLang: (lang: UiLang) => void
  dict: Translations
  t: (path: string, params?: Record<string, string | number>) => string
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [uiLang, setUiLangState] = useState<UiLang>(readStoredLang)

  const setUiLang = (lang: UiLang) => {
    setUiLangState(lang)
    try {
      localStorage.setItem(STORAGE_KEY, lang)
    } catch {
      // localStorage unavailable; language choice just won't persist
    }
  }

  const value = useMemo<LanguageContextValue>(() => {
    const dict = translations[uiLang]
    return {
      uiLang,
      setUiLang,
      dict,
      t: (path, params) => {
        const raw = resolvePath(dict, path)
        return typeof raw === 'string' ? interpolate(raw, params) : path
      },
    }
  }, [uiLang])

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useTranslation(): LanguageContextValue {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useTranslation must be used within a LanguageProvider')
  return ctx
}
