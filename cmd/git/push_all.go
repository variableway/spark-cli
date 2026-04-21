package git

import (
	"fmt"
	"spark/internal/git"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var pushAllCmd = &cobra.Command{
	Use:   "push-all",
	Short: "Commit and push all changes in repositories",
	Long: `Scan the specified directories for git repositories and commit/push all changes.

For each repository:
- Skip if it's not a GitHub repository
- Skip if there are no changes to commit
- Stage all changes, commit, and push to origin
- If a conflict or error occurs, prompt the user and continue with the next repository`,
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
			fmt.Printf("Processing: %s\n", repo)

			isGitHub, err := git.IsGitHubRepo(repo)
			if err != nil {
				fmt.Printf("  Error checking remote: %v\n", err)
				fmt.Println()
				continue
			}
			if !isGitHub {
				fmt.Println("  Not a GitHub repository, skipping...")
				fmt.Println()
				continue
			}

			hasChanges, err := git.HasChanges(repo)
			if err != nil {
				fmt.Printf("  Error checking changes: %v\n", err)
				fmt.Println()
				continue
			}
			if !hasChanges {
				fmt.Println("  No changes to commit, skipping...")
				fmt.Println()
				continue
			}

			if err := git.PushRepository(repo); err != nil {
				fmt.Printf("  Error: %v\n", err)
				fmt.Println("  Please resolve the conflict manually and re-run the command.")
			} else {
				fmt.Println("  Success!")
			}
			fmt.Println()
		}

		return nil
	},
}

func init() {
	GitCmd.AddCommand(pushAllCmd)
}
