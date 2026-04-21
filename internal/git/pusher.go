package git

import (
	"fmt"
	"os"
	"os/exec"
	"strings"
)

// HasChanges checks if a repository has uncommitted changes
func HasChanges(repoPath string) (bool, error) {
	cmd := exec.Command("git", "status", "--porcelain")
	cmd.Dir = repoPath
	output, err := cmd.Output()
	if err != nil {
		return false, fmt.Errorf("failed to check status: %w", err)
	}
	return len(strings.TrimSpace(string(output))) > 0, nil
}

// IsGitHubRepo checks if a repository has a GitHub remote
func IsGitHubRepo(repoPath string) (bool, error) {
	url, err := GetRemoteURL(repoPath)
	if err != nil {
		return false, err
	}
	return strings.Contains(url, "github.com"), nil
}

// PushRepository stages, commits, and pushes all changes in a repository.
// It returns an error if the push fails due to a conflict or other issue.
func PushRepository(repoPath string) error {
	// Stage all changes
	addCmd := exec.Command("git", "add", ".")
	addCmd.Dir = repoPath
	addCmd.Stdout = os.Stdout
	addCmd.Stderr = os.Stderr
	if err := addCmd.Run(); err != nil {
		return fmt.Errorf("failed to add changes: %w", err)
	}

	// Commit changes
	commitCmd := exec.Command("git", "commit", "-m", "chore: update via spark push-all")
	commitCmd.Dir = repoPath
	commitCmd.Stdout = os.Stdout
	commitCmd.Stderr = os.Stderr
	if err := commitCmd.Run(); err != nil {
		return fmt.Errorf("failed to commit: %w", err)
	}

	// Push changes
	pushCmd := exec.Command("git", "push", "origin")
	pushCmd.Dir = repoPath
	pushCmd.Stdout = os.Stdout
	pushCmd.Stderr = os.Stderr
	if err := pushCmd.Run(); err != nil {
		return fmt.Errorf("failed to push: %w", err)
	}

	return nil
}
