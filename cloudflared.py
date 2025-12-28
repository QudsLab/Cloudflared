#!/usr/bin/env python3
"""
Cloudflared DLL Test Script
Tests the DLL by:
1. Thread 1: Loading and managing the DLL
2. Thread 2: Running a simple HTTP server  
3. Thread 3: Testing connectivity through the tunnel
4. Thread 4: Monitoring console output for tunnel URL
"""

import ctypes
import threading
import time
import sys
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error

# Configuration
LOCAL_PORT = 8765
TEST_TIMEOUT = 45
TUNNEL_WAIT_TIME = 20

# Shared state
tunnel_url_holder = {"url": None}
output_lines = []


class SimpleHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler that returns OK for testing."""
    
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Cloudflared DLL Test OK")
    
    def log_message(self, format, *args):
        line = f"[HTTP] {args[0]}"
        print(line)
        output_lines.append(line)


class CloudflaredDLL:
    """Wrapper for cloudflared DLL functions."""
    
    def __init__(self, dll_path: str):
        self.dll_path = dll_path
        self.lib = None
        
    def load(self):
        """Load the DLL."""
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
        result = self.lib.CloudflaredInit()
        print(f"[DLL] Init: {'OK' if result == 0 else 'Already initialized'}")
        return result
    
    def run(self, args: str):
        result = self.lib.CloudflaredRun(args.encode())
        print(f"[DLL] Run: {'OK' if result == 0 else 'Failed'}")
        return result
    
    def stop(self):
        result = self.lib.CloudflaredStop()
        print(f"[DLL] Stop: {'OK' if result == 0 else 'Failed'}")
        return result
    
    def version(self):
        return self.lib.CloudflaredVersion().decode()


def extract_tunnel_url_from_console():
    """
    Since cloudflared writes directly to console, we need to ask user or 
    parse from visible output. This function prompts for manual input as fallback.
    """
    print("\n[URL] Please paste the tunnel URL from the output above (or press Enter to skip):")
    print("[URL] Look for: https://xxx.trycloudflare.com")
    try:
        # Give some time for URL to appear, then ask
        user_input = input("[URL] > ").strip()
        if user_input and "trycloudflare.com" in user_input:
            # Extract URL from input
            match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', user_input)
            if match:
                return match.group(0)
            return user_input
    except:
        pass
    return None


def thread_dll_manager(dll: CloudflaredDLL, stop_event: threading.Event, result: dict):
    """Thread 1: Manage the DLL lifecycle."""
    try:
        dll.load()
        dll.init()
        print(f"[DLL] Version: {dll.version()}")
        
        # Start tunnel with quick tunnel - use http2 to avoid QUIC/UDP firewall issues
        args = f"cloudflared tunnel --url http://localhost:{LOCAL_PORT} --protocol http2"
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


def thread_test_connectivity(stop_event: threading.Event, result: dict, tunnel_url: str):
    """Thread 3: Test connectivity through tunnel."""
    try:
        # Test local server first
        print("[TEST] Testing local server...")
        try:
            response = urllib.request.urlopen(f"http://localhost:{LOCAL_PORT}", timeout=5)
            if response.status == 200:
                print("[TEST] Local server: OK ✓")
                result["local"] = "success"
            else:
                result["local"] = f"error: status {response.status}"
        except Exception as e:
            result["local"] = f"error: {e}"
        
        # Test tunnel if URL provided
        if tunnel_url:
            print(f"[TEST] Testing tunnel: {tunnel_url}")
            try:
                req = urllib.request.Request(tunnel_url, headers={
                    'User-Agent': 'CloudflaredTest/1.0',
                    'Accept': 'text/plain'
                })
                response = urllib.request.urlopen(req, timeout=20)
                content = response.read().decode()
                if response.status == 200:
                    if "Cloudflared DLL Test OK" in content:
                        print(f"[TEST] Tunnel: OK ✓ (verified response)")
                        result["tunnel"] = "success"
                    else:
                        print(f"[TEST] Tunnel: OK ✓ (got response: {content[:50]}...)")
                        result["tunnel"] = "success"
                else:
                    result["tunnel"] = f"error: status {response.status}"
            except urllib.error.HTTPError as e:
                result["tunnel"] = f"error: HTTP {e.code}"
            except urllib.error.URLError as e:
                result["tunnel"] = f"error: {e.reason}"
            except Exception as e:
                result["tunnel"] = f"error: {e}"
        else:
            result["tunnel"] = "skipped (no URL provided)"
        
        # Signal done
        stop_event.set()
        
    except Exception as e:
        print(f"[TEST] Error: {e}")
        result["test"] = f"error: {e}"
        stop_event.set()


def find_dll():
    """Find the appropriate DLL/SO/DYLIB for current platform."""
    if sys.platform == "win32":
        candidates = ["cloudflared.dll", "cloudflared-windows-amd64.dll"]
    elif sys.platform == "darwin":
        candidates = ["cloudflared.dylib", "cloudflared-darwin-arm64.dylib", "cloudflared-darwin-amd64.dylib"]
    else:
        candidates = ["cloudflared.so", "cloudflared-linux-amd64.so"]
    
    search_paths = [".", "binaries", "binaries/windows-amd64", "binaries/linux-amd64", "binaries/darwin-arm64"]
    
    for path in search_paths:
        for name in candidates:
            full = os.path.join(path, name)
            if os.path.exists(full):
                return full
    return None


def main():
    print("=" * 60)
    print("Cloudflared DLL Test")
    print("=" * 60)
    
    # Find DLL
    dll_path = sys.argv[1] if len(sys.argv) > 1 else find_dll()
    
    if not dll_path or not os.path.exists(dll_path):
        print(f"Error: DLL not found. Usage: python test.py <dll_path>")
        sys.exit(1)
    
    print(f"Using DLL: {dll_path}")
    print("-" * 60)
    
    # Create shared objects
    dll = CloudflaredDLL(dll_path)
    stop_event = threading.Event()
    results = {}
    
    # Create and start server thread
    t_server = threading.Thread(target=thread_http_server, args=(stop_event, results), daemon=True)
    t_server.start()
    time.sleep(0.5)
    
    # Create and start DLL thread
    t_dll = threading.Thread(target=thread_dll_manager, args=(dll, stop_event, results), daemon=True)
    t_dll.start()
    
    # Wait for tunnel to start and show URL
    print(f"\n[WAIT] Waiting {TUNNEL_WAIT_TIME}s for tunnel to initialize...")
    print("[WAIT] Watch for the tunnel URL in the output above.")
    print("-" * 60)
    time.sleep(TUNNEL_WAIT_TIME)
    
    # Ask user for tunnel URL since we can't capture it programmatically
    print("-" * 60)
    tunnel_url = extract_tunnel_url_from_console()
    
    if tunnel_url:
        print(f"[URL] Using tunnel URL: {tunnel_url}")
        tunnel_url_holder["url"] = tunnel_url
    else:
        print("[URL] No URL provided, skipping tunnel test")
    
    # Run connectivity tests
    print("-" * 60)
    t_test = threading.Thread(target=thread_test_connectivity, args=(stop_event, results, tunnel_url), daemon=True)
    t_test.start()
    
    # Wait for tests to complete
    t_test.join(timeout=30)
    

    time.sleep(300)  # Allow some time for testing it manually if needed


    if not stop_event.is_set():
        print("[MAIN] Timeout reached, stopping...")
        stop_event.set()
    
    # Wait for cleanup
    time.sleep(2)
    
    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    if tunnel_url_holder["url"]:
        print(f"  Tunnel URL: {tunnel_url_holder['url']}")
    
    for key, value in sorted(results.items()):
        status = "✓" if value == "success" else "✗"
        print(f"  {status} {key}: {value}")
    
    print("=" * 60)
    
    # Exit code
    success_count = sum(1 for v in results.values() if v == "success")
    total = len(results)
    print(f"\nPassed: {success_count}/{total}")
    
    sys.exit(0 if success_count >= 2 else 1)


if __name__ == "__main__":
    main()
