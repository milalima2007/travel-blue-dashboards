/* ============================================================
   TRAVEL BLUE DASHBOARDS — Admin Panel Logic
   ============================================================ */

/* ---- Current state ---- */
let currentTab    = 'users';
let editingUserId = null;
let editingProjId = null;
let confirmAction = null;

/* ---- Init ---- */
function initAdmin() {
  const user = Auth.requireAdminOrOwner();
  if (!user) return;

  Auth.renderUser('#user-name', '#user-email');
  Auth.renderRoleBadge('#role-badge');

  // Build nav
  buildAdminNav(user);

  // Show/hide Projects tab in sidebar (owner only)
  if (Auth.isOwner()) {
    document.querySelectorAll('.owner-only').forEach(el => el.style.display = '');
    document.getElementById('nav-projects-admin-link').style.display = 'block';
  }

  // Read tab from URL param
  const params = new URLSearchParams(window.location.search);
  const tab = params.get('tab') || 'users';
  switchTab(tab);

  // Bind sidebar links
  document.querySelectorAll('[data-tab]').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      switchTab(link.dataset.tab);
    });
  });
}

/* ---- Build Admin dropdown in navbar ---- */
function buildAdminNav(user) {
  const dropdown = document.getElementById('nav-admin-dropdown');
  if (dropdown) dropdown.style.display = 'flex';

  const projsDropdown = document.getElementById('nav-projects-dropdown');
  if (!projsDropdown) return;

  const menu = document.getElementById('nav-projects-menu');
  const projects = MockDB.getProjects(user.role).filter(p =>
    user.role === 'owner' || p.status === 'active'
  );
  menu.innerHTML = projects.length
    ? projects.map(p => `<a href="/${p.slug}/index.html"><span class="menu-icon">${p.icon}</span> ${p.name}</a>`).join('')
    : '<div class="dropdown-label">No projects available</div>';
}

/* ---- Tab switching ---- */
function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('[data-tab]').forEach(l => l.classList.toggle('active', l.dataset.tab === tab));
  document.querySelectorAll('.tab-panel').forEach(p => p.style.display = p.id === `tab-${tab}` ? 'block' : 'none');
  if (tab === 'users')    renderUsersTable();
  if (tab === 'projects') renderProjectsTable();
  history.replaceState(null, '', `?tab=${tab}`);
}

/* ============================================================
   USERS TAB
   ============================================================ */

