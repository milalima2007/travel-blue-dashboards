/* ============================================================
   TRAVEL BLUE DASHBOARDS — Global Theme Toggle
   Priority: 1) user manual override (localStorage)
             2) system preference (prefers-color-scheme)
   - Pages using style.css: body.dark applies dark CSS vars
   - Avolta page: body.light applies its own light overrides;
     no class = avolta dark default (its :root is dark)
   ============================================================ */

const ThemeToggle = {
  STORAGE_KEY: 'tb_theme',

  init() {
    const saved      = localStorage.getItem(this.STORAGE_KEY);
    const sysDark    = window.matchMedia('(prefers-color-scheme: dark)');
    // Use saved manual preference; otherwise default to dark
    this._apply(saved !== null ? saved === 'dark' : true);
    // Update automatically when system changes (only if no manual override)
    sysDark.addEventListener('change', e => {
      if (localStorage.getItem(this.STORAGE_KEY) === null) this._apply(e.matches);
    });
  },

  toggle() {
    const isDark = document.body.classList.contains('dark');
    this._apply(!isDark);
    localStorage.setItem(this.STORAGE_KEY, !isDark ? 'dark' : 'light');
  },

  _apply(isDark) {
    document.body.classList.toggle('dark', isDark);
    document.body.classList.toggle('light', !isDark);
    const btn = document.getElementById('btn-theme');
    if (btn) {
      const iconName = isDark ? 'sun' : 'moon';
      if (typeof lucide !== 'undefined') {
        btn.innerHTML = `<i data-lucide="${iconName}"></i>`;
        lucide.createIcons();
      } else {
        btn.textContent = isDark ? '☀️' : '🌙';
      }
      btn.title = isDark ? 'Switch to light mode' : 'Switch to dark mode';
    }
  }
};

// Apply theme immediately to minimise flash of unstyled content
ThemeToggle.init();
