/** 登录态（V1）：localStorage + Bearer JWT */

const TOKEN_KEY = 'dajian_auth_token_v1'
const USER_KEY = 'dajian_auth_user_v1'

export function getAuthToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function setAuthToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch (_) {}
}

export function getAuthUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    if (!raw) return null
    const o = JSON.parse(raw)
    if (o && typeof o === 'object' && o.username) return { id: o.id, username: String(o.username) }
  } catch (_) {}
  return null
}

export function setAuthUser(user) {
  try {
    if (user && user.username) localStorage.setItem(USER_KEY, JSON.stringify(user))
    else localStorage.removeItem(USER_KEY)
  } catch (_) {}
}

export function clearAuthSession() {
  setAuthToken('')
  setAuthUser(null)
}
