package git

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"spark/internal/git"

	"github.com/spf13/cobra"
)

var submodulePath string

var submoduleCmd = &cobra.Command{
	Use:   "submodule",
	Short: "Manage git submodules",
	Long:  `Add git repositories as submodules to the current git repository.`,
}

var submoduleAddCmd = &cobra.Command{
	Use:   "add <path-or-url>",
	Short: "Add git repositories as submodules to the current repo",
	Long: `Add git repositories as submodules to the current git repository.

Two modes:

1. URL mode: Add a remote repository as a submodule
   spark git submodule add https://github.com/owner/repo

2. Folder mode: Scan a local directory and add all GitHub repos as submodules
   spark git submodule add ./path/to/folder

The current directory must be a git repository.`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		target := args[0]
		repoPath := "."

		if !git.IsGitRepository(repoPath) {
			return fmt.Errorf("current directory is not a git repository. Run 'spark git init' first")
		}

		if isGitURL(target) {
			return addRemoteSubmodule(repoPath, target)
		}

		return addFolderAsSubmodules(repoPath, target)
	},
}

func isGitURL(target string) bool {
	if strings.HasPrefix(target, ".") || strings.HasPrefix(target, "/") {
		return false
	}
	return strings.HasPrefix(target, "https://") ||
		strings.HasPrefix(target, "http://") ||
		strings.HasPrefix(target, "git@") ||
		strings.HasPrefix(target, "git://") ||
		strings.HasPrefix(target, "ssh://") ||
		(strings.Count(target, "/") == 1 && !strings.Contains(target, " "))
}

func addRemoteSubmodule(repoPath, url string) error {
	name := submodulePath
	if name == "" {
		name = extractRepoName(url)
	}

	fmt.Printf("Adding submodule: %s (%s)\n", name, url)

	cmd := exec.Command("git", "submodule", "add", "-f", url, name)
	cmd.Dir = repoPath
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to add submodule: %w", err)
	}

	fmt.Println("\nSubmodule added. To commit: git commit -m 'Add submodule'")
	return nil
}

func addFolderAsSubmodules(repoPath, folder string) error {
	absFolder, err := filepath.Abs(folder)
	if err != nil {
		return fmt.Errorf("failed to resolve path: %w", err)
	}

	var repos []string
	alreadyHandled := false

	if git.IsGitRepository(absFolder) {
		isGitHub, _ := git.IsGitHubRepo(absFolder)
		if isGitHub {
			name := filepath.Base(absFolder)
			cmd := exec.Command("git", "ls-files", "--stage", name)
			cmd.Dir = repoPath
			if out, _ := cmd.Output(); len(out) > 0 && strings.HasPrefix(string(out), "160000") {
				fmt.Printf("Skipping %s: already added as a submodule\n", name)
				alreadyHandled = true
			} else {
				url, _ := git.GetRemoteURL(absFolder)
				parentURL, parentErr := git.GetRemoteURL(repoPath)
				if parentErr == nil && url == parentURL {
					fmt.Printf("Skipping %s: same repository as parent\n", name)
					alreadyHandled = true
				} else if _, err := os.Stat(absFolder); err == nil {
					fmt.Printf("Skipping %s: directory already exists (use 'git submodule add' manually)\n", name)
					alreadyHandled = true
				} else {
					repos = append(repos, absFolder)
				}
			}
		}
	}

	if len(repos) == 0 {
		entries, err := os.ReadDir(absFolder)
		if err != nil {
			return fmt.Errorf("failed to read directory: %w", err)
		}

		for _, entry := range entries {
			if !entry.IsDir() {
				continue
			}
			if strings.HasPrefix(entry.Name(), ".") {
				continue
			}

			childPath := filepath.Join(absFolder, entry.Name())
			if !git.IsGitRepository(childPath) {
				continue
			}

			isGitHub, _ := git.IsGitHubRepo(childPath)
			if !isGitHub {
				continue
			}

			repos = append(repos, childPath)
		}
	}

	if len(repos) == 0 {
		if alreadyHandled {
			fmt.Println("\nDone!")
		} else {
			fmt.Println("No GitHub repositories found in the specified folder.")
		}
		return nil
	}

	fmt.Printf("Found %d GitHub repository(ies)\n\n", len(repos))

	for _, repo := range repos {
		name := filepath.Base(repo)
		url, err := git.GetRemoteURL(repo)
		if err != nil {
			fmt.Printf("Warning: skipping %s (no remote URL): %v\n", name, err)
			continue
		}

		fmt.Printf("Adding submodule: %s (%s)\n", name, url)

		cmd := exec.Command("git", "submodule", "add", "-f", url, name)
		cmd.Dir = repoPath
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		if err := cmd.Run(); err != nil {
			fmt.Printf("Warning: failed to add %s: %v\n", name, err)
		}
	}

	fmt.Println("\nDone! To commit: git commit -m 'Add submodules'")
	return nil
}

func extractRepoName(url string) string {
	url = strings.TrimSuffix(url, ".git")
	if strings.Contains(url, "://") {
		parts := strings.Split(url, "/")
		return parts[len(parts)-1]
	}
	if strings.Contains(url, ":") {
		parts := strings.Split(url, ":")
		last := parts[len(parts)-1]
		if strings.Contains(last, "/") {
			parts := strings.Split(last, "/")
			return parts[len(parts)-1]
		}
		return last
	}
	parts := strings.Split(url, "/")
	return parts[len(parts)-1]
}

func init() {
	submoduleAddCmd.Flags().StringVarP(&submodulePath, "name", "n", "", "Custom name/path for the submodule (URL mode only)")

	submoduleCmd.AddCommand(submoduleAddCmd)
	GitCmd.AddCommand(submoduleCmd)
}
