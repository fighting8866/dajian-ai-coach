/**
 * 目标调整与下一阶段训练规划 V1（规则版，不接模型）
 */

import { hasActiveTrainingGoals, TRAINING_GOAL_FOCUS_LABEL } from './trainingGoals'
import { GOAL_STATUS } from './trainingGoalStatus'
import { computeWeeklyTrainingReview } from './trainingWeeklyReview'

export const NEXT_PLAN_ACTION = {
  CONTINUE_CURRENT_GOAL: 'continue_current_goal',
  RAISE_GOAL: 'raise_goal',
  SWITCH_FOCUS: 'switch_focus',
  BUILD_MORE_SAMPLES: 'build_more_samples',
}

export const NEXT_PLAN_ACTION_LABEL = {
  continue_current_goal: '继续当前目标',
  raise_goal: '提高或刷新目标',
  switch_focus: '切换专项重点',
  build_more_samples: '先积累有效训练',
}

const FOCUS_KEYS = ['language', 'posture', 'qa', 'content']

const DIMS = [
  { key: 'language', field: 'language_score' },
  { key: 'posture', field: 'posture_score' },
  { key: 'content', field: 'content_score' },
  { key: 'qa', field: 'qa_score' },
]

function numOrNull(v) {
  if (v === null || v === undefined || v === '') return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

function isValidTrainingItem(it) {
  return it && it.training_valid !== false
}

function itemTimestampMs(item) {
  const raw = item?.timestamp ?? item?.created_at
  if (raw == null || raw === '') return null
  const t = new Date(raw).getTime()
  return Number.isFinite(t) ? t : null
}

/** 最近若干条有效训练，时间升序 */
function recentValidChronAsc(historyList, maxN = 8) {
  const list = Array.isArray(historyList) ? historyList : []
  const valid = list.filter(isValidTrainingItem)
  valid.sort((a, b) => {
    const tb = itemTimestampMs(b) ?? 0
    const ta = itemTimestampMs(a) ?? 0
    return tb - ta
  })
  const slice = valid.slice(0, Math.max(0, maxN))
  return slice.sort((a, b) => {
    const ta = itemTimestampMs(a) ?? 0
    const tb = itemTimestampMs(b) ?? 0
    return ta - tb
  })
}

function meanField(chron, field) {
  const vals = []
  for (const it of chron) {
    const v = numOrNull(it[field])
    if (v != null) vals.push(v)
  }
  if (!vals.length) return null
  return vals.reduce((s, x) => s + x, 0) / vals.length
}

function focusDeltaHalves(chron, focusKey) {
  const dim = DIMS.find((d) => d.key === focusKey)
  if (!dim || chron.length < 2) return null
  const mid = Math.floor(chron.length / 2)
  const first = chron.slice(0, mid || 1)
  const second = chron.slice(mid || 1)
  const m1 = meanField(first, dim.field)
  const m2 = meanField(second, dim.field)
  if (m1 == null || m2 == null) return null
  return m2 - m1
}

function weakestDimKeyExcluding(chron, excludeKey) {
  let best = null
  let bestAvg = Infinity
  for (const d of DIMS) {
    if (d.key === excludeKey) continue
    const a = meanField(chron, d.field)
    if (a == null) continue
    if (a < bestAvg) {
      bestAvg = a
      best = d.key
    }
  }
  return best
}

function findAxis(axes, key) {
  const ax = Array.isArray(axes) ? axes.find((a) => a.key === key) : null
  return ax || null
}

function focusLabel(k) {
  if (!k) return ''
  const key = String(k).trim().toLowerCase()
  return TRAINING_GOAL_FOCUS_LABEL[key] || key
}

/**
 * @param {{
 *   historyList: any[],
 *   overview?: object | null,
 *   goals: object,
 *   goalProgress: object,
 *   goalStatusPack: object,
 *   rhythmStats?: object | null,
 *   weeklyReview?: object | null,
 *   resultSessionMeta?: { sessionFocus?: string | null, focusTrendKind?: string | null } | null,
 * }} args
 */
export function computeNextTrainingPlan(args) {
  const historyList = args.historyList
  const overview = args.overview ?? null
  const goals = args.goals || {}
  const goalProgress = args.goalProgress || {}
  const goalStatusPack = args.goalStatusPack || {}
  const rhythmStats = args.rhythmStats ?? null
  const meta = args.resultSessionMeta ?? null

  const weeklyReview = args.weeklyReview || computeWeeklyTrainingReview(historyList, { overview, goals })

  const validCount = goalProgress.validSessionCount || 0
  const trendStep = Number(weeklyReview._trend_step) || 0
  const wkN = weeklyReview.weekly_valid_count || 0
  const hasGoals = hasActiveTrainingGoals(goals)
  const status = goalStatusPack.status
  const axes = goalStatusPack.axes || []
  const chron = recentValidChronAsc(historyList, 8)
  const d7 = rhythmStats?.recent_valid_count_7d ?? 0

  const sparseWindow = validCount < 3 || wkN < 2

  if (sparseWindow) {
    return {
      next_plan_action: NEXT_PLAN_ACTION.BUILD_MORE_SAMPLES,
      next_plan_focus: overview?.recommended_continue_focus || null,
      next_plan_reason: 'valid_or_weekly_window_sparse',
      next_plan_user_line:
        '当前有效训练样本还偏少，建议先以每周 2～3 次完整练习把数据攒起来，再谈调目标或换专项。',
      next_plan_action_label: NEXT_PLAN_ACTION_LABEL[NEXT_PLAN_ACTION.BUILD_MORE_SAMPLES],
    }
  }

  if (hasGoals && status === GOAL_STATUS.ACHIEVED) {
    return {
      next_plan_action: NEXT_PLAN_ACTION.RAISE_GOAL,
      next_plan_focus: goals.target_focus || overview?.recommended_continue_focus || null,
      next_plan_reason: 'goal_achieved',
      next_plan_user_line:
        '当前阶段目标已基本达成，建议在首页把总分、次数或专项目标适度抬高一点，给自己新的抓手。',
      next_plan_action_label: NEXT_PLAN_ACTION_LABEL[NEXT_PLAN_ACTION.RAISE_GOAL],
    }
  }

  if (hasGoals && status === GOAL_STATUS.NEAR_COMPLETE) {
    const momentum = trendStep > 0.12 || d7 >= 3
    if (momentum) {
      return {
        next_plan_action: NEXT_PLAN_ACTION.RAISE_GOAL,
        next_plan_focus: goals.target_focus || overview?.recommended_continue_focus || null,
        next_plan_reason: 'near_complete_with_momentum',
        next_plan_user_line:
          '你已非常接近当前目标，且最近练习节奏不错，下一阶段适合把目标略抬高或收紧一点，继续有方向地练。',
        next_plan_action_label: NEXT_PLAN_ACTION_LABEL[NEXT_PLAN_ACTION.RAISE_GOAL],
      }
    }
  }

  if (
    hasGoals &&
    goals.target_focus &&
    validCount >= 4 &&
    status !== GOAL_STATUS.ACHIEVED &&
    FOCUS_KEYS.includes(String(goals.target_focus).trim().toLowerCase())
  ) {
    const tf = String(goals.target_focus).trim().toLowerCase()
    const focusAxis = findAxis(axes, 'focus')
    const axisStrong =
      focusAxis &&
      focusAxis.state !== 'not_applicable' &&
      (focusAxis.state === 'achieved' || focusAxis.state === 'near_complete')
    const fd = focusDeltaHalves(chron, tf)
    const trendUp = String(meta?.focusTrendKind || '').toLowerCase() === 'up'
    const sessionMatchesGoal =
      String(meta?.sessionFocus || '').trim().toLowerCase() === tf ||
      String(meta?.sessionFocus || '').trim() === ''
    const focusImproved = axisStrong || (fd != null && fd >= 0.25) || (trendUp && sessionMatchesGoal)

    const alt = weakestDimKeyExcluding(chron, tf)
    const tfField = DIMS.find((d) => d.key === tf)?.field
    const tfAvg = tfField ? meanField(chron, tfField) : null
    const altField = alt ? DIMS.find((d) => d.key === alt)?.field : null
    const altAvg = altField ? meanField(chron, altField) : null

    const gapOk =
      tfAvg != null &&
      altAvg != null &&
      altAvg <= tfAvg - 3 &&
      alt &&
      FOCUS_KEYS.includes(alt)

    const rec = String(overview?.recommended_continue_focus || '').trim().toLowerCase()
    const recSwitch = rec && FOCUS_KEYS.includes(rec) && rec !== tf && validCount >= 5 && trendStep >= -0.25

    if (focusImproved && (gapOk || recSwitch)) {
      const switchTo = gapOk ? alt : rec
      return {
        next_plan_action: NEXT_PLAN_ACTION.SWITCH_FOCUS,
        next_plan_focus: switchTo,
        next_plan_reason: gapOk ? 'target_focus_improved_other_weak' : 'overview_recommend_differs',
        next_plan_user_line: `「${focusLabel(tf)}」近期已更稳一些，而「${focusLabel(switchTo)}」仍相对拖后腿，下一阶段建议把主专项切到「${focusLabel(switchTo)}」。`,
        next_plan_action_label: NEXT_PLAN_ACTION_LABEL[NEXT_PLAN_ACTION.SWITCH_FOCUS],
      }
    }
  }

  if (!hasGoals) {
    const rf = overview?.recommended_continue_focus || null
    return {
      next_plan_action: NEXT_PLAN_ACTION.CONTINUE_CURRENT_GOAL,
      next_plan_focus: rf,
      next_plan_reason: 'no_goal_follow_overview',
      next_plan_user_line: rf
        ? `你还没设正式目标，可先按总览建议的「${focusLabel(rf)}」方向保持练习，有需要再到首页设一个轻量目标。`
        : '先保持最近的练习节奏，完成几轮后再设一个总分或专项小目标，会更有阶段感。',
      next_plan_action_label: NEXT_PLAN_ACTION_LABEL[NEXT_PLAN_ACTION.CONTINUE_CURRENT_GOAL],
    }
  }

  const tf = goals.target_focus ? focusLabel(goals.target_focus) : '当前组合目标'
  return {
    next_plan_action: NEXT_PLAN_ACTION.CONTINUE_CURRENT_GOAL,
    next_plan_focus: goals.target_focus || overview?.recommended_continue_focus || null,
    next_plan_reason: trendStep < -0.2 ? 'push_with_volatile_trend' : 'steady_push',
    next_plan_user_line:
      trendStep < -0.2
        ? `${tf}仍在推进中，近期分数略有波动，建议先稳住节奏，把同一套动作多练两轮再看是否调目标。`
        : `${tf}仍值得继续推进；保持当前练习频次，把点评里最重要的一条带到下一轮即可。`,
    next_plan_action_label: NEXT_PLAN_ACTION_LABEL[NEXT_PLAN_ACTION.CONTINUE_CURRENT_GOAL],
  }
}

/**
 * 结果页一句话（本轮后）
 * @param {ReturnType<typeof computeNextTrainingPlan>} plan
 * @param {{ trainingValid?: boolean, goalStatus?: string | null, sessionFocus?: string | null, focusTrendKind?: string | null }} ctx
 */
export function buildResultNextPlanHint(plan, ctx = {}) {
  if (!plan || ctx.trainingValid === false) return ''
  const prefix = '本轮后，系统更建议你：'
  let body = plan.next_plan_user_line

  if (ctx.goalStatus === GOAL_STATUS.NEAR_COMPLETE && plan.next_plan_action === NEXT_PLAN_ACTION.RAISE_GOAL) {
    body = '你已经很接近当前目标，下一阶段可以把目标略微抬高一点，并继续保持现在的练习频率。'
  }

  const sf = String(ctx.sessionFocus || '').trim().toLowerCase()
  const trendUp = String(ctx.focusTrendKind || '').toLowerCase() === 'up'
  if (
    plan.next_plan_action === NEXT_PLAN_ACTION.SWITCH_FOCUS &&
    plan.next_plan_focus &&
    trendUp &&
    sf &&
    FOCUS_KEYS.includes(sf)
  ) {
    body = `当前专项本轮趋势向上、更稳了一些，下一阶段可以把训练重点转到「${focusLabel(plan.next_plan_focus)}」上。`
  }

  return `${prefix}${body}`
}

/**
 * 训练页：当前专项是否与规划建议一致（不强制改配置）
 * @param {ReturnType<typeof computeNextTrainingPlan>} plan
 * @param {string | null | undefined} currentFocusKey training_focus 当前值（none 表示常规）
 */
export function buildTrainingPlanAlignHint(plan, currentFocusKey) {
  if (!plan) return ''
  const cf = String(currentFocusKey || 'none').trim().toLowerCase()
  const sug = plan.next_plan_focus ? String(plan.next_plan_focus).trim().toLowerCase() : ''

  if (plan.next_plan_action === NEXT_PLAN_ACTION.BUILD_MORE_SAMPLES) {
    return '下一阶段仍建议先把有效训练次数攒起来；当前选什么模式都可以，只要完整跑通并提交。'
  }

  if (plan.next_plan_action === NEXT_PLAN_ACTION.RAISE_GOAL) {
    return '下一阶段更适合在首页微调目标；本轮训练配置可维持不变，练完再调整也不迟。'
  }

  if (!sug || !FOCUS_KEYS.includes(sug)) return ''

  if (cf === sug) {
    return `当前专项与「下一阶段建议」一致（${focusLabel(sug)}），按这个方向练即可。`
  }
  if (cf === 'none') {
    return `规划建议下一轮以「${focusLabel(sug)}」为主；你当前是常规训练，仍可继续，不必强行切换。`
  }
  return `规划建议下一轮侧重「${focusLabel(sug)}」，与你当前勾选的专项不完全一致；仍可继续本轮，结束后再对齐也不迟。`
}
