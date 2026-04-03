package git

import (
	"fmt"
	"spark/internal/git"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var gitcodeURL string

var gitCodeCmd = &cobra.Command{
	Use:   "gitcode",
	Short: "Add Gitcode as a remote to repositories",
	Long: `Add Gitcode as a remote to existing GitHub repositories.
This command will:
1. Find all git repositories in the specified paths
2. For each repository with a GitHub origin, add Gitcode as another remote
3. The Gitcode URL is auto-generated from the GitHub URL by replacing github.com with gitcode.com`,
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
			if err := addGitcodeRemote(repo); err != nil {
				fmt.Printf("  Error: %v\n", err)
			}
			fmt.Println()
		}

		return nil
	},
}

func addGitcodeRemote(repoPath string) error {
	hasGitcode, err := git.HasRemote(repoPath, "gitcode")
	if err != nil {
		return err
	}
	if hasGitcode {
		fmt.Println("  Gitcode remote already exists, skipping...")
		return nil
	}

	originURL, err := git.GetRemoteURL(repoPath)
	if err != nil {
		return fmt.Errorf("failed to get origin URL: %w", err)
	}

	var gitcodeRemoteURL string
	if gitcodeURL != "" {
		gitcodeRemoteURL = gitcodeURL
	} else {
		gitcodeRemoteURL = git.ConvertGitHubToGitcode(originURL)
	}

	fmt.Printf("  Origin:   %s\n", originURL)
	fmt.Printf("  Gitcode:  %s\n", gitcodeRemoteURL)

	if err := git.AddRemote(repoPath, "gitcode", gitcodeRemoteURL); err != nil {
		return err
	}

	fmt.Println("  Successfully added gitcode remote!")
	return nil
}

func init() {
	GitCmd.AddCommand(gitCodeCmd)
	gitCodeCmd.Flags().StringVar(&gitcodeURL, "url", "", "Custom Gitcode URL (default: auto-convert from GitHub URL)")
}
