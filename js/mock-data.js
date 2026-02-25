/* ============================================================
   TRAVEL BLUE DASHBOARDS — Mock Database (Phase 1)
   Simulates Supabase tables: projects, users, permissions
   All data persists in localStorage until Supabase is connected.
   ============================================================ */

const OWNER_EMAIL  = 'soporte.latam@travel-blue.com';
const MOCK_DB_KEY  = 'tb_mockdb_v2';

const MockDB = {

  /* ---- Seed data (loaded on first run) ---- */
  _seed() {
    return {
      projects: [
        {
          id: 'p1', slug: 'avolta', name: 'Avolta',
          description: 'Sales performance and KPI tracking for the Avolta partnership across global travel retail channels. Includes sell-through rates and revenue insights.',
          icon: '✈️', status: 'active',
          created_at: '2026-01-15', published_at: '2026-01-20'
        },
        {
          id: 'p2', slug: 'backpacks-and-luggage', name: 'Backpacks & Luggage',
          description: 'Category-level analysis and sales tracking for Travel Blue\'s backpacks and luggage product lines. Monitors volume, revenue and distribution.',
          icon: '🧳', status: 'active',
          created_at: '2026-01-15', published_at: '2026-01-20'
        },
        {
          id: 'p3', slug: 'total-sales-bp-latam', name: 'Total Sales BP LATAM',
          description: 'Comprehensive sales dashboard for Business Partners across Latin America. Tracks regional revenue, growth trends and partner performance.',
          icon: '🌎', status: 'active',
          created_at: '2026-01-15', published_at: '2026-01-20'
        }
      ],
      users: [
        {
          id: 'u1', email: OWNER_EMAIL, name: 'LATAM Support',
          role: 'owner', password: 'owner123',
          created_at: '2026-01-01', mustChangePassword: false
        },
        {
          id: 'u2', email: 'admin@travel-blue.com', name: 'Admin User',
          role: 'admin', password: 'admin123',
          created_at: '2026-01-10', mustChangePassword: false
        },
        {
          id: 'u3', email: 'user@travel-blue.com', name: 'Regular User',
          role: 'user', password: 'user123',
          created_at: '2026-01-15', mustChangePassword: false
        }
      ],
      permissions: {
        'u1': ['avolta', 'backpacks-and-luggage', 'total-sales-bp-latam'],
        'u2': ['avolta', 'backpacks-and-luggage', 'total-sales-bp-latam'],
        'u3': ['total-sales-bp-latam']
      }
    };
  },

  /* ---- Internal helpers ---- */
  _get() {
    try {
      const raw = localStorage.getItem(MOCK_DB_KEY);
      if (!raw) { const s = this._seed(); localStorage.setItem(MOCK_DB_KEY, JSON.stringify(s)); return s; }
      return JSON.parse(raw);
    } catch { return this._seed(); }
  },
  _save(db) { localStorage.setItem(MOCK_DB_KEY, JSON.stringify(db)); },
  _uid()    { return 'id_' + Math.random().toString(36).substr(2,9) + Date.now(); },
  _today()  { return new Date().toISOString().split('T')[0]; },

  /* =======================
     PROJECTS
  ======================== */

  /* role: 'owner' → all statuses | others → active only */
  getProjects(role = 'user') {
    const db = this._get();
    if (role === 'owner') return db.projects;
    return db.projects.filter(p => p.status === 'active');
  },

  getProject(id) { return this._get().projects.find(p => p.id === id) || null; },
  getProjectBySlug(slug) { return this._get().projects.find(p => p.slug === slug) || null; },

  createProject(data) {
    const db = this._get();
    if (db.projects.find(p => p.slug === data.slug))
      return { error: 'A project with this slug already exists.' };
    const project = {
      id: this._uid(), slug: data.slug, name: data.name,
      description: data.description || '', icon: data.icon || '📊',
      status: 'draft', created_at: this._today(), published_at: null
    };
    db.projects.push(project);
    this._save(db);
    return project;
  },

  updateProject(id, data) {
    const db = this._get();
    const i = db.projects.findIndex(p => p.id === id);
    if (i === -1) return { error: 'Project not found.' };
    db.projects[i] = { ...db.projects[i], ...data };
    this._save(db);
    return db.projects[i];
  },

  publishProject(id) {
    return this.updateProject(id, { status: 'active', published_at: this._today() });
  },

  archiveProject(id) {
    return this.updateProject(id, { status: 'archived' });
  },

  draftProject(id) {
    return this.updateProject(id, { status: 'draft', published_at: null });
  },

  deleteProject(id) {
    const db = this._get();
    const project = db.projects.find(p => p.id === id);
    if (!project) return { error: 'Project not found.' };
    db.projects = db.projects.filter(p => p.id !== id);
    // Remove from all permissions
    Object.keys(db.permissions).forEach(uid => {
      db.permissions[uid] = (db.permissions[uid] || []).filter(s => s !== project.slug);
    });
    this._save(db);
    return { success: true };
  },

  /* =======================
     USERS
  ======================== */

  /* includeOwner: false → hide owner row from admin's view */
  getUsers(includeOwner = true) {
    const users = this._get().users;
    return includeOwner ? users : users.filter(u => u.role !== 'owner');
  },

  getUserByEmail(email) {
    return this._get().users.find(u => u.email.toLowerCase() === email.toLowerCase()) || null;
  },

  getUserById(id) {
    return this._get().users.find(u => u.id === id) || null;
  },

  createUser(data) {
    const db = this._get();
    if (db.users.find(u => u.email.toLowerCase() === data.email.toLowerCase()))
      return { error: 'A user with this email already exists.' };
    const user = {
      id: this._uid(), email: data.email, name: data.name,
      role: data.role || 'user',
      password: data.password || null,
      invited: data.invited || false,
      created_at: this._today(),
      mustChangePassword: data.mustChangePassword || false
    };
    db.users.push(user);
    db.permissions[user.id] = data.permissions || [];
    this._save(db);
    return user;
  },

  updateUser(id, data) {
    const db = this._get();
    const user = db.users.find(u => u.id === id);
    if (!user) return { error: 'User not found.' };
    if (user.email === OWNER_EMAIL) return { error: 'The owner account cannot be modified.' };
    const i = db.users.findIndex(u => u.id === id);
    db.users[i] = { ...db.users[i], ...data };
    this._save(db);
    return db.users[i];
  },

  deleteUser(id) {
    const db = this._get();
    const user = db.users.find(u => u.id === id);
    if (!user) return { error: 'User not found.' };
    if (user.email === OWNER_EMAIL) return { error: 'The owner account cannot be deleted.' };
    db.users = db.users.filter(u => u.id !== id);
    delete db.permissions[id];
    this._save(db);
    return { success: true };
  },

  /* =======================
     PERMISSIONS
  ======================== */

  getUserPermissions(userId) {
    return this._get().permissions[userId] || [];
  },

  setUserPermissions(userId, projectSlugs) {
    const db = this._get();
    const user = db.users.find(u => u.id === userId);
    if (user && user.email === OWNER_EMAIL) return; // owner always sees all
    db.permissions[userId] = projectSlugs;
    this._save(db);
  },

  canUserViewProject(userId, projectSlug) {
    const db = this._get();
    const user = db.users.find(u => u.id === userId);
    if (!user) return false;
    if (user.role === 'owner') return true;
    if (user.role === 'admin') {
      const project = db.projects.find(p => p.slug === projectSlug);
      return project && project.status === 'active';
    }
    return (db.permissions[userId] || []).includes(projectSlug);
  },

  /* Reset to seed data */
  reset() { localStorage.removeItem(MOCK_DB_KEY); return this._get(); }
};
