package git

import (
	"os"
	"path/filepath"
)

func FindRepositories(rootPath string) ([]string, error) {
	var repos []string

	if IsGitRepository(rootPath) {
		absPath, err := filepath.Abs(rootPath)
		if err != nil {
			return nil, err
		}
		repos = append(repos, absPath)
	}

	entries, err := os.ReadDir(rootPath)
	if err != nil {
		if len(repos) > 0 {
			return repos, nil
		}
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

func IsGitRepository(path string) bool {
	gitDir := filepath.Join(path, ".git")
	info, err := os.Stat(gitDir)
	return err == nil && (info.IsDir() || info.Mode()&os.ModeSymlink != 0)
}
