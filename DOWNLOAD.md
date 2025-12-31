## Cloudflared Binary Download Guide

This guide helps you download and choose the correct Cloudflared binary for your system. All download information is managed in `bin.json` in the base directory.

### 1. Identify Your Platform

Check your operating system and architecture:
- **Windows**: 32-bit (`windows-386`) or 64-bit (`windows-amd64`)
- **Linux**: 32-bit (`linux-386`), 64-bit (`linux-amd64`), ARM (`linux-arm`), ARM64 (`linux-arm64`)
- **macOS**: Intel (`darwin-amd64`), Apple Silicon (`darwin-arm64`)
- **Android**: 386, amd64, arm, arm64

### 2. Locate the Correct Binary

In `bin.json`, find your platform under the `platforms` section. Each platform lists available files with download URLs.

Example for Windows 64-bit:
```
"windows-amd64": {
	"files": [
		{
			"filename": "cloudflared-windows-amd64.dll",
			"url": "..."
		},
		...
	]
}
```

### 3. Download the Binary

Copy the `url` for your platform's binary and download it using your browser or a tool like `curl` or `wget`.

Example (using curl):
```
curl -O https://raw.githubusercontent.com/QudsLab/Cloudflared/main/binaries/windows-amd64/cloudflared-windows-amd64.dll
```

### 4. Verify the Download (Optional)

Check the `sha256` or `md5` hash in `bin.json` to verify your download:
```
CertUtil -hashfile cloudflared-windows-amd64.dll SHA256
```
Compare the output with the value in `bin.json`.

### 5. Load the Binary

To use Cloudflared, you must load the binary from the correct platform folder. Place the downloaded file in the appropriate directory or configure your application to use it.

---
**Note:** Always choose the binary that matches your system. If unsure, check your OS and architecture.