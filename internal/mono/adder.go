package mono

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"spark/internal/git"
	"strings"
)

func AddExistingReposAsSubmodules(parentDir string, repoPaths []string) error {
	absParent, err := filepath.Abs(parentDir)
	if err != nil {
		return fmt.Errorf("failed to resolve parent dir: %w", err)
	}

	if !git.IsGitRepository(absParent) {
		fmt.Println("Initializing git repository...")
		cmd := exec.Command("git", "init")
		cmd.Dir = absParent
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		if err := cmd.Run(); err != nil {
			return fmt.Errorf("failed to init git repo: %w", err)
		}
	}

	modulesBase := filepath.Join(absParent, ".git", "modules")
	if err := os.MkdirAll(modulesBase, 0755); err != nil {
		return fmt.Errorf("failed to create modules dir: %w", err)
	}

	gitmodulesPath := filepath.Join(absParent, ".gitmodules")

	for _, repoPath := range repoPaths {
		absRepo, err := filepath.Abs(repoPath)
		if err != nil {
			fmt.Printf("Warning: Could not resolve path %s: %v\n", repoPath, err)
			continue
		}

		repoName := filepath.Base(absRepo)
		remoteURL, err := git.GetRemoteURL(absRepo)
		if err != nil {
			fmt.Printf("Warning: Could not get remote URL for %s: %v\n", repoName, err)
			continue
		}

		// Skip if already a submodule (.git is a file pointing to modules)
		gitEntry := filepath.Join(absRepo, ".git")
		if info, err := os.Lstat(gitEntry); err == nil && !info.IsDir() {
			fmt.Printf("Skipping %s: already a submodule\n", repoName)
			continue
		}

		fmt.Printf("Adding submodule: %s (%s)\n", repoName, remoteURL)

		// Move .git directory to .git/modules/<name>
		targetModuleDir := filepath.Join(modulesBase, repoName)
		if _, err := os.Stat(targetModuleDir); err == nil {
			fmt.Printf("Warning: Module dir already exists for %s, skipping\n", repoName)
			continue
		}

		if err := os.Rename(gitEntry, targetModuleDir); err != nil {
			fmt.Printf("Warning: Failed to move .git for %s: %v\n", repoName, err)
			continue
		}

		// Create .git file pointing to modules dir
		relPath := filepath.Join("..", ".git", "modules", repoName)
		if err := os.WriteFile(gitEntry, []byte("gitdir: "+relPath+"\n"), 0644); err != nil {
			fmt.Printf("Warning: Failed to create .git file for %s: %v\n", repoName, err)
			// Try to restore
			os.Rename(targetModuleDir, gitEntry)
			continue
		}

		// Update core.worktree in the module config
		setWorktreeCmd := exec.Command("git", "config", "--file",
			filepath.Join(targetModuleDir, "config"),
			"core.worktree", "../../../"+repoName)
		setWorktreeCmd.Dir = absParent
		if err := setWorktreeCmd.Run(); err != nil {
			fmt.Printf("Warning: Failed to set worktree for %s: %v\n", repoName, err)
		}

		// Add entry to .gitmodules
		setPathCmd := exec.Command("git", "config", "--file", gitmodulesPath,
			fmt.Sprintf("submodule.%s.path", repoName), repoName)
		setPathCmd.Dir = absParent
		setPathCmd.Stdout = os.Stdout
		setPathCmd.Stderr = os.Stderr
		if err := setPathCmd.Run(); err != nil {
			fmt.Printf("Warning: Failed to set .gitmodules path for %s: %v\n", repoName, err)
			continue
		}

		setURLCmd := exec.Command("git", "config", "--file", gitmodulesPath,
			fmt.Sprintf("submodule.%s.url", repoName), remoteURL)
		setURLCmd.Dir = absParent
		setURLCmd.Stdout = os.Stdout
		setURLCmd.Stderr = os.Stderr
		if err := setURLCmd.Run(); err != nil {
			fmt.Printf("Warning: Failed to set .gitmodules url for %s: %v\n", repoName, err)
			continue
		}

		// Stage the submodule
		addCmd := exec.Command("git", "add", repoName)
		addCmd.Dir = absParent
		if err := addCmd.Run(); err != nil {
			fmt.Printf("Warning: Failed to stage submodule %s: %v\n", repoName, err)
		}
	}

	// Stage .gitmodules if it exists
	if _, err := os.Stat(gitmodulesPath); err == nil {
		addModulesCmd := exec.Command("git", "add", ".gitmodules")
		addModulesCmd.Dir = absParent
		if err := addModulesCmd.Run(); err != nil {
			fmt.Printf("Warning: Failed to stage .gitmodules: %v\n", err)
		}
	}

	return nil
}

func FindSubRepos(parentDir string) ([]string, error) {
	absParent, err := filepath.Abs(parentDir)
	if err != nil {
		return nil, err
	}

	entries, err := os.ReadDir(absParent)
	if err != nil {
		return nil, err
	}

	var repos []string
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		if strings.HasPrefix(entry.Name(), ".") {
			continue
		}
		dirPath := filepath.Join(absParent, entry.Name())
		if git.IsGitRepository(dirPath) {
			repos = append(repos, dirPath)
		}
	}

	return repos, nil
}
