package mono

import (
	"fmt"
	"spark/internal/git"
	"os"
	"os/exec"
	"path/filepath"
)

// CreateMonoRepo creates a new mono repository with submodules
func CreateMonoRepo(monoRepoPath string, repos []string) error {
	// Create the mono repo directory
	if err := os.MkdirAll(monoRepoPath, 0755); err != nil {
		return fmt.Errorf("failed to create mono repo directory: %w", err)
	}

	// Initialize git repository
	cmd := exec.Command("git", "init")
	cmd.Dir = monoRepoPath
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to init git repo: %w", err)
	}

	// Create .gitignore
	gitignoreContent := `# Mono repo artifacts
.gitmodules.backup
`
	if err := os.WriteFile(filepath.Join(monoRepoPath, ".gitignore"), []byte(gitignoreContent), 0644); err != nil {
		return fmt.Errorf("failed to create .gitignore: %w", err)
	}

	// Add each repository as a submodule
	for _, repo := range repos {
		repoName := git.GetRepoName(repo)
		remoteURL, err := git.GetRemoteURL(repo)
		if err != nil {
			fmt.Printf("Warning: Could not get remote URL for %s: %v\n", repoName, err)
			continue
		}

		fmt.Printf("Adding submodule: %s\n", repoName)

		// Add submodule
		submoduleCmd := exec.Command("git", "submodule", "add", remoteURL, repoName)
		submoduleCmd.Dir = monoRepoPath
		submoduleCmd.Stdout = os.Stdout
		submoduleCmd.Stderr = os.Stderr
		if err := submoduleCmd.Run(); err != nil {
			fmt.Printf("Warning: Failed to add submodule %s: %v\n", repoName, err)
			continue
		}
	}

	// Initialize and update submodules
	initCmd := exec.Command("git", "submodule", "update", "--init", "--recursive")
	initCmd.Dir = monoRepoPath
	initCmd.Stdout = os.Stdout
	initCmd.Stderr = os.Stderr
	if err := initCmd.Run(); err != nil {
		return fmt.Errorf("failed to init submodules: %w", err)
	}

	// Create initial commit
	addCmd := exec.Command("git", "add", ".")
	addCmd.Dir = monoRepoPath
	if err := addCmd.Run(); err != nil {
		return fmt.Errorf("failed to add files: %w", err)
	}

	commitCmd := exec.Command("git", "commit", "-m", "Initial commit: Add all repositories as submodules")
	commitCmd.Dir = monoRepoPath
	commitCmd.Stdout = os.Stdout
	commitCmd.Stderr = os.Stderr
	if err := commitCmd.Run(); err != nil {
		// It's okay if there's nothing to commit
		fmt.Println("Note: Nothing to commit (this is normal if submodules are already up to date)")
	}

	return nil
}
