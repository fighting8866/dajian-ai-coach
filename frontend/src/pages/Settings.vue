<template>
  <div class="settings-page ui-page-frame ui-page-shell-inset">
    <header class="settings-hero">
      <p class="settings-hero__eyebrow">账号与偏好</p>
      <h1 class="settings-hero__title">设置中心</h1>
      <p class="settings-hero__sub">账号安全、登录与默认训练偏好；保存后同步到账号，换设备可沿用。</p>
    </header>

    <div v-if="loading" class="settings-loading" aria-busy="true" aria-live="polite">
      <p class="muted">正在加载…</p>
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else class="settings-dashboard">
      <div v-if="loadError" class="settings-alert-wrap">
        <el-alert type="warning" :closable="false" show-icon title="暂时无法加载账号信息">
          <p class="settings-alert__body">{{ loadError }}</p>
          <el-button type="primary" @click="loadAccount">重试</el-button>
        </el-alert>
      </div>

      <div v-else class="settings-dash-grid">
        <section class="settings-card settings-card--account ui-surface" aria-labelledby="settings-account-title">
          <h2 id="settings-account-title" class="settings-card__title">账号信息</h2>
          <p class="settings-card__lead muted">
            训练记录与当前登录账号关联；改密与退出只影响登录状态，不删服务器上的历史。
          </p>
          <div class="settings-account-block">
            <dl class="settings-account-dl">
              <div class="settings-account-dl__row">
                <dt class="settings-account-dl__k">用户名</dt>
                <dd class="settings-account-dl__v">
                  <strong class="settings-username">{{ displayUsername }}</strong>
                  <span class="settings-tag muted">当前账号</span>
                </dd>
              </div>
              <div class="settings-account-dl__row">
                <dt class="settings-account-dl__k">注册时间</dt>
                <dd class="settings-account-dl__v">{{ memberSinceLabel || '—' }}</dd>
              </div>
              <div class="settings-account-dl__row settings-account-dl__row--status">
                <dt class="settings-account-dl__k">登录状态</dt>
                <dd class="settings-account-dl__v settings-login">
                  <span class="settings-status-dot" aria-hidden="true" />
                  <span><strong>已登录</strong> · 令牌有效期间保持会话</span>
                </dd>
              </div>
            </dl>
          </div>
        </section>

        <aside class="settings-card settings-card--actions ui-surface" aria-label="账号操作">
          <h2 class="settings-card__title">账号操作</h2>
          <div class="settings-actions-body">
            <div class="settings-action-row">
              <el-button class="settings-btn-primary" type="primary" plain size="large" @click="onChangePassword"
                >修改密码</el-button
              >
              <el-button class="settings-btn-danger" type="danger" plain size="large" @click="onLogout"
                >退出登录</el-button
              >
            </div>
            <p class="ui-callout ui-callout--accent settings-actions-tip">
              建议在个人设备上完成密码修改；退出后需重新登录才能继续训练或查看报告。
            </p>
          </div>
        </aside>

        <section
          class="settings-card settings-card--prefs ui-surface settings-prefs-panel"
          aria-labelledby="settings-prefs-title"
        >
          <div class="settings-prefs-header">
            <h2 id="settings-prefs-title" class="settings-card__title settings-prefs-title">默认训练偏好</h2>
            <p class="settings-prefs-lead muted">
              影响从首页进入训练、首次打开历史等默认态；页面内已有草稿时以当前页为准。
            </p>
          </div>

          <div class="settings-prefs-form">
          <div class="settings-prefs-block">
            <div class="settings-prefs-block-head">
              <span class="settings-prefs-label">默认评分模式</span>
              <el-radio-group v-model="prefsUi.scoring_profile" size="default" @change="persistPrefs">
                <el-radio-button label="defense">答辩</el-radio-button>
                <el-radio-button label="interview">面试</el-radio-button>
              </el-radio-group>
            </div>
            <p class="settings-prefs-hint muted">
              从首页「常规训练」等入口进入训练页时，评分口径的初始选择。
            </p>
          </div>

          <div class="settings-prefs-block">
            <div class="settings-prefs-block-head">
              <span class="settings-prefs-label">默认材料模式</span>
              <el-radio-group v-model="prefsUi.defense_material_mode" size="default" @change="persistPrefs">
                <el-radio-button label="with_ppt">有课件</el-radio-button>
                <el-radio-button label="without_ppt">无课件</el-radio-button>
              </el-radio-group>
            </div>
            <p class="settings-prefs-hint muted">
              无其它来源配置时，训练页默认以有课件或无课件方式开始。
            </p>
          </div>

          <div class="settings-prefs-block settings-prefs-block--switch">
            <div class="settings-prefs-block-head">
              <span class="settings-prefs-label">历史页默认只看有效训练</span>
              <el-switch v-model="prefsUi.history_valid_only_default" @change="persistPrefs" />
            </div>
            <p class="settings-prefs-hint muted">仅影响首次打开历史页时的筛选；页内手动改过则以当前筛选为准。</p>
          </div>

          <div class="settings-prefs-block settings-prefs-block--switch">
            <div class="settings-prefs-block-head">
              <span class="settings-prefs-label">训练页显示新手提示</span>
              <el-switch v-model="prefsUi.show_first_time_hints" @change="persistPrefs" />
            </div>
            <p class="settings-prefs-hint muted">关闭后，针对从未训练场景的引导横幅不再出现。</p>
          </div>

          <div class="settings-prefs-block settings-prefs-block--switch">
            <div class="settings-prefs-block-head">
              <span class="settings-prefs-label">显示最近有效训练提醒</span>
              <el-switch v-model="prefsUi.show_recent_valid_reminder" @change="persistPrefs" />
            </div>
            <p class="settings-prefs-hint muted">关闭后，训练页与最近一次有效训练相关的提醒模块将隐藏。</p>
          </div>

          <div class="settings-prefs-danger">
            <el-button @click="onResetPreferences">恢复默认偏好</el-button>
            <el-button type="warning" plain @click="onClearTrainingLocalState">清除本地草稿与恢复状态</el-button>
          </div>
          <p class="settings-prefs-foot muted">
            「清除」仅移除未开始训练的草稿、运行快照、专项预填与本地会话标记；不会删除服务器上的训练记录与报告。
          </p>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getJson } from '../api/base'
