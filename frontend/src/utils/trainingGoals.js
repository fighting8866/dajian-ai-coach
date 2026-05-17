/**
 * 训练目标与达成进度：云端账号同步优先，本地 user-scoped 作缓存兜底（V1）
 */

export { TRAINING_GOAL_FOCUS_LABEL } from '../constants/productTerms'
import { TRAINING_GOAL_FOCUS_LABEL } from '../constants/productTerms'
import { getActiveUserId, readUserScopedItem, writeUserScopedItem, removeUserScopedItem } from './userScopedStorage'

export const TRAINING_GOALS_STORAGE_KEY = 'mianshi_training_goals_v1'
export const TRAINING_GOALS_CHANGED_EVENT = 'mianshi-training-goals-changed'

const FOCUS_KEYS = new Set(['language', 'posture', 'qa', 'content'])

export const TRAINING_GOALS_DEFAULTS = Object.freeze({
  v: 1,
  target_total_score: null,
  target_focus: null,
  target_valid_session_count: null,
})

/** 登录后由 accountSettingsSync 写入 */
let _serverGoalsOverlay = null

export function normalizeGoals(raw) {
  const o = raw && typeof raw === 'object' ? raw : {}
  let target_total_score = null
  if (o.target_total_score != null && o.target_total_score !== '') {
    const n = Number(o.target_total_score)
    if (Number.isFinite(n)) target_total_score = Math.min(100, Math.max(0, n))
  }
  let target_focus = null
  const fk = String(o.target_focus || '').trim().toLowerCase()
  if (FOCUS_KEYS.has(fk)) target_focus = fk
  let target_valid_session_count = null
  if (o.target_valid_session_count != null && o.target_valid_session_count !== '') {
    const c = Number(o.target_valid_session_count)
    if (Number.isFinite(c) && c > 0) target_valid_session_count = Math.min(999, Math.floor(c))
  }
  return {
    v: 1,
    target_total_score,
    target_focus,
    target_valid_session_count,
  }
}

export function setTrainingGoalsServerOverlay(g) {
  _serverGoalsOverlay = g ? normalizeGoals(g) : null
}

export function clearTrainingGoalsServerOverlay() {
  _serverGoalsOverlay = null
}

/**
 * 仅从本地读（不经过云端 overlay）
 */
export function readTrainingGoalsLocalOnly() {
  const uid = getActiveUserId()
  try {
    const raw = readUserScopedItem(localStorage, TRAINING_GOALS_STORAGE_KEY, uid, { migrateLegacy: true })
    if (!raw) return { ...TRAINING_GOALS_DEFAULTS }
    return normalizeGoals(JSON.parse(raw))
  } catch {
    return { ...TRAINING_GOALS_DEFAULTS }
  }
}

function notifyGoalsChanged() {
  try {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event(TRAINING_GOALS_CHANGED_EVENT))
    }
  } catch (_) {}
}

export function readTrainingGoals() {
  if (_serverGoalsOverlay) {
    return normalizeGoals(_serverGoalsOverlay)
  }
  return readTrainingGoalsLocalOnly()
}

function mirrorGoalsToLocal(next) {
  const uid = getActiveUserId()
  try {
    writeUserScopedItem(localStorage, TRAINING_GOALS_STORAGE_KEY, JSON.stringify(next), uid)
  } catch (_) {}
}

/** 登录后拉取云端成功时：写 overlay + 本地镜像 */
export function applyHydratedServerGoals(goals) {
  const next = normalizeGoals(goals)
  _serverGoalsOverlay = { ...next }
  mirrorGoalsToLocal(next)
}

export function writeTrainingGoals(partial) {
  const next = normalizeGoals({ ...readTrainingGoals(), ...partial })
  _serverGoalsOverlay = { ...next }
  mirrorGoalsToLocal(next)
  notifyGoalsChanged()
  return next
}

export function resetTrainingGoals() {
  const uid = getActiveUserId()
  const next = { ...TRAINING_GOALS_DEFAULTS }
  _serverGoalsOverlay = { ...next }
  try {
    removeUserScopedItem(localStorage, TRAINING_GOALS_STORAGE_KEY, uid, true)
  } catch (_) {}
  mirrorGoalsToLocal(next)
  notifyGoalsChanged()
  return { ...TRAINING_GOALS_DEFAULTS }
}

export function goalsSnapshotForLog(g) {
  const x = g && typeof g === 'object' ? normalizeGoals(g) : readTrainingGoals()
  return {
    target_total_score: x.target_total_score,
    target_focus: x.target_focus,
    target_valid_session_count: x.target_valid_session_count,
  }
}

export function hasActiveTrainingGoals(goals) {
  const g = goals ? normalizeGoals(goals) : readTrainingGoals()
  if (g.target_total_score != null) return true
  if (g.target_focus) return true
  if (g.target_valid_session_count != null) return true
  return false
}

