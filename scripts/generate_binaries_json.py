#!/usr/bin/env python3
"""
Generate bin.json file containing metadata for all binary files in the binaries directory.
This script creates a JSON file with platform-specific binary information including:
- File links (GitHub raw URLs)
- SHA256 checksums
- MD5 checksums
- File sizes
"""

import os
import json
import hashlib
from pathlib import Path

# Repository information
REPO_OWNER = "QudsLab"
REPO_NAME = "Cloudflared"
BRANCH = "main"  # Change to "master" if that's your default branch
BASE_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/binaries"

def calculate_file_hash(filepath, algorithm='sha256'):
    """Calculate hash of a file."""
    hash_obj = hashlib.new(algorithm)
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

def get_file_size(filepath):
    """Get file size in bytes."""
    return os.path.getsize(filepath)

def read_checksum_file(filepath, filename):
    """Read checksum from MD5SUMS.txt or SHA256SUMS.txt file."""
    try:
        with open(filepath, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == filename:
                    return parts[0]
    except FileNotFoundError:
        return None
    return None

def generate_binaries_json():
    """Generate bin.json file with binary metadata."""
    binaries_dir = Path('binaries')
    
    if not binaries_dir.exists():
        print("Error: binaries directory not found")
        return
    
    platforms_data = {}
    
    # Iterate through each platform directory
    for platform_dir in sorted(binaries_dir.iterdir()):
        if not platform_dir.is_dir():
            continue
        
        platform_name = platform_dir.name
        files_data = []
        
        # Find binary files (exclude checksum files)
        binary_files = [f for f in platform_dir.iterdir() 
                       if f.is_file() and f.name not in ['MD5SUMS.txt', 'SHA256SUMS.txt']]
        
        md5_file = platform_dir / 'MD5SUMS.txt'
        sha256_file = platform_dir / 'SHA256SUMS.txt'
        
        for binary_file in sorted(binary_files):
            filename = binary_file.name
            
            # Read checksums from files
            sha256 = read_checksum_file(sha256_file, filename)
            md5 = read_checksum_file(md5_file, filename)
            
            # Calculate checksums if not found in files
            if sha256 is None:
                sha256 = calculate_file_hash(binary_file, 'sha256')
            if md5 is None:
                md5 = calculate_file_hash(binary_file, 'md5')
            
            # Get file size
            size = get_file_size(binary_file)
            
            # Create GitHub raw URL
            file_url = f"{BASE_URL}/{platform_name}/{filename}"
            
            file_info = {
                "filename": filename,
                "url": file_url,
                "sha256": sha256,
                "md5": md5,
                "size": size
            }
            
            files_data.append(file_info)
        
        platforms_data[platform_name] = {
            "files": files_data
        }
    
    # Create final JSON structure
    output = {
        "repository": f"https://github.com/{REPO_OWNER}/{REPO_NAME}",
        "platforms": platforms_data
    }
    
    # Write to bin.json in repository root
    output_file = Path('bin.json')
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✓ Generated {output_file} with {len(platforms_data)} platforms")
    
    # Print summary
    total_files = sum(len(p['files']) for p in platforms_data.values())
    print(f"✓ Total files: {total_files}")
    print(f"✓ Platforms: {', '.join(sorted(platforms_data.keys()))}")

if __name__ == '__main__':
    generate_binaries_json()