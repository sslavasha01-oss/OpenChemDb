import { useUserStore } from '@/stores/user'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export async function apiRequest(endpoint, options = {}) {
  const userStore = useUserStore()

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  // Если юзер залогинен, добавляем Bearer токен текущего аккаунта
  if (userStore.isLoggedIn && userStore.currentUser.token) {
    headers['Authorization'] = `Bearer ${userStore.currentUser.token}`
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  if (response.status === 401) {
    // Тут можно добавить логику авто-разлогина при протухшем токене
    console.error('Unauthorized')
  }

  return response
}