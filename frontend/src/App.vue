<template>
  <Toast />
  <ConfirmDialog :baseZIndex="3000" />
  <RouterView />
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
</script>
