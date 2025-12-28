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
)

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

func main() {}
