"""Cloudflared Tunnel Manager - Silent DLL with URL capture"""

import ctypes
import ctypes.wintypes
import sys
import os
import time
import threading
import re

tunnel_url = None
lib = None
running = False


def start_tunnel(dll_path, port=5000, timeout=60):
    """Start tunnel with output capture using ConPTY or pipe redirection."""
    global tunnel_url, lib, running
    
    if not os.path.exists(dll_path):
        print(f"[ERROR] DLL not found: {dll_path}")
        return None
    
    print(f"[TUNNEL] Starting on port {port}...")
    
    # Create pipes for capturing output
    kernel32 = ctypes.windll.kernel32
    
    # Create anonymous pipe
    read_handle = ctypes.wintypes.HANDLE()
    write_handle = ctypes.wintypes.HANDLE()
    
    sa = ctypes.c_void_p()
    
    if not kernel32.CreatePipe(
        ctypes.byref(read_handle),
        ctypes.byref(write_handle),
        sa,
        0
    ):
        print("[ERROR] Failed to create pipe")
        return None
    
    # Set write handle as stdout/stderr
    STD_OUTPUT_HANDLE = -11
    STD_ERROR_HANDLE = -12
    
    old_stdout = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    old_stderr = kernel32.GetStdHandle(STD_ERROR_HANDLE)
    
    kernel32.SetStdHandle(STD_OUTPUT_HANDLE, write_handle)
    kernel32.SetStdHandle(STD_ERROR_HANDLE, write_handle)
    
    # Also set C runtime handles
    try:
        msvcrt = ctypes.CDLL('msvcrt')
        
        # Open write end as file descriptor
        import msvcrt as ms
        write_fd = ms.open_osfhandle(write_handle, 0)
        
        # Redirect fd 1 and 2
        os.dup2(write_fd, 1)
        os.dup2(write_fd, 2)
    except:
        pass
    
    # Load DLL
    lib = ctypes.CDLL(dll_path)
    lib.CloudflaredInit.restype = ctypes.c_int
    lib.CloudflaredRun.argtypes = [ctypes.c_char_p]
    lib.CloudflaredRun.restype = ctypes.c_int
    lib.CloudflaredStop.restype = ctypes.c_int
    
    lib.CloudflaredInit()
    
    # Reader thread
    url_pattern = re.compile(r'https://[a-z0-9\-]+\.trycloudflare\.com')
    url_found = threading.Event()
    
    def reader():
        global tunnel_url
        
        buffer = ctypes.create_string_buffer(4096)
        bytes_read = ctypes.wintypes.DWORD()
        
        collected = ""
        
        while running:
            success = kernel32.ReadFile(
                read_handle,
                buffer,
                4096,
                ctypes.byref(bytes_read),
                None
            )
            
            if success and bytes_read.value > 0:
                text = buffer.raw[:bytes_read.value].decode('utf-8', errors='ignore')
                collected += text
                
                match = url_pattern.search(collected)
                if match and not tunnel_url:
                    tunnel_url = match.group(0)
                    url_found.set()
            else:
                time.sleep(0.1)
    
    running = True
    read_thread = threading.Thread(target=reader, daemon=True)
    read_thread.start()
    
    # Run tunnel
    def run():
        args = f"cloudflared tunnel --url http://localhost:{port} --protocol http2"
        lib.CloudflaredRun(args.encode())
    
    run_thread = threading.Thread(target=run, daemon=True)
    run_thread.start()
    
    # Wait for URL
    if url_found.wait(timeout=timeout):
        print(f"[TUNNEL] URL: {tunnel_url}")
        
        # Now redirect to NUL to silence
        nul = kernel32.CreateFileW(
            "NUL", 0x40000000, 3, None, 3, 0, None
        )
        kernel32.SetStdHandle(STD_OUTPUT_HANDLE, nul)
        kernel32.SetStdHandle(STD_ERROR_HANDLE, nul)
        
        return tunnel_url
    
    print("[TUNNEL] Timeout waiting for URL")
    return None


def stop_tunnel():
    """Stop tunnel."""
    global running, lib
    running = False
    if lib:
        try:
            lib.CloudflaredStop()
        except:
            pass
    print("[TUNNEL] Stopped")


if __name__ == "__main__":
    # DLL_PATH = r"C:\Users\Unkn0\Desktop\VScode\Python.py\Cloudflared\binaries\windows-amd64\cloudflared-windows-amd64.dll"
    # get current script directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    DLL_PATH = os.path.join(current_dir, "binaries", "windows-amd64", "cloudflared-windows-amd64.dll")
    try:
        url = start_tunnel(DLL_PATH, port=5000, timeout=60)
        
        if url:
            print(f"[TUNNEL] Running: {url}")
        else:
            print("[TUNNEL] Running (URL not captured)")
        
        print("[TUNNEL] Press Ctrl+C to stop")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print()
        stop_tunnel()