import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
import axios from 'axios'
import { useUserStore } from '@/stores/user'

axios.interceptors.request.use(config => {
  const userStore = useUserStore()
  if (userStore.isLoggedIn && userStore.currentUser.token) {
    config.headers.Authorization = `Bearer ${userStore.currentUser.token}`
  }
  return config
})
app.use(router)

app.mount('#app')
