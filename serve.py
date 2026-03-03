#!/usr/bin/env python3
"""
serve.py -- Travel Blue Local Dev Server
==========================================
- Serves the static site locally (same Supabase as production)
- Injects a Publicar button (bottom-left) into every HTML page
- POST /api/publish  -> git add -A + commit + push -> triggers Netlify deploy

Usage:
    python serve.py
    -> http://localhost:5500
"""

import http.server
import socketserver
import json
import subprocess
from pathlib import Path
from urllib.parse import urlparse

PORT = 5500
BASE = Path(__file__).resolve().parent

# ── Pages that receive the Publicar button ────────────────────────────────────
# Only dashboard/project pages — home, login and admin are excluded.
DASHBOARD_PATHS = {
    '/project/index.html',
    '/avolta/index.html',
    '/backpacks-and-luggage/index.html',
    '/total-sales-bp-latam/index.html',
    '/backpack-lugagge/index.html',
}

# ── Dev tools injected before </body> ────────────────────────────────────────
DEV_TOOLS = r"""<script>
(function () {
  /* ===== BOTAO PUBLICAR ===================================================== */
  var pubBtn = document.createElement('button');
  pubBtn.textContent = '\uD83D\uDE80 Publicar';
  pubBtn.title = 'Commitar e publicar no Netlify';
  pubBtn.style.cssText = 'position:fixed;bottom:24px;left:24px;z-index:9999;padding:10px 18px;background:#27ae60;color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.25);';

  /* ===== OVERLAY + MODAL ==================================================== */
  var overlay = document.createElement('div');
  overlay.style.cssText = 'display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:10000;align-items:flex-start;justify-content:center;padding-top:5vh;overflow-y:auto;';

  var pubModal = document.createElement('div');
  pubModal.style.cssText = 'background:#fff;border-radius:12px;padding:28px 32px;max-width:460px;width:90%;box-shadow:0 8px 40px rgba(0,0,0,.3);margin-bottom:24px;';
  pubModal.innerHTML =
    '<h3 style="margin:0 0 6px;color:#1B2A6B;font-size:18px;">\uD83D\uDE80 Publicar altera\u00e7\u00f5es</h3>'
    + '<p style="margin:0 0 18px;color:#555;font-size:13px;line-height:1.5;">Faz commit das suas altera\u00e7\u00f5es locais e publica no Netlify (~1 min).</p>'
    + '<label style="display:block;font-size:12px;font-weight:700;color:#333;text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px;">Mensagem do commit *</label>'
    + '<input id="_pub_msg" type="text" placeholder="Ex: refine: ajusta gr\u00e1fico de vendas LATAM"'
    + ' style="width:100%;box-sizing:border-box;padding:9px 12px;border:1.5px solid #ddd;border-radius:7px;font-size:13px;outline:none;margin-bottom:16px;"/>'
    + '<div id="_pub_result" style="display:none;padding:10px 14px;border-radius:7px;font-size:13px;margin-bottom:14px;line-height:1.5;"></div>'
    + '<div style="display:flex;gap:10px;">'
    + '<button id="_pub_ok" style="flex:1;padding:10px;background:#27ae60;color:#fff;border:none;border-radius:7px;font-size:13.5px;font-weight:700;cursor:pointer;">Publicar agora</button>'
    + '<button id="_pub_cancel" style="padding:10px 18px;background:#f0f0f0;color:#333;border:none;border-radius:7px;font-size:13.5px;cursor:pointer;">Cancelar</button>'
    + '</div>';

  overlay.appendChild(pubModal);

  /* ===== HELPERS ============================================================ */
  function _show() {
    overlay.style.display = 'flex';
    document.getElementById('_pub_result').style.display = 'none';
    setTimeout(function () { document.getElementById('_pub_msg').focus(); }, 50);
  }

  function _close() { overlay.style.display = 'none'; }

  function _setResult(ok, html) {
    var el = document.getElementById('_pub_result');
    el.style.cssText = 'display:block;padding:10px 14px;border-radius:7px;font-size:13px;margin-bottom:14px;line-height:1.5;'
      + (ok ? 'background:#d4edda;color:#155724;' : 'background:#f8d7da;color:#721c24;');
    el.innerHTML = html;
  }

  /* ===== PUBLICAR LOGIC ===================================================== */
  async function _doPublish() {
    var msg = document.getElementById('_pub_msg').value.trim();
    if (!msg) { alert('Por favor, escreva uma mensagem para o commit.'); return; }
    var okBtn = document.getElementById('_pub_ok');
    document.getElementById('_pub_result').style.display = 'none';
    okBtn.textContent = 'Publicando\u2026'; okBtn.disabled = true;
    try {
      var r = await fetch('/api/publish', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:msg}) });
      var d = await r.json();
      if (d.ok) {
        _setResult(true, '\u2705 <strong>Publicado!</strong> Netlify vai atualizar em ~1 min.' + (d.output ? '<br><small>' + d.output + '</small>' : ''));
        document.getElementById('_pub_msg').value = '';
      } else {
        _setResult(false, '\u274C <strong>Erro:</strong> ' + (d.error || 'falha desconhecida'));
      }
    } catch(e) { _setResult(false, '\u274C Erro de rede: ' + e.message); }
    okBtn.textContent = 'Publicar agora'; okBtn.disabled = false;
  }

  /* ===== INIT =============================================================== */
  function init() {
    document.body.appendChild(overlay);
    document.body.appendChild(pubBtn);

    pubBtn.addEventListener('click', _show);
    document.getElementById('_pub_cancel').addEventListener('click', _close);
    document.getElementById('_pub_ok').addEventListener('click', _doPublish);
    document.getElementById('_pub_msg').addEventListener('keydown', function(e) { if(e.key==='Enter') _doPublish(); });
    overlay.addEventListener('click', function(e) { if(e.target===overlay) _close(); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
</script>
"""


class DevHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE), **kwargs)

    def do_POST(self):
        path   = self.path.split('?')[0]
        length = int(self.headers.get('Content-Length', 0))
        body   = json.loads(self.rfile.read(length)) if length else {}

        if path == '/api/publish':
            self._handle_publish(body)
        else:
            self.send_response(404); self.end_headers()

    # ── Publish: git add + commit + push ────────────────────────────────────
    def _handle_publish(self, body):
        msg = body.get('message', 'refine: update dashboard').strip()
        try:
            subprocess.run(['git', 'add', '-A'], cwd=BASE, check=True, capture_output=True)
            commit = subprocess.run(
                ['git', 'commit', '-m', msg],
                cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace'
            )
            nothing_new = 'nothing to commit' in (commit.stdout + commit.stderr)
            if commit.returncode != 0 and not nothing_new:
                raise Exception(commit.stderr.strip() or commit.stdout.strip())
            push = subprocess.run(
                ['git', 'push', 'origin', 'HEAD:main'],
                cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace'
            )
            if push.returncode != 0:
                raise Exception(push.stderr.strip() or push.stdout.strip())
            output = commit.stdout.split('\n')[0] if not nothing_new else 'Nenhuma mudanca nova para commitar'
            self._json(200, {'ok': True, 'output': output})
        except Exception as e:
            self._json(500, {'ok': False, 'error': str(e)})

    # ── Disable caching for all responses (dev server only) ──────────────────
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        super().end_headers()

    # ── GET: serve HTML with dev tools injected ──────────────────────────────
    def do_GET(self):
        parsed   = urlparse(self.path)
        rel_path = parsed.path.lstrip('/')
        filepath = BASE / rel_path

        if filepath.is_dir():
            filepath = filepath / 'index.html'

        req_path = parsed.path  # already normalised, no query string
        is_dashboard = req_path in DASHBOARD_PATHS

        if filepath.exists() and filepath.suffix == '.html':
            content = filepath.read_text(encoding='utf-8')
            if is_dashboard:
                content = content.replace('</body>', DEV_TOOLS + '</body>', 1)
            encoded = content.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        else:
            super().do_GET()

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        if args and (args[0].startswith('POST') or 'Error' in str(args)):
            print(f'[dev] {args[0]} -> {args[1] if len(args) > 1 else ""}')


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    print('\n  Travel Blue Dev Server')
    print(f'  http://localhost:{PORT}')
    print('  Botao Publicar ativo apenas em paginas de projeto')
    print('  Ctrl+C para parar\n')
    with socketserver.TCPServer(('', PORT), DevHandler) as httpd:
        httpd.allow_reuse_address = True
        httpd.serve_forever()
