/** 比赛展示用：推理链路文案（非调试日志） */

export function humanSpeechRoute(kind) {
  const k = String(kind || '').trim().toLowerCase()
  if (k === 'ascend') return '昇腾开发板'
  if (k === 'local') return '本机'
  return k ? k : '—'
}

export function humanVisionRoute(kind) {
  const k = String(kind || '').trim().toLowerCase()
  if (k === 'ascend') return '昇腾开发板'
  if (k === 'local') return '本机'
  return k ? k : '—'
}

export function humanDocParser(kind) {
  const k = String(kind || '').trim().toLowerCase()
  if (k === 'basic') return '基础解析'
  if (k === 'enhanced' || k === 'hybrid') return '增强解析'
  return k || '—'
}

export function boardParticipationLine(snap) {
  if (!snap || typeof snap !== 'object') return ''
  const sp = String(snap.speech_provider || '').toLowerCase()
  const vp = String(snap.vision_provider || '').toLowerCase()
  const parts = []
  if (sp === 'ascend') parts.push('语音分析走开发板')
  if (vp === 'ascend') parts.push('仪态与画面分析走开发板')
  if (!parts.length) return '本轮语音与画面分析均在本地完成，未走昇腾开发板推理链路。'
  return `本轮 ${parts.join('；')}。`
}

export function runtimeChainSummaryLine(snap) {
  if (!snap || typeof snap !== 'object') return ''
  const a = humanSpeechRoute(snap.speech_provider)
  const b = humanVisionRoute(snap.vision_provider)
  return `当前运行链路：语音分析 ${a} · 画面与仪态分析 ${b}`
}

export function sessionInferenceLine(snap) {
  if (!snap || typeof snap !== 'object') return ''
  const a = humanSpeechRoute(snap.speech_provider)
  const b = humanVisionRoute(snap.vision_provider)
  return `本轮训练结束时的分析链路：语音 ${a} · 画面与仪态 ${b}（与训练提交时后端配置一致）。`
}

/** 报告 / 打印：一两句说清链路与是否上板，避免过长括号说明 */
export function compactReportChainLine(snap) {
  if (!snap || typeof snap !== 'object') return ''
  const a = humanSpeechRoute(snap.speech_provider)
  const b = humanVisionRoute(snap.vision_provider)
  const usesBoard =
    String(snap.speech_provider || '').toLowerCase() === 'ascend' ||
    String(snap.vision_provider || '').toLowerCase() === 'ascend'
  const tail = usesBoard ? '昇腾开发板已参与本轮语音或仪态分析。' : '本轮语音与仪态分析均在本地完成。'
  return `运行链路：语音「${a}」· 仪态与画面「${b}」。${tail}`
}
