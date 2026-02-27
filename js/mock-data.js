/* ============================================================
   TRAVEL BLUE DASHBOARDS — Data Layer (Supabase)
   All methods are async. Replaces localStorage MockDB.
   ============================================================ */

const MockDB = (() => {

  let _anonClient = null, _svcClient = null;

  function _anon() {
    if (!_anonClient)
      _anonClient = supabase.createClient(window.SUPABASE_URL, window.SUPABASE_KEY);
    return _anonClient;
  }

  function _svc() {
    if (!_svcClient)
      _svcClient = supabase.createClient(window.SUPABASE_URL, window.SUPABASE_SERVICE_KEY);
    return _svcClient;
  }

  /* ── PROJECTS ─────────────────────────────────────────────────────── */

  async function getProjects(role = 'user') {
    let query = _anon().from('projects').select('*').order('created_at', { ascending: true });
    if (role === 'user')  query = query.eq('status', 'active');
    if (role === 'admin') query = query.in('status', ['active', 'draft']);
    // role === 'owner' → no filter, returns all statuses
    const { data, error } = await query;
    if (error) { console.error('getProjects:', error.message); return []; }
    return data || [];
  }

  async function getProject(id) {
    const { data } = await _anon().from('projects').select('*').eq('id', id).maybeSingle();
    return data || null;
  }

  async function getProjectBySlug(slug) {
    const { data } = await _anon().from('projects').select('*').eq('slug', slug).maybeSingle();
    return data || null;
  }

  async function createProject(data) {
    const { data: proj, error } = await _svc()
      .from('projects')
      .insert({ slug: data.slug, name: data.name, description: data.description || '',
                icon: data.icon || '📊', status: 'draft' })
      .select().single();
    if (error)
      return { error: error.code === '23505' ? 'A project with this slug already exists.' : error.message };
    return proj;
  }

  async function updateProject(id, data) {
    const { data: proj, error } = await _svc()
      .from('projects').update(data).eq('id', id).select().single();
    if (error) return { error: error.message };
    return proj;
  }

  async function publishProject(id) {
    return updateProject(id, { status: 'active', published_at: new Date().toISOString() });
  }

  async function archiveProject(id) { return updateProject(id, { status: 'archived' }); }

  async function draftProject(id) {
    return updateProject(id, { status: 'draft', published_at: null });
  }

  async function deleteProject(id) {
    const proj = await getProject(id);
    if (!proj) return { error: 'Project not found.' };
    // Clean up related tables
    await _svc().from('project_data').delete().eq('project_slug', proj.slug);
    await _svc().from('project_meta').delete().eq('project_slug', proj.slug);
    const { error } = await _svc().from('projects').delete().eq('id', id);
    if (error) return { error: error.message };
    return { success: true };
  }

  /* ── USERS (Supabase Auth Admin API) ─────────────────────────────── */

  async function getUsers(includeOwner = true) {
    const { data: { users }, error } = await _svc().auth.admin.listUsers({ perPage: 1000 });
    if (error) { console.error('getUsers:', error.message); return []; }
    return (users || [])
      .filter(u => includeOwner || (u.user_metadata?.role !== 'owner'))
      .map(u => ({
        id:         u.id,
        email:      u.email,
        name:       u.user_metadata?.name || u.email,
        role:       u.user_metadata?.role || 'user',
        projects:   u.user_metadata?.projects || [],
        created_at: u.created_at ? u.created_at.split('T')[0] : '—',
      }));
  }

  async function getUserById(id) {
    const { data: { user }, error } = await _svc().auth.admin.getUserById(id);
    if (error || !user) return null;
    return {
      id:         user.id,
      email:      user.email,
      name:       user.user_metadata?.name || user.email,
      role:       user.user_metadata?.role || 'user',
      projects:   user.user_metadata?.projects || [],
      created_at: user.created_at ? user.created_at.split('T')[0] : '—',
    };
  }

  async function getUserPermissions(userId) {
    const user = await getUserById(userId);
    return user?.projects || [];
  }

  async function setUserPermissions(userId, projectSlugs) {
    const { data: { user } } = await _svc().auth.admin.getUserById(userId);
    const meta = { ...(user?.user_metadata || {}), projects: projectSlugs };
    await _svc().auth.admin.updateUserById(userId, { user_metadata: meta });
  }

  async function createUser(data) {
    if (data.invited) {
      const { error } = await _svc().auth.admin.inviteUserByEmail(data.email, {
        data: { name: data.name, role: data.role || 'user', projects: data.permissions || [] }
      });
      if (error) return { error: error.message };
    } else {
      const { error } = await _svc().auth.admin.createUser({
        email: data.email, password: data.password, email_confirm: true,
        user_metadata: { name: data.name, role: data.role || 'user', projects: data.permissions || [] }
      });
      if (error) return { error: error.message };
    }
    return { success: true, email: data.email };
  }

  async function updateUser(id, data) {
    const { data: { user } } = await _svc().auth.admin.getUserById(id);
    const meta = { ...(user?.user_metadata || {}), name: data.name, role: data.role };
    const { error } = await _svc().auth.admin.updateUserById(id, { user_metadata: meta });
    if (error) return { error: error.message };
    return { success: true };
  }

  async function deleteUser(id) {
    const { error } = await _svc().auth.admin.deleteUser(id);
    if (error) return { error: error.message };
    return { success: true };
  }

  /* ── PUBLIC API ───────────────────────────────────────────────────── */
  return {
    getProjects, getProject, getProjectBySlug,
    createProject, updateProject, publishProject, archiveProject, draftProject, deleteProject,
    getUsers, getUserById, getUserPermissions, setUserPermissions,
    createUser, updateUser, deleteUser,
  };

})();
