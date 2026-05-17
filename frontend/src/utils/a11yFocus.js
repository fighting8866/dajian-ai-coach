/**
 * 轻量焦点辅助：配合路由切换、MessageBox 关闭，不做视觉或布局改动。
 */

/**
 * 将焦点移回仍在文档中的可聚焦元素（避免落在已卸载节点上）。
 * @param {Element | null} el
 * @param {{ preventScroll?: boolean }} [opts]
 */
export function restoreFocusable(el, opts) {
  if (!el || typeof el.focus !== 'function') return
  if (el === document.body) return
  try {
    if (document.contains(el)) {
      const preventScroll = opts?.preventScroll !== false
      el.focus({ preventScroll })
    }
  } catch (_) {}
}

/**
 * 主内容区（与「跳到主内容」/布局中 main#main-content 一致）
 */
export function focusMainContent() {
  const el = document.getElementById('main-content')
  if (el && typeof el.focus === 'function') {
    try {
      el.focus({ preventScroll: true })
    } catch (_) {}
  }
}

/**
 * 将焦点移到容器内第一个可聚焦元素（如 Dialog 打开后）。
 * @param {string} rootSelector 根节点 CSS 选择器（需在 DOM 中已挂载）
 */
export function focusFirstInContainer(rootSelector) {
  const root = document.querySelector(rootSelector)
  if (!root) return
  const sel = [
    'button:not([disabled])',
    '[href]',
    'input:not([type="hidden"]):not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(', ')
  const first = root.querySelector(sel)
  if (first && typeof first.focus === 'function') {
    try {
      first.focus()
    } catch (_) {}
  }
}
