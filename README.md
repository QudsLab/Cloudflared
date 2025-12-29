<p align="center">
    <img src="assets/banner.png" alt="Cloudflared Banner" />
</p>


# Cloudflared DLL Build

Build [cloudflared](https://github.com/cloudflare/cloudflared) as a shared library (DLL/SO/DYLIB).

## Quick Start

```bash
# 1. Load DLL
python test.py binaries/windows-amd64/cloudflared-windows-amd64.dll

# 2. Or use in your code:
import ctypes
lib = ctypes.CDLL("cloudflared.dll")
lib.CloudflaredInit()
lib.CloudflaredRun(b"cloudflared tunnel --url http://localhost:8080 --protocol http2")
# ... your app runs ...
lib.CloudflaredStop()
```

## Exported Functions

| Function                         | Description                   |
| -------------------------------- | ----------------------------- |
| `CloudflaredInit()`              | Initialize (call once)        |
| `CloudflaredRun(char* args)`     | Run tunnel command (async)    |
| `CloudflaredRunSync(char* args)` | Run tunnel command (blocking) |
| `CloudflaredStop()`              | Shutdown gracefully           |
| `CloudflaredVersion()`           | Get version string            |

## Platforms (12)

| Platform                  | File     |
| ------------------------- | -------- |
| Windows x64/x86           | `.dll`   |
| Linux x64/x86/ARM64/ARM   | `.so`    |
| macOS Intel/ARM64         | `.dylib` |
| Android ARM64/ARM/x64/x86 | `.so`    |

## Important: Protocol Selection

> **Use `--protocol http2`** if you have firewall/network issues!

```bash
# QUIC (default) - uses UDP, often blocked by firewalls
cloudflared tunnel --url http://localhost:8080

# HTTP/2 - uses TCP, works through most firewalls ✓
cloudflared tunnel --url http://localhost:8080 --protocol http2
```

## Why QUIC Fails

QUIC uses UDP which is often blocked by:

- Corporate firewalls
- VPNs
- Some ISPs
- Windows Firewall with strict rules

**Solution**: Add `--protocol http2` to use TCP instead.

## Build It Yourself

```bash
# 1. Clone
git clone https://github.com/cloudflare/cloudflared.git

# 2. Apply modifications
python updates/replace.py ./cloudflared

# 3. Build
cd cloudflared
go build -buildmode=c-shared -o cloudflared.dll ./cmd/cloudflared
```

## Files Modified

| File             | Change                   |
| ---------------- | ------------------------ |
| `main.go`        | Added `runAppWithArgs()` |
| `dll_exports.go` | **NEW** - C exports      |
| `*_service.go`   | Accept args parameter    |

## GitHub Actions

Builds run automatically and commit to `binaries/` folder.

## License

Apache 2.0 (same as cloudflared)
