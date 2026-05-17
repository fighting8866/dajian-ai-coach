/**
 * 训练目标状态与阶段总结 V1（规则版，不接模型）
 */

import { hasActiveTrainingGoals, TRAINING_GOAL_FOCUS_LABEL } from './trainingGoals'

export const GOAL_STATUS = {
  NOT_STARTED: 'not_started',
  IN_PROGRESS: 'in_progress',
  NEAR_COMPLETE: 'near_complete',
  ACHIEVED: 'achieved',
}

/** 总分：距目标 ≤3 分视为接近达成 */
const TOTAL_NEAR_GAP_MAX = 3
/** 仅设专项、无总分时：专项历史最好分阈值 */
const FOCUS_ONLY_ACHIEVED_MIN = 85
const FOCUS_ONLY_NEAR_MIN = 72
/** 同时有总目标 T 时，专项最好分与 T 对齐的容差 */
const FOCUS_WITH_TOTAL_MARGIN = 3

/**
 * 单维度状态：achieved | near_complete | in_progress | not_applicable
 */
function axisTotal(T, bestTotal, validCount) {
  if (T == null) return { key: 'total', state: 'not_applicable' }
  if (validCount <= 0 || bestTotal == null) return { key: 'total', state: 'in_progress', gap: T }
  if (bestTotal >= T) return { key: 'total', state: 'achieved', gap: 0 }
  const gap = T - bestTotal
  if (gap > 0 && gap <= TOTAL_NEAR_GAP_MAX) return { key: 'total', state: 'near_complete', gap }
  return { key: 'total', state: 'in_progress', gap }
}

function axisCount(targetN, current, validCount) {
  if (targetN == null || targetN <= 0) return { key: 'count', state: 'not_applicable' }
  if (validCount <= 0 && current <= 0) return { key: 'count', state: 'in_progress', gap: targetN }
  if (current >= targetN) return { key: 'count', state: 'achieved', gap: 0 }
  if (current === targetN - 1) return { key: 'count', state: 'near_complete', gap: 1 }
  return { key: 'count', state: 'in_progress', gap: targetN - current }
}

function axisFocus(g, progress) {
  const fk = g.target_focus
  if (!fk) return { key: 'focus', state: 'not_applicable' }
  const best = progress.focusBest
  const T = g.target_total_score
  if (best == null) {
    return { key: 'focus', state: 'in_progress' }
  }
  if (T != null) {
    if (best >= T) return { key: 'focus', state: 'achieved', gap: 0 }
    const gap = T - best
    if (gap > 0 && gap <= FOCUS_WITH_TOTAL_MARGIN) return { key: 'focus', state: 'near_complete', gap }
    return { key: 'focus', state: 'in_progress', gap }
  }
  if (best >= FOCUS_ONLY_ACHIEVED_MIN) return { key: 'focus', state: 'achieved', gap: 0 }
  if (best >= FOCUS_ONLY_NEAR_MIN) return { key: 'focus', state: 'near_complete', gap: FOCUS_ONLY_ACHIEVED_MIN - best }
  return { key: 'focus', state: 'in_progress', gap: FOCUS_ONLY_ACHIEVED_MIN - best }
}

function allSetAxesAchieved(axes) {
  const relevant = axes.filter((a) => a.state !== 'not_applicable')
  if (!relevant.length) return false
  return relevant.every((a) => a.state === 'achieved')
}

function anySetAxisNear(axes) {
  return axes.some((a) => a.state !== 'not_applicable' && a.state === 'near_complete')
}

/**
 * @param {ReturnType<typeof computeTrainingGoalProgress>} progress
 * @param {object} [goals] 可选，默认 progress.goals
 * @returns {{ status: string, axes: object[], headline: string, summaryForLog: object }}
 */
