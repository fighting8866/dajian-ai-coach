<template>
  <div class="profile-page profile-page--dash ui-page-frame ui-page-shell-inset">
    <header class="profile-hero">
      <p class="profile-hero__eyebrow">训练复盘</p>
      <h1 class="profile-hero__title">个人训练档案</h1>
      <p class="profile-hero__sub">
        查看有效训练概况、最近一次表现与建议方向；设定目标后在此对照进度，一键继续训练或跳转复盘。
      </p>
    </header>

    <div v-if="loading" class="profile-loading" aria-busy="true" aria-live="polite">
      <p class="profile-loading__label muted">正在加载档案…</p>
      <el-skeleton :rows="6" animated />
    </div>

    <div v-else class="profile-dashboard">
      <div v-if="loadError" class="profile-alert-wrap">
        <el-alert type="warning" :closable="false" show-icon title="训练档案暂时无法加载">
          <p class="profile-alert__body">{{ loadError }}</p>
          <el-button type="primary" class="profile-retry" @click="loadAll">重试</el-button>
        </el-alert>
      </div>

      <template v-else>
        <!-- 第一行：训练概况（左）+ 近况与建议（右）；无数据时整行 CTA -->
        <div class="profile-dash-row profile-dash-row--primary">
          <template v-if="hasTrainingData">
            <section
              class="profile-card profile-card--summary ui-surface"
              aria-labelledby="profile-stats-title"
            >
              <p class="profile-card__eyebrow">我的训练档案</p>
              <h2 id="profile-stats-title" class="profile-card__title">训练概况</h2>
              <p v-if="summary?.overview_message" class="profile-stats-note muted">{{ summary.overview_message }}</p>
              <ul class="profile-stat-grid">
                <li class="profile-stat-cell">
                  <span class="profile-stat-label">有效训练（累计）</span>
                  <strong class="profile-stat-value">{{ summary?.valid_training_count ?? 0 }} 次</strong>
                </li>
                <li class="profile-stat-cell">
                  <span class="profile-stat-label">有效训练（最近窗口）</span>
                  <strong class="profile-stat-value">
                    {{ summary?.valid_training_count_recent ?? 0 }} / {{ summary?.recent_window_size ?? 7 }} 次
                  </strong>
                </li>
                <li class="profile-stat-cell">
                  <span class="profile-stat-label">历史最佳总分</span>
                  <strong class="profile-stat-value">{{ bestScoreLabel }}</strong>
                </li>
                <li class="profile-stat-cell">
                  <span class="profile-stat-label">最近窗口平均总分</span>
                  <strong class="profile-stat-value">{{ recentAvgLabel }}</strong>
                </li>
              </ul>
            </section>

            <section class="profile-card profile-card--insight ui-surface" aria-labelledby="profile-insight-title">
              <h2 id="profile-insight-title" class="profile-card__title">近况与下一步</h2>
              <div class="profile-recent-panel">
                <h3 class="profile-subhead">最近一次有效训练</h3>
                <dl class="profile-recent-dl">
                  <div class="profile-recent-item">
                    <dt>时间</dt>
                    <dd>{{ latestTimeLabel }}</dd>
                  </div>
                  <div class="profile-recent-item">
                    <dt>总分</dt>
                    <dd>{{ latestScoreLabel }}</dd>
                  </div>
                  <div class="profile-recent-item">
                    <dt>本轮专项</dt>
                    <dd>{{ trainingFocusLabel(summary?.latest_valid_training_focus) }}</dd>
                  </div>
                </dl>
              </div>
              <div class="profile-focus-panel">
                <h3 class="profile-subhead">练习重心</h3>
                <p class="profile-focus-line">
                  <span class="muted">建议下一轮侧重：</span>
                  <strong>{{ recommendedFocusLabel }}</strong>
                </p>
                <p v-if="frequentFocusLine" class="profile-focus-line muted">
                  <span>最近窗口常练专项：</span>{{ frequentFocusLine }}
                </p>
              </div>
            </section>
          </template>

          <section
            v-else
            class="profile-card profile-card--empty-cta ui-surface profile-card--span-all"
            aria-label="开启训练档案"
          >
            <h2 class="profile-card__title">开启你的训练档案</h2>
            <p class="profile-empty-lead muted">
              当前还没有有效训练记录。完成第一轮练习后，这里会汇总概况、最佳分与专项节奏。
            </p>
            <el-button type="primary" size="large" @click="goTraining">开始第一轮训练</el-button>
          </section>
        </div>

        <!-- 第二行：训练目标 + 快捷入口 -->
        <div class="profile-dash-row profile-dash-row--secondary">
          <section
            v-if="goalSectionVisible"
            class="profile-card profile-card--goals ui-surface"
            aria-labelledby="profile-goals-title"
          >
            <h2 id="profile-goals-title" class="profile-card__title">当前训练目标</h2>
            <p v-if="goalHeadline" class="profile-goal-headline">{{ goalHeadline }}</p>
            <ul v-if="goalLines.length" class="profile-goal-lines">
              <li v-for="(ln, i) in goalLines" :key="`gl-${i}`">{{ ln }}</li>
            </ul>
            <p v-else class="muted">目标已设置，完成更多有效训练后进度会更清晰。</p>
          </section>
          <section v-else class="profile-card profile-card--goals profile-card--goals-empty ui-surface">
            <h2 class="profile-card__title">当前训练目标</h2>
            <p class="muted">
              尚未设定训练目标。请在首页展开「详细：训练数据、目标与设置」，在「训练目标与当前进度」中添加。
            </p>
          </section>

          <section class="profile-card profile-card--actions ui-surface" aria-label="快捷入口">
            <h2 class="profile-card__title">快捷入口</h2>
            <div class="profile-action-grid">
              <el-button type="primary" size="large" @click="goTraining">进入训练</el-button>
              <el-button size="large" plain @click="goHistory">查看历史</el-button>
              <el-button
                size="large"
                plain
                :disabled="loadError || !summary?.latest_valid_session_id"
                @click="goLatestResult"
              >
                查看最近结果
              </el-button>
              <el-button size="large" plain @click="goSettings">打开设置中心</el-button>
            </div>
            <p class="profile-actions-hint muted">以上仅为跳转，不会自动开始训练。</p>
          </section>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getJson } from '../api/base'
