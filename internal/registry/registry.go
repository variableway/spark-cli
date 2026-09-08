package registry

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"go.yaml.in/yaml/v3"
)

type Project struct {
	Name string `yaml:"name"`
	Repo string `yaml:"repo"`
	Path string `yaml:"path,omitempty"`
	Desc string `yaml:"desc,omitempty"`
}

type Registry struct {
	Projects []Project `yaml:"projects"`
}

func Read(path string) (*Registry, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return &Registry{}, nil
		}
		return nil, fmt.Errorf("read registry: %w", err)
	}

	var reg Registry
	if err := yaml.Unmarshal(data, &reg); err != nil {
		return nil, fmt.Errorf("parse registry %s: %w", path, err)
	}
	return &reg, nil
}

func Write(path string, reg *Registry) error {
	data, err := yaml.Marshal(reg)
	if err != nil {
		return fmt.Errorf("encode registry: %w", err)
	}

	header := "# Project registry\n# Synced by spark repo scan\n\n"
	return os.WriteFile(path, append([]byte(header), data...), 0644)
}

func FindByName(reg *Registry, name string) (*Project, error) {
	for i := range reg.Projects {
		if reg.Projects[i].Name == name {
			return &reg.Projects[i], nil
		}
	}
	return nil, fmt.Errorf("repository %q not found in registry", name)
}

// TargetPath returns the clone destination for a project relative to root.
func TargetPath(root string, p Project) string {
	rel := p.Path
	if rel == "" {
		rel = p.Name
	}
	return filepath.Join(root, filepath.FromSlash(rel))
}

// Merge keeps existing name/desc (matched by path, then repo URL), drops entries
// whose directory no longer exists, and appends newly discovered projects.
func Merge(existing, discovered []Project) []Project {
	byPath := make(map[string]Project, len(discovered))
	byURL := make(map[string]Project, len(discovered))
	for _, p := range discovered {
		byPath[p.Path] = p
		byURL[urlKey(p.Repo)] = p
	}

	final := make([]Project, 0, len(discovered))
	matchedPath := make(map[string]bool, len(discovered))
	matchedURL := make(map[string]bool, len(discovered))

	for _, old := range existing {
		p, ok := byPath[old.Path]
		if !ok {
			p, ok = byURL[urlKey(old.Repo)]
		}
		if !ok {
			continue
		}

		merged := p
		if old.Name != "" {
			merged.Name = old.Name
		}
		if old.Desc != "" {
			merged.Desc = old.Desc
		}
		final = append(final, merged)
		matchedPath[merged.Path] = true
		matchedURL[urlKey(merged.Repo)] = true
	}

	for _, p := range discovered {
		if matchedPath[p.Path] {
			continue
		}
		key := urlKey(p.Repo)
		if matchedURL[key] {
			continue
		}
		matchedURL[key] = true
		final = append(final, p)
	}

	return final
}

func normalizeURL(url string) string {
	if strings.HasPrefix(url, "git@") && strings.Contains(url, ":") {
		parts := strings.SplitN(url[4:], ":", 2)
		if len(parts) == 2 {
			return "https://" + parts[0] + "/" + parts[1]
		}
	}
	return url
}

func urlKey(url string) string {
	u := normalizeURL(url)
	u = strings.TrimSuffix(u, "/")
	u = strings.TrimSuffix(u, ".git")
	return u
}
