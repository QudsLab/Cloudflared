#!/usr/bin/env python3
"""
Cloudflared Tunnel Manager using DLL.
No OOP - just functions.
Saves tunnel URL to .cf file.
"""

import ctypes
import sys
import os
import time
import threading
import re
import subprocess

# Config
CF_FILE = ".cf"
PORT = 8765
DLL_PATH = None
lib = None
tunnel_running = False
tunnel_url = None
warp_was_connected = False


def check_warp_status():
    """Check if WARP VPN is connected."""
    try:
        result = subprocess.run(
            ["warp-cli", "status"],
            capture_output=True,
            text=True,
            timeout=5
        )
        output = result.stdout.lower()
        return "connected" in output and "disconnected" not in output
    except:
        return False


def disable_warp():
    """Disable WARP VPN if connected."""
    global warp_was_connected
    
    if check_warp_status():
        print("[WARP] Detected WARP VPN is ON - disabling...")
        warp_was_connected = True
        try:
            subprocess.run(["warp-cli", "disconnect"], timeout=10)
            time.sleep(2)
            print("[WARP] Disconnected")
            return True
        except Exception as e:
            print(f"[WARP] Failed to disconnect: {e}")
            return False
    return True


def restore_warp():
    """Restore WARP VPN if it was connected before."""
    global warp_was_connected
    
    if warp_was_connected:
        print("[WARP] Restoring WARP VPN...")
        try:
            subprocess.run(["warp-cli", "connect"], timeout=10)
            print("[WARP] Reconnected")
            warp_was_connected = False
        except Exception as e:
            print(f"[WARP] Failed to reconnect: {e}")


def find_dll():
    """Find DLL for current platform."""
    if sys.platform == "win32":
        candidates = [
            "cloudflared.dll",
            "binaries/windows-amd64/cloudflared-windows-amd64.dll",
        ]
    elif sys.platform == "darwin":
        candidates = [
            "cloudflared.dylib",
            "binaries/darwin-arm64/cloudflared-darwin-arm64.dylib",
            "binaries/darwin-amd64/cloudflared-darwin-amd64.dylib",
        ]
    else:
        candidates = [
            "cloudflared.so",
            "binaries/linux-amd64/cloudflared-linux-amd64.so",
        ]
    
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def load_dll(dll_path=None):
    """Load cloudflared DLL."""
    global lib, DLL_PATH
    
    DLL_PATH = dll_path or find_dll()
    if not DLL_PATH or not os.path.exists(DLL_PATH):
        print(f"[TUNNEL] ERROR: DLL not found")
        return False
    
    lib = ctypes.CDLL(DLL_PATH)
    
    # Setup function signatures
    lib.CloudflaredInit.restype = ctypes.c_int
    lib.CloudflaredRun.argtypes = [ctypes.c_char_p]
    lib.CloudflaredRun.restype = ctypes.c_int
    lib.CloudflaredStop.restype = ctypes.c_int
    lib.CloudflaredVersion.restype = ctypes.c_char_p
    
    print(f"[TUNNEL] DLL loaded: {DLL_PATH}")
    return True


def save_url(url):
    """Save tunnel URL to .cf file."""
    global tunnel_url
    tunnel_url = url
    with open(CF_FILE, "w") as f:
        f.write(url)
    print(f"[TUNNEL] URL saved to {CF_FILE}: {url}")


def get_url():
    """Get saved tunnel URL from .cf file."""
    if os.path.exists(CF_FILE):
        with open(CF_FILE, "r") as f:
            return f.read().strip()
    return None


def init_tunnel():
    """Initialize cloudflared."""
    if not lib:
        print("[TUNNEL] ERROR: DLL not loaded")
        return False
    
    result = lib.CloudflaredInit()
    if result == 0:
        print("[TUNNEL] Initialized")
        return True
    else:
        print("[TUNNEL] Already initialized")
        return True


def start_tunnel(port=8765, wait_for_url=True, timeout=60):
    """Start cloudflared tunnel."""
    global tunnel_running
    
    if not lib:
        print("[TUNNEL] ERROR: DLL not loaded")
        return False
    
    # Disable WARP if running (conflicts with cloudflared)
    disable_warp()
    
    # Use HTTP/2 to avoid QUIC/firewall issues
    args = f"cloudflared tunnel --url http://localhost:{port} --protocol http2"
    
    print(f"[TUNNEL] Starting tunnel to localhost:{port}...")
    print(f"[TUNNEL] Command: {args}")
    
    result = lib.CloudflaredRun(args.encode())
    if result != 0:
        print("[TUNNEL] ERROR: Failed to start")
        return False
    
    tunnel_running = True
    print("[TUNNEL] Started (waiting for URL...)")
    
    # Wait for URL to appear
    if wait_for_url:
        print(f"[TUNNEL] Waiting up to {timeout}s for tunnel URL...")
        print("[TUNNEL] Watch the output for: https://xxx.trycloudflare.com")
        
        # Give time for tunnel to establish
        for i in range(timeout):
            time.sleep(1)
            if i > 0 and i % 10 == 0:
                print(f"[TUNNEL] Still waiting... ({i}s)")
    
    return True


def stop_tunnel():
    """Stop cloudflared tunnel."""
    global tunnel_running
    
    if not lib:
        restore_warp()
        return
    
    print("[TUNNEL] Stopping...")
    try:
        lib.CloudflaredStop()
    except:
        pass
    tunnel_running = False
    print("[TUNNEL] Stopped")
    
    # Restore WARP if it was connected before
    restore_warp()


def get_version():
    """Get cloudflared version."""
    if not lib:
        return "N/A"
    return lib.CloudflaredVersion().decode()


def run_tunnel_thread(port=8765):
    """Run tunnel in background thread."""
    def _run():
        if load_dll():
            init_tunnel()
            start_tunnel(port=port, wait_for_url=True, timeout=60)
    
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    dll_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not load_dll(dll_path):
        print("Failed to load DLL")
        sys.exit(1)
    
    init_tunnel()
    print(f"Version: {get_version()}")
    
    try:
        start_tunnel(wait_for_url=True)
        print("\nTunnel is running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_tunnel()
