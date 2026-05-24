package git

import (
	"fmt"
	"os"
	"os/exec"

	"spark/internal/git"

	"github.com/spf13/cobra"
)

var syncRecursive bool

var syncCmd = &cobra.Command{
	Use:   "sync",
	Short: "Sync all submodules to their latest versions",
	Long: `Update all submodules in the current repository to the latest versions.

This command:
1. Fetches all remotes for the parent repo
2. Initializes (clones) any uninitialized submodules
3. Updates each submodule to the latest commit on its tracked branch

Examples:
  spark git sync              # sync in current directory
  spark git sync --recursive  # sync nested submodules too`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		repoPath := "."
		if len(args) > 0 {
			repoPath = args[0]
		}

		// 1. Fetch parent remotes
		fmt.Println("Step 1/3: Fetching all remotes...")
		fetchCmd := exec.Command("git", "fetch", "--all")
		fetchCmd.Dir = repoPath
		fetchCmd.Stdout = os.Stdout
		fetchCmd.Stderr = os.Stderr
		fetchCmd.Run() // best-effort

		// 2. Initialize uninitialized submodules
		fmt.Println("\nStep 2/3: Initializing submodules...")
		if err := git.InitAllSubmodules(repoPath, syncRecursive, 1); err != nil {
			fmt.Printf("Warning: some submodules failed to initialize: %v\n", err)
		}

		// 3. Update submodules to latest remote
		fmt.Println("\nStep 3/3: Updating submodules to latest versions...")
		updateArgs := []string{"submodule", "update", "--remote", "--merge"}
		if syncRecursive {
			updateArgs = append(updateArgs, "--recursive")
		}
		updateCmd := exec.Command("git", updateArgs...)
		updateCmd.Dir = repoPath
		updateCmd.Stdout = os.Stdout
		updateCmd.Stderr = os.Stderr
		if err := updateCmd.Run(); err != nil {
			return fmt.Errorf("failed to update submodules: %w", err)
		}

		fmt.Println("\nAll submodules synced!")
		return nil
	},
}

func init() {
	syncCmd.Flags().BoolVarP(&syncRecursive, "recursive", "r", false, "Sync nested submodules recursively")
	GitCmd.AddCommand(syncCmd)
}
