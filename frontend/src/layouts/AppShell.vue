<template>
  <div class="app-shell">
    <a href="#main-content" class="a11y-skip-link">跳到主内容</a>
    <header class="app-shell-header" role="banner">
      <div class="app-shell-brand">
        <router-link to="/home" class="app-shell-logo" aria-label="答见，返回首页">答见</router-link>
        <span class="app-shell-tagline">答辩与演讲训练</span>
      </div>
      <div class="app-shell-header-right">
        <span class="app-shell-session-hint muted" title="登录令牌有效即视为已登录">已登录</span>
        <el-dropdown
          trigger="click"
          class="app-shell-user-dropdown"
          @command="onUserMenuCommand"
          @visible-change="onUserMenuVisible"
        >
          <button
            type="button"
            class="app-shell-user-trigger"
            :aria-expanded="userMenuOpen"
            aria-haspopup="true"
            aria-label="账号菜单"
          >
            <span class="app-shell-user-label">账号</span>
            <strong class="app-shell-user-name">{{ displayName }}</strong>
            <span class="app-shell-user-caret" aria-hidden="true">▾</span>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">我的档案</el-dropdown-item>
              <el-dropdown-item command="settings">设置中心</el-dropdown-item>
              <el-dropdown-item command="password">修改密码</el-dropdown-item>
              <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <div class="app-shell-body">
      <aside class="app-shell-nav" aria-label="主导航">
        <a
          v-for="item in mainNav"
          :key="item.name"
          :href="mainNavItemHref(item.name)"
          class="app-shell-nav-item"
          :class="{ 'is-active': isMainNavItemActive(item.name) }"
          :aria-current="isMainNavItemActive(item.name) ? 'page' : undefined"
          @click.prevent="goMainNav(item.name)"
        >{{ item.label }}</a>
        <a
          v-if="hasReportNavContext"
          :href="reportNavResolvedHref"
          class="app-shell-nav-item"
          :class="{ 'is-active': isReportNavItemActive }"
          :aria-current="isReportNavItemActive ? 'page' : undefined"
          @click.prevent="goReportFromNav"
        >报告</a>
        <span
          v-else
          class="app-shell-nav-item app-shell-nav-item--disabled"
          :title="reportNavDisabledTitle"
          role="text"
          tabindex="0"
          :aria-label="reportNavShortAria"
        >
          报告
        </span>
      </aside>
      <main
        id="main-content"
        class="app-shell-main"
        :data-active-route="String(route.name || '')"
        tabindex="-1"
      >
        <router-view :key="routerViewKey" />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, provide, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { resolveReportRouteSessionId } from '../utils/reportEntryContext'
import { getJson } from '../api/base'
import { clearAuthSession, getAuthUser, setAuthUser } from '../utils/authSession'
import { confirmAndPerformLogout } from '../utils/authLogout'

const router = useRouter()
const route = useRoute()

/** 主导航：用 route.name 与菜单一一对应，不依赖 link 的模糊 isActive。 */
const mainNav = [
  { name: 'Home', label: '首页' },
  { name: 'Profile', label: '我的档案' },
  { name: 'Settings', label: '设置中心' },
  { name: 'Training', label: '训练' },
  { name: 'History', label: '历史' },
]

function isMainNavItemActive(name) {
  return String(route.name || '') === name
}

function mainNavItemHref(name) {
  return router.resolve({ name }).href
}

function goMainNav(name) {
  router.push({ name })
}

/** 与 Report 页同口径：有 URL/LS 会话时侧栏「报告」可点。 */
const hasReportNavContext = computed(() => !!resolveReportRouteSessionId(route))
const reportNavTarget = computed(() => {
  const sid = resolveReportRouteSessionId(route)
  return { name: 'Report', query: { session_id: sid } }
})

const isReportNavItemActive = computed(() => String(route.name || '') === 'Report')

const reportNavResolvedHref = computed(() => {
  if (!hasReportNavContext.value) return '#'
  return router.resolve(reportNavTarget.value).href
})

function goReportFromNav() {
  if (!hasReportNavContext.value) return
  router.push(reportNavTarget.value)
}

/** 子页面随 URL 变；仅 fullPath 避免与 App 根 key 叠加重挂载整壳。 */
const routerViewKey = computed(() => route.fullPath)
const reportNavDisabledTitle =
  '训练报告需绑定某次训练。请先在「训练结果」打开，或到「历史」点某条「查看详情」进入该次结果后，再点「查看训练报告」。'
const reportNavShortAria = '报告：需从某次训练结果中打开。'

const displayName = ref(getAuthUser()?.username || '同学')
const userMenuOpen = ref(false)
function onUserMenuVisible(visible) {
  userMenuOpen.value = visible
}
provide('appDisplayName', displayName)

onMounted(async () => {
  try {
    const me = await getJson('/auth/me')
    displayName.value = me.username || '同学'
    setAuthUser({ id: me.id, username: me.username })
    try {
      const { hydrateAccountSettings } = await import('../utils/accountSettingsSync.js')
      await hydrateAccountSettings()
    } catch (_) {}
  } catch (_) {
    clearAuthSession()
    router.replace({ path: '/login', query: { redirect: route.fullPath } })
  }
})

