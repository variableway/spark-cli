package git

import (
	"fmt"
	"spark/internal/mono"

	"github.com/spf13/cobra"
)

var monoAddPath string

var monoAddCmd = &cobra.Command{
	Use:   "add [flags]",
	Short: "Add existing git repos in current folder as submodules",
	Long: `Add existing git repositories in the current folder as git submodules
without re-cloning them. This converts the current folder into a mono repo.

The command scans for git repositories in the specified directory and adds
each one as a submodule, preserving the existing folder structure and content.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		targetDir := monoAddPath
		if targetDir == "" {
			targetDir = "."
		}

		repos, err := mono.FindSubRepos(targetDir)
		if err != nil {
			return fmt.Errorf("failed to scan for repos: %w", err)
		}

		if len(repos) == 0 {
			fmt.Println("No git repositories found in the specified directory.")
			return nil
		}

		fmt.Printf("Found %d git repository(s)\n", len(repos))
		fmt.Println("Adding as submodules...")

		if err := mono.AddExistingReposAsSubmodules(targetDir, repos); err != nil {
			return fmt.Errorf("failed to add submodules: %w", err)
		}

		fmt.Println("\nSubmodules added successfully!")
		fmt.Println("To commit: git commit -m \"Add submodules\"")
		fmt.Println("To sync later: spark git mono sync .")

		return nil
	},
}

func init() {
	MonoCmd.AddCommand(monoAddCmd)
	monoAddCmd.Flags().StringVarP(&monoAddPath, "path", "p", "", "Directory containing git repos to add as submodules (default: current directory)")
}
