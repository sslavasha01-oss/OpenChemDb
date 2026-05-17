import {defineStore} from 'pinia'

export const useUserStore = defineStore('user', {
    state: () => ({
        // Загружаем список аккаунтов из памяти браузера при старте
        accounts: JSON.parse(localStorage.getItem('chem_accounts') || '[]'),
        // Индекс текущего выбранного аккаунта
        currentAccountIndex: parseInt(localStorage.getItem('chem_current_index') || '0')
    }),

    getters: {
        // Возвращает объект текущего пользователя или null
        currentUser: (state) => {
            if (state.accounts.length === 0) return null
            // Проверка на случай, если индекс вышел за пределы (после удаления)
            const index = state.currentAccountIndex < state.accounts.length ? state.currentAccountIndex : 0
            return state.accounts[index]
        },

        // Флаг: залогинен ли хотя бы один юзер
        isLoggedIn: (state) => state.accounts.length > 0,

        // Проверка роли текущего юзера (привели к единому регистру)
        isAdmin: (state) => state.currentUser?.role?.toUpperCase() === 'ADMIN'
    },

    actions: {
        // Добавление нового аккаунта (после логина)
        addAccount(userData) {
            // 1. Ищем, есть ли уже такой юзер в массиве
            const existingIndex = this.accounts.findIndex(a => a.username === userData.username)

            if (existingIndex !== -1) {
                // Если есть — просто обновляем его данные (токен может быть новый)
                this.accounts[existingIndex] = userData
                this.currentAccountIndex = existingIndex
            } else {
                // Если НЕТ — добавляем в массив НОВЫМ элементом
                this.accounts.push(userData)
                this.currentAccountIndex = this.accounts.length - 1
            }

            // 2. СРАЗУ сохраняем в localStorage
            this.save()
        },

        // Переключение между аккаунтами
        switchAccount(index) {
            if (this.accounts[index]) {
                this.currentAccountIndex = index
                this.save()
            }
        },

        // Выход из текущего аккаунта
        logout() {
            if (this.accounts.length === 0) return

            this.accounts.splice(this.currentAccountIndex, 1)

            // Сбрасываем индекс на первый доступный или на 0
            if (this.currentAccountIndex >= this.accounts.length) {
                this.currentAccountIndex = Math.max(0, this.accounts.length - 1)
            }
            this.save()
        },

        // Сохранение всего состояния в LocalStorage + менеджмент основного токена
        save() {
            localStorage.setItem('chem_accounts', JSON.stringify(this.accounts))
            localStorage.setItem('chem_current_index', this.currentAccountIndex.toString())

            // МЕНЕДЖМЕНТ ТОКЕНА: Синхронизируем базовый 'token' с активным аккаунтом
            const activeUser = this.currentUser
            if (activeUser && activeUser.token) {
                localStorage.setItem('token', activeUser.token)
            } else {
                // Если аккаунтов не осталось или у юзера нет токена — тотальная зачистка
                localStorage.removeItem('token')
            }
        }
    }
})