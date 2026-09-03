export interface Translations {
  nav: {
    logo: string
    runs: string
    agentSection: string
    onlineSection: string
    onlineEditor: string
    templates: string
    resumeViewer: string
    masterResumeSection: string
    masterResume: string
    sidebarUser: string
  }
  runsList: {
    title: string
    subtitle: string
    newRun: string
    loading: string
    empty: string
    colJdCompany: string
    colStatus: string
    colScore: string
    colCreated: string
    uncategorized: string
    showing: string
    pageSize: string
  }
  newRun: {
    title: string
    subtitle: string
    jdLabel: string
    jdLabelPlaceholder: string
    company: string
    companyPlaceholder: string
    jd: string
    jdPlaceholder: string
    submit: string
    submitting: string
    howItWorks: string
    steps: { title: string; desc: string }[]
    privacyNote: string
  }
  runDetail: {
    loading: string
    uncategorized: string
    currentStage: string
    round: string
    generated: string
    runFailed: string
    retry: { button: string; retrying: string }
    jumpToCurrent: string
    compileStepPlaceholder: string
    stepPending: string
    jobProfile: { title: string; weight: string }
    matchReport: { title: string; confidence: string }
    hrReview: {
      title: string
      strengths: string
      weaknesses: string
      missingKeywords: string
      priorities: string
    }
    strategyCard: { title: string; priority: string; evidence: string }
    validation: { title: string; passed: string; failed: string }
    hiringReview: {
      title: string
      concerns: string
      suggestions: string
      scoreLabels: {
        jd_core_match: string
        relevant_experience: string
        technical_depth: string
        business_impact: string
        ats_keywords: string
        clarity: string
        credibility: string
      }
    }
    finalDiff: { title: string; none: string; hidden: string; evidence: string }
    activityLog: { title: string }
    runInfo: { title: string; status: string; stage: string; created: string; elapsed: string }
    tabs: { activityLog: string; notes: string }
    notes: { placeholder: string; save: string; saving: string; saved: string }
    breadcrumbRuns: string
    strategySummary: { title: string; total: string; high: string; medium: string; low: string }
    troubleshooting: { title: string; total: string }
    langsmith: string
  }
  workflow: {
    title: string
    steps: {
      analyze_jd: string
      match_resume: string
      hr_review: string
      build_strategy: string
      gate1: string
      edit_resume: string
      apply_patch: string
      validate_facts: string
      hiring_manager: string
      gate2: string
      final: string
    }
    macro: {
      analyze_jd: string
      match_resume: string
      hr_review: string
      build_strategy: string
      gate1: string
      compile: string
      final: string
    }
  }
  statusBadge: {
    neutral: string
    active: string
    waiting: string
    success: string
    danger: string
    purple: string
  }
  strategyGate: {
    title: string
    positioning: string
    allowedKeywords: string
    forbiddenKeywords: string
    addHint: string
    pendingActionsTitle: string
    pendingActionsHint: string
    priority: string
    instruction: string
    evidence: string
    save: string
    saving: string
    approve: string
    approving: string
  }
  finalGate: {
    approve: string
    restore: string
    reject: string
    advanced: string
  }
  patchBuilder: {
    advancedTitle: string
    hint: string
    targetField: string
    choose: string
    operationType: string
    kindLabels: {
      text: string
      text_hideable: string
      hideable: string
      collection: string
      removed: string
    }
    replaceZh: string
    replaceEn: string
    reason: string
    evidence: string
    addOperation: string
    reorderUnsupported: string
    pendingTitle: string
    remove: string
    submit: string
    submitting: string
    validationError: string
  }
  resumeViewer: {
    title: string
    subtitle: string
    version: string
    masterResumeOption: string
    pendingApproval: string
  }
}

