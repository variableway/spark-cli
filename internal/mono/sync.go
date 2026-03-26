package mono

import (
	"fmt"
	"os"
	"os/exec"
)

// SyncSubmodules updates all submodules to their latest versions
func SyncSubmodules(monoRepoPath string) error {
	// Fetch updates for all submodules
	fetchCmd := exec.Command("git", "submodule", "foreach", "git", "fetch", "--all")
	fetchCmd.Dir = monoRepoPath
	fetchCmd.Stdout = os.Stdout
	fetchCmd.Stderr = os.Stderr
	if err := fetchCmd.Run(); err != nil {
		return fmt.Errorf("failed to fetch submodules: %w", err)
	}

	// Update all submodules to the latest commit on their tracking branch
	updateCmd := exec.Command("git", "submodule", "update", "--remote", "--merge")
	updateCmd.Dir = monoRepoPath
	updateCmd.Stdout = os.Stdout
	updateCmd.Stderr = os.Stderr
	if err := updateCmd.Run(); err != nil {
		return fmt.Errorf("failed to update submodules: %w", err)
	}

	// Check if there are changes to commit
	statusCmd := exec.Command("git", "status", "--porcelain")
	statusCmd.Dir = monoRepoPath
	output, err := statusCmd.Output()
	if err != nil {
		return fmt.Errorf("failed to check status: %w", err)
	}

	if len(output) > 0 {
		// There are changes, commit them
		addCmd := exec.Command("git", "add", ".")
		addCmd.Dir = monoRepoPath
		if err := addCmd.Run(); err != nil {
			return fmt.Errorf("failed to add changes: %w", err)
		}

		commitCmd := exec.Command("git", "commit", "-m", "Update submodules to latest versions")
		commitCmd.Dir = monoRepoPath
		commitCmd.Stdout = os.Stdout
		commitCmd.Stderr = os.Stderr
		if err := commitCmd.Run(); err != nil {
			return fmt.Errorf("failed to commit changes: %w", err)
		}

		fmt.Println("Changes committed to mono repo")
	}

	return nil
}

// InitSubmodules initializes all submodules in the mono repo
func InitSubmodules(monoRepoPath string) error {
	cmd := exec.Command("git", "submodule", "update", "--init", "--recursive")
	cmd.Dir = monoRepoPath
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to init submodules: %w", err)
	}
	return nil
}
