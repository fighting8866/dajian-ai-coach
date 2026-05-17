/**
 * 账号级本地存储：key 形如 baseKey + ':' + userId
 * 读取时优先 scoped；若缺失则读 legacy 全局键并在已知 userId 时迁移到 scoped。
 */
import { getAuthUser } from './authSession'

export const USER_SCOPE_SEPARATOR = ':'

export function getUserScopedKey(baseKey, userId) {
  const bk = String(baseKey || '').trim()
  const uid = userId != null && userId !== '' ? String(userId).trim() : ''
  if (!bk) return ''
  if (!uid) return bk
  return `${bk}${USER_SCOPE_SEPARATOR}${uid}`
}

export function getActiveUserId() {
  try {
    const u = getAuthUser()
    if (!u || u.id == null || u.id === '') return null
    return String(u.id)
  } catch {
    return null
  }
}

/**
 * @param {Storage} store
 * @param {string} baseKey
 * @param {string | null | undefined} [userId] 省略则用当前登录用户
 * @param {{ migrateLegacy?: boolean }} [opts]
 */
export function readUserScopedItem(store, baseKey, userId, opts = {}) {
  const migrateLegacy = opts.migrateLegacy !== false
  const uid = userId === undefined ? getActiveUserId() : userId
  const bk = String(baseKey || '').trim()
  if (!bk) return null
  try {
    if (uid) {
      const sk = getUserScopedKey(bk, uid)
      const scoped = store.getItem(sk)
      if (scoped != null) return scoped
      if (!migrateLegacy) return null
      const leg = store.getItem(bk)
      if (leg != null) {
        try {
          store.setItem(sk, leg)
          store.removeItem(bk)
        } catch (_) {}
        return leg
      }
      return null
    }
    return store.getItem(bk)
  } catch {
    return null
  }
}

/**
 * @param {string | null | undefined} [userId] 省略则用当前用户；为 null 时写入 legacy 键（仅降级）
 */
export function writeUserScopedItem(store, baseKey, value, userId) {
  const uid = userId === undefined ? getActiveUserId() : userId
  const bk = String(baseKey || '').trim()
  if (!bk || value === undefined) return
  try {
    const key = uid ? getUserScopedKey(bk, uid) : bk
    store.setItem(key, String(value))
  } catch (_) {}
}

/**
 * @param {boolean} [alsoRemoveLegacy] 同时删除未隔离的全局键（登出清理、显式清除草稿时用）
 */
export function removeUserScopedItem(store, baseKey, userId, alsoRemoveLegacy = false) {
  const uid = userId === undefined ? getActiveUserId() : userId
  const bk = String(baseKey || '').trim()
  if (!bk) return
  try {
    if (uid) {
      store.removeItem(getUserScopedKey(bk, uid))
    }
    if (alsoRemoveLegacy || !uid) {
      store.removeItem(bk)
    }
  } catch (_) {}
}

/** 登出时移除所有 preflight 标记（含历史遗留的无 user 后缀键） */
export function clearAllPreflightOkKeys() {
  const keys = []
  try {
    const toRemove = []
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i)
      if (k && k.startsWith('mianshi_preflight_ok_')) toRemove.push(k)
    }
    for (const k of toRemove) {
      localStorage.removeItem(k)
      keys.push(k)
    }
  } catch (_) {}
  return keys
}
