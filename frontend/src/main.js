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

axios.interceptors.response.use(
  (response) => response, // Если всё хорошо, просто возвращаем ответ
  (error) => {
    // Проверяем, что ошибка именно 401 (Unauthorized)
    if (error.response && error.response.status === 401) {
      const userStore = useUserStore()

      // 1. Очищаем данные пользователя в сторе (и токены)
      userStore.logout?.() // Если есть метод logout, вызываем его
      localStorage.removeItem('token')

      // 2. Перенаправляем на страницу логина
      // Проверяем, чтобы не редиректить бесконечно, если мы уже на странице логина
      if (router.currentRoute.value.path !== '/login') {
        router.push('/login')
      }
    }
    return Promise.reject(error)
  }
)

app.use(router)

app.mount('#app')
