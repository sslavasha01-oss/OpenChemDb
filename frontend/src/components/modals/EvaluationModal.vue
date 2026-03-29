<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="close">
    <div class="modal-card">
      <h3>Оценить реакцию #{{ entryId }}</h3>

      <div class="status-selector">
        <label :class="{ active: form.status === 'CHECK' }" class="status-option check">
          <input type="radio" v-model="form.status" value="CHECK"/>
          <span class="icon">✅</span> Reproduced
        </label>
        <label :class="{ active: form.status === 'POO' }" class="status-option poo">
          <input type="radio" v-model="form.status" value="POO"/>
          <span class="icon">💩</span> Not Reproduced
        </label>
        <label :class="{ active: form.status === 'ERROR' }" class="status-option error">
          <input type="radio" v-model="form.status" value="ERROR"/>
          <span class="icon">🛑</span> Data Error
        </label>
      </div>

      <textarea
          v-model="form.comment"
          placeholder="Ваш комментарий (нюансы синтеза, очистки...)"
          rows="4"
      ></textarea>

      <div class="actions">
        <button @click="submit" :disabled="loading" class="btn-submit">
          {{ loading ? 'Сохранение...' : 'Сохранить оценку' }}
        </button>
        <button @click="close" class="btn-cancel">Отмена</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import {ref, reactive} from 'vue'
import axios from 'axios'

const props = defineProps(['isOpen', 'entryId'])
const emit = defineEmits(['close', 'success'])

const loading = ref(false)
const form = reactive({
  status: 'CHECK',
  comment: ''
})

const close = () => {
  form.comment = ''
  emit('close')
}

const submit = async () => {
  loading.ref = true
  try {
    // Получаем токен из хранилища
    const token = localStorage.getItem('token')

    await axios.post('/api/evaluations/add', null, {
      params: {
        target: 'REACTIONS',
        entry_id: props.entryId,
        status: form.status,
        comment: form.comment
      },
      headers: {
        // ДОБАВЛЯЕМ ТОКЕН В ЗАГОЛОВОК
        'Authorization': `Bearer ${token}`
      }
    })

    emit('success', {id: props.entryId, status: form.status})
    close()
  } catch (err) {
    alert(err.response?.status === 401 ? "Ошибка авторизации! Проверьте логин." : "Ошибка при сохранении")
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-card {
  background: white;
  padding: 25px;
  border-radius: 12px;
  width: 400px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
}

.status-selector {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 20px 0;
}

.status-option {
  border: 2px solid #eee;
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: 0.2s;
}

.status-option input {
  display: none;
}

.status-option.active.check {
  border-color: #42b983;
  background: #e8f5e9;
}

.status-option.active.poo {
  border-color: #795548;
  background: #efebe9;
}

.status-option.active.error {
  border-color: #f44336;
  background: #ffebee;
}

textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 8px;
  margin-bottom: 15px;
  resize: none;
  box-sizing: border-box;
}

.actions {
  display: flex;
  gap: 10px;
}

.btn-submit {
  flex: 1;
  background: #42b983;
  color: white;
  border: none;
  padding: 10px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
}

.btn-cancel {
  background: #eee;
  border: none;
  padding: 10px;
  border-radius: 6px;
  cursor: pointer;
}
</style>