import { pageFeedback, trainingConfirmDanger } from '../utils/pageFeedback'
import {
  readAppPreferences,
  writeAppPreferences,
  resetAppPreferencesToFactory,
  clearTrainingLocalDraftAndResumeState,
  preferencesSnapshotForLog,
} from '../utils/appPreferences'
import { hydrateAccountSettings, pushFullAccountSettingsToServer } from '../utils/accountSettingsSync'
import { getAuthUser } from '../utils/authSession'
import { confirmAndPerformLogout } from '../utils/authLogout'

const router = useRouter()

const loading = ref(true)
const loadError = ref('')
const summary = ref(null)

const prefsUi = ref(readAppPreferences())

const displayUsername = computed(() => {
  const u = summary.value?.username || getAuthUser()?.username
  return u ? String(u) : '同学'
})

const memberSinceLabel = computed(() => {
  const raw = summary.value?.created_at
  if (raw == null || String(raw).trim() === '') return ''
  try {
    return new Date(raw).toLocaleString()
  } catch {
    return String(raw)
  }
})

async function loadAccount() {
  loading.value = true
  loadError.value = ''
  try {
    try {
      await hydrateAccountSettings()
    } catch (_) {}
    prefsUi.value = readAppPreferences()
    const sum = await getJson('/profile/summary')
    summary.value = sum
  } catch (e) {
    summary.value = null
    loadError.value =
      e && e.message ? String(e.message).slice(0, 200) : '加载失败，请检查网络或稍后重试。'
  } finally {
    loading.value = false
  }
}

