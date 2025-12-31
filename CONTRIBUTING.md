# Contributing New Language Wrappers

Want to add support for your favorite language? Awesome! Here’s how you can build a new wrapper (like the Python one) for Cloudflared:

## 1. Pick Your Language
- Node.js, Rust, C#, Ruby, Java, etc. anything goes!

## 2. Use the Shared Library
- All wrappers should use the prebuilt DLL/SO/DYLIB files in the `binaries/` folder.
- Load the shared library using your language’s FFI (Foreign Function Interface) or equivalent.
- Expose the main functions: `CloudflaredInit`, `CloudflaredRun`, `CloudflaredRunSync`, `CloudflaredStop`, `CloudflaredVersion`.

## 3. Follow the Python Example
- See the `python/` folder for a working wrapper.
- Your wrapper should:
  - Load the correct binary for the user’s platform/arch
  - Provide a simple API for starting/stopping tunnels
  - Optionally: add helpers for downloading binaries, checking connectivity, etc.

## 4. Document Your Wrapper
- Add a README in your language’s folder with usage examples.
- Mention any dependencies or special setup steps.

## 5. Submit a Pull Request
- Place your code in a new folder (e.g., `nodejs/`, `rust/`, etc.)
- Update the main README to mention your wrapper
- Open a PR and describe what you’ve added!

## Tips
- Keep it simple and cross-platform
- Reuse the binaries and checksum logic if possible
- Add tests or demo scripts if you can

---

**Let’s make Cloudflared available everywhere!**

Questions? Open an issue or start a discussion.
