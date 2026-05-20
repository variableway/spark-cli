package git

import (
	"fmt"
	"os"
	"os/exec"

	"github.com/spf13/cobra"
)

var syncCmd = &cobra.Command{
	Use:   "sync",
	Short: "Sync all submodules to their latest versions",
	Long: `Update all submodules in the current repository to the latest versions.

Fetches the latest changes and merges them into the current branch.

Examples:
  spark git sync              # sync current directory
  spark git sync ./my-repo    # sync specific repo`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		repoPath := "."
		if len(args) > 0 {
			repoPath = args[0]
		}

		fmt.Printf("Fetching all remotes...\n")
		fetchCmd := exec.Command("git", "fetch", "--all")
		fetchCmd.Dir = repoPath
		fetchCmd.Stdout = os.Stdout
		fetchCmd.Stderr = os.Stderr
		fetchCmd.Run()

		fmt.Printf("Initializing missing submodules...\n")
		initCmd := exec.Command("git", "submodule", "update", "--init")
		initCmd.Dir = repoPath
		initCmd.Stdout = os.Stdout
		initCmd.Stderr = os.Stderr
		initCmd.Run()

		fmt.Printf("Updating submodules to latest versions...\n")
		updateCmd := exec.Command("git", "submodule", "update", "--remote", "--merge")
		updateCmd.Dir = repoPath
		updateCmd.Stdout = os.Stdout
		updateCmd.Stderr = os.Stderr
		if err := updateCmd.Run(); err != nil {
			return fmt.Errorf("failed to update submodules: %w", err)
		}

		fmt.Println("All submodules synced!")
		return nil
	},
}

func init() {
	GitCmd.AddCommand(syncCmd)
}
