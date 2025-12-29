"""
main.py - Simple entry point for Cloudflared Python utilities
"""

from utils import is_online, get_platform_binaries, is_vpn_connected, start_tunnel, stop_tunnel

if __name__ == "__main__":
    print("Cloudflared Python Utilities Demo\n")
    print(f"Online: {is_online()}")
    print(f"VPN Detected: {is_vpn_connected()}")
    print("Downloading platform binaries (dry run)...")
    get_platform_binaries("../binaries")
    print("(Tunnel demo skipped. See tunnel.py for usage.)")
