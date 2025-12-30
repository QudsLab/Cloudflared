"""Cloudflared utilities package."""
from .is_online import is_online, check_connection
from .vpn_detect import is_vpn_connected, get_vpn_details
from .bin_loader import get_platform_binaries, get_platform_key, get_bin
from .runner import TunnelRunner

__all__ = [
    "is_online",
    "check_connection",
    "is_vpn_connected",
    "get_vpn_details",
    "get_platform_binaries",
    "get_platform_key",
    "get_bin",
    "TunnelRunner"
]

__version__ = "1.0.0"