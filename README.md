<div align="center">

<img src="assets/banner_3.png" alt="Cloudflared Banner" />

<!-- # 🚀 Cloudflared DLL: Tunnels Made Simple -->

### **Embed Cloudflare Tunnels anywhere.** Desktop apps, mobile platforms, automation scripts ,no Go compiler, no complexity. Just drop in a library and go.

[![Tunnel](https://img.shields.io/badge/Cloudflare-Tunnel-orange?style=flat-square&logo=cloudflare)](#)
[![Platforms](https://img.shields.io/badge/Platforms-Windows%20%7C%20Linux%20%7C%20macOS%20%7C%20Android-blue?style=flat-square)](#)
[![Arch](https://img.shields.io/badge/Arch-x86%20%7C%20x64%20%7C%20ARM64-orange?style=flat-square)](#)
[![Embedding](https://img.shields.io/badge/Embedding-DLL%20%7C%20SO%20%7C%20DYLIB-green?style=flat-square)](#)
[![Automation](https://img.shields.io/badge/Automation-Ready-yellow?style=flat-square)](#)

[**Download Binaries**](DOWNLOAD.md) • [**Quick Start**](#quick-start) • [**Python Utils**](python/) • [**Build Guide**](#build-it-yourself)

</div>

---

## 💡 What Makes This Different?

The official `cloudflared` is a CLI tool. This project transforms it into a **shared library** you can integrate into any application:

✨ **Embed tunnels in your apps**  Call tunnel functions from Python, C++, C#, Java, or any language with FFI  
📦 **Prebuilt for 12 platforms**  Windows, Linux, macOS, Android (ARM/x86/x64)  
🔧 **No Go toolchain needed**  Just load the DLL/SO and call functions  
🤖 **Automation-first**  Python scripts included for tunnel management, VPN detection, and connectivity checks  
🎯 **Born from community demand**  Requested in [cloudflared #1402](https://github.com/cloudflare/cloudflared/issues/1402)

### Real-World Use Cases

- **Embed in desktop apps** to expose local services securely
- **Android/iOS apps** that need reverse proxies without root
- **Automation scripts** that spin up/tear down tunnels dynamically
- **Testing frameworks** that need temporary public URLs
- **CI/CD pipelines** for webhook testing or preview deployments

---

## 🎯 Quick Start

### Using the Library (3 lines of code)

```python
import ctypes

# Load the library (DLL/SO/DYLIB based on your platform)
lib = ctypes.CDLL("cloudflared.dll")

# Initialize once
lib.CloudflaredInit()

# Start a tunnel (runs async in background)
lib.CloudflaredRun(b"cloudflared tunnel --url http://localhost:8080 --protocol http2")

# Your app runs here...

# Graceful shutdown
lib.CloudflaredStop()
```

### Using Python Utilities

We've built scripts to make your life easier:

```bash
cd python

# Interactive menu with all features
python main.py

# Or use individual scripts:
python check_connectivity.py   # Test Cloudflare connectivity
python vpn_detect.py           # Check if you're behind a VPN
python download_binaries.py    # Auto-download for your platform
```

---

## 📚 Library API

| Function | Description | Usage |
|----------|-------------|-------|
| `CloudflaredInit()` | Initialize library | Call once at startup |
| `CloudflaredRun(char* args)` | Start tunnel (async) | Non-blocking, returns immediately |
| `CloudflaredRunSync(char* args)` | Start tunnel (blocking) | Blocks until tunnel stops |
| `CloudflaredStop()` | Stop tunnel | Graceful shutdown |
| `CloudflaredVersion()` | Get version | Returns version string |

---

## 🌍 Platforms (12)

| Platform | Architectures | Extension |
|----------|--------------|-----------|
| **Windows** | x64, x86 | `.dll` |
| **Linux** | x64, x86, ARM64, ARM | `.so` |
| **macOS** | Intel, Apple Silicon (ARM64) | `.dylib` |
| **Android** | ARM64, ARM, x64, x86 | `.so` |

All binaries are **automatically built** via GitHub Actions and committed to the [`binaries/`](binaries/) folder. No manual compilation required!

---

## 🔥 Firewall Issues? Use HTTP/2

**Problem:** Default QUIC protocol uses UDP, often blocked by firewalls, VPNs, or corporate networks.

**Solution:** Add `--protocol http2` to use TCP instead:

```bash
# ❌ QUIC (UDP) - May fail on restricted networks
cloudflared tunnel --url http://localhost:8080

# ✅ HTTP/2 (TCP) - Works through most firewalls
cloudflared tunnel --url http://localhost:8080 --protocol http2
```

### When to Use HTTP/2

- Corporate/university networks
- Behind VPNs or proxies
- ISPs that throttle/block UDP
- Windows Firewall with strict rules

---

## 🛠️ Build It Yourself

Want to customize or verify the build?

```bash
# 1. Clone official cloudflared
git clone https://github.com/cloudflare/cloudflared.git

# 2. Apply modifications (adds C exports)
python updates/replace.py ./cloudflared

# 3. Build as shared library
cd cloudflared
go build -buildmode=c-shared -o cloudflared.dll ./cmd/cloudflared
```

### What Gets Modified?

| File | Change |
|------|--------|
| `main.go` | Added `runAppWithArgs()` for programmatic control |
| `lib_bin_exports.go` | **NEW**  C-compatible exports |
| `*_service.go` | Modified to accept args parameter |

All changes are minimal and preserve original functionality.

---

## 🤝 Contributing

Found a bug? Have a feature request? Want to add support for a new platform?

- **Open an issue**  We track everything
- **Submit a PR**  Contributions welcome
- **Star the repo** Helps others discover this project

---

## ⚖️ License

Apache 2.0 (same as official cloudflared)

---

<div align="center">

**If this saved you hours of setup time, consider giving it a ⭐**

Built with 🔥 by developers, for developers

</div>