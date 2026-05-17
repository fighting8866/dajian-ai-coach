/**
 * 账号级偏好与训练目标：GET/PUT /profile/preferences，云端优先（V1）
 */
import { getJson, putJson } from '../api/base'
import {
  normalizePrefs,
  PREFS_DEFAULTS,
  readAppPreferencesLocalOnly,
  applyHydratedServerPreferences,
  clearAccountPreferencesServerOverlay,
  notifyAppPreferencesChanged,
  readAppPreferences,
} from './appPreferences'
import {
  normalizeGoals,
  readTrainingGoalsLocalOnly,
  applyHydratedServerGoals,
  clearTrainingGoalsServerOverlay,
  hasActiveTrainingGoals,
  TRAINING_GOALS_DEFAULTS,
  readTrainingGoals,
} from './trainingGoals'

let _hydrateInFlight = null

function mapApiRowToFrontendPrefs(row) {
  if (!row || typeof row !== 'object') return { ...PREFS_DEFAULTS }
  return normalizePrefs({
    scoring_profile: row.default_scoring_profile,
    defense_material_mode: row.default_defense_material_mode,
    history_valid_only_default: row.history_valid_only_default,
    show_first_time_hints: row.show_first_time_hints,
    show_recent_valid_reminder: row.show_recent_training_reminder,
  })
}

function mapApiRowToFrontendGoals(row) {
  const g = row?.training_goals
  if (!g || typeof g !== 'object') return { ...TRAINING_GOALS_DEFAULTS }
  return normalizeGoals(g)
}

function prefsRoughlyDefault(p) {
  const n = normalizePrefs(p)
  const d = normalizePrefs({ ...PREFS_DEFAULTS })
  return JSON.stringify(n) === JSON.stringify(d)
}

function buildPutPayloadFromMemory() {
  const p = normalizePrefs(readAppPreferences())
  const g = normalizeGoals(readTrainingGoals())
  return {
    default_scoring_profile: p.scoring_profile,
    default_defense_material_mode: p.defense_material_mode,
    history_valid_only_default: p.history_valid_only_default,
    show_first_time_hints: p.show_first_time_hints,
    show_recent_training_reminder: p.show_recent_valid_reminder,
    training_goals: {
      v: 1,
      target_total_score: g.target_total_score,
      target_focus: g.target_focus,
      target_valid_session_count: g.target_valid_session_count,
    },
  }
}

/**
 * 将当前内存中的偏好与目标写入云端（供设置保存、目标保存调用）
 */
export async function pushFullAccountSettingsToServer() {
  const body = buildPutPayloadFromMemory()
  const res = await putJson('/profile/preferences', body)
  applyHydratedServerPreferences(mapApiRowToFrontendPrefs(res))
  applyHydratedServerGoals(mapApiRowToFrontendGoals(res))
  notifyAppPreferencesChanged()
  try {
    window.dispatchEvent(new Event('mianshi-training-goals-changed'))
  } catch (_) {}
  return res
}

/**
 * 登录后拉取账号配置；若云端尚无保存且本地有实质内容则尝试一次性上传
 */
export function hydrateAccountSettings() {
  if (_hydrateInFlight) return _hydrateInFlight
  const run = async () => {
    try {
      const row = await getJson('/profile/preferences')
      const hasSaved = row.has_saved_preferences === true

      if (
        !hasSaved &&
        (!prefsRoughlyDefault(readAppPreferencesLocalOnly()) ||
          hasActiveTrainingGoals(readTrainingGoalsLocalOnly()))
      ) {
        try {
          const p0 = readAppPreferencesLocalOnly()
          const g0 = readTrainingGoalsLocalOnly()
          const body = {
            default_scoring_profile: p0.scoring_profile,
            default_defense_material_mode: p0.defense_material_mode,
            history_valid_only_default: p0.history_valid_only_default,
            show_first_time_hints: p0.show_first_time_hints,
            show_recent_training_reminder: p0.show_recent_valid_reminder,
            training_goals: {
              v: 1,
              target_total_score: g0.target_total_score,
              target_focus: g0.target_focus,
              target_valid_session_count: g0.target_valid_session_count,
            },
          }
          const saved = await putJson('/profile/preferences', body)
          applyHydratedServerPreferences(mapApiRowToFrontendPrefs(saved))
          applyHydratedServerGoals(mapApiRowToFrontendGoals(saved))
        } catch (_) {
          applyHydratedServerPreferences(mapApiRowToFrontendPrefs(row))
          applyHydratedServerGoals(mapApiRowToFrontendGoals(row))
        }
      } else {
        applyHydratedServerPreferences(mapApiRowToFrontendPrefs(row))
        applyHydratedServerGoals(mapApiRowToFrontendGoals(row))
      }
      notifyAppPreferencesChanged()
      try {
        window.dispatchEvent(new Event('mianshi-training-goals-changed'))
      } catch (_) {}
    } catch (_) {
      /* 接口失败：不设置 overlay，read* 回落到本地 */
    }
  }
  _hydrateInFlight = run()
  _hydrateInFlight.finally(() => {
    _hydrateInFlight = null
  })
  return _hydrateInFlight
}

export function clearAccountSyncCaches() {
  clearAccountPreferencesServerOverlay()
  clearTrainingGoalsServerOverlay()
}
