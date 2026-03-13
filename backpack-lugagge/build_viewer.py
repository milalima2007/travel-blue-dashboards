"""
build_viewer.py — bundles backpack-lugagge/index.html into a single
standalone viewer.html with all local CSS/JS inlined and auth removed.
Run from any directory: python backpack-lugagge/build_viewer.py
"""
import os, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASH = os.path.join(BASE, "backpack-lugagge", "index.html")
OUT  = os.path.join(BASE, "backpack-lugagge", "viewer.html")

def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()

html = read(DASH)
css  = read(os.path.join(BASE, "css",  "style.css"))
cfg  = read(os.path.join(BASE, "js",   "config.js"))
dl   = read(os.path.join(BASE, "js",   "data-layer.js"))
auth = read(os.path.join(BASE, "js",   "auth.js"))
thm  = read(os.path.join(BASE, "js",   "theme.js"))

# ── 1. Inline CSS ──────────────────────────────────────────────────
html = html.replace(
    '<link rel="stylesheet" href="/css/style.css" />',
    f'<style>\n{css}\n</style>'
)

# ── 2. Inline local JS files ──────────────────────────────────────
html = html.replace('<script src="/js/config.js"></script>',
                    f'<script>\n{cfg}\n</script>')
html = html.replace('<script src="/js/data-layer.js"></script>',
                    f'<script>\n{dl}\n</script>')
html = html.replace('<script src="/js/auth.js"></script>',
                    f'<script>\n{auth}\n</script>')
html = html.replace('<script src="/js/theme.js"></script>',
                    f'<script>\n{thm}\n</script>')

# ── 3. Replace topbar with a minimal read-only header ─────────────
OLD_HEADER = re.search(
    r'<header class="topbar">.*?</header>', html, re.DOTALL
).group(0)

NEW_HEADER = '''\
<header class="topbar">
    <div class="topbar-logo">
      <svg class="logo-icon" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
        <rect width="48" height="48" rx="8" fill="#1B2A6B"/>
        <path d="M10 34 Q16 10 24 24 Q32 38 38 14" stroke="#FFC72C" stroke-width="3.5" fill="none" stroke-linecap="round"/>
        <circle cx="38" cy="14" r="2.5" fill="#FFC72C"/>
      </svg>
      <div class="logo-text-wrap">
        <span class="logo-brand">Travel Blue</span>
        <span class="logo-tagline">London · Since 1987</span>
      </div>
    </div>
    <nav class="topbar-nav"></nav>
    <div class="topbar-search" style="visibility:hidden;"></div>
    <div class="topbar-user">
      <button class="btn-theme" id="btn-theme" title="Toggle dark mode"><i data-lucide="moon"></i></button>
    </div>
  </header>'''

html = html.replace(OLD_HEADER, NEW_HEADER)

# ── 4. Remove Publicar button ─────────────────────────────────────
html = re.sub(
    r'<button[^>]*id="btn-publish"[^>]*>.*?</button>\s*',
    '', html, flags=re.DOTALL
)

# ── 5. Replace the entire INIT async block ────────────────────────
#    Find the async IIFE that starts with "(async () => {"
OLD_INIT = re.search(
    r'\(async \(\) => \{.*?^\s*\}\)\(\);',
    html, re.DOTALL | re.MULTILINE
).group(0)

NEW_INIT = '''\
(async () => {
    // ── Viewer mode: no authentication required ──
    if (typeof lucide !== 'undefined') lucide.createIcons();
    document.getElementById('btn-theme')?.addEventListener('click', () => ThemeToggle.toggle());

    const sb = supabase.createClient(window.SUPABASE_URL, window.SUPABASE_SERVICE_KEY,
      { auth: { persistSession: false, autoRefreshToken: false } });

    const PAGE = 1000, PARALLEL = 5;
    let allRaw = [], page = 0, fetchError = null;
    const loadingSub = document.querySelector('#state-loading .state-sub');
    outer: while (true) {
      const batch = await Promise.all(
        Array.from({length: PARALLEL}, (_, i) =>
          sb.from('project_data').select('row_data')
            .eq('project_slug', PROJECT_SLUG)
            .range((page+i)*PAGE, (page+i+1)*PAGE-1)
        )
      );
      for (const {data: chunk, error: err} of batch) {
        if (err) { fetchError = err; break outer; }
        if (chunk?.length) allRaw.push(...chunk);
        if (!chunk?.length || chunk.length < PAGE) break outer;
      }
      page += PARALLEL;
      if (loadingSub) loadingSub.textContent = `Fetching… ${allRaw.length.toLocaleString()} rows loaded`;
    }
    const raw = allRaw, error = fetchError;

    if (error || !raw?.length) {
      const errMsg = error ? `Error: ${error.message || JSON.stringify(error)}` : 'Fetch returned 0 rows.';
      document.getElementById('state-loading').innerHTML = `
        <div class="state-card">
          <div class="state-icon">📭</div>
          <div class="state-title">No data available</div>
          <div class="state-sub" style="color:#ef4444;font-size:11px;margin-top:8px;">${errMsg}</div>
        </div>`;
      return;
    }

    const rows = raw.map(r => r.row_data);
    resolveColumns(rows[0]);
    _all = C.company ? rows.filter(r => !norm(r[C.company]).includes('interco')) : rows;
    _filt = [..._all];
    document.getElementById('state-loading').style.display = 'none';
    document.getElementById('dash-wrap').style.display     = 'block';
    populateFilters();
    showTab('overview');
  })();'''

html = html.replace(OLD_INIT, NEW_INIT)

# ── 6. Write output ───────────────────────────────────────────────
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

size_kb = os.path.getsize(OUT) / 1024
print(f"✅  viewer.html written → {OUT}")
print(f"    Size: {size_kb:.1f} KB")