const zh: Translations = {
  nav: {
    logo: 'Resume Agent',
    runs: 'ATS JD 匹配',
    agentSection: '智能优化',
    onlineSection: '在线简历',
    onlineEditor: '修改基线版本',
    templates: '模板管理',
    resumeViewer: '所有版本',
    masterResumeSection: 'MASTER RESUME',
    masterResume: '基线简历',
    sidebarUser: 'Resume Agent',
  },
  runsList: {
    title: 'Runs',
    subtitle: '查看和管理所有简历优化 run。',
    newRun: '新建 Run',
    loading: '加载中…',
    empty: '还没有任何 run，点击右上角新建一个。',
    colJdCompany: 'JD / 公司',
    colStatus: '状态',
    colScore: 'Hiring Manager 评分',
    colCreated: '创建时间',
    uncategorized: '未分类',
    showing: '显示第 {from}-{to} 条，共 {total} 条',
    pageSize: '{size} 条/页',
  },
  newRun: {
    title: '新建 Run',
    subtitle: '填写岗位信息即可开始分析，我们会解析 JD 并帮你制定改写策略。',
    jdLabel: 'JD 标识',
    jdLabelPlaceholder: '例如 Google AI Agent',
    company: '公司（可选，不填会在分析完成后自动识别）',
    companyPlaceholder: '例如 Google',
    jd: '岗位 JD',
    jdPlaceholder: '粘贴职位描述原文…',
    submit: '开始分析',
    submitting: '提交中…',
    howItWorks: '流程说明',
    steps: [
      { title: '分析 JD', desc: '提取岗位的核心要求、技能与招聘信号。' },
      { title: '生成策略', desc: 'AI 提出针对性的简历改写策略与内容规划。' },
      { title: '人工审批', desc: '你来审阅并批准策略和最终内容。' },
      { title: '最终审核', desc: '编译最终简历，供你确认导出。' },
    ],
    privacyNote: '你的 JD 和简历内容不会分享给任何第三方。',
  },
  runDetail: {
    loading: '加载中…',
    uncategorized: '未分类',
    currentStage: '当前阶段：',
    round: '第 {n} 轮',
    generated: '已生成：{file}',
    runFailed: '运行失败',
    retry: { button: '重试', retrying: '重试中…' },
    jumpToCurrent: '回到当前步骤',
    compileStepPlaceholder: '这一步没有独立产出可看，请查看 Fact Validator / Hiring Manager 或最终 Diff。',
    stepPending: '该步骤尚未产出内容',
    jobProfile: { title: '岗位画像', weight: '（权重 {n}）' },
    matchReport: { title: '匹配报告', confidence: '（置信度 {n}%）' },
    hrReview: {
      title: 'HR 评审',
      strengths: '优势：',
      weaknesses: '薄弱点：',
      missingKeywords: '缺失关键词：',
      priorities: '建议优先修改：',
    },
    strategyCard: { title: '修改策略', priority: '优先级', evidence: '事实依据：' },
    validation: { title: '事实校验', passed: '通过', failed: '未通过' },
    hiringReview: {
      title: 'Hiring Manager',
      concerns: '关注点',
      suggestions: '建议',
      scoreLabels: {
        jd_core_match: 'JD 核心匹配',
        relevant_experience: '相关经历',
        technical_depth: '技术深度',
        business_impact: '业务价值',
        ats_keywords: 'ATS 关键词',
        clarity: '清晰度',
        credibility: '可信度',
      },
    },
    finalDiff: { title: '最终 Diff', none: '（无）', hidden: '（已隐藏）', evidence: '事实依据：' },
    activityLog: { title: 'Activity Log' },
    runInfo: { title: 'Run 信息', status: '状态', stage: '当前阶段', created: '创建时间', elapsed: '已耗时' },
    tabs: { activityLog: 'Activity Log', notes: '备注' },
    notes: { placeholder: '记点什么……', save: '保存', saving: '保存中…', saved: '已保存' },
    breadcrumbRuns: 'Runs',
    strategySummary: { title: '策略概览', total: '总修改数', high: '高优先级', medium: '中优先级', low: '低优先级' },
    troubleshooting: { title: '问题排查', total: '共 {n} 个问题' },
    langsmith: '在 LangSmith 中查看',
  },
  workflow: {
    title: 'Workflow',
    steps: {
      analyze_jd: 'JD Analyzer',
      match_resume: 'Resume Matcher',
      hr_review: 'HR Reviewer',
      build_strategy: 'Rewrite Strategy',
      gate1: 'Human Gate ①',
      edit_resume: 'Resume Editor',
      apply_patch: 'Patch Engine',
      validate_facts: 'Fact Validator',
      hiring_manager: 'Hiring Manager',
      gate2: 'Human Gate ②',
      final: 'Final Approval',
    },
    macro: {
      analyze_jd: 'JD Analyzer',
      match_resume: 'Resume Matcher',
      hr_review: 'HR Reviewer',
      build_strategy: 'Rewrite Strategy',
      gate1: 'Strategy Approval',
      compile: 'Compilation',
      final: 'Final Approval',
    },
  },
  statusBadge: {
    neutral: '未开始',
    active: '运行中',
    waiting: '等待中',
    success: '已完成',
    danger: '失败',
    purple: '已拒绝',
  },
  strategyGate: {
    title: '修改策略',
    positioning: '岗位定位',
    allowedKeywords: '允许使用的关键词',
    forbiddenKeywords: '禁止使用的关键词',
    addHint: '输入后回车添加',
    pendingActionsTitle: '拟执行的修改',
    pendingActionsHint: '取消勾选即可丢弃该条建议；只能调整优先级和修改说明，不能新增建议。',
    priority: '优先级（1 最高 - 5 最低）',
    instruction: '修改说明',
    evidence: '事实依据：',
    save: '保存修改',
    saving: '保存中…',
    approve: '批准并生成简历',
    approving: '提交中…',
  },
  finalGate: {
    approve: '批准并导出最终 YAML',
    restore: '恢复完整原始版本',
    reject: '拒绝本次版本',
    advanced: '高级：人工微调',
  },
  patchBuilder: {
    advancedTitle: '高级：人工微调',
    hint: '仍受白名单和 Fact Validator 约束，提交后会立即重新校验。',
    targetField: '目标字段',
    choose: '请选择…',
    operationType: '操作类型',
    kindLabels: {
      text: '可替换文本',
      text_hideable: '可替换/隐藏文本',
      hideable: '可隐藏条目',
      collection: '可重排序的集合',
      removed: '已隐藏（可恢复）',
    },
    replaceZh: '中文内容',
    replaceEn: '英文内容',
    reason: '修改理由',
    evidence: '支撑事实（至少选一条）',
    addOperation: '添加到本次 Patch',
    reorderUnsupported: '这个集合暂不支持在线重排序。',
    pendingTitle: '待提交的修改',
    remove: '删除',
    submit: '应用 Patch 并重新校验',
    submitting: '提交中…',
    validationError: '替换操作需要填写中英文内容、修改理由，并至少选择一条支撑事实。',
  },
  resumeViewer: {
    title: '所有版本',
    subtitle: '查看基线 Master Resume 与已完成的目标简历版本。',
    version: '版本',
    masterResumeOption: 'Master Resume（基准）',
    pendingApproval: '（待批准，预览候选版本）',
  },
}

