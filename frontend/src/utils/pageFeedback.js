import { nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { restoreFocusable } from './a11yFocus'

const DEFAULT_DURATION = 2600

/** Training：统一日志 + 可选 Toast（success / warning / info） */
export function trainingFeedback(action, result, message, showToast = true) {
  console.log('[Training.feedback] action=', action)
  console.log('[Training.feedback] result=', result)
  console.log('[Training.feedback] message=', message)
  if (!showToast) return
  if (result === 'success') {
    ElMessage.success({ message, duration: DEFAULT_DURATION })
  } else if (result === 'warning') {
    ElMessage.warning({ message, duration: DEFAULT_DURATION })
  } else if (result === 'info' || result === 'confirm') {
    ElMessage.info({ message, duration: DEFAULT_DURATION })
  }
}

/** 危险操作确认；取消时不抛错，返回 false */
export async function trainingConfirmDanger({
  title = '请确认',
  message,
  confirmButtonText = '确定',
  cancelButtonText = '取消',
} = {}) {
  const previousFocus = document.activeElement
  try {
    await ElMessageBox.confirm(message, title, {
      type: 'warning',
      confirmButtonText,
      cancelButtonText,
      closeOnPressEscape: true,
    })
    nextTick(() => restoreFocusable(previousFocus))
    return true
  } catch {
    nextTick(() => restoreFocusable(previousFocus))
    return false
  }
}

/** Home / Result / History 等：action + message + 变体（ElMessage 由 Element Plus 以 role=alert 渲染，读屏会朗读） */
export function pageFeedback(scope, action, message, variant = 'success') {
  console.log(`[${scope}.feedback] action=`, action)
  console.log(`[${scope}.feedback] message=`, message)
  if (variant === 'success') {
    ElMessage.success({ message, duration: DEFAULT_DURATION })
  } else if (variant === 'warning') {
    ElMessage.warning({ message, duration: DEFAULT_DURATION })
  } else {
    ElMessage.info({ message, duration: DEFAULT_DURATION })
  }
}
