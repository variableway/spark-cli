package git

import (
	"fmt"
	"spark/internal/git"

	"github.com/spf13/cobra"
)

var urlCmd = &cobra.Command{
	Use:   "url [repo-path]",
	Short: "Get the git remote URL of the current repository",
	Long: `Get the git remote URL of the current repository.

This command reads the .git/config file and extracts the remote origin URL.
If no path is provided, it uses the current directory.`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		repoPath := "."
		if len(args) > 0 {
			repoPath = args[0]
		}

		url, err := git.GetRemoteURL(repoPath)
		if err != nil {
			return fmt.Errorf("failed to get remote URL: %w", err)
		}

		fmt.Println(url)
		return nil
	},
}

func init() {
	GitCmd.AddCommand(urlCmd)
}
