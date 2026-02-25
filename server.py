"""
Travel Blue Dashboards — Local Development Server
Run this file to start the local server and open the site in your browser.

Usage:
  python server.py
  python server.py 8080   (custom port)
"""

import http.server
import socketserver
import webbrowser
import sys
import os

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

os.chdir(os.path.dirname(os.path.abspath(__file__)))

Handler = http.server.SimpleHTTPRequestHandler
Handler.extensions_map.update({
    '.html': 'text/html',
    '.css':  'text/css',
    '.js':   'application/javascript',
    '.json': 'application/json',
})

print(f"\n{'='*50}")
print(f"  Travel Blue Dashboards — Local Server")
print(f"  Running at: http://localhost:{PORT}")
print(f"  Press Ctrl+C to stop.")
print(f"{'='*50}\n")

webbrowser.open(f"http://localhost:{PORT}/index.html")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
