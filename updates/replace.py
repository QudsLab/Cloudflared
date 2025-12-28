#!/usr/bin/env python3
"""
Cloudflared DLL Build - File Replacer
Replaces original cloudflared source files with modified versions for DLL build.
"""

import json
import hashlib
import shutil
import sys
from pathlib import Path

def compute_hash(filepath: Path, algorithm: str = "sha256") -> str:
    """Compute hash of a file."""
    h = hashlib.new(algorithm)
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def load_mapping(updates_dir: Path) -> dict:
    """Load file mapping from JSON."""
    mapping_file = updates_dir / "json" / "file_mapping.json"
    if not mapping_file.exists():
        print(f"Error: {mapping_file} not found")
        sys.exit(1)
    with open(mapping_file, "r") as f:
        return json.load(f)

def replace_files(cloudflared_repo: Path, updates_dir: Path, verify_only: bool = False) -> bool:
    """Replace original files with modified versions."""
    mapping = load_mapping(updates_dir)
    
    success = True
    for file_info in mapping["files"]:
        original = cloudflared_repo / file_info["original_path"]
        modified = updates_dir / file_info["modified_file"]
        is_new = file_info.get("is_new", False)
        
        if not modified.exists():
            print(f"ERROR: Modified file not found: {modified}")
            success = False
            continue
        
        if not is_new and not original.exists():
            print(f"WARNING: Original file not found: {original}")
        
        if verify_only:
            print(f"VERIFY: {modified.name} -> {file_info['original_path']}")
            continue
        
        # Copy modified file to original location
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(modified, original)
        print(f"REPLACED: {file_info['original_path']}")
    
    return success

def main():
    if len(sys.argv) < 2:
        print("Usage: python replace.py <cloudflared_repo_path> [--verify]")
        print("  <cloudflared_repo_path>: Path to cloned cloudflared repository")
        print("  --verify: Only verify files without replacing")
        sys.exit(1)
    
    cloudflared_repo = Path(sys.argv[1]).resolve()
    verify_only = "--verify" in sys.argv
    
    # Get updates directory (same directory as this script)
    updates_dir = Path(__file__).parent.resolve()
    
    if not cloudflared_repo.exists():
        print(f"Error: Repository path not found: {cloudflared_repo}")
        sys.exit(1)
    
    # Check if it's a valid cloudflared repo
    go_mod = cloudflared_repo / "go.mod"
    if not go_mod.exists():
        print(f"Error: Not a valid Go project (no go.mod): {cloudflared_repo}")
        sys.exit(1)
    
    print(f"Cloudflared repo: {cloudflared_repo}")
    print(f"Updates dir: {updates_dir}")
    print("-" * 50)
    
    if replace_files(cloudflared_repo, updates_dir, verify_only):
        print("-" * 50)
        if verify_only:
            print("Verification complete.")
        else:
            print("All files replaced successfully!")
            print("\nNext step: Build with -buildmode=c-shared")
    else:
        print("Some operations failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
