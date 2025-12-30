#!/usr/bin/env python3
"""
Enhanced Universal VPN/Tunnel Detector
- Multiple detection methods with weighted confidence scoring
- Returns bool + confidence score (0.0 - 1.0)
- Works with any VPN: WARP, OpenVPN, WireGuard, etc.
"""
import subprocess
import platform
import socket
import re
import json
import time
from typing import Dict, List, Optional, Tuple
class VPNDetector:
    def __init__(self):
        self.system = platform.system()
        self.results = {
            'vpn_detected': False,
            'confidence': 0.0,
            'methods': {},
            'gateway': None,
            'public_ip': None,
            'local_ip': None,
            'dns_servers': [],
            'virtual_interfaces': [],
            'traceroute_hops': 0,
        }
        # Weights for each detection method (higher = more reliable)
        self.weights = {
            'gateway': 0.08,
            'virtual_interface': 0.25,
            'routing': 0.15,
            'dns': 0.04,
            'ip_mismatch': 0.15,
            'vpn_process': 0.18,
            'mtu_check': 0.06,
            'traceroute': 0.03,
            'latency': 0.03,
            'network_adapter': 0.03,
        }
    def detect_all(self) -> Dict:
        """Run all detection methods with confidence scoring"""
        total_confidence = 0.0
        # Run all detection methods
        methods = [
            ('gateway', self.check_gateway_reachable),
            ('virtual_interface', self.check_virtual_interfaces),
            ('routing', self.check_routing_table),
            ('dns', self.check_dns_servers),
            ('ip_mismatch', self.check_ip_mismatch),
            ('vpn_process', self.check_vpn_processes),
            ('mtu_check', self.check_mtu_size),
            ('traceroute', self.check_traceroute_pattern),
            ('latency', self.check_gateway_latency),
            ('network_adapter', self.check_network_adapter_description),
        ]
        for method_name, method_func in methods:
            try:
                detected = method_func()
                self.results['methods'][method_name] = detected
                if detected:
                    total_confidence += self.weights.get(method_name, 0.05)
            except Exception as e:
                self.results['methods'][method_name] = False
                # Silently handle errors in module mode
        # Calculate final confidence (0.0 - 1.0)
        self.results['confidence'] = min(total_confidence, 1.0)
        # Determine if VPN is active
        has_strong_indicators = (
            self.results['methods'].get('virtual_interface', False) or
            self.results['methods'].get('ip_mismatch', False) or
            (
                self.results['methods'].get('routing', False) and
                self.results['methods'].get('vpn_process', False)
            )
        )
        self.results['vpn_detected'] = (
            self.results['confidence'] >= 0.30 or has_strong_indicators
        )
        return self.results
    def check_gateway_reachable(self) -> bool:
        """Check if default gateway is reachable"""
        try:
            gateway = self.get_default_gateway()
            if not gateway:
                return False
            self.results['gateway'] = gateway
            # Ping gateway multiple times for reliability
            success_count = 0
            for _ in range(3):
                if self.system == "Windows":
                    cmd = ['ping', '-n', '1', '-w', '500', gateway]
                else:
                    cmd = ['ping', '-c', '1', '-W', '1', gateway]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    success_count += 1
            # If gateway mostly unreachable, likely VPN
            return success_count < 2
        except:
            return False
    def get_default_gateway(self) -> Optional[str]:
        """Get default gateway IP"""
        try:
            if self.system == "Windows":
                result = subprocess.run(
                    ['ipconfig'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in result.stdout.split('\n'):
                    if 'Default Gateway' in line or 'デフォルト ゲートウェイ' in line:
                        match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                        if match:
                            return match.group(1)
            elif self.system == "Linux":
                result = subprocess.run(
                    ['ip', 'route', 'show', 'default'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                match = re.search(r'default via (\d+\.\d+\.\d+\.\d+)', result.stdout)
                if match:
                    return match.group(1)
            elif self.system == "Darwin":
                result = subprocess.run(
                    ['route', '-n', 'get', 'default'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in result.stdout.split('\n'):
                    if 'gateway:' in line:
                        match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                        if match:
                            return match.group(1)
        except:
            pass
        return None
    def check_virtual_interfaces(self) -> bool:
        """Check for virtual network interfaces"""
        vpn_indicators = [
            'cloudflare warp', 'warp interface', 'tun', 'tap',
            'utun', 'ppp', 'vpn', 'wireguard', 'wg', 'nord',
            'express', 'proton', 'mullvad', 'pia', 'tunnelblick',
            'openvpn', 'viscosity', 'pritunl'
        ]
        try:
            if self.system == "Windows":
                result = subprocess.run(
                    ['ipconfig', '/all'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            elif self.system == "Linux":
                result = subprocess.run(
                    ['ip', 'addr'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            else:
                result = subprocess.run(
                    ['ifconfig'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            output_lower = result.stdout.lower()
            for indicator in vpn_indicators:
                if indicator in output_lower:
                    for line in result.stdout.split('\n'):
                        if indicator in line.lower():
                            self.results['virtual_interfaces'].append(line.strip())
                    return True
        except:
            pass
        return False
    def check_routing_table(self) -> bool:
        """Check routing table for VPN patterns"""
        try:
            if self.system == "Windows":
                result = subprocess.run(
                    ['route', 'print', '0.0.0.0'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            elif self.system == "Linux":
                result = subprocess.run(
                    ['ip', 'route'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            else:
                result = subprocess.run(
                    ['netstat', '-rn'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            output = result.stdout.lower()
            # VPN-specific CGNAT ranges
            vpn_ranges = [
                '100.96.',
                '100.64.',
                '10.8.',
                '10.2.',
                '172.16.',
            ]
            vpn_count = sum(1 for r in vpn_ranges if r in output)
            # Check interface names in routes
            vpn_ifaces = ['tun', 'tap', 'utun', 'ppp', 'wg']
            iface_count = sum(1 for i in vpn_ifaces if i in output)
            return vpn_count >= 1 or iface_count >= 1
        except:
            pass
        return False
    def check_dns_servers(self) -> bool:
        """Check DNS servers for VPN providers"""
        vpn_dns = [
            ('1.1.1.1', 'Cloudflare WARP'),
            ('1.0.0.1', 'Cloudflare WARP'),
            ('103.86.96.', 'NordVPN'),
            ('103.86.99.', 'NordVPN'),
            ('10.8.0.', 'OpenVPN'),
            ('162.252.172.', 'ProtonVPN'),
        ]
        try:
            if self.system == "Windows":
                result = subprocess.run(
                    ['ipconfig', '/all'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                dns_section = False
                for line in result.stdout.split('\n'):
                    if 'DNS Servers' in line:
                        dns_section = True
                    if dns_section:
                        for dns, provider in vpn_dns:
                            if dns in line:
                                self.results['dns_servers'].append(f"{dns} ({provider})")
                                return True
                        if 'adapter' in line.lower():
                            dns_section = False
            else:
                try:
                    with open('/etc/resolv.conf', 'r') as f:
                        content = f.read()
                        for dns, provider in vpn_dns:
                            if dns in content:
                                self.results['dns_servers'].append(f"{dns} ({provider})")
                                return True
                except:
                    pass
        except:
            pass
        return False
    def check_ip_mismatch(self) -> bool:
        """Advanced IP analysis - check for CGNAT ranges"""
        try:
            # Get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            self.results['local_ip'] = local_ip
            # Get public IP
            try:
                result = subprocess.run(
                    ['curl', '-s', '--max-time', '3', 'https://api.ipify.org'],
                    capture_output=True,
                    text=True,
                    timeout=4
                )
                public_ip = result.stdout.strip()
                self.results['public_ip'] = public_ip
                # CGNAT/VPN ranges (STRONG indicator)
                cgnat_ranges = [
                    '100.64.',
                    '100.96.',
                    '172.16.',
                    '10.8.',
                    '10.2.',
                ]
                for cgnat in cgnat_ranges:
                    if local_ip.startswith(cgnat):
                        return True
                # Normal private IPs = not VPN
                if local_ip.startswith(('192.168.', '10.0.')):
                    return False
            except:
                pass
        except:
            pass
        return False
    def check_vpn_processes(self) -> bool:
        """Check for ACTIVE VPN processes"""
        try:
            if self.system == "Windows":
                result = subprocess.run(
                    ['netstat', '-ano'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                # WARP active = UDP 2408 or connections to Cloudflare edge
                warp_active = (
                    ':2408' in result.stdout or
                    '162.159.' in result.stdout or
                    ':500' in result.stdout and 'UDP' in result.stdout
                )
                if warp_active:
                    return True
                # Check for other VPN processes
                vpn_indicators = [
                    'openvpn.exe',
                    'wireguard.exe',
                    'nordvpn.exe',
                    'expressvpn',
                    'protonvpn'
                ]
                result = subprocess.run(
                    ['tasklist', '/FO', 'CSV', '/NH'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                output_lower = result.stdout.lower()
                for vpn in vpn_indicators:
                    if vpn in output_lower:
                        return True
            else:
                result = subprocess.run(
                    ['ps', 'aux'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                output_lower = result.stdout.lower()
                active_vpns = [
                    'openvpn',
                    'wireguard',
                    'wg-quick',
                    'nordvpnd',
                    'expressvpn',
                    'protonvpn'
                ]
                return any(vpn in output_lower for vpn in active_vpns)
        except:
            pass
        return False
    def check_mtu_size(self) -> bool:
        """Check MTU size (VPNs often use smaller MTU)"""
        try:
            if self.system == "Windows":
                result = subprocess.run(
                    ['netsh', 'interface', 'ipv4', 'show', 'subinterfaces'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in result.stdout.split('\n'):
                    if any(vpn in line.lower() for vpn in ['warp', 'tun', 'tap', 'vpn']):
                        match = re.search(r'\s+(\d+)\s+', line)
                        if match:
                            mtu = int(match.group(1))
                            if mtu < 1400:
                                return True
            else:
                result = subprocess.run(
                    ['ip', 'link'] if self.system == 'Linux' else ['ifconfig'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                current_iface = None
                for line in result.stdout.split('\n'):
                    if 'tun' in line or 'tap' in line or 'utun' in line:
                        current_iface = line
                    if current_iface and 'mtu' in line.lower():
                        match = re.search(r'mtu\s+(\d+)', line.lower())
                        if match:
                            mtu = int(match.group(1))
                            if mtu < 1400:
                                return True
        except:
            pass
        return False
    def check_traceroute_pattern(self) -> bool:
        """Check if first hop is unusual"""
        try:
            gateway = self.results.get('gateway') or self.get_default_gateway()
            if not gateway:
                return False
            if self.system == "Windows":
                cmd = ['tracert', '-h', '3', '-w', '500', gateway]
            else:
                cmd = ['traceroute', '-m', '3', '-w', '1', gateway]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            hops = result.stdout.count('ms') if self.system == "Windows" else result.stdout.count('*')
            self.results['traceroute_hops'] = hops
            return hops > 2
        except:
            pass
        return False
    def check_gateway_latency(self) -> bool:
        """Check if gateway latency is suspiciously high"""
        try:
            gateway = self.results.get('gateway') or self.get_default_gateway()
            if not gateway:
                return False
            latencies = []
            for _ in range(3):
                if self.system == "Windows":
                    cmd = ['ping', '-n', '1', '-w', '1000', gateway]
                else:
                    cmd = ['ping', '-c', '1', '-W', '1', gateway]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    match = re.search(r'time[=<](\d+)', result.stdout)
                    if match:
                        latencies.append(int(match.group(1)))
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                return avg_latency > 15
        except:
            pass
        return False
    def check_network_adapter_description(self) -> bool:
        """Check network adapter descriptions for VPN keywords"""
        try:
            if self.system == "Windows":
                result = subprocess.run(
                    ['wmic', 'nic', 'get', 'name,netenabled'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                vpn_keywords = [
                    'cloudflare', 'warp', 'tunnel', 'vpn',
                    'openvpn', 'wireguard', 'tap', 'tun',
                    'nord', 'express', 'proton', 'mullvad'
                ]
                output_lower = result.stdout.lower()
                for keyword in vpn_keywords:
                    if keyword in output_lower and 'true' in output_lower:
                        return True
        except:
            pass
        return False


if __name__ == "__main__":

    detector = VPNDetector()
    results = detector.detect_all()
    is_vpn = results['vpn_detected']

    print("📋 Simple Output:")
    print(f"VPN_DETECTED={str(is_vpn).lower()}")
    print(f"CONFIDENCE={results['confidence']:.3f}")

# Simple wrapper functions for easy import
def is_vpn_connected():
    """Check if VPN is connected. Returns True if VPN detected."""
    detector = VPNDetector()
    results = detector.detect_all()
    return results["vpn_detected"]


def get_vpn_details():
    """Get detailed VPN detection results."""
    detector = VPNDetector()
    return detector.detect_all()
