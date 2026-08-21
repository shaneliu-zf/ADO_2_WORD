<template>
  <Dialog
    v-model:visible="visible"
    :header="required ? '請先填寫設定' : '設定'"
    modal
    :closable="!required"
    :closeOnEscape="!required"
    :style="{ width: '40rem' }"
    @show="loadConfig"
  >
    <div v-if="loading" class="state-msg">
      <ProgressSpinner style="width:2rem;height:2rem" />
      <span>載入中…</span>
    </div>
    <div v-else class="form">
      <p v-if="required" class="hint">找不到 backend/secrets/config.json，請填寫後儲存。</p>
      <div class="field">
        <label for="cfg-org">ADO 組織</label>
        <InputText id="cfg-org" v-model="form.organization" class="w-full" />
      </div>
      <div class="field">
        <label for="cfg-project">ADO 專案</label>
        <InputText id="cfg-project" v-model="form.project" class="w-full" />
      </div>
      <div class="field">
        <label for="cfg-pat">PAT</label>
        <Password
          id="cfg-pat"
          v-model="form.pat"
          class="secret-input"
          inputClass="secret-field"
          fluid
          toggleMask
          :feedback="false"
        />
      </div>
      <div class="field">
        <label for="cfg-bob">IBM Bob API Key</label>
        <Password
          id="cfg-bob"
          v-model="form.bob_api_key"
          class="secret-input"
          inputClass="secret-field"
          fluid
          toggleMask
          :feedback="false"
        />
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </div>
    <template #footer>
      <Button v-if="!required" label="取消" outlined severity="secondary" @click="visible = false" />
      <Button label="儲存" icon="pi pi-save" :loading="saving" :disabled="loading" @click="handleSave" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import { fetchConfig, updateConfig } from '@/api/client'
import { errorMessage } from '@/utils/apiError'
import type { AppConfig } from '@/types'

const visible = defineModel<boolean>('visible', { default: false })
defineProps<{
  required?: boolean
}>()
const emit = defineEmits<{
  saved: []
}>()
const toast = useToast()
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const form = reactive<AppConfig>({
  organization: '',
  project: '',
  pat: '',
  ado_base_url: 'https://dev.azure.com',
  bob_api_key: '',
})

function applyForm(data: AppConfig) {
  form.organization = data.organization || ''
  form.project = data.project || ''
  form.pat = data.pat || ''
  form.ado_base_url = data.ado_base_url || 'https://dev.azure.com'
  form.bob_api_key = data.bob_api_key || ''
}

async function loadConfig() {
  loading.value = true
  error.value = ''
  try {
    applyForm(await fetchConfig())
  } catch (err) {
    error.value = `載入失敗：${errorMessage(err)}`
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  error.value = ''
  try {
    applyForm(await updateConfig({ ...form }))
    toast.add({ severity: 'success', summary: '已儲存設定', life: 3000 })
    visible.value = false
    emit('saved')
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.hint {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.5;
  color: var(--p-text-secondary-color);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.field label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--p-text-secondary-color);
}

.w-full {
  width: 100%;
}

:deep(.secret-input),
:deep(.p-password) {
  display: flex;
  width: 100%;
}

:deep(.secret-field),
:deep(.p-password-input),
:deep(.p-password input) {
  flex: 1 1 auto;
  width: 100%;
  min-width: 0;
}

.state-msg {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0;
  color: var(--p-text-secondary-color);
}

.error {
  margin: 0;
  color: var(--p-red-500);
  font-size: 0.88rem;
}
</style>
