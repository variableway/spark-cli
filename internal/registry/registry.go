package registry

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"go.yaml.in/yaml/v3"
)

type Project struct {
	Name string `yaml:"name" json:"name"`
	Repo string `yaml:"repo" json:"repo"`
	Path string `yaml:"path,omitempty" json:"path,omitempty"`
	Desc string `yaml:"desc,omitempty" json:"desc,omitempty"`
}

// RegistryVersion is written whenever the registry uses the categorized layout.
const RegistryVersion = 2

// OthersSubcategory is the default bucket for a project that sits directly
// under a category and therefore has no subcategory of its own.
const OthersSubcategory = "others"

// Subcategory groups projects under one category. "others" is always present
// so unclassified projects have a home.
type Subcategory struct {
	Name     string    `yaml:"name" json:"name"`
	Projects []Project `yaml:"projects" json:"projects"`
}

// Category is one top-level bucket (e.g. skills / products / plugins).
type Category struct {
	Name          string        `yaml:"name" json:"name"`
	Subcategories []Subcategory `yaml:"subcategories" json:"subcategories"`
}

// Registry holds either the categorized layout (Version=2, Categories set —
// the canonical format) or the legacy flat layout (Projects only).
// Read() always derives a flattened Projects slice, so callers written against
// the legacy shape keep working.
type Registry struct {
	Version    int        `yaml:"version,omitempty" json:"version,omitempty"`
	Projects   []Project  `yaml:"projects,omitempty" json:"projects,omitempty"`
	Categories []Category `yaml:"categories,omitempty" json:"categories,omitempty"`
}

// IsCategorized reports whether this registry uses the v2 category layout.
func (r *Registry) IsCategorized() bool {
	return r != nil && len(r.Categories) > 0
}

// AllProjects flattens the registry into a single list, preserving order
// (categories -> subcategories -> projects). Legacy flat registries return
// their Projects unchanged.
func (r *Registry) AllProjects() []Project {
	if !r.IsCategorized() {
		return r.Projects
	}
	flat := make([]Project, 0, len(r.Projects))
	for _, c := range r.Categories {
		for _, s := range c.Subcategories {
			flat = append(flat, s.Projects...)
		}
	}
	return flat
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
	if reg.IsCategorized() {
		// v2 file: derive the flattened view so legacy callers (clone/list/find)
		// keep working against a categorized registry.
		reg.Version = RegistryVersion
		reg.Projects = reg.AllProjects()
	}
	return &reg, nil
}

// wire shapes keep the on-disk formats exactly distinguishable:
// legacy = {projects: [...]}, v2 = {version: 2, categories: [...]}.
type legacyYAML struct {
	Projects []Project `yaml:"projects"`
}
type categorizedYAML struct {
	Version    int        `yaml:"version"`
	Categories []Category `yaml:"categories"`
}
type legacyJSON struct {
	Projects []Project `json:"projects"`
}
type categorizedJSON struct {
	Version    int        `json:"version"`
	Categories []Category `json:"categories"`
}

func Write(path string, reg *Registry) error {
	var (
		data []byte
		err  error
	)
	if reg.IsCategorized() {
		data, err = yaml.Marshal(categorizedYAML{Version: RegistryVersion, Categories: reg.Categories})
	} else {
		data, err = yaml.Marshal(legacyYAML{Projects: reg.Projects})
	}
	if err != nil {
		return fmt.Errorf("encode registry: %w", err)
	}

	header := "# Project registry\n# Synced by spark repo scan\n\n"
	return os.WriteFile(path, append([]byte(header), data...), 0644)
}

func WriteJSON(path string, reg *Registry) error {
	var (
		data []byte
		err  error
	)
	if reg.IsCategorized() {
		data, err = json.MarshalIndent(categorizedJSON{Version: RegistryVersion, Categories: reg.Categories}, "", "  ")
	} else {
		data, err = json.MarshalIndent(legacyJSON{Projects: reg.Projects}, "", "  ")
	}
	if err != nil {
		return fmt.Errorf("encode registry: %w", err)
	}
	return os.WriteFile(path, append(data, '\n'), 0644)
}

func FindByName(reg *Registry, name string) (*Project, error) {
	projects := reg.AllProjects()
	for i := range projects {
		if projects[i].Name == name {
			return &projects[i], nil
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
