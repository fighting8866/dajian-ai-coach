/**
 * 退出登录：确认文案 + 清理本机会话态（不删服务器历史、不重置偏好与训练目标）。
 */
import { nextTick } from 'vue'
import { ElMessageBox } from 'element-plus'
import { restoreFocusable } from './a11yFocus'
import { clearAuthSession } from './authSession'
import {
  clearTrainingLocalDraftAndResumeState,
  CURRENT_SESSION_ID_KEY,
  TRAINING_RUNTIME_SNAPSHOT_KEY,
} from './appPreferences'
import { readUserScopedItem, getActiveUserId, clearAllPreflightOkKeys } from './userScopedStorage'
import { clearAccountSyncCaches } from './accountSettingsSync'

export function hasUnfinishedTrainingLocalHint() {
  const uid = getActiveUserId()
  try {
    const cs = readUserScopedItem(localStorage, CURRENT_SESSION_ID_KEY, uid, { migrateLegacy: true })
    if (cs && String(cs).trim()) return true
  } catch (_) {}
  try {
    const rt = readUserScopedItem(localStorage, TRAINING_RUNTIME_SNAPSHOT_KEY, uid, {
      migrateLegacy: true,
    })
    if (rt && String(rt).trim()) return true
  } catch (_) {}
  return false
}

export function clearLogoutLocalState() {
  const logoutUserId = getActiveUserId()
  const clearedKeyList = []
  try {
    clearAccountSyncCaches()
  } catch (_) {}
  clearAuthSession()
  clearedKeyList.push('dajian_auth_token_v1', 'dajian_auth_user_v1')
  try {
    const { cleared: trainingParts, keys: trainingKeys } = clearTrainingLocalDraftAndResumeState(logoutUserId)
    for (const p of trainingParts || []) {
      clearedKeyList.push(`training:${p}`)
    }
    for (const k of trainingKeys || []) {
      if (k && !clearedKeyList.includes(k)) clearedKeyList.push(k)
    }
  } catch (_) {}
  try {
    const preKeys = clearAllPreflightOkKeys()
    for (const k of preKeys) {
      if (!clearedKeyList.includes(k)) clearedKeyList.push(k)
    }
  } catch (_) {}
  console.log('[auth.user_scope] logout_clear_keys=', clearedKeyList.join(','))
  return clearedKeyList
}

/**
 * @param {import('vue-router').Router} router
 * @returns {Promise<boolean>} 是否已退出
 */
export async function confirmAndPerformLogout(router) {
  const hint = hasUnfinishedTrainingLocalHint()
  const message = hint
    ? '检测到本机可能还有未结束的训练会话标记。退出后将清除登录状态与本地会话草稿；服务器上的训练记录与报告不会删除。确定退出？'
    : '确定退出当前账号？退出后将清除本机登录状态与训练会话相关的临时标记。'
  const previousFocus = document.activeElement
  try {
    await ElMessageBox.confirm(message, '退出登录', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      type: 'warning',
      closeOnPressEscape: true,
    })
  } catch {
    console.log('[auth.logout] action=', 'cancel')
    nextTick(() => restoreFocusable(previousFocus))
    return false
  }
  console.log('[auth.logout] action=', 'confirm')
  const cleared = clearLogoutLocalState()
  console.log('[auth.logout] cleared_state=', cleared.join(','))
  try {
    router.replace({ path: '/login', query: {} })
  } catch (_) {}
  return true
}