function renderUsersTable() {
  const isOwner = Auth.isOwner();
  // Owner sees everyone; admin sees non-owners
  const users = MockDB.getUsers(isOwner);
  const tbody = document.getElementById('users-tbody');

  if (!users.length) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><div class="empty-icon">👤</div><p>No users found.</p></div></td></tr>`;
    return;
  }

  tbody.innerHTML = users.map(u => {
    const perms    = MockDB.getUserPermissions(u.id);
    const isOwnerRow = u.role === 'owner';
    const canEdit  = isOwner || (!isOwnerRow);

    let permHtml;
    if (u.role === 'owner' || u.role === 'admin') {
      permHtml = `<span class="perm-chip-all">All active projects</span>`;
    } else if (perms.length === 0) {
      permHtml = `<span style="color:#aaa;font-size:12px;">None assigned</span>`;
    } else {
      permHtml = `<div class="perm-chips">${perms.map(s => {
        const p = MockDB.getProjectBySlug(s);
        return `<span class="perm-chip">${p ? p.icon + ' ' + p.name : s}</span>`;
      }).join('')}</div>`;
    }

    const roleBadge = {
      owner: 'badge-role-owner', admin: 'badge-role-admin', user: 'badge-role-user'
    }[u.role] || '';

    const actions = canEdit ? `
      <button class="btn-sm btn-sm-edit" onclick="openEditUser('${u.id}')">Edit</button>
      ${!isOwnerRow ? `<button class="btn-sm btn-sm-danger" onclick="confirmDeleteUser('${u.id}')">Remove</button>` : ''}
    ` : `<span style="color:#aaa;font-size:12px;">—</span>`;

    return `
      <tr>
        <td>
          <div style="font-weight:600;color:var(--navy)">${u.name}</div>
          <div style="font-size:12px;color:var(--gray)">${u.email}</div>
        </td>
        <td><span class="badge ${roleBadge}">${u.role}</span></td>
        <td>${permHtml}</td>
        <td style="font-size:12px;color:var(--gray)">${u.created_at || '—'}</td>
        <td><div class="actions-cell">${actions}</div></td>
      </tr>`;
  }).join('');
}

/* ---- Add User Modal ---- */
function openAddUser() {
  editingUserId = null;
  document.getElementById('modal-user-title').textContent = 'Add New User';
  document.getElementById('user-form').reset();
  document.getElementById('user-email-field').disabled = false;
  document.getElementById('user-role').value = 'user';
  setMethod('invite');
  buildPermChecklist(null);
  openModal('modal-user');
}

function openEditUser(id) {
  editingUserId = id;
  const u = MockDB.getUserById(id);
  if (!u) return;

  document.getElementById('modal-user-title').textContent = 'Edit User';
  document.getElementById('user-name-field').value  = u.name;
  document.getElementById('user-email-field').value = u.email;
  document.getElementById('user-email-field').disabled = true;
  document.getElementById('user-role').value = u.role;

  setMethod('manual');
  document.getElementById('method-section').style.display = 'none';
  document.getElementById('password-section').style.display = 'none';

  buildPermChecklist(MockDB.getUserPermissions(id));
  openModal('modal-user');
}

function setMethod(method) {
  document.querySelectorAll('.method-btn').forEach(b => b.classList.toggle('selected', b.dataset.method === method));
  document.getElementById('password-section').style.display = method === 'manual' ? 'block' : 'none';
  document.getElementById('invite-note').style.display = method === 'invite' ? 'block' : 'none';
}

function buildPermChecklist(selectedSlugs) {
  const projects = MockDB.getProjects('admin').filter(p => p.status === 'active');
  const container = document.getElementById('perm-checklist');
  const role = document.getElementById('user-role').value;

  if (role === 'admin') {
    container.innerHTML = `<p style="font-size:13px;color:var(--gray);padding:8px 0;">Admins automatically have access to all active projects.</p>`;
    return;
  }

  if (!projects.length) {
    container.innerHTML = `<p style="font-size:13px;color:var(--gray);">No active projects available.</p>`;
    return;
  }

  container.innerHTML = projects.map(p => {
    const checked = selectedSlugs === null ? false : (selectedSlugs || []).includes(p.slug);
    return `
      <label class="perm-item ${checked ? 'checked' : ''}" id="perm-item-${p.slug}">
        <input type="checkbox" name="perm" value="${p.slug}" ${checked ? 'checked' : ''}
               onchange="togglePermItem(this)">
        <span class="perm-item-icon">${p.icon}</span>
        <div>
          <div class="perm-item-name">${p.name}</div>
        </div>
      </label>`;
  }).join('');
}

function togglePermItem(cb) {
  const item = cb.closest('.perm-item');
  item.classList.toggle('checked', cb.checked);
}

function saveUser() {
  const name     = document.getElementById('user-name-field').value.trim();
  const email    = document.getElementById('user-email-field').value.trim();
  const role     = document.getElementById('user-role').value;
  const method   = document.querySelector('.method-btn.selected')?.dataset.method || 'invite';
  const password = document.getElementById('user-password').value;
  const errEl    = document.getElementById('user-form-error');

  errEl.style.display = 'none';

  if (!name || !email) { showFormError(errEl, 'Name and email are required.'); return; }
  if (!editingUserId && method === 'manual' && password.length < 6) {
    showFormError(errEl, 'Password must be at least 6 characters.'); return;
  }

  const selectedPerms = [...document.querySelectorAll('input[name="perm"]:checked')].map(cb => cb.value);

  if (editingUserId) {
    // Edit existing
    const res = MockDB.updateUser(editingUserId, { name, role });
    if (res.error) { showFormError(errEl, res.error); return; }
    MockDB.setUserPermissions(editingUserId, selectedPerms);
  } else {
    // Create new
    const userData = {
      name, email, role,
      password:           method === 'manual' ? password : null,
      invited:            method === 'invite',
      mustChangePassword: method === 'manual',
      permissions:        selectedPerms
    };
    const res = MockDB.createUser(userData);
    if (res.error) { showFormError(errEl, res.error); return; }

    if (method === 'invite') {
      showToast(`✉️  Invite sent to ${email} (simulated — Supabase in Phase 2)`);
    }
  }

  closeModal('modal-user');
  renderUsersTable();
  showToast(editingUserId ? 'User updated successfully.' : 'User created successfully.');
}

function confirmDeleteUser(id) {
  const u = MockDB.getUserById(id);
  if (!u) return;
  document.getElementById('confirm-msg').innerHTML =
    `Are you sure you want to remove <strong>${u.name}</strong> (${u.email})?<br>This action cannot be undone.`;
  confirmAction = () => {
    MockDB.deleteUser(id);
    renderUsersTable();
    showToast('User removed.');
  };
  openModal('modal-confirm');
}

/* ============================================================
   PROJECTS TAB (owner only)
   ============================================================ */

function renderProjectsTable() {
  const projects = MockDB.getProjects('owner');
  const tbody    = document.getElementById('projects-tbody');

  if (!projects.length) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><div class="empty-icon">📁</div><p>No projects yet. Create your first one.</p></div></td></tr>`;
    return;
  }

  tbody.innerHTML = projects.map(p => {
    const statusBadge = {
      active:   `<span class="badge badge-active">● Active</span>`,
      draft:    `<span class="badge badge-draft">◐ Draft</span>`,
      archived: `<span class="badge badge-archived">○ Archived</span>`
    }[p.status] || '';

    const actions = `
      <div class="actions-cell">
        <button class="btn-sm btn-sm-edit" onclick="openEditProject('${p.id}')">Edit</button>
        ${p.status === 'draft'    ? `<button class="btn-sm btn-sm-success" onclick="publishProject('${p.id}')">Publish</button>` : ''}
        ${p.status === 'active'   ? `<button class="btn-sm btn-sm-warn"    onclick="archiveProject('${p.id}')">Archive</button>` : ''}
        ${p.status === 'archived' ? `<button class="btn-sm btn-sm-warn"    onclick="draftProject('${p.id}')">Restore</button>` : ''}
        <button class="btn-sm btn-sm-danger" onclick="confirmDeleteProject('${p.id}')">Delete</button>
      </div>`;

    return `
      <tr>
        <td>
          <div style="display:flex;align-items:center;gap:10px;">
            <span style="font-size:20px;">${p.icon}</span>
            <div>
              <div style="font-weight:600;color:var(--navy)">${p.name}</div>
              <div style="font-size:11px;color:var(--gray);font-family:monospace">/${p.slug}/</div>
            </div>
          </div>
        </td>
        <td>${statusBadge}</td>
        <td style="font-size:12px;color:var(--gray);max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${p.description}</td>
        <td style="font-size:12px;color:var(--gray)">${p.published_at || p.created_at}</td>
        <td>${actions}</td>
      </tr>`;
  }).join('');
}

