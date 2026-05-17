/**
 * 将异常转换为用户可读短文案（不暴露 HTTP 原文与长堆栈）。
 * 页面加载/重试失败时统一使用。
 */
export function toUserFacingMessage(err, fallback = '暂时无法完成操作，请稍后再试。') {
  if (err == null) return fallback
  const raw = typeof err === 'string' ? err : err.message || String(err)
  const s = String(raw).trim()
  if (!s) return fallback
  if (/failed to fetch|networkerror|network request failed|load failed|ecconnrefused/i.test(s)) {
    return '无法连接服务器，请检查网络或稍后重试。'
  }
  if (/HTTP error|status:\s*\d+/i.test(s)) {
    return '服务暂时不可用或响应异常，请稍后重试。'
  }
  if (/abort|timeout|timed out/i.test(s)) {
    return '请求超时或已中断，请稍后重试。'
  }
  if (s.length > 160) return fallback
  return s
}
