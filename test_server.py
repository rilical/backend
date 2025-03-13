"""
Simple test server to check connectivity
"""
import http.server
import socketserver

PORT = 8002
Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving at port {PORT}")
    httpd.serve_forever() 