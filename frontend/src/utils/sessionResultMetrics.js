/**
 * 当前 session 的指标解析（优先 raw_result，与 Result / Report 页面共用，避免默认占位与多源不一致）
 */

export function formatSessionMetricCell(v) {
  if (v == null || v === '') return '—'
  if (typeof v === 'number' && !Number.isFinite(v)) return '—'
  return String(v)
}

export function getSessionResultRow(r) {
  if (!r || typeof r !== 'object') return null
  if (r.raw_result && typeof r.raw_result === 'object') return r.raw_result
  return r
}

function firstFiniteNumber(...vals) {
  for (const v of vals) {
    if (v == null || v === '') continue
    const n = Number(v)
    if (Number.isFinite(n)) return n
  }
  return null
}

/**
 * 语言与音频转写：仅来自本 session 的 audio_session_summary / audio_analysis / 顶层 transcript,audio_metrics
 * audio_valid === false 时，数值性指标一律为 null，不再用 0 占位
 */
export function resolveAudioMetricsFromSession(row) {
  if (!row || typeof row !== 'object') {
    return {
      audio_valid: true,
      audio_message: '',
      transcript: '',
      speech_rate: null,
      pause_count: null,
      avg_pause_sec: null,
      filler_count: null,
    }
  }
  const ass = row.audio_session_summary && typeof row.audio_session_summary === 'object' ? row.audio_session_summary : null
  const aa = row.audio_analysis && typeof row.audio_analysis === 'object' ? row.audio_analysis : null
  const am = row.audio_metrics && typeof row.audio_metrics === 'object' ? row.audio_metrics : null

  const tr = (() => {
    const t1 = ass && typeof ass.transcript === 'string' ? ass.transcript.trim() : ''
    const t2 = aa && typeof aa.transcript === 'string' ? aa.transcript.trim() : ''
    const t3 = typeof row.transcript === 'string' ? row.transcript.trim() : ''
    return t1 || t2 || t3
  })()

  let audioValid = true
  let audioMessage = ''
  if (row.audio_valid === false) {
    audioValid = false
    audioMessage = String(row.audio_message || '').trim()
  }
  if (aa && Object.prototype.hasOwnProperty.call(aa, 'audio_valid') && aa.audio_valid === false) {
    audioValid = false
    if (!audioMessage) audioMessage = String(aa.audio_message || '').trim()
  } else if (ass && Object.prototype.hasOwnProperty.call(ass, 'audio_valid') && ass.audio_valid === false) {
    audioValid = false
    if (!audioMessage) audioMessage = String(ass.audio_message || '').trim()
  }

  const m = (key) => firstFiniteNumber(ass?.[key], aa?.[key], am?.[key])

  let speech_rate = m('speech_rate')
  let pause_count = m('pause_count')
  let avg_pause_sec = m('avg_pause_sec')
  let filler_count = m('filler_count')

  if (audioValid === false) {
    speech_rate = null
    pause_count = null
    avg_pause_sec = null
    filler_count = null
  }

  return {
    audio_valid: audioValid,
    audio_message: audioMessage,
    transcript: tr,
    speech_rate,
    pause_count,
    avg_pause_sec,
    filler_count,
  }
}

/**
 * 仪态与视觉标量：vision_session_summary → vision_analysis → 顶层 vision_* 与 metrics 名称兜底（仅本 session row）
 */
export function resolveVisionMetricsFromSession(row) {
  if (!row || typeof row !== 'object') {
    return {
      vision_valid: true,
      vision_message: '',
      forward_gaze_ratio: null,
      downward_head_ratio: null,
      posture_stability: null,
    }
  }
  const vss = row.vision_session_summary && typeof row.vision_session_summary === 'object' ? row.vision_session_summary : null
  const va = row.vision_analysis && typeof row.vision_analysis === 'object' ? row.vision_analysis : null

  const pick = (k) => firstFiniteNumber(vss?.[k], va?.[k], row[k])
  const forward_gaze_ratio = pick('forward_gaze_ratio')
  const downward_head_ratio = pick('downward_head_ratio')
  const posture_stability = pick('posture_stability')

  let visionMessage = String(row.vision_message || va?.vision_message || vss?.vision_message || '').trim()

  let visionValid = true
  if (row.vision_valid === false) visionValid = false
  if (va && Object.prototype.hasOwnProperty.call(va, 'vision_valid') && va.vision_valid === false) {
    visionValid = false
    if (!visionMessage) visionMessage = String(va.vision_message || '').trim()
  } else if (vss && Object.prototype.hasOwnProperty.call(vss, 'vision_valid') && vss.vision_valid === false) {
    visionValid = false
  }

  if (visionValid === false) {
    return {
      vision_valid: false,
      vision_message: visionMessage,
      forward_gaze_ratio: null,
      downward_head_ratio: null,
      posture_stability: null,
    }
  }
  if (
    forward_gaze_ratio == null &&
    downward_head_ratio == null &&
    posture_stability == null
  ) {
    const metrics = Array.isArray(row.metrics) ? row.metrics : []
    const byName = (name) => {
      const it = metrics.find((x) => x && x.name === name)
      if (!it || it.value == null || it.value === '') return null
      const n = Number(it.value)
      return Number.isFinite(n) ? n : null
    }
    return {
      vision_valid: true,
      vision_message: visionMessage,
      forward_gaze_ratio: forward_gaze_ratio ?? byName('正视前方比例'),
      downward_head_ratio: downward_head_ratio ?? byName('低头率'),
      posture_stability: posture_stability ?? byName('姿态稳定度'),
    }
  }

  return {
    vision_valid: true,
    vision_message: visionMessage,
    forward_gaze_ratio,
    downward_head_ratio,
    posture_stability,
  }
}