import { hydrateAccountSettings } from '../utils/accountSettingsSync'
import {
  trainingFocusLabel,
  TRAINING_FOCUS_LABEL,
  TRAINING_GOAL_FOCUS_LABEL,
} from '../constants/productTerms'
import {
  readTrainingGoals,
  computeTrainingGoalProgress,
  hasActiveTrainingGoals,
} from '../utils/trainingGoals'
import { computeGoalStatusPack } from '../utils/trainingGoalStatus'

const router = useRouter()

const loading = ref(true)
const loadError = ref('')
const summary = ref(null)
const historyList = ref([])

const hasTrainingData = computed(() => (summary.value?.valid_training_count ?? 0) > 0)

const bestScoreLabel = computed(() => {
  const v = summary.value?.best_total_score
  if (v == null || v === '') return '—'
  const n = Number(v)
  return Number.isFinite(n) ? `${n.toFixed(1)} 分` : '—'
})

const recentAvgLabel = computed(() => {
  const v = summary.value?.avg_total_score_recent
  if (v == null || v === '') return '—'
  const n = Number(v)
  return Number.isFinite(n) ? `${n.toFixed(1)} 分` : '—'
})

const latestTimeLabel = computed(() => {
  const ts = summary.value?.latest_valid_created_at
  if (ts == null || String(ts).trim() === '') return '—'
  try {
    return new Date(ts).toLocaleString()
  } catch {
    return String(ts)
  }
})

const latestScoreLabel = computed(() => {
  const v = summary.value?.latest_valid_total_score
  if (v == null || v === '') return '—'
  const n = Number(v)
  return Number.isFinite(n) ? `${n.toFixed(1)} 分` : '—'
})

const recommendedFocusLabel = computed(() => {
  const k = summary.value?.recommended_continue_focus
  if (k == null || String(k).trim() === '' || String(k).toLowerCase() === 'none') {
    return TRAINING_FOCUS_LABEL.none
  }
  return trainingFocusLabel(k)
})

const frequentFocusLine = computed(() => {
  const dist = summary.value?.focus_distribution_recent
  if (!dist || typeof dist !== 'object') return ''
  const keys = ['language', 'posture', 'qa', 'content']
  let bestK = null
  let bestN = -1
  for (const k of keys) {
    const n = Number(dist[k] || 0)
    if (n > bestN) {
      bestN = n
      bestK = k
    }
  }
  if (!bestK || bestN <= 0) return ''
  return `${trainingFocusLabel(bestK)}（${bestN} 次）`
})

const overviewForGoals = computed(() => {
  const s = summary.value
  if (!s) return null
  return {
    overview_ready: s.overview_ready,
    overview_message: s.overview_message,
    valid_count_recent: s.valid_training_count_recent,
    recent_window_size: s.recent_window_size,
    avg_total_score_recent: s.avg_total_score_recent,
    latest_valid_session_id: s.latest_valid_session_id,
    latest_valid_training_focus: s.latest_valid_training_focus,
    latest_valid_created_at: s.latest_valid_created_at,
    latest_valid_total_score: s.latest_valid_total_score,
    recommended_continue_focus: s.recommended_continue_focus,
    focus_distribution_recent: s.focus_distribution_recent,
  }
})

