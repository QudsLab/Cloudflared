"""Binary loader with silent operation and optional progress display."""
import os
import sys
import platform
import requests
from pathlib import Path

BIN_JSON = "https://raw.githubusercontent.com/QudsLab/Cloudflared/refs/heads/main/bin.json"

def load_bin_config():
    """Load binary configuration from remote JSON file."""
    try:
        response = requests.get(BIN_JSON, timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return {}

def is_android():
    """Detect if running on Android."""
    try:
        if 'ANDROID_ROOT' in os.environ or 'ANDROID_DATA' in os.environ:
            return True
        if 'PREFIX' in os.environ and 'com.termux' in os.environ.get('PREFIX', ''):
            return True
        if os.path.exists('/system/build.prop'):
            return True
        return False
    except:
        return False

def get_machine_arch():
    """Get the machine architecture."""
    machine = platform.machine().lower()
    if machine in ('x86_64', 'amd64', 'x64'):
        return 'amd64'
    elif machine in ('i386', 'i686', 'x86'):
        return '386'
    elif machine in ('aarch64', 'arm64', 'armv8l', 'armv8b'):
        return 'arm64'
    elif machine.startswith('arm'):
        return 'arm'
    else:
        return machine

def get_platform_key():
    """Determine the platform key for binary selection."""
    if is_android():
        arch = get_machine_arch()
        return f'android-{arch}'
    
    if sys.platform.startswith('linux'):
        arch = get_machine_arch()
        return f'linux-{arch}'
    elif sys.platform == 'win32':
        arch = get_machine_arch()
        return f'windows-{arch}'
    elif sys.platform == 'darwin':
        arch = get_machine_arch()
        if arch not in ('amd64', 'arm64'):
            arch = 'arm64' if 'arm' in platform.processor().lower() else 'amd64'
        return f'darwin-{arch}'
    else:
        return None

def download_file(url, dest_path, show_progress=False, progress_callback=None):
    """Download a file with optional progress display."""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        downloaded = 0
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if show_progress and progress_callback and total_size > 0:
                        progress = (downloaded / total_size) * 100
                        progress_callback(downloaded, total_size, progress)
        
        return True
    except:
        return False

def verify_checksum(file_path, expected_sha256=None, expected_md5=None):
    """Verify file checksum (SHA256 or MD5)."""
    import hashlib
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        if expected_sha256:
            sha256_hash = hashlib.sha256(content).hexdigest()
            if sha256_hash != expected_sha256:
                return False
        
        if expected_md5:
            md5_hash = hashlib.md5(content).hexdigest()
            if md5_hash != expected_md5:
                return False
        
        return True
    except:
        return False

def get_platform_binaries(bin_dir, force_download=False, update=False, debug=False, progress_callback=None):
    """
    Get and download binaries for the current platform.
    
    Args:
        bin_dir: Directory to store binaries
        force_download: Force re-download even if file exists
        update: Check and download if newer version available
        debug: Show download progress
        progress_callback: Function(downloaded, total, percent) for progress updates
    
    Returns:
        str: Path to binary file or None if failed
    """
    bin_config = load_bin_config()
    if not bin_config or 'platforms' not in bin_config:
        return None
    
    platform_key = get_platform_key()
    if not platform_key or platform_key not in bin_config['platforms']:
        return None
    
    platform_data = bin_config['platforms'][platform_key]
    files = platform_data.get('files', [])
    if not files:
        return None
    
    os.makedirs(bin_dir, exist_ok=True)
    
    file_info = files[0]
    filename = file_info.get('filename')
    url = file_info.get('url')
    sha256 = file_info.get('sha256')
    md5 = file_info.get('md5')
    
    if not filename or not url:
        return None
    
    dest_path = os.path.join(bin_dir, filename)
    
    # Check if file exists and is valid
    if os.path.exists(dest_path) and not force_download:
        if verify_checksum(dest_path, sha256, md5):
            if not update:
                return dest_path
            # For update mode, we could add version checking here
            # For now, treat existing valid file as up-to-date
            return dest_path
    
    # Download the file
    download_success = download_file(
        url, 
        dest_path, 
        show_progress=debug,
        progress_callback=progress_callback
    )
    
    if not download_success:
        return None
    
    # Verify downloaded file
    if verify_checksum(dest_path, sha256, md5):
        # Make executable on Unix-like systems
        if sys.platform != 'win32':
            try:
                os.chmod(dest_path, 0o755)
            except:
                pass
        return dest_path
    else:
        try:
            os.remove(dest_path)
        except:
            pass
        return None

def get_bin(bin_dir=None, debug=True, force_download=False, update=False, progress_callback=None):
    """
    Get binary path, download if needed.
    
    Args:
        bin_dir: Custom binary directory (None = auto-select based on debug)
        debug: Use current directory if True, ~/.cfbin if False
        force_download: Force re-download
        update: Check for updates
        progress_callback: Progress callback function
    
    Returns:
        str: Path to binary or None
    """
    if not bin_dir:
        if debug:
            bin_dir = os.path.join(os.getcwd(), 'binaries')
        else:
            home_dir = os.path.expanduser("~")
            bin_dir = os.path.join(home_dir, '.cfbin')
    
    return get_platform_binaries(
        bin_dir=bin_dir,
        force_download=force_download,
        update=update,
        debug=debug,
        progress_callback=progress_callback
    )