export function computeGoalStatusPack(progress, goals) {
  const g = goals || progress?.goals || {}
  const summaryForLog = {
    validSessionCount: progress?.validSessionCount ?? 0,
    axes: [],
  }

  if (!hasActiveTrainingGoals(g)) {
    return {
      status: null,
      axes: [],
      headline: '',
      summaryForLog: { ...summaryForLog, status: 'no_goal' },
    }
  }

  const validCount = progress.validSessionCount || 0
  const bestTotal = progress.bestTotal
  const T = g.target_total_score
  const tgtN = g.target_valid_session_count
  const curN = progress.validCountProgress?.current ?? validCount
  const targetN = tgtN

  const axes = [
    axisTotal(T, bestTotal, validCount),
    axisFocus(g, progress),
    axisCount(targetN, curN, validCount),
  ]
  summaryForLog.axes = axes.map((a) => ({ key: a.key, state: a.state, gap: a.gap }))

  if (validCount <= 0) {
    summaryForLog.status = GOAL_STATUS.NOT_STARTED
    return {
      status: GOAL_STATUS.NOT_STARTED,
      axes,
      headline: '目标已设，还未产生有效训练记录',
      summaryForLog,
    }
  }

  if (allSetAxesAchieved(axes)) {
    summaryForLog.status = GOAL_STATUS.ACHIEVED
    return {
      status: GOAL_STATUS.ACHIEVED,
      axes,
      headline: '当前阶段目标已达成',
      summaryForLog,
    }
  }

  if (anySetAxisNear(axes)) {
    summaryForLog.status = GOAL_STATUS.NEAR_COMPLETE
    return {
      status: GOAL_STATUS.NEAR_COMPLETE,
      axes,
      headline: '已接近目标，可再完成少量有效训练冲刺',
      summaryForLog,
    }
  }

  summaryForLog.status = GOAL_STATUS.IN_PROGRESS
  return {
    status: GOAL_STATUS.IN_PROGRESS,
    axes,
    headline: '当前目标推进中',
    summaryForLog,
  }
}

/**
 * 阶段总结（规则）：引用进度与概况，不做模型生成
 * @param {object} opts
 * @param {ReturnType<typeof computeTrainingGoalProgress>} opts.progress
 * @param {ReturnType<typeof computeGoalStatusPack>} opts.statusPack
 * @param {object|null} opts.overview valid_training_overview
 * @param {object} opts.trendHint { lastVsPrevText?, trendClass?, bestTotalStr? } 来自历史页 stats 或简化字段
 */
export function buildStageSummary({ progress, statusPack, overview, trendHint = {} }) {
  const mainProgress = []
  const stillNeed = []
  const g = progress?.goals || {}

  const avg = progress.recentAvgTotal
  const best = progress.bestTotal
  if (avg != null && best != null && best > avg + 1) {
    mainProgress.push(`近期平均总分约 ${avg.toFixed(1)}，历史最好 ${best.toFixed(1)}，说明你曾打出过更高水平。`)
  } else if (avg != null) {
    mainProgress.push(`最近有效训练平均总分约 ${avg.toFixed(1)} 分，可作为下一阶段的参照基线。`)
  }

  if (overview?.overview_ready && overview.recommended_continue_focus) {
    const lab = TRAINING_GOAL_FOCUS_LABEL[overview.recommended_continue_focus] || overview.recommended_continue_focus
    mainProgress.push(`系统近期建议可继续侧重「${lab}」专项。`)
  }

  const lvp = trendHint.lastVsPrevText
  const tc = trendHint.trendClass
  if (lvp && lvp !== '—') {
    mainProgress.push(`列表内总分相对上一场：${lvp}${tc === 'up' ? '，短期有起色。' : '。'}`)
  }

  if (g.target_total_score != null && progress.gapToTarget != null && progress.gapToTarget > 0) {
    stillNeed.push(`总分距离目标还差约 ${progress.gapToTarget.toFixed(1)} 分，建议保持设备与流程完整，多积累有效训练。`)
  }

  if (g.target_valid_session_count != null && progress.validCountProgress) {
    const { current, target } = progress.validCountProgress
    if (current < target) {
      stillNeed.push(`有效训练次数还差 ${target - current} 次，尽量避免无效或中断轮次。`)
    }
  }

  if (g.target_focus && progress.focusBest != null) {
    const lab = TRAINING_GOAL_FOCUS_LABEL[g.target_focus] || g.target_focus
    if (statusPack?.status === GOAL_STATUS.NEAR_COMPLETE || statusPack?.status === GOAL_STATUS.IN_PROGRESS) {
      stillNeed.push(`目标专项「${lab}」当前最好约 ${progress.focusBest.toFixed(1)} 分，可对照弱项反馈继续练同一专项。`)
    }
  }

  if (!mainProgress.length) {
    mainProgress.push('继续完成有效训练后，阶段总结会随着数据变完整而更丰富。')
  }
  if (!stillNeed.length && statusPack?.status !== GOAL_STATUS.ACHIEVED) {
    stillNeed.push('可关注历史页趋势与分项，找出下一轮最划算的练习重点。')
  }
  if (statusPack?.status === GOAL_STATUS.ACHIEVED) {
    stillNeed.length = 0
    stillNeed.push('本阶段目标已对齐，若要继续进步，可提高总分目标或切换到下一专项。')
  }

  let nextKey = 'continue_current'
  let nextLabel = '建议继续按当前目标完成有效训练，再回顾首页进度。'
  if (statusPack?.status === GOAL_STATUS.ACHIEVED) {
    nextKey = 'raise_or_switch'
    nextLabel = '建议：在首页「调整训练目标」提高总分/次数，或切换目标专项；也可先巩固当前强项。'
  } else if (statusPack?.status === GOAL_STATUS.NEAR_COMPLETE) {
    nextKey = 'finish_push'
    nextLabel = '建议：再安排 1～2 次完整有效训练，冲刺当前阶段目标。'
  }

  return {
    mainProgress,
    stillNeed,
    nextSuggestion: { key: nextKey, label: nextLabel },
  }
}

