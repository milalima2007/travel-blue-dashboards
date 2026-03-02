/* ============================================================
   TRAVEL BLUE DASHBOARDS — Admin Panel Logic
   ============================================================ */

/* ---- Current state ---- */
let currentTab    = 'users';
let editingUserId = null;
let editingProjId = null;
let confirmAction = null;
let _adminUser    = null;

/* ============================================================
   EMOJI PICKER
   ============================================================ */
const EMOJI_CATEGORIES = [
  { label: 'Charts & Data',     emojis: ['📊','📈','📉','📋','📌','🗂','💹','📁','🗃','📐','🔢','📎'] },
  { label: 'Business',          emojis: ['💼','💰','💵','🤝','🏆','🎯','✅','📑','🥇','🔑','📧','📩'] },
  { label: 'Travel & Products', emojis: ['✈️','🧳','🗺','🌍','🌐','🛫','🏨','🎒','🧤','👜','🎁','🛒'] },
  { label: 'General',           emojis: ['⭐','🌟','🔥','💡','🔔','📢','🎉','🚀','⚡','🔍','🌱','🌿'] }
];

function _buildEmojiDropdown() {
  const dd = document.getElementById('emoji-dropdown');
  if (!dd || dd.dataset.built) return;
  dd.innerHTML = EMOJI_CATEGORIES.map(cat => `
    <div class="emoji-cat-label">${cat.label}</div>
    <div class="emoji-grid">
      ${cat.emojis.map(e => `<button type="button" class="emoji-btn" data-emoji="${e}" onclick="selectEmoji('${e}')">${e}</button>`).join('')}
    </div>
  `).join('');
  dd.dataset.built = '1';
  // Highlight whichever emoji is currently selected
  const current = document.getElementById('proj-icon')?.value;
  if (current) dd.querySelectorAll('.emoji-btn').forEach(b => b.classList.toggle('selected', b.dataset.emoji === current));
}

function toggleEmojiPicker(e) {
  e.stopPropagation();
  _buildEmojiDropdown();
  const dd  = document.getElementById('emoji-dropdown');
  const btn = document.getElementById('emoji-preview-btn');
  const open = dd.style.display !== 'none';
  dd.style.display = open ? 'none' : 'block';
  if (btn) btn.classList.toggle('open', !open);
}

function selectEmoji(emoji) {
  document.getElementById('proj-icon').value              = emoji;
  document.getElementById('emoji-preview-display').textContent = emoji;
  // Highlight selected button
  document.querySelectorAll('.emoji-btn').forEach(b => b.classList.toggle('selected', b.dataset.emoji === emoji));
  // Close dropdown
  const dd  = document.getElementById('emoji-dropdown');
  const btn = document.getElementById('emoji-preview-btn');
  if (dd)  dd.style.display = 'none';
  if (btn) btn.classList.remove('open');
}

function _closeEmojiPicker() {
  const dd  = document.getElementById('emoji-dropdown');
  const btn = document.getElementById('emoji-preview-btn');
  if (dd)  dd.style.display = 'none';
  if (btn) btn.classList.remove('open');
}

// Close emoji picker when clicking outside
document.addEventListener('click', e => {
  const wrap = document.getElementById('emoji-picker-wrap');
  if (wrap && !wrap.contains(e.target)) _closeEmojiPicker();
});

/* ---- CSV upload state (update-data flow) ---- */
let csvFile          = null;
let csvAnalysisState = null;
let csvProjectSlug   = null;
let csvProjectName   = null;

/* ---- New project CSV state ---- */
let newProjCsvFile = null;

/* ---- Init ---- */
async function initAdmin() {
  const user = await Auth.requireAdminOrOwner();
  if (!user) return;

  _adminUser = user;

  Auth.renderUser(user, '#user-name', '#user-email');
  Auth.renderRoleBadge(user, '#role-badge');

  await buildAdminNav(user);

  if (Auth.isOwner(user)) {
    document.querySelectorAll('.owner-only').forEach(el => el.style.display = '');
    document.getElementById('nav-projects-admin-link').style.display = 'block';
  }

  const params = new URLSearchParams(window.location.search);
  const tab    = params.get('tab') || 'users';
  switchTab(tab);

  // Auto-open CSV upload modal if ?upload=<slug> is in URL
  const uploadSlug = params.get('upload');
  if (uploadSlug && Auth.isAdminOrOwner(user)) {
    const proj = await DataLayer.getProjectBySlug(uploadSlug);
    if (proj) openUploadCSVForProject(proj);
  }

  document.querySelectorAll('[data-tab]').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      switchTab(link.dataset.tab);
    });
  });
}

