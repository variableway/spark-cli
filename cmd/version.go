package cmd

import (
	"fmt"
	"runtime/debug"

	"spark/internal/witr/version"

	"github.com/spf13/cobra"
)

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print spark version information",
	Long: `Print the spark binary version, source commit, and build date.

Useful for confirming that the spark binary on PATH matches the latest source build.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		out := cmd.OutOrStdout()
		fmt.Fprintf(out, "spark %s\n", version.Version)
		fmt.Fprintf(out, "  commit:     %s\n", version.Commit)
		fmt.Fprintf(out, "  build date: %s\n", version.BuildDate)
		if vcsTime, vcsDirty := readVCSTime(); vcsTime != "" {
			fmt.Fprintf(out, "  vcs.time:   %s%s\n", vcsTime, dirtyMark(vcsDirty))
		}
		return nil
	},
}

func readVCSTime() (string, bool) {
	info, ok := debug.ReadBuildInfo()
	if !ok {
		return "", false
	}
	var vcsTime, vcsRevision string
	var vcsDirty bool
	for _, s := range info.Settings {
		switch s.Key {
		case "vcs.time":
			vcsTime = s.Value
		case "vcs.revision":
			vcsRevision = s.Value
		case "vcs.modified":
			vcsDirty = s.Value == "true"
		}
	}
	if vcsTime == "" && vcsRevision != "" {
		return vcsRevision[:min(7, len(vcsRevision))], vcsDirty
	}
	return vcsTime, vcsDirty
}

func dirtyMark(dirty bool) string {
	if dirty {
		return " (dirty)"
	}
	return ""
}

func init() {
	rootCmd.AddCommand(versionCmd)
	rootCmd.Version = version.Version
}
