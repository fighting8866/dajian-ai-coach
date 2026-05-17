/**
 * 全局默认配置与偏好：云端账号同步优先，本地 user-scoped 作缓存兜底（V1）
 */

import {
  getActiveUserId,
  getUserScopedKey,
  readUserScopedItem,
  writeUserScopedItem,
  removeUserScopedItem,
} from './userScopedStorage'

export const APP_PREFERENCES_STORAGE_KEY = 'mianshi_app_preferences_v1'

/** 偏好写入后派发，供训练页等在不刷新时刷新与偏好相关的界面 */
export const APP_PREFERENCES_CHANGED_EVENT = 'mianshi-app-preferences-changed'

/** 与 Training.vue 对齐的键名（仅清理草稿/恢复态，不碰历史与结果） */
export const TRAINING_DRAFT_KEY = 'mianshi_training_page_draft_v1'
export const TRAINING_RUNTIME_SNAPSHOT_KEY = 'mianshi_training_runtime_snapshot_v1'
export const TRAINING_FOCUS_HANDOFF_KEY = 'mianshi_training_focus_v1'
export const CURRENT_SESSION_ID_KEY = 'current_session_id'
export const LAST_PPT_ID_STORAGE_KEY = 'mianshi_training_last_ppt_id'

/** 将当前会话 id 写入账号级 localStorage，供 Result/Report 无 params/query 时兜底 */
export function persistCurrentSessionId(sessionId) {
  const s = String(sessionId || '').trim()
  if (!s) return
  try {
    writeUserScopedItem(localStorage, CURRENT_SESSION_ID_KEY, s)
  } catch (_) {}
}

export const PREFS_DEFAULTS = Object.freeze({
  v: 1,
  scoring_profile: 'defense',
  defense_material_mode: 'with_ppt',
  history_valid_only_default: true,
  show_first_time_hints: true,
  show_recent_valid_reminder: true,
})

/** 登录后由 accountSettingsSync 写入；未 hydrated 前为 null */
let _serverPrefsOverlay = null

export function normalizePrefs(raw) {
  const o = raw && typeof raw === 'object' ? raw : {}
  return {
    v: 1,
    scoring_profile: o.scoring_profile === 'interview' ? 'interview' : 'defense',
    defense_material_mode: o.defense_material_mode === 'without_ppt' ? 'without_ppt' : 'with_ppt',
    history_valid_only_default: o.history_valid_only_default !== false,
    show_first_time_hints: o.show_first_time_hints !== false,
    show_recent_valid_reminder: o.show_recent_valid_reminder !== false,
  }
}

/**
 * 仅从本地读（不经过云端 overlay），用于首次登录迁移判断
 */
export function readAppPreferencesLocalOnly() {
  const uid = getActiveUserId()
  try {
    const raw = readUserScopedItem(localStorage, APP_PREFERENCES_STORAGE_KEY, uid, {
      migrateLegacy: true,
    })
    if (!raw) return { ...PREFS_DEFAULTS }
    return normalizePrefs(JSON.parse(raw))
  } catch {
    return { ...PREFS_DEFAULTS }
  }
}

export function setAccountPreferencesServerOverlay(prefs) {
  _serverPrefsOverlay = prefs ? normalizePrefs(prefs) : null
}

export function clearAccountPreferencesServerOverlay() {
  _serverPrefsOverlay = null
}

export function readAppPreferences() {
  if (_serverPrefsOverlay) {
    return normalizePrefs(_serverPrefsOverlay)
  }
  return readAppPreferencesLocalOnly()
}

/** 便于日志输出的一致快照（不含内部版本字段） */
export function preferencesSnapshotForLog(prefs) {
  const p = prefs && typeof prefs === 'object' ? normalizePrefs(prefs) : readAppPreferences()
  return {
    scoring_profile: p.scoring_profile,
    defense_material_mode: p.defense_material_mode,
    history_valid_only_default: p.history_valid_only_default,
    show_first_time_hints: p.show_first_time_hints,
    show_recent_valid_reminder: p.show_recent_valid_reminder,
  }
}

export function notifyAppPreferencesChanged() {
  try {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event(APP_PREFERENCES_CHANGED_EVENT))
    }
  } catch (_) {}
}

function mirrorPrefsToLocal(next) {
  const uid = getActiveUserId()
  try {
    writeUserScopedItem(localStorage, APP_PREFERENCES_STORAGE_KEY, JSON.stringify(next), uid)
  } catch (_) {}
}

/** 登录后拉取云端成功时：写 overlay + 本地镜像 */
export function applyHydratedServerPreferences(prefs) {
  const next = normalizePrefs(prefs)
  _serverPrefsOverlay = { ...next }
  mirrorPrefsToLocal(next)
}

export function writeAppPreferences(partial) {
  const uid = getActiveUserId()
  const next = normalizePrefs({ ...readAppPreferences(), ...partial, v: 1 })
  _serverPrefsOverlay = { ...next }
  mirrorPrefsToLocal(next)
  notifyAppPreferencesChanged()
  return next
}

export function resetAppPreferencesToFactory() {
  const uid = getActiveUserId()
  const next = { ...PREFS_DEFAULTS }
  _serverPrefsOverlay = { ...next }
  try {
    removeUserScopedItem(localStorage, APP_PREFERENCES_STORAGE_KEY, uid, true)
  } catch (_) {}
  mirrorPrefsToLocal(next)
  notifyAppPreferencesChanged()
  return { ...PREFS_DEFAULTS }
}

/**
 * 清除：未开训草稿、运行时快照、专项 handoff、本地 session_id（可恢复会话标记）、最近 ppt_id。
 * 不删除训练记录、报告与后端数据。
 * @param {string | null | undefined} explicitUserId 登出前传入，避免清 session 后丢失 user
 * @returns {{ cleared: string[], keys: string[] }}
 */
export function clearTrainingLocalDraftAndResumeState(explicitUserId) {
  const uid =
    explicitUserId !== undefined && explicitUserId !== null && String(explicitUserId).trim() !== ''
      ? String(explicitUserId).trim()
      : getActiveUserId()
  const cleared = []
  const keys = []
  const parts = [
    [localStorage, TRAINING_DRAFT_KEY, 'draft'],
    [localStorage, TRAINING_RUNTIME_SNAPSHOT_KEY, 'runtime_snapshot'],
    [localStorage, CURRENT_SESSION_ID_KEY, 'current_session_id'],
    [sessionStorage, TRAINING_FOCUS_HANDOFF_KEY, 'focus_handoff'],
    [localStorage, LAST_PPT_ID_STORAGE_KEY, 'last_ppt_id'],
  ]
  for (const [store, base, label] of parts) {
    try {
      if (uid) {
        const sk = getUserScopedKey(base, uid)
        if (store.getItem(sk) != null) {
          store.removeItem(sk)
          cleared.push(label)
          keys.push(sk)
        }
      }
      if (store.getItem(base) != null) {
        store.removeItem(base)
        cleared.push(uid ? `${label}_legacy_global` : label)
        keys.push(base)
      }
    } catch (_) {}
  }
  return { cleared, keys }
}

export async function hydrateAppPreferencesFromServer() {
  const m = await import('./accountSettingsSync.js')
  if (m.hydrateAccountSettings) return m.hydrateAccountSettings()
}
