<template>
  <div class="about-page">
    <h1>About project OpenChemDB</h1>

    <section class="mission">
      <p>
        Today, access to high-quality chemical reaction databases (such as Reaxys) costs tens of thousands of dollars per year.
        This creates a significant barrier for independent researchers, students, and small laboratories.
      </p>
      <p>
        <strong>Our Mission:</strong> To provide a free, open-source alternative.
        While we currently host 3 million reactions, we are actively developing crowdsourcing tools to allow the community to contribute and expand the database.
      </p>
    </section>

    <div class="support-grid">
      <div class="support-card">
        <h3>Support the Development</h3>
        <p>Funds are used to cover server costs (indexing millions of reactions requires high-performance hardware)
          and to maintain the project infrastructure.</p>

        <a href="https://www.buymeacoffee.com/NinjaChemist" target="_blank" class="donate-link">
          <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" >
        </a>
      </div>

      <div class="support-card">
        <h3>Community & Contacts</h3>
        <ul class="social-links">
          <li><a href="https://t.me/ninja_chemist" target="_blank">✈️ Telegram channel</a></li>
          <li><a href="https://youtube.com/@NinjaChemistChannel" target="_blank">📺 YouTube channel</a></li>
          <li><a href="https://github.com/sslavasha01-oss/OpenChemDb" target="_blank">💻 GitHub (Coming soon)</a></li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.about-page {
  line-height: 1.6;
  color: #2c3e50;
}

.mission {
  font-size: 1.1rem;
  margin-bottom: 40px;
  max-width: 800px;
}

.support-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 30px;
}

.support-card {
  background: #f8f9fa;
  padding: 25px;
  border-radius: 12px;
  border: 1px solid #e9ecef;
}

.social-links {
  list-style: none;
  padding: 0;
}

.social-links li {
  margin: 15px 0;
}

.social-links a {
  text-decoration: none;
  color: #42b983;
  font-weight: bold;
  font-size: 1.1rem;
}

.donate-link {
  display: inline-block;
  margin-top: 20px;
  transition: transform 0.2s;
}

.donate-link:hover {
  transform: scale(1.05);
}
</style>