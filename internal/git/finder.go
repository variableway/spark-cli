package git

import (
	"os"
	"path/filepath"
)

// FindRepositories scans the given path for git repositories.
// If the path itself is a git repository, it returns that path.
// Otherwise, it scans the immediate subdirectories of the path.
func FindRepositories(rootPath string) ([]string, error) {
	// First check if the rootPath itself is a git repository
	if IsGitRepository(rootPath) {
		absPath, err := filepath.Abs(rootPath)
		if err != nil {
			return nil, err
		}
		return []string{absPath}, nil
	}

	var repos []string
	entries, err := os.ReadDir(rootPath)
	if err != nil {
		return nil, err
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		dirPath := filepath.Join(rootPath, entry.Name())
		if IsGitRepository(dirPath) {
			absPath, err := filepath.Abs(dirPath)
			if err != nil {
				continue
			}
			repos = append(repos, absPath)
		}
	}

	return repos, nil
}

// IsGitRepository checks if the given path is a git repository
func IsGitRepository(path string) bool {
	gitDir := filepath.Join(path, ".git")
	info, err := os.Stat(gitDir)
	return err == nil && (info.IsDir() || info.Mode()&os.ModeSymlink != 0)
}
