/**
 * 训练周报与阶段复盘 V1（规则版，仅 training_valid !== false）
 */

import { todayLocalDateKey } from './trainingStreaks'
import { hasActiveTrainingGoals } from './trainingGoals'
import { TRAINING_FOCUS_LABEL, trainingFocusLabel, TRAINING_GOAL_FOCUS_LABEL } from '../constants/productTerms'

const FALLBACK_LAST_N = 8
const MIN_SAMPLES_STAY_7D = 2

const FOCUS_KEYS = ['language', 'posture', 'qa', 'content']

const DIM_SPECS = [
  { key: 'language', field: 'language_score', label: TRAINING_FOCUS_LABEL.language },
  { key: 'posture', field: 'posture_score', label: TRAINING_FOCUS_LABEL.posture },
  { key: 'content', field: 'content_score', label: TRAINING_FOCUS_LABEL.content },
  { key: 'qa', field: 'qa_score', label: TRAINING_FOCUS_LABEL.qa },
]

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

function addDaysToKey(key, deltaDays) {
  const [y, mo, da] = key.split('-').map(Number)
  const dt = new Date(y, mo - 1, da + deltaDays)
  return localDateKeyFromMs(dt.getTime())
}

function isValidTrainingItem(it) {
  return it && it.training_valid !== false
}

function numOrNull(v) {
  if (v === null || v === undefined || v === '') return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

function focusLabel(k) {
  return trainingFocusLabel(k)
}

function sortValidDesc(list) {
  const out = list.filter(isValidTrainingItem)
  out.sort((a, b) => {
    const ta = itemTimestampMs(a) ?? 0
    const tb = itemTimestampMs(b) ?? 0
    return tb - ta
  })
  return out
}

/**
 * @param {any[]} historyList
 * @param {{ overview?: object | null, goals?: object | null }} [opts]
 */
function emptyWeeklyReviewFallback() {
  return {
    weekly_valid_count: 0,
    weekly_window_mode: '7d',
    weekly_window_note: '',
    weekly_focus_distribution: { language: 0, posture: 0, qa: 0, content: 0, none: 0 },
    weekly_focus_distribution_text: '—',
    weekly_trend_summary: '—',
    weekly_progress_highlight: '—',
    weekly_attention_point: '—',
    weekly_next_focus: '—',
    stage_one_liner: '',
    _trend_step: 0,
    _trend_delta: 0,
  }
}

export function computeWeeklyTrainingReview(historyList, opts = {}) {
  try {
    return _computeWeeklyTrainingReviewCore(historyList, opts)
  } catch (e) {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.warn('[computeWeeklyTrainingReview] degraded:', e)
    }
    return emptyWeeklyReviewFallback()
  }
}

