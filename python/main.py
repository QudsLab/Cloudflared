#!/usr/bin/env python3
"""
Cloudflared Tunnel Manager - Simple Entry Point
"""
import sys
import time
import signal
from pathlib import Path
from dcft import TunnelRunner

CURRENT_DIR = Path(__file__).parent.resolve()
BIN_DIR = CURRENT_DIR / "binaries"



def progress_callback(downloaded, total, percent):
    """Display download progress."""
    bar_length = 40
    filled = int(bar_length * percent / 100)
    bar = '█' * filled + '░' * (bar_length - filled)
    mb_down = downloaded / (1024 * 1024)
    mb_total = total / (1024 * 1024)
    print(f"\r[DOWNLOAD] {bar} {percent:.1f}% ({mb_down:.2f}/{mb_total:.2f} MB)", end='', flush=True)
    if percent >= 100:
        print()


def url_callback(url):
    """Called when tunnel URL is captured."""
    print(f"\n[TUNNEL] ✓ URL captured: {url}")


def main():
    """Main entry point."""
    print("=" * 60)
    print("  Cloudflared Tunnel Manager v2.0")
    print("=" * 60)
    
    # Create runner with customization
    print("\n[INIT] Initializing tunnel runner...")
    runner = TunnelRunner(
        port=5000,
        timeout=60,
        debug=True,
        auto_download=True,
        force_download=False,
        update=False,
        bin_dir=BIN_DIR,
        check_internet=True,
        check_vpn=True,
        progress_callback=progress_callback,
        url_callback=url_callback
    )
    
    if not runner.binary_path:
        print("[ERROR] Failed to obtain binary")
        return 1
    
    print(f"[INIT] Binary: {runner.binary_path}")
    
    # Health checks
    print("\n[HEALTH] Running health checks...")
    if not runner.health_status:
        # Trigger health check
        runner._health_check()
    
    if not runner.health_status.get('internet', False):
        print("[ERROR] ✗ No internet connection")
        return 1
    print("[HEALTH] ✓ Internet connection OK")
    
    if runner.health_status.get('vpn', False):
        print("[WARNING] ✗ VPN detected - tunnel may fail")
        vpn_info = runner.health_status.get('vpn_details', {})
        if vpn_info.get('confidence', 0) > 0.5:
            print(f"[WARNING] VPN confidence: {vpn_info['confidence']:.2%}")
        print("[WARNING] Please disable VPN and retry")
        return 1
    print("[HEALTH] ✓ No VPN detected")
    
    # Setup signal handler
    def cleanup(signum=None, frame=None):
        print("\n\n[SHUTDOWN] Stopping tunnel...")
        runner.stop()
        print("[SHUTDOWN] Goodbye!")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, cleanup)
    
    # Start tunnel
    print(f"\n[TUNNEL] Starting on port {runner.port}...")
    print(f"[TUNNEL] Timeout: {runner.timeout}s")
    
    if not runner.start():
        print("[ERROR] Failed to start tunnel")
        status = runner.get_status()
        print(f"[ERROR] Status: {status}")
        return 1
    
    print("[TUNNEL] ✓ Tunnel started successfully!")
    print(f"[TUNNEL] URL: {runner.url}")
    print(f"[TUNNEL] Status: {runner.running}")
    print(f"[TUNNEL] Port: {runner.port}")
    
    # Keep alive
    print("\n[TUNNEL] Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        while runner.running:
            time.sleep(1)
            # Check if process died
            status = runner.get_status()
            if status.get('process_alive') == False:
                print("\n[TUNNEL] Process ended unexpectedly")
                break
    except KeyboardInterrupt:
        cleanup()
    
    cleanup()
    return 0


if __name__ == "__main__":
    sys.exit(main())