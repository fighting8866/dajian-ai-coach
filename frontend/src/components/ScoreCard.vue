<template>
  <div class="score-card">
    <h2>综合评分</h2>
    <div class="score-value">{{ overallScore }}</div>
    <div class="score-level" :class="getScoreLevel(overallScore)">
      {{ getScoreText(overallScore) }}
    </div>
  </div>
</template>

<script setup>
import { defineProps } from 'vue'

const props = defineProps({
  overallScore: {
    type: Number,
    default: 0
  }
})

const getScoreLevel = (score) => {
  if (score >= 90) return 'excellent'
  if (score >= 80) return 'good'
  if (score >= 70) return 'average'
  return 'needs-improvement'
}

const getScoreText = (score) => {
  if (score >= 90) return '优秀'
  if (score >= 80) return '良好'
  if (score >= 70) return '一般'
  return '需要改进'
}
</script>

<style scoped>
.score-card {
  width: 300px;
  height: 200px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  margin-bottom: 30px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

h2 {
  margin: 0 0 10px 0;
  font-size: 1.2em;
  opacity: 0.9;
}

.score-value {
  font-size: 3em;
  font-weight: bold;
  margin: 10px 0;
}

.score-level {
  font-size: 1.1em;
  padding: 5px 15px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.2);
}

.excellent {
  background: rgba(76, 175, 80, 0.3);
}

.good {
  background: rgba(33, 150, 243, 0.3);
}

.average {
  background: rgba(255, 193, 7, 0.3);
}

.needs-improvement {
  background: rgba(244, 67, 54, 0.3);
}
</style>