package mono

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
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

// ExtractRepoName extracts repository name from a git URL
func ExtractRepoName(repoURL string) string {
	// Remove trailing .git if present
	repoURL = strings.TrimSuffix(repoURL, ".git")
	
	// Handle different URL formats
	// HTTPS: https://github.com/user/repo
	// SSH: git@github.com:user/repo
	// Simple: user/repo
	
	// Try SSH format first
	sshPattern := regexp.MustCompile(`git@[^:]+:([^/]+/[^/]+)$`)
	if matches := sshPattern.FindStringSubmatch(repoURL); len(matches) > 1 {
		parts := strings.Split(matches[1], "/")
		return parts[len(parts)-1]
	}
	
	// Try HTTPS format
	if strings.Contains(repoURL, "://") {
		parts := strings.Split(repoURL, "/")
		if len(parts) > 0 {
			return parts[len(parts)-1]
		}
	}
	
	// Simple format: user/repo or just repo
	parts := strings.Split(repoURL, "/")
	return parts[len(parts)-1]
}

// AddRemoteRepoAsSubmodule adds a remote git repository as a submodule
func AddRemoteRepoAsSubmodule(parentDir string, repoURL string, submodulePath string) error {
	absParent, err := filepath.Abs(parentDir)
	if err != nil {
		return fmt.Errorf("failed to resolve parent dir: %w", err)
	}

	// Determine submodule name/path
	if submodulePath == "" {
		submodulePath = ExtractRepoName(repoURL)
	}
	
	// Remove trailing .git for the path name
	submodulePath = strings.TrimSuffix(submodulePath, ".git")

	// Check if destination already exists
	targetPath := filepath.Join(absParent, submodulePath)
	if _, err := os.Stat(targetPath); err == nil {
		return fmt.Errorf("destination path already exists: %s", submodulePath)
	}

	// Initialize git repo if not exists
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

	// Check if already a submodule
	gitmodulesPath := filepath.Join(absParent, ".gitmodules")
	if _, err := os.Stat(gitmodulesPath); err == nil {
		// Check if submodule already exists
		checkCmd := exec.Command("git", "config", "--file", gitmodulesPath, fmt.Sprintf("submodule.%s.path", submodulePath))
		checkCmd.Dir = absParent
		if err := checkCmd.Run(); err == nil {
			return fmt.Errorf("submodule '%s' already exists", submodulePath)
		}
	}

	fmt.Printf("Adding submodule: %s (%s)\n", submodulePath, repoURL)

	// Add submodule using git submodule add
	cmd := exec.Command("git", "submodule", "add", "-f", repoURL, submodulePath)
	cmd.Dir = absParent
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to add submodule: %w", err)
	}

	// Stage .gitmodules
	addModulesCmd := exec.Command("git", "add", ".gitmodules")
	addModulesCmd.Dir = absParent
	if err := addModulesCmd.Run(); err != nil {
		fmt.Printf("Warning: Failed to stage .gitmodules: %v\n", err)
	}

	return nil
}
