#!/usr/bin/env python3
"""
serve.py -- Travel Blue Local Dev Server
==========================================
- Serves the static site (espelho do Netlify, mesmo Supabase)
- Injeta botao Publicar (verde, canto inf. esq.) em todas as paginas HTML
- Injeta botao Sincronizar (azul, ao lado do Publicar) que:
    * busca o que mudou no GitHub antes de qualquer acao
    * mostra commits e arquivos que seriam alterados
    * se local tiver mudancas nao commitadas, avisa com destaque
    * exige que usuario leia e confirme antes de sincronizar
- POST /api/publish  -> git add + commit + push -> deploy Netlify
- POST /api/sync     -> git fetch + relatorio de diferenca
- POST /api/pull     -> git pull (so chamado apos confirmacao explicita)

Uso:
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

# ── Dev tools injetado antes de </body> ──────────────────────────────────────
DEV_TOOLS = r"""<script>
(function () {
  /* ===== BOTAO PUBLICAR ===================================================== */
  var pubBtn = document.createElement('button');
  pubBtn.textContent = '\uD83D\uDE80 Publicar';
  pubBtn.title = 'Commitar e publicar no Netlify';
  pubBtn.style.cssText = 'position:fixed;bottom:24px;left:24px;z-index:9999;padding:10px 18px;background:#27ae60;color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.25);';

  /* ===== BOTAO SINCRONIZAR ================================================== */
  var syncBtn = document.createElement('button');
  syncBtn.textContent = '\uD83D\uDD04 Sincronizar';
  syncBtn.title = 'Verificar e baixar atualizacoes do GitHub';
  syncBtn.style.cssText = 'position:fixed;bottom:24px;left:152px;z-index:9999;padding:10px 18px;background:#1B2A6B;color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.25);';

  /* ===== OVERLAY COMPARTILHADO ============================================== */
  var overlay = document.createElement('div');
  overlay.style.cssText = 'display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:10000;align-items:flex-start;justify-content:center;padding-top:5vh;overflow-y:auto;';

  /* ===== MODAL PUBLICAR ===================================================== */
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

  /* ===== MODAL SINCRONIZAR ================================================== */
  var syncModal = document.createElement('div');
  syncModal.style.cssText = 'background:#fff;border-radius:12px;padding:28px 32px;max-width:560px;width:90%;box-shadow:0 8px 40px rgba(0,0,0,.3);margin-bottom:24px;display:none;';
  syncModal.innerHTML =
    '<h3 style="margin:0 0 6px;color:#1B2A6B;font-size:18px;">\uD83D\uDD04 Sincronizar com vers\u00e3o online</h3>'
    + '<p style="margin:0 0 16px;color:#555;font-size:13px;line-height:1.5;">Verificando o GitHub... aguarde.</p>'
    + '<div id="_sync_body"></div>'
    + '<div id="_sync_confirm_area" style="display:none;margin-top:16px;">'
    + '<label style="display:flex;align-items:flex-start;gap:10px;cursor:pointer;padding:14px;border:2px solid #e74c3c;border-radius:8px;background:#fff5f5;">'
    + '<input type="checkbox" id="_sync_checkbox" style="margin-top:3px;width:16px;height:16px;flex-shrink:0;cursor:pointer;" />'
    + '<span style="font-size:13px;color:#333;line-height:1.5;">Li e entendi as altera\u00e7\u00f5es acima. <strong>Quero sincronizar e sobrescrever minha vers\u00e3o local</strong> com a vers\u00e3o online.</span>'
    + '</label>'
    + '</div>'
    + '<div id="_sync_result" style="display:none;padding:10px 14px;border-radius:7px;font-size:13px;margin-top:14px;line-height:1.5;"></div>'
    + '<div style="display:flex;gap:10px;margin-top:16px;">'
    + '<button id="_sync_ok" style="flex:1;padding:10px;background:#1B2A6B;color:#fff;border:none;border-radius:7px;font-size:13.5px;font-weight:700;cursor:pointer;display:none;">Sincronizar agora</button>'
    + '<button id="_sync_cancel" style="padding:10px 18px;background:#f0f0f0;color:#333;border:none;border-radius:7px;font-size:13.5px;cursor:pointer;">Fechar</button>'
    + '</div>';

  overlay.appendChild(pubModal);
  overlay.appendChild(syncModal);

  /* ===== HELPERS ============================================================ */
  function _showPub() {
    pubModal.style.display = 'block';
    syncModal.style.display = 'none';
    overlay.style.display = 'flex';
    document.getElementById('_pub_result').style.display = 'none';
    setTimeout(function () { document.getElementById('_pub_msg').focus(); }, 50);
  }

  function _showSync() {
    pubModal.style.display = 'none';
    syncModal.style.display = 'block';
    overlay.style.display = 'flex';
    _runSyncCheck();
  }

  function _closeOverlay() {
    overlay.style.display = 'none';
    pubModal.style.display = 'block';
    syncModal.style.display = 'none';
  }

  function _setResult(id, ok, html) {
    var el = document.getElementById(id);
    el.style.display = 'block';
    el.style.cssText = 'display:block;padding:10px 14px;border-radius:7px;font-size:13px;margin-top:14px;line-height:1.5;'
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
        _setResult('_pub_result', true, '\u2705 <strong>Publicado!</strong> Netlify vai atualizar em ~1 min.' + (d.output ? '<br><small>' + d.output + '</small>' : ''));
        document.getElementById('_pub_msg').value = '';
      } else {
        _setResult('_pub_result', false, '\u274C <strong>Erro:</strong> ' + (d.error || 'falha desconhecida'));
      }
    } catch(e) { _setResult('_pub_result', false, '\u274C Erro de rede: ' + e.message); }
    okBtn.textContent = 'Publicar agora'; okBtn.disabled = false;
  }

  /* ===== SINCRONIZAR LOGIC ================================================== */
  async function _runSyncCheck() {
    var body = document.getElementById('_sync_body');
    var confirmArea = document.getElementById('_sync_confirm_area');
    var okBtn = document.getElementById('_sync_ok');
    var result = document.getElementById('_sync_result');
    var checkbox = document.getElementById('_sync_checkbox');

    body.innerHTML = '<p style="color:#555;font-size:13px;">Verificando GitHub\u2026 <span style="opacity:.6">(pode levar alguns segundos)</span></p>';
    confirmArea.style.display = 'none';
    okBtn.style.display = 'none';
    result.style.display = 'none';
    if (checkbox) checkbox.checked = false;

    try {
      var r = await fetch('/api/sync', { method:'POST', headers:{'Content-Type':'application/json'}, body:'{}' });
      var d = await r.json();

      if (!d.ok) {
        body.innerHTML = '<p style="color:#c0392b;font-size:13px;">\u274C Erro ao verificar: ' + (d.error || '?') + '</p>';
        return;
      }

      var html = '';

      // Local uncommitted changes warning
      if (d.local_changes && d.local_changes.length) {
        html += '<div style="border:2px solid #e74c3c;border-radius:8px;padding:14px;margin-bottom:14px;background:#fff5f5;">'
          + '<strong style="color:#c0392b;font-size:13px;">\u26A0\uFE0F Voc\u00ea tem altera\u00e7\u00f5es locais n\u00e3o commitadas:</strong>'
          + '<ul style="margin:8px 0 0 0;padding-left:18px;font-size:12.5px;color:#333;line-height:1.8;">'
          + d.local_changes.map(function(f) { return '<li><code style="background:#f0f0f0;padding:1px 5px;border-radius:3px;">' + f + '</code></li>'; }).join('')
          + '</ul>'
          + '<p style="margin:10px 0 0;font-size:12.5px;color:#c0392b;"><strong>Aten\u00e7\u00e3o:</strong> Se sincronizar sem publicar primeiro, essas altera\u00e7\u00f5es podem ser perdidas ou entrar em conflito.</p>'
          + '</div>';
      }

      if (d.up_to_date) {
        html += '<div style="padding:16px;background:#d4edda;border-radius:8px;color:#155724;font-size:13px;text-align:center;">'
          + '\u2705 <strong>Tudo sincronizado!</strong> Sua vers\u00e3o local j\u00e1 est\u00e1 igual ao online.'
          + '</div>';
        body.innerHTML = html;
        return;
      }

      // Commits coming from online
      if (d.commits && d.commits.length) {
        html += '<div style="margin-bottom:14px;">'
          + '<strong style="font-size:13px;color:#1B2A6B;">\uD83D\uDCCB ' + d.commits.length + ' commit(s) novos no GitHub:</strong>'
          + '<ul style="margin:8px 0 0 0;padding-left:18px;font-size:12.5px;color:#333;line-height:1.9;">'
          + d.commits.map(function(c) { return '<li>' + c + '</li>'; }).join('')
          + '</ul></div>';
      }

      // Files that will change
      if (d.changed_files && d.changed_files.length) {
        html += '<div style="margin-bottom:14px;">'
          + '<strong style="font-size:13px;color:#1B2A6B;">\uD83D\uDCC2 Arquivos que ser\u00e3o alterados/criados no seu computador:</strong>'
          + '<ul style="margin:8px 0 0 0;padding-left:18px;font-size:12px;color:#333;line-height:1.9;font-family:monospace;">'
          + d.changed_files.map(function(f) {
              var color = f.startsWith('A') ? '#27ae60' : f.startsWith('D') ? '#e74c3c' : '#e67e22';
              var label = f.startsWith('A') ? 'NOVO' : f.startsWith('D') ? 'REMOVIDO' : 'ALTERADO';
              var name  = f.slice(2);
              return '<li><span style="color:' + color + ';font-weight:700;min-width:70px;display:inline-block;">[' + label + ']</span> ' + name + '</li>';
            }).join('')
          + '</ul></div>';

        // Warn about potential overwrite
        html += '<div style="padding:12px 14px;background:#fff3cd;border:1px solid #ffc107;border-radius:8px;font-size:12.5px;color:#856404;margin-bottom:4px;">'
          + '\u26A0\uFE0F <strong>Importante:</strong> Os arquivos listados acima ser\u00e3o substituidos pela vers\u00e3o do GitHub. Qualquer altera\u00e7\u00e3o local nesses arquivos que n\u00e3o tenha sido publicada ser\u00e1 perdida.'
          + '</div>';
      }

      body.innerHTML = html;
      confirmArea.style.display = 'block';
      okBtn.style.display = 'block';

    } catch(e) {
      body.innerHTML = '<p style="color:#c0392b;font-size:13px;">\u274C Erro de rede: ' + e.message + '</p>';
    }
  }

  async function _doPull() {
    var checkbox = document.getElementById('_sync_checkbox');
    if (!checkbox || !checkbox.checked) {
      alert('\u26A0\uFE0F Por favor, leia as altera\u00e7\u00f5es acima e marque a caixa de confirma\u00e7\u00e3o antes de sincronizar.');
      return;
    }
    var okBtn = document.getElementById('_sync_ok');
    okBtn.textContent = 'Sincronizando\u2026'; okBtn.disabled = true;
    try {
      var r = await fetch('/api/pull', { method:'POST', headers:{'Content-Type':'application/json'}, body:'{}' });
      var d = await r.json();
      if (d.ok) {
        _setResult('_sync_result', true, '\u2705 <strong>Sincronizado!</strong> Sua vers\u00e3o local agora est\u00e1 igual ao GitHub. Recarregue a p\u00e1gina para ver as mudan\u00e7as.<br><small>' + (d.output || '') + '</small>');
        document.getElementById('_sync_confirm_area').style.display = 'none';
        okBtn.style.display = 'none';
      } else {
        _setResult('_sync_result', false, '\u274C <strong>Erro ao sincronizar:</strong> ' + (d.error || '?'));
      }
    } catch(e) { _setResult('_sync_result', false, '\u274C Erro de rede: ' + e.message); }
    okBtn.textContent = 'Sincronizar agora'; okBtn.disabled = false;
  }

  /* ===== INIT =============================================================== */
  function init() {
    document.body.appendChild(overlay);
    document.body.appendChild(pubBtn);
    document.body.appendChild(syncBtn);

    pubBtn.addEventListener('click', _showPub);
    syncBtn.addEventListener('click', _showSync);

    document.getElementById('_pub_cancel').addEventListener('click', _closeOverlay);
    document.getElementById('_pub_ok').addEventListener('click', _doPublish);
    document.getElementById('_pub_msg').addEventListener('keydown', function(e) { if(e.key==='Enter') _doPublish(); });

    document.getElementById('_sync_cancel').addEventListener('click', _closeOverlay);
    document.getElementById('_sync_ok').addEventListener('click', _doPull);

    overlay.addEventListener('click', function(e) { if(e.target===overlay) _closeOverlay(); });
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
        elif path == '/api/sync':
            self._handle_sync()
        elif path == '/api/pull':
            self._handle_pull()
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

    # ── Sync check: fetch + diff report ─────────────────────────────────────
    def _handle_sync(self):
        try:
            # Fetch latest from origin
            subprocess.run(
                ['git', 'fetch', 'origin', 'main'],
                cwd=BASE, check=True, capture_output=True, encoding='utf-8', errors='replace'
            )

            # Check uncommitted local changes
            status = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace'
            )
            local_changes = [l[3:] for l in status.stdout.splitlines() if l.strip() and not l.startswith('??')]

            # Commits on origin/main not in HEAD
            commits_out = subprocess.run(
                ['git', 'log', 'HEAD..origin/main', '--oneline', '--no-decorate'],
                cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace'
            )
            commits = [l.strip() for l in commits_out.stdout.splitlines() if l.strip()]

            # Files that would change
            diff_out = subprocess.run(
                ['git', 'diff', '--name-status', 'HEAD', 'origin/main'],
                cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace'
            )
            changed_files = [l.strip() for l in diff_out.stdout.splitlines() if l.strip()]

            up_to_date = len(commits) == 0 and len(changed_files) == 0

            self._json(200, {
                'ok': True,
                'up_to_date': up_to_date,
                'local_changes': local_changes,
                'commits': commits,
                'changed_files': changed_files,
            })
        except Exception as e:
            self._json(500, {'ok': False, 'error': str(e)})

    # ── Pull: git pull origin main ───────────────────────────────────────────
    def _handle_pull(self):
        try:
            pull = subprocess.run(
                ['git', 'pull', 'origin', 'main', '--ff-only'],
                cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace'
            )
            if pull.returncode != 0:
                # Try regular merge if fast-forward fails
                pull = subprocess.run(
                    ['git', 'pull', 'origin', 'main'],
                    cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace'
                )
            if pull.returncode != 0:
                raise Exception(pull.stderr.strip() or pull.stdout.strip())
            self._json(200, {'ok': True, 'output': pull.stdout.strip().split('\n')[0]})
        except Exception as e:
            self._json(500, {'ok': False, 'error': str(e)})

    # ── GET: serve HTML with dev tools injected ──────────────────────────────
    def do_GET(self):
        parsed   = urlparse(self.path)
        rel_path = parsed.path.lstrip('/')
        filepath = BASE / rel_path

        if filepath.is_dir():
            filepath = filepath / 'index.html'

        if filepath.exists() and filepath.suffix == '.html':
            content = filepath.read_text(encoding='utf-8')
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
    print('  Botoes Publicar + Sincronizar injetados em todas as paginas')
    print('  Ctrl+C para parar\n')
    with socketserver.TCPServer(('', PORT), DevHandler) as httpd:
        httpd.allow_reuse_address = True
        httpd.serve_forever()
