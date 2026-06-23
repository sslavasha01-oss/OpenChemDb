<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios' // или ваш кастомный клиент api

const user = ref(null)
const loading = ref(true)
const error = ref(null)

// 1. Добавьте импорт стора в самый верх (где остальные импорты)
import { useUserStore } from '@/stores/user' // проверьте путь к стору

const userStore = useUserStore()

// 2. Добавьте эти переменные для модального окна и формы
const isModalOpen = ref(false)
const billingEmailInput = ref('')
const linkLoading = ref(false)
const linkError = ref(null)
const linkSuccessMessage = ref(null)

// 3. Вычисляемое свойство для проверки режима
const isCloudMode = computed(() => !userStore.appStatus?.local_mode)

// 4. Функция для отправки email на бэкенд
const handleManualLink = async () => {
  if (!billingEmailInput.value) return
  linkLoading.value = true
  linkError.value = null
  linkSuccessMessage.value = null

  try {
    const token = localStorage.getItem('token')
    const response = await axios.post('/api/billing/link-manual',
      { email: billingEmailInput.value.trim() },
      { headers: { 'Authorization': `Bearer ${token}` } }
    )
    linkSuccessMessage.value = response.data.message
    billingEmailInput.value = ''
    await fetchProfile() // Обновляем данные профиля на странице
  } catch (err) {
    linkError.value = err.response?.data?.detail || 'An error occurred.'
  } finally {
    linkLoading.value = false
  }
}

const closeModal = () => {
  isModalOpen.value = false
  linkError.value = null
  linkSuccessMessage.value = null
  billingEmailInput.value = ''
}

const fetchProfile = async () => {
  try {
    const token = localStorage.getItem('token') // Достаем токен
    const response = await axios.get('/api/users/me', {
      headers: {
        'Authorization': `Bearer ${token}` // Передаем в заголовках
      }
    })
    user.value = response.data
  } catch (err) {
    error.value = 'Failed to load profile information.'
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchProfile()
})

// Хелпер для перевода байт в мегабайты
const toMB = (bytes) => {
  if (!bytes) return 0
  return (bytes / (1024 * 1024)).toFixed(1)
}

// Вычисляем процент заполнения облака
// Вычисляем процент заполнения облака (если лимит 0, то прогресс всегда 0%)
const storagePercentage = computed(() => {
  if (!user.value || !user.value.max_allowed_size || user.value.max_allowed_size === 0) return 0
  const percent = (user.value.attachments_total_size / user.value.max_allowed_size) * 100
  return Math.min(percent, 100).toFixed(1)
})
</script>