const LONG_AUDIO_KEYS = ['total_audio_duration_sec', 'transcribed_chunks', 'skipped_chunks', 'dropped_dirty_chunks']

const LONG_VISION_KEYS = [
  'total_video_duration_sec',
  'duration_source',
  'processed_frames',
  'skipped_frames',
  'sampled_mode_used',
  'sampled_fps',
]

function pickFromVisionLong(ss, va, key) {
  if (ss && Object.prototype.hasOwnProperty.call(ss, key)) {
    const v = ss[key]
    if (v != null && v !== '') return v
  }
  if (!va || typeof va !== 'object') return undefined
  if (key === 'processed_frames') {
    return firstDefinedVision(va.processed_frames, va.valid_detection_frames)
  }
  if (key === 'skipped_frames') {
    return firstDefinedVision(va.skipped_frames, va.vision_skipped_frames)
  }
  if (key === 'sampled_mode_used') {
    return firstDefinedVision(va.sampled_mode_used, va.vision_sampled_mode_used)
  }
  if (key === 'sampled_fps') {
    return firstDefinedVision(va.sampled_fps, va.vision_sampled_fps)
  }
  const u = va[key]
  if (u != null && u !== '') return u
  return undefined
}

function firstDefinedVision(a, b) {
  if (a != null && a !== '') return a
  if (b != null && b !== '') return b
  return undefined
}

function pickLongAudio(ass, aa) {
  const out = {}
  for (const k of LONG_AUDIO_KEYS) {
    let v
    if (ass && Object.prototype.hasOwnProperty.call(ass, k) && ass[k] != null && ass[k] !== '') v = ass[k]
    else if (aa && Object.prototype.hasOwnProperty.call(aa, k) && aa[k] != null && aa[k] !== '') v = aa[k]
    if (v != null && v !== '') out[k] = v
  }
  return Object.keys(out).length ? out : null
}

/**
 * 长时会话：音频块仅来自 audio_session_summary / audio_analysis 中明确长时字段；视频块来自 vision_session_summary / vision_analysis / 顶层
 */
export function resolveLongSessionSummaryFromSession(row) {
  if (!row || typeof row !== 'object') {
    return { hasSummary: false, audio: null, video: null }
  }
  const ass = row.audio_session_summary && typeof row.audio_session_summary === 'object' ? row.audio_session_summary : null
  const aa = row.audio_analysis && typeof row.audio_analysis === 'object' ? row.audio_analysis : null
  const audio = pickLongAudio(ass, aa)

  const ss = row.vision_session_summary && typeof row.vision_session_summary === 'object' ? row.vision_session_summary : null
  const va = row.vision_analysis && typeof row.vision_analysis === 'object' ? row.vision_analysis : null
  const video = {}
  for (const k of LONG_VISION_KEYS) {
    let v
    v = pickFromVisionLong(ss, va, k)
    if (v == null && row[k] != null && row[k] !== '' && !LONG_AUDIO_KEYS.includes(k)) v = row[k]
    if (v == null) {
      if (k === 'total_video_duration_sec' && row.total_video_duration_sec != null) v = row.total_video_duration_sec
    }
    if (v != null && v !== '') video[k] = v
  }
  if (ss?.session_summary_version) video.session_summary_version = ss.session_summary_version

  const videoOut = Object.keys(video).length ? video : null
  const hasSummary = !!(audio && Object.keys(audio).length) || !!(videoOut && Object.keys(videoOut).length)
  return {
    hasSummary,
    audio,
    video: videoOut,
  }
}
