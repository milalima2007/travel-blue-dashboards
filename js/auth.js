/* ============================================
   TRAVEL BLUE DASHBOARDS — Auth Module
   Phase 1: Mock auth (localStorage)
   Phase 2: Will be replaced with Supabase Auth
   ============================================ */

const AUTH_KEY = 'tb_user_session';

const Auth = {

  /* Get current user from storage */
  getUser() {
    try {
      const raw = localStorage.getItem(AUTH_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  /* Save user session */
  setUser(user) {
    localStorage.setItem(AUTH_KEY, JSON.stringify(user));
  },

  /* Check if logged in */
  isLoggedIn() {
    return !!this.getUser();
  },

  /* Logout */
  logout() {
    localStorage.removeItem(AUTH_KEY);
    window.location.href = '/index.html';
  },

  /* Require login — call on protected pages */
  requireLogin() {
    if (!this.isLoggedIn()) {
      window.location.href = '/index.html';
      return null;
    }
    return this.getUser();
  },

  /* Render user info into navbar */
  renderUser(nameSelector, emailSelector) {
    const user = this.getUser();
    if (!user) return;
    const nameEl = document.querySelector(nameSelector);
    const emailEl = document.querySelector(emailSelector);
    if (nameEl) nameEl.textContent = user.name || user.email;
    if (emailEl) emailEl.textContent = user.email;
  },

  /* ---- MOCK LOGIN (Phase 1) ---- */
  /* Replace this function body with Supabase call in Phase 2 */
  async login(email, password) {
    if (!email || !password) {
      return { success: false, error: 'Please enter your email and password.' };
    }
    if (password.length < 6) {
      return { success: false, error: 'Password must be at least 6 characters.' };
    }

    // Derive display name from email (e.g. camila.lima@travelblue.com → Camila Lima)
    const localPart = email.split('@')[0];
    const name = localPart
      .replace(/[._\-]/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());

    const user = { email, name };
    this.setUser(user);
    return { success: true, user };
  }

};

/* ---- Bind logout buttons globally ---- */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-logout]').forEach(btn => {
    btn.addEventListener('click', () => Auth.logout());
  });
});
