package git

import (
	"fmt"
	"spark/internal/git"
	"spark/internal/mono"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var (
	monoRepoName string
	outputPath   string
)

var createCmd = &cobra.Command{
	Use:   "create",
	Short: "Create a mono repo with all repositories as submodules",
	Long:  `Create a new mono repository that contains all found git repositories as submodules.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		paths := viper.GetStringSlice("repo-path")

		if monoRepoName == "" {
			monoRepoName = "mono-repo"
		}

		if outputPath == "" {
			outputPath = "."
		}

		monoRepoPath := filepath.Join(outputPath, monoRepoName)

		var allRepos []string
		for _, path := range paths {
			fmt.Printf("Scanning for git repositories in: %s\n", path)
			repos, err := git.FindRepositories(path)
			if err != nil {
				fmt.Printf("Warning: failed to scan path %s: %v\n", path, err)
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

		fmt.Printf("Found %d unique repository(s)\n", len(uniqueRepos))

		if _, err := os.Stat(monoRepoPath); !os.IsNotExist(err) {
			return fmt.Errorf("mono repo already exists: %s", monoRepoPath)
		}

		fmt.Printf("\nCreating mono repo at: %s\n", monoRepoPath)

		if err := mono.CreateMonoRepo(monoRepoPath, uniqueRepos); err != nil {
			return fmt.Errorf("failed to create mono repo: %w", err)
		}

		fmt.Println("\nMono repo created successfully!")
		fmt.Printf("Location: %s\n", monoRepoPath)
		fmt.Println("\nTo update all submodules, run:")
		fmt.Printf("  cd %s && git submodule update --remote --merge\n", monoRepoPath)

		return nil
	},
}

func init() {
	GitCmd.AddCommand(createCmd)
	createCmd.Flags().StringVarP(&monoRepoName, "name", "n", "mono-repo", "Name of the mono repo directory")
	createCmd.Flags().StringVarP(&outputPath, "output", "o", "", "Output path for the mono repo (default: same as source path)")
}