async function persistPrefs() {
  const next = writeAppPreferences({ ...prefsUi.value })
  prefsUi.value = next
  console.log('[Settings.prefs] changed=', preferencesSnapshotForLog(next))
  try {
    await pushFullAccountSettingsToServer()
    pageFeedback('Settings', 'settings_changed', '已保存并同步到账号。', 'success')
  } catch (_) {
    pageFeedback(
      'Settings',
      'settings_sync_failed',
      '偏好已保存在本机，同步到账号失败，请检查网络后重试。',
      'warning'
    )
  }
}

async function onResetPreferences() {
  const ok = await trainingConfirmDanger({
    title: '恢复默认偏好',
    message: '将所有偏好恢复为系统默认。确定继续？',
    confirmButtonText: '恢复默认',
    cancelButtonText: '取消',
  })
  if (!ok) return
  prefsUi.value = resetAppPreferencesToFactory()
  console.log('[Settings.prefs] reset=', preferencesSnapshotForLog(prefsUi.value))
  try {
    await pushFullAccountSettingsToServer()
    pageFeedback('Settings', 'reset_preferences', '已恢复为默认设置并同步到账号。', 'success')
  } catch (_) {
    pageFeedback(
      'Settings',
      'settings_sync_failed',
      '默认偏好已应用在本机，同步到账号失败，请稍后重试。',
      'warning'
    )
  }
}

async function onClearTrainingLocalState() {
  const ok = await trainingConfirmDanger({
    title: '清除本地草稿与恢复状态',
    message:
      '将清除未开始训练的草稿、运行快照、首页带入的专项预填，以及本地会话标记。服务器上的训练记录与报告不会删除。确定继续？',
    confirmButtonText: '清除',
    cancelButtonText: '取消',
  })
  if (!ok) return
  const cleared = clearTrainingLocalDraftAndResumeState()
  console.log('[Settings.local] clear_draft=', cleared)
  pageFeedback('Settings', 'clear_training_local', '已清除本地草稿与恢复相关状态。', 'success')
}

function onChangePassword() {
  router.push({ name: 'ChangePassword' })
}

async function onLogout() {
  await confirmAndPerformLogout(router)
}

onMounted(() => {
  console.log('[Settings] opened')
  loadAccount()
})
</script>

<style scoped>
.settings-page {
  width: 100%;
  max-width: min(var(--app-content-max-width, 1360px), 100%);
  margin: 0 auto;
  box-sizing: border-box;
}

.settings-hero {
  margin-bottom: var(--ui-stack-gap-sm, 16px);
}

.settings-hero__eyebrow {
  margin: 0 0 8px;
  font-size: var(--font-xs, 14px);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ui-text-muted);
}

.settings-hero__title {
  margin: 0 0 10px;
  font-size: clamp(2rem, 2.6vw, 2.5rem);
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.2;
  color: var(--ui-text-primary);
}

.settings-hero__sub {
  margin: 0;
  max-width: 42rem;
  font-size: var(--font-base, 17px);
  line-height: 1.65;
  color: var(--ui-text-secondary);
}

.settings-loading {
  margin-top: 12px;
}

.settings-dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--ui-stack-gap, 22px);
}

.settings-alert__body {
  margin: 0 0 12px;
  font-size: var(--font-base, 17px);
  line-height: 1.6;
}

.settings-dash-grid {
  display: grid;
  gap: var(--ui-stack-gap, 22px);
  align-items: start;
}

@media (min-width: 1280px) {
  .settings-dash-grid {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    grid-template-areas:
      'account actions'
      'prefs prefs';
    column-gap: 28px;
  }

  .settings-card--account {
    grid-area: account;
  }

  .settings-card--actions {
    grid-area: actions;
  }

  .settings-card--prefs {
    grid-area: prefs;
  }
}

.settings-card {
  padding: var(--ui-card-pad-y, 22px) var(--ui-card-pad-x, 24px);
  border-radius: var(--ui-radius-lg);
  min-width: 0;
  width: 100%;
  box-sizing: border-box;
}

.settings-card__title {
  margin: 0 0 12px;
  font-size: clamp(1.25rem, 1.5vw, 1.45rem);
  font-weight: 800;
  letter-spacing: -0.015em;
  color: var(--ui-text-primary);
  line-height: 1.25;
}

