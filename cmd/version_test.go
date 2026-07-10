package cmd

import (
	"bytes"
	"strings"
	"testing"

	"spark/internal/witr/version"

	"github.com/spf13/cobra"
)

func TestRootCmdHasVersionSubcommand(t *testing.T) {
	found := false
	for _, c := range rootCmd.Commands() {
		if c.Name() == "version" {
			found = true
			break
		}
	}
	if !found {
		t.Fatal("expected rootCmd to register a 'version' subcommand")
	}
}

func TestRootCmdVersionIsSet(t *testing.T) {
	if rootCmd.Version == "" {
		t.Fatal("expected rootCmd.Version to be set from internal/witr/version")
	}
	if version.Version == "" {
		t.Fatal("expected version.Version to be populated (fallback to embedded VERSION file)")
	}
}

func TestVersionCmdPrintsVersionInfo(t *testing.T) {
	buf := &bytes.Buffer{}
	rootCmd.SetOut(buf)
	rootCmd.SetErr(buf)
	rootCmd.SetArgs([]string{"version"})

	if err := rootCmd.Execute(); err != nil {
		t.Fatalf("rootCmd.Execute(version) returned error: %v", err)
	}

	out := buf.String()
	if !strings.Contains(out, "spark") {
		t.Errorf("expected output to mention 'spark', got %q", out)
	}
	if !strings.Contains(out, version.Version) {
		t.Errorf("expected output to include version %q, got %q", version.Version, out)
	}
	if !strings.Contains(out, version.Commit) {
		t.Errorf("expected output to include commit %q, got %q", version.Commit, out)
	}
	if !strings.Contains(out, version.BuildDate) {
		t.Errorf("expected output to include build date %q, got %q", version.BuildDate, out)
	}
}

func findCmd(t *testing.T, root *cobra.Command, name string) *cobra.Command {
	t.Helper()
	for _, c := range root.Commands() {
		if c.Name() == name {
			return c
		}
	}
	t.Fatalf("subcommand %q not found", name)
	return nil
}
