import { nextTick } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { getAuthToken } from '../utils/authSession'
import { focusMainContent } from '../utils/a11yFocus'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/Login.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../pages/Register.vue'),
    meta: { guestOnly: true },
  },
  /**
   * 已登录后 canonical 子路径（与 AppShell 主菜单一一对应）：
   * /、/home → Home；/profile；/settings；/training；/history；/report、/result 等见各 name
   */
  {
    path: '/',
    component: () => import('../layouts/AppShell.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: (to) => ({ path: '/home', query: to.query }),
      },
      {
        path: 'home',
        name: 'Home',
        component: () => import('../pages/Home.vue'),
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('../pages/Profile.vue'),
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('../pages/Settings.vue'),
      },
      {
        path: 'change-password',
        name: 'ChangePassword',
        component: () => import('../pages/ChangePassword.vue'),
      },
      {
        path: 'training',
        name: 'Training',
        component: () => import('../pages/Training.vue'),
      },
      {
        path: 'result/:sessionId?',
        name: 'Result',
        component: () => import('../pages/Result.vue'),
      },
      {
        path: 'report/:sessionId?',
        name: 'Report',
        component: () => import('../pages/Report.vue'),
      },
      {
        path: 'history',
        name: 'History',
        component: () => import('../pages/History.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const token = getAuthToken()
  const needAuth = to.matched.some((r) => r.meta.requiresAuth)
  const guestOnly = to.matched.some((r) => r.meta.guestOnly)

  if (needAuth && !token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }
  if (guestOnly && token) {
    next({ path: '/home' })
    return
  }

  // 无会话上下文的 /report 由 Report 页内空态处理，不要重定向到 History，避免 query/提示「串台」
  next()
})

/** 每页进入后将焦点移入主内容，便于读屏与键盘用户从可预期位置继续 Tab。 */
router.afterEach((to, from) => {
  if (to.fullPath === from.fullPath) return
  nextTick(() => {
    focusMainContent()
  })
})

export default router
