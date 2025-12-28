#!/usr/bin/env python3
"""
Simple HTTP Server for testing cloudflared tunnel.
No OOP - just functions.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Config
PORT = 8765
server_running = False
server_instance = None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Cloudflared DLL Test OK")
    
    def log_message(self, format, *args):
        print(f"[SERVER] {args[0]}")


def start_server():
    """Start HTTP server in current thread (blocking)."""
    global server_running, server_instance
    
    server_instance = HTTPServer(("localhost", PORT), Handler)
    server_instance.timeout = 1
    server_running = True
    
    print(f"[SERVER] Started on http://localhost:{PORT}")
    
    while server_running:
        server_instance.handle_request()
    
    print("[SERVER] Stopped")


def stop_server():
    """Stop the server."""
    global server_running
    server_running = False
    if server_instance:
        server_instance.server_close()


def run_server_thread():
    """Start server in a background thread."""
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    print("Starting server...")
    start_server()
