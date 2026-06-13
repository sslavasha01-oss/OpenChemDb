<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios' // или ваш кастомный клиент api

const user = ref(null)
const loading = ref(true)
const error = ref(null)

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
</style>