const goalProgress = computed(() =>
  computeTrainingGoalProgress({
    goals: readTrainingGoals(),
    historyList: historyList.value,
    overview: overviewForGoals.value,
  })
)

const goalStatusPack = computed(() => computeGoalStatusPack(goalProgress.value))

const goalSectionVisible = computed(() => hasActiveTrainingGoals(readTrainingGoals()))

const goalHeadline = computed(() => goalStatusPack.value.headline || '')

const goalLines = computed(() => {
  const p = goalProgress.value
  const g = p.goals
  if (!hasActiveTrainingGoals(g)) return []
  const lines = []
  if (g.target_total_score != null) {
    lines.push(`当前目标：总分达到 ${Number(g.target_total_score).toFixed(1)} 分`)
    if (p.bestTotal != null) {
      if (p.gapToTarget != null && p.gapToTarget > 0) {
        lines.push(`当前最好成绩 ${p.bestTotal.toFixed(1)} 分，还差 ${p.gapToTarget.toFixed(1)} 分`)
      } else {
        lines.push(`当前最好成绩 ${p.bestTotal.toFixed(1)} 分，已达到目标线`)
      }
    } else {
      lines.push('暂无有效训练记录，完成一轮有效训练后即可对照目标总分。')
    }
    if (p.recentAvgTotal != null) {
      lines.push(`最近有效训练平均总分约 ${p.recentAvgTotal.toFixed(1)} 分。`)
    }
  }
  if (g.target_focus) {
    const lab = TRAINING_GOAL_FOCUS_LABEL[g.target_focus] || g.target_focus
    if (p.focusBest != null) {
      lines.push(`目标专项：${lab}；该项在有效训练中最好约 ${p.focusBest.toFixed(1)} 分`)
    } else {
      lines.push(`目标专项：${lab}；尚未在有效训练中汇总到该项分数`)
    }
  }
  if (p.validCountProgress) {
    const { current, target } = p.validCountProgress
    lines.push(`已完成 ${current} / ${target} 次有效训练`)
  }
  return lines
})

async function loadAll() {
  loading.value = true
  loadError.value = ''
  try {
    try {
      await hydrateAccountSettings()
    } catch (_) {}
    const [sum, hist] = await Promise.all([getJson('/profile/summary'), getJson('/history')])
    summary.value = sum
    historyList.value = Array.isArray(hist.history) ? hist.history : []
    const u = sum?.username ?? null
    console.log('[Profile.load] user=', u)
    console.log('[Profile.load] summary=', {
      valid_training_count: sum?.valid_training_count,
      best_total_score: sum?.best_total_score,
      overview_ready: sum?.overview_ready,
      latest_valid_session_id: sum?.latest_valid_session_id,
    })
  } catch (e) {
    summary.value = null
    historyList.value = []
    loadError.value =
      e && e.message
        ? String(e.message).slice(0, 200)
        : '加载失败，请检查网络或稍后重试。'
    console.log('[Profile.load] user=', null)
    console.log('[Profile.load] summary=', null)
  } finally {
    loading.value = false
  }
}

function goTraining() {
  router.push('/training')
}

function goHistory() {
  router.push('/history')
}

function goLatestResult() {
  const sid = String(summary.value?.latest_valid_session_id || '').trim()
  if (!sid) return
  router.push({ path: '/result', query: { session_id: sid } })
}

function goSettings() {
  router.push({ name: 'Settings' })
}

onMounted(() => {
  console.log('[Profile] opened')
  loadAll()
})
</script>

<style scoped>
.profile-page--dash {
  max-width: min(1220px, 100%);
  margin: 0 auto;
}

.profile-hero {
  margin-bottom: var(--ui-stack-gap-sm, 16px);
}

.profile-hero__eyebrow {
  margin: 0 0 8px;
  font-size: var(--font-xs, 14px);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ui-text-muted);
}

.profile-hero__title {
  margin: 0 0 10px;
  font-size: clamp(28px, 2.1vw, 36px);
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.2;
  color: var(--ui-text-primary);
}

.profile-hero__sub {
  margin: 0;
  max-width: 52rem;
  font-size: var(--font-md, 18px);
  line-height: 1.65;
  color: var(--ui-text-secondary);
}

.profile-dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--ui-stack-gap, 22px);
}

.profile-loading__label {
  margin: 0 0 12px;
  font-size: var(--font-base, 17px);
}

.profile-alert-wrap {
  margin-bottom: 4px;
}

.profile-alert__body {
  margin: 0 0 12px;
  font-size: var(--font-base, 17px);
  line-height: 1.6;
}

