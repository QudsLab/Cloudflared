# Cloudflared DLL API - Clean Status & URL Access

## Overview
Clean API to get tunnel status and URL directly without parsing output or logs.

## Quick Start

```python
from t import load_dll, init_tunnel, start_tunnel, get_tunnel_url

# Load DLL (silent mode by default)
load_dll("path/to/cloudflared.dll", silent=True, debug=False)
init_tunnel()

# Start tunnel and wait for URL
if start_tunnel(port=5000, timeout=30, debug=False):
    url = get_tunnel_url()
    print(f"Tunnel URL: {url}")  # Only this prints!
```

## New DLL Functions

### `CloudflaredGetTunnelStatus()`
Returns the current tunnel status as an integer:
- `0` = Not started
- `1` = Starting (initializing connection)
- `2` = Ready (tunnel established with URL)

**C Signature:**
```c
int CloudflaredGetTunnelStatus();
```

**Python (ctypes):**
```python
lib.CloudflaredGetTunnelStatus.restype = ctypes.c_int
status = lib.CloudflaredGetTunnelStatus()
```

### `CloudflaredGetTunnelURL()`
Returns the tunnel URL as a C string (or NULL if not ready).

**C Signature:**
```c
char* CloudflaredGetTunnelURL();
```

**Python (ctypes):**
```python
lib.CloudflaredGetTunnelURL.restype = ctypes.c_char_p
c_url = lib.CloudflaredGetTunnelURL()
if c_url:
    url = c_url.decode('utf-8')
    lib.CloudflaredFreeString(c_url)  # Important: free memory!
```

## Usage Pattern

```python
import ctypes
import time

# Load DLL
lib = ctypes.CDLL("cloudflared.dll")

# Setup function signatures
lib.CloudflaredInit.restype = ctypes.c_int
lib.CloudflaredRun.argtypes = [ctypes.c_char_p]
lib.CloudflaredRun.restype = ctypes.c_int
lib.CloudflaredGetTunnelStatus.restype = ctypes.c_int
lib.CloudflaredGetTunnelURL.restype = ctypes.c_char_p
lib.CloudflaredFreeString.argtypes = [ctypes.c_char_p]

# Initialize
lib.CloudflaredInit()

# Start tunnel in background thread
import threading
def run():
    lib.CloudflaredRun(b"cloudflared tunnel --url http://localhost:5000")
threading.Thread(target=run, daemon=True).start()

# Poll until ready
while True:
    status = lib.CloudflaredGetTunnelStatus()
    
    if status == 2:  # Ready
        c_url = lib.CloudflaredGetTunnelURL()
        url = c_url.decode('utf-8')
        lib.CloudflaredFreeString(c_url)
        print(f"Tunnel ready: {url}")
        break
    elif status == 0:  # Failed
        print("Tunnel failed to start")
        break
    
    time.sleep(0.5)
```

## Benefits

✓ **No output parsing** - Direct API calls  
✓ **Thread-safe** - Uses mutex internally  
✓ **Clean interface** - Simple status codes  
✓ **Memory safe** - Proper string allocation/deallocation  
✓ **Real-time** - Poll anytime for current status  

## Modified Files

1. **lib_bin_exports.go**
   - Added `globalTunnelURL` and `globalTunnelReady` globals
   - Added `CloudflaredGetTunnelURL()` export
   - Added `CloudflaredGetTunnelStatus()` export
   - Added `CloudflaredSetTunnelURL()` internal function

2. **quick_tunnel.go**
   - Calls `CloudflaredSetTunnelURL()` when tunnel is established
   - Sets global state for DLL API access

## Memory Management

⚠️ **Important**: Always call `CloudflaredFreeString()` after getting the URL to avoid memory leaks:

```python
c_url = lib.CloudflaredGetTunnelURL()
if c_url:
    url = c_url.decode('utf-8')
    lib.CloudflaredFreeString(c_url)  # Free the C string!
```

## Example Class

See `python_example.py` for a complete `CloudflaredTunnel` class that wraps all functionality.
