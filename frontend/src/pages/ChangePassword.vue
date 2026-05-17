<template>
  <main id="main-content" class="auth-page change-password-page" tabindex="-1">
    <div class="auth-card">
      <p class="change-pw-eyebrow muted">账号安全</p>
      <h1 class="auth-title">修改密码</h1>
      <p class="auth-sub muted">请使用当前密码验证身份。新密码请至少 6 位，并与当前密码不同。</p>

      <el-form
        ref="formRef"
        class="auth-form"
        label-position="top"
        :model="form"
        :rules="rules"
        @submit.prevent="onSubmit"
      >
        <el-form-item label="当前密码" prop="current_password">
          <el-input
            v-model="form.current_password"
            type="password"
            maxlength="72"
            show-password
            autocomplete="current-password"
            placeholder="请输入当前密码"
          />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="form.new_password"
            type="password"
            maxlength="72"
            show-password
            autocomplete="new-password"
            placeholder="至少 6 位"
          />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input
            v-model="form.confirm_password"
            type="password"
            maxlength="72"
            show-password
            autocomplete="new-password"
            placeholder="再次输入新密码"
          />
        </el-form-item>
        <el-button
          type="primary"
          class="auth-submit"
          native-type="submit"
          :loading="loading"
          :disabled="loading"
          size="large"
        >
          保存新密码
        </el-button>
      </el-form>

      <p class="auth-foot muted">
        <router-link to="/settings" class="auth-link">返回设置中心</router-link>
      </p>
    </div>
  </main>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { postJson } from '../api/base'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  current_password: '',
  new_password: '',
  confirm_password: '',
})

const validateConfirm = (_rule, value, callback) => {
  if (!value) {
    callback(new Error('请再次输入新密码'))
    return
  }
  if (value !== form.new_password) {
    callback(new Error('两次输入的新密码不一致'))
    return
  }
  callback()
}

const validateNew = (_rule, value, callback) => {
  if (!value) {
    callback(new Error('请输入新密码'))
    return
  }
  if (String(value).length < 6) {
    callback(new Error('新密码至少 6 位'))
    return
  }
  if (value === form.current_password) {
    callback(new Error('新密码不能与当前密码相同'))
    return
  }
  callback()
}

const rules = {
  current_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [{ validator: validateNew, trigger: 'blur' }],
  confirm_password: [{ validator: validateConfirm, trigger: 'blur' }],
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
  if (/401/.test(raw)) return '登录已失效，请重新登录后再修改密码。'
  if (/403|400/.test(raw)) return '无法完成修改，请检查当前密码与新密码是否符合要求。'
  return '修改密码失败，请稍后重试或检查网络。'
}

async function onSubmit() {
  const fr = formRef.value
  if (!fr) return
  try {
    await fr.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    await postJson('/auth/change-password', {
      current_password: form.current_password,
      new_password: form.new_password,
    })
    ElMessage.success('密码已更新，请牢记新密码。')
    router.replace('/settings')
  } catch (e) {
    ElMessage.error(friendlyError(e))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.change-password-page .auth-card {
  max-width: 420px;
}

.change-pw-eyebrow {
  margin: 0 0 0.25rem;
  font-size: 0.82rem;
  letter-spacing: 0.04em;
}
</style>
