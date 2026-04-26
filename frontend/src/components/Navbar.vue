<script setup>
import {ref} from 'vue'
import {useUserStore} from '@/stores/user'

const userStore = useUserStore()
const isMenuOpen = ref(false)

const showAccountMenu = ref(false)

const toggleMenu = () => {
  isMenuOpen.value = !isMenuOpen.value
}

const toggleAccountMenu = () => { // <--- И это
  showAccountMenu.value = !showAccountMenu.value
}
</script>

<template>
  <nav class="navbar">
    <div class="nav-container">
      <div class="logo">OpenChemDB</div>

      <button class="menu-toggle" @click="toggleMenu">
        <span></span>
        <span></span>
        <span></span>
      </button>

      <ul :class="['nav-links', { 'is-open': isMenuOpen }]">
        <li>
          <router-link to="/" @click="isMenuOpen = false">Search</router-link>
        </li>
        <li>
          <router-link to="/journal" @click="isMenuOpen = false">
            {{ userStore.isLoggedIn ? 'My Journal' : 'Journal' }}
          </router-link>
        </li>
        <li v-if="userStore.isAdmin">
          <router-link to="/admin" @click="isMenuOpen = false">Admin Console</router-link>
        </li>
        <li>
           <router-link to="/about" @click="isMenuOpen = false">About & Support</router-link>
        </li>

        <li v-if="!userStore.isLoggedIn">
          <router-link to="/login" @click="isMenuOpen = false">Login</router-link>
        </li>

        <li v-else class="user-section">
          <div class="current-user" @click="toggleAccountMenu">
            <div class="avatar-circle">{{ userStore.currentUser?.name?.[0]?.toUpperCase() }}</div>
            <span class="user-text">{{ userStore.currentUser?.name }}</span>
          </div>

          <div v-if="showAccountMenu" class="account-dropdown">
            <div
                v-for="(acc, index) in userStore.accounts"
                :key="index"
                :class="['account-item', { active: index === userStore.currentAccountIndex }]"
                @click="userStore.switchAccount(index); showAccountMenu = false"
            >
              {{ acc.name }} <small v-if="acc.role === 'admin'">(Admin)</small>
            </div>
            <hr>
            <router-link to="/login" @click="showAccountMenu = false">Add Account</router-link>
            <a href="#" @click.prevent="userStore.logout(); showAccountMenu = false">Logout</a>
          </div>
        </li>
      </ul>
    </div>
  </nav>
</template>

<style scoped>
.navbar {
  background: #2c3e50;
  color: white;
  padding: 1rem;
  position: sticky;
  top: 0;
  z-index: 1000;
}

.nav-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
}

.logo {
  font-weight: bold;
  font-size: 1.2rem;
}

.nav-links {
  display: flex;
  list-style: none;
  gap: 20px;
  margin: 0;
}

.nav-links a {
  color: white;
  text-decoration: none;
  transition: opacity 0.3s;
}

.nav-links a:hover {
  opacity: 0.7;
}

/* Стили для бургера */
.menu-toggle {
  display: none;
  flex-direction: column;
  gap: 5px;
  background: none;
  border: none;
  cursor: pointer;
}

.menu-toggle span {
  display: block;
  width: 25px;
  height: 3px;
  background: white;
}

/* Мобильная адаптация */
@media (max-width: 768px) {
  .menu-toggle {
    display: flex;
  }

  .nav-links {
    display: none; /* Скрываем по умолчанию */
    flex-direction: column;
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: #34495e;
    padding: 20px;
    gap: 15px;
  }

  .nav-links.is-open {
    display: flex;
  }

  .navbar {
    position: sticky;
    top: 0;
    background: rgba(44, 62, 80, 0.9); /* Полупрозрачный фон */
    backdrop-filter: blur(10px); /* Размытие заднего плана */
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }
}

/* Контейнер юзера */
.user-section {
  position: relative;
  cursor: pointer;
  user-select: none;
}

.current-user {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Тот самый кружочек */
.avatar-circle {
  width: 32px;
  height: 32px;
  background-color: #42b983; /* Фирменный цвет Vue или любой другой */
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.9rem;
  color: white;
  text-transform: uppercase;
}

/* Стили выпадающего меню */
.account-dropdown {
  position: absolute;
  top: 120%;
  right: 0;
  background: white;
  color: #2c3e50;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  min-width: 160px;
  padding: 10px 0;
  display: flex;
  flex-direction: column;
}

.account-item, .account-dropdown a {
  padding: 8px 16px;
  text-decoration: none;
  color: #2c3e50;
  font-size: 0.9rem;
}

.account-item:hover, .account-dropdown a:hover {
  background: #f8f9fa;
}

.account-item.active {
  background: #e9ecef;
  font-weight: bold;
}

hr { border: 0; border-top: 1px solid #eee; margin: 5px 0; }
</style>