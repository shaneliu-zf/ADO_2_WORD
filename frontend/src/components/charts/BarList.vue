<template>
  <ul class="bars">
    <li v-for="row in rows" :key="row.label">
      <button type="button" class="bar-row" @click="emit('select', row)">
        <span class="bar-label">{{ row.label }}</span>
        <span class="bar-track">
          <span class="bar-fill" :style="{ width: barWidth(row.value) }" />
        </span>
        <span class="bar-n">{{ row.value }} 張</span>
      </button>
    </li>
  </ul>
</template>

<script setup lang="ts">
import type { CountRow } from '@/composables/useDashboardStats'

const props = defineProps<{
  rows: CountRow[]
}>()

const emit = defineEmits<{
  select: [row: CountRow]
}>()

function barWidth(value: number): string {
  const max = Math.max(1, ...props.rows.map(r => r.value))
  return `${(value / max) * 100}%`
}
</script>

<style scoped>
.bars {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.bar-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  border: 0;
  background: none;
  padding: 0;
  cursor: pointer;
  font: inherit;
  color: inherit;
  text-align: left;
}
.bar-label {
  width: 120px;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bar-track {
  flex: 1;
  min-width: 48px;
  height: 10px;
  background: var(--p-surface-200, #e5e7eb);
  border-radius: 99px;
  overflow: hidden;
}
.bar-fill {
  display: block;
  height: 100%;
  background: var(--p-blue-500);
  border-radius: 99px;
}
.bar-n {
  margin-left: auto;
  width: 4.5rem;
  text-align: right;
  color: var(--p-text-muted-color);
  font-variant-numeric: tabular-nums;
}
</style>
