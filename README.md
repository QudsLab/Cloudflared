# Cloudflared DLL/Shared Library Build

Build [cloudflared](https://github.com/cloudflare/cloudflared) as DLL/shared library instead of executable.

## Quick Start

```bash
# Clone this repo
git clone <this-repo-url>

# Clone cloudflared
git clone https://github.com/cloudflare/cloudflared.git

# Apply modifications
python updates/replace.py ./cloudflared

# Build (Windows example)
cd cloudflared
go build -buildmode=c-shared -o cloudflared.dll ./cmd/cloudflared
```

## Exported Functions

| Function             | Signature                            | Description                                  |
| -------------------- | ------------------------------------ | -------------------------------------------- |
| `CloudflaredInit`    | `int CloudflaredInit()`              | Initialize cloudflared, returns 0 on success |
| `CloudflaredRun`     | `int CloudflaredRun(char* args)`     | Run with args (async), returns 0 on success  |
| `CloudflaredRunSync` | `int CloudflaredRunSync(char* args)` | Run with args (blocking)                     |
| `CloudflaredStop`    | `int CloudflaredStop()`              | Stop and cleanup                             |
| `CloudflaredVersion` | `char* CloudflaredVersion()`         | Get version string                           |

## Usage Example

### C/C++

```c
#include "cloudflared.h"

int main() {
    CloudflaredInit();
    CloudflaredRunSync("cloudflared tunnel run my-tunnel");
    CloudflaredStop();
    return 0;
}
```

### Python (ctypes)

```python
import ctypes

lib = ctypes.CDLL("./cloudflared.dll")  # or .so/.dylib
lib.CloudflaredInit()
lib.CloudflaredRunSync(b"cloudflared tunnel run my-tunnel")
lib.CloudflaredStop()
```

## Build Platforms

| Platform      | File     | GOOS/GOARCH   |
| ------------- | -------- | ------------- |
| Windows x64   | `.dll`   | windows/amd64 |
| Windows x86   | `.dll`   | windows/386   |
| Linux x64     | `.so`    | linux/amd64   |
| Linux x86     | `.so`    | linux/386     |
| Linux ARM64   | `.so`    | linux/arm64   |
| Linux ARM     | `.so`    | linux/arm     |
| macOS Intel   | `.dylib` | darwin/amd64  |
| macOS ARM64   | `.dylib` | darwin/arm64  |
| Android ARM64 | `.so`    | android/arm64 |
| Android ARM   | `.so`    | android/arm   |
| Android x64   | `.so`    | android/amd64 |
| Android x86   | `.so`    | android/386   |
| FreeBSD x64   | `.so`    | freebsd/amd64 |
| OpenBSD x64   | `.so`    | openbsd/amd64 |

## Files Modified

| File                 | Change                                 |
| -------------------- | -------------------------------------- |
| `main.go`            | Added `runAppWithArgs()` for DLL entry |
| `dll_exports.go`     | **NEW** - C-exported functions         |
| `generic_service.go` | `runApp()` accepts `args` parameter    |
| `linux_service.go`   | `runApp()` accepts `args` parameter    |
| `macos_service.go`   | `runApp()` accepts `args` parameter    |
| `windows_service.go` | `runApp()` accepts `args` parameter    |

## Automated Builds

GitHub Actions builds run twice daily (`0 6,18 * * *`). Binaries are committed to `binaries/` with SHA256/MD5 checksums.

## Build Commands

```bash
# Windows DLL
GOOS=windows GOARCH=amd64 CGO_ENABLED=1 go build -buildmode=c-shared -o cloudflared.dll ./cmd/cloudflared

# Linux SO
GOOS=linux GOARCH=amd64 CGO_ENABLED=1 go build -buildmode=c-shared -o cloudflared.so ./cmd/cloudflared

# macOS DYLIB
GOOS=darwin GOARCH=arm64 CGO_ENABLED=1 go build -buildmode=c-shared -o cloudflared.dylib ./cmd/cloudflared
```

## License

Original cloudflared is licensed under [Apache 2.0](https://github.com/cloudflare/cloudflared/blob/master/LICENSE).
