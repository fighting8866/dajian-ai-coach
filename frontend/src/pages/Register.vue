<template>
  <main id="main-content" class="auth-page" tabindex="-1">
    <a href="#auth-register-form" class="a11y-skip-link">跳到注册表单</a>
    <div class="auth-card">
      <h1 class="auth-title">{{ AUTH_COPY.registerTitle }}</h1>
      <p id="auth-register-desc" class="auth-sub muted">{{ AUTH_COPY.registerSubtitle }}</p>

      <div class="a11y-sr-only" aria-live="polite" aria-atomic="true">{{ registerAnnounce }}</div>

      <el-form
        id="auth-register-form"
        ref="formRef"
        class="auth-form"
        label-position="top"
        :model="form"
        :rules="rules"
        :validate-on-rule-change="false"
        :aria-busy="loading"
        aria-describedby="auth-register-desc"
        @submit.prevent="onSubmit"
      >
        <el-form-item label="用户名" prop="username" :error="apiFieldError || undefined">
          <el-input
            id="auth-register-username"
            ref="registerUsernameRef"
            v-model="form.username"
            :placeholder="AUTH_COPY.usernamePlaceholderRegister"
            maxlength="32"
            clearable
            autocomplete="username"
            name="username"
            :aria-invalid="apiFieldError ? 'true' : 'false'"
            :aria-describedby="usernameDescribedBy"
            @input="apiFieldError = ''"
          />
          <span v-if="apiFieldError" id="auth-register-user-errtext" class="a11y-sr-only" role="alert">{{
            apiFieldError
          }}</span>
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            id="auth-register-password"
            v-model="form.password"
            type="password"
            :placeholder="AUTH_COPY.passwordPlaceholderRegister"
            maxlength="72"
            show-password
            autocomplete="new-password"
            name="new-password"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="password2">
          <el-input
            id="auth-register-password2"
            v-model="form.password2"
            type="password"
            :placeholder="AUTH_COPY.password2Placeholder"
            maxlength="72"
            show-password
            autocomplete="new-password"
            name="new-password2"
          />
        </el-form-item>
        <el-button
          type="primary"
          class="auth-submit"
          native-type="submit"
          :loading="loading"
          :disabled="loading"
          :loading-text="AUTH_COPY.registerLoading"
          size="large"
        >
          注册并登录
        </el-button>
      </el-form>

      <p class="auth-foot muted">
        已有账号？
        <router-link to="/login" class="auth-link">去登录</router-link>
      </p>
    </div>
  </main>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { postJson } from '../api/base'
import { setAuthToken, setAuthUser } from '../utils/authSession'
import { AUTH_COPY } from '../constants/productTerms'

const router = useRouter()

const formRef = ref(null)
const form = reactive({
  username: '',
  password: '',
  password2: '',
})
const apiFieldError = ref('')
const loading = ref(false)
const registerUsernameRef = ref(null)
const registerAnnounce = ref('')

const usernameDescribedBy = computed(() => {
  const ids = ['auth-register-desc']
  if (apiFieldError.value) ids.push('auth-register-user-errtext')
  return ids.join(' ')
})

watch(apiFieldError, (msg) => {
  if (msg) registerAnnounce.value = msg
})

watch(loading, (busy) => {
  if (busy) registerAnnounce.value = AUTH_COPY.registerLoading
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    {
      pattern: /^[a-zA-Z0-9_]{3,32}$/,
      message: '需为 3–32 位字母、数字或下划线',
      trigger: 'blur',
    },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  password2: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
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
  if (/400/.test(raw)) return AUTH_COPY.errRegisterTaken
  return AUTH_COPY.errRegisterGeneric
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
    const data = await postJson('/auth/register', { username: u, password: p })
    setAuthToken(data.access_token)
    setAuthUser(data.user)
    ElMessage.success(AUTH_COPY.registerSuccess)
    router.replace('/home')
  } catch (e) {
    apiFieldError.value = friendlyError(e)
    await nextTick()
    try {
      registerUsernameRef.value?.focus?.()
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
  background: linear-gradient(160deg, #f8fafc 0%, #dbeafe 40%, #f1f5f9 100%);
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
  font-size: 1.5rem;
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
    font-size: 1.35rem;
  }
}

@media (max-width: 480px) {
  .auth-card {
    padding: 22px 16px 20px;
  }
}
</style>
