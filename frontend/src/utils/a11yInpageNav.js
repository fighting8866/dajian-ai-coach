/**
 * 页内 # 导航：配合 tabindex="-1" 的锚点，在点击后将焦点移到目标区（读屏/键盘更易感知）。
 * 不修改路由，仅阻止默认的「只滚动不移动焦点」行为。
 * @param {MouseEvent} e
 */
export function onInpageNavLinkClick(e) {
  const a = e.currentTarget
  if (!(a instanceof HTMLAnchorElement)) return
  const href = a.getAttribute('href') || ''
  if (!href.startsWith('#')) return
  e.preventDefault()
  const id = href.slice(1)
  if (!id) return
  const el = document.getElementById(id)
  if (!el) return
  el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  requestAnimationFrame(() => {
    try {
      el.focus({ preventScroll: true })
    } catch (_) {}
  })
}
