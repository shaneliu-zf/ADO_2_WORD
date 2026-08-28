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
    <p class="guide">
      請參考
      <a href="/docs/設定說明.docx" target="_blank" rel="noopener">設定說明</a>
    </p>
    <div v-if="loading" class="state-msg">
      <ProgressSpinner style="width:2rem;height:2rem" />
      <span>載入中…</span>
    </div>
    <div v-else class="form">
      <p v-if="required" class="hint">找不到 backend/secrets/config.json。要對外展示可只開展示模式後儲存；連客戶環境則請填 ADO 與 Bob。</p>
      <div class="field">
        <label for="cfg-demo">展示模式</label>
        <div class="demo-row">
          <ToggleSwitch inputId="cfg-demo" v-model="form.demo_mode" />
          <span class="demo-help">用虛構的 ADO 與 Word 範本，不連客戶 Azure DevOps，產生報告也不呼叫 Bob。</span>
        </div>
      </div>
      <template v-if="!form.demo_mode">
        <div class="field">
          <label for="cfg-org">ADO 組織</label>
          <InputText id="cfg-org" v-model="form.organization" class="w-full" />
        </div>
        <div class="field">
          <label for="cfg-project">ADO 專案</label>
          <InputText id="cfg-project" v-model="form.project" class="w-full" />
        </div>
        <div class="field">
          <label for="cfg-pat">ADO Personal Access Token</label>
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
      </template>
      <p v-else class="hint">展示專案為虛構的 LumenWMS（倉儲系統）。請重新「載入 ID」後再跑流程，清單才會換成假資料。</p>
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
import ToggleSwitch from 'primevue/toggleswitch'
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
  demo_mode: false,
})

function applyForm(data: AppConfig) {
  form.organization = data.organization || ''
  form.project = data.project || ''
  form.pat = data.pat || ''
  form.ado_base_url = data.ado_base_url || 'https://dev.azure.com'
  form.bob_api_key = data.bob_api_key || ''
  form.demo_mode = !!data.demo_mode
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

.demo-row {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.demo-help {
  font-size: 0.88rem;
  line-height: 1.45;
  color: var(--p-text-secondary-color);
}

.guide {
  margin: 0 0 0.85rem;
  font-size: 0.88rem;
  line-height: 1.5;
  color: var(--p-text-color);
}

.guide a {
  color: var(--p-primary-color, #2563eb);
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
