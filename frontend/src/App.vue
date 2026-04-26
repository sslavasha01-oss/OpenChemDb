<script setup>
import Navbar from './components/Navbar.vue'
</script>

<template>
  <Navbar />
  <div class="donation-banner">
    <div class="banner-content">
      <span class="banner-text">
        <strong>OpenChemDB</strong> is an open-source initiative. Help us reach 30M reactions and keep chemical knowledge accessible to everyone, not just big institutions.
      </span>
      <router-link to="/about" class="banner-btn">Learn More & Support</router-link>
    </div>
  </div>
  <main class="container">
    <router-view />
  </main>
</template>

<style>
body { margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
.container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }

.donation-banner {
  background: #fdf6e3; /* Светло-желтый, как на Wiki */
  border-bottom: 1px solid #eee8d5;
  padding: 10px 0;
  font-size: 0.9rem;
  color: #586e75;
}

.banner-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.banner-btn {
  background: #b58900;
  color: white !important;
  padding: 5px 15px;
  border-radius: 4px;
  text-decoration: none;
  font-weight: bold;
  white-space: nowrap;
}

.banner-btn:hover {
  background: #cb4b16;
}

@media (max-width: 768px) {
  .banner-content {
    flex-direction: column;
    text-align: center;
  }
}
</style>