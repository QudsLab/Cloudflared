# Cloudflared DLL Build - Complete Record

> All build progress, analysis, and modifications consolidated in one file.

---

## Project Summary

**Goal**: Build cloudflared as DLL/shared library for 14 platforms  
**Source**: https://github.com/cloudflare/cloudflared  
**Status**: ✅ Complete

---

## Task Checklist

- [x] **Task 1**: Analyze & Identify Files

  - [x] Clone cloudflared repository
  - [x] Analyze `cmd/cloudflared/main.go`
  - [x] Analyze `cmd/cloudflared/generic_service.go`
  - [x] Analyze `cmd/cloudflared/windows_service.go`
  - [x] Analyze `cmd/cloudflared/linux_service.go`
  - [x] Analyze `cmd/cloudflared/macos_service.go`

- [x] **Task 2**: Create Modified Files

  - [x] `dll_exports.go` - NEW: C-exported DLL entry points
  - [x] `main.go` - Added `runAppWithArgs()` function
  - [x] `generic_service.go` - Changed to accept args parameter
  - [x] `linux_service.go` - Changed to accept args parameter
  - [x] `macos_service.go` - Changed to accept args parameter
  - [x] `windows_service.go` - Changed to accept args parameter

- [x] **Task 3**: Create Replace Script

  - [x] `updates/json/file_mapping.json`
  - [x] `updates/replace.py`

- [x] **Task 4**: Create GitHub Actions Workflow

  - [x] `.github/workflows/build-dll.yml`
  - [x] 14-platform build matrix
  - [x] Hash generation (SHA256, MD5)
  - [x] Automated binary commits

- [x] **Task 5**: Create Documentation
  - [x] `README.md`

---

## Analysis Results

### Files with `os.Args` Dependencies

| File                 | Line(s)     | Original Code           | Modification           |
| -------------------- | ----------- | ----------------------- | ---------------------- |
| `generic_service.go` | 31          | `app.Run(os.Args)`      | `app.Run(args)`        |
| `linux_service.go`   | 39          | `app.Run(os.Args)`      | `app.Run(args)`        |
| `macos_service.go`   | 38          | `app.Run(os.Args)`      | `app.Run(args)`        |
| `windows_service.go` | 80, 92, 129 | Multiple `os.Args` uses | Pass `args` via struct |

### Key Changes

1. **`runApp()` signature changed**: `func runApp(app *cli.App, graceShutdownC chan struct{}, args []string)`
2. **New `runAppWithArgs()` function** in main.go for DLL entry
3. **New `dll_exports.go`** with C-exported functions

---

## Generated Files

```
Cloudflared/
├── .github/
│   └── workflows/
│       └── build-dll.yml          # GitHub Actions workflow
├── updates/
│   ├── json/
│   │   └── file_mapping.json      # File path mappings
│   ├── modified_files/
│   │   ├── dll_exports.go         # NEW: DLL entry points
│   │   ├── main.go                # Modified main
│   │   ├── generic_service.go     # Modified service
│   │   ├── linux_service.go       # Modified service
│   │   ├── macos_service.go       # Modified service
│   │   └── windows_service.go     # Modified service
│   └── replace.py                 # File replacer script
└── README.md                      # Usage documentation
```

---

## DLL Exported Functions

```c
int CloudflaredInit();                    // Initialize, returns 0 on success
int CloudflaredRun(char* args);           // Run async
int CloudflaredRunSync(char* args);       // Run blocking
int CloudflaredStop();                    // Stop and cleanup
char* CloudflaredVersion();               // Get version
void CloudflaredFreeString(char* s);      // Free returned strings
```

---

## 14 Target Platforms

| #   | Platform      | GOOS    | GOARCH | Extension |
| --- | ------------- | ------- | ------ | --------- |
| 1   | Windows x64   | windows | amd64  | .dll      |
| 2   | Windows x86   | windows | 386    | .dll      |
| 3   | Linux x64     | linux   | amd64  | .so       |
| 4   | Linux x86     | linux   | 386    | .so       |
| 5   | Linux ARM64   | linux   | arm64  | .so       |
| 6   | Linux ARM     | linux   | arm    | .so       |
| 7   | macOS Intel   | darwin  | amd64  | .dylib    |
| 8   | macOS ARM64   | darwin  | arm64  | .dylib    |
| 9   | Android ARM64 | android | arm64  | .so       |
| 10  | Android ARM   | android | arm    | .so       |
| 11  | Android x64   | android | amd64  | .so       |
| 12  | Android x86   | android | 386    | .so       |
| 13  | FreeBSD x64   | freebsd | amd64  | .so       |
| 14  | OpenBSD x64   | openbsd | amd64  | .so       |

---

## Build Commands

### Windows

```bash
GOOS=windows GOARCH=amd64 CGO_ENABLED=1 go build -buildmode=c-shared -o cloudflared.dll ./cmd/cloudflared
```

### Linux

```bash
GOOS=linux GOARCH=amd64 CGO_ENABLED=1 go build -buildmode=c-shared -o cloudflared.so ./cmd/cloudflared
```

### macOS

```bash
GOOS=darwin GOARCH=arm64 CGO_ENABLED=1 go build -buildmode=c-shared -o cloudflared.dylib ./cmd/cloudflared
```

### Android (requires NDK)

```bash
CC=aarch64-linux-android21-clang GOOS=android GOARCH=arm64 CGO_ENABLED=1 go build -buildmode=c-shared -o cloudflared.so ./cmd/cloudflared
```

---

## Usage

### Step 1: Apply Modifications

```bash
git clone https://github.com/cloudflare/cloudflared.git
python updates/replace.py ./cloudflared
```

### Step 2: Build

```bash
cd cloudflared
go build -buildmode=c-shared -o cloudflared.dll ./cmd/cloudflared
```

### Step 3: Use in Your Application

```python
import ctypes
lib = ctypes.CDLL("./cloudflared.dll")
lib.CloudflaredInit()
lib.CloudflaredRunSync(b"cloudflared tunnel run my-tunnel")
lib.CloudflaredStop()
```

---

## Schedule

GitHub Actions workflow runs at:

- **06:00 UTC** daily
- **18:00 UTC** daily

Binaries are auto-committed to `binaries/` directory with checksums.

---

## Summary of Changes

Modified 5 existing files + added 1 new file to enable DLL build:

1. **Removed direct `os.Args` usage** from all service files
2. **Added `args []string` parameter** to `runApp()` function signature
3. **Created `dll_exports.go`** with C-compatible exported functions
4. **Maintained backward compatibility** - executable build still works

Total lines changed: ~50 lines across 5 files  
Build mode: `-buildmode=c-shared`