function numOrNull(v) {
  if (v === null || v === undefined || v === '') return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

function isValidHistoryItem(it) {
  return it && it.training_valid !== false
}

function subscoreForFocus(it, focusKey) {
  const map = {
    language: 'language_score',
    posture: 'posture_score',
    content: 'content_score',
    qa: 'qa_score',
  }
  return numOrNull(it[map[focusKey]])
}

/**
 * @param {{ goals?: object, historyList: any[], overview?: object | null }} args
 */
export function computeTrainingGoalProgress({ goals, historyList, overview }) {
  const g = goals ? normalizeGoals(goals) : readTrainingGoals()
  const list = Array.isArray(historyList) ? historyList : []
  const valid = list.filter(isValidHistoryItem)
  const validCount = valid.length

  let bestTotal = null
  for (const it of valid) {
    const t = numOrNull(it.total_score)
    if (t == null) continue
    if (bestTotal == null || t > bestTotal) bestTotal = t
  }

  let recentAvgTotal = null
  if (overview?.overview_ready && overview.avg_total_score_recent != null) {
    const a = Number(overview.avg_total_score_recent)
    if (Number.isFinite(a)) recentAvgTotal = a
  }
  if (recentAvgTotal == null && valid.length) {
    const n = Math.min(valid.length, overview?.recent_window_size || 7)
    const slice = valid.slice(0, n)
    const sum = slice.reduce((s, x) => s + (Number(x.total_score) || 0), 0)
    recentAvgTotal = sum / slice.length
  }

  const T = g.target_total_score
  let gapToTarget = null
  if (T != null) {
    if (bestTotal != null) gapToTarget = Math.max(0, T - bestTotal)
    else gapToTarget = T
  }

  const tgtN = g.target_valid_session_count
  const countGoalActive = tgtN != null && tgtN > 0

  let focusBest = null
  const fk = g.target_focus
  const focusLabel = fk ? TRAINING_GOAL_FOCUS_LABEL[fk] || fk : ''
  if (fk && FOCUS_KEYS.has(fk)) {
    for (const it of valid) {
      const s = subscoreForFocus(it, fk)
      if (s == null) continue
      if (focusBest == null || s > focusBest) focusBest = s
    }
  }

  return {
    goals: goalsSnapshotForLog(g),
    validSessionCount: validCount,
    bestTotal,
    recentAvgTotal,
    targetTotal: T,
    gapToTarget,
    targetValidCount: countGoalActive ? tgtN : null,
    validCountProgress: countGoalActive ? { current: validCount, target: tgtN } : null,
    targetFocus: fk && FOCUS_KEYS.has(fk) ? fk : null,
    focusBest,
    focusLabel,
  }
}

/**
 * 结果页：本轮与目标的关系（需传入完整 history 以便排除当前会话算历史最好）
 */
export function buildResultGoalNarrative({
  goals,
  sessionId,
  trainingValid,
  totalScore,
  sessionFocusKey,
  focusTrendKind,
  trainingFocusVsRecent,
  historyList,
}) {
  const g = goals ? normalizeGoals(goals) : readTrainingGoals()
  if (!hasActiveTrainingGoals(g)) {
    return { lines: [], kind: 'no_goal' }
  }
  if (trainingValid === false) {
    return { lines: [], kind: 'invalid' }
  }

  const sid = String(sessionId || '').trim()
  const list = Array.isArray(historyList) ? historyList : []
  const validOthers = list.filter(
    (it) => isValidHistoryItem(it) && String(it.session_id || '').trim() !== sid
  )

  const lines = []
  const T = g.target_total_score
  const C = numOrNull(totalScore)

  if (T != null && C != null) {
    let priorBest = null
    for (const it of validOthers) {
      const t = numOrNull(it.total_score)
      if (t == null) continue
      if (priorBest == null || t > priorBest) priorBest = t
    }
    const newBest = priorBest == null ? C : Math.max(priorBest, C)
    const gapBefore = priorBest == null ? null : Math.max(0, T - priorBest)
    const gapAfter = Math.max(0, T - newBest)
    if (priorBest != null && gapBefore != null && gapBefore - gapAfter > 0.05) {
      const closer = gapBefore - gapAfter
      lines.push(`本轮较目标总分更接近了 ${closer.toFixed(1)} 分（目标总分 ${T.toFixed(1)}）。`)
    } else if (C >= T) {
      lines.push(`本轮总分已达到或超过目标 ${T.toFixed(1)} 分。`)
    } else if (priorBest == null) {
      lines.push(`当前总分 ${C.toFixed(1)} 分，距离目标 ${T.toFixed(1)} 分还差 ${(T - C).toFixed(1)} 分。`)
    }
  }

  const goalFk = g.target_focus
  const roundFk = String(sessionFocusKey || 'none').trim().toLowerCase()
  const trend = String(focusTrendKind || '').trim().toLowerCase()
  const vs = typeof trainingFocusVsRecent === 'string' ? trainingFocusVsRecent : ''
  const focusUp = trend === 'up' || /上升|提高|进步|更好|往上/.test(vs)

  if (
    goalFk &&
    FOCUS_KEYS.has(goalFk) &&
    roundFk === goalFk &&
    focusUp &&
    !lines.some((x) => x.includes('更接近了'))
  ) {
    const lab = TRAINING_GOAL_FOCUS_LABEL[goalFk] || goalFk
    if (lines.length && T != null && C != null && C < T) {
      lines.push(`总分距目标仍有一点距离，但「${lab}」专项较近期同专项已有提升。`)
    } else if (!lines.length) {
      lines.push(`本轮在「${lab}」专项上较近期同专项有提升，继续朝目标积累有效训练。`)
    }
  }

  if (!lines.length && T != null && C != null && C < T) {
    lines.push(`本轮尚未明显拉近与目标总分的距离（目标 ${T.toFixed(1)}），可多练几次再看趋势。`)
  }

  if (
    !lines.length &&
    g.target_valid_session_count != null &&
    g.target_valid_session_count > 0 &&
    trainingValid !== false
  ) {
    lines.push(
      `本轮有效训练已记入次数进度（目标 ${g.target_valid_session_count} 次），可在首页或历史查看累计。`
    )
  }

  return { lines, kind: lines.length ? 'ok' : 'empty' }
}
