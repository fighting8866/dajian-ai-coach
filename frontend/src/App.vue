<template>
  <div class="app-container app-root-v1">
    <router-view :key="appRootViewKey" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
/** 仅「登录/注册等 guest」与「已登录 AppShell」之间换根时重挂载，避免在壳内 /home↔/training 时整树重挂导致异常。 */
const appRootViewKey = computed(() =>
  route.matched.some((r) => r?.meta && r.meta.requiresAuth) ? 'app-authed' : 'app-guest',
)
</script>

<style>
.app-container {
  width: 100%;
  min-height: 100vh;
  font-family: var(--brand-font-sans);
  background: var(--brand-canvas);
  color: var(--ui-text-primary);
}

.app-root-v1 {
  text-rendering: optimizeLegibility;
}
</style>