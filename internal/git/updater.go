package git

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// httpsHost extracts the host from an HTTPS URL, or empty string if not HTTPS.
func httpsHost(url string) string {
	if !strings.HasPrefix(url, "https://") {
		return ""
	}
	withoutScheme := strings.TrimPrefix(url, "https://")
	if idx := strings.Index(withoutScheme, "/"); idx != -1 {
		return withoutScheme[:idx]
	}
	return withoutScheme
}

// UpdateRepository updates a git repository to the latest version.
// When useSSH is true, HTTPS remote URLs are forced to SSH for this
// update via a transient url.insteadOf config override, without modifying the
// repository's configured remote URLs.
func UpdateRepository(repoPath string, useSSH bool) error {
	// Get current branch
	branchCmd := exec.Command("git", "rev-parse", "--abbrev-ref", "HEAD")
	branchCmd.Dir = repoPath
	branch, err := branchCmd.Output()
	if err != nil {
		return fmt.Errorf("failed to get current branch: %w", err)
	}
	currentBranch := strings.TrimSpace(string(branch))

	// Build url.insteadOf overrides for all HTTPS remotes when useSSH is set.
	var sshOverrides []string
	if useSSH {
		remotesCmd := exec.Command("git", "remote")
		remotesCmd.Dir = repoPath
		remotesOut, err := remotesCmd.Output()
		if err == nil {
			for _, remote := range strings.Split(strings.TrimSpace(string(remotesOut)), "\n") {
				if remote == "" {
					continue
				}
				urlCmd := exec.Command("git", "remote", "get-url", remote)
				urlCmd.Dir = repoPath
				urlOut, err := urlCmd.Output()
				if err != nil {
					continue
				}
				remoteURL := strings.TrimSpace(string(urlOut))
				if host := httpsHost(remoteURL); host != "" {
					sshOverrides = append(sshOverrides,
						"-c", fmt.Sprintf("url.git@%s:.insteadOf=https://%s/", host, host))
				}
			}
		}
	}

	// gitArgs builds a git command scoped to the repo, prepending SSH
	// url.insteadOf overrides when useSSH is set.
	gitArgs := func(subcmd ...string) *exec.Cmd {
		args := subcmd
		if len(sshOverrides) > 0 {
			args = append(sshOverrides, args...)
		}
		c := exec.Command("git", args...)
		c.Dir = repoPath
		return c
	}

	// Fetch all updates
	fetchCmd := gitArgs("fetch", "--all")
	fetchCmd.Stdout = os.Stdout
	fetchCmd.Stderr = os.Stderr
	if err := fetchCmd.Run(); err != nil {
		return fmt.Errorf("failed to fetch: %w", err)
	}

	// Pull the latest changes
	pullCmd := gitArgs("pull", "origin", currentBranch)
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

// GetLocalConfig gets a local git config value for a repository
func GetLocalConfig(repoPath, key string) (string, error) {
	cmd := exec.Command("git", "config", "--local", key)
	cmd.Dir = repoPath
	output, err := cmd.Output()
	if err != nil {
		return "", nil
	}
	return strings.TrimSpace(string(output)), nil
}

// SetLocalConfig sets a local git config value for a repository
func SetLocalConfig(repoPath, key, value string) error {
	cmd := exec.Command("git", "config", "--local", key, value)
	cmd.Dir = repoPath
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to set %s: %w", key, err)
	}
	return nil
}

// GetUserConfig gets the user.name and user.email from a repository
func GetUserConfig(repoPath string) (username, email string, err error) {
	username, err = GetLocalConfig(repoPath, "user.name")
	if err != nil {
		return "", "", err
	}
	email, err = GetLocalConfig(repoPath, "user.email")
	if err != nil {
		return "", "", err
	}
	return username, email, nil
}

// SetUserConfig sets the user.name and user.email for a repository
func SetUserConfig(repoPath, username, email string) error {
	if err := SetLocalConfig(repoPath, "user.name", username); err != nil {
		return err
	}
	if err := SetLocalConfig(repoPath, "user.email", email); err != nil {
		return err
	}
	return nil
}
