#!/usr/bin/env python3
"""
Cloudflared Tunnel Manager using subprocess for output control.
Runs cloudflared.exe directly instead of DLL to capture output properly.
"""
import sys
import os
import time
import threading
import re
import subprocess
import signal
# Config
CF_FILE = ".cf"
PORT = 5000
tunnel_process = None
tunnel_running = False
tunnel_url = None

def save_url(url, file_name=CF_FILE):
    """Save tunnel URL to .cf file."""
    global tunnel_url
    tunnel_url = url
    with open(file_name, "w") as f:
        f.write(url)

def get_url(file_name=CF_FILE):
    """Get saved tunnel URL from .cf file."""
    if os.path.exists(file_name):
        with open(file_name, "r") as f:
            return f.read().strip()
    return None

def extract_url_from_line(line):
    """Extract tunnel URL from a log line."""
    pattern = r'https://[a-z0-9\-]+\.trycloudflare\.com'
    match = re.search(pattern, line)
    return match.group(0) if match else None

def start_tunnel(port=5000, cloudflared_path=None, timeout=30, file_name=CF_FILE):
    """Start cloudflared tunnel and capture output silently."""
    global tunnel_process, tunnel_running, tunnel_url
    # Find cloudflared executable
    if not cloudflared_path:
        print("[TUNNEL] ERROR: cloudflared.exe not found")
        print("[TUNNEL] Please specify path or add to PATH")
        return False
    print(f"[TUNNEL] Using: {cloudflared_path}")
    # Build command
    cmd = [
        cloudflared_path,
        "tunnel",
        "--url", f"http://localhost:{port}",
        "--protocol", "http2"
    ]
    print(f"[TUNNEL] Starting tunnel to localhost:{port}...")
    print(f"[TUNNEL] Capturing output (silent mode)...")
    try:
        # Start process with output capture
        tunnel_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        tunnel_running = True
        # Monitor output in background thread
        url_found = threading.Event()
        def monitor_output():
            """Monitor stderr for tunnel URL."""
            nonlocal url_found
            try:
                for line in tunnel_process.stderr:
                    # Check for URL
                    url = extract_url_from_line(line)
                    if url:
                        tunnel_url = url
                        save_url(url, file_name=file_name)
                        print(f"[TUNNEL] ✓ Tunnel URL: {url}")
                        print(f"[TUNNEL] Saved to {file_name}")
                        url_found.set()
                        # Continue consuming output silently
                        break
                # Keep consuming output silently after URL found
                for line in tunnel_process.stderr:
                    pass  # Silently discard
            except Exception as e:
                pass
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_output, daemon=True)
        monitor_thread.start()
        # Wait for URL with timeout
        print(f"[TUNNEL] Waiting up to {timeout}s for URL...")
        if url_found.wait(timeout=timeout):
            print("[TUNNEL] ✓ Tunnel started successfully")
            print("[TUNNEL] Output is now suppressed")
            return True
        else:
            print("[TUNNEL] ⚠ URL extraction timed out")
            print("[TUNNEL] Tunnel may still be running")
            return False
    except Exception as e:
        print(f"[TUNNEL] ERROR: Failed to start tunnel: {e}")
        return False

def stop_tunnel():
    """Stop cloudflared tunnel."""
    global tunnel_process, tunnel_running
    print("[TUNNEL] Stopping...")
    try:
        # Try graceful shutdown first
        if sys.platform == "win32":
            tunnel_process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            tunnel_process.terminate()
        # Wait up to 5 seconds
        try:
            tunnel_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Force kill if needed
            tunnel_process.kill()
            tunnel_process.wait()
        print("[TUNNEL] Stopped")
    except Exception as e:
        print(f"[TUNNEL] Error stopping: {e}")
    finally:
        tunnel_process = None
        tunnel_running = False

def get_status():
    """Get tunnel status."""
    if tunnel_running and tunnel_process:
        if tunnel_process.poll() is None:
            return "running"
        else:
            return "stopped"
    return "not_started"

if __name__ == "__main__":
    # Specify cloudflared.exe path if not in PATH
    cloudflared_path = None  # Or specify: "C:\\path\\to\\cloudflared.exe"
    try:
        if start_tunnel(port=PORT, cloudflared_path=cloudflared_path, timeout=30):
            print(f"\n[TUNNEL] Tunnel is running!")
            print(f"[TUNNEL] URL: {tunnel_url or 'Check .cf file'}")
            print(f"[TUNNEL] Status: {get_status()}")
            print("\n[TUNNEL] Press Ctrl+C to stop")
            print("[TUNNEL] All output is suppressed\n")
            # Keep alive
            while get_status() == "running":
                time.sleep(1)
            print("[TUNNEL] Tunnel process ended")
        else:
            print("[TUNNEL] Failed to start tunnel")
    except KeyboardInterrupt:
        print("\n[TUNNEL] Interrupt received")
        stop_tunnel()
    except Exception as e:
        print(f"[TUNNEL] Error: {e}")
        stop_tunnel()