function onUserMenuCommand(cmd) {
  if (cmd === 'profile') {
    router.push({ name: 'Profile' })
    return
  }
  if (cmd === 'settings') {
    router.push({ name: 'Settings' })
    return
  }
  if (cmd === 'password') {
    router.push({ name: 'ChangePassword' })
    return
  }
  if (cmd === 'logout') {
    confirmAndPerformLogout(router)
  }
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--brand-canvas);
}

.app-shell-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  min-height: 60px;
  height: auto;
  background: var(--app-header-bg);
  border-bottom: 1px solid var(--ui-shell-divider, #e5eaf3);
  flex-shrink: 0;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.05);
}

.app-shell-brand {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 2px;
  padding: 10px 0;
}

.app-shell-logo {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--ui-text-primary);
  text-decoration: none;
  letter-spacing: -0.02em;
  line-height: 1.15;
  transition: color var(--ui-transition);
}

.app-shell-logo:hover {
  color: var(--ui-accent);
}

.app-shell-tagline {
  font-size: var(--font-sm, 15px);
  font-weight: 500;
  line-height: 1.35;
  color: var(--ui-text-secondary);
  letter-spacing: 0.01em;
}

.app-shell-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.app-shell-session-hint {
  font-size: var(--font-sm, 15px);
  white-space: nowrap;
}

.app-shell-user-dropdown {
  font-size: 0.88rem;
}

.app-shell-user-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border: none;
  background: transparent;
  font: inherit;
  font-size: inherit;
  line-height: inherit;
  color: inherit;
  text-align: left;
  cursor: pointer;
  border-radius: var(--ui-radius-md, 8px);
  transition: background-color var(--ui-transition);
}

.app-shell-user-trigger:hover {
  background: var(--ui-surface-subtle);
}

.app-shell-user-trigger:focus-visible {
  outline: 2px solid var(--ui-accent);
  outline-offset: 2px;
}

.app-shell-user-label {
  margin-right: 2px;
  color: var(--ui-text-secondary);
}

.app-shell-user-name {
  color: var(--ui-text-primary);
}

.app-shell-user-caret {
  font-size: 0.65rem;
  color: var(--ui-text-secondary);
  margin-left: 2px;
}

.app-shell-body {
  display: flex;
  flex: 1;
  min-height: 0;
}

.app-shell-nav {
  width: var(--app-nav-width, 276px);
  flex-shrink: 0;
  padding: var(--app-nav-pad-y, 24px) var(--app-nav-pad-x, 16px);
  background: var(--app-nav-bg);
  border-right: 1px solid var(--app-nav-border, var(--ui-shell-divider));
  display: flex;
  flex-direction: column;
  gap: var(--app-nav-item-gap, 10px);
  box-sizing: border-box;
}

.app-shell-nav-item {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  box-sizing: border-box;
  min-height: var(--app-nav-item-min-height, 54px);
  padding: var(--app-nav-item-pad-y, 14px) var(--app-nav-item-pad-x, 22px);
  border-radius: var(--ui-radius-md);
  color: var(--ui-text-primary);
  text-decoration: none;
  font-size: var(--app-nav-item-font-size, 18px);
  font-weight: var(--app-nav-item-font-weight, 600);
  line-height: 1.35;
  letter-spacing: -0.01em;
  transition:
    background-color var(--ui-transition),
    color var(--ui-transition),
    box-shadow var(--ui-transition);
}

.app-shell-nav-item:hover {
  background: rgba(255, 255, 255, 0.72);
  color: var(--ui-text-primary);
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04);
}

.app-shell-nav-item.is-active {
  background: var(--app-nav-active-bg);
  color: var(--app-nav-active-text);
  font-weight: var(--app-nav-item-active-font-weight, 700);
  box-shadow:
    inset 4px 0 0 0 var(--ui-accent),
    0 1px 0 rgba(15, 23, 42, 0.04);
}

.app-shell-nav-item--disabled {
  opacity: 0.5;
  cursor: not-allowed;
  user-select: none;
}

.app-shell-nav-item--disabled:hover {
  background: transparent;
  color: var(--ui-text-secondary);
  box-shadow: none;
}

.app-shell-main {
  flex: 1;
  min-width: 0;
  overflow: auto;
  overflow-x: hidden;
  scroll-behavior: smooth;
  padding: var(--app-main-padding);
  background: var(--brand-canvas-accent);
  box-sizing: border-box;
}
</style>

<style>
/* 打印：仅保留主内容区，隐藏答见壳层（侧栏、顶栏、画布底） */
@media print {
  .a11y-skip-link,
  .app-shell-header,
  .app-shell-nav {
    display: none !important;
  }

  .app-shell {
    min-height: 0 !important;
    background: #fff !important;
  }

  .app-shell-body {
    display: block !important;
  }

  .app-shell-main {
    padding: 0 !important;
    margin: 0 !important;
    overflow: visible !important;
    background: #fff !important;
  }
}
</style>
