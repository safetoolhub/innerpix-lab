// ─── SafeToolHub i18n + Theme + Blog System ─────────────────────────────────
// Common translations shared across all pages.
// Post-specific translations are defined inline in each post HTML file.

const translations = {
  en: {
    // Navigation
    "nav-tools": "Our Tools",
    "nav-about": "About",
    "nav-blog": "Blog",

    // Hero
    "hero-badge": "Open-Source & Privacy-First",
    "hero-title-1": "Your privacy, your tools",
    "hero-title-2": "Secure, private and free",
    "hero-subtitle": "We build open-source, privacy-respecting software for everyone. Everything runs locally on your machine. <strong>No cloud, no telemetry, no tracking. Free as in freedom.</strong>",
    "hero-btn": "Explore Our Tools",

    // Tools Section
    "tools-title": "Available Applications",
    "tools-desc": "Discover our suite of open-source software designed with privacy and transparency as the main pillars.",
    "tools-i-title": "Innerpix Lab",
    "tools-i-desc": "The ultimate privacy-first photo and video management studio. Clean duplicates, organize them in folders, and find visually similar media. Free and open-source.",
    "tools-i-f1": "Exact & Perceptual Hash Duplicate Detection",
    "tools-i-f2": "HEIC/JPG and Live Photo Cleanup",
    "tools-i-f3": "Smart Date Organization & Renaming",
    "tools-i-f4": "Available for Linux, Windows, and macOS",
    "tools-i-btn": "Download Innerpix Lab",
    "tools-v-badge": "Coming Soon",
    "tools-v-title": "Simple Video Editor",
    "tools-v-desc": "A lightning-fast, highly optimized local video editor meant for quick trims, crops, and format conversions without the bloat.",
    "tools-v-f1": "Lossless cutting and trimming",
    "tools-v-f2": "Format conversion without quality loss",
    "tools-v-f3": "Hardware-accelerated encoding",
    "tools-v-f4": "Hardware-level privacy architecture",
    "tools-v-btn": "Not Yet Available",

    // Blog Section
    "blog-title": "Our Blog",
    "blog-desc": "Insights, updates, and deep dives into privacy, freedom, and local-first software.",
    "blog-read-more": "Read Article",

    // About Section
    "about-title-1": "Why",
    "about-title-2": "SafeToolHub?",
    "about-p1": "In an era where every application demands constant internet connectivity and uploads your personal data to \u2018the cloud\u2019 for analytics or AI training, we decided to take a different path.",
    "about-p2": "SafeToolHub is dedicated to building robust, beautiful, and completely offline applications. Our tools are free and open-source under the GPLv3 license\u2014they don\u2019t even contain networking code. Your freedom and privacy are non-negotiable.",
    "about-btn": "Visit our GitHub",
    "about-img-text": "100% Offline Architecture",

    // Donate Section
    "donate-title": "Support SafeToolHub",
    "donate-desc": "We build our tools to be free, open-source, and completely private because we believe that\u2019s how software should be. If you find value in our work, consider supporting our development so we can keep creating tools that respect your freedom.",
    "donate-btn-gh": "GitHub Sponsors",
    "donate-coming-soon": "Coming soon",

    // Footer
    "footer-main-desc": "Free and open-source software for everyone.",
    "footer-tools-title": "Tools",
    "footer-links-title": "Links",
    "footer-links-org": "GitHub Organization",
    "footer-links-repo": "Innerpix Repo",
    "footer-rights": "SafeToolHub \u2014 Free and open-source software (GPLv3).",
    "footer-license": "Licensed under the <a href='https://www.gnu.org/licenses/gpl-3.0.html' target='_blank'>GNU General Public License v3 (GPLv3)</a>. You are free to use, study, modify, and share this software. Source code available on <a href='https://github.com/safetoolhub' target='_blank'>GitHub</a>.",

    // Shared post elements
    "post-back": "Back to Blog",

    // Blog listing page
    "blog-listing-title": "Blog",
    "blog-listing-desc": "Insights, updates, and deep dives into privacy, freedom, and open-source software.",
  },

  es: {
    // Navegación
    "nav-tools": "Herramientas",
    "nav-about": "Acerca de",
    "nav-blog": "Blog",

    // Hero
    "hero-badge": "Software Libre y Privacidad",
    "hero-title-1": "Tu privacidad, tus herramientas",
    "hero-title-2": "Seguras, privadas y libres",
    "hero-subtitle": "Creamos software de c\u00f3digo abierto que respeta tu privacidad, para todos. Todo se ejecuta localmente en tu m\u00e1quina. <strong>Sin nube, sin telemetr\u00eda, sin rastreo. Libre como en libertad.</strong>",
    "hero-btn": "Explorar Herramientas",

    // Herramientas
    "tools-title": "Aplicaciones Disponibles",
    "tools-desc": "Descubre nuestra suite de software de c\u00f3digo abierto dise\u00f1ada con la privacidad y la transparencia como pilares principales.",
    "tools-i-title": "Innerpix Lab",
    "tools-i-desc": "El estudio definitivo para gestionar fotos y v\u00eddeos sin comprometer la privacidad. Limpia duplicados, org\u00e1nizalos en carpetas y encuentra similitudes visuales. Libre y de c\u00f3digo abierto.",
    "tools-i-f1": "Detecci\u00f3n de duplicados exactos y por hash perceptual",
    "tools-i-f2": "Limpieza de HEIC/JPG y Live Photos",
    "tools-i-f3": "Organizaci\u00f3n inteligente por fechas y renombrado",
    "tools-i-f4": "Disponible para Linux, Windows y macOS",
    "tools-i-btn": "Descargar Innerpix Lab",
    "tools-v-badge": "Pr\u00f3ximamente",
    "tools-v-title": "Editor de V\u00eddeo Simple",
    "tools-v-desc": "Un editor de v\u00eddeo local extremadamente r\u00e1pido y optimizado, pensado para recortes r\u00e1pidos y conversiones de formato sin saturar el sistema.",
    "tools-v-f1": "Recortes de v\u00eddeo sin p\u00e9rdida",
    "tools-v-f2": "Conversi\u00f3n de formatos sin p\u00e9rdida de calidad",
    "tools-v-f3": "Codificaci\u00f3n acelerada por hardware",
    "tools-v-f4": "Arquitectura basada en hardware y privacidad",
    "tools-v-btn": "A\u00fan no disponible",

    // Blog
    "blog-title": "Nuestro Blog",
    "blog-desc": "Reflexiones, novedades y an\u00e1lisis sobre privacidad, libertad y software local.",
    "blog-read-more": "Leer Art\u00edculo",

    // Acerca de
    "about-title-1": "\u00bfPor qu\u00e9",
    "about-title-2": "SafeToolHub?",
    "about-p1": "En una era en la que cada aplicaci\u00f3n exige conexi\u00f3n constante a Internet y sube tus datos personales a \u2018la nube\u2019 para anal\u00edticas o para entrenar IA, decidimos tomar otro camino.",
    "about-p2": "SafeToolHub se dedica a construir aplicaciones robustas, bonitas y completamente offline. Nuestras herramientas son libres y de c\u00f3digo abierto bajo la licencia GPLv3: ni siquiera contienen c\u00f3digo de red. Tu libertad y tu privacidad no son negociables.",
    "about-btn": "Visitar en GitHub",
    "about-img-text": "Arquitectura 100% Offline",

    // Donar
    "donate-title": "Apoya a SafeToolHub",
    "donate-desc": "Desarrollamos nuestras herramientas para que sean libres, de c\u00f3digo abierto y completamente privadas porque creemos que as\u00ed debe ser el software. Si encuentras valor en nuestro trabajo, considera apoyar nuestro desarrollo para que podamos seguir creando herramientas que respeten tu libertad.",
    "donate-btn-gh": "GitHub Sponsors",
    "donate-coming-soon": "Pr\u00f3ximamente",

    // Pie de p\u00e1gina
    "footer-main-desc": "Software libre y de c\u00f3digo abierto para todos.",
    "footer-tools-title": "Herramientas",
    "footer-links-title": "Enlaces",
    "footer-links-org": "Organizaci\u00f3n en GitHub",
    "footer-links-repo": "Repo de Innerpix",
    "footer-rights": "SafeToolHub \u2014 Software libre y de c\u00f3digo abierto (GPLv3).",
    "footer-license": "Licenciado bajo la <a href='https://www.gnu.org/licenses/gpl-3.0.html' target='_blank'>Licencia P\u00fablica General v3 de GNU (GPLv3)</a>. Eres libre de usar, estudiar, modificar y compartir este software. C\u00f3digo fuente disponible en <a href='https://github.com/safetoolhub' target='_blank'>GitHub</a>.",

    // Elementos compartidos de posts
    "post-back": "Volver al Blog",

    // P\u00e1gina de listado del blog
    "blog-listing-title": "Blog",
    "blog-listing-desc": "Reflexiones, novedades y an\u00e1lisis sobre privacidad, libertad y software de c\u00f3digo abierto.",
  }
};


