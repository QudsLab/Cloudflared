import os
import sys
import json
import platform
import requests
BIN_JSON = "https://raw.githubusercontent.com/QudsLab/Cloudflared/refs/heads/main/bin.json"
def load_bin_config():
    """Load binary configuration from remote JSON file."""
    try:
        response = requests.get(BIN_JSON)
        response.raise_for_status()
        bin_data = response.json()
        return bin_data
    except Exception as e:
        print(f"Error loading binary configuration: {e}")
        return {}
def is_android():
    """Detect if running on Android."""
    try:
        # Check for Android-specific environment variables
        if 'ANDROID_ROOT' in os.environ or 'ANDROID_DATA' in os.environ:
            return True
        # Check for Termux
        if 'PREFIX' in os.environ and 'com.termux' in os.environ.get('PREFIX', ''):
            return True
        # Check /system/build.prop (Android-specific file)
        if os.path.exists('/system/build.prop'):
            return True
        return False
    except:
        return False
def get_machine_arch():
    """Get the machine architecture."""
    machine = platform.machine().lower()
    # Normalize architecture names
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
    # Check for Android first
    if is_android():
        arch = get_machine_arch()
        return f'android-{arch}'
    # Handle other platforms
    if sys.platform.startswith('linux'):
        arch = get_machine_arch()
        return f'linux-{arch}'
    elif sys.platform == 'win32':
        arch = get_machine_arch()
        return f'windows-{arch}'
    elif sys.platform == 'darwin':
        arch = get_machine_arch()
        # macOS typically uses amd64 or arm64
        if arch not in ('amd64', 'arm64'):
            arch = 'arm64' if 'arm' in platform.processor().lower() else 'amd64'
        return f'darwin-{arch}'
    else:
        return None
def download_file(url, dest_path):
    """Download a file from URL to destination path."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
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
                print(f"SHA256 mismatch for {file_path}")
                return False
        if expected_md5:
            md5_hash = hashlib.md5(content).hexdigest()
            if md5_hash != expected_md5:
                print(f"MD5 mismatch for {file_path}")
                return False
        return True
    except Exception as e:
        print(f"Error verifying checksum: {e}")
        return False
def get_platform_binaries(bin_dir):
    """Get and download binaries for the current platform."""
    # Load binary configuration
    bin_config = load_bin_config()
    if not bin_config or 'platforms' not in bin_config:
        print("Failed to load binary configuration")
        return []
    # Get current platform key
    platform_key = get_platform_key()
    if not platform_key:
        print(f"Unsupported platform: {sys.platform}")
        return []
    if platform_key not in bin_config['platforms']:
        print(f"No binaries available for platform: {platform_key}")
        return []
    platform_data = bin_config['platforms'][platform_key]
    files = platform_data.get('files', [])
    if not files:
        print(f"No files defined for platform: {platform_key}")
        return []
    downloaded_files = []
    # Create bin directory if it doesn't exist
    os.makedirs(bin_dir, exist_ok=True)
    # Download each file
    for file_info in files:
        filename = file_info.get('filename')
        url = file_info.get('url')
        sha256 = file_info.get('sha256')
        md5 = file_info.get('md5')
        if not filename or not url:
            continue
        dest_path = os.path.join(bin_dir, filename)
        # Check if file already exists and is valid
        if os.path.exists(dest_path):
            if verify_checksum(dest_path, sha256, md5):
                print(f"File already exists and verified: {filename}")
                downloaded_files.append(dest_path)
                continue
            else:
                print(f"Existing file corrupted, re-downloading: {filename}")
        # Download the file
        print(f"Downloading {filename}...")
        if download_file(url, dest_path):
            # Verify the downloaded file
            if verify_checksum(dest_path, sha256, md5):
                print(f"Successfully downloaded and verified: {filename}")
                downloaded_files.append(dest_path)
            else:
                print(f"Downloaded file failed verification: {filename}")
                os.remove(dest_path)
        else:
            print(f"Failed to download: {filename}")
    return downloaded_files




if __name__ == '__main__':
    """Main function for testing."""
    print(f"Platform: {sys.platform}")
    print(f"Is Android: {is_android()}")
    print(f"Architecture: {get_machine_arch()}")
    print(f"Platform Key: {get_platform_key()}")
    # bin_dir = os.path.join(os.getcwd(), 'binaries')
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Downloading binaries to: {current_dir}")
    files = get_platform_binaries(bin_dir=current_dir)
    print(f"\nDownloaded files: {files}")