.settings-card__lead {
  margin: 0 0 14px;
  font-size: var(--font-base, 17px);
  line-height: 1.65;
  max-width: none;
}

.settings-account-block {
  padding-top: 14px;
  border-top: 1px solid var(--ui-border);
}

.settings-account-dl {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.settings-account-dl__row {
  display: grid;
  grid-template-columns: minmax(88px, 110px) minmax(0, 1fr);
  gap: 10px 16px;
  align-items: start;
}

.settings-account-dl__k {
  margin: 0;
  font-size: var(--font-sm, 15px);
  font-weight: 700;
  color: var(--ui-text-muted);
}

.settings-account-dl__v {
  margin: 0;
  font-size: var(--font-base, 17px);
  line-height: 1.55;
  color: var(--ui-text-primary);
  min-width: 0;
}

.settings-username {
  font-size: var(--font-xl, 22px);
  font-weight: 800;
  letter-spacing: -0.02em;
}

.settings-tag {
  margin-left: 8px;
  font-size: var(--font-sm, 15px);
  font-weight: 500;
}

.settings-login {
  margin: 0;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: var(--font-base, 17px);
  line-height: 1.55;
  color: var(--ui-text-secondary);
}

.settings-status-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--el-color-success);
  margin-top: 0.45rem;
  flex-shrink: 0;
}

.settings-card--actions {
  border-top: 3px solid var(--ui-accent-muted);
}

@media (min-width: 1280px) {
  .settings-card--actions {
    border-top: none;
    border-left: 3px solid var(--ui-accent-muted);
  }
}

.settings-actions-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-items: stretch;
}

.settings-actions-tip {
  margin: 0;
}

.settings-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 12px;
  align-items: center;
}

.settings-btn-primary.el-button {
  font-size: var(--font-base, 17px);
  font-weight: 700;
  min-height: 44px;
  padding: 10px 20px;
}

.settings-btn-danger.el-button {
  font-size: var(--font-base, 17px);
  font-weight: 600;
  min-height: 44px;
  padding: 10px 20px;
}

.settings-prefs-panel {
  background: var(--ui-surface);
  border: 1px solid var(--ui-card-border);
}

.settings-prefs-header {
  margin-bottom: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--ui-border);
}

.settings-prefs-title {
  margin-bottom: 8px;
}

.settings-prefs-lead {
  margin: 0;
  font-size: var(--font-base, 17px);
  line-height: 1.65;
  max-width: 56rem;
}

.settings-prefs-form {
  margin: 0;
  border-radius: var(--ui-radius-md);
  background: var(--ui-surface-subtle);
  border: 1px solid var(--ui-border);
  padding: 18px 20px 20px;
  box-sizing: border-box;
}

.settings-prefs-block {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--ui-border);
}

.settings-prefs-block:last-of-type {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.settings-prefs-block-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px 16px;
  margin-bottom: 8px;
  min-width: 0;
}

.settings-prefs-block--switch .settings-prefs-block-head {
  align-items: center;
}

.settings-prefs-label {
  font-size: var(--font-base, 17px);
  font-weight: 700;
  color: var(--ui-text-primary);
}

.settings-prefs-hint {
  margin: 0;
  font-size: var(--font-sm, 15px);
  line-height: 1.6;
}

.settings-prefs-danger {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px dashed var(--ui-border);
}

.settings-prefs-danger .el-button {
  font-size: var(--font-sm, 15px);
}

.settings-prefs-foot {
  margin: 12px 0 0;
  font-size: var(--font-sm, 15px);
  line-height: 1.55;
}

@media (max-width: 520px) {
  .settings-account-dl__row {
    grid-template-columns: 1fr;
    gap: 4px;
  }
}

@media (max-width: 640px) {
  .settings-action-row {
    flex-direction: column;
    align-items: stretch;
  }

  .settings-action-row .el-button {
    width: 100%;
    margin: 0;
  }
}
</style>
