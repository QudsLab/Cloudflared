//go:build cgo

package main

/*
#include <stdlib.h>
*/
import "C"
import (
	"strings"
	"sync"
	"unsafe"
)

var (
	globalShutdownC   chan struct{}
	globalMu          sync.Mutex
	globalInitialized bool
	globalStopped     bool
	globalTunnelURL   string
	globalTunnelReady bool
	globalSilentMode  bool
)

//export CloudflaredSetSilentMode
func CloudflaredSetSilentMode(silent C.int) {
	globalMu.Lock()
	defer globalMu.Unlock()
	globalSilentMode = (silent != 0)
}

//export CloudflaredInit
func CloudflaredInit() C.int {
	globalMu.Lock()
	defer globalMu.Unlock()

	if globalInitialized {
		return 1
	}

	globalShutdownC = make(chan struct{})
	globalInitialized = true
	globalStopped = false
	return 0
}

//export CloudflaredRun
func CloudflaredRun(cArgs *C.char) C.int {
	globalMu.Lock()
	if !globalInitialized {
		globalMu.Unlock()
		return -1
	}
	shutdownC := globalShutdownC
	globalMu.Unlock()

	args := strings.Fields(C.GoString(cArgs))
	if len(args) == 0 {
		args = []string{"cloudflared"}
	}

	go func() {
		runAppWithArgs(shutdownC, args)
	}()

	return 0
}

//export CloudflaredRunSync
func CloudflaredRunSync(cArgs *C.char) C.int {
	globalMu.Lock()
	if !globalInitialized {
		globalMu.Unlock()
		return -1
	}
	shutdownC := globalShutdownC
	globalMu.Unlock()

	args := strings.Fields(C.GoString(cArgs))
	if len(args) == 0 {
		args = []string{"cloudflared"}
	}

	runAppWithArgs(shutdownC, args)
	return 0
}

//export CloudflaredStop
func CloudflaredStop() C.int {
	globalMu.Lock()
	defer globalMu.Unlock()

	// Already stopped or not initialized
	if !globalInitialized || globalStopped || globalShutdownC == nil {
		return -1
	}

	// Use recover to prevent panic on double close
	defer func() {
		if r := recover(); r != nil {
			// Channel was already closed, ignore
		}
	}()

	close(globalShutdownC)
	globalShutdownC = nil
	globalInitialized = false
	globalStopped = true
	return 0
}

//export CloudflaredFreeString
func CloudflaredFreeString(s *C.char) {
	C.free(unsafe.Pointer(s))
}

//export CloudflaredVersion
func CloudflaredVersion() *C.char {
	return C.CString(Version)
}

//export CloudflaredGetTunnelURL
func CloudflaredGetTunnelURL() *C.char {
	globalMu.Lock()
	defer globalMu.Unlock()
	
	if globalTunnelURL == "" {
		return nil
	}
	return C.CString(globalTunnelURL)
}

//export CloudflaredGetTunnelStatus
func CloudflaredGetTunnelStatus() C.int {
	globalMu.Lock()
	defer globalMu.Unlock()
	
	// 0 = not started, 1 = starting, 2 = ready
	if !globalInitialized {
		return 0
	}
	if globalTunnelReady {
		return 2
	}
	return 1
}

//export CloudflaredSetTunnelURL
func CloudflaredSetTunnelURL(cURL *C.char) {
	globalMu.Lock()
	defer globalMu.Unlock()
	
	globalTunnelURL = C.GoString(cURL)
	globalTunnelReady = true
}

func main() {}
