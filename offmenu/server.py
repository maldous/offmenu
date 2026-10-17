"""Local web UI and JSON API. Bind to loopback by default."""
import argparse
import json
import sqlite3
import ssl
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from .core import connect, map_product, add_inventory, meals

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, content_type='application/json'):
        payload = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        route = urlparse(self.path)
        if route.path == '/':
            return self.reply(200, Path(__file__).with_name('web.html').read_text(), 'text/html; charset=utf-8')
        db = connect(self.server.database)
        try:
            if route.path == '/api/product':
                code = parse_qs(route.query).get('barcode', [''])[0]
                row = db.execute('SELECT p.*,m.ingredient FROM products p LEFT JOIN mappings m USING(barcode) WHERE barcode=?', (code,)).fetchone()
                self.reply(200 if row else 404, dict(row) if row else {'error': 'Product not imported. Enter a name and ingredient to save it locally.'})
            elif route.path == '/api/inventory':
                self.reply(200, [dict(r) for r in db.execute('SELECT i.*,p.name,m.ingredient FROM inventory i JOIN products p USING(barcode) LEFT JOIN mappings m USING(barcode) ORDER BY i.id DESC')])
            elif route.path == '/api/meals':
                servings = parse_qs(route.query).get('servings', [None])[0]
                self.reply(200, meals(db, servings))
            elif route.path == '/api/shops':
                code = parse_qs(route.query).get('barcode', [''])[0]
                self.reply(200, {'evidence': 'Historical observations, not current stock', 'observations': [dict(r) for r in db.execute('SELECT * FROM observations WHERE barcode=? ORDER BY observed_at DESC', (code,))]})
            else:
                self.reply(404, {'error': 'Not found'})
        except ValueError as e:
            self.reply(400, {'error': str(e)})
        finally:
            db.close()

    def do_POST(self):
        # JSON plus a custom header blocks cross-origin form submissions; no CORS granted.
        origin = self.headers.get('Origin')
        expected = ('https' if self.server.secure else 'http') + '://' + self.headers.get('Host', '')
        if self.headers.get('X-Offmenu') != '1' or self.headers.get('Content-Type', '').split(';')[0] != 'application/json' or (origin and origin != expected):
            return self.reply(403, {'error': 'Same-origin JSON requests required'})
        db = connect(self.server.database)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536:
                raise ValueError('Invalid request size')
            data = json.loads(self.rfile.read(length))
            if self.path == '/api/inventory':
                barcode = data['barcode']
                if not isinstance(barcode, str) or not barcode.isdigit() or len(barcode) > 32:
                    raise ValueError('Barcode must be a string of digits')
                name = str(data['name']).strip()
                if not name:
                    raise ValueError('Product name required')
                expires = data.get('expires') or None
                if expires:
                    expires = date.fromisoformat(expires).isoformat()
                # All writes share one transaction, including ingredient mapping.
                with db:
                    db.execute('INSERT INTO products(barcode,name) VALUES(?,?) ON CONFLICT(barcode) DO NOTHING', (barcode, name))
                    ingredient = str(data['ingredient']).strip()
                    if not ingredient:
                        raise ValueError('Ingredient required')
                    from .core import normalize, amount
                    db.execute('INSERT INTO mappings VALUES(?,?) ON CONFLICT(barcode) DO UPDATE SET ingredient=excluded.ingredient', (barcode, normalize(ingredient)))
                    db.execute('INSERT INTO inventory(barcode,quantity,unit,expires) VALUES(?,?,?,?)', (barcode, amount(data['quantity']), data['unit'], expires))
                self.reply(201, {'saved': barcode})
            elif self.path == '/api/remove':
                with db:
                    db.execute('DELETE FROM inventory WHERE id=?', (int(data['id']),))
                self.reply(200, {'removed': data['id']})
            else:
                self.reply(404, {'error': 'Not found'})
        except (ValueError, KeyError, TypeError, sqlite3.IntegrityError) as e:
            self.reply(400, {'error': str(e)})
        finally:
            db.close()


def main():
    p = argparse.ArgumentParser(description='Serve offmenu on your computer for phone access')
    p.add_argument('--db', default='data/offmenu.sqlite')
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8765)
    p.add_argument('--cert'); p.add_argument('--key')
    a = p.parse_args()
    if bool(a.cert) != bool(a.key):
        p.error('--cert and --key must be supplied together')
    db = connect(a.db); db.close()
    server = ThreadingHTTPServer((a.host, a.port), Handler)
    server.database = a.db
    server.secure = bool(a.cert)
    if a.cert:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(a.cert, a.key)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
    print(f'offmenu: {"https" if a.cert else "http"}://{a.host}:{a.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
