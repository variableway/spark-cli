package registry

import (
	"io/fs"
	"os"
	"path/filepath"
	"strings"
)

var ignoreDirs = map[string]bool{
	"node_modules": true,
	"venv":         true,
	".venv":        true,
	"__pycache__":  true,
	"dist":         true,
	"build":        true,
}

// Scan recursively discovers git repositories with an origin remote under root.
// The returned Project.Path is slash-separated and relative to root.
func Scan(root string) ([]Project, error) {
	absRoot, err := filepath.Abs(root)
	if err != nil {
		return nil, err
	}

	var projects []Project
	err = filepath.WalkDir(absRoot, func(path string, d fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return nil
		}
		if !d.IsDir() {
			return nil
		}
		if path == absRoot {
			return nil
		}
		if strings.HasPrefix(d.Name(), ".") {
			return filepath.SkipDir
		}
		if ignoreDirs[d.Name()] {
			return filepath.SkipDir
		}

		url := remoteURL(path)
		if url == "" {
			return nil
		}

		rel, err := filepath.Rel(absRoot, path)
		if err != nil {
			return nil
		}
		projects = append(projects, Project{
			Name: filepath.Base(path),
			Repo: normalizeURL(url),
			Path: filepath.ToSlash(rel),
		})
		return nil
	})

	return projects, err
}

func isGitRepo(path string) bool {
	gitPath := filepath.Join(path, ".git")
	_, err := os.Stat(gitPath)
	return err == nil
}

func remoteURL(repoPath string) string {
	if !isGitRepo(repoPath) {
		return ""
	}

	gitPath := filepath.Join(repoPath, ".git")
	info, err := os.Stat(gitPath)
	if err != nil {
		return ""
	}

	configDir := gitPath
	if !info.IsDir() {
		configDir = resolveGitFileDir(repoPath, gitPath)
		if configDir == "" {
			return ""
		}
	}

	return parseRemoteOrigin(filepath.Join(configDir, "config"))
}

func resolveGitFileDir(repoPath, gitFile string) string {
	data, err := os.ReadFile(gitFile)
	if err != nil {
		return ""
	}
	line := strings.TrimSpace(string(data))
	if !strings.HasPrefix(line, "gitdir:") {
		return ""
	}
	dir := strings.TrimSpace(strings.TrimPrefix(line, "gitdir:"))
	if !filepath.IsAbs(dir) {
		dir = filepath.Join(repoPath, dir)
	}
	return dir
}

func parseRemoteOrigin(configPath string) string {
	data, err := os.ReadFile(configPath)
	if err != nil {
		return ""
	}

	inOrigin := false
	for _, raw := range strings.Split(string(data), "\n") {
		line := strings.TrimSpace(raw)
		if line == `[remote "origin"]` {
			inOrigin = true
			continue
		}
		if !inOrigin {
			continue
		}
		if strings.HasPrefix(line, "[") {
			inOrigin = false
			continue
		}
		if strings.HasPrefix(line, "url = ") {
			return strings.TrimSpace(strings.TrimPrefix(line, "url = "))
		}
	}
	return ""
}