function _computeWeeklyTrainingReviewCore(historyList, opts = {}) {
  const overview = opts.overview ?? null
  const goals = opts.goals ?? null

  const allDesc = sortValidDesc(Array.isArray(historyList) ? historyList : [])
  const today = todayLocalDateKey()
  const winStart = addDaysToKey(today, -6)

  const in7dDesc = allDesc.filter((it) => {
    const ms = itemTimestampMs(it)
    if (ms == null) return false
    const k = localDateKeyFromMs(ms)
    return k >= winStart && k <= today
  })

  let windowMode = '7d'
  let windowNote = ''
  let workingDesc = in7dDesc

  if (in7dDesc.length < MIN_SAMPLES_STAY_7D && allDesc.length) {
    windowMode = 'last_n'
    const n = Math.min(FALLBACK_LAST_N, allDesc.length)
    workingDesc = allDesc.slice(0, n)
    windowNote =
      in7dDesc.length === 0
        ? '近 7 天暂无有效训练记录，以下按最近几次有效训练汇总。'
        : '近 7 天有效训练偏少，以下已并入更早的有效训练一起观察趋势。'
  }

  /** 时间升序，便于看走势 */
  const chron = [...workingDesc].sort((a, b) => {
    const ta = itemTimestampMs(a) ?? 0
    const tb = itemTimestampMs(b) ?? 0
    return ta - tb
  })

  const weekly_valid_count = chron.length

  const dist = {}
  for (const k of FOCUS_KEYS) dist[k] = 0
  dist.none = 0
  for (const it of chron) {
    const fk = String(it.training_focus || 'none').trim().toLowerCase()
    if (fk in dist) dist[fk]++
    else dist.none++
  }

  const weekly_focus_distribution = { ...dist }

  const distPairs = FOCUS_KEYS.map((k) => ({ k, n: dist[k] || 0 }))
    .filter((p) => p.n > 0)
    .sort((a, b) => b.n - a.n)

  let weekly_focus_distribution_text = '本周以综合训练为主，尚未固定某一专项。'
  if (distPairs.length) {
    weekly_focus_distribution_text = distPairs
      .slice(0, 3)
      .map((p) => `${focusLabel(p.k)}×${p.n}`)
      .join('、')
  }

  const totals = chron.map((it) => numOrNull(it.total_score)).filter((v) => v != null)
  let weekly_trend_summary = '先完成一两轮有效训练后，这里会总结总分走势。'
  let trendDelta = 0
  let trendStep = 0
  if (totals.length >= 2) {
    const first = totals[0]
    const last = totals[totals.length - 1]
    trendDelta = last - first
    trendStep = trendDelta / (totals.length - 1)
    const scope =
      windowMode === '7d'
        ? `最近 7 天内 ${weekly_valid_count} 次有效训练`
        : `最近 ${weekly_valid_count} 次有效训练`
    if (trendStep > 0.35) {
      weekly_trend_summary = `${scope}里，总分整体在往上走，值得保持当前练法。`
    } else if (trendStep < -0.35) {
      weekly_trend_summary = `${scope}里，总分略有承压，不妨回顾最近几轮的点评重点，下一轮放慢节奏抠细节。`
    } else {
      weekly_trend_summary = `${scope}里，总分大致平稳，适合在稳定输出的基础上挑最弱的一项做专项突破。`
    }
  } else if (totals.length === 1) {
    weekly_trend_summary =
      windowMode === '7d'
        ? '近 7 天只有一次有效训练样本，建议再练 1～2 轮，更容易看出趋势。'
        : '当前只有一次有效训练样本，建议再练 1～2 轮，更容易看出趋势。'
  }

  const dimStats = buildDimSplitMeans(chron)
  const weekly_progress_highlight = pickProgressHighlight(chron, dimStats, trendStep)
  const weekly_attention_point = pickAttention(chron, dimStats, overview, goals)

  const weekly_next_focus = pickNextFocus({
    weekly_valid_count,
    trendStep,
    dimStats,
    overview,
    goals,
    distPairs,
    chron,
  })

  const stage_one_liner = buildStageOneLiner({
    trendStep,
    totalsLen: totals.length,
  })

  return {
    weekly_valid_count,
    weekly_window_mode: windowMode,
    weekly_window_note: windowNote,
    weekly_focus_distribution,
    weekly_focus_distribution_text,
    weekly_trend_summary,
    weekly_progress_highlight,
    weekly_attention_point,
    weekly_next_focus,
    stage_one_liner,
    _trend_step: trendStep,
    _trend_delta: trendDelta,
  }
}

function buildDimSplitMeans(chron) {
  const mid = Math.floor(chron.length / 2)
  const firstHalf = chron.slice(0, mid || 1)
  const secondHalf = chron.slice(mid || 1)
  const out = {}
  for (const spec of DIM_SPECS) {
    const m1 = meanScores(firstHalf, spec.field)
    const m2 = meanScores(secondHalf, spec.field)
    const all = meanScores(chron, spec.field)
    out[spec.key] = { m1, m2, all, delta: m1 != null && m2 != null ? m2 - m1 : null, spec }
  }
  return out
}

function meanScores(items, field) {
  const vals = []
  for (const it of items) {
    const v = numOrNull(it[field])
    if (v != null) vals.push(v)
  }
  if (!vals.length) return null
  return vals.reduce((s, x) => s + x, 0) / vals.length
}

