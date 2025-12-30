"""High-level tunnel runner with state management and customization."""
import sys
import os
from .bin_loader import get_bin
from .is_online import check_connection
from .vpn_detect import is_vpn_connected, get_vpn_details
from . import tunnel


class TunnelRunner:
    """
    High-level tunnel manager with state tracking.
    
    Usage:
        runner = TunnelRunner(port=5000, debug=True)
        runner.start()
        print(runner.url)
        runner.stop()
    """
    
    def __init__(
        self,
        port=5000,
        timeout=60,
        debug=True,
        auto_download=True,
        force_download=False,
        update=False,
        bin_dir=None,
        binary_path=None,
        check_internet=True,
        check_vpn=True,
        progress_callback=None,
        url_callback=None
    ):
        """
        Initialize tunnel runner.
        
        Args:
            port: Local port to tunnel (default: 5000)
            timeout: Timeout for URL capture (default: 60)
            debug: Debug mode (default: True)
            auto_download: Auto download binary on init (default: True)
            force_download: Force re-download binary (default: False)
            update: Check for binary updates (default: False)
            bin_dir: Custom binary directory (default: None)
            binary_path: Direct path to binary (skips download)
            check_internet: Check internet before start (default: True)
            check_vpn: Check VPN before start (default: True)
            progress_callback: Download progress callback(downloaded, total, percent)
            url_callback: URL found callback(url)
        """
        self.port = port
        self.timeout = timeout
        self.debug = debug
        self.check_internet = check_internet
        self.check_vpn = check_vpn
        self.progress_callback = progress_callback
        self.url_callback = url_callback
        
        # State variables
        self.url = None
        self.running = False
        self.binary_path = binary_path
        self.health_status = {}
        
        # Internal handles
        self._lib_handle = None
        self._process_handle = None
        self._running_flag = None
        self._reader_thread = None
        
        # Auto-download binary if needed
        if auto_download and not binary_path:
            self.binary_path = get_bin(
                bin_dir=bin_dir,
                debug=debug,
                force_download=force_download,
                update=update,
                progress_callback=progress_callback
            )
    
    def _health_check(self):
        """Run health checks."""
        self.health_status = {
            'internet': True,
            'vpn': False,
            'vpn_details': None
        }
        
        # Check internet
        if self.check_internet:
            self.health_status['internet'] = check_connection()
            if not self.health_status['internet']:
                return False
        
        # Check VPN
        if self.check_vpn:
            self.health_status['vpn'] = is_vpn_connected()
            if self.health_status['vpn']:
                self.health_status['vpn_details'] = get_vpn_details()
                return False
        
        return True
    
    def _url_found_callback(self, url):
        """Internal callback when URL is captured."""
        self.url = url
        if self.url_callback:
            self.url_callback(url)
    
    def start(self):
        """
        Start the tunnel.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if self.running:
            return False
        
        if not self.binary_path or not os.path.exists(self.binary_path):
            return False
        
        # Health checks
        if not self._health_check():
            return False
        
        # Determine if DLL or executable
        is_dll = self.binary_path.lower().endswith('.dll')
        
        if is_dll and sys.platform == 'win32':
            # Windows DLL mode
            self._lib_handle, self.url, self._reader_thread, self._running_flag = \
                tunnel.start_tunnel_dll(
                    self.binary_path,
                    self.port,
                    self.timeout,
                    self._url_found_callback
                )
            
            if self.url:
                self.running = True
                return True
            return False
        else:
            # Subprocess mode
            self._process_handle, self.url = tunnel.start_tunnel_subprocess(
                self.binary_path,
                self.port,
                self.timeout,
                self._url_found_callback
            )
            
            if self.url:
                self.running = True
                return True
            return False
    
    def stop(self):
        """Stop the tunnel."""
        if not self.running:
            return
        
        # Stop based on mode
        if self._lib_handle:
            tunnel.stop_tunnel_dll(self._lib_handle, self._running_flag)
            self._lib_handle = None
            self._running_flag = None
            self._reader_thread = None
        
        if self._process_handle:
            tunnel.stop_tunnel_subprocess(self._process_handle)
            self._process_handle = None
        
        self.running = False
        self.url = None
    
    def restart(self):
        """Restart the tunnel."""
        self.stop()
        return self.start()
    
    def get_status(self):
        """
        Get detailed status.
        
        Returns:
            dict: Status information
        """
        status = {
            'running': self.running,
            'url': self.url,
            'port': self.port,
            'binary': self.binary_path,
            'health': self.health_status
        }
        
        # Check if process is alive
        if self._process_handle and self.running:
            status['process_alive'] = self._process_handle.poll() is None
        
        return status
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
    
    def __repr__(self):
        """String representation."""
        status = "RUNNING" if self.running else "STOPPED"
        return f"<TunnelRunner port={self.port} status={status} url={self.url}>"