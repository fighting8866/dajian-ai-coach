<template>
  <div class="metric-panel">
    <h2>详细指标</h2>
    <div class="metrics-grid">
      <div class="metric-item">
        <div class="metric-label">语速</div>
        <div class="metric-value">{{ metrics.speech_rate || '0字/分钟' }}</div>
      </div>
      <div class="metric-item">
        <div class="metric-label">停顿次数</div>
        <div class="metric-value">{{ metrics.pause_count || 0 }}</div>
      </div>
      <div class="metric-item">
        <div class="metric-label">停顿总时长</div>
        <div class="metric-value">{{ metrics.pause_duration || '0秒' }}</div>
      </div>
      <div class="metric-item">
        <div class="metric-label">口头禅次数</div>
        <div class="metric-value">{{ metrics.口头禅_count || 0 }}</div>
      </div>
      <div class="metric-item">
        <div class="metric-label">正视前方比例</div>
        <div class="metric-value">{{ metrics.eye_contact_ratio || '0%' }}</div>
      </div>
      <div class="metric-item">
        <div class="metric-label">姿态稳定度</div>
        <div class="metric-value">{{ metrics.posture_stability || '不稳定' }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps } from 'vue'

const props = defineProps({
  metrics: {
    type: Object,
    default: () => ({})
  }
})
</script>

<style scoped>
.metric-panel {
  width: 100%;
  max-width: 800px;
  background: white;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

h2 {
  margin: 0 0 20px 0;
  color: #333;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 20px;
}

.metric-item {
  text-align: center;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
}

.metric-label {
  font-size: 0.9em;
  color: #666;
  margin-bottom: 5px;
}

.metric-value {
  font-size: 1.2em;
  font-weight: bold;
  color: #333;
}
</style>