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

func AddChildReposAsSubmodules(rootPath string) error {
	entries, err := os.ReadDir(rootPath)
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

		childPath := filepath.Join(rootPath, entry.Name())
		if !IsGitRepository(childPath) {
			continue
		}

		isGitHub, err := IsGitHubRepo(childPath)
		if err != nil || !isGitHub {
			continue
		}

		url, err := GetRemoteURL(childPath)
		if err != nil {
			fmt.Printf("Warning: skipping %s (no remote URL): %v\n", entry.Name(), err)
			continue
		}

		fmt.Printf("Adding submodule: %s -> %s\n", entry.Name(), url)
		if err := AddSubmodule(rootPath, childPath, url); err != nil {
			fmt.Printf("Warning: failed to add submodule %s: %v\n", entry.Name(), err)
		}
	}

	return nil
}
