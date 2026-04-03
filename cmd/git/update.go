package git

import (
	"fmt"
	"spark/internal/git"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var updateCmd = &cobra.Command{
	Use:   "update",
	Short: "Update all git repositories to the latest version",
	Long:  `Scan the specified directory for git repositories and update each one to the latest version.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		paths := viper.GetStringSlice("repo-path")

		var allRepos []string
		for _, path := range paths {
			fmt.Printf("Scanning for git repositories in: %s\n", path)
			repos, err := git.FindRepositories(path)
			if err != nil {
				fmt.Printf("Warning: failed to find repositories in %s: %v\n", path, err)
				continue
			}
			allRepos = append(allRepos, repos...)
		}

		if len(allRepos) == 0 {
			fmt.Println("No git repositories found.")
			return nil
		}

		repoMap := make(map[string]bool)
		var uniqueRepos []string
		for _, repo := range allRepos {
			if !repoMap[repo] {
				repoMap[repo] = true
				uniqueRepos = append(uniqueRepos, repo)
			}
		}

		fmt.Printf("Found %d unique repository(s)\n\n", len(uniqueRepos))

		for _, repo := range uniqueRepos {
			fmt.Printf("Updating: %s\n", repo)
			if err := git.UpdateRepository(repo); err != nil {
				fmt.Printf("  Error: %v\n", err)
			} else {
				fmt.Printf("  Success!\n")
			}
			fmt.Println()
		}

		return nil
	},
}

func init() {
	GitCmd.AddCommand(updateCmd)
}
