/**
 * 比赛现场演示精简模式（仅展示层，sessionStorage；不影响训练/评分逻辑）
 */
import { getActiveUserId, readUserScopedItem, writeUserScopedItem, removeUserScopedItem } from './userScopedStorage'

export const DEMO_MODE_STORAGE_KEY = 'mianshi_demo_mode_v1'

export function readDemoMode() {
  const uid = getActiveUserId()
  try {
    const raw = readUserScopedItem(sessionStorage, DEMO_MODE_STORAGE_KEY, uid, { migrateLegacy: true })
    if (!raw) return { active: false, presetActive: false }
    const o = JSON.parse(raw)
    return {
      active: o.active === true,
      presetActive: o.presetActive === true,
    }
  } catch {
    return { active: false, presetActive: false }
  }
}

/** 进入演示精简态；presetActive 不传则保留已有预设标记 */
export function enterDemoMode(opts = {}) {
  const uid = getActiveUserId()
  const cur = readDemoMode()
  let preset = cur.presetActive === true
  if (opts.presetActive === true) preset = true
  if (opts.presetActive === false) preset = false
  const next = { active: true, presetActive: preset }
  try {
    writeUserScopedItem(sessionStorage, DEMO_MODE_STORAGE_KEY, JSON.stringify(next), uid)
  } catch (_) {}
}

export function exitDemoMode() {
  const uid = getActiveUserId()
  try {
    removeUserScopedItem(sessionStorage, DEMO_MODE_STORAGE_KEY, uid, true)
  } catch (_) {}
}

/**
 * 从路由查询激活（显式优先）。返回是否已激活。
 * demo_preset=1 会同时置 presetActive。
 */
export function activateDemoModeFromRouteQuery(query) {
  if (!query || typeof query !== 'object') return false
  const dm = String(query.demo_mode || '').trim().toLowerCase()
  const dp = String(query.demo_preset || '').trim().toLowerCase()
  if (dm === '1' || dm === 'true') {
    enterDemoMode({ presetActive: dp === '1' || dp === 'true' })
    return true
  }
  if (dp === '1' || dp === 'true') {
    enterDemoMode({ presetActive: true })
    return true
  }
  return false
}

export function stripDemoQueryKeys(query = {}) {
  const q = { ...query }
  delete q.demo_mode
  delete q.demo_preset
  return q
}
