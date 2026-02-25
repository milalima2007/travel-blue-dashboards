/* ============================================================
   TRAVEL BLUE DASHBOARDS — Auth Module (Phase 1: Mock)
   Phase 2: replace login() body with Supabase Auth call
   ============================================================ */

const AUTH_KEY = 'tb_session';

const Auth = {

  getUser()         { try { const r = localStorage.getItem(AUTH_KEY); return r ? JSON.parse(r) : null; } catch { return null; } },
  setUser(u)        { localStorage.setItem(AUTH_KEY, JSON.stringify(u)); },
  isLoggedIn()      { return !!this.getUser(); },
  getRole()         { return this.getUser()?.role || null; },
  isOwner()         { return this.getRole() === 'owner'; },
  isAdmin()         { return this.getRole() === 'admin'; },
  isAdminOrOwner()  { return ['owner','admin'].includes(this.getRole()); },

  logout() {
    localStorage.removeItem(AUTH_KEY);
    window.location.href = '/index.html';
  },

  /* Redirect to login if not authenticated. Returns user or null. */
  requireLogin() {
    if (!this.isLoggedIn()) { window.location.href = '/index.html'; return null; }
    return this.getUser();
  },

  /* Redirect to home if not admin or owner */
  requireAdminOrOwner() {
    const u = this.requireLogin();
    if (u && !this.isAdminOrOwner()) { window.location.href = '/home.html'; return null; }
    return u;
  },

  /* Inject user name + email into navbar elements */
  renderUser(nameSelector = '#user-name', emailSelector = '#user-email') {
    const u = this.getUser();
    if (!u) return;
    const n = document.querySelector(nameSelector);
    const e = document.querySelector(emailSelector);
    if (n) n.textContent = u.name || u.email;
    if (e) e.textContent = u.email;
  },

  /* Render role badge next to user name */
  renderRoleBadge(selector = '#role-badge') {
    const u = this.getUser();
    if (!u) return;
    const el = document.querySelector(selector);
    if (!el) return;
    const colors = { owner: 'badge-owner', admin: 'badge-admin', user: 'badge-user' };
    el.textContent = u.role.charAt(0).toUpperCase() + u.role.slice(1);
    el.className = 'role-badge ' + (colors[u.role] || '');
    el.style.display = 'inline-block';
  },

  /* ---- MOCK LOGIN (Phase 1) ----
     Replace this entire function body with Supabase signIn in Phase 2 */
  async login(email, password) {
    if (!email || !password)
      return { success: false, error: 'Please enter your email and password.' };

    const dbUser = MockDB.getUserByEmail(email);
    if (!dbUser)
      return { success: false, error: 'No account found with this email address.' };

    if (dbUser.password && dbUser.password !== password)
      return { success: false, error: 'Incorrect password. Please try again.' };

    const session = {
      id:   dbUser.id,
      email: dbUser.email,
      name:  dbUser.name,
      role:  dbUser.role,
      mustChangePassword: dbUser.mustChangePassword || false
    };
    this.setUser(session);
    return { success: true, user: session };
  }
};

/* Bind logout to all [data-logout] elements */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-logout]').forEach(btn =>
    btn.addEventListener('click', () => Auth.logout())
  );
});
