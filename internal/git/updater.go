package git

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// UpdateRepository updates a git repository to the latest version
func UpdateRepository(repoPath string) error {
	// Get current branch
	branchCmd := exec.Command("git", "rev-parse", "--abbrev-ref", "HEAD")
	branchCmd.Dir = repoPath
	branch, err := branchCmd.Output()
	if err != nil {
		return fmt.Errorf("failed to get current branch: %w", err)
	}
	currentBranch := strings.TrimSpace(string(branch))

	// Fetch all updates
	fetchCmd := exec.Command("git", "fetch", "--all")
	fetchCmd.Dir = repoPath
	fetchCmd.Stdout = os.Stdout
	fetchCmd.Stderr = os.Stderr
	if err := fetchCmd.Run(); err != nil {
		return fmt.Errorf("failed to fetch: %w", err)
	}

	// Pull the latest changes
	pullCmd := exec.Command("git", "pull", "origin", currentBranch)
	pullCmd.Dir = repoPath
	pullCmd.Stdout = os.Stdout
	pullCmd.Stderr = os.Stderr
	if err := pullCmd.Run(); err != nil {
		return fmt.Errorf("failed to pull: %w", err)
	}

	return nil
}

// GetRemoteURL gets the remote URL of a git repository
func GetRemoteURL(repoPath string) (string, error) {
	cmd := exec.Command("git", "remote", "get-url", "origin")
	cmd.Dir = repoPath
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to get remote URL: %w", err)
	}
	return strings.TrimSpace(string(output)), nil
}

// GetRepoName gets the repository name from the path
func GetRepoName(repoPath string) string {
	return filepath.Base(repoPath)
}

// AddRemote adds a new remote to the repository
func AddRemote(repoPath, name, url string) error {
	cmd := exec.Command("git", "remote", "add", name, url)
	cmd.Dir = repoPath
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to add remote %s: %w", name, err)
	}
	return nil
}

// HasRemote checks if a remote with the given name exists
func HasRemote(repoPath, name string) (bool, error) {
	cmd := exec.Command("git", "remote")
	cmd.Dir = repoPath
	output, err := cmd.Output()
	if err != nil {
		return false, fmt.Errorf("failed to list remotes: %w", err)
	}
	remotes := strings.Split(strings.TrimSpace(string(output)), "\n")
	for _, r := range remotes {
		if r == name {
			return true, nil
		}
	}
	return false, nil
}

// GetRemoteURLByName gets the URL of a specific remote
func GetRemoteURLByName(repoPath, name string) (string, error) {
	cmd := exec.Command("git", "remote", "get-url", name)
	cmd.Dir = repoPath
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to get remote URL for %s: %w", name, err)
	}
	return strings.TrimSpace(string(output)), nil
}

// ConvertGitHubToGitcode converts a GitHub URL to Gitcode URL
func ConvertGitHubToGitcode(githubURL string) string {
	githubURL = strings.Replace(githubURL, "github.com", "gitcode.com", -1)
	githubURL = strings.Replace(githubURL, "github.com:", "gitcode.com:", -1)
	return githubURL
}
