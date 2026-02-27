/* ============================================================
   TRAVEL BLUE DASHBOARDS — Global Theme Toggle
   Toggles between body.light (default) and body.dark
   - Pages using style.css: body.dark applies dark CSS vars
   - Avolta page: body.light applies its own light overrides;
     no class = avolta dark default (its :root is dark)
   ============================================================ */

const ThemeToggle = {
  STORAGE_KEY: 'tb_theme',

  init() {
    const saved = localStorage.getItem(this.STORAGE_KEY) || 'light';
    this._apply(saved === 'dark');
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
      btn.textContent = isDark ? '☀️' : '🌙';
      btn.title = isDark ? 'Switch to light mode' : 'Switch to dark mode';
    }
  }
};

// Apply theme immediately to minimise flash of unstyled content
ThemeToggle.init();