function pickProgressHighlight(chron, dimStats, trendStep) {
  if (chron.length < 2) {
    return '先把最近一轮的反馈吃透，下一轮带着一个小目标开始训练，更容易看到进步。'
  }
  let bestKey = null
  let bestDelta = -Infinity
  for (const k of Object.keys(dimStats)) {
    const d = dimStats[k].delta
    if (d != null && d > bestDelta) {
      bestDelta = d
      bestKey = k
    }
  }
  if (bestKey && bestDelta >= 0.4) {
    const lab = dimStats[bestKey].spec.label
    return `分项里「${lab}」相较本阶段前半段更稳、更好，是最近最明显的进步点。`
  }
  if (trendStep > 0.35) {
    return '总分在抬升，说明整体表达与临场状态在往好的方向积累。'
  }
  const upFocus = [...chron].reverse().find((it) => String(it.focus_trend_kind || '').toLowerCase() === 'up')
  if (upFocus) {
    const fk = String(upFocus.training_focus || 'none').toLowerCase()
    if (FOCUS_KEYS.includes(fk)) {
      return `「${focusLabel(fk)}」专项在最近一轮的趋势标记为向上，说明针对性练习开始见效。`
    }
  }
  if (chron.length >= 3 && trendStep >= -0.15) {
    return '分数没有大起大落，说明发挥正在变稳定，适合在稳定之上做专项补强。'
  }
  return '继续保持固定节奏练习，把点评里的 1～2 条动作带到下一轮，进步会慢慢显出来。'
}

function pickAttention(chron, dimStats, overview, goals) {
  const volatileLines = []
  const volByFocus = {}
  for (const it of chron) {
    if (String(it.focus_trend_kind || '').toLowerCase() !== 'volatile') continue
    const fk = String(it.training_focus || 'none').toLowerCase()
    if (!FOCUS_KEYS.includes(fk)) continue
    volByFocus[fk] = (volByFocus[fk] || 0) + 1
  }
  for (const fk of Object.keys(volByFocus)) {
    if (volByFocus[fk] >= 2) {
      volatileLines.push(`「${focusLabel(fk)}」专项多次出现波动，需要多练几次把它练稳。`)
    }
  }
  if (volatileLines.length) return volatileLines[0]

  let weakest = null
  let weakestAvg = Infinity
  for (const k of Object.keys(dimStats)) {
    const a = dimStats[k].all
    if (a == null) continue
    if (a < weakestAvg) {
      weakestAvg = a
      weakest = dimStats[k].spec
    }
  }
  if (weakest) {
    return `从分项均值看，「${weakest.label}」仍相对偏弱，下一阶段最值得多花一点时间。`
  }

  const g = goals && typeof goals === 'object' ? goals : null
  if (g && g.target_total_score != null) {
    const T = Number(g.target_total_score)
    let best = null
    for (const it of chron) {
      const t = numOrNull(it.total_score)
      if (t == null) continue
      if (best == null || t > best) best = t
    }
    if (best != null && best + 0.05 < T) {
      return `距离你设定的目标总分还有一点空间，建议下一轮把「抓分点」写在小纸条上提醒自己。`
    }
  }

  if (overview?.recommended_continue_focus && FOCUS_KEYS.includes(String(overview.recommended_continue_focus))) {
    const lab = focusLabel(overview.recommended_continue_focus)
    return `结合近期表现，系统仍建议优先巩固「${lab}」，避免短板拖后腿。`
  }

  return '留意每一轮里最容易被点评点名的环节，下一轮刻意练一次「慢下来、说清楚」。'
}

