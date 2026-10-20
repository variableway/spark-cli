//go:build windows

package proc

import (
	"os"
	"strings"
	"testing"
)

func TestGetCmdlineSelf(t *testing.T) {
	got := GetCmdline(os.Getpid())
	if got == "" || got == "(unknown)" {
		t.Errorf("GetCmdline(self) = %q, want a non-empty exe basename", got)
	}
	// Under `go test` the binary is <pkg>.test.exe, but the ginkgo CLI builds
	// it as <pkg>.test (no .exe suffix on Windows) — accept both.
	lower := strings.ToLower(got)
	if !strings.HasSuffix(lower, ".exe") && !strings.HasSuffix(lower, ".test") {
		t.Errorf("GetCmdline(self) = %q, expected a .exe or .test suffix", got)
	}
}

func TestGetCmdlineNonexistentPID(t *testing.T) {
	if got := GetCmdline(2147483646); got != "(unknown)" {
		t.Errorf("GetCmdline(large-pid) = %q, want %q", got, "(unknown)")
	}
}
