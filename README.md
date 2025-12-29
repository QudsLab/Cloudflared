<p align="center">
    <img src="assets/banner.png" alt="Cloudflared Banner" />
</p>

<div align="center">

[![Tunnel](https://img.shields.io/badge/Cloudflare-Tunnel-orange?style=flat-square&logo=cloudflare)](#)

[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue?style=flat-square)](#)
[![Mobile](https://img.shields.io/badge/Mobile-Android-green?style=flat-square)](#)
[![Architecture](https://img.shields.io/badge/Arch-x86%20%7C%20x64%20%7C%20ARM64-orange?style=flat-square)](#)
[![Language](https://img.shields.io/badge/Language-Go-00ADD8?style=flat-square&logo=go)](#)
[![Android](https://img.shields.io/badge/Android-Termux%20Compatible-brightgreen?style=flat-square)](#)
[![Android](https://img.shields.io/badge/Android-Native%20Binaries-blue?style=flat-square)](#)
[![Compression](https://img.shields.io/badge/Transport-Compressed%20Streams-purple?style=flat-square)](#)
[![Rebuild](https://img.shields.io/badge/Rebuild-Automated%20Binaries-blue?style=flat-square)](#)
[![Update](https://img.shields.io/badge/Update-Rolling%20Upstream-yellow?style=flat-square)](#)
[![Status](https://img.shields.io/badge/Status-Experimental-orange?style=flat-square)](#)
[![Compatibility](https://img.shields.io/badge/Compatible%20With-Go%20%7C%20Python%20%7C%20Node.js%20%7C%20bash%20%7C%20sh%20%7C%20zsh-lightgrey?style=flat-square)](#)
[![Distribution](https://img.shields.io/badge/Distribution-Direct%20Binary%20Links-success?style=flat-square)](#)
[![Index](https://img.shields.io/badge/Index-bin.json-blue?style=flat-square)](#)
[![Checksum](https://img.shields.io/badge/Checksum-SHA256%20Verified-red?style=flat-square)](#)
[![Integrity](https://img.shields.io/badge/Integrity-Hash%20Validation-critical?style=flat-square)](#)
[![Automation](https://img.shields.io/badge/Automation-Scriptable-yellow?style=flat-square)](#)
[![CI](https://img.shields.io/badge/CI-Friendly-lightgrey?style=flat-square)](#)
[![Update-Check](https://img.shields.io/badge/Update%20Check-Checksum%20Based-blue?style=flat-square)](#)


</div>


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
