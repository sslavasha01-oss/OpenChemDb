<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const mode = ref('login') // 'login', 'register', 'forgot'
const router = useRouter()
const userStore = useUserStore()

const form = ref({ username: '', email: '', password: '', confirmPassword: '' })
const error = ref('')
const message = ref('')

const fieldErrors = ref({}) // Для хранения точечных ошибок полей ({ email: '...', password: '...' })

// Функция для разбора ошибок валидации FastAPI
function handleValidationError(detailArray) {
  const errors = {}
  detailArray.forEach(err => {
    const fieldName = err.loc[err.loc.length - 1]
    errors[fieldName] = err.msg
  })
  fieldErrors.value = errors
}

// Валидация совпадения паролей
const passwordsMatch = computed(() => {
  if (mode.value !== 'register') return true
  if (!form.value.confirmPassword) return true
  return form.value.password === form.value.confirmPassword
})

async function handleSubmit() {
  error.value = ''
  message.value = ''
  fieldErrors.value = {}
  try {
    if (mode.value === 'login') {
      const formData = new FormData()
      formData.append('username', form.value.username)
      // Если включен вход без пароля, шлем заглушку, чтобы Pydantic на бэке не ругался
      const passToSend = userStore.appStatus?.no_password_login ? 'nopassword' : form.value.password
      formData.append('password', passToSend)

      const res = await fetch(`/api/auth/login`, {
        method: 'POST',
        body: formData
      })

      const data = await res.json()
      if (!res.ok) {
        if (Array.isArray(data.detail)) {
          handleValidationError(data.detail)
          throw new Error('Please fix the errors below')
        }
        throw new Error(typeof data.detail === 'string' ? data.detail : 'Login failed')
      }

      userStore.addAccount({
        name: form.value.username,
        username: form.value.username,
        token: data.access_token,
        role: data.role
      })
      router.push('/')

    } else if (mode.value === 'register') {
      if (!passwordsMatch.value) throw new Error('Passwords do not match')

      // Если пароли отключены, шлем заглушку и для регистрации тоже
      const passToSend = userStore.appStatus?.no_password_login ? 'nopassword' : form.value.password

      const res = await fetch(`/api/register-prod`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: form.value.username,
          email: form.value.email,
          password: passToSend
        })
      })

      if (!res.ok) {
        const data = await res.json()
        if (Array.isArray(data.detail)) {
          handleValidationError(data.detail)
          throw new Error('Validation failed')
        }
        throw new Error(typeof data.detail === 'string' ? data.detail : 'Registration failed')
      }
      message.value = userStore.appStatus?.local_mode? 'Registered': 'Check your email for verification!'
      mode.value = 'login'

    } else if (mode.value === 'forgot') {
      // Отправляем POST запрос с JSON в теле
      const res = await fetch(`/api/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: form.value.email }) // Тело запроса
      })

      // Бэкенд всегда возвращает 200 (даже если имейла нет в базе) для безопасности
      const data = await res.json()
      if (!res.ok) {
        if (Array.isArray(data.detail)) {
          handleValidationError(data.detail)
          throw new Error('Validation failed')
        }
        throw new Error(typeof data.detail === 'string' ? data.detail : 'Something went wrong')
      }
      message.value = data.message || 'Instructions have been sent to your email'

      // Возвращаем пользователя на форму логина через 5 секунд
      setTimeout(() => {
        mode.value = 'login'
        message.value = ''
      }, 5000)
    }
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <div class="auth-container">
    <div class="tabs" v-if="mode !== 'forgot'">
      <button :class="{ active: mode === 'login' }" @click="mode = 'login'">Login</button>
      <button :class="{ active: mode === 'register' }" @click="mode = 'register'">Register</button>
    </div>

    <div v-else class="forgot-header">
      <h3>Reset Password</h3>
    </div>

    <form @submit.prevent="handleSubmit" class="auth-form">
      <div v-if="error" class="error">{{ error }}</div>
      <div v-if="message" class="success">{{ message }}</div>

      <template v-if="mode !== 'forgot'">
        <input v-model="form.username" placeholder="Username" required />
        <span v-if="fieldErrors.username" class="field-error">{{ fieldErrors.username }}</span>

        <template v-if="mode === 'register'">
          <input v-model="form.email" type="email" placeholder="Email" required />
          <span v-if="fieldErrors.email" class="field-error">{{ fieldErrors.email }}</span>
        </template>

        <template v-if="!userStore.appStatus?.no_password_login">
          <input
            v-model="form.password"
            type="password"
            placeholder="Password"
            :required="!userStore.appStatus?.no_password_login"
          />
          <span v-if="fieldErrors.password" class="field-error">{{ fieldErrors.password }}</span>
        </template>

        <template v-if="mode === 'register' && !userStore.appStatus?.no_password_login">
          <input
            v-model="form.confirmPassword"
            type="password"
            placeholder="Confirm Password"
            :required="mode === 'register' && !userStore.appStatus?.no_password_login"
          />
          <span v-if="!passwordsMatch" class="field-error">Passwords don't match</span>
        </template>
      </template>

      <template v-else>
        <p>Enter your email to receive a reset link</p>
        <input v-model="form.email" type="email" placeholder="Your Email" required />
        <span v-if="fieldErrors.email" class="field-error">{{ fieldErrors.email }}</span>
      </template>

      <button type="submit" :disabled="mode === 'register' && !userStore.appStatus?.no_password_login && !passwordsMatch">
        {{ mode === 'login' ? 'Sign In' : (mode === 'register' ? 'Create Account' : 'Send Reset Link') }}
      </button>

      <div class="extra-links">
        <a v-if="mode === 'login' && !userStore.appStatus?.local_mode && !userStore.appStatus?.no_password_login" @click.prevent="mode = 'forgot'" href="#">Forgot password?</a>
        <a v-if="mode === 'forgot'" @click.prevent="mode = 'login'" href="#">Back to Login</a>
      </div>
    </form>
  </div>
</template>

<style scoped>
.auth-container { max-width: 400px; margin: 50px auto; border: 1px solid #ddd; border-radius: 8px; padding: 20px; background: white; }
.tabs { display: flex; margin-bottom: 20px; }
.tabs button { flex: 1; padding: 10px; cursor: pointer; border: none; background: #f0f0f0; transition: 0.3s; }
.tabs button.active { background: #2c3e50; color: white; }

.auth-form { display: flex; flex-direction: column; gap: 12px; }
.auth-form input { padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 1rem; }
.auth-form button { padding: 12px; background: #42b983; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; margin-top: 10px; }
.auth-form button:disabled { background: #a8d5c2; cursor: not-allowed; }

.error { color: #e74c3c; font-size: 0.9rem; font-weight: bold; }
.field-error { color: #e74c3c; font-size: 0.8rem; margin-top: -8px; }
.success { color: #27ae60; font-size: 0.9rem; font-weight: bold; }

.extra-links { margin-top: 15px; text-align: center; }
.extra-links a { font-size: 0.85rem; color: #3498db; text-decoration: none; cursor: pointer; }
.extra-links a:hover { text-decoration: underline; }

.forgot-header h3 { text-align: center; margin-bottom: 20px; color: #2c3e50; }
</style>