function openAddProject() {
  editingProjId = null;
  document.getElementById('modal-proj-title').textContent = 'New Project';
  document.getElementById('proj-form').reset();
  document.getElementById('proj-slug').disabled = false;
  document.getElementById('proj-form-error').style.display = 'none';
  openModal('modal-project');
}

function openEditProject(id) {
  editingProjId = id;
  const p = MockDB.getProject(id);
  if (!p) return;
  document.getElementById('modal-proj-title').textContent = 'Edit Project';
  document.getElementById('proj-name').value    = p.name;
  document.getElementById('proj-slug').value    = p.slug;
  document.getElementById('proj-slug').disabled = true;
  document.getElementById('proj-icon').value    = p.icon;
  document.getElementById('proj-desc').value    = p.description;
  document.getElementById('proj-form-error').style.display = 'none';
  openModal('modal-project');
}

function saveProject() {
  const name = document.getElementById('proj-name').value.trim();
  const slug = document.getElementById('proj-slug').value.trim().toLowerCase().replace(/\s+/g, '-');
  const icon = document.getElementById('proj-icon').value.trim() || '📊';
  const desc = document.getElementById('proj-desc').value.trim();
  const errEl = document.getElementById('proj-form-error');
  errEl.style.display = 'none';

  if (!name || !slug) { showFormError(errEl, 'Name and slug are required.'); return; }

  if (editingProjId) {
    const res = MockDB.updateProject(editingProjId, { name, icon, description: desc });
    if (res.error) { showFormError(errEl, res.error); return; }
    showToast('Project updated.');
  } else {
    const res = MockDB.createProject({ name, slug, icon, description: desc });
    if (res.error) { showFormError(errEl, res.error); return; }
    showToast('Project created as Draft. Set permissions and publish when ready.');
  }

  closeModal('modal-project');
  renderProjectsTable();
  buildAdminNav(Auth.getUser());
}

