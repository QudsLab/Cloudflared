"""Low-level cloudflared tunnel operations - No state management."""
import ctypes
import ctypes.wintypes
import sys
import os
import time
import threading
import re
import subprocess
import signal


def start_tunnel_dll(dll_path, port, timeout, url_callback=None):
    """
    Start tunnel using Windows DLL with pipe capture.
    
    Args:
        dll_path: Path to cloudflared DLL
        port: Local port to tunnel
        timeout: Timeout in seconds
        url_callback: Callback function(url) when URL is found
    
    Returns:
        tuple: (lib_handle, url, reader_thread, running_flag)
    """
    kernel32 = ctypes.windll.kernel32
    
    # Create pipes
    read_handle = ctypes.wintypes.HANDLE()
    write_handle = ctypes.wintypes.HANDLE()
    sa = ctypes.c_void_p()
    
    if not kernel32.CreatePipe(
        ctypes.byref(read_handle),
        ctypes.byref(write_handle),
        sa,
        0
    ):
        return None, None, None, None
    
    # Redirect handles
    STD_OUTPUT_HANDLE = -11
    STD_ERROR_HANDLE = -12
    kernel32.SetStdHandle(STD_OUTPUT_HANDLE, write_handle)
    kernel32.SetStdHandle(STD_ERROR_HANDLE, write_handle)
    
    # Redirect C runtime
    try:
        import msvcrt as ms
        write_fd = ms.open_osfhandle(write_handle, 0)
        os.dup2(write_fd, 1)
        os.dup2(write_fd, 2)
    except:
        pass
    
    # Load DLL
    try:
        lib = ctypes.CDLL(dll_path)
        lib.CloudflaredInit.restype = ctypes.c_int
        lib.CloudflaredRun.argtypes = [ctypes.c_char_p]
        lib.CloudflaredRun.restype = ctypes.c_int
        lib.CloudflaredStop.restype = ctypes.c_int
        lib.CloudflaredInit()
    except:
        return None, None, None, None
    
    # URL capture
    url_pattern = re.compile(r'https://[a-z0-9\-]+\.trycloudflare\.com')
    url_found = threading.Event()
    captured_url = [None]
    running_flag = [True]
    
    def reader():
        buffer = ctypes.create_string_buffer(4096)
        bytes_read = ctypes.wintypes.DWORD()
        collected = ""
        
        while running_flag[0]:
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
                if match and not captured_url[0]:
                    captured_url[0] = match.group(0)
                    if url_callback:
                        url_callback(captured_url[0])
                    url_found.set()
            else:
                time.sleep(0.1)
    
    read_thread = threading.Thread(target=reader, daemon=True)
    read_thread.start()
    
    # Run tunnel
    def run():
        args = f"cloudflared tunnel --url http://localhost:{port} --protocol http2"
        try:
            lib.CloudflaredRun(args.encode())
        except:
            pass
    
    run_thread = threading.Thread(target=run, daemon=True)
    run_thread.start()
    
    # Wait for URL
    if url_found.wait(timeout=timeout):
        # Silence output
        nul = kernel32.CreateFileW("NUL", 0x40000000, 3, None, 3, 0, None)
        kernel32.SetStdHandle(STD_OUTPUT_HANDLE, nul)
        kernel32.SetStdHandle(STD_ERROR_HANDLE, nul)
        return lib, captured_url[0], read_thread, running_flag
    
    running_flag[0] = False
    return lib, None, read_thread, running_flag


def start_tunnel_subprocess(binary_path, port, timeout, url_callback=None):
    """
    Start tunnel using subprocess.
    
    Args:
        binary_path: Path to cloudflared binary
        port: Local port to tunnel
        timeout: Timeout in seconds
        url_callback: Callback function(url) when URL is found
    
    Returns:
        tuple: (process, url)
    """
    cmd = [
        binary_path,
        "tunnel",
        "--url", f"http://localhost:{port}",
        "--protocol", "http2"
    ]
    
    try:
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            creationflags=creationflags
        )
        
        url_found = threading.Event()
        captured_url = [None]
        url_pattern = re.compile(r'https://[a-z0-9\-]+\.trycloudflare\.com')
        
        def monitor():
            try:
                for line in process.stderr:
                    match = url_pattern.search(line)
                    if match and not captured_url[0]:
                        captured_url[0] = match.group(0)
                        if url_callback:
                            url_callback(captured_url[0])
                        url_found.set()
                        break
                # Continue consuming silently
                for line in process.stderr:
                    pass
            except:
                pass
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        
        if url_found.wait(timeout=timeout):
            return process, captured_url[0]
        
        return process, None
        
    except:
        return None, None


def stop_tunnel_dll(lib_handle, running_flag):
    """Stop DLL-based tunnel."""
    if running_flag:
        running_flag[0] = False
    
    if lib_handle:
        try:
            lib_handle.CloudflaredStop()
        except:
            pass


def stop_tunnel_subprocess(process):
    """Stop subprocess-based tunnel."""
    if not process:
        return
    
    try:
        if sys.platform == "win32":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.terminate()
        
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    except:
        pass