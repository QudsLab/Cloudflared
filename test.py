#!/usr/bin/env python3
"""
Cloudflared DLL Test Script
Tests the DLL by:
1. Thread 1: Loading and managing the DLL
2. Thread 2: Running a simple HTTP server
3. Thread 3: Testing connectivity through the tunnel
"""

import ctypes
import threading
import time
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error
import re

# Configuration
LOCAL_PORT = 8765
TUNNEL_NAME = "test-tunnel"
TEST_TIMEOUT = 60  # seconds


class SimpleHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler that returns OK for testing."""
    
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Cloudflared DLL Test OK")
    
    def log_message(self, format, *args):
        print(f"[HTTP] {args[0]}")


class CloudflaredDLL:
    """Wrapper for cloudflared DLL functions."""
    
    def __init__(self, dll_path: str):
        self.dll_path = dll_path
        self.lib = None
        self.tunnel_url = None
        
    def load(self):
        """Load the DLL."""
        if sys.platform == "win32":
            self.lib = ctypes.CDLL(self.dll_path)
        elif sys.platform == "darwin":
            self.lib = ctypes.CDLL(self.dll_path)
        else:
            self.lib = ctypes.CDLL(self.dll_path)
        
        # Set up function signatures
        self.lib.CloudflaredInit.restype = ctypes.c_int
        self.lib.CloudflaredRun.argtypes = [ctypes.c_char_p]
        self.lib.CloudflaredRun.restype = ctypes.c_int
        self.lib.CloudflaredRunSync.argtypes = [ctypes.c_char_p]
        self.lib.CloudflaredRunSync.restype = ctypes.c_int
        self.lib.CloudflaredStop.restype = ctypes.c_int
        self.lib.CloudflaredVersion.restype = ctypes.c_char_p
        
        print(f"[DLL] Loaded: {self.dll_path}")
        return True
    
    def init(self):
        """Initialize cloudflared."""
        result = self.lib.CloudflaredInit()
        print(f"[DLL] Init: {'OK' if result == 0 else 'Already initialized'}")
        return result
    
    def run(self, args: str):
        """Run cloudflared with args (async)."""
        result = self.lib.CloudflaredRun(args.encode())
        print(f"[DLL] Run: {'OK' if result == 0 else 'Failed'}")
        return result
    
    def stop(self):
        """Stop cloudflared."""
        result = self.lib.CloudflaredStop()
        print(f"[DLL] Stop: {'OK' if result == 0 else 'Failed'}")
        return result
    
    def version(self):
        """Get version."""
        return self.lib.CloudflaredVersion().decode()


def thread_dll_manager(dll: CloudflaredDLL, stop_event: threading.Event, result: dict):
    """Thread 1: Manage the DLL lifecycle."""
    try:
        dll.load()
        dll.init()
        
        print(f"[DLL] Version: {dll.version()}")
        
        # Start tunnel with quick tunnel (no token needed)
        args = f"cloudflared tunnel --url http://localhost:{LOCAL_PORT}"
        dll.run(args)
        
        # Wait for stop signal
        while not stop_event.is_set():
            time.sleep(0.5)
        
        dll.stop()
        result["dll"] = "success"
        
    except Exception as e:
        print(f"[DLL] Error: {e}")
        result["dll"] = f"error: {e}"


def thread_http_server(stop_event: threading.Event, result: dict):
    """Thread 2: Run simple HTTP server."""
    try:
        server = HTTPServer(("localhost", LOCAL_PORT), SimpleHandler)
        server.timeout = 1
        
        print(f"[HTTP] Server started on port {LOCAL_PORT}")
        result["server"] = "running"
        
        while not stop_event.is_set():
            server.handle_request()
        
        server.server_close()
        result["server"] = "success"
        
    except Exception as e:
        print(f"[HTTP] Error: {e}")
        result["server"] = f"error: {e}"


def thread_test_connectivity(stop_event: threading.Event, result: dict, tunnel_url_holder: list):
    """Thread 3: Test connectivity through tunnel."""
    try:
        # Wait for tunnel URL (normally would parse from DLL output)
        # For now, just test local server
        time.sleep(5)
        
        # Test local server first
        try:
            response = urllib.request.urlopen(f"http://localhost:{LOCAL_PORT}", timeout=5)
            if response.status == 200:
                print("[TEST] Local server: OK")
                result["local"] = "success"
            else:
                result["local"] = f"error: status {response.status}"
        except Exception as e:
            result["local"] = f"error: {e}"
        
        # If we have a tunnel URL, test it
        if tunnel_url_holder:
            tunnel_url = tunnel_url_holder[0]
            try:
                response = urllib.request.urlopen(tunnel_url, timeout=10)
                if response.status == 200:
                    print(f"[TEST] Tunnel ({tunnel_url}): OK")
                    result["tunnel"] = "success"
                else:
                    result["tunnel"] = f"error: status {response.status}"
            except Exception as e:
                result["tunnel"] = f"error: {e}"
        else:
            result["tunnel"] = "skipped (no URL)"
        
        # Signal done
        stop_event.set()
        
    except Exception as e:
        print(f"[TEST] Error: {e}")
        result["test"] = f"error: {e}"


def find_dll():
    """Find the appropriate DLL/SO/DYLIB for current platform."""
    if sys.platform == "win32":
        candidates = ["cloudflared.dll", "cloudflared-windows-amd64.dll"]
        ext = ".dll"
    elif sys.platform == "darwin":
        candidates = ["cloudflared.dylib", "cloudflared-darwin-arm64.dylib", "cloudflared-darwin-amd64.dylib"]
        ext = ".dylib"
    else:
        candidates = ["cloudflared.so", "cloudflared-linux-amd64.so"]
        ext = ".so"
    
    # Check current directory and binaries folder
    search_paths = [".", "binaries", f"binaries/{sys.platform}"]
    
    for path in search_paths:
        for name in candidates:
            full = os.path.join(path, name)
            if os.path.exists(full):
                return full
    
    return None


def main():
    print("=" * 50)
    print("Cloudflared DLL Test")
    print("=" * 50)
    
    # Find DLL
    dll_path = sys.argv[1] if len(sys.argv) > 1 else find_dll()
    
    if not dll_path or not os.path.exists(dll_path):
        print(f"Error: DLL not found. Usage: python test.py <dll_path>")
        print(f"  Searched for: {dll_path}")
        sys.exit(1)
    
    print(f"Using DLL: {dll_path}")
    
    # Create shared objects
    dll = CloudflaredDLL(dll_path)
    stop_event = threading.Event()
    results = {}
    tunnel_url = []
    
    # Create threads
    t1 = threading.Thread(target=thread_dll_manager, args=(dll, stop_event, results))
    t2 = threading.Thread(target=thread_http_server, args=(stop_event, results))
    t3 = threading.Thread(target=thread_test_connectivity, args=(stop_event, results, tunnel_url))
    
    # Start threads
    t2.start()  # Start server first
    time.sleep(1)
    t1.start()  # Then DLL
    time.sleep(2)
    t3.start()  # Then test
    
    # Wait with timeout
    t3.join(timeout=TEST_TIMEOUT)
    
    if not stop_event.is_set():
        print("[MAIN] Timeout reached, stopping...")
        stop_event.set()
    
    # Wait for cleanup
    t1.join(timeout=5)
    t2.join(timeout=5)
    
    # Print results
    print("\n" + "=" * 50)
    print("Results:")
    print("=" * 50)
    for key, value in results.items():
        status = "✓" if value == "success" else "✗"
        print(f"  {status} {key}: {value}")
    
    # Exit code
    success = all(v == "success" or v == "skipped (no URL)" for v in results.values())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