function publishProject(id) {
  MockDB.publishProject(id);
  renderProjectsTable();
  showToast('Project published and now visible to authorised users.');
}

function archiveProject(id) {
  MockDB.archiveProject(id);
  renderProjectsTable();
  showToast('Project archived.');
}

function draftProject(id) {
  MockDB.draftProject(id);
  renderProjectsTable();
  showToast('Project restored to Draft.');
}

function confirmDeleteProject(id) {
  const p = MockDB.getProject(id);
  if (!p) return;
  document.getElementById('confirm-msg').innerHTML =
    `Are you sure you want to delete <strong>${p.name}</strong>?<br>All user permissions for this project will also be removed.`;
  confirmAction = () => {
    MockDB.deleteProject(id);
    renderProjectsTable();
    showToast('Project deleted.');
  };
  openModal('modal-confirm');
}

/* ============================================================
   MODAL HELPERS
   ============================================================ */
function openModal(id) {
  document.getElementById(id).classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeModal(id) {
  document.getElementById(id).classList.remove('open');
  document.body.style.overflow = '';
}
function runConfirm() {
  if (confirmAction) { confirmAction(); confirmAction = null; }
  closeModal('modal-confirm');
}

function showFormError(el, msg) { el.textContent = msg; el.style.display = 'block'; }

/* Close modal when clicking overlay */
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
    document.body.style.overflow = '';
  }
});

/* ---- Toast ---- */
function showToast(msg) {
  const t = document.createElement('div');
  t.style.cssText = `position:fixed;bottom:28px;left:50%;transform:translateX(-50%) translateY(20px);
    background:var(--navy);color:#fff;padding:12px 22px;border-radius:8px;font-size:13.5px;
    font-weight:600;z-index:9999;box-shadow:0 8px 24px rgba(0,0,0,0.2);
    opacity:0;transition:all 0.3s ease;max-width:90vw;text-align:center;`;
  t.textContent = msg;
  document.body.appendChild(t);
  requestAnimationFrame(() => { t.style.opacity = '1'; t.style.transform = 'translateX(-50%) translateY(0)'; });
  setTimeout(() => {
    t.style.opacity = '0'; t.style.transform = 'translateX(-50%) translateY(10px)';
    setTimeout(() => t.remove(), 300);
  }, 3500);
}

/* ---- Auto-generate slug from name ---- */
document.addEventListener('DOMContentLoaded', () => {
  const nameField = document.getElementById('proj-name');
  const slugField = document.getElementById('proj-slug');
  if (nameField && slugField) {
    nameField.addEventListener('input', () => {
      if (!editingProjId && !slugField.dataset.manual) {
        slugField.value = nameField.value.toLowerCase()
          .replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-').replace(/-+/g, '-').trim();
      }
    });
    slugField.addEventListener('input', () => { slugField.dataset.manual = '1'; });
  }

  // Bind role change to rebuild perm checklist
  const roleSelect = document.getElementById('user-role');
  if (roleSelect) {
    roleSelect.addEventListener('change', () => buildPermChecklist(null));
  }

  // Bind method buttons
  document.querySelectorAll('.method-btn').forEach(btn => {
    btn.addEventListener('click', () => setMethod(btn.dataset.method));
  });

  initAdmin();
});