// ─── i18n Engine ─────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  // 1. Determine language
  let currentLang = localStorage.getItem("safetoolhub_lang");
  if (!currentLang) {
    const browserLang = navigator.language || navigator.userLanguage;
    currentLang = browserLang.startsWith("es") ? "es" : "en";
  }

  // 2. Merge post-specific translations if present
  if (window.POST_TRANSLATIONS) {
    for (const lang of Object.keys(window.POST_TRANSLATIONS)) {
      if (translations[lang]) {
        Object.assign(translations[lang], window.POST_TRANSLATIONS[lang]);
      }
    }
  }

  function applyLanguage(lang) {
    document.documentElement.lang = lang;
    const dict = translations[lang] || translations.en;

    // Update data-i18n elements
    document.querySelectorAll("[data-i18n]").forEach(el => {
      const key = el.getAttribute("data-i18n");
      const isHtml = el.hasAttribute("data-i18n-html");

      if (dict[key]) {
        if (isHtml) el.innerHTML = dict[key];
        else el.textContent = dict[key];
      }
    });

    // Update active state in language switch
    document.querySelectorAll(".lang-switch a").forEach(el => {
      el.classList.remove("active");
      if (el.getAttribute("data-lang") === lang) {
        el.classList.add("active");
      }
    });

    // Render blog cards if containers exist
    renderBlogCards(lang);
  }

  // 3. Apply initially
  applyLanguage(currentLang);

  // 4. Bind language switchers
  document.querySelectorAll(".lang-switch a").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const newLang = e.target.getAttribute("data-lang");
      localStorage.setItem("safetoolhub_lang", newLang);
      currentLang = newLang;
      applyLanguage(newLang);
    });
  });

  // 5. Bind theme toggle
  const themeToggle = document.getElementById("theme-toggle");
  if (themeToggle) {
    updateThemeIcon();
    themeToggle.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("sth-theme", next);
      updateThemeIcon();
    });
  }
});

