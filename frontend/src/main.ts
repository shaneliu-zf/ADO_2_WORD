import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import { definePreset } from '@primevue/themes'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Tooltip from 'primevue/tooltip'
import 'primeicons/primeicons.css'
import './styles.css'

import App from './App.vue'
import router from './router'

// IBM Design Language blue scale anchored at #0F62FE on the 500 slot
const IbmBluePreset = definePreset(Aura, {
  semantic: {
    primary: {
      50: '#edf5ff',
      100: '#d0e2ff',
      200: '#a6c8ff',
      300: '#78a9ff',
      400: '#4589ff',
      500: '#0F62FE',
      600: '#0043ce',
      700: '#002d9c',
      800: '#001d6c',
      900: '#001141',
      950: '#000a2e',
    },
  },
})

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: IbmBluePreset,
    options: {
      // 關掉系統深色模式；沒有切換 UI，一律淺色
      darkModeSelector: false,
    },
  },
})
app.use(ToastService)
app.use(ConfirmationService)
app.directive('tooltip', Tooltip)

app.mount('#app')
