/**
 * Result 页首屏「较上次有效训练」变化摘要：纯展示用，不修改评分与接口。
 * 对比基准：在 /history 列表中、training_valid 非 false、且非当前 session 的条目中，按时间选「上一次」有效训练。
 */

import { SCORE_DIM_SHORT } from '../constants/productTerms'

function timeMsFromRow(row) {
  if (!row || typeof row !== 'object') return 0
  const s = String(row.timestamp || row.created_at || '').trim()
  if (!s) return 0
  const ms = Date.parse(s)
  return Number.isFinite(ms) ? ms : 0
}

function timeMsFromResult(r) {
  if (!r || typeof r !== 'object') return 0
  const s = String(r.timestamp || r.created_at || '').trim()
  if (!s) return 0
  const ms = Date.parse(s)
  return Number.isFinite(ms) ? ms : 0
}

function numOrNull(v) {
  if (v == null || v === '') return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

const DIMS = [
  { key: 'language', field: 'language_score' },
  { key: 'posture', field: 'posture_score' },
  { key: 'content', field: 'content_score' },
  { key: 'qa', field: 'qa_score' },
]

/**
 * @param {object} opts
 * @param {boolean} opts.trainingValid
 * @param {string} opts.sessionId
 * @param {object|null} opts.result
 * @param {Array} opts.historyList
 * @returns {{ show: boolean, titleLine: string, detailLine: string, tone: string }|null}
 */
export function buildResultCompareSummary({ trainingValid, sessionId, result, historyList }) {
  if (trainingValid === false) {
    return { show: false, titleLine: '', detailLine: '', tone: 'invalid' }
  }
  if (!result || typeof result !== 'object') {
    return { show: false, titleLine: '', detailLine: '', tone: 'empty' }
  }

  const curTotal = numOrNull(result.total_score)
  if (curTotal == null) {
    return { show: false, titleLine: '', detailLine: '', tone: 'empty' }
  }

  const sid = String(sessionId || '').trim()
  const list = Array.isArray(historyList) ? historyList : []
  const others = list.filter((it) => {
    if (!it || typeof it !== 'object') return false
    if (it.training_valid === false) return false
    const id = String(it.session_id || '').trim()
    if (!id || id === sid) return false
    return true
  })

  if (others.length === 0) {
    return {
      show: true,
      titleLine: '这是你在本账号上可参与统计的一次有效训练；后续多练几轮后，将可与上一次作分数对照。',
      detailLine: '',
      tone: 'first',
    }
  }

  const curMs = timeMsFromResult(result)
  let prev = null
  if (curMs > 0) {
    const before = others
      .map((it) => ({ it, t: timeMsFromRow(it) }))
      .filter((x) => x.t > 0 && x.t < curMs)
    before.sort((a, b) => b.t - a.t)
    prev = before[0]?.it || null
  }
  if (!prev) {
    const sorted = others.map((it) => ({ it, t: timeMsFromRow(it) })).sort((a, b) => b.t - a.t)
    prev = sorted[0]?.it || null
  }

  if (!prev) {
    return {
      show: true,
      titleLine: '这是你在本账号上可参与统计的一次有效训练；后续多练几轮后，将可与上一次作分数对照。',
      detailLine: '',
      tone: 'first',
    }
  }

  const prevTotal = numOrNull(prev.total_score)
  if (prevTotal == null) {
    return {
      show: true,
      titleLine: '这是你在本账号上可参与统计的一次有效训练；后续多练几轮后，将可与上一次作分数对照。',
      detailLine: '',
      tone: 'first',
    }
  }

  const rawDelta = curTotal - prevTotal
  const eps = 0.05
  let deltaTone = 'flat'
  if (rawDelta > eps) deltaTone = 'up'
  else if (rawDelta < -eps) deltaTone = 'down'

  const titleLine =
    deltaTone === 'flat'
      ? '较上一次有效训练，总分持平。'
      : `较上一次有效训练，总分约${rawDelta > 0 ? '高' : '低'} ${Math.abs(rawDelta).toFixed(1)} 分。`

  let mostLabel = ''
  const apiHighlights = result.training_focus_metric_highlights
  if (Array.isArray(apiHighlights) && apiHighlights.length) {
    const h0 = String(apiHighlights[0] || '').trim()
    if (h0 && h0.length <= 80) {
      mostLabel = h0
    } else if (h0) {
      mostLabel = `${h0.slice(0, 77)}…`
    }
  }

  if (!mostLabel) {
    let best = { key: 'language', abs: 0, d: 0 }
    for (const { key, field } of DIMS) {
      const a = numOrNull(result[field])
      const b = numOrNull(prev[field])
      if (a == null || b == null) continue
      const d = a - b
      const ad = Math.abs(d)
      if (ad > best.abs + 1e-6) {
        best = { key, abs: ad, d }
      }
    }
    if (best.abs >= 0.15) {
      const lab = SCORE_DIM_SHORT[best.key] || '分项'
      const sign = best.d > 0 ? '高' : '低'
      mostLabel = `${lab}较上次约${sign} ${Math.abs(best.d).toFixed(1)} 分，变化最显眼。`
    }
  }

  if (!mostLabel) {
    const vs = String(result.training_focus_vs_recent || '').trim()
    if (vs && vs.length && vs !== '—' && !/^暂无/.test(vs)) {
      mostLabel = vs.length > 90 ? `${vs.slice(0, 87)}…` : vs
    }
  }

  let conclusion = ''
  if (deltaTone === 'up') conclusion = '整体较上次有进步。'
  else if (deltaTone === 'down') conclusion = '整体较上次略低，可结合下方老师点评对薄弱项多练。'
  else conclusion = '与上次整体接近，可结合下方老师点评看细节。'

  const detailLine = [mostLabel, conclusion].filter(Boolean).join(' ').trim()

  return {
    show: true,
    titleLine,
    detailLine,
    tone: deltaTone,
  }
}
