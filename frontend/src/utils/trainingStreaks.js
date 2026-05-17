/**
 * 训练节奏与连续练习日 V1（仅统计 training_valid=true，规则版）
 */

import { TRAINING_GOAL_FOCUS_LABEL } from './trainingGoals'

function itemTimestampMs(item) {
  const raw = item?.timestamp ?? item?.created_at
  if (raw == null || raw === '') return null
  const t = new Date(raw).getTime()
  return Number.isFinite(t) ? t : null
}

function localDateKeyFromMs(ms) {
  const d = new Date(ms)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function todayLocalDateKey() {
  return localDateKeyFromMs(Date.now())
}

function addDaysToKey(key, deltaDays) {
  const [y, m, d] = key.split('-').map(Number)
  const dt = new Date(y, m - 1, d + deltaDays)
  return localDateKeyFromMs(dt.getTime())
}

function isValidTrainingItem(it) {
  return it && it.training_valid !== false
}

/**
 * @param {any[]} historyList
 * @param {{ goalStatus?: string | null, targetFocus?: string | null, countRemaining?: number | null }} [opts]
 */
export function computeTrainingRhythm(historyList, opts = {}) {
  const list = Array.isArray(historyList) ? historyList : []
  const valid = list.filter(isValidTrainingItem)

  const daySet = new Set()
  for (const it of valid) {
    const ms = itemTimestampMs(it)
    if (ms == null) continue
    daySet.add(localDateKeyFromMs(ms))
  }

  const today = todayLocalDateKey()
  const yesterday = addDaysToKey(today, -1)

  let streak_days = 0
  let streak_anchor = null
  if (daySet.has(today)) streak_anchor = today
  else if (daySet.has(yesterday)) streak_anchor = yesterday

  if (streak_anchor) {
    let d = streak_anchor
    while (daySet.has(d)) {
      streak_days++
      d = addDaysToKey(d, -1)
    }
  }

  const today_done = daySet.has(today)
  let today_valid_sessions_count = 0
  for (const it of valid) {
    const ms = itemTimestampMs(it)
    if (ms == null) continue
    if (localDateKeyFromMs(ms) === today) today_valid_sessions_count++
  }

  const windowStart7 = addDaysToKey(today, -6)
  const windowStart14 = addDaysToKey(today, -13)

  let recent_valid_count_7d = 0
  let recent_valid_count_14d = 0
  for (const it of valid) {
    const ms = itemTimestampMs(it)
    if (ms == null) continue
    const k = localDateKeyFromMs(ms)
    if (k >= windowStart7 && k <= today) recent_valid_count_7d++
    if (k >= windowStart14 && k <= today) recent_valid_count_14d++
  }

  const sortedDays = [...daySet].sort()
  const last_training_day_key = sortedDays.length ? sortedDays[sortedDays.length - 1] : null

  const rhythm_gap =
    daySet.size > 0 &&
    !daySet.has(today) &&
    !daySet.has(yesterday) &&
    last_training_day_key != null &&
    last_training_day_key < yesterday

  const goalStatus = opts.goalStatus ?? null
  const countRemaining =
    opts.countRemaining != null && Number.isFinite(opts.countRemaining) ? opts.countRemaining : null
  const targetFocus = opts.targetFocus || null

  const next_training_hint = buildNextTrainingHint({
    today_done,
    streak_days,
    goalStatus,
    countRemaining,
    targetFocus,
    rhythm_gap,
    recent_valid_count_7d,
  })

  return {
    streak_days,
    recent_valid_count_7d,
    recent_valid_count_14d,
    today_done,
    today_valid_sessions_count,
    rhythm_gap,
    last_training_day_key,
    total_valid_sessions: valid.length,
    distinct_valid_days: daySet.size,
    next_training_hint,
  }
}

function buildNextTrainingHint({
  today_done,
  streak_days,
  goalStatus,
  countRemaining,
  targetFocus,
  rhythm_gap,
  recent_valid_count_7d,
}) {
  const focusLab = targetFocus ? TRAINING_GOAL_FOCUS_LABEL[targetFocus] || targetFocus : ''

  if (rhythm_gap) {
    return '最近练习节奏有过间隔，建议在日程允许时恢复规律的有效训练，更有利于稳定提升。'
  }

  if (!today_done) {
    if (recent_valid_count_7d < 2) {
      return '今日尚未记录有效训练；最近一周有效练习偏少，建议在日程允许时尽快完成一轮。'
    }
    if (goalStatus === 'near_complete' || goalStatus === 'achieved') {
      return '今日尚未记录有效训练；若仍想推进或巩固目标，可在方便时完成一轮完整练习。'
    }
    return '今日尚未记录有效训练，建议在方便时完成一轮有效练习，保持连续节奏。'
  }

  if (goalStatus === 'achieved') {
    return '今日已完成有效训练；阶段目标已对齐时，可休息或改练其他专项做巩固。'
  }
  if (goalStatus === 'near_complete') {
    const extra = focusLab ? `可继续侧重「${focusLab}」方向。` : '可延续当前目标方向。'
    return `今日已完成有效训练；目标已较近，明日若有余力建议再安排一轮，${extra}`
  }
  if (streak_days >= 3 && (goalStatus === 'in_progress' || goalStatus === 'not_started')) {
    return '已连续多日完成有效训练，节奏很好；明日可继续当前目标方向，或穿插巩固弱项。'
  }
  const tail =
    countRemaining != null && countRemaining > 0
      ? `阶段目标还差 ${countRemaining} 次有效训练，可按周分摊练习。`
      : '明日可继续按首页目标推进，不必急于求成。'
  return `今日已完成有效训练；${tail}`
}

export function buildHomeRhythmLines(stats, goalProgress) {
  const lines = []
  if (!stats || (stats.total_valid_sessions || 0) === 0) {
    lines.push('暂时还没有有效训练记录；完成首轮完整练习后，这里会汇总你的练习节奏。')
    return lines
  }

  lines.push(
    `最近连续有效练习日：${stats.streak_days} 天（按本地自然日，同一天多次练习仍计为 1 天）。`
  )
  lines.push(
    `最近 7 天累计 ${stats.recent_valid_count_7d} 次有效训练，最近 14 天 ${stats.recent_valid_count_14d} 次。`
  )
  if (stats.today_done) {
    const n = stats.today_valid_sessions_count || 1
    lines.push(
      n > 1
        ? `今日已完成 ${n} 次有效训练，可适当休息或换专项巩固。`
        : '今日已完成有效训练，可视状态安排巩固或休息。'
    )
  } else {
    lines.push('今日尚未记录有效训练。')
  }

  if (stats.next_training_hint) {
    lines.push(stats.next_training_hint)
  }

  if (goalProgress?.validCountProgress) {
    const { current, target } = goalProgress.validCountProgress
    const rem = target - current
    if (rem > 0) {
      lines.push(`阶段次数目标还差 ${rem} 次；若按一周为一个安排周期，可把剩余次数匀到本周后续几天。`)
    }
  }

  return lines
}

export function buildHistoryRhythmSummaryLines(stats) {
  if (!stats || (stats.total_valid_sessions || 0) === 0) {
    return []
  }
  return [
    `最近 7 天：${stats.recent_valid_count_7d} 次有效训练`,
    `当前连续有效练习日：${stats.streak_days} 天`,
  ]
}

export function buildResultRhythmLines(stats, opts = {}) {
  const { goalStatus = null, targetFocus = null } = opts
  const lines = []
  if (!stats || (stats.total_valid_sessions || 0) === 0) return lines

  const focusLab = targetFocus ? TRAINING_GOAL_FOCUS_LABEL[targetFocus] || targetFocus : ''

  if (stats.today_done) {
    const n = stats.today_valid_sessions_count || 1
    lines.push(n > 1 ? `你今天已完成 ${n} 次有效训练。` : '你今天已完成有效训练。')
  }
  if (stats.streak_days > 0) {
    lines.push(`当前已连续 ${stats.streak_days} 个自然日保持有效练习。`)
  }
  if (stats.today_done && goalStatus && goalStatus !== 'achieved') {
    lines.push(
      focusLab
        ? `建议明日继续朝当前目标方向练习，可延续「${focusLab}」专项。`
        : '建议明日继续按首页目标方向练习。'
    )
  } else if (stats.today_done && goalStatus === 'achieved') {
    lines.push('阶段目标已达成时，明日可巩固或调整新的练习重点。')
  }

  return lines
}

export function buildTrainingRhythmHintLines(stats) {
  const lines = []
  if (!stats) return lines
  if (stats.today_done) {
    lines.push('今日已完成有效训练；本轮可继续巩固，或改练其他专项，不必重复刷量。')
  }
  if (stats.rhythm_gap) {
    lines.push('最近练习节奏有过中断，恢复规律有效训练会更有帮助。')
  }
  return lines
}