/**
 * Result 页：基于「当前会话已写入后的 progress」与 status
 */
export function buildResultGoalStatusReminder(progress, statusPack) {
  const lines = []
  const nextAction = { key: 'continue', label: '' }
  const g = progress?.goals || {}

  if (!hasActiveTrainingGoals(g)) {
    return { lines, status: null, nextAction }
  }

  const st = statusPack?.status
  if (st === GOAL_STATUS.ACHIEVED) {
    lines.push('恭喜：按当前规则判断，你已完成本阶段设定的训练目标。')
    nextAction.key = 'adjust_or_consolidate'
    nextAction.label = '下一步可在首页调整更高目标，或用同专项再做巩固训练。'
  } else if (st === GOAL_STATUS.NEAR_COMPLETE) {
    lines.push('当前阶段目标已接近达成，再坚持少量有效训练有望收尾。')
    nextAction.key = 'one_more_push'
    nextAction.label = '建议尽快再完成一轮流程完整的有效训练。'
  } else if (st === GOAL_STATUS.IN_PROGRESS) {
    if (
      g.target_total_score != null &&
      progress.gapToTarget != null &&
      progress.gapToTarget > 0 &&
      progress.gapToTarget <= TOTAL_NEAR_GAP_MAX
    ) {
      lines.push('本轮训练后，你已更接近当前总分目标。')
    } else {
      lines.push('本轮已计入进度，当前阶段目标仍在推进中。')
    }
    nextAction.key = 'keep_going'
    nextAction.label = '建议继续按目标完成有效训练，并关注分项反馈。'
  } else if (st === GOAL_STATUS.NOT_STARTED) {
    lines.push('目标已设，有效训练积累较少，本轮有助于正式启动阶段计划。')
    nextAction.key = 'build_habit'
    nextAction.label = '建议先稳定完成几次有效训练，再看首页进度曲线。'
  }

  const totalAxis = statusPack?.axes?.find((a) => a.key === 'total')
  if (totalAxis?.state === 'near_complete' && st !== GOAL_STATUS.ACHIEVED) {
    lines.push('总分目标：已非常接近达标线。')
  }
  const countAxis = statusPack?.axes?.find((a) => a.key === 'count')
  if (countAxis?.state === 'achieved') {
    lines.push('你已完成当前设定的有效训练次数目标。')
  } else if (countAxis?.state === 'near_complete') {
    lines.push('有效训练次数：还差最后一次即可达标。')
  }
  const focusAxis = statusPack?.axes?.find((a) => a.key === 'focus')
  if (focusAxis?.state === 'near_complete' && g.target_focus) {
    const lab = TRAINING_GOAL_FOCUS_LABEL[g.target_focus] || g.target_focus
    lines.push(`专项目标「${lab}」已接近达成（按历史最好/总分对照规则）。`)
  }

  return { lines, status: st, nextAction }
}
