import os, sys, urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

port = int(sys.argv[1])
root = sys.argv[2]
os.chdir(root)

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=root, **kw)
    def do_GET(self):
        if self.path in ('/', ''):
            files = sorted(os.listdir(root))
            # Prefer real index.html
            for f in files:
                if f == 'index.html':
                    self.path = '/index.html'
                    return super().do_GET()
            # Any *index.html
            for f in files:
                if f.lower().endswith('.html') and 'index' in f.lower():
                    self.path = '/' + urllib.parse.quote(f)
                    return super().do_GET()
            # Any .html at all
            for f in files:
                if f.lower().endswith('.html'):
                    self.path = '/' + urllib.parse.quote(f)
                    return super().do_GET()
        return super().do_GET()
    def log_message(self, *a, **kw):
        pass

ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()