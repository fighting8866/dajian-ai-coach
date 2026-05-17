/**
 * 与 Report.vue 中 resolvedSessionId 相同口径，用于：
 * - 路由进入报告页前是否有可打开报告的会话上下文
 * - 侧栏「报告」是否可点
 */
import { readUserScopedItem } from './userScopedStorage'
import { CURRENT_SESSION_ID_KEY } from './appPreferences'

export function normalizeRouteParamId(val) {
  if (val == null) return ''
  if (Array.isArray(val)) return normalizeRouteParamId(val[0])
  return String(val).trim()
}

/**
 * 从「路由 to」与 localStorage 解析 session id（与 Report 页内逻辑一致，不含回退逻辑以外的差异）
 * @param {{ params?: object, query?: object }} to
 * @returns {string}
 */
export function resolveReportRouteSessionId(to) {
  if (!to) return ''
  const p = normalizeRouteParamId(to.params?.sessionId)
  if (p) return p
  const q1 = normalizeRouteParamId(to.query?.session_id)
  if (q1) return q1
  const q2 = normalizeRouteParamId(to.query?.sessionId)
  if (q2) return q2
  return normalizeRouteParamId(
    readUserScopedItem(localStorage, CURRENT_SESSION_ID_KEY, undefined, { migrateLegacy: true })
  )
}