function pickNextFocus({
  weekly_valid_count,
  trendStep,
  dimStats,
  overview,
  goals,
  distPairs,
  chron,
}) {
  if (weekly_valid_count < 3) {
    return '先把有效训练次数积累起来：尽量本周再完成 2～3 次完整练习，周报会更准、建议也更稳。'
  }

  const g = goals && typeof goals === 'object' ? goals : {}
  const hasGoals = hasActiveTrainingGoals(g)
  const goalFk = g.target_focus && FOCUS_KEYS.includes(String(g.target_focus)) ? String(g.target_focus) : null

  if (goalFk) {
    const d = dimStats[goalFk]
    const improving = d?.delta != null && d.delta >= 0.35
    if (!improving) {
      const lab =
        (TRAINING_GOAL_FOCUS_LABEL && TRAINING_GOAL_FOCUS_LABEL[goalFk]) || focusLabel(goalFk) || String(goalFk)
      return `你正在追「${lab}」目标，建议下一轮继续以该专项为主，练到分数波动明显变小为止。`
    }
  }

  const rec = overview?.recommended_continue_focus
  if (rec && FOCUS_KEYS.includes(String(rec))) {
    const sameRecCount = chron.filter((it) => String(it.training_focus || '').toLowerCase() === String(rec)).length
    const weakImproving =
      dimStats[String(rec)]?.delta != null && dimStats[String(rec)].delta >= 0.25
    if (sameRecCount >= 2 && !weakImproving) {
      return `「${focusLabel(rec)}」已连续多轮出现，建议继续沿用同一专项，把动作练成肌肉记忆。`
    }
  }

  if (trendStep > 0.45 && distPairs.length) {
    const top = distPairs[0].k
    let secondWeakest = null
    let secondAvg = Infinity
    for (const spec of DIM_SPECS) {
      if (spec.key === top) continue
      const a = dimStats[spec.key]?.all
      if (a != null && a < secondAvg) {
        secondAvg = a
        secondWeakest = spec
      }
    }
    if (secondWeakest) {
      return `主专项已有起色，下一阶段可以把一部分时间分给「${secondWeakest.label}」，让整体更均衡。`
    }
  }

  let weakest = null
  let weakestAvg = Infinity
  for (const spec of DIM_SPECS) {
    const a = dimStats[spec.key]?.all
    if (a != null && a < weakestAvg) {
      weakestAvg = a
      weakest = spec
    }
  }
  if (weakest) {
    return `建议下一轮以「${weakest.label}」为优先突破口，配合一轮专项训练更容易看到分数变化。`
  }

  if (hasGoals) {
    return '围绕当前训练目标继续安排练习：保持节奏，比单纯追高分更重要。'
  }
  return '保持当前练习频率，并在每轮结束后用一分钟对照点评记下一条改进点。'
}

function buildStageOneLiner({ trendStep, totalsLen }) {
  if (totalsLen < 1) return ''
  if (totalsLen < 2) return '样本还在积累中，下一轮带着一个小目标练，更容易看到变化。'
  if (trendStep > 0.35) return '整体状态向上，说明最近的练习节奏和方法开始见效。'
  if (trendStep < -0.35) return '最近略有起伏，适合放慢节奏，把基本功再打牢一点。'
  return '发挥比较稳定，可以把精力集中到最常被点评点名的弱项上。'
}

/** @param {ReturnType<typeof computeWeeklyTrainingReview>} r */
export function buildHomeWeeklyDisplayLines(r) {
  if (!r || !r.weekly_valid_count) return []
  const lines = []
  const countLine =
    r.weekly_window_mode === '7d'
      ? `最近 7 天有效训练 ${r.weekly_valid_count} 次。`
      : `最近 ${r.weekly_valid_count} 次有效训练（已扩展统计窗口）。`
  lines.push(countLine)
  if (r.weekly_window_note) lines.push(r.weekly_window_note)
  lines.push(`最近主要训练重点：${r.weekly_focus_distribution_text}。`)
  if (r.stage_one_liner) lines.push(`当前阶段：${r.stage_one_liner}`)
  lines.push(`下一阶段建议：${r.weekly_next_focus}`)
  return lines
}

/** @param {ReturnType<typeof computeWeeklyTrainingReview>} r */
export function buildHistoryStageReviewLines(r) {
  if (!r || !r.weekly_valid_count) return []
  const lines = []
  if (r.weekly_window_note) lines.push(r.weekly_window_note)
  lines.push(`整体趋势：${r.weekly_trend_summary}`)
  lines.push(`最近进步点：${r.weekly_progress_highlight}`)
  lines.push(`待改进点：${r.weekly_attention_point}`)
  lines.push(`下一阶段：${r.weekly_next_focus}`)
  return lines
}

/**
 * @param {{ trainingValid: boolean, hasGoals: boolean }} args
 */
export function buildResultWeeklyAccumulationHint({ trainingValid, hasGoals }) {
  if (trainingValid === false) return ''
  if (hasGoals) return '本轮结果已计入你的阶段统计，并会更新当前训练目标的进度。'
  return '本轮有效训练已计入首页与历史的本周训练摘要，便于你回顾阶段性变化。'
}
