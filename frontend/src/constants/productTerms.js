/**
 * 产品文案与核心概念口径 V1：首页 / 训练 / 结果 / 报告 / 历史等共用。
 * 仅统一前端展示用语，不承载业务规则。
 */

export const TRAINING_FOCUS_LABEL = Object.freeze({
  none: '常规训练',
  language: '语言专项',
  posture: '仪态专项',
  qa: '问答专项',
  content: '内容专项',
})

/** 目标设置等场景（四项专项，不含 none 键名导出时与 TRAINING_FOCUS_LABEL 一致） */
export const TRAINING_GOAL_FOCUS_LABEL = Object.freeze({
  language: TRAINING_FOCUS_LABEL.language,
  posture: TRAINING_FOCUS_LABEL.posture,
  qa: TRAINING_FOCUS_LABEL.qa,
  content: TRAINING_FOCUS_LABEL.content,
})

/** @param {string|null|undefined} raw */
export function trainingFocusLabel(raw) {
  const k = String(raw ?? 'none').trim().toLowerCase()
  if (k === 'none' || k === '') return TRAINING_FOCUS_LABEL.none
  return TRAINING_FOCUS_LABEL[k] || k
}

/** 分项分数行等：语言核心分 */
export const SCORE_DIM_SHORT = Object.freeze({
  language: '语言',
  posture: '仪态',
  content: '内容',
  qa: '问答',
})

export const DEFENSE_MATERIAL_LABEL = Object.freeze({
  with_ppt: '有课件答辩',
  without_ppt: '无课件答辩',
})

/** 答辩流程一句话（结果 / 报告 / 说明共用） */
export const DEFENSE_FLOW_OVERVIEW =
  '本轮流程：讲解阶段 → 老师提问 → 回答评估 → 老师追问。'

/** 训练页阶段步骤条（与主流程顺序一致） */
export const TRAINING_STAGE_TRACK = Object.freeze([
  { key: 'lecture', label: '讲解阶段' },
  { key: 'teacher_question', label: '答辩问答' },
  { key: 'answer_eval', label: '回答评估' },
  { key: 'followup', label: '老师追问' },
  { key: 'done', label: '训练完成' },
])

export const VALIDITY_LABEL = Object.freeze({
  valid: '有效训练',
  invalid: '无效训练',
})

/** 各页区块标题（宜短、宜稳） */
export const SECTION = Object.freeze({
  recentOverview: '最近训练概况',
  weeklySummary: '本周训练摘要',
  stageReviewSummary: '阶段复盘摘要',
  nextStagePlan: '下一阶段训练规划',
  nextStageSuggest: '下一阶段建议',
  validTrainingOverview: '有效训练总览',
  focusReview: '专项复盘',
  historyTitle: '训练历史',
  reportTitle: '训练报告',
  teacherFeedback: '老师点评与训练建议',
  overallSummary: '整体表现小结',
  primaryScores: '一级评分',
})

/** 登录 / 注册（账号入口口径） */
export const AUTH_COPY = Object.freeze({
  loginSubtitle: '登录后即可开始训练与查看复盘',
  registerTitle: '注册答见账号',
  registerSubtitle: '用于登录并保存你的训练记录',
  loginSuccess: '已登录',
  registerSuccess: '注册成功，已自动登录',
  loginLoading: '登录中…',
  registerLoading: '注册中…',
  usernamePlaceholderLogin: '字母、数字或下划线',
  usernamePlaceholderRegister: '3–32 位：字母、数字或下划线',
  passwordPlaceholderLogin: '至少 6 位',
  passwordPlaceholderRegister: '6–72 位',
  password2Placeholder: '再次输入密码',
  errBadCredentials: '账号或密码不正确',
  errLoginGeneric: '登录未成功，请检查网络后重试',
  errRegisterGeneric: '注册未成功，请稍后重试',
  errRegisterTaken: '该用户名可能已被占用',
})
