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

	entries, err := os.ReadDir(absFolder)
	if err != nil {
		return fmt.Errorf("failed to read directory: %w", err)
	}

	var repos []string
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

	if len(repos) == 0 {
		fmt.Println("No GitHub repositories found in the specified folder.")
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
		if err := addLocalRepoAsSubmodule(repoPath, repo, url); err != nil {
			fmt.Printf("Warning: failed to add %s: %v\n", name, err)
		}
	}

	fmt.Println("\nDone! To commit: git commit -m 'Add submodules'")
	return nil
}

func addLocalRepoAsSubmodule(parentPath, childPath, remoteURL string) error {
	childName := filepath.Base(childPath)

	gitmodulesPath := filepath.Join(parentPath, ".gitmodules")

	modulesDir := filepath.Join(parentPath, ".git", "modules", childName)
	if err := os.MkdirAll(modulesDir, 0755); err != nil {
		return fmt.Errorf("failed to create modules dir: %w", err)
	}

	gitEntry := filepath.Join(childPath, ".git")
	if info, err := os.Lstat(gitEntry); err == nil && !info.IsDir() {
		fmt.Printf("Skipping %s: already a submodule\n", childName)
		return nil
	}

	for _, item := range []string{"config", "description", "hooks", "info", "logs", "objects", "refs"} {
		src := filepath.Join(gitEntry, item)
		if _, err := os.Stat(src); err == nil {
			dst := filepath.Join(modulesDir, item)
			os.Rename(src, dst)
		}
	}

	for _, item := range []string{"HEAD", "index", "packed-refs"} {
		src := filepath.Join(gitEntry, item)
		if _, err := os.Stat(src); err == nil {
			dst := filepath.Join(modulesDir, item)
			os.Rename(src, dst)
		}
	}
	os.Remove(gitEntry)

	relPath := filepath.Join("..", ".git", "modules", childName)
	os.WriteFile(gitEntry, []byte("gitdir: "+relPath+"\n"), 0644)

	submoduleConfig := filepath.Join(modulesDir, "config")
	worktree := filepath.Join("..", "..", "..", childName)
	exec.Command("git", "config", "--file", submoduleConfig, "core.worktree", worktree).Run()

	setPath := exec.Command("git", "config", "--file", gitmodulesPath, fmt.Sprintf("submodule.%s.path", childName), childName)
	setPath.Dir = parentPath
	setPath.Stdout = os.Stdout
	setPath.Stderr = os.Stderr
	setPath.Run()

	setURL := exec.Command("git", "config", "--file", gitmodulesPath, fmt.Sprintf("submodule.%s.url", childName), remoteURL)
	setURL.Dir = parentPath
	setURL.Stdout = os.Stdout
	setURL.Stderr = os.Stderr
	setURL.Run()

	exec.Command("git", "add", childName).Run()

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
	submoduleCmd.Flags().StringVarP(&submodulePath, "name", "n", "", "Custom name/path for the submodule (URL mode only)")

	GitCmd.AddCommand(submoduleCmd)
}