<template>
  <div class="profile-container">
    <h2>My Profile</h2>

    <div v-if="loading" class="info-box">Loading profile...</div>
    <div v-else-if="error" class="error-box">{{ error }}</div>

    <div v-else-if="user" class="profile-card">
      <div class="profile-info">
        <p><strong>Username:</strong> {{ user.username }}</p>
        <p>
          <strong>Email:</strong> {{ user.email }}
          <span class="privacy-badge">Visible only to you</span>
        </p>
        <p v-if="user.billing_email">
          <strong>Billing Email:</strong> {{ user.billing_email }}
          <span class="privacy-badge">Visible only to you</span>
        </p>
        <p><strong>Role:</strong> {{ user.role }}</p>
        <p><strong>Tariff Plan:</strong> <span class="tariff-badge">{{ user.tariff_plan }}</span></p>
      </div>

      <div class="storage-section">
        <h3>Cloud Storage Usage</h3>

        <div class="storage-text">
          <span>Used: {{ toMB(user.attachments_total_size) }} MB</span>
          <span>Limit: {{ user.max_allowed_size > 0 ? toMB(user.max_allowed_size) + ' MB' : '∞ (Local Mode)' }}</span>
        </div>

        <div class="progress-bar-container">
          <div
            class="progress-bar-fill"
            :style="{ width: storagePercentage + '%' }"
            :class="{ 'danger': storagePercentage > 90 }"
          ></div>
        </div>

        <div class="percentage-label">
          <span v-if="user.max_allowed_size > 0">{{ storagePercentage }}% space used</span>
          <span v-else>No storage limits applied</span>
        </div>
      </div>
      <div v-if="isCloudMode" class="billing-section">
        <h3>Premium Features</h3>
        <p class="billing-text">
          Want more space? You can buy <strong>50GB Cloud Storage</strong> for your attachments.
          Please join our membership program on Buy Me a Coffee:
        </p>
        <a href="https://buymeacoffee.com/ninjachemist/membership" target="_blank" class="bmc-button">
          🚀 Upgrade on Buy Me a Coffee
        </a>
        <blockquote class="billing-note">
          <strong>Important:</strong> Please ensure you provide the exact same email address you use for your OpenChemDb account during checkout.
        </blockquote>

        <div class="manual-link-trigger">
          <button @click="isModalOpen = true" class="link-btn-text">
            I already paid but my subscription didn't update
          </button>
        </div>
      </div>
    </div>
    <div v-if="isModalOpen" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <h3>Link Payment Manually</h3>
        <p class="modal-desc">
          If your payment didn't sync automatically, please enter the email address you used during payment on Buy Me a Coffee.
        </p>
        <p class="modal-warn">
          💡 <strong>Note:</strong> If you used Google Pay or Apple Pay, this might be the email address associated with your Apple/Google account.
        </p>

        <form @submit.prevent="handleManualLink" class="modal-form">
          <input
            v-model="billingEmailInput"
            type="email"
            placeholder="Enter payment email"
            required
            :disabled="linkLoading"
            class="modal-input"
          />
          <div v-if="linkError" class="modal-error">{{ linkError }}</div>
          <div v-if="linkSuccessMessage" class="modal-success">{{ linkSuccessMessage }}</div>

          <div class="modal-actions">
            <button type="button" @click="closeModal" :disabled="linkLoading" class="btn-cancel">Close</button>
            <button type="submit" :disabled="linkLoading || !billingEmailInput" class="btn-submit">
              {{ linkLoading ? 'Verifying...' : 'Link Payment' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-container {
  max-width: 600px;
  margin: 40px auto;
  padding: 20px;
}

.profile-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  padding: 24px;
  color: #2c3e50;
}

.profile-info p {
  margin: 12px 0;
  font-size: 1.05rem;
}

.privacy-badge {
  background: #e8f5e9;
  color: #2e7d32;
  font-size: 0.8rem;
  padding: 2px 8px;
  border-radius: 12px;
  margin-left: 8px;
}

.tariff-badge {
  background: #34495e;
  color: white;
  font-weight: bold;
  font-size: 0.85rem;
  padding: 3px 10px;
  border-radius: 4px;
}

/* Хранилище и прогресс-бар */
.storage-section {
  margin-top: 30px;
  border-top: 1px solid #eee;
  padding-top: 20px;
}

.storage-text {
  display: flex;
  justify-content: space-between;
  font-size: 0.95rem;
  margin-bottom: 8px;
  color: #7f8c8d;
}

.progress-bar-container {
  width: 100%;
  height: 12px;
  background: #ecf0f1;
  border-radius: 6px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: #42b983;
  transition: width 0.5s ease;
}

.progress-bar-fill.danger {
  background: #e74c3c;
}

.percentage-label {
  font-size: 0.85rem;
  text-align: right;
  margin-top: 5px;
  color: #7f8c8d;
}

.info-box, .error-box {
  text-align: center;
  padding: 20px;
}

.error-box {
  color: #e74c3c;
}

/* Дополнительные стили для биллинга и модалки */
.billing-section {
  margin-top: 30px;
  border-top: 1px dashed #e2e8f0;
  padding-top: 20px;
}
.billing-text { font-size: 0.95rem; line-height: 1.5; margin-bottom: 15px; }
.bmc-button {
  display: inline-block; background: #ffdd00; color: #000; font-weight: bold;
  padding: 10px 20px; border-radius: 6px; text-decoration: none; margin-bottom: 15px;
}
.billing-note {
  background: #f8fafc; border-left: 4px solid #3498db; padding: 10px 15px;
  margin: 10px 0; font-size: 0.9rem; border-radius: 0 6px 6px 0;
}
.manual-link-trigger { margin-top: 15px; text-align: center; }
.link-btn-text { background: none; border: none; color: #3498db; text-decoration: underline; cursor: pointer; }
.modal-overlay {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal-content { background: white; padding: 25px; border-radius: 8px; max-width: 450px; width: 90%; }
.modal-desc { font-size: 0.95rem; color: #34495e; margin-bottom: 10px; }
.modal-warn { font-size: 0.85rem; background: #fff9db; color: #664d03; padding: 8px 12px; border-radius: 6px; margin-bottom: 15px; }
.modal-form { display: flex; flex-direction: column; }
.modal-input { padding: 10px; border: 1px solid #ccd1d9; border-radius: 4px; margin-bottom: 15px; }
.modal-error { color: #e74c3c; font-size: 0.9rem; margin-bottom: 10px; }
.modal-success { color: #27ae60; font-size: 0.9rem; margin-bottom: 10px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; }
.btn-cancel { background: #e2e8f0; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
.btn-submit { background: #3498db; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
.btn-submit:disabled { background: #bdc3c7; cursor: not-allowed; }
</style>