const en: Translations = {
  nav: {
    logo: 'Resume Agent',
    runs: 'Runs',
    agentSection: 'AGENT WORKBENCH',
    onlineSection: 'ONLINE RESUME',
    onlineEditor: 'Resume Editor',
    templates: 'Templates',
    resumeViewer: 'Resume Viewer',
    masterResumeSection: 'MASTER RESUME',
    masterResume: 'Master Resume',
    sidebarUser: 'Resume Agent',
  },
  runsList: {
    title: 'Runs',
    subtitle: 'View and manage all your resume optimization runs.',
    newRun: 'New Run',
    loading: 'Loading…',
    empty: 'No runs yet — click "New Run" in the top right to create one.',
    colJdCompany: 'JD / Company',
    colStatus: 'Status',
    colScore: 'Hiring Manager Score',
    colCreated: 'Created',
    uncategorized: 'Uncategorized',
    showing: 'Showing {from} to {to} of {total} runs',
    pageSize: '{size} / page',
  },
  newRun: {
    title: 'New Run',
    subtitle: "Create a new run by adding the job details. We'll analyze the JD and help you build a winning strategy.",
    jdLabel: 'JD Name',
    jdLabelPlaceholder: 'e.g. Google AI Agent',
    company: 'Company (optional — auto-detected after analysis if left blank)',
    companyPlaceholder: 'e.g. Google',
    jd: 'Job Description',
    jdPlaceholder: 'Paste the job description here…',
    submit: 'Start Analysis',
    submitting: 'Submitting…',
    howItWorks: 'How it works',
    steps: [
      { title: 'Analyze JD', desc: 'We extract key requirements, skills, and hiring signals.' },
      { title: 'Propose Strategy', desc: 'AI proposes a tailored resume strategy and content plan.' },
      { title: 'Human Approval', desc: 'You review and approve the strategy and content.' },
      { title: 'Final Review', desc: 'We compile the final resume for your review.' },
    ],
    privacyNote: 'Your job descriptions and resumes are never shared with third parties.',
  },
  runDetail: {
    loading: 'Loading…',
    uncategorized: 'Uncategorized',
    currentStage: 'Current stage: ',
    round: 'Round {n}',
    generated: 'Generated: {file}',
    runFailed: 'Run Failed',
    retry: { button: 'Retry', retrying: 'Retrying…' },
    jumpToCurrent: 'Jump to current step',
    compileStepPlaceholder: 'No standalone output for this step — see Fact Validator / Hiring Manager or the final diff.',
    stepPending: 'Nothing to show for this step yet',
    jobProfile: { title: 'Job Profile', weight: '(Weight {n})' },
    matchReport: { title: 'Match Report', confidence: '(Confidence {n}%)' },
    hrReview: {
      title: 'HR Review',
      strengths: 'Strengths: ',
      weaknesses: 'Weaknesses: ',
      missingKeywords: 'Missing keywords: ',
      priorities: 'Rewrite priorities: ',
    },
    strategyCard: { title: 'Rewrite Strategy', priority: 'Priority', evidence: 'Evidence: ' },
    validation: { title: 'Fact Validation', passed: 'Passed', failed: 'Failed' },
    hiringReview: {
      title: 'Hiring Manager',
      concerns: 'Concerns',
      suggestions: 'Suggestions',
      scoreLabels: {
        jd_core_match: 'JD Core Match',
        relevant_experience: 'Relevant Experience',
        technical_depth: 'Technical Depth',
        business_impact: 'Business Impact',
        ats_keywords: 'ATS Keywords',
        clarity: 'Clarity',
        credibility: 'Credibility',
      },
    },
    finalDiff: { title: 'Final Diff', none: '(none)', hidden: '(hidden)', evidence: 'Evidence: ' },
    activityLog: { title: 'Activity Log' },
    runInfo: { title: 'Run Info', status: 'Status', stage: 'Current Stage', created: 'Created', elapsed: 'Elapsed' },
    tabs: { activityLog: 'Activity Log', notes: 'Notes' },
    notes: { placeholder: 'Jot something down…', save: 'Save', saving: 'Saving…', saved: 'Saved' },
    breadcrumbRuns: 'Runs',
    strategySummary: { title: 'Strategy Summary', total: 'Total Actions', high: 'High Priority', medium: 'Medium Priority', low: 'Low Priority' },
    troubleshooting: { title: 'Troubleshooting', total: '{n} issues found' },
    langsmith: 'View in LangSmith',
  },
  workflow: {
    title: 'Workflow',
    steps: {
      analyze_jd: 'JD Analyzer',
      match_resume: 'Resume Matcher',
      hr_review: 'HR Reviewer',
      build_strategy: 'Rewrite Strategy',
      gate1: 'Human Gate ①',
      edit_resume: 'Resume Editor',
      apply_patch: 'Patch Engine',
      validate_facts: 'Fact Validator',
      hiring_manager: 'Hiring Manager',
      gate2: 'Human Gate ②',
      final: 'Final Approval',
    },
    macro: {
      analyze_jd: 'JD Analyzer',
      match_resume: 'Resume Matcher',
      hr_review: 'HR Reviewer',
      build_strategy: 'Rewrite Strategy',
      gate1: 'Strategy Approval',
      compile: 'Compilation',
      final: 'Final Approval',
    },
  },
  statusBadge: {
    neutral: 'INIT',
    active: 'RUNNING',
    waiting: 'WAITING',
    success: 'COMPLETED',
    danger: 'FAILED',
    purple: 'REJECTED',
  },
  strategyGate: {
    title: 'Rewrite Strategy',
    positioning: 'Positioning Statement',
    allowedKeywords: 'Allowed Keywords',
    forbiddenKeywords: 'Blocked Keywords',
    addHint: 'Type and press Enter to add',
    pendingActionsTitle: 'Strategy Actions',
    pendingActionsHint: 'Uncheck to discard a suggestion; you can only adjust priority and instructions, not add new ones.',
    priority: 'Priority (1 highest – 5 lowest)',
    instruction: 'Instruction',
    evidence: 'Evidence: ',
    save: 'Save Changes',
    saving: 'Saving…',
    approve: 'Approve & Generate Resume',
    approving: 'Submitting…',
  },
  finalGate: {
    approve: 'Approve & Export Final YAML',
    restore: 'Restore Original',
    reject: 'Reject This Version',
    advanced: 'Advanced: Manual Edit',
  },
  patchBuilder: {
    advancedTitle: 'Advanced: Manual Edit',
    hint: 'Still constrained by the whitelist and Fact Validator — revalidated immediately on submit.',
    targetField: 'Target Field',
    choose: 'Select…',
    operationType: 'Operation Type',
    kindLabels: {
      text: 'Replaceable Text',
      text_hideable: 'Replaceable / Hideable Text',
      hideable: 'Hideable Entry',
      collection: 'Reorderable Collection',
      removed: 'Hidden (Restorable)',
    },
    replaceZh: 'Chinese Content',
    replaceEn: 'English Content',
    reason: 'Reason',
    evidence: 'Supporting Facts (select at least one)',
    addOperation: 'Add to This Patch',
    reorderUnsupported: 'This collection does not support online reordering yet.',
    pendingTitle: 'Pending Changes',
    remove: 'Remove',
    submit: 'Apply Patch & Revalidate',
    submitting: 'Submitting…',
    validationError: 'A replace operation needs Chinese and English content, a reason, and at least one supporting fact.',
  },
  resumeViewer: {
    title: 'Resume Viewer',
    subtitle: 'Preview the generated resume. Switch versions or languages to review different outputs.',
    version: 'Version',
    masterResumeOption: 'Master Resume (baseline)',
    pendingApproval: '(pending approval, previewing candidate)',
  },
}

export const translations = { zh, en }
export type UiLang = keyof typeof translations
