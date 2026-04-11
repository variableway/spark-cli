package git

import (
	"fmt"
	"spark/internal/mono"
	"strings"

	"github.com/spf13/cobra"
)

var monoAddPath string
var monoAddURL string
var monoAddName string

var monoAddCmd = &cobra.Command{
	Use:   "add [flags] [repo-url]",
	Short: "Add git repos as submodules",
	Long: `Add git repositories as submodules to the current mono repo.

Supports two modes:

1. Add existing local repos as submodules (default):
   Scans the specified directory for git repositories and adds them as submodules
   without re-cloning. This preserves the existing folder structure.

2. Add a remote repository as a submodule:
   Clones a remote git repository and adds it as a submodule using git submodule add.
   The submodule path defaults to the repository name, or can be specified with --name.

Examples:
  # Add all local git repos in current directory as submodules
  spark git mono add

  # Add all local git repos from a specific directory
  spark git mono add -p /path/to/repos

  # Add a remote repository as submodule
  spark git mono add https://github.com/user/repo

  # Add a remote repository with custom path
  spark git mono add https://github.com/user/repo --name my-folder`,
	RunE: func(cmd *cobra.Command, args []string) error {
		// Check if a remote URL is provided as argument or flag
		var repoURL string
		if len(args) > 0 {
			repoURL = args[0]
		} else if monoAddURL != "" {
			repoURL = monoAddURL
		}

		// Remote URL mode
		if repoURL != "" {
			// Validate it looks like a git URL
			if !isValidGitURL(repoURL) {
				return fmt.Errorf("invalid git URL: %s", repoURL)
			}
			
			targetDir := monoAddPath
			if targetDir == "" {
				targetDir = "."
			}
			
			if err := mono.AddRemoteRepoAsSubmodule(targetDir, repoURL, monoAddName); err != nil {
				return fmt.Errorf("failed to add remote submodule: %w", err)
			}
			
			fmt.Println("\nSubmodule added successfully!")
			fmt.Println("To commit: git commit -m \"Add submodule\"")
			fmt.Println("To sync later: spark git mono sync .")
			return nil
		}

		// Local directory mode (existing behavior)
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

// isValidGitURL checks if the string looks like a valid git URL
func isValidGitURL(url string) bool {
	// Check for common git URL patterns
	if strings.HasPrefix(url, "https://") || strings.HasPrefix(url, "http://") {
		return true
	}
	if strings.HasPrefix(url, "git@") {
		return true
	}
	if strings.HasPrefix(url, "git://") {
		return true
	}
	if strings.HasPrefix(url, "ssh://") {
		return true
	}
	// Allow simple user/repo format for GitHub
	if strings.Count(url, "/") == 1 && !strings.Contains(url, " ") {
		return true
	}
	return false
}

func init() {
	MonoCmd.AddCommand(monoAddCmd)
	monoAddCmd.Flags().StringVarP(&monoAddPath, "path", "p", "", "Directory containing git repos to add as submodules (default: current directory)")
	monoAddCmd.Flags().StringVarP(&monoAddURL, "url", "u", "", "Remote git repository URL to add as submodule")
	monoAddCmd.Flags().StringVarP(&monoAddName, "name", "n", "", "Custom name/path for the submodule (default: repo name from URL)")
}