/* ---- Build Admin dropdown in navbar ---- */
async function buildAdminNav(user) {
  const dropdown = document.getElementById('nav-admin-dropdown');
  if (dropdown) dropdown.style.display = 'flex';

  const menu = document.getElementById('nav-projects-menu');
  if (!menu) return;

  const role     = Auth.role(user);
  const projects = await DataLayer.getProjects(role);
  const visible  = projects.filter(p => role === 'owner' || p.status === 'active');
  menu.innerHTML = visible.length
    ? visible.map(p => `<a href="${p.custom_url || '/project/index.html?slug=' + p.slug}"><span class="menu-icon">${p.icon}</span> ${p.name}</a>`).join('')
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

async function renderUsersTable() {
  const isOwner = Auth.isOwner(_adminUser);
  const tbody   = document.getElementById('users-tbody');
  tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><div class="empty-icon">⏳</div><p>Loading…</p></div></td></tr>`;

  const [users, projects] = await Promise.all([
    DataLayer.getUsers(isOwner),
    DataLayer.getProjects('owner')
  ]);
  const projMap = Object.fromEntries(projects.map(p => [p.slug, p]));

  if (!users.length) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><div class="empty-icon">👤</div><p>No users found.</p></div></td></tr>`;
    return;
  }

  tbody.innerHTML = users.map(u => {
    const isOwnerRow = u.role === 'owner';
    const canEdit    = isOwner || !isOwnerRow;

    let permHtml;
    if (u.role === 'owner' || u.role === 'admin') {
      permHtml = `<span class="perm-chip-all">All active projects</span>`;
    } else if (!u.projects.length) {
      permHtml = `<span style="color:#aaa;font-size:12px;">None assigned</span>`;
    } else {
      permHtml = `<div class="perm-chips">${u.projects.map(s => {
        const p = projMap[s];
        return `<span class="perm-chip">${p ? p.icon + ' ' + p.name : s}</span>`;
      }).join('')}</div>`;
    }

    const roleBadge = { owner: 'badge-role-owner', admin: 'badge-role-admin', user: 'badge-role-user' }[u.role] || '';
    const actions   = canEdit ? `
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

function openAddUser() {
  editingUserId = null;
  document.getElementById('modal-user-title').textContent = 'Add New User';
  document.getElementById('user-form').reset();
  document.getElementById('user-email-field').disabled = false;
  document.getElementById('user-role').value = 'user';
  document.getElementById('method-section').style.display = '';
  document.getElementById('password-section').style.display = 'none';
  setMethod('invite');
  buildPermChecklist(null);
  openModal('modal-user');
}

async function openEditUser(id) {
  editingUserId = id;
  const u = await DataLayer.getUserById(id);
  if (!u) return;

  document.getElementById('modal-user-title').textContent = 'Edit User';
  document.getElementById('user-name-field').value  = u.name;
  document.getElementById('user-email-field').value = u.email;
  document.getElementById('user-email-field').disabled = true;
  document.getElementById('user-role').value = u.role;

  setMethod('manual');
  document.getElementById('method-section').style.display = 'none';
  document.getElementById('password-section').style.display = 'none';

  buildPermChecklist(u.projects);
  openModal('modal-user');
}

function setMethod(method) {
  document.querySelectorAll('.method-btn').forEach(b => b.classList.toggle('selected', b.dataset.method === method));
  document.getElementById('password-section').style.display = method === 'manual' ? 'block' : 'none';
  document.getElementById('invite-note').style.display = method === 'invite' ? 'block' : 'none';
}

async function buildPermChecklist(selectedSlugs) {
  const allProjects = await DataLayer.getProjects('admin');
  const projects    = allProjects.filter(p => p.status === 'active');
  const container   = document.getElementById('perm-checklist');
  const role        = document.getElementById('user-role').value;

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
  cb.closest('.perm-item').classList.toggle('checked', cb.checked);
}

async function saveUser() {
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
    const res = await DataLayer.updateUser(editingUserId, { name, role });
    if (res.error) { showFormError(errEl, res.error); return; }
    await DataLayer.setUserPermissions(editingUserId, selectedPerms);
  } else {
    const userData = {
      name, email, role,
      password:    method === 'manual' ? password : null,
      invited:     method === 'invite',
      permissions: selectedPerms
    };
    const res = await DataLayer.createUser(userData);
    if (res.error) { showFormError(errEl, res.error); return; }
    if (method === 'invite') showToast(`✉️  Invite sent to ${email}`);
  }

  closeModal('modal-user');
  renderUsersTable();
  showToast(editingUserId ? 'User updated successfully.' : 'User created successfully.');
}

async function confirmDeleteUser(id) {
  const u = await DataLayer.getUserById(id);
  if (!u) return;
  document.getElementById('confirm-msg').innerHTML =
    `Are you sure you want to remove <strong>${u.name}</strong> (${u.email})?<br>This action cannot be undone.`;
  confirmAction = async () => {
    const res = await DataLayer.deleteUser(id);
    if (res?.error) throw new Error(res.error);
    await renderUsersTable();
    showToast('User removed.');
  };
  openModal('modal-confirm');
}

/* ============================================================
   PROJECTS TAB (owner only)
   ============================================================ */

async function renderProjectsTable() {
  const tbody = document.getElementById('projects-tbody');
  tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><div class="empty-icon">⏳</div><p>Loading…</p></div></td></tr>`;

  const projects = await DataLayer.getProjects('owner');

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
        <button class="btn-sm btn-sm-edit"   onclick="openEditProject('${p.id}')">Edit</button>
        <button class="btn-sm btn-sm-upload" onclick="openUploadCSVById('${p.id}')">⬆ Data</button>
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
        <td style="font-size:12px;color:var(--gray)">${p.published_at ? p.published_at.split('T')[0] : p.created_at ? p.created_at.split('T')[0] : '—'}</td>
        <td>${actions}</td>
      </tr>`;
  }).join('');
}

function openAddProject() {
  editingProjId  = null;
  newProjCsvFile = null;
  document.getElementById('modal-proj-title').textContent = 'New Project';
  document.getElementById('proj-form').reset();
  document.getElementById('proj-slug').disabled = false;
  document.getElementById('proj-form-error').style.display = 'none';
  document.getElementById('proj-save-btn').textContent = 'Create Project';
  _clearNewProjCsv();
  selectEmoji('📊');
  _closeEmojiPicker();
  const csvSec = document.getElementById('new-proj-csv-section');
  if (csvSec) csvSec.style.display = 'block';
  const note = document.getElementById('proj-note');
  if (note) note.style.display = 'block';
  openModal('modal-project');
}

async function openEditProject(id) {
  editingProjId = id;
  const p = await DataLayer.getProject(id);
  if (!p) return;
  document.getElementById('modal-proj-title').textContent = 'Edit Project';
  document.getElementById('proj-name').value    = p.name;
  document.getElementById('proj-slug').value    = p.slug;
  document.getElementById('proj-slug').disabled = true;
  selectEmoji(p.icon || '📊');
  _closeEmojiPicker();
  document.getElementById('proj-desc').value    = p.description;
  document.getElementById('proj-form-error').style.display = 'none';
  document.getElementById('proj-save-btn').textContent = 'Save Changes';
  const csvSec = document.getElementById('new-proj-csv-section');
  if (csvSec) csvSec.style.display = 'none';
  const note = document.getElementById('proj-note');
  if (note) note.style.display = 'none';
  openModal('modal-project');
}

async function saveProject() {
  const name  = document.getElementById('proj-name').value.trim();
  const slug  = document.getElementById('proj-slug').value.trim().toLowerCase().replace(/\s+/g, '-');
  const icon  = document.getElementById('proj-icon').value.trim() || '📊';
  const desc  = document.getElementById('proj-desc').value.trim();
  const errEl = document.getElementById('proj-form-error');
  const btn   = document.getElementById('proj-save-btn');
  const origLabel = editingProjId ? 'Save Changes' : 'Create Project';

  errEl.style.display = 'none';
  if (!name || !slug) { showFormError(errEl, 'Name and slug are required.'); return; }

  btn.disabled = true;

  try {
    if (editingProjId) {
      btn.textContent = 'Saving…';
      const res = await DataLayer.updateProject(editingProjId, { name, icon, description: desc });
      if (res?.error) { showFormError(errEl, res.error); btn.disabled = false; btn.textContent = origLabel; return; }
      showToast('Project updated.');
      closeModal('modal-project');
      await renderProjectsTable();
      await buildAdminNav(_adminUser);
      return;
    }

    // Create new project
    btn.textContent = 'Creating…';
    const res = await DataLayer.createProject({ name, slug, icon, description: desc });
    if (res?.error) { showFormError(errEl, res.error); btn.disabled = false; btn.textContent = origLabel; return; }

    // If CSV file was chosen, upload it
    if (newProjCsvFile) {
      btn.textContent = 'Analysing CSV…';
      const state = await CSVUpload.analyse(newProjCsvFile, slug);
      btn.textContent = 'Uploading…';
      await CSVUpload.confirm(state, null);
      showToast('Project created with data! Redirecting to dashboard…');
      closeModal('modal-project');
      setTimeout(() => { window.location.href = `/project/index.html?slug=${slug}`; }, 1200);
    } else {
      btn.disabled = false; btn.textContent = origLabel;
      showToast('Project created as Draft.');
      closeModal('modal-project');
      await renderProjectsTable();
      await buildAdminNav(_adminUser);
    }

  } catch (e) {
    console.error('[saveProject]', e);
    btn.disabled = false;
    btn.textContent = origLabel;
    showFormError(errEl, 'Error: ' + (e.message || String(e)));
  }
}

async function publishProject(id) {
  await DataLayer.publishProject(id);
  renderProjectsTable();
  showToast('Project published and now visible to authorised users.');
}

async function archiveProject(id) {
  await DataLayer.archiveProject(id);
  renderProjectsTable();
  showToast('Project archived.');
}

async function draftProject(id) {
  await DataLayer.draftProject(id);
  renderProjectsTable();
  showToast('Project restored to Draft.');
}

async function confirmDeleteProject(id) {
  const p = await DataLayer.getProject(id);
  if (!p) return;
  document.getElementById('confirm-msg').innerHTML =
    `Are you sure you want to delete <strong>${p.name}</strong>?<br>All data for this project will also be permanently removed.`;
  confirmAction = async () => {
    const res = await DataLayer.deleteProject(id);
    if (res?.error) throw new Error(res.error);
    await renderProjectsTable();
    await buildAdminNav(_adminUser);
    showToast('Project deleted.');
  };
  openModal('modal-confirm');
}

/* ============================================================
   CSV UPLOAD HANDLERS
   ============================================================ */

/* Called from Projects table "⬆ Data" button (has project id) */
async function openUploadCSVById(projId) {
  const p = await DataLayer.getProject(projId);
  if (!p) return;
  openUploadCSVForProject(p);
}

/* Open the upload modal for a project object */
function openUploadCSVForProject(p) {
  csvFile          = null;
  csvAnalysisState = null;
  csvProjectSlug   = p.slug;
  csvProjectName   = p.name;

  document.getElementById('csv-proj-name').textContent = p.name;
  _csvShowStep('drop');

  const input    = document.getElementById('csv-file-input');
  const dropzone = document.getElementById('csv-dropzone');
  if (input)    input.value = '';
  if (dropzone) dropzone.classList.remove('has-file');
  document.getElementById('csv-file-name').style.display = 'none';
  document.getElementById('csv-analyse-btn').style.display = 'none';

  openModal('modal-csv-upload');
}

function _csvShowStep(step) {
  ['drop', 'analysing', 'preview', 'progress', 'result'].forEach(s => {
    const el = document.getElementById(`csv-step-${s}`);
    if (el) el.style.display = (s === step) ? 'block' : 'none';
  });
  const confirmBtn = document.getElementById('csv-confirm-btn');
  if (confirmBtn) confirmBtn.style.display = (step === 'preview') ? '' : 'none';
}

function closeCsvModal() {
  closeModal('modal-csv-upload');
  csvFile = null;
  csvAnalysisState = null;
}

function _onCsvFileChosen(file) {
  if (!file) return;
  if (!file.name.match(/\.csv$/i)) {
    showToast('Please select a valid .csv file.'); return;
  }
  csvFile = file;
  const nameEl = document.getElementById('csv-file-name');
  nameEl.textContent = `📄 ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  nameEl.style.display = 'block';
  document.getElementById('csv-dropzone').classList.add('has-file');
  document.getElementById('csv-analyse-btn').style.display = '';
}

async function runAnalyse() {
  if (!csvFile) { showToast('Please select a CSV file first.'); return; }
  _csvShowStep('analysing');

  try {
    csvAnalysisState = await CSVUpload.analyse(csvFile, csvProjectSlug);
    _renderCsvPreview(csvAnalysisState);
    _csvShowStep('preview');
  } catch (err) {
    showToast('Error: ' + err.message);
    _csvShowStep('drop');
  }
}

function _renderCsvPreview(state) {
  const typeLabels = { date: '📅 date', numeric: '🔢 numeric', categorical: '🏷 category' };
  const keySet     = new Set(state.keys);

  const chips = Object.entries(state.types).map(([col, type]) => {
    const isKey = keySet.has(col);
    return `<span class="col-chip col-chip-${type}${isKey ? ' col-chip-key' : ''}">
      ${isKey ? '🔑 ' : ''}${col} <em style="font-style:normal;opacity:0.7;">${typeLabels[type] || type}</em>
    </span>`;
  }).join('');

  document.getElementById('csv-col-types').innerHTML = `
    <div class="upload-section-label">Detected Columns (${Object.keys(state.types).length})</div>
    <div class="col-types-wrap">${chips}</div>
    <p style="font-size:12px;color:var(--gray);margin-top:8px;">
      🔑 Duplicate-detection key: <strong>${state.keys.join(' + ')}</strong>
    </p>`;

  const { newRows, updateRows, unchangedRows } = state.diff;
  const noChanges = newRows.length + updateRows.length === 0;
  document.getElementById('csv-diff').innerHTML = `
    <div class="upload-section-label" style="margin-top:18px;">Data Preview (${state.records.length} rows in file)</div>
    <div class="diff-summary">
      <div class="diff-card new-rows"><div class="diff-count">${newRows.length}</div><div class="diff-label">New rows</div></div>
      <div class="diff-card update-rows"><div class="diff-count">${updateRows.length}</div><div class="diff-label">Updated</div></div>
      <div class="diff-card same-rows"><div class="diff-count">${unchangedRows.length}</div><div class="diff-label">Unchanged</div></div>
    </div>
    ${noChanges ? `<p style="font-size:13px;color:var(--gray);margin-top:10px;text-align:center;">⚠️ No new or changed rows detected — nothing will be written.</p>` : ''}`;
}

async function runConfirmUpload() {
  if (!csvAnalysisState) return;
  _csvShowStep('progress');

  try {
    const result = await CSVUpload.confirm(csvAnalysisState, (msg, pct) => {
      const lbl = document.getElementById('csv-progress-label');
      const bar = document.getElementById('csv-progress-bar');
      if (lbl) lbl.textContent = msg;
      if (bar) { bar.style.width = pct + '%'; if (pct === 100) bar.classList.add('done'); }
    });
    _showUploadResult(result);
  } catch (err) {
    showToast('Upload failed: ' + err.message);
    _csvShowStep('preview');
  }
}

function _showUploadResult(result) {
  document.getElementById('csv-result-content').innerHTML = `
    <div class="upload-result success" style="text-align:center;padding:24px 18px;">
      <div class="upload-result-icon">✅</div>
      <div class="upload-result-title">Upload complete!</div>
      <div class="upload-result-stats" style="margin:10px 0 18px;">
        <span>${result.inserted}</span> new &nbsp;·&nbsp;
        <span>${result.updated}</span> updated &nbsp;·&nbsp;
        <span>${result.unchanged}</span> unchanged
      </div>
      <a href="/project/index.html?slug=${csvProjectSlug}"
         style="display:inline-block;padding:10px 28px;background:var(--navy);color:#fff;
                border-radius:7px;text-decoration:none;font-weight:700;font-size:14px;">
        View Dashboard →
      </a>
    </div>`;

  _csvShowStep('result');
  renderProjectsTable();
  showToast(`✅ Data uploaded for ${csvProjectName}!`);
}

/* ---- New Project CSV helpers ---- */
function _clearNewProjCsv() {
  newProjCsvFile = null;
  const placeholder = document.getElementById('new-proj-csv-placeholder');
  const selected    = document.getElementById('new-proj-csv-selected');
  const clearBtn    = document.getElementById('new-proj-csv-clear');
  const input       = document.getElementById('new-proj-csv-input');
  if (placeholder) placeholder.style.display = 'flex';
  if (selected)    selected.style.display    = 'none';
  if (clearBtn)    clearBtn.style.display    = 'none';
  if (input)       input.value               = '';
}

function clearNewProjCsv() { _clearNewProjCsv(); }

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
async function runConfirm() {
  const btn = document.querySelector('#modal-confirm .btn-sm-danger');
  if (btn) { btn.disabled = true; btn.textContent = 'Processing…'; }
  try {
    if (confirmAction) { await confirmAction(); confirmAction = null; }
    closeModal('modal-confirm');
  } catch (e) {
    console.error('[runConfirm]', e);
    showToast('Error: ' + (e.message || String(e)));
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Yes, proceed'; }
  }
}

function showFormError(el, msg) { el.textContent = msg; el.style.display = 'block'; }

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

/* ---- DOMContentLoaded ---- */
document.addEventListener('DOMContentLoaded', async () => {
  // Auto-generate slug from project name
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

  // Role change → rebuild perm checklist
  const roleSelect = document.getElementById('user-role');
  if (roleSelect) roleSelect.addEventListener('change', () => buildPermChecklist(null));

  // Method buttons
  document.querySelectorAll('.method-btn').forEach(btn => {
    btn.addEventListener('click', () => setMethod(btn.dataset.method));
  });

  // CSV upload modal: file input
  const csvInput = document.getElementById('csv-file-input');
  if (csvInput) csvInput.addEventListener('change', e => _onCsvFileChosen(e.target.files[0]));

  // CSV upload modal: drag-and-drop
  const dropzone = document.getElementById('csv-dropzone');
  if (dropzone) {
    dropzone.addEventListener('dragover',  e => { e.preventDefault(); dropzone.classList.add('drag-over'); });
    dropzone.addEventListener('dragleave', ()  => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop',      e  => {
      e.preventDefault(); dropzone.classList.remove('drag-over');
      _onCsvFileChosen(e.dataTransfer.files[0]);
    });
  }

  // New project CSV input
  const newProjInput = document.getElementById('new-proj-csv-input');
  if (newProjInput) {
    newProjInput.addEventListener('change', e => {
      const file = e.target.files[0];
      if (!file) return;
      if (!file.name.match(/\.csv$/i)) { showToast('Please select a .csv file.'); return; }
      newProjCsvFile = file;
      document.getElementById('new-proj-csv-placeholder').style.display = 'none';
      document.getElementById('new-proj-csv-selected').style.display    = 'flex';
      document.getElementById('new-proj-csv-selected').querySelector('span').textContent =
        `📄 ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      document.getElementById('new-proj-csv-clear').style.display = 'inline-block';
    });
  }

  // Theme toggle
  const themeBtn = document.getElementById('btn-theme');
  if (themeBtn) themeBtn.addEventListener('click', () => ThemeToggle.toggle());

  await initAdmin();
});
