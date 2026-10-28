import json, sys, threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

config_path = sys.argv[1]
with open(config_path, "r", encoding="utf-8-sig") as f:
    apps = json.load(f)

servers = []
try:
    for app in apps:
        handler = partial(
            SimpleHTTPRequestHandler,
            directory=app["Directory"]
        )
        server = ThreadingHTTPServer(("127.0.0.1", int(app["Port"])), handler)
        servers.append(server)
        print(f'LISTENING {app["App"]} 127.0.0.1:{app["Port"]}', flush=True)

    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()

    threading.Event().wait()
except Exception as exc:
    print(f"SERVER_START_FAILURE: {exc}", file=sys.stderr, flush=True)
    for server in servers:
        server.server_close()
    sys.exit(1)