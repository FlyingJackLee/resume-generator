import { FileSearch, FileText, PlayCircle, Settings } from 'lucide-react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { useTranslation } from './i18n/LanguageContext'
import NewRunPage from './pages/NewRunPage'
import ResumeViewerPage from './pages/ResumeViewerPage'
import RunDetailPage from './pages/RunDetailPage'
import RunsListPage from './pages/RunsListPage'

export default function App() {
  const { t, uiLang, setUiLang } = useTranslation()

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <FileSearch size={22} />
          {t('nav.logo')}
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/" end>
            <PlayCircle size={16} />
            {t('nav.runs')}
          </NavLink>
          <NavLink to="/viewer">
            <FileText size={16} />
            {t('nav.resumeViewer')}
          </NavLink>
        </nav>
        <div className="sidebar-section-label">{t('nav.masterResumeSection')}</div>
        <nav className="sidebar-nav">
          <NavLink to="/viewer?token=master">
            <FileText size={16} />
            {t('nav.masterResume')}
          </NavLink>
        </nav>
        <div className="sidebar-spacer" />
        <div className="lang-toggle" style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
          <button className={uiLang === 'zh' ? 'active' : ''} onClick={() => setUiLang('zh')}>
            中
          </button>
          <button className={uiLang === 'en' ? 'active' : ''} onClick={() => setUiLang('en')}>
            EN
          </button>
        </div>
        <div className="sidebar-user">
          <div className="sidebar-user-avatar">RA</div>
          <span className="sidebar-user-name">{t('nav.sidebarUser')}</span>
          <Settings size={16} />
        </div>
      </aside>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<RunsListPage />} />
          <Route path="/runs/new" element={<NewRunPage />} />
          <Route path="/runs/:runId" element={<RunDetailPage />} />
          <Route path="/viewer" element={<ResumeViewerPage />} />
        </Routes>
      </main>
    </div>
  )
}