.profile-dash-row {
  display: grid;
  gap: var(--ui-stack-gap, 22px);
  align-items: stretch;
}

.profile-dash-row--primary {
  grid-template-columns: 1fr;
}

.profile-dash-row--secondary {
  grid-template-columns: 1fr;
}

.profile-card--span-all {
  grid-column: 1 / -1;
}

@media (min-width: 1280px) {
  .profile-dash-row--primary {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }

  .profile-dash-row--secondary {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
}

@media (min-width: 900px) and (max-width: 1279px) {
  .profile-dash-row--primary {
    display: flex;
    flex-direction: column;
  }

  .profile-card--insight {
    order: -1;
  }
}

.profile-card {
  padding: var(--ui-card-pad-y, 20px) var(--ui-card-pad-x, 22px);
  border-radius: var(--ui-radius-lg, 12px);
  min-width: 0;
}

.profile-card__eyebrow {
  margin: 0 0 6px;
  font-size: var(--font-xs, 14px);
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ui-accent);
}

.profile-card__title {
  margin: 0 0 12px;
  font-size: var(--ui-typo-section, 22px);
  font-weight: 800;
  letter-spacing: -0.015em;
  color: var(--ui-text-primary);
  line-height: 1.25;
}

.profile-stats-note {
  margin: 0 0 16px;
  font-size: var(--font-base, 17px);
  line-height: 1.6;
}

.profile-stat-grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 14px 18px;
}

.profile-stat-cell {
  margin: 0;
  padding: 14px 16px;
  border-radius: var(--ui-radius-md, 8px);
  border: 1px solid var(--ui-border);
  background: var(--ui-surface-subtle);
}

.profile-stat-label {
  display: block;
  font-size: var(--font-sm, 15px);
  font-weight: 600;
  color: var(--ui-text-secondary);
  margin-bottom: 6px;
}

.profile-stat-value {
  display: block;
  font-size: clamp(22px, 2vw, 28px);
  font-weight: 800;
  color: var(--ui-text-primary);
  line-height: 1.2;
}

.profile-card--insight {
  border-left: 4px solid var(--ui-accent-muted);
}

.profile-recent-panel {
  margin: 0 0 18px;
  padding: 14px 16px;
  border-radius: var(--ui-radius-md, 8px);
  background: linear-gradient(165deg, var(--ui-accent-soft) 0%, var(--ui-surface) 100%);
  border: 1px solid var(--ui-accent-muted);
}

.profile-subhead {
  margin: 0 0 10px;
  font-size: var(--font-lg, 21px);
  font-weight: 700;
  color: var(--ui-text-primary);
}

.profile-recent-dl {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px 16px;
}

.profile-recent-item {
  margin: 0;
}

.profile-recent-item dt {
  margin: 0 0 4px;
  font-size: var(--font-sm, 15px);
  font-weight: 600;
  color: var(--ui-text-secondary);
}

.profile-recent-item dd {
  margin: 0;
  font-size: var(--font-base, 17px);
  font-weight: 700;
  color: var(--ui-text-primary);
  line-height: 1.35;
}

.profile-focus-panel {
  padding-top: 16px;
  border-top: 1px solid var(--ui-border);
}

.profile-focus-line {
  margin: 0 0 8px;
  font-size: var(--font-base, 17px);
  line-height: 1.6;
}

.profile-focus-line:last-child {
  margin-bottom: 0;
}

.profile-empty-lead {
  margin: 0 0 18px;
  font-size: var(--font-base, 17px);
  line-height: 1.65;
}

.profile-card--goals {
  border-left: 4px solid var(--ui-accent-muted);
}

.profile-card--goals-empty {
  border-left: 4px solid var(--ui-border-strong);
}

.profile-goal-headline {
  margin: 0 0 12px;
  font-size: var(--font-md, 18px);
  font-weight: 700;
  color: var(--ui-text-primary);
  line-height: 1.45;
}

.profile-goal-lines {
  margin: 0;
  padding-left: 1.25rem;
  font-size: var(--font-base, 17px);
  line-height: 1.7;
  color: var(--ui-text-secondary);
}

.profile-goal-lines li {
  margin-bottom: 8px;
}

.profile-card--actions {
  background: linear-gradient(180deg, var(--ui-surface) 0%, var(--ui-surface-subtle) 100%);
}

.profile-action-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.profile-actions-hint {
  margin: 0;
  font-size: var(--font-sm, 15px);
  line-height: 1.55;
}

.profile-retry {
  margin-top: 8px;
}

@media (max-width: 640px) {
  .profile-action-grid {
    grid-template-columns: 1fr;
  }
}
</style>
