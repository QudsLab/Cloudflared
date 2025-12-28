## Issue: WARP VPN Conflict

### Symptoms

```
ERR Unable to establish connection with Cloudflare edge
Lost connection with the edge
connection with edge closed
```

### Cause

**Cloudflare WARP VPN conflicts with cloudflared tunnels.**

Both try to route traffic through Cloudflare's network and interfere with each other.

### Solution

**Turn OFF WARP VPN** before running cloudflared tunnels.

---

## Issue: QUIC Connection Timeout

### Symptoms

```
ERR Failed to dial a quic connection error="timeout: handshake did not complete in time"
ERR Failed to dial a quic connection error="timeout: no recent network activity"
```

### Cause

QUIC protocol uses **UDP** which is blocked by:

- Firewalls (corporate/personal)
- VPNs
- Some ISPs
- Strict Windows Firewall settings

### Solution

Use **HTTP/2** instead of QUIC:

```bash
# Add --protocol http2
cloudflared tunnel --url http://localhost:8080 --protocol http2
```

### In Python/DLL:

```python
lib.CloudflaredRun(b"cloudflared tunnel --url http://localhost:8080 --protocol http2")
```

---

## Issue: Origin Certificate Not Found

### Symptoms

```
ERR Cannot determine default origin certificate path. No file cert.pem
```

### Cause

This is a warning, not an error. For quick tunnels, it's expected.

### Solution

Ignore it - quick tunnels work without certificates.

For production, use named tunnels with proper auth.

---

## Issue: DLL Not Found

### Symptoms

```
Error: DLL not found
```

### Solution

```bash
# Specify full path
python test.py "C:\path\to\cloudflared.dll"

# Or place DLL in current directory
python test.py cloudflared.dll
```

---

## Issue: Port Already in Use

### Symptoms

```
OSError: [Errno 98] Address already in use
```

### Solution

Change the port in test.py or kill the existing process:

```powershell
# Windows
netstat -ano | findstr :8765
taskkill /PID <pid> /F
```

---

## Quick Test Commands

```bash
# Windows
python test.py binaries/windows-amd64/cloudflared-windows-amd64.dll

# Linux
python3 test.py binaries/linux-amd64/cloudflared-linux-amd64.so

# macOS
python3 test.py binaries/darwin-arm64/cloudflared-darwin-arm64.dylib
```
