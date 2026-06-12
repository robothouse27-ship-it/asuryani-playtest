import http.server, socketserver, functools, os
ROOT = "/Users/Benjamin/Desktop/Projects/Eldar Playtest APP"
os.chdir(ROOT)
Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
with socketserver.TCPServer(("127.0.0.1", 8731), Handler) as httpd:
    httpd.serve_forever()
