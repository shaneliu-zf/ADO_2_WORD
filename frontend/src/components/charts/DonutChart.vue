<template>
  <div class="chart-row">
    <svg viewBox="0 0 42 42" class="donut">
      <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="var(--p-surface-200)" stroke-width="6" />
      <circle
        v-for="ring in rings"
        :key="ring.label"
        cx="21"
        cy="21"
        r="15.915"
        fill="transparent"
        :stroke="ring.color"
        stroke-width="6"
        :stroke-dasharray="ring.dash"
        :stroke-dashoffset="ring.offset"
        class="donut-slice"
        @click="emit('select', ring)"
      />
      <text x="21" y="22.5" text-anchor="middle" class="donut-total">{{ total }}</text>
    </svg>
    <ul class="legend">
      <li v-for="s in slices" :key="s.label">
        <button type="button" @click="emit('select', s)">
          <i :style="{ background: s.color }" />{{ s.label }}<b>{{ s.value }}</b>
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Slice } from '@/composables/useDashboardStats'

const props = defineProps<{
  slices: Slice[]
  total: number
}>()

const emit = defineEmits<{
  select: [slice: Slice]
}>()

const rings = computed(() => {
  const total = props.slices.reduce((sum, s) => sum + s.value, 0)
  let offset = 25
  return props.slices.map(slice => {
    const pct = total ? (slice.value / total) * 100 : 0
    const ring = { ...slice, dash: `${pct} ${100 - pct}`, offset }
    offset -= pct
    return ring
  })
})
</script>

<style scoped>
.chart-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.donut {
  width: 140px;
  height: 140px;
  flex-shrink: 0;
}
.donut-total {
  font-size: 7px;
  fill: var(--p-text-color, #222);
  font-weight: 650;
}
.legend {
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.donut-slice { cursor: pointer; }
.legend button {
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
.legend i {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex-shrink: 0;
}
.legend b {
  margin-left: auto;
  font-variant-numeric: tabular-nums;
}
</style>