function updateThemeIcon() {
  const themeToggle = document.getElementById("theme-toggle");
  if (!themeToggle) return;
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  themeToggle.textContent = isDark ? "\u2600\ufe0f" : "\ud83c\udf19";
  themeToggle.title = isDark ? "Switch to light mode" : "Switch to dark mode";
}

// ─── Blog Card Rendering ─────────────────────────────────────────────────────
// Renders blog cards from the BLOG_POSTS manifest (loaded from posts/posts.js)

function renderBlogCards(lang) {
  if (typeof BLOG_POSTS === "undefined") return;
  const dict = translations[lang] || translations.en;

  // Render into all containers with class "blog-cards-container"
  document.querySelectorAll(".blog-cards-container").forEach(container => {
    const maxPosts = parseInt(container.getAttribute("data-max-posts")) || BLOG_POSTS.length;
    const postsToShow = BLOG_POSTS.slice(0, maxPosts);

    // Determine the base path for post links
    const basePath = container.getAttribute("data-posts-path") || "posts/";

    container.innerHTML = postsToShow.map(post => `
      <article class="blog-card" onclick="window.location.href='${basePath}${post.slug}.html';">
        <div class="blog-meta">
          <span>${post.date_display[lang] || post.date_display.en}</span> &bull;
          <span>${post.tag[lang] || post.tag.en}</span>
        </div>
        <h3>${post.title[lang] || post.title.en}</h3>
        <p>${post.description[lang] || post.description.en}</p>
        <span class="read-more">${dict["blog-read-more"] || "Read Article"} &rarr;</span>
      </article>
    `).join("");
  });
}
