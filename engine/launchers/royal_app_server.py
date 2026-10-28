import os,sys
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
port=int(sys.argv[1]); d=sys.argv[2]
h=partial(SimpleHTTPRequestHandler,directory=d)
s=ThreadingHTTPServer(("127.0.0.1",port),h)
print(f"READY port={port} dir={d}",flush=True)
s.serve_forever()
