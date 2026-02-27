/* ============================================================
   TRAVEL BLUE DASHBOARDS — Auth Module (Supabase Auth)
   ============================================================ */

const Auth = {
  _client: null,
  _cachedUser: null,

  _sb() {
    if (!this._client)
      this._client = window.supabase.createClient(window.SUPABASE_URL, window.SUPABASE_KEY);
    return this._client;
  },

  /* ── Async: fetch user from Supabase session ── */
  async getUser() {
    if (this._cachedUser !== null) return this._cachedUser;
    const { data: { session } } = await this._sb().auth.getSession();
    this._cachedUser = session?.user || null;
    return this._cachedUser;
  },

  /* ── Sync helpers — call AFTER getUser() resolves ── */
  role(user)           { return user?.user_metadata?.role || 'user'; },
  isOwner(user)        { return this.role(user) === 'owner'; },
  isAdmin(user)        { return this.role(user) === 'admin'; },
  isAdminOrOwner(user) { return ['owner', 'admin'].includes(this.role(user)); },

  /* Returns true if user can view the project slug */
  canViewProject(user, slug) {
    if (this.isAdminOrOwner(user)) return true;
    const projects = user?.user_metadata?.projects || [];
    return projects.includes(slug);
  },

  /* ── Async: redirect to login if not authenticated ── */
  async requireLogin() {
    const user = await this.getUser();
    if (!user) { window.location.href = '/index.html'; return null; }
    return user;
  },

  /* ── Async: redirect to home if not admin/owner ── */
  async requireAdminOrOwner() {
    const user = await this.requireLogin();
    if (user && !this.isAdminOrOwner(user)) { window.location.href = '/home.html'; return null; }
    return user;
  },

  /* ── Logout ── */
  async logout() {
    this._cachedUser = null;
    await this._sb().auth.signOut();
    window.location.href = '/index.html';
  },

  /* ── Render helpers ── */
  renderUser(user, nameSelector = '#user-name', emailSelector = '#user-email') {
    const n = document.querySelector(nameSelector);
    const e = document.querySelector(emailSelector);
    if (n) n.textContent = user?.user_metadata?.name || user?.email || '—';
    if (e) e.textContent = user?.email || '—';
  },

  renderRoleBadge(user, selector = '#role-badge') {
    const role = this.role(user);
    const el = document.querySelector(selector);
    if (!el) return;
    const colors = { owner: 'badge-owner', admin: 'badge-admin', user: 'badge-user' };
    el.textContent = role.charAt(0).toUpperCase() + role.slice(1);
    el.className = 'role-badge ' + (colors[role] || '');
    el.style.display = 'inline-block';
  },

  /* ── Login with Supabase Auth ── */
  async login(email, password) {
    if (!email || !password)
      return { success: false, error: 'Please enter your email and password.' };

    const { data, error } = await this._sb().auth.signInWithPassword({ email, password });
    if (error) return { success: false, error: this._friendlyError(error.message) };

    this._cachedUser = data.user;
    return { success: true, user: data.user };
  },

  _friendlyError(msg) {
    if (/invalid login/i.test(msg))        return 'Incorrect email or password. Please try again.';
    if (/email not confirmed/i.test(msg))  return 'Please confirm your email address first.';
    return msg;
  }
};

/* Bind logout to all [data-logout] elements */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-logout]').forEach(btn =>
    btn.addEventListener('click', () => Auth.logout())
  );
});
