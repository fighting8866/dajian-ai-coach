<template>
  <main id="main-content" class="auth-page" tabindex="-1">
    <a href="#auth-login-form" class="a11y-skip-link">跳到登录表单</a>
    <div class="auth-card">
      <h1 class="auth-title">答见</h1>
      <p id="auth-login-desc" class="auth-sub muted">{{ AUTH_COPY.loginSubtitle }}</p>

      <div class="a11y-sr-only" aria-live="polite" aria-atomic="true">{{ loginAnnounce }}</div>

      <el-form
        id="auth-login-form"
        ref="formRef"
        class="auth-form"
        label-position="top"
        :model="form"
        :rules="rules"
        :validate-on-rule-change="false"
        :aria-busy="loading"
        aria-describedby="auth-login-desc"
        @submit.prevent="onSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            id="auth-login-username"
            v-model="form.username"
            :placeholder="AUTH_COPY.usernamePlaceholderLogin"
            maxlength="32"
            clearable
            autocomplete="username"
            name="username"
            @input="onAuthFieldInput"
          />
        </el-form-item>
        <el-form-item label="密码" prop="password" :error="apiFieldError || undefined">
          <el-input
            id="auth-login-password"
            ref="passwordInputRef"
            v-model="form.password"
            type="password"
            :placeholder="AUTH_COPY.passwordPlaceholderLogin"
            maxlength="72"
            show-password
            autocomplete="current-password"
            name="password"
            :aria-invalid="apiFieldError ? 'true' : 'false'"
            :aria-describedby="passwordDescribedBy"
            @input="onAuthFieldInput"
          />
          <span
            v-if="apiFieldError"
            id="auth-login-password-errtext"
            class="a11y-sr-only"
            role="alert"
            >{{ apiFieldError }}</span>
        </el-form-item>
        <el-button
          type="primary"
          class="auth-submit"
          native-type="submit"
          :loading="loading"
          :disabled="loading"
          :loading-text="AUTH_COPY.loginLoading"
          size="large"
        >
          登录
        </el-button>
      </el-form>

      <p class="auth-foot muted">
        还没有账号？
        <router-link to="/register" class="auth-link">注册</router-link>
      </p>
    </div>
  </main>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { postJson } from '../api/base'
import { setAuthToken, setAuthUser } from '../utils/authSession'
import { AUTH_COPY } from '../constants/productTerms'

const route = useRoute()
const router = useRouter()

const formRef = ref(null)
const form = reactive({
  username: '',
  password: '',
})
const apiFieldError = ref('')
const loading = ref(false)
const passwordInputRef = ref(null)
const loginAnnounce = ref('')

const passwordDescribedBy = computed(() => {
  const ids = ['auth-login-desc']
  if (apiFieldError.value) ids.push('auth-login-password-errtext')
  return ids.join(' ')
})

watch(apiFieldError, (msg) => {
  if (msg) loginAnnounce.value = msg
})

watch(loading, (busy) => {
  if (busy) loginAnnounce.value = AUTH_COPY.loginLoading
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

function onAuthFieldInput() {
  apiFieldError.value = ''
}

function friendlyError(e) {
  const raw = e?.message || String(e)
  const m = raw.match(/body:\s*(\{[\s\S]*\})\s*$/i)
  if (m) {
    try {
      const j = JSON.parse(m[1])
      if (j.detail) {
        if (typeof j.detail === 'string') return j.detail
        if (Array.isArray(j.detail) && j.detail[0]?.msg) return j.detail.map((x) => x.msg).join('；')
      }
    } catch (_) {}
  }
  if (/401/.test(raw)) return AUTH_COPY.errBadCredentials
  return AUTH_COPY.errLoginGeneric
}

async function onSubmit() {
  apiFieldError.value = ''
  const fr = formRef.value
  if (!fr) return
  try {
    await fr.validate()
  } catch {
    return
  }
  const u = String(form.username || '').trim()
  const p = String(form.password || '')
  loading.value = true
  try {
    const data = await postJson('/auth/login', { username: u, password: p })
    setAuthToken(data.access_token)
    setAuthUser(data.user)
    ElMessage.success(AUTH_COPY.loginSuccess)
    const redir = route.query.redirect
    const path = typeof redir === 'string' && redir.startsWith('/') ? redir : '/home'
    router.replace(path)
  } catch (e) {
    apiFieldError.value = friendlyError(e)
    await nextTick()
    try {
      passwordInputRef.value?.focus?.()
    } catch (_) {}
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: linear-gradient(160deg, #f8fafc 0%, #e0e7ff 45%, #f1f5f9 100%);
}

.auth-card {
  width: 100%;
  max-width: 400px;
  padding: 36px 32px 28px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.08);
  border: 1px solid #e2e8f0;
}

.auth-title {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
  color: #0f172a;
  text-align: center;
}

.auth-sub {
  margin: 8px 0 24px;
  text-align: center;
  font-size: 0.9rem;
}

.auth-form {
  margin-top: 8px;
}

.auth-submit {
  width: 100%;
  margin-top: 8px;
}

.auth-foot {
  margin: 20px 0 0;
  text-align: center;
  font-size: 0.88rem;
}

.auth-link {
  color: #2563eb;
  font-weight: 600;
  text-decoration: none;
}

.auth-link:hover {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .auth-page {
    padding: 16px 14px;
    align-items: flex-start;
    padding-top: max(24px, env(safe-area-inset-top, 0px));
  }

  .auth-card {
    padding: 28px 20px 22px;
    border-radius: var(--ui-radius-lg);
    max-width: 100%;
  }

  .auth-title {
    font-size: 1.55rem;
  }
}

@media (max-width: 480px) {
  .auth-card {
    padding: 22px 16px 20px;
  }

  .auth-sub {
    font-size: 0.86rem;
  }
}
</style>
