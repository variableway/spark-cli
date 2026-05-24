package git

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

func InitRepo(repoPath string) error {
	cmd := exec.Command("git", "init")
	cmd.Dir = repoPath
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to init git repository: %w", err)
	}
	return nil
}

func AddSubmodule(repoPath, submodulePath, submoduleURL string) error {
	relPath, err := filepath.Rel(repoPath, submodulePath)
	if err != nil {
		return fmt.Errorf("failed to get relative path: %w", err)
	}

	cmd := exec.Command("git", "submodule", "add", submoduleURL, relPath)
	cmd.Dir = repoPath
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to add submodule %s: %w", relPath, err)
	}
	return nil
}

func CreateGitHubRepo(repoPath, owner, name string, private bool) error {
	visibility := "--public"
	if private {
		visibility = "--private"
	}

	args := []string{"repo", "create", fmt.Sprintf("%s/%s", owner, name), visibility, "--source=.", "--push"}
	cmd := exec.Command("gh", args...)
	cmd.Dir = repoPath
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to create GitHub repository: %w", err)
	}
	return nil
}

func WriteGitIgnore(repoPath string) error {
	content := `# Dependencies
node_modules/
vendor/

# Build output
dist/
build/
*.exe
*.dll
*.so
*.dylib

# IDE
.vscode/
.idea/

# Environment
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/

# Go
*.out

# OS
.DS_Store
Thumbs.db

# Test
coverage/
*.log
`
	gitignorePath := filepath.Join(repoPath, ".gitignore")
	return os.WriteFile(gitignorePath, []byte(content), 0644)
}

func InitialCommit(repoPath, message string) error {
	addCmd := exec.Command("git", "add", ".")
	addCmd.Dir = repoPath
	addCmd.Stdout = os.Stdout
	addCmd.Stderr = os.Stderr
	if err := addCmd.Run(); err != nil {
		return fmt.Errorf("failed to stage files: %w", err)
	}

	commitCmd := exec.Command("git", "commit", "-m", message)
	commitCmd.Dir = repoPath
	commitCmd.Stdout = os.Stdout
	commitCmd.Stderr = os.Stderr
	if err := commitCmd.Run(); err != nil {
		return fmt.Errorf("failed to commit: %w", err)
	}

	return nil
}

// maxSubmoduleDepth controls how deep we scan for git repos to add as submodules.
const maxSubmoduleDepth = 3

// AddChildReposAsSubmodules scans the root path recursively (up to maxSubmoduleDepth)
// for git repositories with GitHub remotes, and adds them as submodules.
// This handles nested structures like projects/innate-ai-art in addition to
// top-level repos like spark-cli.
func AddChildReposAsSubmodules(rootPath string) error {
	repos := findChildGitHubRepos(rootPath, 0)

	if len(repos) == 0 {
		fmt.Println("No GitHub repositories found to add as submodules.")
		return nil
	}

	fmt.Printf("Found %d GitHub repository(ies) to add as submodules\n", len(repos))

	for _, repo := range repos {
		relPath, err := filepath.Rel(rootPath, repo)
		if err != nil {
			relPath = filepath.Base(repo)
		}

		url, err := GetRemoteURL(repo)
		if err != nil {
			fmt.Printf("Warning: skipping %s (no remote URL): %v\n", relPath, err)
			continue
		}

		fmt.Printf("Adding submodule: %s -> %s\n", relPath, url)
		if err := AddSubmodule(rootPath, repo, url); err != nil {
			fmt.Printf("Warning: failed to add submodule %s: %v\n", relPath, err)
		}
	}

	return nil
}

// findChildGitHubRepos walks the directory tree starting at dirPath (up to
// maxSubmoduleDepth) and returns paths of git repos that have GitHub remotes.
// It skips hidden directories and already-registered submodules.
func findChildGitHubRepos(dirPath string, depth int) []string {
	if depth > maxSubmoduleDepth {
		return nil
	}

	entries, err := os.ReadDir(dirPath)
	if err != nil {
		return nil
	}

	var repos []string

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		if strings.HasPrefix(entry.Name(), ".") {
			continue
		}

		childPath := filepath.Join(dirPath, entry.Name())

		if IsGitRepository(childPath) {
			isGitHub, _ := IsGitHubRepo(childPath)
			if isGitHub {
				url, err := GetRemoteURL(childPath)
				if err == nil {
					// Don't add the parent repo itself as a child
					parentURL, _ := GetRemoteURL(dirPath)
					if url == parentURL {
						continue
					}
				}
				repos = append(repos, childPath)
				continue // don't recurse into a git repo
			}
		}

		// Recurse into non-git directories
		children := findChildGitHubRepos(childPath, depth+1)
		repos = append(repos, children...)
	}

	return repos
}
