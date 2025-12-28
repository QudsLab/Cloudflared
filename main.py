#!/usr/bin/env python3
"""
Main test runner - runs server and tunnel in separate threads.
No OOP - keeps it simple.
"""

import sys
import time
import threading
import os
import re

# Import our modules
import server
import tunnel

# Config
WAIT_FOR_TUNNEL = 30  # seconds to wait for tunnel to establish


def parse_url_from_input(text):
    """Extract trycloudflare URL from text."""
    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', text)
    if match:
        return match.group(0)
    return None


def main():
    print("=" * 60)
    print("Cloudflared DLL Test")
    print("=" * 60)
    
    # Get DLL path
    dll_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Load DLL
    print("\n[1/4] Loading DLL...")
    if not tunnel.load_dll(dll_path):
        print("ERROR: Could not load DLL")
        print("Usage: python main.py [dll_path]")
        sys.exit(1)
    
    print(f"      Version: {tunnel.get_version()}")
    
    # Initialize tunnel
    print("\n[2/4] Initializing tunnel...")
    tunnel.init_tunnel()
    
    # Start HTTP server in background
    print("\n[3/4] Starting HTTP server...")
    server_thread = server.run_server_thread()
    time.sleep(1)  # Wait for server to start
    print(f"      Server running on http://localhost:{server.PORT}")
    
    # Start tunnel
    print("\n[4/4] Starting Cloudflare tunnel...")
    print("      (This may take 30-60 seconds)")
    print("-" * 60)
    
    # Start tunnel in background so we can see output
    tunnel_thread = threading.Thread(
        target=lambda: tunnel.start_tunnel(port=server.PORT, wait_for_url=False),
        daemon=True
    )
    tunnel_thread.start()
    
    # Wait for tunnel to establish
    print(f"\nWaiting {WAIT_FOR_TUNNEL}s for tunnel to connect...")
    print("Watch for: https://xxx.trycloudflare.com\n")
    
    for i in range(WAIT_FOR_TUNNEL):
        time.sleep(1)
        sys.stdout.write(f"\r[{i+1}/{WAIT_FOR_TUNNEL}s] ")
        sys.stdout.flush()
    
    print("\n")
    print("-" * 60)
    
    # Ask user for URL
    print("\nCopy the tunnel URL from above and paste it here:")
    print("(or press Enter to skip tunnel test)")
    
    try:
        user_input = input("> ").strip()
    except EOFError:
        user_input = ""
    
    url = parse_url_from_input(user_input) if user_input else None
    
    if url:
        tunnel.save_url(url)
        print(f"\nTunnel URL: {url}")
        print(f"Saved to: {tunnel.CF_FILE}")
    else:
        # Check if we have a saved URL
        saved_url = tunnel.get_url()
        if saved_url:
            print(f"\nUsing saved URL: {saved_url}")
            url = saved_url
    
    # Print status
    print("\n" + "=" * 60)
    print("TEST READY")
    print("=" * 60)
    print(f"  Local server: http://localhost:{server.PORT}")
    if url:
        print(f"  Tunnel URL:   {url}")
    print("")
    print("You can now test manually in your browser.")
    print("Press Ctrl+C to stop.\n")
    
    # Keep running until user stops
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    
    # Cleanup
    tunnel.stop_tunnel()
    server.stop_server()
    
    print("Done.")


if __name__ == "__main__":
    main()
